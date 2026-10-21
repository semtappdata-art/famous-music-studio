# tests/test_social_text_llm.py
import os, sys, json
from unittest.mock import patch
import pytest

# Proje kökünü Python path'ine ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from upload.social_text import (
    ai_caption,
    build_caption,
    _call_llm_for_caption,
    _safe_log,
)

def test_ai_caption_returns_string_when_disabled():
    meta = {"title": "Test Şarkı", "theme": "pop", "ai_caption": False}
    assert ai_caption(meta) == ""

def test_ai_caption_returns_string_when_forced_and_llm_fails():
    meta = {"title": "Test Şarkı", "theme": "pop", "ai_caption": True}
    with patch("upload.social_text._call_llm_for_caption", return_value=None):
        result = ai_caption(meta, force=True)
        # When LLM fails but force=True, it should fall back to deterministic pool
        # and return a non-empty string (same as build_caption would produce)
        assert isinstance(result, str)
        assert result != ""  # Should not be empty - falls back to deterministic pool

def test_build_caption_returns_str_without_exception():
    meta = {
        "title": "Test Şarkı",
        "theme": "pop",
        "ai_caption": False,
        "custom_hooks": [],
        "custom_questions": [],
    }
    for platform in ("instagram","tiktok","youtube","facebook","twitter","x","bluesky","telegram"):
        result = build_caption(meta, platform=platform)
        assert isinstance(result, str)

def test_call_llm_for_caption_returns_none_on_failure():
    meta = {"title": "Test Şarkı", "theme": "pop"}
    with patch("upload.social_text.subprocess.run", side_effect=FileNotFoundError):
        assert _call_llm_for_caption(meta) is None

def test_safe_log_does_not_raise():
    with patch("upload.social_text.open", side_effect=OSError):
        try:
            _safe_log("test message")
        except Exception:
            pytest.fail("_safe_log raised an exception")
