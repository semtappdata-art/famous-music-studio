"""Render ayarları — tüm görünüm/kalite parametreleri burada."""

import os

FPS = 30

# platform_key -> (genişlik, yükseklik, çıktı dosya adı)
PLATFORMS = {
    "youtube_16x9": (1920, 1080),
    "shorts_9x16": (1080, 1920),
    "square_1x1": (1080, 1080),
}

# Bu platformlar şarkının TAMAMI yerine, audio_highlight.find_highlight() ile
# bulunan en enerjik/yoğun bölümden kırpılır (viral kısa video için) —
# meta.json'da "highlight_start"/"highlight_end" (saniye) belirtilirse onlar
# öncelikli kullanılır, otomatik tespit devreye girmez.
HIGHLIGHT_PLATFORMS = {"shorts_9x16", "square_1x1"}
HIGHLIGHT_DURATION = 45.0  # saniye — YouTube Shorts/TikTok/Reels limitinin (180s) çok altında

# Aynı anda kaç platform paralel render edilsin (varsayılan: hepsi birden)
MAX_PARALLEL_RENDERS = len(PLATFORMS)

# Müzik türüne göre 5 renk paleti — her şarkı meta.json'da "theme" ile birini seçer.
# accent/accent2: çerçevenin iki rengi — statik açısal (aynı anda çok renkli) gradyan
# bu ikisi arasında oluşur (referans videoda çerçeve dönmüyor, sabit).
THEMES = {
    "pop": {"label": "Pop", "related": ["R&B", "Trap"], "accent": (255, 60, 140), "accent2": (80, 120, 255)},
    "rock": {"label": "Rock", "related": ["Alternative", "Punk"], "accent": (230, 35, 35), "accent2": (255, 170, 40)},
    "elektronik": {"label": "Elektronik", "related": ["Synthwave", "House"], "accent": (60, 220, 255), "accent2": (170, 60, 255)},
    "akustik": {"label": "Akustik", "related": ["Folk", "Indie"], "accent": (230, 150, 60), "accent2": (255, 90, 140)},
    "hiphop": {"label": "Hip-Hop", "related": ["Trap", "Rap"], "accent": (255, 195, 60), "accent2": (255, 90, 40)},
    "arabesk": {"label": "Arabesk", "related": ["Trap", "Türkçe Rap"], "accent": (200, 40, 90), "accent2": (255, 140, 60)},
}
DEFAULT_THEME = "hiphop"  # meta.json'da "theme" belirtilmezse kullanılır

# --- Kart tasarımı: referans video stili — tam ekran değil, ekranın büyük kısmını
# kaplayan ("orta alan") yuvarlak köşeli albüm kartı + etrafında dönen neon çerçeve +
# altında kayan başlık + ilerleme çubuğu.
# Sadece bu kart alanı işlenir (kenarlar düz siyah) — bu yüzden eski tam ekran/zoom/
# waveform tasarımına göre çok daha az render maliyeti var.
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


FONT_PATH = _find_font_path()
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
BRAND_HASHTAGS = ["#FamousMusicStudio", "#AIMusic", "#YapayZekaMüzik", "#AIMusicChallenge"]

# Caption'ın ilk satırı — kaydırmayı durdurmak için merak uyandıran kısa açılış cümlesi.
# build_caption() şarkı başlığına göre bunlardan birini deterministik seçer (her şarkı
# için hep aynı hook, ama şarkılar arası çeşitlilik olur).
HOOK_LINES = [
    "Bu şarkı tamamen yapay zeka ile yapıldı 🤖🎵",
    "İnsan mı yapay zeka mı, sen karar ver 👇",
    "0'dan yapay zeka ile üretilen yeni şarkı 🎶",
    "Bunu bir AI besteledi, inanabiliyor musun?",
]

# Video/ses kodek ayarları
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
CRF = "20"
PRESET = "medium"
