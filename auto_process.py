"""Bekleyen (audio.wav hazır) projeleri otomatik render edip YouTube/TikTok/
Instagram'a yükler — Windows Görev Zamanlayıcı ile periyodik çalıştırılmak
üzere tasarlandı.

Suno'da şarkı üretimi ve indirme hâlâ elle yapılmalı (bkz. suno_prompt_hazirlik.md)
— bu script "audio.wav bir proje klasörüne konduktan sonraki her şeyi"
(cover/art üretimi + render + YouTube + TikTok + Instagram) otomatikleştiriyor.
cover.jpg/png veya art.jpg/png elle hazırlanmışsa dokunulmaz; eksikse
generate_cover.py ile meta.json'daki title/theme'e göre otomatik üretilir.

Kullanım:
    python auto_process.py
    python auto_process.py --privacy unlisted
    python auto_process.py --base projects
    python auto_process.py --count 3

Her çalıştırmada en fazla `--count` kadar proje işlenir (varsayılan: 1, henüz
3 platforma da tam yüklenmemiş olanlardan en eskiden başlayarak) — kademeli
paylaşım için: aynı anda birden fazla şarkı paylaşmak aynı takipçi kitlesinin
aynı taramasında birbiriyle yarışabiliyor. Günde birden fazla şarkı istiyorsan
Görev Zamanlayıcı'da GÜNDE BİRDEN FAZLA AYRI tetikleyici kullan (ör. 13:00 ve
19:00), tek tetikleyicide `--count`'u yükseltmek yerine. (Bu değer bir ara
kullanıcı isteğiyle 2'ye çıkarılmış, sonra aynı rekabet riski gerekçesiyle
tekrar 1'e döndürülmüştü — bkz. git geçmişi.)

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

# Windows'ta konsol/log çıktısı varsayılan olarak yerel kod sayfasına (örn.
# cp1252/charmap) düşüyor — bu ne Türkçe karakterleri doğru basabiliyor (loglar
# "Ba�ka bir" gibi bozuk görünüyordu) ne de caption'lardaki emoji'yi (örn. 🎵)
# hiç temsil edemiyor, ikincisi UnicodeEncodeError ile print() çağrısını
# patlatıp upload'ı (henüz gerçek yükleme başlamadan) tamamen durduruyordu —
# bkz. tiktok_upload.py'deki caption print'i. UTF-8'e zorlamak ikisini de çözer.
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
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_process.log")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auto_process.lock")
LOCK_STALE_SECONDS = 2 * 60 * 60  # 2 saat — normal bir render+upload'dan çok daha uzun


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _acquire_lock() -> bool:
    """İki auto_process.py çalıştırması aynı anda çakışırsa (örn. çakışan Görev
    Zamanlayıcı tetikleyicileri, ya da elle + zamanlanmış çalıştırma çakışması) ikisi
    de AYNI en eski projeyi seçip aynı videoyu iki kez yükleyebilir — bu basit dosya
    kilidi ikinci çalıştırmayı erken çıkışa yönlendirir. Kilit dosyası LOCK_STALE_SECONDS'
    tan eskiyse (önceki çalıştırma çökmüş/kilidini bırakmamış olabilir) yok sayılır."""
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


def find_ready_projects(base: str) -> list:
    """audio'su hazır olan tüm proje klasörlerini, klasörün oluşturulma zamanına
    göre (en eskiden en yeniye) sıralı döner (zaten tamamen işlenmiş olanlar
    dahil — process_project zaten-yapılmış adımları atlar, bu yüzden burada
    filtrelemeye gerek yok). cover/art artık aranmıyor — eksikse process_project
    render'dan önce otomatik üretir.

    NOT: Önceden burada `sorted(os.listdir(base))` (isim alfabetik sırası)
    kullanılıyordu ve docstring/main() "en eski bekleyen proje" işlendiğini
    iddia ediyordu — ama alfabetik sıra oluşturulma zamanıyla ilgisiz, adı
    alfabetik önde olan YENİ bir proje gerçekten daha uzun süredir bekleyen
    bir projenin önüne geçebiliyordu. os.path.getctime ile gerçek klasör
    oluşturulma zamanına göre sıralanıyor (isim, eşit zaman durumunda
    determinizm için ikincil anahtar)."""
    ready = []
    if not os.path.isdir(base):
        return ready
    for name in os.listdir(base):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if _has_any(project_dir, AUDIO_NAMES):
            ready.append(project_dir)
    ready.sort(key=lambda p: (os.path.getctime(p), p))
    return ready


def _is_fully_done(project_dir: str) -> bool:
    """Tüm platformlara (YouTube uzun format + Shorts, TikTok, Instagram) yüklenmişse
    True — bu proje için yapılacak bir şey kalmadı. Daha önce yüklenmiş ama
    youtube_shorts_video_id'si olmayan projeler (bu alan sonradan eklendi) bu
    kontrolden geçemez, yani bir sonraki çalıştırmada otomatik olarak Shorts
    yüklemesi de yapılır (retroaktif tamamlama)."""
    state = _load_state(project_dir)
    return all(
        key in state
        for key in (
            "youtube_video_id",
            "youtube_shorts_video_id",
            "tiktok_publish_id",
            "instagram_media_id",
        )
    )


def process_project(project_dir: str, privacy: str) -> None:
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
                log(f"  render başarısız, bu proje atlanıyor: {project_dir}")
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
            youtube_video_id = yt_upload(project_dir, privacy)
            log(f"  YouTube: tamam, https://youtu.be/{youtube_video_id}")
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    # Tema/tarz playlist'i: video yüklüyse (yeni veya daha önceden), kendi temasının
    # playlist'ine ekler — state.json'da youtube_playlist_id zaten varsa atlar (idempotent),
    # yani daha önce yüklenmiş şarkılar için de retroaktif çalışır.
    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    # YouTube Shorts: zaten render edilen shorts_9x16.mp4'ü AYRICA (uzun formattan
    # bağımsız) bir YouTube Short olarak yükler — küçük/yeni kanallar için Shorts
    # akışı, uzun format önerilen videolar sisteminden çok daha erişilebilir bir
    # keşif kanalı. Uzun format zaten yüklüyse (youtube_video_id var) ona bağlantı
    # veriyor. Önce uzun format yüklenmiş olmalı (linklemek için video id gerekli).
    if "youtube_shorts_video_id" in state:
        log("  YouTube Shorts: zaten yüklü, atlanıyor")
    elif not youtube_video_id:
        log("  YouTube Shorts atlandı: önce uzun format yüklenmeli")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_short as yt_upload_short
            shorts_id = yt_upload_short(project_dir, privacy, youtube_video_id)
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
        description="Bekleyen (audio hazır) projeleri otomatik render edip yükler."
    )
    parser.add_argument(
        "--privacy", default="public", choices=["private", "unlisted", "public"],
        help="Yeni YouTube yüklemeleri için görünürlük (varsayılan: public)",
    )
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    parser.add_argument(
        "--count", type=int, default=1,
        help=(
            "Bu koşuda işlenecek en fazla proje sayısı (varsayılan: 1). NOT: bir ara "
            "kullanıcı isteğiyle 2'ye yükseltilmişti, sonra 'aynı anda birden fazla şarkı "
            "paylaşmak aynı takipçi kitlesinin dikkatinde birbiriyle yarışır' gerekçesiyle "
            "tekrar 1'e (ve günde 2 AYRI Görev Zamanlayıcı tetikleyicisine, ör. 13:00/19:00) "
            "döndürüldü — kademeli paylaşım. Daha yüksek bir hacim istiyorsan --count N ile "
            "geçici olarak artırabilirsin, ama varsayılan davranış artık kademeli."
        ),
    )
    args = parser.parse_args()

    if not _acquire_lock():
        log("Başka bir auto_process.py çalışması zaten sürüyor (kilit dosyası var) — "
            "bu çalıştırma atlanıyor, çakışan yükleme riski önlendi.")
        return

    try:
        ready = find_ready_projects(args.base)
        if not ready:
            log("İşlenecek proje yok (audio hazır olan bulunamadı).")
            return

        pending = [p for p in ready if not _is_fully_done(p)]
        if not pending:
            log("Tüm hazır projeler zaten 3 platforma da yüklenmiş, yapılacak bir şey yok.")
            return

        batch = pending[:args.count]
        log(f"{len(pending)} bekleyen proje var, bu koşuda işlenecek ({len(batch)}): "
            f"{', '.join(os.path.basename(p) for p in batch)}")
        for project_dir in batch:
            process_project(project_dir, args.privacy)

        log("Çalıştırma tamamlandı.")
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
