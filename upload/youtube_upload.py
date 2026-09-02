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
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from social_text import build_caption
from youtube_auth import get_authenticated_service


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


def _upload(video_path: str, snippet: dict, privacy: str) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    youtube = get_authenticated_service()

    body = {
        "snippet": snippet,
        # containsSyntheticMedia: YouTube'un "altered or synthetic content" açıklama
        # zorunluluğunun API karşılığı (Ekim 2024'te eklendi, resmi kaynak:
        # support.google.com/youtube/answer/14328491 ve developers.google.com/youtube/
        # v3/revision_history). Bu kanalın TÜM içeriği (vokal+beste+kapak+video) AI
        # üretimi olduğu için True olarak işaretleniyor — hem uzun format hem Shorts
        # (ikisi de bu _upload()'ı kullanıyor).
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"  yükleniyor: {snippet['title']} ({privacy})")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"    %{int(status.progress() * 100)}")
        except HttpError as e:
            print(f"  HATA: {e}")
            raise

    return response["id"]


def _update_state(project_dir: str, fields: dict) -> None:
    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state.update(fields)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def upload_video(project_dir: str, privacy: str) -> str:
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    meta = load_meta(project_dir)
    snippet = build_snippet(meta)

    video_id = _upload(video_path, snippet, privacy)
    print(f"  tamam: https://youtu.be/{video_id}")

    _update_state(project_dir, {
        "youtube_video_id": video_id,
        "youtube_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_privacy": privacy,
    })
    return video_id


def upload_short(project_dir: str, privacy: str, full_video_id: str | None = None) -> str:
    """shorts_9x16.mp4'ü uzun formattan BAĞIMSIZ, ayrı bir YouTube video'su (Short)
    olarak yükler. full_video_id verilmişse açıklamada tam versiyona bağlantı verir."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    meta = load_meta(project_dir)
    snippet = build_shorts_snippet(meta, full_video_id)

    video_id = _upload(video_path, snippet, privacy)
    print(f"  tamam: https://youtube.com/shorts/{video_id}")

    _update_state(project_dir, {
        "youtube_shorts_video_id": video_id,
        "youtube_shorts_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_shorts_privacy": privacy,
    })
    return video_id


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
    args = parser.parse_args()

    if args.shorts:
        upload_short(args.project, args.privacy)
    else:
        upload_video(args.project, args.privacy)


if __name__ == "__main__":
    main()
