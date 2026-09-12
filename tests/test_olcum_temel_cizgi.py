# -*- coding: utf-8 -*-
"""`olcum_temel_cizgi.py` muhafızları.

NEDEN VAR: bu araç yılda birkaç kez çalışıyor (randevu 2026-10-09). Yılda
birkaç kez çalışan bir script, bozulduğunu ancak çalıştırıldığı gün — yani
ölçümün alınması GEREKEN gün — belli eder; o gün de geri dönüş yoktur, çünkü
ölçüm penceresi kayar. Testler bu boşluğu kapatıyor.

Üç şeyi koruyorlar:
  1. TEMEL ÇİZGİ ÜSTÜNE YAZILAMAZ (araç kaybedilemez tek dosyayı bozamaz).
  2. Çekim, temel çizgideki 14 bölümün AYNISINI üretir (bölüm adı sessizce
     düşerse karşılaştırma bir ay sonra yarım çalışır).
  3. Birincil metrik (%2 / %3 ortalaması) kopya videoyu ORTALAMAYA KATMAZ.

Hiçbir test ağa çıkmıyor: `Cekici(kuru=True)` `youtube_analytics`'i hiç import
etmiyor, dolayısıyla token da okunmuyor.
"""

import json
import os

import pytest

import olcum_temel_cizgi as ol


# --- 1. Temel çizgi muhafızı ------------------------------------------------
def test_temel_cizgi_cikti_yolu_olarak_reddedilir():
    with pytest.raises(SystemExit):
        ol._cikti_yolu(ol.TEMEL_CIZGI_PATH)


def test_temel_cizgi_goreli_yolla_da_reddedilir():
    """Mutlak yol karşılaştırması: `olcum_temel_cizgi.json` de aynı dosya."""
    with pytest.raises(SystemExit):
        ol._cikti_yolu(os.path.join(ol.BASE_DIR, ".", "olcum_temel_cizgi.json"))


def test_yaz_temel_cizgiye_zorla_ile_bile_yazmaz(tmp_path):
    with pytest.raises(SystemExit):
        ol.yaz({"x": 1}, ol.TEMEL_CIZGI_PATH, zorla=True)


def test_yaz_ayni_dosyanin_ustune_zorla_olmadan_yazmaz(tmp_path):
    hedef = tmp_path / "olcum_2026-10-09.json"
    ol.yaz({"a": 1}, str(hedef))
    with pytest.raises(SystemExit):
        ol.yaz({"a": 2}, str(hedef))
    ol.yaz({"a": 2}, str(hedef), zorla=True)
    assert json.loads(hedef.read_text(encoding="utf-8"))["a"] == 2


def test_varsayilan_cikti_adi_tarihli(tmp_path):
    import datetime
    yol = ol._cikti_yolu(bugun=datetime.date(2026, 10, 9))
    assert os.path.basename(yol) == "olcum_2026-10-09.json"


# --- 2. Çekim, 14 bölümü üretiyor mu ---------------------------------------
def test_dry_run_14_bolumu_da_uretir_ve_dosya_yazmaz(tmp_path, monkeypatch):
    onceki = set(os.listdir(ol.BASE_DIR))
    sonuc = ol.cek(kuru=True)
    for bolum in ol.BOLUMLER:
        assert bolum in sonuc, "eksik bölüm: %s" % bolum
    # Kuru koşu HİÇBİR dosya yaratmamalı.
    assert set(os.listdir(ol.BASE_DIR)) == onceki


def test_bolum_listesi_temel_cizgiyle_ortusuyor():
    """BOLUMLER, gerçek temel çizginin veri bölümlerinin AYNISI olmalı.

    Bir bölüm adı değişirse karşılaştırma o bölümü sessizce "YOK" sayardı.
    Dosya sadece OKUNUYOR.
    """
    if not os.path.isfile(ol.TEMEL_CIZGI_PATH):
        pytest.skip("temel çizgi diskte yok")
    with open(ol.TEMEL_CIZGI_PATH, encoding="utf-8") as f:
        temel = json.load(f)
    meta = {"alindi", "not", "kucuk_resim_degisikligi_tarihi",
            "veri_gecikmesi_notu", "olcum_turu"}
    assert set(ol.BOLUMLER) == set(temel) - meta


def test_kuru_cekici_aga_cikmaz():
    c = ol.Cekici(kuru=True)
    assert c.servis is None
    assert c.q("deneme", startDate="2026-01-01", endDate="2026-01-02",
               metrics="views") == {"_dry_run": "deneme"}


# --- 3. Birincil metrik: %2 / %3 --------------------------------------------
def _olcum(egriler):
    return {"alindi": "t", "kitle_tutma_28gun": {
        "vid%d" % i: {"proje": p, "egri": e, "onluk": {}}
        for i, (p, e) in enumerate(egriler.items())}}


def test_kopya_video_ortalamaya_katilmaz():
    """`Küllerimden Geç` = `Yeniden Doğacağım`'ın kopyası; ortalamayı bozmamalı."""
    eski = _olcum({"A": {"0.02": 0.80, "0.03": 0.70},
                   "Küllerimden Geç": {"0.02": 0.96, "0.03": 0.89}})
    yeni = _olcum({"A": {"0.02": 0.90, "0.03": 0.70},
                   "Küllerimden Geç": {"0.02": 0.10, "0.03": 0.10}})
    r = ol.karsilastir(eski, yeni)
    b = r["birincil"]["0.02"]
    assert b["video_sayisi"] == 1                     # sadece A
    assert b["haric_tutulan"] == ["Küllerimden Geç"]
    assert b["eski_ortalama"] == 0.8 and b["yeni_ortalama"] == 0.9
    assert b["fark_puan"] == 10.0
    # kopya ortalamadan çıktı ama TABLODA görünüyor (gizlenmiyor)
    assert "Küllerimden Geç" in b["video_bazinda"]


def test_yalnizca_bir_olcumde_olan_video_isaretleniyor():
    eski = _olcum({"A": {"0.02": 0.8, "0.03": 0.7},
                   "B": {"0.02": 0.9, "0.03": 0.8}})
    yeni = _olcum({"A": {"0.02": 0.8, "0.03": 0.7},
                   "C": {"0.02": 0.5, "0.03": 0.4}})
    b = ol.karsilastir(eski, yeni)["birincil"]["0.03"]
    assert b["yalnizca_eskide"] == ["B"] and b["yalnizca_yenide"] == ["C"]
    assert b["video_sayisi"] == 1


def test_bolum_durumu_hatali_bolumu_yakalar():
    eski = {"kanal_28gun": {"views": 1}}
    yeni = {"kanal_28gun": {"views": 2},
            "arama_terimleri_28gun": {"hata": "patladi"},
            "ulke_28gun": []}
    d = ol.karsilastir(eski, yeni)["bolum_durumu"]
    assert d["arama_terimleri_28gun"][1] == "HATA"
    assert d["ulke_28gun"][1] == "BOŞ"
    assert d["kitle_tutma_28gun"] == ("YOK", "YOK")
    assert d["kanal_28gun"] == ("var", "var")


def test_ikincil_kanal_farklari():
    eski = {"kanal_28gun": {"views": 100, "averageViewPercentage": 23.13}}
    yeni = {"kanal_28gun": {"views": 150, "averageViewPercentage": 25.4}}
    d = ol.karsilastir(eski, yeni)["ikincil"]["kanal_28gun"]
    assert d["views"]["fark"] == 50
    assert d["averageViewPercentage"]["fark"] == 2.27
    assert d["likes"]["fark"] is None        # iki tarafta da yok -> uydurma yok


# --- 4. Belgelenmiş sabitler kaymasın ---------------------------------------
def test_randevu_ve_temel_ortalama_sabitleri():
    """Devir belgesi (§4.1) bu üç değeri isimle referans veriyor."""
    assert ol.OLCUM_RANDEVUSU == "2026-10-09"
    assert ol.KUCUK_RESIM_DEGISIKLIGI == "2026-09-11"
    assert ol.TEMEL_TUTMA_ORTALAMASI == {"0.02": 0.837, "0.03": 0.715}
