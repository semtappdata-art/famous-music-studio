"""watch_projects._scan_dir() için testler — Suno'dan indirilen, adı ne
olursa olsun bir ses dosyasının audio.* olarak yeniden adlandırılıp doğru
script'i (auto_process.py / dj_famous_process.py) tetiklediğini doğrular.
Bu, dj_sets/ (DJ Famous) desteğinin projects/ ile aynı davranışı
paylaştığını garanti eder."""

import time

import watch_projects as wp


def test_renames_stray_audio_and_triggers_given_script(tmp_path, monkeypatch):
    project_dir = tmp_path / "Bir Sarki"
    project_dir.mkdir()
    (project_dir / "Suno indirmesi.wav").write_bytes(b"x" * 100)

    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    triggered = []
    monkeypatch.setattr(wp, "_trigger_script", lambda script: triggered.append(script))

    wp._scan_dir(str(tmp_path), "dj_famous_process.py")

    assert (project_dir / "audio.wav").is_file()
    assert not (project_dir / "Suno indirmesi.wav").exists()
    assert triggered == ["dj_famous_process.py"]


def test_skips_project_that_already_has_audio(tmp_path, monkeypatch):
    project_dir = tmp_path / "Zaten Hazir"
    project_dir.mkdir()
    (project_dir / "audio.wav").write_bytes(b"x" * 100)
    (project_dir / "baska bir dosya.mp3").write_bytes(b"x" * 100)

    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    triggered = []
    monkeypatch.setattr(wp, "_trigger_script", lambda script: triggered.append(script))

    wp._scan_dir(str(tmp_path), "auto_process.py")

    # audio.wav zaten var -> "baska bir dosya.mp3" dokunulmadan kalmalı, tetiklenmemeli
    assert (project_dir / "baska bir dosya.mp3").exists()
    assert triggered == []


def test_missing_base_dir_is_a_noop(tmp_path, monkeypatch):
    triggered = []
    monkeypatch.setattr(wp, "_trigger_script", lambda script: triggered.append(script))

    wp._scan_dir(str(tmp_path / "yok"), "auto_process.py")

    assert triggered == []


def test_main_scans_both_projects_and_dj_sets(tmp_path, monkeypatch):
    monkeypatch.setattr(wp, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(wp, "PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setattr(wp, "DJ_SETS_DIR", str(tmp_path / "dj_sets"))
    monkeypatch.setattr(wp, "LOG_PATH", str(tmp_path / "watch_projects.log"))
    monkeypatch.setattr(wp, "AUTO_PROCESS_LOG_PATH", str(tmp_path / "auto_process.log"))
    monkeypatch.setattr(wp, "HEARTBEAT_MARKER_PATH", str(tmp_path / ".watchdog_alerted"))
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)

    (tmp_path / "projects" / "Ana Katalog Sarkisi").mkdir(parents=True)
    (tmp_path / "projects" / "Ana Katalog Sarkisi" / "indirilen.mp3").write_bytes(b"x" * 100)
    (tmp_path / "dj_sets" / "Bir DJ Set").mkdir(parents=True)
    (tmp_path / "dj_sets" / "Bir DJ Set" / "indirilen.wav").write_bytes(b"x" * 100)

    triggered = []
    monkeypatch.setattr(wp, "_trigger_script", lambda script: triggered.append(script))

    wp.main()

    assert (tmp_path / "projects" / "Ana Katalog Sarkisi" / "audio.mp3").is_file()
    assert (tmp_path / "dj_sets" / "Bir DJ Set" / "audio.wav").is_file()
    assert sorted(triggered) == ["auto_process.py", "dj_famous_process.py"]
