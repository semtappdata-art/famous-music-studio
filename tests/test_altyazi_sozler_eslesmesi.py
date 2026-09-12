# -*- coding: utf-8 -*-
"""Altyazı hattının EN BÜYÜK sessiz riski: bir şarkının altyazısına BAŞKA
şarkının sözlerinin yazılması.

NEDEN AYRI BİR DOSYA (test_caption_align.py zaten var): o dosya hizalama
ARİTMETİĞİNİ test ediyor (eşleşen kelime ASR zamanını alsın, nakarat tekrarları
karışmasın, dejenere cue birleşsin). Hiçbiri "sözler dosyası doğru şarkıya mı
ait" sorusunu sormuyor — ve gerçek risk orada: yanlış dosya seçilirse hizalama
hatasız çalışır, geçerli bir SRT üretir, YouTube kabul eder, izleyici görür,
biz görmeyiz.

ÖLÇÜM (2026-09-11, 19 sözler dosyasında tam çapraz, bu dosyanın altındaki
testlerle aynı yöntem):
  - YANLIŞ şarkı eşlendiğinde (kusursuz ASR ile bile) en yüksek eşleşme 0,146
  - DOĞRU şarkıda, gerçekçi %25 ASR bozulmasıyla en düşük eşleşme 0,303
`caption_align.MIN_ESLESME_ORANI = 0.25` bu iki bulutun arasında.

Ağa ÇIKMAZ, gerçek token/ASR gerektirmez: ASR sentetik olarak gerçek sözler
dosyalarından üretiliyor.
"""

import difflib
import io
import os
import random
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import caption_align
import stock_art


# --- yardımcılar -----------------------------------------------------------

def _sarkilar():
    """Depodaki gerçek `*_sozler.md`'lerin "Temiz Sözler" bölümleri."""
    import glob
    out = {}
    for p in sorted(glob.glob(os.path.join(_REPO, "*_sozler.md"))):
        stem = os.path.basename(p)[: -len("_sozler.md")]
        lyr = caption_align.extract_clean_lyrics(io.open(p, encoding="utf-8").read())
        if lyr:
            out[stem] = lyr
    return out


def _sahte_asr(lyrics: str, bozukluk: float = 0.0, seed: int = 0) -> str:
    """Sözlerden sahte bir ASR SRT'si: satır başı 2,4 sn; kelimelerin
    `bozukluk` kadarı yanlış duyulmuş, üçte biri de hiç duyulmamış."""
    rnd = random.Random(seed)
    bloklar = []
    t = 1.0
    for i, satir in enumerate([x.strip() for x in lyrics.splitlines() if x.strip()]):
        kelimeler = []
        for w in satir.split():
            r = rnd.random()
            if r < bozukluk * 0.3:
                continue                      # ASR kaçırdı
            if r < bozukluk:
                w = (w[:-1] + "x") if len(w) > 2 else (w + "x")   # yanlış duydu
            kelimeler.append(w)
        if not kelimeler:
            kelimeler = ["mm"]
        e = t + 2.4

        def ts(x):
            ms = int(round(x * 1000))
            h, ms = divmod(ms, 3600000)
            m, ms = divmod(ms, 60000)
            sn, ms = divmod(ms, 1000)
            return "%02d:%02d:%02d,%03d" % (h, m, sn, ms)

        bloklar.append("%d\n%s --> %s\n%s\n" % (i + 1, ts(t), ts(e), " ".join(kelimeler)))
        t = e + 0.3
    return "\n".join(bloklar)


def _yaz(tmp_path, ad, icerik):
    p = tmp_path / ad
    p.write_text(icerik, encoding="utf-8")
    return str(p)


def _md(lyrics):
    return "## Temiz Sözler\n```\n%s\n```\n" % lyrics


def _oran(asr_srt: str, lyrics: str) -> float:
    asr_norm = [w[0] for w in caption_align._build_word_time_list(
        caption_align.parse_srt_cues(asr_srt))]
    real_norm = [caption_align._norm_word(w)
                 for c in caption_align.split_into_cues(lyrics) for w in c.split()]
    return caption_align.esleme_istatistigi(asr_norm, real_norm)[2]


# --- 1) Türkçe büyük "İ" normalizasyonu ------------------------------------

def test_buyuk_i_asr_ile_ayni_normalize_olur():
    """`"İçimde".lower()` Python'da "i" + U+0307 üretiyor; ASR küçük harf
    yazdığı için bu kelimeler HİÇ eşleşmiyordu (katalogda 14 kelime)."""
    assert caption_align._norm_word("İçimde") == caption_align._norm_word("içimde")
    assert "̇" not in caption_align._norm_word("İçimde")


def test_buyuk_i_noktasiz_i_ile_karismaz():
    """Türkçe doğru eşleme I->ı: "IŞIK" ile "ışık" aynı, "İyi" ile farklı."""
    assert caption_align._norm_word("IŞIK") == caption_align._norm_word("ışık")
    assert caption_align._norm_word("İyi") != caption_align._norm_word("ıyı")


def test_buyuk_i_ile_baslayan_kelime_artik_capa_olabiliyor(tmp_path):
    asr = ("1\n00:00:01,000 --> 00:00:03,000\niçimde tas kesilir\n\n"
           "2\n00:00:04,000 --> 00:00:06,000\nyine de dururum\n")
    asr_p = _yaz(tmp_path, "asr.srt", asr)
    md_p = _yaz(tmp_path, "l.md", _md("İçimde tas kesilir, yine de dururum"))
    assert _oran(asr, "İçimde tas kesilir\nyine de dururum") == 1.0
    cues = caption_align.align(asr_p, md_p, 10)
    assert cues[0][0] == 1.0          # ASR'nin GERÇEK zamanı, aradeğer değil


# --- 2) Yanlış şarkı kapısı (LyricsMismatch) --------------------------------

def test_yanlis_sarkinin_sozleri_yayinlanmaz(tmp_path):
    """Gerçek iki şarkı: birinin ASR'si, ötekinin sözleriyle eşlenirse
    hizalama SESSİZCE devam ETMEMELİ."""
    sarkilar = _sarkilar()
    a, b = "kirik_zincir", "sokaklar_beni_tanir"
    asr_p = _yaz(tmp_path, "asr.srt", _sahte_asr(sarkilar[a], 0.0, seed=1))
    md_p = _yaz(tmp_path, "l.md", _md(sarkilar[b]))
    with pytest.raises(caption_align.LyricsMismatch):
        caption_align.align(asr_p, md_p, 200.0)


def test_dogru_sarki_gercekci_asr_bozulmasiyla_gecer(tmp_path):
    """Aynı kapı DOĞRU eşleşmeleri engellememeli — katalogdaki her şarkı,
    %25 ASR bozulmasında ve birkaç farklı rastgele tohumda geçmeli."""
    for stem, lyr in _sarkilar().items():
        for seed in range(3):
            asr_p = _yaz(tmp_path, "asr.srt", _sahte_asr(lyr, 0.25, seed))
            md_p = _yaz(tmp_path, "l.md", _md(lyr))
            cues = caption_align.align(asr_p, md_p, 400.0)
            assert cues, stem


def test_esik_iki_bulutun_arasinda():
    """Eşik keyfî değil: YANLIŞ eşleşmelerin EN YÜKSEĞİ ile DOĞRU
    eşleşmelerin EN DÜŞÜĞÜ arasında durmalı. Bu test, katalog büyüdükçe
    (yeni şarkı eklendikçe) iki bulut birbirine yaklaşırsa kırmızı yanar —
    eşiğin sessizce anlamsızlaşmasını engelleyen tek mekanizma."""
    sarkilar = _sarkilar()
    stemler = list(sarkilar)
    en_yuksek_yanlis = 0.0
    en_dusuk_dogru = 1.0
    for a in stemler:
        asr = _sahte_asr(sarkilar[a], 0.0, seed=1)          # kusursuz ASR
        en_dusuk_dogru = min(en_dusuk_dogru,
                             _oran(_sahte_asr(sarkilar[a], 0.25, 7), sarkilar[a]))
        for b in stemler:
            if a == b:
                continue
            # Küllerimden Geç / Yeniden Doğacağım AYNI kaydın iki yüklemesi ve
            # sözleri BİREBİR AYNI (bkz. CLAUDE.md) — "yanlış eşleşme" sayılmaz.
            if {a, b} == {"kullerimden_gec", "yeniden_dogacagim"}:
                continue
            en_yuksek_yanlis = max(en_yuksek_yanlis, _oran(asr, sarkilar[b]))

    assert en_yuksek_yanlis < caption_align.MIN_ESLESME_ORANI < en_dusuk_dogru, (
        "eşik iki bulutun arasında değil: yanlış=%.3f eşik=%.3f doğru=%.3f"
        % (en_yuksek_yanlis, caption_align.MIN_ESLESME_ORANI, en_dusuk_dogru))


# --- 3) Slug eşleşmesi: gevşek ön-ek altyazıda KABUL EDİLMEMELİ -------------

def test_katalogdaki_her_proje_kendi_sozler_dosyasini_buluyor():
    """18 projenin hepsi — özellikle ünsüz yumuşamalı "Beton Krallığı" ve
    aynı kaydın iki yüklemesi olan Küllerimden Geç / Yeniden Doğacağım."""
    import json
    import youtube_captions
    kok = os.path.join(_REPO, "projects")
    bulunan = 0
    for ad in sorted(os.listdir(kok)):
        d = os.path.join(kok, ad)
        if not os.path.isdir(d) or ad.startswith("_"):
            continue
        meta_p = os.path.join(d, "meta.json")
        if not os.path.isfile(meta_p):
            continue
        baslik = json.load(io.open(meta_p, encoding="utf-8")).get("title", "")
        p = youtube_captions._sozler_dosyasi(baslik)
        assert p, "%s: doğrulanmış sözler dosyası bulunamadı" % ad
        stem = os.path.basename(p)[: -len("_sozler.md")]
        slug = stock_art._slugify(baslik)
        oran = difflib.SequenceMatcher(None, slug, stem).ratio()
        assert stem == slug or oran >= youtube_captions.SLUG_BENZERLIK_ESIGI, (
            "%s -> %s (%.3f)" % (baslik, stem, oran))
        bulunan += 1
    # SABİT SAYI DEĞİL, TABAN (2026-09-12). Eskiden `== 18` yazıyordu ve
    # katalog 19'a çıkınca test kırıldı — oysa yeni bir şarkı eklemek ARIZA
    # DEĞİL, bu deponun normal işleyişi. CLAUDE.md'nin "buraya sabit test
    # sayısı yazma, dakikalar içinde yanlışa düşer" kuralının aynısı.
    # Bu satırın gerçek işi "döngü hiç çalışmadı" halini yakalamak: sıfır ya
    # da bir avuç proje görülüyorsa keşif bozulmuştur. Üst sınır YOK.
    assert bulunan >= 18, "katalog küçülmüş ya da keşif bozulmuş: %d proje" % bulunan


@pytest.mark.parametrize("baslik, gevsek_dosya", [
    ("Neon", "neon_kalp"),                  # ön-ek: yeni şarkı, eski dosya
    ("Son", "son_kez"),
    ("Bu Gece", "bu_gece_kazandik"),
    ("Yeraltı Kralı", "yeralti"),           # ters yön: slug.startswith(stem)
    ("Sokaklar", "sokaklar_beni_tanir"),
])
def test_gevsek_onek_eslesmesi_altyazida_reddedilir(baslik, gevsek_dosya):
    """`stock_art.find_lyrics_file()` BU dosyaları döndürüyor (ön-ek kuralının
    uzunluk koruması yok) — görsel araması için zararsız, altyazı için DEĞİL.

    Gerçekleşmesi için "Neon" ya da "Yeraltı Kralı" adlı YENİ bir şarkı yeterli;
    o zaman bu videoya BAŞKA bir şarkının sözleri yazılırdı."""
    import youtube_captions
    # ÖN KOŞUL DEĞİŞTİ (2026-09-11, aynı gün): bu test yazıldığında
    # `find_lyrics_file` gevşek ön-eki KABUL ediyordu ve buradaki iddia da
    # onu doğruluyordu. Sonra kaynakta `stock_art.ONEK_UZUNLUK_ORANI`
    # koruması eklendi, yani artık KAYNAKTA da reddediliyor. Testin ASIL
    # iddiası (aşağıdaki `_sozler_dosyasi(...) is None`) değişmedi: altyazı
    # hattı ikinci bir süzgeç tutuyor ve iki kapı da BİLEREK duruyor
    # (savunma derinliği — `SLUG_BENZERLIK_ESIGI` difflib dalını da kapsıyor,
    # ön-ek koruması kapsamıyor).
    gevsek = stock_art.find_lyrics_file(baslik)
    assert gevsek is None, (
        "ön-ek koruması sonrası kaynakta da reddedilmeli: %s -> %s"
        % (baslik, gevsek))
    assert youtube_captions._sozler_dosyasi(baslik) is None
