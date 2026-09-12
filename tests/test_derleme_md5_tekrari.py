# -*- coding: utf-8 -*-
"""Aynı kayıt bir derlemeye İKİ KEZ giremez — md5 kapısı.

NEDEN BU TESTLER VAR (2026-09-11):
`derleme.adaylar()` kopyayı yalnızca `youtube_privacy in ("unlisted",
"private")` filtresiyle eliyordu — yani koruma kodun kendisinde DEĞİL,
"kopya olan taraf ELLE liste dışına alınmış" konvansiyonunda duruyordu.
`uyumluluk.py`'deki md5 tekrar kapısı aynı gün sıkılaştırıldı ve bundan
SONRA iki public kopyanın oluşmasını engelliyor, ama mevcut/geçmiş veri
için garanti vermiyor: bir gün o konvansiyon uygulanmazsa (ya da
`state.json` bozulup `youtube_privacy` kaybolursa) aynı ses derlemeye iki
kez girerdi. Bir derlemenin İÇİNDE aynı kaydın iki kez çıkması, YouTube'un
"önemli değişiklik yapılmadan bir araya getirilmiş şarkı koleksiyonu"
tarifine doğrudan yem olur — ve derlemenin var olma sebebi TAM OLARAK o
"inauthentic content" politikasına karşı küratörlük göstermek.

Testler üç şeyi çiviliyor:
  1. Aynı md5 -> biri elenir, KALAN İLK YAYINLANANDIR (izlenme DEĞİL —
     gerçek vakada kopya orijinalden daha çok izlenmişti).
  2. Eleme SESSİZ DEĞİL (stderr'e satır düşer). Sessiz eleme, sonradan
     "bu şarkı derlemede neden yok" sorusunu cevapsız bırakır.
  3. Boyut ön filtresi gerçekten çalışıyor — boyutlar tekilse md5 HİÇ
     hesaplanmıyor (`uyumluluk.py`'deki aynı desen).
"""

import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import derleme
import uyumluluk


def _proje(kok, ad, ses_icerik, *, privacy="public", yuklendi="2026-09-01T10:00:00",
           izlenme=0, tema="hiphop", video_id="vid_%s"):
    """`projects/<ad>` benzeri bir fikstür klasörü kurar."""
    p = os.path.join(str(kok), ad)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, "audio.wav"), "wb") as f:
        f.write(ses_icerik)
    st = {
        "youtube_video_id": video_id % ad if "%s" in video_id else video_id,
        "youtube_privacy": privacy,
        "youtube_uploaded_at": yuklendi,
        "youtube_views": izlenme,
    }
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(p, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": ad, "theme": tema}, f)
    return p


@pytest.fixture
def havuz(tmp_path, monkeypatch):
    """`adaylar()`ı tmp fikstür köküne bağlar; ffprobe'a bağımlılığı keser."""
    monkeypatch.setattr(derleme, "KAYNAK", str(tmp_path))
    # _sure() ffprobe çağırıyor; bu testlerin konusu SÜRE değil ELEME.
    monkeypatch.setattr(derleme, "_sure", lambda yol: 180.0)
    return tmp_path


def test_ayni_md5_tasiyan_iki_aday_tekine_dusuyor(havuz):
    """İki public aday AYNI sesi taşıyorsa derlemeye sadece biri girer."""
    ayni = b"RIFF" + b"\x01\x02\x03\x04" * 500
    _proje(havuz, "Yeniden Doğacağım", ayni, yuklendi="2026-09-01T14:46:26")
    _proje(havuz, "Küllerimden Geç", ayni, yuklendi="2026-09-07T13:42:00")

    adlar = [p["ad"] for p in derleme.adaylar()]
    assert len(adlar) == 1, "aynı ses derlemeye iki kez girdi: %r" % adlar


def test_kalan_ilk_yayinlanan_cok_izlenen_degil(havuz):
    """Gerçek vakanın sayılarıyla: kopya orijinalden DAHA ÇOK izlenmişti.

    'Küllerimden Geç' 7 Eylül'deki İKİNCİ yükleme ve 182 izlenmeyle
    orijinali ('Yeniden Doğacağım', 1 Eylül, 146) geçiyor. "Çok izlenen
    kalsın" kuralı kanalın kanonik kaydı olarak KOPYAYI seçerdi — bu test
    tam da o kuralın geri gelmesini engelliyor.
    """
    ayni = b"RIFF" + b"\x09\x08\x07\x06" * 500
    _proje(havuz, "Yeniden Doğacağım", ayni,
           yuklendi="2026-09-01T14:46:26", izlenme=146)
    _proje(havuz, "Küllerimden Geç", ayni,
           yuklendi="2026-09-07T13:42:00", izlenme=182)

    adlar = [p["ad"] for p in derleme.adaylar()]
    assert adlar == ["Yeniden Doğacağım"]


def test_farkli_md5_ikisi_de_kaliyor(havuz):
    """Kapı YALNIZCA birebir aynı sesi eliyor — yanlış pozitif yok."""
    _proje(havuz, "Son Kez", b"RIFF" + b"\xaa" * 2000)
    _proje(havuz, "Yeraltı", b"RIFF" + b"\xbb" * 2000)

    adlar = sorted(p["ad"] for p in derleme.adaylar())
    assert adlar == ["Son Kez", "Yeraltı"]


def test_ayni_boyut_farkli_icerik_elenmiyor(havuz):
    """Boyut ön filtresi bir KISA YOL, karar mercii DEĞİL.

    Boyutu eşit ama içeriği farklı iki dosya md5'e kadar gitmeli ve
    ikisi de kalmalı; ön filtre eleme yapan taraf olsaydı bu bozulurdu.
    """
    _proje(havuz, "A Şarkısı", b"RIFF" + b"\x11" * 3000)
    _proje(havuz, "B Şarkısı", b"RIFF" + b"\x22" * 3000)

    adlar = sorted(p["ad"] for p in derleme.adaylar())
    assert adlar == ["A Şarkısı", "B Şarkısı"]


def test_eleme_loga_dusuyor(havuz, capsys):
    """Eleme SESSİZ OLAMAZ — iki şarkının adı da satırda geçmeli.

    Bu deponun en pahalı hata sınıfı "sessizce bir şey yapan/yapmayan
    koruma" (bkz. CLAUDE.md); sessiz bir eleme sonradan "bu şarkı
    derlemede neden yok" sorusunu cevapsız bırakır.
    """
    ayni = b"RIFF" + b"\x33\x44" * 1000
    _proje(havuz, "Orijinal", ayni, yuklendi="2026-09-01T10:00:00")
    _proje(havuz, "Kopya", ayni, yuklendi="2026-09-07T10:00:00")

    derleme.adaylar()
    hata = capsys.readouterr().err
    assert "Kopya" in hata and "Orijinal" in hata
    assert "ELENDİ" in hata


def test_boyut_on_filtresi_gereksiz_md5_hesaplamiyor(havuz, monkeypatch):
    """Boyutlar tekilse md5 HİÇ çağrılmamalı.

    `uyumluluk.py`'deki aynı gerekçe: md5 pahalı (City Pulse Set'te 935 MB
    -> 11 sn), boyut bedava. Gerçek havuzda 17 dosyanın 17'si tekil
    boyutta — bu koruma pratikte bedava olmalı.
    """
    sayac = {"n": 0}
    gercek = uyumluluk._md5

    def _sayan(yol):
        sayac["n"] += 1
        return gercek(yol)

    monkeypatch.setattr(uyumluluk, "_md5", _sayan)

    _proje(havuz, "Bir", b"RIFF" + b"\x01" * 1000)
    _proje(havuz, "İki", b"RIFF" + b"\x02" * 1500)
    _proje(havuz, "Üç", b"RIFF" + b"\x03" * 2000)

    assert len(derleme.adaylar()) == 3
    assert sayac["n"] == 0, "boyutlar tekilken md5 %d kez hesaplandı" % sayac["n"]


def test_boyut_esitse_md5_sadece_o_grup_icin_hesaplaniyor(havuz, monkeypatch):
    """md5 yalnızca boyutu ÇAKIŞAN gruba giriyor — 2 dosya, 2 hesap."""
    sayac = {"n": 0}
    gercek = uyumluluk._md5

    def _sayan(yol):
        sayac["n"] += 1
        return gercek(yol)

    monkeypatch.setattr(uyumluluk, "_md5", _sayan)

    ayni = b"RIFF" + b"\x55" * 1000
    _proje(havuz, "Çift A", ayni)
    _proje(havuz, "Çift B", ayni)
    _proje(havuz, "Tekil", b"RIFF" + b"\x66" * 4321)   # boyutu farklı

    derleme.adaylar()
    assert sayac["n"] == 2, "beklenen 2 md5, olan %d" % sayac["n"]


def test_liste_disi_kopya_hala_eleniyor(havuz):
    """Eski `youtube_privacy` kapısı KALDIRILMADI — iki kapı birlikte.

    md5 kapısı eklenirken privacy filtresinin gereksizleştiği düşünülebilir;
    değil: unlisted bir kayıt md5'i EŞSİZ olsa bile yayında olmadığı için
    derlemeye girmemeli.
    """
    _proje(havuz, "Yayında", b"RIFF" + b"\x77" * 1000)
    _proje(havuz, "Liste Dışı", b"RIFF" + b"\x88" * 2222, privacy="unlisted")

    adlar = [p["ad"] for p in derleme.adaylar()]
    assert adlar == ["Yayında"]


def test_md5_uyumluluktan_iceri_aktariliyor_kopyalanmiyor(havuz, monkeypatch):
    """`derleme.py` kendi md5'ini YAZMAMALI — `uyumluluk._md5` kullanmalı.

    Bugün bu depoda kopya kod defalarca soruna yol açtı (en ağırı
    `state_io` vakası). İki yerde ayrı ayrı hesaplanan bir hash, ikisi
    ayrıştığında SESSİZCE farklı cevap verir. Bu test bağlantıyı çiviliyor:
    `uyumluluk._md5` yamalanınca `derleme` de onu görmeli.
    """
    cagrildi = {"var": False}

    def _sahte(yol):
        cagrildi["var"] = True
        return "sabit-hash"

    monkeypatch.setattr(uyumluluk, "_md5", _sahte)

    # Boyutları EŞİT: ön filtre geçilsin, md5'e gerçekten gidilsin.
    _proje(havuz, "X Şarkısı", b"RIFF" + b"\xa1" * 900)
    _proje(havuz, "Y Şarkısı", b"RIFF" + b"\xa2" * 900)

    kalan = derleme.adaylar()
    assert cagrildi["var"], "derleme.py kendi md5 kopyasını kullanıyor"
    # Sahte hash ikisini de aynı gösterdi -> biri elenmeli.
    assert len(kalan) == 1


def test_ses_okunamazsa_aday_dusmuyor_ama_sessiz_de_degil(havuz, capsys,
                                                          monkeypatch):
    """OSError kontrolü düşürür, ADAYI değil — ve log'a düşer.

    `uyumluluk.py`'deki aynı karar: kilitli/okunamayan bir dosya yüzünden
    kontrolün sessizce devre dışı kalması asıl tehlikedir.
    """
    _proje(havuz, "Okunur", b"RIFF" + b"\xc1" * 1000)
    kirik = _proje(havuz, "Okunmaz", b"RIFF" + b"\xc2" * 1000)

    gercek_getsize = os.path.getsize
    kirik_ses = os.path.join(kirik, "audio.wav")

    def _getsize(yol):
        if os.path.abspath(yol) == os.path.abspath(kirik_ses):
            raise OSError(13, "Permission denied")
        return gercek_getsize(yol)

    monkeypatch.setattr(os.path, "getsize", _getsize)

    adlar = sorted(p["ad"] for p in derleme.adaylar())
    assert adlar == ["Okunmaz", "Okunur"], "OSError adayı düşürdü"
    assert "YAPILAMADI" in capsys.readouterr().err
