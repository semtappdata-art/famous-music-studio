# -*- coding: utf-8 -*-
"""Testler kullanıcının telefonuna GERÇEK bildirim gönderemez.

NEDEN VAR (2026-09-12): bir test `notify.send`'i taklit etmeden
`weekly_report.izlenme_raporu()`nu çağırıyordu ve her tam test koşusunda
kullanıcının Telegram'ına "Haftalık izlenme süresi — projects: video başına
20 dk (2 video)" düşüyordu (sahte veri). Gece boyunca ajanlar dakikalar arayla
test koştuğu için mesaj ~4 dakikada bir geldi; kullanıcı fark etti.

Koruma `tests/conftest.py::gercek_bildirim_kanalini_kapat`. Bu dosya o
korumanın VARLIĞINI ve ETKİSİNİ ölçüyor: biri fixture'ı silerse ya da `notify`
yeni bir yapılandırma yolu eklerse burada kırmızı yanar.
"""

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import notify


def test_testte_bildirim_kanali_KAPALI():
    """Gerçek `notify_config.json` diskte dursa bile test içinde kanal yok."""
    assert not notify.is_configured(), (
        "test sırasında bildirim kanalı AÇIK — conftest koruması çalışmıyor; "
        "taklit etmeyen her test kullanıcıya gerçek mesaj gönderir")


def test_yapilandirma_yollari_depo_disina_cekilmis():
    """Yollar gerçek dosyaları göstermemeli."""
    gercek_config = os.path.join(_REPO, "notify_config.json")
    assert os.path.abspath(notify._CONFIG_PATH) != os.path.abspath(gercek_config)
    assert not os.path.isfile(notify._CONFIG_PATH)
    assert not os.path.isfile(notify._TELEGRAM_SECRETS_PATH)


def test_send_ag_istegi_atmadan_false_doner(monkeypatch):
    """Kanal yokken `send()` hiçbir HTTP isteği atmamalı."""
    import requests

    def _yasak(*a, **k):
        raise AssertionError("test sırasında gerçek HTTP isteği atıldı")

    monkeypatch.setattr(requests, "post", _yasak)
    monkeypatch.setattr(requests, "get", _yasak)
    monkeypatch.setattr(requests.Session, "request", _yasak, raising=False)
    assert notify.send("test", "gönderilmemeli") is False


def test_sizdiran_test_artik_bildirimleri_tasiyor():
    """Sızıntının kaynağı olan testin imzası `bildirimler` taklidini almalı."""
    yol = os.path.join(_REPO, "tests", "test_haftalik_gozden_gecirme.py")
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    i = metin.find("def test_izlenme_raporu_ozeti_damgaya_yaziyor(")
    assert i >= 0
    imza = metin[i:metin.find("):", i)]
    assert "bildirimler" in imza
