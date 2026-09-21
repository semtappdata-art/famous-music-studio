# -*- coding: utf-8 -*-
"""`merge_dj_set_segments.py` — KESİNTİSİZ geçiş kuralı (kullanıcı kararı 2026-09-14).

Kural: bundan sonraki TÜM DJ seti birleştirmelerinde geçişler fark edilmemelidir;
müzik akışında düşüş (dip) olmamalıdır. Kod düzeyinde bu iki şey demek:
  1. Kenar sessizlik (Suno parçalarında 0.06-0.81 sn ölçüldü) kırpılmadan crossfade
     sessizliğe biner -> "müzik -> sessizlik -> müzik" boşluğu. `atrim` + `asetpts`
     ile kırpılıyor.
  2. Eğri `tri` (linear) değil `qsin` (equal-power): linear crossfade orta noktada
     ~3dB dip üretir, `qsin/qsin` toplam gücü sabit tutar.

KORUNAN SÖZLEŞMELER:
  - İLK parçanın baş sessizliği de kırpılır (set müzikle açılır).
  - SON parçanın kuyruk sessizliği KORUNUR (set sönümlenerek biter — SUNO.md).
  - Kırpma sonucu 1 sn'den kısa kalan parça KIRPILMAZ (ölçüm hatası müziği kesmez).
  - Filtergraph'taki her etiket dengeli üretilip tüketilmeli; eğri HİÇBİR koşulda
    tri'ye dönmemeli.

ÇALIŞMADIĞINI NASIL ANLARIZ (gerçek ffmpeg): `acrossfade` + `atrim` + `asetpts`
zinciri bozulursa merge ffmpeg hatasıyla düşer; sessizlik ölçümü bozulursa
`test_kenar_sessizlik_gercek_dosyada` yanlış süre döndürür; eğri tri'ye dönerse
`test_grafige_qsin_ve_atrim_biner` düşer.
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import merge_dj_set_segments as m                       # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None
FFPROBE = shutil.which("ffprobe") is not None
ffmpeg_gerekli = pytest.mark.skipif(not (FFMPEG and FFPROBE), reason="ffmpeg/ffprobe yok")

# Sentetik parça: 1 sn sessizlik -> 2 sn sine -> 1 sn sessizlik (toplam 4 sn)
def _sentetik_parca(yol: str):
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2",
         "-af", "adelay=1000:all=1,apad=pad_dur=1",
         "-ac", "1", str(yol)],
        capture_output=True)
    assert r.returncode == 0, r.stderr


# --- _kesimler: kırpma sınırı mantığı (saf fonksiyon) ----------------------

def test_ilk_parcanin_bas_sessizligi_de_kirpilir():
    # [(bas_sil, son_sil, toplam)] üç parça
    kes = m._kesimler([(1.0, 0.5, 200.0), (0.5, 0.8, 200.0), (0.4, 2.0, 200.0)])
    assert kes[0] == (1.0, 199.5)       # ilk parça: baş kırpılır, kuyruk da kırpılır
    assert kes[1] == (0.5, 199.2)       # orta: iki taraftan
    assert kes[2] == (0.4, 200.0)       # SON parça: kuyruk KORUNUR


def test_sessizlik_sifir_ise_kirpma_yok():
    kes = m._kesimler([(0.0, 0.0, 200.0), (0.0, 0.0, 200.0)])
    assert kes == [(0.0, 200.0), (0.0, 200.0)]


def test_kirpma_sonucu_bir_saniyenin_altinda_kalan_kirpilmaz():
    """Ölçüm bozuksa (neredeyse tamamı sessiz diyorsa) kapı: MÜZİK KESİLMEZ."""
    kes = m._kesimler([(9.5, 0.0, 10.0), (0.0, 0.0, 200.0)])
    assert kes[0] == (0.0, 10.0)  # 10-9.5=0.5 < 1.0 -> kırpma YOK
    kes2 = m._kesimler([(9.0, 0.0, 10.0), (0.0, 0.0, 200.0)])
    assert kes2[0] == (9.0, 10.0)  # 10-9.0=1.0 eşiğinde: kırpma devam (1 sn içerik kalır)


def test_kesimler_yuvarlama():
    kes = m._kesimler([(1.23456, 0.0, 200.0), (0.0, 0.0, 200.0)])
    assert kes[0] == (1.235, 200.0)
    assert kes[1] == (0.0, 200.0)   # son parça kuyruğu korunur


# --- _filtre_grafigi: eğri + etiket dengesi ---------------------------------

def test_grafige_qsin_ve_atrim_biner():
    g = m._filtre_grafigi([(1.0, 199.0), (0.5, 199.5), (0.4, 200.0)], 3.0)
    assert "c1=qsin:c2=qsin" in g
    assert "c1=tri" not in g and "c2=tri" not in g
    assert "[0:a]atrim=start=1.000:end=199.000" in g
    assert "asetpts=PTS-STARTPTS" in g


def test_grafik_etiketleri_dengeli():
    """Üretilen her ara etiket bir sonraki part tarafından tüketilmeli."""
    g = m._filtre_grafigi([(0.0, 100.0), (1.0, 99.0), (2.0, 98.0), (0.0, 100.0)], 3.0)
    ciktilar, girdiler = [], []
    for part in g.split(";"):
        etiketler = re.findall(r"\[([^\]]+)\]", part)
        ciktilar.append(etiketler[-1])
        girdiler.extend(l for l in etiketler[:-1] if not l.endswith(":a"))
    for c in ciktilar:
        if c == "aout":
            continue
        assert c in girdiler, f"etiket üretildi ama tüketilmedi: {c}"
    assert len(girdiler) == len(set(girdiler)), "aynı etiket iki kez tüketiliyor"
    assert ciktilar[0] == "a0" and ciktilar[-1] == "aout"


# --- _kenar_sessizlik: gerçek onaylanmış wav (ffmpeg gerekli) ---------------

@ffmpeg_gerekli
def test_kenar_sessizlik_gercek_dosyada(tmp_path):
    ses = tmp_path / "k1.wav"
    _sentetik_parca(ses)
    bas, son = m._kenar_sessizlik(str(ses))
    assert 0.8 <= bas <= 1.05          # ~0.95 sn baş sessizlik (1 sn - pay 0.05)
    assert 0.8 <= son <= 1.05          # ~0.95 sn kuyruk sessizlik


@ffmpeg_gerekli
def test_kenar_sessizlik_sessiz_olmayan_dosyada(tmp_path):
    ses = tmp_path / "k2.wav"
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ac", "1", str(ses)],
        capture_output=True)
    assert r.returncode == 0
    bas, son = m._kenar_sessizlik(str(ses))
    assert bas <= 0.35 and son <= 0.35   # sine üretiminde ölçülen sessizlik çok küçük


# --- uçtan uca: sentetik segmentlerle gerçek merge --------------------------

@ffmpeg_gerekli
def test_merge_kesintisiz_gercek_ffmpeg(tmp_path):
    """İki sentetik segment (öncesi/sonrası sessiz) kırpma + qsin ile birleşmeli;
    çıktının İÇİNDE uzun sessizlik olmamalı (geçiş fark edilmemeli)."""
    set_dir = tmp_path / "set"
    seg = set_dir / "_segments"
    seg.mkdir(parents=True)
    _sentetik_parca(seg / "Test 1.wav")
    _sentetik_parca(seg / "Test 2.wav")

    cikti = m.merge(str(set_dir), crossfade=1.0)
    assert os.path.isfile(cikti) and os.path.getsize(cikti) > 0

    toplam = m._sure(cikti)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", cikti,
         "-af", "silencedetect=noise=-50dB:d=0.2", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    bloklar = []
    simdiki = None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            simdiki = float(line.split("silence_start:")[1].split("|")[0].strip())
        elif simdiki is not None and "silence_end:" in line:
            bitis = float(line.split("silence_end:")[1].split("|")[0].strip())
            bloklar.append((simdiki, bitis, bitis - simdiki))
            simdiki = None
    # İçeride uzun sessizlik olmamalı — SON parçanın kuyruk sessizliği BİLEREK
    # korunur (set sönümlenerek biter), o yüzden pencere onu dışlar sak.
    # (toplam - 1.4: son parçanın ~1 sn'lik korunan kuyruğu + marj.)
    uzun_ic = [b for b in bloklar if b[2] > 0.3 and 0.2 < b[0] < toplam - 1.4]
    assert uzun_ic == [], f"Çıktının içinde uzun sessizlik var: {uzun_ic}"


@ffmpeg_gerekli
def test_merge_iki_parca_toplam_sure(tmp_path):
    """2 parça (her biri 4 sn: 1 sn sessiz + 2 sn sine + 1 sn sessiz), 1 sn crossfade.
    Kırpma sonrası: par1 ~2.1 sn (0.95..3.05), par2 ~3.05 sn (0.95..4.0, kuyruk korunur);
    toplam ~ (2.1 + 3.05) - 1 = ~4.15 sn — geçiş uzunluğu kadar düşüm, sessizlik birikmez."""
    set_dir = tmp_path / "set"
    seg = set_dir / "_segments"
    seg.mkdir(parents=True)
    _sentetik_parca(seg / "Test 1.wav")
    _sentetik_parca(seg / "Test 2.wav")
    m.merge(str(set_dir), crossfade=1.0)
    sure = m._sure(str(set_dir / "audio.wav"))
    assert 3.5 <= sure <= 5.5, f"beklenen ~4.15 sn, geldi {sure}"


@ffmpeg_gerekli
def test_merge_crossfade_tavanlanir(tmp_path):
    """crossfade en kısa kırpılmış parçanın yarısını aşamaz (ffmpeg overlap şartı)."""
    set_dir = tmp_path / "set"
    seg = set_dir / "_segments"
    seg.mkdir(parents=True)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ac", "1",
         str(seg / "Test 1.wav")], capture_output=True)
    assert r.returncode == 0
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ac", "1",
         str(seg / "Test 2.wav")], capture_output=True)
    assert r.returncode == 0
    cikti = m.merge(str(set_dir), crossfade=10.0)  # dev crossfade -> tavanlanmalı
    assert m._sure(cikti) > 1.0


@ffmpeg_gerekli
def test_merge_sessiz_parca_kirpilmaz(tmp_path):
    """Tam sessiz ikinci parça kırpma sonucu 1 sn altına inmeli değil (kapı)."""
    set_dir = tmp_path / "set"
    seg = set_dir / "_segments"
    seg.mkdir(parents=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ac", "1",
         str(seg / "Test 1.wav")], capture_output=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", "anullsrc=channel_layout=mono:sample_rate=44100:duration=3",
         "-ac", "1", str(seg / "Test 2.wav")], capture_output=True)
    cikti = m.merge(str(set_dir), crossfade=1.0)
    sure = m._sure(cikti)
    assert sure > 2.5  # ikinci parça 1 sn'ye kırpılmadı; toplam çok küçülmedi


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))