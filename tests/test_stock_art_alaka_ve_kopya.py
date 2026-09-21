"""stock_art.py'nin 2026-09-11 kapak denetiminden doğan ÜÇ düzeltmesinin
koruma testleri. Hiçbiri ağa çıkmaz — Pexels/Pixabay sahtelenir.

Denetimin bulduğu üç ayrı mekanizma:
  1. Seçim derinliği: listeden `hash(başlık) % n` ile kare seçiliyordu, ALAKA
     EŞİĞİ yoktu ("night empty road" -> gündüz şehir panoraması).
  2. Mood çapası ile söz terimleri ÇELİŞİYORDU ("bright vibrant night ...").
  3. Katalog genelinde kopya koruması yoktu (iki proje byte-birebir aynı
     art.jpg aldı; md5 dbf1fd44…).

Ayrıca bu dosya, düzeltmenin GERİYE DÖNÜK olmadığını da kilitliyor:
`generate_cover.generate()` mevcut bir `art.*`'a dokunmuyor.
"""

import hashlib
import json
import subprocess
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config              # noqa: E402
import generate_cover      # noqa: E402
import stock_art           # noqa: E402


class _SahteYanit:
    """requests.Response'un bu modülün kullandığı kadarı."""

    def __init__(self, payload=None, raw: bytes = b""):
        self._payload = payload
        self.content = raw

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _pexels_sahtele(monkeypatch, photos, indirilenler=None, icerik=None):
    """Pexels aramasını ve görsel indirmesini sahteler.

    `icerik`: url -> bytes. Verilmezse her url'den url'nin kendisi türetilir
    (yani farklı url = farklı bayt = farklı md5)."""
    monkeypatch.setattr(stock_art, "_load_api_key",
                        lambda alan="pexels_api_key": "key" if alan == "pexels_api_key" else None)

    def sahte_get(url, **kwargs):
        if url == stock_art.API_URL:
            return _SahteYanit({"photos": photos})
        if indirilenler is not None:
            indirilenler.append(url)
        gövde = (icerik or {}).get(url, url.encode("utf-8"))
        return _SahteYanit(raw=gövde)

    monkeypatch.setattr(stock_art.requests, "get", sahte_get)


# --- 1. ALAKA EŞİĞİ ---------------------------------------------------------

def test_alakasiz_kare_elenir(monkeypatch, tmp_path):
    """Sorgunun sahne kelimeleri fotoğrafın `alt` metninde geçmiyorsa o kare
    seçilmemeli.

    Gerçek vaka: 'Gece Sürüşü' sorgusu "... night empty road ..." idi ve
    hash indeksi listenin kuyruğundaki bir GÜNDÜZ ŞEHİR PANORAMASINA düştü."""
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"},
               "alt": "aerial view of a city skyline at daytime"} for i in range(15)]
    # Tek alakalı kare — listenin sonunda, yani hash indeksi oraya düşmezse
    # eski kod bunu ASLA seçmezdi.
    photos[14] = {"src": {"large2x": "http://x/dogru.jpg"},
                  "alt": "an empty road at night with street lights"}

    indirilenler = []
    _pexels_sahtele(monkeypatch, photos, indirilenler)
    proje = tmp_path / "projects" / "Gece Sürüşü"
    proje.mkdir(parents=True)

    ok = stock_art.fetch_art("Gece Sürüşü", "vibrant night empty road cinematic atmospheric",
                             str(proje / "art.jpg"))
    assert ok is True
    assert indirilenler == ["http://x/dogru.jpg"], indirilenler


def test_hicbiri_esigi_gecemezse_eski_davranisa_dusulur(monkeypatch, tmp_path):
    """Eşik bir KAPI değil: hiçbir aday geçemezse liste olduğu gibi kullanılır
    (alt metni boş gelebilir, elle yazılmış art_query sahne kelimesi
    içermeyebilir). Aksi hâlde otomasyon gereksiz yere bokeh'e düşerdi."""
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"}, "alt": ""} for i in range(15)]
    indirilenler = []
    _pexels_sahtele(monkeypatch, photos, indirilenler)
    proje = tmp_path / "projects" / "Bir Şarkı"
    proje.mkdir(parents=True)

    assert stock_art.fetch_art("Bir Şarkı", "night empty road cinematic atmospheric",
                               str(proje / "art.jpg")) is True
    assert len(indirilenler) == 1


def test_ayni_baslik_ayni_liste_ayni_kare(monkeypatch, tmp_path):
    """Determinizm KORUNDU: aynı şarkı, aynı sonuç listesinde hep aynı kareyi
    alır (projenin genelindeki deterministik üretim ilkesi)."""
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"},
               "alt": "an empty road at night"} for i in range(15)]
    secilenler = []
    for _ in range(3):
        indirilenler = []
        _pexels_sahtele(monkeypatch, photos, indirilenler)
        proje = tmp_path / "projects" / "Yürek Yarası"
        proje.mkdir(parents=True, exist_ok=True)
        assert stock_art.fetch_art("Yürek Yarası", "night empty road",
                                   str(proje / "art.jpg")) is True
        secilenler.append(indirilenler[0])
        os.remove(proje / "art.jpg")
    assert len(set(secilenler)) == 1, secilenler


def test_sahne_kelimeleri_atmosferi_disliyor():
    """Puanlamaya katılmayan kelimeler config'ten TÜRETİLİYOR (elle yazılmış
    bir kopya olsaydı bir tema `art_mood`'u değişince sessizce eskirdi)."""
    disari = stock_art._atmosfer_kelimeleri()
    for tema in config.THEMES.values():
        for kelime in (tema.get("art_mood") or "").lower().split():
            assert kelime in disari, kelime
    for kelime in stock_art.STYLE_SUFFIX.lower().split():
        assert kelime in disari, kelime
    assert stock_art._sahne_kelimeleri(
        "bright vibrant night empty road cinematic atmospheric") == ["empty", "road"]


# --- 2. MOOD / SÖZ ÇELİŞKİSİ ------------------------------------------------

@pytest.mark.parametrize("mood, terms, beklenen", [
    # Ölçülen üç gerçek vaka (pop teması + sözlerden "night")
    ("bright vibrant", ["night", "empty road"], "vibrant"),
    ("bright vibrant", ["night", "empty street"], "vibrant"),
    # Çelişki yoksa mood AYNEN kalır — eski davranış
    ("bright vibrant", ["blossom", "mountains"], "bright vibrant"),
    ("warm golden hour", ["doorway", "window"], "warm golden hour"),
    # "golden hour" iki kelimesi de gece ile çelişiyor, ikisi de düşer
    ("warm golden hour", ["night", "doorway"], "warm"),
    ("warm golden hour", ["winter", "snow"], "golden hour"),
    # Ters yön: tema gece diyor, sözler şafak diyor -> söz kazanır
    ("gritty urban night", ["sunrise", "empty street"], "gritty urban"),
    ("melancholy moody rainy", ["night", "doorway"], "melancholy moody rainy"),
])
def test_mood_celiskisi_cozumu(mood, terms, beklenen):
    assert stock_art._mood_celiskisini_coz(mood, terms) == beklenen


def test_celiskili_sorgu_artik_uretilmiyor(tmp_path):
    """Uçtan uca: pop teması + sözlerde "gece" -> sorguda "bright" OLMAMALI."""
    sozler = tmp_path / "sahte_sarki_sozler.md"
    sozler.write_text("Gece gece yollara düştüm\nGecenin yolu uzun\nYol bitmiyor gece\n",
                      encoding="utf-8")
    import types
    eski = stock_art.BASE_DIR
    stock_art.BASE_DIR = str(tmp_path)
    try:
        q = stock_art.build_query({}, config.THEMES["pop"], "Sahte Şarkı")
    finally:
        stock_art.BASE_DIR = eski
    assert q is not None
    assert "bright" not in q, q
    assert "night" in q, q
    assert isinstance(types, object)


# --- 3. KOPYA KORUMASI ------------------------------------------------------

def _art_yaz(kok, ad, veri: bytes):
    d = kok / ad
    d.mkdir(parents=True, exist_ok=True)
    (d / "art.jpg").write_bytes(veri)
    return d


def test_katalogda_duran_kopya_atlanir(monkeypatch, tmp_path):
    """Gerçek vaka: 'Küllerimden Geç' ile 'Yeniden Doğacağım' AYNI sorguyu
    üretiyor ve havuz 5 sonuçluk olduğu için (11 %% 5 == 1 %% 5) ikisi de aynı
    kareye düşmüştü — art.jpg'leri byte-birebir aynı (md5 dbf1fd44…)."""
    kok = tmp_path / "projects"
    _art_yaz(kok, "Yeniden Doğacağım", b"http://x/0.jpg")   # ilk aday ile AYNI bayt
    proje = kok / "Küllerimden Geç"
    proje.mkdir(parents=True)

    photos = [{"src": {"large2x": f"http://x/{i}.jpg"},
               "alt": "a rainy night doorway"} for i in range(5)]
    indirilenler = []
    _pexels_sahtele(monkeypatch, photos, indirilenler)
    # Hash indeksini sabitle: ilk aday 0.jpg olsun (katalogda DURAN kopya)
    monkeypatch.setattr(stock_art, "_secim_indeksi", lambda t, n: 0)

    out = proje / "art.jpg"
    assert stock_art.fetch_art("Küllerimden Geç", "melancholy rainy night doorway",
                               str(out)) is True
    # İlk aday kopya çıktı -> bir SONRAKİ aday denendi
    assert indirilenler == ["http://x/0.jpg", "http://x/1.jpg"], indirilenler
    yeni = hashlib.md5(out.read_bytes()).hexdigest()
    eski = hashlib.md5((kok / "Yeniden Doğacağım" / "art.jpg").read_bytes()).hexdigest()
    assert yeni != eski


def test_kopya_taramasi_projenin_KENDI_art_dosyasini_saymaz(monkeypatch, tmp_path):
    """Kendi klasöründeki bir art.jpg "başka projede var" sayılmamalı."""
    kok = tmp_path / "projects"
    proje = _art_yaz(kok, "Bir Şarkı", b"http://x/0.jpg")
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"}, "alt": "a road"} for i in range(5)]
    indirilenler = []
    _pexels_sahtele(monkeypatch, photos, indirilenler)
    monkeypatch.setattr(stock_art, "_secim_indeksi", lambda t, n: 0)

    assert stock_art.fetch_art("Bir Şarkı", "empty road", str(proje / "art.jpg")) is True
    assert indirilenler == ["http://x/0.jpg"], indirilenler


def test_hepsi_kopyaysa_yarim_dosya_BIRAKMAZ(monkeypatch, tmp_path):
    """Tüm adaylar kopya çıkarsa False dönülür VE diskte dosya kalmaz —
    yoksa çağıran taraf 'art var' sanıp prosedürel üretimi atlardı
    (`_indir`'in zaten koruduğu aynı tuzak)."""
    kok = tmp_path / "projects"
    for i in range(stock_art.MAKS_ADAY_DENEME):
        _art_yaz(kok, f"Baska {i}", f"http://x/{i}.jpg".encode("utf-8"))
    proje = kok / "Yeni Şarkı"
    proje.mkdir(parents=True)

    photos = [{"src": {"large2x": f"http://x/{i}.jpg"}, "alt": "a road"}
              for i in range(stock_art.MAKS_ADAY_DENEME)]
    _pexels_sahtele(monkeypatch, photos)
    monkeypatch.setattr(stock_art, "_secim_indeksi", lambda t, n: 0)

    out = proje / "art.jpg"
    assert stock_art.fetch_art("Yeni Şarkı", "empty road", str(out)) is False
    assert not out.exists()


def test_kopya_taramasi_bilinen_UC_kokun_hepsine_bakar():
    """`uyumluluk.KOK_ADLARI` ile aynı küme; biri unutulursa bir derlemenin
    kopyası fark edilmezdi (CLAUDE.md: 'yanlış kümeye bakan kod')."""
    import uyumluluk
    assert set(stock_art.ART_KOK_ADLARI) == set(uyumluluk.KOK_ADLARI)
    for k in stock_art.ART_KOKLER:
        assert os.path.isabs(k), k


# --- GERİYE DÖNÜK ETKİ YOK --------------------------------------------------

def test_mevcut_art_yeniden_URETILMEZ(monkeypatch, tmp_path):
    """Denetim ajanının çekincesi ('arşiv kayar') GEÇERSİZ: generate() bir
    art.* dosyası varsa stock_art'a hiç gelmiyor ve art'a hiç yazmıyor."""
    proje = tmp_path / "projects" / "Bir Şarkı"
    proje.mkdir(parents=True)
    # GERCEK bir JPEG sart: cop bayt yazilirsa generate() ffmpeg adiminda
    # patliyor ve test, olcmek istedigi seyi (art yeniden uretiliyor mu)
    # hic olcemeden dusuyor. Kucuk ama gecerli bir kare uretiyoruz.
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=navy:s=64x64:d=0.04", "-frames:v", "1",
                    str(proje / "art.jpg")], check=True)
    (proje / "meta.json").write_text(json.dumps({"title": "Bir Şarkı", "theme": "pop"}),
                                     encoding="utf-8")
    once = hashlib.md5((proje / "art.jpg").read_bytes()).hexdigest()

    def _patlat(*a, **k):
        raise AssertionError("fetch_art çağrıldı — mevcut art yeniden üretiliyor!")

    monkeypatch.setattr(generate_cover.stock_art, "fetch_art", _patlat)
    # cover YOK, yani generate() erken return ETMEZ, gerçekten çalışır.
    generate_cover.generate(str(proje))

    assert hashlib.md5((proje / "art.jpg").read_bytes()).hexdigest() == once
