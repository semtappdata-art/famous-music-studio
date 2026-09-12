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


def test_bozuk_state_json_md5_IKIZINI_de_dusuruyor(kok):
    """Tek bir yarım yazım, MEŞRU tarafı da yayından düşürür (C-2).

    Ölçülmüş ama testle kaplı OLMAYAN yan etki (2026-09-12 denetimi): depodaki
    tek belgelenmiş kopya çifti (`Küllerimden Geç` / `Yeniden Doğacağım`) bugün
    UYARI seviyesinde duruyor — çünkü karşı taraf okunabiliyor ve "yayından
    çekilmiş" görünüyor. Karşı tarafın `state.json`'ı bozulursa
    `cekilmis_taraf = None` **ve** `oteki_yayinda = True` olur, md5 muafiyetinin
    iki şartı da düşer ve kalan tek dal HATA'dır.

    Davranış BİLİNÇLİ ve DOĞRU ("bilmiyorum" != "çözülmüş"); test onu
    DEĞİŞTİRMİYOR, mesafeyi ÖLÇÜYOR: meşru taraf ile durmuş bir kanal arasında
    tek bir yarım JSON yazımı var.

    ÇALIŞMADIĞINI NASIL ANLARIZ: (3) numaralı iddia düşer — yani bozuk bir
    komşu sessizce "zararsız" sayılmaya başlanmıştır.
    """
    a = _proje(kok, "Kullerimden Gec",
               durum={"youtube_video_id": "-CQ7", "youtube_privacy": "unlisted",
                      "kopya_notu": "liste dışına alındı"})
    b = _proje(kok, "Yeniden Dogacagim",
               durum={"youtube_video_id": "kZML", "youtube_privacy": "public"},
               meta={"kopya_notu": "'Küllerimden Geç' ile aynı ses"})
    # Aynı ses md5'ini TAŞIMAYAN, ilgisiz üçüncü proje.
    ucuncu = _proje(kok, "Ilgisiz", durum={}, ses=b"bambaska-ses")

    # (1) TEMEL ÇİZGİ: çift bugün UYARI seviyesinde, meşru taraf akıyor.
    h0, u0 = uyumluluk.kontrol(b, "yukleme")
    assert _md5_bulgusu(h0) == [], h0
    assert _md5_bulgusu(u0), "bulgu tamamen kaybolmamalı"

    # (2) Tek bir YARIM YAZIM: A'nın state.json'ı diskte yarıda kesildi.
    (kok / "Kullerimden Gec" / "state.json").write_text('{"a":',
                                                        encoding="utf-8")

    # (3) İKİZ de düştü: meşru, yayındaki taraf artık HATA alıyor.
    h1, _ = uyumluluk.kontrol(b, "yukleme")
    assert _md5_bulgusu(h1), (
        "bozuk komşu md5 ikizini de durdurmalı — 'bilmiyorum' muafiyet değil")
    assert any("BİREBİR AYNI (md5)" in h for h in h1), h1

    # (4) YAN KAZANÇ: kanal DURMUYOR — ilgisiz proje etkilenmiyor (B-20).
    h2, _ = uyumluluk.kontrol(ucuncu, "yukleme")
    assert _md5_bulgusu(h2) == [], (
        "bozuk bir state.json yalnızca kendisini ve md5 ikizini durdurmalı")


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

    ASIL/KOPYA 2026-09-12'de TERS ÇEVRİLDİ (kullanıcının son kararı): asıl kayıt
    `Küllerimden Geç` (yeni görselli sürüm, kalıyor), kopya `Yeniden Doğacağım`
    (YouTube'un videodan aldığı karelerde kapak kartı BOŞ; kullanıcı liste dışına
    aldı). Bu test önceden "iki tarafta da `kopya_notu`, `Küllerimden Geç`
    liste dışı" diyordu — o varsayım artık yanlış.

    Yeni kanıt düzeni: `kopya_notu` YALNIZ kopyada (`Yeniden Doğacağım`) ve o
    taraf yayından çekilmiş; asıl tarafta not YOK ve kapı ona md5 HATASI
    VERMİYOR. Biri bozulursa asılın geri doldurmaları sessizce tıkanır — bu
    test o sessiz tıkanmayı önceden bağırır.
    """
    kok_dizin = os.path.join(os.path.dirname(os.path.abspath(
        uyumluluk.__file__)), "projects")
    asil, kopya = "Küllerimden Geç", "Yeniden Doğacağım"
    for ad in (asil, kopya):
        if not os.path.isdir(os.path.join(kok_dizin, ad)):
            pytest.skip("gerçek katalog bu ortamda yok: %s" % ad)
    pa, pk = os.path.join(kok_dizin, asil), os.path.join(kok_dizin, kopya)
    dk, mk = uyumluluk._durum(pk), uyumluluk._meta(pk)
    assert uyumluluk._kopya_notu_var(dk, mk), (
        "kopya tarafında (`%s`) `kopya_notu` olmalı" % kopya)
    assert uyumluluk._yayindan_cekilmis(dk), (
        "kopya (`%s`) YouTube'da liste dışı KALMALI; ikisi de yayına dönerse "
        "aynı kayıt kanalda iki kez canlı olur" % kopya)
    da, ma = uyumluluk._durum(pa), uyumluluk._meta(pa)
    assert not uyumluluk._kopya_notu_var(da, ma), (
        "asıl kayıtta (`%s`) `kopya_notu` OLMAMALI — not kopyayı işaretler" % asil)
    # Kapının KENDİSİ: iki taraf da md5 HATASI almamalı.
    # Bu kısım GERÇEK ses dosyası ister: `projects/*/audio.*` .gitignore'da, yani
    # CI checkout'unda YOK — md5 hesaplanamaz, kapı bulgu üretemez ve alttaki
    # "UYARI kalmalı" iddiası ortam yüzünden düşer (2026-09-12'de CI tam olarak
    # bununla kırmızıya döndü; yerelde 1383/1383 yeşildi). Ürün arızası değil,
    # ortam farkı. Yukarıdaki kopya_notu / yayından-çekilme iddiaları yalnız
    # İZLENEN state/meta dosyalarını okuduğu için CI'da KOŞMAYA DEVAM ediyor —
    # atlanan yalnız md5 kısmı.
    for p in (pa, pk):
        if not any(os.path.isfile(os.path.join(p, "audio" + uzanti))
                   for uzanti in (".wav", ".mp3", ".m4a")):
            pytest.skip("ses dosyası bu ortamda yok (gitignore / CI): %s"
                        % os.path.basename(p))
    for p in (pa, pk):
        hatalar, uyarilar = uyumluluk.kontrol(p, "yukleme")
        assert _md5_bulgusu(hatalar) == [], (p, hatalar)
        assert _md5_bulgusu(uyarilar), "bulgu kaybolmamalı, UYARI kalmalı"


# --- 8. TERS YÖN: not yalnız KOPYADA, asıl tarafta YOK ----------------------
# 2026-09-12 kararıyla gerçek katalog bu düzene geçti. Eski kural "BU projede
# `kopya_notu` şart" diyordu, yani notu kopyaya taşımak asılın geri
# doldurmalarını md5 HATASIYLA durdururdu. Yeni (dar) muafiyet: BU proje zaten
# yayında + karşı taraf `kopya_notu` taşıyor + karşı taraf yayından çekilmiş.

def _ters_cift(kok, asil_gizlilik="public"):
    asil = _proje(kok, "Kullerimden Gec",
                  durum={"youtube_video_id": "-CQ7", "youtube_privacy": asil_gizlilik})
    kopya = _proje(kok, "Yeniden Dogacagim",
                   durum={"youtube_video_id": "kZML", "youtube_privacy": "unlisted",
                          "kopya_notu": "kapağı eksik sürüm; asıl = Küllerimden Geç"})
    return asil, kopya


def test_ters_yon_asil_engellenmiyor(kok):
    asil, kopya = _ters_cift(kok)
    h, u = uyumluluk.kontrol(asil, "yukleme")
    assert _md5_bulgusu(h) == [], "asıl kayıt durdurulmamalı: %r" % h
    assert _md5_bulgusu(u), "bulgu uyarı olarak kalmalı"
    h2, u2 = uyumluluk.kontrol(kopya, "yukleme")
    assert _md5_bulgusu(h2) == [] and _md5_bulgusu(u2)


def test_ters_yon_asil_henuz_unlisted_iken_de_engellenmiyor(kok):
    """Golden-hour planı uygulanana kadar asılın state'i unlisted durabilir."""
    asil, _ = _ters_cift(kok, asil_gizlilik="unlisted")
    assert _md5_bulgusu(uyumluluk.kontrol(asil, "yukleme")[0]) == []


def test_ters_yon_isaretsiz_yayinlanmamis_ucuncu_hala_hata(kok):
    """Karşı tarafın notu, YENİ bir klasöre muafiyet KAZANDIRMAMALI."""
    _ters_cift(kok)
    ucuncu = _proje(kok, "Ucuncu", durum={})
    assert _md5_bulgusu(uyumluluk.kontrol(ucuncu, "yukleme")[0])


def test_ters_yon_kopya_yayina_donerse_asil_hata(kok):
    """Kopya public'e dönerse "canlıda tek kayıt" kanıtı düşer: HATA."""
    asil = _proje(kok, "Kullerimden Gec",
                  durum={"youtube_video_id": "-CQ7", "youtube_privacy": "public"})
    _proje(kok, "Yeniden Dogacagim",
           durum={"youtube_video_id": "kZML", "youtube_privacy": "public",
                  "kopya_notu": "kopya"})
    assert _md5_bulgusu(uyumluluk.kontrol(asil, "yukleme")[0])
