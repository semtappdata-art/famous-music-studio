"""Bir YouTube videosunu kalıcı olarak siler.

Kullanım:
    python upload/delete_video.py VIDEO_ID
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service


def delete_video(video_id: str) -> None:
    youtube = get_authenticated_service()
    youtube.videos().delete(id=video_id).execute()
    print(f"  {video_id} silindi")


if __name__ == "__main__":
    delete_video(sys.argv[1])
