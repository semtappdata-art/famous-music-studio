# -*- coding: utf-8 -*-
"""Aynı ses (md5) tekrarı: ne zaman UYARI, ne zaman HATA.

NEDEN VAR: `uyumluluk.py` aynı `audio.wav` md5'ini iki projede görüyordu ama
bulgu UYARI seviyesindeydi ve HER İKİ kapı da uyarıyı geçiriyor
(`auto_process.py` yalnızca `if _uh:` ile duruyor, `validate_project.py`
uyarıyı `warnings`'e koyup render'ı sürdürüyor). Yani aynı ses ÜÇÜNCÜ kez bir
projeye kopyalansa YİNE yayınlanırdı — kanalın en büyük riski olan
"inauthentic / toplu üretilmiş AI içerik" politikasının tam merkezindeki
davranış.

Eşiği körü körüne HATA'ya çekmek de olmazdı: `Küllerimden Geç` ve
`Yeniden Doğacağım` klasörlerinin İKİSİ de diskte duruyor ve md5'leri eşit;
biri (public) meşru orijinal, diğeri 11 Eylül'de liste dışına alınmış kopya.
Kör bir HATA meşru işlemleri de durdururdu.

KURAL (bkz. `uyumluluk.kontrol()` içindeki yorum): eşleşme ancak İKİ şart
birlikte sağlanırsa UYARI kalır — (1) BU projenin kaydında `kopya_notu` var
(belge) ve (2) çiftin en az bir tarafı yayından çekilmiş (kanıt). Aksi her
durumda HATA.
"""

import json
import os

import pytest

import uyumluluk


def _proje(kok, ad, durum=None, meta=None, ses=b"ayni-ses"):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    if durum is not None:
        (p / "state.json").write_text(
            durum if isinstance(durum, str)
            else json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    if meta is not None:
        (p / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                     encoding="utf-8")
    if ses is not None:
        (p / "audio.wav").write_bytes(ses)
    return str(p)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


def _md5_bulgusu(liste):
    return [x for x in liste if "md5" in x]


# --- 1. YENİ (işaretsiz) bir kopya: yayın DURMALI --------------------------

def test_isaretsiz_ucuncu_kopya_hata_uretir(kok):
    """Asıl açık buydu: aynı ses üçüncü kez kopyalanınca yine yayınlanıyordu."""
    _proje(kok, "Orijinal", durum={"youtube_video_id": "abc",
                                   "youtube_privacy": "public"})
    _proje(kok, "Liste Disi Kopya",
           durum={"youtube_video_id": "def", "youtube_privacy": "unlisted",
                  "kopya_notu": "bilinen kopya"})
    ucuncu = _proje(kok, "Ucuncu Kopya", durum={})
    hatalar, _ = uyumluluk.kontrol(ucuncu, "yukleme")
    assert _md5_bulgusu(hatalar), (
        "işaretsiz üçüncü kopya HATA almalı — uyarı iki kapıdan da geçiyor")
    assert any("Orijinal" in h for h in hatalar)


def test_isaretsiz_kopya_render_asamasinda_da_hata(kok):
    """Kapı yalnızca yüklemede değil, render'dan ÖNCE de kapanmalı."""
    _proje(kok, "Orijinal", durum={"youtube_video_id": "abc",
                                   "youtube_privacy": "public"})
    yeni = _proje(kok, "Yeni", durum={})
    hatalar, _ = uyumluluk.kontrol(yeni, "render")
    assert _md5_bulgusu(hatalar)


# --- 2. BİLİNEN çift: yanlış pozitif üretilmemeli --------------------------

def test_belgelenmis_ve_liste_disi_cift_sadece_uyari(kok):
    """Gerçek katalogdaki `Yeniden Doğacağım` / `Küllerimden Geç` deseni.

    İkisi de diskte, md5'leri eşit, ikisinde de `kopya_notu` var ve biri
    unlisted. İKİSİ de HATA ALMAMALI.
    """
    orijinal = _proje(kok, "Yeniden Dogacagim",
                      durum={"youtube_video_id": "kZML", "youtube_privacy": "public"},
                      meta={"kopya_notu": "'Küllerimden Geç' ile aynı ses"})
    kopya = _proje(kok, "Kullerimden Gec",
                   durum={"youtube_video_id": "-CQ7", "youtube_privacy": "unlisted",
                          "kopya_notu": "liste dışına alındı"})

    h1, u1 = uyumluluk.kontrol(orijinal, "yukleme")
    assert _md5_bulgusu(h1) == [], "meşru orijinal durdurulmamalı"
    assert _md5_bulgusu(u1), "bulgu tamamen kaybolmamalı, uyarı olarak kalmalı"

    h2, u2 = uyumluluk.kontrol(kopya, "yukleme")
    assert _md5_bulgusu(h2) == [], "zaten liste dışı kopya da durdurulmamalı"
    assert _md5_bulgusu(u2)


def test_kopya_notu_meta_jsonda_da_gecerli(kok):
    """Alan tarihsel olarak bir projede state.json'da, ötekinde meta.json'da."""
    _proje(kok, "Liste Disi",
           durum={"youtube_video_id": "x", "youtube_privacy": "unlisted"})
    p = _proje(kok, "Orijinal",
               durum={"youtube_video_id": "y", "youtube_privacy": "public"},
               meta={"kopya_notu": "çift belgelendi"})
    hatalar, uyarilar = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar) == []
    assert _md5_bulgusu(uyarilar)


# --- 3. Kaçış yolu bırakılmamalı ------------------------------------------

def test_kopya_notu_tek_basina_kapiyi_ACMAZ(kok):
    """Sadece not yazıp iki kaydı da yayında bırakmak = iki canlı kopya."""
    _proje(kok, "Digeri", durum={"youtube_video_id": "x",
                                 "youtube_privacy": "public"})
    p = _proje(kok, "Bu Proje", durum={"youtube_video_id": "y",
                                       "youtube_privacy": "public",
                                       "kopya_notu": "not yazdım, geçir"})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar), (
        "iki taraf da yayındayken `kopya_notu` tek başına yetmemeli")


def test_zamanlanmis_private_cekilmis_SAYILMAZ(kok):
    """Golden-hour zamanlanan video private duruyor ama PUBLIC OLACAK."""
    _proje(kok, "Zamanlanmis", durum={"youtube_video_id": "x",
                                      "youtube_privacy": "private",
                                      "youtube_publish_at": "2026-09-12T19:00:00Z"})
    p = _proje(kok, "Bu Proje", durum={"kopya_notu": "çift"})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar)


def test_karantinadaki_private_cekilmis_SAYILMAZ(kok):
    """Content ID karantinası (dj_tarama_bekliyor) temiz çıkarsa public olur."""
    _proje(kok, "Karantinada", durum={"youtube_video_id": "x",
                                      "youtube_privacy": "private",
                                      "dj_tarama_bekliyor": True})
    p = _proje(kok, "Bu Proje", durum={"kopya_notu": "çift"})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar)


def test_karsi_taraf_bozuk_state_json_ise_hata(kok):
    """"Bilmiyorum" ile "çözülmüş" aynı şey değil — bu deponun tekrar eden dersi."""
    _proje(kok, "Bozuk Komsu", durum='{"youtube_privacy": "unlis')
    p = _proje(kok, "Bu Proje", durum={"kopya_notu": "çift"})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar), (
        "okunamayan bir state.json kopyayı meşrulaştıramaz")


# --- 3b. Kapı yayına GİRECEK tarafta kapanır ------------------------------

def test_yayindaki_mesru_kayit_yeni_bir_kopya_yuzunden_DURMAZ(kok):
    """Birinin diske attığı yanlış kopya, meşru orijinali rehin almamalı.

    Tekrarı YARATACAK olan yayınlanmamış klasörün yayınlanmasıdır; kapı orada
    HATA veriyor. Yayındaki kayıtta da HATA vermek, onun geri doldurma/altyazı
    işlerini de durdururdu — engellenmek istenen şey bu değil.
    """
    yayinda = _proje(kok, "Orijinal", durum={"youtube_video_id": "abc",
                                             "youtube_privacy": "public"})
    yanlis = _proje(kok, "Yanlis Kopya", durum={})

    h1, u1 = uyumluluk.kontrol(yayinda, "yukleme")
    assert _md5_bulgusu(h1) == [], "yayındaki meşru kayıt durdurulmamalı"
    assert any("Yanlis Kopya" in x for x in _md5_bulgusu(u1)), (
        "yine de hangi klasörün sorunlu olduğu söylenmeli")

    h2, _ = uyumluluk.kontrol(yanlis, "yukleme")
    assert _md5_bulgusu(h2), "asıl kapı YAYINLANMAMIŞ kopyada kapanmalı"


def test_iki_taraf_da_yayindaysa_ikisi_de_hata(kok):
    """Kopya ZATEN yayına çıkmışsa (7 Eylül'de olan) muafiyet yok."""
    a = _proje(kok, "Bir", durum={"youtube_video_id": "x",
                                  "youtube_privacy": "public"})
    b = _proje(kok, "Iki", durum={"youtube_video_id": "y",
                                  "youtube_privacy": "public"})
    assert _md5_bulgusu(uyumluluk.kontrol(a, "yukleme")[0])
    assert _md5_bulgusu(uyumluluk.kontrol(b, "yukleme")[0])


def test_karsi_taraf_okunamiyorsa_muafiyet_YOK(kok):
    """Bozuk state.json "yayınlanmamış" sayılmaz — bilinmeyen ≠ zararsız."""
    _proje(kok, "Bozuk", durum='{"youtube_video_id": "ab')
    p = _proje(kok, "Yayinda", durum={"youtube_video_id": "x",
                                      "youtube_privacy": "public"})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert _md5_bulgusu(hatalar)


# --- 4. Hiç yayınlanmamış iki klasör (7 Eylül'de olan) ---------------------

def test_iki_yayinlanmamis_klasor_ayni_md5_ikisi_de_hata(kok):
    """Suno'dan YANLIŞ dosyayı kopyalamak — kaza tam olarak burada yakalanmalı.

    Hiçbiri yayınlanmadığı için hiçbiri "yayından çekilmiş" sayılmaz; ikisi de
    durur ve operatör hangisinin yanlış olduğunu ayırt eder.
    """
    a = _proje(kok, "A", durum={})
    b = _proje(kok, "B", durum={})
    assert _md5_bulgusu(uyumluluk.kontrol(a, "render")[0])
    assert _md5_bulgusu(uyumluluk.kontrol(b, "render")[0])


# --- 5. Mesaj operatöre NE YAPACAĞINI söylemeli ---------------------------

def test_hata_mesaji_yapilacagi_soyluyor(kok):
    """Sebebini söylemeyen bir engel, engellemeyen bir uyarı kadar işe yaramaz."""
    _proje(kok, "Orijinal", durum={"youtube_video_id": "abc",
                                   "youtube_privacy": "public"})
    p = _proje(kok, "Yeni", durum={})
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    mesaj = _md5_bulgusu(hatalar)[0]
    assert "Orijinal" in mesaj, "hangi projeyle çakıştığı yazmalı"
    assert "kopya_notu" in mesaj, "kopya ise ne yapılacağı yazmalı"
    assert "unlisted" in mesaj, "liste dışına alma adımı yazmalı"
    assert "audio.wav" in mesaj, "farklı kayıt olmalıysa ne yapılacağı yazmalı"
    assert "henüz yayınlanmamış" in mesaj or "YouTube'da" in mesaj, (
        "karşı tarafın yayın durumu yazmalı")


# --- 6. Yardımcıların tek tek davranışı -----------------------------------

@pytest.mark.parametrize("durum, beklenen", [
    ({"youtube_privacy": "unlisted"}, True),
    ({"youtube_privacy": "private"}, True),
    ({"youtube_privacy": "private", "youtube_publish_at": "2026-09-12"}, False),
    ({"youtube_privacy": "private", "dj_tarama_bekliyor": True}, False),
    ({"youtube_privacy": "public"}, False),
    ({}, False),
    (None, False),
])
def test_yayindan_cekilmis(durum, beklenen):
    assert uyumluluk._yayindan_cekilmis(durum) is beklenen


# --- 7. GERÇEK katalog muhafızı -------------------------------------------

def test_gercek_katalogdaki_cift_hala_isaretli():
    """Bilinen çiftin KANITI yerinde mi — yoksa kapı meşru işi durdurur.

    `kopya_notu` alanları kanıt: biri silinirse `Yeniden Doğacağım` (public,
    orijinal) bir anda HATA almaya başlar ve yayın hattı sessizce tıkanır.
    Bu test o sessiz tıkanmayı önceden bağırır.
    """
    kok_dizin = os.path.join(os.path.dirname(os.path.abspath(
        uyumluluk.__file__)), "projects")
    cift = ("Yeniden Doğacağım", "Küllerimden Geç")
    for ad in cift:
        p = os.path.join(kok_dizin, ad)
        if not os.path.isdir(p):
            pytest.skip("gerçek katalog bu ortamda yok: %s" % ad)
    isaretli = []
    cekilmis = []
    for ad in cift:
        p = os.path.join(kok_dizin, ad)
        d, m = uyumluluk._durum(p), uyumluluk._meta(p)
        isaretli.append(uyumluluk._kopya_notu_var(d, m))
        cekilmis.append(uyumluluk._yayindan_cekilmis(d))
    assert all(isaretli), (
        "çiftin İKİ tarafında da `kopya_notu` olmalı — yoksa md5 kapısı meşru "
        "'%s' işlemlerini durdurur" % cift[0])
    assert any(cekilmis), (
        "çiftin bir tarafı liste dışı KALMALI ('Küllerimden Geç'); ikisi de "
        "yayına dönerse aynı kayıt kanalda iki kez canlı olur")
