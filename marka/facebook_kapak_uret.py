# -*- coding: utf-8 -*-
"""Facebook sayfa kapagi - 2. surum.

1. surumden farklar ve NEDENLERI:
  * Logo KART KALKTI. Profil fotografi zaten ayni logo (API'den indirip
    dogruladim) ve Facebook onu kapagin uzerine bindiriyor - ayni gorsel
    ust uste iki kez cikiyordu.
  * Metin YUKARI tasindi. Profil fotografi kapagin SOL ALT kosesini
    (masaustu) / ALT ORTASINI (mobil) kapatiyor; ortaya yazilan yazi
    gercek sayfada altta kalirdi.
  * Turkce karakterler duzeldi. 1. suruмde "sarki" yaziyordu; metin artik
    drawtext'e dosyadan (textfile=, UTF-8) veriliyor, boylece kacis
    kurallarina hic girilmiyor.
"""
import io
import os
import subprocess
import sys

sys.path.insert(0, r"C:\Users\ACER\Desktop\ilk-projem")
os.chdir(r"C:\Users\ACER\Desktop\ilk-projem")

import config

G, Y = 1640, 856
logo = "docs/assets/logo.png"
cikti = sys.argv[1]
gecici = os.path.dirname(os.path.abspath(cikti))

font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")

satirlar = [
    ("Her hafta yeni \u015Fark\u0131", 84, "white@0.97", 0.26),
    ("Yapay zek\u00E2 ile \u00FCretilen orijinal m\u00FCzik", 38, "white@0.70", 0.26),
]

yollar = []
for i, (metin, _, _, _) in enumerate(satirlar):
    y = os.path.join(gecici, "kapak_metin_%d.txt" % i)
    io.open(y, "w", encoding="utf-8").write(metin)
    yollar.append(y.replace("\\", "/").replace(":", "\\:"))

# Arka plan: logonun buyutulup guclu bulaniklastirilmis hali - videolardaki
# ensure_art_backdrop ile ayni mantik, sayfa ve videolar ayni aileden gorunsun.
parcalar = [
    f"[0:v]scale={G}:{Y}:force_original_aspect_ratio=increase,crop={G}:{Y},"
    f"gblur=sigma=70,eq=brightness=0.02:saturation=1.2,"
    f"curves=all='0/0.08 0.5/0.54 1/0.90'[bg]"
]
onceki = "bg"
for i, (_, boyut, renk, ust) in enumerate(satirlar):
    ek = 0 if i == 0 else 112
    cikis = "t%d" % i
    parcalar.append(
        f"[{onceki}]drawtext=fontfile={font}:textfile='{yollar[i]}':"
        f"fontcolor={renk}:fontsize={boyut}:"
        f"shadowcolor=black@0.55:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2:y={int(Y * ust) + ek}[{cikis}]"
    )
    onceki = cikis

cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
       "-i", logo,
       "-filter_complex", ";".join(parcalar), "-map", "[%s]" % onceki,
       "-frames:v", "1", "-update", "1", cikti]
subprocess.run(cmd, check=True)
for y in yollar:
    try:
        os.remove(y.replace("\\:", ":"))
    except OSError:
        pass
print("kapak:", cikti, os.path.getsize(cikti), "bayt")
