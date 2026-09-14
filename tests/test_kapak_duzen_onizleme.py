# -*- coding: utf-8 -*-
"""Kapak düzen önizlemesi + KAPALI mesafe kapısı (özgünlük planı §2a, Aşama 1 iş 5).

Bu modül YAYINA BAĞLI DEĞİL: önizleme scratch klasörüne yazar, kapı bayrağı kapalı.
Testler: pHash / hamming / bindirme kutusu / IoU birimleri (ffmpeg ile sentetik
görüntüler), kapının üç koşulu, bayrak kapalıyken yayını ENGELLEMEMESİ, düzen
tanımlarında reddedilmiş dekoratif öğe olmaması ve önizleme komutunun yalnız
verilen klasöre yazması. Ağa çıkmaz, üretim dosyalarına yazmaz.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import kapak_duzen_onizleme as K   # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None
ffmpeg_gerekli = pytest.mark.skipif(not FFMPEG, reason="ffmpeg yok")


def _gorsel(yol, renk="gray", w=320, h=180, kutular=()):
    """Düz renk zemin + isteğe bağlı beyaz kutular (x, y, w, h)."""
    vf = "".join(",drawbox=x=%d:y=%d:w=%d:h=%d:color=white:t=fill" % k for k in kutular)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=%s:s=%dx%d:d=0.04%s" % (renk, w, h, vf),
                    "-frames:v", "1", "-update", "1", str(yol)], check=True)
    return str(yol)


# --- saf fonksiyonlar ---------------------------------------------------------

def test_hamming():
    assert K.hamming(0, 0) == 0
    assert K.hamming(0b1011, 0b0001) == 2
    assert K.hamming((1 << 63) - 1, 0) == 63


def test_iou():
    assert K.iou((0, 0, 9, 9), (0, 0, 9, 9)) == pytest.approx(1.0)
    assert K.iou((0, 0, 9, 9), (20, 20, 29, 29)) == 0.0
    # 10x10 ile 10x10, 5x10 örtüşme -> 50 / 150
    assert K.iou((0, 0, 9, 9), (5, 0, 14, 9)) == pytest.approx(50 / 150)
    assert K.iou(None, (0, 0, 1, 1)) == 0.0


# --- ffmpeg'li birimler -------------------------------------------------------

@ffmpeg_gerekli
def test_phash_ayni_goruntu_sifir_farkli_uzak(tmp_path):
    a = _gorsel(tmp_path / "a.png", kutular=[(20, 20, 120, 60)])
    b = _gorsel(tmp_path / "b.png", kutular=[(20, 20, 120, 60)])
    c = _gorsel(tmp_path / "c.png", kutular=[(200, 100, 100, 70), (10, 130, 60, 40)])
    ha, hb, hc = K.phash(a), K.phash(b), K.phash(c)
    assert 0 <= ha < (1 << 63)
    assert K.hamming(ha, hb) == 0
    assert K.hamming(ha, hc) >= 14


@ffmpeg_gerekli
def test_bindirme_kutusu_yalniz_eklenen_bolgeyi_bulur(tmp_path):
    art = _gorsel(tmp_path / "art.png", renk="0x303030", w=1600, h=900)
    kapak = _gorsel(tmp_path / "kapak.png", renk="0x303030", w=1600, h=900,
                    kutular=[(400, 100, 800, 300)])
    kutu = K.bindirme_kutusu(kapak, art)
    assert kutu is not None
    x0, y0, x1, y1 = kutu
    # 160x90 ızgarada beklenen: x 40..119, y 10..39 (±2 ölçekleme payı)
    assert abs(x0 - 40) <= 2 and abs(x1 - 119) <= 2
    assert abs(y0 - 10) <= 2 and abs(y1 - 39) <= 2
    assert K.bindirme_kutusu(art, art) is None


# --- kapı ---------------------------------------------------------------------

def _aday(ph=0, duzen="D2", kutu=(0, 60, 80, 89)):
    return {"phash": ph, "duzen": duzen, "kutu": kutu}


def test_kapi_bayrak_kapaliyken_yayini_engellemez():
    assert K.MESAFE_KAPISI_AKTIF is False
    gecmis = [_aday(ph=0, duzen="D2", kutu=(0, 60, 80, 89))] * 3
    gecti, sebepler = K.mesafe_kapisi(_aday(ph=0), gecmis)
    assert gecti is True
    assert any("kapalı" in s for s in sebepler)


def test_kapi_uc_kosul_aktifken():
    uzak = (1 << 40) - 1                          # 40 bit fark
    gecmis = [_aday(ph=uzak, duzen="D3", kutu=(40, 60, 120, 85)),
              _aday(ph=uzak, duzen="D4", kutu=(0, 30, 150, 55)),
              _aday(ph=uzak, duzen="D1", kutu=(25, 5, 134, 40))]
    temiz = _aday(ph=0, duzen="D2", kutu=(0, 70, 60, 89))
    assert K.mesafe_kapisi(temiz, gecmis, aktif=True) == (True, [])

    # 1) pHash yakın (geçmişin TAMAMINA karşı; en eskiye bile)
    yakin = [_aday(ph=0b111, duzen="D3", kutu=(40, 0, 50, 5))] + gecmis
    gecti, s = K.mesafe_kapisi(temiz, yakin, aktif=True)
    assert not gecti and any("pHash" in x for x in s)

    # 2) düzen kimliği son 3'ten biriyle aynı
    gecti, s = K.mesafe_kapisi(_aday(ph=0, duzen="D4", kutu=(0, 70, 60, 89)),
                               gecmis, aktif=True)
    assert not gecti and any("düzen" in x for x in s)
    # ...ama 4. sıradaki eski yayın düzen kuralına sayılmaz
    eski = [_aday(ph=uzak, duzen="D2", kutu=(0, 0, 1, 1))] + gecmis
    assert K.mesafe_kapisi(temiz, eski, aktif=True)[0] is True

    # 3) bindirme IoU >= 0,6 son 3'e karşı
    gecti, s = K.mesafe_kapisi(_aday(ph=0, duzen="D2", kutu=(25, 5, 134, 40)),
                               gecmis, aktif=True)
    assert not gecti and any("IoU" in x for x in s)


# --- düzen tanımları ----------------------------------------------------------

def test_duzenler_uc_aday_ve_yasak_dekor_yok():
    assert set(K.DUZENLER) == {"D2", "D3", "D4"}
    for kimlik, d in K.DUZENLER.items():
        assert d["kimlik"] == kimlik
        assert not (set(d.get("dekor", ())) & set(K.YASAK_OGELER)), kimlik
        assert d["logo_oran"] <= 0.18, "büyük logo bloğu reddedildi (%s)" % kimlik
        assert d["maks_satir"] <= 2
        assert d["punto_tavan_orani"] <= 0.14
    assert K.DUZENLER["D4"]["font"] == "kalin" and K.DUZENLER["D4"]["maks_satir"] == 1


def test_mood_stil_etiketinden_cikar_tahmin_etmez():
    assert K.mood_bul("Turkish rap, gritty street authenticity, deep 808") == "gritty"
    assert K.mood_bul("") is None
    assert K.mood_bul("Turkish pop, 120 BPM") is None
    for filtre in K.MOOD_COLOR_MODIFIERS.values():
        assert filtre and "'" not in filtre


# --- önizleme komutu yalnız verilen klasöre yazar -----------------------------

@ffmpeg_gerekli
def test_onizleme_yalniz_cikti_klasorune_yazar(tmp_path):
    proje = tmp_path / "Deneme Sarki"
    proje.mkdir()
    _gorsel(proje / "art.jpg", renk="0x4060a0", w=1600, h=1600, kutular=[(300, 300, 400, 400)])
    _gorsel(proje / "cover.png", renk="0x4060a0", w=1600, h=900)
    (proje / "meta.json").write_text(json.dumps({"title": "Deneme Sarki", "theme": "pop"}),
                                     encoding="utf-8")
    once = sorted(os.listdir(proje))
    repo_once = sorted(os.listdir(_KOK))
    cikti = tmp_path / "cikti"
    rc = K.main(["--cikti", str(cikti), "--projeler", str(proje)])
    assert rc == 0
    assert sorted(os.listdir(proje)) == once
    assert sorted(os.listdir(_KOK)) == repo_once
    dosyalar = set(os.listdir(cikti))
    for d in ("D2", "D3", "D4"):
        for oran in ("16x9", "9x16"):
            assert any(f.endswith("_%s_%s.png" % (d, oran)) for f in dosyalar), (d, oran)
    assert any(f.startswith("kontakt_16x9") for f in dosyalar)
