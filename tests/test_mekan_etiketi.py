"""Mekan etiketi (`meta.json`daki `mekan` alanı).

Kural: mekan doluysa `#EiffelNights` YouTube görünür hashtag bloğunda,
görünmez tags'te, Shorts/kesit tags'te, build_caption'da ve TikTok kit
açıklamasında çıkar; boş/yoksa hiçbir çıktı değişmez (eski setler bayt
bayt aynı kalır).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "upload"))

from social_text import (build_caption, mekan_etiketleri,
                         tiktok_kit_hashtagleri)
from youtube_upload import build_shorts_snippet, build_snippet


def _meta(**kw):
    m = {"title": "Deep Medusa | Eiffel Nights", "theme": "dj",
         "artist": "DJ Famous", "set_style": "deep_house",
         "mekan": "Eiffel Nights"}
    m.update(kw)
    return m


def test_yardimci_bosken_bos():
    assert mekan_etiketleri({"title": "X"}) == []
    assert mekan_etiketleri({"title": "X", "mekan": "  "}) == []


def test_youtube_gorunur_ve_gorunmez():
    sn = build_snippet(_meta())
    assert "#EiffelNights" in sn["description"]
    assert "Eiffel Nights" in sn["tags"]


def test_shorts_tags():
    sn = build_shorts_snippet(_meta())
    assert "Eiffel Nights" in sn["tags"]


def test_caption_ve_kit():
    assert "#EiffelNights" in build_caption(_meta())
    assert "#EiffelNights" in tiktok_kit_hashtagleri(_meta())


def test_mekansiz_set_degismez():
    eski = {"title": "Night Drive", "theme": "dj",
            "set_style": "techno_chill"}
    sn = build_snippet(eski)
    assert "Eiffel" not in sn["description"]
    assert "Eiffel" not in " ".join(sn["tags"])
    assert "#EiffelNights" not in build_caption(eski)
    assert "#EiffelNights" not in tiktok_kit_hashtagleri(eski)
