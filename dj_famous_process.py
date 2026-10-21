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
    social_text modulunun AI beyani yardimcisi ile tek, göze az batan bir satır
    ekleniyor — ana katalogda BU SATIR YOK, sadece DJ Famous'ta.
"""

import argparse
import json
import os
import sys
import time

for _stream in (sys.stdout, sys.stderr):
    try:
        print("DEBUG: entering try block")
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".claude/worktrees/dj-city-pulse-set"))

import cover_generator as generate_cover
import asyncio
import tools
import config
from suno_mcp_wrapper import SunoProducerMCP, TrackSpec
from state_io import atomic_write, load_state
import render as render_module

# Optional improvements imports
try:
    import librosa
    LIBROSA_AVAILABLE = True
except Exception:
    LIBROSA_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

import numpy as np

def _apply_hook(wav_path: str) -> None:
    """Apply a volume boost hook: detect onset and boost volume around it."""
    if not LIBROSA_AVAILABLE:
        hooked = wav_path.replace(".wav", "_hook.wav")
        cmd = ["ffmpeg", "-y", "-i", wav_path, "-af", "volume=enable='between(t,0,3)':volume=2", hooked]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Hook uygulanamadı: {result.stderr}")
        os.replace(hooked, wav_path)
        return

    try:
        y, sr = librosa.load(wav_path, sr=None)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        peaks = librosa.util.peak_pick(onset_env, pre_max=3, post_max=3, pre_avg=3, post_avg=3, delta=0.5, wait=0)
        if len(peaks) == 0:
            onset_sec = 0.0
        else:
            peak_idx = peaks[np.argmax(onset_env[peaks])]
            onset_sec = librosa.frames_to_time(peak_idx, sr=sr)
        duration = librosa.get_duration(y=y, sr=sr)
        hook_start = max(0.0, onset_sec)
        hook_end = min(duration, hook_start + 3.0)
        afilter = f"volume=enable='between(t,{hook_start:.3f},{hook_end:.3f})':volume=2"
        hooked = wav_path.replace('.wav', '_hook.wav')
        cmd = ["ffmpeg", "-y", "-i", wav_path, "-af", afilter, hooked]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Hook uygulanamadı: {result.stderr}")
        os.replace(hooked, wav_path)
        log(f"  Hook uygulandı: onset={onset_sec:.2f}s, window={hook_start:.2f}-{hook_end:.2f}s")
    except Exception as e:
        log(f"  Hook tespiti sırasında hata, sabit hook uygulanıyor: {e}")
        hooked = wav_path.replace('.wav', '_hook.wav')
        cmd = ["ffmpeg", "-y", "-i", wav_path, "-af", "volume=enable='between(t,0,3)':volume=2", hooked]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Hook uygulanamadı: {result.stderr}")
        os.replace(hooked, wav_path)

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


def _fetch_top_references(query: str, max_results: int = 5) -> list[dict]:
    """
    Son 1 ay içinde verilen sorgu için YouTube videolarını
    (başlık, videoId, süre[saniye]) çeker.
    Dönen liste: [{'title': str, 'videoId': str, 'duration_sec': int}, ...]
    """
    import json, re, html
    import tools
    raw = tools.web_search_exa(
        query=f"{query} site:youtube.com posted:last month",
        objective="En çok izlenen, en yüksek etkileşimli melodik techno / deep house setlerinin listesini al",
        numResults=max_results,
    )
    results = []
    for block in raw.split("\n\n"):
        m_title = re.search(r"^([^\n]+)", block, re.M)
        m_url = re.search(r"https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})", block)
        m_dur = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", block)
        if not (m_title and m_url and m_dur):
            continue
        title = html.unescape(m_title.group(1).strip())
        vid = m_url.group(1)
        h, m, s = m_dur.groups(default="0")
        dur = int(h)*3600 + int(m)*60 + int(s)
        results.append({"title": title, "videoId": vid, "duration_sec": dur})
    return results[:max_results]


def _determine_suno_segment_length(top_refs: list[dict]) -> int:
    """
    - En uzun tek Suno üretimi yaklaşık 120 saniye (2 dakika) – bu limiti aşmayız.
    - Referansların ortalama süresini alır; eğer 120’den büyükse 120’ye,
      küçükse o değere yuvarlar (en az 30 s).
    """
    if not top_refs:
        return 90   # fallback: 1:30 dakika
    avg = sum(r["duration_sec"] for r in top_refs) / len(top_refs)
    target = min(120, max(30, round(avg)))
    return target   # saniye cinsiden


def _generate_dj_set_audio(project_dir: str) -> str:
    import asyncio, json, os
    from suno_mcp_wrapper import SunoProducerMCP, TrackSpec
    from config import SET_STILLERI
    meta_path = os.path.join(project_dir, "meta.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    set_style = meta.get("set_style", "techno_chill")
    # Determine segment length via references
    style_label = SET_STILLERI[set_style]["label"]
    query = f"{style_label} set"
    top_refs = _fetch_top_references(query)
    seg_len = _determine_suno_segment_length(top_refs)
    # Target total length 45-60 minutes; we'll aim for 50 minutes
    target_total = 50 * 60  # seconds
    # Build TrackSpec
    spec = TrackSpec(
        title=meta.get("title", "Untitled DJ Set"),
        project_dir=project_dir,
        prompt=meta.get("art_query", ""),
        style_raw=SET_STILLERI[set_style]["suno_stil"],
        vocal_gender="",
        target_duration_sec=target_total,
    )
    producer = SunoProducerMCP()
    # Generate initial segment
    gen_result = asyncio.run(producer.generate_track(spec))
    if gen_result.error:
        raise RuntimeError(f"Suno generate error: {gen_result.error}")
    # Extend if needed
    remaining = max(0, target_total - (gen_result.duration or seg_len))
    extend_count = 0
    while remaining > 0:
        chunk = min(seg_len, remaining)
        ext_result = asyncio.run(producer.mcp.extend(
            audio_id=gen_result.audio_id,
            continue_at=(gen_result.duration or seg_len) + extend_count * seg_len,
            lyric="",
            model="chirp-v5-5",
            style=SET_STILLERI[set_style]["suno_stil"],
            duration=int(chunk)
        ))
        if ext_result.error:
            raise RuntimeError(f"Suno extend error: {ext_result.error}")
        gen_result.audio_id = ext_result.audio_id
        remaining -= chunk
        extend_count += 1
    # Download and convert to wav (using existing wait_and_download which deletes mp3 after)
    wav_path = asyncio.run(producer.wait_and_download(gen_result.audio_id, project_dir))
    _apply_hook(wav_path)
    if not os.path.isfile(wav_path):
        raise RuntimeError("WAV dosyası oluşturulamadı")
    return wav_path


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


def _topluluk_bildir(project_dir: str, video_id: str, log_fn=log) -> None:
    """Yeni yayinlanan DJ seti topluluğa bildir (Madde 29).

    FAIL-SAFE: hata olursa yayin geri alinmaz, sadece bildirim atlanir.
    (auto_process.py'deki ayni fonksiyonun DJ set'e uyarlanmis hali.)
    """
    try:
        import topluluk
    except Exception as e:
        log_fn(f"  Topluluk bildirimi atlandi (modul hatasi): {e}")
        return

    try:
        meta = {}
        meta_yolu = os.path.join(project_dir, "meta.json")
        if os.path.isfile(meta_yolu):
            with open(meta_yolu, encoding="utf-8") as f:
                meta = json.load(f) or {}

        baslik = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
        stil = meta.get("set_style") or "DJ Set"
        konum = ""
        loc = meta.get("location")
        if isinstance(loc, dict) and loc.get("city"):
            konum = f"📍 {loc.get('city')}, {loc.get('country', '')}".rstrip(", ")

        link = f"https://youtu.be/{video_id}"
        site = getattr(config, "SITE_URL", "https://famousmusicstudio.com")

        mesaj = (
            f"**{baslik}**\n\n"
            f"🎛️ {stil}\n"
            + (f"{konum}\n" if konum else "")
            + f"▶️ {link}\n\n"
            f"🌐 {site}\n"
            f"🔔 Abone ol → https://youtube.com/@{getattr(config, 'YOUTUBE_HANDLE', 'Famous_musics_studio')}"
        )

        sonuc = topluluk.bildir(baslik=f"🎛️ {baslik}", mesaj=mesaj, link=link)
        kanallar = []
        if sonuc.get("discord"):
            kanallar.append("Discord")
        if sonuc.get("telegram"):
            kanallar.append("Telegram")
        if sonuc.get("abone_sayisi"):
            kanallar.append(f"{sonuc['abone_sayisi']} abone logu")
        if kanallar:
            log_fn(f"  📣 Topluluk bildirimi: {', '.join(kanallar)}")
        else:
            log_fn("  📣 Topluluk bildirimi: kanal yapilandirilmamis (atlandi)")
    except Exception as e:
        log_fn(f"  📣 Topluluk bildirimi HATA (yayin etkilenmedi): {e}")


def process_set(project_dir: str, privacy: str, schedule: bool) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    # VALIDATION KAPISI — YouTube Algoritması Blueprint kuralları
    # Render/Upload başlamadan TÜM kurallar kontrol edilir (CLAUDE.md §13 ön-kontrol)
    try:
        import validate_project
        val_errors, val_warnings = validate_project.validate(project_dir)
        validate_project.print_report(project_dir, val_errors, val_warnings)
        if val_errors:
            log(f"  VALIDATION HATASI — Bu set işlenmeyecek, hatalar giderilmeli:")
            for e in val_errors:
                log(f"    - {e}")
            return
        if val_warnings:
            log(f"  UYARI: {len(val_warnings)} uyarı — üretim devam ediyor ama öneri giderilmeli:")
            for w in val_warnings:
                log(f"    - {w}")
    except Exception as e:
        log(f"  VALIDATION MODÜL HATASI: {e}")
        return

    try:
        print("DEBUG: entering try block")
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
            # TOPLULUK BILDIRIMI (Madde 29) — DJ set Discord/Telegram'a düşer.
            # FAIL-SAFE: hata olursa yayin geri alinmaz.
            _topluluk_bildir(project_dir, youtube_video_id, log)
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
            # Shorts/Reels otomatik klip kesme (hook/transition/outro)
            _create_shorts_clips(project_dir, youtube_video_id, shorts_id)
        except Exception as e:
            log(f"  YouTube Shorts HATA: {e}")

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
            from social_text import build_caption
            meta_path = os.path.join(project_dir, "meta.json")
            meta = {}
            if os.path.isfile(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            # AI beyani caption'IN ICINDE (ai_beyani=True) — ayri bir satir
            # DEGIL. Once ayri `build_ai_disclosure_line()` satiri ekleniyordu;
            # bu Instagram/FB tarafinda iki ayri beyan kaynagiydi.
            # (test_ai_beyan_satiri: "eski ayri satir geri gelmemeli")
            caption = build_caption(meta, ai_beyani=True)
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
        print("DEBUG: entering try block")
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