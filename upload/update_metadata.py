"""Zaten yüklenmiş bir YouTube videosunun title/description/tags bilgisini
güncel meta.json + config.SOCIAL_LINKS şablonuna göre yeniden yazar.

Kullanım:
    python upload/update_metadata.py VIDEO_ID "projects/proje-adi"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service
from youtube_upload import load_meta, build_snippet


def update_metadata(video_id: str, project_dir: str) -> None:
    meta = load_meta(project_dir)
    snippet = build_snippet(meta)

    youtube = get_authenticated_service()
    current = youtube.videos().list(part="snippet", id=video_id).execute()
    full_snippet = current["items"][0]["snippet"]
    full_snippet.update(snippet)

    youtube.videos().update(
        part="snippet", body={"id": video_id, "snippet": full_snippet}
    ).execute()
    print(f"  {video_id} guncellendi: {snippet['title']}")


if __name__ == "__main__":
    update_metadata(sys.argv[1], sys.argv[2])
