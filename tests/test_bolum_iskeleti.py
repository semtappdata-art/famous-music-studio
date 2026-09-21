# -*- coding: utf-8 -*-
"""Bölüm iskeleti KODDA ve BELGEDE aynı olmak zorunda.

NEDEN VAR: kural 2026-09-12'de `suno_prompt_hazirlik.md`'ye yazıldı ama üretici
(`yeni_parca.py`) eski tek şablonu basmaya devam ediyordu — yani belge bir şey
söylüyor, kod başka bir şey yapıyordu. Bu, deponun CLAUDE.md'de yazdığı
"yalan söyleyen yorum, hiç yorum olmamasından kötüdür" kuralının dosya
ölçeğindeki hâli.

İkinci ve daha sinsi sebep: `tests/test_yeni_parca.py` "[Intro]" varlığını
çiviliyordu ve "Vardiya" başlığı ŞANS ESERİ 3 numaralı (Intro'lu) iskelete
düştüğü için yeşil kalıyordu. Başka bir başlık seçilse testler kırılırdı.

Ağa ÇIKMAZ, dosya yazmaz.
"""

import hashlib
import io
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

import yeni_parca


BELGE = os.path.join(_REPO, "suno_prompt_hazirlik.md")

# Belgede "Hesaplanmış örnekler" satırında yazılı olan değerler.
BELGEDEKI_ORNEKLER = {
    "Kırık Zincir": 0,
    "Sabah Senin": 1,
    "Yeraltı": 1,
    "Son Kez": 2,
    "Yürek Yarası": 3,
    "Gece Sürüşü": 3,
}


def test_belgedeki_ornekler_KODLA_ayni():
    """Belge altı şarkı için hesaplanmış indeks yazıyor; kod aynısını vermeli.

    Ayrışırlarsa sözler dosyası bir iskeletle yazılır, üretilen ses başka
    bir iskeletle beklenir — arşiv sessizce tutarsızlaşır."""
    for baslik, beklenen in BELGEDEKI_ORNEKLER.items():
        assert yeni_parca.iskelet_sec(baslik) == beklenen, baslik


def test_ornekler_BELGEDE_gercekten_yaziyor():
    """Yukarıdaki sözlük belgeden KOPYALANDI — belge değişirse burası da
    değişsin diye asıl metin de okunuyor."""
    metin = io.open(BELGE, encoding="utf-8").read()
    i = metin.find("Hesaplanmış örnekler")
    assert i > 0, "belgede 'Hesaplanmış örnekler' satırı yok"
    parca = metin[i:i + 400]
    for baslik, beklenen in BELGEDEKI_ORNEKLER.items():
        kalip = re.escape(baslik) + r"`?\s*(?:→|->)\s*" + str(beklenen)
        assert re.search(kalip, parca), "%s -> %d belgede yok" % (baslik, beklenen)


def test_formul_belgede_yazilanin_AYNISI():
    """sha256(başlık)[:8] % 4 — belge bu formülü açıkça yazıyor."""
    for baslik in BELGEDEKI_ORNEKLER:
        seed = int(hashlib.sha256(baslik.encode("utf-8")).hexdigest()[:8], 16)
        assert yeni_parca.iskelet_sec(baslik) == seed % 4


def test_dort_iskelet_var_ve_HEPSI_farkli():
    assert len(yeni_parca.ISKELETLER) == 4
    assert len(set(yeni_parca.ISKELETLER)) == 4


def test_uc_iskelette_INTRO_YOK():
    """Kuralın varlık sebebi: doymuş şablondan kaçmak.

    Dördü de `[Intro]` ile başlasaydı değişiklik hiçbir şey çözmezdi."""
    introsuz = [i for i, s in enumerate(yeni_parca.ISKELETLER)
                if not s[0].endswith("Intro")]
    assert len(introsuz) == 2, introsuz          # 0 ve 1
    # 2 numaralı "Instrumental Intro" — Intro var ama SEN tarif ediyorsun,
    # yani Suno'nun tür-varsayılanı devreye girmiyor. Doymuş olan yalnız 3.
    assert yeni_parca.ISKELETLER[3][0] == "Intro"
    assert yeni_parca.ISKELETLER[2][0] == "Instrumental Intro"


def test_her_iskelette_chorus_ve_outro_VAR():
    """Şablonun iki değişmezi: çengel ve kapanış kuralı."""
    for i, s in enumerate(yeni_parca.ISKELETLER):
        assert "Chorus" in s, i
        assert s[-1] == "Outro", i


def test_intro_kurali_ILK_ANLATI_bolumune_gidiyor():
    """1 numaralı iskelette açılış NAKARAT; nakaratın işi çapayı vermektir,
    yani "ilk satır temayı adlandırmasın" kuralı oraya uygulanamaz. Belge bu
    çakışmanın çözümünü yazıyor: kural açılıştan sonraki ilk kıtaya kayar."""
    satirlar = yeni_parca.iskelet_satirlari("Sabah Senin")   # -> iskelet 1
    assert satirlar[0] == "[Chorus]"
    metin = "\n".join(satirlar)
    # Kural metni Verse 1'in altında olmalı, Chorus'un değil.
    verse_i = satirlar.index("[Verse 1]")
    kural_i = next(i for i, s in enumerate(satirlar)
                   if "DOĞRUDAN ADLANDIRMAZ" in s)
    assert kural_i > verse_i, metin
    assert "DOĞRUDAN ADLANDIRMAZ" not in satirlar[1]


def test_tekrar_eden_chorus_BIREBIR_AYNI_diyor():
    """İlk Chorus doldurulacak, sonrakiler onun kopyası olmalı — aksi hâlde
    şarkının çengeli her seferinde değişir."""
    satirlar = yeni_parca.iskelet_satirlari("Kırık Zincir")   # -> iskelet 0
    birebir = [s for s in satirlar if "BİREBİR aynısı" in s]
    chorus_sayisi = sum(1 for s in satirlar if s == "[Chorus]")
    assert chorus_sayisi >= 2
    assert len(birebir) == chorus_sayisi - 1


def test_deterministik_ayni_baslik_ayni_iskelet():
    for baslik in ("Sabah Senin", "Kırık Zincir", "Yeni Bir Şarkı"):
        a = yeni_parca.iskelet_satirlari(baslik)
        b = yeni_parca.iskelet_satirlari(baslik)
        assert a == b


def test_uretilen_sablonda_bolum_sirasi_ISKELETLE_ayni():
    """Yer tutucular arasında etiketlerin SIRASI bozulmasın."""
    for baslik in BELGEDEKI_ORNEKLER:
        satirlar = yeni_parca.iskelet_satirlari(baslik)
        etiketler = [s[1:-1] for s in satirlar if re.match(r"^\[[^\]]+\]$", s)]
        assert tuple(etiketler) == yeni_parca.ISKELETLER[
            yeni_parca.iskelet_sec(baslik)], baslik
