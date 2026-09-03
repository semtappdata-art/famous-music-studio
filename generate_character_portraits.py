"""karakter_roster.md'deki 10 karakter için characters/ klasörüne sabit, deterministik
portre üretir — büst siluet + baş harfleri monogramı, tema rengine göre.

Bilinçli olarak fotogerçekçi DEĞİL (bkz. karakter_roster.md "Sınır ve dürüstlük notu"
ve characters/README.md): karakterler gerçek insan sanatçı gibi sunulmamalı, ve bir
yüz üretme modelinin var olan gerçek birine benzeyen bir sonuç üretme riski de yok.
Bunun yerine generate_cover.py'nin zaten kullandığı radial gradyan + bokeh dokusuna,
düz renkli bir büst siluet + 2 harfli monogram ekleyerek her karaktere marka
logosu gibi tutarlı, tanınabilir ama insan-fotoğrafı OLMAYAN bir kimlik veriyor.
Proje geleneğine uyarak ek bir görsel kütüphane (Pillow/Playwright vb.) eklemeden
sadece ffmpeg kullanıyor.

Kullanım:
    python generate_character_portraits.py
    python generate_character_portraits.py --force   # var olanların üstüne de yazar

Sadece EKSİK karakter dosyalarını üretir (--force verilmedikçe) — elle hazırlanmış
(veya daha önce bu scriptle üretilmiş) bir portre varsa dokunulmaz.
"""

import argparse
import hashlib
import os
import subprocess

import config
from generate_cover import CANVAS_SIZE, _add_bokeh, _escape_drawtext, _radial_background

CHARACTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")

# (isim, slug, tema) — karakter_roster.md ile birebir aynı sırada/eşleşmede tutulmalı.
CHARACTERS = [
    ("ASI", "asi", "hiphop"),
    ("Nova Deniz", "nova-deniz", "hiphop"),
    ("Kerem Ateşi", "kerem-atesi", "arabesk"),
    ("Azra Yıldız", "azra-yildiz", "arabesk"),
    ("Ege Barış", "ege-baris", "pop"),
    ("Lina Su", "lina-su", "pop"),
    ("Mira Rüzgar", "mira-ruzgar", "pop"),
    ("Efe Sinyal", "efe-sinyal", "elektronik"),
    ("Elif Yağmur", "elif-yagmur", "akustik"),
    ("Kaya Demir", "kaya-demir", "rock"),
]


def _initials(name: str) -> str:
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper()


def _draw_silhouette(bg_path: str, out_path: str, accent: tuple[int, int, int]) -> None:
    """bg_path'in üstüne, ekranın altına doğru taşan basit bir baş+omuz büst siluet
    çizer (klasik "varsayılan kullanıcı" ikonu geometrisi) — accent'in çok açık
    (neredeyse beyaz) bir tonunda düz renk, keskin kenar (flat-icon stili, fotoğraf
    değil bunun bilinçli görsel kanıtı)."""
    size = CANVAS_SIZE
    silhouette = tuple(c + (255 - c) * 0.85 for c in accent)

    head_cx, head_cy, head_r = size * 0.5, size * 0.40, size * 0.15
    sh_cx, sh_cy, sh_rx, sh_ry = size * 0.5, size * 0.92, size * 0.34, size * 0.42

    head_mask = f"lte(hypot(X-{head_cx:.1f}\\,Y-{head_cy:.1f})\\,{head_r:.1f})"
    shoulder_mask = (
        f"lte(pow((X-{sh_cx:.1f})/{sh_rx:.1f}\\,2)+pow((Y-{sh_cy:.1f})/{sh_ry:.1f}\\,2)\\,1)"
    )
    mask = f"max({head_mask}\\,{shoulder_mask})"

    def _channel_expr(source: str, idx: int) -> str:
        return f"if({mask}\\,{silhouette[idx]:.1f}\\,{source}(X,Y))"

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-vf", f"geq=r='{_channel_expr('r', 0)}':g='{_channel_expr('g', 1)}':b='{_channel_expr('b', 2)}'",
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Siluet çizilemedi: {result.stderr[-1000:]}")


def _draw_monogram(bg_path: str, out_path: str, initials: str, accent: tuple[int, int, int]) -> None:
    """Baş dairesinin ortasına, siluetle kontrast oluşturan koyu bir tonda 2 harfli
    monogram yazar — insan yüzü değil, marka/logo tarzı bir kimlik işareti."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    dark = tuple(c * 0.35 for c in accent)
    fontcolor = f"0x{int(dark[0]):02x}{int(dark[1]):02x}{int(dark[2]):02x}"
    fontsize = int(CANVAS_SIZE * 0.11)
    head_cy = int(CANVAS_SIZE * 0.40)

    filter_complex = (
        f"drawtext=fontfile={rel_font}:text='{_escape_drawtext(initials)}':"
        f"fontcolor={fontcolor}:fontsize={fontsize}:"
        f"x=(w-text_w)/2:y={head_cy}-(text_h/2)"
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
        raise RuntimeError(f"Monogram yazılamadı: {result.stderr[-1000:]}")


def generate_one(name: str, slug: str, theme_key: str, force: bool) -> str:
    out_path = os.path.join(CHARACTERS_DIR, f"{slug}.jpg")
    if os.path.isfile(out_path) and not force:
        return f"  atlandı (zaten var): {slug}.jpg"

    theme = config.THEMES[theme_key]
    accent = theme["accent"]
    seed = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)

    base_path = os.path.join(CHARACTERS_DIR, f"_tmp_base_{slug}.png")
    bg_path = os.path.join(CHARACTERS_DIR, f"_tmp_bg_{slug}.png")
    sil_path = os.path.join(CHARACTERS_DIR, f"_tmp_sil_{slug}.png")
    try:
        _radial_background(base_path, accent)
        _add_bokeh(base_path, bg_path, accent, seed)
        _draw_silhouette(bg_path, sil_path, accent)
        _draw_monogram(sil_path, out_path, _initials(name), accent)
    finally:
        for p in (base_path, bg_path, sil_path):
            if os.path.isfile(p):
                os.remove(p)
    return f"  üretildi: {slug}.jpg ({name}, {theme_key} teması)"


def main():
    parser = argparse.ArgumentParser(
        description="karakter_roster.md'deki 10 karakter için characters/ klasörüne portre üretir."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Var olan portrelerin üstüne de yazar (varsayılan: sadece eksik olanları üretir)",
    )
    args = parser.parse_args()

    os.makedirs(CHARACTERS_DIR, exist_ok=True)
    for name, slug, theme_key in CHARACTERS:
        print(generate_one(name, slug, theme_key, args.force))


if __name__ == "__main__":
    main()
