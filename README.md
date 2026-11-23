<p align="center">
  <img src="gorseller/okul_logo.png" alt="Okul Logo" width="120"/>
</p>

# AI Staj Asistanı

Üniversite öğrencilerinin staj süreciyle ilgili sorularını, okulun resmi staj dökümanlarına dayanarak yanıtlayan, **RAG (Retrieval-Augmented Generation)** tabanlı bir yapay zeka **agent**'ı. Cevap dökümanlarda yoksa, öğrenci için staj komisyonuna hazır bir mail taslağı oluşturabilir (**MCP** aracı ile).

🔗 **Canlı Demo:** [ai-staj-asistan.streamlit.app](https://ai-staj-asistan.streamlit.app/)

## 📌 Proje Hakkında

Staj sürecine dair güncel bilgiler (başvuru adımları, staj süresi, gerekli belgeler, İSG sertifikası vb.) genellikle dağınık PDF ve Word dökümanlarında yer alıyor. Bu proje, öğrencilerin bu bilgilere doğal bir sohbet arayüzü üzerinden, saniyeler içinde ve doğru kaynaktan erişebilmesini sağlıyor.

Sistem, kullanıcının sorusuna cevap üretirken **sadece okulun resmi dökümanlarındaki bilgilere dayanır**, böylece yanlış veya uydurma bilgi verme riski minimize edilir.

## 🛠️ Kullanılan Teknolojiler

- **Python** – Ana geliştirme dili
- **Streamlit** – Web arayüzü
- **ChromaDB** – Vector database
- **Sentence Transformers** (multilingual embedding) – Türkçe metinler için anlamsal arama
- **Google Gemini API** – Doğal dilde cevap üretimi ve function calling ile agent döngüsü (LLM)
- **MCP (Model Context Protocol)** – Mail aracını ayrı bir server olarak sunma
- **pdfplumber / python-docx** – PDF ve Word dökümanlarından metin çıkarma

## ⚙️ Nasıl Çalışıyor?

1. **Döküman İşleme** – Okulun staj dökümanları (PDF/Word) okunup metne çevrilir
2. **Parçalama (Chunking)** – Metinler, bağlamı koruyacak şekilde küçük parçalara bölünür
3. **Embedding & Vector Database** – Her parça, anlamsal aramaya uygun hale getirilip ChromaDB'ye kaydedilir
4. **Agent** – Gemini, soruya göre hangi aracı kullanacağına kendisi karar verir:
   - `dokumanlarda_ara` → ChromaDB'de en alakalı döküman parçalarını bulur
   - `komisyona_mail_hazirla` → MCP server'daki araç; komisyona hazır mail linki üretir
5. **Generation** – Araç sonuçlarına dayanarak doğal bir cevap üretilir
6. **Arayüz** – Tüm süreç, Streamlit ile oluşturulan sohbet arayüzünde kullanıcıya sunulur

```
Kullanıcı Sorusu → Agent (Gemini)
                     ├─ dokumanlarda_ara (ChromaDB) → Cevap
                     └─ Cevap yoksa → "Mail hazırlayayım mı?" → Ad, soyad, öğrenci no
                                       → komisyona_mail_hazirla (MCP) → "Gmail'de aç" / "Mail uygulamasında aç"
```

### 📧 Komisyona Mail Özelliği

- Hiçbir hesaba giriş yapılmaz, mail **otomatik gönderilmez**. Sadece hazır doldurulmuş bir link üretilir; öğrenci maili kontrol edip kendisi gönderir.
- Alıcı adresi kodda sabittir, agent değiştiremez.
- Cihaz otomatik algılanır: bilgisayarda **Gmail'de aç**, telefonda **Mail uygulamasında aç** butonu gösterilir.

## ✨ Özellikler

- 🔍 Anlamsal arama (kelime eşleşmesi değil, anlam bazlı sonuç bulma)
- 🌐 Türkçe dil desteği için multilingual embedding modeli
- 🤖 Araç kullanan agent yapısı (Gemini function calling)
- 📧 Cevap bulunamazsa komisyona tek tıkla mail taslağı (MCP)
- 🧠 Sohbet geçmişini hatırlama
- 🛡️ Hata durumlarında kullanıcı dostu geri bildirim
- 💬 Gerçek zamanlı, akıcı sohbet arayüzü
- 🏫 Kuruma özel, tanıdık bir görünüm (okul logosu ile)

## 🚀 Yerel Kurulum

```bash
# Repoyu klonla
git clone https://github.com/Selimcagan32/ai-staj-asistan.git
cd ai-staj-asistan

# Sanal ortam oluştur ve aktive et
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Mac/Linux

# Gerekli kütüphaneleri kur
pip install -r requirements.txt

# .env dosyası oluştur ve API key'ini ekle
echo GEMINI_API_KEY=senin_api_keyin > .env

# Uygulamayı çalıştır
streamlit run app.py
```

## 📂 Proje Yapısı

```
ai-staj-asistan/
├── app.py                  # Streamlit arayüzü
├── chatbot.py               # RAG mantığı ve Gemini API entegrasyonu
├── document_loader.py       # PDF/Word/txt döküman okuma
├── text_splitter.py         # Metin parçalama (chunking)
├── vector_db.py              # ChromaDB entegrasyonu
├── dokumanlar/                # Staj ile ilgili resmi dökümanlar
├── requirements.txt
└── README.md
```

## 🎯 Gelecek Geliştirmeler

- [ ] Kullanıcı geri bildirimi (👍/👎) ile cevap kalitesini takip etme
- [ ] Sık sorulan soruların analitiği
- [ ] Çoklu döküman kaynağı desteği (farklı bölümler için)

## 👤 Geliştirici

**Selim Çağan**
[GitHub](https://github.com/Selimcagan32)