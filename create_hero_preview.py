#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hero onizleme MP3 uretir (Madde 25/31): en yuksek enerjili 30 saniye.

Yontem: ffmpeg `astats` ile saniye basina RMS alinir, ardindan 30 sn'lik
pencere icin en yuksek ortalama enerji (RMS) aranir. Bu, Suno "radio dial"
yaklasiminin basit bir karsiligidir: en etkileyici bolume girer.

Kullanim:
    python create_hero_preview.py --proje "projects/Gece Sürüşü"
    python create_hero_preview.py --proje "projects/Gece Sürüşü" --sure 30 --baslangic 45
"""
import argparse
import json
import os
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(REPO, "site", "assets", "gece-masallari-preview-30s.mp3")


def rms_saniye(ffmpeg, ses):
    """Saniye basina RMS degerleri (liste)."""
    # ametadata ciktisini stdout'a yaziyoruz (file=-): stderr'de gorunmez.
    cmd = [
        ffmpeg, "-v", "error", "-i", ses,
        "-af", "astats=metadata=1:reset=1:length=1,"
              "ametadata=print:file=-:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-400:])
    # astats length=1 -> kare basina reset. `ametadata` iki farkli satir
    # yaziyor: once "pts_time:N", sonra "lavfi.astats...=V". Durum makinesi
    # ile eslestiriyoruz.
    ham = []
    son_pts = None
    for satir in (r.stdout or "").splitlines():
        tm = re.search(r"pts_time:([\d.]+)", satir)
        if tm:
            son_pts = float(tm.group(1))
            continue
        lv = re.search(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+)", satir)
        if lv and son_pts is not None:
            ham.append((son_pts, float(lv.group(1))))
    if not ham:
        return []
    toplam_sure = ham[-1][0]
    kova = [0.0] * (int(toplam_sure) + 1)
    sayac = [0] * (int(toplam_sure) + 1)
    for t, v in ham:
        if v <= -90.0:      # sessizlik -> ortalama haricinde tut
            continue
        i = int(t)
        if i < len(kova):
            kova[i] += v
            sayac[i] += 1
    return [kova[i] / sayac[i] if sayac[i] else -90.0 for i in range(len(kova))]


def en_iyi_pencere(degerler, pencere_sn, adim_sn=1):
    """En yuksek ortalama enerjiye sahip pencere baslangic saniyesi."""
    if not degerler:
        return 0
    n = len(degerler)
    if n <= pencere_sn:
        return 0
    # kayan pencere (prefix sum)
    prefix = [0.0] * (n + 1)
    for i, v in enumerate(degerler):
        prefix[i + 1] = prefix[i] + v
    en_iyi, en_iyi_i = -1e9, 0
    for i in range(0, n - pencere_sn, adim_sn):
        toplam = prefix[i + pencere_sn] - prefix[i]
        if toplam > en_iyi:
            en_iyi, en_iyi_i = toplam, i
    return en_iyi_i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proje", default="projects/Gece Sürüşü")
    ap.add_argument("--sure", type=int, default=30)
    ap.add_argument("--baslangic", type=int, default=None,
                    help="verilirse enerji analizi yerine bu saniyeden keser")
    ap.add_argument("--cikti", default=HEDEF)
    ap.add_argument("--bitrate", default="192k")
    args = ap.parse_args()

    proje = os.path.join(REPO, args.proje) if not os.path.isabs(args.proje) else args.proje
    ses = None
    for ad in ("audio.wav", "audio.mp3", "audio.m4a"):
        p = os.path.join(proje, ad)
        if os.path.isfile(p):
            ses = p
            break
    if not ses:
        print(f"HATA: {proje} icinde audio dosyasi yok")
        return 2

    bas = args.baslangic
    if bas is None:
        print("Enerji analizi yapiliyor...")
        rms = rms_saniye("ffmpeg", ses)
        print(f"  {len(rms)} saniye analiz edildi")
        bas = en_iyi_pencere(rms, args.sure)
        print(f"  En guclu {args.sure}sn pencere: {bas}s")

    os.makedirs(os.path.dirname(args.cikti), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(bas), "-t", str(args.sure), "-i", ses,
        "-af", "afade=t=in:st=0:d=1.5,afade=t=out:st=%d:d=2" % max(0, args.sure - 2),
        "-c:a", "libmp3lame", "-b:a", args.bitrate, "-ar", "44100", "-ac", "2",
        args.cikti,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print("HATA:", r.stderr[-500:])
        return 1

    boyut = os.path.getsize(args.cikti) // 1024
    print(f"OK: {args.cikti}  ({boyut} KB, {bas}s-{bas + args.sure}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
