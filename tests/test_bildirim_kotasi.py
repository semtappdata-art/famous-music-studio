# -*- coding: utf-8 -*-
"""Telegram günlük kota (günde 1) — davranış kilidi.

Kapsam: `send` / `send_text` / `send_photo` ORTAK havuzdan yer;
ikinci başarılı gönderim aynı gün çıkmaz. Başarısız gönderim damga yakmaz.
"""
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

import bildirim_kotasi
import notify

SAHTE_TOKEN = "1234567890:TEST-SAHTE-TOKEN-hicbir-yere-gitmez"
YAYIN_CHAT = "-1004337174284"
OPERATOR_CHAT = "987654321"


class _SahteYanit:
    def __init__(self, kod=200, govde=None):
        self.status_code = kod
        self._govde = govde if govde is not None else {"ok": True}
    def json(self):
        return self._govde
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %s" % self.status_code)


def _kur(monkeypatch, tmp_path):
    c = tmp_path / "notify_config.json"
    c.write_text(json.dumps(
        {"ntfy_topic": "yedek", "telegram_chat_id": OPERATOR_CHAT}),
        encoding="utf-8")
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(c))
    s = tmp_path / "telegram_client_secrets.json"
    s.write_text(json.dumps(
        {"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT}), encoding="utf-8")
    monkeypatch.setattr(notify, "_TELEGRAM_SECRETS_PATH", str(s))
    monkeypatch.setattr(notify.requests, "post",
                        lambda *a, **k: _SahteYanit(200))
    monkeypatch.delenv("FMS_BILDIRIM_KOTA_KAPALI", raising=False)
    monkeypatch.delenv("BILDIRIM_KOTA_DOSYASI", raising=False)


def test_ikinci_gonderim_ayni_gun_cikmaz(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path)
    notify._uyarilanlar.clear()
    assert notify.send("A", "bir") is True
    notify._uyarilanlar.clear()
    assert notify.send("B", "iki") is False  # kota: ağa çıkılmadan elenir


def test_havuz_send_ve_send_text_arasinda_ortak(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path)
    notify._uyarilanlar.clear()
    assert notify.send("A", "bir") is True
    notify._uyarilanlar.clear()
    assert notify.send_text("kopyalanacak metin") is False


def test_basarisiz_gonderim_kota_yakmaz(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path)
    notify._uyarilanlar.clear()
    monkeypatch.setattr(notify.requests, "post",
                        lambda *a, **k: _SahteYanit(400, {"ok": False}))
    assert notify.send("A", "bir") is False
    notify._uyarilanlar.clear()
    monkeypatch.setattr(notify.requests, "post",
                        lambda *a, **k: _SahteYanit(200))
    assert notify.send("B", "iki") is True


def test_bozuk_kota_dosyasi_fail_open(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path)
    yol = bildirim_kotasi._kota_yolu()
    with open(yol, "w", encoding="utf-8") as f:
        f.write("{bozuk")
    assert bildirim_kotasi.hak_var_mi() is True


def test_kill_switch_kotayi_kapatir(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path)
    monkeypatch.setenv("FMS_BILDIRIM_KOTA_KAPALI", "1")
    notify._uyarilanlar.clear()
    assert notify.send("A", "bir") is True
    notify._uyarilanlar.clear()
    assert notify.send("B", "iki") is True
