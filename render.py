"""Suno ses dosyalarından tüm platformlar için video üreten ana script.

Kullanım:
    python render.py --project projects/sarki-adi
    python render.py --all
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import ffmpeg_utils
from audio_highlight import find_highlight

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]
AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]


def find_cover(project_dir: str) -> str | None:
    for name in COVER_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def find_art(project_dir: str) -> str | None:
    """Kart içinde gösterilecek opsiyonel görsel — cover.jpg'den (thumbnail) FARKLI.
    Yoksa render_video düz renge (config.CARD_ART_COLOR) düşer."""
    for name in ART_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def find_audio(project_dir: str) -> str | None:
    for name in AUDIO_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def render_project(project_dir: str) -> bool:
    name = os.path.basename(os.path.normpath(project_dir))
    print(f"\n=== {name} ===")

    audio_path = find_audio(project_dir)
    if not audio_path:
        print(f"  HATA: {project_dir} içinde audio.wav/.mp3/.m4a bulunamadı, bu proje atlanıyor.")
        return False

    cover_path = find_cover(project_dir)
    if not cover_path:
        print(f"  HATA: {project_dir} içinde cover.jpg/.jpeg/.png bulunamadı, bu proje atlanıyor.")
        return False

    art_path = find_art(project_dir)
    print(f"  kart içeriği: {'art görseli (' + art_path + ')' if art_path else 'düz renk (art.jpg yok)'}")

    meta = load_meta(project_dir)
    title = meta.get("title")
    theme = meta.get("theme")

    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    highlight_start = meta.get("highlight_start")
    highlight_end = meta.get("highlight_end")
    if highlight_start is None or highlight_end is None:
        if config.HIGHLIGHT_PLATFORMS:
            print("  highlight otomatik tespit ediliyor (en yoğun bölüm)...")
            highlight_start, highlight_end = find_highlight(audio_path, config.HIGHLIGHT_DURATION)
            print(f"  highlight: {highlight_start:.1f}s - {highlight_end:.1f}s")
    else:
        print(f"  highlight (meta.json'dan): {highlight_start:.1f}s - {highlight_end:.1f}s")

    def render_one(platform_key, width, height):
        output_path = os.path.join(output_dir, f"{platform_key}.mp4")
        print(f"  -> {platform_key} ({width}x{height}) render ediliyor...")
        use_highlight = platform_key in config.HIGHLIGHT_PLATFORMS
        ffmpeg_utils.render_video(
            art_path, audio_path, output_path, width, height, title, theme,
            start_time=highlight_start if use_highlight else None,
            end_time=highlight_end if use_highlight else None,
        )
        return platform_key, output_path

    ok = True
    # Kart maskesi/parlaması ilk kullanımda üretiliyor; paralel süreçler yarışıp
    # bozuk/eksik bir dosya yazmasın diye render başlamadan önce garantiye alıyoruz.
    theme_key = ffmpeg_utils.get_theme_key(theme)
    ffmpeg_utils.ensure_card_mask()
    ffmpeg_utils.ensure_card_glow(theme_key)
    for width, height in config.PLATFORMS.values():
        ffmpeg_utils.ensure_vignette(width, height, theme_key)

    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_RENDERS) as executor:
        futures = {
            executor.submit(render_one, platform_key, width, height): platform_key
            for platform_key, (width, height) in config.PLATFORMS.items()
        }
        for future in as_completed(futures):
            platform_key = futures[future]
            try:
                _, output_path = future.result()
                print(f"     tamam: {output_path}")
            except Exception as e:
                print(f"     HATA ({platform_key}): {e}")
                ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Suno ses dosyalarından çoklu platform video üretir.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Tek bir proje klasörü (örn. projects/sarki-adi)")
    group.add_argument("--all", action="store_true", help="projects/ altındaki tüm klasörleri render et")
    args = parser.parse_args()

    if args.project:
        project_dirs = [args.project]
    else:
        base = "projects"
        if not os.path.isdir(base):
            print(f"HATA: {base} klasörü bulunamadı.")
            sys.exit(1)
        project_dirs = [
            os.path.join(base, name)
            for name in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, name))
        ]
        if not project_dirs:
            print(f"HATA: {base} altında hiç proje klasörü yok.")
            sys.exit(1)

    all_ok = True
    for project_dir in project_dirs:
        if not render_project(project_dir):
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
