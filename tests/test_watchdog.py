"""watch_projects._check_heartbeat() için testler — auto_process.log çok
uzun süre güncellenmezse (Görev Zamanlayıcı görevi tetiklenmiyor demektir)
tek seferlik bir telefon uyarısı gönderiyor mu, spam yapmıyor mu, sağlık geri
gelince tekrar uyarabiliyor mu."""

import os
import time

import watch_projects as wp


def _set_paths(monkeypatch, tmp_path):
    auto_log = tmp_path / "auto_process.log"
    marker = tmp_path / ".watchdog_alerted"
    monkeypatch.setattr(wp, "AUTO_PROCESS_LOG_PATH", str(auto_log))
    monkeypatch.setattr(wp, "HEARTBEAT_MARKER_PATH", str(marker))
    return auto_log, marker


def test_no_auto_process_log_yet_is_a_noop(monkeypatch, tmp_path):
    _auto_log, marker = _set_paths(monkeypatch, tmp_path)
    sent = {"count": 0}
    monkeypatch.setattr(wp.notify, "send", lambda *a, **k: sent.__setitem__("count", sent["count"] + 1) or True)

    wp._check_heartbeat()

    assert sent["count"] == 0
    assert not marker.exists()


def test_fresh_log_sends_no_alert(monkeypatch, tmp_path):
    auto_log, marker = _set_paths(monkeypatch, tmp_path)
    auto_log.write_text("[son çalıştırma]\n")

    sent = {"count": 0}
    monkeypatch.setattr(wp.notify, "send", lambda *a, **k: sent.__setitem__("count", sent["count"] + 1) or True)

    wp._check_heartbeat()

    assert sent["count"] == 0
    assert not marker.exists()


def test_stale_log_sends_exactly_one_alert(monkeypatch, tmp_path):
    auto_log, marker = _set_paths(monkeypatch, tmp_path)
    auto_log.write_text("eski\n")
    stale_time = time.time() - wp.HEARTBEAT_STALE_SECONDS - 3600  # eşiğin 1 saat üzeri
    os.utime(auto_log, (stale_time, stale_time))

    sent_calls = []
    monkeypatch.setattr(wp.notify, "send", lambda title, msg: sent_calls.append((title, msg)) or True)

    wp._check_heartbeat()
    assert len(sent_calls) == 1
    assert marker.exists()

    # aynı durum devam ederken tekrar çağrılırsa SPAM yapmamalı
    wp._check_heartbeat()
    assert len(sent_calls) == 1


def test_recovery_clears_marker_and_allows_realert_on_new_outage(monkeypatch, tmp_path):
    auto_log, marker = _set_paths(monkeypatch, tmp_path)
    auto_log.write_text("eski\n")
    stale_time = time.time() - wp.HEARTBEAT_STALE_SECONDS - 3600
    os.utime(auto_log, (stale_time, stale_time))

    sent_calls = []
    monkeypatch.setattr(wp.notify, "send", lambda title, msg: sent_calls.append((title, msg)) or True)

    wp._check_heartbeat()
    assert len(sent_calls) == 1
    assert marker.exists()

    # log tazelendi (otomasyon toparlandı)
    auto_log.write_text("yeni çalıştırma\n")
    wp._check_heartbeat()
    assert not marker.exists()  # sağlık geri geldi, marker temizlendi

    # yeniden bayatlarsa TEKRAR uyarabilmeli
    os.utime(auto_log, (stale_time, stale_time))
    wp._check_heartbeat()
    assert len(sent_calls) == 2


def test_failed_notification_does_not_set_marker_so_it_retries(monkeypatch, tmp_path):
    auto_log, marker = _set_paths(monkeypatch, tmp_path)
    auto_log.write_text("eski\n")
    stale_time = time.time() - wp.HEARTBEAT_STALE_SECONDS - 3600
    os.utime(auto_log, (stale_time, stale_time))

    monkeypatch.setattr(wp.notify, "send", lambda *a, **k: False)  # ntfy yok/başarısız

    wp._check_heartbeat()

    assert not marker.exists()  # başarısız gönderim -> bir dahaki dakika tekrar denenmeli
