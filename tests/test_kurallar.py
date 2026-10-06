# -*- coding: utf-8 -*-
"""CLAUDE.md KURAL GATE — CI'da zorunlu gecen testler.

Kural: Yeni kural eklendiginde BURAYA test eklenir. Doc rotlamaz.
Calistirma: pytest tests/test_kurallar.py -q -p no:cacheprovider
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", "assets",
    "projects", "dj_sets", "derlemeler",
    ".pi", ".hermes", ".claude", "gorev_izleri", "logs",
}

SKIP_FILES = {"test_kurallar.py"}


def _iter_py_files():
    for p in REPO_ROOT.rglob("*.py"):
        parts = set(p.parts)
        if parts & SKIP_DIRS:
            continue
        if p.stat().st_size > 2_000_000:
            continue
        yield p


def _search_in_files(pattern: str):
    rx = re.compile(pattern)
    hits = []
    for f in _iter_py_files():
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                rel = f.relative_to(REPO_ROOT).as_posix()
                hits.append(f"{rel}:{i}:{line.strip()[:160]}")
    return hits


def _hassas_dosya_ara(adlar):
    out = set()
    for f in _iter_py_files():
        if f.name in adlar:
            out.add(f.relative_to(REPO_ROOT).as_posix())
    return out


# 1. STATE — sadece state_io.atomic_write()
def test_state_io_tek_yazici():
    hits = _search_in_files(r'open\([^)]*state\.json[^)]*["\']w')
    violations = [h for h in hits if "state_io.py" not in h]
    assert not violations, (
        "state.json dogrudan open(..., 'w') ile yaziliyor — state_io.atomic_write() KULLAN:\n"
        + "\n".join(violations[:10])
    )


def test_state_io_atomik_fonksiyon_var():
    import state_io
    assert callable(state_io.atomic_write)


# 2. _is_fully_done() yasak platform
def test_is_fully_done_yasak_platform():
    content = (REPO_ROOT / "auto_process.py").read_text(encoding="utf-8")
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_is_fully_done":
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Constant) and isinstance(stmt.value, str):
                    val = stmt.value.lower()
                    for b in ["tiktok", "instagram", "facebook", "telegram", "bluesky"]:
                        if b in val and not any(f in val for f in ["video_id", "media_id", "privacy", "publish_at"]):
                            raise AssertionError(f"_is_fully_done() icinde platform: {stmt.value}")


# 3. FAIL-CLOSED — 7 dosya
def test_fail_closed_7_nokta():
    hits = _search_in_files(r"uyumluluk\.kontrol\(")
    files = {h.split(":")[0] for h in hits}
    assert len(files) >= 7, f"Fail-closed cagri az ({len(files)}): {sorted(files)}"


def test_uyumluluk_try_except_ayri():
    content = (REPO_ROOT / "uyumluluk.py").read_text(encoding="utf-8")
    assert content.count("try:") >= 2, "karar ve rapor icin ayri try/except gerekli"


# 4. NOTIFY
def test_notify_is_configured_kontrolu():
    assert "def is_configured" in (REPO_ROOT / "notify.py").read_text(encoding="utf-8")
    hits = _search_in_files(r"notify\.(send|send_text|send_photo)\(")
    for h in hits:
        fp = h.split(":")[0]
        if "test_" in fp or fp.endswith("notify.py"):
            continue
        text = (REPO_ROOT / fp).read_text(encoding="utf-8", errors="ignore")
        # Kural: ya onceden is_configured kontrolu, ya donus degeri kontrolu
        ok = ("is_configured" in text
              or "= notify.send" in text or "= notify.send_text" in text
              or "= notify.send_photo" in text or "if notify.send" in text)
        assert ok, f"{fp}: notify gonderimi kontrolsuz"


# 5. MASK ELEME
def test_gizli_maskele_log_icinde():
    content = (REPO_ROOT / "gorev_sarmalayici.py").read_text(encoding="utf-8")
    assert "def _yaz(" in content, "_yaz() bulunamadi"
    assert "maskele" in content.lower(), "maskeleme yok"
    i = content.index("def _yaz(")
    assert "maskel" in content[i:i + 1500].lower(), "_yaz() icinde maskeleme yok"


# 6. YASAK HASHTAG (yorum degil gercek liste degerleri)
def test_yasak_ai_hashtag_yok():
    import config
    yasak = ["AIMusic", "YapayZekaMuzik", "AIMusicChallenge", "SunoAI"]
    vals = []
    for ad in ["BRAND_HASHTAGS", "DISCOVERY_HASHTAGS", "DISCOVERY_HASHTAGS_EN",
               "HOOK_LINES", "HOOK_LINES_EN"]:
        v = getattr(config, ad, None)
        if isinstance(v, list):
            vals.extend([str(x) for x in v])
    birlesik = " ".join(vals)
    for y in yasak:
        assert y.lower() not in birlesik.lower(), f"Yasak hashtag listelerde: {y}"


# 7. KAPAK IKI ORAN
def test_kapak_iki_oran():
    content = (REPO_ROOT / "generate_cover.py").read_text(encoding="utf-8")
    assert "cover_vertical.png" in content
    assert "cover.png" in content


# 8. DRAWTEXT
def test_drawtext_satir_sonu():
    content = (REPO_ROOT / "generate_cover.py").read_text(encoding="utf-8")
    assert "DRAWTEXT_SATIR_SONU" in content


# 9. TURKCE LOWER
def test_turkce_lower_norm_word():
    content = (REPO_ROOT / "caption_align.py").read_text(encoding="utf-8")
    assert "_norm_word" in content
    assert "lower()" in content


# 10. DRAWTEXT'TE LITERAL \n YOK (hizli, sadece generate_cover + ffmpeg_utils)
def test_ters_egik_cizgi_drawtext_yasak():
    for name in ["generate_cover.py", "ffmpeg_utils.py"]:
        p = REPO_ROOT / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                v = node.value
                # drawtext iceren stringlerde gercek 0x0A disinda kacis kontrolu
                if "drawtext" in v and "\\n" in repr(v):
                    # repr'da \\n varsa kaynakta literal \n olabilir — satir bazli dogrula
                    pass
        # Kaynak satir kontrolu: drawtext satirinda "\\n" literal varsa hata
        for i, line in enumerate(text.splitlines(), 1):
            if "drawtext" in line.lower() and "\\n" in line:
                if "DRAWTEXT_SATIR_SONU" not in line and "chr(10)" not in line:
                    raise AssertionError(f"{name}:{i}: drawtext'te literal \\n YASAK")


# 11. SARMALAYICI 3 GOREV
def test_gorev_sarmalayici_uc_gorev():
    content = (REPO_ROOT / "setup_task_scheduler.ps1").read_text(encoding="utf-8")
    for r in ["auto_process.py", "dj_famous_process.py", "watch_projects.py"]:
        assert r in content, f"{r} referansi yok"
    assert "gorev_sarmalayici" in content


# 12. GOLDEN HOUR
def test_golden_hour_platform_stratejisi():
    content = (REPO_ROOT / "config.py").read_text(encoding="utf-8")
    assert "GOLDEN_HOURS" in content
    assert "next_golden_publish_time" in content
