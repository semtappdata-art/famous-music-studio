#!/usr/bin/env python3
"""Debug Chrome'daki YouTube/Google oturumunu tespit eder.

YouTube Studio'nun Data API'de YAZILAMAYAN 4 alanı sadece UI'dan
ayarlanabilir (kanal açıklaması, kanal linkleri, subscribedTrailer, banner).
Bunlar için debug Chrome'da (port 9222) bir kez oturum açılması gerekir.

Bu script, o oturumun açılıp açılmadığını cookie veritabanından izler.
Kullanım:
    python youtube_studio_login_check.py            # tek seferlik kontrol
    python youtube_studio_login_check.py --bekle 30 # 30 dakika bekle
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DBG_DIR = os.path.expandvars(r"%LOCALAPPDATA%\ChromeDebugProfile\Default")
COOKIE_DB = os.path.join(DBG_DIR, "Network", "Cookies")

# YouTube oturumunu taşıyan cookie'ler
OTURUM_COOKIE = ("SID", "SSID", "APISID", "SAPISID", "__Secure-3PSID",
                 "__Secure-3PAPISID", "__Secure-1PSID", "LOGIN_INFO")


def oturum_cookie_oku():
    """Debug profilin cookie DB'sini (kilidi atlayarak) oku."""
    if not os.path.isfile(COOKIE_DB):
        return set(), set()
    tmp = COOKIE_DB + ".logincheck"
    try:
        shutil.copy2(COOKIE_DB, tmp)
    except OSError:
        return set(), set()
    try:
        con = sqlite3.connect(tmp)
        rows = con.execute(
            "select host_key, name from cookies "
            "where host_key like '%youtube.com' or host_key like '%.google.com'"
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return set(), set()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    isimler = {r[1] for r in rows}
    hostlar = {r[0] for r in rows}
    return isimler, hostlar


def studio_erisilebilir_mi():
    """Debug Chrome'da studio.youtube.com oturumu var mı (CDP üzerinden)."""
    import urllib.request
    import json
    try:
        url = "http://127.0.0.1:9222/json/list"
        with urllib.request.urlopen(url, timeout=5) as r:
            sekmeler = json.load(r)
    except Exception:
        return None
    for t in sekmeler:
        if "studio.youtube.com" in (t.get("url") or ""):
            return t.get("url")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bekle", type=int, default=0,
                    help="kaç dakika beklensin (0 = tek kontrol)")
    args = ap.parse_args()

    if not os.path.isfile(COOKIE_DB):
        print(f"HATA: debug Chrome cookie DB yok: {COOKIE_DB}")
        print("Önce launch_chrome_debug_silent.vbs ile Chrome'u baslat.")
        return 2

    deadline = time.time() + args.bekle * 60
    while True:
        isimler, hostlar = oturum_cookie_oku()
        bulunan = sorted(set(isimler) & set(OTURUM_COOKIE))
        sayfa = studio_erisilebilir_mi()

        if bulunan:
            print(f"LOGIN OK  — oturum cookie: {', '.join(bulunan)}")
            if sayfa:
                print(f"Studio sekmesi: {sayfa}")
            return 0

        kalan = int(deadline - time.time())
        if kalan <= 0:
            print("LOGIN YOK — oturum cookie'si bulunamadi.")
            print("Debug Chrome penceresinde (gorunur) Google'a giris yap.")
            print("Beklenen hesap: free.famous7@gmail.com")
            return 1
        print(f"... bekleniyor ({kalan // 60} dk {kalan % 60} sn kaldi) "
              f"toplam youtube/google cookie: {len(isimler)}")
        time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
