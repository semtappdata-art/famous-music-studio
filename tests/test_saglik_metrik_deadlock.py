# -*- coding: utf-8 -*-
"""Metrik self-deadlock regresyonu — _TarihceMetrik.set asilmamali.

UC SORU (CLAUDE.md section 9):
1. Kim cagiriyor? kontrol_et (METRIKLER) + uretim_kuyrugu_bos + diger olcumler.
2. Hangi gorevden? saatlik auto_process.py (_saglik_kontrol adimi).
3. Calismadigini nasil anlariz? Bu test FAIL (timeout) + saatlik hat durur.

Olay (2026-10-08): _TarihceMetrik.set, self._lock eldeyken super().set()
cagiriyordu; threading.Lock reentrant OLMADIGI icin ilk deger degisiminde
self-deadlock -> kontrol_et() SONSUZA asiliyordu -> saatlik hat kitleniyordu.
"""

import os
import sys
import threading

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _sureli_cagir(fn, saniye=15):
    sonuc = {}
    def hedef():
        try:
            fn()
            sonuc["ok"] = True
        except Exception as e:  # noqa: BLE001
            sonuc["hata"] = repr(e)
    t = threading.Thread(target=hedef, daemon=True)
    t.start()
    t.join(saniye)
    assert not t.is_alive(), "DEADLOCK: cagri %ds icinde donmedi" % saniye
    assert sonuc.get("ok"), "hata: %s" % sonuc.get("hata")


def test_tarihce_set_asmiyor():
    import saglik_kontrol as s
    m = s._TarihceMetrik(max_kayit=10)
    _sureli_cagir(lambda: m.set(100.0))
    assert m.get_gauge() == 100.0


def test_tarihce_set_ayni_deger_asmiyor():
    import saglik_kontrol as s
    m = s._TarihceMetrik(max_kayit=10)
    _sureli_cagir(lambda: m.set(50.0))
    _sureli_cagir(lambda: m.set(50.0))  # degismeyen deger
    assert m.get_gauge() == 50.0


def test_tarihce_budama_calismaya_devam():
    import saglik_kontrol as s
    m = s._TarihceMetrik(max_kayit=5)
    for i in range(10):
        _sureli_cagir(lambda i=i: m.set(float(i)))
    assert len(m.tarihce(saniye=3600 * 24)) <= 5
    assert m.get_gauge() == 9.0


def test_global_metrikler_set_asmiyor():
    import saglik_kontrol as s
    for ad, m in s.METRIKLER.items():
        _sureli_cagir(lambda m=m: m.set(1.0), saniye=15)
