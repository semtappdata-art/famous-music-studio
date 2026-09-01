"""Bekleyen (audio.wav + cover.jpg hazır) projeleri otomatik render edip
YouTube/TikTok/Instagram'a yükler — Windows Görev Zamanlayıcı ile periyodik
çalıştırılmak üzere tasarlandı.

Suno'da şarkı üretimi ve indirme hâlâ elle yapılmalı (bkz. suno_prompt_hazirlik.md)
— bu script sadece "audio.wav + cover.jpg bir proje klasörüne konduktan sonraki
her şeyi" (render + YouTube + TikTok + Instagram) otomatikleştiriyor.

Kullanım:
    python auto_process.py
    python auto_process.py --privacy unlisted
    python auto_process.py --base projects

Her çalıştırmada en fazla 2 proje işlenir (henüz 3 platforma da tam
yüklenmemiş olanlardan en eskisi + mümkünse ondan farklı temada olan bir
tane daha) — paylaşım sıklığını günde 2 farklı tarz şarkı ile sınırlı
tutmak için. Görev Zamanlayıcı günde bir kez çalışacak şekilde kurulmalı,
her iki şarkı da aynı koşuda arka arkaya işlenir.

Kendini iyileştiren mantık: proje için render sadece çıktı dosyaları eksikse
yapılır; her platforma yükleme sadece state.json'da o platforma ait alan
(youtube_video_id / tiktok_publish_id / instagram_media_id) yoksa denenir. Yani
bir platform bir çalıştırmada başarısız olursa, bir sonraki çalıştırmada sadece
o platform tekrar denenir — render veya diğer platformlar tekrarlanmaz.

Çıktı hem konsola hem auto_process.log dosyasına yazılır (Görev Zamanlayıcı
arka planda çalıştığında konsolu görmezsin, log dosyasından takip edersin).
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import render as render_module

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
RENDER_OUTPUTS = ["youtube_16x9.mp4", "shorts_9x16.mp4", "square_1x1.mp4"]
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_process.log")


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


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


def find_ready_projects(base: str) -> list:
    """audio+cover'ı hazır olan tüm proje klasörlerini döner (zaten tamamen
    işlenmiş olanlar dahil — process_project zaten-yapılmış adımları atlar,
    bu yüzden burada filtrelemeye gerek yok)."""
    ready = []
    if not os.path.isdir(base):
        return ready
    for name in sorted(os.listdir(base)):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if _has_any(project_dir, AUDIO_NAMES) and _has_any(project_dir, COVER_NAMES):
            ready.append(project_dir)
    return ready


def _is_fully_done(project_dir: str) -> bool:
    """Üç platforma da yüklenmişse True — bu proje için yapılacak bir şey kalmadı."""
    state = _load_state(project_dir)
    return all(
        key in state
        for key in ("youtube_video_id", "tiktok_publish_id", "instagram_media_id")
    )


def _project_theme(project_dir: str) -> str:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f).get("theme")
    return None


def pick_todays_projects(pending: list) -> list:
    """Bekleyen projelerden bugün işlenecek en fazla 2 taneyi seçer — ilki en
    eski bekleyen, ikincisi ise mümkünse ilkinden farklı temada olan en eski
    bekleyen (günde 2 farklı tarz hedefiyle). Farklı temada başka bekleyen
    proje yoksa, ikinci sıradaki proje temaya bakılmaksızın seçilir."""
    if not pending:
        return []
    todays = [pending[0]]
    first_theme = _project_theme(pending[0])
    for p in pending[1:]:
        if _project_theme(p) != first_theme:
            todays.append(p)
            break
    if len(todays) < 2 and len(pending) > 1:
        todays.append(pending[1])
    return todays


def process_project(project_dir: str, privacy: str) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    if not _is_rendered(project_dir):
        log(f"=== Render: {project_dir} ===")
        try:
            if not render_module.render_project(project_dir):
                log(f"  render başarısız, bu proje atlanıyor: {project_dir}")
                return
        except Exception as e:
            log(f"  render HATA: {e}")
            return
    else:
        log(f"=== Zaten render edilmiş, upload kontrolüne geçiliyor: {project_dir} ===")

    state = _load_state(project_dir)

    if "youtube_video_id" in state:
        log("  YouTube: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_video as yt_upload
            video_id = yt_upload(project_dir, privacy)
            log(f"  YouTube: tamam, https://youtu.be/{video_id}")
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    if "tiktok_publish_id" in state:
        log("  TikTok: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "tiktok_token.json")):
        try:
            from tiktok_upload import upload_video as tt_upload
            publish_id = tt_upload(project_dir)
            log(f"  TikTok: tamam (taslak/inbox), publish_id={publish_id} — TikTok uygulamasından yayınla")
        except Exception as e:
            log(f"  TikTok HATA: {e}")
    else:
        log("  TikTok atlandı: upload/tiktok_token.json yok (önce tiktok_auth.py çalıştır)")

    if "instagram_media_id" in state:
        log("  Instagram: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "instagram_token.json")):
        try:
            from instagram_upload import upload_video as ig_upload
            media_id = ig_upload(project_dir)
            log(f"  Instagram: tamam, media_id={media_id}")
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    else:
        log("  Instagram atlandı: upload/instagram_token.json yok (önce instagram_auth.py çalıştır)")


def main():
    parser = argparse.ArgumentParser(
        description="Bekleyen (audio+cover hazır) projeleri otomatik render edip yükler."
    )
    parser.add_argument(
        "--privacy", default="public", choices=["private", "unlisted", "public"],
        help="Yeni YouTube yüklemeleri için görünürlük (varsayılan: public)",
    )
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    args = parser.parse_args()

    ready = find_ready_projects(args.base)
    if not ready:
        log("İşlenecek proje yok (audio+cover hazır olan bulunamadı).")
        return

    pending = [p for p in ready if not _is_fully_done(p)]
    if not pending:
        log("Tüm hazır projeler zaten 3 platforma da yüklenmiş, yapılacak bir şey yok.")
        return

    # Günde en fazla 2 yeni şarkı işlenir, mümkünse farklı tarzda (paylaşım
    # sıklığını sürdürülebilir tutmak ve çeşitlilik sağlamak için) — Görev
    # Zamanlayıcı günde bir kez çalıştırılacak şekilde ayarlanmalı.
    todays = pick_todays_projects(pending)
    names = ", ".join(os.path.basename(p) for p in todays)
    log(f"{len(pending)} bekleyen proje var, bugün işlenecek ({len(todays)}): {names}")
    for project_dir in todays:
        process_project(project_dir, args.privacy)

    log("Çalıştırma tamamlandı.")


if __name__ == "__main__":
    main()
