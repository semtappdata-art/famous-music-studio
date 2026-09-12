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

LİSANS: Pexels License — ücretsiz, ticari kullanıma açık, atıf zorunlu değil.
Pixabay Content License — ücretsiz ve ticari kullanıma açık, ama Pixabay
dokümantasyonu API kullanımında görselin kaynağının kullanıcıya gösterilmesini
RİCA ediyor ("we kindly request"). Zorunlu değil; kapakta atıf yeri olmadığı
için şimdilik uygulanmıyor, video açıklamasına eklenebilir.
Pixabay hız sınırı: 60 saniyede 100 istek (saatlik koşu için fazlasıyla yeterli)
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

import config
import uyumluluk

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

# Sözlerden gelen imge -> onunla DOĞRUDAN ÇELİŞEN art_mood kelimeleri.
#
# NEDEN VAR (2026-09-11, kapak denetimi): sorgu = temanın `art_mood`'u +
# sözlerden gelen 2 imge. Bu iki kaynak birbiriyle ÇELİŞEBİLİYOR ve Pexels
# çelişkiyi keyfî çözüyor. Ölçülmüş üç vaka, üçü de `pop` teması
# ("bright vibrant") + sözlerden gelen "night":
#   Gece Sürüşü     -> "bright vibrant night empty road" -> GÜNDÜZ şehir panoraması
#   Bu Gece Kazandık-> "bright vibrant night empty road" -> karanlık sisli boş yol
#   Kalbim Oynuyor  -> "bright vibrant night empty street" -> karanlık sisli sokak
# Yani aynı çelişkili sorgu bir seferinde gündüz, bir seferinde gece getiriyor;
# hangisi geleceği öngörülemiyor. Kataloğun 18 şarkısından TAM BU ÜÇÜ çelişki
# üretiyor ve gözle doğrulanan uyumsuzlukların da tamamı bu üçü.
#
# KURAL: çelişkide SÖZ terimi kazanır, çelişen MOOD KELİMESİ düşer.
# Gerekçe: söz terimi şarkının KENDİ somut kanıtıdır (sözlerde geçen mekân/
# zaman), `art_mood` ise tarzın jenerik varsayılanı. Bir şarkının sözleri
# "gece" diyorsa fotoğraf gece olmalı; temanın işi zaten rengi/enerjiyi
# taşımak (accent renkleri + kalan mood kelimeleri), günün saatini dayatmak
# değil. Tersi kural (tema kazansın) sözlük çıkarımını anlamsızlaştırırdı —
# o zaman doğrudan tema sorgusunu kullanmak gerekirdi.
#
# Atmosfer çapası TAMAMEN kaybolmuyor: yalnızca çelişen KELİME düşüyor
# ("bright vibrant" + night -> "vibrant night"), çünkü çapanın tümünü atmak
# docstring'te anlatılan eski sorunu (gündüz/neşeli/alakasız kare) geri getirir.
# Eksen bilerek DAR: sadece IŞIK/GÜNÜN SAATİ. Yanlış görselleri üreten eksen
# ölçülen buydu; "melancholy" + "blossom" gibi duygu-nesne gerilimleri
# fotoğrafta gerçek bir çelişki üretmiyor (hüzünlü bir bahar karesi olabilir).
MOOD_CELISKILERI = {
    "night": {"bright", "golden", "hour", "sunny", "daylight"},
    "darkness": {"bright", "golden", "hour", "sunny", "daylight"},
    "moonlight": {"bright", "golden", "hour", "sunny", "daylight"},
    "stars": {"bright", "golden", "hour", "sunny", "daylight"},
    "tunnel": {"bright", "golden", "hour", "sunny", "daylight"},
    "fog": {"bright", "sunny", "daylight"},
    "smoke": {"bright", "sunny", "daylight"},
    "winter": {"warm"},
    "snow": {"warm"},
    # Ters yön: tema "gece" diyor ama sözler günün AYDINLIK bir anını
    # adlandırıyor. Aynı kural, aynı gerekçe — söz terimi kazanır.
    "sunrise": {"night", "nightclub", "midnight"},
    "sunset": {"night", "nightclub", "midnight"},
    "blossom": {"night", "nightclub", "midnight"},
}


def _mood_celiskisini_coz(mood: str, terms: list[str]) -> str:
    """`art_mood`'tan, söz terimleriyle ÇELİŞEN kelimeleri çıkarır.

    Sıra korunur; hiçbir çelişki yoksa mood aynen döner (eski davranış)."""
    if not mood:
        return ""
    yasak = set()
    for term in terms:
        for kelime in term.lower().split():
            yasak |= MOOD_CELISKILERI.get(kelime, set())
    if not yasak:
        return mood
    return " ".join(w for w in mood.split() if w.lower() not in yasak)


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
PIXABAY_API_URL = "https://pixabay.com/api/"
# Pixabay yönelim değerleri: all | horizontal | vertical ("square" yok).
PIXABAY_ORIENTATION = "all"
# Kart KARE (bkz. generate_cover.CANVAS_SIZE 1600x1600) ve backdrop de aynı
# görselden türüyor — "square" yönelim, scale+crop'ta en az içerik kaybı demek.
ORIENTATION = "square"
# Deterministik seçim için makul bir havuz: tek sonuç dönerse tüm arabesk
# şarkıları aynı fotoğrafı alırdı, 15 sonuç tarz içinde çeşitlilik bırakıyor.
PER_PAGE = 15
REQUEST_TIMEOUT = 20


def _load_api_key(alan: str = "pexels_api_key") -> str | None:
    """stock_art_config.json'dan bir sağlayıcının anahtarını okur. Dosya
    gitignored — üretim makinesinde var, fresh checkout'ta olmayabilir; yoksa
    None. Alan adı parametreli: ikinci kaynak (Pixabay) aynı dosyayı kullanıyor."""
    if not os.path.isfile(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get(alan) or None
    except (OSError, ValueError):
        return None


def _secim_indeksi(title: str, n: int) -> int:
    """Başlıktan türeyen sabit indeks — aynı şarkı hep aynı fotoğrafı alır."""
    seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
    return seed % n


def _indir(src: str, out_path: str) -> bool:
    """Görseli indirip out_path'e yazar. Aksilikte yarım dosya BIRAKMAZ —
    bir sonraki koşu onu 'art var' sanıp prosedürel üretimi atlardı."""
    try:
        img = requests.get(src, timeout=REQUEST_TIMEOUT)
        img.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(img.content)
    except (requests.RequestException, OSError):
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return False
    return True


def _slugify(text: str) -> str:
    """"Yürek Yarası" -> "yurek_yarasi" — sözler dosyası adlarının kuralı."""
    slug = text.translate(_TR_SLUG_MAP).lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


# Ön-ek eşleşmesinin UZUNLUK KORUMASI (2026-09-11, altyazı denetimi).
#
# NEDEN VAR: çıplak `stem.startswith(slug) or slug.startswith(stem)` kuralının
# hiçbir uzunluk/benzerlik koruması yoktu ve BAŞKA BİR ŞARKIYI sessizce
# eşliyordu — beşi de ölçüldü:
#   "Neon" -> neon_kalp (0,615)          "Son" -> son_kez (0,600)
#   "Bu Gece" -> bu_gece_kazandik (0,609) "Sokaklar" -> sokaklar_beni_tanir (0,593)
#   "Yeraltı Kralı" -> yeralti            (ters yön: slug.startswith(stem))
# Altyazı hattı bunu KENDİ İÇİNDE kapatmıştı (`youtube_captions._sozler_dosyasi`
# ikinci kez süzüyor), ama GÖRSEL araması savunmasızdı: `query_from_lyrics`
# başka bir şarkının imgelerinden Pexels sorgusu üretir, kapak konudan
# tamamen kopar ve hiçbir yerde iz kalmaz. Bugün tetiklenmemiş olmasının tek
# sebebi şans: `neon_kalp_sozler.md` katalogda SAHİPSİZ duruyor (karşılığı
# olan proje yok), yani tuzağın yemi diskte hazır — eksik olan yalnızca
# "Neon" adlı bir şarkı.
#
# EŞİK NEDEN 0,8:
#  1. Ön-ek kuralının TEK meşru işi klasör/dosya adı arasındaki BİRKAÇ HARFLİK
#     farkı yutmak (docstring'deki "Kalbim Oynuyo" vakası: 13/14 = 0,929).
#     Fazladan bir KELİME ise her zaman en az 4 karakter ("_" + 3 harflik kök),
#     yani tipik 10-16 karakterlik bir slug'da oran 0,75'in ALTINA düşer.
#     0,8 tam olarak bu iki sınıfın arasında duruyor.
#  2. Daha sağlam olan ikinci gerekçe — aşağıdaki difflib dalıyla TUTARLILIK:
#     saf ön-ek çiftlerinde difflib oranı tam olarak 2r/(1+r)'dir (r =
#     kısa/uzun). r = 0,8 -> 0,889, yani difflib eşiğinin (0,85) ÜSTÜNDE:
#     ön-ek dalı artık difflib'in kabul ETMEYECEĞİ hiçbir şeyi kabul edemez.
#     Bu sayı aşağı çekilemez: eşik 0,739'un altına inseydi koruma İŞE
#     YARAMAZDI, çünkü ön-ek dalı reddettiğini difflib dalı zaten geçirirdi.
# ÖLÇÜLDÜ (katalogdaki 18 projenin tamamı): 17'si BİREBİR ad ile eşleşiyor,
# 18.'si "Beton Krallığı" -> `beton_krallik` ve o ön-ek DEĞİL difflib dalından
# geçiyor (0,889; ünsüz yumuşaması). Yani bu koruma doğru eşleşmelerin
# HİÇBİRİNE dokunmuyor — ön-ek dalı bugün kataloğa tek bir doğru eşleşme bile
# kazandırmıyor, sadece risk taşıyordu.
ONEK_UZUNLUK_ORANI = 0.8


def find_lyrics_file(title: str) -> str | None:
    """Şarkı başlığından `<slug>_sozler.md` dosyasını bulur.

    Önce birebir ad denenir; bulunamazsa ön-ek eşleşmesine düşülür — proje
    klasörü ile sözler dosyası adı her zaman birebir tutmuyor (ör. "Kalbim
    Oynuyo" klasörü ile `kalbim_oynuyor_sozler.md`, klasör adında harf eksik).
    Ön-ek dalı ONEK_UZUNLUK_ORANI ile korunuyor (bkz. o sabitin yanındaki not):
    korumasız hâli "Neon" başlığını `neon_kalp_sozler.md` ile eşliyordu.
    Hiçbiri tutmazsa None; çağıran taraf tema varsayılanına düşer."""
    slug = _slugify(title)
    if not slug:
        return None

    exact = os.path.join(BASE_DIR, f"{slug}_sozler.md")
    if os.path.isfile(exact):
        return exact

    candidates = sorted(glob.glob(os.path.join(BASE_DIR, "*_sozler.md")))
    by_stem = {os.path.basename(p)[: -len("_sozler.md")]: p for p in candidates}

    # Eskiden alfabetik sıradaki İLK ön-ek adayı dönüyordu; iki aday varsa
    # hangisinin geldiği tamamen dosya adına bağlıydı. Artık EN YAKIN olan
    # seçiliyor (eşitlikte sıra deterministik olsun diye `sorted`).
    onek = [(min(len(slug), len(stem)) / max(len(slug), len(stem)), path)
            for stem, path in sorted(by_stem.items())
            if stem.startswith(slug) or slug.startswith(stem)]
    onek = [(oran, path) for oran, path in onek if oran >= ONEK_UZUNLUK_ORANI]
    if onek:
        return max(onek, key=lambda t: t[0])[1]

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
    # Çelişen mood kelimelerini DÜŞÜR (bkz. MOOD_CELISKILERI): "bright vibrant"
    # + "night" -> "vibrant"; aksi hâlde Pexels çelişkiyi keyfî çözüyordu.
    mood = _mood_celiskisini_coz(mood, terms)

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


# --- Alaka eşiği ------------------------------------------------------------
#
# NEDEN VAR (2026-09-11, kapak denetimi): eskiden listeden SADECE
# `index = hash(başlık) % len(sonuclar)` ile bir kare seçiliyordu ve seçilen
# fotoğrafın sorguyla GERÇEKTEN ilgili olup olmadığına HİÇ bakılmıyordu.
# Pexels dokümantasyonu /v1/search için ne bir sıralama garantisi ne de bir
# `sort` parametresi TANIMLIYOR (doğrulandı, 2026-09-11:
# https://www.pexels.com/api/documentation/ — `sort` yalnızca /collections'ta
# var) — yani "ilk sonuçlar daha alakalıdır" bir VARSAYIM, koda dayanak olamaz.
#
# BU YÜZDEN "% min(5, n)" gibi bir DARALTMA yapılmadı; iki sebeple:
#   1. Yukarıdaki varsayım doğrulanamadı — ilk 5 daha alakalı olmayabilir.
#   2. Daraltma, düzeltmeye çalıştığımız KOPYA sorununu BÜYÜTÜYOR. Ölçüldü:
#      kataloğun 18 şarkısı içinde AYNI sorguyu üreten iki çift var; n=15'te
#      indeks çakışması YOK, n=5'te ise 'Küllerimden Geç'/'Yeniden Doğacağım'
#      çifti ikisi de indeks 1'e düşüyor — depoda gerçekten duran birebir
#      kopya (md5 dbf1fd44…) TAM OLARAK bu çakışmanın ürünü.
#
# Onun yerine havuz GENİŞ bırakılıp gerçek bir ALAKA ÖLÇÜSÜ getirildi: Pexels
# her fotoğrafla birlikte `alt` (fotoğrafın metin tarifi) alanını döndürüyor
# (aynı dokümantasyon), Pixabay ise `tags`. Sorgunun SAHNE kelimeleri bu
# tarifte geçmiyorsa o kare eleniyor. Hiçbiri geçmiyorsa (alt boş dönebilir)
# eleme TAMAMEN devre dışı kalır — bu yol otomasyonu asla durdurmamalı.
STYLE_SUFFIX_WORDS = frozenset(STYLE_SUFFIX.lower().split())


def _atmosfer_kelimeleri() -> frozenset:
    """Alaka puanlamasına KATILMAYAN kelimeler: stil eki + tüm temaların
    `art_mood` kelimeleri.

    NEDEN config'ten türetiliyor, elle yazılmıyor: `art_mood` değiştiğinde bu
    liste kendiliğinden güncellensin. Elle yazılmış bir kopya, bu depodaki
    klasik "unutulacak liste" tuzağı olurdu (bkz. CLAUDE.md).

    NEDEN dışarıda bırakılıyorlar: Pexels'in `alt` metni neredeyse her zaman
    NESNE/MEKÂN tarif eder ("an empty road at night"), ruh hâli değil —
    "melancholy"/"gritty"/"cinematic" gibi kelimeleri puanlamaya katmak her
    kareyi sıfır puana düşürür ve eşik anlamsızlaşır."""
    kelimeler = set(STYLE_SUFFIX_WORDS)
    for tema in (getattr(config, "THEMES", None) or {}).values():
        kelimeler.update(((tema or {}).get("art_mood") or "").lower().split())
    return frozenset(kelimeler)


def _sahne_kelimeleri(query: str) -> list[str]:
    """Sorgudan, alt metninde aranacak SOMUT kelimeleri süzer (sıra korunur)."""
    disari = _atmosfer_kelimeleri()
    gorulen = set()
    sonuc = []
    for kelime in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if len(kelime) < 3 or kelime in disari or kelime in gorulen:
            continue
        gorulen.add(kelime)
        sonuc.append(kelime)
    return sonuc


def _alaka_puani(tarif: str, sahne: list[str]) -> int:
    """Fotoğrafın tarifinde (Pexels `alt` / Pixabay `tags`) kaç sahne kelimesi
    geçiyor. Alt metin boşsa 0 — çağıran taraf bunu "bilinmiyor" sayar."""
    metin = (tarif or "").lower()
    return sum(1 for k in sahne if k in metin)


def _alakali_adaylar(adaylar: list[dict], query: str) -> list[dict]:
    """Alaka eşiğini geçen kareler; hiçbiri geçemezse LİSTENİN TAMAMI.

    Tam listeye düşmek bilinçli: `alt` boş gelebilir, sorgu tamamen atmosfer
    kelimelerinden oluşabilir (elle yazılmış bir `art_query`) ya da Pexels
    tarifleri sorgudan başka kelimelerle yazmış olabilir. Bu yolda eski
    davranış aynen korunur — eleme bir İYİLEŞTİRME, bir KAPI değil."""
    sahne = _sahne_kelimeleri(query)
    if not sahne:
        return adaylar
    gecen = [a for a in adaylar if _alaka_puani(a.get("tarif"), sahne) > 0]
    return gecen or adaylar


def _sirali_adaylar(title: str, query: str, adaylar: list[dict]) -> list[dict]:
    """Alaka eşiğini geçen kareleri, deterministik indeksten başlayıp SARARAK
    sıralar.

    Başlangıç noktası eskisiyle aynı mantık (`_secim_indeksi`) — yani aynı
    şarkı aynı sonuç listesinde hep aynı kareyi İLK sırada görür. Sarma, kopya
    korumasının (bkz. fetch_art) "bir sonrakini dene" adımına sabit ve
    deterministik bir sıra verir."""
    gecen = _alakali_adaylar(adaylar, query)
    if not gecen:
        return []
    bas = _secim_indeksi(title, len(gecen))
    return [gecen[(bas + i) % len(gecen)] for i in range(len(gecen))]


# --- Katalog genelinde kopya koruması ---------------------------------------
#
# NEDEN VAR: `_secim_indeksi` yalnızca BAŞLIK bazında deterministik. `art_query`
# yazılmamış, aynı temadaki iki şarkı BİREBİR aynı sorguyu üretebiliyor ve
# sonuç havuzu küçükse iki farklı hash aynı indekse düşüyor — depoda gerçekten
# oldu: 'Küllerimden Geç' ile 'Yeniden Doğacağım'ın art.jpg'si byte-birebir
# AYNI (md5 dbf1fd44…), çünkü o sorgu 5 sonuç döndürüyor ve 11 % 5 == 1 % 5.
#
# Desen `uyumluluk.py`'nin ses md5 kontrolünden alındı (aynı dosya, "Aynı ses
# başka projede var mı" bölümü): önce BOYUT ön filtresi, boyut tutarsa md5.
# Kaynak olarak `state.json` DEĞİL DİSK taranıyor — `uyumluluk.py` de öyle
# yapıyor: state.json bir İDDİA, diskteki dosya KANIT (bkz. CLAUDE.md'deki
# `youtube_playlist_id` dersi: yerel bir iddiayı kapı olarak kullanmak bir
# videoyu kalıcı olarak listesiz bırakmıştı).
# Kok listesi KOPYALANMIYOR: kanonik tanim uyumluluk.py'de. Dorduncu bir
# kok acilirsa tek yerde degisiyor (tests/test_kok_listesi_muhafizi.py
# elle yazilmis kopyalari zaten kiriyor).
ART_KOK_ADLARI = uyumluluk.KOK_ADLARI
# Mutlak yol ZORUNLU: göreli bırakılırsa yanlış cwd'de os.path.isdir False
# döner ve tarama SESSİZCE boş sonuç üretir — yani koruma kendiliğinden açılır
# (uyumluluk.KOKLER'de aynı hata gerçekten yaşandı).
ART_KOKLER = tuple(os.path.join(BASE_DIR, k) for k in ART_KOK_ADLARI)
ART_ADLARI = ("art.jpg", "art.jpeg", "art.png", "art.webp")
# Kopya çıkarsa en fazla bu kadar aday denenir. Sınır ŞART: her deneme bir
# İNDİRME demek; sınırsız döngü, tüm havuzu kopya olan bir sorguda 15 gereksiz
# indirme yapardı.
MAKS_ADAY_DENEME = 4


def _art_yolu(proje: str) -> str | None:
    for ad in ART_ADLARI:
        yol = os.path.join(proje, ad)
        if os.path.isfile(yol):
            return yol
    return None


def _md5(yol: str) -> str:
    h = hashlib.md5()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _taranacak_kokler(proje_dizini: str) -> list[str]:
    """Bilinen üç kök + (farklıysa) bu projenin KENDİ kökü.

    İkincisi hem geçici/taşınmış bir çalışma klasöründe doğru çalışmayı hem de
    testlerin üretim kataloğuna hiç dokunmadan kendi klasörlerini kurabilmesini
    sağlıyor."""
    kokler = list(ART_KOKLER)
    ust = os.path.dirname(os.path.abspath(proje_dizini))
    if ust and all(os.path.abspath(ust) != os.path.abspath(k) for k in kokler):
        kokler.append(ust)
    return kokler


def _katalogda_ayni_art_var(yol: str, proje_dizini: str) -> bool:
    """İndirilen görselin birebir aynısı BAŞKA bir projede duruyor mu.

    Herhangi bir okuma hatasında False — bu bir KAPI değil, bir iyileştirme;
    okunamayan bir dosya yüzünden kapak üretimini durdurmak yanlış olurdu."""
    try:
        boyut = os.path.getsize(yol)
    except OSError:
        return False

    adaylar = []
    for kok in _taranacak_kokler(proje_dizini):
        if not os.path.isdir(kok):
            continue
        try:
            icerik = os.listdir(kok)
        except OSError:
            continue
        for ad in icerik:
            bp = os.path.join(kok, ad)
            if os.path.abspath(bp) == os.path.abspath(proje_dizini):
                continue
            baska = _art_yolu(bp)
            if not baska:
                continue
            try:
                if os.path.getsize(baska) != boyut:
                    continue      # boyut farklıysa md5 hesaplama (ön filtre)
            except OSError:
                continue
            adaylar.append(baska)

    if not adaylar:
        return False
    try:
        benim = _md5(yol)
    except OSError:
        return False
    for baska in adaylar:
        try:
            if _md5(baska) == benim:
                return True
        except OSError:
            continue
    return False


def _pexels_adaylari(query: str) -> list[dict]:
    """Birinci kaynak. Her aday: {"src": indirme adresi, "tarif": alt metni}.
    Herhangi bir aksilikte (anahtar/ağ/sonuç yok) BOŞ liste."""
    api_key = _load_api_key()
    if not api_key:
        return []

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
        return []

    adaylar = []
    for photo in photos:
        # "original" BİLEREK kullanılmıyor: Pexels'te 5000px+/28MB dosyalar
        # dönüyor, oysa bu görselin gideceği en büyük yer 1600x1600 art.jpg ve
        # videoda kart min(w,h)*0.45 ≈ 486px olarak çiziliyor (backdrop ise
        # zaten ağır blur'lu). large2x fazlasıyla yeterli, disk/render maliyeti
        # 10-20 kat düşük.
        src_variants = (photo or {}).get("src") or {}
        src = (src_variants.get("large2x") or src_variants.get("large")
               or src_variants.get("original"))
        if src:
            adaylar.append({"src": src, "tarif": (photo or {}).get("alt") or ""})
    return adaylar


def _pixabay_adaylari(query: str) -> list[dict]:
    """İkinci kaynak — Pexels sonuç vermediğinde denenir.

    Anahtar yoksa SESSİZCE boş liste: bu yol isteğe bağlı, kurulmamış bir
    makinede davranış eskisiyle birebir aynı kalır (doğrudan prosedürel bokeh).

    Pixabay'de "square" yönelimi YOK (yalnızca all/horizontal/vertical), bu
    yüzden "all" isteniyor ve kırpma generate_cover'a bırakılıyor. Pexels'te
    square istenmesinin sebebi kırpma kaybını azaltmaktı; burada o garanti
    edilemiyor — yine de bokeh'e düşmekten iyi.

    Alaka ölçüsü olarak `tags` kullanılıyor (Pixabay'in `alt` karşılığı yok;
    `tags` virgülle ayrılmış anahtar kelimeler)."""
    api_key = _load_api_key("pixabay_api_key")
    if not api_key:
        return []

    try:
        resp = requests.get(
            PIXABAY_API_URL,
            params={
                "key": api_key,
                "q": query,
                "image_type": "photo",
                "orientation": PIXABAY_ORIENTATION,
                "per_page": PER_PAGE,
                "safesearch": "true",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits") or []
    except (requests.RequestException, ValueError):
        return []

    adaylar = []
    for hit in hits:
        # largeImageURL ~1280px; kart 1600x1600'e ölçekleniyor ama videoda
        # min(w,h)*0.45 ≈ 486px çiziliyor, backdrop zaten ağır blur'lu.
        src = (hit or {}).get("largeImageURL") or (hit or {}).get("webformatURL")
        if src:
            adaylar.append({"src": src, "tarif": (hit or {}).get("tags") or ""})
    return adaylar


def fetch_art(title: str, query: str, out_path: str) -> bool:
    """query için deterministik bir fotoğraf indirip out_path'e yazar.

    Önce Pexels, sonuç yoksa Pixabay. İkisi de veremezse False — çağıran taraf
    False'ta prosedürel bokeh üretimine düşer.

    İkinci kaynak 2026-09-10'da eklendi: tek kaynakta arama boş dönünce kapak
    doğrudan bokeh'e düşüyordu ve bu, gerçek fotoğraf isteğinin karşılanmadığı
    tek yerdi. Sıra sabit (önce Pexels): mevcut kapakların yeniden üretiminde
    aynı görsel çıksın, arşiv değişmesin.

    İKİ SÜZGEÇ (2026-09-11): (1) alaka eşiği — sorgunun sahne kelimeleri
    fotoğrafın tarifinde geçmiyorsa aday elenir; (2) kopya koruması —
    indirilen kare kataloğun başka bir projesinde BİREBİR duruyorsa bir
    sonraki aday denenir. İkisi de bir KAPI değil: eşiği hiçbir aday geçemezse
    liste olduğu gibi kullanılır, tüm adaylar kopya çıkarsa en sondaki indirme
    silinir ve False dönülür (yani prosedürel bokeh) — otomasyon HİÇBİR
    durumda bu yüzden durmaz.

    GERİYE DÖNÜK ETKİSİ YOK: `generate_cover.generate()` bir `art.*` dosyası
    VARSA `fetch_art`'a hiç gelmiyor (`existing_art` dalı) ve `art_path`'e
    yazan satır `if not has_art:` ile korunuyor. Yani mevcut kapaklar yeniden
    üretilmiyor; buradaki değişiklik yalnızca YENİ projeleri etkiler.
    """
    proje_dizini = os.path.dirname(os.path.abspath(out_path))
    indirildi = False
    for adaylari_getir in (_pexels_adaylari, _pixabay_adaylari):
        adaylar = adaylari_getir(query)
        if not adaylar:
            continue
        for aday in _sirali_adaylar(title, query, adaylar)[:MAKS_ADAY_DENEME]:
            if not _indir(aday["src"], out_path):
                continue
            indirildi = True
            if _katalogda_ayni_art_var(out_path, proje_dizini):
                continue          # katalogda zaten var — bir sonraki adayı dene
            return True

    # Buraya gelindiyse ya hiç aday indirilemedi ya da indirilenlerin HEPSİ
    # kopyaydı. İkinci durumda diskte kopya bir dosya kalırdı ve çağıran taraf
    # False dönüşüne rağmen onu "art var" sanabilirdi — temizle.
    if indirildi and os.path.isfile(out_path):
        try:
            os.remove(out_path)
        except OSError:
            pass
    return False
