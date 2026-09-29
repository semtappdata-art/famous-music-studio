# -*- coding: utf-8 -*-
"""YouTube İLK YORUM (kanalın kendi yorumu — Studio/telefondan sabitlenir).

Neden var: açıklama satırlarını neredeyse kimse açmıyor; sabitlenmiş ilk
yorum videonun altında herkesin gördüğü ilk satır (abone + bölüm sorusu).
`social_text.build_ilk_yorum()` metni kurar, bu modül GÖNDERİR.

Kurallar (hepsi bilinçli):
- Video başına TEK yorum: `youtube_ilk_yorum_at` bayrağı varsa çıkılır.
  Metin de deterministik (aynı video aynı metin) — ikinci kilit.
- Kota kapısı: `comments.insert` 50 birim. `youtube_kota.yeterli_mi(60)`
  False ise DOKUNULMAZ (yükleme hattının kotasını yemek yok — 2026-09-06
  captions dersi). Sessiz de değil: `uyar_bir_kez` log'a düşer.
- Sabitleme (pin) API'de YOK — ilk yorum atılır, pin Studio/telefondan
  10 saniyede elle basılır. Pin basılmasa bile ilk yorum en üstte durur.
- `_is_fully_done()`'a EKLENMEZ (altyazı kuralıyla aynı gerekçe: asla "tam"
  olamayan proje kuyruğu tıkar).
- Hata = log + çık. Yorum, yüklemeyi ASLA durdurmaz.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BIRIM_YORUM = 50
KOTA_PAYI = 60


def _durum_oku(project_dir: str) -> dict:
    import json
    try:
        with open(os.path.join(project_dir, "state.json"), encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def gonder(project_dir: str, log=print) -> bool:
    """İlk yorumu gönderir; gönderildiyse/atlanırsa False, yeni gönderimde True."""
    import notify
    import state_io
    import youtube_kota
    from social_text import build_ilk_yorum, resolve_language
    from youtube_auth import get_authenticated_service

    try:
        with open(os.path.join(project_dir, "meta.json"), encoding="utf-8") as f:
            import json
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}
    state = _durum_oku(project_dir)
    video_id = state.get("youtube_video_id")
    if not video_id:
        return False
    if state.get("youtube_ilk_yorum_at"):
        return False
    if not youtube_kota.yeterli_mi(KOTA_PAYI):
        notify.uyar_bir_kez("youtube_ilk_yorum_kota",
                            "İlk yorum atlandı: kota yetersiz (video %s)" % video_id)
        log("  YouTube ilk yorum atlandı: kota yetersiz")
        return False

    title = meta.get("title") or os.path.basename(project_dir.rstrip("/\\"))
    metin = build_ilk_yorum(title, resolve_language(meta))
    youtube = get_authenticated_service()
    youtube.commentThreads().insert(
        part="snippet",
        body={"snippet": {"videoId": video_id,
                          "topLevelComment": {"snippet": {"textOriginal": metin}}}},
    ).execute()
    state["youtube_ilk_yorum_at"] = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    state_io.durum_yaz(project_dir, state)
    log("  YouTube ilk yorum gönderildi (sabitleme Studio'dan elle)")
    return True
