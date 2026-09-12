"""Kanaldaki yorumları çeker ve YANIT BEKLEYENLERİ bir önbellek dosyasına yazar.

Neden ayrı bir modül ve neden önbellek:

  * Depoda bugüne kadar yorum OKUYAN tek satır kod yoktu. 6 gerçek yorum
    (4-8 Eylül) hiç görülmemişti — biri DJ set'ine gelmişti ve hangi projeye
    ait olduğu bile eşlenemiyordu.
  * Pano (Jarvis HUD) YouTube'a doğrudan gidemez: Hermes kendi Python
    ortamında koşuyor ve orada google-api-python-client yok. Ayrıca panoyu her
    açışta API'ye gitmek gereksiz kota harcar. İstatistikte kurulan desen
    burada da geçerli: boru hattı çeker, pano dosyayı okur.

KOTA: `commentThreads.list` + `allThreadsRelatedToChannelId` ile TÜM kanal
yorumları TEK istekte geliyor — sayfa başına 1 birim. Video video dolaşmak
(40 video = 40 istek) yerine 1-2 istek yetiyor.

YANIT YAZMA BU MODÜLDE YOK. Bilerek: yanıt 50 birim ve daha önemlisi
YouTube'un "high-volume, repetitive" spam tanımına giren tek şey şablon yanıt.
Yanıt, panodan tek tek onaylanarak gönderilmeli (bkz. plugin_api).

Kullanım:
    python upload/youtube_comments.py            # önbelleği tazele
    python upload/youtube_comments.py --print    # ekrana yaz
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(REPO, "comments_cache.json")
# Kok listesi ELLE SAYILMIYOR — tek kanonik kaynak uyumluluk.KOKLER (mutlak
# yollar). Eskiden burada ("projects", "dj_sets", "derlemeler") yaziyordu;
# icerigi dogruydu ama depoda ayni listenin YEDI kopyasi vardi ve yeni eklenen
# bir kok (derlemeler, 2026-09-11) bir kismina islenmemisti.
# Muhafiz: tests/test_kok_listesi_muhafizi.py
# KOKLER disaridan kullanilmiyor ama BILEREK yeniden disa veriliyor: bu modulu
# okuyan biri "hangi kokler taraniyor?" sorusunu burada cevaplayabilsin.
from uyumluluk import KOKLER, proje_klasorleri   # noqa: E402,F401

SAYFA_SINIRI = 3            # 3 x 100 yorum; bu katalog icin fazlasiyla yeter
TAZELEME_ARALIGI_SN = 60 * 60


def _video_haritasi() -> dict:
    """video_id -> "Proje Adi (uzun|short)". Yorumun hangi parcaya geldigini
    soylemek icin; kanal yaniti sadece videoId veriyor."""
    harita = {}
    for proje in proje_klasorleri():
        ad = os.path.basename(proje)
        sp = os.path.join(proje, "state.json")
        if not os.path.isfile(sp):
            continue
        try:
            with open(sp, "r", encoding="utf-8") as f:
                st = json.load(f)
        except (OSError, ValueError):
            continue
        for anahtar, tur in (("youtube_video_id", "uzun"),
                             ("youtube_shorts_video_id", "short")):
            if st.get(anahtar):
                harita[st[anahtar]] = "%s (%s)" % (ad, tur)
    return harita


def _onbellek_oku() -> dict:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _eskimis_mi() -> bool:
    veri = _onbellek_oku()
    damga = veri.get("cekildi")
    if not damga:
        return True
    try:
        t = time.mktime(time.strptime(damga, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return True
    return (time.time() - t) >= TAZELEME_ARALIGI_SN


def fetch_comments(force: bool = False) -> dict:
    """Kanal yorumlarini ceker, YANIT VERILMEMIS olanlari onbellege yazar."""
    if not force and not _eskimis_mi():
        return _onbellek_oku()

    yt = get_authenticated_service()
    kanal = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
    harita = _video_haritasi()

    bekleyen = []
    istek = 0
    tok = None
    while istek < SAYFA_SINIRI:
        r = yt.commentThreads().list(
            part="snippet", allThreadsRelatedToChannelId=kanal,
            order="time", maxResults=100, textFormat="plainText",
            pageToken=tok).execute()
        istek += 1
        for it in r.get("items", []):
            sn = it["snippet"]
            ust = sn["topLevelComment"]["snippet"]
            # Kanalin KENDI yorumu (ör. YouTube linki yorumu) yanit bekleyen
            # sayilmamali; yoksa her gonderi kendi kendine "cevaplanmamis"
            # goruunurdu.
            yazan_kanal = (ust.get("authorChannelId") or {}).get("value")
            if yazan_kanal == kanal:
                continue
            if sn.get("totalReplyCount", 0) > 0:
                continue          # zaten yanitlanmis
            vid = sn.get("videoId")
            bekleyen.append({
                "id": it["id"],
                "video_id": vid,
                "parca": harita.get(vid, "(eşleşmedi)"),
                "yazan": ust.get("authorDisplayName", "?"),
                "metin": (ust.get("textDisplay") or "").strip(),
                "tarih": (ust.get("publishedAt") or "")[:10],
                "begeni": ust.get("likeCount", 0),
            })
        tok = r.get("nextPageToken")
        if not tok:
            break

    veri = {
        "cekildi": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "istek": istek,
        "bekleyen": bekleyen,
    }
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    return veri


def main():
    ap = argparse.ArgumentParser(description="Yanıt bekleyen YouTube yorumlarını çeker.")
    ap.add_argument("--print", action="store_true", dest="yazdir", help="Ekrana yaz")
    ap.add_argument("--force", action="store_true", help="Önbellek taze olsa da çek")
    args = ap.parse_args()

    veri = fetch_comments(force=args.force)
    b = veri.get("bekleyen", [])
    print("yanıt bekleyen: %d  (çekildi: %s, istek: %s)" % (
        len(b), veri.get("cekildi"), veri.get("istek", "-")))
    if args.yazdir:
        for y in b:
            print()
            print("  %s — %s  (%s, %d beğeni)" % (y["parca"], y["yazan"], y["tarih"], y["begeni"]))
            print("    %s" % y["metin"][:200])


if __name__ == "__main__":
    main()
