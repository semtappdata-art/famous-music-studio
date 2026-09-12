# -*- coding: utf-8 -*-
"""TikTok yayın kiti ana anahtarı (config.TIKTOK_KIT_AKTIF).

NEDEN VAR (2026-09-13): kit canlı checkout'a incelemeden önce düştü; bir
sonraki golden-hour koşusu gerçek bir kit gönderecekti. Anahtar kapalıyken
`_tiktok_kit_sirasi()` modülü HİÇ çağırmamalı.
"""

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process
import config
import tiktok_yayin_kiti


def _kur(monkeypatch, aktif):
    cagrilar, loglar = [], []
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", aktif)
    monkeypatch.setattr(tiktok_yayin_kiti, "kit_gonder_sirasi",
                        lambda log=print, **k: cagrilar.append(1))
    monkeypatch.setattr(auto_process, "log", loglar.append)
    auto_process._tiktok_kit_sirasi()
    return cagrilar, loglar


def test_kapaliyken_kit_modulu_cagrilmaz(monkeypatch):
    cagrilar, loglar = _kur(monkeypatch, False)
    assert cagrilar == []
    assert any("kapalı" in l for l in loglar)


def test_acikken_kit_sirasi_calisir(monkeypatch):
    cagrilar, _ = _kur(monkeypatch, True)
    assert cagrilar == [1]
