"""Facebook Sayfası OAuth2 (Facebook İşletme Girişi / config_id akışı) kimlik
doğrulama — bir kere tamamlanır, facebook_token.json'a kaydedilir.

Instagram/TikTok ile aynı iki adımlı desen (localhost redirect_uri kabul
edilmediği için):
    1. python upload/facebook_auth.py --print-url
       -> auth_url'i yazdırır. Bu linki tarayıcıda aç, Facebook'ta giriş yapıp
       Sayfa yönetim izinlerini ver. Facebook seni docs/oauth-callback.html
       sayfasına yönlendirir, orada bir kod görünür.
    2. python upload/facebook_auth.py --code KOPYALANAN_KOD
       -> kodu kullanıcı token'ına, sonra long-lived token'a çevirir, /me/accounts
       ile Sayfa Access Token'ını bulur, facebook_token.json'a yazar.

Önkoşul: upload/facebook_client_secrets.json dosyasında
{"app_id": "...", "app_secret": "...", "config_id": "...", "page_id": "..."}
olmalı:
  - app_id/app_secret: Meta for Developers > Famous Music Studio > Uygulama
    ayarları > Temel sayfasındaki Uygulama Kimliği / Uygulama sırrı.
  - config_id: Facebook İşletme Girişi > Konfigürasyonlar altında oluşturulan
    yapılandırmanın Kimliği (pages_show_list + pages_manage_posts +
    pages_read_engagement izinleriyle).
  - page_id: Yönetilecek Facebook Sayfasının ID'si.

Sayfa Access Token'ı, long-lived kullanıcı token'ından türetildiği için
SÜRESİZ (non-expiring) kabul edilir — Instagram/TikTok'un aksine periyodik
yenileme gerekmez, kullanıcı izni geri almadığı sürece geçerli kalır.
"""

import argparse
import json
import os
import secrets
import urllib.parse

import requests

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "facebook_client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "facebook_token.json")
STATE_PATH = os.path.join(UPLOAD_DIR, "facebook_auth_state.json")

GRAPH_VERSION = "v21.0"
AUTH_URL = "https://www.facebook.com/" + GRAPH_VERSION + "/dialog/oauth"
TOKEN_URL = "https://graph.facebook.com/" + GRAPH_VERSION + "/oauth/access_token"
ACCOUNTS_URL = "https://graph.facebook.com/" + GRAPH_VERSION + "/me/accounts"
REDIRECT_URI = "https://semtappdata-art.github.io/famous-music-studio/oauth-callback.html"


def _load_client_secrets() -> dict:
    if not os.path.isfile(CLIENT_SECRETS_PATH):
        raise FileNotFoundError(
            f"facebook_client_secrets.json bulunamadı: {CLIENT_SECRETS_PATH}\n"
            "Meta for Developers > Famous Music Studio > Uygulama ayarları > Temel'den "
            "Uygulama Kimliği/sırrını, Facebook İşletme Girişi > Konfigürasyonlar'dan "
            "config_id'yi kopyalayıp şu formatta kaydet:\n"
            '{"app_id": "...", "app_secret": "...", "config_id": "...", "page_id": "..."}'
        )
    with open(CLIENT_SECRETS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def print_auth_url() -> None:
    """Yetkilendirme URL'ini üretir, yazdırır ve state'i STATE_PATH'e kaydeder
    (exchange_code() bu state'i doğrulamak için okur)."""
    secrets_data = _load_client_secrets()

    state = secrets.token_urlsafe(16)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"state": state}, f)

    params = {
        "client_id": secrets_data["app_id"],
        "redirect_uri": REDIRECT_URI,
        "config_id": secrets_data["config_id"],
        "response_type": "code",
        "state": state,
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)
    print(f"Bu linki tarayicida ac: {auth_url}")
    print("Giris/izin verdikten sonra yonlendirilecegin sayfadaki kodu kopyala,")
    print("sonra: python upload/facebook_auth.py --code KOPYALANAN_KOD")


def get_access_token() -> dict:
    """facebook_token.json varsa onu döner, yoksa hata verir (önce --print-url /
    --code adımlarıyla giriş tamamlanmalı)."""
    if os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        f"{TOKEN_PATH} yok. Once: python upload/facebook_auth.py --print-url, "
        "sonra: python upload/facebook_auth.py --code KOD"
    )


def exchange_code(code: str) -> dict:
    """Yetkilendirme kodunu kullanıcı token'ına, sonra long-lived kullanıcı
    token'ına çevirir; /me/accounts ile config_id'deki page_id'ye ait Sayfa
    Access Token'ını bulup facebook_token.json'a yazar."""
    secrets_data = _load_client_secrets()
    app_id = secrets_data["app_id"]
    app_secret = secrets_data["app_secret"]
    page_id = secrets_data["page_id"]

    # 1) Yetkilendirme kodunu kisa omurlu kullanici token'ina cevir
    short_resp = requests.get(
        TOKEN_URL,
        params={
            "client_id": app_id,
            "client_secret": app_secret,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=(10, 30),
    )
    short_resp.raise_for_status()
    short_token = short_resp.json()["access_token"]

    # 2) Long-lived kullanici token'ina cevir (~60 gun, ama asil onemli olan
    # bundan turetilecek Sayfa Access Token'i sonsuz omurlu olacak)
    long_resp = requests.get(
        TOKEN_URL,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
        timeout=(10, 30),
    )
    long_resp.raise_for_status()
    long_user_token = long_resp.json()["access_token"]

    # 3) Kullanicinin yonettigi Sayfalari listele, hedef page_id'yi bul
    accounts_resp = requests.get(
        ACCOUNTS_URL,
        params={"access_token": long_user_token},
        timeout=(10, 30),
    )
    accounts_resp.raise_for_status()
    pages = accounts_resp.json().get("data", [])

    page = next((p for p in pages if p["id"] == page_id), None)
    if page is None:
        available = ", ".join(f"{p['name']} ({p['id']})" for p in pages) or "(hicbiri)"
        raise RuntimeError(
            f"page_id={page_id} /me/accounts listesinde bulunamadi. "
            f"Bu kullanicinin yonettigi Sayfalar: {available}"
        )

    token = {
        "page_id": page["id"],
        "page_name": page["name"],
        "page_access_token": page["access_token"],
    }

    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)

    return token


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Facebook Sayfasi OAuth2 kimlik dogrulama (2 adimli).")
    parser.add_argument("--print-url", action="store_true", help="Yetkilendirme URL'ini yazdir.")
    parser.add_argument("--code", default=None, help="Callback sayfasindan kopyalanan kod.")
    args = parser.parse_args()

    if args.print_url:
        print_auth_url()
    elif args.code:
        token = exchange_code(args.code)
        print(f"Kimlik dogrulama basarili, facebook_token.json yazildi (page={token['page_name']}).")
    else:
        print("Kullanim: --print-url ile basla, sonra --code KOD ile tamamla.")
