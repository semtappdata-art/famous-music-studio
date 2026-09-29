"""_llm_router modülünün temel davranışını test eder.

- openai paketi yoksa tüm sağlayıcılar None döner (fail-open)
- provider_status her zaman dict döner (asla exception değil)
- llm_chat anahtar yoksa RuntimeError fırlatır (fail-closed)
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest


def test_provider_status_her_zaman_dict():
    """Anahtar hiç yok bile durum raporu dictionary döner."""
    from _llm_router import provider_status
    # os.getenv'i mock'la — hiçbir anahtar yok
    with patch("os.getenv", return_value=None):
        sonuc = provider_status()
    assert isinstance(sonuc, dict)
    for name, info in sonuc.items():
        assert "configured" in info
        assert "client_ok" in info
        assert "models" in info
        assert info["configured"] is False
        assert info["client_ok"] is False
        assert info["models"] == []


def test_llm_chat_anahtarsiz_hata():
    """Hiç anahtar yoksa RuntimeError fırlatır (fail-closed)."""
    from _llm_router import llm_chat
    with patch("os.getenv", return_value=None):
        with pytest.raises(RuntimeError, match="Tüm LLM sağlayıcılar"):
            llm_chat([{"role": "user", "content": "test"}])


def test_llm_chat_openai_yoksa_graceful(monkeypatch):
    """openai paketi yüklü değilse hiçbir şey çökmesin."""
    monkeypatch.setitem(sys.modules, "openai", None)
    import importlib
    import _llm_router
    importlib.reload(_llm_router)
    sonuc = _llm_router.provider_status()
    assert all(v["client_ok"] is False for v in sonuc.values())


def test_llm_chat_env_anahtari_belirli_saglayici(monkeypatch):
    """Ortam anahtarı varsa o sağlayıcı configured=True döner."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
    import importlib
    import _llm_router
    importlib.reload(_llm_router)
    sonuc = _llm_router.provider_status()
    assert sonuc["openrouter"]["configured"] is True
    # Client oluşturulur (anahtar var) ama API denemede hata verebilir
    assert sonuc["openrouter"]["client_ok"] is True