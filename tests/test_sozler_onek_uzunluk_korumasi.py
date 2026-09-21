# -*- coding: utf-8 -*-
"""`stock_art.find_lyrics_file()` ön-ek kuralının UZUNLUK KORUMASI +
`auto_process._check_youtube_captions`'ın artık sessiz olmayan "token yok" dalı.

NEDEN AYRI BİR DOSYA: `tests/test_altyazi_sozler_eslesmesi.py` aynı boşluğu
ALTYAZI tarafından ölçüyor (`youtube_captions._sozler_dosyasi` ikinci kez
süzdüğü için orada zarar zaten kapalıydı). Burada ölçülen şey KAYNAKTAKİ
kural: gevşek ön-ek eşleşmesi `stock_art.find_lyrics_file`in KENDİSİNDEN
çıkmamalı — çünkü ikinci süzgeci OLMAYAN bir çağıran daha var:
`stock_art.query_from_lyrics()`, yani KAPAK GÖRSELİ araması. Orada yanlış
eşleşme hiçbir istisna atmaz, hiçbir log satırı bırakmaz; sadece kapak
şarkının konusundan kopar.

Ağa ÇIKMAZ, `notify.send()` GERÇEKTEN çağrılmaz, üretim dosyalarına yazmaz
(sözler dosyaları yalnızca OKUNUR; log/kilit yolları `tests/conftest.py`
tarafından yönlendiriliyor).
"""

import difflib
import glob
import io
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap
import notify
import stock_art


# --- 1) Katalogdaki 18 projenin hepsi KENDİ dosyasını buluyor ---------------

def _katalog_basliklari():
    kok = os.path.join(_REPO, "projects")
    for ad in sorted(os.listdir(kok)):
        meta_p = os.path.join(kok, ad, "meta.json")
        if ad.startswith("_") or not os.path.isfile(meta_p):
            continue
        yield ad, json.load(io.open(meta_p, encoding="utf-8")).get("title", "")


def test_katalogdaki_her_proje_dogru_sozler_dosyasini_buluyor():
    """Koruma doğru eşleşmelerin HİÇBİRİNE dokunmamalı.

    Beklenen dosya, başlığın slug'ının KENDİSİ; tek istisna ünsüz yumuşaması
    olan "Beton Krallığı" -> `beton_krallik` (0,889 ile difflib dalından
    geçiyor, ön-ek dalından DEĞİL)."""
    istisna = {"beton_kralligi": "beton_krallik"}
    sayi = 0
    for ad, baslik in _katalog_basliklari():
        slug = stock_art._slugify(baslik)
        beklenen = istisna.get(slug, slug)
        yol = stock_art.find_lyrics_file(baslik)
        assert yol, "%s: sözler dosyası bulunamadı" % ad
        stem = os.path.basename(yol)[: -len("_sozler.md")]
        assert stem == beklenen, "%s: %s -> %s (beklenen %s)" % (
            ad, slug, stem, beklenen)
        sayi += 1
    # SABİT SAYI DEĞİL, TABAN (2026-09-12) — kardeşi
    # tests/test_altyazi_sozler_eslesmesi.py'deki aynı satırla birlikte
    # düzeltildi. `== 18` yazıyordu; katalog 19'a çıkınca kırıldı, oysa yeni
    # şarkı eklemek arıza değil normal işleyiş. Bu assert'in gerçek işi
    # "döngü hiç çalışmadı / keşif bozuldu" halini yakalamak.
    assert sayi >= 18, "katalog küçülmüş ya da keşif bozulmuş: %d proje" % sayi


def test_beton_kralligi_difflib_esiginin_ustunde_kaliyor():
    """Koruma bu GERÇEK ve GEREKLİ eşleşmeyi kırmamalı — ön koşulu da ölç:
    çift saf bir ön-ek çifti DEĞİL, difflib dalından geçiyor."""
    slug = stock_art._slugify("Beton Krallığı")
    stem = "beton_krallik"
    assert not (stem.startswith(slug) or slug.startswith(stem))
    oran = difflib.SequenceMatcher(None, slug, stem).ratio()
    assert oran >= 0.85, oran
    # Uzunluk oranı da 0,8'in üstünde: ön-ek çifti OLSAYDI bile geçerdi.
    assert min(len(slug), len(stem)) / max(len(slug), len(stem)) >= \
        stock_art.ONEK_UZUNLUK_ORANI


# --- 2) Beş gevşek vaka artık REDDEDİLİYOR ---------------------------------

@pytest.mark.parametrize("baslik, eski_dosya", [
    ("Neon", "neon_kalp"),                  # ön-ek: yeni şarkı, eski dosya
    ("Son", "son_kez"),
    ("Bu Gece", "bu_gece_kazandik"),
    ("Yeraltı Kralı", "yeralti"),           # ters yön: slug.startswith(stem)
    ("Sokaklar", "sokaklar_beni_tanir"),
])
def test_gevsek_onek_eslesmesi_kaynakta_reddedilir(baslik, eski_dosya):
    """Korumadan ÖNCE `find_lyrics_file` bu dosyaları döndürüyordu.

    `neon_kalp_sozler.md` katalogda SAHİPSİZ (karşılığı olan proje yok) —
    yani "Neon" adlı bir şarkı eklendiği an tuzak tetiklenirdi."""
    slug = stock_art._slugify(baslik)
    # Ön koşul: dosya diskte DURUYOR ve çıplak ön-ek kuralı onu seçerdi.
    assert os.path.isfile(os.path.join(_REPO, "%s_sozler.md" % eski_dosya))
    assert eski_dosya.startswith(slug) or slug.startswith(eski_dosya)
    assert stock_art.find_lyrics_file(baslik) is None


def test_gevsek_eslesme_kapak_sorgusu_da_uretmiyor():
    """Asıl zarar burada: sözler dosyası yanlış seçilirse BAŞKA bir şarkının
    imgelerinden Pexels sorgusu üretilir ve kapak konudan kopar."""
    tema = {"art_mood": "melancholy moody", "art_query": "rainy window"}
    assert stock_art.query_from_lyrics("Neon", tema) is None


# --- 3) Eşiğin kendisi: difflib daliyla TUTARLI olmak zorunda --------------

def test_onek_esigi_difflib_dalini_bos_birakmiyor():
    """Saf ön-ek çiftlerinde difflib oranı tam olarak 2r/(1+r) (r=kısa/uzun).

    Eşik 0,739'un ALTINA çekilirse koruma anlamını yitirir: ön-ek dalının
    reddettiğini difflib dalı (0,85) zaten geçirirdi. Bu test, birinin eşiği
    "biraz gevşetelim" diye düşürmesini yakalar."""
    r = stock_art.ONEK_UZUNLUK_ORANI
    difflib_karsiligi = 2 * r / (1 + r)
    import youtube_captions
    assert difflib_karsiligi >= youtube_captions.SLUG_BENZERLIK_ESIGI, (
        "ön-ek eşiği %.3f, difflib karşılığı %.3f < %.2f — koruma delinir"
        % (r, difflib_karsiligi, youtube_captions.SLUG_BENZERLIK_ESIGI))


def test_bir_harf_eksik_klasor_adi_hala_calisiyor():
    """Ön-ek dalının TEK meşru işi (docstring'deki "Kalbim Oynuyo" vakası):
    birkaç harflik fark yutulmalı, bir KELİMELİK fark yutulmamalı."""
    assert stock_art.find_lyrics_file("Kalbim Oynuyo") is not None
    assert stock_art.find_lyrics_file("Sokaklar Beni") is None


def test_sahipsiz_sozler_dosyalari_beklenen_kumede():
    """Katalogda 19 sözler dosyası, 18 proje var. Yeni bir sahipsiz dosya
    eklenirse bu test kırmızı yanar — her sahipsiz dosya yeni bir yem."""
    stemler = {os.path.basename(p)[: -len("_sozler.md")]
               for p in glob.glob(os.path.join(_REPO, "*_sozler.md"))}
    sahipli = set()
    for _, baslik in _katalog_basliklari():
        yol = stock_art.find_lyrics_file(baslik)
        if yol:
            sahipli.add(os.path.basename(yol)[: -len("_sozler.md")])
    assert stemler - sahipli == {"neon_kalp"}


# --- 4) auto_process: "token yok" dalı artık SESSİZ DEĞİL ------------------

@pytest.fixture
def temiz_uyari(monkeypatch):
    """Her test ayrı bir 'koşu' (uyar_bir_kez hafızası koşu başına).
    `notify.send` GERÇEKTEN çağrılırsa test patlar."""
    notify._uyarilanlar.clear()

    def _yasak(*a, **k):
        raise AssertionError("notify.send() gerçekten çağrıldı")

    monkeypatch.setattr(notify, "send", _yasak)
    yield
    notify._uyarilanlar.clear()


@pytest.fixture
def token_yok(monkeypatch):
    """SADECE `upload/token.json`'ı yok gösterir — gerçek token dosyaları
    diskte duruyor, geniş bir `os.path.isfile` sahtesi başka testleri/kod
    yollarını sessizce bozardı."""
    hedef = os.path.join(os.path.dirname(os.path.abspath(ap.__file__)),
                         "upload", "token.json")
    gercek = os.path.isfile

    def _isfile(yol):
        if os.path.abspath(yol) == os.path.abspath(hedef):
            return False
        return gercek(yol)

    monkeypatch.setattr(ap.os.path, "isfile", _isfile)
    return hedef


def _durum():
    return {"youtube_video_id": "VID123"}


def test_token_yoksa_kosu_basina_bir_satir_birakilir(tmp_path, capsys,
                                                     temiz_uyari, token_yok):
    """Eskiden bu dal sessizce False dönüyordu: altyazı hattı KATALOĞUN
    TAMAMI için ölü olurdu ve tek belirtisi "hiçbir videoda altyazı yok"."""
    assert ap._check_youtube_captions(str(tmp_path), _durum()) is False
    metin = capsys.readouterr().err
    assert "token.json" in metin
    assert "altyaz" in metin.lower()


def test_token_uyarisi_proje_basina_tekrarlanmiyor(tmp_path, capsys,
                                                   temiz_uyari, token_yok):
    """18 bekleyen projede 18 satır = log'u gürültüye boğmak."""
    for _ in range(5):
        assert ap._check_youtube_captions(str(tmp_path), _durum()) is False
    assert capsys.readouterr().err.count("token.json") == 1


def test_video_yoksa_hala_sessiz(tmp_path, capsys, temiz_uyari, token_yok):
    """Henüz YouTube'a çıkmamış proje TEK sessiz dal olarak kalmalı —
    aksi halde her koşuda her bekleyen proje için satır basılırdı."""
    assert ap._check_youtube_captions(str(tmp_path), {}) is False
    assert capsys.readouterr().err == ""


def test_docstringde_cooldown_artik_karsiligi_var():
    """"Yalan söyleyen yorum, hiç yorum olmamasından kötüdür" (CLAUDE.md):
    docstring bir SOĞUMA PENCERESİNDEN bahsediyorsa o pencere kodda OLMALI."""
    import youtube_captions
    d = ap._check_youtube_captions.__doc__
    assert "soğuma" in d
    assert "UYUSMAZLIK_BEKLEME_SN" in d
    assert youtube_captions.UYUSMAZLIK_BEKLEME_SN > 0
