"""Render ayarları — tüm görünüm/kalite parametreleri burada."""

import os
from datetime import datetime, timedelta, timezone

FPS = 30

# platform_key -> (genişlik, yükseklik, çıktı dosya adı)
# NOT: "square_1x1" (1080x1080) daha önce burada vardı ama hiçbir upload script'i
# onu kullanmıyordu — her render'da boşuna üretiliyordu, kaldırıldı.
PLATFORMS = {
    "youtube_16x9": (1920, 1080),
    "shorts_9x16": (1080, 1920),
}

# Bu platformlar şarkının TAMAMI yerine, audio_highlight.find_highlight() ile
# bulunan en enerjik/yoğun bölümden kırpılır (viral kısa video için) —
# meta.json'da "highlight_start"/"highlight_end" (saniye) belirtilirse onlar
# öncelikli kullanılır, otomatik tespit devreye girmez.
HIGHLIGHT_PLATFORMS = {"shorts_9x16"}
HIGHLIGHT_DURATION = 45.0  # saniye — YouTube Shorts/TikTok/Reels limitinin (180s) çok altında

# Aynı anda kaç platform paralel render edilsin (varsayılan: hepsi birden)
MAX_PARALLEL_RENDERS = len(PLATFORMS)

# Müzik türüne göre renk paletleri — her şarkı meta.json'da "theme" ile birini seçer.
# accent: art.jpg yoksa (ensure_vignette fallback) kullanılan tema rengi. accent2: şu an
# kodda hiç KULLANILMIYOR (eski, artık var olmayan bir çerçeve/gradyan tasarımından
# kalma ölü veri) — kaldırılmadı ama render'ı fiilen etkilemiyor.
# "language": paylaşım metinlerinin (caption/hashtag/YouTube yorumu, bkz.
# social_text.resolve_language) hangi dilde üretileceğinin STİLE göre
# varsayılanı — kullanıcı isteği: Suno'da üretilen müziğin stiline göre dil
# hazırlığı otomatik olsun, her projede elle "language" yazmaya gerek kalmasın.
# meta.json'da açık bir "language" varsa o öncelikli (istisna/override için).
# Ana katalog (6 tarz) tamamen Türkiye pazarına göre kurulu, "tr" — "dj" (DJ
# Famous, bkz. dj_sets/README.md) markanın global açılımının ilk denemesi
# olarak "en" (kullanıcı kararı, 2026-09-03).
#
# "art_query": art.jpg elle sağlanmadığında stock_art.py'nin Pexels'te arayacağı
# VARSAYILAN terimler — şarkının tarzına uygun, gerçek bir mekân/atmosfer
# fotoğrafı gelsin diye (kullanıcı isteği: kapak görseli müzik tarzını ve
# sözlerin çağrıştırdığı mekânı anımsatsın, düz prosedürel gradyan yerine).
# Şarkıya ÖZEL bir sahne isteniyorsa meta.json'a "art_query" yazılır, o öncelikli
# olur — bu alan sadece hiçbir şey yazılmadığındaki tarz-bazlı taban.
# Sorgular İNGİLİZCE: Pexels'in etiket/arama dizini ezici çoğunlukla İngilizce,
# Türkçe terimler ("yağmurlu pencere") çok az/alakasız sonuç döndürüyor.
THEMES = {
    "pop": {"label": "Pop", "related": ["R&B", "Trap"], "accent": (255, 60, 140), "accent2": (80, 120, 255), "language": "tr", "art_mood": "bright vibrant", "art_query": "vibrant sunset city skyline pastel sky"},
    "rock": {"label": "Rock", "related": ["Alternative", "Punk"], "accent": (230, 35, 35), "accent2": (255, 170, 40), "language": "tr", "art_mood": "dark dramatic moody", "art_query": "dramatic stormy sky dark mountains"},
    "elektronik": {"label": "Elektronik", "related": ["Synthwave", "House"], "accent": (60, 220, 255), "accent2": (170, 60, 255), "language": "tr", "art_mood": "neon night", "art_query": "neon city night lights reflection"},
    "akustik": {"label": "Akustik", "related": ["Folk", "Indie"], "accent": (230, 150, 60), "accent2": (255, 90, 140), "language": "tr", "art_mood": "warm golden hour", "art_query": "warm golden hour forest sunlight"},
    "hiphop": {"label": "Hip-Hop", "related": ["Trap", "Rap"], "accent": (255, 195, 60), "accent2": (255, 90, 40), "language": "tr", "art_mood": "gritty urban night", "art_query": "urban street night city concrete"},
    "arabesk": {"label": "Arabesk", "related": ["Trap", "Türkçe Rap"], "accent": (200, 40, 90), "accent2": (255, 140, 60), "language": "tr", "art_mood": "melancholy moody rainy", "art_query": "rainy window night melancholy blur"},
    # Ana kataloğun 6 tarzından AYRI — haftalık DJ Famous setleri için (bkz.
    # dj_sets/README.md). Kataloğun 6-slotlu tema çeşitlilik takibine dahil değil.
    "dj": {"label": "DJ Set", "related": ["Mix", "Live Set"], "accent": (255, 210, 60), "accent2": (255, 60, 140), "language": "en", "art_mood": "nightclub stage lights", "art_query": "nightclub crowd stage lights"},
}
DEFAULT_THEME = "hiphop"  # meta.json'da "theme" belirtilmezse kullanılır

# --- Kart tasarımı: Spotify "Now Playing" stili — tam ekran değil, ekranın büyük
# kısmını kaplayan ("orta alan") yuvarlak köşeli albüm kartı + kartın kendi görselinden
# (art.jpg) türetilmiş, hareketli (pan+hue) bir backdrop + altında kayan başlık +
# ilerleme çubuğu. Çerçeve/glow YOK (eski bir tasarımda vardı, kaldırıldı).
# Kart statik durur (zoom yok) — bu yüzden eski tam ekran/zoom/waveform tasarımına
# göre çok daha az render maliyeti var.
CARD_SIZE_RATIO = 0.45  # min(genişlik,yükseklik)'e oran — büyütüldü, daha belirgin görünüm
CARD_CORNER_RATIO = 0.08  # kart boyutuna oran, köşe yuvarlaklığı
CARD_ASSET_REF_SIZE = 800  # maske asset üretim çözünürlüğü (render'da ölçeklenir)
CARD_MASK_ASSET_PATH = "assets/card_mask.png"

# Kart içeriği: "Famous Music Studio" logosu SADECE platform thumbnail'inde (cover.jpg)
# kullanılıyor, video içindeki kartta GÖSTERİLMİYOR. Kart içeriği artık ESNEK —
# proje klasöründe art.jpg/.jpeg/.png varsa o kullanılır (kare kırpılıp yerleştirilir),
# yoksa düz renkle dolduruluyor (aşağıdaki renk, "sabit koda" fallback).
CARD_ART_COLOR = "0x151515"

# Arka plan: ortada hafif aydınlık (merkez falloff, accent tonunda) + asimetrik bokeh blob
# (complementary cool-blue tonunda) → dramatik derinlik, card "floating" hissi.
BG_CENTER_BRIGHTNESS = 28  # merkezdeki radial falloff parlaklığı (0-255) — düşürüldü, arka plan daha derin/karanlık
# BG_BOKEH_POS/RADIUS_RATIO/BRIGHTNESS/COLOR KALDIRILDI (2026-09-11): dördü de
# hiçbir yerden okunmuyordu — ensure_vignette() bokeh blob'unun konumunu/
# yarıçapını/parlaklığını/rengini kendi içinde sabit kodluyor, bu sabitler eski
# bir tasarımdan kalmaydı. (BG_CENTER_BRIGHTNESS yukarıda DURUYOR: o gerçekten
# okunuyor, bkz. ffmpeg_utils.py:154.)

# Arka plan artık statik değil, video boyunca yavaşça kayıyor (pan): kaynak görsel
# hedef çözünürlükten biraz büyük üretiliyor, render sırasında crop x/y zamanla
# (sin/cos ile) kayıyor. Zoom YOK — crop neredeyse ücretsiz ama her karede yeniden
# ölçekleme (scale/zoom) render'ı ciddi yavaşlatırdı.
BACKDROP_PAN_MARGIN_RATIO = 0.14  # arka planın hedef boyuttan ne kadar büyük üretileceği
BACKDROP_PAN_SPEED_X = 0.05  # radyan/saniye, x ekseni salınım hızı
BACKDROP_PAN_SPEED_Y = 0.035  # radyan/saniye, y ekseni — x'ten farklı, tekrarsız/organik desen için

# Renk akışı: pan'a ek olarak backdrop'un hue'su zamanla yumuşakça salınıyor.
# Tam 360° dönmüyor (dar bir açı aralığında ileri-geri akıyor) — şarkının kendi
# tema renginden (art.jpg'nin rengi) çok uzaklaşmasın, yine de gözle görülür bir
# "renk akışı" hissi olsun diye.
BACKDROP_HUE_AMPLITUDE_DEG = 35  # salınımın genliği (derece) — 0 = orijinal renk, +/- bu kadar kayar
BACKDROP_HUE_SPEED = 0.025  # radyan/saniye

# EQ bars (sese duyarlı çubuklar) kaldırıldı — kullanıcı beğenmedi, kaldırıldı.
# BAR_THICKNESS_RATIO hâlâ layout boşluğu (kart altı/text arası) için kullanılıyor.
EQ_BAR_THICKNESS_RATIO = 0.15  # kart boyutuna oran, layout spacing için

MARQUEE_GAP_RATIO = 0.02  # kartın altı ile kayan yazı arası (yüksekliğe oran)
# Pillow gibi ek bir bağımlılık eklemeden (proje bilinçli olarak sadece stdlib +
# ffmpeg kullanıyor) "Famous Music Studio" yazısının piksel genişliğini kabaca tahmin
# etmek için ortalama karakter genişliği oranı (Segoe UI, orantılı sans-serif font).
FONT_CHAR_WIDTH_RATIO = 0.55

# --- AÇILIŞ (ilk saniyeler) ---
# NEDEN (2026-09-11, olcum_temel_cizgi.json / kitle_tutma_28gun ölçümü):
# 8 uzun videonun kitle tutma eğrisinde kaybın TAMAMI başta toplanıyor —
# videonun %1'inden %3'üne (yani ~2. saniyeden ~6,5. saniyeye) ortalama 25
# puan, oradan %10'a kadar (~22. saniye) sadece ~12 puan daha. Yani sorun
# "düzgün azalma" değil, 2.-7. saniyede bir uçurum.
# O saniyelerde ekranda ÖLÇÜLEN değişim (kare(0) ile kare(11) arası ortalama
# mutlak fark, 0-255 gri): 7,3-8,6 — yani ~%3. Pratikte donmuş bir kare.
# Üstelik ilk karede şarkı adı HİÇBİR YERDE yazmıyor (kayan künye yazısı
# t=0'da şeridin sağ dışında başlıyor) ve kadraj, tıklanan küçük resimle
# uyuşmuyor: küçük resim tam ekran fotoğraf + büyük başlık, video ise aynı
# fotoğrafın ekranın ~%24'ünü kaplayan küçültülmüş kart hâli.
# ÇÖZÜM: video projenin KENDİ cover.png'siyle (birebir YouTube küçük resmi)
# tam ekran açılıyor, kısa bir bekleme sonrası karta çözülüyor (cross-dissolve).
# Tek değişiklikle üç açık birden kapanıyor: tıklama sürekliliği, ilk karede
# başlık, ve tam uçurumun olduğu saniyelerde gerçek hareket.
INTRO_KAPAK = True
INTRO_KAPAK_BEKLEME = 0.9   # kapak tam ekran sabit kalma süresi (sn)
INTRO_KAPAK_COZULME = 1.5   # karta çözülme süresi (sn) — bitiş: bekleme+çözülme
# Sadece uzun formatta. Shorts akışında küçük resim izleyiciye HİÇ gösterilmiyor
# (bkz. buyume_analizi.md Bulgu 3), yani orada tıklama sürekliliği diye bir şey
# yok; 45 saniyelik bir kesitte 2,4 saniyeyi kapak ekranına vermek ise net kayıp.
INTRO_KAPAK_PLATFORMLAR = {"youtube_16x9"}

# Suno çıktıları başta dijital sessizlikle geliyor — 18 projede ölçüldü:
# 0,15 sn ile 2,65 sn arası, medyan ~1,1 sn (-99 dB, yani mutlak sessizlik).
# O sürede izleyici ne ses duyuyor ne hareket görüyor. Kırpılıyor.
# DÜRÜST NOT: sessizlik süresi ile açılış tutması arasında ÖLÇÜLEBİLİR bir
# ilişki YOK (n=8, Sessiz Mektup en kısa sessizliğe sahip ve en kötü üçte;
# sıra korelasyonu ~0). Yani bu, veriyle kanıtlanmış bir düzeltme değil —
# "hiçbir şey olmayan saniyeyi at" mantığıyla yapılmış ucuz bir temizlik.
# Kapatmak için: INTRO_SESSIZLIK_KIRP = False.
INTRO_SESSIZLIK_KIRP = True
INTRO_SESSIZLIK_ESIGI = "-50dB"  # silencedetect eşiği
INTRO_SESSIZLIK_PAY = 0.12       # atağın başı kesilmesin diye bırakılan pay (sn)
INTRO_SESSIZLIK_MAKS = 3.0       # güvenlik tavanı: tespit bozulsa bile şarkıdan
                                 # bundan fazlası ASLA kırpılmaz (sn)

PROGRESS_BAR_HEIGHT_RATIO = 0.008  # yüksekliğe oran — kalınlaştırıldı, görünürlük için
PROGRESS_BAR_MARGIN_RATIO = 0.08  # kenarlardan içeri, genişliğe oran
PROGRESS_BAR_BOTTOM_RATIO = 0.05  # alttan yukarı, yüksekliğe oran
PROGRESS_BAR_FILLED = 235  # dolu kısım parlaklığı (0-255)
PROGRESS_BAR_EMPTY = 70  # boş kısım parlaklığı (0-255)

# Başlık metni (meta.json'da "title" varsa kullanılır) — kayan, künye/jenerik tarzı
# küçük ve göze batmayan bir yazı (büyük/kalın başlık değil).
def _find_font_path() -> str:
    """İşletim sistemine göre ilk bulunan sistem fontunu döndürür — proje Windows,
    macOS ve Linux'ta çalışabilsin diye (tek sabit Windows yolu yerine). Segoe UI
    (Windows) tercih edilir, bulunamazsa her platformda yaygın bir sans-serif
    alternatife düşülür. Hiçbiri yoksa render.py başlarken açık hata versin diye
    RuntimeError fırlatılır (drawtext sessizce hatalı/eksik yazı üretmesin diye)."""
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise RuntimeError(
        "Sistemde uygun bir font bulunamadı (denenen yollar: "
        + ", ".join(candidates)
        + "). config.FONT_PATH'i elle bir .ttf/.ttc dosyasına ayarlayın."
    )


def _find_bold_font_path() -> str:
    """Kalın font varyantı — sadece cover.png başlığı için (künye yazısı normal
    kalınlıkta kalıyor). Bulunamazsa hata vermez, FONT_PATH'e (normal ağırlık)
    düşer — kalın font kozmetik bir tercih, zorunlu değil."""
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return FONT_PATH


FONT_PATH = _find_font_path()
FONT_BOLD_PATH = _find_bold_font_path()


def _find_logo_path() -> str | None:
    """Famous Music Studio amblemi (altın sunburst + wordmark, düz siyah zemin
    üzerinde) — cover.png'de metin marka satırı yerine kullanılır. Gitignored
    (upload/assets/*.png, assets/*.png) — üretim makinesinde elle konmuş
    olabilir ama fresh checkout'ta YOK olabilir, bu yüzden bulunamazsa None
    döner ve generate_cover.py sessizce düz metin satırına düşer (hata vermez)."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload", "assets", "famous_music_studio_logo_v2.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "assets", "logo.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


LOGO_PATH = _find_logo_path()
FONT_SIZE_RATIO = 0.032  # video yüksekliğine oran — büyütüldü, okunurluk için
FONT_COLOR = "white@0.95"
# Yazi golgesi - SADECE video arka planli render'da (DJ setleri).
# Sabit gorsel arka plan koyu oldugu icin orada golgeye gerek yok.
FONT_SHADOW_COLOR = "black@0.55"
FONT_SHADOW_OFFSET = 2  # künye yazısı net okunsun diye yüksek opaklık
MARQUEE_SEPARATOR = "  •  "
MARQUEE_REPEAT = 6  # metnin geniş ekranlarda da kesintisiz görünmesi için tekrar sayısı
MARQUEE_SPEED_PX_S = 60

# Kayan künye yazısının altında duran SABİT (kaymayan) marka satırı — künye yazısıyla
# AYNI font ve AYNI düz beyaz renk (STATIC_LABEL_FONT_RATIO sadece boyut farkı için).
STATIC_LABEL_TEXT = "Famous Music Studio"
STATIC_LABEL_FONT_RATIO = 0.85  # ana font boyutuna oran — biraz daha küçük
STATIC_LABEL_GAP_RATIO = 0.01  # kayan yazı ile arasındaki boşluk (yüksekliğe oran)

# Paylaşım metinleri (YouTube açıklaması, sosyal medya caption şablonları) için
# tek merkezi marka bilgisi — upload/youtube_upload.py ve ileride
# instagram_upload.py/tiktok_upload.py bu değerleri kullanır.
SOCIAL_LINKS = {
    "instagram": "https://instagram.com/famous_music_studio",
    "tiktok": "https://www.tiktok.com/@famousmusicstudio",
    "website": "https://famousmusicstudio.com",
}

# YouTube kanal handle'ı (@ işaretsiz) — DJ Famous açıklama şablonunda
# "Subscribe ... 👉 @handle" satırı için (bkz. youtube_upload.build_snippet).
YOUTUBE_HANDLE = "Famous_musics_studio"

# @mention handle'ları (SOCIAL_LINKS'teki URL'lerden AYRI tutuluyor) —
# Instagram/TikTok'ta düz metin linkler caption/yorumda TIKLANAMIYOR ama
# "@handle" bir hesabı gerçekten ETİKETLİYORSA (mention) tıklanabilir oluyor
# ve doğrudan o profile açılıyor (WebSearch ile doğrulandı, 2026-09-05) — bkz.
# social_text.build_youtube_comment(). Bu, düz URL'den FARKLI bir mekanizma.
SOCIAL_HANDLES = {
    "instagram": "famous_music_studio",
    "tiktok": "famousmusicstudio",
}
# NOT: "#AIMusic"/"#YapayZekaMüzik"/"#AIMusicChallenge"/"#SunoAI" gibi AI-vurgulu
# ibareler BİLİNÇLİ olarak burada YOK — kullanıcı kuralı: ürettiğimiz hiçbir
# içerikte (caption, YouTube tag, video içi kayan yazı) bu ibareler kullanılmasın.
# AI-üretimi olduğunun ZORUNLU bildirimi (platform politikası gereği) bundan AYRI
# ve hâlâ yerinde: YouTube'da containsSyntheticMedia API bayrağı
# (youtube_upload.py), TikTok'ta uygulama içi "AI-generated content" etiketi
# hatırlatması (tiktok_upload.py), Instagram'da caption'a eklenen tek satır
# (social_text.build_ai_disclosure_line, sadece DJ Famous'ta) — bunlar hashtag/
# marka etiketi değil, gerçek zorunlu bildirim mekanizmaları, dokunulmadı.
BRAND_HASHTAGS = ["#FamousMusicStudio"]

# Keşfet/For You dağıtımını hedefleyen genel hashtag'ler — marka hashtag'lerinden
# ayrı tutuluyor çünkü bunlar zamanla değişebilir (trend_hashtag_notlari.md'ye bak).
# 2026-09-10: sabit üçlü yerine HAVUZ. Sebep: her paylaşımda birebir aynı
# hashtag setini tekrarlamak tekdüzelik sinyali; ayrıca caption'ın yarısı zaten
# sabitti. build_caption() bu havuzdan şarkıya göre deterministik 3 tane seçer —
# aynı şarkı hep aynı seti alır (arşiv tutarlılığı), şarkılar arası çeşitlenir.
# AI-vurgulu hashtag KOYMA (bkz. yukarıdaki not, kullanıcı kararı 2026-09-05).
DISCOVERY_HASHTAGS = [
    "#keşfet", "#fyp", "#viral", "#keşfetteyiz", "#müzik",
    "#şarkı", "#yenişarkı", "#türkçemüzik", "#foryou",
]
DISCOVERY_HASHTAG_COUNT = 3

# Caption'ın ilk satırı — kaydırmayı durdurmak için merak uyandıran kısa açılış cümlesi.
# build_caption() şarkı başlığına göre bunlardan birini deterministik seçer (her şarkı
# için hep aynı hook, ama şarkılar arası çeşitlilik olur).
# NOT: burada BİLİNÇLİ olarak "yapay zeka/AI ile yapıldı" gibi görünür bir vurgu YOK
# (kullanıcı kararı, 2026-09-05) — bu içerik hook/etkileşim amaçlı, ZORUNLU bir
# bildirim değil; zorunlu AI-üretimi bildirimi bundan tamamen ayrı ve hâlâ yerinde
# (YouTube containsSyntheticMedia bayrağı, TikTok uygulama-içi etiket hatırlatması,
# Instagram'da SADECE DJ Famous için build_ai_disclosure_line — hiçbiri buradaki
# hook/soru metinlerine bağlı değil, dokunulmadı).
HOOK_LINES = [
    "Bunu ilk sen keşfet 👀🎶",
    "Kulaklığı tak, bu şarkı tam sana göre 🎧",
    "Yeni parça, yeni hikaye 🎵",
    "Bu şarkıyı bitirmeden geçme 👇",
    "İlk on saniye yeter, anlarsın 🎧",
    "Sesi aç, gerisi kendiliğinden gelir 🔊",
    "Bu akşamın şarkısı belli oldu 🌙",
    "Bir dinle, aklından çıkmasın 🎶",
    "Kaydırıp geçme, dönüp geleceksin 👀",
    "Bu ritim seni yakalar 🔥",
    "Yeni parça yayında 🎵",
    "Sessiz izleme, ses şart 🔊",
    "Bunu listene ekleyeceksin, şimdiden söyleyeyim 📲",
    "Bu şarkı gece dinlenir 🌃",
]

# Caption'ın orta bölümü de artık sabit değil (2026-09-10). Önceden
# "Bu sesi edit/kesit videolarında kullanabilirsin 🔥" ve "Yeni şarkılar için
# takipte kalın" satırları HER paylaşımda birebir aynıydı; caption'ın yarısı
# şarkıdan bağımsız tekrar ediyordu.
USE_LINES = [
    "Bu sesi edit/kesit videolarında kullanabilirsin 🔥",
    "Edit'lerinde bu sesi rahatça kullan 🔥",
    "Kesitlerinde kullanmak serbest 🎬",
    "Bu ses senin videolarında da güzel durur 🔥",
    "İstersen edit'ine ekle, sorun değil 🎬",
    "Videolarında kullanmak istersen buyur 🔥",
    "Bu parçayı edit'lerde duymak isterim 🎬",
    "Kesit yaparsan bu ses tam oturur 🔥",
]

FOLLOW_LINES = [
    "Yeni şarkılar için takipte kalın",
    "Yeni parçalar için takip et 🎵",
    "Her hafta yeni şarkı — takipte kal",
    "Devamı gelecek, takipte kal 🎶",
    "Yeni işler için takip etmeyi unutma",
    "Takip et, yenileri kaçırma 🎧",
    "Daha fazlası için takipteyiz 🎵",
    "Sıradaki parça için takipte kal 🔔",
]

# Caption'ın sonunda, hashtag'lerden hemen önce — yorum sayısını artırmayı
# hedefleyen bir soru (yorum, algoritma için güçlü bir etkileşim sinyali).
# HOOK_LINES ile aynı deterministik seçim mantığı ama farklı bir index kullanılır
# (bkz. social_text._pick_hook) — aynı şarkıda hep aynı ikili tekrarlanmasın diye.
ENGAGEMENT_QUESTIONS = [
    "Yorumda hangi türü bir sonraki duymak istersin? 👇",
    "Bu şarkı sana neyi hatırlattı, yorumda yaz 💬",
    "1'den 10'a kadar puanla 👇",
    "Bu şarkıyı kaç kez tekrar dinlersin? Yorumda söyle 🔁",
    "Hangi kısmı tekrar tekrar dinledin? 👇",
    "Bu şarkı hangi anını hatırlattı? 💬",
    "Bunu kime dinletirsin, etiketle 👇",
    "Sözler mi ritim mi? Yorumda söyle 💬",
    "Kaç saniyede kaptırdın kendini? ⏱️",
    "Buna başka bir isim verseydin ne olurdu? 💭",
    "Nakarat mı giriş mi daha iyi? 👇",
    "Bunu listene ekler misin? 📲",
    "Bu şarkı hangi saatte dinlenir? 🌙",
    "Hangi tarzı daha çok yakıştırdın? 🎧",
]

# DJ setlerinde arka planı stok videodan kurmak (bkz. stock_video.py).
# YALNIZCA dj_sets/ için ve yalnızca uzun formatta (16x9) uygulanıyor:
# 4 dakikalık bir şarkıda tek görsel sorun değil, 80 dakikalık bir sette
# hiç değişmeyen bir kare izleyiciyi kaçırıyor. Kapatılırsa setler eski
# bulanık art.jpg arka planına döner — hiçbir şey bozulmaz.
DJ_ARKA_PLAN_VIDEO = True

# DJ setlerinde sci-fi HUD kaplaması (bkz. dj_hud.py). Arka plan videosuyla
# aynı kapsam: YALNIZCA dj_sets/ ve yalnızca uzun formatta. Dikey 45 saniyelik
# kesitte köşe ayraçları kadrajı daraltıyor, orada kapalı.
DJ_HUD = True

# SAHNE MODU: arka plan artık kartın ARKASINDAKİ dekor değil, kadrajın
# KENDİSİ. Kart kaldırılıyor, görüntü bulanıklaştırılmıyor, HUD onu
# çerçeveliyor - referanstaki ("NOXELUNE HOUSE") düzenin mantığı bu.
#
# Neden ayrı bir mod: mevcut tasarım arka planı BİLEREK bulanık ve koyu
# tutuyor ki ortadaki kart öne çıksın. Aynı kareye hem kart hem net bir
# sahne koymak ikisini de zayıflatıyor - biri diğerini boğuyor. Bu yüzden
# ikisi ayrı düzen, aynı anda açılmıyor.
DJ_SAHNE_MODU = True


# --- DJ setlerinde yayin oncesi Content ID taramasi ----------------------
# NEDEN: City Pulse Set (4 Eylul 2026) yayinlandiktan SONRA telif itirazi aldi
# - Suno ciktisi "Bring Me To Life (Tiesto, FORS)" ile eslesti, 4 ayri yerde
# toplam 106 saniye. Sonuc: para kazanma kapali + 2 ulkede engelli. O anda
# icerik zaten 6 platformdaydi.
#
# YouTube Content ID taramasini videonun gizlilik ayarindan BAGIMSIZ yapiyor.
# Bu yuzden set once `private` yukleniyor, tarama otursun diye bekleniyor,
# temizse herkese aciliyor ve diger platformlara ancak o zaman gidiyor.
#
# Yalnizca dj_sets/ icin. Ana katalog (gunde 2 sarki, 4 dakikalik tek parca)
# degismiyor - risk profili farkli ve gunluk akisi 2 saat geciktirmek boru
# hattini gereksiz karmasiklastirir.
DJ_ON_TARAMA = True

# Taramanin oturmasi icin beklenecek sure. YouTube genelde 1 saat icinde
# tamamliyor; 2 saat rahat bir pay.
DJ_TARAMA_BEKLEME_SN = 2 * 60 * 60

# Sahne modunda blur neredeyse sıfır: görüntünün kendisi gösteriliyor.
# Tamamen 0 değil - hafif bir yumuşatma stok kliplerin sıkıştırma
# gürültüsünü bastırıyor ve üstteki yazıları okunur tutuyor.
DJ_SAHNE_BLUR_SIGMA = 1.5
DJ_SAHNE_EGRISI = "0/0.02 0.5/0.46 1/0.92"

# Video arka plan, kartın ARKASINDA durmalı — ham stok klip fazla dikkat çekiyor
# ve koyu art.jpg kartı yutuyordu (ilk denemede kart neredeyse görünmez oldu).
# Sabit görsel arka planla (ensure_art_backdrop) aynı mantık uygulanıyor:
# bulanıklaştır + siyahları kaldır, böylece kart ve yazılar öne çıkıyor.
# Blur sabit görseldekinden (sigma ~48) çok daha HAFİF — hareketin okunması,
# yani videonun video olduğunun anlaşılması gerekiyor.
DJ_ARKA_PLAN_BLUR_SIGMA = 14
# Sabit gorsel arka plandaki (ffmpeg_utils.ensure_art_backdrop) ile AYNI
# islem: pozitif parlaklik + siyahlari kaldiran egri. Ilk denemede daha
# zayif bir egri kullanilmisti (0/0.10 0.5/0.62) ve koyu kliplerde -- duman,
# gece govdesi -- arka plan neredeyse siyaha cokup karti yine yutuyordu.
# Kullanicinin sabit arka plan icin verdigi karar burada da gecerli:
# "arka fon kapaktan acik tonda olsun".
DJ_ARKA_PLAN_PARLAKLIK = "brightness=0.08:saturation=1.2"
# Ust uc 1/0.88: parlak klipler (altin bokeh, gun batimi) kayan yaziyi
# yutuyordu - yazi acik renkli ve arka plan beyaza dogru gidince kontrast
# kalmiyor. Sabit gorsel arka planda bu sorun hic yoktu cunku o goruntu
# koyu art.jpg'den tureiyordu; video havuzunda ise parlak klipler var.
# Siyahlar hala kaldiriliyor (kart one ciksin), sadece tepe bastiriliyor.
DJ_ARKA_PLAN_EGRISI = "0/0.14 0.5/0.70 1/0.88"


# --- DJ setlerinin muzik stili -------------------------------------------
# SORUN: her set `theme: "dj"` kullaniyordu, yani deep house bir set ile
# techno bir set YouTube/TikTok gozunde birebir ayni sinyali veriyordu -
# ayni hashtag, ayni etiket, ayni stok goruntu. Iki set de AYNI kitleye
# dusuyor; ikinci set birinciyi genisletmiyor, tekrar ediyor.
# COZUM: meta.json'a `set_style` alani. Tema ("dj") marka kimligi olarak
# kaliyor, stil ise kesif sinyalini ayristiriyor: kendi hashtag'leri, kendi
# stok video sorgulari, kendi Suno tarifi. Alan YOKSA hicbir sey degismiyor
# (eski setler aynen calisir) - bu yuzden geriye donuk guvenli.
SET_STILLERI = {
    "deep_house": {
        "label": "Deep House",
        "etiketler": ["Deep House", "Melodic House", "Chillout Mix", "Lounge Music"],
        "video_sorgulari": [
            "rain window night city lights",
            "smoke slow motion dark background",
            "neon lights bokeh night abstract",
            "city night traffic timelapse",
        ],
        "suno_stil": "deep house, melodic, warm analog bass, soft female vocal chops, 120 bpm, late night lounge",
    },
    "techno_chill": {
        # Deep house'un dinleyicisiyle ortusuyor ama aynisi degil: techno
        # tarafi "focus/work/study" ve "night drive" aramalarini yakaliyor,
        # deep house daha cok "lounge/relax" tarafinda. Kasitli olarak sert
        # techno DEGIL - kanalin mevcut sakin tonundan kopmadan komsu bir
        # kitleye aciliyor.
        "label": "Techno Chill",
        "etiketler": ["Melodic Techno", "Chill Techno", "Focus Music", "Night Drive"],
        "video_sorgulari": [
            "night highway lights motion blur",
            "tunnel lights driving pov night",
            "abstract dark geometric motion loop",
            "industrial dark fog light beams",
            "aerial city night lights slow",
            "particles dark blue slow motion",
        ],
        "suno_stil": "melodic techno, hypnotic arpeggio, deep sub bass, airy pads, no vocals, 124 bpm, late night drive",
    },
}


def set_stili(meta: dict) -> dict | None:
    """meta.json'daki `set_style` icin stil tanimi; yoksa None."""
    return SET_STILLERI.get(meta.get("set_style") or "")

# --- İngilizce varyantlar (meta.json'da "language": "en" ise kullanılır) ---
# İlk kullanım: DJ Famous (bkz. dj_sets/README.md) — markanın uzun vadeli global
# açılımının ilk somut denemesi olarak İngilizce başlık/metin tercih edildi
# (kullanıcı kararı, 2026-09-03). Ana katalog (`projects/`) meta.json'larında
# "language" alanı YOK, yani varsayılan ("tr") değişmedi — bu varyantlar sadece
# language="en" olan projeler için devreye giriyor.
DISCOVERY_HASHTAGS_EN = [
    "#explore", "#fyp", "#viral", "#foryoupage", "#music",
    "#newmusic", "#newsong", "#musicdiscovery", "#indiemusic",
]

HOOK_LINES_EN = [
    "Discover this one before everyone else 👀🎶",
    "Put your headphones on, this one's for you 🎧",
    "New track, new story 🎵",
    "Don't scroll past this one 👇",
    "Ten seconds in and you'll know 🎧",
    "Turn it up, the rest follows 🔊",
    "Tonight's track just landed 🌙",
    "Play it once, it stays with you 🎶",
    "Scroll past and you'll come back 👀",
    "This rhythm catches you 🔥",
    "New track out now 🎵",
    "Don't watch this on mute 🔊",
    "You're adding this to your playlist 📲",
    "This one's for late nights 🌃",
]

USE_LINES_EN = [
    "Feel free to use this track in your edits 🔥",
    "Use this sound in your edits, it's free 🔥",
    "Clip it, edit it, it's yours 🎬",
    "This sound works great in your videos 🔥",
    "Drop it into your edit, no problem 🎬",
    "Use it in your videos if you like 🔥",
    "I'd love to hear this in your edits 🎬",
    "This sound fits your clips perfectly 🔥",
]

FOLLOW_LINES_EN = [
    "Follow for more tracks",
    "Follow for new drops 🎵",
    "New music every week — follow along",
    "More coming, stay tuned 🎶",
    "Don't miss the next one, follow",
    "Follow so you don't miss a drop 🎧",
    "More where this came from 🎵",
    "Follow for the next track 🔔",
]

ENGAGEMENT_QUESTIONS_EN = [
    "What genre should we drop next? Comment below 👇",
    "What does this track remind you of? Tell us in the comments 💬",
    "Rate it from 1 to 10 👇",
    "How many times will you replay this one? Tell us 🔁",
    "Which part did you rewind? 👇",
    "What moment does this bring back? 💬",
    "Who needs to hear this? Tag them 👇",
    "Lyrics or the beat? Tell us 💬",
    "How fast did it pull you in? ⏱️",
    "What would you have named this one? 💭",
    "Chorus or intro — which hits harder? 👇",
    "Adding this to your playlist? 📲",
    "What time of day is this track for? 🌙",
    "Which style suits it best? 🎧",
]

# Video/ses kodek ayarları
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
CRF = "20"
PRESET = "medium"

# --- YouTube yayın zamanlaması (Türkiye yerel saati — Türkiye DST kullanmıyor,
# yıl boyunca sabit UTC+3) ---
# trend_hashtag_notlari.md'ye göre en iyi paylaşım saatleri: 12:00-14:00 ve
# 18:00-22:00. Eskiden Görev Zamanlayıcı sadece 13:00/19:00'da çalıştığı için
# her yükleme zaten bu aralıklara denk geliyordu; artık otomatik kademeleme
# saatte bir SIK çalıştığı için (bkz. auto_process.py) yükleme anı günün her
# saatine denk gelebilir. YouTube'un status.publishAt özelliği (video
# privacyStatus="private" + gelecek bir publishAt zamanıyla yüklenir, YouTube
# o ana gelince otomatik public'e çeviriyor) sayesinde render/upload ANI ile
# videonun CANLIYA ÇIKTIĞI an birbirinden ayrılabiliyor — auto_process.py
# kendi kademeleme mantığına göre istediği saatte render+upload yapmaya devam
# eder, YouTube tarafı ise bir sonraki golden-hour penceresine kadar bekletir.
# --- Yeni platformlar: OPT-IN -----------------------------------------------
# Facebook / Telegram / Bluesky modulleri yazildi ama saatlik otomasyona
# KAPALI baslatiliyor. Iki kapi birden var ve ikisi de gecilmeli:
#   1. buradaki bayrak True olacak,
#   2. ilgili kimlik dosyasi (upload/*_token.json | *_client_secrets.json) var olacak.
#
# Neden cift kapi: kimlik dosyasi kondugu anda platformun otomatik yayina
# baslamasi istenmiyor. Once elle bir kez calistirilip ciktisi gozle
# dogrulanmali (`python upload/<modul>.py --project ... --dry-run`), ancak
# ondan sonra buradaki bayrak acilmali. Bayragi acmadan once o platformdan
# hicbir sey yayinlanmaz.
# DJ Famous setleri icin AYRI bayraklar - EK_PLATFORMLAR'dan kasitli olarak
# bagimsiz. Sebep dj_sets/README.md'de: setler GERCEK, taninabilir bir kisiyi
# konu aliyor ve "yeni bir kullanim/platform eklenecekse tekrar teyit edilmeli"
# kurali var. Tek bir sozluk olsaydi, katalog icin Facebook'u acmak DJ Famous'u
# da sessizce yeni bir platforma tasirdi - onay bir daha sorulmadan.
# Onay 2026-09-10'da bu ucu icin ayrica alindi.
EK_PLATFORMLAR_DJ = {
    "facebook": True,
    "telegram": True,
    "bluesky": True,
}

EK_PLATFORMLAR = {
    # 2026-09-10: uçtan uca doğrulandı — Reels yüklendi (video_id
    # 1421888749896337), YouTube linki yorumu eklendi, state.json yazıldı.
    "facebook": True,
    # 2026-09-10: uçtan uca doğrulandı — @hermes_famous_asistan kanalına
    # (id -1004337174284) uzun format gönderildi, message_id=3. Aynı bot
    # Hermes asistanı da çalıştırıyor ama kanal gönderilerine tepki
    # vermiyor (eşleştirme listesinde yalnızca kullanıcının DM'i var).
    "telegram": True,
    # 2026-09-10: uçtan uca doğrulandı — famousmusicstudio.bsky.social
    # hesabına video gönderildi (3mv6owocx562t), aspectRatio ve facet'ler
    # doğru geldi. E-posta doğrulaması ŞART (video için), yapıldı.
    "bluesky": True,
}


GOLDEN_HOURS = [(12, 14), (18, 22)]  # (başlangıç, bitiş) — TR yerel saat, [başlangıç, bitiş)
TR_TZ = timezone(timedelta(hours=3))


def next_golden_publish_time(now: datetime | None = None) -> datetime | None:
    """Şu an bir golden-hour penceresinin içindeyse None döner (hemen public
    edilebilir, zamanlamaya gerek yok). Dışındaysa bir sonraki pencerenin
    başlangıcını (TR yerel, tz-aware) döndürür."""
    now = (now or datetime.now(TR_TZ)).astimezone(TR_TZ)
    for start_hour, end_hour in GOLDEN_HOURS:
        if start_hour <= now.hour < end_hour:
            return None

    candidates = []
    for day_offset in (0, 1):
        day = (now + timedelta(days=day_offset)).replace(minute=0, second=0, microsecond=0)
        for start_hour, _ in GOLDEN_HOURS:
            candidate = day.replace(hour=start_hour)
            if candidate > now:
                candidates.append(candidate)
    return min(candidates)
