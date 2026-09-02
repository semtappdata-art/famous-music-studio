"""meta.json'daki title + theme'e göre otomatik cover.png (başlıklı, platform
thumbnail'i) ve art.png (metinsiz, video kartı + arka plan blur kaynağı) üretir.

Proje bilinçli olarak sadece ffmpeg kullanıyor (Pillow/Playwright gibi ek bir
görsel işleme bağımlılığı eklemiyor) — tema rengine göre radial gradyan arka
plan + (cover.png için) ortalanmış başlık metni.

Kullanım:
    python generate_cover.py --project "projects/sarki-adi"

Sadece EKSİK olan dosyayı üretir, var olanın üstüne yazmaz — elle hazırlanmış
özel bir cover/art varsa dokunulmaz. auto_process.py, render'dan önce bunu bir
projede cover eksikse otomatik çağırır; yani artık görselleri elle hazırlamak
zorunlu değil, sadece audio.wav + (opsiyonel) meta.json yeterli.
"""

import argparse
import json
import os
import shutil
import subprocess

import config

CANVAS_SIZE = 1600


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")
    text = text.replace("%", "\\%")
    return text


def _radial_background(out_path: str, accent: tuple[int, int, int]) -> None:
    """Tema accent renginin açık tonundan (merkez) neredeyse siyaha (kenarlar)
    radial gradyan — ffmpeg_utils.ensure_vignette ile aynı geq deseni."""
    light = tuple(c + (255 - c) * 0.55 for c in accent)
    dark = (12, 9, 16)
    size = CANVAS_SIZE

    dist = "hypot(X-W/2\\,Y-H/2)"
    maxdist = "hypot(W/2\\,H/2)"
    t = f"min(1\\,{dist}/{maxdist})"
    r_expr = f"{light[0]:.1f}+({dark[0] - light[0]:.1f})*{t}"
    g_expr = f"{light[1]:.1f}+({dark[1] - light[1]:.1f})*{t}"
    b_expr = f"{light[2]:.1f}+({dark[2] - light[2]:.1f})*{t}"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={size}x{size}",
        "-vf", f"geq=r='{r_expr}':g='{g_expr}':b='{b_expr}'",
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Arka plan üretilemedi: {result.stderr[-1000:]}")


def _add_title_text(bg_path: str, out_path: str, title: str) -> None:
    """bg_path'teki görsele başlık + sabit marka satırını ortalayarak yazar,
    out_path'e yazar (bg_path değiştirilmez)."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    title_escaped = _escape_drawtext(title)
    label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    title_fontsize = int(CANVAS_SIZE * 0.075)
    label_fontsize = int(CANVAS_SIZE * 0.03)

    filter_complex = (
        f"drawtext=fontfile={rel_font}:text='{title_escaped}':"
        f"fontcolor=white:fontsize={title_fontsize}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2,"
        f"drawtext=fontfile={rel_font}:text='{label_escaped}':"
        f"fontcolor=white@0.75:fontsize={label_fontsize}:"
        f"x=(w-text_w)/2:y=(h/2)+{int(title_fontsize * 0.9)}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-vf", filter_complex,
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Başlık yazılamadı: {result.stderr[-1000:]}")


def generate(project_dir: str) -> None:
    meta = load_meta(project_dir)
    title = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])

    cover_path = os.path.join(project_dir, "cover.png")
    art_path = os.path.join(project_dir, "art.png")
    has_cover = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("cover.jpg", "cover.jpeg", "cover.png")
    )
    has_art = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("art.jpg", "art.jpeg", "art.png")
    )
    if has_cover and has_art:
        return

    bg_path = os.path.join(project_dir, "_bg_tmp.png")
    _radial_background(bg_path, theme["accent"])
    try:
        if not has_art:
            shutil.copy(bg_path, art_path)
            print(f"  art.png üretildi ({theme_key} teması)")
        if not has_cover:
            _add_title_text(bg_path, cover_path, title)
            print(f"  cover.png üretildi ({title!r}, {theme_key} teması)")
    finally:
        if os.path.isfile(bg_path):
            os.remove(bg_path)


def main():
    parser = argparse.ArgumentParser(
        description="Bir projede eksik olan cover.png/art.png dosyalarını tema rengine göre üretir."
    )
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()
    generate(args.project)


if __name__ == "__main__":
    main()
