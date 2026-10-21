# -*- coding: utf-8 -*-
"""YouTube İLK YORUM — kanalın kendi yorumu (bölüm sorusu + abone çağrısı).

NEDEN VAR
---------
Bir videonun altındaki SABİTLENMİŞ (pinned) yorum, videonun en görünür
etkileşim alanıdır: izleyici önce yorumu okur, sonra videoya döner. İki
şeyi birden yapar:

  1. **Bölüm sorusu** — izleyici "favori bölümün hangisi, dakikasıyla yaz"
     der. Bu hem etkileşim sinyali (retention + yorum sayısı) hem de
     SONRAKİ videonun konusunu önceden haber verir.
  2. **Abone çağrısı** — "Abone ol, her yeni paragraftan önce haberdar ol".
     Videonun içindeki CTA (ABONE_CTA) 4 saniyelik bir bant; buradaki çağrı
     SÜREKLİ görünür ve okunabilir.

SIRA ÖNEMLİ: abone çağrısı ÖNCE geliyorsa ("Abone ol + soru") ikna
edici; soru önce geliyorsa ("soru + abone") sohbet başlatır. Mevcut
`social_text.build_ilk_yorum` İKİ SATIR (soru, abone) üretir — test bunu
kilitledi.

KOTA
----
`commentThreads.insert` = 50 birim (youtube_kota.MALIYETLER). Kota yetmezse
DOKUNULMAZ (fail-soft) — yükleme hattı durmaz.

GÜVENLİK
--------
* **Video başına TEK gönderim**: state.json'da `youtube_ilk_yorum_at`
  bayrağı. Test bunu kilitledi.
* **Kota kapısı**: `youtube_kota.yeterli_mi(50)`.
* **API hatası YUTULMAZ**: istisna yukarı çıkar, çağıran (`youtube_abone.py`
  / `auto_process`) yakalar → yükleme durmaz, sadece bu adım atlanır.
* **Politika kapısı**: `uyumluluk.kontrol(proje, "yukleme")` çağıran yapar
  (fail-closed). Bu modül kapıyı ATLAR.

KULLANIM
---------
    python upload/youtube_ilk_yorum.py --project "projects/X"
    python upload/youtube_ilk_yorum.py --hepsi
    python upload/youtube_ilk_yorum.py --project "projects/X" --dry-run
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BIRIM_ILK_YORUM = 50      # commentThreads.insert


def _state_oku(proje: str) -> dict:
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return {}
    return s if isinstance(s, dict) else {}


def _state_yaz(proje: str, alanlar: dict) -> None:
    """Atomik yazım (state_io deseni — CLAUDE.md §4: tek yazıcı)."""
    import state_io
    yol = os.path.join(proje, "state.json")
    state = _state_oku(proje)
    state.update(alanlar)
    state_io._atomik_yaz(yol, state)


def gonder(proje: str, log=print) -> bool:
    """Kanalın ilk yorumunu (soru + abone) gönderir.

    Dönüş: True (gönderildi) / False (atlandı — bayrak, kota, video yok).
    API hatası İSTİSNA olarak yukarı çıkar (modül yutmaz).
    """
    import youtube_kota
    from social_text import build_ilk_yorum, resolve_language

    state = _state_oku(proje)
    if state.get("youtube_ilk_yorum_at"):
        log("  ilk yorum: zaten gonderilmis — atlandi")
        return False
    if state.get("youtube_video_silinmis"):
        # Video API'de yok (silinmis) — tekrar denemek 404 uretir.
        log("  ilk yorum: video silinmis — atlandi")
        return False

    video_id = state.get("youtube_video_id")
    if not video_id:
        log("  ilk yorum: video yok — atlandi")
        return False

    if not youtube_kota.yeterli_mi(BIRIM_ILK_YORUM):
        log("  ilk yorum: kota yetersiz — atlandi")
        return False

    meta = {}
    meta_yol = os.path.join(proje, "meta.json")
    if os.path.isfile(meta_yol):
        try:
            with open(meta_yol, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if not isinstance(meta, dict):
                meta = {}
        except (OSError, ValueError):
            meta = {}

    lang = resolve_language(meta)
    metin = build_ilk_yorum(meta.get("title", "Untitled"), lang)

    from youtube_auth import get_authenticated_service
    yt = get_authenticated_service()
    yt.commentThreads().insert(
        part="snippet",
        body={"snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": metin}},
        }}).execute()

    _state_yaz(proje, {
        "youtube_ilk_yorum_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "youtube_ilk_yorum_metni": metin,
    })
    log("  ilk yorum gonderildi: %s" % video_id)
    return True


def _projeler() -> list:
    import uyumluluk
    out = []
    for kok in uyumluluk.KOKLER:
        if not os.path.isdir(kok):
            continue
        for ad in sorted(os.listdir(kok)):
            yol = os.path.join(kok, ad)
            if not os.path.isdir(yol):
                continue
            if _state_oku(yol).get("youtube_video_id"):
                out.append(yol)
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Kanalin ilk yorumunu (soru + abone cagrisi) gonderir.")
    ap.add_argument("--project", help="Tek proje klasoru")
    ap.add_argument("--hepsi", action="store_true", help="Tum yuklenmis videolar")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Sadece ne yapilacagini yaz")
    args = ap.parse_args()

    if args.project:
        projeler = [args.project]
    elif args.hepsi:
        projeler = _projeler()
    else:
        ap.error("--project ya da --hepsi gerekli")

    if args.dry_run:
        from social_text import build_ilk_yorum, resolve_language
        for p in projeler:
            st = _state_oku(p)
            if not st.get("youtube_video_id"):
                continue
            if st.get("youtube_ilk_yorum_at"):
                print("  [dry-run] zaten gonderilmis: %s" % os.path.basename(p))
                continue
            meta = {}
            mp = os.path.join(p, "meta.json")
            if os.path.isfile(mp):
                try:
                    with open(mp, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except (OSError, ValueError):
                    meta = {}
            if not isinstance(meta, dict):
                meta = {}
            metin = build_ilk_yorum(meta.get("title", "Untitled"),
                                     resolve_language(meta))
            print("  [dry-run] %s -> %r" % (os.path.basename(p), metin))
        return

    gonderilen = 0
    for p in projeler:
        try:
            if gonder(p):
                gonderilen += 1
        except Exception as e:                               # noqa: BLE001
            # API hatasi: bu adim atlanir, YUKLEME HATTI DURMAZ.
            print("  [HATA] %s: %s" % (os.path.basename(p), e))
    print("Gonderilen: %d" % gonderilen)


if __name__ == "__main__":
    main()
