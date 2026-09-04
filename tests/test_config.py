"""config.py için testler — özellikle next_golden_publish_time (golden-hour
zamanlama mantığı, yanlışsa videolar erken/geç yayınlanır) ve THEMES'in yapısal
bütünlüğü (validate_project.py bunun eksiksiz olduğunu varsayıyor)."""

from datetime import datetime

import config


def _tr(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=config.TR_TZ)


def test_inside_golden_hour_returns_none():
    # GOLDEN_HOURS = [(12,14), (18,22)] — 13:00 ilk pencerenin içinde
    assert config.next_golden_publish_time(_tr(2026, 9, 4, 13, 0)) is None
    assert config.next_golden_publish_time(_tr(2026, 9, 4, 19, 30)) is None


def test_just_before_window_returns_that_window_start():
    result = config.next_golden_publish_time(_tr(2026, 9, 4, 11, 59))
    assert result == _tr(2026, 9, 4, 12, 0)


def test_between_windows_returns_next_window_same_day():
    result = config.next_golden_publish_time(_tr(2026, 9, 4, 15, 0))
    assert result == _tr(2026, 9, 4, 18, 0)


def test_after_last_window_rolls_over_to_next_day():
    result = config.next_golden_publish_time(_tr(2026, 9, 4, 23, 0))
    assert result == _tr(2026, 9, 5, 12, 0)


def test_window_end_hour_is_exclusive():
    # (18,22) -> [18,22) demek, saat 22:00'ın kendisi pencerenin İÇİNDE değil
    result = config.next_golden_publish_time(_tr(2026, 9, 4, 22, 0))
    assert result == _tr(2026, 9, 5, 12, 0)


def test_all_six_catalog_themes_present_with_required_fields():
    catalog_themes = {"pop", "rock", "elektronik", "akustik", "hiphop", "arabesk"}
    assert catalog_themes.issubset(config.THEMES.keys())
    for name in catalog_themes:
        theme = config.THEMES[name]
        assert "label" in theme
        assert "language" in theme
        assert theme["language"] == "tr"  # CLAUDE.md: ana katalog tamamen TR


def test_dj_theme_is_english_and_separate_from_catalog():
    assert config.THEMES["dj"]["language"] == "en"


def test_default_theme_is_a_valid_theme_key():
    assert config.DEFAULT_THEME in config.THEMES
