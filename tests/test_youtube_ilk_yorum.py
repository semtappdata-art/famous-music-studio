# -*- coding: utf-8 -*-
"""YouTube ilk yorum (social_text.build_ilk_yorum + youtube_ilk_yorum.gonder).

Kilitlenen davranış:
- Metin iki satır: bölüm sorusu + abone çağrısı; dil ve determinizm korunur.
- Video başına TEK gönderim (bayrak ikinci kilit); kota yoksa DOKUNULMAZ.
- API patlarsa istisna yukarı çıkar (kanca yakalar, yükleme durmaz).
"""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD = os.path.join(REPO, "upload")
for _yol in (UPLOAD, REPO):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

from social_text import build_ilk_yorum
import youtube_ilk_yorum


def test_metin_iki_satir_tr():
    m = build_ilk_yorum("Gece Sürüşü", "tr")
    satirlar = m.split("\n")
    assert len(satirlar) == 2
    assert "Abone ol" in satirlar[1]
    assert m == build_ilk_yorum("Gece Sürüşü", "tr")  # deterministik


def test_metin_en():
    m = build_ilk_yorum("Night Drive", "en")
    satirlar = m.split("\n")
    assert len(satirlar) == 2
    assert "Subscribe" in satirlar[1]


def test_farkli_baslik_farkli_soru_olabilir():
    # Deterministik ama tekdüze değil: havuzda 3 soru var, 6 başlık hepsini
    # aynı indexe düşürmemeli (tuzak: salt kaybolursa her video aynı soru).
    sorular = {build_ilk_yorum(f"Şarkı {i}", "tr").split("\n")[0]
               for i in range(6)}
    assert len(sorular) > 1


def _proje(tmp_path, bayrak=False):
    p = tmp_path / "proj"
    p.mkdir()
    (p / "meta.json").write_text(
        json.dumps({"title": "Test Şarkısı", "theme": "pop"}),
        encoding="utf-8")
    state = {"youtube_video_id": "VID123"}
    if bayrak:
        state["youtube_ilk_yorum_at"] = "2026-09-01T00:00:00Z"
    (p / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(p)


class _SahteEkle:
    def __init__(self, disari):
        self.disari = disari

    def insert(self, part=None, body=None):
        self.disari.append(body)
        return self

    def execute(self):
        return {"id": "YORUM1"}


class _SahteServis:
    def __init__(self, disari):
        self._ekle = _SahteEkle(disari)

    def commentThreads(self):
        return self._ekle


def test_gonderir_ve_bayrak_yazar(tmp_path, monkeypatch):
    import youtube_auth
    import youtube_kota
    giden = []
    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _SahteServis(giden))
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    p = _proje(tmp_path)
    assert youtube_ilk_yorum.gonder(p, log=lambda *a: None) is True
    assert len(giden) == 1
    govde = giden[0]
    assert govde["snippet"]["videoId"] == "VID123"
    assert "Abone ol" in govde["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
    state = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    assert state.get("youtube_ilk_yorum_at")


def test_bayrak_varsa_tekrar_gondermez(tmp_path, monkeypatch):
    import youtube_auth
    import youtube_kota
    giden = []
    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _SahteServis(giden))
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    p = _proje(tmp_path, bayrak=True)
    assert youtube_ilk_yorum.gonder(p, log=lambda *a: None) is False
    assert giden == []


def test_kota_yoksa_dokunmaz(tmp_path, monkeypatch):
    import youtube_auth
    import youtube_kota
    giden = []
    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _SahteServis(giden))
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: False)
    p = _proje(tmp_path)
    assert youtube_ilk_yorum.gonder(p, log=lambda *a: None) is False
    assert giden == []
    state = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    assert "youtube_ilk_yorum_at" not in state


def test_api_hatasi_yukari_cikar(tmp_path, monkeypatch):
    """Modül yutmaz — kancadaki `except` yakalar, yükleme durmaz."""
    import youtube_auth
    import youtube_kota

    class _Bozuk:
        def commentThreads(self):
            raise RuntimeError("ag koptu")

    monkeypatch.setattr(youtube_auth, "get_authenticated_service", lambda: _Bozuk())
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    with pytest.raises(RuntimeError):
        youtube_ilk_yorum.gonder(_proje(tmp_path), log=lambda *a: None)
