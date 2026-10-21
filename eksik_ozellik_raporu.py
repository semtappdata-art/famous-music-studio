# -*- coding: utf-8 -*-
"""
Eksik ozellik raporu: testlerin bekledigi ama repoda OLMAYAN API'leri listeler.

NEDEN (2026-10-21): tam test paketi 407 failure veriyordu. Bunlarin
buyuk bolumu "module X has no attribute Y" — yani test BIR OZELLIK icin
yazilmis ama ozellik (veya ozelligin bulundugu modul) repoda degil.
Bu, "kirmizi cizgi" degil: gelistirme sirasinda yazilip birakilan testler.

Bu arac:
  1) test dosyalarini AST ile tarar,
  2) `mod.attr` bicimindeki erisimleri yerel moduller icin toplar,
  3) modulun ust duzey adlarinda olmayanlari "EKSIK" olarak raporlar.

Kullanim: python eksik_ozellik_raporu.py
"""
import ast
import io
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(REPO, "tests")
YEREL_MODUL = {}


def _modul_adlari(ad):
    if ad in YEREL_MODUL:
        return YEREL_MODUL[ad]
    adlar = set()
    for kok in (REPO, TESTS, os.path.join(REPO, "upload"), os.path.join(REPO, "tools")):
        yol = os.path.join(kok, ad + ".py")
        if not os.path.isfile(yol):
            continue
        try:
            with io.open(yol, encoding="utf-8") as f:
                src = f.read()
            agac = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        for node in agac.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                adlar.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        adlar.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                adlar.add(node.target.id)
        # try/except icinde atanan sabitler de (orn. `_SENTRY_MEVCUT = False`)
        for node in ast.walk(agac):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        adlar.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                adlar.add(node.target.id)
        # IMPORT EDILEN moduller de modulun ust duzey adlaridir
        # (orn. `import requests` -> mod.requests gecerli) — aksi halde
        # HER import false-positive uretir. try/except icindeki import'lar
        # da yakalansin diye agacin TAMAMI gezilir.
        for node in ast.walk(agac):
            if isinstance(node, ast.Import):
                for n in node.names:
                    adlar.add(n.asname or n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for n in node.names:
                    if n.name != "*":
                        adlar.add(n.asname or n.name)
    YEREL_MODUL[ad] = adlar
    return adlar


def main():
    eksik = {}
    for ad in sorted(os.listdir(TESTS)):
        if not ad.startswith("test_") or not ad.endswith(".py"):
            continue
        yol = os.path.join(TESTS, ad)
        try:
            with io.open(yol, encoding="utf-8") as f:
                src = f.read()
            agac = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        # bu testin import ettigi yerel moduller
        yerel = set()
        for node in ast.walk(agac):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name.split(".")[0] not in ("os", "sys", "json", "re", "io",
                                                   "pytest", "pathlib", "shutil",
                                                   "subprocess", "time", "tempfile"):
                        yerel.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                kok = node.module.split(".")[0]
                if not kok.startswith("_") and kok not in ("pytest", "typing", "pathlib"):
                    yerel.add(kok)
        for node in ast.walk(agac):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                mod = node.value.id
                if mod not in yerel:
                    continue
                adlar = _modul_adlari(mod)
                if not adlar:
                    continue
                if node.attr not in adlar and not node.attr.startswith("__"):
                    eksik.setdefault("%s.%s" % (mod, node.attr), set()).add(ad)

    print("=" * 76)
    print("EKSIK OZELLIK RAPORU — %d API eksik" % len(eksik))
    print("=" * 76)
    for api, dosyalar in sorted(eksik.items(), key=lambda x: -len(x[1])):
        print("  %-46s %d test" % (api, len(dosyalar)))

    # markdown rapor
    satirlar = [
        "# Eksik Özellik Raporu",
        "",
        "**Tarih:** 2026-10-21  ",
        "**Üreten:** `python eksik_ozellik_raporu.py`",
        "",
        "Bu rapor, testlerin beklediği ama repoda **bulunmayan** API'leri listeler.",
        "Bunlar geliştirme sırasında yazılıp bırakılmış testlerdir — kırmızı çizgi",
        "değildir, ancak her biri ayrı bir özellik işidir.",
        "",
        "| Eksik API | Etkilenen test dosyası |",
        "|---|---|",
    ]
    for api, dosyalar in sorted(eksik.items(), key=lambda x: -len(x[1])):
        satirlar.append("| `%s` | %d |" % (api, len(dosyalar)))
    satirlar += ["", "## Modül bazlı dağılım", ""]
    modul = {}
    for api, dosyalar in eksik.items():
        modul.setdefault(api.split(".")[0], []).append(api)
    for m, apiler in sorted(modul.items(), key=lambda x: -len(x[1])):
        satirlar.append("- **%s** (%d): %s" % (m, len(apiler), ", ".join("`%s`" % a for a in sorted(apiler))))
    with io.open("EKSIK_OZELLIKLER.md", "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print()
    print("  -> EKSIK_OZELLIKLER.md yazildi (%d API)" % len(eksik))
    return 0


if __name__ == "__main__":
    sys.exit(main())
