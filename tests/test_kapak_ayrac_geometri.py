# -*- coding: utf-8 -*-
"""Kapak başlığı ile tema-rengi AYRAÇ çizgisi arasındaki geometri.

NEDEN VAR (2026-09-11): `generate_cover._compose_cover_rich` başlık bloğunu
ayracın üstüne oturtuyor ama `y_title` ifadesi (`y_rule - fs*(1.15 + 1.33*(n-1))`)
metin KUTUSUNUN altını ayracın 0.18 em İÇİNE sokuyordu. Ekranda harf fiilen
kesilmiyordu — ama sadece kullanılan fontun (Segoe UI Bold) kutu altında ~0.395
em boş "internal leading" bırakması sayesinde. Yani doğruluk, kodun hiç
bilmediği bir font metriğine bağlıydı; `config.FONT_BOLD_PATH` değişse ya da
kuyruğu daha derin bir font gelse tema rengi çizgi `ç/ş/y/p` kuyruklarını
SESSİZCE kesmeye başlardı (hata vermez, sadece bazı başlıklarda göze çarpar —
"konuma bağlı ve sessiz" bozulma).

Bu test o sessizliği kapatıyor: gerçekten render edip PİKSEL ölçüyor.
ffmpeg yoksa atlanır (CI'da kurulu, bu geliştirme makinesinde de var).
"""

import os
import subprocess
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import config                      # noqa: E402
import generate_cover as gc       # noqa: E402

pytestmark = pytest.mark.skipif(
    __import__("shutil").which("ffmpeg") is None, reason="ffmpeg yok")

ACCENT = (233, 69, 149)           # kontrastı yüksek olsun, ölçüm netleşsin
# İlk ~2 karakterinde ALT-UZANTI olan başlıklar — ayraç yalnızca out_w*0.09
# genişliğinde, yani sadece baştaki birkaç karakterin altından geçiyor. "Ge"
# ile başlayan bir başlıkta bu hata hiç görünmez; hatayı görünür kılan tam
# olarak baştaki `Ç/Ş/y/p`.
BASLIKLAR = ["Çığlık", "Şafak Çöküyor Ve Gece Uzuyor", "Yağmur", "puslu yol"]


def _ayrac_y(w, h):
    """_compose_cover_rich'in ayraç y'sini AYNI aritmetikle yeniden kurar."""
    basis = min(w, h)
    y_bar = h - int(basis * 0.03)
    y_brand = y_bar - int(h * 0.05) - int(basis * 0.30)
    return y_brand - int(h * 0.025) - 3


def _en_alt_beyaz(png, w, h, x0, x1, y_son):
    """[x0,x1) sütunlarında, y_son'a kadar en ALTTAKİ beyaz (harf) satırı."""
    ham = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", png, "-f", "rawvideo",
         "-pix_fmt", "gray", "-"], capture_output=True).stdout
    assert len(ham) == w * h, "ham çerçeve boyutu beklenenden farklı"
    en_alt = None
    for y in range(0, min(h, y_son)):
        satir = ham[y * w:(y + 1) * w]
        if any(satir[x] > 225 for x in range(x0, x1)):
            en_alt = y
    return en_alt


@pytest.fixture(scope="module")
def bokeh(tmp_path_factory):
    d = tmp_path_factory.mktemp("kapak")
    duz, bg = str(d / "duz.png"), str(d / "bg.png")
    gc._radial_background(duz, ACCENT)
    gc._add_bokeh(duz, bg, ACCENT, seed=7)
    return bg


@pytest.mark.parametrize("baslik", BASLIKLAR)
@pytest.mark.parametrize("boyut", [gc.COVER_SIZE_WIDE, gc.COVER_SIZE_TALL])
def test_ayrac_baslik_kuyrugunu_kesmiyor(baslik, boyut, bokeh, tmp_path):
    w, h = boyut
    out = str(tmp_path / "cover.png")
    gc._compose_cover_rich(bokeh, out, baslik, ACCENT, out_w=w, out_h=h)

    y_rule = _ayrac_y(w, h)
    margin = int(w * 0.07)
    rule_w = int(w * 0.09)
    # Ayraç HARFİN ÜSTÜNE çiziliyor (drawbox drawtext'ten SONRA), yani kesilen
    # piksel yok olur — "çizginin üstünde beyaz var mı" diye bakmak yanıltır.
    # Doğru ölçüt: harf mürekkebinin EN ALTI ayracın ÜSTÜNDE kalmalı.
    ink = _en_alt_beyaz(out, w, h, margin, margin + rule_w, y_rule + 40)
    assert ink is not None, "ayracın x aralığında hiç başlık harfi bulunamadı"
    assert ink < y_rule, (
        "%r (%dx%d): başlık ayracın İÇİNE giriyor (harf altı %d >= ayraç %d)"
        % (baslik, w, h, ink, y_rule))
    # Ayrıca sadece "kıl payı" geçmesin: en az yarım satır boşluk olsun ki
    # font değişince hemen kesmeye başlamasın.
    fs_tavan = int(min(w, h) * 0.16)
    assert y_rule - ink >= int(fs_tavan * 0.15), (
        "%r (%dx%d): pay çok dar (%d px) — font metriğine bağımlı kalıyor"
        % (baslik, w, h, y_rule - ink))


def test_satir_yuksekligi_sabiti_gercek_olcumle_uyusuyor(tmp_path):
    """DRAWTEXT_SATIR_YUKSEKLIGI bir TAHMİN değil, ölçülmüş bir değer olmalı.

    Sabit yanlışsa iki satırlı başlıklarda blok kayar ve ayraç payı sessizce
    erir — bu yüzden sabitin kendisi de test ediliyor."""
    font = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    w, h, fs, y0 = 800, 1200, 144, 100
    nl = chr(10)

    def ciz(metin, out):
        f = ("color=c=black:s=%dx%d,drawtext=fontfile=%s:text='%s':"
             "fontcolor=white:fontsize=%d:x=40:y=%d" % (w, h, font, metin, fs, y0))
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                            "-i", f, "-frames:v", "1", "-update", "1", out],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, r.stderr[-400:]

    def alt(out):
        return _en_alt_beyaz(out, w, h, 0, w, h)

    a, b = str(tmp_path / "s1.png"), str(tmp_path / "s2.png")
    ciz("Çp", a)
    ciz("Çp" + nl + "Çp", b)
    olculen = (alt(b) - alt(a)) / fs
    assert abs(olculen - gc.DRAWTEXT_SATIR_YUKSEKLIGI) < 0.02, (
        "drawtext satır yüksekliği %.4f em ölçüldü ama sabit %.4f — "
        "generate_cover.DRAWTEXT_SATIR_YUKSEKLIGI güncellenmeli"
        % (olculen, gc.DRAWTEXT_SATIR_YUKSEKLIGI))
