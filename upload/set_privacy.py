"""Bir YouTube videosunun privacyStatus'unu günceller.

Kullanım:
    python upload/set_privacy.py VIDEO_ID public
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service


def set_privacy(video_id: str, privacy: str) -> None:
    youtube = get_authenticated_service()
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": privacy}},
    ).execute()
    print(f"  {video_id} -> {privacy}")


if __name__ == "__main__":
    set_privacy(sys.argv[1], sys.argv[2])
