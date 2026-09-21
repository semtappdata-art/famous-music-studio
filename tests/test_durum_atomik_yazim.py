# -*- coding: utf-8 -*-
"""`upload/saglik_durum.json` ve `analytics_token.json` ATOMİK yazılmalı.

NEDEN (2026-09-11): `state_io.py` atomik yazım için eklendi ama göç yarım
kalmıştı — `saglik_kontrol._kaydet`, `weekly_report._kaydet` ve
`upload/youtube_analytics`in token yazımı hâlâ ham `open(..., "w")`
kullanıyordu. `open` hedefi ÖNCE SIFIRLIYOR: yazım yarıda kesilirse diskte
yarım bir dosya kalıyor. İlk ikisi AYNI dosyayı paylaşıyor (biri günlük sağlık
damgaları, diğeri haftalık izlenme damgaları) — yarım bir yazım ikisinin
damgalarını BİRLİKTE siler; üçüncüsü bozulunca
`Credentials.from_authorized_user_file` patlar ve izlenme ölçümü sessizce ölür.
"""

import json
import os
import sys
import types

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

import pytest

import saglik_kontrol as SK
import state_io
import weekly_report as WR


def test_atomik_metin_yazim_stringi_aynen_birakir(tmp_path):
    yol = str(tmp_path / "t.json")
    metin = '{"token": "abc", "tr": "ğüşİı"}'
    state_io._atomik_metin_yaz(yol, metin)
    assert open(yol, encoding="utf-8").read() == metin
    assert not os.path.isfile(yol + ".tmp")     # geçici dosya bırakılmadı


def test_yarim_kalan_yazim_eski_dosyayi_bozmaz(tmp_path, monkeypatch):
    """os.replace'ten ÖNCE ölen bir süreç hedefi ellememiş olmalı."""
    yol = str(tmp_path / "d.json")
    state_io._atomik_yaz(yol, {"eski": 1})

    def patla(*a, **k):
        raise KeyboardInterrupt("süreç öldürüldü")

    monkeypatch.setattr(state_io.os, "replace", patla)
    with pytest.raises(KeyboardInterrupt):
        state_io._atomik_yaz(yol, {"yeni": 2})
    # Hedef ESKİ (geçerli) halini korumalı — ham open(...,"w") burada
    # sıfırlanmış/yarım bir dosya bırakırdı.
    assert json.load(open(yol, encoding="utf-8")) == {"eski": 1}


def test_saglik_kaydet_atomik_yol_kullaniyor(tmp_path, monkeypatch):
    yol = str(tmp_path / "saglik_durum.json")
    monkeypatch.setattr(SK, "DURUM_DOSYASI", yol)
    cagrilar = []
    gercek = state_io._atomik_yaz
    monkeypatch.setattr(state_io, "_atomik_yaz",
                        lambda y, v: (cagrilar.append(y), gercek(y, v))[1])
    SK._kaydet({"a": "2026-09-11"})
    assert cagrilar == [yol]
    assert json.load(open(yol, encoding="utf-8")) == {"a": "2026-09-11"}


def test_weekly_kaydet_atomik_yol_kullaniyor(tmp_path, monkeypatch):
    yol = str(tmp_path / "saglik_durum.json")
    cagrilar = []
    gercek = state_io._atomik_yaz
    monkeypatch.setattr(state_io, "_atomik_yaz",
                        lambda y, v: (cagrilar.append(y), gercek(y, v))[1])
    WR._kaydet({"h": "2026-W37"}, yol)
    assert cagrilar == [yol]
    assert json.load(open(yol, encoding="utf-8")) == {"h": "2026-W37"}


def test_iki_modul_ayni_dosyada_birbirinin_damgasini_silmiyor(tmp_path, monkeypatch):
    """saglik_kontrol + weekly_report AYNI `saglik_durum.json`a yazıyor.

    İkisi de oku-değiştir-yaz yapıyor; `auto_process.main()`in `finally`
    bloğunda AYNI süreçte SIRAYLA çağrıldıkları için (`_saglik_kontrol()`
    hemen ardından `_izlenme_raporu()`) araya girme riski yok — bu test o
    sıralı davranışın damga kaybetmediğini sabitliyor.
    """
    yol = str(tmp_path / "saglik_durum.json")
    monkeypatch.setattr(SK, "DURUM_DOSYASI", yol)
    SK._kaydet({"instagram_bildirim_gun": "2026-09-11"})
    WR._kaydet({"izlenme_rapor_hafta": "2026-W37"}, yol)
    SK._kaydet({"netlify_bildirim_gun": "2026-09-11"})

    d = json.load(open(yol, encoding="utf-8"))
    assert d == {"instagram_bildirim_gun": "2026-09-11",
                 "izlenme_rapor_hafta": "2026-W37",
                 "netlify_bildirim_gun": "2026-09-11"}


def test_analytics_token_atomik_yaziliyor(tmp_path, monkeypatch):
    import youtube_analytics as YA

    yol = str(tmp_path / "analytics_token.json")
    monkeypatch.setattr(YA, "TOKEN_PATH", yol)

    class SahteCreds:
        def to_json(self):
            return '{"refresh_token": "x", "scopes": ["yt-analytics.readonly"]}'

    YA._token_yaz(SahteCreds())
    # google-auth'un ürettiği gösterim AYNEN korunmalı (yeniden
    # serileştirilmemeli) — token dosyasını kütüphane de kendisi okuyor.
    assert open(yol, encoding="utf-8").read() == SahteCreds().to_json()
    assert not os.path.isfile(yol + ".tmp")

    # Yazım yarıda kesilirse eski token GEÇERLİ kalmalı.
    def patla(*a, **k):
        raise KeyboardInterrupt("süreç öldürüldü")

    monkeypatch.setattr(state_io.os, "replace", patla)
    with pytest.raises(KeyboardInterrupt):
        YA._token_yaz(SahteCreds())
    assert json.load(open(yol, encoding="utf-8"))["refresh_token"] == "x"
