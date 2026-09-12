"""Proje-yerel Hermes skill'i (.hermes/skills/famous-music-studio/SKILL.md) için testler.

Hermes Agent, repo kökündeki `.hermes/skills/<isim>/SKILL.md` dosyalarını (repo
`hermes skills trust` ile güvenilir işaretlendikten sonra) otomatik keşfeder. Frontmatter
bozulursa skill sessizce listeden düşer — bu testler en azından dosyanın var olduğunu,
YAML frontmatter'ının okunabildiğini ve dizin adıyla `name` alanının eşleştiğini garanti
eder. Ayrıca skill'in içinde repo'da GERÇEKTEN var olan dosyalara atıf yapıldığını kontrol
eder (yeniden adlandırma sonrası ölü referans kalmasın).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".hermes" / "skills" / "famous-music-studio"
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md YAML frontmatter ile başlamalı (--- ... ---)"
    fields = {}
    for line in m.group(1).splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"')
    return fields


def test_skill_file_exists():
    assert SKILL_MD.is_file()


def test_frontmatter_name_matches_directory():
    fm = _frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    assert fm.get("name") == SKILL_DIR.name
    assert fm.get("description"), "description alanı boş olmamalı"
    # Hermes'in yazım standardı: kısa, tek cümle, nokta ile biten description.
    assert len(fm["description"]) <= 60
    assert fm["description"].endswith(".")


def test_referenced_repo_files_exist():
    text = SKILL_MD.read_text(encoding="utf-8")
    for rel in (
        "CLAUDE.md",
        ".claude/skills/suno-video-render/SKILL.md",
        "auto_process.py",
        "render.py",
        "generate_cover.py",
        "validate_project.py",
        "setup_task_scheduler.ps1",
    ):
        assert rel in text, f"skill {rel} dosyasına atıf yapmalı"
        assert (ROOT / rel).exists(), f"skill'in atıf yaptığı {rel} repoda yok"


def test_setup_script_has_utf8_bom():
    # CLAUDE.md: .ps1 dosyaları BOM'suz kaydedilirse Windows PowerShell 5.1'de bozuluyor.
    raw = (ROOT / "setup_hermes_agent.ps1").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
