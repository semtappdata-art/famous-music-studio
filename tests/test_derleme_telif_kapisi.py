# -*- coding: utf-8 -*-
"""TELİF KAPISI — telif işareti taşıyan şarkı bir derlemeye GİREMEZ.

NEDEN BU TESTLER VAR (2026-09-12 denetimi):
`derlemeler/README.md` ve `derleme.py`'nin modül başlığı bunu bir GARANTİ
olarak yazıyordu ("`telif_araliklari` olan şarkılar hiç girmiyor"), kapı da
gerçekten koddaydı — ama HİÇBİR test onu sınamıyordu
(`grep -c telif tests/test_derleme_md5_tekrari.py tests/test_derleme_playlist.py`
ikisinde de 0). Yani deponun en sert güvenlik garantilerinden biri tek bir
`if` satırına dayanıyordu; o satır silinse ya da koşulu terse dönse test
paketi YEŞİL kalırdı. Bu, CLAUDE.md'deki kuralın ihlali:
"bir yorum bir GARANTİ ifade ediyorsa, o garantiyi doğrulayan bir test
olmadan yazma" (`tests/test_sizinti_kaynaklari.py` ile aynı gerekçe —
`dj_famous_process.py`'nin maskeleyici yorumu doğruyu söylediği için arıza
grep'le bile görünmüyordu).

BAHİS BOŞ DEĞİL: `dj_sets/City Pulse Set`'in Content ID itirazı HÂLÂ AÇIK.
Derleme YENİDEN YAYIN demek; telifli bir kesidin derlemeye girmesi mevcut
itirazın üstüne İKİNCİ bir ihlal eklerdi.

Testler dört şeyi çiviliyor:
  1. Kapı GERÇEKTEN kapanıyor — `telif_araliklari` dolu olan aday listede yok.
  2. Alanın hangi BİÇİMİ kapıyı kapatır (dolu liste, bozuk tip, `telif_eser`
     tek başına) ve hangisi KAPATMAZ (boş liste, alan hiç yok, `null`,
     `telif_notu`) — her biri ayrı bir testte, gerekçesiyle.
  3. Eleme SESSİZ DEĞİL (stderr'e satır düşer).
  4. `uret()` ucu ucuna: kapı `adaylar()`'da olsa bile telifli şarkı ne
     özete, ne `meta.json`'daki `derleme_liste`/`derleme_temalari`'na girer.

Ayrıca bu dosya `uret()`in UÇTAN UCA ilk dumanı testi — o fonksiyon bugüne
kadar hiç test edilmemişti. ffmpeg/render TAMAMEN monkeypatch: `ses_birlestir`
yerine sahte bir yazıcı geçiyor ve `subprocess.run` patlayacak şekilde
yamalanıyor, yani gerçek bir render kazayla bile çalışamaz.

Fikstür deseni `tests/test_derleme_md5_tekrari.py`'den alındı (aynı `_proje`
kurulumu + `KAYNAK`/`_sure` monkeypatch'i); buradaki tek fark `state.json`'a
telif alanları koyabilmek ve `HEDEF_KOK`'ü de tmp'ye çekmek.
"""

import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import config
import derleme


def _proje(kok, ad, *, ses_icerik=None, privacy="public",
           yuklendi="2026-09-01T10:00:00", izlenme=0, tema="hiphop",
           telif=None):
    """`projects/<ad>` benzeri bir fikstür klasörü kurar.

    `telif`: `state.json`'a AYNEN eklenen sözlük (ör.
    `{"telif_araliklari": [[10, 20]]}`). Sesler bilerek FARKLI: bu dosyanın
    konusu telif kapısı, md5 tekrar elemesi değil (o `test_derleme_md5_tekrari`).
    """
    p = os.path.join(str(kok), ad)
    os.makedirs(p, exist_ok=True)
    if ses_icerik is None:
        ses_icerik = b"RIFF" + ad.encode("utf-8") * 40
    with open(os.path.join(p, "audio.wav"), "wb") as f:
        f.write(ses_icerik)
    st = {
        "youtube_video_id": "vid_%s" % ad,
        "youtube_privacy": privacy,
        "youtube_uploaded_at": yuklendi,
        "youtube_views": izlenme,
    }
    if telif:
        st.update(telif)
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    with open(os.path.join(p, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": ad, "theme": tema}, f, ensure_ascii=False)
    return p


@pytest.fixture
def havuz(tmp_path, monkeypatch):
    """`adaylar()`ı tmp fikstür köküne bağlar; ffprobe'a bağımlılığı keser."""
    kaynak = tmp_path / "projects"
    kaynak.mkdir()
    monkeypatch.setattr(derleme, "KAYNAK", str(kaynak))
    # _sure() ffprobe çağırıyor; bu testlerin konusu SÜRE değil ELEME.
    monkeypatch.setattr(derleme, "_sure", lambda yol: 180.0)
    return kaynak


# --- 1) Garantinin kendisi: telifli şarkı derlemeye GİRMEZ ---------------

def test_telif_araliklari_olan_sarki_derlemeye_girmiyor(havuz):
    """README'nin ve modül başlığının GARANTİSİ, birebir.

    Bu testin kırmızıya dönmesinin TEK yolu kapının kodda kaybolması —
    yani denetimin bulduğu boşluk artık kapalı.
    """
    _proje(havuz, "Temiz Şarkı")
    _proje(havuz, "Telifli Şarkı", telif={
        "telif_araliklari": [[180.0, 190.0], [330.0, 388.5]],
        "telif_eser": "Bring Me To Life - Tiesto, FORS",
    })

    adlar = [p["ad"] for p in derleme.adaylar()]
    assert adlar == ["Temiz Şarkı"], \
        "telifli şarkı derleme havuzuna girdi: %r" % adlar


def test_telif_kapisi_temaya_gore_daraltilmis_havuzda_da_calisiyor(havuz):
    """`--tema` filtresi kapıyı ATLATAMAZ — iki filtre bağımsız.

    Tema filtresi kapıdan SONRA geliyor; sıra değişse (ya da kapı yanlışlıkla
    `if tema and ...` bloğunun içine kaysa) telifli bir şarkı tek temalı bir
    derlemede yeniden görünürdü.
    """
    _proje(havuz, "Arabesk Temiz", tema="arabesk")
    _proje(havuz, "Arabesk Telifli", tema="arabesk",
           telif={"telif_araliklari": [[0, 12]]})

    adlar = [p["ad"] for p in derleme.adaylar("arabesk")]
    assert adlar == ["Arabesk Temiz"]


# --- 2) Alanın BİÇİMLERİ: hangisi kapatır, hangisi kapatmaz --------------

def test_telif_alani_hic_yoksa_sarki_giriyor(havuz):
    """İşaret YOKSA kapı AÇIK — yoksa hiçbir şarkı derlemeye giremezdi."""
    _proje(havuz, "İşaretsiz")
    assert [p["ad"] for p in derleme.adaylar()] == ["İşaretsiz"]


def test_bos_liste_isaret_sayilmiyor(havuz):
    """`telif_araliklari: []` = TEMİZLENMİŞ kayıt, kapı AÇIK KALMALI.

    Bu bilinçli bir karar, kazara truthiness değil: `state_io` göçünde
    temizlenen bir kayıt tam olarak böyle görünüyor
    (`tests/test_state_io.py`, `{"telif_araliklari": []}`) ve
    `uyumluluk.kontrol()` de aynı kuralı kullanıyor
    (`if durum.get("telif_araliklari"):`). Boş listeyi işaret saymak, telifi
    temizlenmiş her şarkıyı KALICI olarak derleme dışında bırakır ve iki
    kapının kuralını ayrıştırırdı — bu depoda "aynı karar iki yerde iki
    kuralla" tam olarak `test_derleme_playlist.py`'nin yakaladığı arıza sınıfı.
    """
    _proje(havuz, "Temizlenmiş", telif={"telif_araliklari": []})
    assert [p["ad"] for p in derleme.adaylar()] == ["Temizlenmiş"]


def test_null_isaret_sayilmiyor(havuz):
    """`telif_araliklari: null` alanın hiç olmamasıyla AYNI muamele görür.

    JSON `null` bu deponun state dosyalarında "alan var ama değeri yok"
    demek; `uyumluluk` de onu işaret saymıyor. Kapıyı buna bağlamak iki
    kapıyı ayrıştırırdı.
    """
    _proje(havuz, "Boş Değer", telif={"telif_araliklari": None,
                                      "telif_eser": None})
    assert [p["ad"] for p in derleme.adaylar()] == ["Boş Değer"]


@pytest.mark.parametrize("bozuk", [
    "Bring Me To Life",                    # liste yerine düz metin
    {"0": [10, 20]},                       # liste yerine sözlük
    [[10, 20], "ikinci aralık bozuk"],     # yarı bozuk liste
    1,                                     # sayı
])
def test_bozuk_tip_kapiyi_KAPATIYOR(havuz, bozuk):
    """Alan bozuk tipteyse kapı KAPANIR — "okuyamıyorum" ≠ "temiz".

    Yön burada kritik: bozuk bir işareti yok sayan bir kapı, `state.json`
    bozulduğu anda kendiliğinden AÇILIRDI. `uyumluluk.py` aynı kararı
    `DurumBozuk` ile veriyor ("bilmiyorum ile temiz aynı şey değil, boru
    hattı burada durmalı"), `uyumluluk.KOKLER` vakası da (CLAUDE.md) bir
    kapının SESSİZCE kendiliğinden açılmasının bu depodaki bedelini
    gösteriyor.
    """
    _proje(havuz, "Bozuk İşaret", telif={"telif_araliklari": bozuk})
    assert [p["ad"] for p in derleme.adaylar()] == [], \
        "bozuk tipli telif işareti kapıyı AÇTI: %r" % (bozuk,)


def test_telif_eser_tek_basina_da_kapiyi_kapatiyor(havuz):
    """`telif_eser` var, `telif_araliklari` YOK -> şarkı yine de GİRMEZ.

    BU, DENETİMDE BULUNAN GERÇEK BOŞLUKTU (2026-09-12'de kapatıldı).
    Telif alanlarını depoda hiçbir kod üretmiyor — `dj_tarama_kontrol.py`
    karantina kurar ama `telif_*` YAZMAZ — yani ikisi de ELLE yazılıyor.
    Content ID eşleşmesi eserin TAMAMINI kapsadığında ya da aralıklar henüz
    çıkarılmadığında `telif_eser` tek başına yazılır; eski kapı o hâlde
    açıktı. Bu, aynı dosyadaki `_md5_tekrarini_ele`'nin kapattığı boşluğun
    birebir aynısı: koruma DOSYADA değil, "operatör her iki yarıyı da
    doldurur" KONVANSİYONUNDA duruyordu.
    """
    _proje(havuz, "Aralıksız Telif",
           telif={"telif_eser": "Bring Me To Life - Tiesto, FORS"})
    assert [p["ad"] for p in derleme.adaylar()] == []


def test_telif_notu_tek_basina_kapiyi_kapatmiyor(havuz):
    """`telif_notu` BİLEREK işaret listesinde YOK — sınır burada.

    O alan serbest metin ve tersi bir cümle de taşıyabilir ("kontrol edildi,
    telif yok"). Kapıyı bir NOTUN varlığına bağlamak "işaret" ile "yorum"u
    karıştırmak olurdu. Gerçek City Pulse kaydında not zaten `telif_eser` +
    `telif_araliklari` ile BİRLİKTE duruyor, yani kapı orada yine kapanıyor.
    """
    _proje(havuz, "Sadece Not",
           telif={"telif_notu": "kontrol edildi, Content ID eşleşmesi yok"})
    assert [p["ad"] for p in derleme.adaylar()] == ["Sadece Not"]


def test_isaret_alanlari_sabitte_tanimli(havuz):
    """Kapı bir SABİTTEN besleniyor — alan listesi tek yerde.

    `TELIF_ISARETLERI`'nden bir alan düşerse bu test, o alanın kendi testiyle
    BİRLİKTE kırmızıya döner; liste sessizce daralamaz.
    """
    assert derleme.TELIF_ISARETLERI == ("telif_araliklari", "telif_eser")
    for alan in derleme.TELIF_ISARETLERI:
        assert derleme._telif_isareti({alan: [[0, 1]]}) == alan
    assert derleme._telif_isareti({}) == ""


def test_state_json_okunamazsa_sarki_aday_olamiyor(havuz):
    """`state.json` bozuksa TELİF DOĞRULANAMAZ -> şarkı havuza GİRMEZ.

    Kapının en sessiz atlatma yolu telif alanını silmek değil, dosyayı
    okunamaz hâle getirmekti. `adaylar()` bozuk dosyayı `continue` ile
    atlıyor — yani fail-CLOSED. Bu testin işi o yönü çivilemek: bir gün
    `except` bloğu "boş sözlükle devam et"e çevrilirse telifli bir kayıt
    sessizce derlemeye girerdi (`uyumluluk._durum()`'un 2026-09-11'de
    düzeltilen arızasının birebir aynısı).
    """
    _proje(havuz, "Temiz Şarkı")
    kirik = _proje(havuz, "Bozuk Kayıt",
                   telif={"telif_araliklari": [[10, 20]]})
    with open(os.path.join(kirik, "state.json"), "w", encoding="utf-8") as f:
        f.write('{"telif_araliklari": [[10, 20]], "telif_ese')   # yarım JSON

    assert [p["ad"] for p in derleme.adaylar()] == ["Temiz Şarkı"]


# --- 3) Eleme SESSİZ OLAMAZ ----------------------------------------------

def test_telif_elemesi_loga_dusuyor(havuz, capsys):
    """Şarkının adı VE hangi alanın kapattığı stderr'e düşmeli.

    Sessiz bir eleme "bu şarkı derlemede neden yok" sorusunu cevapsız
    bırakır; bu deponun en pahalı hata sınıfı tam olarak sessiz koruma
    (bkz. CLAUDE.md). `_md5_tekrarini_ele` aynı kararı zaten veriyor.
    """
    _proje(havuz, "Telifli Şarkı", telif={"telif_araliklari": [[10, 20]]})

    derleme.adaylar()
    hata = capsys.readouterr().err
    assert "Telifli Şarkı" in hata
    assert "telif_araliklari" in hata
    assert "ALINMADI" in hata


def test_telif_elemesi_stdout_u_kirletmiyor(havuz, capsys):
    """Satır stderr'e gider, stdout'a DEĞİL — `--dry-run` tablosu boru
    hattına verilebilir olmalı (`_md5_tekrarini_ele` ile aynı karar)."""
    _proje(havuz, "Telifli Şarkı", telif={"telif_eser": "X"})

    derleme.adaylar()
    yakalanan = capsys.readouterr()
    assert "Telifli" not in yakalanan.out
    assert "Telifli" in yakalanan.err


# --- 4) uret() UÇTAN UCA (duman testi) -----------------------------------

@pytest.fixture
def uret_ortami(havuz, tmp_path, monkeypatch):
    """`uret()`i gerçek ffmpeg/render'a HİÇ dokunmadan koşturulabilir yapar.

    ÜÇ yamanın üçü de zorunlu:
      * `HEDEF_KOK` -> tmp. 2026-09-12'den beri `tests/conftest.py`'nin
        `KORUNAN_YOL_ADLARI` listesi `HEDEF_KOK`'u da kapsıyor, yani bu yama
        artık TEK savunma hattı değil. Yine de duruyor ve durmalı: conftest
        kör bir emniyet ağı (adı geçen her sabiti tmp'ye çeker), burada ise
        klasörün YERİNİ bilmek gerekiyor — `uret()`in ne yazdığı okunacak.
        İki kapı bilerek: conftest'ten bir gün bu ad düşerse test sessizce
        gerçek `derlemeler/`e yazmaya başlamamalı.
      * `_enerji` -> librosa yüklemesi yok, sıralama DETERMİNİSTİK olsun.
      * `ses_birlestir` -> ffmpeg yok; sahte bir audio.wav yazıp True döner.
    Ayrıca `subprocess.run` patlayacak şekilde yamalanıyor: gerçek bir render
    kazayla bile başlayamaz (gerçek koşu SAATLER sürer ve diski doldurur).
    """
    hedef = tmp_path / "derlemeler"
    hedef.mkdir()
    monkeypatch.setattr(derleme, "HEDEF_KOK", str(hedef))

    enerjiler = {"Alfa": 0.1, "Beta": 0.2, "Gama": 0.3,
                 "Delta": 0.4, "Epsilon": 0.5, "Telifli": 0.9}

    def _sahte_enerji(yol):
        return enerjiler.get(os.path.basename(os.path.dirname(yol)), 0.0)

    monkeypatch.setattr(derleme, "_enerji", _sahte_enerji)

    birlesenler = []

    def _sahte_birlestir(secilen, cikti):
        birlesenler.append([p["ad"] for p in secilen])
        with open(cikti, "wb") as f:
            f.write(b"RIFF sahte birlesik ses")
        return True

    monkeypatch.setattr(derleme, "ses_birlestir", _sahte_birlestir)

    def _yasak_run(*a, **kw):
        raise AssertionError("TESTTE GERÇEK subprocess ÇALIŞTI: %r" % (a,))

    monkeypatch.setattr(derleme.subprocess, "run", _yasak_run)

    return {"hedef": hedef, "birlesenler": birlesenler}


def _katalog(kok):
    """Beş temiz + bir telifli şarkı. Süreler eşit (180 sn), izlenmeler farklı."""
    for i, ad in enumerate(["Alfa", "Beta", "Gama", "Delta", "Epsilon"]):
        _proje(kok, ad, izlenme=100 - i * 10,
               tema="arabesk" if i < 3 else "pop")
    _proje(kok, "Telifli", izlenme=9999, tema="arabesk", telif={
        "telif_araliklari": [[180.0, 190.0]],
        "telif_eser": "Bring Me To Life - Tiesto, FORS",
    })


def test_uret_ucdan_uca_secim_siralama_ve_cikti(havuz, uret_ortami):
    """`uret()`in seçim -> sıralama -> çıktı zinciri bozulmamış.

    Bu fonksiyon bugüne kadar UÇTAN UCA hiç test edilmemişti; parçaları
    (`adaylar`, `sec`, `zaman_damgalari`) ayrı ayrı test edilse bile
    ARALARINDAKİ BAĞLANTI test edilmiyordu — bu deponun en sık arıza sınıfı
    tam olarak bağlantı seviyesinde (bkz. CLAUDE.md).
    """
    _katalog(havuz)

    ozet = derleme.uret("Gece Seansı Vol. 9", None, 15.0, dry_run=False)

    assert not ozet.get("hata"), ozet
    # SIRALAMA: enerji eğrisi (ikinci en sakin açılış, en sakinler sona).
    # Enerjiler Alfa<Beta<Gama<Delta<Epsilon -> Beta, Epsilon, Delta, Gama, Alfa.
    assert [x["ad"] for x in ozet["liste"]] == \
        ["Beta", "Epsilon", "Delta", "Gama", "Alfa"]
    # SEÇİM: telifli şarkı EN ÇOK izlenen olmasına rağmen (9999) listede YOK.
    assert "Telifli" not in [x["ad"] for x in ozet["liste"]]
    assert ozet["parca"] == 5
    # ZAMAN DAMGALARI: 180 sn parçalar, 6 sn çapraz geçiş -> 174 sn adım.
    assert [x["zaman"] for x in ozet["liste"]] == \
        ["0:00", "2:54", "5:48", "8:42", "11:36"]
    assert ozet["sure_dk"] == pytest.approx(14.6, abs=0.1)
    # Birleştirmeye giden liste ile özetteki liste AYNI olmalı — ikisi
    # ayrışırsa YouTube açıklamasındaki bölüm damgaları sesle uyuşmaz.
    assert uret_ortami["birlesenler"] == [[x["ad"] for x in ozet["liste"]]]


def test_uret_meta_json_yaziyor_ve_telifliyi_icermiyor(havuz, uret_ortami):
    """Çıktı klasöründeki `meta.json` yayın hattının TEK girdisi.

    `dj_famous_process.py --base derlemeler` bu dosyayı normal bir proje gibi
    okuyor; `derleme_liste` YouTube açıklamasına bölüm damgası,
    `derleme_temalari` başlıktaki tür etiketi oluyor. Telifli şarkı bunların
    HİÇBİRİNDE geçmemeli — geçseydi telifli malzeme metin olarak da yayına
    çıkardı.
    """
    _katalog(havuz)

    ozet = derleme.uret("Gece Seansı Vol. 9", None, 15.0, dry_run=False)

    klasor = ozet["klasor"]
    assert os.path.isdir(klasor)
    assert os.path.isfile(os.path.join(klasor, "audio.wav"))
    with open(os.path.join(klasor, "meta.json"), encoding="utf-8") as f:
        m = json.load(f)

    assert m["title"] == "Gece Seansı Vol. 9"
    assert m["derleme"] is True
    # `theme` GEÇERLİ bir config.THEMES anahtarı olmak ZORUNDA (kapak rengi,
    # validate_project, resolve_language hep buradan okuyor).
    assert m["theme"] in config.THEMES
    assert len(m["derleme_temalari"]) == 5
    assert [x["ad"] for x in m["derleme_liste"]] == \
        [x["ad"] for x in ozet["liste"]]
    assert "Telifli" not in json.dumps(m, ensure_ascii=False)
    # Geçici klasör ARKADA KALMADI (yarım klasör yayın hattına girerdi).
    assert not os.path.isdir(os.path.join(str(uret_ortami["hedef"]),
                                          ".tmp-Gece Seansı Vol. 9"))


def test_uret_dry_run_diske_HIC_dokunmuyor(havuz, uret_ortami):
    """`--dry-run` tabloyu üretir ama klasör/ses YAZMAZ."""
    _katalog(havuz)

    ozet = derleme.uret("Kuru Deneme", None, 15.0, dry_run=True)

    assert ozet.get("kuru") is True
    assert "klasor" not in ozet
    assert ozet["liste"]
    assert os.listdir(str(uret_ortami["hedef"])) == []
    assert uret_ortami["birlesenler"] == [], "dry-run ffmpeg tarafına geçti"


def test_uret_havuz_telif_yuzunden_kuculunce_duruyor(havuz, uret_ortami):
    """Telif kapısı havuzu 2'nin altına düşürürse `uret()` HATA döner.

    Bu, kapının "sessizce yarım bir derleme üretme" ihtimalini kapatıyor:
    telifliyi atlayıp tek parçalık bir "derleme" üretmek yerine iş durur.
    """
    _proje(havuz, "Tek Temiz")
    _proje(havuz, "Telifli Bir", telif={"telif_araliklari": [[0, 5]]})
    _proje(havuz, "Telifli İki", telif={"telif_eser": "Bring Me To Life"})

    ozet = derleme.uret("Olmayan Derleme", None, 15.0, dry_run=False)

    assert "yeterli şarkı yok" in ozet.get("hata", "")
    assert os.listdir(str(uret_ortami["hedef"])) == []


def test_uret_ayni_adla_yeniden_uretim_ustune_yaziyor(havuz, uret_ortami):
    """Aynı ada ikinci koşu: dizin üstüne `os.replace` Windows'ta patlar,
    bu yüzden dosya dosya taşınıyor. İkinci koşu hata vermemeli."""
    _katalog(havuz)

    ilk = derleme.uret("Gece Seansı Vol. 9", None, 15.0, dry_run=False)
    ikinci = derleme.uret("Gece Seansı Vol. 9", None, 15.0, dry_run=False)

    assert not ikinci.get("hata"), ikinci
    assert ikinci["klasor"] == ilk["klasor"]
    assert os.path.isfile(os.path.join(ikinci["klasor"], "meta.json"))
