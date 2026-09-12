# -*- coding: utf-8 -*-
"""Telegram/Bluesky ana hattan ÇIKTI; geri doldurmada yeni public şarkı ÖNCE (2026-09-13).

ARIZA (doğrulama turu 2, bulgu 4): `auto_process._ek_platformlari_isle`
Telegram ve Bluesky'ı `process_project` anında gönderiyordu — golden-hour,
gizlilik ve günlük tavan kapısı YOK. Pencere dışında işlenen yeni şarkı
YouTube'da private + `publishAt` iken linkiyle bu platformlara düşüyordu;
Bluesky 12 Eylül'de günlük tavan 1 iken 2 gönderi yaptı. Geri doldurmada
(`upload/ek_platform_backfill.py`) üç kapı da var. Facebook ana hatta KALDI:
native zamanlaması (`scheduled_publish_time`) var.

Karşılığı: geri doldurma adayları artık "public anı son 7 gün içinde" olanları
ÖNE alıyor — yoksa yeni şarkı 16+ günlük eski eksik kuyruğunun arkasında kalırdı.
Public anı GELECEKTE olan (private + publishAt bekleyen) proje aday DEĞİL.

Ağa ÇIKMAZ: yükleyici modüller sahte, çoğu test `dry_run=True`.
"""

import ast
import json
import os
import sys
import time
import types
from datetime import datetime, timedelta, timezone

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import auto_process as ap                           # noqa: E402
import config                                       # noqa: E402
import notify                                       # noqa: E402
import uyumluluk                                    # noqa: E402
import ag_yeniden_deneme as ag                      # noqa: E402
import ek_platform_backfill as E                    # noqa: E402

TUM_BAYRAKLAR = {"facebook": True, "telegram": True, "bluesky": True}


def _yerel(saat_once):
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.localtime(time.time() - saat_once * 3600))


def _utc(saat_once):
    an = datetime.now(timezone.utc) - timedelta(hours=saat_once)
    return an.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _proje(base, ad, durum, ses=None):
    d = os.path.join(base, ad)
    os.makedirs(os.path.join(d, "output"), exist_ok=True)
    for v in ("youtube_16x9.mp4", "shorts_9x16.mp4"):
        with open(os.path.join(d, "output", v), "wb") as f:
            f.write(b"x" * 8)
    if ses is not None:
        with open(os.path.join(d, "audio.wav"), "wb") as f:
            f.write(ses)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False)
    return d


@pytest.fixture
def base(tmp_path, monkeypatch):
    b = str(tmp_path / "projects")
    os.makedirs(b)
    monkeypatch.setattr(E, "BASE", b)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR", dict(TUM_BAYRAKLAR))
    sahte = tmp_path / "sahte_upload"
    sahte.mkdir()
    for p in E.PLATFORMLAR:
        (sahte / p[5]).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(E, "UPLOAD_DIR", str(sahte))
    monkeypatch.setattr(E, "_UYARILANLAR", set())
    E._KAPI_ONBELLEGI.clear()
    monkeypatch.setattr(notify, "uyar_bir_kez", lambda a, m: None)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda p, asama="render": ([], []))
    return b


def _eski(base, ad="00_eski"):
    return _proje(base, ad, {"youtube_video_id": "e", "youtube_privacy": "public",
                             "youtube_uploaded_at": _yerel(24 * 30),
                             "youtube_publish_at": None})


def test_tempo_disi_alan_adi_auto_process_ile_ayni():
    assert E.TEMPO_DISI_PUBLIC_ANI_ALANI == ap.TEMPO_DISI_PUBLIC_ANI_ALANI


def _secilen(s):
    return [(x["platform"], x["proje"]) for x in s["islenen"]]


def _tg():
    return [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]


# --- KIRMIZI 1: ana hat Telegram/Bluesky göndermez --------------------------

def test_process_project_ek_platformlarinda_telegram_bluesky_yok_facebook_kaldi(
        tmp_path, monkeypatch):
    cagri = []

    def _fb(p, schedule=True):
        cagri.append(("facebook_upload", schedule))
        return "fb1"

    def _diger(ad):
        def f(p, **k):
            cagri.append((ad, None))
            return "x"
        return f

    for mod, fonk, islev in (("facebook_upload", "upload_reels", _fb),
                             ("telegram_upload", "upload_video", _diger("telegram_upload")),
                             ("bluesky_upload", "upload_video", _diger("bluesky_upload"))):
        m = types.ModuleType(mod)
        setattr(m, fonk, islev)
        monkeypatch.setitem(sys.modules, mod, m)
    up = tmp_path / "upload"
    up.mkdir()
    for f in ("facebook_token.json", "telegram_client_secrets.json",
              "bluesky_client_secrets.json"):
        (up / f).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(config, "EK_PLATFORMLAR", dict(TUM_BAYRAKLAR))
    monkeypatch.setattr(ap, "log", lambda m: None)

    ap._ek_platformlari_isle(str(tmp_path / "p"), {}, str(up), False)

    assert cagri == [("facebook_upload", False)], cagri
    assert [t[0] for t in ap._EK_PLATFORMLAR] == ["facebook"]


def test_process_project_facebook_icin_ek_platformlari_hala_cagiriyor():
    """Facebook ana hatta KALDI: bağlantı kopmamalı (ast)."""
    agac = ast.parse(open(os.path.join(_KOK, "auto_process.py"), encoding="utf-8").read())
    pp = next(n for n in agac.body
              if isinstance(n, ast.FunctionDef) and n.name == "process_project")
    adlar = {getattr(n.func, "id", None) for n in ast.walk(pp) if isinstance(n, ast.Call)}
    assert "_ek_platformlari_isle" in adlar


# --- KIRMIZI 2: geri doldurma yeni public şarkıyı önce seçer ----------------

def test_backfill_yeni_public_sarkiyi_eski_eksik_sarkidan_once_secer(base):
    _eski(base)
    yeni = _proje(base, "01_yeni", {"youtube_video_id": "y", "youtube_privacy": "public",
                                    "youtube_uploaded_at": _yerel(30),
                                    "youtube_publish_at": _utc(20)})
    assert E.adaylar(_tg())[0][0] == yeni
    s = E.backfill(dry_run=True)
    assert _secilen(s) == [("Telegram", "01_yeni"), ("Bluesky", "01_yeni")], s


def test_zamanlamasiz_yeni_yukleme_de_yeni_sayilir(base):
    _eski(base)
    _proje(base, "01_yeni", {"youtube_video_id": "y", "youtube_privacy": "public",
                             "youtube_uploaded_at": _yerel(5),
                             "youtube_publish_at": None})
    assert [x[1] for x in _secilen(E.backfill(dry_run=True))] == ["01_yeni", "01_yeni"]


def test_yeni_grupta_en_yeni_once_eski_grup_degismedi(base):
    """Yeni grup: EN YENİ public anı önce (bugün çıkan şarkı geçen haftanınkini
    beklemesin). Eski grup: eskisi gibi eskiden yeniye."""
    a = _proje(base, "03_eskinin_eskisi", {"youtube_video_id": "a", "youtube_privacy": "public",
                                           "youtube_uploaded_at": _yerel(24 * 40)})
    b = _eski(base, "02_eski")
    c = _proje(base, "01_yeni_ama_once", {"youtube_video_id": "c", "youtube_privacy": "public",
                                          "youtube_uploaded_at": _yerel(60),
                                          "youtube_publish_at": _utc(50)})
    d = _proje(base, "00_en_yeni", {"youtube_video_id": "d", "youtube_privacy": "public",
                                    "youtube_uploaded_at": _yerel(10)})
    assert [p for p, _v in E.adaylar(_tg())] == [d, c, a, b]


def test_yedi_gunden_eski_public_ani_yeni_sayilmaz(base):
    b = _eski(base, "00_eski")
    sinirda = _proje(base, "01_sekiz_gun", {"youtube_video_id": "s", "youtube_privacy": "public",
                                            "youtube_uploaded_at": _yerel(24 * 8)})
    assert [p for p, _v in E.adaylar(_tg())] == [b, sinirda]


# --- YEŞİL: kapılar ----------------------------------------------------------

def test_private_publishat_bekleyen_aday_degil(base):
    _eski(base)
    _proje(base, "01_zamanli", {"youtube_video_id": "z", "youtube_privacy": "public",
                                "youtube_uploaded_at": _yerel(2),
                                "youtube_publish_at": _utc(-5)})       # 5 sa SONRA
    _proje(base, "02_private", {"youtube_video_id": "p", "youtube_privacy": "private",
                                "youtube_uploaded_at": _yerel(2)})
    adlar = [os.path.basename(p) for p, _v in E.adaylar(_tg())]
    assert adlar == ["00_eski"]


def test_gercek_olcum_public_degilse_aday_degil_bayat_zamanlama_olcumu_haric(base):
    _eski(base)
    _proje(base, "01_studioda_gizli", {"youtube_video_id": "u", "youtube_privacy": "public",
                                       "youtube_uploaded_at": _yerel(10),
                                       "youtube_privacy_gercek": "unlisted",
                                       "youtube_privacy_gercek_at": _yerel(1)})
    # ölçüm yayından ÖNCE alındı (private idi), publishAt geçti -> gerçekte public
    _proje(base, "02_bayat_olcum", {"youtube_video_id": "b", "youtube_privacy": "public",
                                    "youtube_uploaded_at": _yerel(10),
                                    "youtube_publish_at": _utc(3),
                                    "youtube_privacy_gercek": "private",
                                    "youtube_privacy_gercek_at": _yerel(8)})
    # ölçüm yayın anından SONRA ve hâlâ private -> aday değil
    _proje(base, "03_hala_private", {"youtube_video_id": "h", "youtube_privacy": "public",
                                     "youtube_uploaded_at": _yerel(10),
                                     "youtube_publish_at": _utc(8),
                                     "youtube_privacy_gercek": "private",
                                     "youtube_privacy_gercek_at": _yerel(1)})
    adlar = [os.path.basename(p) for p, _v in E.adaylar(_tg())]
    assert adlar == ["02_bayat_olcum", "00_eski"]


def test_golden_hour_disinda_gonderi_yok_yukleyici_cagrilmaz(base, monkeypatch):
    _proje(base, "01_yeni", {"youtube_video_id": "y", "youtube_privacy": "public",
                             "youtube_uploaded_at": _yerel(5)})
    cagri = []
    for mod in ("telegram_upload", "bluesky_upload"):
        m = types.ModuleType(mod)
        m.upload_video = lambda p, _m=mod, **k: cagri.append(_m)
        monkeypatch.setitem(sys.modules, mod, m)
    monkeypatch.setattr(config, "next_golden_publish_time",
                        lambda *a, **k: datetime.now(config.TR_TZ) + timedelta(hours=3))
    s = E.backfill()                                  # dry_run DEĞİL
    assert s["durum"] == "golden-hour disinda" and s["islenen"] == []
    assert cagri == []


def test_belirsiz_isaretli_aday_degil(base):
    _eski(base)
    _proje(base, "01_yeni_belirsiz", {
        "youtube_video_id": "y", "youtube_privacy": "public",
        "youtube_uploaded_at": _yerel(5),
        ag.ISARET_ALANI: {"telegram_message_id": {"platform": "Telegram",
                                                  "istisna": "ReadTimeout"}}})
    adlar = [os.path.basename(p) for p, _v in E.adaylar(_tg())]
    assert adlar == ["00_eski"]


def test_bekletilen_yeni_sarki_gercek_kapida_duruyor_eski_gidiyor(base, monkeypatch):
    """Taklit YOK: `uyumluluk.kontrol` gerçek; bekletme 0. bölüm -> HATA."""
    monkeypatch.undo()                     # fixture'daki sahte kontrolü kaldır...
    b = str(base)
    monkeypatch.setattr(E, "BASE", b)      # ...ama ortamı yeniden kur
    monkeypatch.setattr(uyumluluk, "KOKLER", (b,))
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR", dict(TUM_BAYRAKLAR))
    sahte = os.path.join(os.path.dirname(b), "sahte_upload")
    monkeypatch.setattr(E, "UPLOAD_DIR", sahte)
    monkeypatch.setattr(E, "_UYARILANLAR", set())
    monkeypatch.setattr(notify, "uyar_bir_kez", lambda a, m: None)
    E._KAPI_ONBELLEGI.clear()
    _proje(b, "00_eski", {"youtube_video_id": "e", "youtube_privacy": "public",
                          "youtube_uploaded_at": _yerel(24 * 30)}, ses=b"ESKI" * 64)
    _proje(b, "01_yeni_bekletilen", {"youtube_video_id": "y", "youtube_privacy": "public",
                                     "youtube_uploaded_at": _yerel(5),
                                     "yayin_beklet": {"sebep": "yeniden render"}},
           ses=b"YENI" * 64)
    s = E.backfill(dry_run=True)
    assert all(x["proje"] != "01_yeni_bekletilen" for x in s["islenen"]), s
    engel = s["engellenen"]["Telegram"][0]
    assert engel["proje"] == "01_yeni_bekletilen" and "BEKLET" in engel["sebep"]
    assert ("Telegram", "00_eski") in _secilen(s)
