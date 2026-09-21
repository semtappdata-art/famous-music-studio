# -*- coding: utf-8 -*-
"""Sizintinin KAYNAGINI kapatan duzeltmelerin testleri (maskeleyiciden AYRI).

Maskeleyici son savunma hatti; asil is token'in istisna metnine HIC girmemesi.
Burada test edilenler:
  1. `telegram_upload._api_post` — bot token URL'in YOLUNDA; bir ag hatasinda
     istisna metni token'siz olmali.
  2. `instagram_upload._graph_istek` — token SORGU DIZESINDE; hem ag hatasi
     hem HTTP hatasi token'siz olmali (`raise_for_status()` mesaji da URL'i
     tasiyordu).
  3. `state_io` gocu — bes upload modulu de state.json'i ATOMIK yaziyor mu.
  4. Instagram "eski gonderi yeni konteyneri blokluyor" arizasi.
  5. `gorev_sarmalayici.py` — UCUNCU log ailesi (`gorev_izleri/*.log`) iz
     dosyasina HAM yazmiyor (yapisal tarama; davranis tarafi
     `tests/test_sarmalayici_maskeleme.py`).

Tum token degerleri SAHTEDIR.
"""

import ast
import json
import os
import sys
import time

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import instagram_upload
import state_io
import telegram_upload

SAHTE_BOT = "123456789:AAF-SAHTE-abcdefghijklmnopqrstuvwxyz01"
SAHTE_IG = "IGQWRPSAHTE1234567890abcdefGHIJKLMNOP"


# --- 1) Telegram: token URL'in YOLUNDA -----------------------------------

def test_telegram_ag_hatasi_bot_tokeni_sizdirmaz(monkeypatch):
    def patlayan_post(url, **kw):
        # requests'in gercek davranisi: mesaj TAM URL'i icerir.
        raise requests.exceptions.ConnectionError(
            f"HTTPSConnectionPool(host='api.telegram.org', port=443): Max "
            f"retries exceeded with url: {url}"
        )

    monkeypatch.setattr(telegram_upload.requests, "post", patlayan_post)

    with pytest.raises(RuntimeError) as hata:
        telegram_upload._api_post(SAHTE_BOT, "sendVideo", {"chat_id": "@x"})

    metin = str(hata.value)
    assert SAHTE_BOT not in metin, f"SIZINTI: {metin!r}"
    assert "sendVideo" in metin          # teshis icin metot adi duruyor
    assert "ConnectionError" in metin    # istisna tipi duruyor


def test_telegram_ag_hatasi_zinciri_de_tasimiyor(monkeypatch):
    """`from None` sart: zincirdeki orijinal istisna traceback'e basilirdi."""
    def patlayan_post(url, **kw):
        raise requests.exceptions.ReadTimeout(f"timeout for url: {url}")

    monkeypatch.setattr(telegram_upload.requests, "post", patlayan_post)

    with pytest.raises(RuntimeError) as hata:
        telegram_upload._api_post(SAHTE_BOT, "sendMessage", {})

    assert hata.value.__cause__ is None
    assert hata.value.__context__ is None or SAHTE_BOT not in str(hata.value.__context__) or \
        hata.value.__suppress_context__


class _SahteYanit:
    def __init__(self, status_code=200, govde="", veri=None):
        self.status_code = status_code
        self.text = govde
        self._veri = veri

    def json(self):
        if self._veri is None:
            raise json.JSONDecodeError("yok", "", 0)
        return self._veri


def test_telegram_json_olmayan_yanit_url_basmiyor(monkeypatch):
    """Eskiden burada `resp.raise_for_status()` vardi; HTTPError mesaji
    '... for url: <tam url>' formatinda, yani token'i basiyordu."""
    monkeypatch.setattr(telegram_upload.requests, "post",
                        lambda url, **kw: _SahteYanit(502, "<html>bad gateway</html>"))

    with pytest.raises(RuntimeError) as hata:
        telegram_upload._api_post(SAHTE_BOT, "sendVideo", {})

    metin = str(hata.value)
    assert SAHTE_BOT not in metin
    assert "502" in metin


# --- 2) Instagram: token SORGU DIZESINDE ---------------------------------

def test_instagram_ag_hatasi_token_sizdirmaz(monkeypatch):
    def patlayan_request(metot, url, **kw):
        # requests URL'i params ile birlestirdikten SONRA hata mesajina koyar.
        sorgu = "&".join(f"{k}={v}" for k, v in (kw.get("params") or {}).items())
        raise requests.exceptions.ConnectionError(
            f"Max retries exceeded with url: {url}?{sorgu}")

    monkeypatch.setattr(instagram_upload.requests, "request", patlayan_request)

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "GET", "https://graph.instagram.com/v21.0/123", "konteyner durumu",
            params={"fields": "status_code", "access_token": SAHTE_IG})

    metin = str(hata.value)
    assert SAHTE_IG not in metin, f"SIZINTI: {metin!r}"
    assert "konteyner durumu" in metin


def test_instagram_http_hatasi_token_sizdirmaz(monkeypatch):
    """`raise_for_status()` yerine token'siz RuntimeError."""
    monkeypatch.setattr(
        instagram_upload.requests, "request",
        lambda metot, url, **kw: _SahteYanit(
            400, govde='{"error": {"message": "Invalid OAuth access_token=%s"}}' % SAHTE_IG))

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "GET", "https://graph.instagram.com/v21.0/123", "konteyner durumu",
            params={"access_token": SAHTE_IG})

    metin = str(hata.value)
    assert SAHTE_IG not in metin, f"SIZINTI (yanit govdesi maskelenmemis): {metin!r}"
    assert "400" in metin


# --- 3) state_io gocu ----------------------------------------------------

GOC_EDILEN_MODULLER = [
    "upload/facebook_upload.py",
    "upload/telegram_upload.py",
    "upload/bluesky_upload.py",
    "upload/instagram_upload.py",
    "upload/tiktok_upload.py",
]


def test_upload_modulleri_state_json_i_ham_yazmiyor():
    """Hicbiri state.json'i `open(..., "w")` + `json.dump` ile yazmamali.

    NEDEN: yarim kalan bir yazim `uyumluluk._durum()` sertlestirildikten sonra
    boru hattini DURDURUYOR; ayrica auto_process (saatlik) ile
    dj_famous_process (haftalik) AYRI kilitler kullanip ayni dosyaya
    yazabiliyor — kaybolan bir `telegram_message_id` o platformda IKINCI bir
    yukleme demek."""
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in GOC_EDILEN_MODULLER:
        kaynak = open(os.path.join(kok, rel), encoding="utf-8").read()
        assert "state_io" in kaynak, f"{rel}: state_io hic kullanilmiyor"
        # state.json'a yazan ham desen: `open(state_path, "w"...)`
        assert 'open(state_path, "w"' not in kaynak, f"{rel}: hala ham state.json yazimi var"


def test_telegram_save_state_atomik(tmp_path, monkeypatch):
    proje = tmp_path / "Sahte Sarki"
    proje.mkdir()
    (proje / "state.json").write_text('{"youtube_video_id": "abc"}', encoding="utf-8")

    cagrildi = {}
    gercek = state_io.durum_yaz
    monkeypatch.setattr(
        telegram_upload.state_io, "durum_yaz",
        lambda p, v: (cagrildi.setdefault("evet", True), gercek(p, v))[-1])

    telegram_upload._save_state(str(proje), {"telegram_message_id": 42})

    assert cagrildi.get("evet") is True
    veri = json.loads((proje / "state.json").read_text(encoding="utf-8"))
    assert veri == {"youtube_video_id": "abc", "telegram_message_id": 42}


# --- 4) Instagram: eski gonderi yeni konteyneri bloklamiyor --------------

def test_konteyner_yayindan_yeni_dogru_ayirt_ediyor():
    # Gercek ariza: 05 Eylul konteyneri, 01 Eylul yayini -> yayinlanmali.
    assert instagram_upload._konteyner_yayindan_yeni({
        "instagram_uploaded_at": "2026-09-01T18:53:07",
        "instagram_container_created_at": "2026-09-05T14:21:19",
    }) is True

    # Konteyner yayindan ESKI -> zaten yayinlanmis, tekrar yayinlama.
    assert instagram_upload._konteyner_yayindan_yeni({
        "instagram_uploaded_at": "2026-09-05T14:30:00",
        "instagram_container_created_at": "2026-09-05T14:21:19",
    }) is False

    # Damga eksik -> TEMKINLI (cift yayin riskine girme).
    assert instagram_upload._konteyner_yayindan_yeni({
        "instagram_uploaded_at": "2026-09-01T18:53:07",
    }) is False
    assert instagram_upload._konteyner_yayindan_yeni({
        "instagram_container_created_at": "2026-09-05T14:21:19",
    }) is False


def _damga(saat_once: float) -> str:
    """`instagram_container_created_at` ile AYNI bicim/saat dilimi.

    NEDEN SABIT METIN DEGIL: bu testler eskiden gercek olaydaki damgalari
    ("2026-09-05T14:21:19") aynen yaziyordu. `try_publish_pending()`e YAS
    KAPISI eklenince (24 saati asan konteyner, `status_code` ne derse desin
    bayat) o sabit damgalar takvim ilerledikce bayat oldu ve testler asil
    olcmek istedikleri dala (eski media_id yeni konteyneri bloklamasin) hic
    gelemez oldu. Damga artik "su andan N saat once" diye uretiliyor."""
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _proje_yaz(tmp_path, state: dict) -> str:
    proje = tmp_path / "Gece Surusu"
    proje.mkdir()
    (proje / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                      encoding="utf-8")
    return str(proje)


def test_eski_media_id_yeni_konteyneri_artik_bloklamiyor(tmp_path, monkeypatch):
    """KURU dogrulama: gercek bir yayin YAPILMIYOR, konteyner EXPIRED donuyor.

    Eskiden `try_publish_pending()` `instagram_media_id` dolu oldugu icin
    API'ye HIC gitmeden None donuyordu — bu yuzden 05 Eylul konteynerleri
    6 gun boyunca 'golden-hour bekleniyor' diye yanlis loglandi."""
    proje = _proje_yaz(tmp_path, {
        "instagram_media_id": "17957449007998018",
        "instagram_uploaded_at": _damga(4 * 24),   # 01 Eylul yayini
        "instagram_creation_id": "18092925116265431",
        "instagram_container_created_at": _damga(2),   # TAZE (yas kapisi devrede degil)
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    istekler = []

    def sahte_istek(metot, url, ne, **kw):
        istekler.append(ne)
        return _SahteYanit(200, veri={"status_code": "EXPIRED"})

    monkeypatch.setattr(instagram_upload, "_graph_istek", sahte_istek)

    sonuc = instagram_upload.try_publish_pending(proje)

    assert istekler == ["konteyner durumu"], "kapi hala API'ye hic gitmiyor"
    assert sonuc is None                      # EXPIRED -> yayin YOK
    veri = json.loads(open(os.path.join(proje, "state.json"), encoding="utf-8").read())
    assert "instagram_creation_id" not in veri          # olu kayit temizlendi
    assert "instagram_container_created_at" not in veri
    assert veri["instagram_media_id"] == "17957449007998018"  # eski gonderi duruyor


def test_ayni_konteyner_iki_kez_yayinlanmiyor(tmp_path, monkeypatch):
    """Cift yayin korumasi KIRILMADI: konteyner son yayindan eskiyse cikilir."""
    proje = _proje_yaz(tmp_path, {
        "instagram_media_id": "17957449007998018",
        "instagram_uploaded_at": _damga(1),        # yayin, konteynerden YENI
        "instagram_creation_id": "18092925116265431",
        "instagram_container_created_at": _damga(2),   # TAZE (yas kapisi devrede degil)
    })

    def olmamali(*a, **kw):
        raise AssertionError("API'ye gidilmemeliydi — cift yayin korumasi kirik")

    monkeypatch.setattr(instagram_upload, "get_access_token", olmamali)
    monkeypatch.setattr(instagram_upload, "_graph_istek", olmamali)

    assert instagram_upload.try_publish_pending(proje) is None


def test_damgasiz_eski_state_temkinli_davraniyor(tmp_path, monkeypatch):
    """`instagram_container_created_at` alani eklenmeden ONCEKI state'ler."""
    proje = _proje_yaz(tmp_path, {
        "instagram_media_id": "17957449007998018",
        "instagram_uploaded_at": "2026-09-01T18:53:07",
        "instagram_creation_id": "18092925116265431",
    })

    def olmamali(*a, **kw):
        raise AssertionError("damga yokken yayin denenmemeliydi")

    monkeypatch.setattr(instagram_upload, "get_access_token", olmamali)
    monkeypatch.setattr(instagram_upload, "_graph_istek", olmamali)

    assert instagram_upload.try_publish_pending(proje) is None


# --- 5) gorev_sarmalayici: ucuncu log ailesi ------------------------------

def test_gorev_sarmalayici_maskeleyiciyi_kullaniyor():
    """YAPISAL tarama: sarmalayici `gizli_maskele`'yi GERCEKTEN cagiriyor mu.

    NEDEN BURAYA EKLENDI: bu dosyanin konusu "sizintinin KAYNAGI". 2026-09-12
    denetiminde ucuncu bir log ailesi (`gorev_izleri/*.log`) bulundu ve
    `gorev_sarmalayici.py` `gizli_maskele`'yi HIC import etmiyordu — yani
    tarama, kapsamasi gereken bir kaynagi kapsamiyordu.

    NEDEN AYRICA `log_rotate` BU KLASORU TEMIZLEMIYOR: sarmalayicinin kendi
    `_buda()`'si satir sayisina gore ATOMIK budama yapiyor; `trim_log()` ise
    duz `open(path, "w")` ile yeniden yaziyor. Yani buradaki bir sizinti
    SONRADAN temizlenmiyor — maskeleme YAZARKEN olmak zorunda.
    """
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kaynak = open(os.path.join(kok, "gorev_sarmalayici.py"),
                  encoding="utf-8").read()
    assert "from gizli_maskele import maskele" in kaynak, \
        "gorev_sarmalayici.py maskeleyiciyi hic import etmiyor"


def test_gorev_sarmalayici_stderr_i_ham_dosyaya_baglamiyor():
    """`sys.stderr = <ham dosya>` maskeleyiciyi ATLAR — ast ile kilitli.

    Bu yol `_yaz()`'dan BAGIMSIZ: `_yaz` maskeliyor olsa bile, stderr ham bir
    dosya nesnesine baglandiginda C-seviyesi uyarilar, thread istisnalari ve
    kapanis traceback'leri iz dosyasina MASKELENMEDEN duser.
    """
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agac = ast.parse(open(os.path.join(kok, "gorev_sarmalayici.py"),
                          encoding="utf-8").read())

    def _maskeli_akis_cagrisi(dugum):
        return (isinstance(dugum, ast.Call)
                and getattr(dugum.func, "id", None) == "_MaskeliAkis")

    # `sys.stderr = _MaskeliAkis(...)` dogrudan yazilabilir, ya da once bir
    # yerel degiskene alinabilir (bugunku hali: `hata_akisi`) — ikisi de gecerli.
    guvenli_adlar = set()
    atamalar = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Assign):
            continue
        if _maskeli_akis_cagrisi(dugum.value):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name):
                    guvenli_adlar.add(hedef.id)
        for hedef in dugum.targets:
            if (isinstance(hedef, ast.Attribute) and hedef.attr == "stderr"
                    and isinstance(hedef.value, ast.Name)
                    and hedef.value.id == "sys"):
                atamalar.append(dugum.value)

    assert atamalar, "sys.stderr yonlendirmesi hic bulunamadi (tasindi mi?)"
    for deger in atamalar:
        tamam = (_maskeli_akis_cagrisi(deger)
                 or (isinstance(deger, ast.Name) and deger.id in guvenli_adlar))
        assert tamam, \
            "sys.stderr maskeleyici sarmalayicisindan GECMEDEN baglaniyor"
