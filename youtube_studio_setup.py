#!/usr/bin/env python3
"""
Famous Music Studio — YouTube Studio 5 manuel işlemi, OTOMASYONLA.

Manuel (YouTube Studio arayüzünde) yapılması istenen 5 işlem, doğrudan
YouTube Data API v3 üzerinden yapılır. Böylece login/UI gerekmez ve
idempotent (tekrar çalıştırılabilir) olur.

İşlemler:
  1. KANAL BANNER      -> youtube.thumbnails().set(onBehalfOfContentOwnerChannel)
  2. ÖNE ÇIKAN VİDEO   -> channelSections: unsubscribedTrailer + subscribedTrailer
  3. 4 ANA PLAYLIST    -> playlists.insert + playlistItems.insert
  4. KANAL AÇIKLAMASI   -> channels.update(part=snippet)
  5. KANAL LİNKLERİ    -> channels.update(part=brandingSettings)
  (+) ANA SAYFA RAFLARI-> channelSections (playlist rafları + Shorts rafı)

Kullanım:
    python youtube_studio_setup.py --kuru        # sadece planla, yazma
    python youtube_studio_setup.py               # uygula
    python youtube_studio_setup.py --rapor       # sadece mevcut durumu göster
"""
import argparse
import json
import os
import re
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(REPO, "upload")
sys.path.insert(0, UPLOAD)
sys.path.insert(0, REPO)

from youtube_auth import get_authenticated_service  # noqa: E402

CHANNEL_ID = "UCbbcH8rtQTtz8R66jfKoSZg"
BANNER_PATH = os.path.join(REPO, "site", "assets", "youtube-banner-2560x1440.png")

# ---------------------------------------------------------------- 5. LİNKLER
KANAL_LINKLERI = [
    ("Ko-fi — Support the Studio", "https://ko-fi.com/famousmusicstudio"),
    ("Listen Everywhere — DistroKid", "https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar"),
    ("TikTok", "https://tiktok.com/@famousmusicstudio"),
    ("Instagram", "https://instagram.com/famous_music_studio"),
    ("Booking & Collabs", "mailto:booking@famousmusicstudio.com"),
]

# ---------------------------------------------------------------- 4. AÇIKLAMA
ACIKLAMA = """🎵 Famous Music Studio — AI-assisted Turkish music production
🌙 Gece Masalları album · Night Drive DJ sets · Melodic Techno · Arabesk · Trap

🎧 Listen everywhere: https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar
☕ Support: https://ko-fi.com/famousmusicstudio
📱 TikTok: @famousmusicstudio | Instagram: @famous_music_studio
📧 Booking: booking@famousmusicstudio.com

📺 Tüm şarkılar: https://youtube.com/playlist?list=PLKFBTOXunWQ0
📺 Kısa kesitler: https://youtube.com/playlist?list=PLIfBoPfEuEWQ

Abone ol — yeni parçalar kaçmasın. 🔔  @Famous_musics_studio

Yapay zekâ destekli müzik ve görseller içerir."""

# ---------------------------------------------------------------- 3. PLAYLIST'LER
# Anahtarlar: youtube_playlists.py'nin playlist_ids.json ile AYNI anahtar
# adları kullanılır -> otomasyon yeni listeleri de otomatik doldurur.
ANA_PLAYLISTLER = [
    {
        "anahtar": "gece_surusu",
        "baslik": "🎧 Gece Sürüşleri — Melodic Techno & Night Drive",
        "aciklama": (
            "Gece yarısı için tasarlanmış Melodic Techno ve Night Drive mixleri. "
            "Uzun, kesintisiz akış — DJ Famous'un imza setleri.\n\n"
            "Her cuma yeni şehir."
        ),
        "filtre": ["night drive", "city pulse", "melodic techno", "dj famous"],
        "haric_tut": ["#shorts"],
    },
    {
        "anahtar": "arabesk_trap_vibes",
        "baslik": "🌙 Arabesk & Trap Vibes — Türkçe Gece Müziği",
        "aciklama": (
            "Türkçe arabesk, trap ve R&B: Gece Sürüşü, Dönmüyor Bu Yol, "
            "Küllerimden Geç ve daha fazlası.\n\n"
            "Türkçe klasiği, modern prodüksiyonla buluşuyor."
        ),
        "filtre": ["arabesk", "trap", "hip-hop", "yükseliş", "gece seansı",
                   "dönmüyor", "küllerimden", "sofraya", "kader ortakları"],
        "haric_tut": ["#shorts"],
    },
    {
        "anahtar": "dj_setler",
        "baslik": "🎛️ DJ Setler — DJ Famous Live Mixes",
        "aciklama": (
            "DJ Famous'un canlı ve stüdyo setleri. Melodic Techno, Progressive "
            "House ve Deep House akışları — 20+ dakikalık kesintisiz dinleme.\n\n"
            "Her cuma yeni şehir için yeni set."
        ),
        "filtre": ["night drive", "city pulse", "deep focus", "dj famous",
                   "dj set", "mix"],
        "haric_tut": ["#shorts", "(sözleri)", "(remake)"],
    },
    {
        "anahtar": "yeni_cikanlar",
        "baslik": "🆕 Yeni Çıkanlar — Son Yüklemeler",
        "aciklama": (
            "Kanalda en son yüklenen parçalar ve setler. Her hafta yenisi.\n\n"
            "Abone ol ki hiçbirini kaçırma."
        ),
        "filtre": None,          # None = tüm videolar, tarih sırasıyla (en yeni 12)
        "haric_tut": ["#shorts"],
        "en_yeni_adet": 12,
    },
]

# ---------------------------------------------------------------- 2. ÖNE ÇIKAN
TRAILER_ABONE_OLMAYAN = "p_aqy1fVgeI"   # Night Drive - DJ Cut (21 dk)
TRAILER_ABONE = "dG3IFcyQvnM"           # Night Drive - Melodic Techno Mix 2026


def log(msg):
    print(msg)


def tum_videolar(yt):
    """Kanalın public videoları (başlık + ID + yayın tarihi)."""
    out = []
    token = None
    while True:
        resp = yt.search().list(
            part="snippet",
            channelId=CHANNEL_ID,
            type="video",
            order="date",
            maxResults=50,
            pageToken=token,
        ).execute()
        for it in resp.get("items", []):
            vid = it.get("id", {}).get("videoId")
            sn = it.get("snippet", {})
            if vid:
                out.append({
                    "id": vid,
                    "baslik": sn.get("title", ""),
                    "yayin": sn.get("publishedAt", ""),
                })
        token = resp.get("nextPageToken")
        if not token:
            break
    return out


def _filtrele(videolar, kural):
    """filtre: kelime listesi (hepsi küçük harf) veya None=hepsi."""
    if kural["filtre"] is None:
        aday = [v for v in videolar
                if not any(h in v["baslik"].lower() for h in kural["haric_tut"])]
        return aday[:kural.get("en_yeni_adet", 12)]

    sec = []
    for v in videolar:
        b = v["baslik"].lower()
        if any(h in b for h in kural["haric_tut"]):
            continue
        if any(f in b for f in kural["filtre"]):
            sec.append(v)
    return sec


def mevcut_playlistler(yt):
    """{baslik: playlist_id} + {playlist_id: title}"""
    baslik_map = {}
    id_map = {}
    token = None
    while True:
        resp = yt.playlists().list(
            part="snippet",
            channelId=CHANNEL_ID,
            maxResults=50,
            pageToken=token,
        ).execute()
        for p in resp.get("items", []):
            t = p["snippet"]["title"]
            baslik_map[t] = p["id"]
            id_map[p["id"]] = t
        token = resp.get("nextPageToken")
        if not token:
            break
    return baslik_map, id_map


def playlist_ogeleri(yt, pid, deneme=4):
    """Set olarak video ID'ler. Yeni playlist'ler olusturulduktan sonra
    yayilma gecikmesi olabiliyor -> 404 'playlistNotFound' retry'lanir."""
    son_hata = None
    for deneme_no in range(deneme):
        try:
            out = set()
            token = None
            while True:
                resp = yt.playlistItems().list(
                    part="contentDetails",
                    playlistId=pid,
                    maxResults=50,
                    pageToken=token,
                ).execute()
                for it in resp.get("items", []):
                    out.add(it["contentDetails"]["videoId"])
                token = resp.get("nextPageToken")
                if not token:
                    break
            return out
        except Exception as e:
            son_hata = e
            if "playlistNotFound" in str(e) or "cannot be found" in str(e):
                time.sleep(2 + deneme_no * 2)
                continue
            raise
    raise son_hata


def anahtari_yaz(anahtar, pid):
    """playlist_ids.json'a anahtar -> playlist_id yaz (atomik)."""
    import state_io
    yol = os.path.join(UPLOAD, "playlist_ids.json")
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        veri = {}
    veri[anahtar] = pid
    state_io.atomic_write(yol, veri)
    return veri


# ------------------------------------------------------------------ İŞLEMLER
def islem_banner(yt, kuru):
    log("\n[1/6] KANAL BANNER")
    if not os.path.isfile(BANNER_PATH):
        log(f"  ATLANDI: banner dosyasi yok ({BANNER_PATH})")
        return False
    if kuru:
        log(f"  [KURU] yuklenecek: {BANNER_PATH}")
        return True
    try:
        yt.thumbnails().set(
            onBehalfOfContentOwnerChannel=CHANNEL_ID,
            media_body=BANNER_PATH,
        ).execute()
        log(f"  OK: banner yuklendi (2560x1440)")
        return True
    except Exception as e:
        log(f"  HATA: {e}")
        return False


def islem_aciklama(yt, kuru):
    log("\n[4/6] KANAL ACIKLAMASI")
    if kuru:
        log(f"  [KURU] yazilacak:\n{ACIKLAMA}")
        return True
    # DİKKAT: channels.update(part=snippet) -> 400 ERROR_PART_UNEXPECTED.
    # Data API v3 sadece `brandingSettings` (ve `invideoPromotion`) part'ini
    # destekliyor. Açıklama brandingSettings.channel.description içinde
    # taşınır -- aynı alan, API'nin kabul ettiği yol.
    try:
        ch = yt.channels().list(
            part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        chan = ch.get("brandingSettings", {}).get("channel", {})
    except Exception as e:
        log(f"  HATA: mevcut brandingSettings okunamadi: {e}")
        return False

    body = {
        "id": CHANNEL_ID,
        "brandingSettings": {
            "channel": {
                "title": chan.get("title", "Famous Music Studio"),
                "description": ACIKLAMA,
                "keywords": chan.get("keywords", ""),
                "defaultLanguage": chan.get("defaultLanguage", "tr"),
                "country": chan.get("country", "TR"),
                "unsubscribedTrailer": TRAILER_ABONE_OLMAYAN,
            }
        },
    }
    try:
        yt.channels().update(part="brandingSettings", body=body).execute()
        # DOĞRULA
        ch2 = yt.channels().list(
            part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        yeni = ch2["brandingSettings"]["channel"].get("description", "")
        if ACIKLAMA.strip()[:40] in yeni:
            log(f"  OK: aciklama guncellendi ve DOGRULANDI ({len(yeni)} karakter)")
            return True
        log(f"  ! yazildi ama dogrulanamadi (beklenen baslangic yok)")
        log(f"    okunan: {yeni[:80]!r}")
        return False
    except Exception as e:
        log(f"  HATA: {e}")
        return False


def islem_linkler_ve_trailer(yt, kuru):
    log("\n[5/6] KANAL LINKLERI + [2/6] ONE CIKAN VIDEOLAR")
    try:
        ch = yt.channels().list(
            part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]
        chan = ch.get("brandingSettings", {}).get("channel", {})
    except Exception as e:
        log(f"  HATA: brandingSettings okunamadi: {e}")
        return False

    body = {
        "id": CHANNEL_ID,
        "brandingSettings": {
            "channel": {
                "title": chan.get("title", "Famous Music Studio"),
                "description": chan.get("description", ""),
                "keywords": chan.get("keywords", ""),
                "defaultLanguage": chan.get("defaultLanguage", "tr"),
                "country": chan.get("country", "TR"),
                # 2) ONE CIKAN VIDEOLAR
                "unsubscribedTrailer": TRAILER_ABONE_OLMAYAN,
                "subscribedTrailer": TRAILER_ABONE,
                # 5) LINKLER
                "links": [
                    {"rel": "self", "title": t, "url": u, "episode": False}
                    for t, u in KANAL_LINKLERI
                ],
            }
        },
    }
    if kuru:
        log(f"  [KURU] unsubscribedTrailer={TRAILER_ABONE_OLMAYAN}")
        log(f"  [KURU] subscribedTrailer={TRAILER_ABONE}")
        for t, u in KANAL_LINKLERI:
            log(f"  [KURU] link: {t} -> {u}")
        return True
    try:
        yt.channels().update(part="brandingSettings", body=body).execute()
        log(f"  OK: {len(KANAL_LINKLERI)} link + 2 trailer ayarlandi")
        return True
    except Exception as e:
        log(f"  HATA: {e}")
        return False


def islem_playlistler(yt, kuru):
    log("\n[3/6] 4 ANA PLAYLIST")
    videolar = tum_videolar(yt)
    baslik_map, id_map = mevcut_playlistler(yt)
    sonuc = {}

    for kural in ANA_PLAYLISTLER:
        secilen = _filtrele(videolar, kural)
        baslik = kural["baslik"]
        log(f"\n  -> {baslik}")
        log(f"     aday video: {len(secilen)}")

        if baslik in baslik_map:
            pid = baslik_map[baslik]
            log(f"     MEVCUT playlist: {pid}")
        else:
            if kuru:
                log("     [KURU] olusturulacak")
                sonuc[kural["anahtar"]] = None
                continue
            pid = yt.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": baslik,
                        "description": kural["aciklama"],
                        "defaultLanguage": "tr",
                    },
                    "status": {"privacyStatus": "public"},
                },
            ).execute()["id"]
            log(f"     OLUSTURULDU: {pid}")

        # videoları ekle
        mevcut = set() if kuru else playlist_ogeleri(yt, pid)
        eklenecek = [v for v in secilen if v["id"] not in mevcut]
        if kuru:
            log(f"     [KURU] eklenecek: {len(eklenecek)}")
            for v in eklenecek[:6]:
                log(f"        + {v['id']}  {v['baslik'][:52]}")
            if len(eklenecek) > 6:
                log(f"        ... +{len(eklenecek) - 6} daha")
            sonuc[kural["anahtar"]] = pid
            continue

        for v in eklenecek:
            try:
                yt.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": pid,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": v["id"],
                            },
                        }
                    },
                ).execute()
            except Exception as e:
                log(f"     ! video eklenemedi {v['id']}: {e}")
        log(f"     EKLENDI: {len(eklenecek)} (toplam {len(mevcut) + len(eklenecek)})")
        sonuc[kural["anahtar"]] = pid

    # playlist_ids.json'a yaz (otomasyon yeni listeleri de doldursun)
    if not kuru and sonuc:
        for anahtar, pid in sonuc.items():
            if pid:
                anahtari_yaz(anahtar, pid)
        log(f"\n  playlist_ids.json guncellendi: {sorted(k for k, v in sonuc.items() if v)}")
    return sonuc


def islem_ana_sayfa_raflari(yt, kuru, playlist_map):
    log("\n[+] ANA SAYFA RAFLARI (channelSections)")
    # Discovery enum'ları:
    #   type : singlePlaylist, multiplePlaylists, popularUploads, recentUploads,
    #          likes, allPlaylists, likedPlaylists, recentPosts, recentActivity,
    #          liveEvents, upcomingEvents, completedEvents, multipleChannels,
    #          postedVideos, postedPlaylists, subscriptions
    #   style: horizontalRow, verticalList
    # contentDetails: {"playlists": [playlistId...]}  (DÜZ liste, iç içe değil)
    if kuru:
        log("  [KURU] 4 playlist rafı + popularUploads + recentUploads")
        return True
    try:
        mevcut = yt.channelSections().list(
            part="snippet", channelId=CHANNEL_ID).execute()
        for it in mevcut.get("items", []):
            sn = it.get("snippet", {})
            log(f"  mevcut bolum: pos={sn.get('position')} type={sn.get('type')} "
                f"title={sn.get('title')}")
    except Exception as e:
        log(f"  okuma hatası: {e}")

    pos = 0
    for anahtar in ("gece_surusu", "arabesk_trap_vibes", "dj_setler", "yeni_cikanlar"):
        pid = playlist_map.get(anahtar)
        if not pid:
            continue
        baslik = next(k["baslik"] for k in ANA_PLAYLISTLER if k["anahtar"] == anahtar)
        try:
            yt.channelSections().insert(
                part="snippet,contentDetails",
                body={
                    "snippet": {
                        "type": "multiplePlaylists",
                        "style": "horizontalRow",
                        "position": pos,
                        "title": baslik,
                    },
                    "contentDetails": {
                        "channels": [CHANNEL_ID],
                        "playlists": [pid],
                    },
                },
            ).execute()
            log(f"  OK: raf -> {baslik} ({pid})")
            pos += 1
        except Exception as e:
            log(f"  ! raf {anahtar}: {str(e)[:160]}")

    for tip, baslik in (("popularUploads", "Popüler Videolar"),
                        ("recentUploads", "Son Yüklenenler"),
                        ("likes", "Beğeniler")):
        try:
            yt.channelSections().insert(
                part="snippet",
                body={
                    "snippet": {
                        "type": tip,
                        "style": "horizontalRow",
                        "position": pos,
                        "title": baslik,
                    }
                },
            ).execute()
            log(f"  OK: raf -> {baslik} ({tip})")
            pos += 1
        except Exception as e:
            log(f"  ! raf {tip}: {str(e)[:160]}")
    return True


def rapor(yt):
    ch = yt.channels().list(
        part="snippet,brandingSettings", id=CHANNEL_ID).execute()["items"][0]
    sn = ch["snippet"]
    bs = ch.get("brandingSettings", {}).get("channel", {})
    print("=" * 72)
    print("FAMOUS MUSIC STUDIO — KANAL DURUMU")
    print("=" * 72)
    print(f"Açıklama: {len(sn.get('description',''))} karakter")
    print(f"Trailer (abone olmayan): {bs.get('unsubscribedTrailer','(YOK)')}")
    print(f"Trailer (abone):         {bs.get('subscribedTrailer','(YOK)')}")
    print(f"Linkler: {len(bs.get('links',[]))}")
    for l in bs.get("links", []):
        print(f"   - {l.get('title')}: {l.get('url')}")
    print("\nBölümler:")
    for it in yt.channelSections().list(
            part="snippet,contentDetails", channelId=CHANNEL_ID).execute().get("items", []):
        s = it.get("snippet", {})
        print(f"   pos={s.get('position')} type={s.get('type')} title={s.get('title')}")
    print("\nAna playlist'ler:")
    baslik_map, _ = mevcut_playlistler(yt)
    for k in ANA_PLAYLISTLER:
        pid = baslik_map.get(k["baslik"])
        if pid:
            print(f"   OK  {k['baslik']}  ({pid}, {len(playlist_ogeleri(yt, pid))} video)")
        else:
            print(f"   --  {k['baslik']}  (YOK)")


def main():
    ap = argparse.ArgumentParser(description="YouTube Studio 5 manuel işlem — otomasyon")
    ap.add_argument("--kuru", action="store_true", help="sadece planla, yazma")
    ap.add_argument("--rapor", action="store_true", help="sadece mevcut durumu göster")
    args = ap.parse_args()

    yt = get_authenticated_service()

    if args.rapor:
        rapor(yt)
        return 0

    log(f"MOD: {'KURU (yazma yok)' if args.kuru else 'UYGULA'}")
    log(f"Kanal: {CHANNEL_ID}")

    islem_banner(yt, args.kuru)
    islem_aciklama(yt, args.kuru)
    islem_linkler_ve_trailer(yt, args.kuru)
    pmap = islem_playlistler(yt, args.kuru)
    islem_ana_sayfa_raflari(yt, args.kuru, pmap)

    log("\n" + "=" * 72)
    if args.kuru:
        log("KURU bitti — değişiklik YAZILMADI. Uygulamak için: --kuru OLMADAN çalıştır.")
    else:
        log("UYGULANDI. Doğrulama:")
        rapor(yt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
