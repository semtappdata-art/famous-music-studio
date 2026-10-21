# -*- coding: utf-8 -*-
"""YouTube Shorts EFEKTLERI (beat sync / hız rampası) — kilit testler.

Kilitlenen davranış:
- `beat_sync` modülü var ve librosa yoksa sessizce devre dışı kalır.
- Beat listesi kirpmaya uygun gelir (mutlak zaman, ofset uygulanmış).
- Flash `enable` ifadesi beat başına `between()` üretir, toplamı truthy'dir.
- Hız rampası planı beat'e kilitlidir (t_snap bir beat zamanıdır).
- **Hız rampası zaman eşlemesi tutarlıdır**: video `setpts='T/kat'` ve
  ses `atempo=kat` aynı hız çarpanını kullanır (ölçüldü: ters yönde
  çalışıyordu — video hızlanıyor, ses yavaşlıyordu).
- Beat'ler hız rampasıyla birlikte eşlenir (a/v uyumsuzluk olmaz).
- Shorts filtresi beat efektleri kapalıyken de çalışır (geriye uyum).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _yol in (REPO, os.path.join(REPO, "upload")):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import beat_sync
import config
import ffmpeg_utils


# --- 1) TEMEL FONKSİYONLAR -----------------------------------------------


def test_kirp_beatler_ofset_uygular():
    beatler = [30.5, 31.0, 31.5, 40.0]
    kirp = beat_sync.kirp_beatler(beatler, offset=30.0, duration=9.0)
    assert kirp == [0.5, 1.0, 1.5]


def test_kirp_beatler_sure_ile_keser():
    beatler = [1.0, 2.0, 3.0, 4.0, 5.0]
    kirp = beat_sync.kirp_beatler(beatler, offset=0.0, duration=3.5)
    assert kirp == [1.0, 2.0, 3.0]


def test_kirp_beatler_negatif_atlar():
    assert beat_sync.kirp_beatler([0.1, 1.0], offset=0.5) == [0.5]


def test_flash_ifadesi_beat_basina_between():
    ifade = beat_sync.flash_enable_ifadesi([1.0, 2.0], sure_sn=0.1)
    assert "between(t,0.970,1.100)" in ifade
    assert "between(t,1.970,2.100)" in ifade
    assert "+" in ifade          # toplam -> truthy


def test_flash_ifadesi_beat_yoksa_guvenli():
    assert beat_sync.flash_enable_ifadesi([]) == "0"


def test_nabiz_ifadesi_periyot_kullanir():
    ifade = beat_sync.beat_nabzi_ifadesi(0.5)
    assert "exp(" in ifade
    assert "0.5000" in ifade
    assert beat_sync.beat_nabzi_ifadesi(0.0) == "0"


def test_sure_hesaplama():
    """ISO-8601 sure -> saniye (beat_sync icinde kullanilir)."""
    import youtube_abone
    assert youtube_abone._sure_sn("PT3M40S") == 220
    assert youtube_abone._sure_sn("PT31S") == 31
    assert youtube_abone._sure_sn("PT1H2M3S") == 3723
    assert youtube_abone._sure_sn("") == 0


# --- 2) HIZ RAMPASI PLANI ------------------------------------------------


def test_ramp_plani_beat_e_kilitli():
    beatler = [0.4, 0.8, 1.2, 1.7, 2.1]
    plan = beat_sync.hiz_rampasi_planla(beatler, yavas_sure=1.6, yavas_kat=0.55)
    assert plan is not None
    # t_snap bir beat zamanı olmalı
    assert plan["t_snap"] in beatler
    assert plan["t_snap"] >= 1.6


def test_ramp_plani_beat_yoksa_none():
    assert beat_sync.hiz_rampasi_planla([], 1.6, 0.55) is None
    assert beat_sync.hiz_rampasi_planla([1.0], 1.6, 0.0) is None


def test_ramp_zaman_eslemesi_tutarli():
    """Video setpts='T/kat' → girdi [0,T_in) çıktı [0,T_in/kat).
    Ses atempo=kat → aynı eşleme. T_in = t_snap * kat olmalı."""
    beatler = [0.4, 0.8, 1.2, 1.7, 2.1, 2.5]
    plan = beat_sync.hiz_rampasi_planla(beatler, 1.6, 0.55)
    # T_in / kat == t_snap
    assert abs(plan["T_in"] / plan["kat"] - plan["t_snap"]) < 0.001


def test_beatler_ramp_ile_eslenir():
    """Beat'ler post-ramp zaman cizgisine tasinir (a/v uyumsuzluk olmaz)."""
    beatler = [0.4, 0.8, 1.2, 1.7, 2.1, 2.5]
    plan = beat_sync.hiz_rampasi_planla(beatler, 1.6, 0.55)
    esli = beat_sync.beatleri_zaman_esle(beatler, plan)
    assert len(esli) == len(beatler)
    # ilk beatler yavas bolgede -> kat ile carpilir
    assert abs(esli[0] - beatler[0] * plan["kat"]) < 0.001
    # monoton artar
    assert esli == sorted(esli)


def test_esleme_plansiz_degismez():
    beatler = [1.0, 2.0, 3.0]
    assert beat_sync.beatleri_zaman_esle(beatler, None) == beatler


# --- 3) FFMPEG FİLTRE ZİNCİRİ -------------------------------------------


def test_video_zinciri_setpts_bolme_kullanir():
    """setpts='T*kat' TERS yönde çalışır (hızlandırır). Doğrusu 'T/kat'."""
    plan = {"t_snap": 1.718, "T_in": 0.9449, "kat": 0.55}
    zincir, _ = ffmpeg_utils._build_speed_ramp_video("[1:v]", plan, 30.0)
    assert "setpts='T/0.5500'" in zincir
    assert "setpts='T*0.5500'" not in zincir


def test_ses_zinciri_atempo_kat_kullanir():
    """atempo=kat -> cikti suresi girdi/kat (setpts ile ayni esleme)."""
    plan = {"t_snap": 1.718, "T_in": 0.9449, "kat": 0.55}
    zincir, _ = ffmpeg_utils._build_speed_ramp_audio("0:a", plan, 30.0)
    assert "atempo=0.5500" in zincir
    assert "atempo=1.8182" not in zincir


def test_video_ve_ses_zinciri_ayni_T_in_kullanir():
    plan = {"t_snap": 1.718, "T_in": 0.9449, "kat": 0.55}
    v, _ = ffmpeg_utils._build_speed_ramp_video("[1:v]", plan, 30.0)
    a, _ = ffmpeg_utils._build_speed_ramp_audio("0:a", plan, 30.0)
    assert "0.9449" in v and "0.9449" in a


def test_zincir_etiketleri_ayri():
    plan = {"t_snap": 1.718, "T_in": 0.9449, "kat": 0.55}
    v, vlabel = ffmpeg_utils._build_speed_ramp_video("[1:v]", plan, 30.0)
    a, alabel = ffmpeg_utils._build_speed_ramp_audio("0:a", plan, 30.0)
    assert vlabel == "canvas_ramp"
    assert alabel == "aout_ramp"


def test_beat_flash_filteri_enable_icerir():
    fc = ffmpeg_utils._build_shorts_filter_complex(
        1080, 1920, 30.0, "Test", True, "pop",
        hashtags=["#Test"], beat_times=[0.4, 1.0, 1.6], beat_period=0.5)
    assert "enable='between(t," in fc
    assert "flash_strip" in fc


def test_beat_efekti_kapaliyken_de_calisir():
    """Bayraklar kapaliyken filtre zinciri beat icermemeli (geriye uyum)."""
    eski = config.SHORTS_BEAT_SYNC_AKTIF
    try:
        config.SHORTS_BEAT_SYNC_AKTIF = False
        fc = ffmpeg_utils._build_shorts_filter_complex(
            1080, 1920, 30.0, "Test", True, "pop",
            hashtags=["#Test"], beat_times=[0.4, 1.0], beat_period=0.5)
        assert "flash_strip" not in fc
        # NOT: CTA/end card da tek between() kullanir; beat flasi birden
        # fazla between()i '+' ile birlestirir (toplam -> truthy).
        assert ")+between(" not in fc
        assert "eval=frame" not in fc
    finally:
        config.SHORTS_BEAT_SYNC_AKTIF = eski


def test_beat_zoom_punch_scale_eval_frame_kullanir():
    """crop w/h FFmpeg 9'da per-frame olmuyor; scale eval=frame kullanilir."""
    fc = ffmpeg_utils._build_shorts_filter_complex(
        1080, 1920, 30.0, "Test", True, "pop",
        beat_times=[0.4, 1.0], beat_period=0.5)
    assert "eval=frame" in fc
    assert "crop=1080:1920" in fc


# --- 4) CONFIG BAYRAKLARI ------------------------------------------------


def test_config_bayraklari_mevcut():
    for ad in ("SHORTS_BEAT_SYNC_AKTIF", "SHORTS_BEAT_FLASH_AKTIF",
               "SHORTS_BEAT_HUE_AKTIF", "SHORTS_BEAT_PAN_AKTIF",
               "SHORTS_BEAT_ZOOM_AKTIF", "SHORTS_SPEED_RAMP_AKTIF"):
        assert hasattr(config, ad), ad
        assert isinstance(getattr(config, ad), bool)


def test_speed_ramp_kat_araligi_gecerli():
    """atempo araligi [0.5, 2.0] — kat bu aralikta olmali."""
    assert 0.5 <= config.SHORTS_SPEED_RAMP_YAVAS_KAT <= 1.0


# --- 5) LIBROSA YOKSA SESSIZCE DEVRE DISI --------------------------------


def test_librosa_yoksa_hata_yok(monkeypatch):
    """Kutuphane eksikligi boru hattini DUSURMEMELI."""
    import builtins
    gercek_import = builtins.__import__

    def sahte_import(ad, *args, **kwargs):
        if ad == "librosa" or ad.startswith("librosa."):
            raise ImportError("librosa yok (test)")
        return gercek_import(ad, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sahte_import)
    sonuc = beat_sync.analiz_et("olmayan.wav")
    assert sonuc["basari"] is False
    assert sonuc["beats"] == []
