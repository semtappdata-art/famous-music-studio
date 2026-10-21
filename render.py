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
import validate_project
from audio_highlight import find_highlight
from upload.social_text import build_caption, hashtag, pick_subset, _dil_havuzlari

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


def _write_chapters_ffmeta(project_dir: str, meta: dict, duration: float, offset_sec: float = 0.0) -> str | None:
    """tracklist meta verisinden chapters.ffmeta dosyası üretir (FFmpeg chapter formatı).
    offset_sec: cold-open ön tadı kadar tüm chapter'ları ötele (video başı uzadığı için).
    Duration is set to max of passed duration and last chapter end time to ensure
    all chapters are within the declared duration (FFmpeg requirement)."""
    tracklist = meta.get("tracklist")
    if not tracklist:
        return None

    # Calculate actual chapter end times to determine proper file duration
    chapter_end_times = []
    for i, track in enumerate(tracklist):
        start_sec = track.get("start_sec")
        end_sec = track.get("end_sec")
        if start_sec is None and track.get("timestamp"):
            parts = track["timestamp"].split(":")
            if len(parts) == 2:
                start_sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                start_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None and i + 1 < len(tracklist):
            next_track = tracklist[i + 1]
            if next_track.get("start_sec") is not None:
                end_sec = next_track["start_sec"]
            elif next_track.get("timestamp"):
                parts = next_track["timestamp"].split(":")
                if len(parts) == 2:
                    end_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    end_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None:
            end_sec = duration - offset_sec  # duration includes offset, so subtract
        chapter_end_times.append(end_sec + offset_sec)

    # Use max of passed duration and last chapter end time
    file_duration = max(duration, max(chapter_end_times) if chapter_end_times else duration)

    lines = [";FFMETADATA1", f"duration={int(file_duration * 1000000000)}"]  # nanoseconds
    for i, track in enumerate(tracklist):
        start_sec = track.get("start_sec")
        end_sec = track.get("end_sec")
        if start_sec is None and track.get("timestamp"):
            parts = track["timestamp"].split(":")
            if len(parts) == 2:
                start_sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                start_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None and i + 1 < len(tracklist):
            next_track = tracklist[i + 1]
            if next_track.get("start_sec") is not None:
                end_sec = next_track["start_sec"]
            elif next_track.get("timestamp"):
                parts = next_track["timestamp"].split(":")
                if len(parts) == 2:
                    end_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    end_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None:
            end_sec = duration - offset_sec

        start_ns = int((start_sec + offset_sec) * 1000000000)
        end_ns = int((end_sec + offset_sec) * 1000000000)
        title = track.get("title", f"Track {i+1}")
        artist = track.get("artist", "")
        chapter_title = f"{title} - {artist}" if artist else title
        lines.append(f"[CHAPTER]")
        lines.append(f"TIMEBASE=1/1000000000")
        lines.append(f"START={start_ns}")
        lines.append(f"END={end_ns}")
        lines.append(f"title={chapter_title}")

    chapters_path = os.path.join(project_dir, "chapters.ffmeta")
    with open(chapters_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  chapters.ffmeta üretildi: {len(tracklist)} chapter (duration={file_duration:.1f}s)")
    return chapters_path


def render_project(project_dir: str) -> bool:
    name = os.path.basename(os.path.normpath(project_dir))
    print(f"\n=== {name} ===")

    # Render'dan önce kapsamlı sağlık kontrolü (bkz. validate_project.py) — bozuk
    # ses dosyası, geçersiz meta.json, art.jpg'nin yanlışlıkla cover ile birebir
    # aynı olması gibi hataları render BAŞLAMADAN yakalar. HATA varsa render'a
    # hiç girmiyoruz (saatler süren bir işi baştan boşa harcamamak için); UYARI
    # varsa loglayıp devam ediyoruz.
    val_errors, val_warnings = validate_project.validate(project_dir)
    validate_project.print_report(project_dir, val_errors, val_warnings)
    if val_errors:
        print(f"  Render durduruldu: {len(val_errors)} doğrulama hatası (yukarıda).")
        return False

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
    # DJ Famous gibi özel içerikler için kayan yazının içeriğini override eder
    # (ör. "DJ Famous  •  Hafta 1 Seti  •  #DJFamous ...") — sabit alt satır
    # ("Famous Music Studio") HER ZAMAN aynı kalır, bundan etkilenmez.
    marquee_override = meta.get("marquee_text")

    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    highlight_start = meta.get("highlight_start")
    highlight_end = meta.get("highlight_end")
    if (highlight_start is None) != (highlight_end is None):
        print(
            "  UYARI: meta.json'da highlight_start/highlight_end alanlarından sadece biri "
            "belirtilmiş, ikisi de gerekli — göz ardı edilip otomatik tespite geçiliyor."
        )
        highlight_start = highlight_end = None
    if highlight_start is None or highlight_end is None:
        if config.HIGHLIGHT_PLATFORMS:
            print("  highlight otomatik tespit ediliyor (en yoğun bölüm)...")
            highlight_start, highlight_end = find_highlight(audio_path, config.HIGHLIGHT_DURATION)
            print(f"  highlight: {highlight_start:.1f}s - {highlight_end:.1f}s")
    else:
        print(f"  highlight (meta.json'dan): {highlight_start:.1f}s - {highlight_end:.1f}s")

    # Chapter dosyasını üret (tracklist varsa)
    full_duration = ffmpeg_utils.get_audio_duration(audio_path)
    # BÜYÜME cold-open (madde 6): uzun videonun VE Shorts'ün başına highlight'tan
    # kısa ön tat eklenir; chapter'lar (uzun video için) aynı süre kadar ötelenir.
    cold_open_cfg = None
    cold_preview = 0.0
    if (
        getattr(config, "COLD_OPEN_ACIK", True)
        and any(p in getattr(config, "COLD_OPEN_PLATFORMLAR", ["youtube_16x9"]) for p in ("youtube_16x9", "shorts_9x16"))
        and highlight_start is not None and highlight_end is not None
        and highlight_end > highlight_start
    ):
        cold_preview = max(0.0, min(float(getattr(config, "COLD_OPEN_SURE_SN", 4.0)), highlight_end - highlight_start))
        if cold_preview > 0.0:
            cold_open_cfg = (highlight_start, highlight_end)
    chapters_path = _write_chapters_ffmeta(project_dir, meta, full_duration + cold_preview, offset_sec=cold_preview)
    metadata_file = chapters_path

    # BÜYÜME CTA (madde 11) + bitiş kartı (madde 10) — bayrak/metinden beslenir.
    theme_key = ffmpeg_utils.get_theme_key(theme)
    if getattr(config, "ABONE_CTA_ACIK", True):
        cta_cfg = config.ABONE_CTA_METIN.get(theme_key, config.ABONE_CTA_METIN["varsayilan"])
    else:
        cta_cfg = None
    end_card_cfg = meta.get("end_card_text")

    # Hashtag'leri üret (Shorts overlay için) — Title Case + Mavi renk
    def _generate_hashtags_list(meta: dict) -> list:
        """build_caption benzeri hashtag listesi üret."""
        title = meta.get("title", "Untitled")
        theme_key_local = meta.get("theme", config.DEFAULT_THEME)
        theme_local = config.THEMES.get(theme_key_local, config.THEMES[config.DEFAULT_THEME])
        genre_tags = [hashtag(theme_local["label"])] + [hashtag(t) for t in theme_local.get("related", [])]
        discovery_tags = pick_subset(title, _dil_havuzlari(meta)["kesif"], config.DISCOVERY_HASHTAG_COUNT, salt=13)
        all_tags = config.BRAND_HASHTAGS + discovery_tags + genre_tags
        # Liste formatında döndür (string yerine)
        return all_tags

    hashtags_list = _generate_hashtags_list(meta) if meta else []

    # --- BEAT SYNC (YouTube Shorts efekti) ---------------------------------
    # NEDEN burada: beat'ler kırpma aralığına göre bulunmalı (Shorts
    # highlight kırpması 30-60sn). Tespit cache'li (beat_sync.py) → ikinci
    # render'da anında.
    #
    # NEDEN "shorts_9x16" kontrolü: config.HIGHLIGHT_PLATFORMS = {"shorts_9x16"}
    # olduğu için kırpma Shorts'a özel; uzun formatta highlight_start/end
    # None'dır ve beat'ler tam dosyadan alınır.
    beat_times: list = []
    beat_period: float = 0.0
    speed_ramp: dict | None = None
    if getattr(config, "SHORTS_BEAT_SYNC_AKTIF", True):
        try:
            import beat_sync as _beat_sync
            _kirpma_var = ("shorts_9x16" in
                           getattr(config, "HIGHLIGHT_PLATFORMS", set())
                           and highlight_start is not None
                           and highlight_end is not None)
            _hs = highlight_start if _kirpma_var else None
            _he = highlight_end if _kirpma_var else None
            _analiz = _beat_sync.analiz_et(audio_path, start=_hs, end=_he)
            if _analiz.get("basari"):
                beat_period = float(_analiz.get("period") or 0.0)
                _ofset = _hs if _kirpma_var else 0.0
                _sure = (_he - _hs) if _kirpma_var else None
                beat_times = _beat_sync.kirp_beatler(
                    _analiz.get("beats", []), offset=_ofset, duration=_sure)
                print(f"  -> beat sync: bpm={_analiz.get('bpm')} "
                      f"beat={len(beat_times)}")
                # HIZ RAMPASI (YouTube efekti): yavaş başla, beat'te hızlan
                if getattr(config, "SHORTS_SPEED_RAMP_AKTIF", True):
                    speed_ramp = _beat_sync.hiz_rampasi_planla(
                        beat_times,
                        yavas_sure=float(getattr(
                            config, "SHORTS_SPEED_RAMP_YAVAS_SURE_SN", 1.6)),
                        yavas_kat=float(getattr(
                            config, "SHORTS_SPEED_RAMP_YAVAS_KAT", 0.55)))
                    if speed_ramp:
                        # NEDEN: ramp zaman cizgisini kaydiriyor; beat
                        # flasi post-ramp hesaplandigi icin beat'ler de
                        # ayni eslemeden gecirilmeli (a/v uyumsuzluk olmasin).
                        beat_times = _beat_sync.beatleri_zaman_esle(
                            beat_times, speed_ramp)
                        print(f"  -> hiz rampasi: snap@{speed_ramp['t_snap']}sn "
                              f"yavas x{speed_ramp['kat']}")
        except Exception as e:                               # noqa: BLE001
            print(f"  -> beat sync atlandi: {e}")

    def render_one(platform_key, width, height):
        output_path = os.path.join(output_dir, f"{platform_key}.mp4")
        print(f"  -> {platform_key} ({width}x{height}) render ediliyor...")
        use_highlight = platform_key in config.HIGHLIGHT_PLATFORMS
        is_shorts = platform_key == "shorts_9x16"
        # Cold-open: hem youtube_16x9 hem shorts_9x16 için etkin (config.COLD_OPEN_PLATFORMLAR'a göre)
        platform_cold_open = None
        if cold_open_cfg and platform_key in getattr(config, "COLD_OPEN_PLATFORMLAR", ["youtube_16x9"]):
            platform_cold_open = (cold_open_cfg[0], cold_open_cfg[1], cold_preview)
        # CTA ve End Card: hem uzun format hem Shorts için (Shorts'ta da görünebilir)
        platform_end_card = end_card_cfg
        platform_cta = cta_cfg
        ffmpeg_utils.render_video(
            art_path, audio_path, output_path, width, height, title, theme,
            marquee_override=marquee_override,
            start_time=highlight_start if use_highlight else None,
            end_time=highlight_end if use_highlight else None,
            # Chapter zaman damgaları tam süreye ait — 45sn highlight kırpmasına
            # gömülmez (aralık dışı kalır); sadece tam boy render'a gömülür.
            chapters_file=metadata_file if not use_highlight else None,
            is_shorts=is_shorts,
            cold_open=platform_cold_open,
            end_card_text=platform_end_card,
            cta_text=platform_cta,
            hashtags=hashtags_list if is_shorts else None,
            beat_times=beat_times if is_shorts else None,
            beat_period=beat_period if is_shorts else 0.0,
            speed_ramp=speed_ramp if is_shorts else None,
        )
        return platform_key, output_path

    ok = True
    # Kart maskesi/arka planı ilk kullanımda üretiliyor; paralel süreçler yarışıp
    # bozuk/eksik bir dosya yazmasın diye render başlamadan önce garantiye alıyoruz.
    theme_key = ffmpeg_utils.get_theme_key(theme)
    ffmpeg_utils.ensure_card_mask()
    for width, height in config.PLATFORMS.values():
        if art_path:
            ffmpeg_utils.ensure_art_backdrop(art_path, width, height)
        else:
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
