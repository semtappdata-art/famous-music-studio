# -*- coding: utf-8 -*-
"""uyumluluk._meta() sertlestirmesi — bozuk meta.json artik SESSIZ degil.

_durum() ile ayni desen, FARKLI siddet: bozuk state.json HATA (telif kapisini
aciyordu), bozuk meta.json UYARI (actigi bir kapi yok — `containsSyntheticMedia`
youtube_upload'da kosulsuz True ve derleme dali `derlemeler/` kokunden de
tetikleniyor). Bu testler hem sessizligin kirildigini hem siddetin UYARI'da
kaldigini kilitliyor.
"""

import json
import os

import pytest

import uyumluluk


def _proje(tmp_path, ad, meta_ham=None, durum=None):
    p = tmp_path / ad
    p.mkdir(parents=True)
    if meta_ham is not None:
        (p / "meta.json").write_text(meta_ham, encoding="utf-8")
    if durum is not None:
        (p / "state.json").write_text(json.dumps(durum), encoding="utf-8")
    return str(p)


def test_meta_yoksa_bos_sozluk(tmp_path):
    # Henuz hazirlanmamis proje — uyari uretilmemeli.
    assert uyumluluk._meta(_proje(tmp_path, "yeni")) == {}


def test_bozuk_meta_DurumBozuk_firlatiyor(tmp_path):
    p = _proje(tmp_path, "yarim", meta_ham='{"tema": "arabesk", "ai_be')
    with pytest.raises(uyumluluk.DurumBozuk):
        uyumluluk._meta(p)


def test_bozuk_meta_UYARI_uretiyor_HATA_degil(tmp_path, monkeypatch):
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(tmp_path),))
    p = _proje(tmp_path, "yarim", meta_ham="{bu json degil", durum={})
    hatalar, uyarilar = uyumluluk.kontrol(p, "render")
    assert hatalar == [], "bozuk meta.json boru hattini DURDURMAMALI"
    assert any("meta.json" in u for u in uyarilar), uyarilar
    assert any("ai_beyani" in u for u in uyarilar), uyarilar


def test_bozuk_meta_derleme_kontrollerini_YINE_calistiriyor(tmp_path, monkeypatch):
    """meta={} ile devam edilince derleme dali kok adindan tetiklenmeye devam
    ediyor — sertlestirmenin UYARI olarak kalabilmesinin asil gerekcesi."""
    kok = tmp_path / "derlemeler"
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    p = _proje(tmp_path, "derlemeler/eylul", meta_ham="{bozuk", durum={})
    hatalar, uyarilar = uyumluluk.kontrol(p, "render")
    assert hatalar == []
    assert any("bölüm damgası" in u for u in uyarilar), uyarilar
    assert any("derleme_notu" in u for u in uyarilar), uyarilar


def test_saglam_meta_eskisi_gibi_calisiyor(tmp_path, monkeypatch):
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(tmp_path),))
    p = _proje(tmp_path, "iyi",
               meta_ham=json.dumps({"ai_beyani": False}), durum={})
    hatalar, uyarilar = uyumluluk.kontrol(p, "render")
    # ai_beyani=False HALA hata — sertlestirme bu kontrolu bozmadi.
    assert any("ai_beyani=False" in h for h in hatalar), hatalar


def test_bozuk_state_HALA_hata(tmp_path, monkeypatch):
    """Siddet farkinin karsi tarafi: state.json bozuksa HATA olmaya devam."""
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(tmp_path),))
    p = _proje(tmp_path, "bozuk_state", meta_ham=json.dumps({}))
    (tmp_path / "bozuk_state" / "state.json").write_text("{yarim",
                                                        encoding="utf-8")
    hatalar, _ = uyumluluk.kontrol(p, "render")
    assert any("state.json" in h for h in hatalar), hatalar
