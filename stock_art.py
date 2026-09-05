"""Şarkının tarzına/sözlerine uygun GERÇEK bir fotoğrafı Pexels'ten indirir —
generate_cover.py bunu art.jpg olarak kullanır (kart içeriği + blur backdrop
kaynağı).

NEDEN VAR: Önceden art.jpg elle sağlanmadığında generate_cover.py düz bir
prosedürel gradyan + bokeh dokusu üretiyordu. Kullanıcı isteği: kapak görseli
şarkının TARZINI ve sözlerinin çağrıştırdığı MEKÂNI/atmosferi anımsatsın
(yağmurlu pencere, gece şehri, altın saat ormanı gibi) — soyut bir gradyan
değil. Videodaki kartın ve blur backdrop'ın rengi zaten art.jpg'den türediği
için (bkz. ffmpeg_utils.ensure_art_backdrop), fotoğraf değişince videonun tüm
renk atmosferi de otomatik olarak o tarza uyuyor.

ARAMA TERİMİ nereden gelir (öncelik sırasıyla):
  1. meta.json'daki "art_query"  — o şarkıya özel sahne (en güçlü kontrol)
  2. config.THEMES[theme]["art_query"] — tarzın varsayılan atmosferi
Terimler İngilizce yazılır (Pexels'in arama dizini ağırlıklı İngilizce).

DETERMİNİSTİK: Aynı şarkı (aynı başlık + aynı sorgu) her zaman AYNI fotoğrafı
seçer — sonuç listesinden başlığın hash'ine göre bir indeks alınır. Böylece bir
projeyi yeniden işlemek kapağı rastgele değiştirmez (projenin genelindeki
deterministik üretim ilkesiyle aynı, bkz. social_text.py, generate_cover.py'nin
bokeh seed'i).

BOZULMAZ: API anahtarı yoksa, ağ yoksa, sonuç yoksa ya da indirme başarısızsa
None döner — generate_cover.py sessizce eski prosedürel bokeh üretimine düşer.
Otomasyon HİÇBİR durumda bu yüzden durmaz.

LİSANS: Pexels License — ücretsiz, ticari kullanıma açık, atıf zorunlu değil
(bu kanal para kazanabilir bir YouTube kanalı olduğu için önemli). Kaynak:
https://www.pexels.com/license/
"""

import difflib
import glob
import hashlib
import json
import os
import re

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "stock_art_config.json")

# --- Sözlerden görsel anahtar kelime çıkarımı -------------------------------
#
# Türkçe sözlerdeki SOMUT/FOTOĞRAFLANABİLİR imgeleri İngilizce Pexels terimlerine
# eşler. Kasıtlı olarak SADECE somut şeyler var — "aşk", "umut", "yalnızlık" gibi
# soyut kelimeler stok fotoğraf aramalarında ucuz görünen poz vermiş insan
# fotoğrafları döndürüyor, bu da markayı amatörleştirir. Mekân/hava/nesne/ışık
# kalır, duygu kalmaz (duyguyu zaten tema rengi + karartma katmanı taşıyor).
#
# Türkçe SONDAN EKLEMELİ: "sokak" -> "sokakta", "sokakları", "sokağından".
# Bu yüzden eşleşme kelimenin BAŞINA bakıyor (startswith) ve ünsüz yumuşaması
# olan kökler ("sokak"/"sokağ", "kitap"/"kitab") ayrı ayrı listeleniyor.
# Kökler en az 3 harf — daha kısası çok fazla yanlış eşleşme üretiyor.
# SADECE MEKÂN / HAVA / IŞIK terimleri var — NESNE terimleri (zincir, masa,
# mektup, gitar, saat) BİLEREK çıkarıldı. Denendi ve kötü sonuç verdi: nesne
# aramaları stok fotoğrafta katalog/ürün çekimi döndürüyor ve kelimenin yanlış
# anlamına kayıyor ("Kırık Zincir" -> "chain" -> BİSİKLET zinciri fotoğrafı).
# Mekân/hava terimleri ise atmosferik ve şarkının duygusunu taşıyabiliyor.
# İkincil fayda: tabela/logo içeren kare gelme olasılığı düşüyor — art.jpg
# METİNSİZ olmak zorunda (blur backdrop'ta yazı okunaksız lekeye dönüşür).
LYRIC_IMAGERY = {
    "rain": ["yağmur", "yagmur"],
    "snow": ["kar ", "karlı", "karli"],
    "fog": ["sis ", "sisli", "pus"],
    "smoke": ["duman"],
    "sea": ["deniz", "dalga"],
    "harbor": ["liman", "iskele"],
    "river": ["nehir", "irmak", "dere"],
    "mountains": ["dağ", "dag"],
    "forest": ["orman", "ağaç", "agac"],
    "desert": ["çöl", "col ", "kum"],
    "clouds": ["gökyüz", "gokyuz", "bulut"],
    "stars": ["yıldız", "yildiz"],
    "moonlight": ["ay ışığ", "mehtap"],
    "sunset": ["gün batım", "gunbatim", "günbatım", "batınca"],
    "sunrise": ["şafak", "safak", "gün doğ", "seher"],
    "night": ["gece", "geceler"],
    "empty street": ["sokak", "sokağ", "cadde"],
    "city skyline": ["şehir", "sehir", "kent", "metropol"],
    "empty road": ["yol ", "yollar", "yolu", "yolun"],
    "bridge": ["köprü", "kopru"],
    "railway": ["tren", "istasyon", "ray "],
    "window": ["pencere", "cam "],
    "doorway": ["kapı", "kapi"],
    "streetlight": ["lamba", "fener", "sokak lamba"],
    "neon": ["neon"],
    "glowing light": ["ışık", "isik", "ışıklar", "aydınlık"],
    "darkness": ["karanlık", "karanlik", "gölge", "golge"],
    "tunnel": ["yeraltı", "yeralti", "tünel", "tunel"],
    "concrete wall": ["beton", "duvar"],
    "stairs": ["merdiven", "basamak"],
    "rooftop": ["çatı", "cati", "dam "],
    "empty room": ["boş oda", "bos oda", "oda "],
    "autumn leaves": ["sonbahar", "yaprak", "hazan"],
    "blossom": ["bahar", "ilkbahar"],
    "winter": ["kış", "kis "],
}

# Otomatik üretilen HER sorgunun sonuna eklenir (elle yazılmış meta.json
# "art_query"e EKLENMEZ — orada kullanıcı ne istediğini biliyor).
#
# NEDEN: Düz mekân aramaları ("neon night") Pexels'te belgesel tarzı sokak
# kareleri döndürüyor ve bunlar çoğu zaman TABELA/YAZI içeriyor — gerçek bir
# vaka: "neon night" -> üzerinde büyük Kiril harflerle "ОБМЕН ВАЛЮТ" yazan bir
# döviz bürosu tabelası. art.jpg METİNSİZ olmak ZORUNDA (blur backdrop'ta yazı
# okunaksız lekeye döner, ayrıca kapaktaki logo/başlıkla çakışıyor).
# "cinematic atmospheric" eki aramayı belgesel sokak fotoğrafından sanatsal/
# atmosferik kareye kaydırıyor — bunlarda tabela olma olasılığı belirgin
# şekilde düşük. Kesin bir garanti DEĞİL (Pexels'te "yazısız" filtresi yok,
# OCR eklemek yeni bir bağımlılık demek) — ıskalayan bir şarkıda çözüm
# meta.json'a elle "art_query" yazmak.
STYLE_SUFFIX = "cinematic atmospheric"

# Anlamlı bir sahne için en az bu kadar farklı imge bulunmalı — tek kelimelik
# bir arama ("night") jenerik sonuç veriyor, o durumda temanın kendi varsayılan
# sorgusu daha iyi.
MIN_LYRIC_MATCHES = 2
# Sözlerden EN FAZLA 2 terim alınıyor: tema atmosferiyle (art_mood) birleşince
# toplam 4-5 kelime oluyor, Pexels'te daha fazlası sonuç sayısını sıfıra
# yaklaştırıyor.
MAX_LYRIC_TERMS = 2

_TR_SLUG_MAP = str.maketrans({
    "ı": "i", "İ": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
    "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})

API_URL = "https://api.pexels.com/v1/search"
# Kart KARE (bkz. generate_cover.CANVAS_SIZE 1600x1600) ve backdrop de aynı
# görselden türüyor — "square" yönelim, scale+crop'ta en az içerik kaybı demek.
ORIENTATION = "square"
# Deterministik seçim için makul bir havuz: tek sonuç dönerse tüm arabesk
# şarkıları aynı fotoğrafı alırdı, 15 sonuç tarz içinde çeşitlilik bırakıyor.
PER_PAGE = 15
REQUEST_TIMEOUT = 20


def _load_api_key() -> str | None:
    """stock_art_config.json'dan Pexels anahtarını okur. Dosya gitignored —
    üretim makinesinde var, fresh checkout'ta olmayabilir; yoksa None."""
    if not os.path.isfile(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("pexels_api_key") or None
    except (OSError, ValueError):
        return None


def _slugify(text: str) -> str:
    """"Yürek Yarası" -> "yurek_yarasi" — sözler dosyası adlarının kuralı."""
    slug = text.translate(_TR_SLUG_MAP).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def find_lyrics_file(title: str) -> str | None:
    """Şarkı başlığından `<slug>_sozler.md` dosyasını bulur.

    Önce birebir ad denenir; bulunamazsa ön-ek eşleşmesine düşülür — proje
    klasörü ile sözler dosyası adı her zaman birebir tutmuyor (ör. "Kalbim
    Oynuyo" klasörü ile `kalbim_oynuyor_sozler.md`, klasör adında harf eksik).
    Hiçbiri tutmazsa None; çağıran taraf tema varsayılanına düşer."""
    slug = _slugify(title)
    if not slug:
        return None

    exact = os.path.join(BASE_DIR, f"{slug}_sozler.md")
    if os.path.isfile(exact):
        return exact

    candidates = sorted(glob.glob(os.path.join(BASE_DIR, "*_sozler.md")))
    by_stem = {os.path.basename(p)[: -len("_sozler.md")]: p for p in candidates}

    for stem, path in sorted(by_stem.items()):
        if stem.startswith(slug) or slug.startswith(stem):
            return path

    # Türkçe ünsüz yumuşaması ön-ek eşleşmesini bozuyor: "Beton Krallığı" ->
    # "beton_kralligi" ama dosya "beton_krallik" (k -> ğ). Harf tablosu yazmak
    # yerine benzerlik eşiği kullanılıyor — tüm yumuşama biçimlerini tek seferde
    # çözüyor. Eşik yüksek (0.85): yanlış eşleşme sadece alakasız bir arama
    # terimi üretir (çökmez), ama yine de başka bir şarkının imgelerini
    # kullanmak istemiyoruz.
    close = difflib.get_close_matches(slug, list(by_stem), n=1, cutoff=0.85)
    return by_stem[close[0]] if close else None


def keywords_from_lyrics(lyrics: str) -> list[str]:
    """Sözlerdeki somut imgeleri İngilizce Pexels terimlerine çevirip en sık
    geçen MAX_LYRIC_TERMS tanesini döner.

    Sıralama SIKLIĞA göre (şarkının merkezindeki imge en çok tekrar eder —
    genelde nakaratta), eşitlikte LYRIC_IMAGERY'deki tanım sırasına göre —
    yani sonuç tamamen deterministik, aynı sözler hep aynı terimleri verir."""
    text = lyrics.lower()
    scored = []
    for i, (term, stems) in enumerate(LYRIC_IMAGERY.items()):
        hits = sum(text.count(stem) for stem in stems)
        if hits:
            # (-sıklık, tanım sırası) -> çok geçen önce, eşitlikte sabit sıra
            scored.append((-hits, i, term))
    scored.sort()
    return [term for _, _, term in scored[:MAX_LYRIC_TERMS]]


def query_from_lyrics(title: str, theme: dict | None = None) -> str | None:
    """Şarkının sözler dosyasından bir arama sorgusu üretir (yoksa None).

    Sonuç = temanın ATMOSFER çapası + sözlerden gelen en fazla 2 mekân terimi.
    Atmosfer çapası şart: sadece sözlerden gelen terimlerle arandığında
    ("underground tunnel street road") gündüz çekilmiş, neşeli, şarkının
    duygusuyla alakasız kareler geliyordu — tarzın modu bunu düzeltiyor."""
    path = find_lyrics_file(title)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lyrics = f.read()
    except OSError:
        return None

    terms = keywords_from_lyrics(lyrics)
    if len(terms) < MIN_LYRIC_MATCHES:
        return None

    mood = ((theme or {}).get("art_mood") or "").strip()

    # Tema modu ile sözlerden gelen terimler örtüşebiliyor (elektronik modu
    # "neon night", sözlerden de "neon"+"night" çıkıyor -> "neon night neon
    # night"). Kelime bazında tekilleştir, sıra korunur.
    seen = set(mood.lower().split())
    parts = [mood] if mood else []
    for term in terms:
        kept = [w for w in term.split() if w.lower() not in seen]
        if not kept:
            continue
        seen.update(w.lower() for w in kept)
        parts.append(" ".join(kept))

    return " ".join(parts).strip() or None


def build_query(meta: dict, theme: dict, title: str = "") -> str | None:
    """Aranacak terimi seçer, öncelik sırasıyla:
      1. meta.json'daki "art_query" — o şarkıya özel, elle yazılmış (en güçlü)
      2. şarkının sözlerinden çıkarılan imgeler (bkz. query_from_lyrics)
      3. temanın varsayılan sorgusu — sözler dosyası yoksa/yetersizse
    """
    explicit = (meta.get("art_query") or "").strip()
    if explicit:
        return explicit  # elle yazılmışa dokunma, stil eki bile ekleme

    if title:
        from_lyrics = query_from_lyrics(title, theme)
        if from_lyrics:
            return f"{from_lyrics} {STYLE_SUFFIX}"

    theme_query = (theme.get("art_query") or "").strip()
    return f"{theme_query} {STYLE_SUFFIX}" if theme_query else None


def fetch_art(title: str, query: str, out_path: str) -> bool:
    """query için Pexels'ten deterministik bir fotoğraf indirip out_path'e yazar.
    Başarılıysa True, herhangi bir aksilikte (anahtar/ağ/sonuç yok) False —
    çağıran taraf False'ta prosedürel üretime düşer."""
    api_key = _load_api_key()
    if not api_key:
        return False

    try:
        resp = requests.get(
            API_URL,
            headers={"Authorization": api_key},
            params={"query": query, "orientation": ORIENTATION, "per_page": PER_PAGE},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos") or []
    except (requests.RequestException, ValueError):
        return False

    if not photos:
        return False

    # Başlıktan türeyen sabit indeks — aynı şarkı hep aynı fotoğrafı alır.
    seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
    photo = photos[seed % len(photos)]

    # "original" BİLEREK kullanılmıyor: Pexels'te 5000px+/28MB dosyalar dönüyor,
    # oysa bu görselin gideceği en büyük yer 1600x1600 art.jpg ve videoda kart
    # min(w,h)*0.45 ≈ 486px olarak çiziliyor (backdrop ise zaten ağır blur'lu).
    # large2x (~1880px) fazlasıyla yeterli, disk/render maliyeti 10-20 kat düşük.
    src_variants = photo.get("src") or {}
    src = src_variants.get("large2x") or src_variants.get("large") or src_variants.get("original")
    if not src:
        return False

    try:
        img = requests.get(src, timeout=REQUEST_TIMEOUT)
        img.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(img.content)
    except (requests.RequestException, OSError):
        # Yarım kalmış dosya bırakma — bir sonraki koşu bunu "art var" sanmasın.
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return False

    return True
