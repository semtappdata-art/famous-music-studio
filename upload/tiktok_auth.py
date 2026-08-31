"""TikTok OAuth2 (PKCE) kimlik doğrulama — bir kere tamamlanır, tiktok_token.json'a kaydedilir.

Kullanım:
    python upload/tiktok_auth.py

Önkoşul: upload/tiktok_client_secrets.json dosyasında {"client_key": "...", "client_secret": "..."}
olmalı — bu değerleri TikTok Developer Portal'daki "Famous Music Studio" app'inin
Credentials bölümünden kopyala (Client key / Client secret).
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import webbrowser

import requests

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "tiktok_client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "tiktok_token.json")

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.upload,video.publish"
REDIRECT_PORT = 8722
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"


def _load_client_secrets() -> dict:
    if not os.path.isfile(CLIENT_SECRETS_PATH):
        raise FileNotFoundError(
            f"tiktok_client_secrets.json bulunamadı: {CLIENT_SECRETS_PATH}\n"
            'TikTok Developer Portal > Famous Music Studio > App details > Credentials\'tan '
            'Client key ve Client secret\'ı kopyalayıp şu formatta kaydet:\n'
            '{"client_key": "...", "client_secret": "..."}'
        )
    with open(CLIENT_SECRETS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


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
    """tiktok_token.json varsa onu döner, yoksa OAuth flow'u başlatır (tarayıcı açar)."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    secrets_data = _load_client_secrets()
    client_key = secrets_data["client_key"]
    client_secret = secrets_data["client_secret"]

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print(f"Bu linki taraycida ac (otomatik acilmadiysa): {auth_url}")
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

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": _CallbackHandler.code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
    )
    resp.raise_for_status()
    token = resp.json()

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    return token


if __name__ == "__main__":
    token = get_access_token()
    print("Kimlik dogrulama basarili, tiktok_token.json yazildi.")
