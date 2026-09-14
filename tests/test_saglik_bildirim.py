# -*- coding: utf-8 -*-
"""saglik_kontrol._bildir — başarısız bildirim "gönderildi" diye damgalanmamalı.

NEDEN (2026-09-11 denetimi): `notify.send` patlasa bile `_kaydet({anahtar:
bugun})` çalışıyordu. Yani telefon bildirim hattı bozuksa "Instagram token'ı
doldu" uyarısı hiç ulaşmıyor AMA 24 saat boyunca tekrar da denenmiyordu. Bu
modülün TÜM var oluş gerekçesi "sessizce duran korumaları yakalamak" — koruma
tam kendi tuzağına düşüyordu.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import saglik_kontrol as SK


def _sahte_notify(monkeypatch, gonderilen, patlasin=False):
    m = types.ModuleType("notify")

    def send(baslik, mesaj, **k):
        if patlasin:
            raise RuntimeError("ntfy erişilemiyor")
        gonderilen.append((baslik, mesaj))
        # Gerçek notify.send() BOOL döner (2026-09-11 sözleşmesi) — sahtenin
        # de dönmesi şart: _bildir artık dönüş değerine bakıp damgayı yalnızca
        # gerçekten gönderildiğinde atıyor. Sessizce False dönen (ağ yok,
        # kanal kurulu değil) yolun testi: test_saglik_bildirim_sessiz_false.py
        return True

    m.send = send
    monkeypatch.setitem(sys.modules, "notify", m)


def test_basarili_bildirim_gunu_damgalar(tmp_path, monkeypatch):
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "d.json"))
    gonderilen = []
    _sahte_notify(monkeypatch, gonderilen)
    assert SK._bildir("b", "m", "anahtar") is True
    assert len(gonderilen) == 1
    assert SK._durum()["anahtar"]
    # Aynı gün ikinci çağrı susmalı.
    assert SK._bildir("b", "m", "anahtar") is False
    assert len(gonderilen) == 1


def test_basarisiz_bildirim_damgalamaz_ve_tekrar_dener(tmp_path, monkeypatch):
    yol = str(tmp_path / "d.json")
    monkeypatch.setattr(SK, "DURUM_DOSYASI", yol)
    gonderilen = []
    _sahte_notify(monkeypatch, gonderilen, patlasin=True)

    assert SK._bildir("b", "m", "anahtar") is False
    assert "anahtar" not in SK._durum()      # DAMGA ATILMAMALI
    assert not os.path.isfile(yol) or json.load(open(yol, encoding="utf-8")) == {}

    # Hat düzelince bir sonraki koşu GERÇEKTEN gönderebilmeli.
    _sahte_notify(monkeypatch, gonderilen)
    assert SK._bildir("b", "m", "anahtar") is True
    assert len(gonderilen) == 1
    assert SK._durum()["anahtar"]
