# -*- coding: utf-8 -*-
"""Yayın BEKLETME kapısı: `state.json`'da `yayin_beklet` varsa proje YAYINLANMAZ.

NEDEN VAR (2026-09-12, kullanıcı kararı): `Bu Gece Kazandık`ın kapak ve video
görselleri eski; yeni formatta yeniden render edilecek. YouTube'daki iki eski
video unlisted kaldı, ama proje `pending` kuyruğunda sıradaydı: günlük pencere
dolunca saatlik koşu ESKİ `output/shorts_9x16.mp4` ile Instagram konteyneri
açacak, ardından Facebook/Telegram/Bluesky geri doldurmaları da eski görselle
gidebilecekti. Depoda projeye özel bir "yayını beklet" mekanizması YOKTU.

TASARIM — kapı TEK yerde: `uyumluluk.kontrol(..., "yukleme")`. O kapı zaten
fail-closed ve yayına çıkan yolların hepsinde çağrılıyor (auto_process,
dj_famous_process, iki geri doldurma süpürgesi, dj_clips'te iki nokta, TikTok
yayın planı). Yeni bir kapıyı yedi yere ayrı ayrı eklemek "unutulacak liste"
olurdu. `render` aşamasında HATA DEĞİL UYARI: yeniden render bekletmenin
SEBEBİ; render'ı da durdurmak düzeltmenin kendisini kilitlerdi.

İKİ EK BAĞLANTI, ikisi de kapının GÖREMEDİĞİ yol için:
  * `auto_process._bekletilenleri_ayir` — bekletilen proje `pending`den
    ÇIKARILIYOR. Çıkarılmasaydı `batch = pending[:1]` her koşuda aynı projeyi
    seçer, `process_project` kapıda `return` eder ve arkasındaki proje
    (gerçek sıra: Kader Ortakları, Bu Gece Kazandık, Sabah Senin) KALICI olarak
    tıkanırdı.
  * `_drain_golden_hour_queue` — mevcut bir Instagram konteynerini yayınlayan
    ve TikTok taslağı için "şimdi yayınla" bildirimi gönderen dallar
    `uyumluluk`'tan GEÇMİYOR; bekletilen projede ikisi de atlanıyor.

AĞA ÇIKILMIYOR: bütün state dosyaları tmp altında, yükleyiciler sahte.
"""

import ast
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap                            # noqa: E402
import uyumluluk                                     # noqa: E402

BEKLET = {"sebep": "kullanıcı: kapak ve video görselleri eski, yeni formatta "
                   "yeniden render edilecek (2026-09-12)",
          "istendi_at": "2026-09-12T23:30:00"}


def _proje(kok, ad, durum, ses=None, videolar=("shorts_9x16.mp4",)):
    d = kok / ad
    (d / "output").mkdir(parents=True, exist_ok=True)
    for v in videolar:
        (d / "output" / v).write_bytes(b"x" * 8)
    (d / "audio.wav").write_bytes(ses if ses is not None else ad.encode("utf-8") * 4)
    (d / "state.json").write_text(json.dumps(durum, ensure_ascii=False),
                                  encoding="utf-8")
    return str(d)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


def _bekletme_bulgusu(liste):
    return [x for x in liste if "beklet" in x.lower()]


# --- 1. Kapının kendisi ----------------------------------------------------

def test_bekletme_yuklemede_hata(kok):
    p = _proje(kok, "Bu Gece Kazandik", {"youtube_video_id": "v1",
                                         "youtube_privacy": "unlisted",
                                         "yayin_beklet": BEKLET})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _bekletme_bulgusu(hatalar), hatalar
    assert any("yeniden render" in h for h in hatalar), "sebep mesajda görünmeli"


def test_bekletme_renderi_durdurmuyor_ama_uyariyor(kok):
    """Yeniden render bekletmenin SEBEBİ — render'ı kilitlemek düzeltmeyi kilitler."""
    p = _proje(kok, "Bu Gece Kazandik", {"yayin_beklet": BEKLET})
    hatalar, uyarilar = uyumluluk.kontrol(p, "render")
    assert _bekletme_bulgusu(hatalar) == [], hatalar
    assert _bekletme_bulgusu(uyarilar), "render aşamasında sessiz kalmamalı"


def test_bekletme_kaldirilinca_akis_normale_donuyor(kok):
    p = _proje(kok, "Bu Gece Kazandik", {"youtube_video_id": "v1",
                                         "yayin_beklet": BEKLET})
    assert _bekletme_bulgusu(uyumluluk.kontrol(p, "yukleme")[0])
    durum = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    durum.pop("yayin_beklet")
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump(durum, f)
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert hatalar == [], hatalar


def test_bekletme_baska_projeyi_etkilemiyor(kok):
    _proje(kok, "Bu Gece Kazandik", {"yayin_beklet": BEKLET})
    diger = _proje(kok, "Sabah Senin", {})
    hatalar, uyarilar = uyumluluk.kontrol(diger, "yukleme")
    assert hatalar == [] and _bekletme_bulgusu(uyarilar) == []


@pytest.mark.parametrize("deger", ["", None, {}, False])
def test_bos_bekletme_degeri_kapiyi_kapatmiyor(kok, deger):
    """Boş/falsy değer bekletme SAYILMAZ (alanın temizlenmiş hâli)."""
    p = _proje(kok, "X", {"yayin_beklet": deger})
    assert _bekletme_bulgusu(uyumluluk.kontrol(p, "yukleme")[0]) == []


def test_bozuk_tipte_bekletme_yine_kapatiyor(kok):
    """"Okuyamıyorum" != "bekletme yok": metin olarak yazılmış bir değer de durdurur."""
    p = _proje(kok, "X", {"yayin_beklet": "evet beklet"})
    assert _bekletme_bulgusu(uyumluluk.kontrol(p, "yukleme")[0])


# --- 2. Kapıyı kullanan GERÇEK yayın yolları ------------------------------

def test_geri_doldurma_supurgeleri_bekletilen_projeyi_gondermiyor(tmp_path, monkeypatch):
    import config
    import notify
    import ek_platform_backfill as E
    import facebook_backfill as F

    base = tmp_path / "projects"
    base.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(base),))
    monkeypatch.setattr(E, "BASE", str(base))
    monkeypatch.setattr(F, "BASE", str(base))
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR",
                        {"facebook": True, "telegram": True, "bluesky": True})
    sahte = tmp_path / "sahte_upload"
    sahte.mkdir()
    for p in E.PLATFORMLAR:
        (sahte / p[5]).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(E, "UPLOAD_DIR", str(sahte))
    monkeypatch.setattr(E, "_UYARILANLAR", set())
    monkeypatch.setattr(F, "_UYARILANLAR", set())
    monkeypatch.setattr(notify, "uyar_bir_kez", lambda *a, **k: None)
    E._KAPI_ONBELLEGI.clear()
    F._KAPI_ONBELLEGI.clear()

    _proje(base, "Bu Gece Kazandik",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-08",
            "youtube_privacy": "public", "yayin_beklet": BEKLET},
           videolar=("youtube_16x9.mp4", "shorts_9x16.mp4"))
    _proje(base, "Sabah Senin",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-09",
            "youtube_privacy": "public"},
           videolar=("youtube_16x9.mp4", "shorts_9x16.mp4"))

    s = E.backfill(dry_run=True, log=lambda *a: None)
    assert "Bu Gece" not in str(s["islenen"]), s
    assert "Sabah Senin" in str(s["islenen"]), "başka proje etkilenmemeli: %r" % s
    assert "Bu Gece" in str(s.get("engellenen")), (
        "bekletilen proje engellenenlere düşmeli (sessiz değil): %r" % s)

    f = F.backfill(dry_run=True, log=lambda *a: None)
    assert not any("Bu Gece" in str(x) for x in f["islenen"]), f
    assert any("Bu Gece" in str(x) for x in f.get("engellenen", [])), f


def test_tiktok_yayin_plani_bekletilen_projede_hazir_degil(kok):
    import tiktok_publish_plan as TPP
    p = _proje(kok, "Bu Gece Kazandik", {"youtube_video_id": "v1",
                                         "youtube_privacy": "unlisted",
                                         "tiktok_publish_id": "v_inbox~x",
                                         "yayin_beklet": BEKLET})
    plan = TPP.build_plan(p)
    assert plan["hazir"] is False
    assert "beklet" in (plan["engel"] or "").lower()


# NOT — `process_project` burada BİLEREK uçtan uca çağrılmıyor: kapı açık
# kalırsa (kırmızı aşamada tam olarak bu durum) fonksiyon GERÇEK
# `upload/token.json` ile Shorts/TikTok/Instagram yüklemesine girer. Ana hattın
# kapıyı çağırdığı ve HATA'da döndüğü `tests/test_uyumluluk_fail_closed.py`'de
# zaten kilitli; buradaki yeni şey kapının bekletmeye HATA demesi (bölüm 1).
@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    import socket

    def _patla(*a, **k):
        raise AssertionError("test ağa çıkmaya çalıştı")
    monkeypatch.setattr(socket.socket, "connect", _patla)
    monkeypatch.setattr(socket, "create_connection", _patla)


# --- 3. pending sırası: bekletilen proje arkasındakini TIKAMAMALI ----------

def test_bekletilen_proje_pendingden_ayrilir(tmp_path):
    ko = _proje(tmp_path, "Kader Ortaklari", {})
    bgk = _proje(tmp_path, "Bu Gece Kazandik", {"yayin_beklet": BEKLET})
    ss = _proje(tmp_path, "Sabah Senin", {})
    kalan, bekletilen = ap._bekletilenleri_ayir([ko, bgk, ss])
    assert kalan == [ko, ss]
    assert bekletilen == [bgk]


def test_bekletilen_proje_basa_gelince_siradaki_secilir(tmp_path, monkeypatch):
    """Kader Ortakları bitti: sırada Bu Gece Kazandık var ama batch Sabah Senin olmalı."""
    bgk = _proje(tmp_path, "Bu Gece Kazandik", {"yayin_beklet": BEKLET})
    ss = _proje(tmp_path, "Sabah Senin", {})
    kalan, _ = ap._bekletilenleri_ayir([bgk, ss])
    assert kalan[:1] == [ss], "batch = pending[:1] bekletilen projeyi seçmemeli"


def test_bozuk_state_bekletme_sayilmaz_ama_pendingde_kalir(tmp_path):
    """Ayırıcı kapının YERİNE geçmez: okunamayan state'i sessizce düşürmez,
    `process_project`'e bırakır — orada `uyumluluk` HATA verip atlar."""
    d = tmp_path / "Bozuk"
    d.mkdir()
    (d / "state.json").write_text('{"a":', encoding="utf-8")
    kalan, bekletilen = ap._bekletilenleri_ayir([str(d)])
    assert kalan == [str(d)] and bekletilen == []


def _main_cagri_satirlari(ad):
    kaynak = open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read()
    agac = ast.parse(kaynak)
    main = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    return [n.lineno for n in ast.walk(main)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == ad]


def test_main_ayiriciyi_kademelemeden_ONCE_cagiriyor():
    """Bağlantı muhafızı: ayırıcı yazılmış ama main() onu çağırmıyorsa kapı ölüdür."""
    ayir = _main_cagri_satirlari("_bekletilenleri_ayir")
    pace = _main_cagri_satirlari("_auto_pace_count")
    assert ayir, "main() _bekletilenleri_ayir'i çağırmıyor"
    assert pace and min(ayir) < min(pace)


# --- 4. golden-hour kuyruğu: kapıdan geçmeyen iki yayın dalı ---------------

def test_drain_bekletilen_projede_instagram_ve_tiktok_dallarini_atliyor(tmp_path, monkeypatch):
    bgk = _proje(tmp_path, "Bu Gece Kazandik",
                 {"instagram_creation_id": "c1", "tiktok_publish_id": "t1",
                  "yayin_beklet": BEKLET})
    diger = _proje(tmp_path, "Sabah Senin",
                   {"instagram_creation_id": "c2", "tiktok_publish_id": "t2"})
    ig, tt = [], []
    monkeypatch.setattr(ap, "_check_instagram_pending", ig.append)
    monkeypatch.setattr(ap, "_check_tiktok_notification", lambda p, s: tt.append(p))
    monkeypatch.setattr(ap, "_check_youtube_captions", lambda p, s: False)
    monkeypatch.setattr(ap, "log", lambda *a: None)
    ap._drain_golden_hour_queue([bgk, diger])
    assert ig == [diger] and tt == [diger]
