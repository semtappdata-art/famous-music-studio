# -*- coding: utf-8 -*-
"""Stil ifadeleri havuzu (`config.STIL_IFADE_HAVUZU`) ve `suno_stil.py` seçicisi.

NEDEN VAR (2026-09-13, `suno_kalite_onerileri.md` §2 ve §7): stil tarifine
eklenen mix/master cümlesi her şarkıya birebir kopyalanırsa bütün katalogda
aynı dizi tekrarlanır. Bu, YouTube'un "toplu üretilmiş içerik" tanımına
yaklaştıran şablon izlerinden biri. Havuz tür bazlı, seçim proje adından
DETERMİNİSTİK: aynı şarkı için her çağrı aynı ifadeleri verir (ajan tekrar
çalıştırınca tarif değişmez), farklı şarkılar farklı alt küme ve sıra alır.

YASAKLAR testle kilitli: havuzda sanatçı adı, "Suno" ya da AI vurgusu yok;
`wide vocal` da yok (vokal merkezde kalmalı, A/B'deki merkez/yan ölçütünü
bozar).
"""

import json
import os
import re
import subprocess
import sys

import pytest

import config
import suno_stil

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ANA_TURLER = [t for t in config.THEMES if t != "dj"]
KATEGORILER = ("mix", "vokal", "duzenleme")

# Havuzda OLMAMASI gereken her şey. Sanatçı adı listesi kapsamlı olamaz; bu
# yüzden ikinci, YAPISAL bir koruma da var (aşağıda `_BICIM`): ifadeler yalnız
# küçük harf ASCII. Özel ad yazmak büyük harf ya da Türkçe karakter getirir.
YASAK = re.compile(
    r"suno|\bai\b|a\.i\.|artificial|generated|\bgpt\b|udio"
    r"|style of|in the vein|inspired by|sounds? like|reminiscent|a la\b"
    r"|wide vocal"
    r"|tarkan|sezen|aksu|ajda|pekkan|m[uü]sl[uü]m|g[uü]rses|ferdi|tayfur"
    r"|ceza|ezhel|sagopa|duman|teoman|manga|hadise|sertab|mabel|edis"
    r"|madonna|drake|eminem|taylor|swift|beyonce|weeknd|coldplay|adele"
    r"|billie|eilish|dua lipa|kanye|rihanna|daft punk|metallica|nirvana",
    re.IGNORECASE,
)
_BICIM = re.compile(r"[a-z0-9][a-z0-9 ,'/-]*")


def _tum_ifadeler():
    for tur in ANA_TURLER:
        for kat in KATEGORILER:
            for ifade in config.STIL_IFADE_HAVUZU[tur][kat]:
                yield tur, kat, ifade


def test_her_ana_turde_her_kategori_4_ile_6_secenek():
    for tur in ANA_TURLER:
        assert tur in config.STIL_IFADE_HAVUZU, tur
        for kat in KATEGORILER:
            secenekler = config.STIL_IFADE_HAVUZU[tur][kat]
            assert 4 <= len(secenekler) <= 6, (tur, kat, len(secenekler))
            assert len(set(secenekler)) == len(secenekler), (tur, kat)


def test_havuzda_yasak_kelime_yok():
    ihlal = [(t, k, i) for t, k, i in _tum_ifadeler() if YASAK.search(i)]
    assert ihlal == []


def test_havuz_yalniz_kucuk_harf_ascii():
    """Yapısal sanatçı adı koruması: özel ad büyük harf ya da Türkçe harf
    getirir. Liste tabanlı regex tek başına kapsamlı olamaz."""
    ihlal = [(t, k, i) for t, k, i in _tum_ifadeler() if not _BICIM.fullmatch(i)]
    assert ihlal == []


def test_yasak_regex_kendisi_calisiyor():
    """Muhafızın kendisi sessizce kör olmasın."""
    for ornek in ("Suno v6 mix", "ai generated vocal", "in the style of Tarkan",
                  "wide vocal", "Sezen Aksu ballad"):
        assert YASAK.search(ornek), ornek
    assert not YASAK.search("smooth controlled highs")


def test_secim_deterministik_ve_sayilar_dogru():
    a = suno_stil.stil_ifadeleri("Bu Gece Kazandık", "pop")
    b = suno_stil.stil_ifadeleri("Bu Gece Kazandık", "pop")
    assert a == b
    assert len(a["mix"]) == config.STIL_MIX_ADET
    assert len(a["vokal"]) == 1 and len(a["duzenleme"]) == 1
    assert len(set(a["mix"])) == len(a["mix"])
    havuz = config.STIL_IFADE_HAVUZU["pop"]
    assert set(a["mix"]) <= set(havuz["mix"])
    assert a["vokal"][0] in havuz["vokal"]
    assert a["duzenleme"][0] in havuz["duzenleme"]
    assert a["cumle"] == ", ".join(a["mix"] + a["vokal"] + a["duzenleme"])
    assert not YASAK.search(a["cumle"])


def test_ad_normalizasyonu_bosluk_ve_unicode():
    """Aynı şarkı iki farklı yazımla (NFD 'ı' / baştaki boşluk) çağrılınca
    farklı tarif çıkmamalı; aksi hâlde determinizm kâğıt üstünde kalır."""
    import unicodedata
    nfd = unicodedata.normalize("NFD", "Küllerimden Geç")
    assert (suno_stil.stil_ifadeleri("  " + nfd + " ", "arabesk")
            == suno_stil.stil_ifadeleri("Küllerimden Geç", "arabesk"))


def test_farkli_projeler_ayni_diziyi_almiyor():
    adlar = ["Şarkı %d" % i for i in range(30)]
    diziler = {tuple(suno_stil.stil_ifadeleri(ad, "rock")["mix"]) for ad in adlar}
    # 6 seçenekten sıralı 3'lü: 120 olası dizi. 30 adda en az 15 farklı dizi.
    assert len(diziler) >= 15, len(diziler)


def test_bilinmeyen_tur_hata():
    with pytest.raises(ValueError):
        suno_stil.stil_ifadeleri("X", "dj")
    with pytest.raises(ValueError):
        suno_stil.stil_ifadeleri("X", "yok-boyle-tur")


def test_tur_proje_meta_jsonundan_okunuyor(tmp_path):
    d = tmp_path / "Deneme Şarkı"
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"title": "Deneme Şarkı", "theme": "akustik"}),
                                 encoding="utf-8")
    assert suno_stil.turu_bul("Deneme Şarkı", kokler=str(tmp_path)) == "akustik"
    assert suno_stil.turu_bul("Olmayan", kokler=str(tmp_path)) is None


def _cli(*argumanlar, hashseed="0"):
    ortam = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED=hashseed)
    return subprocess.run([sys.executable, os.path.join(_KOK, "suno_stil.py"), *argumanlar],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=_KOK, env=ortam, timeout=60)


def test_cli_surecler_arasi_deterministik():
    """`hash()` süreç başına tuzlanır; seçim ona dayansaydı her koşu farklı
    tarif verirdi. İki farklı PYTHONHASHSEED ile aynı çıktı beklenir."""
    r1 = _cli("--proje", "Yükseliş", "--tur", "hiphop", "--json", hashseed="1")
    r2 = _cli("--proje", "Yükseliş", "--tur", "hiphop", "--json", hashseed="987")
    assert r1.returncode == 0, r1.stderr
    assert r1.stdout == r2.stdout
    veri = json.loads(r1.stdout)
    assert veri == suno_stil.stil_ifadeleri("Yükseliş", "hiphop")


def test_cli_tur_bulunamazsa_sifir_olmayan_cikis():
    r = _cli("--proje", "Hiç Olmayan Proje Adı 123")
    assert r.returncode != 0
    assert "--tur" in (r.stderr + r.stdout)
