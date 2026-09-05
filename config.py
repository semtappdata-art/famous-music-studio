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
BG_BOKEH_POS = (0.8, 0.7)  # bokeh blob merkezi, (x,y) genişlik/yükseklik oranı (0-1)
BG_BOKEH_RADIUS_RATIO = 0.45  # min(W,H)'e oran, bokeh yarıçapı — ne kadar kapsadığı
BG_BOKEH_BRIGHTNESS = 50  # bokeh blob'ün en parlak merkez noktası (0-255)
BG_BOKEH_COLOR = (80, 180, 255)  # cool cyan-blue, accent rengiyle complementary

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
FONT_COLOR = "white@0.95"  # künye yazısı net okunsun diye yüksek opaklık
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
DISCOVERY_HASHTAGS = ["#keşfet", "#fyp", "#viral"]

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
]

# --- İngilizce varyantlar (meta.json'da "language": "en" ise kullanılır) ---
# İlk kullanım: DJ Famous (bkz. dj_sets/README.md) — markanın uzun vadeli global
# açılımının ilk somut denemesi olarak İngilizce başlık/metin tercih edildi
# (kullanıcı kararı, 2026-09-03). Ana katalog (`projects/`) meta.json'larında
# "language" alanı YOK, yani varsayılan ("tr") değişmedi — bu varyantlar sadece
# language="en" olan projeler için devreye giriyor.
DISCOVERY_HASHTAGS_EN = ["#explore", "#fyp", "#viral"]

HOOK_LINES_EN = [
    "Discover this one before everyone else 👀🎶",
    "Put your headphones on, this one's for you 🎧",
    "New track, new story 🎵",
    "Don't scroll past this one 👇",
]

ENGAGEMENT_QUESTIONS_EN = [
    "What genre should we drop next? Comment below 👇",
    "What does this track remind you of? Tell us in the comments 💬",
    "Rate it from 1 to 10 👇",
    "How many times will you replay this one? Tell us 🔁",
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
