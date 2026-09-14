# -*- coding: utf-8 -*-
"""dj_tarama_kontrol — koşu başına TEK kök + timeout'ta kilit sızmaması.

NEDEN (2026-09-11 denetimi):
  * Kota: `_kalan_platformlari_isle` her kök için ayrı bir dj_famous_process
    koşusu başlatıyordu. Her koşu uzun format + Shorts = ~3200 YouTube birimi;
    aynı saatte hem bir DJ seti hem bir derleme temiz geçerse 6400, üstüne aynı
    finally bloğundaki normal auto_process yüklemeleri (3200) = 9600/10000.
  * Kilit: `subprocess.run(..., timeout=3600)` süre dolunca çocuk süreci
    öldürüyor; Windows'ta `finally: _release_lock()` HİÇ çalışmıyor ve
    `.dj_famous_process.lock` 8 saat (LOCK_STALE_SECONDS) diskte kalıyordu —
    haftalık Cuma tetikleyicisi dahil her DJ koşusu sessizce atlanıyordu.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import dj_tarama_kontrol as D


def _proje(base, ad, state):
    d = os.path.join(base, ad)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return d


def _iki_kok(tmp_path, monkeypatch):
    setler = str(tmp_path / "dj_sets")
    derlemeler = str(tmp_path / "derlemeler")
    os.makedirs(setler)
    os.makedirs(derlemeler)
    _proje(setler, "set_a", {"dj_kalan_bekliyor": True})
    _proje(derlemeler, "derleme_a", {"dj_kalan_bekliyor": True})
    monkeypatch.setattr(D, "BASELER", (setler, derlemeler))
    return setler, derlemeler


def test_kosu_basina_tek_kok(tmp_path, monkeypatch):
    setler, derlemeler = _iki_kok(tmp_path, monkeypatch)
    monkeypatch.setattr(D.config, "DJ_ON_TARAMA", True)
    monkeypatch.setattr(D, "bekleyen_setler", lambda: [])   # yeni set yok

    cagrilan = []
    monkeypatch.setattr(D, "_kalan_platformlari_isle",
                        lambda base, projeler, log=print: cagrilan.append(base) or True)

    s = D.kontrol_et(log=lambda *_: None)
    assert len(cagrilan) == D.KOSU_BASINA_KOK == 1
    assert s["kalan_kok"] == 1          # ikinci kök sonraki koşuya bırakıldı


def test_bayrak_kalici_ertelenen_kok_kaybolmuyor(tmp_path, monkeypatch):
    setler, derlemeler = _iki_kok(tmp_path, monkeypatch)
    harita = D._kalan_bekleyen_kokler()
    assert sorted(harita) == sorted([setler, derlemeler])
    # Bayrak düşünce kök listeden çıkmalı.
    _proje(setler, "set_a", {"dj_kalan_bekliyor": False})
    assert list(D._kalan_bekleyen_kokler()) == [derlemeler]


def test_timeout_kilidi_temizler(tmp_path, monkeypatch):
    setler, _ = _iki_kok(tmp_path, monkeypatch)
    kilit = str(tmp_path / ".dj_famous_process.lock")
    with open(kilit, "w", encoding="utf-8") as f:
        f.write("pid")

    sahte = type("M", (), {"LOCK_PATH": kilit})
    monkeypatch.setitem(sys.modules, "dj_famous_process", sahte)

    def patlat(*a, **k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=D.DJ_SUREC_TIMEOUT)

    monkeypatch.setattr(subprocess, "run", patlat)

    satirlar = []
    ok = D._kalan_platformlari_isle(setler, [os.path.join(setler, "set_a")],
                                    log=satirlar.append)
    assert ok is False
    assert not os.path.isfile(kilit)     # ASIL REGRESYON: kilit sızmamalı
    # Bayrak korunmalı (deneme sayacı artmış, tavan dolmamış) -> tekrar denenir.
    st = json.load(open(os.path.join(setler, "set_a", "state.json"), encoding="utf-8"))
    assert st["dj_kalan_bekliyor"] is True
    assert st["dj_kalan_deneme"] == 1


def test_basarida_bayrak_dusuyor(tmp_path, monkeypatch):
    setler, _ = _iki_kok(tmp_path, monkeypatch)
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())
    proje = os.path.join(setler, "set_a")
    assert D._kalan_platformlari_isle(setler, [proje], log=lambda *_: None) is True
    st = json.load(open(os.path.join(proje, "state.json"), encoding="utf-8"))
    assert st["dj_kalan_bekliyor"] is False


def test_deneme_tavaninda_pes_edilir(tmp_path, monkeypatch):
    setler, _ = _iki_kok(tmp_path, monkeypatch)
    proje = _proje(setler, "set_a", {"dj_kalan_bekliyor": True,
                                     "dj_kalan_deneme": D.DJ_KALAN_DENEME_TAVANI - 1})
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "x"})())
    monkeypatch.setattr(D, "_bildir", lambda *a, **k: True)
    D._kalan_platformlari_isle(setler, [proje], log=lambda *_: None)
    st = json.load(open(os.path.join(proje, "state.json"), encoding="utf-8"))
    assert st["dj_kalan_bekliyor"] is False   # sonsuz döngü olmuyor


def test_timeout_2_saatlik_auto_process_kilidinden_kisa():
    """auto_process kendi kilidini tutarken bekliyor; süre onun bayatlama
    eşiğini (2 saat) aşmamalı, yoksa ikinci bir auto_process başlayabilir."""
    import auto_process
    assert D.DJ_SUREC_TIMEOUT * D.KOSU_BASINA_KOK < auto_process.LOCK_STALE_SECONDS
