"""git_sync.auto_pull() için testler.

Gerçek (geçici) git depoları kurup davranışı uçtan uca doğruluyor —
subprocess çağrılarını mock'lamak yerine, çünkü asıl risk git'in kendi
davranışını (fast-forward, dirty working tree, diverged history) doğru
varsaydığımızdan emin olmak."""

import subprocess

from git_sync import auto_pull


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo_pair(tmp_path):
    """origin (bare, main dalı) + iki klon (local, dev) kurar. local main'de,
    ilk commit'i (code.py + state.json) her ikisine de push'lanmış olarak
    döner."""
    remote = tmp_path / "remote.git"
    _run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], tmp_path)

    local = tmp_path / "local"
    _run(["git", "clone", "-q", str(remote), str(local)], tmp_path)
    _run(["git", "config", "user.email", "a@a.com"], local)
    _run(["git", "config", "user.name", "a"], local)
    (local / "code.py").write_text("kod v1\n")
    (local / "state.json").write_text('{"x": 1}\n')
    _run(["git", "add", "code.py", "state.json"], local)
    _run(["git", "commit", "-q", "-m", "init"], local)
    _run(["git", "push", "-q", "-u", "origin", "main"], local)

    dev = tmp_path / "dev"
    _run(["git", "clone", "-q", str(remote), str(dev)], tmp_path)
    _run(["git", "config", "user.email", "b@b.com"], dev)
    _run(["git", "config", "user.name", "b"], dev)

    return remote, local, dev


def _push_new_commit(dev, message="update code"):
    (dev / "code.py").write_text("kod v2\n")
    _run(["git", "add", "code.py"], dev)
    _run(["git", "commit", "-q", "-m", message], dev)
    _run(["git", "push", "-q", "origin", "main"], dev)


def test_fast_forward_pulls_code_and_preserves_dirty_state_file(tmp_path):
    _, local, dev = _init_repo_pair(tmp_path)
    _push_new_commit(dev)

    # runtime dosyası (state.json) yerelde commit'siz değiştirilmiş olsun —
    # tıpkı auto_process.py'nin her yüklemede yaptığı gibi.
    (local / "state.json").write_text('{"x": 2}\n')

    logs = []
    auto_pull(str(local), logs.append)

    assert (local / "code.py").read_text() == "kod v2\n"
    assert (local / "state.json").read_text() == '{"x": 2}\n'
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=local, capture_output=True, text=True, check=True
    )
    assert "state.json" in status.stdout
    assert any("otomatik güncellendi" in m for m in logs)


def test_skips_silently_on_non_main_branch(tmp_path):
    _, local, dev = _init_repo_pair(tmp_path)
    _push_new_commit(dev)
    _run(["git", "checkout", "-q", "-b", "deneme"], local)

    logs = []
    auto_pull(str(local), logs.append)

    assert (local / "code.py").read_text() == "kod v1\n"
    assert logs == []


def test_skips_silently_without_git_dir(tmp_path):
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()

    logs = []
    auto_pull(str(not_a_repo), logs.append)

    assert logs == []


def test_diverged_history_logs_and_gives_up_without_crashing(tmp_path):
    _, local, dev = _init_repo_pair(tmp_path)

    # local'de commit'li bir değişiklik yap (push'lanmamış)
    (local / "code.py").write_text("yerel değişiklik\n")
    _run(["git", "add", "code.py"], local)
    _run(["git", "commit", "-q", "-m", "yerel commit"], local)

    # uzakta da bağımsız bir commit olsun -> fast-forward imkansız
    _push_new_commit(dev, message="uzak commit")

    logs = []
    auto_pull(str(local), logs.append)  # hata fırlatmamalı

    # yerel commit korunmuş olmalı, ezilmemiş
    assert (local / "code.py").read_text() == "yerel değişiklik\n"
    assert any("atlandı" in m for m in logs)


def test_missing_git_binary_does_not_raise(tmp_path, monkeypatch):
    """git binary PATH'te yoksa auto_pull çökmemeli, OSError'ı yutmalı."""
    monkeypatch.setenv("PATH", "")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    auto_pull(str(repo), lambda m: None)  # exception fırlatırsa test zaten fail olur
