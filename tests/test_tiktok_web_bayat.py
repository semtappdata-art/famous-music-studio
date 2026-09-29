# -*- coding: utf-8 -*-
"""TikTok WEB bayat kuralı (2026-09-29): +48sa doğrulanmayan plan rozet + yaşlı hatırlatma.

Sözleşme: `durum` satırı `gecikme_sn`/`bayat` taşır; `rapor_satirlari` bayata
"(N gündür doğrulanmadı)" yazar; `kontrol_hatirlatma` yaş + kapanış komutlarını
(`yayınladım X` / `iptal X`) mesaja koyar. Günlük tavan, golden-hour kapısı ve
config şalteri aynen korunur. Ağ yok, gerçek klasöre/deftere yazma yok.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import tiktok_web as TW

SAAT = 3600


def _an(g, s, dk=0):
    from datetime import datetime
    return datetime(2026, 9, g, s, dk, tzinfo=config.TR_TZ).timestamp()


# 2026-09-20 19:00 TR — golden-hour İÇİ.
T = _an(20, 19)


def _proje(kok, ad, plan_an_ts):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    d = {"youtube_video_id": "yt-" + ad,
         "tiktok_web": {"durum": "planlandi", "planlanan_an": TW._iso(plan_an_ts),
                        "yuklendi_at": TW._iso(plan_an_ts - 30 * SAAT),
                        "studio_id": None, "aciklama_sha1": "x", "kaynak": "claude"}}
    (p / "state.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return str(p)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    import uyumluluk
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(TW, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    monkeypatch.setattr(config, "TIKTOK_WEB_KONTROL_HATIRLATMA", True, raising=False)
    monkeypatch.setattr(config, "TIKTOK_WEB_BAYAT_SAAT", 48, raising=False)
    return k


def test_bayat_esigi_48sa(kok):
    genc = _proje(kok, "Genc", T - 47 * SAAT)
    yasli = _proje(kok, "Yasli", T - 49 * SAAT)
    d = TW.durum(T, [genc, yasli])
    sat = {s["proje"]: s for s in d["planli"]}
    assert sat["Genc"]["dogrulanmadi"] is True
    assert sat["Genc"]["bayat"] is False
    assert sat["Yasli"]["bayat"] is True
    assert sat["Yasli"]["gecikme_sn"] >= 49 * SAAT


def test_rapor_rozeti(kok):
    _proje(kok, "Genc", T - 2 * SAAT)
    _proje(kok, "Yasli", T - 5 * 24 * SAAT)
    satirlar = TW.rapor_satirlari(T, [str(kok / "Genc"), str(kok / "Yasli")])
    genc = next(s for s in satirlar if "Genc" in s)
    yasli = next(s for s in satirlar if "Yasli" in s)
    assert "(an geçti, doğrulanmadı)" in genc
    assert "(5 gündür doğrulanmadı)" in yasli


def test_hatirlatma_yasli_mesaj(kok):
    p = _proje(kok, "Yasli", T - 3 * 24 * SAAT)
    giden = []
    sonuc = TW.kontrol_hatirlatma(simdi=T, klasorler=[p],
                                  gonder=lambda b, m: giden.append((b, m)) or True)
    assert sonuc["gonderilen"] == "Yasli"
    baslik, mesaj = giden[0]
    assert "3 gündür" in mesaj
    assert "yayınladım Yasli" in mesaj
    assert "iptal Yasli" in mesaj


def test_hatirlatma_genc_rozetsiz(kok):
    p = _proje(kok, "Genc", T - 2 * SAAT)
    giden = []
    TW.kontrol_hatirlatma(simdi=T, klasorler=[p],
                          gonder=lambda b, m: giden.append((b, m)) or True)
    assert "gündür" not in giden[0][1]
    assert "yayınladım Genc" in giden[0][1]


def test_hatirlatma_gunluk_tavan(kok):
    p = _proje(kok, "Yasli", T - 3 * 24 * SAAT)
    cagrilar = []
    TW.kontrol_hatirlatma(simdi=T, klasorler=[p],
                          gonder=lambda b, m: cagrilar.append(1) or True)
    ikinci = TW.kontrol_hatirlatma(simdi=T + SAAT, klasorler=[p],
                                   gonder=lambda b, m: cagrilar.append(1) or True)
    assert len(cagrilar) == 1
    assert ikinci["sebep"] == "bugün zaten hatırlatıldı"


def test_config_esigi_override(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_WEB_BAYAT_SAAT", 72, raising=False)
    p = _proje(kok, "Yasli", T - 49 * SAAT)
    d = TW.durum(T, [p])
    assert d["planli"][0]["bayat"] is False


def test_bayat_rozet_gunluk_rapora_akar(kok):
    import weekly_report as WR
    _proje(kok, "Yasli", T - 5 * 24 * SAAT)
    bolum = WR._tiktok_web_bolumu(T, [str(kok / "Yasli")])
    assert "5 gündür doğrulanmadı" in bolum
