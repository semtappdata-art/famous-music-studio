"""Video renderer utilities - stub for Telegram upload"""

import subprocess
import json

def get_audio_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("streams"):
                return float(data["streams"][0].get("duration", 0))
    except Exception:
        pass
    return 0.0


def get_video_dimensions(video_path: str) -> tuple:
    """Get video width and height using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("streams"):
                stream = data["streams"][0]
                return int(stream.get("width", 0)), int(stream.get("height", 0))
    except Exception:
        pass
    return (0, 0)


def get_video_aspect_ratio(video_path: str) -> float:
    """Get video aspect ratio"""
    w, h = get_video_dimensions(video_path)
    if w > 0 and h > 0:
        return w / h
    return 16/9
