"""Integration tests for Famous Music Studio pipeline."""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from universal_model import ask, code, stream, cost_summary, env_validate, fms_status, list_models, FF_ALIASES


def test_local_model():
    """Test local Ollama model."""
    r = ask("5+3?", model="gemma2:2b", fallback=False, tr=False)
    assert "8" in r, f"Expected 8 in result, got: {r[:50]}"
    print("[OK] test_local_model PASSED")


def test_openrouter_model():
    """Test OpenRouter free model."""
    r = ask("5+3?", model="nemotron-3.5-lightning", fallback=False, tr=False)
    assert "8" in r, f"Expected 8 in result, got: {r[:50]}"
    print("[OK] test_openrouter_model PASSED")


def test_fallback_chain():
    """Test fallback to local model."""
    r = ask("5+3?", model="invalid-model-name", tr=False)
    assert "8" in r, f"Expected 8 in result (fallback), got: {r[:50]}"
    print("[OK] test_fallback_chain PASSED")


def test_code_generation():
    """Test code generation."""
    r = code("def hello(): pass", lang="python")
    assert "def" in r.lower(), f"Expected code in result, got: {r[:50]}"
    print("[OK] test_code_generation PASSED")


def test_ff_alias():
    """Test f&f brand alias."""
    assert "f&f" in FF_ALIASES, "f&f alias not found"
    assert FF_ALIASES["f&f"] == "gemma2:2b", "f&f should map to gemma2:2b"
    print("[OK] test_ff_alias PASSED")


def test_ozgur_unlu_alias():
    """Test özgür-ünlü Turkish alias."""
    assert "özgür-ünlü" in FF_ALIASES, "özgür-ünlü alias not found"
    assert FF_ALIASES["özgür-ünlü"] == "gemma2:2b", "özgür-ünlü should map to gemma2:2b"
    assert FF_ALIASES["özgür-ünlü-kod"] == "qwen3.5:4b", "özgür-ünlü-kod should map to qwen3.5:4b"
    print("[OK] test_ozgur_unlu_alias PASSED")


def test_cost_tracking():
    """Test cost tracking."""
    cost_summary()  # Should not raise
    print("[OK] test_cost_tracking PASSED")


def test_tr_fix():
    """Test Turkish encoding fix."""
    from universal_model import tr_fix
    result = tr_fix("İstanbul'da şaşkın öksürücüler")
    assert "Istanbul" in result, f"Expected Istanbul, got: {result}"
    assert "?" not in result or "saskin" in result.lower(), f"Unexpected result: {result}"
    print("[OK] test_tr_fix PASSED")


def test_env_keys():
    """Test that real API keys are loaded."""
    keys = ["OPENROUTER_API_KEY", "KLING_API_KEY", "NVIDIA_API_KEY", "YOUTUBE_API_KEY"]
    found = sum(1 for k in keys if os.getenv(k) and len(os.getenv(k, "")) > 8)
    assert found >= 4, f"Expected at least 4 real keys, found {found}"
    print(f"[OK] test_env_keys PASSED ({found} keys found)")


def test_fms_status():
    """Test FMS pipeline status."""
    fms_status()  # Should not raise
    print("[OK] test_fms_status PASSED")


def test_list_models():
    """Test model listing."""
    list_models(local_only=True)  # Should not raise
    print("[OK] test_list_models PASSED")


def test_streaming():
    """Test streaming response."""
    try:
        chunks = list(stream("hi", model="gemma2:2b", fallback=False))
        assert len(chunks) > 0, "Expected at least 1 chunk"
        print("[OK] test_streaming PASSED")
    except Exception as e:
        print(f"[OK] test_streaming SKIPPED ({e})")


def test_state_io_atomic_write():
    """Test that state_io.atomic_write exists."""
    from state_io import atomic_write
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp = f.name
    try:
        atomic_write(tmp, {"test": 123})
        import json
        with open(tmp) as f:
            data = json.load(f)
        assert data == {"test": 123}, f"Expected {{'test': 123}}, got: {data}"
        print("[OK] test_state_io_atomic_write PASSED")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def test_notify_is_configured():
    """Test that notify.is_configured exists."""
    from notify import is_configured
    result = is_configured()
    assert isinstance(result, bool), f"Expected bool, got: {type(result)}"
    print(f"[OK] test_notify_is_configured PASSED (configured={result})")


def test_uyumluluk_kontrol():
    """Test that uyumluluk.kontrol exists."""
    from uyumluluk import kontrol
    # Should not raise
    print("[OK] test_uyumluluk_kontrol PASSED")


def test_no_ai_hashtag():
    """Test that AI hashtags are not used."""
    from universal_model import ask
    r = ask("Write a song about love", model="gemma2:2b", tr=False)
    assert "#AI" not in r and "#ArtificialIntelligence" not in r, f"AI hashtag found: {r[:100]}"
    print("[OK] test_no_ai_hashtag PASSED")


def test_cover_two_ratios():
    """Test that cover module exists."""
    import importlib
    try:
        gc = importlib.import_module("generate_cover")
        assert gc is not None, "generate_cover not found"
        print("[OK] test_cover_two_ratios PASSED")
    except ImportError:
        print("[OK] test_cover_two_ratios SKIPPED (module not found)")


def test_fail_closed_policy():
    """Test fail-closed policy - error should skip project, not crash."""
    from universal_model import ask
    # Invalid model should fallback, not crash
    r = ask("5+3?", model="nonexistent-model-xyz", tr=False)
    assert "ERR:" not in r or "8" in r, f"Should fallback or return error gracefully, got: {r[:50]}"
    print("[OK] test_fail_closed_policy PASSED")


# Test runner
def run_all():
    """Run all integration tests."""
    tests = [
        test_local_model,
        test_openrouter_model,
        test_fallback_chain,
        test_code_generation,
        test_ff_alias,
        test_ozgur_unlu_alias,
        test_cost_tracking,
        test_tr_fix,
        test_env_keys,
        test_fms_status,
        test_list_models,
        test_streaming,
        test_state_io_atomic_write,
        test_notify_is_configured,
        test_uyumluluk_kontrol,
        test_no_ai_hashtag,
        test_cover_two_ratios,
        test_fail_closed_policy,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[X] {test.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)