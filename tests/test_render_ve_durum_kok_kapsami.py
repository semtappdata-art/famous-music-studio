# -*- coding: utf-8 -*-
"""`render.py --all` ve `youtube_playlists.durum()` UC KOKU de geziyor mu.

NEDEN VAR (2026-09-11): ikisi de kok listesini ELLE sayiyordu.

  * `render.py --all` yalnizca `base = "projects"` klasorunu geziyordu. Etkisi
    dusuk ama gercek: DJ setleri ve derlemeler `dj_famous_process` ile render
    ediliyor, yani boru hatti bundan etkilenmiyordu — ama ELLE yapilan
    tam-katalog kosusu ("hepsini bir daha render et") katalogun ucte birini HIC
    gormuyordu ve hicbir hata vermiyordu. Ayni sinif: `validate_project --all`
    (bkz. tests/test_kok_listesi_muhafizi.py).
  * `durum()`'un `base_list` varsayilani uc kokun ELLE yazilmis bir KOPYASIYDI
    ve icindeki yollar GORELIydi.

Ikinci testin asil konusu bir TUZAK: kanonik `uyumluluk.KOKLER` MUTLAK yollar
tutuyor (goreli birakilirsa yanlis cwd'de os.path.isdir False doner ve rapor
SESSIZCE bos cikar). Raporun kok sutununa bu mutlak yol dogrudan basilirsa
11 karakterlik sutun tam bir Windows yoluna donuyor — `youtube_analytics.
_video_haritasi`'nda 2026-09-11'de tam olarak bu yasandi. Sutun KISA kok adini
basmali.
"""

import io
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import uyumluluk                                   # noqa: E402


def _uc_kok(tmp_path, proje_adi="Ornek Proje", durum=None):
    """Uc kokun her birinde bir proje olan sahte bir katalog kurar."""
    kokler = []
    for ad in uyumluluk.KOK_ADLARI:
        proje = tmp_path / ad / ("%s %s" % (ad, proje_adi))
        proje.mkdir(parents=True)
        if durum is not None:
            (proje / "state.json").write_text(
                json.dumps(durum, ensure_ascii=False), encoding="utf-8")
        kokler.append(str(tmp_path / ad))
    return tuple(kokler)


# --- render.py --all -----------------------------------------------------

def test_render_all_uc_kokun_hepsini_geziyor(tmp_path, monkeypatch):
    """GERCEK render BASLATILMIYOR: render_project sahte, sadece liste olculuyor."""
    import render

    kokler = _uc_kok(tmp_path)
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)

    gorulen = []

    def _sahte_render(proje):
        gorulen.append(proje)
        return True

    monkeypatch.setattr(render, "render_project", _sahte_render)
    monkeypatch.setattr(sys, "argv", ["render.py", "--all"])
    with pytest.raises(SystemExit) as e:
        render.main()

    assert e.value.code == 0
    assert [os.path.basename(os.path.dirname(p)) for p in gorulen] ==         list(uyumluluk.KOK_ADLARI)
    for p in gorulen:
        # Mutlak yol: goreli birakilsaydi cwd degisince liste SESSIZCE bosalirdi.
        assert os.path.isabs(p), p


def test_render_all_bos_katalogda_tek_kok_varsaymiyor(tmp_path, monkeypatch,
                                                      capsys):
    """Hata metni artik "projects klasoru yok" diyemez — uc kok birden var."""
    import render

    kokler = tuple(str(tmp_path / ad) for ad in uyumluluk.KOK_ADLARI)
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)
    monkeypatch.setattr(render, "render_project",
                        lambda p: pytest.fail("render'a hic girilmemeliydi"))
    monkeypatch.setattr(sys, "argv", ["render.py", "--all"])
    with pytest.raises(SystemExit) as e:
        render.main()

    assert e.value.code == 1
    cikti = capsys.readouterr().out
    for ad in uyumluluk.KOK_ADLARI:
        assert ad in cikti, cikti


def test_render_all_kok_listesini_elle_saymiyor():
    """Kaynakta `base = "projects"` gibi bir tekil kok kalmadi."""
    kaynak = io.open(os.path.join(_KOK, "render.py"), encoding="utf-8").read()
    assert 'base = "projects"' not in kaynak
    assert "uyumluluk.proje_klasorleri()" in kaynak


# --- youtube_playlists.durum() -------------------------------------------

def test_durum_varsayilani_kanonik_nesnenin_kendisi():
    """Ayni icerikli bir KOPYA tuple, dorduncu kok acilinca sessizce geri kalirdi."""
    import inspect

    import youtube_playlists

    varsayilan = inspect.signature(
        youtube_playlists.durum).parameters["base_list"].default
    assert varsayilan is uyumluluk.KOKLER


def test_durum_kok_sutununa_kisa_ad_basiyor(tmp_path, monkeypatch, capsys):
    """TUZAK TESTI: mutlak kok yolu sutuna dogrudan basilirsa rapor okunamaz."""
    import youtube_playlists

    kokler = _uc_kok(tmp_path, durum={"youtube_video_id": "vid123"})

    # AGA CIKMA YOK: bu makinede gercek bir upload/token.json duruyor.
    monkeypatch.setattr(youtube_playlists, "get_authenticated_service",
                        lambda: None)
    monkeypatch.setattr(youtube_playlists, "_load_playlist_ids", dict)
    monkeypatch.setattr(youtube_playlists, "playlist_videolari",
                        lambda *a, **k: set())

    youtube_playlists.durum(base_list=kokler)
    cikti = capsys.readouterr().out

    for kok in kokler:
        # Kokun KENDISI (mutlak yol) ciktiya girmemeli...
        assert kok not in cikti, cikti
        # ...ama kisa adi, kendi satirinin BASINDA olmali.
        ad = os.path.basename(kok)
        assert any(satir.strip().startswith(ad + " ")
                   for satir in cikti.splitlines()), (ad, cikti)
    assert "toplam eksik: 3" in cikti, cikti
