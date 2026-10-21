# -*- coding: utf-8 -*-
"""i18n.js degerlerindeki gereksiz <p> / </span> kapanislarini temizler (Madde 31).

SORUN: data-i18n bir <p> veya <span> icine yerlestirildiginde, degerin
kendisi de <p>...</p> ile basliyorsa HTML'de IC ICE <p> olusuyor. Tarayici
bunu otomatik duzeltir ama DOM kiridir ve bazi tarayicilar farkli render
eder.

COZUM: deger basinda <p> varsa ve sonunda </p> (veya </span></p>) varsa
kaldirilir. Ic etiketler (<strong>, <a>, <code>, <br>) KORUNUR.
"""
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

YOL = "site/i18n.js"


def temizle(deger: str) -> str:
    d = deger.strip()
    # basindaki <p> ve varyantlari
    d = re.sub(r"^<p>\s*", "", d)
    # sondaki kapanislar
    d = re.sub(r"\s*</span>\s*</p>\s*$", "", d)
    d = re.sub(r"\s*</p>\s*</span>\s*$", "", d)
    d = re.sub(r"\s*</p>\s*$", "", d)
    d = re.sub(r"\s*</span>\s*$", "", d)
    return d


def main():
    with open(YOL, encoding="utf-8") as f:
        js = f.read()

    # tek satirlik "anahtar': 'deger'," kaliplarini bul
    desen = re.compile(r"^(\s*)'([a-z0-9_.]+)': '(.*)',$", re.M)
    degisen = []

    def yazici(m):
        girinti, anahtar, deger = m.group(1), m.group(2), m.group(3)
        yeni = temizle(deger)
        if yeni != deger:
            degisen.append(anahtar)
            return "%s'%s': '%s'," % (girinti, anahtar, yeni)
        return m.group(0)

    yeni_js = desen.sub(yazici, js)

    with open(YOL, "w", encoding="utf-8") as f:
        f.write(yeni_js)
    print("  i18n.js: %d deger temizlendi" % len(degisen))
    for a in degisen[:12]:
        print("    - " + a)
    if len(degisen) > 12:
        print("    ... +%d" % (len(degisen) - 12))


if __name__ == "__main__":
    main()
