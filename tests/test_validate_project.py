"""validate_project.validate() için testler — render'dan önceki sağlık
kontrolü, bu projede tekrar tekrar düşülen hataları (bozuk ses, art==cover
metin sızıntısı, geçersiz theme) yakalamak için var (bkz. CLAUDE.md)."""

import json
import shutil
import subprocess
import wave

import pytest

import validate_project as vp

FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

requires_ffprobe = pytest.mark.skipif(not FFPROBE_AVAILABLE, reason="ffprobe bu ortamda yok")
requires_ffmpeg = pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg bu ortamda yok")


def _write_silent_wav(path, seconds=2.0, rate=44100):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))


def _write_image(path, size="64x64", color="red"):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color={color}:s={size}",
         "-frames:v", "1", str(path)],
        check=True, capture_output=True,
    )


def test_missing_audio_is_an_error(tmp_path):
    (tmp_path / "meta.json").write_text('{"theme": "pop"}', encoding="utf-8")
    errors, warnings = vp.validate(str(tmp_path))
    assert any("audio" in e for e in errors)


def test_invalid_json_meta_is_an_error(tmp_path):
    # audio.wav kasıtlı olarak yok — validate() audio kontrolünü zaten ayrı
    # test ediyor, burada sadece meta.json'daki JSON hatasına odaklanıyoruz
    # (audio yoksa ffprobe hiç çağrılmıyor, bu testi ffprobe'dan bağımsız tutar).
    (tmp_path / "meta.json").write_text("{bozuk json", encoding="utf-8")
    errors, warnings = vp.validate(str(tmp_path))
    assert any("geçersiz JSON" in e for e in errors)


def test_unknown_theme_is_an_error(tmp_path):
    (tmp_path / "meta.json").write_text('{"theme": "olmayan-tema"}', encoding="utf-8")
    errors, warnings = vp.validate(str(tmp_path))
    assert any("config.THEMES'te tanımlı değil" in e for e in errors)


def test_missing_meta_json_is_only_a_warning(tmp_path):
    errors, warnings = vp.validate(str(tmp_path))
    assert any("meta.json yok" in w for w in warnings)
    # meta.json yokluğu tek başına render'ı durdurmamalı
    assert not any("meta.json" in e for e in errors)


@requires_ffprobe
@requires_ffmpeg
def test_valid_short_audio_still_passes_when_long_enough(tmp_path):
    _write_silent_wav(tmp_path / "audio.wav", seconds=3.0)
    errors, warnings = vp.validate(str(tmp_path))
    assert not any("audio.wav" in e for e in errors)


@requires_ffprobe
@requires_ffmpeg
def test_too_short_audio_is_an_error(tmp_path):
    _write_silent_wav(tmp_path / "audio.wav", seconds=0.3)
    errors, warnings = vp.validate(str(tmp_path))
    assert any("çok kısa" in e for e in errors)


@requires_ffprobe
def test_corrupt_audio_file_is_an_error(tmp_path):
    (tmp_path / "audio.wav").write_bytes(b"bu gecerli bir wav dosyasi degil")
    errors, warnings = vp.validate(str(tmp_path))
    assert any("okunamadı" in e for e in errors)


@requires_ffprobe
@requires_ffmpeg
def test_identical_cover_and_art_triggers_text_leak_warning(tmp_path):
    _write_silent_wav(tmp_path / "audio.wav", seconds=3.0)
    _write_image(tmp_path / "cover.jpg")
    shutil.copyfile(tmp_path / "cover.jpg", tmp_path / "art.jpg")

    errors, warnings = vp.validate(str(tmp_path))

    assert any("byte-birebir aynı" in w for w in warnings)


@requires_ffprobe
@requires_ffmpeg
def test_different_cover_and_art_no_leak_warning(tmp_path):
    _write_silent_wav(tmp_path / "audio.wav", seconds=3.0)
    _write_image(tmp_path / "cover.jpg", color="red")
    _write_image(tmp_path / "art.jpg", color="blue")

    errors, warnings = vp.validate(str(tmp_path))

    assert not any("byte-birebir aynı" in w for w in warnings)


def test_file_hash_is_content_based_not_path_based(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_text("aynı içerik", encoding="utf-8")
    b.write_text("aynı içerik", encoding="utf-8")
    assert vp._file_hash(str(a)) == vp._file_hash(str(b))

    c = tmp_path / "c.bin"
    c.write_text("farklı içerik", encoding="utf-8")
    assert vp._file_hash(str(a)) != vp._file_hash(str(c))
