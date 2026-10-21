#!/usr/bin/env python3
"""
Distribution Package Builder — Tüm platformlar için hazır dağıtım paketi üretir.

Platform Kategorileri:
1. VIDEO PLATFORMLAR (Kendi render dosyalarımız)
   - YouTube (Uzun Format 4K HDR/SDR)
   - YouTube Shorts (9:16)
   - TikTok (9:16)
   - Instagram Reels (9:16)
   - Facebook Reels (9:16)
   - Bluesky (9:16)
   - Telegram (9:16)
   - X/Twitter (16:9 + 9:16)
   - LinkedIn (16:9)
   - Pinterest (9:16)
   - Snapchat Spotlight (9:16)
   - Twitch (Clips/Highlights)

2. MÜZİK STREAMİNG (Dağıtıcı üzerinden - DistroKid/TuneCore/CD Baby)
   - Spotify
   - Apple Music
   - YouTube Music
   - Amazon Music
   - Deezer
   - Tidal
   - Pandora
   - Napster
   - iHeartRadio
   - Anghami
   - JioSaavn
   - Boomplay
   - AudioMack

3. SOSYAL SES / KATALOĞ (Doğrudan yüklenebilir)
   - SoundCloud
   - Bandcamp
   - Audiomack
   - ReverbNation
   - HearThis.at

4. PODCAST (Opsiyonel - aynı ses dosyası)
   - Apple Podcasts
   - Spotify Podcasts
   - Google Podcasts
   - Amazon Music Podcasts
   - Pocket Casts
   - Overcast

5. DAĞITICI / AGGREGATOR (Metadata + Audio teslimi)
   - DistroKid
   - TuneCore
   - CD Baby
   - Ditto Music
   - AWAL
   - Believe
   - The Orchard
   - Symphonic
   - Stem
   - UnitedMasters

Kullanım:
    python distribution_package.py --project projects/my-song

Çıktı: projects/my-song/distribution/
  ├─ package.json              # Manifest (tüm platform eşlemesi)
  ├─ video/                    # Video platformları için
  │   ├─ youtube_4k_hdr.mp4
  │   ├─ youtube_4k_sdr.mp4
  │   ├─ shorts_9x16.mp4
  │   ├─ tiktok_9x16.mp4
  │   ├─ reels_9x16.mp4
  │   ├─ twitter_16x9.mp4
  │   ├─ linkedin_16x9.mp4
  │   └─ ...
  ├─ audio/                    # Müzik dağıtıcısı/streaming için
  │   ├─ master.wav            # 24-bit/48kHz (veya 96kHz) master
  │   ├─ master.flac           # Lossless
  │   ├─ master_16bit.wav      # 16-bit/44.1kHz (CD standardı)
  │   ├─ master_320.mp3        # 320kbps MP3
  │   └─ instrumental.wav      # (varsa)
  ├─ artwork/                  # Kapak formatları
  │   ├─ cover_3000x3000.jpg   # Spotify/Apple/YouTube Music (3000x3000, <20MB)
  │   ├─ cover_1400x1400.jpg   # SoundCloud/Bandcamp
  │   ├─ cover_16x9.png        # YouTube/Twitter/LinkedIn (3840x2160)
  │   ├─ cover_9x16.png        # Shorts/TikTok/Reels (2160x3840)
  │   ├─ cover_1x1.png         # Generic square (3000x3000)
  │   ├─ thumbnail_1280x720.jpg# YouTube thumbnail
  │   └─ thumbnail_9x16.jpg    # Shorts/Reels thumbnail
  ├─ metadata/
  │   ├─ track_metadata.json   # Tüm platformlar için unified metadata
  │   ├─ distributor_metadata.json  # DistroKid/TuneCore formatı
  │   ├─ chapters.json         # YouTube chapters
  │   ├─ lyrics.lrc            # Senkronize liriklere (varsa)
  │   ├─ lyrics.txt            # Düz metin liriklere
  │   └─ credits.json          # Producer, writer, musician credits
  └─ ids/
      ├─ isrc.txt              # ISRC kodu (varsa)
      ├─ upc.txt               # UPC/EAN kodu (varsa)
      └─ iswc.txt              # ISWC kodu (varsa)
"""

import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Any
import sys

sys.path.insert(0, str(Path(__file__).parent))
import config


# =============================================================================
# PLATFORM TANIMLARI
# =============================================================================

@dataclass
class PlatformSpec:
    """Platform spesifikasyonu."""
    name: str
    category: str  # "video", "streaming", "social_audio", "podcast", "distributor"
    video_file: Optional[str] = None      # Hangi video dosyası
    audio_file: Optional[str] = None      # Hangi audio dosyası
    artwork_file: Optional[str] = None    # Hangi kapak dosyası
    metadata_file: Optional[str] = None   # Hangi metadata dosyası
    requires_distributor: bool = False    # Dağıtıcı gerekli mi?
    native_schedule: bool = False         # Native zamanlama var mı?
    max_file_size_mb: Optional[int] = None
    notes: str = ""


# TÜM PLATFORMLAR - Merkezi Tanım
PLATFORMS: Dict[str, PlatformSpec] = {
    # === VIDEO PLATFORMLAR ===
    "youtube": PlatformSpec(
        name="YouTube",
        category="video",
        video_file="youtube_4k_hdr.mp4",
        artwork_file="thumbnail_1280x720.jpg",
        metadata_file="track_metadata.json",
        native_schedule=True,
        max_file_size_mb=256000,  # 256 GB (YouTube limiti)
        notes="HDR master tercih edilir, SDR fallback olarak youtube_4k_sdr.mp4",
    ),
    "youtube_shorts": PlatformSpec(
        name="YouTube Shorts",
        category="video",
        video_file="shorts_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=True,
        max_file_size_mb=256000,
        notes="60sn altı, dikey 9:16, #Shorts etiketi",
    ),
    "tiktok": PlatformSpec(
        name="TikTok",
        category="video",
        video_file="tiktok_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=True,  # PostWire/Buffer üzerinden
        max_file_size_mb=287,  # 287 MB (mobil), 720 MB (web)
        notes="En fazla 10 dk (şu an 3 dk standart), dikey 9:16",
    ),
    "instagram_reels": PlatformSpec(
        name="Instagram Reels",
        category="video",
        video_file="reels_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=True,  # Meta Business Suite / PostWire
        max_file_size_mb=4000,  # 4 GB
        notes="90sn altı (Reels), dikey 9:16, konteyner 23sa ömürlü",
    ),
    "facebook_reels": PlatformSpec(
        name="Facebook Reels",
        category="video",
        video_file="reels_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=True,
        max_file_size_mb=4000,
        notes="video_state=SCHEDULED ile native planlama",
    ),
    "bluesky": PlatformSpec(
        name="Bluesky",
        category="video",
        video_file="shorts_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=False,  # PostWire/API ile
        max_file_size_mb=100,  # 100 MB (video), 25 MB (image)
        notes="AT Protocol, video desteği sınırlı",
    ),
    "telegram": PlatformSpec(
        name="Telegram",
        category="video",
        video_file="shorts_9x16.mp4",
        artwork_file="cover_1x1.png",
        metadata_file="track_metadata.json",
        native_schedule=False,
        max_file_size_mb=2000,  # 2 GB
        notes="Channel/Group paylaşımı, bot ile otomatik",
    ),
    "twitter": PlatformSpec(
        name="X (Twitter)",
        category="video",
        video_file="twitter_16x9.mp4",
        artwork_file="cover_16x9.png",
        metadata_file="track_metadata.json",
        native_schedule=True,  # Twitter Media Studio / PostWire
        max_file_size_mb=512,  # 512 MB
        notes="16:9 veya 9:16, 2 dakika 20 saniye limiti (Premium daha fazla)",
    ),
    "linkedin": PlatformSpec(
        name="LinkedIn",
        category="video",
        video_file="linkedin_16x9.mp4",
        artwork_file="cover_16x9.png",
        metadata_file="track_metadata.json",
        native_schedule=True,
        max_file_size_mb=5000,  # 5 GB
        notes="16:9 profesyonel içerik, 10 dk limiti",
    ),
    "pinterest": PlatformSpec(
        name="Pinterest",
        category="video",
        video_file="shorts_9x16.mp4",
        artwork_file="cover_1x1.png",
        metadata_file="track_metadata.json",
        native_schedule=True,
        max_file_size_mb=2000,
        notes="Dikey 9:16 Idea Pin, 15 dk limiti",
    ),
    "snapchat": PlatformSpec(
        name="Snapchat Spotlight",
        category="video",
        video_file="shorts_9x16.mp4",
        artwork_file="thumbnail_9x16.jpg",
        metadata_file="track_metadata.json",
        native_schedule=False,
        max_file_size_mb=1000,
        notes="60sn altı, dikey 9:16",
    ),
    "twitch": PlatformSpec(
        name="Twitch",
        category="video",
        video_file="youtube_4k_sdr.mp4",
        artwork_file="cover_16x9.png",
        metadata_file="track_metadata.json",
        native_schedule=False,
        max_file_size_mb=10000,
        notes="Clips/Highlights/Uploads, 1080p60 önerilir",
    ),

    # === MÜZİK STREAMİNG (Dağıtıcı Gerekli) ===
    "spotify": PlatformSpec(
        name="Spotify",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,  # Dağıtıcı planlar
        notes="DistroKid/TuneCore/CD Baby üzerinden. 3000x3000 JPEG/PNG <20MB. Release date planlanır.",
    ),
    "apple_music": PlatformSpec(
        name="Apple Music",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="AAC 256kbps stream. Artwork 3000x3000. Pre-add/Pre-save kampanyası mümkün.",
    ),
    "youtube_music": PlatformSpec(
        name="YouTube Music",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="YouTube Content ID + Music Premium. Art track otomatik oluşturulur. Dağıtıcıdan YouTube Music'e ayrı teslim.",
    ),
    "amazon_music": PlatformSpec(
        name="Amazon Music",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="HD/Ultra HD destekli. Dağıtıcı üzerinden.",
    ),
    "deezer": PlatformSpec(
        name="Deezer",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="HiFi/FLAC streaming. Dağıtıcı üzerinden.",
    ),
    "tidal": PlatformSpec(
        name="Tidal",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Master Quality (MQA) destekli. Dağıtıcı üzerinden.",
    ),
    "pandora": PlatformSpec(
        name="Pandora",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Radio + On-demand. Dağıtıcı üzerinden (genellikle CD Baby/TuneCore).",
    ),
    "napster": PlatformSpec(
        name="Napster",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Dağıtıcı üzerinden.",
    ),
    "iheartradio": PlatformSpec(
        name="iHeartRadio",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Radio odaklı. Dağıtıcı üzerinden.",
    ),
    "anghami": PlatformSpec(
        name="Anghami",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="MENA bölgesi popüler. Dağıtıcı üzerinden.",
    ),
    "jiosaavn": PlatformSpec(
        name="JioSaavn",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Hindistan/Alt kıta. Dağıtıcı üzerinden.",
    ),
    "boomplay": PlatformSpec(
        name="Boomplay",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Afrika pazarı lideri. Dağıtıcı üzerinden.",
    ),
    "audiomack_streaming": PlatformSpec(
        name="Audiomack (Streaming)",
        category="streaming",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=True,
        native_schedule=False,
        notes="Afrika/Global. Dağıtıcı üzerinden streaming kataloguna girer.",
    ),

    # === SOSYAL SES / DOĞRUDAN YÜKLEME ===
    "soundcloud": PlatformSpec(
        name="SoundCloud",
        category="social_audio",
        audio_file="master.wav",
        artwork_file="cover_1400x1400.jpg",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=True,  # SoundCloud Premier / Schedule
        max_file_size_mb=5000,
        notes="Doğrudan yükleme. WAV/FLAC/MP3. Private + scheduled publish. Monetization (Premier) ayrı.",
    ),
    "bandcamp": PlatformSpec(
        name="Bandcamp",
        category="social_audio",
        audio_file="master.flac",
        artwork_file="cover_1400x1400.jpg",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        max_file_size_mb=2000,
        notes="Doğrudan yükleme. FLAC/WAV/MP3/ALAC. Name-your-price. Fan ilişkisi güçlü.",
    ),
    "audiomack_social": PlatformSpec(
        name="Audiomack (Social)",
        category="social_audio",
        audio_file="master_320.mp3",
        artwork_file="cover_1x1.png",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        max_file_size_mb=500,
        notes="Doğrudan yükleme (Creator). MP3 320kbps. Trending/Charts.",
    ),
    "reverbnation": PlatformSpec(
        name="ReverbNation",
        category="social_audio",
        audio_file="master_320.mp3",
        artwork_file="cover_1x1.png",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=False,
        max_file_size_mb=100,
        notes="Doğrudan yükleme. Promosyon araçları.",
    ),
    "hearthis": PlatformSpec(
        name="HearThis.at",
        category="social_audio",
        audio_file="master.wav",
        artwork_file="cover_1x1.png",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=False,
        max_file_size_mb=500,
        notes="DJ/Producer odaklı. Doğrudan yükleme.",
    ),

    # === PODCAST (Opsiyonel) ===
    "apple_podcasts": PlatformSpec(
        name="Apple Podcasts",
        category="podcast",
        audio_file="master_16bit.wav",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="track_metadata.json",
        requires_distributor=False,  # RSS feed üzerinden
        native_schedule=False,
        notes="RSS feed (anchor.fm, buzzsprout, libsyn vb.) üzerinden. Episode olarak eklenir.",
    ),
    "spotify_podcasts": PlatformSpec(
        name="Spotify Podcasts",
        category="podcast",
        audio_file="master_16bit.wav",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="track_metadata.json",
        requires_distributor=False,
        native_schedule=False,
        notes="Spotify for Podcasters / RSS feed.",
    ),

    # === DAĞITICILAR (Aggregators) ===
    "distrokid": PlatformSpec(
        name="DistroKid",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,  # O dağıtıcıdır
        native_schedule=True,
        notes="En hızlı, yıllık ücret. Leave a Legacy, Splits, HyperFollow, YouTube Content ID, TikTok/IG/FB library sync.",
    ),
    "tunecore": PlatformSpec(
        name="TuneCore",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        notes="Yıllık ücret parça/bazında. Publishing administration, YouTube Sound Recording revenue.",
    ),
    "cdbaby": PlatformSpec(
        name="CD Baby",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        notes="Tek seferlik ödeme + %9 komisyon. Publishing (CD Baby Pro), Sync licensing, YouTube Monetization.",
    ),
    "dittomusic": PlatformSpec(
        name="Ditto Music",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        notes="Yıllık ücret. Vevo channel, Chart registration, Pre-save.",
    ),
    "awal": PlatformSpec(
        name="AWAL",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        notes="Kabul şartlı (selective). %15 komisyon. Marketing/destek güçlü.",
    ),
    "unitedmasters": PlatformSpec(
        name="UnitedMasters",
        category="distributor",
        audio_file="master.flac",
        artwork_file="cover_3000x3000.jpg",
        metadata_file="distributor_metadata.json",
        requires_distributor=False,
        native_schedule=True,
        notes="Free tier + Select (yıllık). Brand partnerships, Sync, TikTok/IG music library.",
    ),
}


# =============================================================================
# VERİ SINIFLARI
# =============================================================================

@dataclass
class DistributionManifest:
    """Paket manifesti — 3. parti araçların okuyacağı tek kaynak."""
    project_name: str
    created_at: str
    version: int
    source_hash: str  # audio.wav SHA256
    deliverables: Dict[str, Dict]  # platform -> {file, hash, size, spec}
    metadata: Dict  # Unified metadata
    distributor_metadata: Dict  # DistroKid/TuneCore formatında
    schedule: Dict[str, str]  # platform -> publish_at (ISO UTC)
    platforms: List[str]
    artwork: Dict[str, str]  # artwork_name -> hash
    audio_files: Dict[str, str]  # audio_name -> hash
    ids: Dict[str, str]  # isrc, upc, iswc


@dataclass
class TrackMetadata:
    """Unified track metadata — tüm platformlar için ortak."""
    # Temel
    title: str
    artist: str
    artist_id: str = ""  # Spotify/Apple artist ID (varsa)
    featuring: List[str] = field(default_factory=list)
    remixers: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    writers: List[str] = field(default_factory=list)
    isrc: str = ""
    upc: str = ""
    iswc: str = ""
    
    # Release
    release_date: str = ""  # YYYY-MM-DD
    original_release_date: str = ""  # Orijinal çıkış tarihi (re-release için)
    label: str = "Famous Music Studio"
    catalog_number: str = ""
    
    # Sınıflandırma
    genre: str = "Electronic"
    subgenre: str = ""
    mood: List[str] = field(default_factory=list)
    bpm: int = 0
    key: str = ""  # örn: "C# minor"
    language: str = "tr"
    explicit: bool = False
    
    # Açıklama
    description: str = ""
    short_description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Telif / Yayıncı
    copyright_p: str = ""  # ℗ (Sound recording)
    copyright_c: str = ""  # © (Composition)
    publisher: str = ""
    publishing_rights: str = ""
    
    # AI Beyani
    ai_generated: bool = True
    ai_tool: str = "Suno"
    ai_prompt: str = ""
    
    # Platform özel
    spotify_artist_id: str = ""
    apple_artist_id: str = ""
    youtube_channel_id: str = ""
    
    # Ek
    lyrics: str = ""
    synced_lyrics: str = ""  # LRC formatında
    chapters: List[Dict] = field(default_factory=list)
    playlist_pitch: str = ""  # Spotify playlist pitch için


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_audio_master(project_dir: Path) -> Optional[Path]:
    """Master ses dosyasını bul (öncelik: wav > flac > mp3)."""
    for name in ["audio.wav", "master.wav", "master.flac", "master_24bit.wav", "master_96khz.wav"]:
        p = project_dir / name
        if p.exists():
            return p
    return None


def find_artwork_files(project_dir: Path) -> Dict[str, Path]:
    """Mevcut kapak dosyalarını bul."""
    found = {}
    patterns = {
        "cover_3000x3000.jpg": ["cover_3000x3000.jpg", "cover_square.jpg", "art_3000.jpg"],
        "cover_1400x1400.jpg": ["cover_1400x1400.jpg", "cover_bandcamp.jpg"],
        "cover_16x9.png": ["cover_16x9.png", "cover.png", "cover_youtube.png"],
        "cover_9x16.png": ["cover_9x16.png", "cover_vertical.png", "cover_shorts.png"],
        "cover_1x1.png": ["cover_1x1.png", "cover_square.png", "cover_instagram.jpg"],
        "thumbnail_1280x720.jpg": ["thumbnail_1280x720.jpg", "thumbnail_youtube.jpg", "thumb.jpg"],
        "thumbnail_9x16.jpg": ["thumbnail_9x16.jpg", "thumbnail_shorts.jpg", "thumb_vertical.jpg"],
    }
    for target, candidates in patterns.items():
        for cand in candidates:
            p = project_dir / cand
            if p.exists():
                found[target] = p
                break
    return found


def generate_missing_artwork(project_dir: Path, found: Dict[str, Path]) -> Dict[str, Path]:
    """Eksik kapakları varsayıdan üret (cover_generator.py kullanarak).
    
    NOT: Bu fonksiyon sadece yer tutucudur. Gerçek üretim için cover_generator.py
    çalıştırılmalıdır. Burada sadece hangi dosyaların beklendiği tanımlanır.
    """
    # cover_generator.py zaten şunları üretir:
    # - cover.png (16:9, 3840x2160) -> cover_16x9.png
    # - cover_vertical.png (9:16, 2160x3840) -> cover_9x16.png
    # - art.jpg (kare, metinsiz) -> cover_3000x3000.jpg kaynağı
    return found


def load_project_metadata(project_dir: Path) -> Dict:
    """Proje meta.json ve metadata.json'larını birleştir."""
    meta = {}
    meta_path = project_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    
    metadata_path = project_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            rendered_meta = json.load(f)
        # metadata.json meta.json'u ezer (daha güncel)
        meta.update(rendered_meta)
    
    return meta


def build_track_metadata(project_dir: Path, meta: Dict, state: Dict) -> TrackMetadata:
    """Unified TrackMetadata nesnesi oluştur."""
    # ISRC/UPC state'den veya meta'dan al
    isrc = state.get("isrc") or meta.get("isrc") or ""
    upc = state.get("upc") or meta.get("upc") or ""
    iswc = state.get("iswc") or meta.get("iswc") or ""
    
    # Eğer yoksa ISRC üret (basit: YY-XXX-YY-NNNNN)
    # Gerçekte ISRC yöneticisi (IFPI/ulusal ajans) verilir.
    if not isrc:
        # Turkey: TR-XXX-YY-NNNNN
        # Bu sadece placeholder - GERÇEK ISRC DAĞITICIDAN GELİR
        year = datetime.now().strftime("%y")
        # Basit hash tabanlı
        import hashlib
        hash_part = hashlib.md5(meta.get("title", "").encode()).hexdigest()[:5].upper()
        isrc = f"TR-FMZ-{year}-{hash_part}"  # FMZ = Famous Music Studio (kendi kodunuz)
    
    return TrackMetadata(
        title=meta.get("title", project_dir.name),
        artist=meta.get("artist", "Famous Music Studio"),
        artist_id=meta.get("artist_id", ""),
        featuring=meta.get("featuring", []),
        remixers=meta.get("remixers", []),
        producers=meta.get("producers", ["Famous Music Studio"]),
        writers=meta.get("writers", []),
        isrc=isrc,
        upc=upc,
        iswc=iswc,
        release_date=meta.get("release_date", datetime.now().strftime("%Y-%m-%d")),
        original_release_date=meta.get("original_release_date", ""),
        label=meta.get("label", "Famous Music Studio"),
        catalog_number=meta.get("catalog_number", f"FMS-{datetime.now().strftime('%Y%m%d')}"),
        genre=meta.get("genre", "Electronic"),
        subgenre=meta.get("subgenre", ""),
        mood=meta.get("mood", []),
        bpm=meta.get("bpm", 0),
        key=meta.get("key", ""),
        language=meta.get("language", "tr"),
        explicit=meta.get("explicit", False),
        description=meta.get("description", ""),
        short_description=meta.get("short_description", meta.get("description", "")[:160]),
        tags=meta.get("tags", []),
        copyright_p=meta.get("copyright_p", f"℗ {datetime.now().year} Famous Music Studio"),
        copyright_c=meta.get("copyright_c", f"© {datetime.now().year} Famous Music Studio"),
        publisher=meta.get("publisher", "Famous Music Studio Publishing"),
        publishing_rights=meta.get("publishing_rights", "All rights reserved"),
        ai_generated=meta.get("ai_generated", True),
        ai_tool=meta.get("ai_tool", "Suno"),
        ai_prompt=meta.get("ai_prompt", ""),
        spotify_artist_id=meta.get("spotify_artist_id", ""),
        apple_artist_id=meta.get("apple_artist_id", ""),
        youtube_channel_id=meta.get("youtube_channel_id", config.YOUTUBE_HANDLE),
        lyrics=meta.get("lyrics", ""),
        synced_lyrics=meta.get("synced_lyrics", ""),
        chapters=meta.get("chapters", []),
        playlist_pitch=meta.get("playlist_pitch", ""),
    )


def build_distributor_metadata(track: TrackMetadata, project_dir: Path) -> Dict:
    """DistroKid/TuneCore/CD Baby formatında metadata."""
    return {
        # DistroKid formatı (en yaygın)
        "distrokid": {
            "title": track.title,
            "artist": track.artist,
            "featuring": ", ".join(track.featuring) if track.featuring else "",
            "release_date": track.release_date,
            "genre": track.genre,
            "subgenre": track.subgenre,
            "language": track.language,
            "explicit": "Yes" if track.explicit else "No",
            "isrc": track.isrc,
            "upc": track.upc,
            "label": track.label,
            "copyright_p": track.copyright_p,
            "copyright_c": track.copyright_c,
            "publisher": track.publisher,
            "composer": ", ".join(track.writers) if track.writers else track.artist,
            "producer": ", ".join(track.producers) if track.producers else "",
            "lyrics": track.lyrics,
            "spotify_artist_id": track.spotify_artist_id,
            "apple_artist_id": track.apple_artist_id,
            "youtube_channel_id": track.youtube_channel_id,
            "ai_generated": "Yes" if track.ai_generated else "No",
            "ai_tool": track.ai_tool,
            "playlist_pitch": track.playlist_pitch,
            "stores": [
                "Spotify", "Apple Music", "YouTube Music", "Amazon Music",
                "Deezer", "Tidal", "Pandora", "Napster", "iHeartRadio",
                "Anghami", "JioSaavn", "Boomplay", "Audiomack",
                "TikTok", "Instagram/Facebook", "Snapchat", "Triller"
            ],
        },
        # TuneCore formatı
        "tunecore": {
            "track_title": track.title,
            "artist_name": track.artist,
            "featuring_artists": track.featuring,
            "release_date": track.release_date,
            "primary_genre": track.genre,
            "secondary_genre": track.subgenre,
            "language": track.language,
            "parental_advisory": track.explicit,
            "isrc": track.isrc,
            "upc": track.upc,
            "label_name": track.label,
            "p_line": track.copyright_p,
            "c_line": track.copyright_c,
            "publisher_name": track.publisher,
            "composer_names": track.writers,
            "producer_names": track.producers,
            "lyrics": track.lyrics,
            "territories": ["Worldwide"],
        },
        # CD Baby formatı
        "cdbaby": {
            "title": track.title,
            "artist": track.artist,
            "featuring": track.featuring,
            "release_date": track.release_date,
            "genre": track.genre,
            "subgenre": track.subgenre,
            "language": track.language,
            "explicit": track.explicit,
            "isrc": track.isrc,
            "upc": track.upc,
            "label": track.label,
            "copyright": track.copyright_p,
            "publisher": track.publisher,
            "composers": track.writers,
            "producers": track.producers,
            "lyrics": track.lyrics,
            "distribution_outlets": "all",
        },
        # UnitedMasters formatı
        "unitedmasters": {
            "title": track.title,
            "artist": track.artist,
            "features": track.featuring,
            "release_date": track.release_date,
            "genre": track.genre,
            "explicit": track.explicit,
            "isrc": track.isrc,
            "upc": track.upc,
            "label": track.label,
            "copyright_owner": track.copyright_p,
            "publisher": track.publisher,
            "songwriters": track.writers,
            "producers": track.producers,
            "lyrics": track.lyrics,
            "platforms": ["spotify", "apple", "youtube", "tiktok", "instagram", "facebook", "snapchat"],
        },
    }


# =============================================================================
# ANA PAKET OLUŞTURMA
# =============================================================================

def build_distribution_package(
    project_dir: Path,
    output_dir: Optional[Path] = None,
    include_categories: Optional[List[str]] = None,
    distributor: str = "distrokid"
) -> Path:
    """
    Proje klasöründen tam dağıtım paketi oluşturur.
    
    Args:
        project_dir: Proje klasörü (audio.wav, meta.json, state.json, output/, cover'lar)
        output_dir: Çıktı klasörü (varsayılan: project/distribution)
        include_categories: Hangi kategoriler dahil edilsin?
            ["video", "streaming", "social_audio", "podcast", "distributor"]
            None = hepsi
        distributor: Hangi dağıtıcı metadata formatı öncelikli? (distrokid/tunecore/cdbaby/unitedmasters)
    """
    project_dir = Path(project_dir)
    if output_dir is None:
        output_dir = project_dir / "distribution"
    
    if include_categories is None:
        include_categories = ["video", "streaming", "social_audio", "distributor"]
    
    # Temizlik ve klasör yapısı
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    video_dir = output_dir / "video"
    audio_dir = output_dir / "audio"
    artwork_dir = output_dir / "artwork"
    metadata_dir = output_dir / "metadata"
    ids_dir = output_dir / "ids"
    
    for d in [video_dir, audio_dir, artwork_dir, metadata_dir, ids_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 1. State ve metadata oku
    state_path = project_dir / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"state.json yok: {project_dir} - önce video_pipeline çalıştır")
    
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    
    meta = load_project_metadata(project_dir)
    track_meta = build_track_metadata(project_dir, meta, state)
    distributor_meta = build_distributor_metadata(track_meta, project_dir)
    
    # 2. Audio hash (kaynak kimliği)
    audio_path = find_audio_master(project_dir)
    if not audio_path:
        raise FileNotFoundError("Master ses dosyası bulunamadı (audio.wav/master.wav/master.flac)")
    source_hash = sha256_file(audio_path)
    
    # 3. Video dosyalarını kopyala (video kategorisi istenirse)
    deliverables = {}
    video_src = project_dir / "output"
    video_file_map = {
        "youtube_4k_hdr.mp4": "youtube_4k_hdr.mp4",
        "youtube_4k_sdr.mp4": "youtube_4k_sdr.mp4",
        "shorts_9x16.mp4": "shorts_9x16.mp4",
        "reels_9x16.mp4": "reels_9x16.mp4",
        "tiktok_9x16.mp4": "tiktok_9x16.mp4",
        "twitter_16x9.mp4": "twitter_16x9.mp4",
        "linkedin_16x9.mp4": "linkedin_16x9.mp4",
    }
    
    if "video" in include_categories:
        for src_name, dst_name in video_file_map.items():
            src = video_src / src_name
            if src.exists():
                dst = video_dir / dst_name
                shutil.copy2(src, dst)
                stat = src.stat()
                deliverables[dst_name.replace(".mp4", "")] = {
                    "file": f"video/{dst_name}",
                    "hash": sha256_file(src),
                    "size": stat.st_size,
                    "spec": config.INDIE_FLAGSHIP_5CAM["deliverable_specs"].get(
                        src_name.replace(".mp4", ""), {}
                    ),
                }
    
    # 4. Audio dosyalarını kopyala (streaming/social_audio/distributor kategorisi)
    audio_files = {}
    if any(c in include_categories for c in ["streaming", "social_audio", "distributor"]):
        # Master dosyaları kopyala
        audio_copies = {
            "master.flac": audio_path if audio_path.suffix == ".flac" else None,
            "master.wav": audio_path if audio_path.suffix == ".wav" else None,
            "master_16bit.wav": project_dir / "master_16bit.wav",
            "master_320.mp3": project_dir / "master_320.mp3",
            "instrumental.wav": project_dir / "instrumental.wav",
        }
        
        for name, src in audio_copies.items():
            if src and src.exists():
                dst = audio_dir / name
                shutil.copy2(src, dst)
                audio_files[name] = sha256_file(src)
            elif src is None and name == "master.flac":
                # FLAC yoksa WAV'dan FLAC üret (placeholder - ffmpeg lazım)
                pass
            elif src is None and name == "master_16bit.wav":
                # 16-bit/44.1kHz dönüşüm (placeholder)
                pass
            elif src is None and name == "master_320.mp3":
                # 320kbps MP3 dönüşüm (placeholder)
                pass
    
    # 5. Kapak dosyalarını kopyala
    artwork_files = {}
    found_artwork = find_artwork_files(project_dir)
    found_artwork = generate_missing_artwork(project_dir, found_artwork)
    
    for target_name, src in found_artwork.items():
        dst = artwork_dir / target_name
        shutil.copy2(src, dst)
        artwork_files[target_name] = sha256_file(src)
    
    # 6. Metadata dosyalarını yaz
    # Unified track metadata
    track_meta_path = metadata_dir / "track_metadata.json"
    with open(track_meta_path, "w", encoding="utf-8") as f:
        json.dump(asdict(track_meta), f, ensure_ascii=False, indent=2)
    
    # Distributor metadata
    dist_meta_path = metadata_dir / "distributor_metadata.json"
    with open(dist_meta_path, "w", encoding="utf-8") as f:
        json.dump(distributor_meta, f, ensure_ascii=False, indent=2)
    
    # Chapters
    chapters_path = metadata_dir / "chapters.json"
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump(track_meta.chapters, f, ensure_ascii=False, indent=2)
    
    # Lyrics
    if track_meta.lyrics:
        lyrics_path = metadata_dir / "lyrics.txt"
        with open(lyrics_path, "w", encoding="utf-8") as f:
            f.write(track_meta.lyrics)
    
    if track_meta.synced_lyrics:
        lrc_path = metadata_dir / "lyrics.lrc"
        with open(lrc_path, "w", encoding="utf-8") as f:
            f.write(track_meta.synced_lyrics)
    
    # Credits
    credits = {
        "artist": track_meta.artist,
        "featuring": track_meta.featuring,
        "remixers": track_meta.remixers,
        "producers": track_meta.producers,
        "writers": track_meta.writers,
        "label": track_meta.label,
        "publisher": track_meta.publisher,
        "copyright_p": track_meta.copyright_p,
        "copyright_c": track_meta.copyright_c,
        "ai_generated": track_meta.ai_generated,
        "ai_tool": track_meta.ai_tool,
    }
    credits_path = metadata_dir / "credits.json"
    with open(credits_path, "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=2)
    
    # 7. ISRC/UPC/ISWC dosyaları
    ids = {}
    for id_name, id_value in [("isrc", track_meta.isrc), ("upc", track_meta.upc), ("iswc", track_meta.iswc)]:
        if id_value:
            id_path = ids_dir / f"{id_name}.txt"
            id_path.write_text(id_value, encoding="utf-8")
            ids[id_name] = id_value
    
    # 8. Schedule bilgisi (state'den)
    schedule = {}
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Video platformları için YouTube planlısa
    if state.get("youtube_publish_at"):
        schedule["youtube"] = state["youtube_publish_at"]
        schedule["youtube_shorts"] = state.get("youtube_shorts_publish_at", state["youtube_publish_at"])
    elif state.get("youtube_uploaded_at"):
        schedule["youtube"] = state["youtube_uploaded_at"]
        schedule["youtube_shorts"] = state.get("youtube_shorts_uploaded_at", state["youtube_uploaded_at"])
    
    # Streaming platformları için release_date
    release_date = track_meta.release_date
    if release_date:
        # Dağıtıcı planlar, biz release_date veririz
        for platform in PLATFORMS:
            if PLATFORMS[platform].category in ["streaming", "distributor"]:
                schedule[platform] = f"{release_date}T00:00:00Z"
    
    # Social audio için golden hour (yaklaşık)
    if "soundcloud" in PLATFORMS:
        schedule["soundcloud"] = now_utc  # Hemen veya golden hour
    
    # 9. Platform listesi (kategorilere göre filtrele)
    platforms = []
    for platform_id, spec in PLATFORMS.items():
        if spec.category in include_categories:
            platforms.append(platform_id)
    
    # 10. Manifest oluştur
    manifest = DistributionManifest(
        project_name=project_dir.name,
        created_at=now_utc,
        version=1,
        source_hash=source_hash,
        deliverables=deliverables,
        metadata=asdict(track_meta),
        distributor_metadata=distributor_meta,
        schedule=schedule,
        platforms=platforms,
        artwork=artwork_files,
        audio_files=audio_files,
        ids=ids,
    )
    
    # 11. Manifest yaz
    manifest_path = output_dir / "package.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(asdict(manifest), f, ensure_ascii=False, indent=2)
    
    # Özet
    print(f"[OK] Dagitim paketi hazir: {output_dir}")
    print(f"   Proje: {project_dir.name}")
    print(f"   Kategoriler: {', '.join(include_categories)}")
    print(f"   Platform sayısı: {len(platforms)}")
    print(f"   Video dosyaları: {len([d for d in deliverables if 'video' in d or any(k in d for k in ['youtube', 'shorts', 'tiktok', 'reels', 'twitter', 'linkedin'])])}")
    print(f"   Audio dosyaları: {len(audio_files)}")
    print(f"   Kapak dosyaları: {len(artwork_files)}")
    print(f"   ISRC: {ids.get('isrc', 'YOK (dağıtıcıdan alınacak)')}")
    print(f"   UPC: {ids.get('upc', 'YOK (albüm için dağıtıcıdan alınacak)')}")
    print(f"   Manifest: {manifest_path}")
    
    return output_dir


def validate_package(package_dir: Path) -> Dict[str, Any]:
    """Oluşturulan paketi doğrula."""
    package_dir = Path(package_dir)
    manifest_path = package_dir / "package.json"
    
    if not manifest_path.exists():
        return {"valid": False, "errors": ["package.json bulunamadı"]}
    
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    
    errors = []
    warnings = []
    
    # Dosya varlık kontrolü
    for platform, info in manifest.get("deliverables", {}).items():
        file_path = package_dir / info["file"]
        if not file_path.exists():
            errors.append(f"Eksik dosya: {info['file']} ({platform})")
        else:
            # Hash doğrula
            actual_hash = sha256_file(file_path)
            if actual_hash != info["hash"]:
                errors.append(f"Hash uyuşmazlığı: {info['file']} (beklenen: {info['hash'][:16]}, actual: {actual_hash[:16]})")
    
    # Artwork kontrolü
    for name, hash_val in manifest.get("artwork", {}).items():
        file_path = package_dir / "artwork" / name
        if not file_path.exists():
            warnings.append(f"Eksik kapak: {name}")
        else:
            actual_hash = sha256_file(file_path)
            if actual_hash != hash_val:
                errors.append(f"Kapak hash uyuşmazlığı: {name}")
    
    # Audio kontrolü
    for name, hash_val in manifest.get("audio_files", {}).items():
        file_path = package_dir / "audio" / name
        if not file_path.exists():
            warnings.append(f"Eksik audio: {name}")
        else:
            actual_hash = sha256_file(file_path)
            if actual_hash != hash_val:
                errors.append(f"Audio hash uyuşmazlığı: {name}")
    
    # ISRC kontrolü
    if not manifest.get("ids", {}).get("isrc"):
        warnings.append("ISRC kodu yok - dağıtıcı atayacak")
    
    # UPC kontrolü (tek parça için zorunlu değil)
    if not manifest.get("ids", {}).get("upc"):
        warnings.append("UPC kodu yok - albüm/değerli tekil için dağıtıcı atayacak")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "platform_count": len(manifest.get("platforms", [])),
        "deliverable_count": len(manifest.get("deliverables", {})),
    }


def get_platforms_by_category(category: str) -> List[str]:
    """Kategoriye göre platform ID listesi döndür."""
    return [pid for pid, spec in PLATFORMS.items() if spec.category == category]


def get_distributor_platforms(distributor: str) -> List[str]:
    """Dağıtıcının dağıttığı platform listesi (DistroKid varsayılan)."""
    base = [
        "spotify", "apple_music", "youtube_music", "amazon_music",
        "deezer", "tidal", "pandora", "napster", "iheartradio",
        "anghami", "jiosaavn", "boomplay", "audiomack_streaming",
        "tiktok", "instagram_reels", "facebook_reels", "snapchat"
    ]
    # DistroKid ekstra
    if distributor == "distrokid":
        base.extend(["youtube_content_id", "tiktok_music", "instagram_music", "facebook_music"])
    return base


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Distribution Package Builder - All Platforms")
    parser.add_argument("--project", required=True, help="Proje klasörü")
    parser.add_argument("--output", help="Çıktı klasörü (varsayılan: project/distribution)")
    parser.add_argument("--categories", nargs="+", 
                        choices=["video", "streaming", "social_audio", "podcast", "distributor", "all"],
                        default=["video", "streaming", "social_audio", "distributor"],
                        help="Hangi platform kategorileri dahil edilsin")
    parser.add_argument("--distributor", choices=["distrokid", "tunecore", "cdbaby", "dittomusic", "awal", "unitedmasters"],
                        default="distrokid", help="Dağıtıcı metadata formatı")
    parser.add_argument("--validate", action="store_true", help="Sadece doğrula, paket oluşturma")
    parser.add_argument("--list-platforms", action="store_true", help="Desteklenen platformları listele")
    
    args = parser.parse_args()
    
    if args.list_platforms:
        print("DESTEKLENEN PLATFORMLAR:")
        print()
        for cat in ["video", "streaming", "social_audio", "podcast", "distributor"]:
            platforms = get_platforms_by_category(cat)
            print(f"  {cat.upper()} ({len(platforms)}):")
            for p in platforms:
                spec = PLATFORMS[p]
                dist = " (dagitici gerekli)" if spec.requires_distributor else ""
                sched = " [native schedule]" if spec.native_schedule else ""
                print(f"    - {spec.name} ({p}){dist}{sched}")
        return
    
    project_dir = Path(args.project)
    output_dir = Path(args.output) if args.output else None
    
    if args.validate:
        result = validate_package(output_dir or project_dir / "distribution")
        if result["valid"]:
            print(f"[OK] Paket gecerli: {result['deliverable_count']} teslimat, {result['platform_count']} platform")
        else:
            print(f"[HATA] Paket HATALI:")
            for e in result["errors"]:
                print(f"  - {e}")
        for w in result.get("warnings", []):
            print(f"  [UYARI] {w}")
        sys.exit(0 if result["valid"] else 1)
    
    # "all" kategorisi seçildiyse hepsini al
    categories = args.categories
    if "all" in categories:
        categories = ["video", "streaming", "social_audio", "podcast", "distributor"]
    
    try:
        build_distribution_package(
            project_dir=project_dir,
            output_dir=output_dir,
            include_categories=categories,
            distributor=args.distributor
        )
    except Exception as e:
        print(f"[HATA] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()