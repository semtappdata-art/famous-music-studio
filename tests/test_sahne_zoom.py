# -*- coding: utf-8 -*-
"""Sahne zoom'u (config.DJ_SAHNE_ZOOM_* + ffmpeg_utils video-canvas dalı).

Kilitlenen davranış:
- Varsayılan açık, bitiş 1.00-1.15 aralığında (üstü yumuşama/sarsıntı bölgesi).
- YALNIZCA video backdrop dalında; statik PNG dalında pan/hue aynen durur.
- Kapalıyken graf eski hâline döner (çıplak scale -> crop zinciri).
- zoompan zinciri bu makinenin ffmpeg'inde gerçekten çalışıyor ve
  kareler zamanla DEĞİŞİYOR (donuk zoom testi yakalar).
"""
import subprocess

import config
import ffmpeg_utils


def _graf(**kw):
    varsayilan = dict(width=1280, height=720, duration=600.0, title="Test",
                      has_art=True, theme_key=config.DEFAULT_THEME)
    varsayilan.update(kw)
    return ffmpeg_utils._build_filter_complex(**varsayilan)


def test_zoom_varsayilanlari():
    assert config.DJ_SAHNE_ZOOM is True
    assert 1.0 <= float(config.DJ_SAHNE_ZOOM_BITIS) <= 1.15


def test_zoom_video_dalinda():
    g = _graf(backdrop_video=True)
    assert "zoompan" in g
    assert "min(" in g and "*time/" in g  # set sonuna kadar rampa, sonra sabit
    # Merkez sabiti: varsayılan (0,0) kadrajı sağa-aşağı kaydırır ("sola zoom").
    assert "x='iw/2-(iw/zoom/2)'" in g
    assert "y='ih/2-(ih/zoom/2)'" in g


def test_zoom_statik_dalda_yok():
    g = _graf(backdrop_video=False)
    assert "zoompan" not in g
    assert "hue=h='" in g  # pan/hue düzeni aynen duruyor


def test_zoom_kapaliyken_eski_zincir(monkeypatch):
    monkeypatch.setattr(config, "DJ_SAHNE_ZOOM", False)
    g = _graf(backdrop_video=True)
    assert "zoompan" not in g
    assert "crop=1280:720,setsar=1[canvas]" in g


def test_zoom_kareleri_hareket_ediyor(tmp_path):
    """Hızlandırılmış rampa: ilk ve son kare FARKLI olmalı (donuk zoomu yakalar)."""
    cikti = tmp_path / "zoom.mp4"
    r = subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x180:duration=5:rate=10",
        "-filter_complex",
        "[0:v]scale=320:180:force_original_aspect_ratio=increase,"
        "crop=320:180,setsar=1,"
        "zoompan=z='min(1.3,1+0.3*time/5)':d=1:s=320x180:fps=10,setsar=1[v]",
        "-map", "[v]", str(cikti),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-500:]
    k0 = tmp_path / "k0.raw"
    k1 = tmp_path / "k1.raw"
    for ss, k in (("0", k0), ("4", k1)):
        rr = subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-ss", ss, "-i", str(cikti),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", str(k),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert rr.returncode == 0, rr.stderr[-500:]
    assert k0.read_bytes() != k1.read_bytes(), "zoom donuk: ilk/son kare aynı"
