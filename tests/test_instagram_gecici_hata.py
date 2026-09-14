# -*- coding: utf-8 -*-
"""Instagram `_graph_istek`: DAR gecici-hata (5xx + `is_transient`) yeniden denemesi.

NE KAPATILIYOR (pencere kenari riski): golden-hour penceresinin sonuna
dakikalar kala (or. 21:12, pencere 22:00'de kapaniyor) gelen GERCEK bir
gecici HTTP 500'un dogal tekrar sansi kalmiyor — bir sonraki kontrol
pencerenin disinda kalir ve o yayin GUNU kacirir. Olcum (2026-09-12): tum
log gecmisinde TOPLAM 8 adet 5xx var, hepsi 2026-09-11 golden-hour
saatlerinde tam ikiser, yani iki BAYAT konteynerin imzasi; o ariza 23
saatlik yas kapisiyla kaynagindan kesildi ve TAZE bir konteyner bugune
kadar HIC 500 yemedi. Bu yuzden dal bilerek DAR.

BU DOSYANIN ASIL ISI — CIFT YAYIN GUVENLIGINI KANITLAMAK.
`media_publish` IDEMPOTENT DEGIL; ayni konteyner iki kez yayinlanirsa
kanalda ayni Reel iki kez cikar. Ayrim:

  * TAM bir HTTP yanit geldi + kod 5xx + govdede `is_transient: true`
    -> Instagram istegi ISLEMEDIGINI kendisi soyluyor -> tekrar GUVENLI.
  * Baglanti hatasi / zaman asimi (yanit KAYBOLDU) -> istek islenmis
    OLABILIR -> TEKRAR YOK. `except RequestException` dali oldugu gibi
    duruyor ve `test_media_publish_baglanti_hatasinda_TEK_cagri` bunu
    her kosuda dogruluyor.

Ayrica 4xx dalina dokunulmadigi (kota/izin/politika hatalari tekrarlanmaz)
ve bekleme tavaninin asilmadigi dogrulaniyor.

TUM ag cagrilari ve TUM `sleep`ler monkeypatch ile taklit ediliyor: GERCEK
istek YOK, GERCEK bekleme YOK. Token degerleri SAHTEDIR.
"""

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

SAHTE_IG = "IGQWRPSAHTE1234567890abcdefGHIJKLMNOP"

# Uretimde GORULEN gercek govde (auto_process.log:3167+), duz bicim.
GECICI_GOVDE_DUZ = {
    "message": "Service temporarily unavailable",
    "is_transient": True,
    "code": 2,
}
# Meta'nin diger sarmalayicisi — ikisi de kabul edilmeli.
GECICI_GOVDE_SARILI = {
    "error": {
        "message": "Service temporarily unavailable",
        "is_transient": True,
        "code": 2,
    }
}


class _SahteYanit:
    """`requests.request` donusunu taklit eder (status_code/text/json)."""

    def __init__(self, status_code=200, veri=None, govde=None):
        self.status_code = status_code
        self._veri = veri
        self.text = govde if govde is not None else json.dumps(veri or {})

    def json(self):
        if self._veri is None:
            raise json.JSONDecodeError("JSON yok", self.text or "", 0)
        return self._veri


@pytest.fixture
def sahte_ag(monkeypatch):
    """Sirayla verilen yanitlari donduren bir `requests.request` kurar ve
    `time.sleep`i kaydedip HIC beklemeyen bir sahteyle degistirir.

    GERCEK `sleep` bilerek yasak: en kotu senaryo 40 saniye, bunu test
    suresine eklemek testi yavaslatir ve kimse tavani olcemez."""
    kayit = {"cagrilar": [], "uykular": []}

    monkeypatch.setattr(instagram_upload.time, "sleep",
                        lambda sn: kayit["uykular"].append(sn))

    def kur(yanitlar):
        sira = list(yanitlar)

        def sahte_request(metot, url, **kw):
            kayit["cagrilar"].append((metot, url))
            if not sira:
                raise AssertionError(
                    f"beklenenden FAZLA istek: {len(kayit['cagrilar'])}")
            sonraki = sira.pop(0)
            if isinstance(sonraki, Exception):
                raise sonraki
            return sonraki

        monkeypatch.setattr(instagram_upload.requests, "request", sahte_request)
        return kayit

    kayit["kur"] = kur
    return kayit


# --- (a) 5xx + is_transient:true -> yeniden deniyor, sonunda basarili ----

def test_gecici_5xx_yeniden_denenip_basariyla_bitiyor(sahte_ag, capsys):
    basarili = _SahteYanit(200, {"id": "17999999999999999"})
    kayit = sahte_ag["kur"]([
        _SahteYanit(500, GECICI_GOVDE_DUZ),
        _SahteYanit(500, GECICI_GOVDE_DUZ),
        basarili,
    ])

    resp = instagram_upload._graph_istek(
        "POST", "https://graph.instagram.com/v21.0/1/media_publish",
        "yayınlama (media_publish)",
        data={"creation_id": "18000000000000001", "access_token": SAHTE_IG})

    assert resp is basarili
    assert len(kayit["cagrilar"]) == 3
    assert kayit["uykular"] == list(instagram_upload.GECICI_5XX_BEKLEME_SN)
    # Sessiz yeniden deneme, OLMAYAN yeniden denemeden kotudur: log satiri sart.
    cikti = capsys.readouterr().out
    assert cikti.count("yeniden") == 2
    assert "is_transient" in cikti


def test_sarili_error_bicimi_de_taniniyor(sahte_ag):
    """Meta hatayi bazen `{"error": {...}}` icinde sariyor. Tek bicime
    baglanmak, digeri geldiginde dalin SESSIZCE hic calismamasi demekti."""
    kayit = sahte_ag["kur"]([
        _SahteYanit(503, GECICI_GOVDE_SARILI),
        _SahteYanit(200, {"id": "17999999999999998"}),
    ])

    instagram_upload._graph_istek(
        "POST", "https://graph.instagram.com/v21.0/1/media", "konteyner oluşturma",
        data={"access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 2
    assert kayit["uykular"] == [instagram_upload.GECICI_5XX_BEKLEME_SN[0]]


def test_sinir_kodlari_500_ve_599_dahil(sahte_ag):
    for kod in (500, 502, 503, 599):
        assert instagram_upload._gecici_5xx_mi(
            _SahteYanit(kod, GECICI_GOVDE_DUZ)) is True


# --- (b) 5xx ama is_transient yok/false -> yeniden DENEMIYOR -------------

@pytest.mark.parametrize("veri, govde", [
    ({"message": "Internal error", "code": 1}, None),                 # alan YOK
    ({"message": "Kalici", "is_transient": False}, None),             # False
    ({"error": {"message": "Kalici", "is_transient": False}}, None),  # sarili False
    ({"is_transient": "true"}, None),                                 # metin, bool DEGIL
    (None, "<html>502 Bad Gateway</html>"),                           # JSON degil
    (None, ""),                                                       # bos govde
])
def test_isaretsiz_5xx_yeniden_DENENMIYOR(sahte_ag, veri, govde):
    """5xx TEK BASINA yetmiyor — Instagram'in kendi isaretine guveniliyor.

    NEDEN: bayat (olu) konteynerler de HTTP 500 veriyordu; orada tekrar
    denemek sadece bosa API cagrisiydi, hata KALICIYDI."""
    kayit = sahte_ag["kur"]([_SahteYanit(500, veri, govde)])

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "GET", "https://graph.instagram.com/v21.0/123", "konteyner durumu",
            params={"access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 1
    assert kayit["uykular"] == []
    assert "HTTP 500" in str(hata.value)


# --- (c) 4xx -> yeniden DENEMIYOR ---------------------------------------

@pytest.mark.parametrize("kod", [400, 401, 403, 429])
def test_4xx_yeniden_DENENMIYOR(sahte_ag, kod):
    """400/401/403 kimlik, izin, kota ve politika hatalaridir; tekrar
    denemek kotayi yakar ve hiz sinirina takar."""
    kayit = sahte_ag["kur"]([
        _SahteYanit(kod, {"error": {"message": "Invalid OAuth access_token"}})])

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "GET", "https://graph.instagram.com/v21.0/123", "konteyner durumu",
            params={"access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 1
    assert kayit["uykular"] == []
    assert f"HTTP {kod}" in str(hata.value)


def test_4xx_govdesinde_is_transient_OLSA_BILE_denenmiyor(sahte_ag):
    """Saldirgan/bozuk bir 4xx govdesi 5xx dalini ACMAMALI — kapi ONCE
    durum koduna bakiyor."""
    kayit = sahte_ag["kur"]([_SahteYanit(400, GECICI_GOVDE_DUZ)])

    with pytest.raises(RuntimeError):
        instagram_upload._graph_istek(
            "POST", "https://graph.instagram.com/v21.0/1/media_publish",
            "yayınlama (media_publish)", data={"access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 1
    assert kayit["uykular"] == []
    assert instagram_upload._gecici_5xx_mi(
        _SahteYanit(400, GECICI_GOVDE_DUZ)) is False


# --- (d) Denemeler tukenirse ESKI davranis: hata yukseliyor --------------

def test_denemeler_tukenince_eski_hata_mesaji_aynen(sahte_ag):
    kayit = sahte_ag["kur"](
        [_SahteYanit(500, GECICI_GOVDE_DUZ)] * instagram_upload.GECICI_5XX_DENEME)

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "POST", "https://graph.instagram.com/v21.0/1/media_publish",
            "yayınlama (media_publish)", data={"access_token": SAHTE_IG})

    metin = str(hata.value)
    assert metin.startswith("Instagram yayınlama (media_publish): HTTP 500 — ")
    assert "Service temporarily unavailable" in metin
    assert len(kayit["cagrilar"]) == instagram_upload.GECICI_5XX_DENEME
    assert len(kayit["uykular"]) == instagram_upload.GECICI_5XX_DENEME - 1


def test_tukenen_denemede_de_token_sizmiyor(sahte_ag):
    """Mevcut sizinti korumasi (bkz. `tests/test_sizinti_kaynaklari.py`)
    yeni dalda da gecerli olmali: govde `maskele`den geciyor."""
    govde = '{"is_transient": true, "message": "access_token=%s"}' % SAHTE_IG
    veri = {"is_transient": True, "message": f"access_token={SAHTE_IG}"}
    sahte_ag["kur"]([_SahteYanit(500, veri, govde)] * instagram_upload.GECICI_5XX_DENEME)

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "GET", "https://graph.instagram.com/v21.0/123", "konteyner durumu",
            params={"access_token": SAHTE_IG})

    assert SAHTE_IG not in str(hata.value), f"SIZINTI: {hata.value!r}"


# --- (e) Bekleme tavani --------------------------------------------------

def test_bekleme_tavani_asilmiyor(sahte_ag):
    """En fazla 2-3 deneme, toplam en kotu bekleme ~96 sn'yi ASMAMALI.

    Tavan dar tutuldu cunku bu dalin tek amaci golden-hour penceresinin
    SON dakikalarini kurtarmak; beklemeyle pencerenin kalanini yemek degil."""
    assert instagram_upload.GECICI_5XX_DENEME <= 3
    assert sum(instagram_upload.GECICI_5XX_BEKLEME_SN) <= 96
    # Deneme sayisi bekleme listesinden TUREMELI (ikisi birbirinden kayarsa
    # IndexError olurdu).
    assert (instagram_upload.GECICI_5XX_DENEME
            == len(instagram_upload.GECICI_5XX_BEKLEME_SN) + 1)

    kayit = sahte_ag["kur"](
        [_SahteYanit(500, GECICI_GOVDE_DUZ)] * instagram_upload.GECICI_5XX_DENEME)
    with pytest.raises(RuntimeError):
        instagram_upload._graph_istek(
            "POST", "https://graph.instagram.com/v21.0/1/media_publish",
            "yayınlama (media_publish)", data={"access_token": SAHTE_IG})

    assert sum(kayit["uykular"]) <= 96, kayit["uykular"]


def test_gercek_sleep_cagrilmiyor(sahte_ag):
    """Bu dosyadaki HICBIR test gercekten beklememeli — koruma olarak
    gecen sureyi olcuyoruz."""
    sahte_ag["kur"]([
        _SahteYanit(500, GECICI_GOVDE_DUZ),
        _SahteYanit(200, {"id": "1"}),
    ])
    basladi = time.monotonic()
    instagram_upload._graph_istek(
        "POST", "https://graph.instagram.com/v21.0/1/media", "konteyner oluşturma",
        data={"access_token": SAHTE_IG})
    assert time.monotonic() - basladi < 1.0


# --- CIFT YAYIN GUVENLIGI: tasima katmani tekrari YOK --------------------

@pytest.mark.parametrize("istisna", [
    requests.exceptions.ConnectionError("Connection aborted"),
    requests.exceptions.ReadTimeout("Read timed out"),
    requests.exceptions.ConnectTimeout("Connect timed out"),
])
def test_media_publish_baglanti_hatasinda_TEK_cagri(sahte_ag, istisna):
    """EN ONEMLI TEST. `media_publish` idempotent DEGIL: yanit KAYBOLDUGUNDA
    istek islenmis OLABILIR, yani korü korüne tekrar ayni Reel'i IKI KEZ
    yayinlayabilir. Bu yuzden `except RequestException` dali oldugu gibi
    duruyor — tasima katmani tekrari EKLENMEDI.

    Yeni dalin on sarti sunucudan TAM bir yanit almak; istisna geldiginde
    o sarta hic gelinmiyor."""
    kayit = sahte_ag["kur"]([istisna])

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "POST", "https://graph.instagram.com/v21.0/1/media_publish",
            "yayınlama (media_publish)",
            data={"creation_id": "18000000000000002", "access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 1, "TASIMA KATMANI TEKRARI: cift yayin riski!"
    assert kayit["uykular"] == []
    assert "ağ hatası" in str(hata.value)
    assert type(istisna).__name__ in str(hata.value)


def test_ilk_5xx_sonrasi_baglanti_hatasi_da_TEKRARLANMIYOR(sahte_ag):
    """Karisik senaryo: 1. deneme gecici 5xx (guvenli, tekrar edildi),
    2. deneme baglanti hatasi -> ORADA DURULUYOR. Yeniden deneme hakki
    kalmis olmasi, belirsiz bir sonucu tekrarlamak icin gerekce degil."""
    kayit = sahte_ag["kur"]([
        _SahteYanit(500, GECICI_GOVDE_DUZ),
        requests.exceptions.ConnectionError("Connection aborted"),
    ])

    with pytest.raises(RuntimeError) as hata:
        instagram_upload._graph_istek(
            "POST", "https://graph.instagram.com/v21.0/1/media_publish",
            "yayınlama (media_publish)", data={"access_token": SAHTE_IG})

    assert len(kayit["cagrilar"]) == 2
    assert "ağ hatası" in str(hata.value)


# --- Uctan uca: try_publish_pending uzerinden TEK media_id --------------

def _proje_yaz(tmp_path, ad, state):
    proje = tmp_path / ad
    proje.mkdir()
    (proje / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                      encoding="utf-8")
    return str(proje)


def _durum_oku(proje):
    with open(os.path.join(proje, "state.json"), encoding="utf-8") as f:
        return json.load(f)


def _taze_damga():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


@pytest.fixture
def golden_hour_icinde(monkeypatch):
    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    monkeypatch.setattr(instagram_upload.config, "next_golden_publish_time",
                        lambda *a, **kw: None)


def test_uctan_uca_gecici_500_sonrasi_TEK_yayin(tmp_path, sahte_ag,
                                                golden_hour_icinde):
    """Pencere kenari senaryosu: konteyner hazir, golden-hour icindeyiz,
    `media_publish` bir kez gecici 500 veriyor -> yeniden deneniyor ve
    state'e TEK bir `instagram_media_id` yaziliyor."""
    proje = _proje_yaz(tmp_path, "Pencere Kenari", {
        "instagram_creation_id": "18000000000000003",
        "instagram_container_created_at": _taze_damga(),
    })

    kayit = sahte_ag["kur"]([
        _SahteYanit(200, {"status_code": "FINISHED"}),   # konteyner durumu
        _SahteYanit(500, GECICI_GOVDE_DUZ),              # media_publish (gecici)
        _SahteYanit(200, {"id": "17900000000000123"}),   # media_publish (basarili)
    ])

    media_id = instagram_upload.try_publish_pending(proje)

    assert media_id == "17900000000000123"
    yayin_cagrilari = [u for _, u in kayit["cagrilar"] if u.endswith("media_publish")]
    assert len(yayin_cagrilari) == 2   # 1 gecici + 1 basarili, KOPYA yok
    veri = _durum_oku(proje)
    assert veri["instagram_media_id"] == "17900000000000123"
    assert "instagram_creation_id" not in veri
    assert "instagram_container_created_at" not in veri


def test_uctan_uca_baglanti_hatasi_state_i_KIRLETMIYOR(tmp_path, sahte_ag,
                                                       golden_hour_icinde):
    """`media_publish` sirasinda baglanti koparsa: TEK deneme, hata yukseliyor,
    state'e `instagram_media_id` YAZILMIYOR — bekleyen konteyner duruyor.
    (Yayin gercekten olustuysa bunu operator gorur; sessizce IKINCI bir
    yayin uretmiyoruz.)"""
    proje = _proje_yaz(tmp_path, "Kopan Baglanti", {
        "instagram_creation_id": "18000000000000004",
        "instagram_container_created_at": _taze_damga(),
    })

    kayit = sahte_ag["kur"]([
        _SahteYanit(200, {"status_code": "FINISHED"}),
        requests.exceptions.ReadTimeout("Read timed out"),
    ])

    with pytest.raises(RuntimeError):
        instagram_upload.try_publish_pending(proje)

    yayin_cagrilari = [u for _, u in kayit["cagrilar"] if u.endswith("media_publish")]
    assert len(yayin_cagrilari) == 1, "TASIMA KATMANI TEKRARI: cift yayin riski!"
    veri = _durum_oku(proje)
    assert "instagram_media_id" not in veri
    assert veri["instagram_creation_id"] == "18000000000000004"


def test_konteyner_durumu_sorgusu_da_kurtariliyor(tmp_path, sahte_ag,
                                                  golden_hour_icinde):
    """Dal `media_publish`e ozel DEGIL — merkezi sarmalayicida oldugu icin
    GET `status_code` sorgusu da ayni gecici arizadan kurtuluyor. Bu cagri
    zaten idempotent (salt okuma)."""
    proje = _proje_yaz(tmp_path, "Durum Sorgusu", {
        "instagram_creation_id": "18000000000000005",
        "instagram_container_created_at": _taze_damga(),
    })

    kayit = sahte_ag["kur"]([
        _SahteYanit(502, GECICI_GOVDE_SARILI),           # konteyner durumu (gecici)
        _SahteYanit(200, {"status_code": "FINISHED"}),   # konteyner durumu
        _SahteYanit(200, {"id": "17900000000000456"}),   # media_publish
    ])

    assert instagram_upload.try_publish_pending(proje) == "17900000000000456"
    assert len(kayit["cagrilar"]) == 3
