# -*- coding: utf-8 -*-
"""Netlify kimlik bilgilerini sınar — Instagram yüklemesi denemeden ÖNCE.

Instagram akışı videoyu geçici olarak Netlify'a deploy edip herkese açık bir URL
üretiyor (bkz. upload/instagram_upload.py). Token süresi dolduğunda bu adım 401
veriyor ve tüm Instagram yüklemeleri sessizce duruyor — 2026-09-08'de tam olarak
bu oldu ve 25+ koşu boyunca fark edilmedi.

Kullanım:
    python netlify_kontrol.py

Token'ı EKRANA YAZMAZ; yalnızca çalışıp çalışmadığını söyler.
"""
import io
import json
import os
import sys

GIZLI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "upload", "netlify_client_secrets.json")


def _cikti_utf8() -> None:
    """Çıktı akışını UTF-8'e çeker — SADECE `main()` içinden, import anında DEĞİL.

    NEDEN (2026-09-12, üçüncü duman koşusu): bu modül eskiden MODÜL DÜZEYİNDE
    `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` yapıyordu. Amaç
    doğruydu (cp1254 konsolunda ✓/✗ çökmesin) ama yeri yanlıştı:

    * `import netlify_kontrol` yapan HERKESİN stdout'u yerinden ediliyordu —
      `saglik_kontrol.netlify_araci()` bunu SAATLİK hattın içinde import ediyor.
    * pytest altında ölümcül: pytest stdout'u kendi yakalama dosyasıyla değiştirir;
      yeni sarmalayıcı o dosyanın `buffer`ını PAYLAŞIR, eski `TextIOWrapper`
      referanssız kalıp GC edilince ortak tamponu KAPATIR ve sonraki HER test
      `ValueError: I/O operation on closed file` ile düşer (bir koşuda 32 ERROR).
    * Üretimde SESSİZDİ: Görev Zamanlayıcı `pythonw.exe` kullanıyor, orada
      `sys.stdout` None ve `hasattr(None, "buffer")` False — dal hiç girilmiyordu.
      Konsoldan elle `python auto_process.py` çalıştıran biri ise stdout'unun
      değiştiğini görürdü.

    Doğru desen `upload/tiktok_publish_plan._cikti_utf8()`: `reconfigure()`
    yeni bir sarmalayıcı YARATMAZ, mevcut akışı yerinde yeniden yapılandırır
    (kapanacak eski nesne yok) ve yalnızca CLI girişinde çağrılır. `sys.stdout`
    None ise (pythonw) ya da `reconfigure` yoksa (çok eski Python / özel akış)
    sessizce geçilir — bu yardımcı sağlık kontrolünü ASLA durdurmamalı.
    """
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


def main() -> int:
    # İLK SATIR: aşağıdaki her mesaj Türkçe ve ✓ içeriyor; cp1254'e
    # yönlendirilmiş (boru/dosya) bir stdout ilk print'te çökerdi.
    _cikti_utf8()
    if not os.path.isfile(GIZLI):
        print("HATA: dosya yok ->", GIZLI)
        return 2

    try:
        creds = json.load(io.open(GIZLI, encoding="utf-8"))
    except ValueError as e:
        print("HATA: dosya geçerli JSON değil ->", e)
        return 2

    token = (creds.get("token") or "").strip()
    site_id = (creds.get("site_id") or "").strip()
    print(f"token   : {len(token)} karakter" if token else "token   : YOK")
    print(f"site_id : {site_id or 'YOK'}")
    if not token or not site_id:
        print("\nSONUÇ: eksik alan var, doldurulmalı.")
        return 2

    import requests
    basliklar = {"Authorization": f"Bearer {token}"}

    # 1) Token gecerli mi
    try:
        r = requests.get("https://api.netlify.com/api/v1/user",
                         headers=basliklar, timeout=15)
    except requests.RequestException as e:
        print("\nHATA: Netlify'a ulaşılamadı ->", type(e).__name__)
        return 2

    if r.status_code == 401:
        print("\nSONUÇ: TOKEN GEÇERSİZ (401) — süresi dolmuş veya iptal edilmiş.")
        return 1
    if r.status_code != 200:
        print(f"\nSONUÇ: beklenmeyen yanıt ({r.status_code}) -> {r.text[:200]}")
        return 1
    print("token   : GEÇERLİ ✓  (hesap: %s)" % (r.json().get("email") or "?"))

    # 2) site_id bu hesapta var mi
    r2 = requests.get(f"https://api.netlify.com/api/v1/sites/{site_id}",
                      headers=basliklar, timeout=15)
    if r2.status_code == 404:
        print("site_id : BULUNAMADI (404) — site silinmiş ya da başka hesapta.")
        return 1
    if r2.status_code != 200:
        print(f"site_id : beklenmeyen yanıt ({r2.status_code})")
        return 1
    site = r2.json()
    print("site_id : GEÇERLİ ✓  (ad: %s, url: %s)"
          % (site.get("name"), site.get("ssl_url") or site.get("url")))

    print("\nSONUÇ: Netlify tarafı hazır — Instagram yüklemeleri açılabilir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
