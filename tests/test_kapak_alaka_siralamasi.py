# -*- coding: utf-8 -*-
"""`_sirali_adaylar` alaka puanını SIRALAMAYA yansıtmalı.

NEDEN VAR: alaka eşiği bilerek bir KAPI değil, bir iyileştirme
(`_alakali_adaylar` docstring'i) — ama eşik İKİLİ olduğu için ("puan > 0")
sadece bir kelimesi tutan kare, altı kelimesi tutan kareyle aynı kademede
sayılıyordu ve sıra tamamen `_secim_indeksi` hash'inden geliyordu.

2026-09-12'de ölçülen bedel: `Sabah Senin`in sorgusu
"empty city street at dawn first light cinematic" iken 10 aday içinde ilk
denenen kare "architecture, buildings, city" (puan 1) oluyordu. Katalog
genelinde 19 başlığın 12'si puan-1 bir kareye düşüyordu.

Arıza sessiz: istisna yok, log satırı yok, sadece kapak şarkının konusundan
kopuyor. Ağa ÇIKMAZ — tüm adaylar sahte sözlüklerdir.
"""

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

import stock_art


SORGU = "empty city street at dawn first light cinematic"


def _aday(tarif, idx):
    return {"tarif": tarif, "src": "https://ornek/%d.jpg" % idx, "id": idx}


# Puanları bilerek karışık sırada: en alakalı kare listenin ORTASINDA.
HAVUZ = [
    _aday("Free stock photo of architecture, buildings, city", 0),   # 1: city
    _aday("Brown wooden table near window", 1),                      # 0
    _aday("Empty city street at dawn with first light", 2),          # 6
    _aday("City lights at night", 3),                                # 2: city, light
    _aday("Person walking on empty street", 4),                      # 2: empty, street
    _aday("Aerial view of a city", 5),                               # 1
    _aday("Sunrise over rooftops", 6),                               # 0
]


def _puan(a):
    return stock_art._alaka_puani(a["tarif"], stock_art._sahne_kelimeleri(SORGU))


def test_en_alakali_kare_ILK_sirada():
    """Asıl düzeltme. Eskiden sıra hash'ten geliyordu ve bu kare 3. sıraya
    düşebiliyordu."""
    sirali = stock_art._sirali_adaylar("Sabah Senin", SORGU, HAVUZ)
    assert sirali[0]["id"] == 2, [a["id"] for a in sirali]
    assert _puan(sirali[0]) == max(_puan(a) for a in HAVUZ)


def test_puanlar_azalan_sirada():
    """Sadece ilk eleman değil, listenin TAMAMI kademeli olmalı — kopya
    koruması sıradakine geçtiğinde de daha alakalıyı görsün."""
    sirali = stock_art._sirali_adaylar("Sabah Senin", SORGU, HAVUZ)
    puanlar = [_puan(a) for a in sirali]
    assert puanlar == sorted(puanlar, reverse=True), puanlar


def test_siralama_ELEME_YAPMIYOR():
    """Sıralama hiçbir kareyi DÜŞÜRMEMELİ — düşürme işi `_alakali_adaylar`'ın.

    Ayrımı çivilemek önemli: eşiği geçen (puan > 0) her kare sırada kalmalı,
    yoksa kopya koruması "bir sonrakini dene" adımında aday bulamaz. Puan-0
    kareleri zaten `_alakali_adaylar` eliyor ve bu DÜZELTMEDEN ÖNCE de böyleydi
    (id 1 ve 6 burada puan 0)."""
    gecen = stock_art._alakali_adaylar(HAVUZ, SORGU)
    sirali = stock_art._sirali_adaylar("Sabah Senin", SORGU, HAVUZ)
    assert {a["id"] for a in sirali} == {a["id"] for a in gecen}
    assert len(sirali) == len(gecen)
    assert {a["id"] for a in sirali} == {0, 2, 3, 4, 5}


def test_deterministik_ayni_baslik_ayni_sonuc():
    """Arşiv tutarlılığı: aynı şarkı + aynı havuz -> hep aynı sıra."""
    a = [x["id"] for x in stock_art._sirali_adaylar("Sabah Senin", SORGU, HAVUZ)]
    b = [x["id"] for x in stock_art._sirali_adaylar("Sabah Senin", SORGU, HAVUZ)]
    assert a == b


def test_ayni_kademede_baslik_hala_ayirt_ediyor():
    """Puan eşitse eski davranış korunmalı: iki farklı şarkı aynı havuzdan
    (mümkün olduğunca) farklı kare seçsin — kopya kapağın ilk savunması bu."""
    esit = [_aday("Empty road", i) for i in range(5)]   # hepsi puan 1 (empty)
    # Başlıklar ÖLÇÜLEREK seçildi: n=5'te farklı indekse düşen gerçek iki
    # katalog başlığı ("Beni Bırakma" -> 0, "Beton Krallığı" -> 3). İlk denemede
    # seçtiğim dört başlığın dördü de 4'e düşmüştü — hash'te sorun yok, katalog
    # genelinde dağılım düzgün (19 başlık n=10'da on kovaya yayılıyor), sadece
    # o dörtlü çakışmıştı.
    assert stock_art._secim_indeksi("Beni Bırakma", 5) != \
        stock_art._secim_indeksi("Beton Krallığı", 5)
    a = [x["id"] for x in stock_art._sirali_adaylar("Beni Bırakma", SORGU, esit)]
    b = [x["id"] for x in stock_art._sirali_adaylar("Beton Krallığı", SORGU, esit)]
    assert a != b, "hash ayrimi kayboldu"
    assert sorted(a) == sorted(b)


def test_atmosfer_sorgusunda_ESKI_davranis(monkeypatch):
    """Sorguda hiç sahne kelimesi yoksa puan ayrımı yapılamaz; o yolda
    davranış eskisiyle BİREBİR aynı kalmalı (sarmalı hash sırası)."""
    sorgu = "cinematic atmospheric"
    assert stock_art._sahne_kelimeleri(sorgu) == []
    sirali = stock_art._sirali_adaylar("Sabah Senin", sorgu, HAVUZ)
    bas = stock_art._secim_indeksi("Sabah Senin", len(HAVUZ))
    beklenen = [HAVUZ[(bas + i) % len(HAVUZ)]["id"] for i in range(len(HAVUZ))]
    assert [a["id"] for a in sirali] == beklenen


def test_bos_havuz_bos_doner():
    assert stock_art._sirali_adaylar("Sabah Senin", SORGU, []) == []
