# -*- coding: utf-8 -*-
"""Süpürgelerin "hiçbir şey yapmadım" koşuları da log'a iz bırakmalı.

NEDEN (2026-09-12'de canlı olarak ölçüldü): `auto_process.log`'da
`Telegram/Bluesky geri doldurma: ...` satırları YALNIZCA golden-hour
koşularında görünüyordu. Sebep `ek_platform_backfill.backfill()`'in ilk
satırı:

    if config.next_golden_publish_time() is not None:
        sonuc["durum"] = "golden-hour disinda"
        return sonuc            # islenen/tavan/kalan hepsi BOŞ

`auto_process._ek_platform_backfill()` yalnızca `islenen`, `tavan` ve sıfırdan
büyük `kalan` değerlerini yazdığı için bu dönüş log'a TEK BİR satır bile
düşürmüyordu. `facebook_backfill` tarafında durum daha kötüydü: `_facebook_backfill()`
SADECE `durum == "tamam" and islenen` dalını yazıyordu, yani "kapalı",
"beklemede", "tavan" ve "bitti" dönüşlerinin dördü de tamamen sessizdi.

Bedeli: günün 24 saatinin 18'i golden-hour DIŞI, yani koşuların dörtte üçünde
**"süpürge çalıştı, işi yoktu"** ile **"süpürge artık `main()`'in `finally`
bloğundan hiç çağrılmıyor"** log'da BİREBİR AYNI görünüyordu. CLAUDE.md'nin
üçüncü sorusu ("çalışmadığını nasıl anlarız?") tam olarak cevapsızdı ve
2026-09-12'de bu ayrımı yapabilmek için ayrı bir soruşturma gerekti.

İKİNCİ ARIZA — bağlantı seviyesinde, aynı sınıftan: `_facebook_backfill()`
süpürgeyi `backfill(limit=1)` ile çağırıyordu, `log=log` GEÇMİYORDU. Modülün
varsayılanı `_stderr`, yani 2026-09-12'de eklenen politika kapısının
"UYUMLULUK HATASI — Facebook geri doldurma ATLANDI" satırı `notify` import
edilemediğinde `auto_process.log`'a değil stderr'e düşüp KAYBOLUYORDU
(`_ek_platform_backfill` aynı çağrıda `log=log` geçiyor — asimetri kazaydı).

Bu testler AĞA ÇIKMAZ ve GERÇEK süpürgeleri ÇALIŞTIRMAZ: iki modül de
`sys.modules`'a konan taklitlerle değiştiriliyor (fonksiyonlar `backfill`'i
çağrı anında import ediyor, bu yüzden taklit yeterli).
"""

import os
import sys
import types

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

import auto_process


def _kurulum(monkeypatch, modul_adi, sonuc):
    """`modul_adi` yerine sabit `sonuc` dönen bir taklit koyar; log'u toplar.

    Dönen sözlük çağrının kwargs'ını da taşıyor — `log=` geçilip geçilmediği
    davranışla değil, ÇAĞRIYLA doğrulanıyor.
    """
    cagri = {}

    def _sahte_backfill(*a, **kw):
        cagri["args"] = a
        cagri["kwargs"] = kw
        return dict(sonuc)

    sahte = types.ModuleType(modul_adi)
    sahte.backfill = _sahte_backfill
    monkeypatch.setitem(sys.modules, modul_adi, sahte)

    satirlar = []
    monkeypatch.setattr(auto_process, "log", lambda m: satirlar.append(m))
    return satirlar, cagri


# --- ek_platform_backfill (Telegram/Bluesky) ------------------------------

def test_ek_platform_golden_hour_disinda_tek_satir_yazar(monkeypatch):
    satirlar, _ = _kurulum(monkeypatch, "ek_platform_backfill", {
        "durum": "golden-hour disinda", "islenen": [], "kalan": {}, "tavan": {},
    })
    auto_process._ek_platform_backfill()
    assert satirlar, ("golden-hour dışı koşu log'a hiçbir iz bırakmıyor — "
                      "süpürgenin hiç çağrılmamasından ayırt edilemez")
    assert len(satirlar) == 1, "koşu başına tek satır olmalı (gürültü sınırı)"
    assert "golden-hour" in satirlar[0]


def test_ek_platform_hepsi_tamamlandiginda_da_iz_birakir(monkeypatch):
    # Kota VAR, golden-hour İÇİ, ama gidecek aday yok: `kalan` sıfır olduğu
    # için eski kod burada da hiçbir şey yazmıyordu.
    satirlar, _ = _kurulum(monkeypatch, "ek_platform_backfill", {
        "durum": "tamam", "islenen": [], "tavan": {},
        "kalan": {"Telegram": 0, "Bluesky": 0},
    })
    auto_process._ek_platform_backfill()
    assert satirlar


def test_ek_platform_is_varken_ozet_satiri_EKLENMEZ(monkeypatch):
    """Gürültü sınırı: mevcut satırlar varken özet satırı tekrar yazılmaz."""
    satirlar, _ = _kurulum(monkeypatch, "ek_platform_backfill", {
        "durum": "tamam", "tavan": {},
        "islenen": [{"platform": "Telegram", "proje": "X", "sonuc": "7"}],
        "kalan": {"Telegram": 3},
    })
    auto_process._ek_platform_backfill()
    assert len(satirlar) == 2          # islenen + kalan
    assert not any("golden-hour" in s for s in satirlar)


def test_ek_platform_tavan_satiri_ozetle_ikilenmiyor(monkeypatch):
    satirlar, _ = _kurulum(monkeypatch, "ek_platform_backfill", {
        "durum": "tamam", "islenen": [],
        "tavan": {"Telegram": "bugün 1 gönderi yapıldı (tavan 1)"},
        "kalan": {"Telegram": 15},
    })
    auto_process._ek_platform_backfill()
    assert len(satirlar) == 2          # tavan + kalan
    assert any("tavan" in s for s in satirlar)


# --- facebook_backfill ----------------------------------------------------

@pytest.mark.parametrize("sonuc", [
    {"durum": "beklemede", "sebep": "golden-hour dışındayız"},
    {"durum": "kapalı", "sebep": "config.EK_PLATFORMLAR['facebook'] False"},
    {"durum": "tavan", "sebep": "bugün 2 gönderi yapıldı"},
    {"durum": "bitti", "sebep": "Facebook'a gitmemiş proje kalmadı"},
])
def test_facebook_gonderisiz_kosular_iz_birakir(monkeypatch, sonuc):
    satirlar, _ = _kurulum(monkeypatch, "facebook_backfill", sonuc)
    auto_process._facebook_backfill()
    assert satirlar, "gönderi yapılmayan koşu log'a hiçbir iz bırakmıyor: %r" % sonuc
    assert len(satirlar) == 1


def test_facebook_engellenen_sayisi_ozette_gorunur(monkeypatch):
    satirlar, _ = _kurulum(monkeypatch, "facebook_backfill", {
        "durum": "tamam", "kalan": 14, "islenen": [],
        "engellenen": [{"proje": "Küllerimden Geç", "sebep": "aynı md5"}],
    })
    auto_process._facebook_backfill()
    assert satirlar
    assert "1" in satirlar[0] and "engel" in satirlar[0].lower()


def test_facebook_supurgeye_log_gecirilir(monkeypatch):
    """BAĞLANTI muhafızı: politika kapısının satırı auto_process.log'a düşmeli."""
    _, cagri = _kurulum(monkeypatch, "facebook_backfill",
                        {"durum": "beklemede", "sebep": "golden-hour dışındayız"})
    auto_process._facebook_backfill()
    assert "log" in cagri["kwargs"], (
        "facebook_backfill.backfill() `log=` olmadan çağrılıyor — modülün "
        "varsayılanı _stderr, politika kapısının satırı auto_process.log'a "
        "hiç ulaşmıyor")
    assert callable(cagri["kwargs"]["log"])


def test_facebook_islenen_varken_tek_satir(monkeypatch):
    satirlar, _ = _kurulum(monkeypatch, "facebook_backfill", {
        "durum": "tamam", "kalan": 13,
        "islenen": [{"proje": "Gece Sürüşü", "video_id": "123"}],
    })
    auto_process._facebook_backfill()
    assert len(satirlar) == 1
    assert "123" in satirlar[0]


def test_facebook_video_id_yoksa_cokmez(monkeypatch):
    """`x['video_id']` KeyError'ı tüm özeti 'HATA' satırına çeviriyordu."""
    satirlar, _ = _kurulum(monkeypatch, "facebook_backfill", {
        "durum": "tamam", "kalan": 13, "islenen": [{"proje": "Gece Sürüşü"}],
    })
    auto_process._facebook_backfill()
    assert len(satirlar) == 1
    assert "HATA" not in satirlar[0]
