"""
Staj Asistanı Agent

Gemini function calling ile çalışan basit bir agent döngüsü.
İki aracı var:
    - dokumanlarda_ara      -> ChromaDB'de staj dökümanlarını arar (yerel araç)
    - komisyona_mail_hazirla -> mail_mcp_server.py'deki MCP aracı (mail göndermez, link üretir)

MCP server her çağrıda alt süreç olarak açılıp kapatılır.
"""

import asyncio
import json
import os
import re
import sys
import time
import traceback

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import Client, StdioServerParameters

from vector_db import benzer_parcalari_bul

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-flash-lite-latest"
MAKS_ADIM = 5  # sonsuz araç döngüsüne karşı sınır
ON_ARAMA_MIN_KELIME = 3  # bundan kısa mesajlarda baştan döküman araması yapılmaz

MCP_SERVER = StdioServerParameters(
    command=sys.executable,
    args=[os.path.join(os.path.dirname(os.path.abspath(__file__)), "mail_mcp_server.py")],
)

SISTEM_MESAJI = """Sen bir üniversitenin staj süreciyle ilgili sorulara cevap veren, samimi bir asistansın. Türkçe, kısa ve net cevap ver.

SADECE selamlaşma veya "sen kimsin" gibi sorularda kendini kısaca tanıt: staj süresi, başvuru adımları, staj raporu gibi konularda yardımcı olduğunu söyle. Bu tür mesajlarda hiçbir araç çağırma. Diğer cevaplara tanıtım veya selamlama EKLEME, doğrudan soruyu cevapla.

Öğrencinin son mesajının altında "[OTOMATİK DÖKÜMAN ARAMASI]" başlığıyla döküman parçaları verilebilir. Bu parçaları sistem bulmuştur, öğrenci yazmamıştır.
- Bu parçalar soruyu cevaplıyorsa araç çağırmadan doğrudan cevap ver.
- Parçalar yetersizse, alakasızsa ya da hiç parça verilmediyse ve soru stajla ilgiliyse, dokumanlarda_ara aracını konuşmanın bağlamına göre daha iyi kelimelerle çağır (örneğin "Peki donanım için?" sorusunda "donanım stajı süresi" diye ara).
SADECE dökümanlardaki bilgilere dayanarak cevap ver. Uydurma bilgi verme. Hiç döküman görmeden asla "bulamadım" deme.

Cevap dökümanlarda yoksa:
1. "Bu konuda dökümanlarda net bir bilgi bulamadım. Staj komisyonuna mail hazırlayayım mı?" diye sor.
2. Öğrenci evet derse adını, soyadını ve öğrenci numarasını iste.
3. Bu bilgiler gelince komisyona_mail_hazirla aracını çağır. Konu kısa olsun. İçerikte kibar bir selamlama ("Sayın Hocam,"), öğrencinin sorusu, ad soyad ve öğrenci numarası olsun.
   konu_turu seçimi:
   - "teslim": staj bittikten sonraki işler (staj teslim tutanağı, staj faaliyet raporu/defteri, değerlendirme formu, belge teslimi). Bu mail Dr.Öğr.Üyesi İbrahim Arda Çankaya'ya gider.
   - "basvuru": staj başvurusu, staj öncesi belgeler, gönüllü staj ve diğer her konu. Bu mail Arş.Gör. Muhammet Çağrı Gencer'e gider.
   Sorunun hangisi olduğundan emin değilsen öğrenciye "Sorun staj başvurusuyla mı, staj teslimiyle mi ilgili?" diye sor.
4. Araç çalışınca mailin kime gittiğini söyle (örneğin "Mailin Arş.Gör. Muhammet Çağrı Gencer'e hazır") ve aşağıdaki butondan açıp kontrol ettikten sonra gönderebileceğini belirt. Linkleri metne YAZMA, butonu uygulama gösteriyor.

Mail asla otomatik gönderilmez, öğrenci kendisi gönderir. Alıcı adresleri sabittir, değiştirilemez."""


DOKUMAN_ARACI = types.FunctionDeclaration(
    name="dokumanlarda_ara",
    description="Staj dökümanlarında (yönerge, esaslar vb.) arama yapar ve en alakalı metin parçalarını döner.",
    parameters_json_schema={
        "type": "object",
        "properties": {"sorgu": {"type": "string", "description": "Aranacak soru veya anahtar kelimeler"}},
        "required": ["sorgu"],
    },
)


# ---------- MCP ----------

async def _mcp_araclari_listele():
    async with Client(MCP_SERVER) as mcp:
        sonuc = await mcp.list_tools()
        return sonuc.tools


async def _mcp_arac_cagir(ad, argumanlar):
    async with Client(MCP_SERVER) as mcp:
        sonuc = await mcp.call_tool(ad, argumanlar)
        metin = "".join(p.text for p in sonuc.content if hasattr(p, "text"))
        if sonuc.is_error:
            # Hatayı Gemini'ye geri ver, düzeltip tekrar denesin
            return json.dumps({"hata": metin}, ensure_ascii=False)
        return metin


def _mcp_araclarini_gemini_formatina_cevir():
    """MCP server'daki araçları Gemini'nin anlayacağı fonksiyon tanımlarına çevirir."""
    araclar = asyncio.run(_mcp_araclari_listele())
    return [
        types.FunctionDeclaration(
            name=a.name,
            description=a.description or "",
            parameters_json_schema=a.input_schema,
        )
        for a in araclar
    ]


_arac_tanimlari = None


def _araclar():
    global _arac_tanimlari
    if _arac_tanimlari is None:
        mcp_araclari = _mcp_araclarini_gemini_formatina_cevir()
        _arac_tanimlari = [types.Tool(function_declarations=[DOKUMAN_ARACI, *mcp_araclari])]
    return _arac_tanimlari


# ---------- Agent ----------

def _araci_calistir(ad, argumanlar, koleksiyon):
    if ad == "dokumanlarda_ara":
        # Gemini bazen şemaya uymayıp "queries" listesi gönderiyor; ikisini de kabul et
        sorgular = argumanlar.get("sorgu") or argumanlar.get("queries") or argumanlar.get("query") or ""
        if isinstance(sorgular, str):
            sorgular = [sorgular]
        parcalar = []
        for sorgu in sorgular:
            for parca in benzer_parcalari_bul(sorgu, koleksiyon, sonuc_sayisi=8)["documents"][0]:
                if parca not in parcalar:
                    parcalar.append(parca)
        return {"parcalar": parcalar[:10]}
    # Geri kalan her şey MCP aracı
    return json.loads(asyncio.run(_mcp_arac_cagir(ad, argumanlar)))


def _gemini_cagir(icerikler, config, deneme_sayisi=3):
    """Gemini'yi çağırır. Model geçici olarak yoğunsa (503) birkaç saniye bekleyip tekrar dener."""
    for deneme in range(deneme_sayisi):
        try:
            return client.models.generate_content(model=MODEL, contents=icerikler, config=config)
        except Exception as e:
            yogun = "503" in str(e) or "UNAVAILABLE" in str(e)
            if not yogun or deneme == deneme_sayisi - 1:
                raise
            time.sleep(2 * (deneme + 1))  # 2 sn, sonra 4 sn bekle


def agent_cevap(gecmis, koleksiyon):
    """
    gecmis: [{"rol": "user"/"assistant", "icerik": "..."}, ...] (son mesaj öğrencinin sorusu)
    Dönen değer: (cevap_metni, mail) -> mail yoksa None, varsa {"gmail_link", "mailto_link", ...}
    """
    icerikler = [
        types.Content(
            role="user" if m["rol"] == "user" else "model",
            parts=[types.Part(text=m["icerik"])],
        )
        for m in gecmis
    ]
    mail = None

    # Hız için: soruyla ilgili parçaları baştan bulup ilk çağrıya ekle.
    # Böylece çoğu soru tek Gemini çağrısında cevaplanır. Çok kısa mesajlarda
    # ("Evet", "Ahmet Yılmaz, 123...") arama anlamsız olduğu için atlanır.
    son_mesaj = gecmis[-1]["icerik"] if gecmis else ""
    if len(son_mesaj.split()) >= ON_ARAMA_MIN_KELIME:
        parcalar = _araci_calistir("dokumanlarda_ara", {"sorgu": son_mesaj}, koleksiyon)["parcalar"]
        on_arama = "[OTOMATİK DÖKÜMAN ARAMASI]\n" + "\n\n---\n\n".join(parcalar)
        icerikler[-1].parts.append(types.Part(text=on_arama))

    try:
        config = types.GenerateContentConfig(
            system_instruction=SISTEM_MESAJI,
            tools=_araclar(),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        for _ in range(MAKS_ADIM):
            yanit = _gemini_cagir(icerikler, config)
            cagrilar = yanit.function_calls or []

            if not cagrilar:
                cevap = (yanit.text or "").strip()
                if mail:
                    # Link butonda gösteriliyor; model kurala uymayıp metne yazdıysa temizle
                    cevap = re.sub(r"<a [^>]*>.*?</a>|https?://\S+|mailto:\S+", "", cevap).strip()
                return cevap, mail

            icerikler.append(yanit.candidates[0].content)
            cevap_parcalari = []
            for cagri in cagrilar:
                sonuc = _araci_calistir(cagri.name, dict(cagri.args or {}), koleksiyon)
                if cagri.name == "komisyona_mail_hazirla" and "hata" not in sonuc:
                    mail = sonuc
                cevap_parcalari.append(
                    types.Part.from_function_response(name=cagri.name, response=sonuc)
                )
            icerikler.append(types.Content(role="user", parts=cevap_parcalari))

        return "Şu an cevap üretemedim, lütfen sorunu biraz farklı sorar mısın?", mail

    except Exception as e:
        traceback.print_exc()  # detay Streamlit Cloud loglarında görünür, öğrenci görmez
        if any(k in str(e) for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
            return "Şu anda çok yoğunuz, lütfen birkaç dakika sonra tekrar dener misin? 🙏", None
        return "Bir hata oluştu, lütfen tekrar dener misin. Sorun devam ederse staj komisyonuyla iletişime geçebilirsin.", None


if __name__ == "__main__":
    from vector_db import veritabani_olustur

    koleksiyon = veritabani_olustur()
    gecmis = []
    while True:
        soru = input("\nSorunuz (çıkmak için 'q'): ")
        if soru.lower() == "q":
            break
        gecmis.append({"rol": "user", "icerik": soru})
        cevap, mail = agent_cevap(gecmis, koleksiyon)
        gecmis.append({"rol": "assistant", "icerik": cevap})
        print(f"\nCevap: {cevap}")
        if mail:
            print(f"Gmail: {mail['gmail_link']}\nMailto: {mail['mailto_link']}")
