"""DJ Famous — haftalık, GERÇEK bir kişiyi (bkz. dj_sets/README.md) konu alan,
tamamen AI-üretimi set videolarını render edip YouTube/TikTok/Instagram'a
yükler. auto_process.py'nin (günlük 6 üretimlik ana katalog) işlediği
projects/ klasörüne HİÇ dokunmaz — ayrı bir dj_sets/ klasörünü işler, ayrı
bir kilit dosyası kullanır, kendi log dosyasına yazar.

Kullanım:
    python dj_famous_process.py
    python dj_famous_process.py --privacy unlisted
    python dj_famous_process.py --no-schedule

Ana kataloğun aksine burada otomatik kademeleme YOK — haftada bir kez
Görev Zamanlayıcı ile çalıştırılması yeterli (bkz. setup_task_scheduler.ps1),
her çalıştırmada dj_sets/ altında bekleyen (audio hazır, henüz 3 platforma
tam yüklenmemiş) HER seti işler.

ÖNEMLİ — AI-üretimi olduğu GİZLENMEZ (kullanıcıyla netleştirilen tasarım
kararı, bkz. dj_sets/README.md):
  - YouTube: containsSyntheticMedia=True (youtube_upload.py'de zaten her
    yüklemede otomatik set ediliyor, burada ek bir şey gerekmiyor).
  - TikTok: tiktok_upload.py yüklerken "AI-generated content" etiketini
    TikTok uygulamasından elle açman gerektiğini zaten hatırlatıyor (genel,
    her proje için geçerli bir reminder).
  - Instagram: Meta'nın resmi 'is_ai_generated' API alanı doğrulanamadığı
    için (bkz. instagram_upload.py'deki not) caption'ın SONUNA
    social_text.build_ai_disclosure_line() ile tek, göze az batan bir satır
    ekleniyor — ana katalogda BU SATIR YOK, sadece DJ Famous'ta.
"""

import argparse
import json
import os
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import generate_cover
import render as render_module

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
RENDER_OUTPUTS = ["youtube_16x9.mp4", "shorts_9x16.mp4"]
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dj_famous_process.log")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dj_famous_process.lock")
# Ana kataloğun kilidinden (2 saat) çok daha yüksek — bir set ~1 saatlik ses
# içerebilir, render+3 platform yükleme normalde de çok daha uzun sürer.
LOCK_STALE_SECONDS = 8 * 60 * 60


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _acquire_lock() -> bool:
    if os.path.isfile(LOCK_PATH):
        age = time.time() - os.path.getmtime(LOCK_PATH)
        if age < LOCK_STALE_SECONDS:
            return False
        log(f"  Eski kilit dosyası bulundu ({age:.0f}s) — önceki çalıştırma muhtemelen "
            f"yarıda kalmış, yok sayılıp devam ediliyor.")
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True


def _release_lock() -> None:
    if os.path.isfile(LOCK_PATH):
        os.remove(LOCK_PATH)


def _has_any(project_dir: str, names: list) -> bool:
    return any(os.path.isfile(os.path.join(project_dir, n)) for n in names)


def _is_rendered(project_dir: str) -> bool:
    output_dir = os.path.join(project_dir, "output")
    return all(os.path.isfile(os.path.join(output_dir, n)) for n in RENDER_OUTPUTS)


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_pending_sets(base: str) -> list:
    """audio'su hazır olan ve henüz 3 platforma da tam yüklenmemiş TÜM
    dj_sets/ klasörlerini, oluşturulma zamanına göre sıralı döner."""
    pending = []
    if not os.path.isdir(base):
        return pending
    for name in os.listdir(base):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if not _has_any(project_dir, AUDIO_NAMES):
            continue
        state = _load_state(project_dir)
        fully_done = all(
            key in state
            for key in (
                "youtube_video_id", "youtube_shorts_video_id",
                "tiktok_publish_id", "instagram_media_id",
            )
        )
        if not fully_done:
            pending.append(project_dir)
    pending.sort(key=lambda p: (os.path.getctime(p), p))
    return pending


def process_set(project_dir: str, privacy: str, schedule: bool) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    try:
        generate_cover.generate(project_dir)
    except Exception as e:
        log(f"  cover/art üretimi HATA: {e}")
        return

    if not _is_rendered(project_dir):
        log(f"=== Render: {project_dir} ===")
        try:
            if not render_module.render_project(project_dir):
                log(f"  render başarısız, bu set atlanıyor: {project_dir}")
                return
        except Exception as e:
            log(f"  render HATA: {e}")
            return
    else:
        log(f"=== Zaten render edilmiş, upload kontrolüne geçiliyor: {project_dir} ===")

    state = _load_state(project_dir)
    youtube_video_id = state.get("youtube_video_id")

    if youtube_video_id:
        log("  YouTube: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_video as yt_upload
            youtube_video_id = yt_upload(project_dir, privacy, schedule=schedule)
            log(f"  YouTube: tamam, https://youtu.be/{youtube_video_id}")
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    if "youtube_shorts_video_id" in state:
        log("  YouTube Shorts: zaten yüklü, atlanıyor")
    elif not youtube_video_id:
        log("  YouTube Shorts atlandı: önce uzun format yüklenmeli")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_short as yt_upload_short
            shorts_id = yt_upload_short(project_dir, privacy, youtube_video_id, schedule=schedule)
            log(f"  YouTube Shorts: tamam, https://youtube.com/shorts/{shorts_id}")
        except Exception as e:
            log(f"  YouTube Shorts HATA: {e}")
    else:
        log("  YouTube Shorts atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    if "tiktok_publish_id" in state:
        log("  TikTok: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "tiktok_token.json")):
        try:
            from tiktok_upload import upload_video as tt_upload
            publish_id = tt_upload(project_dir)
            log(f"  TikTok: tamam (taslak/inbox), publish_id={publish_id} — TikTok uygulamasından "
                f"yayınla, 'AI-generated content' etiketini açmayı UNUTMA")
        except Exception as e:
            log(f"  TikTok HATA: {e}")
    else:
        log("  TikTok atlandı: upload/tiktok_token.json yok (önce tiktok_auth.py çalıştır)")

    def _log_instagram_result(media_id: str | None) -> None:
        if media_id:
            log(f"  Instagram: tamam, media_id={media_id}")
        else:
            log("  Instagram: konteyner hazır, golden-hour penceresi bekleniyor")

    if "instagram_media_id" in state:
        log("  Instagram: zaten yüklü, atlanıyor")
    elif "instagram_creation_id" in state:
        # Önceki çalıştırmada konteyner oluşturulmuş ama golden-hour dışında
        # kaldığı için yayınlanamamıştı (bkz. instagram_upload.try_publish_pending).
        # NOT: DJ Famous haftada bir çalıştığı için (varsayılan Cuma 18:00 —
        # BİLEREK config.GOLDEN_HOURS'un akşam penceresiyle örtüşüyor) bu dal
        # normalde hiç tetiklenmemeli; -DjFamousTime golden-hour DIŞINA
        # ayarlanırsa konteyner 24 saat içinde expire olabilir (bir sonraki
        # kontrol ancak bir hafta sonra gelir) — DjFamousTime'ı GOLDEN_HOURS
        # içinde tutmak en güvenlisi.
        try:
            from instagram_upload import try_publish_pending as ig_try_publish
            _log_instagram_result(ig_try_publish(project_dir))
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    elif os.path.isfile(os.path.join(upload_dir, "instagram_token.json")):
        try:
            from instagram_upload import upload_video as ig_upload
            from social_text import build_caption, build_ai_disclosure_line, resolve_language
            meta_path = os.path.join(project_dir, "meta.json")
            meta = {}
            if os.path.isfile(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            caption = build_caption(meta) + "\n\n" + build_ai_disclosure_line(resolve_language(meta))
            _log_instagram_result(ig_upload(project_dir, caption=caption))
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    else:
        log("  Instagram atlandı: upload/instagram_token.json yok (önce instagram_auth.py çalıştır)")


def main():
    parser = argparse.ArgumentParser(
        description="dj_sets/ altında bekleyen DJ Famous setlerini render edip yükler."
    )
    parser.add_argument(
        "--privacy", default="public", choices=["private", "unlisted", "public"],
        help="Yeni YouTube yüklemeleri için görünürlük (varsayılan: public)",
    )
    parser.add_argument("--base", default="dj_sets", help="Set klasörlerinin kök dizini")
    parser.add_argument(
        "--no-schedule", action="store_true",
        help="YouTube'un golden-hour zamanlamasını (config.GOLDEN_HOURS) devre dışı "
             "bırakıp hemen public yükler (bkz. auto_process.py --no-schedule).",
    )
    args = parser.parse_args()

    if not _acquire_lock():
        log("Başka bir dj_famous_process.py çalışması zaten sürüyor (kilit dosyası var) — "
            "bu çalıştırma atlanıyor.")
        return

    try:
        pending = find_pending_sets(args.base)
        if not pending:
            log("İşlenecek DJ Famous seti yok.")
            return

        log(f"{len(pending)} bekleyen set var, hepsi işlenecek: "
            f"{', '.join(os.path.basename(p) for p in pending)}")
        for project_dir in pending:
            process_set(project_dir, args.privacy, schedule=not args.no_schedule)

        log("Çalıştırma tamamlandı.")
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
