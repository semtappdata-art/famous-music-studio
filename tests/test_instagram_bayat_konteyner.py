# -*- coding: utf-8 -*-
"""Instagram bayat konteyner YAS KAPISI + "None"in sebebini ayirt eden log.

ARIZA A (bayat konteyner sonsuz dongusu, 2026-09-11):
`projects/Gece Surusu` ve `projects/Kalbim Oynuyor` state'lerinde 05 Eylul
damgali konteynerler, yayin damgalari 01 Eylul. `_konteyner_yayindan_yeni()`
True donuyor, `try_publish_pending()` yayinlamaya devam ediyor — ama
konteynerler 7 GUNLUK, yani Instagram'in 24 saatlik omrunu coktan asmislar.
Instagram `status_code` olarak **EXPIRED DONDURMUYOR** (donduruyor olsaydi
mevcut EXPIRED dali temizlerdi); bunun yerine `media_publish` adiminda
HTTP 500 `{"message":"Service temporarily unavailable","is_transient":true,
"code":2}` veriyor. Sonuc: her golden-hour saatinde 2 bosa API cagrisi,
11 Eylul'de 8 hata (`auto_process.log:3167+`), ve KENDILIGINDEN asla
duzelmiyor.

ARIZA B (yaniltici log satiri): yayinlanmis projelerde bayat kayit state'te
durdugu icin `try_publish_pending()` sessizce None donuyor, `auto_process`
bunu "konteyner hazir, golden-hour penceresi bekleniyor" diye logluyordu —
her kosuda 13 kez, gercekte bekleyen TEK proje varken.

Tum ag cagrilari monkeypatch ile taklit ediliyor; GERCEK istek YOK.
Token degerleri SAHTEDIR.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import auto_process as ap
import instagram_upload

SAHTE_IG = "IGQWRPSAHTE1234567890abcdefGHIJKLMNOP"


class _SahteDurum:
    """`_graph_istek`in donusunu taklit eder (sadece .json() kullaniliyor)."""

    def __init__(self, veri):
        self._veri = veri
        self.status_code = 200
        self.text = json.dumps(veri)

    def json(self):
        return self._veri


def _damga(saat_once: float) -> str:
    """`instagram_container_created_at` ile AYNI bicim/saat dilimi.

    Sabit metin ("2026-09-05T14:21:19") yerine "su andan N saat once" diye
    uretiliyor: sabit damga yazan bir test, takvim ilerledikce sessizce
    anlamini degistirir (bugun taze olan damga yarin bayat olur)."""
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _proje_yaz(tmp_path, ad: str, state: dict) -> str:
    proje = tmp_path / ad
    proje.mkdir()
    (proje / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                      encoding="utf-8")
    return str(proje)


def _durum_oku(proje: str) -> dict:
    with open(os.path.join(proje, "state.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ag_yasak(monkeypatch):
    """Token okuma ve Graph API cagrilarini YASAKLAR; cagrilirsa test patlar."""
    def olmamali(*a, **kw):
        raise AssertionError("bayat konteyner icin aga HIC gidilmemeliydi")

    monkeypatch.setattr(instagram_upload, "get_access_token", olmamali)
    monkeypatch.setattr(instagram_upload, "_graph_istek", olmamali)


# --- Yas kapisinin kendisi -----------------------------------------------

def test_yedi_gunluk_konteyner_bayat_sayiliyor():
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": _damga(7 * 24)}) is True


def test_esik_23_saat(monkeypatch):
    """Tam esik: 22 saat taze, 23 saat + 1 dakika bayat.

    24 degil 23: damga YEREL saatle yaziliyor, Instagram'in saati bizimkiyle
    birebir ayni olmak zorunda degil ve 24 saate dakikalar kala yayina
    kalkismak yaris durumu. 23 saat, golden-hour pencereleri arasi en kotu
    araligi (~14 saat) hala rahatca kapsiyor."""
    assert instagram_upload.KONTEYNER_OMRU_SN == 23 * 3600
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": _damga(22)}) is False
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": _damga(23 + 1 / 60)}) is True


def test_damga_yoksa_veya_bozuksa_bayat_SAYILMIYOR():
    """TEMKINLI dal: yas bilinmiyorsa "sil" demek, gercekten bekleyen bir
    konteyneri sessizce dusurup gonderiyi hic yayinlamamak demekti."""
    assert instagram_upload._konteyner_bayat({}) is False
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": ""}) is False
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": "bozuk-damga"}) is False
    assert instagram_upload._konteyner_bayat(
        {"instagram_container_created_at": 12345}) is False
    assert instagram_upload._konteyner_yasi_sn(
        {"instagram_container_created_at": "2026-13-45T99:99:99"}) is None


# --- Ariza A: gercek senaryo (Gece Surusu / Kalbim Oynuyor) ---------------

def test_yedi_gunluk_konteyner_aga_HIC_gitmeden_temizleniyor(tmp_path, ag_yasak):
    """DUZELTMEDEN ONCEKI kodda KIRMIZI: eski kod once token aliyor, Graph
    API'ye gidiyor, FINISHED goruyor ve `media_publish`e kalkisiyordu
    (uretimde HTTP 500). `ag_yasak` fikstürü o cagrilarin ikisini de
    AssertionError'a ceviriyor."""
    proje = _proje_yaz(tmp_path, "Gece Surusu", {
        "instagram_media_id": "17957449007998018",
        "instagram_uploaded_at": _damga(11 * 24),      # 01 Eylul yayini
        "instagram_creation_id": "18092925116265431",
        "instagram_container_created_at": _damga(7 * 24),   # 05 Eylul konteyneri
    })

    sebep: dict = {}
    sonuc = instagram_upload.try_publish_pending(proje, sebep_out=sebep)

    assert sonuc is None
    assert sebep["kod"] == instagram_upload.SEBEP_BAYAT_TEMIZLENDI
    veri = _durum_oku(proje)
    assert "instagram_creation_id" not in veri
    assert "instagram_container_created_at" not in veri
    # Yayinlanmis gonderi KORUNUYOR — temizlenen sadece olu konteyner kaydi.
    assert veri["instagram_media_id"] == "17957449007998018"
    assert veri["instagram_uploaded_at"]


def test_bayat_temizligi_operator_komutunu_basiyor(tmp_path, ag_yasak, capsys):
    """Mevcut EXPIRED dalindaki operator mesaji bayat dalinda da verilmeli —
    kullanici ne oldugunu log'dan/konsoldan anlayabilsin."""
    proje = _proje_yaz(tmp_path, "Kalbim Oynuyor", {
        "instagram_media_id": "17900000000000000",
        "instagram_uploaded_at": _damga(11 * 24),
        "instagram_creation_id": "18000000000000000",
        "instagram_container_created_at": _damga(7 * 24),
    })

    instagram_upload.try_publish_pending(proje)

    cikti = capsys.readouterr().out
    assert "bayat" in cikti
    assert "kaydı temizleniyor" in cikti
    assert "instagram_upload.py --project" in cikti


def test_bayat_kapisi_cift_yayin_korumasinin_ONUNDE(tmp_path, ag_yasak):
    """Konteyner son yayindan ESKI olsa bile (yani cift-yayin korumasi zaten
    cikaracak olsa bile) olu kayit temizlenmeli.

    Kapi asagida olsaydi bu kayitlar state'te SONSUZA KADAR kalir ve
    `auto_process` onlari her kosuda "bekleyen konteyner" sanmaya devam
    ederdi — Ariza B'nin kaynagi tam olarak buydu."""
    proje = _proje_yaz(tmp_path, "Eski Kayit", {
        "instagram_media_id": "17900000000000001",
        "instagram_uploaded_at": _damga(24),           # yayin, konteynerden YENI
        "instagram_creation_id": "18000000000000001",
        "instagram_container_created_at": _damga(7 * 24),
    })

    sebep: dict = {}
    assert instagram_upload.try_publish_pending(proje, sebep_out=sebep) is None
    assert sebep["kod"] == instagram_upload.SEBEP_BAYAT_TEMIZLENDI
    assert "instagram_creation_id" not in _durum_oku(proje)


def test_taze_konteyner_yas_kapisindan_GECIYOR(tmp_path, monkeypatch):
    """Yas kapisi GERCEKTEN bekleyen hicbir konteyneri dusurmemeli."""
    proje = _proje_yaz(tmp_path, "Taze", {
        "instagram_creation_id": "18000000000000002",
        "instagram_container_created_at": _damga(1),
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    istekler = []

    def sahte_istek(metot, url, ne, **kw):
        istekler.append(ne)
        return _SahteDurum({"status_code": "FINISHED"})

    monkeypatch.setattr(instagram_upload, "_graph_istek", sahte_istek)
    # Golden-hour DISINDAYIZ -> yayinlamadan bekle (gercek yayin denenmesin).
    monkeypatch.setattr(instagram_upload.config, "next_golden_publish_time",
                        lambda *a, **kw: "2026-09-12T19:00:00")

    sebep: dict = {}
    assert instagram_upload.try_publish_pending(proje, sebep_out=sebep) is None
    assert istekler == ["konteyner durumu"]
    assert sebep["kod"] == instagram_upload.SEBEP_GOLDEN_HOUR
    # Taze kayit KORUNUYOR.
    assert _durum_oku(proje)["instagram_creation_id"] == "18000000000000002"


def test_damgasiz_konteyner_eski_davranisi_koruyor(tmp_path, monkeypatch):
    """`instagram_container_created_at` eklenmeden ONCEKI state'ler: yas
    bilinmiyor, bu yuzden yas kapisi devreye GIRMEMELI ve kayit silinmemeli.
    Bu state'ler icin tek emniyet agi hala Instagram'in EXPIRED cevabi."""
    proje = _proje_yaz(tmp_path, "Damgasiz", {
        "instagram_creation_id": "18000000000000003",
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    istekler = []

    def sahte_istek(metot, url, ne, **kw):
        istekler.append(ne)
        return _SahteDurum({"status_code": "FINISHED"})

    monkeypatch.setattr(instagram_upload, "_graph_istek", sahte_istek)
    monkeypatch.setattr(instagram_upload.config, "next_golden_publish_time",
                        lambda *a, **kw: "2026-09-12T19:00:00")

    sebep: dict = {}
    assert instagram_upload.try_publish_pending(proje, sebep_out=sebep) is None
    # Yas kapisi atlandi -> API'ye gidildi (eski davranis aynen).
    assert istekler == ["konteyner durumu"]
    assert sebep["kod"] == instagram_upload.SEBEP_GOLDEN_HOUR
    assert _durum_oku(proje)["instagram_creation_id"] == "18000000000000003"


def test_damgasiz_EXPIRED_dali_hala_temizliyor(tmp_path, monkeypatch):
    proje = _proje_yaz(tmp_path, "Damgasiz Expired", {
        "instagram_creation_id": "18000000000000004",
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    monkeypatch.setattr(instagram_upload, "_graph_istek",
                        lambda *a, **kw: _SahteDurum({"status_code": "EXPIRED"}))

    sebep: dict = {}
    assert instagram_upload.try_publish_pending(proje, sebep_out=sebep) is None
    assert sebep["kod"] == instagram_upload.SEBEP_SURESI_DOLDU
    assert "instagram_creation_id" not in _durum_oku(proje)


# --- Geriye uyumluluk: mevcut cagri noktalari BOZULMAMALI ----------------

def test_sebep_out_opsiyonel(tmp_path, ag_yasak):
    """`dj_famous_process.py` ve bu modulun kendi CLI'i tek argumanla
    (pozisyonel) cagiriyor — imza geriye uyumlu kalmali."""
    proje = _proje_yaz(tmp_path, "Tek Arguman", {
        "instagram_creation_id": "18000000000000005",
        "instagram_container_created_at": _damga(7 * 24),
    })
    assert instagram_upload.try_publish_pending(proje) is None
    assert "instagram_creation_id" not in _durum_oku(proje)


# --- Ariza B: auto_process log satiri ------------------------------------

def _log_topla(monkeypatch) -> list:
    satirlar: list = []
    monkeypatch.setattr(ap, "log", lambda mesaj: satirlar.append(mesaj))
    return satirlar


def test_zaten_yayinlanmis_proje_golden_hour_satirini_BASMIYOR(tmp_path, monkeypatch):
    """ARIZA B'nin ta kendisi: "golden-hour penceresi bekleniyor" satiri her
    kosuda 13 kez basiliyordu, gercekte bekleyen TEK proje vardi."""
    # Damga TAZE (yas kapisi devrede degil) ama yayindan ESKI — yani
    # "zaten yayinlanmis, bekleyen is yok" dali.
    proje = _proje_yaz(tmp_path, "Yayinlanmis", {
        "instagram_media_id": "17900000000000002",
        "instagram_uploaded_at": _damga(1),
        "instagram_creation_id": "18000000000000006",
        "instagram_container_created_at": _damga(2),
    })

    def olmamali(*a, **kw):
        raise AssertionError("bekleyen is yokken aga gidilmemeliydi")

    monkeypatch.setattr(instagram_upload, "get_access_token", olmamali)
    monkeypatch.setattr(instagram_upload, "_graph_istek", olmamali)

    satirlar = _log_topla(monkeypatch)
    ap._check_instagram_pending(proje)

    assert not any("golden-hour penceresi bekleniyor" in s for s in satirlar), satirlar
    assert any("bekleyen konteyner yok" in s for s in satirlar), satirlar


def test_bayat_temizligi_log_satiri_ayri(tmp_path, ag_yasak, monkeypatch):
    proje = _proje_yaz(tmp_path, "Bayat", {
        "instagram_media_id": "17900000000000003",
        "instagram_uploaded_at": _damga(11 * 24),
        "instagram_creation_id": "18000000000000007",
        "instagram_container_created_at": _damga(7 * 24),
    })

    satirlar = _log_topla(monkeypatch)
    ap._check_instagram_pending(proje)

    assert not any("golden-hour penceresi bekleniyor" in s for s in satirlar), satirlar
    assert any("bayat" in s and "temizlendi" in s for s in satirlar), satirlar


def test_golden_hour_satiri_SADECE_gercekten_bekleyende(tmp_path, monkeypatch):
    proje = _proje_yaz(tmp_path, "Gercekten Bekleyen", {
        "instagram_creation_id": "18000000000000008",
        "instagram_container_created_at": _damga(1),
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    monkeypatch.setattr(instagram_upload, "_graph_istek",
                        lambda *a, **kw: _SahteDurum({"status_code": "FINISHED"}))
    monkeypatch.setattr(instagram_upload.config, "next_golden_publish_time",
                        lambda *a, **kw: "2026-09-12T19:00:00")

    satirlar = _log_topla(monkeypatch)
    ap._check_instagram_pending(proje)

    assert any("golden-hour penceresi bekleniyor" in s for s in satirlar), satirlar


def test_isleniyor_dali_golden_hour_satirini_basmiyor(tmp_path, monkeypatch):
    proje = _proje_yaz(tmp_path, "Isleniyor", {
        "instagram_creation_id": "18000000000000009",
        "instagram_container_created_at": _damga(0.1),
    })

    monkeypatch.setattr(instagram_upload, "get_access_token",
                        lambda: {"access_token": SAHTE_IG, "ig_user_id": "1"})
    monkeypatch.setattr(instagram_upload, "_graph_istek",
                        lambda *a, **kw: _SahteDurum({"status_code": "IN_PROGRESS"}))

    satirlar = _log_topla(monkeypatch)
    ap._check_instagram_pending(proje)

    assert not any("golden-hour penceresi bekleniyor" in s for s in satirlar), satirlar
    assert any("işleniyor" in s for s in satirlar), satirlar
