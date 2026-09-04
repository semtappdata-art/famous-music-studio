"""watch_projects._place_stray_images() için testler — Pixlr gibi bir tasarım
aracından indirilen, adı ne olursa olsun bir görselin cover.*/art.* olarak
otomatik yerleştirilmesini doğrular."""

import watch_projects as wp


def test_single_image_without_art_becomes_cover(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    (tmp_path / "pixlr_export_1234.png").write_bytes(b"x" * 100)

    wp._place_stray_images(str(tmp_path))

    assert (tmp_path / "cover.png").is_file()
    assert not (tmp_path / "pixlr_export_1234.png").exists()


def test_image_with_art_in_name_becomes_art(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    (tmp_path / "sahne_art_final.jpg").write_bytes(b"x" * 100)

    wp._place_stray_images(str(tmp_path))

    assert (tmp_path / "art.jpg").is_file()
    assert not (tmp_path / "cover.jpg").exists()


def test_two_images_one_art_one_cover(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    (tmp_path / "kapak_tasarimi.png").write_bytes(b"x" * 100)
    (tmp_path / "kart_art_gorseli.png").write_bytes(b"x" * 100)

    wp._place_stray_images(str(tmp_path))

    assert (tmp_path / "cover.png").is_file()
    assert (tmp_path / "art.png").is_file()


def test_second_non_art_image_left_untouched_when_cover_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    (tmp_path / "cover.jpg").write_bytes(b"x" * 100)
    (tmp_path / "baska_bir_gorsel.png").write_bytes(b"x" * 100)

    wp._place_stray_images(str(tmp_path))

    # cover zaten var, "art" içermiyor -> belirsiz durum, dokunulmamalı
    assert (tmp_path / "baska_bir_gorsel.png").exists()
    assert not (tmp_path / "cover.png").exists()


def test_does_not_overwrite_existing_art(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    (tmp_path / "art.png").write_bytes(b"eski")
    (tmp_path / "yeni_art_gorseli.jpg").write_bytes(b"x" * 100)

    wp._place_stray_images(str(tmp_path))

    assert (tmp_path / "art.png").read_bytes() == b"eski"
    assert (tmp_path / "yeni_art_gorseli.jpg").exists()  # yerleştirilmedi


def test_no_stray_images_is_a_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    wp._place_stray_images(str(tmp_path))  # boş klasör, hata fırlatmamalı


def test_scan_dir_places_images_even_when_audio_already_ready(tmp_path, monkeypatch):
    """_scan_dir, audio zaten hazır olsa bile görsel yerleştirmeyi denemeli —
    kullanıcı sesi önce, kapağı sonra indirmiş olabilir."""
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    project_dir = tmp_path / "Hazir Sarki"
    project_dir.mkdir()
    (project_dir / "audio.wav").write_bytes(b"x" * 100)
    (project_dir / "pixlr_kapak.jpg").write_bytes(b"x" * 100)

    triggered = []
    monkeypatch.setattr(wp, "_trigger_script", lambda script: triggered.append(script))

    wp._scan_dir(str(tmp_path), "auto_process.py")

    assert (project_dir / "cover.jpg").is_file()
    assert triggered == []  # audio zaten hazırdı, yeniden tetiklenmemeli
