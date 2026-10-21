# -*- coding: utf-8 -*-
"""Ko-fi destek satiri — build_snippet'e baglanma testi.

UC SORU (CLAUDE.md section 9):
1. Kim cagiriyor? upload/youtube_upload.build_snippet (upload_video,
   update_metadata, youtube_studio, mcp_postwire buradan snippet alir).
2. Hangi gorevden? saatlik auto_process.py (uzun format yukleme yolu).
3. Calismadigini nasil anlariz? Bu test FAIL + haftalik raporda aciklama
   orneginde ko-fi satiri yok.

Kural: KOFI_URL doluyken description'da ko-fi linki OLMALI, bosken OLMAMALI.
"""

import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))


def test_kofi_dolu_tr():
    import config
    from youtube_upload import build_snippet
    eski = config.KOFI_URL
    try:
        config.KOFI_URL = "https://ko-fi.com/famousmusicstudio"
        d = build_snippet({"title": "Test", "theme": "pop", "language": "tr"})["description"]
        assert "ko-fi.com/famousmusicstudio" in d
        assert "Bizi destekle" in d
    finally:
        config.KOFI_URL = eski


def test_kofi_dolu_en():
    import config
    from youtube_upload import build_snippet
    eski = config.KOFI_URL
    try:
        config.KOFI_URL = "https://ko-fi.com/famousmusicstudio"
        d = build_snippet({"title": "Night Drive", "theme": "dj", "language": "en"})["description"]
        assert "ko-fi.com/famousmusicstudio" in d
        assert "Support us" in d
    finally:
        config.KOFI_URL = eski


def test_kofi_bos_satir_yok():
    import config
    from youtube_upload import build_snippet
    eski = config.KOFI_URL
    try:
        config.KOFI_URL = ""
        d = build_snippet({"title": "Test", "theme": "pop", "language": "tr"})["description"]
        assert "ko-fi" not in d
    finally:
        config.KOFI_URL = eski


def test_kofi_varsayilan_dolu():
    import config
    # config.py varsayilani: sayfa acildi, bos degil
    assert (config.KOFI_URL or "") != ""


def test_kofi_token_dosyada():
    import json
    yol = os.path.join(REPO, ".secrets", "kofi.json")
    assert os.path.isfile(yol), ".secrets/kofi.json yok"
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    assert veri.get("page_url") == "https://ko-fi.com/famousmusicstudio"
    assert len(veri.get("verification_token", "")) >= 8
