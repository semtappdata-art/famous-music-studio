#!/usr/bin/env python3
"""Create EPK placeholder files for Famous Music Studio"""
import os
import json
from datetime import datetime

epk_dir = "C:/Users/ACER/Desktop/ilk-projem/site/epk"
os.makedirs(epk_dir, exist_ok=True)

# 1. Bio & Fact Sheet (JSON for programmatic use, markdown for human)
bio_data = {
    "artist_name": "Famous Music Studio",
    "tagline": "AI-assisted music production from Turkey",
    "location": "Turkey",
    "genres": ["Turkish Pop", "R&B", "Trap", "Arabesk", "Melodic Techno", "DJ Mix"],
    "debut_album": "Gece Masalları (2026)",
    "notable_tracks": [
        "Gece Sürüsü",
        "Kalbim Oynuyor", 
        "Sabah Senin",
        "Dönmüyor Bu Yol",
        "Bu Gece Kazandık",
        "Yükseliş",
        "Kırık Zincir",
        "Küllerimden Geç"
    ],
    "dj_sets": [
        "Night Drive - DJ Cut | Cinematic Melodic Techno Mix (21 min)",
        "Night Drive - Melodic Techno Mix 2026 (25 min)"
    ],
    "description": (
        "Famous Music Studio is an AI-assisted music production project from Turkey, "
        "blending Turkish Pop, R&B, Trap, Arabesk, and Melodic Techno. "
        "The studio produces original tracks and DJ sets using cutting-edge AI tools "
        "while maintaining authentic Turkish musical identity. "
        "Debut album 'Gece Masalları' (2026) showcases this unique fusion."
    ),
    "achievements": [
        "Debut album 'Gece Masalları' released 2026",
        "Multiple DJ sets with 20+ minute cinematic mixes",
        "Growing presence on YouTube, TikTok, Instagram",
        "AI-assisted production workflow innovation"
    ],
    "press_contact": "press@famousmusicstudio.com",
    "booking_contact": "booking@famousmusicstudio.com",
    "management_contact": "hello@famousmusicstudio.com",
    "social_links": {
        "youtube": "https://youtube.com/@Famous_musics_studio",
        "tiktok": "https://tiktok.com/@famousmusicstudio",
        "instagram": "https://instagram.com/famous_music_studio",
        "ko-fi": "https://ko-fi.com/famousmusicstudio",
        "distrokid": "https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar"
    },
    "updated": datetime.now().isoformat()
}

with open(os.path.join(epk_dir, "bio.json"), "w", encoding="utf-8") as f:
    json.dump(bio_data, f, ensure_ascii=False, indent=2)

# Markdown version
bio_md = f"""# Famous Music Studio — EPK Bio & Fact Sheet

**Artist:** Famous Music Studio  
**Tagline:** AI-assisted music production from Turkey  
**Location:** Turkey  
**Genres:** {', '.join(bio_data['genres'])}  
**Debut Album:** {bio_data['debut_album']}

## Description
{bio_data['description']}

## Notable Tracks
{chr(10).join(f'- {t}' for t in bio_data['notable_tracks'])}

## DJ Sets
{chr(10).join(f'- {s}' for s in bio_data['dj_sets'])}

## Achievements
{chr(10).join(f'- {a}' for a in bio_data['achievements'])}

## Contact
- **Press:** {bio_data['press_contact']}
- **Booking:** {bio_data['booking_contact']}
- **Management:** {bio_data['management_contact']}

## Social Links
{chr(10).join(f'- **{k.title()}:** {v}' for k, v in bio_data['social_links'].items())}

---
*Updated: {datetime.now().strftime('%Y-%m-%d')}*
"""

with open(os.path.join(epk_dir, "bio.md"), "w", encoding="utf-8") as f:
    f.write(bio_md)

# 2. Press Photos - README
photos_readme = """# Press Photos

This folder should contain high-resolution press photos in the following formats:

## Required Assets
- **Portrait** (vertical) - 3000x4000px minimum
- **Landscape** (horizontal) - 4000x3000px minimum  
- **Square** (1:1) - 3000x3000px minimum
- **Logo variations** - SVG + PNG (transparent background)

## Naming Convention
- `famous-music-studio-portrait.jpg`
- `famous-music-studio-landscape.jpg`
- `famous-music-studio-square.jpg`
- `famous-music-studio-logo.svg`
- `famous-music-studio-logo-white.png`
- `famous-music-studio-logo-black.png`

## Style Guide
- Dark theme (#0a0a0f background)
- Accent color: #e94560
- Gold accent: #ffd700
- AI/tech aesthetic with Turkish cultural elements

## Usage Rights
All photos cleared for editorial use with credit: "Photo by Famous Music Studio"
"""

with open(os.path.join(epk_dir, "photos_README.md"), "w", encoding="utf-8") as f:
    f.write(photos_readme)

# 3. Music Assets - README
music_readme = """# Music Assets for Press/Remixers

## Available on Request
- **WAV stems** (drums, bass, synths, vocals, FX)
- **Instrumental versions** (all tracks)
- **Acapella/vocal stems** (where applicable)
- **MIDI files** (melody, chords, bass)
- **Loops & one-shots** for DJ sets

## Tracks Available
1. Gece Sürüsü
2. Kalbim Oynuyor
3. Sabah Senin
4. Dönmüyor Bu Yol
5. Bu Gece Kazandık
6. Yükseliş
7. Kırık Zincir
8. Küllerimden Geç

## DJ Set Assets
- Night Drive - DJ Cut (21 min) - Full mix + tracklist
- Night Drive - Melodic Techno Mix 2026 (25 min) - Full mix + tracklist

## Request Access
Email: press@famousmusicstudio.com
Subject: "Music Assets Request - [Publication/Platform]"

Include:
- Your name/publication
- Intended use (review, remix, playlist, sync)
- Specific tracks needed
- Deadline (if any)

## Licensing
- Editorial/review use: Free with credit
- Remix/derivative: Contact for license
- Sync/commercial: Contact for quote
"""

with open(os.path.join(epk_dir, "music_assets_README.md"), "w", encoding="utf-8") as f:
    f.write(music_readme)

# 4. Booking & Collabs - Form template
booking_md = """# Booking & Collaborations

## DJ Sets / Live Performances
**DJ Famous** available for:
- Club nights (Melodic Techno, Progressive House, Deep House)
- Festival sets (Daytime/Closing)
- Private events
- Livestream performances

**Technical Rider:**
- 2x CDJ-3000 or XDJ-XZ
- 1x DJM-V10 or DJM-900NXS2
- 2x Monitor speakers
- 1x Mic (wireless preferred)
- Table space for laptop/controller

## Remix Requests
- Stems available on request
- Remix fee negotiable
- Release coordination support

## Sync Licensing
- All tracks available for sync
- Instrumental versions available
- Custom edits possible
- Contact: booking@famousmusicstudio.com

## Collaboration Inquiries
- Vocal features
- Production collabs
- AI music tool demos
- Content partnerships

## Contact Form
```
Name: _______________
Email: _______________
Organization: _______________
Type: [ ] DJ Booking  [ ] Remix  [ ] Sync  [ ] Collab  [ ] Other
Details: _______________
Budget Range: _______________
Timeline: _______________
```

## Response Time
- Standard: 48 hours
- Urgent (subject line "URGENT"): 4 hours
"""

with open(os.path.join(epk_dir, "booking.md"), "w", encoding="utf-8") as f:
    f.write(booking_md)

# 5. Create a simple ZIP index
zip_index = {
    "epk_package": "famous-music-studio-epk.zip",
    "contents": [
        "bio.md",
        "bio.json",
        "photos_README.md",
        "music_assets_README.md",
        "booking.md"
    ],
    "note": "Add actual photos and music files before distributing",
    "generated": datetime.now().isoformat()
}

with open(os.path.join(epk_dir, "index.json"), "w", encoding="utf-8") as f:
    json.dump(zip_index, f, ensure_ascii=False, indent=2)

print(f"EPK placeholders created in: {epk_dir}")
print("Files:")
for f in os.listdir(epk_dir):
    print(f"  - {f}")