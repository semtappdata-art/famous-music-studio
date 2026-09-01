"""Render edilmiş bir projeyi TikTok'a Content Posting API (Direct Post) ile yükler.

Kullanım:
    python upload/tiktok_upload.py --project "projects/beni bırakma"

NOT: App henüz TikTok'un audit/review sürecinden geçmediyse, video sadece
sandbox'ta tanımlı hedef kullanıcıya (target user) gönderilebilir, herkese
açık yayınlanamaz. Detay: https://developers.tiktok.com/docs/en/content-posting-api-get-started
"""

import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tiktok_auth import get_access_token
from social_text import build_caption

API_BASE = "https://open.tiktokapis.com/v2"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def upload_video(project_dir: str) -> str:
    """App'de sadece video.upload scope'u varsa (video.publish yok), TikTok'un
    "Upload to TikTok" (inbox/draft) akışı kullanılır: video kullanıcının TikTok
    gelen kutusuna taslak olarak düşer, yayınlamayı kullanıcı TikTok uygulamasından
    elle tamamlar. Doğrudan/otomatik yayın (Direct Post) video.publish scope'u
    gerektirir — app review onayı olmadan bu scope alınamıyor."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    token = get_access_token()
    access_token = token["access_token"]

    meta = _load_meta(project_dir)
    display_title = meta.get("title", "Untitled")

    video_size = os.path.getsize(video_path)
    init_body = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }
    resp = requests.post(
        f"{API_BASE}/post/publish/inbox/video/init/", headers=_headers(access_token), json=init_body
    )
    resp.raise_for_status()
    init_data = resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    print(f"  yükleniyor (taslak): {display_title}")
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        data=video_bytes,
    )
    upload_resp.raise_for_status()

    # Yayın durumunu poll et
    for _ in range(30):
        time.sleep(3)
        status_resp = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers=_headers(access_token),
            json={"publish_id": publish_id},
        )
        status_resp.raise_for_status()
        status = status_resp.json()["data"]["status"]
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            print(f"  tamam ({status}): publish_id={publish_id} — TikTok uygulamasından yayınla.")
            break
        if status == "FAILED":
            raise RuntimeError(f"TikTok yükleme başarısız: {status_resp.json()}")
    else:
        print(f"  Durum belirsiz (timeout), publish_id={publish_id} — TikTok Studio'dan kontrol et.")

    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state["tiktok_publish_id"] = publish_id
    state["tiktok_uploaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state["tiktok_privacy"] = "DRAFT_INBOX"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return publish_id


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi TikTok'a yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()

    upload_video(args.project)


if __name__ == "__main__":
    main()
