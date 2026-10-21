"""Render edilmiş bir projeyi YouTube'a resumable upload ile yükler.

Kullanım:
    python upload/youtube_upload.py --project "projects/beni bırakma"
    python upload/youtube_upload.py --project "projects/beni bırakma" --privacy public
    python upload/youtube_upload.py --project "projects/beni bırakma" --shorts
    python upload/youtube_upload.py --project "projects/beni bırakma" --thumbnail-only
    python upload/youtube_upload.py --thumbnail-only --all   # TÜM projelerin thumbnail'ini tek seferde düzeltir
    python upload/youtube_upload.py --project "projects/beni bırakma" --description-only
    python upload/youtube_upload.py --description-only --all   # TÜM projelerin açıklamasını tek seferde düzeltir

meta.json'dan title/theme okur, output/youtube_16x9.mp4'ü yükler (upload_video),
sonucu projects/<isim>/state.json'a yazar. --shorts ile output/shorts_9x16.mp4
AYRI bir YouTube video'su (Short) olarak yüklenir (upload_short) — küçük/yeni
kanallar için Shorts akışı, uzun format önerilen videolar sisteminden çok daha
erişilebilir bir keşif kanalı olduğu için. auto_process.py ikisini de otomatik
tetikler (önce uzun format, sonra Short — Short'un açıklamasına tam versiyona
bağlantı eklemek için).

DJ Sets (dj_sets/): Series-based metadata (Cercle/HÖR/Boiler Room best practices)
otomatik kullanılır. meta.json'da "series" varsa yeni format devreye girer.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # upload/ dizini için

import config
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import social_text
from social_text import build_caption, hashtag, pick_deterministic, resolve_language
import ozgun_metin as OM
from youtube_auth import get_authenticated_service

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}



def _youtube_playlist_ids() -> dict:
    """Kanal playlist ID'leri — TEK kaynak: upload/playlist_ids.json.

    NEDEN AYRI DOSYA: config.py'de DJ_SERIES icinde var ama tarz playlist'leri
    (pop/hiphop/...) config.THEMES'te YOK; hepsi upload/playlist_ids.json'da.
    Ayni listenin iki yerde tutulmasi = birinin sessizce bos kalma riski
    (2026-10-19'da ayni sey oldu: aciklamada 'Playlist:' satiri hic cikmiyordu).
    """
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist_ids.json")
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def is_dj_set(meta: dict) -> bool:
    """Check if this is a DJ set with series-based metadata."""
    return "series" in meta and meta.get("series")


def build_snippet(meta: dict, baslik_kalibi: str | None = None) -> dict:
    """Uzun format (youtube_16x9.mp4) açıklaması. Dil resolve_language() ile
    belirlenir (stile göre otomatik, meta.json'daki "language" öncelikli) —
    DJ Famous ("dj" teması, "en") gibi İngilizce projelerde de doğru dilde
    üretilsin diye (eskiden burası hardcoded Türkçe idi, DJ Famous'un uzun
    format videosu bile Türkçe açıklama alıyordu). Hook + keşfet/tür
    hashtag'leri + etkileşim sorusu artık Shorts/TikTok/Instagram'ın kullandığı
    build_caption() ile AYNI havuzlardan (config.HOOK_LINES/DISCOVERY_HASHTAGS/
    ENGAGEMENT_QUESTIONS, aynı deterministik seçim) geliyor — eskiden bu üçü de
    sadece kısa-format caption'da vardı, uzun format elinde tek marka
    hashtag'iyle (#FamousMusicStudio) kalıyordu. Link bloğu (Instagram/TikTok/
    Website) uzun formata ÖZGÜ kalıyor — build_caption bunu içermiyor çünkü
    Instagram/TikTok caption'ında dış link YOK (bkz. build_caption docstring).
    
    baslik_kalibi: opsiyonel başlık kalıbı ID'si (K1, K2, K3). Verilirse
    o kalıp kullanılır, verilmezse varsayılan (K1) kullanılır.
    Hikaye (meta['hikaye']) varsa hook'tan sonra, link bloğundan önce eklenir."""

    # DJ Set with series? Use new series-based metadata
    if is_dj_set(meta):
        return build_dj_set_snippet(meta)

    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", [])
    links = config.SOCIAL_LINKS
    lang = resolve_language(meta)

    if lang == "en":
        discovery_hashtags = config.DISCOVERY_HASHTAGS_EN
        hook = pick_deterministic(title, config.HOOK_LINES_EN)
        engagement_question = pick_deterministic(title, config.ENGAGEMENT_QUESTIONS_EN, salt=7)
        follow_line = "Follow for more tracks 🎵"
        # DJ Famous setleri için kullanıcının referans aldığı bir YouTube DJ-mix
        # kanalının (ör. "GUESTMIX | ... | MENU") açıklama formatı: kısa,
        # doğrudan "kanala abone ol" + "Instagram'da takip et" satırları,
        # handle'a gerçekten tıklanabilir (@mention) bağlantı veriyor —
        # kullanıcı isteği: "açıklamalarda bu tarz olsun" (2026-09-07).
        if theme_key == "dj":
            follow_line = (
                f"Subscribe to the {config.STATIC_LABEL_TEXT} channel 👉 "
                f"@{config.YOUTUBE_HANDLE}\n"
                f"Follow the journey on Instagram 👉 {links['instagram']}"
            )
        else:
            # NEDEN: sadece "Follow for more tracks" ABONE OLUŞTURMAZ —
            # tıklanabilir @mention şart. Tüm temalarda aynı blok
            # (tek kaynak: social_text.aciklama_abone_bloku).
            follow_line = (
                f"Subscribe to the {config.STATIC_LABEL_TEXT} channel 👉 "
                f"@{config.YOUTUBE_HANDLE}"
            )
    else:
        discovery_hashtags = config.DISCOVERY_HASHTAGS
        hook = pick_deterministic(title, config.HOOK_LINES)
        engagement_question = pick_deterministic(title, config.ENGAGEMENT_QUESTIONS, salt=7)
        follow_line = "Yeni şarkılar için takipte kalın 🎵"
        # "dj" (DJ Famous) enstrümantal/canlı set, "sözleri" arama niyeti taşımıyor —
        # sadece ana kataloğun şarkı temalarına uygulanıyor.
        if theme_key == "dj":
            follow_line = (
                f"Subscribe to the {config.STATIC_LABEL_TEXT} channel 👉 "
                f"@{config.YOUTUBE_HANDLE}\n"
                f"Follow the journey on Instagram 👉 {links['instagram']}"
            )
        else:
            # NEDEN: sadece "takipte kalın" ABONE OLUŞTURMAZ — tıklanabilir
            # @mention şart. Tüm temalarda aynı blok (tek kaynak:
            # social_text.aciklama_abone_bloku).
            follow_line = (
                f"{config.STATIC_LABEL_TEXT} kanalına abone ol 👉 "
                f"@{config.YOUTUBE_HANDLE}"
            )

    # Hikaye paragrafı (hook'tan sonra, link bloğundan önce)
    hikaye = OM.aciklama_paragrafi(meta)
    if hikaye:
        # Hikaye varsa: hook + hikaye + boş satır + follow_line + linkler + destek + engagement + hashtags
        description = (
            f"{hook}\n\n{hikaye}\n\n"
            f"{follow_line}\n\n"
            f"📷 Instagram: {links['instagram']}\n"
            f"🎵 TikTok: {links['tiktok']}\n"
            f"🌐 Website: {links['website']}\n"
        )
    else:
        # Hikaye yoksa: eski format (hook + boş satır + follow_line + linkler + destek + engagement + hashtags)
        description = (
            f"{hook}\n\n{title} | {config.STATIC_LABEL_TEXT}\n\n"
            f"{follow_line}\n\n"
            f"📷 Instagram: {links['instagram']}\n"
            f"🎵 TikTok: {links['tiktok']}\n"
            f"🌐 Website: {links['website']}\n"
        )

    # DESTEK (2026-10-08) — Ko-fi satiri:
    _kofi = getattr(config, "KOFI_URL", "") or ""
    if _kofi:
        _destek_satiri = (
            f"\u2615 Support us: {_kofi}\n"
            if lang == "en"
            else f"\u2615 Bizi destekle: {_kofi}\n"
        )
    else:
        _destek_satiri = ""

    description += f"{_destek_satiri}\n{engagement_question}\n\n"

    # AI Disclosure (REQUIRED by YouTube for AI-generated content)
    description += "\n\n🤖 AI DISCLOSURE:\n"
    if lang == "en":
        description += "This video contains AI-generated music and visuals.\n"
        description += "Music: Suno AI | Visuals: AI-generated | Edit: Automated\n"
    else:
        description += "Bu video AI destekli müzik ve görseller içerir.\n"
        description += "Müzik: Suno AI | Görseller: AI-üretilmiş | Edit: Otomatik\n"

    genre_hashtags = [hashtag(theme["label"])] + [hashtag(t) for t in theme.get("related", [])]
    hashtags = " ".join(config.BRAND_HASHTAGS + discovery_hashtags + genre_hashtags)
    description += hashtags

    # CTA Strengthening (P0 #4) -- Cercle/Boiler Room best practices
    # Add streaming links, playlist links, credits
    description += "\n\n🎵 LISTEN ON:\n"
    description += f"Spotify: {config.SOCIAL_LINKS.get('spotify', 'https://spotify.com/artist/famousmusicstudio')}\n"
    description += f"Apple Music: {config.SOCIAL_LINKS.get('apple_music', 'https://music.apple.com/artist/famousmusicstudio')}\n"
    description += "\n"
    
    # Playlist reference
    theme_label = theme["label"]
    pid_map = _youtube_playlist_ids()
    playlist_id = pid_map.get(theme_key, '')
    all_songs_id = pid_map.get('_tum_sarkilar', '')
    if playlist_id:
        description += f"📋 {theme_label} Playlist: https://youtube.com/playlist?list={playlist_id}\n"
    if all_songs_id:
        description += f"📋 Tüm Şarkılar: https://youtube.com/playlist?list={all_songs_id}\n"
    description += "\n"
    
    # Credits
    description += "🎬 CREDITS:\n"
    description += f"Artist: {config.STATIC_LABEL_TEXT}\n"
    description += f"Music & Vocals: Suno AI\n"
    description += f"Visuals: AI-generated\n"
    description += f"Edit: Automated\n"
    description += "\n"

    # Title template selection ("Sözleri" kalıpları yalnız vokal katalog için:
    # "dj" enstrümantal setlerde söz araması niyeti yok, meta başlığı aynen kullanılır.)
    if baslik_kalibi and theme_key != "dj":
        k = OM.kalip(baslik_kalibi) or OM.kalip("K1")
        if k:
            alanlar = {"title": title, "tur": theme["label"],
                       "baslik_eki": str(meta.get("baslik_eki") or "").strip()}
            if k.get("gerekli") and not alanlar.get(k["gerekli"]):
                k = OM.kalip("K1")
            video_title = k["sablon"].format(**alanlar)
        else:
            video_title = f"{title} (Sözleri) | Türkçe {theme['label']} Şarkısı"
    elif theme_key == "dj":
        video_title = title
    else:
        video_title = f"{title} (Sözleri) | Türkçe {theme['label']} Şarkısı"

    lyrics_tags = [] if theme_key == "dj" else [f"{title} sözleri", "sözleri", "lyrics"]
    meta_tags = [hashtag(t) for t in meta.get("tags", [])]
    tags = genre_tags + [config.STATIC_LABEL_TEXT] + [h.lstrip("#") for h in discovery_hashtags] + meta_tags + lyrics_tags

    return {
        "title": video_title,
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


def build_dj_set_snippet(meta: dict) -> dict:
    """Build YouTube snippet for DJ sets using series-based metadata (Cercle/HÖR/Boiler Room style)."""
    series_key = meta.get("series")
    if not series_key:
        return build_snippet(meta)  # Fallback

    from config import get_dj_series, get_series_location
    series = get_dj_series(series_key)
    if not series:
        return build_snippet(meta)

    title = meta.get("title", "Untitled")
    episode = meta.get("episode", 1)
    location = meta.get("location") or get_series_location(series_key)
    landmark = location.get("landmark", location.get("city", ""))
    city = location.get("city", "")
    country = location.get("country", "")
    route = location.get("route", "")
    story = location.get("story", "")
    gps = location.get("gps", "")

    # Get tracklist for chapters
    tracklist = meta.get("tracklist", [])

    # Build description (Cercle style — matches Cercle/Boiler Room/HÖR best practices)
    desc_parts = []

    # Hook lines (first 2 lines visible in search)
    hook_lines = [
        f"DJ Famous playing {series['brand'].lower()} at {landmark}, {city}.",
        f"Episode {episode} of {series['brand']} — {series['tagline']}",
    ]
    desc_parts.extend(hook_lines)
    desc_parts.append("")

    # Tracklist with timestamps = YouTube chapters (Cercle style with BPM/Key)
    if tracklist:
        desc_parts.append("🎧 TRACKLIST:")
        for i, track in enumerate(tracklist):
            ts = track.get("timestamp", "00:00")
            tr_title = track.get("title", f"Track {i+1}")
            tr_artist = track.get("artist", "Unknown")
            bpm = track.get("bpm", "")
            key = track.get("key", "")
            extra = f" [{bpm} BPM, {key}]" if bpm or key else ""
            desc_parts.append(f"{ts} {tr_title} - {tr_artist}{extra}")
        desc_parts.append("")

    # Location story (Cercle style)
    if story:
        desc_parts.append("📍 LOCATION STORY:")
        desc_parts.append(story)
        if gps:
            desc_parts.append(f"GPS: {gps}")
        desc_parts.append("")

    # BÜYÜME (madde 14): Türkçe mekan hikayesi varsa ayrı paragraf — global
    # format bozulmadan yerel aidiyet kurulur.
    story_tr = location.get("story_tr", "")
    if story_tr:
        desc_parts.append("📍 MEKAN HİKAYESİ:")
        desc_parts.append(story_tr)
        desc_parts.append("")

    # Credits (Cercle style — full production credits)
    desc_parts.append("🎬 CREDITS:")
    desc_parts.append(f"Artist: DJ Famous")
    desc_parts.append(f"Series: {series['brand']} (Ep {episode})")
    desc_parts.append(f"Location: {landmark}, {city}, {country}")
    if route:
        desc_parts.append(f"Route: {route}")
    desc_parts.append(f"Produced by: DJ Famous")
    desc_parts.append(f"Directed by: DJ Famous")
    desc_parts.append(f"Sound Design: DJ Famous")
    desc_parts.append(f"Visual Art: AI-generated (Midjourney/DALL-E)")
    desc_parts.append("")

    # Connect links
    desc_parts.append("🔗 CONNECT:")
    desc_parts.append(f"YouTube: {config.SOCIAL_LINKS['youtube']}")
    desc_parts.append("Instagram: https://instagram.com/djfamous")
    desc_parts.append("Spotify: https://spotify.com/artist/djfamous")
    desc_parts.append("Apple Music: https://music.apple.com/artist/djfamous")
    desc_parts.append("TikTok: https://tiktok.com/@djfamous")
    desc_parts.append("Bluesky: https://bsky.app/profile/djfamous.bsky.social")
    desc_parts.append("Telegram: https://t.me/djfamous")
    desc_parts.append("")

    # Streaming links (Cercle style)
    desc_parts.append("🎵 LISTEN ON:")
    desc_parts.append("Spotify: https://spotify.com/artist/djfamous")
    desc_parts.append("Apple Music: https://music.apple.com/artist/djfamous")
    desc_parts.append("")

    # Series links
    desc_parts.append(f"📺 {series['brand'].upper()}:")
    playlist_id = series["youtube"].get("playlist_id", "")
    if playlist_id:
        desc_parts.append(f"Playlist: https://youtube.com/playlist?list={playlist_id}")
    desc_parts.append(f"\U0001f514 Subscribe to {config.STATIC_LABEL_TEXT} — "
                      f"new set every week \U0001f449 @{config.YOUTUBE_HANDLE}")
    desc_parts.append("")

    # BÜYÜME (madde 4): Kendi Spotify playlist'leri (Anjunadeep doktrini)
    # Boşken açıklamaya blok EKLENMEZ — doldurunca otomatik düşer.
    sp_lists = getattr(config, "SPOTIFY_CALMA_LISTELERI", {})
    if sp_lists:
        desc_parts.append("🎵 SPOTIFY CALMA LİSTELERİMİZ:")
        for name, url in sp_lists.items():
            desc_parts.append(f"  {name}: {url}")
        desc_parts.append("")

    # AI Disclosure (REQUIRED by YouTube for AI-generated content)
    desc_parts.append("🤖 AI DISCLOSURE:")
    desc_parts.append("This video contains AI-generated music and visuals.")
    desc_parts.append("Music: Suno AI | Visuals: Midjourney/DALL-E | Edit: Premiere Pro")
    desc_parts.append("")

    # Hashtags
    hashtags = series["youtube"].get("hashtags", "")
    if hashtags:
        desc_parts.append(hashtags)

    description = "\n".join(desc_parts)

    # Ensure description <= 5000 chars
    if len(description) > 5000:
        description = description[:4997] + "..."

    # Build tags (expanded for SEO)
    tags = []
    tags.extend(series["youtube"].get("tags_base", []))
    tags.extend(["dj famous", series_key.replace("_", " "), city.lower(), country.lower()])
    if landmark:
        tags.append(landmark.lower())
    # Add SEO keywords
    seo = series.get("seo", {})
    if seo.get("primary_keyword"):
        tags.append(seo["primary_keyword"])
    tags.extend(seo.get("secondary_keywords", []))
    # Add genre variations
    tags.extend(["melodic techno mix", "progressive house mix", "dj set 2024", "best dj sets", "rooftop dj set", "sunset dj", "chill electronic"])
    # Add location variations
    tags.extend([city.lower().replace(" ", ""), country.lower().replace(" ", "")])
    # Deduplicate
    tags = list(dict.fromkeys([t.strip().lower() for t in tags if t.strip()]))

    # Limit to 500 chars total (YouTube limit)
    tags_str = ", ".join(tags)
    if len(tags_str) > 500:
        tags_str = tags_str[:497] + "..."

    # Title from series format
    title_format = series["youtube"]["title_format"]
    video_title = title_format.format(artist="DJ Famous", landmark=landmark, city=city, route=route)
    if len(video_title) > 100:
        video_title = video_title[:97] + "..."

    return {
        "title": video_title,
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


# =============================================================================
# KESİT (ikinci dalga) YÜKLEME UCU (2026-10-21)
# =============================================================================

def _dakika_damgasi(saniye: float) -> str:
    """Saniyeyi "M:SS" biçimine çevirir (kesit başlığı/acıklaması için).

    KURAL: saniye KESİLİR (yuvarlanmaz) — 59.9 -> "0:59", 332.53 -> "5:32".
    Negatif/bozuk damga "0:00" olur (asla "-1:-5" basılmaz).
    """
    try:
        sn = float(saniye)
    except (TypeError, ValueError):
        sn = 0.0
    if sn < 0:
        sn = 0.0
    toplam = int(sn)
    return "%d:%02d" % (toplam // 60, toplam % 60)


def build_clip_snippet(meta: dict, full_video_id: str | None = None,
                       saniye: float = 0.0) -> dict:
    """Kesit (set içinden ikinci dalga) için YouTube snippet'i.

    NEDEN AYRI FONKSİYON: Kesit, setin KENDİ Shorts'uyla aynı başlığı
    alırsa kanalda neredeyse aynı iki video aynı adla durur — bu, kanalın
    en büyük riski olan "inauthentic content" politikasının tarifi. Farkı
    sağlayan şey DAKİNA DAMGASI ("5:32") — yorum değil, garanti.

    video_id yoksa (set henüz yüklenmedi) KIRIK link basılmaz.
    """
    baslik = meta.get("title", "DJ Set")
    damga = _dakika_damgasi(saniye)
    lang = resolve_language(meta)

    # İlk satır: küratörlük cümlesi + damga (+ tam set linki)
    ilk = "A different moment from the same set — %s" % damga
    if full_video_id:
        ilk += " · https://youtu.be/%s" % full_video_id
    description = ilk
    if lang == "en":
        description += ("\n\n🎧 The full set is on the channel. "
                        "Which moment would you keep?")
    else:
        description += ("\n\n🎧 Setin tamamı kanalda. "
                        "Bu anlardan hangisini seçerdin?")
    description += social_text.aciklama_abone_bloku(lang)
    if lang == "en":
        description += ("\n\n🤖 AI DISCLOSURE:\n"
                        "This Short contains AI-generated music and visuals.\n")
    else:
        description += ("\n\n🤖 AI BEYANI:\n"
                        "Bu Short AI destekli müzik ve görseller içerir.\n")

    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", [])
    discovery = (config.DISCOVERY_HASHTAGS_EN if lang == "en"
                 else config.DISCOVERY_HASHTAGS)
    tags = genre_tags + [config.STATIC_LABEL_TEXT, "Shorts"] + [
        h.lstrip("#") for h in discovery]

    return {
        "title": "%s %s #Shorts" % (baslik, damga),
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


def _golden_publish_at(gun: int) -> str:
    """`gun` gün SONRAKİ golden-hour penceresine zamanlama damgası (ISO, Z).

    TUZAK (2026-10-21): `config.next_golden_publish_time` "verilen an ZATEN
    golden-hour penceresindeyse None" döner ("hemen yayınla"). O None
    "zamanlama yok"a çevrilirse kesit BUGÜN yayınlanır — 3 günlük
    ertelemenin tamamen kaybolması, hattın var oluş sebebi olan hacim
    kısıtının sessizce delinmesi. Burada None ASLA dönmez: hedef günün
    penceresi geçmişse SONRAKİ güne kaydırılır.
    """
    simdi = datetime.now(config.TR_TZ)
    hedef = simdi + timedelta(days=int(gun))
    adaylar = []
    for gun_offset in range(0, 4):
        gun_basi = (hedef + timedelta(days=gun_offset)).replace(
            minute=0, second=0, microsecond=0)
        for bas, _son in config.GOLDEN_HOURS:
            adaylar.append(gun_basi.replace(hour=int(bas)))
    uygun = [a for a in adaylar if a >= hedef]
    if not uygun:
        # Teorik olarak imkânsız; yine de None DÖNME.
        uygun = [hedef.replace(hour=int(config.GOLDEN_HOURS[0][0]))]
    secilen = min(uygun)
    return secilen.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def build_shorts_snippet(meta: dict, full_video_id: str | None = None) -> dict:
    """Shorts (shorts_9x16.mp4, 45sn highlight) için ayrı bir snippet — uzun format
    künyesi yerine TikTok/Instagram'la AYNI kısa-format caption'ı kullanıyor
    (social_text.build_caption: hook + hashtag'ler + etkileşim sorusu), çünkü
    Shorts algoritması da hashtag/hook odaklı kısa video mantığıyla çalışıyor.
    Başlığa "#Shorts" ekleniyor (YouTube'un Shorts sınıflandırması için ek sinyal —
    video zaten <=60sn ve dikey olduğu için asıl belirleyici bu değil ama önerilen
    pratik). full_video_id verilmişse, izleyiciyi kanaldaki tam versiyona
    yönlendiren bir satır ekleniyor."""

    # DJ Set with series? Use series-based shorts metadata
    if is_dj_set(meta):
        return build_dj_set_shorts_snippet(meta, full_video_id)

    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", [])

    description = build_caption(meta)
    # NEDEN burada: lang asagida "AI Disclosure" icin hesaplaniyordu; abone
    # blogu de ayni dili kullaniyor, o yuzden once burada hesaplaniyor.
    lang = resolve_language(meta)
    if full_video_id:
        description += f"\n\n\U0001f3a7 Şarkının tamamı kanalımızda: https://youtu.be/{full_video_id}"
    # ABONE CTA — Shorts'a özel. NEDEN: Shorts izleyicisi akışta kayıp
    # ediyor; açıklamadaki @handle en görünür abone kaldıracı.
    description += social_text.aciklama_abone_bloku(lang)

    # AI Disclosure (REQUIRED by YouTube for AI-generated content)
    if lang == "en":
        description += "\n\n🤖 AI DISCLOSURE:\nThis Short contains AI-generated music and visuals.\n"
    else:
        description += "\n\n🤖 AI BEYANI:\nBu Short AI destekli müzik ve görseller içerir.\n"

    discovery_hashtags = config.DISCOVERY_HASHTAGS_EN if lang == "en" else config.DISCOVERY_HASHTAGS
    tags = genre_tags + [config.STATIC_LABEL_TEXT, "Shorts"] + [h.lstrip("#") for h in discovery_hashtags]

    return {
        "title": f"{title} #Shorts",
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


def build_dj_set_shorts_snippet(meta: dict, full_video_id: str | None = None) -> dict:
    """Build YouTube Shorts snippet for DJ sets using series-based metadata."""
    series_key = meta.get("series")
    if not series_key:
        return build_shorts_snippet(meta, full_video_id)

    from config import get_dj_series, get_series_location
    series = get_dj_series(series_key)
    if not series:
        return build_shorts_snippet(meta, full_video_id)

    title = meta.get("title", "Untitled")
    episode = meta.get("episode", 1)
    location = meta.get("location") or get_series_location(series_key)
    landmark = location.get("landmark", location.get("city", ""))
    city = location.get("city", "")

    # Shorts description: hook + location + track highlight + AI disclosure + link to full
    hook = f"DJ Famous @ {landmark}, {city} — {series['brand']} Ep {episode}"
    desc_parts = [
        hook,
        f"",
        f"🎧 {series['brand']} Episode {episode}",
        f"📍 {landmark}, {city}",
    ]

    # Add track highlight if available
    tracklist = meta.get("tracklist", [])
    if tracklist:
        # Show first 3 tracks as preview
        for track in tracklist[:3]:
            ts = track.get("timestamp", "00:00")
            tr_title = track.get("title", "")
            desc_parts.append(f"{ts} {tr_title}")
        if len(tracklist) > 3:
            desc_parts.append(f"... +{len(tracklist) - 3} more tracks")
        desc_parts.append("")

    if full_video_id:
        desc_parts.append(f"🎧 Full set: https://youtu.be/{full_video_id}")
        desc_parts.append("")

    # Subscribe CTA — NEDEN handle ile: "@DJFamous" başka bir kanal,
    # "Subscribe for more sets!" ise tıklanabilir değil. Gerçek kanal:
    # @Famous_musics_studio (config.YOUTUBE_HANDLE).
    desc_parts.append(f"\U0001f514 Subscribe to {config.STATIC_LABEL_TEXT} — "
                      f"new set every week \U0001f449 @{config.YOUTUBE_HANDLE}")
    desc_parts.append("")

    # AI Disclosure (REQUIRED by YouTube for AI-generated content)
    desc_parts.append("🤖 AI DISCLOSURE:")
    desc_parts.append("This Short contains AI-generated music and visuals.")
    desc_parts.append("👉 Remember to toggle 'AI-generated content' label in TikTok/Reels!")
    desc_parts.append("")

    # Series hashtags
    hashtags = series["youtube"].get("hashtags", "")
    if hashtags:
        desc_parts.append(hashtags)
    desc_parts.append("#Shorts #DJFamous #AIGenerated #MusicAI")

    description = "\n".join(desc_parts)

    # Tags (expanded for Shorts SEO)
    tags = series["youtube"].get("tags_base", []) + [config.STATIC_LABEL_TEXT, "Shorts", "DJFamous", "AIGenerated", "MusicAI", "DJSet", "ShortsMusic"]
    tags = list(dict.fromkeys([t.strip().lower() for t in tags if t.strip()]))

    return {
        "title": f"{title} #Shorts",
        "description": description,
        "tags": tags,
        "categoryId": "10",
    }


def _upload(video_path: str, snippet: dict, privacy: str, publish_at: str | None = None) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    youtube = get_authenticated_service()

    status = {
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": True,
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = privacy

    body = {"snippet": snippet, "status": status}

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    if publish_at:
        print(f"  yükleniyor: {snippet['title']} (zamanlı: {publish_at}'te public olacak)")
    else:
        print(f"  yükleniyor: {snippet['title']} ({privacy})")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=3)
            if status:
                print(f"    %{int(status.progress() * 100)}")
        except HttpError as e:
            print(f"  HATA: {e}")
            raise

    return response["id"]


def _find_cover(project_dir: str) -> str | None:
    for name in COVER_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def _find_cover_vertical(project_dir: str) -> str | None:
    """Shorts thumbnail'i için 9:16 kapak — yoksa (eski projeler) 16:9 cover.png'ye
    düşülür (hiç thumbnail'siz kalmaktan iyidir, sadece Shorts'un dikey kutusunda
    üstte/altta ince bir şerit görünebilir)."""
    for name in COVER_VERTICAL_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return _find_cover(project_dir)


def _prepare_thumbnail_jpeg(cover_path: str) -> str:
    """YouTube thumbnails.set 2MB sınırı var — procedural PNG kapaklar (bokeh
    dokusu yüzünden) bunu kolayca aşabiliyor (bir projede 2.7MB'a çıktığı
    görüldü). Kaynak boyutuna bakmadan HER ZAMAN güvenli bir JPEG'e yeniden
    kodluyoruz (PNG boyutu içerik gürültüsüne göre öngörülemez), geçici bir
    dosyaya yazıp döndürüyoruz — çağıran temizlemekten sorumlu."""
    tmp_path = cover_path + "._thumb_tmp.jpg"
    cmd = ["ffmpeg", "-y", "-i", cover_path, "-q:v", "3", tmp_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Thumbnail JPEG'e dönüştürülemedi: {result.stderr[-500:]}")
    return tmp_path


def upload_thumbnail(youtube, video_id: str, project_dir: str, vertical: bool = False) -> None:
    """cover.jpg/png'yi (ya da Shorts için cover_vertical.jpg/png'yi) videonun
    gerçek YouTube thumbnail'i olarak ayarlar. Bunsuz YouTube videodan rastgele
    bir kare seçip thumbnail yapıyordu — kartın başlıksız hâli (art.jpg)
    görünüyordu, tasarlanan başlıklı kapak hiç kullanılmıyordu (kullanıcı geri
    bildirimiyle tespit edildi). vertical=True (Shorts) iken 9:16 kapak
    kullanılır — uzun-format için 16:9 kapağın aynısını kullanmak dikey
    thumbnail kutusunda üstte/altta çirkin bir şeride yol açıyordu (yine
    kullanıcı geri bildirimiyle tespit edildi)."""
    cover_path = _find_cover_vertical(project_dir) if vertical else _find_cover(project_dir)
    if not cover_path:
        print("  Thumbnail atlandı: cover.jpg/png bulunamadı")
        return

    tmp_path = _prepare_thumbnail_jpeg(cover_path)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(tmp_path, mimetype="image/jpeg"),
        ).execute()
        print("  Thumbnail: tamam")
    finally:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)


def _update_state(project_dir: str, fields: dict) -> None:
    import state_io
    state = state_io.load_state(os.path.join(project_dir, "state.json"))
    state.update(fields)
    state_io.durum_yaz(project_dir, state)


def _compute_publish_at(privacy: str, schedule: bool) -> str | None:
    """privacy="public" ve schedule=True ise, şu an bir golden-hour penceresinin
    (config.GOLDEN_HOURS) dışındaysak bir sonraki pencerenin başlangıcını UTC
    ISO8601 ("...Z") olarak döner — içindeysek (ya da schedule kapalıysa/privacy
    public değilse) None döner, hemen (zamanlamasız) yüklenir."""
    if privacy != "public" or not schedule:
        return None
    target = config.next_golden_publish_time()
    if target is None:
        return None
    return target.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def upload_video(project_dir: str, privacy: str, schedule: bool = True) -> str:
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    meta = load_meta(project_dir)
    
    # DJ Set with series? Use series-based metadata
    if is_dj_set(meta):
        snippet = build_dj_set_snippet(meta)
    else:
        # Başlık kalıbı seçimi (YOUTUBE_BASLIK_ROTASYONU_AKTIF aktifse)
        baslik_kalibi = None
        if getattr(config, "YOUTUBE_BASLIK_ROTASYONU_AKTIF", False):
            import uyumluluk
            klasorler = list(uyumluluk.proje_klasorleri())
            onceki = OM.onceki_kalip(klasorler, haric=project_dir)
            baslik_kalibi = OM.kalip_sec(meta, onceki)
        snippet = build_snippet(meta, baslik_kalibi=baslik_kalibi)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtu.be/{video_id}")

    youtube = get_authenticated_service()
    try:
        upload_thumbnail(youtube, video_id, project_dir, vertical=False)
    except Exception as e:
        print(f"  Thumbnail HATA: {e}")

    state_fields = {
        "youtube_video_id": video_id,
        "youtube_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_privacy": privacy,
        "youtube_publish_at": publish_at,
    }
    if not is_dj_set(meta):
        baslik_kalibi = None
        if getattr(config, "YOUTUBE_BASLIK_ROTASYONU_AKTIF", False):
            import uyumluluk
            klasorler = list(uyumluluk.proje_klasorleri())
            onceki = OM.onceki_kalip(klasorler, haric=project_dir)
            baslik_kalibi = OM.kalip_sec(meta, onceki)
        if baslik_kalibi:
            state_fields["youtube_baslik_kalibi"] = baslik_kalibi
    _update_state(project_dir, state_fields)
    return video_id


def upload_short(project_dir: str, privacy: str, full_video_id: str | None = None, schedule: bool = True) -> str:
    """shorts_9x16.mp4'ü uzun formattan BAĞIMSIZ, ayrı bir YouTube video'su (Short)
    olarak yükler. full_video_id verilmişse açıklamada tam versiyona bağlantı verir."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    meta = load_meta(project_dir)

    # DJ Set with series? Use series-based metadata
    if is_dj_set(meta):
        snippet = build_dj_set_shorts_snippet(meta, full_video_id)
    else:
        snippet = build_shorts_snippet(meta, full_video_id)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtube.com/shorts/{video_id}")

    try:
        upload_thumbnail(get_authenticated_service(), video_id, project_dir, vertical=True)
    except Exception as e:
        print(f"  Thumbnail HATA: {e}")

    _update_state(project_dir, {
        "youtube_shorts_video_id": video_id,
        "youtube_shorts_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_shorts_privacy": privacy,
        "youtube_shorts_publish_at": publish_at,
    })
    return video_id


def upload_clip(project_dir: str, clip_name: str, full_video_id: str | None = None,
                bas_sn: float = 0.0, gun_ertele: int = 0,
                privacy: str = "public") -> tuple[str, str | None]:
    """Kesit klibini (clip_NN.mp4) YouTube'a yükler — ERTELENMIŞ golden hour'a.

    DÖNER: (video_id, publish_at_iso)

    NEDEN `gun_ertele`: kesit, setin KENDİ Shorts'undan SONRA yayınlanır.
    Bu bir "güzel olur" değil, HAFTALIK HACİM KISITININ KENDİSİ — erteleme
    kaybolursa kanalda aynı anda birden fazla kesit düşer.

    NEDEN state'e YAZMAZ: tekrar gönderimi engelleyen anahtarları yazan
    taraf `dj_clips.kesit_yayinla`dır. Burada yazılırsa iki taraf da yazar
    ve ikinci koşu aynı kesidi tekrar yükleyebilir.
    """
    video_path = os.path.join(project_dir, "output", clip_name)
    if not os.path.isfile(video_path):
        raise FileNotFoundError("Kesit dosyası yok: %s" % video_path)
    meta = load_meta(project_dir)
    snippet = build_clip_snippet(meta, full_video_id, bas_sn)

    if gun_ertele:
        publish_at = _golden_publish_at(gun_ertele)
    else:
        publish_at = _compute_publish_at(privacy, True)

    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print("  tamam: https://youtube.com/shorts/%s" % video_id)
    return video_id, publish_at

def fix_thumbnail(project_dir: str) -> None:
    """Zaten yüklenmiş video(lar) için thumbnail'i (cover.jpg/cover_vertical.jpg)
    videonun gerçek YouTube thumbnail'i olarak ayarlar — videoyu tekrar
    yüklemeden. state.json'dan youtube_video_id VE (varsa)
    youtube_shorts_video_id okur, ikisini de dener."""
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        print(f"  HATA: {state_path} yok — bu proje hiç yüklenmemiş.")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    shorts_id = state.get("youtube_shorts_video_id")
    if not video_id and not shorts_id:
        print("  HATA: state.json'da youtube_video_id/youtube_shorts_video_id yok.")
        return

    youtube = get_authenticated_service()
    if video_id:
        print("  uzun format:")
        upload_thumbnail(youtube, video_id, project_dir, vertical=False)
    if shorts_id:
        print("  Shorts:")
        try:
            upload_thumbnail(youtube, shorts_id, project_dir, vertical=True)
        except Exception as e:
            print(f"  Shorts thumbnail HATA: {e}")


def fix_description(project_dir: str) -> None:
    """Zaten yüklenmiş video(lar) için açıklamayı (description/title/tags) güncel
    build_snippet()/build_shorts_snippet() çıktısıyla YENİDEN yazar — video
    upload_thumbnail'daki gibi, videoyu tekrar yüklemeden. Bazı eski videolar
    (özellikle Shorts) açıklama eklenmeden ÖNCEKI bir kod sürümüyle yüklendiği
    için eksik/boş açıklamayla kalmıştı (kullanıcı geri bildirimiyle tespit
    edildi, 2026-09-05) — bu onu düzeltir. state.json'dan youtube_video_id VE
    (varsa) youtube_shorts_video_id okur, ikisini de dener. videos().update
    part="snippet" TÜM snippet alanlarını (categoryId dahil) üzerine yazdığı
    için build_snippet/build_shorts_snippet'in ürettiği TAM snippet gönderiliyor,
    eksik alan bırakmıyor.
    
    Başlık kalıbı: state.json'daki youtube_baslik_kalibi kullanılır (varsa).
    Eski videolar (kalıp kaydı yok) K1'de kalır (geriye uyumluluk)."""
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        print(f"  HATA: {state_path} yok — bu proje hiç yüklenmemiş.")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    shorts_id = state.get("youtube_shorts_video_id")
    if not video_id and not shorts_id:
        print("  HATA: state.json'da youtube_video_id/youtube_shorts_video_id yok.")
        return

    meta = load_meta(project_dir)
    youtube = get_authenticated_service()
    
    # DJ Set with series? Use series-based metadata
    if is_dj_set(meta):
        long_snippet = build_dj_set_snippet(meta)
        shorts_snippet = build_dj_set_shorts_snippet(meta, video_id)
    else:
        # Eski videolar için başlık kalıbı: state'den oku, yoksa K1 (varsayılan)
        baslik_kalibi = state.get("youtube_baslik_kalibi", "K1")
        long_snippet = build_snippet(meta, baslik_kalibi=baslik_kalibi)
        shorts_snippet = build_shorts_snippet(meta, video_id)

    if video_id:
        print("  uzun format:")
        youtube.videos().update(part="snippet", body={"id": video_id, "snippet": long_snippet}).execute()
        print("  Açıklama: tamam")
    if shorts_id:
        print("  Shorts:")
        try:
            youtube.videos().update(part="snippet", body={"id": shorts_id, "snippet": shorts_snippet}).execute()
            print("  Açıklama: tamam")
        except Exception as e:
            print(f"  Shorts açıklama HATA: {e}")


def fix_all_thumbnails(bases: tuple[str, ...] = ("projects", "dj_sets")) -> None:
    """--thumbnail-only --all: bases altındaki, YouTube'a zaten yüklü (state.json'da
    youtube_video_id ve/veya youtube_shorts_video_id olan) TÜM projelerin
    thumbnail'ini tek seferde düzeltir. Zaten doğru kapakla yüklü videolarda da
    tekrar çağırmak güvenlidir (thumbnails().set() üzerine yazar, idempotent).
    Varsayılan olarak hem ana katalog (`projects/`) hem DJ Famous setlerini
    (`dj_sets/`) tarar — eskiden sadece `projects/` taranıyordu, bu yüzden
    dj_sets/ projelerinin thumbnail'i hiç düzeltilmiyordu (kullanıcı geri
    bildirimiyle tespit edildi: City Pulse Set'in kapağı YouTube'da hiç
    görünmüyordu)."""
    for base in bases:
        if not os.path.isdir(base):
            continue
        _fix_all_thumbnails_in(base)


def _fix_all_thumbnails_in(base: str) -> None:
    for name in sorted(os.listdir(base)):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        state_path = os.path.join(project_dir, "state.json")
        if not os.path.isfile(state_path):
            continue
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not state.get("youtube_video_id") and not state.get("youtube_shorts_video_id"):
            continue
        print(f"\n=== {name} ===")
        try:
            fix_thumbnail(project_dir)
        except Exception as e:
            print(f"  HATA: {e}")


def fix_all_descriptions(bases: tuple[str, ...] = ("projects", "dj_sets")) -> None:
    """--description-only --all: bases altındaki, YouTube'a zaten yüklü TÜM
    videoların açıklamasını güncel kalıpla günceller."""
    for base in bases:
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            project_dir = os.path.join(base, name)
            if not os.path.isdir(project_dir):
                continue
            state_path = os.path.join(project_dir, "state.json")
            if not os.path.isfile(state_path):
                continue
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if not state.get("youtube_video_id") and not state.get("youtube_shorts_video_id"):
                continue
            print(f"\n=== {name} ===")
            try:
                fix_description(project_dir)
            except Exception as e:
                print(f"  HATA: {e}")


def main():
    parser = argparse.ArgumentParser(description="YouTube upload tool")
    parser.add_argument("--project", help="Proje dizini (projects/... veya dj_sets/...)")
    parser.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"],
                        help="Video gizliliği (default: private)")
    parser.add_argument("--shorts", action="store_true",
                        help="Shorts (shorts_9x16.mp4) yükle, uzun format (youtube_16x9.mp4) değil")
    parser.add_argument("--thumbnail-only", action="store_true",
                        help="Sadece thumbnail güncelle (video yükleme)")
    parser.add_argument("--description-only", action="store_true",
                        help="Sadece açıklama/title/tags güncelle (video yükleme)")
    parser.add_argument("--all", action="store_true",
                        help="--thumbnail-only ya da --description-only ile birlikte: projects/ (+ dj_sets/) altındaki YouTube'a zaten yüklü TÜM projeleri tek seferde düzeltir.")
    parser.add_argument("--no-schedule", action="store_true",
                        help="privacy=public olsa bile golden-hour zamanlamasını (config.GOLDEN_HOURS) devre dışı bırakıp hemen public yükler.")
    args = parser.parse_args()

    if args.thumbnail_only and args.description_only:
        parser.error("--thumbnail-only ve --description-only aynı anda kullanılamaz")
    elif args.thumbnail_only and args.all:
        fix_all_thumbnails()
    elif args.thumbnail_only:
        if not args.project:
            parser.error("--thumbnail-only için --project ya da --all gerekli")
        fix_thumbnail(args.project)
    elif args.description_only and args.all:
        fix_all_descriptions()
    elif args.description_only:
        if not args.project:
            parser.error("--description-only için --project ya da --all gerekli")
        fix_description(args.project)
    elif not args.project:
        parser.error("--project gerekli (ya da --thumbnail-only/--description-only --all)")
    elif args.shorts:
        upload_short(args.project, args.privacy, schedule=not args.no_schedule)
    else:
        upload_video(args.project, args.privacy, schedule=not args.no_schedule)


if __name__ == "__main__":
    main()