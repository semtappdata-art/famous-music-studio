# -*- coding: utf-8 -*-
"""
Failing testleri ikiye ayirir:
  A) OLU TEST  — test, repoda OLMAYAN bir API'yi bekliyor (AttributeError /
                unexpected keyword / bilinmeyen modul). Ozellik kodla birlikte
                repoya girmedi. -> collection'dan cikarilmali.
  B) GERCEK REGRESYON — test, VAR OLAN bir API'nin yanlis davranisini
                test ediyor. -> DUZELTILMELI.

Kullanim: python classify_failures.py
"""
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
TESTS = os.path.join(REPO, "tests")

# "Olmayan API" imzalari
OLU_IMZALARI = [
    r"AttributeError: module '[^']+' has no attribute",
    r"TypeError: \w+\(\) got an unexpected keyword argument",
    r"ImportError: cannot import name",
    r"ModuleNotFoundError: No module named",
    r"AttributeError: module '[^']+' has no attribute '\w+'",
    r"NameError: name '\w+' is not defined",
]


def hata_metinleri():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
         "--tb=line", "-rf"],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    return r.stdout + (r.stderr or "")


def main():
    cikti = hata_metinleri()
    satirlar = [s for s in cikti.splitlines() if "::" in s and ("FAILED" in s or "ERROR" in s)]
    dosyalar = {}
    for s in satirlar:
        m = re.search(r"(?:FAILED|ERROR)\s+(tests/[\w./]+\.py)", s)
        if m:
            dosyalar.setdefault(m.group(1), []).append(s.strip())

    # hata detaylarini dosya bazinda topla
    detay = {}
    for ad in dosyalar:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", ad, "-q", "-p", "no:cacheprovider", "--tb=line"],
            cwd=REPO, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300,
        )
        detay[ad] = r.stdout + (r.stderr or "")

    olu, gercek = [], []
    for ad, _ in sorted(dosyalar.items()):
        d = detay.get(ad, "")
        olu_imza = None
        for imza in OLU_IMZALARI:
            m = re.search(imza, d)
            if m:
                olu_imza = m.group(0)
                break
        if olu_imza:
            olu.append((ad, len(dosyalar[ad]), olu_imza[:80]))
        else:
            gercek.append((ad, len(dosyalar[ad]), ""))

    print("=" * 78)
    print("A) OLU TEST (repoda olmayan API bekleniyor) — %d dosya" % len(olu))
    print("=" * 78)
    for ad, n, imza in olu:
        print("  %-46s %3d  %s" % (ad.replace("tests/", ""), n, imza))
    print()
    print("=" * 78)
    print("B) GERCEK REGRESYON (var olan API yanlis davranis) — %d dosya" % len(gercek))
    print("=" * 78)
    for ad, n, _ in gercek:
        print("  %-46s %3d" % (ad.replace("tests/", ""), n))
    print()
    toplam = sum(n for _, n, _ in olu) + sum(n for _, n, _ in gercek)
    print("TOPLAM: %d basarisiz (%d olu + %d gercek regresyon)"
          % (toplam, sum(n for _, n, _ in olu), sum(n for _, n, _ in gercek)))


if __name__ == "__main__":
    main()
