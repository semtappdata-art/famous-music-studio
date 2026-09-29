"""_llm_cache modülü testi — önbellek çalışmalı, hata değil."""

import os
import tempfile
from unittest.mock import patch

import pytest


def test_cache_başarılı_istek():
    """LLM başarılıysa cache'e yazılır."""
    from _llm_cache import caption_cache, cache_temizle

    meta = {"title": "Test Şarkı Cache"}
    cache_temizle(meta)

    sonuc = caption_cache(meta, lambda: "Yeni AI caption")
    assert sonuc == "Yeni AI caption"

    # Tekrar çağrıda cache'ten gelir
    sonuc2 = caption_cache(meta, lambda: (_ for _ in ()).throw(RuntimeError("yok")))
    assert sonuc2 == "Yeni AI caption"

    cache_temizle(meta)


def test_cache_başarısız_empty():
    """LLM başarısız + cache boş → boş string (hata değil)."""
    from _llm_cache import caption_cache, cache_temizle

    meta = {"title": "Test Şarkı Cache Boş"}
    cache_temizle(meta)

    sonuc = caption_cache(
        meta,
        lambda: (_ for _ in ()).throw(RuntimeError("tüm başarısız")),
    )
    assert sonuc == ""


def test_cache_force():
    """force=True ile cache atlanır."""
    from _llm_cache import caption_cache, cache_temizle

    meta = {"title": "Test Şarkı Force"}
    cache_temizle(meta)

    # İlk çağrı cache'e yazar
    caption_cache(meta, lambda: "İlk")

    # Force=False (varsayılan) → cache'den gelir
    sonuc = caption_cache(meta, lambda: "İkinci")
    assert sonuc == "İlk"

    # Force=True → LLM çağrılır
    sonuc2 = caption_cache(meta, lambda: "İkinci", force=True)
    assert sonuc2 == "İkinci"

    cache_temizle(meta)


def test_cache_temizle():
    """cache_temizle çalışır."""
    from _llm_cache import caption_cache, cache_temizle

    meta = {"title": "Test Şarkı Temizle"}
    cache_temizle(meta)

    caption_cache(meta, lambda: "X")
    assert cache_temizle(meta) == 1
    # Bellekte bir şey kalmamış
    assert cache_temizle() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])