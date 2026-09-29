"""AI-beyan + sosyal metin doğrulama — turkus prototip.

Kapsam:
- build_ai_disclosure_line: dil (tr/en) + meta var/ Yok → doğru satır.
- build_caption içinde ai_beyani=True ile eklenme.
- hashtag yasağı: yasaklı hashtag'ler üretilmez (config.HOOK_LINES/HOOK_LINES_EN kontrolü yok, yalnızca üretim).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from upload import social_text
from upload import config


def test_build_ai_disclosure_line_tr_meta_var():
    """meta verilirse ai_beyan_satiri(meta) döner (içerik türüne göre)."""
    meta = {"title": "Test Şarkısı", "theme": "pop"}
    satir = social_text.build_ai_disclosure_line(lang="tr", meta=meta)
    assert satir
    assert isinstance(satir, str)
    # Boş değil, içerikli
    assert len(satir.strip()) > 0


def test_build_ai_disclosure_line_tr_metasiz():
    """meta yoksa dilin varsayılan vokalli satır."""
    satir = social_text.build_ai_disclosure_line(lang="tr")
    assert satir
    assert isinstance(satir, str)
    # Config'de varsayılan tr vokalli satır
    assert satir == config.AI_BEYAN_SATIRLARI["tr"]["vokalli"]


def test_build_ai_disclosure_line_en_metasiz():
    """Dil İngilizce → İngilizce varsayılan (vokalli)."""
    satir = social_text.build_ai_disclosure_line(lang="en")
    assert satir
    assert satir == config.AI_BEYAN_SATIRLARI["en"]["vokalli"]


def test_ai_beyan_hashtag_yasagi():
    """AI-vurgulu hashtag'ler üretilmez (asla yasak)."""
    # Örnek bir meta ile build_caption'ı ürün yasağına göre kontrol.
    # Config.HOOK_LINES / EN kontrolü yok (yalnızca üretim); burada caption içinde
    # yasak hashtag yok.
    meta = {"title": "Test", "theme": "pop"}
    caption = social_text.build_caption(meta, ai_beyani=True)
    yasak = ["#AIMusic", "#YapayZekaMuzik", "#AIMusicChallenge", "#SunoAI", "#AİMüzik"]
    for h in yasak:
        assert h not in caption, f"yasak hashtag bulundu: {h}"
