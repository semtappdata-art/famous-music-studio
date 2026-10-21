#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
site/index.html icindeki inline JS'lerde brace dengesini kontrol eder.

Kullanim:
    python check_js_braces.py            # rapor
    python check_js_braces.py --check    # hata varsa exit 1 (CI icin)

NEDEN VAR (2026-10-21): Madde 31 (i18n) sirasinda "fazla }" hatasindan
dolayi TUM ana script cokmus, tarayici konsolunda SyntaxError veriyordu.
Testler yesil kalirken sayfa calismiyordu. Bu modul, inline script'lerde
brace dengesini denetler.

DIKKAT: string/template literal icindeki parantezler sayilmaz.
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
SITE_HTML = os.path.join(REPO, "site", "index.html")

_RE_TEK = re.compile(r"'(\\.|[^'\\])*'")
_RE_CIFT = re.compile(r'"(\\.|[^"\\])*"')
_RE_TEMPLATE = re.compile(r"`(\\.|[^`\\])*`")
_RE_YORUM = re.compile(r"//.*$")


def _satiri_temizle(satir):
    t = _RE_TEK.sub("''", satir)
    t = _RE_CIFT.sub('""', t)
    t = _RE_TEMPLATE.sub("``", t)
    t = _RE_YORUM.sub("", t)
    return t


def inline_scriptler(html):
    return re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.S)


def script_dengesi(script):
    """(satir_no, metin, derinlik). Hata varsa ilk negatif derinlikte durur."""
    lines = script.split("\n")
    depth = 0
    for i, l in enumerate(lines):
        t = _satiri_temizle(l)
        for ch in t:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
        if depth < 0:
            return (i + 1, l.strip(), depth)
    return (None, None, depth)


def kontrol(dosya=None):
    yol = dosya or SITE_HTML
    try:
        with open(yol, encoding="utf-8") as f:
            html = f.read()
    except OSError as e:
        return [{"script": -1, "satir": 0, "metin": str(e), "tip": "dosya", "derinlik": 0}]

    sorunlar = []
    for i, s in enumerate(inline_scriptler(html)):
        if "application/ld+json" in s[:200]:
            continue
        satir, metin, derinlik = script_dengesi(s)
        if satir is not None:
            sorunlar.append({
                "script": i, "satir": satir, "metin": metin,
                "tip": "fazla }", "derinlik": derinlik,
            })
        elif derinlik != 0:
            sorunlar.append({
                "script": i, "satir": 0, "metin": "",
                "tip": "kapanmamis {", "derinlik": derinlik,
            })
    return sorunlar


def main():
    kontrol_modu = "--check" in sys.argv
    sorunlar = kontrol()
    if not sorunlar:
        print("JS brace dengesi TAMAM — inline script'lerde sorun yok.")
        return 0
    print("JS brace DENGESIZ:")
    for s in sorunlar:
        print("  script #%s satir %s: %s (derinlik %s) %s" % (
            s["script"], s["satir"], s["tip"], s.get("derinlik"), s["metin"][:60]))
    return 1 if kontrol_modu else 0


if __name__ == "__main__":
    sys.exit(main())
