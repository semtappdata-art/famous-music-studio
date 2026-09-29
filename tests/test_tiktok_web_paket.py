# -*- coding: utf-8 -*-
"""TikTok WEB paket servisi (2026-09-29): 24sa içindeki plana kapak+açıklama+ayar.

Sözleşme: koşu başına en erken anlı 1 proje; proje başına günde 1
(`tiktok_web.paket_at`); yalnız golden-hour; `config.TIKTOK_WEB_PAKET` kapısı;
geçmiş-anlı kayıtlara dokunmaz. Ağ yok, gerçek klasöre yazma yok.
"""

import json
import os
import struct
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import tiktok_web as TW
import tiktok_yayin_kiti as K
import uyumluluk

SAAT = 3600


def _an(g, s, dk=0):
    from datetime import datetime
    return datetime(2026, 9, g, s, dk, tzinfo=config.TR_TZ).timestamp()


T = _an(20, 19)  # golden-hour İÇİ


def _png(yol, w=900, h=1600):
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)


def _proje(kok, ad, plan_an_ts):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    d = {"youtube_video_id": "yt-" + ad, "youtube_privacy": "public",
         "tiktok_web": {"durum": "planlandi", "planlanan_an": TW._iso(plan_an_ts),
                        "yuklendi_at": TW._iso(plan_an_ts - 30 * SAAT),
                        "studio_id": None, "aciklama_sha1": "x", "kaynak": "claude"}}
    (p / "state.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": "pop"}, ensure_ascii=False),
                                 encoding="utf-8")
    (p / "audio.wav").write_bytes(b"sahte-ses")
    (p / "output").mkdir(exist_ok=True)
    (p / "output" / "shorts_9x16.mp4").write_bytes(b"sahte-mp4")
    _png(str(p / "cover_vertical.png"))
    return str(p)


def _st(p):
    with open(os.path.join(p, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(config, "TIKTOK_WEB_PAKET", True, raising=False)
    return k


def _gonderiler():
    foto, metin = [], []
    return (foto, metin,
            lambda f, m: foto.append((f, m)) or True,
            lambda b, m: metin.append((b, m)) or True)


def test_paket_gonderir_ve_damga_yazar(kok):
    p = _proje(kok, "Aksam", T + 3 * SAAT)
    foto, metin, gf, gm = _gonderiler()
    sonuc = TW.paket_hatirlatma(simdi=T, klasorler=[p], gonder=gm, gonder_foto=gf)
    assert sonuc["gonderilen"] == "Aksam"
    assert len(foto) == 1 and len(metin) == 1
    assert "olduğu gibi yapıştır" in metin[0][1]
    assert _st(p)["tiktok_web"]["paket_at"] == "2026-09-20"


def test_paket_gunde_bir(kok):
    p = _proje(kok, "Aksam", T + 3 * SAAT)
    foto, metin, gf, gm = _gonderiler()
    TW.paket_hatirlatma(simdi=T, klasorler=[p], gonder=gm, gonder_foto=gf)
    ikinci = TW.paket_hatirlatma(simdi=T + SAAT, klasorler=[p], gonder=gm, gonder_foto=gf)
    assert len(metin) == 1
    assert "paketsiz plan yok" in ikinci["sebep"]


def test_paket_golden_disinda_yok(kok):
    p = _proje(kok, "Aksam", _an(21, 19))
    foto, metin, gf, gm = _gonderiler()
    sonuc = TW.paket_hatirlatma(simdi=_an(21, 10), klasorler=[p], gonder=gm, gonder_foto=gf)
    assert sonuc["gonderilen"] is None
    assert metin == [] and foto == []


def test_paket_uzak_plan_yok(kok):
    p = _proje(kok, "Uzak", T + 30 * SAAT)
    foto, metin, gf, gm = _gonderiler()
    sonuc = TW.paket_hatirlatma(simdi=T, klasorler=[p], gonder=gm, gonder_foto=gf)
    assert sonuc["gonderilen"] is None


def test_paket_gecmis_ana_dokunmaz(kok):
    p = _proje(kok, "Gecmis", T - 5 * SAAT)
    foto, metin, gf, gm = _gonderiler()
    sonuc = TW.paket_hatirlatma(simdi=T, klasorler=[p], gonder=gm, gonder_foto=gf)
    assert sonuc["gonderilen"] is None
    assert "paket_at" not in _st(p)["tiktok_web"]


def test_paket_config_kapali(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_WEB_PAKET", False, raising=False)
    p = _proje(kok, "Aksam", T + 3 * SAAT)
    foto, metin, gf, gm = _gonderiler()
    sonuc = TW.paket_hatirlatma(simdi=T, klasorler=[p], gonder=gm, gonder_foto=gf)
    assert sonuc["gonderilen"] is None
    assert metin == []
