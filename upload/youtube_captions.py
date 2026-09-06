"""YouTube'un otomatik (ASR) altyazısını gerçek sözlerle (`<slug>_sozler.md`)
hizalayıp, doğru METİN + doğru ZAMANLAMA içeren bir "Manuel altyazılar"
parçası olarak videoya yükler.

NEDEN GEREKLİ: YouTube'un kendi ASR altyazısı zamanlama açısından güvenilir
ama METNİ kendi ses-tanımasına göre yazıyor — sık sık yanlış kelime/eksik
noktalama üretiyor (bkz. 2026-09-06'da Gece Sürüşü/Sessiz Mektup/Kumdan
Denize/Beni Bırakma için elle yapılan inceleme ve düzeltme). Bu modül o elle
yapılan işi, SADECE gerçek sözleri elimizde olan projeler için otomatikleştiriyor
— `caption_align.align()` ASR'nin zamanlamasını gerçek kelimelerle eşleştiriyor.

NEDEN SADECE SÖZLER DOSYASI VARSA ÇALIŞIYOR: sözler yoksa elimizde ASR'nin
kendi (hatalı olabilecek) metninden başka bir şey yok — bunu "düzeltilmiş"
gibi otomatik yayınlamak, gerçekte hatalı kelimeleri de olduğu gibi
yayınlamak demek olurdu (Beni Bırakma'nın elle incelemesinde bulunan iki
belirsiz bölüm gibi — insan gözden geçirmesi gerektirdi, bkz. o projenin
state.json'ında captions_done hiç set edilmedi). Sözler dosyası yoksa
sessizce atlanır (`stock_art.find_lyrics_file` ile aynı "bulunamazsa None,
otomasyon durmaz" deseni) — YouTube'un kendi ASR/otomatik-çeviri altyazısı
varsayılan kaynak olarak kalmaya devam eder.

NEDEN "PENDING" (tekrar deneme) GEREKİYOR: YouTube'un ASR'si yükleme
sonrası HEMEN hazır olmuyor (işleme süresi dakikalar-saatler arası değişken).
auto_process.py bu yüzden `youtube_captions_done` state.json'da set olana
kadar HER koşuda tekrar dener (Instagram'ın golden-hour konteyner kuyruğuyla
AYNI desen, bkz. auto_process.py::_drain_golden_hour_queue) — ASR track'i
henüz yoksa sessizce bir sonraki koşuya bırakılır, hiçbir hata otomasyonu
durdurmaz.

MEVCUT (manuel) BİR ALTYAZI PARÇASI VARSA: insert() değil update() kullanılır
— bu, 2026-09-06'da elle (YouTube Studio üzerinden) düzeltilmiş 4 şarkının
(Gece Sürüşü, Sessiz Mektup, Kumdan Denize, kısmen Beni Bırakma) üzerine
otomasyon tekrar çalıştığında DUPLICATE bir "Manuel altyazılar (2)" parçası
oluşturmak yerine, aynı parçayı (idempotent, zararsız) yeniden yazmasını
sağlıyor.
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from googleapiclient.http import MediaFileUpload

import caption_align
import ffmpeg_utils
import stock_art
from social_text import resolve_language
from youtube_auth import get_authenticated_service

VIDEO_FILENAME = "youtube_16x9.mp4"


def _load_json(path: str) -> dict:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _update_state(project_dir: str, fields: dict) -> None:
    state_path = os.path.join(project_dir, "state.json")
    state = _load_json(state_path)
    state.update(fields)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _find_caption_tracks(youtube, video_id: str):
    """(asr_track_id, manual_track_id) döner — ikisi de yoksa None. Birden
    fazla manuel parça olması beklenmiyor (bu modül idempotent, üzerine
    yazar) ama varsa ilkini alır."""
    resp = youtube.captions().list(part="snippet", videoId=video_id).execute()
    asr_id = None
    manual_id = None
    for item in resp.get("items", []):
        if item["snippet"].get("trackKind") == "ASR":
            asr_id = item["id"]
        elif manual_id is None:
            manual_id = item["id"]
    return asr_id, manual_id


def sync_captions(project_dir: str) -> str:
    """Döner: "done" (bu koşuda yayınlandı/güncellendi), "already" (daha
    önce yapılmıştı), "skipped" (sözler dosyası/video/render çıktısı yok —
    kalıcı, bu proje için bir daha denenmeyecek bir durum DEĞİL, sadece bu
    koşuda uygulanabilir değil), "pending" (video var ama YouTube'un ASR'si
    henüz hazır değil — sonraki koşuda tekrar denenecek)."""
    state = _load_json(os.path.join(project_dir, "state.json"))
    if state.get("youtube_captions_done"):
        return "already"

    video_id = state.get("youtube_video_id")
    if not video_id:
        return "skipped"

    meta = _load_json(os.path.join(project_dir, "meta.json"))
    lyrics_path = stock_art.find_lyrics_file(meta.get("title", ""))
    if not lyrics_path:
        return "skipped"

    video_path = os.path.join(project_dir, "output", VIDEO_FILENAME)
    if not os.path.isfile(video_path):
        return "skipped"

    youtube = get_authenticated_service()
    asr_track_id, manual_track_id = _find_caption_tracks(youtube, video_id)
    if not asr_track_id:
        return "pending"

    asr_bytes = youtube.captions().download(id=asr_track_id, tfmt="srt").execute()
    duration = ffmpeg_utils.get_audio_duration(video_path)

    tmp_dir = tempfile.mkdtemp(prefix="yt_captions_")
    asr_path = os.path.join(tmp_dir, "asr.srt")
    out_path = os.path.join(tmp_dir, "aligned.srt")
    try:
        with open(asr_path, "wb") as f:
            f.write(asr_bytes)

        cues = caption_align.align(asr_path, lyrics_path, duration)
        if not cues:
            return "skipped"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(caption_align.format_srt(cues))

        media = MediaFileUpload(out_path, mimetype="application/octet-stream")
        if manual_track_id:
            youtube.captions().update(
                part="snippet",
                body={"id": manual_track_id, "snippet": {"isDraft": False}},
                media_body=media,
            ).execute()
        else:
            youtube.captions().insert(
                part="snippet",
                sync=False,
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": resolve_language(meta),
                        "name": "",
                        "isDraft": False,
                    }
                },
                media_body=media,
            ).execute()

        _update_state(project_dir, {
            "youtube_captions_done": True,
            "youtube_captions_synced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        return "done"
    finally:
        for p in (asr_path, out_path):
            if os.path.isfile(p):
                os.remove(p)
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
