# -*- coding: utf-8 -*-
"""Ritim kuralları GERÇEK kapılara bağlı mı (CLAUDE.md "bağlantı seviyesinde sessiz arıza").

yayin_ritmi.py kendi içinde doğru olabilir ve hiçbir hat onu çağırmayabilir — bu depoda
tam olarak bu sınıf arıza on kez yaşandı. Bu dosya her bağlantı noktasını hem DAVRANIŞLA
hem `ast` ile (çağrı VAR ve doğru yerde) kilitler:

  R1  dj_famous_process.process_set (YouTube yüklemesinden ÖNCE) + auto_process._auto_pace_count
  R3a auto_process.process_project Shorts dalı + _shorts_gecikmeli_supurge (main finally)
      + dj_famous_process.process_set Shorts dalı; _ana_anahtarlar Shorts'u şalter açıkken saymaz
  R3b ek_platform_backfill, facebook_backfill, instagram_upload.try_publish_pending,
      tiktok_web._kural_ihlalleri, auto_process (Instagram konteyneri + Facebook ana hattı)

Ağa çıkmaz; tüm yükleyiciler sahte.
"""

import ast
import json
import os
import sys
import time
from datetime import datetime

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _y in (_REPO, _UPLOAD):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import auto_process as ap
import config
import uyumluluk
import yayin_ritmi as YR

SAAT = 3600.0


def _an(g, s, dk=0, ay=9):
    return datetime(2026, ay, g, s, dk, tzinfo=config.TR_TZ).timestamp()


def _iso(ts):
    return datetime.fromtimestamp(ts, config.TR_TZ).isoformat()


def _yerel(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def _agac(yol):
    with open(os.path.join(_REPO, yol), "r", encoding="utf-8") as f:
        return ast.parse(f.read())


def _fonk(agac, ad):
    return next(n for n in ast.walk(agac) if isinstance(n, ast.FunctionDef) and n.name == ad)


def _cagri_satirlari(dugum, ad):
    satirlar = []
    for n in ast.walk(dugum):
        if isinstance(n, ast.Call):
            f = n.func
            isim = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if isim == ad:
                satirlar.append(n.lineno)
    return sorted(satirlar)


@pytest.fixture
def ayar(monkeypatch):
    monkeypatch.setattr(config, "YAYIN_RITMI_SET_SARKI_ARA_SAAT", 48, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKME_SAAT", 24, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", True, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 2, raising=False)


def _proje(kok, ad, **st):
    p = kok / ad
    (p / "output").mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": "rock"}), encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + ad).encode("utf-8"))
    for v in ("youtube_16x9.mp4", "shorts_9x16.mp4"):
        (p / "output" / v).write_bytes(b"x")
    return str(p)


# --- ast sözleşmeleri ----------------------------------------------------------

def test_ast_dj_process_set_kanal_tabanini_youtube_yuklemesinden_once_sorar():
    f = _fonk(_agac("dj_famous_process.py"), "process_set")
    taban = _cagri_satirlari(f, "kanal_tabani")
    yukle = [n.lineno for n in ast.walk(f) if isinstance(n, ast.Call)
             and getattr(n.func, "id", None) == "yt_upload"]
    assert taban and yukle and taban[0] < min(yukle)
    assert _cagri_satirlari(f, "shorts_zamani"), "set Shorts dalı R3a'yı sormuyor"


def test_ast_platform_gun_izni_tum_yayin_yollarinda():
    for yol, fonk in (("upload/ek_platform_backfill.py", "backfill"),
                      ("upload/facebook_backfill.py", "backfill"),
                      ("upload/instagram_upload.py", "try_publish_pending"),
                      ("upload/tiktok_web.py", "_kural_ihlalleri"),
                      ("auto_process.py", "process_project"),
                      ("auto_process.py", "_ek_platformlari_isle"),
                      ("auto_process.py", "_shorts_gecikmeli_supurge")):
        assert _cagri_satirlari(_fonk(_agac(yol), fonk), "platform_gun_izni"), (yol, fonk)


def test_ast_shorts_supurgesi_main_finally_icinde():
    main = _fonk(_agac("auto_process.py"), "main")
    tr = next(n for n in main.body if isinstance(n, ast.Try))
    cagrilar = [getattr(n.func, "id", None) for s in tr.finalbody for n in ast.walk(s)
                if isinstance(n, ast.Call)]
    assert "_shorts_gecikmeli_supurge" in cagrilar
    pp = _fonk(_agac("auto_process.py"), "process_project")
    assert _cagri_satirlari(pp, "shorts_zamani")
    assert _cagri_satirlari(_fonk(_agac("auto_process.py"), "_auto_pace_count"), "kanal_tabani")


# --- davranış: auto_process ------------------------------------------------------

def test_ana_anahtarlar_salter_acikken_shorts_saymaz(ayar, monkeypatch):
    assert "youtube_shorts_video_id" not in ap._ana_anahtarlar()
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", False)
    assert "youtube_shorts_video_id" in ap._ana_anahtarlar()


def test_auto_pace_count_setten_48_saat_gecmeden_yeni_sarki_yok(tmp_path, ayar, monkeypatch):
    simdi = time.time()
    k1, k2 = tmp_path / "projects", tmp_path / "dj_sets"
    eski = _proje(k1, "Eski", youtube_video_id="v", youtube_uploaded_at=_yerel(simdi - 100 * SAAT))
    yeni = _proje(k1, "Yeni")
    _proje(k2, "Set", youtube_video_id="d", youtube_uploaded_at=_yerel(simdi - 20 * SAAT))
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k1), str(k2)))
    assert ap._auto_pace_count([yeni], [eski, yeni]) == 0
    monkeypatch.setattr(config, "YAYIN_RITMI_SET_SARKI_ARA_SAAT", 12)
    assert ap._auto_pace_count([yeni], [eski, yeni]) == 1


class _Sahte:
    def __init__(self):
        self.shorts = []


def _sahte_youtube(monkeypatch, kayit):
    import youtube_upload

    def upload_short(project_dir, privacy, full_video_id=None, schedule=True):
        kayit.shorts.append(os.path.basename(project_dir))
        st = json.load(open(os.path.join(project_dir, "state.json"), encoding="utf-8"))
        st.update(youtube_shorts_video_id="S-" + os.path.basename(project_dir),
                  youtube_shorts_uploaded_at=_yerel(time.time()))
        json.dump(st, open(os.path.join(project_dir, "state.json"), "w", encoding="utf-8"))
        return "S"
    monkeypatch.setattr(youtube_upload, "upload_short", upload_short)
    import youtube_playlists
    monkeypatch.setattr(youtube_playlists, "sync_project", lambda *a, **k: None)
    monkeypatch.setattr(youtube_playlists, "get_authenticated_service", lambda: None)


@pytest.fixture
def supurge(tmp_path, ayar, monkeypatch):
    kok = tmp_path / "projects"
    kok.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    monkeypatch.setattr(ap, "log", lambda m: kayit_log.append(m))
    kayit_log = []
    up = tmp_path / "upload"
    up.mkdir()
    (up / "token.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ap, "_UPLOAD_DIR", str(up), raising=False)
    s = _Sahte()
    _sahte_youtube(monkeypatch, s)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda p, a="render": ([], []))
    return kok, s, kayit_log


def test_supurge_24_saat_dolmadan_shorts_yuklemez_dolunca_yukler(supurge):
    kok, s, loglar = supurge
    simdi = time.time()
    _proje(kok, "Taze", youtube_video_id="v", youtube_uploaded_at=_yerel(simdi - 5 * SAAT),
           youtube_privacy="public")
    _proje(kok, "Olgun", youtube_video_id="w", youtube_uploaded_at=_yerel(simdi - 30 * SAAT),
           youtube_privacy="public")
    ap._shorts_gecikmeli_supurge()
    assert s.shorts == ["Olgun"]
    assert any("Shorts" in m for m in loglar)


def test_supurge_kosu_basina_tek_shorts_ve_bekletme_uyumluluk(supurge, monkeypatch):
    kok, s, _ = supurge
    simdi = time.time()
    for ad in ("A", "B"):
        _proje(kok, ad, youtube_video_id=ad, youtube_uploaded_at=_yerel(simdi - 40 * SAAT),
               youtube_privacy="public")
    _proje(kok, "Bekle", youtube_video_id="x", youtube_uploaded_at=_yerel(simdi - 90 * SAAT),
           youtube_privacy="public", yayin_beklet={"sebep": "test"})
    ap._shorts_gecikmeli_supurge()
    assert len(s.shorts) == 1 and s.shorts[0] in ("A", "B")
    monkeypatch.setattr(uyumluluk, "kontrol", lambda p, a="render": (["telif"], []))
    ap._shorts_gecikmeli_supurge()
    assert len(s.shorts) == 1, "uyumluluk HATASI Shorts'u durdurmalı (fail-closed)"


def test_supurge_salter_kapaliyken_hicbir_sey_yapmaz(supurge, monkeypatch):
    kok, s, _ = supurge
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", False)
    _proje(kok, "A", youtube_video_id="a", youtube_uploaded_at=_yerel(time.time() - 40 * SAAT),
           youtube_privacy="public")
    ap._shorts_gecikmeli_supurge()
    assert s.shorts == []


# --- davranış: platform/gün tavanı -----------------------------------------------

def test_facebook_backfill_gun_tavanindaki_sarkiyi_atlar(tmp_path, ayar, monkeypatch):
    import facebook_backfill as F
    kok = tmp_path / "projects"
    bugun = time.strftime("%Y-%m-%d")
    dolu = _proje(kok, "Dolu", youtube_video_id="a", youtube_uploaded_at=bugun + "T08:00:00",
                  youtube_privacy="public", instagram_media_id="i",
                  instagram_uploaded_at=bugun + "T09:00:00")
    bos = _proje(kok, "Bos", youtube_video_id="b", youtube_uploaded_at="2026-09-01T08:00:00",
                 youtube_privacy="public")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    monkeypatch.setattr(F, "BASE", (str(kok),))
    monkeypatch.setattr(config, "EK_PLATFORMLAR", {"facebook": True})
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda p, a="render": ([], []))
    r = F.backfill(limit=2, dry_run=True, log=lambda m: None)
    assert r["islenen"] == ["Bos"], r
    assert any("Dolu" in e["proje"] for e in r.get("ritim", [])), r


def test_tiktok_web_kurali_gun_tavanini_uygular(ayar):
    import tiktok_web as TW
    st = {"youtube_video_id": "v", "youtube_publish_at": _iso(_an(15, 12)),
          "youtube_privacy": "public", "instagram_media_id": "i",
          "instagram_uploaded_at": _yerel(_an(15, 12, 30))}
    bag = {"katalog": [], "bantlar": [], "turev": [], "kit_rezervi": None, "kit_adayi": None}
    ihlal = TW._kural_ihlalleri(_an(15, 19), "p", st, bag, _an(13, 10))
    assert any("ritim" in i for i in ihlal), ihlal
    assert not any("ritim" in i for i in TW._kural_ihlalleri(_an(16, 19), "p", st, bag,
                                                             _an(13, 10)))


def test_ek_platform_backfill_gun_tavanindaki_sarkiyi_atlar(tmp_path, ayar, monkeypatch):
    import ek_platform_backfill as E
    kok = tmp_path / "projects"
    bugun = time.strftime("%Y-%m-%d")
    _proje(kok, "Dolu", youtube_video_id="a", youtube_uploaded_at=bugun + "T08:00:00",
           youtube_privacy="public", instagram_media_id="i",
           instagram_uploaded_at=bugun + "T09:00:00")
    _proje(kok, "Bos", youtube_video_id="b", youtube_uploaded_at="2026-09-01T08:00:00",
           youtube_privacy="public")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    monkeypatch.setattr(E, "BASE", str(kok))
    up = tmp_path / "up"
    up.mkdir()
    for pl in E.PLATFORMLAR:
        (up / pl[5]).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(E, "UPLOAD_DIR", str(up))
    monkeypatch.setattr(config, "EK_PLATFORMLAR", {"telegram": True, "bluesky": True})
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda p, a="render": ([], []))
    r = E.backfill(limit=2, dry_run=True, log=lambda m: None)
    assert all(x["proje"] == "Bos" for x in r["islenen"]) and r["islenen"], r
    assert r.get("ritim"), r


def test_config_sayilari_tanimli():
    import importlib
    import config as C
    importlib.reload(C)
    for ad in ("YAYIN_RITMI_SET_SARKI_ARA_SAAT", "YAYIN_RITMI_SHORTS_GECIKME_SAAT",
               "YAYIN_RITMI_SHORTS_GECIKMELI", "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI",
               "YAYIN_RITMI_PLATFORM_MIN_ARA_SAAT", "HIKAYE_KAPISI_TARIHI",
               "YOUTUBE_BASLIK_ROTASYONU_AKTIF", "YOUTUBE_BASLIK_KALIPLARI",
               "TUREV_TOPLULUK_TIKTOK_SONRASI_SAAT"):
        assert hasattr(C, ad), ad
    assert C.YAYIN_RITMI_SET_SARKI_ARA_SAAT == 48 and C.YAYIN_RITMI_SHORTS_GECIKME_SAAT == 24
    assert C.YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI == 2
