"""Instagram OAuth2 (Instagram Login for Business) kimlik doğrulama — bir kere
tamamlanır, instagram_token.json'a kaydedilir (long-lived token'a çevrilmiş halde).

Kullanım:
    python upload/instagram_auth.py

Önkoşul: upload/instagram_client_secrets.json dosyasında {"app_id": "...", "app_secret": "..."}
olmalı — bu değerleri Meta for Developers > Famous Music Studio > Instagram API >
"Instagram girişiyle API kurulumu" sayfasındaki "Instagram uygulama kimliği" /
"Instagram uygulamasının sırrı" alanlarından kopyala.

Ayrıca aynı sayfada "Geri Çağrı URL'si" alanına REDIRECT_URI (aşağıda) kayıtlı olmalı.

Bağlanacak Instagram hesabının Business/Creator (profesyonel) hesaba çevrilmiş ve
herkese açık olması gerekiyor — kişisel/gizli hesaplarla token üretilemiyor.
"""

import http.server
import json
import os
import secrets
import threading
import urllib.parse
import webbrowser

import requests

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "instagram_client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "instagram_token.json")

AUTH_URL = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
SCOPES = (
    "instagram_business_basic,"
    "instagram_business_content_publish,"
    "instagram_business_manage_comments,"
    "instagram_business_manage_messages"
)
REDIRECT_PORT = 8723
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"


def _load_client_secrets() -> dict:
    if not os.path.isfile(CLIENT_SECRETS_PATH):
        raise FileNotFoundError(
            f"instagram_client_secrets.json bulunamadı: {CLIENT_SECRETS_PATH}\n"
            "Meta for Developers > Famous Music Studio > Instagram API > "
            "Instagram girişiyle API kurulumu sayfasından Instagram uygulama kimliği "
            've sırrını kopyalayıp şu formatta kaydet:\n'
            '{"app_id": "...", "app_secret": "..."}'
        )
    with open(CLIENT_SECRETS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None
    state = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.state = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>Kimlik dogrulama tamamlandi, bu sekmeyi kapatabilirsin.</h2>".encode())

    def log_message(self, *args):
        pass


def get_access_token() -> dict:
    """instagram_token.json varsa onu döner, yoksa OAuth flow'u başlatır (tarayıcı açar)."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    secrets_data = _load_client_secrets()
    app_id = secrets_data["app_id"]
    app_secret = secrets_data["app_secret"]

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
        "state": state,
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print(f"Bu linki tarayicida ac (otomatik acilmadiysa): {auth_url}")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    thread.join(timeout=300)
    server.server_close()

    if not _CallbackHandler.code:
        raise RuntimeError("Yetkilendirme kodu alinamadi (zaman asimi veya iptal).")
    if _CallbackHandler.state != state:
        raise RuntimeError("state uyusmuyor, guvenlik hatasi.")

    # 1) Kisa omurlu token al
    short_resp = requests.post(
        SHORT_TOKEN_URL,
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": _CallbackHandler.code,
        },
    )
    short_resp.raise_for_status()
    short_data = short_resp.json()
    short_token = short_data["access_token"]
    ig_user_id = short_data["user_id"]

    # 2) Uzun omurlu token'a cevir (60 gun gecerli, yenilenebilir)
    long_resp = requests.get(
        LONG_TOKEN_URL,
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": app_secret,
            "access_token": short_token,
        },
    )
    long_resp.raise_for_status()
    long_data = long_resp.json()

    token = {
        "access_token": long_data["access_token"],
        "token_type": long_data.get("token_type", "bearer"),
        "expires_in": long_data.get("expires_in"),
        "ig_user_id": ig_user_id,
    }

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    return token


def refresh_access_token() -> dict:
    """Mevcut long-lived token'i (bitmeden once, ideal olarak 60 gunluk surenin ilk
    yarisindan sonra) yeniler. Cron/scheduled task ile periyodik cagirmak icin."""
    if not os.path.isfile(TOKEN_PATH):
        raise FileNotFoundError("instagram_token.json yok, once get_access_token() ile giris yap.")
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = json.load(f)

    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={
            "grant_type": "ig_refresh_token",
            "access_token": token["access_token"],
        },
    )
    resp.raise_for_status()
    data = resp.json()
    token["access_token"] = data["access_token"]
    token["expires_in"] = data.get("expires_in")

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    return token


if __name__ == "__main__":
    token = get_access_token()
    print(f"Kimlik dogrulama basarili, instagram_token.json yazildi (ig_user_id={token['ig_user_id']}).")
