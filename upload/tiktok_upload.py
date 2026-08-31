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

API_BASE = "https://open.tiktokapis.com/v2"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _query_creator_info(access_token: str) -> dict:
    resp = requests.post(f"{API_BASE}/post/publish/creator_info/query/", headers=_headers(access_token))
    resp.raise_for_status()
    return resp.json()["data"]


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def upload_video(project_dir: str, privacy_level: str | None = None) -> str:
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    token = get_access_token()
    access_token = token["access_token"]

    creator_info = _query_creator_info(access_token)
    allowed_privacy = creator_info.get("privacy_level_options", [])
    if privacy_level is None:
        # Sandbox/onaysız app'lerde genelde sadece SELF_ONLY (private) mevcut.
        privacy_level = "SELF_ONLY" if "SELF_ONLY" in allowed_privacy else allowed_privacy[0]
    elif privacy_level not in allowed_privacy:
        raise ValueError(f"'{privacy_level}' bu hesap için izinli değil. İzinli: {allowed_privacy}")

    meta = _load_meta(project_dir)
    title = meta.get("title", "Untitled")

    video_size = os.path.getsize(video_path)
    init_body = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }
    resp = requests.post(
        f"{API_BASE}/post/publish/video/init/", headers=_headers(access_token), json=init_body
    )
    resp.raise_for_status()
    init_data = resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    print(f"  yükleniyor: {title} ({privacy_level})")
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
        if status == "PUBLISH_COMPLETE":
            print(f"  tamam: publish_id={publish_id}")
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
    state["tiktok_privacy"] = privacy_level
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return publish_id


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi TikTok'a yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument("--privacy", default=None, help="Örn. SELF_ONLY, PUBLIC_TO_EVERYONE (hesaba göre kısıtlı)")
    args = parser.parse_args()

    upload_video(args.project, args.privacy)


if __name__ == "__main__":
    main()
