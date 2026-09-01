"""TikTok App Review icin demo video uretir — gercek ekran kaydi yerine,
entegrasyon akisini anlatan metin slaytlari + gercek yuklenen icerikten (shorts_9x16.mp4)
kisa bir kesit birlestirilerek 1080x1920 (9:16) bir mp4 olusturulur.

Kullanim:
    python upload/make_tiktok_demo_video.py
"""

import os
import subprocess
import sys

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(UPLOAD_DIR)
TMP_DIR = r"C:\Users\ACER\AppData\Local\Temp\claude\C--Users-ACER-Desktop-ilk-projem\dd91f44d-01d4-4ff6-98c4-bb0237611735\scratchpad\tiktok_demo"
FONT = os.path.relpath(r"C:\Windows\Fonts\segoeui.ttf", os.getcwd()).replace("\\", "/")
BG = "0x0a0806"
GOLD = "0xe6c17e"
REAL_CLIP = os.path.join(ROOT_DIR, "projects", "beni bırakma", "output", "shorts_9x16.mp4")
LOGO_PATH = os.path.join(UPLOAD_DIR, "assets", "famous_music_studio_logo_v2.png")
OUT_PATH = os.path.join(UPLOAD_DIR, "assets", "tiktok_review_demo.mp4")

SLIDES = [
    ("Step 1", "User logs in via TikTok Login Kit (OAuth)", 3),
    ("Step 2", "User grants permission: user.info.basic, video.upload", 3),
    ("Step 3", "App uploads the video via Content Posting API", 3),
]

SLIDES_AFTER = [
    ("Step 4", "Video is sent to the user's TikTok inbox as a draft", 3),
    ("Step 5", "User opens the TikTok app and publishes the draft", 3),
]


def esc(text: str) -> str:
    return text.replace("\\", "\\\\\\\\").replace(":", "\\:").replace("'", "\u2019")


def make_slide(index: int, title: str, subtitle: str, duration: float) -> str:
    out = os.path.join(TMP_DIR, f"slide_{index:02d}.mp4")
    title_e = esc(title)
    subtitle_e = esc(subtitle)
    vf = (
        f"drawtext=fontfile={FONT}:text='{title_e}':fontcolor={GOLD}:fontsize=72:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-60,"
        f"drawtext=fontfile={FONT}:text='{subtitle_e}':fontcolor=white@0.9:fontsize=40:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+40:line_spacing=10"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BG}:s=1080x1920:d={duration}:r=30",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def make_title_slide(duration: float = 3) -> str:
    out = os.path.join(TMP_DIR, "slide_title.mp4")
    title_e = esc("Famous Music Studio")
    subtitle_e = esc("TikTok Integration Demo")
    filter_complex = (
        f"[0:v]drawtext=fontfile={FONT}:text='{title_e}':fontcolor={GOLD}:fontsize=64:"
        f"x=(w-text_w)/2:y=1230:line_spacing=10[bg1];"
        f"[bg1]drawtext=fontfile={FONT}:text='{subtitle_e}':fontcolor=white@0.9:fontsize=38:"
        f"x=(w-text_w)/2:y=1330[bg2];"
        f"[1:v]scale=520:520[logo];"
        f"[bg2][logo]overlay=(main_w-overlay_w)/2:380"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BG}:s=1080x1920:d={duration}:r=30",
        "-i", LOGO_PATH,
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def make_clip_segment() -> str:
    out = os.path.join(TMP_DIR, "real_clip.mp4")
    caption_e = esc("Content being uploaded: \u201cBeni B\u0131rakma\u201d")
    vf = (
        f"drawtext=fontfile={FONT}:text='{caption_e}':fontcolor={GOLD}:fontsize=36:"
        f"x=(w-text_w)/2:y=100:box=1:boxcolor=black@0.5:boxborderw=14"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", REAL_CLIP,
        "-t", "6",
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    if not os.path.isfile(REAL_CLIP):
        print(f"HATA: {REAL_CLIP} bulunamadi.")
        sys.exit(1)

    print("baslik slayti olusturuluyor (logo ile)...")
    clips = [make_title_slide()]
    for i, (title, subtitle, dur) in enumerate(SLIDES, start=1):
        print(f"slayt olusturuluyor: {title}")
        clips.append(make_slide(i, title, subtitle, dur))

    print("gercek video kesiti hazirlaniyor...")
    clips.append(make_clip_segment())

    for i, (title, subtitle, dur) in enumerate(SLIDES_AFTER, start=len(SLIDES) + 1):
        print(f"slayt olusturuluyor: {title}")
        clips.append(make_slide(i, title, subtitle, dur))

    concat_list_path = os.path.join(TMP_DIR, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    print("birlestiriliyor...")
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        OUT_PATH,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"tamam: {OUT_PATH}")


if __name__ == "__main__":
    main()
