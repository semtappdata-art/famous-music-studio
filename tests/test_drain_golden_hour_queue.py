"""auto_process._drain_golden_hour_queue() — YouTube altyazı kontrolünün tek
bir koşuda EN FAZLA BİR projede gerçek bir API isteğine dönüştüğünü doğrular.

2026-09-06'da bu sınır YOKTU: `ready` listesindeki (kataloğun çoğunda bir
lyrics dosyası olduğu için genelde 10+ proje) HER projede `captions.list`
çağrılıyordu, bu da tek bir koşuda günlük YouTube kotasını (10.000 birim)
tüketip asıl video yüklemelerini engelledi. Bu test o regresyonu bir daha
sessizce geri getirmeyi engeller."""

import auto_process as ap


def test_stops_after_first_real_captions_api_call(tmp_path, monkeypatch):
    project_dirs = []
    for name in ("a", "b", "c"):
        d = tmp_path / name
        d.mkdir()
        (d / "state.json").write_text("{}")
        project_dirs.append(str(d))

    calls = []

    def fake_check(project_dir, state):
        calls.append(project_dir)
        return True  # her proje "gerçek bir API isteği yaptı" gibi davransın

    monkeypatch.setattr(ap, "_check_youtube_captions", fake_check)
    ap._drain_golden_hour_queue(project_dirs)

    assert len(calls) == 1
    assert calls[0] == project_dirs[0]


def test_moves_to_next_project_if_previous_check_was_purely_local(tmp_path, monkeypatch):
    """_check_youtube_captions False dönerse (video/sözler dosyası yok gibi
    tamamen yerel bir kontrolle sessizce çıktıysa) API'ye hiç dokunulmamış
    demektir — bir sonraki proje için kontrol yine de denenmeli."""
    project_dirs = []
    for name in ("a", "b", "c"):
        d = tmp_path / name
        d.mkdir()
        (d / "state.json").write_text("{}")
        project_dirs.append(str(d))

    calls = []

    def fake_check(project_dir, state):
        calls.append(project_dir)
        return project_dir == project_dirs[1]  # sadece ikincisi "gerçek" bir istek

    monkeypatch.setattr(ap, "_check_youtube_captions", fake_check)
    ap._drain_golden_hour_queue(project_dirs)

    # a (False, yerel) -> b (True, gerçek istek, dur) -- c'ye HİÇ gidilmemeli
    assert calls == project_dirs[:2]
