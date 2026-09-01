"""Instagram OAuth2 (Instagram Login for Business) kimlik doğrulama — bir kere
tamamlanır, instagram_token.json'a kaydedilir (long-lived token'a çevrilmiş halde).

Meta, production app'lerde localhost redirect_uri'yi reddettiği için akış İKİ ADIMLI:
    1. python upload/instagram_auth.py --print-url
       -> auth_url'i yazdırır. Bu linki tarayıcıda aç, Instagram'da giriş yapıp izin ver.
       Instagram seni docs/oauth-callback.html sayfasına yönlendirir, orada bir kod görünür.
    2. python upload/instagram_auth.py --code KOPYALANAN_KOD
       -> kodu token'a çevirir, instagram_token.json'a yazar.

Önkoşul: upload/instagram_client_secrets.json dosyasında {"app_id": "...", "app_secret": "..."}
olmalı — bu değerleri Meta for Developers > Famous Music Studio > Instagram API >
"Instagram girişiyle API kurulumu" sayfasındaki "Instagram uygulama kimliği" /
"Instagram uygulamasının sırrı" alanlarından kopyala.

Ayrıca aynı sayfada "Geri Çağrı URL'si" alanına REDIRECT_URI (aşağıda) kayıtlı olmalı —
GitHub Pages'teki docs/oauth-callback.html'in tam URL'i.

Bağlanacak Instagram hesabının Business/Creator (profesyonel) hesaba çevrilmiş ve
herkese açık olması gerekiyor — kişisel/gizli hesaplarla token üretilemiyor.
"""

import argparse
import json
import os
import secrets
import urllib.parse

import requests

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "instagram_client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "instagram_token.json")
STATE_PATH = os.path.join(UPLOAD_DIR, "instagram_auth_state.json")

AUTH_URL = "https://www.instagram.com/oauth/authorize"
SHORT_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
SCOPES = (
    "instagram_business_basic,"
    "instagram_business_content_publish,"
    "instagram_business_manage_comments,"
    "instagram_business_manage_messages"
)
REDIRECT_URI = "https://semtappdata-art.github.io/famous-music-studio/oauth-callback.html"


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


def print_auth_url() -> None:
    """Yetkilendirme URL'ini üretir, yazdırır ve state'i STATE_PATH'e kaydeder
    (exchange_code() bu state'i doğrulamak için okur)."""
    secrets_data = _load_client_secrets()
    app_id = secrets_data["app_id"]

    state = secrets.token_urlsafe(16)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"state": state}, f)

    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
        "state": state,
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    print(f"Bu linki tarayicida ac: {auth_url}")
    print("Giris/izin verdikten sonra yonlendirilecegin sayfadaki kodu kopyala,")
    print("sonra: python upload/instagram_auth.py --code KOPYALANAN_KOD")


def get_access_token() -> dict:
    """instagram_token.json varsa onu döner, yoksa hata verir (önce --print-url /
    --code adımlarıyla giriş tamamlanmalı)."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        f"{TOKEN_PATH} yok. Once: python upload/instagram_auth.py --print-url, "
        "sonra: python upload/instagram_auth.py --code KOD"
    )


def exchange_code(code: str) -> dict:
    """Yetkilendirme kodunu long-lived access token'a çevirir, instagram_token.json'a yazar."""
    secrets_data = _load_client_secrets()
    app_id = secrets_data["app_id"]
    app_secret = secrets_data["app_secret"]

    # 1) Kisa omurlu token al
    short_resp = requests.post(
        SHORT_TOKEN_URL,
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
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
    parser = argparse.ArgumentParser(description="Instagram OAuth2 kimlik dogrulama (2 adimli).")
    parser.add_argument("--print-url", action="store_true", help="Yetkilendirme URL'ini yazdir.")
    parser.add_argument("--code", default=None, help="Callback sayfasindan kopyalanan kod.")
    args = parser.parse_args()

    if args.print_url:
        print_auth_url()
    elif args.code:
        token = exchange_code(args.code)
        print(f"Kimlik dogrulama basarili, instagram_token.json yazildi (ig_user_id={token['ig_user_id']}).")
    else:
        print("Kullanim: --print-url ile basla, sonra --code KOD ile tamamla.")
