#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Famous Music Studio — Topluluk Abonelik Endpoint'i (Madde 29)

Site'deki "Join the Community" formundan e-posta toplar ve topluluk
listesine yazar. Analitik ziyaret verisiyle TAMAMEN AYRI tutulur.

PII: sadece e-posta adresi (topluluk listesi icin gerekli).
Dogrulama: gecerli e-posta formati + cift kayit engeli.

Kullanim:
    Netlify: site/api/topluluk.py otomatik fonksiyon olur
    Yerel  : python site/api/topluluk.py   (http://127.0.0.1:8793)
"""
import datetime
import json
import os
import re
import sys
import threading

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import config  # noqa: E402

# CORS: sadece kendi domainimiz (site URL'si). "*" yerine bunu kullanmak
# bot/spam gonderimlerini engeller. Yerel gelistirmede localhost da izinli.
_IZINLI_ORIGINLER = None


def _izinli_origins() -> set:
    global _IZINLI_ORIGINLER
    if _IZINLI_ORIGINLER is None:
        import config as _c
        site = getattr(_c, "SITE_URL", "https://famousmusicstudio.com")
        host = site.split("//", 1)[-1].split("/", 1)[0]
        _IZINLI_ORIGINLER = {
            site.rstrip("/"),
            "https://" + host,
            "http://" + host,
            "http://localhost:8791",
            "http://127.0.0.1:8791",
            "http://localhost:8888",
            "http://127.0.0.1:8888",
        }
    return _IZINLI_ORIGINLER


def _cors_origin(istek=None) -> str:
    """Istek Origin header'ini dogrular; izinliyse geri doner, degilse '*'."""
    origin = ""
    if istek is not None:
        origin = (istek.headers.get("Origin") or "").strip()
    if origin and origin in _izinli_origins():
        return origin
    # Izinli degilse '*' DONUMEYIZ (bogazdan veri alinir).
    # Tarayici ayni-origin isteklerde Origin gondermez -> '*' guvenli.
    return "*" if not origin else ""

TZ = datetime.timezone(datetime.timedelta(hours=3))
VERI_KLASORU = os.path.join(REPO, config.TOPLULUK_VERI_KLASORU)
ABONE_DOSYASI = os.path.join(VERI_KLASORU, "topluluk_aboneleri.json")
LOCK = threading.Lock()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _klasor_hazirla():
    os.makedirs(VERI_KLASORU, exist_ok=True)


def _oku() -> list:
    if not os.path.isfile(ABONE_DOSYASI):
        return []
    try:
        with open(ABONE_DOSYASI, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


def _yaz(liste: list):
    _klasor_hazirla()
    tmp = ABONE_DOSYASI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ABONE_DOSYASI)


def abone_ekle(email: str, kaynak: str = "site") -> tuple:
    """(basarili, mesaj) doner."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        return False, "gecersiz e-posta"
    if len(email) > 254:
        return False, "cok uzun e-posta"
    with LOCK:
        liste = _oku()
        for a in liste:
            if a.get("email") == email:
                return True, "zaten kayitli"
        liste.append({
            "email": email,
            "kaynak": kaynak,
            "zaman": datetime.datetime.now(TZ).isoformat(),
            "onay": False,
        })
        _yaz(liste)
    return True, "eklendi"


def handler(event, context=None):
    """Netlify Functions giris noktasi."""
    if event.get("httpMethod", "GET") != "POST":
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Allow": "POST"},
            "body": json.dumps({"hata": "sadece POST"}),
        }
    try:
        body = json.loads(event.get("body") or "{}")
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    basarili, mesaj = abone_ekle(body.get("email", ""), body.get("kaynak", "site"))
    if not basarili:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"hata": mesaj}, ensure_ascii=False),
        }
    return {
        "statusCode": 204,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Content-Length": "0",
        },
        "body": "",
    }


import http.server  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        try:
            uzunluk = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            uzunluk = 0
        ham = self.rfile.read(uzunluk) if uzunluk else b"{}"
        try:
            veri = json.loads(ham.decode("utf-8", "replace") or "{}")
        except ValueError:
            veri = {}
        if not isinstance(veri, dict):
            veri = {}
        basarili, mesaj = abone_ekle(veri.get("email", ""), veri.get("kaynak", "site"))
        kod = 204 if basarili else 400
        govde = b"" if basarili else json.dumps(
            {"hata": mesaj}, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        if govde:
            self.wfile.write(govde)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        liste = _oku()
        govde = json.dumps({
            "toplam": len(liste),
            "onayli": sum(1 for a in liste if a.get("onay")),
        }, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, fmt, *args):
        sys.stderr.write("[topluluk] " + (fmt % args) + "\n")


def main():
    port = int(os.environ.get("TOPLULUK_PORT", "8793"))
    srv = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    print(f"Topluluk endpoint: http://127.0.0.1:{port}  (veri: {ABONE_DOSYASI})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
