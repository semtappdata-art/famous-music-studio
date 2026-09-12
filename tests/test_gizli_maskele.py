# -*- coding: utf-8 -*-
"""gizli_maskele — log'a token sizdiran desenin kapatildiginin kaniti.

NEDEN (2026-09-04 olayi): `dj_famous_process.log` satir 17'de GERCEK bir
Instagram erisim token'i bulundu. Saldirgan yoktu; bir ag kesintisi vardi.
`requests`'in ConnectionError mesaji tam istek URL'sini (sorgu dizesiyle
birlikte) tasiyor, token da orada gidiyor, `log(f"... HATA: {e}")` de onu
diske yaziyordu.

Bu dosyadaki TUM token degerleri SAHTEDIR — gercek bir kimlik bilgisi
buraya (ya da rapora) asla yazilmaz.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gizli_maskele import MASKE, maskele, maskele_istisna
from log_rotate import trim_log

# Hepsi uydurma. Bicimleri gercek token'lara BENZIYOR (desenlerin gercekten
# eslesmesi icin sart) ama hicbiri gecerli degil.
SAHTE_IG = "IGQWRPSAHTE1234567890abcdefGHIJKLMNOP"
SAHTE_FB = "EAASAHTE1234567890abcdefghijklmnop"
SAHTE_BOT = "123456789:AAF-SAHTE-abcdefghijklmnopqrstuvwxyz01"
SAHTE_GOOGLE = "1//0gSAHTE-abcdefghijklmnopqrstuvwxyz"
SAHTE_BLUESKY = "abcd-efgh-ijkl-mnop"


def _sizmadi(cikti: str, gizli: str) -> None:
    assert gizli not in cikti, f"SIZINTI: {gizli!r} ciktida duruyor -> {cikti!r}"
    assert MASKE in cikti, f"maskelenmedi: {cikti!r}"


# --- Her desen icin ayri test -------------------------------------------

def test_access_token_sorgu_dizesinde():
    """ASIL OLAY: ConnectionError'un mesaji tam URL'i tasiyor."""
    metin = (
        "HTTPSConnectionPool(host='graph.instagram.com', port=443): Max retries "
        "exceeded with url: /v21.0/18092925116265431?fields=status_code&"
        f"access_token={SAHTE_IG} (Caused by NewConnectionError)"
    )
    _sizmadi(maskele(metin), SAHTE_IG)


def test_input_token_sorgu_dizesinde():
    metin = f"GET /debug_token?input_token={SAHTE_FB}&access_token=123|sahte"
    _sizmadi(maskele(metin), SAHTE_FB)


def test_bot_token_url_yolunda():
    """Telegram'da token sorgu dizesinde DEGIL, YOLUN icinde."""
    metin = f"ConnectionError: https://api.telegram.org/bot{SAHTE_BOT}/sendVideo"
    _sizmadi(maskele(metin), SAHTE_BOT)


def test_bot_token_anahtarsiz_ham_halde():
    metin = f"telegram_client_secrets.json okundu: {SAHTE_BOT}"
    _sizmadi(maskele(metin), SAHTE_BOT)


def test_bearer_basligi():
    metin = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.sahteGovde.sahteImza"
    assert "sahteImza" not in maskele(metin)
    assert MASKE in maskele(metin)


def test_client_secret_json_govdesinde():
    metin = '{"client_id": "1234", "client_secret": "GOCSPX-sahte-gizli-deger"}'
    cikti = maskele(metin)
    assert "GOCSPX-sahte-gizli-deger" not in cikti
    assert MASKE in cikti
    assert "client_id" in cikti      # gizli olmayan alan korunuyor


def test_refresh_token_hem_esittir_hem_json():
    _sizmadi(maskele(f"refresh_token={SAHTE_GOOGLE}"), SAHTE_GOOGLE)
    _sizmadi(maskele(f'{{"refresh_token": "{SAHTE_GOOGLE}"}}'), SAHTE_GOOGLE)


def test_tek_tirnakli_dict_repr():
    """Python bir dict'i repr ederken tek tirnak kullanir."""
    metin = "istek verisi: {'access_token': '" + SAHTE_FB + "', 'media_type': 'REELS'}"
    cikti = maskele(metin)
    assert SAHTE_FB not in cikti
    assert "REELS" in cikti


def test_meta_token_on_eki_anahtarsiz():
    _sizmadi(maskele(f"beklenmedik yanit: {SAHTE_FB}"), SAHTE_FB)
    _sizmadi(maskele(f"beklenmedik yanit: {SAHTE_IG}"), SAHTE_IG)


def test_bluesky_app_password():
    _sizmadi(maskele(f"app_password {SAHTE_BLUESKY} ile giris"), SAHTE_BLUESKY)


# --- YANLIS POZITIF YOK --------------------------------------------------

NORMAL_SATIRLAR = [
    "[2026-09-11 15:07:03] === Islenen proje: projects/Gece Surusu ===",
    "[2026-09-11 12:00:00]   render tamam: output/youtube_16x9.mp4 (3:41)",
    "  Instagram: konteyner hala isleniyor (IN_PROGRESS), sonraki kontrolde",
    "  YouTube: tamam, video_id=7gyLv84KxTk, publishAt=2026-09-11T19:00:00",
    "  TikTok HATA: publish_id=v_pub_url~v2.123456 icin durum alinamadi",
    "  uuid 550e8400-e29b-41d4-a716-446655440000 ile eslesti",
    "  Facebook veri erisimi 12 gun sonra doluyor - yeniden yetkilendir",
    "  kapak: cover_vertical.png (1080x1920), art.jpg 1600x1600",
    "  Bluesky: post_uri=at://did:plc:abc123/app.bsky.feed.post/3kxyz",
]


def test_normal_log_satirlari_aynen_korunur():
    for satir in NORMAL_SATIRLAR:
        assert maskele(satir) == satir, f"YANLIS POZITIF: {satir!r} -> {maskele(satir)!r}"


def test_zaman_damgasi_token_sanilmaz():
    """`\\d+:\\d+` deseni saat:dakika:saniyeye BENZIYOR — takilmamali."""
    satir = "[2026-09-11 23:59:59] 12:34:56 suresinde tamamlandi"
    assert maskele(satir) == satir


def test_maskeleme_idempotent():
    """Iki kez maskelemek metni DEGISTIRMEMELI.

    NEDEN BU TEST VAR (gercek bug, bu denetimde yakalandi): deger karakter
    sinifi `]`'i ayirici sayiyor, yani `access_token=…[MASKELİ]` ikinci
    gecişte `…[MASKELİ` olarak eslesip sonuna BIR `]` DAHA ekliyordu.
    `log_rotate.trim_log()` ayni dosyayi her kosuda yeniden maskeledigi icin
    bu, satirin her kosuda bir karakter uzamasi demekti."""
    ornekler = [
        f"url: /v21.0/1?fields=status_code&access_token={SAHTE_IG} (Caused by X)",
        f"https://api.telegram.org/bot{SAHTE_BOT}/sendVideo",
        '{"client_secret": "GOCSPX-sahte"}',
        "Authorization: Bearer eyJhbGciOi.sahte.imza",
        f"refresh_token={SAHTE_GOOGLE}",
    ] + NORMAL_SATIRLAR
    for metin in ornekler:
        bir = maskele(metin)
        assert maskele(bir) == bir, f"idempotent degil: {metin!r} -> {bir!r} -> {maskele(bir)!r}"


def test_bos_ve_none_guvenli():
    assert maskele(None) == ""
    assert maskele("") == ""
    assert maskele(1234) == "1234"


# --- Istisna sarmalayicisi ----------------------------------------------

def test_maskele_istisna_token_sizdirmaz():
    import requests

    e = requests.exceptions.ConnectionError(
        "HTTPSConnectionPool(host='graph.instagram.com', port=443): Max retries "
        f"exceeded with url: /v21.0/123?access_token={SAHTE_IG}"
    )
    _sizmadi(maskele_istisna(e), SAHTE_IG)


def test_maskele_istisna_bos_mesajda_tip_adi_verir():
    assert maskele_istisna(KeyError()) == "KeyError"


# --- log() yolu ucdan uca ------------------------------------------------

def test_watch_projects_log_fonksiyonu_maskeliyor(tmp_path, monkeypatch):
    """Sahte bir ConnectionError'u GERCEK log() yolundan gecir, dosyada ara."""
    import requests

    import watch_projects

    log_dosyasi = tmp_path / "watch.log"
    monkeypatch.setattr(watch_projects, "LOG_PATH", str(log_dosyasi))

    e = requests.exceptions.ConnectionError(
        f"Max retries exceeded with url: /v21.0/123?access_token={SAHTE_IG}"
    )
    watch_projects.log(f"  Instagram HATA: {e}")

    icerik = log_dosyasi.read_text(encoding="utf-8")
    _sizmadi(icerik, SAHTE_IG)
    assert "Instagram HATA" in icerik   # tanilama bilgisi kaybolmadi


# --- log_rotate: diskte DURAN eski sizintiyi de temizliyor ---------------

def test_trim_log_mevcut_sizintiyi_maskeler(tmp_path):
    """Sizinti zaten diske yazilmissa bir sonraki budama onu temizlemeli."""
    import time

    simdi = time.strftime("%Y-%m-%d %H:%M:%S")
    log = tmp_path / "dj.log"
    log.write_text(
        f"[{simdi}] normal satir\n"
        f"[{simdi}]   Instagram HATA: url: /v21.0/1?access_token={SAHTE_IG}\n",
        encoding="utf-8",
    )

    trim_log(str(log), days=7)

    icerik = log.read_text(encoding="utf-8")
    _sizmadi(icerik, SAHTE_IG)
    assert "normal satir" in icerik     # eski satir sayisi degismedi, sadece maskelendi
