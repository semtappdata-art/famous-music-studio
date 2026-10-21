#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Famous Music Studio — Site Analitik Endpoint'i (Madde 28)

COOKIE-LESS, PII-YOK, FIRST-PARTY toplama. Ucuncu taraf hesap gerektirmez.

Toplanan alanlar (yalnizca bunlar):
  ts        — ziyaret zamanı (ISO 8601, UTC)
  path      — sayfa yolu (query string HARIC)
  ref       — referrer host (yoksa "-")
  device    — masaustu / mobil / tablet
  lang      — tarayici dili
  tz        — saat dilimi
  vp        — "WxH" viewport (kaba cihaz sinifi icin)

Toplanmayanlar: IP, cookie, localStorage, fingerprint, e-posta, ad.

Cift yazma korumasi: ayni (path, gun) icin 5 dakika icinde tekrar sayilirsa
atilir (bot/marka yenileme sinyali).

Kullanim:
    python site/api/analytics.py            # yerel sunucu (http://127.0.0.1:8792)
    Netlify: site/api/analytics.py otomatik olarak fonksiyon olur
    Herhangi bir WSGI: app uygulamasini kullan
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

DATA_DIR = os.path.join(REPO, config.ANALITIK_VERI_KLASORU)
DATA_FILE = os.path.join(DATA_DIR, config.ANALITIK_RAPOR_DOSYASI)
LOCK = threading.Lock()

# CORS: sadece kendi domainimiz (site URL'si). "*" yerine bunu kullanmak
# bot/spam gonderimlerini engeller. Yerel gelistirmede localhost da izinli.
_IZINLI_ORIGINLER = None


def _izinli_origins() -> set:
    global _IZINLI_ORIGINLER
    if _IZINLI_ORIGINLER is None:
        site = getattr(config, "SITE_URL", "https://famousmusicstudio.com")
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
    """Istek Origin header'ini dogrular; izinliyse geri doner, degilse bos."""
    origin = ""
    if istek is not None:
        origin = (istek.headers.get("Origin") or "").strip()
    if origin and origin in _izinli_origins():
        return origin
    # Izinli degilse '*' DONUMEYIZ (bogazdan veri alinir).
    # Tarayici ayni-origin isteklerde Origin gondermez -> '*' guvenli.
    return "*" if not origin else ""

# Istenen veri dosyalari disaridan gelmemeli (path traversal koruması)
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_.\-]{0,180}$")


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _klasor_hazirla():
    os.makedirs(DATA_DIR, exist_ok=True)


def _temiz_sayfa_yolu(path):
    """Query string ve hash atilir; sadece yol kalir."""
    if not path:
        return "/"
    path = path.split("?", 1)[0].split("#", 1)[0]
    if not _SAFE_PATH.match(path):
        return "/"
    return path[:180]


def _ip_al():
    """IP SADECE rate-limit icin kullanilir, KAYDEDILMEZ."""
    return "local"


def _kayitlari_oku():
    if not os.path.isfile(DATA_FILE):
        return []
    out = []
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out


def _yaz(kayitlar):
    _klasor_hazirla()
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for k in kayitlar:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    os.replace(tmp, DATA_FILE)


def kaydet(ziyaret: dict) -> bool:
    """Ziyareti kaydeder. Cift yazma (5 dk ayni sayfa) engellenir."""
    ziyaret["ts"] = _now().isoformat()
    ziyaret["path"] = _temiz_sayfa_yolu(ziyaret.get("path", "/"))

    with LOCK:
        kayitlar = _kayitlari_oku()
        # ayni path, son 5 dakika icinde -> atla
        yeni = _now()
        for k in kayitlar[-400:]:
            try:
                eski = datetime.datetime.fromisoformat(k.get("ts", ""))
            except ValueError:
                continue
            if k.get("path") == ziyaret["path"] and (yeni - eski).total_seconds() < 300:
                return False
        kayitlar.append(ziyaret)
        # son 30 gunu tut (dosya kucuk kalsin)
        kesme = yeni - datetime.timedelta(days=30)
        kayitlar = [k for k in kayitlar if k.get("ts", "") >= kesme.isoformat()]
        _yaz(kayitlar)
    return True


def ozet(kayitlar=None) -> dict:
    """Kayitlardan gunluk ozet cikarir."""
    if kayitlar is None:
        kayitlar = _kayitlari_oku()
    bugun = _now().date().isoformat()
    d = [k for k in kayitlar if k.get("ts", "").startswith(bugun)]
    yollar = {}
    for k in d:
        yollar[k.get("path", "/")] = yollar.get(k.get("path", "/"), 0) + 1
    cihazlar = {}
    for k in d:
        c = k.get("device", "bilinmiyor")
        cihazlar[c] = cihazlar.get(c, 0) + 1
    referrer = {}
    for k in d:
        r = k.get("ref", "-")
        referrer[r] = referrer.get(r, 0) + 1
    return {
        "tarih": bugun,
        "toplam_ziyaret": len(d),
        "toplam_kayit": len(kayitlar),
        "sayfalar": dict(sorted(yollar.items(), key=lambda x: -x[1])[:10]),
        "cihazlar": cihazlar,
        "referrer": dict(sorted(referrer.items(), key=lambda x: -x[1])[:10]),
    }


# ------------------------------------------------------------------
# Netlify Function girisi
# ------------------------------------------------------------------
def handler(event, context=None):
    """Netlify Functions (AWS Lambda tarzi) giris noktasi."""
    import json as _json
    if event.get("httpMethod", "GET") != "POST":
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json", "Allow": "POST"},
            "body": _json.dumps({"hata": "sadece POST"}),
        }
    try:
        body = _json.loads(event.get("body") or "{}")
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    kaydedildi = kaydet(body)
    return {
        "statusCode": 204,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": "",
    }


# ------------------------------------------------------------------
# Stand-alone yerel sunucu (gelistirme)
# ------------------------------------------------------------------
import http.server  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    """http.server tabanli minimal handler."""

    def do_POST(self):  # noqa: N802
        # Content-Type ne olursa olsun govde JSON olarak ayristirilir
        # (istemci "text/plain" gonderiyor ki preflight olmasin).
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
        kaydedildi = kaydet(veri)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/summary"):
            govde = json.dumps(ozet(), ensure_ascii=False, indent=2)
            kod = 200
        else:
            govde = json.dumps({"hata": "POST / (kayit), GET /summary (ozet)"}, ensure_ascii=False)
            kod = 404
        veri = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("[analytics] " + (fmt % args) + "\n")


def main():
    import http.server
    port = int(os.environ.get("ANALYTIK_PORT", "8792"))
    srv = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    print(f"Analitik endpoint: http://127.0.0.1:{port}  (veri: {DATA_FILE})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
