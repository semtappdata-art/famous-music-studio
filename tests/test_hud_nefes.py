# -*- coding: utf-8 -*-
"""HUD nefes alması (config.DJ_HUD_NEFES_* + ffmpeg_utils blend öncesi eq).

Kilitlenen davranış:
- Varsayılan açık, yukarı-yönlü nabız (siyah taban klipte kalır).
- Kapalıyken graf eski hâline döner (çıplak scale -> format zinciri).
- Ara etiketler dengeli ([hud_rgb] bir üretim, bir tüketim).
- eq+screen zinciri bu makinenin ffmpeg'inde gerçekten çalışıyor.
"""
import subprocess

import config
import ffmpeg_utils


def _graf(**kw):
    varsayilan = dict(width=1280, height=720, duration=120.0, title="Test",
                      has_art=True, theme_key=config.DEFAULT_THEME)
    varsayilan.update(kw)
    return ffmpeg_utils._build_filter_complex(**varsayilan)


def test_nefes_varsayilanlari():
    assert config.DJ_HUD_NEFES is True
    # Zevk değerleri sabit sayıya DEĞİL aralığa kilitli: periyotla/derinlikle
    # oynanabilir, ama gri-peçe (derinlik > 0.30) ve telaş (periyot < 4 sn)
    # bölgesine girilemez. Sınırlar config.py'deki yorumla aynı olmalı.
    assert 4 <= float(config.DJ_HUD_NEFES_SURE_SN) <= 16
    assert 0.05 <= float(config.DJ_HUD_NEFES_DERINLIK) <= 0.30
    # Yön yukarı olmalı: 1+derinlik*(0.5+0.5*sin) en az 1.0'dır, siyah klipte kalır.


def test_nefes_acikken_grafta():
    g = _graf(hud_index=4)
    assert "eval=frame" in g
    assert "sin(2*PI*t/" in g
    assert "blend=all_mode=screen" in g
    assert "eq=contrast='1+" in g


def test_nefes_kapaliyken_eski_zincir(monkeypatch):
    monkeypatch.setattr(config, "DJ_HUD_NEFES", False)
    g = _graf(hud_index=4)
    assert "eval=frame" not in g
    assert "[4:v]scale=1280:720,format=gbrp[hud_rgb]" in g
    assert "blend=all_mode=screen" in g


def test_hud_etiketleri_dengeli():
    import re
    for kw in ({"hud_index": 4}, {"hud_index": 4, "intro_index": 5}):
        g = _graf(**kw)
        uretilen = set()
        for adim in g.split(";"):
            for m in re.finditer(r"\[([a-z_0-9]+)\]$", adim.strip()):
                uretilen.add(m.group(1))
        for etiket in uretilen:
            if etiket == "vfinal":
                continue
            assert g.count(f"[{etiket}]") == 2, (
                f"{etiket} dengesiz ({kw}): {g.count('[' + etiket + ']')} kez geçiyor")


def test_nefes_zinciri_ffmpegde_calisiyor(tmp_path):
    """Grafın ürettiği eq+blend zincirinin aynısı, küçük girdilerle uçtan uca."""
    cikti = tmp_path / "nefes.mp4"
    derinlik = float(config.DJ_HUD_NEFES_DERINLIK)
    sure = float(config.DJ_HUD_NEFES_SURE_SN)
    r = subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x180:duration=2:rate=10",
        "-f", "lavfi", "-i",
        "color=c=black:size=320x180:duration=2:rate=10,"
        "drawbox=x=10:y=10:w=60:h=4:color=0x7FE8FF@0.55:t=fill",
        "-filter_complex",
        "[0:v]format=gbrp[vb];"
        f"[1:v]scale=320:180,"
        f"eq=contrast='1+{derinlik}*(0.5+0.5*sin(2*PI*t/{sure}))':eval=frame,"
        "format=gbrp[h];"
        "[vb][h]blend=all_mode=screen,format=yuv420p[v]",
        "-map", "[v]", str(cikti),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-500:]
    assert cikti.is_file() and cikti.stat().st_size > 1000
