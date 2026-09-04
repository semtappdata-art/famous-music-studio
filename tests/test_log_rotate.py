"""log_rotate.trim_log() için testler."""

import time

from log_rotate import trim_log


def _ts(days_ago: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days_ago * 86400))


def test_drops_lines_older_than_cutoff(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        f"[{_ts(10)}] eski satır\n"
        f"[{_ts(1)}] yeni satır\n",
        encoding="utf-8",
    )

    trim_log(str(log), days=7)

    content = log.read_text(encoding="utf-8")
    assert "eski satır" not in content
    assert "yeni satır" in content


def test_missing_file_is_a_noop(tmp_path):
    log = tmp_path / "yok.log"
    trim_log(str(log))  # dosya yok, hata fırlatmamalı
    assert not log.exists()


def test_multiline_entry_grouped_with_preceding_timestamp(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        f"[{_ts(1)}] hata oluştu\n"
        "  Traceback (most recent call last):\n"
        "    ValueError: bir şey\n",
        encoding="utf-8",
    )

    trim_log(str(log), days=7)

    content = log.read_text(encoding="utf-8")
    assert "Traceback" in content
    assert "ValueError" in content


def test_old_multiline_entry_is_dropped_entirely(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        f"[{_ts(10)}] hata oluştu\n"
        "  Traceback (most recent call last):\n"
        f"[{_ts(1)}] yeni satır\n",
        encoding="utf-8",
    )

    trim_log(str(log), days=7)

    content = log.read_text(encoding="utf-8")
    assert "Traceback" not in content
    assert "yeni satır" in content


def test_unparseable_timestamp_line_kept_with_previous_group(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        f"[{_ts(1)}] normal satır\n"
        "[bozuk-zaman-damgası] garip bir satır\n",
        encoding="utf-8",
    )

    trim_log(str(log), days=7)

    content = log.read_text(encoding="utf-8")
    assert "garip bir satır" in content
