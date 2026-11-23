"""
Mail MCP Server

Agent'ın kullanabileceği tek bir araç sunar: komisyona_mail_hazirla.
Bu araç mail GÖNDERMEZ ve hiçbir hesaba giriş yapmaz.
Sadece mail metnini hazır doldurulmuş iki link üretir:
    - gmail_link  -> bilgisayarda Gmail'in "Yeni mail" ekranını açar
    - mailto_link -> telefonda varsayılan mail uygulamasını açar
Gönder'e basmak öğrenciye kalır.

Tek başına çalıştırma (test için):
    python mail_mcp_server.py
"""

import json
from urllib.parse import quote, urlencode

from mcp.server.mcpserver import MCPServer

# Alıcı sabit: agent başka bir adrese mail hazırlayamaz
KOMISYON_MAIL = "muhammetgencer@sdu.edu.tr"

mcp = MCPServer("staj-mail")


@mcp.tool()
def komisyona_mail_hazirla(konu: str, icerik: str) -> str:
    """
    Staj komisyonuna gönderilmek üzere hazır doldurulmuş mail linkleri üretir.
    Maili göndermez. Öğrenci linke tıklar, maili kontrol eder ve kendisi gönderir.

    konu: mailin konu satırı
    icerik: mailin gövdesi (düz metin)
    """
    icerik = icerik.replace("\r\n", "\n").replace("\n", "\r\n")  # mail standardındaki satır sonu

    gmail_link = "https://mail.google.com/mail/?" + urlencode(
        {"view": "cm", "fs": "1", "to": KOMISYON_MAIL, "su": konu, "body": icerik},
        quote_via=quote,
    )
    mailto_link = f"mailto:{KOMISYON_MAIL}?" + urlencode(
        {"subject": konu, "body": icerik},
        quote_via=quote,  # boşluklar "+" değil "%20" olmalı, yoksa mail uygulamasında "+" görünür
    )

    return json.dumps(
        {
            "durum": "Mail hazırlandı. GÖNDERİLMEDİ, öğrenci linkten açıp kendisi gönderecek.",
            "alici": KOMISYON_MAIL,
            "konu": konu,
            "gmail_link": gmail_link,
            "mailto_link": mailto_link,
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    mcp.run()  # stdio üzerinden çalışır: agent bu dosyayı alt süreç olarak başlatır
