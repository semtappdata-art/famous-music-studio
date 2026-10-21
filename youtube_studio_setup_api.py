#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Famous Music Studio - YouTube Kanal 5 Islem (API ile otomatik)

Isler:
 1. Kanal Banner (ogori: 2560x1440)
 2. One Cikan Video (Trailer / Oto-baslatma)
 3. 4 Ana Oynatma Listesi
 4. Kanal Aciklamasi
 5. Kanal Baglantilari

API: YouTube Data API v3 (upload/token.json - youtube.force-ssl)
"""
import sys, os, json, time
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError): pass

REPO = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(REPO, "upload")
sys.path.insert(0, UPLOAD)
sys.path.insert(0, REPO)

from youtube_auth import get_authenticated_service

CHANNEL_ID = "UCbbcH8rtQTtz8R66jfKoSZg"

# Banner dosyasi (2560x1440) - upload sonrasinda raw URL olarak kullanilir
BANNER_PATH = os.path.join(REPO, "site", "assets", "youtube-banner-2560x1440.png")

# --------------------------- 4. KANAL ACIKLAMA ---------------------------
CHANNEL_DESCRIPTION = """🎵 Famous Music Studio — AI-assisted Turkish music production
🌙 Gece Masallari album · Night Drive DJ sets · Melodic Techno · Arabesk · Trap

🎧 Listen everywhere: https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar
☕ Support: https://ko-fi.com/famousmusicstudio
📱 TikTok: @famousmusicstudio | Instagram: @famous_music_studio
📧 Booking: booking@famousmusicstudio.com

📺 Tüm şarkılar: https://youtube.com/playlist?list=PLKFBTOXunWQ0
📺 Kısa kesitler: https://youtube.com/playlist?list=PLIfBoPfEuEWQ

Abone ol — yeni parçalar kaçmasın. 🔔 @Famous_musics_studio

Yapay zekâ destekli müzik ve görseller içerir."""

# --------------------------- 5. KANAL BAGLANTILAR ---------------------------
CHANNEL_LINKS = [
    {"rel": "other", "title": "Support on Ko-fi", "url": "https://ko-fi.com/famousmusicstudio"},
    {"rel": "other", "title": "Listen Everywhere (DistroKid)", "url": "https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar"},
    {"rel": "other", "title": "TikTok", "url": "https://tiktok.com/@famousmusicstudio"},
    {"rel": "other", "title": "Instagram", "url": "https://instagram.com/famous_music_studio"},
    {"rel": "other", "title": "Booking", "url": "mailto:booking@famousmusicstudio.com"},
]

# --------------------------- 3. ANA PLAYLISTLER ---------------------------
PLAYLISTS = [
    {
        "title": "🎧 Gece Sürüşleri — Melodic Techno & Night Drive",
        "desc": "Gece yarısı için tasarlanmış Melodic Techno ve Night Drive mixleri. Uzun, kesintisiz akış.",
        "video_ids": ["p_aqy1fVgeI", "dG3IFcyQvnM", "3morAyRFOhY", "-POsJbDVGAU", "Jp8DsUPg77U", "3MyDXRgl1xQ", "62DlYkzzNrc"],
    },
    {
        "title": "🌙 Arabesk & Trap Vibes — Türkçe Gece Müziği",
        "desc": "Türkçe arabesk, trap ve R&B: Gece Sürüşü, Dönmüyor Bu Yol, Küllerimden Geç ve daha fazlası.",
        "video_ids": ["HKTjVrrAgSk", "-CQ7MmUygTQ", "9qgIU8vcYZY", "kYEu28WcOxk", "O2VGj5SUz30", "FIkTi_SEI9w", "sTXz-7V1fzc", "NMFMXdUPBT8"],
    },
    {
        "title": "🎛️ DJ Setler — DJ Famous Live Mixes",
        "desc": "DJ Famous'un canlı ve stüdyo setleri. Melodic Techno, Progressive House ve Deep House akışları.",
        "video_ids": ["p_aqy1fVgeI", "dG3IFcyQvnM", "Jp8DsUPg77U", "-POsJbDVGAU", "3MyDXRgl1xQ", "62DlYkzzNrc"],
    },
    {
        "title": "🆕 Yeni Çıkanlar — Son Yüklemeler",
        "desc": "Kanalda en son yüklenen parçalar ve setler. Her hafta yenisi.",
        "video_ids": ["p_aqy1fVgeI", "HKTjVrrAgSk", "dG3IFcyQvnM"],
    },
]

# --------------------------- 2. ONE CIKAN VIDEO ---------------------------
# Abone olmayanlar icin on izleme videosu
UNSUBSCRIBED_TRAILER = "p_aqy1fVgeI"  # Night Drive - DJ Cut (21 dk)

# --------------------------- 1. KANAL BANNER ---------------------------
BANNER_GITHUB_URL = (
    "https://raw.githubusercontent.com/semtappdata-art/famous-music-studio/"
    "main/site/assets/youtube-banner-2560x1440.png"
)


def print_step(n, title):
    print(f"\n{'='*60}")
    print(f"[{n}/6] {title}")
    print("=" * 60)


def step_4_description(yt, dry_run=False):
    print_step(4, "KANAL ACIKLAMASI GUNCELLE")
    if dry_run:
        print(f"[DRY-RUN] aciklama yazilacak ({len(CHANNEL_DESCRIPTION)} karakter)")
        return True
    try:
        ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        bs = ch.get("brandingSettings", {})
        chan = bs.get("channel", {})
        chan["description"] = CHANNEL_DESCRIPTION
        body = {"id": CHANNEL_ID, "brandingSettings": {"channel": chan}}
        yt.channels().update(part="brandingSettings", body=body).execute()
        print("  OK: kanal aciklamasi guncellendi")
        return True
    except Exception as e:
        print(f"  HATA: {e}")
        return False


def step_5_links(yt, dry_run=False):
    print_step(5, "KANAL BAGLANTILARI")
    if dry_run:
        print(f"[KURU] {len(CHANNEL_LINKS)} link yazilacak:")
        for l in CHANNEL_LINKS:
            print(f"    {l['title']} -> {l['url']}")
        return True
    try:
        ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        bs = ch.get("brandingSettings", {})
        chan = bs.get("channel", {})
        chan["links"] = CHANNEL_LINKS
        body = {"id": CHANNEL_ID, "brandingSettings": {"channel": chan}}
        yt.channels().update(part="brandingSettings", body=body).execute()
        print(f"  OK: {len(CHANNEL_LINKS)} link eklendi")
        for l in CHANNEL_LINKS:
            print(f"    {l['title']} -> {l['url']}")
        return True
    except Exception as e:
        print(f"  HATA: {e}")
        return False


def step_2_trailer(yt, dry_run=False):
    print_step(2, "ONE CIKAN VIDEO (UNSUBSCRIBED TRAILER)")
    if dry_run:
        print(f"[KURU] trailer={UNSUBSCRIBED_TRAILER} ayarlanacak")
        return True
    try:
        ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        bs = ch.get("brandingSettings", {})
        chan = bs.get("channel", {})
        chan["unsubscribedTrailer"] = UNSUBSCRIBED_TRAILER
        body = {"id": CHANNEL_ID, "brandingSettings": {"channel": chan}}
        yt.channels().update(part="brandingSettings", body=body).execute()
        print(f"  OK: trailer={UNSUBSCRIBED_TRAILER} (Night Drive - DJ Cut)")
        return True
    except Exception as e:
        print(f"  HATA: {e}")
        return False


def step_3_playlists(yt, dry_run=False):
    print_step(3, "4 ANA OYNATMA LISTESI")
    ok = 0
    for pl in PLAYLISTS:
        title = pl["title"]
        if dry_run:
            print(f"  [KURU] olusturulacak: {title} ({len(pl['video_ids'])} video)")
            ok += 1
            continue
        try:
            existing = yt.playlists().list(
                part="snippet", channelId=CHANNEL_ID, maxResults=50
            ).execute()
            match = [i for i in existing.get("items", []) if i["snippet"]["title"] == title]
            if match:
                pid = match[0]["id"]
                print(f"    var: {title} ({pid})")
            else:
                res = yt.playlists().insert(
                    part="snippet,status",
                    body={
                        "snippet": {"title": title, "description": pl["desc"]},
                        "status": {"privacyStatus": "public"},
                    },
                ).execute()
                pid = res["id"]
                print(f"    olusturuldu: {title} ({pid})")
            # videolari ekle
            vid_ids = pl["video_ids"]
            existing_items = yt.playlistItems().list(
                part="contentDetails", playlistId=pid, maxResults=50
            ).execute()
            existing_ids = {it["contentDetails"]["videoId"] for it in existing_items.get("items", [])}
            added = 0
            for vid in vid_ids:
                if vid not in existing_ids:
                    yt.playlistItems().insert(
                        part="snippet",
                        body={"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}},
                    ).execute()
                    added += 1
            print(f"    eklenen video: {added}")
            ok += 1
        except Exception as e:
            print(f"  HATA ({title}): {e}")
    return ok == len(PLAYLISTS)


def step_1_banner(yt, dry_run=False):
    print_step(1, "KANAL BANNER (2560x1440)")
    if not os.path.isfile(BANNER_PATH):
        print(f"  HATA: banner dosya bulunamadi: {BANNER_PATH}")
        print("    Once create_youtube_banner.py calistirin.")
        return False
    print(f"  Banner dosya: {BANNER_PATH} ({os.path.getsize(BANNER_PATH)//1024} KB)")
    print(f"  Harici URL: {BANNER_GITHUB_URL}")
    if dry_run:
        print("[KURU] bannerExternalUrl degistirilecek")
        return True
    try:
        ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        bs = ch.get("brandingSettings", {})
        chan = bs.get("channel", {})
        if "image" not in chan:
            chan["image"] = {}
        chan["image"]["bannerExternalUrl"] = BANNER_GITHUB_URL
        body = {"id": CHANNEL_ID, "brandingSettings": {"channel": chan}}
        yt.channels().update(part="brandingSettings", body=body).execute()
        print("  OK: bannerExternalUrl degistirildi")
        return True
    except Exception as e:
        print(f"  HATA: {e}")
        return False


def main():
    yt = get_authenticated_service()
    print("Kimlik dogrulandi:", yt is not None)
    results = {}
    results[4] = step_4_description(yt)
    results[5] = step_5_links(yt)
    results[2] = step_2_trailer(yt)
    results[3] = step_3_playlists(yt)
    results[1] = step_1_banner(yt)

    print("\n" + "=" * 60)
    print("SONUC OZET")
    print("=" * 60)
    labels = {
        4: "Kanal aciklamasi",
        5: "Kanal baglantilari",
        2: "One cikan video (trailer)",
        3: "4 ana oynatma listesi",
        1: "Kanal banneri",
    }
    for n in sorted(results):
        print(f"  [{n}] {labels[n]}: {'TAMAM' if results[n] else 'HATA'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
