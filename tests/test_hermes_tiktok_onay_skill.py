# -*- coding: utf-8 -*-
"""Hermes becerisi `.hermes/skills/tiktok-yayin-onayi/SKILL.md` için testler.

Beceri, Telegram'dan gelen "yayınladım <ad>" yanıtını (Hermes gateway'i zaten
dinliyor; bot paylaşılıyor, depoda getUpdates YOK) TEK bir betiğe çeviriyor.
Bu testler becerinin DAR kalmasını çiviliyor: tek komut kalıbı, açık yasaklar,
geçerli frontmatter. Beceri genişlerse (ör. "gerekirse state.json'u düzelt"),
Telegram'dan gelen kısa bir mesaj depoda keyfi değişiklik yapabilen bir kapıya
dönüşür.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hermes_skill import _frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".hermes" / "skills" / "tiktok-yayin-onayi"
SKILL_MD = SKILL_DIR / "SKILL.md"
BETIK_REL = "upload/tiktok_yayin_onayi.py"


def _metin():
    return SKILL_MD.read_text(encoding="utf-8")


def test_beceri_dosyasi_ve_frontmatter():
    assert SKILL_MD.is_file()
    ham = SKILL_MD.read_bytes()
    assert b"\r\n" not in ham, "frontmatter regex'i LF bekliyor"
    fm = _frontmatter(_metin())
    assert fm.get("name") == SKILL_DIR.name
    assert fm.get("description")
    assert len(fm["description"]) <= 60
    assert fm["description"].endswith(".")


def test_tetikleyici_yayinladim():
    assert re.search(r"(?m)^triggers:\s*$", _metin())
    assert re.search(r"(?m)^\s+-\s+yayınladım", _metin())


def test_tek_komut_kalibi():
    metin = _metin()
    komutlar = re.findall(r"(?m)^\s*python\s+\S+.*$", metin)
    assert komutlar, "beceri çalıştırılacak komutu açıkça yazmalı"
    for k in komutlar:
        assert k.strip().split()[1].replace("\\", "/").endswith(BETIK_REL), k
        assert re.fullmatch(r"\s*python\s+\S+\s+'<ad>'\s*", k), (
            "tek argüman, tek tırnak içinde, başka bayrak/boru yok: %r" % k)
    assert (ROOT / BETIK_REL).is_file()


def test_kod_bloklarinda_baska_komut_yok():
    bloklar = re.findall(r"```[a-z]*\n(.*?)```", _metin(), re.S)
    assert bloklar
    for blok in bloklar:
        for satir in blok.splitlines():
            if satir.strip():
                assert satir.strip().startswith("python "), satir


def test_yasaklar_acikca_yazili():
    metin = _metin().lower()
    for ifade in ("başka komut", "git", "dosya düzenleme", "state.json",
                  "getupdates", "belirsiz"):
        assert ifade in metin, "beceri şunu açıkça ele almalı: %s" % ifade


def test_yasak_eylemler_komut_olarak_gecmiyor():
    metin = _metin()
    for yasak in ("--yayinlandi-hepsi", "--dogrulandi", "git commit", "git push",
                  "rm -", "curl ", "Invoke-WebRequest"):
        assert yasak not in metin, yasak
