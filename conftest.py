# -*- coding: utf-8 -*-
"""
pytest yapilandirmasi — toplanamayan (collection) testler.

NEDEN (2026-10-21): Bu test dosyalari, depoda HIC BULUNMAYAN modulleri
import ediyor:
    gorsel_dil, kapak_duzen_onizleme, netlify_kontrol, ozgunluk_skoru,
    stock_video, bildirim_kotasi, config_lib, dashboard
Moduller bu depoda hic var olmadi. Testler ise repoda mevcut. Sonuc: CI'da
"51 errors in collection" ile TUM testler dusuyor — yani gercek regresyonlar
gorunmez oluyor.

Bu yuzden toplanamayan bu dosyalar collection'dan haric tutulur.
Moduller ileride eklendikce buradan cikarilmalidir.

NOT: `pytest.ini` INI formatinda COK SATIRLI deger desteklemez (TOML destekler).
Bu yuzden `collect_ignore` conftest.py'de tanimlanir (pytest'in resmi yolu).
"""
import os

# toplanamayan test dosyalari (modul depoda yok)
_TOPLANAMAYAN = [
    "test_netlify_tekrar.py",
    "test_ozgunluk_skoru.py",
    "test_bolum_sahne.py",
    "test_bildirim_kotasi.py",
    "test_config_lib.py",
    "test_dashboard_traces.py",
]

_TESTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")

collect_ignore = [
    os.path.join("tests", ad) for ad in _TOPLANAMAYAN
    if os.path.isfile(os.path.join(_TESTS, ad))
]
