# -*- coding: utf-8 -*-
"""`saglik_kontrol.yayin_durgunlugu()` — yayın durgunluğu nöbetçisi.

NEDEN VAR (2026-09-12): depoda "en son ne zaman bir şey YAYINLANDI" diye soran
tek bir kontrol yoktu. Aynı gün eklenen iki koruma da yayın durmasını
yakalamıyor:
  - `kacan_kosu()` KENDİ damgasına bakıyor, o damga da HER koşuda tazeleniyor
    -> koşu yapılıyor ama hiçbir şey yayınlanmıyorsa "tamam" diyor;
  - `git_senkron()` yerel/canlı FARKINI ölçüyor, BÜYÜMEYİ değil -> hiçbir şey
    yayınlanmazsa iki taraf eşit kalır, o da "tamam" diyor.
Aynı gün `uyumluluk.kontrol()` yedi çağrı noktasında fail-closed yapıldı: bir
kapı kapanırsa proje ATLANIYOR ve geriye yalnızca bir log satırı kalıyor
(`notify.uyar_bir_kez()` telefona GİTMEZ). Yani kanal günlerce sessizce
durabilirdi.

EN ÖNEMLİ TEST BURADA "ALARM ÇALIYOR MU" DEĞİL: bekleyen proje YOKKEN uzun
sessizliğin alarm ÜRETMEMESİ (test_bekleyen_proje_yoksa_uzun_sessizlik_sessiz).
Katalog bittiğinde sessizlik normaldir; orada çalan bir alarm her hafta tekrar
eder ve üç yanlış alarmdan sonra bu nöbetçi de "kimsenin bakmadığı koruma"
sınıfına düşerdi.

BU TESTLERDE GERÇEK BİR ŞEY ÇALIŞMIYOR: `notify` modülü, saat (`time.time`) ve
durum dosyası monkeypatch'li; katalog kökü `tmp_path`e çekiliyor
(`uyumluluk.KOKLER`), yani gerçek `projects/`, `dj_sets/`, `derlemeler/`
klasörlerine ne yazılıyor ne de bakılıyor. Hiçbir ağ çağrısı, hiçbir
PowerShell süreci yok.
"""

import ast
import json
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import pytest

import saglik_kontrol as SK

SAAT = 3600.0
T0 = 1_760_000_000.0          # sabit bir "şimdi" çapası

# Dört ana platform anahtarı dolu = bu proje `pending`den düşmüş demek.
TAM = {
    "youtube_video_id": "yt1",
    "youtube_shorts_video_id": "sh1",
    "tiktok_publish_id": "tk1",
    "instagram_media_id": "ig1",
}

_KAYNAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "saglik_kontrol.py")


def _damga(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    """Durum dosyası tmp'de, notify sahte, katalog kökü tmp'de."""
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))

    import uyumluluk
    kok = tmp_path / "projects"
    kok.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))

    gonderilen = []
    m = types.ModuleType("notify")
    m.send = lambda baslik, mesaj, *a, **k: (gonderilen.append((baslik, mesaj)), True)[1]
    monkeypatch.setitem(sys.modules, "notify", m)

    monkeypatch.setattr(SK.time, "time", lambda: T0)
    return types.SimpleNamespace(kok=kok, gonderilen=gonderilen,
                                 monkeypatch=monkeypatch)


def _proje(ortam, ad, state=None, ses=True):
    d = ortam.kok / ad
    d.mkdir()
    if ses:
        (d / "audio.wav").write_bytes(b"RIFF0000")
    if state is not None:
        (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return d


def _yayinlanmis(ortam, ad, saat_once):
    """Dört anahtarı da dolu, `saat_once` saat önce yayınlanmış proje."""
    st = dict(TAM)
    st["youtube_uploaded_at"] = _damga(T0 - saat_once * SAAT)
    return _proje(ortam, ad, st)


# --- (a) bekleyen proje VAR + uzun sessizlik -> BİLDİRİM -------------------

def test_bekleyen_proje_varken_uzun_sessizlik_bildirim_gonderir(ortam):
    """Eşiğin üstü: 52 saatlik yayın tabanı aşıldı, bir pencere tamamen kaçtı."""
    _yayinlanmis(ortam, "Yayinda", saat_once=80)
    _proje(ortam, "Bekleyen", {"youtube_video_id": "yt9"})   # 3 anahtar eksik

    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)

    assert s["durum"] == "durgun"
    assert s["bekleyen"] == 1
    assert s["bildirildi"] is True
    assert s["son_yayin"] == "Yayinda/youtube_uploaded_at"
    assert 79 * SAAT < s["sessizlik_sn"] < 81 * SAAT

    assert len(ortam.gonderilen) == 1
    baslik, mesaj = ortam.gonderilen[0]
    assert baslik == "Yayın durdu"
    # Eyleme dönük olmak ZORUNDA: kaç saat, kaç proje, ilk bakılacak yer.
    assert "python uyumluluk.py" in mesaj
    assert "3 gün" in mesaj                      # 80 saat -> gün biçimi
    assert "1 proje" in mesaj
    assert "52 saat" in mesaj and "78 saat" in mesaj
    assert any("yayın durgunluğu" in l for l in satirlar)
    assert any("python uyumluluk.py" in l for l in satirlar)


def test_esik_tam_sinirinda_bildirim_gider(ortam):
    """78 saat = eşik; `<` karşılaştırması olduğu için tam sınırda ALARM."""
    _yayinlanmis(ortam, "Yayinda", saat_once=78)
    _proje(ortam, "Bekleyen", {})
    s = SK.yayin_durgunlugu(log=lambda *a: None)
    assert s["durum"] == "durgun"
    assert len(ortam.gonderilen) == 1


# --- (b) bekleyen proje VAR + sessizlik eşiğin ALTINDA -> SESSİZ -----------

@pytest.mark.parametrize("saat", [0.5, 5.2, 24.0, 52.0, 60.0, 77.9])
def test_esigin_altinda_sessiz_kalir(ortam, saat):
    """52 saatlik yayın tabanı yüzünden İKİ GÜN sessizlik TAMAMEN NORMAL.

    5.2 saat bu deponun 2026-09-12 öğlen ölçümüdür (Sofraya Gelmedin 06:48'de
    beş platforma çıktı); 52 saat tabanın kendisi; 77.9 eşiğin bir tık altı.
    Üçünde de telefon ÇALMAMALI ve log da SUSMALI.
    """
    _yayinlanmis(ortam, "Yayinda", saat_once=saat)
    _proje(ortam, "Bekleyen", {"youtube_video_id": "yt9"})

    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)

    assert s["durum"] == "tamam"
    assert s["bekleyen"] == 1
    assert ortam.gonderilen == []
    assert satirlar == []


# --- (c) bekleyen proje YOK + uzun sessizlik -> BİLDİRİM YOK --------------

def test_bekleyen_proje_yoksa_uzun_sessizlik_sessiz(ortam):
    """EN ÖNEMLİ YANLIŞ-ALARM TESTİ.

    Katalog tamamen bitmişse yayınlanacak hiçbir şey yoktur; kullanıcı Suno'da
    yeni şarkı üretene kadar kanalın sessiz kalması TASARIM GEREĞİ normaldir.
    Burada alarm çalsaydı uyarı her hafta tekrarlar ve değersizleşirdi.
    """
    _yayinlanmis(ortam, "Yayinda 1", saat_once=200)
    _yayinlanmis(ortam, "Yayinda 2", saat_once=300)

    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)

    assert s["durum"] == "bekleyen_yok"
    assert s["bekleyen"] == 0
    assert ortam.gonderilen == []
    assert satirlar == []


def test_sessiz_dosyasiz_klasor_bekleyen_SAYILMAZ(ortam):
    """`dj_sets/Night Drive` vakası: audio/state olmayan klasör proje DEĞİL.

    `uyumluluk.proje_klasorleri()` TEK SEVİYE tarıyor ve gördüğü her klasörü
    döndürüyor. Ses şartı olmasaydı böyle bir klasör SONSUZA KADAR "bekleyen"
    sayılır, yani katalog gerçekten bitse bile bu nöbetçi her gün alarm çalardı.
    """
    _yayinlanmis(ortam, "Yayinda", saat_once=300)
    _proje(ortam, "Night Drive", state=None, ses=False)

    s = SK.yayin_durgunlugu(log=lambda *a: None)
    assert s["durum"] == "bekleyen_yok"
    assert s["proje"] == 1, "sessiz klasör proje olarak da sayılmamalı"
    assert ortam.gonderilen == []


# --- (d) damga hiç yok / bozuk -> ÇÖKMEZ ----------------------------------

def test_hic_yayin_damgasi_yoksa_atlanir(ortam):
    """Taze checkout: karşılaştırmanın bir tarafı hiç YOK -> iddia da yok."""
    _proje(ortam, "Bekleyen", {})
    s = SK.yayin_durgunlugu(log=lambda *a: None)
    assert s["durum"] == "atlandi"
    assert s["sebep"] == "yayin damgasi yok"
    assert ortam.gonderilen == []


def test_bozuk_state_ve_bozuk_damga_cokmez(ortam):
    """Yarım JSON, liste JSON, sayı/None damga, anlamsız tarih — hiçbiri çökmemeli."""
    _yayinlanmis(ortam, "Yayinda", saat_once=10)

    yarim = _proje(ortam, "Yarim JSON", {})
    (yarim / "state.json").write_text('{"youtube_video_id": ', encoding="utf-8")

    liste = _proje(ortam, "Liste JSON", {})
    (liste / "state.json").write_text("[1, 2, 3]", encoding="utf-8")

    _proje(ortam, "Bozuk Damga", {"youtube_uploaded_at": 12345,
                                  "tiktok_uploaded_at": None,
                                  "bluesky_uploaded_at": "dun aksam"})
    _proje(ortam, "State Yok", state=None)

    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)

    # Tek geçerli damga 10 saat önce -> eşiğin altı, sessiz.
    assert s["durum"] == "tamam"
    assert s["bekleyen"] == 4, "bozuk/eksik state'li projeler bekleyen sayılır"
    assert s["proje"] == 5
    assert ortam.gonderilen == []
    assert satirlar == []


def test_damga_gelecekteyse_alarm_yok(ortam):
    """Sistem saati geri alınmış: ölçüm anlamsız, log'a satır düşer, telefon susar."""
    _yayinlanmis(ortam, "Yayinda", saat_once=-5)     # 5 saat SONRA
    _proje(ortam, "Bekleyen", {})

    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)

    assert s["durum"] == "atlandi"
    assert s["sebep"] == "damga gelecekte"
    assert ortam.gonderilen == []
    assert any("gelecekte" in l for l in satirlar)


def test_tarama_patlarsa_sessiz_kalmaz(ortam, monkeypatch):
    """Kontrolün KENDİSİ patlarsa log'a satır düşer — sessizce `{}` dönmez."""
    def _patla():
        raise RuntimeError("disk gitti")

    monkeypatch.setattr(SK, "_yayin_taramasi", _patla)
    satirlar = []
    s = SK.yayin_durgunlugu(log=satirlar.append)
    assert s["durum"] == "calistirilamadi"
    assert satirlar and "disk gitti" in satirlar[0]
    assert ortam.gonderilen == []


# --- (e) günde bir --------------------------------------------------------

def test_ayni_gun_ikinci_bildirim_bastirilir(ortam):
    """`_bildir` mekanizmasının AYNISI: saatlik koşuda telefon bir kez çalar."""
    _yayinlanmis(ortam, "Yayinda", saat_once=90)
    _proje(ortam, "Bekleyen", {})

    ilk = SK.yayin_durgunlugu(log=lambda *a: None)
    assert ilk["bildirildi"] is True
    assert len(ortam.gonderilen) == 1

    ikinci = SK.yayin_durgunlugu(log=lambda *a: None)
    assert ikinci["durum"] == "durgun"          # log'a yine düşer
    assert ikinci["bildirildi"] is False
    assert len(ortam.gonderilen) == 1, "aynı gün ikinci bildirim gitmemeli"


def test_gonderim_basarisizsa_damga_atilmaz(ortam, monkeypatch):
    """`notify.send` False dönerse bir sonraki saatlik koşu YENİDEN dener."""
    _yayinlanmis(ortam, "Yayinda", saat_once=90)
    _proje(ortam, "Bekleyen", {})

    m = sys.modules["notify"]
    m.send = lambda *a, **k: False
    s = SK.yayin_durgunlugu(log=lambda *a: None)
    assert s["bildirildi"] is False
    assert SK._durum().get("yayin_durgunlugu_bildirim_gun") is None


# --- (f) kontrol_et'e GERÇEKTEN bağlı mı? (ast muhafızı) ------------------

def test_kontrol_et_yayin_durgunlugunu_cagiriyor_ve_kacan_kosudan_ONCE():
    """CLAUDE.md'nin birinci dersi: yazıldı ama HİÇBİR YERDEN çağrılmıyor.

    SIRA da kilitleniyor: `kacan_kosu` damgayı EN SONDA tazeliyor, yani
    "saatlik hattın sonuna ulaşıldı" iddiası en sonda doğmalı. `ast` ile
    doğrulanıyor, çünkü `kontrol_et()`i çalıştırmak gerçek PowerShell/git/
    token dosyalarına dokunurdu.
    """
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    hedef = next(d for d in ast.walk(agac)
                 if isinstance(d, ast.FunctionDef) and d.name == "kontrol_et")
    anahtarlar = [k.value for d in ast.walk(hedef)
                  if isinstance(d, ast.Dict)
                  for k in d.keys
                  if isinstance(k, ast.Constant)]
    assert "yayin_durgunlugu" in anahtarlar
    assert anahtarlar.index("yayin_durgunlugu") < anahtarlar.index("kacan_kosu")


# --- (g) cp1254 tuzağı ----------------------------------------------------

def _cp1254_disi(metin: str) -> str:
    disarida = []
    for ch in metin:
        try:
            ch.encode("cp1254")
        except UnicodeEncodeError:
            if ch not in disarida:
                disarida.append(ch)
    return "".join(disarida)


def test_uretilen_tum_metinler_cp1254e_kodlanabiliyor(ortam):
    """Modül `python saglik_kontrol.py` ile elle de çalıştırılıyor; konsol cp1254.

    Türkçenin ı/İ/ş/ğ harfleri cp1254'te VAR, ok işareti (U+2192) ve emoji YOK
    — tek bir süs karakteri tanı çıktısını `UnicodeEncodeError` ile çökertir
    (2026-09-12'de `upload/tiktok_publish_plan.py` tam olarak buna düştü).
    """
    _yayinlanmis(ortam, "Yürek Yarası", saat_once=90)
    _proje(ortam, "Sofraya Gelmedin", {})

    satirlar = []
    SK.yayin_durgunlugu(log=satirlar.append)
    baslik, mesaj = ortam.gonderilen[0]

    for metin in satirlar + [baslik, mesaj]:
        assert not _cp1254_disi(metin), (
            "cp1254'e sığmayan karakter: %r (metin: %s)"
            % (_cp1254_disi(metin), metin[:80]))


def test_fonksiyondaki_tum_metin_sabitleri_cp1254_uyumlu():
    """Yalnız bu koşuda üretilenler değil, KAYNAKTAKİ tüm metin sabitleri.

    Yorumlar kapsam dışı (AST'de yoklar ve konsola basılmıyorlar); denetlenen
    şey basılabilecek her dize.
    """
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    hedefler = {"yayin_durgunlugu", "_yayin_taramasi", "_damga_ts", "_proje_state"}
    sabitler = []
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name in hedefler:
            sabitler += [x.value for x in ast.walk(d)
                         if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    assert sabitler
    for metin in sabitler:
        assert not _cp1254_disi(metin), "cp1254 dışı sabit: %r" % metin


# --- Sürüklenme muhafızları (kopyalanan değerler) -------------------------

def test_ana_platform_anahtarlari_is_fully_done_ile_AYNI(tmp_path):
    """`_is_fully_done()` KOPYALANMADI; eşdeğerliği DAVRANIŞLA kanıtlanıyor.

    `auto_process` üretim kodundan import EDİLMİYOR (yan etkili, ağır ve ters
    yönde import döngüsü riski var) — ama iki tanımın sessizce ayrışması da
    kabul edilemez: ayrışırsa bu nöbetçi "bekleyen proje" sorusuna
    `_auto_pace_count`tan FARKLI cevap verir ve ya kör kalır ya yanlış alarm
    üretir.
    """
    import auto_process as ap

    tam = tmp_path / "tam"
    tam.mkdir()
    (tam / "state.json").write_text(
        json.dumps({k: "x" for k in SK.ANA_PLATFORM_ANAHTARLARI}), encoding="utf-8")
    assert ap._is_fully_done(str(tam)) is True, (
        "saglik_kontrol'ün dörtlüsü _is_fully_done'ı tatmin etmiyor")

    for eksik in SK.ANA_PLATFORM_ANAHTARLARI:
        d = tmp_path / ("eksik_" + eksik)
        d.mkdir()
        (d / "state.json").write_text(
            json.dumps({k: "x" for k in SK.ANA_PLATFORM_ANAHTARLARI if k != eksik}),
            encoding="utf-8")
        assert ap._is_fully_done(str(d)) is False, (
            "%s eksikken _is_fully_done True diyor — kümeler ayrışmış" % eksik)


def test_esik_52_saatlik_yayin_tabaniyla_iliskili():
    """Eşik, tabanın 1,5 katı: bir pencere kaçınca çalar, ikincisi kaçmadan."""
    import auto_process as ap

    assert SK.YAYIN_TABANI_SN == ap.MIN_YAYIN_ARALIGI_SN, (
        "yayın tabanı auto_process'ten ayrışmış")
    assert SK.YAYIN_DURGUNLUK_ESIGI_SN == 78 * 3600
    assert ap.MIN_YAYIN_ARALIGI_SN < SK.YAYIN_DURGUNLUK_ESIGI_SN < 2 * ap.MIN_YAYIN_ARALIGI_SN


def test_damga_soneki_diskteki_tum_uploaded_at_alanlarini_kapsiyor():
    """Sonek kuralı, elle sayılan listenin unuttuğu alanları da yakalar.

    `telegram_shorts_uploaded_at` (DJ setleri/derlemeler) elle yazılmış bir
    listeye kesinlikle eklenmezdi; sonek eşleşmesi onu kendiliğinden kapsıyor.
    """
    hepsi = ("youtube_uploaded_at", "youtube_shorts_uploaded_at",
             "tiktok_uploaded_at", "instagram_uploaded_at",
             "telegram_uploaded_at", "telegram_shorts_uploaded_at",
             "bluesky_uploaded_at", "facebook_uploaded_at")
    for k in hepsi:
        assert k.endswith(SK.YAYIN_DAMGA_SONEKI)
    # Yayın damgası OLMAYAN alanlar yanlışlıkla kapsanmamalı.
    for k in ("youtube_video_id", "instagram_creation_id", "tiktok_notified",
              "youtube_playlist_id", "kopya_notu"):
        assert not k.endswith(SK.YAYIN_DAMGA_SONEKI)


def test_en_yeni_damga_seciliyor_ve_kokler_elle_sayilmiyor(ortam):
    """Birden çok proje/anahtar arasından EN YENİSİ alınmalı."""
    _yayinlanmis(ortam, "Eski", saat_once=500)
    _proje(ortam, "Karisik", {
        "youtube_uploaded_at": _damga(T0 - 200 * SAAT),
        "bluesky_uploaded_at": _damga(T0 - 90 * SAAT),      # en yenisi bu
        "instagram_uploaded_at": _damga(T0 - 400 * SAAT),
    })

    s = SK.yayin_durgunlugu(log=lambda *a: None)
    assert s["son_yayin"] == "Karisik/bluesky_uploaded_at"
    assert 89 * SAAT < s["sessizlik_sn"] < 91 * SAAT

    # Kök listesi ELLE sayılmıyor: tek kanonik kaynak uyumluluk.proje_klasorleri.
    kaynak = open(_KAYNAK, encoding="utf-8").read()
    agac = ast.parse(kaynak)
    hedef = next(d for d in ast.walk(agac)
                 if isinstance(d, ast.FunctionDef) and d.name == "_yayin_taramasi")
    cagrilar = [d.func.attr for d in ast.walk(hedef)
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)]
    assert "proje_klasorleri" in cagrilar
    # Kök adı bir METİN SABİTİ olarak geçmemeli (docstring hariç — o yalnızca
    # anlatıyor, kod yolunu belirlemiyor).
    govde = [x for x in hedef.body[1:]] if ast.get_docstring(hedef) else hedef.body
    sabitler = [x.value for d in govde for x in ast.walk(d)
                if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    for kok in ("projects", "dj_sets", "derlemeler"):
        assert kok not in sabitler, (
            "kök adı elle sayılmış: %r — tek kanonik kaynak "
            "uyumluluk.proje_klasorleri()" % kok)
