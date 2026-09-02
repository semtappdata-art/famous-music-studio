"""meta.json'daki title + theme'e göre otomatik cover.png (başlıklı, platform
thumbnail'i) ve art.png (metinsiz, video kartı + arka plan blur kaynağı) üretir.

Proje bilinçli olarak sadece ffmpeg kullanıyor (Pillow/Playwright gibi ek bir
görsel işleme bağımlılığı eklemiyor) — tema rengine göre radial gradyan arka
plan + şarkı başlığından türetilen deterministik bokeh dokusu + (cover.png
için) ortalanmış başlık metni.

Kullanım:
    python generate_cover.py --project "projects/sarki-adi"

Sadece EKSİK olan dosyayı üretir, var olanın üstüne yazmaz — elle hazırlanmış
özel bir cover/art varsa dokunulmaz. auto_process.py, render'dan önce bunu bir
projede cover eksikse otomatik çağırır; yani artık görselleri elle hazırlamak
zorunlu değil, sadece audio.wav + (opsiyonel) meta.json yeterli.
"""

import argparse
import hashlib
import json
import os
import random
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


def _add_bokeh(bg_path: str, out_path: str, accent: tuple[int, int, int], seed: int) -> None:
    """Düz radyal arka planın üstüne, şarkı başlığından türetilen SEED ile
    deterministik (her şarkı farklı ama tekrar üretilince aynı) birkaç yumuşak
    ışık lekesi (bokeh) ekler.

    Bunsuz art.png tamamen düz bir gradyandı: video render'da kart (ön plan) ve
    arka plan (o gradyanın bulanıklaştırılmış hâli) neredeyse ayırt edilemiyordu
    — kartın içi de boş kalıyordu. Bokeh dokusu hem art.png'ye (kart + backdrop
    kaynağı) hem cover.png'ye gerçek bir doku/derinlik katıyor, ffmpeg_utils.
    ensure_vignette()'teki bokeh formülüyle aynı yaklaşımı kullanıyor."""
    rng = random.Random(seed)
    size = CANVAS_SIZE
    light = tuple(c + (255 - c) * 0.55 for c in accent)
    white = (255, 255, 255)

    blobs = []
    for _ in range(rng.randint(5, 8)):
        cx = rng.uniform(0.12, 0.88) * size
        cy = rng.uniform(0.12, 0.88) * size
        sigma = rng.uniform(0.05, 0.14) * size
        peak = rng.uniform(30, 70)
        color = white if rng.random() < 0.35 else light
        blobs.append((cx, cy, sigma, peak, color))

    def _channel_expr(source: str, idx: int) -> str:
        terms = [f"{source}(X,Y)"]
        for cx, cy, sigma, peak, color in blobs:
            dist = f"hypot(X-{cx:.1f}\\,Y-{cy:.1f})"
            falloff = f"exp(-pow({dist}/{sigma:.1f}\\,2))"
            terms.append(f"{peak * color[idx] / 255:.3f}*{falloff}")
        return "clip(" + "+".join(terms) + "\\,0\\,255)"

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-vf", f"geq=r='{_channel_expr('r', 0)}':g='{_channel_expr('g', 1)}':b='{_channel_expr('b', 2)}'",
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Bokeh dokusu eklenemedi: {result.stderr[-1000:]}")


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

    seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
    base_path = os.path.join(project_dir, "_bg_base_tmp.png")
    bg_path = os.path.join(project_dir, "_bg_tmp.png")
    _radial_background(base_path, theme["accent"])
    _add_bokeh(base_path, bg_path, theme["accent"], seed)
    try:
        if not has_art:
            shutil.copy(bg_path, art_path)
            print(f"  art.png üretildi ({theme_key} teması)")
        if not has_cover:
            _add_title_text(bg_path, cover_path, title)
            print(f"  cover.png üretildi ({title!r}, {theme_key} teması)")
    finally:
        for tmp_path in (base_path, bg_path):
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Bir projede eksik olan cover.png/art.png dosyalarını tema rengine göre üretir."
    )
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()
    generate(args.project)


if __name__ == "__main__":
    main()
