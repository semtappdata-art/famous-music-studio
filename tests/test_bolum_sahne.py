# -*- coding: utf-8 -*-
"""Bölüm-sahne backdrop'u (stock_video.bolum_sahneleri / bolum_backdrop_kur).

Kilitlenen davranış:
- Eşleşme YALNIZCA dosyası diskte olan sahneleri alır; eksik/bozuk girdi
  [] döner (havuz yoluna düşülür, üretim durmaz).
- Sahne segmenti istenen SÜREDE çıkar (bölüm zamanlaması buna dayanır).
- Uçtan uca: 2 sahne + havuz dolgusu tek dosyada birleşir, süre tutar.
"""
import json
import os
import subprocess

import stock_video


def _png(yol, renk="red", boy="320x180"):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", f"testsrc=size={boy}:duration=1:rate=1",
                        "-frames:v", "1", "-update", "1", yol],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]


def _wav(yol, sure=12.0):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", f"sine=frequency=440:duration={sure}",
                        yol], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]


def _klip(yol, sure=10.0):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", f"testsrc=size=320x180:duration={sure}:rate=10",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", yol],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]


def _kurulum(tmp_path):
    d = tmp_path / "set"
    d.mkdir()
    _wav(str(d / "audio.wav"), 12.0)
    _png(str(d / "s1.png"), "red")
    _png(str(d / "s2.png"), "blue")
    bolumler = {"parcalar": [
        {"sira": 1, "ad": "Acilis", "bas": 0.0},
        {"sira": 2, "ad": "Orta", "bas": 4.0},
        {"sira": 3, "ad": "Kapanis", "bas": 8.0},
    ]}
    (d / "bolumler.json").write_text(json.dumps(bolumler), encoding="utf-8")
    spec = {"model": "x", "sahneler": [
        {"id": "bir", "bas": "Orta", "bitis": "Kapanis", "dosya": "s1.png"},
        {"id": "iki", "bas": "Kapanis", "bitis": None, "dosya": "s2.png"},
        {"id": "yok", "bas": "Acilis", "bitis": "Orta", "dosya": "olmayan.png"},
    ]}
    (d / "sahne_parti.json").write_text(json.dumps(spec), encoding="utf-8")
    return d


def test_eslesme_yalnizca_var_olanlar(tmp_path):
    d = _kurulum(tmp_path)
    es = stock_video.bolum_sahneleri(str(d))
    assert [(round(b, 1), round(e, 1), os.path.basename(y)) for b, e, y in es] == [
        (4.0, 8.0, "s1.png"),
        (8.0, 12.0, "s2.png"),
    ]


def test_eksik_girdi_bos_doner(tmp_path):
    d = tmp_path / "bos"
    d.mkdir()
    assert stock_video.bolum_sahneleri(str(d)) == []
    (d / "sahne_parti.json").write_text("{bozuk", encoding="utf-8")
    assert stock_video.bolum_sahneleri(str(d)) == []
    (d / "sahne_parti.json").write_text("{}", encoding="utf-8")
    (d / "bolumler.json").write_text("{}", encoding="utf-8")
    assert stock_video.bolum_sahneleri(str(d)) == []


def test_sahne_segmenti_sureyi_tutar(tmp_path):
    src = tmp_path / "k.png"
    _png(str(src))
    out = tmp_path / "seg.mp4"
    assert stock_video._sahne_segment_hazirla(str(src), 3.0, str(out), 320, 180)
    assert abs(stock_video._sure(str(out)) - 3.0) < 0.3


def test_bolum_backdrop_uctan_uca(tmp_path):
    d = _kurulum(tmp_path)
    _klip(str(d / "havuz.mp4"), 10.0)
    out = d / "backdrop.mp4"
    ok = stock_video.bolum_backdrop_kur(
        str(d), [str(d / "havuz.mp4")], str(out),
        genislik=320, yukseklik=180)
    assert ok, "bölüm backdrop kurulamadı"
    # Baş havuzla doluyor (0-4), sahneler 4-8 ve 8-12; xfade'ler biraz yer:
    # beklenen ≈ 12 - GECIS_SN * (parça_sayısı - 1) civarı, alt sınır gevşek.
    sure = stock_video._sure(str(out))
    assert 8.0 < sure <= 12.5, sure


def test_sahnesiz_kurulum_reddeder(tmp_path):
    d = tmp_path / "sade"
    d.mkdir()
    _wav(str(d / "audio.wav"), 5.0)
    _klip(str(d / "havuz.mp4"), 10.0)
    assert stock_video.bolum_backdrop_kur(
        str(d), [str(d / "havuz.mp4")], str(d / "out.mp4"),
        genislik=320, yukseklik=180) is False


def test_video_aralik_kisa_kaynaktan_donguye_alinir(tmp_path):
    d = _kurulum(tmp_path)
    _klip(str(d / "kisa.mp4"), 2.0)
    out = tmp_path / "vseg.mp4"
    assert stock_video._video_segment_hazirla(
        str(d / "kisa.mp4"), 5.0, str(out), 320, 180)
    assert abs(stock_video._sure(str(out)) - 5.0) < 0.4


def test_video_aralik_uzun_kaynaktan_ortalanir(tmp_path):
    d = _kurulum(tmp_path)
    _klip(str(d / "uzun.mp4"), 10.0)
    out = tmp_path / "vseg2.mp4"
    assert stock_video._video_segment_hazirla(
        str(d / "uzun.mp4"), 4.0, str(out), 320, 180)
    assert abs(stock_video._sure(str(out)) - 4.0) < 0.4
