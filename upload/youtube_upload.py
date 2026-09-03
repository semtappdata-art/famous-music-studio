"""Render edilmiş bir projeyi YouTube'a resumable upload ile yükler.

Kullanım:
    python upload/youtube_upload.py --project "projects/beni bırakma"
    python upload/youtube_upload.py --project "projects/beni bırakma" --privacy public
    python upload/youtube_upload.py --project "projects/beni bırakma" --shorts

meta.json'dan title/theme okur, output/youtube_16x9.mp4'ü yükler (upload_video),
sonucu projects/<isim>/state.json'a yazar. --shorts ile output/shorts_9x16.mp4
AYRI bir YouTube video'su (Short) olarak yüklenir (upload_short) — küçük/yeni
kanallar için Shorts akışı, uzun format önerilen videolar sisteminden çok daha
erişilebilir bir keşif kanalı olduğu için. auto_process.py ikisini de otomatik
tetikler (önce uzun format, sonra Short — Short'un açıklamasına tam versiyona
bağlantı eklemek için).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from social_text import build_caption
from youtube_auth import get_authenticated_service

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def build_snippet(meta: dict) -> dict:
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", [])
    links = config.SOCIAL_LINKS
    hashtags = " ".join(config.BRAND_HASHTAGS)

    description = (
        f"{title} | {config.STATIC_LABEL_TEXT}\n\n"
        f"Yeni şarkılar için takipte kalın 🎵\n\n"
        f"📷 Instagram: {links['instagram']}\n"
        f"🎵 TikTok: {links['tiktok']}\n"
        f"🌐 Website: {links['website']}\n\n"
        f"{hashtags}"
    )
    tags = genre_tags + [config.STATIC_LABEL_TEXT, "AI Music", "Yapay Zeka Muzik"]

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


def build_shorts_snippet(meta: dict, full_video_id: str | None = None) -> dict:
    """Shorts (shorts_9x16.mp4, 45sn highlight) için ayrı bir snippet — uzun format
    künyesi yerine TikTok/Instagram'la AYNI kısa-format caption'ı kullanıyor
    (social_text.build_caption: hook + hashtag'ler + etkileşim sorusu), çünkü
    Shorts algoritması da hashtag/hook odaklı kısa video mantığıyla çalışıyor.
    Başlığa "#Shorts" ekleniyor (YouTube'un Shorts sınıflandırması için ek sinyal —
    video zaten <=60sn ve dikey olduğu için asıl belirleyici bu değil ama önerilen
    pratik). full_video_id verilmişse, izleyiciyi kanaldaki tam versiyona
    yönlendiren bir satır ekleniyor."""
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", [])

    description = build_caption(meta)
    if full_video_id:
        description += f"\n\n🎧 Şarkının tamamı kanalımızda: https://youtu.be/{full_video_id}"

    tags = genre_tags + [config.STATIC_LABEL_TEXT, "Shorts", "AI Music", "Yapay Zeka Muzik"]

    return {
        "title": f"{title} #Shorts",
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
    }


def _upload(video_path: str, snippet: dict, privacy: str, publish_at: str | None = None) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    youtube = get_authenticated_service()

    # publish_at verilmişse (bkz. config.next_golden_publish_time): video ŞİMDİ
    # private olarak yüklenir, YouTube belirtilen zamanda OTOMATİK public'e
    # çevirir — publishAt sadece privacyStatus="private" ile birlikte kabul
    # ediliyor (resmi API kısıtı). Böylece render/upload anı (auto_process.py'nin
    # kendi kademeleme mantığı) ile videonun canlıya çıktığı an (golden-hour
    # penceresi) birbirinden ayrılıyor.
    status = {
        "selfDeclaredMadeForKids": False,
        # containsSyntheticMedia: YouTube'un "altered or synthetic content" açıklama
        # zorunluluğunun API karşılığı (Ekim 2024'te eklendi, resmi kaynak:
        # support.google.com/youtube/answer/14328491 ve developers.google.com/youtube/
        # v3/revision_history). Bu kanalın TÜM içeriği (vokal+beste+kapak+video) AI
        # üretimi olduğu için True olarak işaretleniyor — hem uzun format hem Shorts
        # (ikisi de bu _upload()'ı kullanıyor).
        "containsSyntheticMedia": True,
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = privacy

    body = {"snippet": snippet, "status": status}

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    if publish_at:
        print(f"  yükleniyor: {snippet['title']} (zamanlı: {publish_at}'te public olacak)")
    else:
        print(f"  yükleniyor: {snippet['title']} ({privacy})")
    response = None
    while response is None:
        try:
            # num_retries=3: googleapiclient'ın kendi kaynağına göre varsayılan 0
            # ("isteği sadece bir kez dener") — yani bu olmadan uzun bir upload
            # sırasındaki geçici bir ağ kesintisi/5xx hatası TÜM yüklemeyi anında
            # iptal ediyordu, bir sonraki deneme saatler sonraki bir sonraki
            # zamanlanmış çalıştırmaya kalıyordu. 3, kütüphanenin kendi exponential
            # backoff'unu (HttpError 5xx ve bağlantı hataları için) devreye sokar.
            status, response = request.next_chunk(num_retries=3)
            if status:
                print(f"    %{int(status.progress() * 100)}")
        except HttpError as e:
            print(f"  HATA: {e}")
            raise

    return response["id"]


def _find_cover(project_dir: str) -> str | None:
    for name in COVER_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def _prepare_thumbnail_jpeg(cover_path: str) -> str:
    """YouTube thumbnails.set 2MB sınırı var — procedural PNG kapaklar (bokeh
    dokusu yüzünden) bunu kolayca aşabiliyor (bir projede 2.7MB'a çıktığı
    görüldü). Kaynak boyutuna bakmadan HER ZAMAN güvenli bir JPEG'e yeniden
    kodluyoruz (PNG boyutu içerik gürültüsüne göre öngörülemez), geçici bir
    dosyaya yazıp döndürüyoruz — çağıran temizlemekten sorumlu."""
    tmp_path = cover_path + "._thumb_tmp.jpg"
    cmd = ["ffmpeg", "-y", "-i", cover_path, "-q:v", "3", tmp_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Thumbnail JPEG'e dönüştürülemedi: {result.stderr[-500:]}")
    return tmp_path


def upload_thumbnail(youtube, video_id: str, project_dir: str) -> None:
    """cover.jpg/png'yi videonun gerçek YouTube thumbnail'i olarak ayarlar.
    Bunsuz YouTube videodan rastgele bir kare seçip thumbnail yapıyordu —
    kartın başlıksız hâli (art.jpg) görünüyordu, tasarlanan başlıklı kapak
    hiç kullanılmıyordu (kullanıcı geri bildirimiyle tespit edildi)."""
    cover_path = _find_cover(project_dir)
    if not cover_path:
        print("  Thumbnail atlandı: cover.jpg/png bulunamadı")
        return

    tmp_path = _prepare_thumbnail_jpeg(cover_path)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(tmp_path, mimetype="image/jpeg"),
        ).execute()
        print("  Thumbnail: tamam")
    finally:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)


def _update_state(project_dir: str, fields: dict) -> None:
    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state.update(fields)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _compute_publish_at(privacy: str, schedule: bool) -> str | None:
    """privacy="public" ve schedule=True ise, şu an bir golden-hour penceresinin
    (config.GOLDEN_HOURS) dışındaysak bir sonraki pencerenin başlangıcını UTC
    ISO8601 ("...Z") olarak döner — içindeysek (ya da schedule kapalıysa/privacy
    public değilse) None döner, hemen (zamanlamasız) yüklenir."""
    if privacy != "public" or not schedule:
        return None
    target = config.next_golden_publish_time()
    if target is None:
        return None
    return target.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def upload_video(project_dir: str, privacy: str, schedule: bool = True) -> str:
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    meta = load_meta(project_dir)
    snippet = build_snippet(meta)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtu.be/{video_id}")

    try:
        upload_thumbnail(get_authenticated_service(), video_id, project_dir)
    except Exception as e:
        # Thumbnail başarısız olsa da video zaten yüklendi — akışı durdurmuyoruz,
        # sadece uyarıyoruz. Video YouTube'un otomatik seçtiği kareyle kalır.
        print(f"  Thumbnail HATA: {e}")

    _update_state(project_dir, {
        "youtube_video_id": video_id,
        "youtube_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_privacy": privacy,
        "youtube_publish_at": publish_at,
    })
    return video_id


def upload_short(project_dir: str, privacy: str, full_video_id: str | None = None, schedule: bool = True) -> str:
    """shorts_9x16.mp4'ü uzun formattan BAĞIMSIZ, ayrı bir YouTube video'su (Short)
    olarak yükler. full_video_id verilmişse açıklamada tam versiyona bağlantı verir."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    meta = load_meta(project_dir)
    snippet = build_shorts_snippet(meta, full_video_id)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtube.com/shorts/{video_id}")

    _update_state(project_dir, {
        "youtube_shorts_video_id": video_id,
        "youtube_shorts_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_shorts_privacy": privacy,
        "youtube_shorts_publish_at": publish_at,
    })
    return video_id


def fix_thumbnail(project_dir: str) -> None:
    """Zaten yüklenmiş bir video için thumbnail'i (yeniden) ayarlar — video
    upload_thumbnail eklenmeden ÖNCE yüklendiyse YouTube'un rastgele seçtiği
    kareyle kalmıştı, bu onu düzeltir. state.json'dan youtube_video_id okur."""
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        print(f"  HATA: {state_path} yok — bu proje hiç yüklenmemiş.")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    video_id = state.get("youtube_video_id")
    if not video_id:
        print("  HATA: state.json'da youtube_video_id yok.")
        return
    upload_thumbnail(get_authenticated_service(), video_id, project_dir)


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi YouTube'a yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument(
        "--privacy", default="private", choices=["private", "unlisted", "public"],
        help="Yükleme görünürlüğü (varsayılan: private)",
    )
    parser.add_argument(
        "--shorts", action="store_true",
        help="Uzun format yerine (veya sonrasında) shorts_9x16.mp4'ü ayrı bir YouTube Short olarak yükle",
    )
    parser.add_argument(
        "--thumbnail-only", action="store_true",
        help="Video zaten yüklüyse (state.json'da youtube_video_id varsa) sadece thumbnail'i "
             "(yeniden) ayarlar, videoyu tekrar yüklemez — geriye dönük düzeltme için.",
    )
    parser.add_argument(
        "--no-schedule", action="store_true",
        help="privacy=public olsa bile golden-hour zamanlamasını (config.GOLDEN_HOURS) "
             "devre dışı bırakıp hemen public yükler.",
    )
    args = parser.parse_args()

    if args.thumbnail_only:
        fix_thumbnail(args.project)
    elif args.shorts:
        upload_short(args.project, args.privacy, schedule=not args.no_schedule)
    else:
        upload_video(args.project, args.privacy, schedule=not args.no_schedule)


if __name__ == "__main__":
    main()
