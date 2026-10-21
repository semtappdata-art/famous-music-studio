# -*- coding: utf-8 -*-
"""`bluesky_upload.grapheme_len()` — 300 sınırının sayacı (C-14).

NEDEN VAR (2026-09-12 denetimi): fonksiyonun docstring'i bir GARANTİ ifade
ediyordu — *"gerçek grapheme sayısından asla AZ saymaz"* — ve o garantiyi
doğrulayan HİÇBİR test yoktu. Garanti YANLIŞTI: ZWJ dalı bir sonraki karakteri
KOŞULSUZ yutuyordu, yani `"a" + ZWJ + "b"` gerçekte 2 grapheme iken 1
sayılıyordu.

BEDELİ: Bluesky 300'lük sınırı grapheme üzerinden uyguluyor. AZ sayan bir
sayaç, `trim_to_graphemes()`'i "daha yer var" diye yanıltır ve sınırı AŞAN bir
gönderi üretir — Bluesky isteği REDDEDER, yani gönderi hiç yayınlanmaz.
FAZLA saymak ise en kötü ihtimalle metni birkaç karakter erken kırpar.

Bu deponun kuralı (CLAUDE.md): *bir yorum bir GARANTİ ifade ediyorsa, o
garantiyi doğrulayan bir test olmadan yazma.* Bu dosya o testtir.

Ağ YOK: `grapheme_len`/`trim_to_graphemes` saf fonksiyonlar.
"""

import os
import sys
import unicodedata

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import bluesky_upload as B                               # noqa: E402

ZWJ = "‍"
VS16 = "️"


# --- ASIL ARIZA -----------------------------------------------------------

def test_harfler_arasindaki_ZWJ_birlestirmez():
    """C-14'ün kendisi: `a` + ZWJ + `b` = 2 grapheme, 1 DEĞİL.

    ÇALIŞMADIĞINI NASIL ANLARIZ: bu test 1 görür — sayaç yine AZ sayıyordur.
    """
    assert B.grapheme_len("a" + ZWJ + "b") == 2


def test_turkce_harfler_arasindaki_ZWJ_de_birlestirmez():
    assert B.grapheme_len("ş" + ZWJ + "ğ") == 2


# --- gerçek emoji ZWJ dizileri: TEK grapheme kalmalı ----------------------

@pytest.mark.parametrize("metin,beklenen,ad", [
    ("\U0001F468" + ZWJ + "\U0001F469" + ZWJ + "\U0001F467", 1, "aile"),
    ("\U0001F3F3" + VS16 + ZWJ + "\U0001F308", 1, "gökkuşağı bayrağı"),
    ("\U0001F469" + ZWJ + "\U0001F4BB", 1, "kadın yazılımcı"),
    ("\U0001F469\U0001F3FD", 1, "ten rengi modifierı"),
    ("\U0001F1F9\U0001F1F7", 1, "bayrak (bölgesel gösterge çifti)"),
    ("\U0001F1F9\U0001F1F7\U0001F1E9\U0001F1EA", 2, "iki bayrak yan yana"),
    ("\U0001F3A7", 1, "tek emoji"),
])
def test_emoji_dizileri_tek_grapheme(metin, beklenen, ad):
    assert B.grapheme_len(metin) == beklenen, ad


def test_duz_metin_len_ile_ayni():
    m = "Famous Music Studio — yeni parça yayında!"
    assert B.grapheme_len(m) == len(m)


def test_birlestirici_isaret_onceki_graphemee_katiliyor():
    """NFD ile ayrılmış "ö" = 2 kod noktası ama TEK grapheme."""
    ayrik = unicodedata.normalize("NFD", "gökyüzü")
    assert len(ayrik) > len("gökyüzü")
    assert B.grapheme_len(ayrik) == len("gökyüzü")


# --- GARANTİNİN KENDİSİ ---------------------------------------------------

_ORNEKLER = [
    "",
    "a",
    "Merhaba dünya",
    "a" + ZWJ + "b",
    "a" + ZWJ + ZWJ + "b",
    "yeni parça \U0001F3A7 dinle",
    "\U0001F468" + ZWJ + "\U0001F469" + ZWJ + "\U0001F467" + " ailece",
    "\U0001F1F9\U0001F1F7 Türkiye",
    "\U0001F3F3" + VS16 + ZWJ + "\U0001F308",
    unicodedata.normalize("NFD", "şarkı sözü"),
    "ç" + ZWJ + "1" + ZWJ + "x",
]


@pytest.mark.parametrize("metin", _ORNEKLER)
def test_garanti_AZ_saymaz(metin):
    """Docstring'in ifade ettiği garanti — artık ölçülüyor.

    Alt sınır olarak "ayrı grapheme olduğu KESİN olan" karakterleri sayıyoruz:
    birleştirici işaret / ZWJ / varyasyon seçici / ten rengi / bölgesel
    gösterge OLMAYAN her kod noktası, kendinden önce ZWJ yoksa, ayrı bir
    grapheme'dir. Sayaç bundan AZ dönerse garanti çiğnenmiştir.
    """
    alt_sinir = 0
    onceki_zwj = False
    for ch in metin:
        code = ord(ch)
        if code == 0x200D:
            onceki_zwj = True
            continue
        birlesik = (unicodedata.combining(ch)
                    or 0xFE00 <= code <= 0xFE0F
                    or 0x1F3FB <= code <= 0x1F3FF
                    or 0x1F1E6 <= code <= 0x1F1FF)
        if not birlesik and not onceki_zwj:
            alt_sinir += 1
        onceki_zwj = False
    assert B.grapheme_len(metin) >= alt_sinir, metin


@pytest.mark.parametrize("metin", _ORNEKLER)
def test_asla_kod_noktasi_sayisindan_FAZLA_olmaz(metin):
    """Üst sınır: grapheme sayısı hiçbir zaman len()'i geçemez."""
    assert B.grapheme_len(metin) <= len(metin)


# --- kırpma: sayaçla tutarlı olmalı --------------------------------------

def test_trim_sonucu_HER_ZAMAN_limitin_altinda():
    """Sayaç AZ sayarsa burası sessizce sınırı aşar — asıl bedel burada."""
    metin = ("a" + ZWJ + "b " ) * 60 + "son"
    for limit in (20, 50, 120, 300):
        kirpik = B.trim_to_graphemes(metin, limit)
        assert B.grapheme_len(kirpik) <= limit, (limit, kirpik)


def test_limitin_altindaki_metin_DEGISMEDEN_donuyor():
    metin = "kısa bir caption \U0001F3A7"
    assert B.trim_to_graphemes(metin, 300) == metin


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
