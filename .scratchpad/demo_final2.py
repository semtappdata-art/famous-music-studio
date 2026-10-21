"""Final demo 2: Canva sahnesi (Rooftop DJ in Paris) + hareket + HUD."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("upload"))

import dj_hud
import config

OUT = ".scratchpad/demo"
os.makedirs(OUT, exist_ok=True)
SAHNE = "C:/Users/ACER/Downloads/Gemini_Generated_Image_1aypvt1aypvt1ayp.jpg"
W, H, DUR = 1280, 720, 25.0
N = int(DUR * 30)

rel_font = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
hud = dj_hud.ensure_hud(W, H)

ses = os.path.join(OUT, "demo_audio.wav")
if not os.path.isfile(ses):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", "120", "-i", "dj_sets/Deep-Medusa/audio.wav",
                    "-t", str(DUR), "-c", "copy", ses], check=True)

fc = ";".join([
    "[1:v]fps=30,scale=%d:%d:force_original_aspect_ratio=increase,"
    "crop=%d:%d,zoompan=z='1+0.05*on/%d':d=%d:s=%dx%d:fps=30[base]"
    % (W, H, W, H, N, N, W, H),
    "[0:a]showspectrum=s=%dx48:slide=1:mode=separate:color=rainbow:"
    "scale=log:fps=30,format=yuv420p[spec]" % W,
    "[base][spec]overlay=0:%d[sp]" % (H - 48),
    "[sp]format=gbrp[sp_rgb]",
    "[2:v]scale=%d:%d,format=gbrp[hud_rgb]" % (W, H),
    "[sp_rgb][hud_rgb]blend=all_mode=screen,format=yuv420p[hudded]",
    "[hudded]drawbox=x=60:y=%d:w=%d:h=5:color=0x555555:t=fill,"
    "drawbox=x=60:y=%d:w='%d*t/%.3f':h=5:color=white:t=fill,"
    "drawtext=fontfile=%s:text='Deep Medusa  •  Eiffel Nights':"
    "fontcolor=white@0.9:fontsize=30:x=60:y=%d,"
    "drawtext=fontfile=%s:text='VOL.1':fontcolor=0x33CCFF:fontsize=30:"
    "x=%d:y=%d[vfinal]" % (H - 21, W - 120, H - 21, W - 120, DUR,
                           rel_font, H - 88, rel_font, W - 180, H - 88),
])
r = subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
     "-i", ses, "-loop", "1", "-i", SAHNE, "-loop", "1", "-i", hud,
     "-filter_complex", fc,
     "-map", "[vfinal]", "-map", "0:a", "-t", "%.3f" % DUR,
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
     os.path.join(OUT, "final_demo3.mp4")],
    capture_output=True, text=True)
print("RC:", r.returncode)
print((r.stderr or "")[-400:])
assert r.returncode == 0
print("DEMO2 OK")
