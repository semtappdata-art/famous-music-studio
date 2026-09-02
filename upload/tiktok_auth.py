"""TikTok OAuth2 (PKCE) kimlik doğrulama — bir kere tamamlanır, tiktok_token.json'a kaydedilir.

TikTok da localhost redirect_uri'yi reddettiği için akış İKİ ADIMLI (Instagram ile aynı desen):
    1. python upload/tiktok_auth.py --print-url
       -> auth_url'i yazdırır. Bu linki tarayıcıda aç, TikTok'ta giriş yapıp izin ver.
       TikTok seni docs/oauth-callback.html sayfasına yönlendirir, orada bir kod görünür.
    2. python upload/tiktok_auth.py --code KOPYALANAN_KOD
       -> kodu token'a çevirir, tiktok_token.json'a yazar.

Önkoşul: upload/tiktok_client_secrets.json dosyasında {"client_key": "...", "client_secret": "..."}
olmalı — bu değerleri TikTok Developer Portal'daki "Famous Music Studio" app'inin
Credentials bölümünden kopyala (Client key / Client secret).

Ayrıca TikTok Developer Portal'da (App > Login Kit veya Products > redirect URI ayarları)
REDIRECT_URI (aşağıda) kayıtlı olmalı — GitHub Pages'teki docs/oauth-callback.html'in tam URL'i.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import urllib.parse

import requests

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "tiktok_client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "tiktok_token.json")
STATE_PATH = os.path.join(UPLOAD_DIR, "tiktok_auth_state.json")

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.upload"
REDIRECT_URI = "https://semtappdata-art.github.io/famous-music-studio/oauth-callback.html"


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


def print_auth_url() -> None:
    """Yetkilendirme URL'ini üretir, yazdırır; state ve code_verifier'ı STATE_PATH'e kaydeder
    (exchange_code() bunları okur)."""
    secrets_data = _load_client_secrets()
    client_key = secrets_data["client_key"]

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"state": state, "verifier": verifier}, f)

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
    print(f"Bu linki tarayicida ac: {auth_url}")
    print("Giris/izin verdikten sonra yonlendirilecegin sayfadaki kodu kopyala,")
    print("sonra: python upload/tiktok_auth.py --code KOPYALANAN_KOD")


def get_access_token() -> dict:
    """tiktok_token.json'daki access_token'ı döner — TikTok access token'ları
    kısa ömürlü (genelde 24 saat) olduğu için, kullanmadan önce her zaman
    refresh_token ile YENİLENİR (refresh_token çok daha uzun ömürlü, ~1 yıl).
    Bu yenileme olmadan token birkaç saat içinde 401 Unauthorized vermeye
    başlıyordu — otomasyon günlerce arayla çalıştığı için her seferinde
    yenilemek şart."""
    if not os.path.isfile(TOKEN_PATH):
        raise FileNotFoundError(
            f"{TOKEN_PATH} yok. Once: python upload/tiktok_auth.py --print-url, "
            "sonra: python upload/tiktok_auth.py --code KOD"
        )
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = json.load(f)

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return token

    secrets_data = _load_client_secrets()
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        data={
            "client_key": secrets_data["client_key"],
            "client_secret": secrets_data["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    if not resp.ok:
        raise RuntimeError(
            f"TikTok token yenilenemedi ({resp.status_code}): {resp.text[:500]}\n"
            "refresh_token da süresi dolmuş/geçersiz olabilir — yeniden yetkilendirme "
            "gerekebilir: python upload/tiktok_auth.py --print-url"
        )
    new_token = resp.json()
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(new_token, f, ensure_ascii=False, indent=2)
    return new_token


def exchange_code(code: str) -> dict:
    """Yetkilendirme kodunu access token'a çevirir, tiktok_token.json'a yazar."""
    secrets_data = _load_client_secrets()
    client_key = secrets_data["client_key"]
    client_secret = secrets_data["client_secret"]

    if not os.path.isfile(STATE_PATH):
        raise FileNotFoundError("Once: python upload/tiktok_auth.py --print-url calistirilmali.")
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    verifier = state_data["verifier"]

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
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
    parser = argparse.ArgumentParser(description="TikTok OAuth2 kimlik dogrulama (2 adimli).")
    parser.add_argument("--print-url", action="store_true", help="Yetkilendirme URL'ini yazdir.")
    parser.add_argument("--code", default=None, help="Callback sayfasindan kopyalanan kod.")
    args = parser.parse_args()

    if args.print_url:
        print_auth_url()
    elif args.code:
        token = exchange_code(args.code)
        print("Kimlik dogrulama basarili, tiktok_token.json yazildi.")
    else:
        print("Kullanim: --print-url ile basla, sonra --code KOD ile tamamla.")
