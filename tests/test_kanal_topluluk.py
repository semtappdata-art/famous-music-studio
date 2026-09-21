# -*- coding: utf-8 -*-
"""turev_takvimi — kanal geneli YouTube TOPLULUK yüzeyi (özgünlük planı Aşama 1, iş #4).

Söz Defteri #1 ve Kulis #1'in TikTok sürümlerinin YouTube Topluluk karşılığı. Kurallar:
elle (Topluluk gönderisi için API yok), insan emeği, haftalık insan emeği tavanı ve "aynı gün
ikinci insan emeği" kuralı DIŞI (`tavan_disi`), bağlı TikTok kaydının ÇÖZÜLMÜŞ anından en az
`config.TUREV_TOPLULUK_TIKTOK_SONRASI_SAAT` (24) saat sonra; golden-hour ve yeni yayın bandı
aynen; TikTok şarkı kesiti aynı gün kuralı uygulanmaz (ayrı yüzey). Ağa ÇIKMAZ, gerçek dosyalara YAZMAZ (her şey tmp_path).
"""

import datetime
import json
import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import uyumluluk                                          # noqa: E402
import turev_takvimi as TT                                # noqa: E402

TR = datetime.timezone(datetime.timedelta(hours=3))
SIMDI = None


def T(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).timestamp()


def iso(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).isoformat()


SIMDI = T(2026, 9, 13, 8)
SS = {"youtube_video_id": "Ozn9", "youtube_uploaded_at": "2026-09-13T02:22:17",
      "youtube_publish_at": "2026-09-01T09:00:00Z"}


@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    import socket
    import notify

    def _yasak(*a, **k):
        raise AssertionError("topluluk takvimi testi ağa/bildirime çıktı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)
    for ad in ("send", "send_text", "send_photo"):
        monkeypatch.setattr(notify, ad, _yasak)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    for ad in ("projects", "dj_sets"):
        (tmp_path / ad).mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER",
                        (str(tmp_path / "projects"), str(tmp_path / "dj_sets")))
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    monkeypatch.setattr(TT, "DJ_KILIT_YOLU", str(tmp_path / "yok.lock"))
    monkeypatch.setattr(TT, "KANAL_TAKVIMI_YOLU", str(tmp_path / "kanal_takvimi.json"))
    return tmp_path


def _proje(kok, ad, st):
    p = kok / "projects" / ad
    p.mkdir(parents=True)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": "pop"}), encoding="utf-8")
    (p / "audio.wav").write_bytes(b"x")
    return str(p)


def _tiktok(tur, an, baslik="Söz Defteri #1"):
    return TT.kanal_plan(tur, an, baslik, simdi=SIMDI, uygula=True)


def _topluluk(tur, an, kaynak_id, baslik="Topluluk", uygula=True):
    return TT.kanal_plan(tur, an, baslik, simdi=SIMDI, uygula=uygula, kaynak_id=kaynak_id)


def _kanal(tk, kid):
    return next(o for o in tk["kanal_gonderileri"] if o["id"] == kid)


SD = "KNL-2026-09-15-soz_defteri"
KL = "KNL-2026-09-19-kulis"


def test_tur_tanimlari_youtube_topluluk_yuzeyi():
    for tur, kaynak in (("soz_defteri_topluluk", "soz_defteri"), ("kulis_topluluk", "kulis")):
        tanim = TT.KANAL_TUR_TANIMLARI[tur]
        assert tanim["platform"] == "youtube_topluluk"
        assert tanim["kaynak_tur"] == kaynak and tanim["tavan_disi"] is True
    # mevcut TikTok türleri değişmedi
    assert TT.KANAL_TUR_TANIMLARI["soz_defteri"]["platform"] == "tiktok"
    assert not TT.KANAL_TUR_TANIMLARI["kulis"].get("tavan_disi")


def test_topluluk_tiktoktan_en_az_24_saat_sonra(kok):
    _tiktok("soz_defteri", iso(2026, 9, 15, 20, 30))
    with pytest.raises(TT.TurevHatasi, match="24"):
        _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 12), SD)
    r = _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD,
                  baslik="Söz Defteri #1 — Sabah Senin (Topluluk)")
    k = r["kayit"]
    assert r["yazildi"] and k["id"] == "KNL-2026-09-16-soz_defteri_topluluk"
    assert k["platform"] == "youtube_topluluk" and k["kaynak_id"] == SD
    assert k["tavan_disi"] is True and k["insan_emegi"] and k["elle"]
    assert k["tempo_sayilir"] is False and k["sarki_kesiti_tavanina_sayilir"] is False
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[])
    o = _kanal(tk, k["id"])
    assert o["an"] == iso(2026, 9, 16, 20, 30) and o["kaynak_id"] == SD and o["tavan_disi"]
    assert o["platform"] == "youtube_topluluk"


def test_kaynak_zorunlu_ve_turu_uymali(kok):
    _tiktok("kulis", iso(2026, 9, 19, 13), baslik="Kulis #1")
    with pytest.raises(TT.TurevHatasi, match="kaynak"):
        _topluluk("kulis_topluluk", iso(2026, 9, 20, 13), None)
    with pytest.raises(TT.TurevHatasi, match="kaynak"):
        _topluluk("kulis_topluluk", iso(2026, 9, 20, 13), "KNL-yok")
    with pytest.raises(TT.TurevHatasi, match="kaynak"):
        _topluluk("soz_defteri_topluluk", iso(2026, 9, 20, 13), KL)   # tür uymuyor
    with pytest.raises(TT.TurevHatasi, match="kaynak"):
        TT.kanal_plan("kulis", iso(2026, 9, 22, 13), "x", simdi=SIMDI, kaynak_id=KL)


def test_tiktok_kaydi_kayarsa_topluluk_da_kayar(kok):
    b = _proje(kok, "Beni Birakma", dict(SS, tiktok_web={
        "durum": "planlandi", "planlanan_an": iso(2026, 9, 15, 12, 15)}))
    _tiktok("soz_defteri", iso(2026, 9, 15, 20, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD)
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[b])
    tiktok_an = datetime.datetime.fromisoformat(_kanal(tk, SD)["an"])
    assert tiktok_an == datetime.datetime(2026, 9, 16, 12, tzinfo=TR)   # kesit yüzünden kaydı
    top = _kanal(tk, "KNL-2026-09-16-soz_defteri_topluluk")
    assert top["an"] == iso(2026, 9, 17, 12)                          # TikTok + 24 sa
    assert datetime.datetime.fromisoformat(top["an"]) - tiktok_an >= datetime.timedelta(hours=24)


def test_tiktok_sarki_kesiti_gunu_toplulugu_engellemez(kok):
    """Canlı takvim vakası (2026-09-13): 17 ve 18 Eyl TikTok kesiti günleri Topluluk'u
    düşürüyordu. Kesit kuralı TikTok yüzeyi içindir; Topluluk yine TikTok + 24 sa'e yerleşir."""
    k1 = _proje(kok, "Kesit Bir", dict(SS, tiktok_web={
        "durum": "planlandi", "planlanan_an": iso(2026, 9, 17, 18)}))
    _tiktok("soz_defteri", iso(2026, 9, 16, 12, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 17, 12, 30), SD.replace("15", "16"))
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[k1])
    assert _kanal(tk, "KNL-2026-09-17-soz_defteri_topluluk")["an"] == iso(2026, 9, 17, 12, 30)


def test_kaynak_duserse_topluluk_duser(kok):
    _tiktok("soz_defteri", iso(2026, 9, 15, 20, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD)
    TT.iptal(SD, sebep="test")
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[])
    assert all(o["id"] != "KNL-2026-09-16-soz_defteri_topluluk" for o in tk["kanal_gonderileri"])
    d = next(o for o in tk["dusenler"] if o["id"] == "KNL-2026-09-16-soz_defteri_topluluk")
    assert d["etkin"] == "kaynak_dustu"


def test_tavan_disi_haftada_iki_tiktok_iki_topluluk(kok):
    _tiktok("soz_defteri", iso(2026, 9, 15, 20, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD)
    # Topluluk kaydıyla AYNI GÜN TikTok insan emeği gönderisi hâlâ serbest
    _tiktok("kulis", iso(2026, 9, 16, 12, 30), baslik="Kulis #1")
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[])
    assert _kanal(tk, "KNL-2026-09-16-kulis")["an"] == iso(2026, 9, 16, 12, 30)
    TT.iptal("KNL-2026-09-16-kulis", sebep="test")
    _tiktok("kulis", iso(2026, 9, 19, 13), baslik="Kulis #1")
    _topluluk("kulis_topluluk", iso(2026, 9, 20, 13), KL)
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[])
    ids = sorted(o["id"] for o in tk["kanal_gonderileri"])
    assert ids == sorted([SD, KL, "KNL-2026-09-16-soz_defteri_topluluk",
                          "KNL-2026-09-20-kulis_topluluk"])
    # TikTok insan emeği tavanı yine 2: üçüncü TikTok reddedilir
    with pytest.raises(TT.TurevHatasi, match="haftalık"):
        _tiktok("soz_defteri", iso(2026, 9, 17, 19))


def test_gecmis_ve_golden_hour_disi_red(kok):
    _tiktok("soz_defteri", iso(2026, 9, 15, 20, 30))
    with pytest.raises(TT.TurevHatasi, match="golden"):
        _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 23), SD)
    with pytest.raises(TT.TurevHatasi, match="geçmişte"):
        TT.kanal_plan("soz_defteri_topluluk", iso(2026, 9, 12, 20), "x", simdi=SIMDI,
                      uygula=True, kaynak_id=SD)


def test_topluluk_yeni_yayin_bandina_uyar(kok):
    y = _proje(kok, "Yeni Sarki", {"youtube_video_id": "y",
                                   "youtube_publish_at": "2026-09-16T17:00:00Z"})  # 16 20:00
    _tiktok("soz_defteri", iso(2026, 9, 15, 12, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD)
    tk = TT.takvim(gun=8, simdi=SIMDI, klasorler=[y])
    # 17 12:00 (16 sa) ve 17 18:00 (22 sa) bandın içinde -> ilk uygun pencere 18 12:00
    assert _kanal(tk, "KNL-2026-09-16-soz_defteri_topluluk")["an"] == iso(2026, 9, 18, 12)


def test_gercek_kanal_dosyasina_testte_topluluk_yazilmaz(kok, monkeypatch):
    monkeypatch.setattr(TT, "KANAL_TAKVIMI_YOLU", TT.GERCEK_KANAL_TAKVIMI_YOLU)
    once = open(TT.GERCEK_KANAL_TAKVIMI_YOLU, "rb").read()
    with pytest.raises(TT.TurevHatasi):
        _topluluk("soz_defteri_topluluk", iso(2026, 12, 16, 20, 30), SD)
    assert open(TT.GERCEK_KANAL_TAKVIMI_YOLU, "rb").read() == once


def test_hatirlatma_ve_tiktok_web_topluluk_kaydini_gormez(kok, monkeypatch):
    import config
    import tiktok_web
    monkeypatch.setattr(config, "TUREV_HATIRLATMA_AKTIF", True)
    _tiktok("soz_defteri", iso(2026, 9, 15, 12, 30))
    _topluluk("soz_defteri_topluluk", iso(2026, 9, 16, 20, 30), SD)
    giden = []
    r = TT.hatirlatma_sirasi(lambda *a: None, simdi=T(2026, 9, 16, 20, 45), klasorler=[],
                             gonder=lambda m: giden.append(m) or True)
    assert giden == [] and r["gonderilen"] is None
    baglam = tiktok_web._baglam(SIMDI, klasorler=[])
    assert all(o.get("kok") != "kanal" for o in baglam["turev"])
    satirlar = TT.bugun_yarin_satirlari(simdi=T(2026, 9, 16, 10), klasorler=[])
    assert any("youtube_topluluk" in s for s in satirlar)


def test_cli_kaynak_id_kuru_uygula_takvim_json(kok):
    yol = str(kok / "cli_kanal.json")
    env = dict(os.environ, PYTHONIOENCODING="cp1254")
    betik = os.path.join(_REPO, "turev_takvimi.py")
    simdi = ["--kanal-yolu", yol, "--simdi", "2026-09-13T08:00:00+03:00"]
    p = subprocess.run([sys.executable, betik, "plan", "--kanal", "soz_defteri", "--hedef",
                        "2026-09-15T20:30:00+03:00", "--baslik", "Söz Defteri #1", "--uygula"]
                       + simdi, capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    top = ["plan", "--kanal", "soz_defteri_topluluk", "--hedef", "2026-09-16T20:30:00+03:00",
           "--baslik", "Söz Defteri #1 — Topluluk", "--kaynak-id", SD]
    p = subprocess.run([sys.executable, betik] + top + simdi, capture_output=True, env=env,
                       timeout=120)
    assert p.returncode == 0 and "KURU" in p.stdout.decode("utf-8")
    p = subprocess.run([sys.executable, betik] + top + ["--uygula"] + simdi,
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stdout.decode("utf-8", "replace")
    p = subprocess.run([sys.executable, betik, "takvim", "--gun", "8", "--json",
                        "--kok", str(kok / "projects")] + simdi,
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    veri = json.loads(p.stdout.decode("utf-8"))
    top_o = next(o for o in veri["kanal_gonderileri"] if o["tur"] == "soz_defteri_topluluk")
    assert top_o["kaynak_id"] == SD and top_o["an"] == "2026-09-16T20:30:00+03:00"
    assert veri["kurallar"]["topluluk_tiktok_sonrasi_saat"] == 24
