# -*- coding: utf-8 -*-
"""Content ID karantina kapısı SESSİZCE çıkmamalı — 2026-09-11 arızası.

OLAN: 15:15:29'da `derlemeler/Gece Seansı Vol. 1` private yüklendi ve
`dj_tarama_bekliyor` işaretlendi (`DJ_TARAMA_BEKLEME_SN` = 7200). Saatlik koşu
17:12:15'te çalıştı — eşiğe 194 SANİYE kalmıştı. `_bekleyenler()` projeyi
listeden düşürdü, `kontrol_et()` `bakilan=0` döndü ve `auto_process._dj_tarama`
`if s.get("bakilan"):` koşulu yüzünden HİÇBİR satır basmadı.

Sonuç: `auto_process.log`'da "tarama"/"karantina" geçen TEK bir satır yoktu.
Dışarıdan bakan biri için "kapı çalıştı ama henüz erkendi" ile "kapı hiç
çağrılmıyor / bir regresyon var" AYIRT EDİLEMEZ hâldeydi; video takılı sanıldı.

Bu dosya o sessizliği kalıcı olarak yasaklıyor: kapı hangi daldan çıkarsa
çıksın en az bir log satırı bırakmalı (CLAUDE.md — "sessizce boş liste dönen
bir koruma, OLMAYAN korumadan kötüdür").
"""

import json
import os
import time

import pytest

import config
import dj_tarama_kontrol as D


def _kok(tmp_path, monkeypatch):
    setler = tmp_path / "dj_sets"
    derlemeler = tmp_path / "derlemeler"
    setler.mkdir()
    derlemeler.mkdir()
    monkeypatch.setattr(D, "BASELER", (str(setler), str(derlemeler)))
    return str(setler), str(derlemeler)


def _proje(base, ad, state):
    d = os.path.join(base, ad)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return d


def _karantina(base, ad, saniye_once):
    damga = time.strftime("%Y-%m-%dT%H:%M:%S",
                          time.localtime(time.time() - saniye_once))
    return _proje(base, ad, {"dj_tarama_bekliyor": True,
                             "youtube_video_id": "VID123",
                             "dj_tarama_yuklendi_at": damga})


@pytest.fixture(autouse=True)
def _kapi_acik(monkeypatch):
    monkeypatch.setattr(config, "DJ_ON_TARAMA", True)
    # Ağ/bildirim/alt süreç YOK — bu dosya sadece görünürlüğü test ediyor.
    monkeypatch.setattr(D, "_bildir", lambda *a, **k: True)
    monkeypatch.setattr(D, "_kalan_platformlari_isle",
                        lambda base, projeler, log=print: True)


def test_sure_dolmadiginda_bile_log_satiri_var(tmp_path, monkeypatch):
    """ASIL REGRESYON: 17:12 koşusunun hiçbir iz bırakmaması."""
    _, derlemeler = _kok(tmp_path, monkeypatch)
    # Gerçek olayın birebir zamanlaması: eşiğe 194 saniye kala.
    _karantina(derlemeler, "Gece Seansı Vol. 1",
               config.DJ_TARAMA_BEKLEME_SN - 194)

    satirlar = []
    s = D.kontrol_et(log=satirlar.append)

    assert s["bakilan"] == 0          # henüz bakılmadı (doğru davranış)
    assert s["erken"] == 1
    assert satirlar, "eşik dolmadı diye SESSİZ çıkılmamalı"
    metin = "\n".join(satirlar)
    assert "Gece Seansı Vol. 1" in metin
    assert "dolmadı" in metin
    assert "~3 dk" in metin           # kalan süre okunabilir olmalı


def test_sure_dolunca_proje_goruluyor(tmp_path, monkeypatch):
    """Kapı gerçekten açılıyor mu — eşik dolduğunda proje listeye girmeli."""
    _, derlemeler = _kok(tmp_path, monkeypatch)
    proje = _karantina(derlemeler, "Gece Seansı Vol. 1",
                       config.DJ_TARAMA_BEKLEME_SN + 60)
    assert D.bekleyen_setler() == [proje]

    monkeypatch.setattr(D, "video_engelli_mi", lambda vid: (False, []))
    monkeypatch.setattr(D, "yayina_ac", lambda vid: True)
    satirlar = []
    s = D.kontrol_et(log=satirlar.append)

    assert (s["bakilan"], s["acilan"]) == (1, 1)
    st = json.load(open(os.path.join(proje, "state.json"), encoding="utf-8"))
    assert st["dj_tarama_temiz"] is True
    assert st["dj_tarama_bekliyor"] is False
    assert st["dj_kalan_bekliyor"] is True     # kalan platformlar sıraya girdi


def test_karantina_bossa_da_bir_satir_dusuyor(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)
    satirlar = []
    D.kontrol_et(log=satirlar.append)
    assert any("karantinada bekleyen içerik yok" in x for x in satirlar)


def test_dj_on_tarama_kapaliyken_de_satir_dusuyor(tmp_path, monkeypatch):
    _kok(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "DJ_ON_TARAMA", False)
    satirlar = []
    D.kontrol_et(log=satirlar.append)
    assert any("DJ_ON_TARAMA" in x for x in satirlar)


def test_damgasiz_kayit_gorunur_oluyor(tmp_path, monkeypatch):
    """Bayrak açık ama `dj_tarama_yuklendi_at` yok: eskiden sonsuza kadar
    görünmezdi (hiçbir listeye girmez, hiçbir satır basmazdı)."""
    setler, _ = _kok(tmp_path, monkeypatch)
    _proje(setler, "damgasiz_set", {"dj_tarama_bekliyor": True,
                                    "youtube_video_id": "VID999"})
    satirlar = []
    s = D.kontrol_et(log=satirlar.append)
    assert s["damgasiz"] == 1
    assert any("damgasiz_set" in x for x in satirlar)


def test_video_idsiz_kayit_gorunur_oluyor(tmp_path, monkeypatch):
    """`if not vid: continue` sessiz bir daldı."""
    setler, _ = _kok(tmp_path, monkeypatch)
    damga = time.strftime("%Y-%m-%dT%H:%M:%S",
                          time.localtime(time.time()
                                         - config.DJ_TARAMA_BEKLEME_SN - 60))
    _proje(setler, "idsiz_set", {"dj_tarama_bekliyor": True,
                                 "dj_tarama_yuklendi_at": damga})
    satirlar = []
    s = D.kontrol_et(log=satirlar.append)
    assert s["bakilan"] == 1
    assert any("youtube_video_id yok" in x for x in satirlar)


def test_auto_process_dj_tarama_kapiyi_gercekten_cagiriyor(monkeypatch):
    """BAĞLANTI testi: `_dj_tarama()` gerçekten `kontrol_et()`e ulaşıyor mu ve
    modülün bastığı satırlar `log()`'a mı gidiyor? (CLAUDE.md: bu deponun en
    sık hatası fonksiyonda değil, BAĞLANTIDA.)"""
    import auto_process as ap
    cagrildi = {}
    satirlar = []

    def sahte_kontrol(log=print):
        cagrildi["log"] = log
        log("  DJ tarama: sahte satir")
        return {"bakilan": 0}

    monkeypatch.setattr(D, "kontrol_et", sahte_kontrol)
    monkeypatch.setattr(ap, "log", satirlar.append)
    ap._dj_tarama()

    assert cagrildi.get("log") is not None, "_dj_tarama kontrol_et'i çağırmadı"
    assert satirlar == ["  DJ tarama: sahte satir"]


def test_dj_tarama_main_finally_blogunda():
    """Kapı, iş olsun olmasın çalışan `finally` bloğuna bağlı olmalı —
    `count==0` dalındaki erken `return` onu atlamamalı."""
    import inspect
    import auto_process as ap
    kaynak = inspect.getsource(ap.main)
    finally_govde = kaynak.split("\n    finally:\n", 1)[1]
    assert "_dj_tarama()" in finally_govde
