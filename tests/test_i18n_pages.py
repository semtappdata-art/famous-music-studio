# -*- coding: utf-8 -*-
"""
Madde 31 — Tum sayfalarda TR/EN destegi (i18n_pages).

Kurallar:
  - privacy/epk/404 sayfalari i18n.js + i18n.css baglamali
  - Her sayfada dil toggle (data-dil-btn) olmali
  - i18n.js sozlugu TR/EN esit olmali
  - i18n.js ic ice <p> uretmemeli
  - Guvenli HTML: script/on*/javascript: temizlenmeli
  - Yeni sayfa eklendiginde bu test KIRMALI (regresyon korumasi)
"""
import os
import re

import pytest

REPO_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAYAFALAR = ["site/index.html", "site/privacy.html", "site/epk/bio.html", "site/404.html"]


def _oku(yol):
    p = os.path.join(REPO_KOK, yol)
    if not os.path.isfile(p):
        pytest.skip("dosya yok: " + yol)
    with open(p, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- sayfalar
@pytest.mark.parametrize("sayfa", SAYAFALAR)
def test_sayfa_i18n_js_bagli(sayfa):
    ic = _oku(sayfa)
    assert "i18n.js" in ic, f"{sayfa}: i18n.js baglanmamis"
    assert re.search(r'src="(\.\./)?i18n\.js"', ic), f"{sayfa}: i18n.js yolu hatali"


@pytest.mark.parametrize("sayfa", SAYAFALAR)
def test_sayfa_i18n_css_bagli(sayfa):
    ic = _oku(sayfa)
    assert re.search(r'href="(\.\./)?i18n\.css"', ic), f"{sayfa}: i18n.css baglanmamis"


@pytest.mark.parametrize("sayfa", SAYAFALAR)
def test_sayfa_dil_toggle_var(sayfa):
    ic = _oku(sayfa)
    assert 'data-dil-btn="tr"' in ic, f"{sayfa}: TR butonu yok"
    assert 'data-dil-btn="en"' in ic, f"{sayfa}: EN butonu yok"
    assert "dil-toggle" in ic


@pytest.mark.parametrize("sayfa", SAYAFALAR)
def test_sayfa_en_anahtar_kullanili(sayfa):
    """Her sayfa en az bir ceviri tasiyicisi kullanmali (bos sayfa olmamali)."""
    ic = _oku(sayfa)
    n = len(re.findall(r'data-i18n="([a-z0-9_.]+)"', ic))
    assert n >= 4, f"{sayfa}: sadece {n} ceviri tasiyicisi var (beklenen >= 4)"


# ---------------------------------------------------------------- sozluk
def _sozluk(dil):
    js = _oku("site/i18n.js")
    m = re.search(r"\b" + dil + r":\s*\{(.*?)\n    \}", js, re.S)
    assert m, "i18n.js'te %s blogu bulunamadi" % dil
    return set(re.findall(r"'([a-z0-9_.]+)':", m.group(1)))


def test_i18n_sozlugu_tr_en_esit():
    tr, en = _sozluk("tr"), _sozluk("en")
    assert tr == en, (
        "TR/EN anahtar farki — TR eksik: %s | EN eksik: %s"
        % (sorted(en - tr)[:10], sorted(tr - en)[:10])
    )


def test_i18n_anahtar_sayisi_yeterli():
    tr = _sozluk("tr")
    assert len(tr) >= 150, "i18n anahtari azaldi: %d" % len(tr)


def test_i18n_degerlerde_ic_ice_p_yok():
    """Deger <p> ile baslamamali — data-i18n zaten <p>/<span> icinde."""
    js = _oku("site/i18n.js")
    kotu = []
    for dil in ("tr", "en"):
        m = re.search(r"\b" + dil + r":\s*\{(.*?)\n    \}", js, re.S)
        for anahtar, deger in re.findall(r"'([a-z0-9_.]+)': '(.*?)',", m.group(1), re.S):
            if deger.strip().startswith("<p>"):
                kotu.append("%s/%s" % (dil, anahtar))
    assert not kotu, "ic ice <p> ureten degerler: %s" % kotu[:8]


def test_i18n_guvenli_html_temizleyici():
    """script/on*/javascript: temizlenmeli, guvenli etiketler korunmali."""
    js = _oku("site/i18n.js")
    assert "TEHLIKELI_ETIKET" in js
    assert "OLAY_ATTR" in js
    assert "TEHLIKELI_URL" in js
    assert "htmlTemizle" in js
    # guvenli HTML yazimi (textContent yerine)
    assert "metinYaz" in js
    assert "el.innerHTML = htmlTemizle(v)" in js


def test_i18n_metin_yaz_etiket_korur():
    """<strong> gibi etiketler korunmali (textContent'a duz yazilirsa kaybolur)."""
    js = _oku("site/i18n.js")
    assert "if (!/[<&]/.test(v)) { el.textContent = v; return; }" in js


def test_ortak_i18n_css_dosyasi_var():
    ic = _oku("site/i18n.css")
    assert ".dil-toggle" in ic
    assert ".aktif" in ic
    # index.html'de gomulu CSS KURALLARI olmamali (tek kaynak) — yorum serbest
    idx = _oku("site/index.html")
    assert ".dil-toggle {" not in idx, "index.html'de gomulu .dil-toggle CSS kurali kaldi"
    assert ".dil-toggle button" not in idx, "index.html'de gomulu toggle CSS kurali kaldi"


def test_epk_i18n_js_yolu_dogru():
    """epk/bio.html alt klasorde — i18n.js 'site/epk/i18n.js' olarak ARANAMAZ."""
    ic = _oku("site/epk/bio.html")
    assert 'src="../i18n.js"' in ic, "epk/bio.html: i18n.js yolu '..' ile baslamali"
    assert 'src="i18n.js"' not in ic, "epk/bio.html: goreli yol hatali (404 verir)"


def test_yeni_site_sayfalari_ihmal_edilmemis():
    """site/ altinda yeni HTML varsa bu test KIRMALI — yeni sayfa kontrol edilmeli."""
    site = os.path.join(REPO_KOK, "site")
    bulunan = set()
    for dizin, _alt, dosyalar in os.walk(site):
        if "assets" in dizin or "api" in dizin:
            continue
        for ad in dosyalar:
            if ad.endswith(".html"):
                rel = os.path.relpath(os.path.join(dizin, ad), site).replace("\\", "/")
                bulunan.add("site/" + rel)
    bilinmeyen = bulunan - set(SAYAFALAR)
    assert not bilinmeyen, (
        "yeni sayfa(lar) bulundu: %s — bu teste ekle ve i18n kontrolu yap" % sorted(bilinmeyen)
    )
