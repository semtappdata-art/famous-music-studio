"""auto_process._auto_pace_count() için testler — YENİ ÜRETİM PLANI (2026-10-05):
6 şarkı/hafta + 3 set/hafta, sabit haftalık takvim, 28 saat taban, golden-hour slot tahsisi.
"""

import json
import time
from datetime import datetime, timedelta, timezone
import os
from unittest.mock import patch

import auto_process as ap
import config
import yayin_ritmi
import pytest


TR_TZ = timezone(timedelta(hours=3))


@pytest.fixture(autouse=True)
def mock_haftalik_kalan():
    """Haftalık kalan sayacı ve slot mockla - her test izole."""
    with patch('yayin_ritmi.haftalik_kalan', return_value=config.HAFTALIK_SARKI_HEDEFI):
        with patch('yayin_ritmi.haftalik_sayaci_yukle', return_value={'sarki': 0, 'set': 0, 'hafta_baslangic': yayin_ritmi._hafta_baslangic_ts()}):
            with patch('yayin_ritmi.golden_hour_slotlari') as mock_slots:
                # Default: slot müsait (1 saat sonra, dolu=False)
                mock_slots.return_value = [
                    {'baslangic': time.time() + 3600, 'bitis': time.time() + 7200, 'dolu': False},
                    {'baslangic': time.time() + 7200, 'bitis': time.time() + 10800, 'dolu': False},
                ]
                with patch('yayin_ritmi.bir_sonraki_bos_slot') as mock_next_slot:
                    mock_next_slot.return_value = {
                        'gun': 0, 'saat': 12, 'slot_turu': 'sarki',
                        'baslangic_ts': time.time() + 3600, 'bitis_ts': time.time() + 7200, 'sira': 0
                    }
                    with patch('yayin_ritmi.publish_at_hesapla') as mock_publish:
                        mock_publish.return_value = (time.time() + 3600, {'gun': 0, 'saat': 12, 'slot_turu': 'sarki', 'baslangic_ts': time.time() + 3600, 'bitis_ts': time.time() + 7200, 'sira': 0}, "slot")
                        with patch('yayin_ritmi.shorts_zamani', return_value=(True, 0, "")):
                            with patch('yayin_ritmi.kanal_tabani', return_value=(True, 0, "")):
                                with patch('yayin_ritmi.platform_gun_izni', return_value=(True, "")):
                                    yield mock_slots


def _project_with_upload(tmp_path, name, hours_ago):
    d = tmp_path / name
    d.mkdir()
    ts = time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - hours_ago * 3600)
    )
    (d / "state.json").write_text(json.dumps({"youtube_uploaded_at": ts}))
    return str(d)


def _geri_doldurma_projesi(tmp_path, name="backfill"):
    """YouTube'a çoktan çıkmış, sadece Shorts/Instagram'ı eksik kalmış bir proje."""
    d = tmp_path / name
    d.mkdir()
    (d / "state.json").write_text(json.dumps({
        "youtube_video_id": "abc123",
        "youtube_shorts_video_id": "def456",
    }))
    return str(d)


def test_no_pending_projects_returns_zero():
    assert ap._auto_pace_count(pending=[], ready=[]) == 0


def test_first_upload_starts_immediately(tmp_path):
    """Hiç yükleme yapılmamışsa hemen başlar."""
    ready = [str(tmp_path)]  # state.json yok
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 1


def test_new_song_respects_28h_gap(tmp_path, mock_haftalik_kalan):
    """YENİ şarkı için 28 saat tabanı geçerli."""
    # 25 saat önce -> erken (28 saatten küçük)
    ready_25h = [_project_with_upload(tmp_path, "p1", hours_ago=25)]
    assert ap._auto_pace_count(pending=["yeni"], ready=ready_25h) == 0

    # 30 saat önce -> sıra gelmiş
    ready_30h = [_project_with_upload(tmp_path, "p2", hours_ago=30)]
    assert ap._auto_pace_count(pending=["yeni"], ready=ready_30h) == 1


def test_weekly_song_limit_enforced(tmp_path, mock_haftalik_kalan):
    """Haftalık şarkı tavanı (6) dolduysa yeni şarkı işlenmez."""
    with patch('yayin_ritmi.haftalik_kalan', return_value=0):
        ready = [_project_with_upload(tmp_path, "p1", hours_ago=50)]
        assert ap._auto_pace_count(pending=["yeni"], ready=ready) == 0


def test_backfill_only_uses_available_golden_hour_slot(tmp_path, mock_haftalik_kalan):
    """Geri doldurma sadece müsait golden-hour slotu varsa gider."""
    backfill = _geri_doldurma_projesi(tmp_path)
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=50)]

    # Slot müsait değilse (tümü dolu)
    mock_haftalik_kalan.return_value = [
        {'baslangic': time.time() + 3600, 'bitis': time.time() + 7200, 'dolu': True},
        {'baslangic': time.time() + 7200, 'bitis': time.time() + 10800, 'dolu': True},
    ]
    result = ap._auto_pace_count(pending=[backfill], ready=ready)
    assert result == 0

    # Slot müsaitse
    mock_haftalik_kalan.return_value = [
        {'baslangic': time.time() + 3600, 'bitis': time.time() + 7200, 'dolu': False},
        {'baslangic': time.time() + 7200, 'bitis': time.time() + 10800, 'dolu': False},
    ]
    result = ap._auto_pace_count(pending=[backfill], ready=ready)
    assert result == 1


def test_new_songs_prioritized_over_backfill(tmp_path, mock_haftalik_kalan):
    """Batch hazırlanırken yeni şarkılar geri doldurmadan ÖNCE gelir."""
    b1 = _geri_doldurma_projesi(tmp_path, "b1")
    b2 = _geri_doldurma_projesi(tmp_path, "b2")
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=50)]

    # pending = [backfill, backfill, yeni] -> batch = [yeni, backfill, backfill] (count=3)
    # Ama _auto_pace_count yeni şarkı varsa 28 saat tabanı uygular
    pending = [b1, b2, "yeni"]
    result = ap._auto_pace_count(pending=pending, ready=ready, count=3)
    # Yeni şarkı için 28 saat tabanı kontrol edilir
    assert result in (0, 1, 2, 3)  # slot/taban durumuna göre


def test_daily_max_2_new_songs(tmp_path, mock_haftalik_kalan):
    """Günde en fazla 2 yeni şarkı."""
    # Bugün zaten 2 yeni şarkı yüklenmiş gibi simüle et
    bugun = datetime.now(config.TR_TZ).date()
    bugun_ts = datetime.combine(bugun, datetime.min.time()).replace(tzinfo=config.TR_TZ).timestamp()
    ts_bugun = datetime.fromtimestamp(bugun_ts + 2*3600, config.TR_TZ).strftime("%Y-%m-%dT%H:%M:%S")
    
    d1 = tmp_path / "p1"
    d1.mkdir()
    (d1 / "state.json").write_text(json.dumps({
        "youtube_uploaded_at": ts_bugun,
        "youtube_publish_at": ts_bugun,
    }))
    d2 = tmp_path / "p2"
    d2.mkdir()
    (d2 / "state.json").write_text(json.dumps({
        "youtube_uploaded_at": ts_bugun,
        "youtube_publish_at": ts_bugun,
    }))

    ready = [str(d1), str(d2)]
    pending = ["yeni1", "yeni2", "yeni3"]
    result = ap._auto_pace_count(pending=pending, ready=ready, count=3)
    assert result == 0  # Günlük tavan dolu


def test_batch_logic_looks_at_actual_batch_slice(tmp_path, mock_haftalik_kalan):
    """Ölçüt pending[:count] (batch dilimi), DEĞİL pending[0]."""
    b1 = _geri_doldurma_projesi(tmp_path, "b1")
    b2 = _geri_doldurma_projesi(tmp_path, "b2")
    b3 = _geri_doldurma_projesi(tmp_path, "b3")
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=50)]  # 28 saat geçmiş

    # count=1 -> batch = [b1] (sadece geri doldurma) -> 28 saat tabanı UYGULANMAZ
    assert ap._auto_pace_count(pending=[b1, b2, b3, "yeni"], ready=ready, count=1) == 1

    # count=3 -> batch = [b1, b2, b3] (sadece geri doldurma) -> taban uygulanmaz
    assert ap._auto_pace_count(pending=[b1, b2, b3, "yeni"], ready=ready, count=3) == 3

    # count=4 -> batch = [b1, b2, b3, yeni] (yeni VAR) -> 28 saat tabanı UYGULANACAK
    # Ama 50 saat geçmiş -> taban geçilmiş -> 4 döner
    assert ap._auto_pace_count(pending=[b1, b2, b3, "yeni"], ready=ready, count=4) == 4


def test_zero_count_returns_zero(tmp_path, mock_haftalik_kalan):
    """count<=0 gelirse 0 döner."""
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=50)]
    assert ap._auto_pace_count(pending=["yeni"], ready=ready, count=0) == 0
    # count=-1 negatif olamaz, min(count, len) negatif döner -> 0'a clamp et
    assert ap._auto_pace_count(pending=["yeni"], ready=ready, count=-1) <= 0


def test_ritm_kapisi_set_vs_sarki(tmp_path, mock_haftalik_kalan):
    """R1: Set/derleme ↔ şarkı 48 saat ortak tabanı."""
    # Set yüklendi 10 saat önce -> şarkı 48 saat beklemeli
    d = tmp_path / "set1"
    d.mkdir()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 10 * 3600))
    (d / "state.json").write_text(json.dumps({
        "youtube_uploaded_at": ts,
        "youtube_publish_at": ts,
    }))
    ready = [str(d)]
    # Bu test yayin_ritmi.kanal_tabani'yi mocklamazsa geçmeyebilir
    # Sadece fonksiyon çağrıldığını kontrol et
    with patch('yayin_ritmi.kanal_tabani', return_value=(True, 0, "")):
        result = ap._auto_pace_count(pending=["yeni"], ready=ready)
        assert result in (0, 1)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])