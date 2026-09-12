# -*- coding: utf-8 -*-
"""Kuyruk başı tıkanması: yalnız Instagram golden-hour yayınını bekleyen proje
`process_project` için SEÇİLMEZ (2026-09-13).

ARIZA (doğrulama turu 2, bulgu 1 — log'dan sayıldı): `main()` `pending[:count]`
alıyordu. Başındaki proje dört ana anahtardan yalnız `instagram_media_id`'si
eksik ve konteyneri (`instagram_creation_id`) golden-hour'u bekliyorsa, her
koşuda boşuna seçiliyordu: Son Kez 28, Sessiz Mektup 34, Yeraltı 11 kez yalnız
"Instagram: konteyner hazır, golden-hour bekleniyor" için seçildi ve arkadaki
YENİ şarkı o süre boyunca işlenemedi. O yayını zaten `_drain_golden_hour_queue`
(`ready` ile geziyor) yapıyor.

DEĞİŞMEYENLER: günlük pencerenin paydası TÜM pending (ayrılanlar dahil);
52 saatlik taban arkadaki yeni şarkıya aynen uygulanır; bayat konteyner ya da
konteynersiz proje normal seçilir.

Ağa ÇIKMAZ, üretim dosyalarına yazmaz (her şey tmp_path'te).
"""

import ast
import json
import os
import sys
import time

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap                            # noqa: E402

_FINALLY = ("_refresh_latest_listing", "_refresh_stats", "_refresh_comments",
            "_facebook_backfill", "_ek_platform_backfill", "_facebook_yorumlari",
            "_facebook_veri_erisimi", "_dj_tarama", "_saglik_kontrol",
            "_izlenme_raporu", "_haftalik_gozden_gecirme", "_gunluk_izlenme",
            "_tiktok_yayin_dogrulama", "_tiktok_kit_sirasi")


def _damga(saat_once):
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _proje(kok, ad, durum=None):
    d = kok / ad
    d.mkdir(parents=True)
    (d / "audio.wav").write_bytes(b"x")
    if durum is not None:
        (d / "state.json").write_text(json.dumps(durum), encoding="utf-8")
    return str(d)


def _geri(konteyner_yasi_sa=1.0, cid=True, yt_saat=200, **ek):
    """YouTube/Shorts/TikTok tamam; Instagram yayını eksik."""
    d = {"youtube_video_id": "v", "youtube_shorts_video_id": "s",
         "tiktok_publish_id": "t", "youtube_uploaded_at": _damga(yt_saat)}
    if cid:
        d["instagram_creation_id"] = "c1"
        d["instagram_container_created_at"] = _damga(konteyner_yasi_sa)
    d.update(ek)
    return d


@pytest.fixture
def kos(tmp_path, monkeypatch):
    kok = tmp_path / "projects"
    kok.mkdir()
    olay = {"islenen": [], "drain": [], "log": []}
    monkeypatch.setattr(sys, "argv", ["auto_process.py", "--base", str(kok)])
    monkeypatch.setattr(ap, "trim_log", lambda *a, **k: None)
    monkeypatch.setattr(ap, "auto_pull", lambda *a, **k: None)
    monkeypatch.setattr(ap, "_acquire_lock", lambda: True)
    monkeypatch.setattr(ap, "_release_lock", lambda: None)
    for ad in _FINALLY:
        monkeypatch.setattr(ap, ad, lambda *a, **k: None)
    monkeypatch.setattr(ap, "process_project",
                        lambda p, privacy, schedule=True: olay["islenen"].append(p))
    monkeypatch.setattr(ap, "_drain_golden_hour_queue",
                        lambda dirs: olay["drain"].append(list(dirs)))
    monkeypatch.setattr(ap, "log", lambda m: olay["log"].append(str(m)))

    def _calistir():
        ap.main()
        return olay
    return type("K", (), {"kok": kok, "calistir": staticmethod(_calistir)})


# --- KIRMIZI: asıl arıza ----------------------------------------------------

def test_ig_konteyneri_bekleyen_geri_doldurma_basta_arkadaki_yeni_sarki_secilir(kos):
    geri = _proje(kos.kok, "01_Son Kez", _geri())
    yeni = _proje(kos.kok, "02_Sabah Senin")
    olay = kos.calistir()
    assert olay["islenen"] == [yeni], olay["log"]
    # IG yayını drain'e kaldı: geri doldurma drain listesinde
    assert any(geri in d for d in olay["drain"]), olay["drain"]


# --- YEŞİL: ölçütün sınırları ------------------------------------------------

def test_bayat_konteyner_sira_disi_sayilmaz_normal_secilir(kos):
    geri = _proje(kos.kok, "01_Geri", _geri(konteyner_yasi_sa=30))
    _proje(kos.kok, "02_Yeni")
    assert kos.calistir()["islenen"] == [geri]


def test_creation_id_yoksa_normal_secilir(kos):
    geri = _proje(kos.kok, "01_Geri", _geri(cid=False))
    _proje(kos.kok, "02_Yeni")
    assert kos.calistir()["islenen"] == [geri]


def test_baska_anahtar_da_eksikse_normal_secilir(kos):
    d = _geri()
    d.pop("tiktok_publish_id")
    geri = _proje(kos.kok, "01_Geri", d)
    _proje(kos.kok, "02_Yeni")
    assert kos.calistir()["islenen"] == [geri]


def test_yalniz_drain_bekleyen_varsa_hicbir_sey_islenmez_drain_calisir(kos):
    geri = _proje(kos.kok, "01_Geri", _geri())
    olay = kos.calistir()
    assert olay["islenen"] == []
    assert olay["drain"] and geri in olay["drain"][0]
    assert any("İşlenecek proje yok" in s for s in olay["log"]), olay["log"]


def test_taban_arkadaki_yeni_sarkiya_uygulanir(kos):
    # geri doldurmanın YouTube yüklemesi 10 saat önce -> yeni şarkı 42 saat bekler
    _proje(kos.kok, "01_Geri", _geri(yt_saat=10))
    _proje(kos.kok, "02_Yeni")
    olay = kos.calistir()
    assert olay["islenen"] == []
    assert any("yeni yayın tabanı" in s for s in olay["log"]), olay["log"]


def test_gunluk_pencere_paydasi_degismedi_tum_pending(kos):
    """Payda TÜM pending (2) -> 12 saat; son paylaşım 13 saat önce -> serbest.
    Payda seçilebilirlere (1) düşseydi 24 saat olur ve bekletirdi."""
    _proje(kos.kok, "01_Geri", _geri(tiktok_uploaded_at=_damga(13)))
    yeni = _proje(kos.kok, "02_Yeni")
    assert kos.calistir()["islenen"] == [yeni]


def test_auto_pace_count_pencere_paydasi_parametresi(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "log", lambda m: None)
    eski = _proje(tmp_path, "Eski", {"youtube_video_id": "v",
                                     "youtube_uploaded_at": _damga(13 + 100),
                                     "tiktok_uploaded_at": _damga(13)})
    yeni = _proje(tmp_path, "Yeni")
    assert ap._auto_pace_count([yeni], [eski, yeni]) == 0          # 24 sa gerekir
    assert ap._auto_pace_count([yeni], [eski, yeni], pencere_paydasi=2) == 1


def test_ayirici_birim(tmp_path):
    a = _proje(tmp_path, "a", _geri())
    b = _proje(tmp_path, "b", _geri(konteyner_yasi_sa=30))
    c = _proje(tmp_path, "c", _geri(cid=False))
    e = _proje(tmp_path, "e")
    kalan, drain = ap._yalniz_drain_bekleyenleri_ayir([a, b, c, e])
    assert kalan == [b, c, e] and drain == [a]


def test_drain_ig_konteynerini_ready_ile_yayinlamaya_calisiyor(tmp_path, monkeypatch):
    """Ayrılan proje gerçekten drain'de: `_check_instagram_pending` çağrılıyor."""
    a = _proje(tmp_path, "a", _geri())
    ig = []
    monkeypatch.setattr(ap, "_check_instagram_pending", ig.append)
    monkeypatch.setattr(ap, "_check_tiktok_notification", lambda p, s: None)
    monkeypatch.setattr(ap, "_check_youtube_captions", lambda p, s: False)
    monkeypatch.setattr(ap, "_youtube_gorunurluk_planlarini_uygula", lambda d: None)
    ap._drain_golden_hour_queue([a])
    assert ig == [a]


# --- SÖZLEŞME (ast): main'deki dilim, _auto_pace_count'a verilen listeden ----

def _main():
    agac = ast.parse(open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read())
    return next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "main")


def test_main_batch_dilimi_auto_pace_count_listesiyle_ayni():
    main = _main()
    pace = [n for n in ast.walk(main) if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "_auto_pace_count"]
    assert len(pace) == 1 and isinstance(pace[0].args[0], ast.Name)
    liste = pace[0].args[0].id
    batch = [n for n in ast.walk(main) if isinstance(n, ast.Assign)
             and any(getattr(t, "id", None) == "batch" for t in n.targets)]
    assert len(batch) == 1
    dilim = batch[0].value
    assert isinstance(dilim, ast.Subscript) and dilim.value.id == liste, (
        "batch, _auto_pace_count'a verilen listeden dilimlenmeli")
    kws = {k.arg for k in pace[0].keywords}
    assert "pencere_paydasi" in kws, "payda tüm pending olarak AÇIKÇA geçilmeli"


def test_main_ayiriciyi_bekletmeden_sonra_kademelemeden_once_cagiriyor():
    main = _main()

    def satir(ad):
        return [n.lineno for n in ast.walk(main)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == ad]
    bek, dr, pace = (satir("_bekletilenleri_ayir"),
                     satir("_yalniz_drain_bekleyenleri_ayir"),
                     satir("_auto_pace_count"))
    assert bek and dr and pace and min(bek) < min(dr) < min(pace)
