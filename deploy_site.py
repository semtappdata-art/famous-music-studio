#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEK KOMUTLU DEPLOY — Famous Music Studio (Madde 30)

GitHub Actions'a GEREK YOK (ve calismiyor: PAT'te `workflow` scope yok,
GitHub workflow dosyasi push'unu reddediyor). Bu script ayni isi yapar,
AMA GitHub'a hicbir sey gondermeden:

  1. Testleri koser (62 test) — hata varsa DURUR
  2. JS/HTML dengesini kontrol eder
  3. config -> analytics.js senkronlar
  4. Netlify'e deploy eder (statik + API fonksiyonlari)
  5. Post-deploy smoke test (sayfalar + API endpoint'ler)
  6. GitHub Pages'e publish eder (docs/ alt-yolu)
  7. Ozet rapor

Kullanim:
    python deploy_site.py                # tam deploy
    python deploy_site.py --skip-tests   # testleri atla (acil duzeltme icin)
    python deploy_site.py --dry-run     # sadece kontrol et
"""
import argparse
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(REPO, "site")
GITHUB_REPO = "semtappdata-art/famous-music-studio"
GITHUB_API = "https://api.github.com"
NETLIFY_SITE_ID = "1d513c51-9ae9-46bc-b9b6-84e770b67fa9"
NETLIFY_DOMAIN = "famous-music-studio.netlify.app"

MOR = "\033[31m"
YESIL = "\033[32m"
SARI = "\033[33m"
MAVI = "\033[36m"
SIFIR = "\033[0m"


def adim(no, baslik):
    print(f"\n{MAVI}[{no}] {baslik}{SIFIR}")


def basarili(mesaj):
    print(f"  {YESIL}OK{SIFIR}  {mesaj}")


def hata(mesaj):
    print(f"  {MOR}HATA{SIFIR} {mesaj}")


def uyari(mesaj):
    print(f"  {SARI}UYARI{SIFIR} {mesaj}")


def calistir(komut, cwd=REPO, timeout=900):
    # Windows'ta "netlify" -> "netlify.cmd" (subprocess shell olmadan calistirmaz)
    if isinstance(komut, list) and komut and komut[0] == "netlify":
        komut = ["netlify.cmd"] + list(komut[1:])
    r = subprocess.run(komut, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, shell=isinstance(komut, str))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def gh_token():
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith("password="):
            return l.split("=", 1)[1].strip()
    return None


def http_json(url, data=None, method="GET", headers=None, timeout=60):
    h = dict(headers or {})
    b = None
    if data is not None:
        b = data if isinstance(data, bytes) else json_dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=b, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            c = r.read()
            return r.status, (c.decode("utf-8", "replace") if c else "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def json_dumps(o):
    import json
    return json.dumps(o)


def url_kontrol(url, beklenen="200"):
    st, _ = http_json(url, method="GET")
    return st == int(beklenen), st


def main():
    ap = argparse.ArgumentParser(description="Tek komutlu site deploy")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-github-pages", action="store_true")
    args = ap.parse_args()

    baslangic = time.time()
    print(f"{MAVI}=== FAMOUS MUSIC STUDIO — DEPLOY ==={SIFIR}")

    # --- 1) Testler ---
    adim(1, "Testler (CLAUDE.md kurallari)")
    if args.skip_tests:
        uyari("atlandi (--skip-tests)")
    else:
        # NEDEN sadece bu dosyalar: tam `pytest tests/` paketi ag + ffmpeg
        # cagirili testler iceriyor ve dakikalarca asili kalabiliyor
        # (bluesky_upload/telegram_upload -> requests.get timeout=20).
        # Buradaki set HIZLIDIR ve uretim kurallarini tamamen kapsar.
        hizli_testler = [
            "tests/test_kurallar.py",
            "tests/test_buyume_onerileri.py",
            "tests/test_kurtarma_kurallari.py",
            "tests/test_i18n_pages.py",
        ]
        kod, cikti = calistir([sys.executable, "-m", "pytest"] + hizli_testler +
                              ["-q", "--basetemp=pytest_tmp"])
        if kod != 0:
            hata("Testler basarisiz — deploy iptal")
            print(cikti[-2500:])
            return 1
        gecen = "gecmedi"
        for satir in cikti.splitlines():
            if " passed" in satir and "failed" not in satir:
                gecen = satir.strip()
                break
        basarili("kural testleri %s" % gecen)

    # --- 2) JS/HTML dengesizligi ---
    adim(2, "JS/HTML yapi kontrolu")
    kod, cikti = calistir([sys.executable, "check_js_braces.py", "--check"])
    if kod != 0:
        hata("JS brace dengesiz — deploy iptal")
        print(cikti[-1200:])
        return 1
    basarili("inline JS brace dengesi tam")

    # --- 3) config senkronu ---
    adim(3, "config -> analytics.js senkronu")
    kod, cikti = calistir([sys.executable, "sync_site_analytics.py"])
    if "guncellendi" in cikti:
        basarili(cikti.strip().splitlines()[-1])
    else:
        basarili("zaten senkron")

    if args.dry_run:
        print(f"\n{SARI}[DRY-RUN] Deploy yapilmadi{SIFIR}")
        return 0

    # --- 4) Netlify deploy ---
    adim(4, "Netlify deploy (statik + API fonksiyonlari)")
    kod, cikti = calistir([
        "netlify", "deploy", "--prod",
        "--dir=site", "--functions=netlify/functions",
        f"--site={NETLIFY_SITE_ID}",
        "--skip-functions-cache",
        "--message", f"site: {time.strftime('%Y-%m-%d %H:%M')}",
    ], timeout=1200)
    if kod != 0:
        hata("Netlify deploy basarisiz")
        print(cikti[-2000:])
        return 1
    basarili("Netlify deploy tamam")

    # --- 5) Smoke test ---
    adim(5, "Post-deploy smoke test")
    url = f"https://{NETLIFY_DOMAIN}"
    basarisiz = []
    for yol in ("/", "/privacy.html", "/epk/bio.html", "/robots.txt", "/sitemap.xml",
                "/i18n.js", "/analytics.js", "/assets/gece-masallari-preview-30s.mp3"):
        st, _ = http_json(url + yol)
        if st != 200:
            basarisiz.append(f"{yol} -> {st}")
    # API endpoint'ler
    st, _ = http_json(url + "/api/analytics",
                      data=json_dumps({"path": "/deploy-smoke", "ua": "deploy",
                                       "vw": 1280, "lang": "tr-TR"}).encode("utf-8"),
                      method="POST",
                      headers={"Content-Type": "text/plain;charset=UTF-8"})
    if st != 204:
        basarisiz.append(f"/api/analytics -> {st}")
    st, _ = http_json(url + "/api/topluluk")
    if st != 200:
        basarisiz.append(f"/api/topluluk -> {st}")

    if basarisiz:
        hata("Smoke test basarisiz: " + ", ".join(basarisiz))
        return 1
    basarili("Tum sayfalar + API endpoint'ler 200/204")

    # --- 6) GitHub Pages ---
    if args.skip_github_pages:
        uyari("GitHub Pages atlandi")
    else:
        adim(6, "GitHub Pages publish (docs/)")
        kod, cikti = calistir([sys.executable, "publish_site_github.py"], timeout=600)
        if kod == 0:
            basarili("GitHub Pages guncellendi")
        else:
            uyari("GitHub Pages publish atlandi (push protection / token)")

    # --- 7) Ozet ---
    sure = time.time() - baslangic
    print(f"\n{YESIL}{'=' * 58}{SIFIR}")
    print(f"{YESIL}  DEPLOY TAMAMLANDI ({sure:.0f} sn){SIFIR}")
    print(f"{YESIL}{'=' * 58}{SIFIR}")
    print(f"  Netlify (statik + API) : https://{NETLIFY_DOMAIN}/")
    print(f"  GitHub Pages (statik)  : https://{OWNER}/{REPO_NAME}/")
    print(f"  Analitik               : POST https://{NETLIFY_DOMAIN}/api/analytics")
    print(f"  Topluluk               : POST https://{NETLIFY_DOMAIN}/api/topluluk")
    return 0


OWNER = "semtappdata-art"
REPO_NAME = "famous-music-studio"

if __name__ == "__main__":
    sys.exit(main())
