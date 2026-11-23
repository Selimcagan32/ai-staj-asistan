import re


def metni_parcala(metin, parca_boyutu=500, ortusme=50):
    """
    Uzun bir metni sabit boyutlu parçalara böler.
    Başlık yapısı olmayan dosyalar (PDF/Word) için kullanılır.

    parca_boyutu: her parçanın yaklaşık karakter sayısı
    ortusme: parçalar arasında ne kadar örtüşme olacağı
             (cümlelerin ortadan bölünmesini azaltmak için)
    """
    parcalar = []
    baslangic = 0

    while baslangic < len(metin):
        bitis = baslangic + parca_boyutu
        parca = metin[baslangic:bitis]
        parcalar.append(parca)
        baslangic = bitis - ortusme  # bir sonraki parça biraz geriden başlasın

    return parcalar


def basliklara_gore_parcala(metin):
    """
    "# Konu" ve "## Soru" başlıklı metni, her "## Soru" ve cevabı ayrı bir parça
    olacak şekilde böler. Her parçanın başına konu başlığı eklenir ki parça tek
    başına okunduğunda da hangi konuya ait olduğu anlaşılsın.
    """
    konu = ""
    konu_eslesme = re.search(r"^# (.+)$", metin, flags=re.MULTILINE)
    if konu_eslesme:
        konu = konu_eslesme.group(1).strip()

    bolumler = re.split(r"^## ", metin, flags=re.MULTILINE)[1:]  # ilk eleman konu başlığı
    parcalar = []
    for bolum in bolumler:
        bolum = bolum.strip()
        if bolum:
            parcalar.append(f"Konu: {konu}\nSoru: {bolum}" if konu else bolum)
    return parcalar


def tum_dokumanlari_parcala(dokumanlar, parca_boyutu=900, ortusme=150):
    """
    document_loader'dan gelen döküman listesini alır,
    her birini parçalara böler.

    "## " başlıkları olan dosyalar soru-cevap bazlı, diğerleri sabit boyutlu bölünür.

    Dönen format: [{"dosya_adi": ..., "parca_no": ..., "metin": ...}, ...]
    """
    tum_parcalar = []

    for dokuman in dokumanlar:
        if re.search(r"^## ", dokuman["metin"], flags=re.MULTILINE):
            parcalar = basliklara_gore_parcala(dokuman["metin"])
        else:
            parcalar = metni_parcala(dokuman["metin"], parca_boyutu, ortusme)

        for i, parca in enumerate(parcalar):
            tum_parcalar.append({
                "dosya_adi": dokuman["dosya_adi"],
                "parca_no": i,
                "metin": parca
            })

    return tum_parcalar


# Test etmek için
if __name__ == "__main__":
    from document_loader import tum_dokumanlari_yukle

    dokumanlar = tum_dokumanlari_yukle()
    parcalar = tum_dokumanlari_parcala(dokumanlar)

    print(f"\nToplam {len(parcalar)} parça oluşturuldu.\n")

    # İlk 2 parçayı örnek olarak göster
    for parca in parcalar[:2]:
        print(f"--- {parca['dosya_adi']} - Parça {parca['parca_no']} ---")
        print(parca['metin'])
        print()
