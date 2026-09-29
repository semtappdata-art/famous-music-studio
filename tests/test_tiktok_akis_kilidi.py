# -*- coding: utf-8 -*-
"""TikTok akış kilidi (2026-09-29): web_planla tek yol, api_taslak donduruldu.

`config.TIKTOK_AKIS = "web_planla"` iken yeni kod API taslak yüklemesi
(`tiktok_upload.upload_video`) çağıramaz. Eski yol yalnız iki legacy dalda
yaşar (api_taslak moduna dönülürse): `auto_process._tiktok_adimi` ve
`dj_famous_process` — ikisi de `tiktok_web_modu()` kapısının arkasında
(bu kapılar test_tiktok_web.py'de davranışla kilitli). Bu test LİSTEYİ
kilitler: izinsiz üçüncü bir çağıran sessizce API yolunu diriltmesin.
"""

import ast
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IZINLI = {"auto_process.py", "dj_famous_process.py"}

ATLAMA = (".claude", ".git", ".scratchpad", "__pycache__", ".pytest_cache")


def _dosyalar():
    for kok, altlar, dosyalar in os.walk(_REPO):
        altlar[:] = [a for a in altlar if a not in ATLAMA and not a.startswith(".")]
        for d in dosyalar:
            if d.endswith(".py"):
                yield os.path.join(kok, d)


def _tiktok_upload_video_kullanan(yol):
    try:
        agac = ast.parse(open(yol, encoding="utf-8").read())
    except (OSError, SyntaxError):
        return False
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.ImportFrom) and dugum.module == "tiktok_upload":
            if any(a.name == "upload_video" for a in dugum.names):
                return True
        if isinstance(dugum, ast.Attribute) and dugum.attr == "upload_video":
            return True
    return False


def test_upload_video_cagiranlar_izinli_listede():
    kullanan = set()
    for yol in _dosyalar():
        if os.path.join("tests", "") in yol:
            continue
        if _tiktok_upload_video_kullanan(yol):
            kullanan.add(os.path.basename(yol))
    assert kullanan <= IZINLI, "yeni API taslak çağıranı: %s" % sorted(kullanan - IZINLI)


def test_web_modu_varsayilan_acik():
    import sys
    sys.path.insert(0, _REPO)
    import config
    assert config.TIKTOK_AKIS == "web_planla"
    assert config.tiktok_web_modu() is True
