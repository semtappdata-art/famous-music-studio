# -*- coding: utf-8 -*-
"""`weekly_report.gunluk_izlenme_raporu()` + haftalık izlenme kıyası.

KULLANICI İSTEĞİ (2026-09-12): "İzlenme raporu Telegram'dan bana günlük izlenme
olarak tüm parçaların isimleri ile tek mesaj olsun, ve haftada bir kere toplam
haftalık izlenme, bir önceki hafta ile kıyaslama şeklinde gelsin."

Kilitlenenler:
  (a) Günlük mesajın İÇERİĞİ: adlar (meta.json `title`), artışa göre sıralama,
      bölüm ve gün toplamları, Türkçe karakterler, cp1254 güvenliği.
  (b) Günde EN FAZLA BİR mesaj; gün damgası YALNIZ başarılı gönderimde.
  (c) Bayat veri "bugün" diye sunulmuyor; veri hiç tazelenmezse akşam
      AÇIKÇA "BAYAT" diye söyleniyor (sessiz kalmıyor).
  (d) Liste dışı / kopya projeler toplamı şişirmiyor.
  (e) 4096 karakter sınırı içinde anlamlı kalıyor (toplam satırı kaybolmuyor).
  (f) YouTube'a/ağa SIFIR istek.
  (g) Haftalık kıyas matematiği; ilk hafta kıyassız; eski biçimli anlık görüntü.
  (h) Haftada TEK izlenme mesajı: `izlenme_raporu()` artık ayrı bildirim atmıyor.
  (i) `auto_process.main()` `finally` bloğu günlük raporu GERÇEKTEN çağırıyor,
      istatistik tazelemesinden SONRA (`ast`).

Gerçek bildirim GİTMEZ: `notify.send` her testte taklit ediliyor (ayrıca
`tests/conftest.py` gerçek kanalı kapatıyor).
"""

import ast
import io
import json
import os
import sys
import time

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import weekly_report as wr                               # noqa: E402


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def _an(yil, ay, gun, saat, dakika=5):
    return time.mktime((yil, ay, gun, saat, dakika, 0, 0, 1, -1))


def _damga(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


# 2026-09-13 Pazar (pazartesi değil: haftalık özet penceresine girmesin).
GUN = (2026, 9, 13)
OLCUM = _an(*GUN, 9, 5)            # bugünkü tazeleme
ONCEKI = OLCUM - 20 * 3600          # dünkü tazeleme (20 saat önce)


@pytest.fixture
def durum(tmp_path):
    return str(tmp_path / "saglik_durum.json")


@pytest.fixture
def bildirimler(monkeypatch):
    import notify
    kayit = []

    def _send(baslik, mesaj):
        kayit.append((baslik, mesaj))
        return True

    monkeypatch.setattr(notify, "send", _send)
    return kayit


@pytest.fixture
def agsiz(monkeypatch):
    """Her ağ çağrısını ve YouTube kimlik doğrulamasını PATLATIR ve sayar."""
    sayac = {"istek": 0}

    def _patla(*a, **k):
        sayac["istek"] += 1
        raise AssertionError("günlük izlenme ağa/YouTube'a çıktı")

    import requests
    for ad in ("request", "get", "post", "put", "patch", "delete"):
        monkeypatch.setattr(requests, ad, _patla, raising=False)
    import youtube_auth
    monkeypatch.setattr(youtube_auth, "get_authenticated_service", _patla,
                        raising=False)
    import youtube_stats
    monkeypatch.setattr(youtube_stats, "get_stats_batch", _patla, raising=False)
    monkeypatch.setattr(youtube_stats, "get_stats", _patla, raising=False)
    monkeypatch.setattr(wr, "get_stats_batch", _patla, raising=False)
    return sayac


class Katalog:
    """tmp_path altında sahte proje klasörleri kurar ve
    `uyumluluk.proje_klasorleri`ni onlara yönlendirir."""

    def __init__(self, tmp_path, monkeypatch):
        self.tmp = tmp_path
        self.yollar = []
        import uyumluluk
        monkeypatch.setattr(uyumluluk, "proje_klasorleri",
                            lambda *a, **k: list(self.yollar))

    def ekle(self, ad, uzun=None, shorts=None, uzun_prev=None, shorts_prev=None,
             kok="projects", baslik=None, at=OLCUM, prev_at=ONCEKI, **ek):
        p = self.tmp / kok / ad
        p.mkdir(parents=True, exist_ok=True)
        st = {"youtube_privacy": "public", "youtube_shorts_privacy": "public"}
        if uzun is not None:
            st["youtube_video_id"] = "u-" + ad
            st["youtube_views"] = uzun
        if shorts is not None:
            st["youtube_shorts_video_id"] = "s-" + ad
            st["youtube_shorts_views"] = shorts
        if uzun_prev is not None:
            st["youtube_views_prev"] = uzun_prev
        if shorts_prev is not None:
            st["youtube_shorts_views_prev"] = shorts_prev
        if at is not None:
            st["youtube_stats_checked_at"] = _damga(at)
        if prev_at is not None:
            st["youtube_stats_prev_at"] = _damga(prev_at)
        st.update(ek)
        (p / "state.json").write_text(json.dumps(st, ensure_ascii=False),
                                      encoding="utf-8")
        (p / "meta.json").write_text(json.dumps({"title": baslik or ad},
                                                ensure_ascii=False),
                                     encoding="utf-8")
        if str(p) not in self.yollar:
            self.yollar.append(str(p))
        return p


@pytest.fixture
def katalog(tmp_path, monkeypatch):
    return Katalog(tmp_path, monkeypatch)


def _calistir(durum, **kw):
    kw.setdefault("simdi", _an(*GUN, 10))
    return wr.gunluk_izlenme_raporu(log=lambda *a, **k: None,
                                    durum_dosyasi=durum, **kw)


def _oku(durum):
    with open(durum, encoding="utf-8") as f:
        return json.load(f)


def _standart(katalog):
    katalog.ekle("Son Kez", uzun=317, shorts=18, uzun_prev=316, shorts_prev=18)
    katalog.ekle("Kader Ortakları", uzun=100, shorts=172, uzun_prev=86,
                 shorts_prev=172)
    katalog.ekle("kullerimden-gec", uzun=182, shorts=115, uzun_prev=182,
                 shorts_prev=112, baslik="Küllerimden Geç")
    katalog.ekle("Just Relax", uzun=128, shorts=88, uzun_prev=114,
                 shorts_prev=88, kok="dj_sets")


# ---------------------------------------------------------------------------
# (a) İÇERİK
# ---------------------------------------------------------------------------
def test_mesaj_adlar_siralama_toplamlar(durum, bildirimler, katalog):
    _standart(katalog)
    s = _calistir(durum)
    assert s["durum"] == "tamam", s
    assert len(bildirimler) == 1
    baslik, mesaj = bildirimler[0]
    assert baslik == "Günlük izlenme"
    satirlar = mesaj.split("\n")

    # Adlar meta.json'dan (klasör adı değil) ve Türkçe harfler bozulmadan.
    assert any(x.startswith("Küllerimden Geç: +3 (297)") for x in satirlar), mesaj
    assert "kullerimden-gec" not in mesaj

    # Şarkılar artışa göre: Kader +14, Küllerimden +3, Son Kez +1.
    sirali = [x.split(":")[0] for x in satirlar
              if x.split(":")[0] in ("Kader Ortakları", "Küllerimden Geç", "Son Kez")]
    assert sirali == ["Kader Ortakları", "Küllerimden Geç", "Son Kez"], mesaj
    assert "Kader Ortakları: +14 (272)" in mesaj

    # DJ seti AYRI bölümde, şarkılardan sonra.
    i_sarki = mesaj.index("ŞARKILAR")
    i_set = mesaj.index("DJ SET / DERLEME")
    assert i_sarki < mesaj.index("Kader Ortakları") < i_set < mesaj.index("Just Relax")
    assert "ŞARKILAR: +18" in mesaj
    assert "DJ SET / DERLEME: +14" in mesaj
    # Gün toplamı: 18 + 14, toplam izlenme 335+272+297+216.
    assert "GÜNÜN TOPLAMI: +32 (toplam izlenme 1.120)" in mesaj
    # Süre DÜRÜST: 20 saatlik aralık "20 saat" diye yazılıyor.
    assert "son 20 saat" in mesaj


def test_bin_ayraci_ve_negatif_fark(durum, bildirimler, katalog):
    katalog.ekle("Büyük", uzun=12345, uzun_prev=12347)
    mesaj = _calistir(durum)["metin"]
    assert "Büyük: -2 (12.345)" in mesaj


def test_cp1254_guvenli_ve_emoji_raporu_kirmaz(durum, bildirimler, katalog):
    katalog.ekle("Tuhaf", uzun=5, uzun_prev=1, baslik="Tuhaf \U0001F600 Ad → iki")
    _calistir(durum)
    baslik, mesaj = bildirimler[0]
    baslik.encode("cp1254")
    mesaj.encode("cp1254")
    assert "şğıİÇÜÖ" in wr._cp1254_guvenli("şğıİÇÜÖ")


def test_ilk_kez_olculen_video_artisa_katilmiyor(durum, bildirimler, katalog):
    """Gece Seansı Vol. 1'in gerçek durumu: Shorts'un `_prev`i YOK (ilk ölçüm).
    80 izlenmenin tamamı 'bugünkü artış' sayılmamalı."""
    katalog.ekle("Gece Seansı Vol. 1", uzun=15, shorts=80, uzun_prev=0,
                 kok="derlemeler")
    mesaj = _calistir(durum)["metin"]
    assert "Gece Seansı Vol. 1: +15 (95) [bir videosu ilk ölçüm]" in mesaj
    assert "GÜNÜN TOPLAMI: +15" in mesaj


def test_hic_onceki_olcumu_olmayan_proje_yeni_gorunur(durum, bildirimler, katalog):
    katalog.ekle("Taze Şarkı", uzun=40, prev_at=None)
    katalog.ekle("Eski", uzun=10, uzun_prev=8)
    mesaj = _calistir(durum)["metin"]
    assert "Taze Şarkı: yeni (40)" in mesaj
    assert "GÜNÜN TOPLAMI: +2 (toplam izlenme 50)" in mesaj
    assert mesaj.index("Eski:") < mesaj.index("Taze Şarkı:")


# ---------------------------------------------------------------------------
# (b) GÜNDE BİR; DAMGA YALNIZ BAŞARIDA
# ---------------------------------------------------------------------------
def test_gunde_bir_kez(durum, bildirimler, katalog):
    _standart(katalog)
    assert _calistir(durum)["durum"] == "tamam"
    for saat in (11, 15, 21, 23):
        assert _calistir(durum, simdi=_an(*GUN, saat))["durum"] == "atlandi"
    assert len(bildirimler) == 1
    assert _oku(durum)[wr.GUNLUK_GUN_ANAHTARI] == "2026-09-13"


def test_pencere_saat_dokuzdan_once_acilmaz(durum, bildirimler, katalog):
    _standart(katalog)
    assert _calistir(durum, simdi=_an(*GUN, 8, 30))["durum"] == "atlandi"
    assert bildirimler == []


def test_basarisiz_gonderimde_damga_ve_anlik_goruntu_yok(durum, katalog,
                                                        monkeypatch):
    _standart(katalog)
    import notify
    monkeypatch.setattr(notify, "send", lambda b, m: False)
    assert _calistir(durum)["durum"] == "gonderilemedi"
    d = wr._durum(durum)
    assert wr.GUNLUK_GUN_ANAHTARI not in d
    assert wr.GUNLUK_ANLIK_ANAHTARI not in d

    # Kanal düzelince bir SONRAKİ saatlik koşu gönderir.
    kayit = []
    monkeypatch.setattr(notify, "send",
                        lambda b, m: kayit.append((b, m)) or True)
    assert _calistir(durum, simdi=_an(*GUN, 11))["durum"] == "tamam"
    assert len(kayit) == 1


def test_notify_patlarsa_otomasyon_durmaz(durum, katalog, monkeypatch):
    _standart(katalog)
    import notify

    def _patla(b, m):
        raise RuntimeError("telegram çöktü")

    monkeypatch.setattr(notify, "send", _patla)
    assert _calistir(durum)["durum"] == "gonderilemedi"
    assert wr.GUNLUK_GUN_ANAHTARI not in wr._durum(durum)


def test_ikinci_gunun_farki_raporlanan_anlik_goruntuden(durum, bildirimler,
                                                        katalog):
    """Tazeleme 20 saatte bir: günde İKİ ölçüm düşebilir. Fark `_prev`ten
    alınsaydı aradaki ölçümün artışı kaybolurdu; en son RAPORLANAN anlık
    görüntüden alınıyor."""
    katalog.ekle("Yeraltı", uzun=240, uzun_prev=239)
    assert _calistir(durum)["durum"] == "tamam"

    # Ertesi gün: arada iki tazeleme oldu (240 -> 250 -> 260). `_prev` yalnız
    # son adımı (250) biliyor; doğru artış +20.
    ertesi_olcum = _an(2026, 9, 14, 7, 5)
    katalog.ekle("Yeraltı", uzun=260, uzun_prev=250, at=ertesi_olcum,
                 prev_at=ertesi_olcum - 20 * 3600)
    s = _calistir(durum, simdi=_an(2026, 9, 14, 10))
    assert s["durum"] == "tamam"
    assert "Yeraltı: +20 (260)" in bildirimler[1][1]
    # Aralık da raporlanan ölçümden: 13.09 09:05 -> 14.09 07:05 = 22 saat.
    assert "son 22 saat" in bildirimler[1][1]


# ---------------------------------------------------------------------------
# (c) BAYAT VERİ
# ---------------------------------------------------------------------------
def test_yeni_olcum_yoksa_bekler_aksam_bayat_der(durum, bildirimler, katalog):
    _standart(katalog)
    assert _calistir(durum)["durum"] == "tamam"
    anlik = wr._durum(durum)[wr.GUNLUK_ANLIK_ANAHTARI]

    # Ertesi gün tazeleme HİÇ olmadı (ölçüm dünkü). Sabah bekler...
    ertesi = (2026, 9, 14)
    assert _calistir(durum, simdi=_an(*ertesi, 10))["durum"] == "atlandi"
    assert _calistir(durum, simdi=_an(*ertesi, 20))["durum"] == "atlandi"
    assert len(bildirimler) == 1
    # ...akşam 21:00'de "bugün" DEMEDEN, açıkça bayat der.
    s = _calistir(durum, simdi=_an(*ertesi, 21))
    assert s["durum"] == "tamam" and s["tur"] == "bayat"
    mesaj = bildirimler[1][1]
    assert "BAYAT" in mesaj
    assert "ŞARKILAR" not in mesaj and "GÜNÜN TOPLAMI" not in mesaj
    assert "36 saat önce" in mesaj            # 13.09 09:05 -> 14.09 21:05
    # Bayat mesaj anlık görüntüyü İLERLETMEZ; ertesi günün farkı eksiksiz.
    assert wr._durum(durum)[wr.GUNLUK_ANLIK_ANAHTARI] == anlik
    assert _calistir(durum, simdi=_an(*ertesi, 22))["durum"] == "atlandi"


def test_eski_ama_hic_raporlanmamis_olcum_bugun_sayilmaz(durum, bildirimler,
                                                        katalog):
    """Tazeleme 30 saattir başarısız: ölçüm hiç raporlanmamış olsa bile
    'son 20 saat' diye sunulmamalı."""
    katalog.ekle("Son Kez", uzun=317, uzun_prev=316,
                 at=_an(*GUN, 10) - 30 * 3600, prev_at=_an(*GUN, 10) - 50 * 3600)
    assert _calistir(durum)["durum"] == "atlandi"
    s = _calistir(durum, simdi=_an(*GUN, 21))
    assert s["tur"] == "bayat"
    assert "BAYAT" in bildirimler[0][1]


def test_hic_olcum_yoksa_aksam_soyler(durum, bildirimler, katalog):
    katalog.ekle("Yüklenmemiş", at=None, prev_at=None)
    assert _calistir(durum)["durum"] == "atlandi"
    s = _calistir(durum, simdi=_an(*GUN, 21))
    assert s["tur"] == "bayat"
    assert "ölçüm yok" in bildirimler[0][1].lower()


# ---------------------------------------------------------------------------
# (d) LİSTE DIŞI / KOPYA
# ---------------------------------------------------------------------------
def test_liste_disi_ve_kopya_toplama_katilmaz(durum, bildirimler, katalog):
    katalog.ekle("Açık", uzun=100, uzun_prev=90)
    # İki videosu da unlisted (Bu Gece Kazandık).
    katalog.ekle("Bu Gece Kazandık", uzun=4, shorts=10, uzun_prev=4,
                 shorts_prev=8, youtube_privacy="unlisted",
                 youtube_shorts_privacy="unlisted")
    # Kopya notu (Yeniden Doğacağım) — gizlilik ne olursa olsun dışarıda.
    katalog.ekle("Yeniden Doğacağım", uzun=148, shorts=51, uzun_prev=146,
                 shorts_prev=51, kopya_notu="Küllerimden Geç ile aynı ses")
    mesaj = _calistir(durum)["metin"]
    assert "GÜNÜN TOPLAMI: +10 (toplam izlenme 100)" in mesaj, mesaj
    i = mesaj.index("LİSTE DIŞI / KOPYA (toplama katılmadı): +4")
    assert mesaj.index("Bu Gece Kazandık: +2 (14)") > i
    assert "Yeniden Doğacağım: +2 (199) [kopya]" in mesaj
    assert mesaj.index("Açık:") < i


def test_gercek_gizlilik_istenenin_onune_gecer(durum, bildirimler, katalog):
    """Küllerimden Geç: state 'unlisted' diyor ama kullanıcı uzun formatı
    Studio'dan public yaptı; `youtube_privacy_gercek` bunu ölçüyor."""
    katalog.ekle("Küllerimden Geç", uzun=182, shorts=115, uzun_prev=180,
                 shorts_prev=115, youtube_privacy="unlisted",
                 youtube_shorts_privacy="unlisted",
                 youtube_privacy_gercek="public",
                 youtube_shorts_privacy_gercek="unlisted")
    mesaj = _calistir(durum)["metin"]
    assert "LİSTE DIŞI" not in mesaj
    assert "GÜNÜN TOPLAMI: +2 (toplam izlenme 297)" in mesaj


def test_zamanlanmis_private_video_liste_disi_sayilmaz(durum, bildirimler,
                                                      katalog):
    katalog.ekle("Yarın Çıkacak", uzun=0, uzun_prev=0,
                 youtube_privacy="private",
                 youtube_publish_at="2099-01-01T09:00:00Z")
    mesaj = _calistir(durum)["metin"]
    assert "LİSTE DIŞI" not in mesaj


# ---------------------------------------------------------------------------
# (e) 4096
# ---------------------------------------------------------------------------
def test_telegram_siniri_icinde_anlamli_kalir(durum, bildirimler, katalog):
    beklenen = 0
    for i in range(300):
        katalog.ekle("Çok Uzun Şarkı Adı Numarası %03d Ve Devamı" % i,
                     uzun=1000 + i, uzun_prev=1000)
        beklenen += i
    mesaj = _calistir(durum)["metin"]
    assert len(mesaj) <= wr.MESAJ_TAVANI <= 4096
    assert "GÜNÜN TOPLAMI: +%s" % wr._sayi_bicim(beklenen) in mesaj
    assert "tane daha" in mesaj
    # En çok artan üstte kaldı, kırpılan en alttakiler.
    assert "Numarası 299" in mesaj and "Numarası 000" not in mesaj
    baslik, gonderilen = bildirimler[0]
    assert len(baslik) + len(gonderilen) < 4096


# ---------------------------------------------------------------------------
# (f) AĞ YOK
# ---------------------------------------------------------------------------
def test_youtube_istegi_sifir(durum, bildirimler, katalog, agsiz):
    _standart(katalog)
    s = _calistir(durum)
    assert s["durum"] == "tamam"
    _calistir(durum, simdi=_an(2026, 9, 14, 21))       # bayat dalı da
    assert agsiz["istek"] == 0


# ---------------------------------------------------------------------------
# (g) HAFTALIK KIYAS MATEMATİĞİ
# ---------------------------------------------------------------------------
def _k(anahtar, toplam, disi=None, at=OLCUM):
    return {"anahtar": anahtar, "ad": anahtar.split("/")[-1], "toplam": toplam,
            "disi": disi, "grup": "sarki", "at": _damga(at)}


def test_haftalik_ilk_hafta_kiyassiz(durum):
    satirlar, olcum = wr._haftalik_izlenme_satirlari(
        {}, [_k("projects/A", 100), _k("projects/B", 50)], _an(*GUN, 10))
    metin = "\n".join(satirlar)
    assert "toplam 150" in metin and "ilk hafta" in metin
    assert olcum["toplam"] == 150
    assert olcum["projeler"] == {"projects/A": 100, "projects/B": 50}
    assert olcum["artis"] is None


def test_haftalik_kiyas_fark_ve_yuzde():
    onceki = {"toplam": 100, "izlenme": 120, "artis": 50, "artis_tum": 55,
              "olcum_at": _damga(OLCUM - 7 * 86400),
              "projeler": {"projects/A": 60, "projects/B": 40, "projects/Gizli": 20}}
    katalog = [_k("projects/A", 100),            # +40
               _k("projects/B", 60),             # +20
               _k("projects/Yeni", 5),           # yeni şarkı: +5
               _k("projects/Gizli", 30, disi="liste dışı")]
    satirlar, olcum = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: onceki}, katalog, _an(*GUN, 10))
    metin = "\n".join(satirlar)
    assert "İZLENME bu hafta: +65 (toplam 165)" in metin, metin
    assert "Önceki hafta: +50 -> fark +15 (+%30,0)" in metin, metin
    assert "En çok artan: A +40, B +20, Yeni +5 (yeni)" in metin, metin
    assert "7,0 gün" in metin
    assert olcum["artis"] == 65
    assert olcum["artis_tum"] == 195 - 120


def test_haftalik_dususte_negatif_yuzde():
    onceki = {"toplam": 100, "izlenme": 100, "artis": 80,
              "projeler": {"projects/A": 100}}
    satirlar, _ = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: onceki}, [_k("projects/A", 140)],
        _an(*GUN, 10))
    assert "Önceki hafta: +80 -> fark -40 (-%50,0)" in "\n".join(satirlar)


def test_haftalik_onceki_artis_sifirsa_yuzde_uydurulmaz():
    onceki = {"toplam": 100, "izlenme": 100, "artis": 0,
              "projeler": {"projects/A": 100}}
    satirlar, _ = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: onceki}, [_k("projects/A", 110)],
        _an(*GUN, 10))
    metin = "\n".join(satirlar)
    assert "fark +10 (yüzde hesaplanamaz)" in metin


def test_liste_disindan_cikan_sarki_haftalik_artisi_sisirmez():
    """Geçen hafta liste dışı olup bu hafta public olan şarkının ESKİ
    izlenmeleri 'bu haftanın artışı' sayılmamalı."""
    onceki = {"toplam": 100, "izlenme": 400, "artis": 10,
              "projeler": {"projects/A": 100, "projects/Kul": 300}}
    satirlar, olcum = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: onceki},
        [_k("projects/A", 110), _k("projects/Kul", 305)], _an(*GUN, 10))
    assert olcum["artis"] == 15, satirlar


def test_eski_bicimli_anlik_goruntu_durustce_etiketlenir():
    """Bugünkü gerçek dosyada `haftalik_ozet_olcum` = {izlenme, dakika, video}
    — şarkı dökümü ve 'toplam' YOK. İlk yeni rapor tüm videoların farkını
    'liste dışı dahil' diye etiketler, kıyas uydurmaz."""
    onceki = {"izlenme": 3843, "dakika": 0, "video": 0}
    satirlar, olcum = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: onceki},
        [_k("projects/A", 3800), _k("projects/Gizli", 100, disi="kopya")],
        _an(*GUN, 10))
    metin = "\n".join(satirlar)
    assert "İZLENME bu hafta: +57 (liste dışı dahil)" in metin, metin
    assert "kıyas yok" in metin
    assert "Şarkı bazında kıyas gelecek hafta" in metin
    assert olcum["artis"] is None and olcum["artis_tum"] == 57

    # Bir sonraki hafta: 'artis' yok ama 'artis_tum' var -> tüm videolarla kıyas.
    satirlar2, _ = wr._haftalik_izlenme_satirlari(
        {wr.HAFTALIK_OLCUM_ANAHTARI: olcum},
        [_k("projects/A", 3850), _k("projects/Gizli", 110, disi="kopya")],
        _an(2026, 9, 20, 10))
    metin2 = "\n".join(satirlar2)
    assert "Önceki hafta: +57 (liste dışı dahil) -> fark +3" in metin2, metin2


def test_haftalik_bayat_olcum_uyarisi():
    satirlar, _ = wr._haftalik_izlenme_satirlari(
        {}, [_k("projects/A", 10, at=_an(*GUN, 10) - 50 * 3600)], _an(*GUN, 10))
    assert "son ölçüm 50 saat önce" in "\n".join(satirlar)


# ---------------------------------------------------------------------------
# (h) HAFTADA TEK İZLENME MESAJI
# ---------------------------------------------------------------------------
def test_izlenme_raporu_artik_ayri_bildirim_atmiyor(durum, bildirimler):
    """Kullanıcı haftada TEK izlenme raporu istedi. İzlenme süresi özeti
    kaydediliyor ve haftalık özetin İZLENME bölümüne giriyor; ayrı
    'Haftalık izlenme süresi' mesajı YOK."""
    ozet = {"projects": {"video": 2, "izlenme": 10, "dakika": 40,
                         "ort_izlenme_sn": 30}}
    s = wr.izlenme_raporu(log=lambda *a, **k: None, durum_dosyasi=durum,
                          rapor_fn=lambda: {"ozet": ozet}, token_yolu=None)
    assert s["durum"] == "tamam"
    assert bildirimler == []
    assert wr._durum(durum)[wr.IZLENME_OZET_ANAHTARI]["projects"]["dakika"] == 40


def test_weekly_reportta_haftalik_izlenme_suresi_basligi_kalmadi():
    with io.open(os.path.join(_KOK, "weekly_report.py"), encoding="utf-8") as f:
        agac = ast.parse(f.read())
    basliklar = [d.args[0].value for d in ast.walk(agac)
                 if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                 and d.func.id == "_bildir" and d.args
                 and isinstance(d.args[0], ast.Constant)]
    assert "Haftalık izlenme süresi" not in basliklar
    assert "Günlük izlenme" in basliklar


def test_haftalik_ozet_izlenme_kiyasini_tasiyor_ve_anlik_goruntuyu_yaziyor(
        durum, bildirimler, katalog):
    katalog.ekle("A", uzun=100, uzun_prev=90)

    def _saglik(log=print):
        return {"x": {"durum": "tamam"}}

    pzt = _an(2026, 9, 14, 10)
    wr.haftalik_gozden_gecirme(log=lambda *a, **k: None, durum_dosyasi=durum,
                               simdi=pzt, saglik_fn=_saglik)
    assert "İZLENME: toplam 100 (ilk hafta" in bildirimler[0][1]
    olcum = wr._durum(durum)[wr.HAFTALIK_OLCUM_ANAHTARI]
    assert olcum["projeler"] == {"projects/A": 100}

    katalog.ekle("A", uzun=130, uzun_prev=125, at=pzt + 7 * 86400 - 3600,
                 prev_at=pzt + 6 * 86400)
    wr.haftalik_gozden_gecirme(log=lambda *a, **k: None, durum_dosyasi=durum,
                               simdi=pzt + 7 * 86400, saglik_fn=_saglik)
    haftalik = [m for b, m in bildirimler if b.startswith("Haftalık özet")]
    assert "İZLENME bu hafta: +30 (toplam 130)" in haftalik[1], haftalik[1]
    assert wr._durum(durum)[wr.HAFTALIK_OLCUM_ANAHTARI]["artis"] == 30


def test_haftalik_izlenme_hesaplanamazsa_temel_cizgi_silinmez(
        durum, bildirimler, monkeypatch):
    with open(durum, "w", encoding="utf-8") as f:
        json.dump({wr.HAFTALIK_OLCUM_ANAHTARI: {"toplam": 5, "projeler": {}}}, f)

    def _patla(*a, **k):
        raise RuntimeError("katalog okunamadı")

    monkeypatch.setattr(wr, "_izlenme_katalogu", _patla)
    s = wr.haftalik_gozden_gecirme(log=lambda *a, **k: None, durum_dosyasi=durum,
                                   simdi=_an(2026, 9, 14, 10),
                                   saglik_fn=lambda log=print: {})
    assert s["durum"] == "tamam"
    assert "İZLENME: hesaplanamadı" in bildirimler[0][1]
    assert wr._durum(durum)[wr.HAFTALIK_OLCUM_ANAHTARI] == {"toplam": 5,
                                                           "projeler": {}}


# ---------------------------------------------------------------------------
# (i) BAĞLANTI — auto_process
# ---------------------------------------------------------------------------
def _auto_process_agaci():
    with io.open(os.path.join(_KOK, "auto_process.py"), encoding="utf-8") as f:
        return ast.parse(f.read())


def test_auto_process_finally_gunluk_raporu_tazelemeden_sonra_cagiriyor():
    agac = _auto_process_agaci()
    main = next(d for d in ast.walk(agac)
                if isinstance(d, ast.FunctionDef) and d.name == "main")
    deneme = next(d for d in ast.walk(main)
                  if isinstance(d, ast.Try) and d.finalbody)
    satir = {}
    for d in ast.walk(ast.Module(body=deneme.finalbody, type_ignores=[])):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            satir.setdefault(d.func.id, d.lineno)
    assert "_gunluk_izlenme" in satir, "günlük izlenme kancası finally'de yok"
    assert satir["_refresh_stats"] < satir["_gunluk_izlenme"], \
        "günlük rapor istatistik tazelemesinden ÖNCE çağrılıyor (bayat veri)"


def test_auto_process_kancasi_dogru_fonksiyonu_try_icinde_cagiriyor():
    agac = _auto_process_agaci()
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == "_gunluk_izlenme")
    assert isinstance(fn.body[-1], ast.Try) or any(
        isinstance(x, ast.Try) for x in fn.body), "hata otomasyonu durdurabilir"
    cagrilar = {d.func.id for d in ast.walk(fn)
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
    assert "gunluk_izlenme_raporu" in cagrilar
    assert "weekly_report" in {a.module for a in ast.walk(fn)
                               if isinstance(a, ast.ImportFrom)}


def test_auto_process_kancasi_patlasa_da_yutulur(monkeypatch):
    import auto_process
    import weekly_report

    def _patla(*a, **k):
        raise RuntimeError("beklenmedik")

    satirlar = []
    monkeypatch.setattr(weekly_report, "gunluk_izlenme_raporu", _patla,
                        raising=False)
    monkeypatch.setattr(auto_process, "log", satirlar.append)
    auto_process._gunluk_izlenme()                      # istisna FIRLATMAZ
    assert any("Günlük izlenme HATA" in s for s in satirlar)
