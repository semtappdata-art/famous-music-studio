# -*- coding: utf-8 -*-
"""Kapak (thumbnail) dosyası seçimi — SESSİZ eski-kapak arızasına karşı.

NEDEN (2026-09-11): `_find_cover()` adayları sabit liste sırasıyla tarayıp İLK
eşleşeni döndürüyordu. Liste `["cover.jpg", "cover.jpeg", "cover.png"]` olduğu
için `cover.jpg` her zaman `cover.png`'yi yeniyordu — oysa kapak üreticisi
(`generate_cover.py`) `cover.png` yazıyor. Bir projede eski bir `cover.jpg`
kalmışsa yenilenen PNG SESSİZCE yok sayılıyor ve YouTube/TikTok/Instagram'a
ESKİ kapak gidiyordu; hiçbir hata/uyarı satırı yoktu (bkz. `dj_sets/_arda`,
yenilenmemiş `cover.jpg`). Bu deponun en sık deseni: doğru yazılmış kod, yanlış
sırayla, sessiz sonuç.

Testler iki şeyi birden çiviliyor: (1) en YENİ mtime kazanır, (2) birden fazla
aday varsa stdout'a UYARI düşer — asıl arıza yanlış seçim değil, SESSİZLİKTİ.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import instagram_upload
import tiktok_upload
import youtube_upload

MODULLER = [youtube_upload, tiktok_upload, instagram_upload]


def _yaz(proje_dir, ad, mtime):
    yol = os.path.join(str(proje_dir), ad)
    with open(yol, "wb") as f:
        f.write(b"sahte gorsel")
    os.utime(yol, (mtime, mtime))
    return yol


# --- 1) En yeni mtime kazanır (liste sırası DEĞİL) ---

@pytest.mark.parametrize("modul", MODULLER, ids=lambda m: m.__name__)
def test_yeni_png_eski_jpgyi_yener(tmp_path, modul):
    _yaz(tmp_path, "cover.jpg", 1_600_000_000)   # eski, yenilenmemiş
    yeni = _yaz(tmp_path, "cover.png", 1_700_000_000)  # bugün üretilen
    assert modul._find_cover(str(tmp_path)) == yeni


@pytest.mark.parametrize("modul", MODULLER, ids=lambda m: m.__name__)
def test_jpg_gercekten_yeniyse_o_secilir(tmp_path, modul):
    """Kural "png her zaman kazanır" DEĞİL, "en yeni kazanır" — kullanıcının
    elle koyduğu taze bir cover.jpg de geçerli bir kapaktır."""
    _yaz(tmp_path, "cover.png", 1_600_000_000)
    yeni = _yaz(tmp_path, "cover.jpg", 1_700_000_000)
    assert modul._find_cover(str(tmp_path)) == yeni


@pytest.mark.parametrize("modul", MODULLER, ids=lambda m: m.__name__)
def test_tek_aday_ve_hic_aday_yok(tmp_path, modul):
    assert modul._find_cover(str(tmp_path)) is None
    tek = _yaz(tmp_path, "cover.png", 1_700_000_000)
    assert modul._find_cover(str(tmp_path)) == tek


# --- 2) Birden fazla aday varsa UYARI (sessiz kalmasın) ---

@pytest.mark.parametrize("modul", MODULLER, ids=lambda m: m.__name__)
def test_coklu_adayda_uyari_basilir(tmp_path, modul, capsys):
    _yaz(tmp_path, "cover.jpg", 1_600_000_000)
    _yaz(tmp_path, "cover.png", 1_700_000_000)
    modul._find_cover(str(tmp_path))
    cikti = capsys.readouterr().out
    assert "UYARI" in cikti
    assert "cover.png" in cikti and "cover.jpg" in cikti


@pytest.mark.parametrize("modul", MODULLER, ids=lambda m: m.__name__)
def test_tek_adayda_uyari_yok(tmp_path, modul, capsys):
    _yaz(tmp_path, "cover.png", 1_700_000_000)
    modul._find_cover(str(tmp_path))
    assert "UYARI" not in capsys.readouterr().out


# --- 3) Dikey/yatay TERCİHİ mtime'dan önce gelir ---

def test_youtube_shorts_dikeyi_tercih_eder(tmp_path):
    """Shorts thumbnail'i 9:16 olmalı — 16:9 cover.png daha YENİ olsa bile
    dikey varyant kazanır (mtime sadece aynı grup içindeki uzantı çakışmasını
    çözer, oran tercihini EZMEZ)."""
    _yaz(tmp_path, "cover.png", 1_800_000_000)
    dikey = _yaz(tmp_path, "cover_vertical.png", 1_600_000_000)
    assert youtube_upload._find_cover_vertical(str(tmp_path)) == dikey


def test_youtube_shorts_dikey_yoksa_yatayya_duser(tmp_path):
    yatay = _yaz(tmp_path, "cover.png", 1_700_000_000)
    assert youtube_upload._find_cover_vertical(str(tmp_path)) == yatay


def test_youtube_shorts_dikey_grubunda_en_yeni(tmp_path):
    _yaz(tmp_path, "cover_vertical.jpg", 1_600_000_000)
    yeni = _yaz(tmp_path, "cover_vertical.png", 1_700_000_000)
    assert youtube_upload._find_cover_vertical(str(tmp_path)) == yeni


@pytest.mark.parametrize("modul", [tiktok_upload, instagram_upload],
                         ids=lambda m: m.__name__)
def test_dikey_platformlar_dikeyi_tercih_eder(tmp_path, modul):
    """TikTok/Instagram videosu dikey — 16:9 kapak daha yeni olsa bile
    cover_vertical.* kazanmalı (eski davranışın korunması şart)."""
    _yaz(tmp_path, "cover.png", 1_800_000_000)
    dikey = _yaz(tmp_path, "cover_vertical.png", 1_600_000_000)
    assert modul._find_cover(str(tmp_path)) == dikey


@pytest.mark.parametrize("modul", [tiktok_upload, instagram_upload],
                         ids=lambda m: m.__name__)
def test_dikey_grubunda_da_en_yeni_kazanir(tmp_path, modul):
    _yaz(tmp_path, "cover_vertical.jpg", 1_600_000_000)
    yeni = _yaz(tmp_path, "cover_vertical.png", 1_700_000_000)
    assert modul._find_cover(str(tmp_path)) == yeni
