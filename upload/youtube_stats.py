"""Yüklenmiş bir projenin YouTube istatistiklerini (görüntülenme, beğeni) çeker.

Kullanım:
    python upload/youtube_stats.py --project "projects/beni bırakma"

projects/<isim>/state.json'daki youtube_video_id'yi kullanır, sonucu aynı
dosyaya (views/likes/last_checked) yazar.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_auth import get_authenticated_service


def get_stats(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        raise FileNotFoundError(f"{state_path} bulunamadı — önce upload/youtube_upload.py ile yükle.")

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    if not video_id:
        raise ValueError(f"{state_path} içinde youtube_video_id yok.")

    youtube = get_authenticated_service()
    response = youtube.videos().list(part="statistics,status", id=video_id).execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Video bulunamadı: {video_id}")

    stats = items[0]["statistics"]
    status = items[0]["status"]

    state["youtube_views"] = int(stats.get("viewCount", 0))
    state["youtube_likes"] = int(stats.get("likeCount", 0))
    state["youtube_comments"] = int(stats.get("commentCount", 0))
    state["youtube_privacy"] = status.get("privacyStatus", state.get("youtube_privacy"))
    state["youtube_stats_checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return state


def main():
    parser = argparse.ArgumentParser(description="YouTube video istatistiklerini çeker.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()

    state = get_stats(args.project)
    print(f"  görüntülenme: {state['youtube_views']}")
    print(f"  beğeni: {state['youtube_likes']}")
    print(f"  yorum: {state['youtube_comments']}")
    print(f"  görünürlük: {state['youtube_privacy']}")


if __name__ == "__main__":
    main()
