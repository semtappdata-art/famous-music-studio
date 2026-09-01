"""Render edilmiş bir projeyi YouTube'a resumable upload ile yükler.

Kullanım:
    python upload/youtube_upload.py --project "projects/beni bırakma"
    python upload/youtube_upload.py --project "projects/beni bırakma" --privacy public

meta.json'dan title/theme okur, output/youtube_16x9.mp4'ü yükler, sonucu
projects/<isim>/state.json'a yazar.
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


def upload_video(project_dir: str, privacy: str) -> str:
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    meta = load_meta(project_dir)
    snippet = build_snippet(meta)

    youtube = get_authenticated_service()

    body = {
        "snippet": snippet,
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
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

    video_id = response["id"]
    print(f"  tamam: https://youtu.be/{video_id}")

    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state["youtube_video_id"] = video_id
    state["youtube_uploaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["youtube_privacy"] = privacy
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return video_id


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi YouTube'a yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument(
        "--privacy", default="private", choices=["private", "unlisted", "public"],
        help="Yükleme görünürlüğü (varsayılan: private)",
    )
    args = parser.parse_args()

    upload_video(args.project, args.privacy)


if __name__ == "__main__":
    main()
