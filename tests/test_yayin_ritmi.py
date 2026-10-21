# -*- coding: utf-8 -*-
"""yayin_ritmi.py — onaylanan karar 4 (2026-09-13): set/şarkı 48 sa, Shorts T0+24 sa,
şarkı başına günde en fazla 2 platform; ve 5 Eylül deseni fikstürü.

5 EYLÜL DESENİ (ozgunluk_plani.md §1.4, gerçek state damgalarından): 74 dakikada 6 uzun
video (02:12-03:26, publishAt 04:30-06:30 + 09:00), Shorts'lar aynı anlarda, TikTok'ta
03:29-03:34 arası 5 dakikada 7 gönderi, 13:12-13:21 arası 9 dakikada 5 Instagram. Bu
dosya o olay dizisini kurallara TEK TEK sunar ve desenin OLUŞAMADIĞINI gösterir.

Ağa çıkmaz, üretim dosyalarına yazmaz.
"""

import json
import os
import sys
from datetime import datetime

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import config
import uyumluluk
import yayin_ritmi as YR

SAAT = 3600.0


def _an(g, s, dk=0, ay=9):
    return datetime(2026, ay, g, s, dk, tzinfo=config.TR_TZ).timestamp()


def _iso(ts):
    return datetime.fromtimestamp(ts, config.TR_TZ).isoformat()


@pytest.fixture
def ayar(monkeypatch):
    monkeypatch.setattr(config, "YAYIN_RITMI_SET_SARKI_ARA_SAAT", 48, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKME_SAAT", 24, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", True, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 2, raising=False)
    monkeypatch.setattr(config, "YAYIN_RITMI_PLATFORM_MIN_ARA_SAAT", 6, raising=False)
    monkeypatch.setattr(config, "TIKTOK_KIT_ARALIK_SAAT", 36)


def _proje(kok, ad, **st):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return str(p)


# --- damga okuma -------------------------------------------------------------

def test_ts_oku_bicimleri():
    assert YR.ts_oku("2026-09-05T04:30:00Z") == datetime(2026, 9, 5, 7, 30,
                                                          tzinfo=config.TR_TZ).timestamp()
    assert YR.ts_oku("2026-09-05T07:30:00+03:00") == _an(5, 7, 30)
    assert YR.ts_oku("2026-09-05T07:30:00") is not None          # yerel, dilimsiz
    for bozuk in (None, "", "dün", 5):
        assert YR.ts_oku(bozuk) is None


def test_uzun_yayin_ani_publish_at_yuklemeden_gecse_onu_alir():
    st = {"youtube_video_id": "v", "youtube_uploaded_at": "2026-09-05T02:12:00",
          "youtube_publish_at": "2026-09-05T01:30:00Z"}              # 04:30 TR
    assert YR.uzun_yayin_ani(st) == _an(5, 4, 30)
    assert YR.uzun_yayin_ani({"youtube_uploaded_at": "2026-09-05T02:12:00"}) is None


# --- R3b: şarkı başına günde en fazla 2 platform ------------------------------

def test_platform_gun_tavani_uzun_ve_shorts_ayni_gun_ucuncuyu_durdurur(ayar):
    st = {"youtube_video_id": "v", "youtube_publish_at": _iso(_an(13, 12)),
          "youtube_shorts_video_id": "s", "youtube_shorts_publish_at": _iso(_an(13, 12))}
    izin, sebep = YR.platform_gun_izni(st, "instagram", _an(13, 18))
    assert izin is False and "2 platformda" in sebep and "ritim" in sebep
    assert YR.platform_gun_izni(st, "instagram", _an(14, 12))[0] is True     # ertesi gün


def test_ayni_platformun_ikinci_kaydi_yeni_platform_sayilmaz(ayar):
    st = {"youtube_video_id": "v", "youtube_publish_at": _iso(_an(13, 12)),
          "telegram_uploaded_at": "2026-09-13T12:30:00"}
    assert YR.platform_gun_izni(st, "telegram", _an(13, 19))[0] is True
    assert YR.platform_gun_izni(st, "bluesky", _an(13, 19))[0] is False


def test_tiktok_web_plani_ve_facebook_zamanlamasi_sayilir_api_tespit_ani_sayilmaz(ayar):
    st = {"tiktok_web": {"durum": "planlandi", "planlanan_an": _iso(_an(15, 18))},
          "facebook_reels_id": "f", "facebook_scheduled_for": _iso(_an(15, 12))}
    assert YR.gun_platformlari(st, _an(15, 20)) == {"tiktok", "facebook"}
    st2 = {"tiktok_published_at": "2026-09-13T02:23:10",
           "tiktok_published_kaynak": "TikTok API PUBLISH_COMPLETE (otomatik)"}
    assert YR.gun_platformlari(st2, _an(13, 12)) == set()


def test_tavan_sifir_kurali_kapatir(ayar, monkeypatch):
    monkeypatch.setattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 0)
    st = {"youtube_video_id": "v", "youtube_publish_at": _iso(_an(13, 12)),
          "instagram_media_id": "i", "instagram_uploaded_at": "2026-09-13T12:05:00"}
    assert YR.platform_gun_izni(st, "facebook", _an(13, 13))[0] is True


# --- R3a: Shorts uzun formattan 24 saat sonra ---------------------------------

def test_shorts_24_saat_dolmadan_hazir_degil(ayar):
    st = {"youtube_video_id": "v", "youtube_uploaded_at": "2026-09-13T10:05:00",
          "youtube_publish_at": _iso(_an(13, 12))}
    hazir, kalan, sebep = YR.shorts_zamani(st, simdi=_an(14, 11))
    assert hazir is False and 0 < kalan <= SAAT and "24" in sebep
    assert YR.shorts_zamani(st, simdi=_an(14, 12))[0] is True


def test_shorts_uzun_format_yoksa_ya_da_ani_bilinmiyorsa_bekler(ayar):
    assert YR.shorts_zamani({}, simdi=_an(14, 12))[0] is False
    assert YR.shorts_zamani({"youtube_video_id": "v"}, simdi=_an(14, 12))[0] is False


def test_shorts_salter_kapaliyken_eski_akis(ayar, monkeypatch):
    monkeypatch.setattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", False)
    st = {"youtube_video_id": "v", "youtube_uploaded_at": "2026-09-13T10:05:00"}
    assert YR.shorts_zamani(st, simdi=_an(13, 10, 6))[0] is True


# --- R1: set/derleme ↔ şarkı ortak 48 saat ------------------------------------

def test_set_sarkidan_48_saat_gecmeden_yayinlanmaz(tmp_path, ayar):
    sarki = _proje(tmp_path / "projects", "Sarki", youtube_video_id="v",
                   youtube_uploaded_at="2026-09-13T10:05:00",
                   youtube_publish_at=_iso(_an(13, 12)))
    dj = _proje(tmp_path / "dj_sets", "Set")
    izin, kalan, sebep = YR.kanal_tabani(dj, simdi=_an(14, 18), klasorler=[sarki, dj])
    assert izin is False and "48" in sebep and "Sarki" in sebep
    assert kalan == pytest.approx(_an(13, 12) + 48 * SAAT - _an(14, 18))
    assert YR.kanal_tabani(dj, simdi=_an(15, 12, 1), klasorler=[sarki, dj])[0] is True


def test_sarki_tarafi_yalniz_seti_sayar_sarki_sarki_52_saatte_kalir(tmp_path, ayar):
    s1 = _proje(tmp_path / "projects", "S1", youtube_video_id="v",
                youtube_uploaded_at="2026-09-13T10:00:00")
    s2 = _proje(tmp_path / "projects", "S2")
    assert YR.kanal_tabani(s2, simdi=_an(13, 12), klasorler=[s1, s2])[0] is True
    derleme = _proje(tmp_path / "derlemeler", "Vol", youtube_video_id="d",
                     youtube_uploaded_at="2026-09-13T10:00:00")
    izin, _k, sebep = YR.kanal_tabani(s2, simdi=_an(13, 12), klasorler=[s1, s2, derleme])
    assert izin is False and "Vol" in sebep


def test_gelecekte_zamanlanmis_sarki_da_seti_bekletir(tmp_path, ayar):
    sarki = _proje(tmp_path / "projects", "Sarki", youtube_video_id="v",
                   youtube_uploaded_at="2026-09-13T10:05:00",
                   youtube_publish_at=_iso(_an(15, 18)))
    dj = _proje(tmp_path / "dj_sets", "Set")
    izin, kalan, _ = YR.kanal_tabani(dj, simdi=_an(13, 18), klasorler=[sarki, dj])
    assert izin is False and kalan > 48 * SAAT


def test_varsayilan_klasorler_uyumluluk_koklerinden(tmp_path, ayar, monkeypatch):
    k1, k2 = tmp_path / "projects", tmp_path / "dj_sets"
    _proje(k1, "Sarki", youtube_video_id="v", youtube_uploaded_at="2026-09-13T10:05:00")
    dj = _proje(k2, "Set")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k1), str(k2)))
    assert YR.kanal_tabani(dj, simdi=_an(13, 18))[0] is False


# --- 5 EYLÜL FİKSTÜRÜ -----------------------------------------------------------

def _bes_eylul():
    """Gerçek desenin olay dizisi: (ts, proje, platform, tür)."""
    uzun = [("Sokaklar", 2, 12, 4, 30), ("Son Kez", 2, 30, 5, 0), ("Sabaha", 2, 45, 5, 30),
            ("Bir Bahar", 3, 0, 6, 0), ("Kumdan", 3, 15, 6, 30), ("Just Relax", 3, 26, 9, 0)]
    olaylar = []
    for ad, ys, ydk, ps, pdk in uzun:
        tur = "set" if ad == "Just Relax" else "sarki"
        olaylar.append(YR.olay(_an(5, ps, pdk), ad, "youtube", tur))          # publishAt
        olaylar.append(YR.olay(_an(5, ps, pdk), ad, "youtube_shorts", tur))   # aynı an
    tiktok = ["Sokaklar", "Son Kez", "Sabaha", "Bir Bahar", "Kumdan", "Yeniden", "Kalbim"]
    for i, ad in enumerate(tiktok):                                           # 03:29-03:34
        olaylar.append(YR.olay(_an(5, 3, 29) + i * 50, ad, "tiktok"))
    for i, ad in enumerate(["Kumdan", "Bir Bahar", "Sabaha", "Yeniden", "Sokaklar"]):
        olaylar.append(YR.olay(_an(5, 13, 12) + i * 135, ad, "instagram"))     # 13:12-13:21
    return sorted(olaylar, key=lambda o: o["ts"])


def test_bes_eylul_deseni_bugunku_olculerle_ihlal_uretir(ayar):
    ihlal = YR.ihlaller(_bes_eylul())
    kurallar = {i["kural"] for i in ihlal}
    assert {"R1", "R2", "R3a", "R3b"} <= kurallar
    assert sum(1 for i in ihlal if i["kural"] == "R1") >= 5       # 6 uzun videonun 5'i


def test_bes_eylul_deseni_yeni_kurallarla_OLUSAMAZ(ayar):
    kabul = []
    reddedilen = []
    for aday in _bes_eylul():
        sebep = YR.aday_ihlalleri(kabul, aday)
        (reddedilen if sebep else kabul).append((aday, sebep))
        if not sebep:
            kabul[-1] = aday
    uzun = [o for o in kabul if o["platform"] == "youtube"]
    assert len(uzun) == 1, "74 dakikada 6 uzun video → yalnız ilki"
    assert [o for o in kabul if o["platform"] == "youtube_shorts"] == [], \
        "Shorts aynı gün (T0+24 sa dolmadan) çıkamaz"
    assert len([o for o in kabul if o["platform"] == "tiktok"]) <= 1, \
        "5 dakikada 7 TikTok → en fazla 1"
    assert len([o for o in kabul if o["platform"] == "instagram"]) <= 1
    gunluk = {}
    for o in kabul:
        gunluk.setdefault(o["proje"], set()).add(o["platform"])
    assert all(len(v) <= 2 for v in gunluk.values())
    # Kabul edilen dizide R1/R3a/R3b ihlali SIFIR.
    assert [i for i in YR.ihlaller(kabul) if i["kural"] in ("R1", "R3a", "R3b")] == []
    assert len(kabul) <= 3 < len(_bes_eylul())


def test_ertesi_gun_shorts_ve_platformlar_acilir(ayar):
    kabul = [YR.olay(_an(5, 12), "Sokaklar", "youtube"),
             YR.olay(_an(5, 12, 5), "Sokaklar", "instagram")]
    assert YR.aday_ihlalleri(kabul, YR.olay(_an(5, 18), "Sokaklar", "youtube_shorts"))
    assert YR.aday_ihlalleri(kabul, YR.olay(_an(6, 12), "Sokaklar", "youtube_shorts")) == []
    assert YR.aday_ihlalleri(kabul, YR.olay(_an(5, 19), "Sokaklar", "facebook"))
    assert YR.aday_ihlalleri(kabul, YR.olay(_an(6, 19), "Sokaklar", "facebook")) == []


def test_uzun_format_olmadan_diger_platform_kabul_edilmez(ayar):
    assert YR.aday_ihlalleri([], YR.olay(_an(5, 13), "Yeni", "instagram"))


def test_olaylar_diskten_okur_ve_cli_json(tmp_path, ayar, capsysbinary):
    kok = tmp_path / "projects"
    _proje(kok, "A", youtube_video_id="a", youtube_uploaded_at="2026-09-05T04:30:00",
           youtube_shorts_video_id="as", youtube_shorts_uploaded_at="2026-09-05T04:30:00",
           instagram_media_id="i", instagram_uploaded_at="2026-09-05T13:12:00")
    liste = YR.olaylar([str(kok / "A")])
    assert [o["platform"] for o in liste] == ["youtube", "youtube_shorts", "instagram"]
    assert {i["kural"] for i in YR.ihlaller(liste)} == {"R3a", "R3b"}
