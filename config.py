"""Render ayarları — tüm görünüm/kalite parametreleri burada."""

import importlib
import os
from datetime import datetime, timedelta, timezone

try:
    from tools.config_loader import get as _cfg_get

    def get(key, default=None):
        try:
            return _cfg_get(key, default)
        except Exception:
            return default
except Exception:
    def get(key, default=None):
        return default

FPS = get('FPS', 30)

PLATFORMS = {
    "youtube_16x9": (1920, 1080),
    "shorts_9x16": (1080, 1920),
}

HIGHLIGHT_PLATFORMS = {"shorts_9x16"}
HIGHLIGHT_DURATION = 45.0
MAX_PARALLEL_RENDERS = len(PLATFORMS)

THEMES = {
    "pop": {"label": "Pop", "related": ["R&B", "Trap"], "accent": (255, 60, 140), "accent2": (80, 120, 255), "language": "tr", "art_mood": "bright vibrant", "art_query": "vibrant sunset city skyline pastel sky"},
    "rock": {"label": "Rock", "related": ["Alternative", "Punk"], "accent": (230, 35, 35), "accent2": (255, 170, 40), "language": "tr", "art_mood": "dark dramatic moody", "art_query": "dramatic stormy sky dark mountains"},
    "elektronik": {"label": "Elektronik", "related": ["Synthwave", "House"], "accent": (60, 220, 255), "accent2": (170, 60, 255), "language": "tr", "art_mood": "neon night", "art_query": "neon city night lights reflection"},
    "akustik": {"label": "Akustik", "related": ["Folk", "Indie"], "accent": (230, 150, 60), "accent2": (255, 90, 140), "language": "tr", "art_mood": "warm golden hour", "art_query": "warm golden hour forest sunlight"},
    "hiphop": {"label": "Hip-Hop", "related": ["Trap", "Rap"], "accent": (255, 195, 60), "accent2": (255, 90, 40), "language": "tr", "art_mood": "gritty urban night", "art_query": "urban street night city concrete"},
    "arabesk": {"label": "Arabesk", "related": ["Trap", "Türkçe Rap"], "accent": (200, 40, 90), "accent2": (255, 140, 60), "language": "tr", "art_mood": "melancholy moody rainy", "art_query": "rainy window night melancholy blur"},
    "dj": {"label": "DJ Set", "related": ["Mix", "Live Set"], "accent": (255, 210, 60), "accent2": (255, 60, 140), "language": "en", "art_mood": "nightclub stage lights", "art_query": "nightclub crowd stage lights"},
}
DEFAULT_THEME = "hiphop"

GORSEL_DIL_AKTIF = get('GORSEL_DIL.AKTIF', True)
GORSEL_DIL_KAPAK_KONSEPT = get('GORSEL_DIL.KAPAK_KONSEPT', 'split')

TEMA_GRADE = get('TEMA_GRADE', {
    "pop": {"contrast": 1.06, "saturation": 1.08},
    "rock": {"contrast": 1.10, "saturation": 0.92},
    "elektronik": {"contrast": 1.05, "saturation": 1.10},
    "akustik": {"contrast": 1.03, "saturation": 0.98},
    "hiphop": {"contrast": 1.08, "saturation": 1.00},
    "arabesk": {"contrast": 1.06, "saturation": 0.94},
    "dj": {"contrast": 1.06, "saturation": 1.06},
})

NABIZ_BUDGET = get('NABIZ_BUDGET', 0.20)

CARD_SIZE_RATIO = get('CARD.SIZE_RATIO', 0.45)
CARD_CORNER_RATIO = 0.08
CARD_ASSET_REF_SIZE = get('CARD.ASSET_REF_SIZE', 800)
CARD_MASK_ASSET_PATH = get('CARD.MASK_ASSET_PATH', "assets/card_mask.png")
CARD_ART_COLOR = get('CARD.ART_COLOR', "0x151515")

BG_CENTER_BRIGHTNESS = get('BG.CENTER_BRIGHTNESS', 28)

BACKDROP_PAN_MARGIN_RATIO = get('BACKDROP.PAN_MARGIN_RATIO', 0.14)
BACKDROP_PAN_SPEED_X = get('BACKDROP.PAN_SPEED_X', 0.12)
BACKDROP_PAN_SPEED_Y = get('BACKDROP.PAN_SPEED_Y', 0.08)

BACKDROP_HUE_AMPLITUDE_DEG = get('BACKDROP.HUE_AMPLITUDE_DEG', 35)
BACKDROP_HUE_SPEED = get('BACKDROP.HUE_SPEED', 0.025)

EQ_BAR_THICKNESS_RATIO = get('EQ.BAR_THICKNESS_RATIO', 0.15)
MARQUEE_GAP_RATIO = get('MARQUEE.GAP_RATIO', 0.02)
FONT_CHAR_WIDTH_RATIO = get('FONT.CHAR_WIDTH_RATIO', 0.55)

INTRO_KAPAK = get('INTRO.KAPAK', True)
INTRO_KAPAK_BEKLEME = get('INTRO.KAPAK_BEKLEME', 0.9)
INTRO_KAPAK_COZULME = get('INTRO.KAPAK_COZULME', 1.5)
INTRO_KAPAK_PLATFORMLAR = get('INTRO.KAPAK_PLATFORMLAR', ["youtube_16x9"])

DIKEY_HOOK_METNI = get('DIKEY_HOOK.METNI', "Sesi A\u00e7")
DIKEY_HOOK_SURE_SN = get('DIKEY_HOOK.SURE_SN', 2.5)

# ============================================================
# BÜYÜME MOTORU (BUYUME_ONERILERI.md) — izlenme/kalma/abone kaldıraçları.
# Hepsi config bayraklı: kapatmak silmek değil, False yapmak.
# ============================================================
# Madde 6 — Cold open: uzun videonun ilk saniyelerine highlight'tan kısa bir
# "ön tat" eklenir (ses concat: önce zirve kesiti, sonra tam şarkı).
COLD_OPEN_ACIK = get('BUYUME.COLD_OPEN_ACIK', True)
COLD_OPEN_SURE_SN = get('BUYUME.COLD_OPEN_SURE_SN', 4.0)
COLD_OPEN_PLATFORMLAR = get('BUYUME.COLD_OPEN_PLATFORMLAR', ["youtube_16x9", "shorts_9x16"])
# Madde 7 — Görsel nabız: bölüm verisi olmasa bile periyodik renk/pan vurgusu.
GORSEL_NABIZ_SURE_SN = get('BUYUME.GORSEL_NABIZ_SURE_SN', 25.0)
GORSEL_NABIZ_GUC = get('BUYUME.GORSEL_NABIZ_GUC', 0.9)
# Shorts için ayrı nabız gücü (dikey format = daha hızlı dikkat kaybı)
GORSEL_NABIZ_GUC_SHORTS = get('BUYUME.GORSEL_NABIZ_GUC_SHORTS', 1.35)

# --- YOUTUBE SHORTS EFEKTLERI (beat sync / hız rampası) -------------------
# YouTube Shorts düzenleyicisindeki "müzikle uyum" efektlerinin karşılığı.
# Kapatmak silmek değil: False yapmak (CLAUDE.md §16).
# beat_sync.py: librosa ile beat tespiti (cache'li), ffmpeg'e aktarılır.
SHORTS_BEAT_SYNC_AKTIF = get('BUYUME.SHORTS_BEAT_SYNC_AKTIF', True)
# Her beat'te parlaklik flaşı (YouTube "Beat sync" özelliginin görsel izi)
SHORTS_BEAT_FLASH_AKTIF = get('BUYUME.SHORTS_BEAT_FLASH_AKTIF', True)
SHORTS_BEAT_FLASH_ALFA = get('BUYUME.SHORTS_BEAT_FLASH_ALFA', 0.14)
SHORTS_BEAT_FLASH_SURE_SN = get('BUYUME.SHORTS_BEAT_FLASH_SURE_SN', 0.11)
# Beat'e kilitli renk (hue) sıçraması — görsel "snap" hissi
SHORTS_BEAT_HUE_AKTIF = get('BUYUME.SHORTS_BEAT_HUE_AKTIF', True)
SHORTS_BEAT_HUE_DERECE = get('BUYUME.SHORTS_BEAT_HUE_DERECE', 26.0)
# Beat'e kilitli pan itmesi
SHORTS_BEAT_PAN_AKTIF = get('BUYUME.SHORTS_BEAT_PAN_AKTIF', True)
SHORTS_BEAT_PAN_PIXEL = get('BUYUME.SHORTS_BEAT_PAN_PIXEL', 14.0)
# Beat zoom punch (YouTube "cut on beat" görünümü) — yüzde cinsinden
SHORTS_BEAT_ZOOM_AKTIF = get('BUYUME.SHORTS_BEAT_ZOOM_AKTIF', True)
SHORTS_BEAT_ZOOM_YUZDE = get('BUYUME.SHORTS_BEAT_ZOOM_YUZDE', 8.0)
# Beat nabzının sönüm hızı (üstel) — büyük değer = daha "snap"
SHORTS_BEAT_HUE_SERTLIK = get('BUYUME.SHORTS_BEAT_HUE_SERTLIK', 9.0)
# Hız rampası (YouTube "speed ramp"): yavaş başla, beat'te hızlan
SHORTS_SPEED_RAMP_AKTIF = get('BUYUME.SHORTS_SPEED_RAMP_AKTIF', True)
SHORTS_SPEED_RAMP_YAVAS_SURE_SN = get('BUYUME.SHORTS_SPEED_RAMP_YAVAS_SURE_SN', 1.6)
SHORTS_SPEED_RAMP_YAVAS_KAT = get('BUYUME.SHORTS_SPEED_RAMP_YAVAS_KAT', 0.55)
# Madde 11 — Abone CTA'sı: videonun %40'ında 1 kez, 4sn, emir kipi yok.
ABONE_CTA_ACIK = get('BUYUME.ABONE_CTA_ACIK', True)
ABONE_CTA_ORAN = get('BUYUME.ABONE_CTA_ORAN', 0.4)
ABONE_CTA_SURE_SN = get('BUYUME.ABONE_CTA_SURE_SN', 4.0)
ABONE_CTA_METIN = {
    "dj": "Her Cuma yeni \u015fehir \U0001f514",
    "varsayilan": "Her hafta yeni \u015fark\u0131 \U0001f514",
}
# Madde 10 — Bitiş kartı: son 15sn'de sonraki içerik (meta'da end_card_text varsa).
END_CARD_SURE_SN = get('BUYUME.END_CARD_SURE_SN', 15.0)

# ---------------------------------------------------------------------
# Madde 25 — AI TARZ SEÇİCİ (site + YouTube "Future Record" tarzı)
# "Hangi ruh halindesin?" -> sanatçı tarzı -> 15sn önizleme dinle.
# Amaç: ziyaretçi 0 saniyede değer görsün (Suno/Chime/AI-Tool landing
# blueprint'i). Otomatik oynatma YOK (kullanıcı isteği olmadan ses = spam
# sinyali); tıklayınca çalar.
# ---------------------------------------------------------------------
TARZ_SECICI_ACIK = get('BUYUME.TARZ_SECICI_ACIK', True)
TARZ_SECICI_ONEK_OGNE = 0.15   # her seçimde önerilen içerik oranı
# ruh hali -> etiketler + açıklama + (opsiyonel) video_id
TARZ_SECICI_TONUZLER = [
    {
        "id": "gece",
        "etiket": "Gece Sürüşü",
        "ikon": "\U0001f319",
        "aciklama": "Melodic Techno & Night Drive mixleri",
        "tur": "melodic techno",
        "playlist": "gece_surusu",
    },
    {
        "id": "arabesk",
        "etiket": "Arabesk & Trap",
        "ikon": "\U0001f319",
        "aciklama": "Türkçe arabesk, trap ve R&B",
        "tur": "arabesk trap",
        "playlist": "arabesk_trap_vibes",
    },
    {
        "id": "djset",
        "etiket": "DJ Set",
        "ikon": "\U0001f39b",
        "aciklama": "DJ Famous canlı setleri",
        "tur": "dj set",
        "playlist": "dj_setler",
    },
    {
        "id": "chill",
        "etiket": "Chill",
        "ikon": "\U0001f634",
        "aciklama": "Organic House & Deep Focus",
        "tur": "organic house",
        "playlist": "yeni_cikanlar",
    },
    {
        "id": "rock",
        "etiket": "Rock",
        "ikon": "\U0001f3b8",
        "aciklama": "Türkçe Rock & Alternative",
        "tur": "turkish rock",
        "playlist": "yeni_cikanlar",
    },
    {
        "id": "yeni",
        "etiket": "Yeni Çıkanlar",
        "ikon": "\U0001f195",
        "aciklama": "Bu hafa yayınlananlar",
        "tur": "new music",
        "playlist": "yeni_cikanlar",
    },
]

# ---------------------------------------------------------------------
# Madde 28 — SITE ANALITIK (cookie-less, self-hosted)
# Ucuncu taraf hesap gerektirmez; ilk ziyaretci (first-party) toplama.
# Tasarim karari: PII YOK, cookie YOK, localStorage fingerprint YOK.
# Sadece: tarih, sayfa, referrer, cihaz tipi, dil, saat dilimi.
# Saglayici secenekleri:
#   "self_hosted" -> /api/analytics endpoint'i (site/api/analytics.py)
#   "plausible"  -> data-domain + plausible script
#   "umami"      -> self-hosted Umami instance (script src)
#   "yok"        -> kapalı
# ---------------------------------------------------------------------
ANALITIK_ACIK = get('BUYUME.ANALITIK_ACIK', True)
ANALITIK_SAGLAYICI = get('BUYUME.ANALITIK_SAGLAYICI', 'self_hosted')
ANALITIK_UYGULAMA_ADI = get('BUYUME.ANALITIK_UYGULAMA_ADI', 'famous-music-studio')
ANALITIK_PLAUSIBLE_DOMAIN = get('BUYUME.ANALITIK_PLAUSIBLE_DOMAIN', 'famousmusicstudio.com')
ANALITIK_UMAMI_SCRIPT = get('BUYUME.ANALITIK_UMAMI_SCRIPT', '')
# Beacon endpoint (self_hosted). Uretimde ayni domain oldigi icin goreli yol yeter.
# Yerel gelistirmede mutlaka adres kullan: http://127.0.0.1:8792
ANALITIK_ENDPOINT = get('BUYUME.ANALITIK_ENDPOINT', '/api/analytics')
# Veri nereye yazilsin (self_hosted modunda)
ANALITIK_VERI_KLASORU = get('BUYUME.ANALITIK_VERI_KLASORU', 'analytics_data/site')
# Gunluk rapor bu klasorden de okusun
ANALITIK_RAPOR_DOSYASI = 'site_visits.jsonl'

# ---------------------------------------------------------------------
# Madde 29 — TOPLULUK (Discord + Telegram + abonelik listesi)
# Discord: WEBHOOK (token yok). Telegram: mevcut bot + chat id.
# Disa aktarim: python topluluk.py disa-aktar --bicim csv
# ---------------------------------------------------------------------
TOPLULUK_ACIK = get('BUYUME.TOPLULUK_ACIK', True)
TOPLULUK_DISCORD_WEBHOOK = get('BUYUME.TOPLULUK_DISCORD_WEBHOOK', '')
TOPLULUK_VERI_KLASORU = get('BUYUME.TOPLULUK_VERI_KLASORU', 'analytics_data/topluluk')
TOPLULUK_BILDIRIM_BASLIK = get('BUYUME.TOPLULUK_BILDIRIM_BASLIK', 'Yeni Video')
# ntfy (Discord bu agdan erisilemez; ntfy token gerektirmez, telefona push)
TOPLULUK_NTFY_TOPIC = get('BUYUME.TOPLULUK_NTFY_TOPIC', 'fms-t38y77gjd6r7a7h649mb16w2')
TOPLULUK_NTFY_SUNUCU = get('BUYUME.TOPLULUK_NTFY_SUNUCU', 'https://ntfy.sh')
TOPLULUK_NTFY_ACIK = get('BUYUME.TOPLULUK_NTFY_ACIK', True)
# Kanal sirasi: hangi kanallara gonderilecegini belirler.
TOPLULUK_KANALLAR = get('BUYUME.TOPLULUK_KANALLAR', ['discord', 'telegram', 'ntfy'])
TOPLULUK_BILDIRIM_MESAJ = get('BUYUME.TOPLULUK_BILDIRIM_MESAJ',
    "Famous Music Studio'da yeni bir sey var. Dinle, begen, abone ol!")
SITE_URL = get('SITE_URL', 'https://famousmusicstudio.com')

KOFI_URL = get('DESTEK.KOFI_URL', "https://ko-fi.com/famousmusicstudio")

INTRO_SESSIZLIK_KIRP = get('INTRO.SESSIZLIK_KIRP', True)
INTRO_SESSIZLIK_ESIGI = "-50dB"
INTRO_SESSIZLIK_PAY = 0.12
INTRO_SESSIZLIK_MAKS = 3.0

PROGRESS_BAR_HEIGHT_RATIO = 0.008
PROGRESS_BAR_MARGIN_RATIO = 0.08
PROGRESS_BAR_BOTTOM_RATIO = 0.05
PROGRESS_BAR_FILLED = 235
PROGRESS_BAR_EMPTY = 70

def _find_font_path() -> str:
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
    raise RuntimeError("Sistemde uygun bir font bulunamadı.")

def _find_bold_font_path() -> str:
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
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload", "assets", "famous_music_studio_logo_v2.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "assets", "logo.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None

LOGO_PATH = _find_logo_path()
FONT_SIZE_RATIO = 0.032
FONT_COLOR = "white@0.95"
FONT_SHADOW_COLOR = "black@0.55"
FONT_SHADOW_OFFSET = 2
MARQUEE_SEPARATOR = "  •  "
MARQUEE_REPEAT = 6
MARQUEE_SPEED_PX_S = 60

STATIC_LABEL_TEXT = "Famous Music Studio"
STATIC_LABEL_FONT_RATIO = 0.85
STATIC_LABEL_GAP_RATIO = 0.01

# YouTube kanal handle'ı. SOCIAL_LINKS'ten ÖNCE tanımlanmalı (aşağıda
# kullanılıyor) — sıra önemli.
YOUTUBE_HANDLE = "Famous_musics_studio"

SOCIAL_LINKS = {
    "instagram": "https://instagram.com/famous_music_studio",
    "tiktok": "https://www.tiktok.com/@famousmusicstudio",
    "website": "https://famousmusicstudio.com",
    # YouTube kanalı — ABONE çağrılarında kullanılır.
    # NEDEN burada: 9 upload modülü aynı linki yazıyordu ve 8'i YANLIŞ
    # kanala (@DJFamous — başka bir sanatçı) işaret ediyordu. Tek kaynak.
    "youtube": f"https://youtube.com/@{YOUTUBE_HANDLE}",
    # Akış (streaming) linkleri — açıklamada "LISTEN ON" bloğu için.
    # Spotify/Apple Music artist sayfaları; şarkı bazlı linkler DistroKid
    # dağıtımı sonrası eklenir.
    "spotify": "https://open.spotify.com/artist/famousmusicstudio",
    "apple_music": "https://music.apple.com/artist/famousmusicstudio",
}

# Kendi Spotify playlist'lerin (Anjunadeep doktrini: önce kendi pazarın).
# Boşken açıklamaya blok EKLENMEZ — doldurunca otomatik düşer.
# Format: {"Playlist Adı": "https://open.spotify.com/playlist/..."}
# Yer tutucu değerler — gerçek playlist ID'leriyle değiştirilmeli
SPOTIFY_CALMA_LISTELERI = get('SPOTIFY_CALMA_LISTELERI', {
    "City Pulse Sessions": "https://open.spotify.com/playlist/PL_CityPulse",
    "Night Drive Series": "https://open.spotify.com/playlist/PL_NightDrive",
    "Deep Focus Sessions": "https://open.spotify.com/playlist/PL_DeepFocus",
    "DJ Famous Essentials": "https://open.spotify.com/playlist/PL_DJFamousEssentials"
})

# Topluluk sekmesi anket şablonları (500 abone sonrası; haftada 2-3).
# Tam topluluk modülü (turev_takvimi) ayrı iştir — bunlar sadece metin şablonu.
TOPLULUK_SABLONLARI = {
    "siradaki_sehir": "Sıradaki durak hangisi olsun? 🗳️\n1️⃣ {secenek_a}\n2️⃣ {secenek_b}",
    "kapak_secimi": "Cuma videosunun kapağını sen seç! Hangisi tıklatır? 🖼️\nA ve B yorumda 👇",
}

# Promo havuzu: her setten önce türdaş DJ'lere ilk-dalga DM (takvim.py).
PROMO_DM_SABLONU = get('PROMO_DM_SABLONU', "Merhaba {dj} — sana özel ilk dinleme: {parca} {link} Desteklersen setinde çalman bizi uçurur 🙏")
PROMO_HAVUZ_BOYUTU = get('PROMO_HAVUZ_BOYUTU', 15)

# Kanal kimligi (UC ile baslar) — DistroKid Content ID allowlist icin GEREKLI.
# 2026-10-19: API'den dogrulandi (channels().list(mine=True)).
YOUTUBE_KANAL_ID = "UCbbcH8rtQTtz8R66jfKoSZg"
# Content ID allowlist yapildi mi? (DistroKid Dashboard > Content ID > Whitelist)
# False ise yeni yuklemeler claim yiyebilir — SOP_yukleme.md ��8.
CONTENT_ID_ALLOWLIST_AKTIF = get('CONTENT_ID.ALLOWLIST_AKTIF', False)

SOCIAL_HANDLES = {
    "instagram": "famous_music_studio",
    "tiktok": "famousmusicstudio",
}

BRAND_HASHTAGS = ["#FamousMusicStudio"]

DISCOVERY_HASHTAGS = [
    "#keşfet", "#fyp", "#viral", "#keşfetteyiz", "#müzik",
    "#şarkı", "#yenişarkı", "#türkçemüzik", "#foryou",
]
DISCOVERY_HASHTAG_COUNT = 3

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

ILK_YORUM_SORULARI = [
    "Favori bölümün hangisi? Dakikasıyla yaz 👇",
    "En çok nerede kaldın? Bölümü yaz, konuşalım 💬",
    "Baştan sona mı, bölüm bölüm mü dinliyorsun? 👇",
]
ILK_YORUM_SORULARI_EN = [
    "Which section is your favorite? Drop the timestamp 👇",
    "Where did you stay the longest? Tell us 💬",
    "Full listen or section hopping? 👇",
]
ILK_YORUM_ABONE = "Abone ol, her yeni paragraftan önce haberdar ol 🔔"
ILK_YORUM_ABONE_EN = "Subscribe for the next track before it drops 🔔"

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

DJ_ARKA_PLAN_VIDEO = True
DJ_ARDA_GORSELLERI = True
DJ_ARDA_BACKDROP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dj_sets", "_arda", "preview", "arda_tshirt_slideshow_45s.mp4")

DJ_HUD = True
DJ_HUD_NEFES = True
DJ_HUD_NEFES_SURE_SN = 8.0
DJ_HUD_NEFES_DERINLIK = 0.15
DJ_SAHNE_MODU = True
DJ_ON_TARAMA = True
DJ_TARAMA_BEKLEME_SN = 2 * 60 * 60
DJ_SAHNE_BLUR_SIGMA = 1.5
DJ_SAHNE_EGRISI = "0/0.02 0.5/0.46 1/0.92"
DJ_ARKA_PLAN_BLUR_SIGMA = 14
DJ_ARKA_PLAN_PARLAKLIK = "brightness=0.08:saturation=1.2"
DJ_ARKA_PLAN_EGRISI = "0/0.14 0.5/0.70 1/0.88"
DJ_SAHNE_ZOOM = True
DJ_SAHNE_ZOOM_BITIS = 1.08

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
        "label": "Techno Chill",
        "etiketler": ["Melodic Techno", "Chill Techno", "Focus Music", "Night Drive"],
        "video_sorgulari": [
            "night highway lights motion blur",
            "tunnel lights driving pov night",
            "abstract dark geometric motion loop",
            "industrial dark fog light beams",
            "aerial city night lights slow",
            "particles dark blue slow motion",
            "luxury yacht party night",
            "rooftop pool dancing nightclub",
        ],
        "suno_stil": "melodic techno, hypnotic arpeggio, deep sub bass, airy pads, no vocals, 124 bpm, late night drive",
    },
    "organic_morning": {
        "label": "Organic House",
        "etiketler": ["Organic House", "Sunrise Mix", "Balearic House", "Morning Music"],
        "video_sorgulari": [
            "sunrise over ocean golden light slow",
            "palm tree shadows warm morning terrace",
            "sun rays through leaves bokeh",
            "calm sea waves golden hour aerial",
        ],
        "suno_stil": "organic house, warm analog synth, gentle marimba melody, soft latin percussion, no vocals, 118 bpm, sunrise terrace, uplifting calm",
    },
    "progressive_node": {
        "label": "Progressive House",
        "etiketler": ["Progressive House", "Peak Time House", "Driving House", "Club Mix"],
        "video_sorgulari": [
            "dark club crowd silhouettes laser beams",
            "dj booth hands lights dark party",
            "concert stage lights beams crowd night",
            "neon tunnel light streaks fast motion",
            "luxury yacht party night",
            "superyacht deck night party",
        ],
        "suno_stil": "melodic progressive house, driving kick, hypnotic lead synth, layered atmosphere, no vocals, 126 bpm, peak time club, forward motion",
    },
    "arabesk_trap": {
        "label": "Arabesk Trap",
        "etiketler": ["Arabesk Trap", "Türkçe Trap", "Damar Mix", "Gece Mix"],
        "video_sorgulari": [
            "rainy istanbul street night neon reflections",
            "car interior night drive city lights bokeh",
            "smoke dark background slow motion gold",
            "bosporus bridge night lights long exposure",
        ],
        "suno_stil": "arabesk trap fusion, emotional turkish string melody, deep 808 bass, slow tempo 140 bpm half-time, late night damar mood, turkish vocal",
    },
    "nineties_nostalji": {
        "label": "90'lar Nostalji",
        "etiketler": ["90'lar Türkçe Pop", "Nostalji Mix", "Retro Pop", "Eski Şarkılar"],
        "video_sorgulari": [
            "vintage tv static retro living room",
            "cassette tape close up warm light",
            "retro istanbul street 90s film grain",
            "neon retro arcade night glow",
        ],
        "suno_stil": "90s turkish pop revival, bright synth brass, nostalgic melody, danceable 118 bpm, retro production with modern mix, turkish vocal",
    },
}

def set_stili(meta: dict) -> dict | None:
    return SET_STILLERI.get(meta.get("set_style") or "")


# ============================================================
# DJ SERIES CONFIGURATION (Best Practices from Cercle/Boiler Room/HÖR)
# ============================================================
DJ_SERIES = {
    "city_pulse": {
        "brand": "City Pulse Sessions",
        "tagline": "Urban soundscapes from the world's most iconic rooftops",
        "visual_theme": "urban_rooftop_cinematic",  # Cercle-style location story
        "thumbnail_template": "artist_silhouette + city_landmark + series_logo",
        "description_template": "full_tracklist + city_story + credits + cross_promo",
        "schedule": "biweekly_friday_18:00_tr",
        "locations": [
            {"city": "Istanbul", "country": "Turkey", "landmark": "Hagia Sophia", "gps": "41.0082,28.9784", "story": "Sunset over Bosphorus, minarets calling, city waking up"},
            {"city": "Berlin", "country": "Germany", "landmark": "TV Tower", "gps": "52.5200,13.4050", "story": "Techno capital, concrete and neon, history in every beat"},
            {"city": "Tokyo", "country": "Japan", "landmark": "Tokyo Tower", "gps": "35.6762,139.6503", "story": "Neon dreams, Shibuya crossing, future sound"},
            {"city": "New York", "country": "USA", "landmark": "Empire State", "gps": "40.7484,-73.9857", "story": "City that never sleeps, rooftop stories, concrete jungle"},
            {"city": "London", "country": "UK", "landmark": "The Shard", "gps": "51.5045,-0.0865", "story": "Thames reflections, underground legacy, global sound"},
        ],
        "default_location_idx": 0,
        "youtube": {
            "playlist_id": "PLD9oWKZnu0vY",
            "tags_base": ["melodic techno", "progressive house", "city pulse", "dj famous", "rooftop"],
            "hashtags": "#CityPulse #MelodicTechno #DJFamous",
            "title_format": "{artist} @ {landmark}, {city} for City Pulse Sessions",
        },
        "seo": {
            "primary_keyword": "melodic techno rooftop set",
            "secondary_keywords": ["progressive house", "cityscape", "sunset dj"],
        },
    },
    "deep_focus": {
        "brand": "Deep Focus Sessions",
        "tagline": "Immersive organic house from nature's most serene locations",
        "visual_theme": "nature_immersive_cinematic",
        "thumbnail_template": "artist_photo + nature_scene + series_logo",
        "description_template": "full_tracklist + nature_story + wellness_angles + credits",
        "schedule": "monthly_first_friday_10:00_tr",
        "locations": [
            {"city": "Bali", "country": "Indonesia", "landmark": "Rice Terraces", "gps": "-8.4095,115.1889", "story": "Morning mist over Tegallalang, gamelan whispers in the wind"},
            {"city": "Tulum", "country": "Mexico", "landmark": "Cenote", "gps": "20.2114,-87.4654", "story": "Crystal waters, ancient caves, jungle heartbeat"},
            {"city": "Santorini", "country": "Greece", "landmark": "Caldera", "gps": "36.3932,25.4615", "story": "White cliffs, azure infinity, cycladic calm"},
        ],
        "default_location_idx": 0,
        "youtube": {
            "playlist_id": "PLBJq1HPOlly4",
            "tags_base": ["organic house", "deep house", "deep focus", "dj famous", "nature"],
            "hashtags": "#DeepFocus #OrganicHouse #DJFamous",
            "title_format": "{artist} @ {landmark}, {city} for Deep Focus Sessions",
        },
        "seo": {
            "primary_keyword": "organic house nature set",
            "secondary_keywords": ["deep house", "wellness music", "morning mix"],
        },
    },
    "night_drive": {
        "brand": "Night Drive Series",
        "tagline": "Cinematic melodic techno from the driver's seat",
        "visual_theme": "dashboard_driving_cinematic",  # Existing strength
        "thumbnail_template": "dashboard_view + artist_silhouette + series_logo",
        "description_template": "full_tracklist + drive_route_story + credits + cross_promo",
        "schedule": "monthly_last_friday_22:00_tr",
        "locations": [
            {"city": "Los Angeles", "country": "USA", "route": "Mulholland Drive", "gps": "34.1033,-118.3275", "story": "City lights below, stars above, midnight cruise"},
            {"city": "Dubai", "country": "UAE", "route": "Sheikh Zayed Road", "gps": "25.2048,55.2708", "story": "Futuristic skyline, desert meets neon, endless highway"},
            {"city": "Tokyo", "country": "Japan", "route": "Shuto Expressway", "gps": "35.6895,139.6917", "story": "Neon tunnels, rain on windshield, cyberpunk reality"},
        ],
        "default_location_idx": 0,
        "youtube": {
            "playlist_id": "PLWbxoxvoVTa0",
            "tags_base": ["melodic techno", "night drive", "dj famous", "driving music", "late night"],
            "hashtags": "#NightDrive #MelodicTechno #DJFamous",
            "title_format": "{artist} | {route}, {city} for Night Drive Series",
        },
        "seo": {
            "primary_keyword": "melodic techno driving mix",
            "secondary_keywords": ["night drive", "late night music", "focus driving"],
        },
    },
    "boiler_room_style": {
        "brand": "DJ Famous Live",
        "tagline": "Raw energy, real crowd, pure connection",
        "visual_theme": "crowd_club_raw",  # Boiler Room style
        "thumbnail_template": "dj_action + crowd_energy + boiler_logo_style",
        "description_template": "full_tracklist + venue_story + crowd_moments + credits",
        "schedule": "quarterly_special",
        "locations": [
            {"city": "Berlin", "country": "Germany", "venue": "Historic Warehouse", "gps": "52.5200,13.4050"},
            {"city": "Istanbul", "country": "Turkey", "venue": "Underground Club", "gps": "41.0082,28.9784"},
        ],
        "default_location_idx": 0,
        "youtube": {
            "playlist_id": "PLMXZSo1En0cg",
            "tags_base": ["techno", "live set", "boiler room style", "dj famous", "club"],
            "hashtags": "#DJFamousLive #Techno #LiveSet",
            "title_format": "{artist} | DJ Famous Live: {city}",
        },
        "seo": {
            "primary_keyword": "techno live set club",
            "secondary_keywords": ["dj set", "underground", "berlin techno"],
        },
    },
}

def get_dj_series(series_key: str) -> dict | None:
    return DJ_SERIES.get(series_key)

def list_dj_series() -> list:
    return list(DJ_SERIES.keys())

def get_series_location(series_key: str, idx: int = None) -> dict | None:
    series = DJ_SERIES.get(series_key)
    if not series:
        return None
    locations = series.get("locations", [])
    if not locations:
        return None
    if idx is None:
        idx = series.get("default_location_idx", 0)
    return locations[idx % len(locations)]

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

VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
CRF = "20"
PRESET = "medium"

GOLDEN_HOURS = [(12, 14), (18, 22)]
TR_TZ = timezone(timedelta(hours=3))

# YENİ ÜRETİM PLANI (2026-10-05): 6 şarkı/hafta + 3 set/hafta
HAFTALIK_SARKI_HEDEFI = 6
HAFTALIK_SET_HEDEFI = 3
MIN_YENI_SARKI_ARALIK_SAAT = 28 * 3600  # 28 saat
GUNLUK_MAKS_YENI_SARKI = 2
YAYIN_GUNLERI = [0, 2, 4]  # Pazartesi, Çarşamba, Cuma
YAYIN_SAATLERI = [12, 18]  # 12:00, 18:00
HAFTA_SONU_HAZIRLIK_GUN = 4  # Cuma
HAFTA_SONU_HAZIRLIK_SAAT = 20  # 20:00

BACKFILL_TELAFI_BITIS = datetime(2026, 9, 21, 0, 0, tzinfo=TR_TZ)
BACKFILL_TELAFI_TAVANLARI = {"telegram": 3, "bluesky": 3, "facebook": 2}

# ============================================================
# ARŞİV / YEDEKLEME KONFİGÜRASYONU
# ============================================================
ARCHIVE_CONFIG = {
    "enabled": True,
    "retention_days": 90,           # 90 gün sakla
    "backup_on_upload": True,       # Upload sonrası yedek al
    "archive_on_delete": True,      # Silme anında arşivle (hard delete yerine)
    "storage_paths": {
        "local": "archives/",       # Yerel
        "cloud": "",                # Opsiyonel: S3/GDrive/R2 bucket
    },
    "auto_archive_after_upload": True,
}

def backfill_telafi_aktif(now: datetime | None = None) -> bool:
    now = (now or datetime.now(TR_TZ)).astimezone(TR_TZ)
    return now < BACKFILL_TELAFI_BITIS

def next_golden_publish_time(now: datetime | None = None) -> datetime | None:
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

TIKTOK_KIT_AKTIF = True
TIKTOK_KIT_GUNLUK_TAVAN = 1
TIKTOK_KIT_HAFTALIK_TAVAN = 4
TIKTOK_KIT_ARALIK_SAAT = 36
TIKTOK_KIT_ONAY_TIMEOUT_SAAT = 48
TIKTOK_KIT_HATIRLATMA_SAAT = 48
TIKTOK_KIT_DURUM_TAZELIK_SAAT = 72

TIKTOK_AKIS = "web_planla"
TIKTOK_WEB_PLANLA_MAX_GUN = 10
TIKTOK_WEB_PLANLA_MIN_DAKIKA = 60
TIKTOK_WEB_KONTROL_HATIRLATMA = True
TIKTOK_WEB_PAKET = True
TIKTOK_WEB_BAYAT_SAAT = 48

def tiktok_web_modu() -> bool:
    return globals().get("TIKTOK_AKIS") != "api_taslak"

TIKTOK_AI_BEYANI = "aciklama"

AI_BEYAN_SATIRLARI = {
    "tr": {
        "vokalli": "Söz: Famous Music Studio · Müzik ve vokal: AI destekli",
        "vokalsiz": "Müzik: AI destekli · Famous Music Studio",
        "dj": "Seçki ve miks: DJ Famous · Müzik: AI destekli",
    },
    "en": {
        "vokalli": "Lyrics: Famous Music Studio · Music & vocals: AI-assisted",
        "vokalsiz": "Music: AI-assisted · Famous Music Studio",
        "dj": "Selection & mix: DJ Famous · Music: AI-assisted",
    },
}

TIKTOK_KIT_ETIKET_SAYISI = 6

TEMA_KESIF_ETIKETLERI = {
    "pop": ["#türkçepop", "#popmüzik", "#yenişarkı", "#türkçemüzik", "#şarkı", "#keşfet"],
    "rock": ["#türkçerock", "#rockmüzik", "#alternatifrock", "#yenişarkı", "#türkçemüzik", "#keşfet"],
    "elektronik": ["#elektronikmüzik", "#türkçeelektronik", "#synthwave", "#yenişarkı", "#türkçemüzik", "#keşfet"],
    "akustik": ["#akustikmüzik", "#türkçeakustik", "#folk", "#yenişarkı", "#türkçemüzik", "#keşfet"],
    "hiphop": ["#türkçehiphop", "#hiphoptr", "#rap", "#yenişarkı", "#türkçemüzik", "#keşfet"],
    "arabesk": ["#arabesk", "#türkçearabesk", "#trap", "#yenişarkı", "#türkçemüzik", "#keşfet"],
    "dj": ["#djset", "#mix", "#livemix", "#techhouse", "#keşfet"],
}

EK_PLATFORMLAR_DJ = {
    "facebook": True,
    "telegram": True,
    "bluesky": True,
}

EK_PLATFORMLAR = {
    "facebook": True,
    "telegram": True,
    "bluesky": True,
}

# ============================================================
# INDIE FLAGSHIP 5-KAMERA VİDEO PRODÜKSİYON CONFIG
# ============================================================
INDIE_FLAGSHIP_5CAM = {
    "cameras": 5,
    "camera_roles": ["master", "tight", "detail", "wide", "gimbal"],
    "resolution": "4K",
    "fps": 23.976,
    "codec": "XAVC_HS_422_10bit",
    "picture_profile": "S-Log3",
    "timecode_sync": "Tentacle_Sync_E",
    "operators": 2,
    "static_cameras": 3,
    "gimbal_camera": True,
    "vertical_native": True,
    "songs_per_day": 3,
    "takes_per_song": {"main": 4, "secondary": 3, "acoustic": 2},
    "post_days": 3,
    "deliverables": [
        "youtube_4k_sdr",
        "youtube_4k_hdr",
        "shorts_9x16",
        "reels_9x16",
        "tiktok_9x16",
        "archival_master",
        "vertical_pack",
        "thumbnails",
        "metadata"
    ],
    "quality_gates": {
        "min_bitrate_4k": 35000000,
        "max_true_peak": -1.0,
        "target_lufs": -14.0,
        "frame_drop_tolerance": 0,
        "audio_sync_tolerance_ms": 5,
    },
    "budget_tl": 16300,
    "crew_count": 5,

    # Kamera eşleştirme ayarları (tüm kameralar aynı olmalı)
    "camera_matching": {
        "resolution": "3840x2160",
        "fps": 23.976,
        "codec": "XAVC_HS_422_10bit",
        "picture_profile": "S-Log3",
        "white_balance": 5600,
        "shutter": "1/48",
        "iso": 800,
        "focus_mode": "MF",
        "nd_filter": "Variable_ND",
    },

    # Platform teslimat spesifikasyonları
    "deliverable_specs": {
        "youtube_4k_sdr": {
            "video_codec": "libx264",
            "profile": "high",
            "level": "5.1",
            "bitrate": "45M",
            "bitrate_mode": "vbr_2pass",
            "resolution": "3840x2160",
            "fps": 23.976,
            "audio_codec": "aac",
            "audio_bitrate": "320k",
            "audio_sample_rate": 48000,
            "color_space": "bt709",
            "color_primaries": "bt709",
            "color_transfer": "bt709",
        },
        "youtube_4k_hdr": {
            "video_codec": "libx265",
            "profile": "main10",
            "level": "5.1",
            "bitrate": "50M",
            "bitrate_mode": "vbr_2pass",
            "resolution": "3840x2160",
            "fps": 23.976,
            "audio_codec": "aac",
            "audio_bitrate": "320k",
            "audio_sample_rate": 48000,
            "color_space": "bt2020nc",
            "color_primaries": "bt2020",
            "color_transfer": "smpte2084",
            "hdr10": True,
            "max_cll": "1000,400",
            "master_display": "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)",
        },
        "shorts_9x16": {
            "video_codec": "libx264",
            "profile": "high",
            "level": "4.1",
            "bitrate": "20M",
            "bitrate_mode": "cbr",
            "resolution": "1080x1920",
            "fps": 30,
            "audio_codec": "aac",
            "audio_bitrate": "256k",
            "audio_sample_rate": 48000,
            "color_space": "bt709",
            "safe_zones": {"top": 0.15, "bottom": 0.20, "sides": 0.10},
        },
        "reels_9x16": {
            "video_codec": "libx264",
            "profile": "high",
            "level": "4.1",
            "bitrate": "20M",
            "bitrate_mode": "cbr",
            "resolution": "1080x1920",
            "fps": 30,
            "audio_codec": "aac",
            "audio_bitrate": "256k",
            "audio_sample_rate": 48000,
            "color_space": "bt709",
        },
        "tiktok_9x16": {
            "video_codec": "libx264",
            "profile": "high",
            "level": "4.1",
            "bitrate": "16M",
            "bitrate_mode": "cbr",
            "resolution": "1080x1920",
            "fps": 30,
            "audio_codec": "aac",
            "audio_bitrate": "128k",
            "audio_sample_rate": 44100,
            "color_space": "bt709",
        },
        "archival_master": {
            "video_codec": "prores_ks",
            "profile": "4444",
            "resolution": "3840x2160",
            "fps": 23.976,
            "audio_codec": "pcm_s32le",
            "audio_sample_rate": 96000,
            "audio_channels": "multitrack",
        },
    },

    # Segment bazlı görsel parametreler (caption_align çıktısıyla kullanılır)
    "segment_visuals": {
        "enabled": True,
        "verse": {"zoom": 1.00, "pan_speed": 1.0, "hue_amp": 35, "nabiz_pct": 12, "grade": "normal"},
        "chorus": {"zoom": 1.05, "pan_speed": 2.0, "hue_amp": 70, "nabiz_pct": 30, "grade": "intense"},
        "bridge": {"zoom": 0.98, "pan_speed": 0.5, "hue_amp": -20, "nabiz_pct": 0, "grade": "cool"},
        "outro": {"zoom": 1.00, "pan_speed": 1.0, "hue_amp": 35, "nabiz_pct": 12, "grade": "normal"},
    },

    # Backdrop parametreleri
    "backdrop": {
        "blur_sigma_ratio": 0.02,  # 0.045 -> 0.02 for faster rendering
        "pan_margin": 0.14,
        "pan_speed_x": 0.12,
        "pan_speed_y": 0.08,
        "hue_amp": 35,
        "hue_speed": 0.025,
        "vignette_strength": 0.4,
        "brightness": 0.08,
        "saturation": 1.2,
        "curves": "0/0.12 0.5/0.68 1/1",
    },

    # Alt bilgi çubuğu (Lower Third) - Kart YOK, tam ekran video üzerine
    "lower_third": {
        "enabled": True,
        "height_ratio": 0.12,
        "marquee_speed": 60,
        "marquee_repeat": 6,
        "font_size_ratio": 0.032,
        "static_font_ratio": 0.85,
        "gap_ratio": 0.01,
        "font_color": "white@0.95",
        "font_shadow": "black@0.55",
        "font_shadow_offset": 2,
        "progress_bar": {
            "enabled": True,
            "platforms": ["youtube_16x9"],
            "height_ratio": 0.008,
            "margin_ratio": 0.08,
            "bottom_ratio": 0.05,
            "filled": 235,
            "empty": 70,
        },
    },

    # Açılış (Intro) - Sadece YouTube 16:9
    "intro": {
        "enabled": True,
        "hold": 0.9,
        "dissolve": 1.5,
        "platforms": ["youtube_16x9"],
    },

    # Dikey Hook - Sadece Shorts/Reels/TikTok
    "hook": {
        "text": "🔊 Sesini Aç",
        "duration": 2.5,
        "vertical_only": True,
        "position": "top_center",
        "y_ratio": 0.12,
        "font_size_ratio": 0.045,
    },

    # CTA (Call to Action) - Sadece dikey
    "cta": {
        "text": "Abone ol 🔔",
        "duration": 3.0,
        "vertical_only": True,
        "position": "bottom_center",
        "font_size_ratio": 0.04,
    },

    # Loop-friendly (Shorts için son kare cross-dissolve)
    "loop_friendly": {
        "enabled": True,
        "cross_dissolve": 0.5,
        "vertical_only": True,
    },

    # DJ Set özel
    "dj": {
        "sahne_zoom": 1.08,
        "hud_nefes": True,
        "hud_nefes_sure": 8.0,
        "hud_nefes_derinlik": 0.15,
        "portre_spektrum": True,
    },

    # Görsel Dil (gorsel_dil.py entegrasyonu)
    "gorsel_dil": {
        "enabled": True,
        "kapak_konsept": "split",
        "nabiz_budget": 0.20,
        "flash_guvenlik_esigi": 3.0,
    },
}

# --- GERI UYUMLULUK DOLGUSU (config_mod; 2026-10-09) ---
# config.py render cekirdegine indirgendi; alan sabitleri config_mod/* altinda.
# Bu blok YALNIZCA config.py'de OLMAYAN isimleri ekler, mevcut degerleri EZMEZ.
# Yeni alan config_mod'daki dogru dosyaya yazilir, buraya DEGIL.
_MODUL_DOLGULARI = (
    "config_mod.turev_takvimi",
    "config_mod.insan_emeği",
    "config_mod.yayin_ritmi",
    "config_mod.tiktok_kit",
    "config_mod.tiktok_akis",
    "config_mod.youtube_studio",
    "config_mod.youtube_zamanlama",
    "config_mod.platform_optin",
    "config_mod.dj_kesit",
    "config_mod.dj_content_id",
    "config_mod.dj_muzik_stili",
    "config_mod.ingilizce",
    "config_mod.ozgun_metin",
    "config_mod.ses_limiter",
    "config_mod.suno_stil",
    "config_mod.acilis",
)
try:
    for _mod_adi in _MODUL_DOLGULARI:
        try:
            _mod = importlib.import_module(_mod_adi)
        except Exception:
            continue
        for _ad in dir(_mod):
            if _ad.isupper() and _ad not in globals():
                globals()[_ad] = getattr(_mod, _ad)
except Exception:
    pass