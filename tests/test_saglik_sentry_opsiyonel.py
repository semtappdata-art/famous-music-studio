# -*- coding: utf-8 -*-
"""Sentry opsiyonelligi — saglik monitoru telemetri kirikken olmemeli.

UC SORU (CLAUDE.md section 9):
1. Kim cagiriyor? auto_process._saglik_kontrol (saatlik) + `python saglik_kontrol.py`.
2. Hangi gorevden? saatlik auto_process.py.
3. Calismadigini nasil anlariz? Bu test FAIL (import patlarsa) + saatlik
   log'da "Saglik kontrolu HATA" satiri.

Olay (2026-10-08): sentry_sdk (eventlet'li eski surum) Python 3.14'te
`import` aninda patliyordu (ssl.wrap_socket AttributeError) ve modulu
ice aktaran HERKES (auto_process dahil) dusuyordu — monitor sessizce
hic calismiyordu. Cozum: fail-open fallback (modul yasiyor, sentry sessiz).
"""

import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def test_sentry_import_guarded_ast():
    yol = os.path.join(REPO, "saglik_kontrol.py")
    with open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    sentry_satirlar = []
    for node in ast.walk(agac):
        if isinstance(node, ast.Import):
            if any("sentry" in a.name for a in node.names):
                sentry_satirlar.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if "sentry" in (node.module or ""):
                sentry_satirlar.append(node.lineno)
    assert sentry_satirlar, "sentry import bulunamadi"
    try_araliklar = []
    for node in ast.walk(agac):
        if isinstance(node, ast.Try):
            try_araliklar.append((node.lineno, node.end_lineno or node.lineno))
    for satir in sentry_satirlar:
        assert any(a <= satir <= b for a, b in try_araliklar), \
            f"sentry import satir {satir} try/except disinda"


def test_modul_import_oluyor():
    import saglik_kontrol
    assert callable(saglik_kontrol.kontrol_et)
    assert callable(saglik_kontrol._sentry_durum)
    assert callable(saglik_kontrol._sentry_init)


def test_sentry_yokken_durum_aktif_degil():
    import saglik_kontrol
    eski_sdk, eski_bayrak = saglik_kontrol.sentry_sdk, saglik_kontrol._SENTRY_MEVCUT
    try:
        saglik_kontrol.sentry_sdk = None
        saglik_kontrol._SENTRY_MEVCUT = False
        sonuc = saglik_kontrol._sentry_durum(log=lambda *a, **k: None)
        assert sonuc["durum"] == "aktif_degil"
        saglik_kontrol._sentry_init()  # patlamamali
    finally:
        saglik_kontrol.sentry_sdk, saglik_kontrol._SENTRY_MEVCUT = eski_sdk, eski_bayrak


def test_capture_fallback_noop():
    import saglik_kontrol
    # fallback veya gercek — ikisi de cagrilabilir olmali, patlamamali
    assert callable(saglik_kontrol.capture_exception)
    assert callable(saglik_kontrol.capture_message)
