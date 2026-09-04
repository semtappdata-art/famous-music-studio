"""auto_process._auto_pace_count() için testler — --count elle verilmediğinde
kaç proje işleneceğine karar veren otomatik kademeleme mantığı. Yanlışsa
şarkılar art arda (algoritma rekabeti riski) ya da hiç paylaşılmaz."""

import json
import time

import auto_process as ap


def _project_with_upload(tmp_path, name, hours_ago):
    d = tmp_path / name
    d.mkdir()
    ts = time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - hours_ago * 3600)
    )
    (d / "state.json").write_text(json.dumps({"youtube_uploaded_at": ts}))
    return str(d)


def test_no_pending_projects_returns_zero():
    assert ap._auto_pace_count(pending=[], ready=[]) == 0


def test_never_uploaded_before_starts_immediately(tmp_path):
    ready = [str(tmp_path)]  # state.json yok -> _last_upload_time None döner
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 1


def test_single_pending_recent_upload_is_too_early(tmp_path):
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=1)]
    # tek proje bekliyor -> gerekli aralık 24 saat, 1 saat önce yüklenmiş -> erken
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 0


def test_single_pending_upload_over_24h_ago_is_due(tmp_path):
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=25)]
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 1


def test_nine_pending_spreads_gap_to_under_three_hours(tmp_path):
    # 9 proje bekliyor -> gerekli aralık = 24/9 ≈ 2.67 saat
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=2)]
    pending = ["a"] * 9
    assert ap._auto_pace_count(pending=pending, ready=ready) == 0  # 2h < 2.67h, henüz erken

    ready_late = [_project_with_upload(tmp_path, "p2", hours_ago=3)]
    assert ap._auto_pace_count(pending=pending, ready=ready_late) == 1  # 3h > 2.67h, sırası geldi


def test_more_pending_projects_shortens_required_gap(tmp_path):
    # Aynı "3 saat önce yüklendi" durumu: 2 proje bekliyorsa (gerekli aralık 12h)
    # HENÜZ erken, ama 9 proje bekliyorsa (gerekli aralık ~2.67h) sırası gelmiş olmalı.
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=3)]
    assert ap._auto_pace_count(pending=["a", "b"], ready=ready) == 0
    assert ap._auto_pace_count(pending=["a"] * 9, ready=ready) == 1


def test_uses_most_recent_upload_across_multiple_platforms(tmp_path):
    d = tmp_path / "p1"
    d.mkdir()
    old_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 25 * 3600))
    recent_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 1 * 3600))
    (d / "state.json").write_text(json.dumps({
        "youtube_uploaded_at": old_ts,
        "tiktok_uploaded_at": recent_ts,  # bu daha yeni, referans bu olmalı
    }))

    # en yeni yükleme (tiktok, 1 saat önce) referans alınmalı -> tek proje için hâlâ erken
    assert ap._auto_pace_count(pending=["a"], ready=[str(d)]) == 0
