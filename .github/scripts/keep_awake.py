import os
import sys

from playwright.sync_api import sync_playwright

APP_URL = os.environ["APP_URL"]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5_000)

    button = page.get_by_role("button", name="Yes, get this app back up!")
    if button.count() > 0:
        print("Uygulama uyuyordu, uyandırılıyor...")
        button.click()
        try:
            button.wait_for(state="hidden", timeout=120_000)
            print("Uyandı.")
        except Exception:
            print("Buton kaybolmadı, uyandırma başarısız olabilir.")
            browser.close()
            sys.exit(1)
    else:
        print("Uygulama zaten açık.")

    page.wait_for_timeout(10_000)
    browser.close()
