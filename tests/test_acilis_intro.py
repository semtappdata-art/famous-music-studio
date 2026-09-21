# -*- coding: utf-8 -*-
"""Açılış (ilk saniyeler) davranışı: kapak intro'su + baştaki sessizliğin kırpılması.

NEDEN VAR: 2026-09-11 ölçümünde (olcum_temel_cizgi.json / kitle_tutma_28gun)
izleyicinin ~yarısı videonun ilk %5'inde (≈11 sn) gidiyor ve kaybın büyük kısmı
videonun %1-%3'ü arasında, yani ~2.-7. saniyede toplanıyor. O saniyelerde ekranda
ölçülen değişim ~%3'tü (donmuş kare). Açılışa kapak intro'su eklendi. Bu dosya
intro'nun FİLTRE GRAFİĞİNİ ve sessizlik kırpmasını koruyor — ikisi de ffmpeg
filtergraph'ı bozmaya çok müsait yerler.
"""
import os
import subprocess

import config
import ffmpeg_utils
import render


# --------------------------------------------------------------------------
# Baştaki sessizliğin tespiti
# --------------------------------------------------------------------------

def _ses_uret(path, sessizlik_sn, ton_sn=3.0):
    """Başında `sessizlik_sn` kadar dijital sessizlik olan bir wav üretir."""
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={ton_sn}",
        "-af", f"adelay={int(sessizlik_sn * 1000)}|{int(sessizlik_sn * 1000)}",
        "-ar", "44100", "-ac", "2", str(path),
    ], check=True)


def test_bastaki_sessizlik_olculuyor(tmp_path):
    ses = tmp_path / "audio.wav"
    _ses_uret(ses, 1.5)
    kirp = ffmpeg_utils.bastaki_sessizlik(str(ses))
    # 1,5 sn sessizlik - INTRO_SESSIZLIK_PAY (0,12) ≈ 1,38
    assert 1.2 < kirp < 1.5, f"beklenen ~1,38 sn, gelen {kirp}"


def test_sessizlik_yoksa_kirpma_yok(tmp_path):
    ses = tmp_path / "audio.wav"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-ar", "44100", "-ac", "2", str(ses),
    ], check=True)
    assert ffmpeg_utils.bastaki_sessizlik(str(ses)) == 0.0


def test_sessizlik_tavani_asilmiyor(tmp_path, monkeypatch):
    """Tespit ne derse desin şarkıdan INTRO_SESSIZLIK_MAKS'tan fazlası kesilemez.
    Bu tavan bilinçli bir emniyet: bozuk bir tespit şarkının nakaratını yutmasın."""
    monkeypatch.setattr(config, "INTRO_SESSIZLIK_MAKS", 0.5)
    ses = tmp_path / "audio.wav"
    _ses_uret(ses, 2.5)
    assert ffmpeg_utils.bastaki_sessizlik(str(ses)) == 0.5


def test_bozuk_dosyada_sessizce_sifir(tmp_path):
    """ffmpeg hata verirse kırpma YAPILMAMALI — bu fonksiyonun arızası hiçbir
    zaman şarkının başını kesmeye dönüşmemeli."""
    bozuk = tmp_path / "yok.wav"
    bozuk.write_bytes(b"bu bir wav degil")
    assert ffmpeg_utils.bastaki_sessizlik(str(bozuk)) == 0.0


# --------------------------------------------------------------------------
# Kapak seçimi
# --------------------------------------------------------------------------

def test_kapak_orana_gore_seciliyor(tmp_path):
    (tmp_path / "cover.png").write_bytes(b"x")
    (tmp_path / "cover_vertical.png").write_bytes(b"x")
    yatay = render.find_intro_cover(str(tmp_path), 1920, 1080)
    dikey = render.find_intro_cover(str(tmp_path), 1080, 1920)
    assert os.path.basename(yatay) == "cover.png"
    assert os.path.basename(dikey) == "cover_vertical.png"


def test_kapak_yoksa_none(tmp_path):
    assert render.find_intro_cover(str(tmp_path), 1920, 1080) is None


# --------------------------------------------------------------------------
# Filtre grafiği
# --------------------------------------------------------------------------

def _graf(**kw):
    varsayilan = dict(width=1920, height=1080, duration=120.0, title="Test",
                      has_art=True, theme_key=config.DEFAULT_THEME)
    varsayilan.update(kw)
    return ffmpeg_utils._build_filter_complex(**varsayilan)


def test_intro_yokken_graf_degismiyor():
    g = _graf(intro_index=None)
    assert "[intro]" not in g
    assert g.count("[vfinal]") == 1
    assert "vpre" not in g


def test_intro_varken_zincir_kuruluyor():
    g = _graf(intro_index=4)
    # Kapak dalı: ölçekle -> kırp -> rgba -> trim -> fade(alpha)
    assert "[4:v]" in g
    assert "fade=t=out" in g and "alpha=1" in g
    assert "trim=0:" in g
    # Nihai birleşim en ÜSTTE olmalı: kapak, ilerleme çubuğunun da üstünü örtüyor.
    assert g.endswith("[intro]overlay=0:0:eof_action=pass[vfinal]")
    assert g.count("[vfinal]") == 1
    assert g.count("[vpre]") == 2  # bir üretim, bir tüketim


def test_intro_hud_ile_birlikte_calisiyor():
    """HUD (DJ setleri) yolunda da nihai etiket bir kez üretilip bir kez tüketilmeli.
    Bu iki yol ayrı ayrı [vfinal] üretiyordu; intro eklenince çakışma riski vardı."""
    g = _graf(intro_index=5, hud_index=4)
    assert g.count("[vfinal]") == 1
    assert g.count("[vpre]") == 2
    assert "blend=all_mode=screen" in g


def test_grafta_etiketler_dengeli():
    """Üretilen her ara etiket tüketiliyor mu? Dengesiz bir etiket ffmpeg'de
    'Cannot find a matching stream' hatası verir — testte yakalamak daha ucuz."""
    import re
    for kw in ({"intro_index": None}, {"intro_index": 4},
               {"intro_index": 5, "hud_index": 4}):
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


# --------------------------------------------------------------------------
# Uçtan uca render (filtergraph gerçekten ffmpeg'de çalışıyor mu)
# --------------------------------------------------------------------------

def _kucuk_proje(tmp_path, ses_sn=8.0, sessizlik=1.0):
    _ses_uret(tmp_path / "audio.wav", sessizlik, ses_sn)
    for ad in ("art.jpg", "cover.png"):
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", f"testsrc=size=320x320:duration=1:rate=1",
            "-frames:v", "1", "-update", "1", str(tmp_path / ad),
        ], check=True)
    return tmp_path



def test_intro_ile_render_calisiyor(tmp_path):
    p = _kucuk_proje(tmp_path)
    cikti = tmp_path / "out.mp4"
    ffmpeg_utils.render_video(
        str(p / "art.jpg"), str(p / "audio.wav"), str(cikti),
        640, 360, title="Test", theme=config.DEFAULT_THEME,
        intro_cover=str(p / "cover.png"),
    )
    assert cikti.is_file() and cikti.stat().st_size > 1000
    # Sessizlik kırpıldığı için çıktı sesten KISA olmalı.
    sure = ffmpeg_utils.get_audio_duration(str(cikti))
    assert sure < 9.0 - 0.5, f"baştaki sessizlik kırpılmamış görünüyor: {sure}"



def test_cok_kisa_parcada_intro_atlaniyor(tmp_path, monkeypatch):
    """2,4 saniyelik bir kapak, 4 saniyelik bir videonun yarısı demek olurdu."""
    p = _kucuk_proje(tmp_path, ses_sn=3.0, sessizlik=0.2)
    cagrilar = {}
    gercek = ffmpeg_utils._build_filter_complex

    def ara(*a, **kw):
        cagrilar["intro_index"] = kw.get("intro_index", a[10] if len(a) > 10 else None)
        return gercek(*a, **kw)

    monkeypatch.setattr(ffmpeg_utils, "_build_filter_complex", ara)
    ffmpeg_utils.render_video(
        str(p / "art.jpg"), str(p / "audio.wav"), str(tmp_path / "out.mp4"),
        640, 360, title="Test", theme=config.DEFAULT_THEME,
        intro_cover=str(p / "cover.png"),
    )
    assert cagrilar["intro_index"] is None
