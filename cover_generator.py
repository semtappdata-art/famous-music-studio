"""Cover Generator — Indie Flagship Basitleştirilmiş Kapak Üretici.

Eski generate_cover.py'den farklı olarak:
- Sadece eksik dosyaları üretir (var olanı dokunmaz)
- İki oran: cover.png (16:9) + cover_vertical.png (9:16) + art.jpg (1:1)
- Pexels stok fotoğrafı (aesthetic score) veya prosedürel fallback
- Basit, hızlı, deterministik
- DJ Set serileri için series-based thumbnail şablonları (Cercle/HÖR best practices)
"""

import os
import json
import hashlib
import shutil
import subprocess
import random
import config
from typing import Optional


# Series thumbnail şablonları (DJ_SERIES config'inden)
SERIES_THUMBNAIL_TEMPLATES = {
    "city_pulse": {
        "layout": "silhouette_landmark_logo",
        "silhouette_color": (255, 210, 60),  # Gold/amber accent
        "landmark_opacity": 0.85,
        "logo_position": "bottom_right",
        "text_position": "bottom_left",
        "text_format": "{brand} • Ep{episode:02d}",
        "background_style": "cinematic_rooftop",
    },
    "deep_focus": {
        "layout": "artist_nature_logo",
        "silhouette_color": (60, 220, 255),  # Cyan/turquoise
        "landmark_opacity": 0.8,
        "logo_position": "bottom_right",
        "text_position": "bottom_left",
        "text_format": "{brand} • Ep{episode:02d}",
        "background_style": "nature_immersive",
    },
    "night_drive": {
        "layout": "dashboard_silhouette_logo",
        "silhouette_color": (255, 60, 140),  # Magenta/pink
        "landmark_opacity": 0.75,
        "logo_position": "bottom_right",
        "text_position": "bottom_left",
        "text_format": "{brand} • Ep{episode:02d}",
        "background_style": "dashboard_driving",
    },
    "boiler_room_style": {
        "layout": "dj_action_crowd_logo",
        "silhouette_color": (255, 35, 35),  # Red
        "landmark_opacity": 0.7,
        "logo_position": "top_right",
        "text_position": "bottom_left",
        "text_format": "DJ Famous Live • {city}",
        "background_style": "crowd_club_raw",
    },
}


CANVAS_SIZE = 1600  # art.jpg (1:1)
COVER_SIZE_WIDE = (1600, 900)   # cover.png (16:9)
COVER_SIZE_TALL = (900, 1600)   # cover_vertical.png (9:16)


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")
    text = text.replace("%", "\\%")
    return text


def _slugify(name: str) -> str:
    tr_map = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
    ascii_name = name.translate(tr_map)
    import re
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def find_character_image(character_name: str) -> Optional[str]:
    if not character_name:
        return None
    slug = _slugify(character_name)
    characters_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")
    for ext in (".jpg", ".jpeg", ".png"):
        path = os.path.join(characters_dir, slug + ext)
        if os.path.isfile(path):
            return path
    return None


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _find_existing_art(project_dir: str) -> Optional[str]:
    for name in ("art.jpg", "art.jpeg", "art.png"):
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def _radial_background(out_path: str, accent: tuple[int, int, int]) -> None:
    """Tema accent'ten radial gradient."""
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
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Arka plan üretilemedi: {result.stderr[-1000:]}")


def _add_bokeh(bg_path: str, out_path: str, accent: tuple[int, int, int], seed: int) -> None:
    """Deterministik bokeh dokusu."""
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
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Bokeh dokusu eklenemedi: {result.stderr[-1000:]}")


def _stock_art_fetch(title: str, query: str, out_path: str) -> bool:
    """Pexels'ten stok fotoğraf indir (stock_art.py entegrasyonu)."""
    try:
        import stock_art
        return stock_art.fetch_art(title, query, out_path)
    except Exception:
        return False


def _create_procedural_bg(project_dir: str, theme: dict, title: str) -> str:
    """Prosedürel arka plan oluştur (radial gradient + bokeh)."""
    seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
    base_path = os.path.join(project_dir, "_bg_base_tmp.png")
    bg_path = os.path.join(project_dir, "_bg_tmp.png")
    _radial_background(base_path, theme["accent"])
    _add_bokeh(base_path, bg_path, theme["accent"], seed)
    return bg_path


def _generate_series_thumbnail(project_dir: str, meta: dict, bg_path: str, title: str, theme: dict, is_photo: bool) -> bool:
    """DJ Set serisi için series-based thumbnail üretir (Cercle/HÖR best practices).
    Returns True if series thumbnail was generated, False otherwise."""
    series_key = meta.get("series")
    if not series_key:
        return False

    series_config = config.DJ_SERIES.get(series_key)
    if not series_config:
        return False

    template = SERIES_THUMBNAIL_TEMPLATES.get(series_key)
    if not template:
        return False

    episode = meta.get("episode", 1)
    location = meta.get("location") or config.get_series_location(series_key)
    if not location:
        return False

    landmark = location.get("landmark", location.get("city", ""))
    city = location.get("city", "")
    brand = series_config.get("brand", "DJ Famous")
    series_logo_text = series_config.get("youtube", {}).get("hashtags", "").split()[0] if series_config.get("youtube", {}).get("hashtags") else brand

    # Series thumbnail metni - Cercle style: {Brand} • Ep{XX}
    text_format = template.get("text_format", "{brand} • Ep{episode:02d}")
    series_text = text_format.format(brand=brand, episode=episode, city=city, landmark=landmark)

    # Arka plan: art.jpg varsa onu kullan, yoksa series'e göre procedural
    has_cover = any(os.path.isfile(os.path.join(project_dir, n)) for n in ("cover.png", "cover.jpg", "cover.jpeg"))
    has_cover_vertical = any(os.path.isfile(os.path.join(project_dir, n)) for n in ("cover_vertical.png", "cover_vertical.jpg", "cover_vertical.jpeg"))

    if has_cover and has_cover_vertical:
        # Ana kapaklar zaten var — ama Variant B (A/B test) ÜRETİLMEMİŞ OLABİLİR
        # (kapaklar önceki koşuda üretilmiş, variant B sonradan eklendiyse).
        # 2026-10-19: bu yol sessizce variant B'yi atlayordu.
        _generate_series_thumbnail_variant_b(
            project_dir, meta, bg_path, template, series_text, landmark)
        return True  # Zaten var

    # Temp dosya takibi (prosedürel bg oluşturulduysa temizle)
    temp_files = []
    if bg_path.endswith("_bg_tmp.png"):
        temp_files = [
            os.path.join(project_dir, "_bg_base_tmp.png"),
            os.path.join(project_dir, "_bg_tmp.png"),
        ]
    elif bg_path.endswith("_stock_art_tmp.jpg"):
        temp_files = [bg_path]

    try:
        # 16:9 cover.png - Cercle style: Artist silhouette + Landmark + Series logo
        if not has_cover:
            cover_path = os.path.join(project_dir, "cover.png")
            _add_series_title_text(bg_path, cover_path, series_text, landmark, template,
                                   out_w=COVER_SIZE_WIDE[0], out_h=COVER_SIZE_WIDE[1])
            print(f"  cover.png (series: {series_key}) üretildi ({series_text!r})")

        # 9:16 cover_vertical.png - Same branding for Shorts/Reels
        if not has_cover_vertical:
            cover_v_path = os.path.join(project_dir, "cover_vertical.png")
            _add_series_title_text(bg_path, cover_v_path, series_text, landmark, template,
                                   out_w=COVER_SIZE_TALL[0], out_h=COVER_SIZE_TALL[1])
            print(f"  cover_vertical.png (series: {series_key}) üretildi ({series_text!r})")

        # Variant B (A/B test) — DAHA BURA'DA: bg_path geçici bir dosya
        # (prosedürel `_bg_tmp.png` / `_stock_art_tmp.jpg`) ve `finally`
        # bloğu onu SİLİYOR. Çağıran (generate()) variant B'yi DIŞARIDA
        # çağırıyordu — temp dosya çoktan silinmişti, ffmpeg "No such file
        # or directory" ile patlıyordu. 2026-10-19: 6 DJ set'in variant B
        # kapakları bu yüzden ÜRETİLEMEDİ.
        _generate_series_thumbnail_variant_b(
            project_dir, meta, bg_path, template, series_text, landmark)

        return True
    except Exception as e:
        print(f"  Series thumbnail hatası ({series_key}): {e}")
        return False
    finally:
        for tmp in temp_files:
            if os.path.isfile(tmp):
                os.remove(tmp)


def _generate_series_thumbnail_variant_b(project_dir: str, meta: dict, bg_path: str, template: dict, series_text: str, landmark: str) -> bool:
    """Variant B (A/B test) için series thumbnail - farklı renk paleti ve yerleşim.
    Sol üst logo, sağ alt başlık, accent2 rengi."""
    series_key = meta.get("series")
    if not series_key:
        return False

    has_cover_b = os.path.isfile(os.path.join(project_dir, "cover_variant_B.png"))
    has_cover_v_b = os.path.isfile(os.path.join(project_dir, "cover_vertical_variant_B.png"))
    if has_cover_b and has_cover_v_b:
        return True

    try:
        # Variant B uses accent2 color
        from config import THEMES
        theme_key = meta.get("theme", "dj")
        theme = THEMES.get(theme_key, THEMES["dj"])
        accent2 = theme.get("accent2", theme["accent"])
        accent2_hex = f"#{accent2[0]:02x}{accent2[1]:02x}{accent2[2]:02x}"

        # Override template colors for variant B
        variant_template = template.copy()
        variant_template["silhouette_color"] = accent2

        if not has_cover_b:
            cover_b_path = os.path.join(project_dir, "cover_variant_B.png")
            _add_series_title_text(bg_path, cover_b_path, series_text, landmark, variant_template,
                                   out_w=COVER_SIZE_WIDE[0], out_h=COVER_SIZE_WIDE[1])
            print(f"  cover_variant_B.png (series: {series_key}) üretildi")

        if not has_cover_v_b:
            cover_v_b_path = os.path.join(project_dir, "cover_vertical_variant_B.png")
            _add_series_title_text(bg_path, cover_v_b_path, series_text, landmark, variant_template,
                                   out_w=COVER_SIZE_TALL[0], out_h=COVER_SIZE_TALL[1])
            print(f"  cover_vertical_variant_B.png (series: {series_key}) üretildi")

        return True
    except Exception as e:
        print(f"  Series variant B thumbnail hatası ({series_key}): {e}")
        return False


def _download_landmark_silhouette(landmark: str, out_path: str) -> bool:
    """Landmark silüetini Pexels/Unsplash'ten indir veya prosedürel oluştur."""
    try:
        import requests
        # Pexels API ile landmark silüeti ara
        query = f"{landmark} silhouette black background"
        stock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"_silhouette_{hash(landmark) % 10000}.jpg")
        # Önce cache kontrolü
        if os.path.isfile(stock_path):
            shutil.copy(stock_path, out_path)
            return True
        # Stock art fetch dene
        try:
            import stock_art
            if stock_art.fetch_art(f"{landmark} silhouette", f"{landmark} silhouette black background", stock_path):
                shutil.copy(stock_path, out_path)
                return True
        except Exception:
            pass
        # Prosedürel fallback: basit geometrik silüeti oluştur
        _create_procedural_silhouette(landmark, out_path)
        if os.path.isfile(stock_path):
            shutil.copy(out_path, stock_path)
        return True
    except Exception:
        return False


def _create_procedural_silhouette(landmark: str, out_path: str) -> None:
    """Basit geometrik landmark silüeti oluştur (fallback)."""
    size = 800
    # Landmark tipine göre basit geometrik şekil
    shapes = {
        "hagia sophia": "minaret+ dome",
        "tv tower": "tower",
        "mulholland": "mountain road",
        "rice terraces": "terraced hills",
        "tv tower": "tower",
        "eiffel": "tower",
        "hagia": "dome+minaret",
    }
    # Basit: landmark adından anahtar kelime çıkar
    key = landmark.lower()
    shape_type = "building"
    for k, v in shapes.items():
        if k in key:
            shape_type = v
            break
    # Prosedürel silüeti oluştur (basit geometrik)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={size}x{size}",
        "-vf", (
            f"geq=r='if(lt(hypot(X-{size/2},Y-{size/2}),{size*0.35}),255,0)':"
            f"g='if(lt(hypot(X-{size/2},Y-{size/2}),{size*0.35}),255,0)':"
            f"b='if(lt(hypot(X-{size/2},Y-{size/2}),{size*0.35}),255,0)'"
        ),
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # En basit fallback: siyah daire
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={size}x{size}",
            "-vf", f"drawtext=text='{landmark[:20]}':fontcolor=white:fontsize=40:x=(w-tw)/2:y=(h-th)/2",
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
        subprocess.run(cmd, capture_output=True)

def _download_landmark_silhouette(landmark: str, out_path: str) -> bool:
    """Landmark silüetini indir veya oluştur."""
    # Cache kontrolü
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"_silhouette_cache_{hash(landmark) % 10000}.png")
    if os.path.isfile(cache_path):
        shutil.copy(cache_path, out_path)
        return True
    # Prosedürel oluştur
    _create_procedural_silhouette(landmark, out_path)
    if os.path.isfile(out_path):
        shutil.copy(out_path, cache_path)
        return True
    return False


def _add_series_title_text(
    bg_path: str, out_path: str, series_text: str, landmark: str,
    template: dict, out_w: int, out_h: int
) -> None:
    """Series-specific thumbnail text overlay (silhouette + landmark + logo style).
    Landmark silüeti görseli kullanır (text yerine)."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")

    basis = min(out_w, out_h)
    title_fs = int(basis * 0.08)  # Series text boyutu
    landmark_fs = int(basis * 0.045)
    label_fs = int(basis * 0.025)

    # Y pozisyonları (alt 1/3 bölgesi)
    y_center = int(out_h * 0.75)
    title_y = y_center - int(title_fs * 0.8)
    landmark_y = title_y + int(title_fs * 1.4)
    label_y = landmark_y + int(landmark_fs * 1.3)

    # BÜYÜME (madde 8): kapakta 3 eleman, 4 kelimeden az yazı — mobilde %10
    # boyutta okunmayan kapak tıklanmaz. Landmark uzunsa kısaltılır.
    landmark_kisa = " ".join(landmark.split()[:4])
    series_escaped = _escape_drawtext(series_text)
    landmark_escaped = _escape_drawtext(landmark[:40])
    logo_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)

    # Silhouette/landmark rengi
    sil_r, sil_g, sil_b = template.get("silhouette_color", (255, 210, 60))
    sil_color = f"#{sil_r:02x}{sil_g:02x}{sil_b:02x}"

    # Landmark silüeti görselini indir/oluştur
    silhouette_path = os.path.join(os.path.dirname(out_path), f"_silhouette_{hash(landmark) % 10000}.png")
    _download_landmark_silhouette(landmark, silhouette_path)
    has_silhouette = os.path.isfile(silhouette_path)

    # Silhouette/landmark rengi
    sil_r, sil_g, sil_b = template.get("silhouette_color", (255, 210, 60))
    sil_color = f"#{sil_r:02x}{sil_g:02x}{sil_b:02x}"

    # Logo varsa ekle
    if config.LOGO_PATH and os.path.isfile(config.LOGO_PATH):
        logo_h = int(basis * 0.18)
        logo_y = out_h - logo_h - int(out_h * 0.03)
        logo_x = out_w - logo_h - int(out_w * 0.03)

        if has_silhouette:
            # Silüeti ortada, üstte göster
            sil_h = int(basis * 0.35)
            sil_y = int(out_h * 0.15)
            sil_x = (out_w - sil_h) // 2
            filter_complex = (
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                f"drawtext=fontfile={rel_font_bold}:text='{_escape_drawtext(series_text)}':"
                f"fontcolor={sil_color}:fontsize={title_fs}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
                f"x=(w-text_w)/2:y={title_y}[bg];"
                f"[bg]drawtext=fontfile={rel_font}:text='{_escape_drawtext(landmark)}':"
                f"fontcolor=white@0.9:fontsize={int(basis * 0.035)}:"
                f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={title_y + int(title_fs * 1.5)}[bg2];"
                f"[2:v]scale={sil_h}:{sil_h}:force_original_aspect_ratio=decrease,format=rgba[sil];"
                f"[bg2][sil]overlay=x={sil_x}:y={sil_y}[bg3];"
                f"[bg3]drawtext=fontfile={rel_font}:text='{_escape_drawtext(config.STATIC_LABEL_TEXT)}':"
                f"fontcolor=white@0.7:fontsize={int(basis * 0.025)}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={out_h - int(out_h * 0.05)}[bg4];"
                f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
                f"eq=brightness=0.1:saturation=1.5:contrast=1.1,format=rgba[logo];"
                f"[bg4][logo]overlay=x={logo_x}:y={logo_y}[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bg_path,
                "-i", config.LOGO_PATH,
                "-i", silhouette_path,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-frames:v", "1", "-update", "1",
                out_path,
            ]
        else:
            # Silüet yoksa sadece text
            filter_complex = (
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                f"drawtext=fontfile={rel_font_bold}:text='{_escape_drawtext(series_text)}':"
                f"fontcolor={sil_color}:fontsize={title_fs}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
                f"x=(w-text_w)/2:y={title_y}[bg];"
                f"[bg]drawtext=fontfile={rel_font}:text='{_escape_drawtext(landmark)}':"
                f"fontcolor=white@0.9:fontsize={int(basis * 0.035)}:"
                f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={title_y + int(title_fs * 1.5)}[bg2];"
                f"[bg2]drawtext=fontfile={rel_font}:text='{_escape_drawtext(config.STATIC_LABEL_TEXT)}':"
                f"fontcolor=white@0.7:fontsize={int(basis * 0.025)}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={out_h - int(out_h * 0.05)}[bg3];"
                f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
                f"eq=brightness=0.1:saturation=1.5:contrast=1.1,format=rgba[logo];"
                f"[bg3][logo]overlay=x={logo_x}:y={logo_y}[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bg_path,
                "-i", config.LOGO_PATH,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-frames:v", "1", "-update", "1",
                out_path,
            ]
    else:
        if has_silhouette:
            sil_h = int(basis * 0.35)
            sil_y = int(out_h * 0.15)
            sil_x = (out_w - sil_h) // 2
            filter_complex = (
                f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                f"drawtext=fontfile={rel_font_bold}:text='{_escape_drawtext(series_text)}':"
                f"fontcolor={sil_color}:fontsize={title_fs}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
                f"x=(w-text_w)/2:y={title_y}[bg];"
                f"[bg]drawtext=fontfile={rel_font}:text='{_escape_drawtext(landmark)}':"
                f"fontcolor=white@0.9:fontsize={int(basis * 0.035)}:"
                f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={title_y + int(title_fs * 1.5)}[bg2];"
                f"[1:v]scale={sil_h}:{sil_h}:force_original_aspect_ratio=decrease,format=rgba[sil];"
                f"[bg2][sil]overlay=x={sil_x}:y={sil_y}[bg3];"
                f"[bg3]drawtext=fontfile={rel_font}:text='{_escape_drawtext(config.STATIC_LABEL_TEXT)}':"
                f"fontcolor=white@0.7:fontsize={int(basis * 0.025)}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={out_h - int(out_h * 0.05)}[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bg_path,
                "-i", silhouette_path,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-frames:v", "1", "-update", "1",
                out_path,
            ]
        else:
            # Silüet yoksa sadece text
            filter_complex = (
                f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},"
                f"drawtext=fontfile={rel_font_bold}:text='{_escape_drawtext(series_text)}':"
                f"fontcolor={sil_color}:fontsize={title_fs}:"
                f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
                f"x=(w-text_w)/2:y={title_y},"
                f"drawtext=fontfile={rel_font}:text='{_escape_drawtext(landmark)}':"
                f"fontcolor=white@0.9:fontsize={int(basis * 0.035)}:"
                f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={title_y + int(title_fs * 1.5)},"
                f"drawtext=fontfile={rel_font}:text='{_escape_drawtext(config.STATIC_LABEL_TEXT)}':"
                f"fontcolor=white@0.7:fontsize={int(basis * 0.025)}:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={out_h - int(out_h * 0.05)}"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bg_path,
                "-vf", filter_complex,
                "-frames:v", "1", "-update", "1",
                out_path,
            ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Series thumbnail yazılamadı: {result.stderr[-1000:]}")


def _add_title_text(
    bg_path: str, out_path: str, title: str, y_center_ratio: float = 0.5,
    out_w: int = CANVAS_SIZE, out_h: int = CANVAS_SIZE,
) -> None:
    """Başlık + marka yazısı ekle."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)

    basis = min(out_w, out_h)
    en_buyuk = int(basis * 0.14)
    kullanilabilir = out_w * 0.86

    # Basit sigdirma (eski _basligi_sigdir mantığı)
    title_escaped = _escape_drawtext(title)
    # Tek satır dene
    cmd_test = [
        "ffmpeg", "-v", "error", "-f", "lavfi",
        "-i", f"color=black:s=1920x140:d=0.04,drawtext=fontfile={rel_font_bold}:text='{title_escaped}':fontcolor=white:fontsize={en_buyuk}:x=10:y=30",
        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    try:
        ham = subprocess.run(cmd_test, capture_output=True, timeout=10).stdout
        # Basit genişlik ölçümü
        g, y = 1920, 140
        sag = 0
        for sat in range(y):
            u = len(ham[sat * g:(sat + 1) * g].rstrip(b'\x00'))
            if u > sag:
                sag = u
        genislik = max(1, sag - 10) / en_buyuk
    except Exception:
        genislik = len(title) * 0.5

    if kullanilabilir / genislik >= en_buyuk:
        final_title = title_escaped
        title_fs = en_buyuk
    else:
        # Küçült
        title_fs = max(1, int(kullanilabilir / genislik))
        final_title = title_escaped

    label_fs = int(basis * 0.03)
    y_center = int(out_h * y_center_ratio)
    blok_h = int(title_fs * 1.33)
    en_ust = int(out_h * 0.04)
    if y_center - blok_h // 2 < en_ust:
        y_center = en_ust + blok_h // 2

    base_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        f"drawtext=fontfile={rel_font_bold}:text='{final_title}':"
        f"fontcolor=white:fontsize={title_fs}:"
        f"shadowcolor=black@0.75:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2:y={y_center}-(text_h/2)"
    )

    if config.LOGO_PATH and os.path.isfile(config.LOGO_PATH):
        logo_h = int(basis * 0.26)
        logo_y = y_center + blok_h // 2 + int(title_fs * 0.04)
        alt_pay = int(out_h * 0.02)
        if logo_y + logo_h > out_h - alt_pay:
            logo_y = max(0, out_h - logo_h - alt_pay)

        filter_complex = (
            f"[0:v]{base_chain}[bg];"
            f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
            f"eq=brightness=0.16:saturation=1.9:contrast=1.25,"
            f"curves=r='0/0 0.5/0.7 1/1':g='0/0 0.5/0.6 1/1',format=rgba,"
            f"split=3[logo][isima_src][golge_src];"
            f"[golge_src]lutrgb=r=0:g=0:b=0,gblur=sigma={max(1, round(logo_h * 0.085))},"
            f"colorchannelmixer=aa=2,colorchannelmixer=aa=2,colorchannelmixer=aa=1.5,"
            f"colorchannelmixer=aa={0.72},format=rgba[golge];"
            f"[isima_src]gblur=sigma={max(1, round(logo_h * 0.03))},"
            f"eq=brightness=0.55:saturation=1.6,format=rgba[isima];"
            f"[bg][golge]overlay=x=(main_w-overlay_w)/2:y={logo_y}[lg1];"
            f"[lg1][isima]overlay=x=(main_w-overlay_w)/2:y={logo_y}[lg2];"
            f"[lg2][logo]overlay=x=(main_w-overlay_w)/2:y={logo_y}[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", config.LOGO_PATH,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
    else:
        filter_complex = (
            f"{base_chain},"
            f"drawtext=fontfile={rel_font}:text='{label_escaped}':"
            f"fontcolor=white@0.75:fontsize={label_fs}:"
            f"x=(w-text_w)/2:y={y_center}+{int(title_fs * 0.9)}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", filter_complex,
            "-frames:v", "1", "-update", "1",
            out_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Başlık yazılamadı: {result.stderr[-1000:]}")


def generate(project_dir: str) -> None:
    """Proje için eksik kapak/art dosyalarını üret."""
    meta = load_meta(project_dir)
    title = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    character = meta.get("character")

    # Hangi dosyalar var?
    has_cover = any(os.path.isfile(os.path.join(project_dir, n)) for n in ("cover.png", "cover.jpg", "cover.jpeg"))
    has_cover_vertical = any(os.path.isfile(os.path.join(project_dir, n)) for n in ("cover_vertical.png", "cover_vertical.jpg", "cover_vertical.jpeg"))
    has_art = any(os.path.isfile(os.path.join(project_dir, n)) for n in ("art.jpg", "art.jpeg", "art.png"))

    # Variant B (A/B test) dosyaları — ayrı kontrol (2026-10-19).
    # NEDEN AYRI: önceki erken çıkış `cover + cover_vertical + art` hepsi
    # varsa dönüyordu — ve Variant B ÜRETİLMEDİĞİ için 24 yüklenmiş videonun
    # 23'ünde A/B test kapakları eksik kaldı. Eriken çıkış artık Variant B'yi
    # de kontrol ediyor.
    var_b_yol = os.path.join(project_dir, "cover_variant_B.png")
    var_bv_yol = os.path.join(project_dir, "cover_vertical_variant_B.png")
    has_variant_b = os.path.isfile(var_b_yol) and os.path.isfile(var_bv_yol)

    if has_cover and has_cover_vertical and has_art and has_variant_b:
        return  # Hepsi var, hiçbir şey yapma

    if has_cover and has_cover_vertical and has_art and not has_variant_b:
        # Ana kapaklar + art hazır; sadece Variant B eksik → üret ve çık.
        existing_art = _find_existing_art(project_dir)
        character_image = find_character_image(character) if character else None
        bg_path = character_image or existing_art
        if bg_path and os.path.isfile(bg_path):
            _generate_variant_b_covers(bg_path, var_b_yol, var_bv_yol, title, theme, True)
            print(f"  cover_variant_B.png + cover_vertical_variant_B.png üretildi (A/B test için)")
            return

    # DJ Set series-based thumbnail kontrolü (öncelikli)
    if meta.get("series"):
        # Önce mevcut art.jpg/karakter/stok görseli bul
        character_image = find_character_image(character) if character else None
        existing_art = _find_existing_art(project_dir)
        if character_image:
            bg_path = character_image
        elif existing_art:
            bg_path = existing_art
        else:
            # Stok veya prosedürel fallback
            stock_path = os.path.join(project_dir, "_stock_art_tmp.jpg")
            stock_query = theme.get("art_query", "")
            if stock_query and _stock_art_fetch(title, stock_query, stock_path):
                bg_path = stock_path
            else:
                bg_path = _create_procedural_bg(project_dir, theme, title)

        # Series thumbnail üret
        is_photo = bool(character_image or existing_art)
        if _generate_series_thumbnail(project_dir, meta, bg_path, title, theme, is_photo):
            # art.jpg de üret (series thumbnail için)
            if not has_art and is_photo:
                art_ext = os.path.splitext(bg_path)[1] or ".jpg"
                art_path = os.path.join(project_dir, f"art{art_ext}")
                shutil.copy(bg_path, art_path)
                print(f"  art{art_ext} üretildi (series thumbnail source)")
            # NOT: Variant B artık `_generate_series_thumbnail` İÇİNDE üretiliyor
            # (geçici bg dosyası `finally`de silindiği için dışarıdan
            # çağrıldığında dosya bulunamıyordu — 2026-10-19 hatası).
            return

    # Normal (non-series) kapak üretimi
    # Kaynak görsel belirle
    character_image = find_character_image(character) if character else None
    existing_art = _find_existing_art(project_dir) if has_art else None
    cleanup_paths = []
    fetched_stock = False

    if character_image:
        bg_path = character_image
        source_label = f"karakter portresi: {character}"
    elif existing_art:
        bg_path = existing_art
        source_label = "elle sağlanan art görseli"
    else:
        # Pexels dene
        stock_path = os.path.join(project_dir, "_stock_art_tmp.jpg")
        stock_query = theme.get("art_query", "")
        if stock_query and _stock_art_fetch(title, stock_query, stock_path):
            bg_path = stock_path
            cleanup_paths = [stock_path]
            source_label = f"Pexels: {stock_query}"
            fetched_stock = True
        else:
            # Prosedürel fallback
            bg_path = _create_procedural_bg(project_dir, theme, title)
            cleanup_paths = [os.path.join(project_dir, "_bg_base_tmp.png"), os.path.join(project_dir, "_bg_tmp.png")]
            source_label = f"{theme_key} teması (prosedürel)"

    is_photo = bool(character_image or existing_art or fetched_stock)

    try:
        # art.jpg (1:1, metinsiz)
        if not has_art:
            art_ext = os.path.splitext(bg_path)[1] or ".jpg"
            art_path = os.path.join(project_dir, f"art{art_ext}")
            shutil.copy(bg_path, art_path)
            print(f"  art{art_ext} üretildi ({source_label})")

        # cover.png (16:9) — ana versiyon (A)
        if not has_cover:
            cover_path = os.path.join(project_dir, "cover.png")
            if is_photo:
                oran = 0.13 if character_image else 0.75
                _add_title_text(bg_path, cover_path, title, y_center_ratio=oran,
                                out_w=COVER_SIZE_WIDE[0], out_h=COVER_SIZE_WIDE[1])
            else:
                _add_title_text(bg_path, cover_path, title, y_center_ratio=0.5,
                                out_w=COVER_SIZE_WIDE[0], out_h=COVER_SIZE_WIDE[1])
            print(f"  cover.png üretildi ({title!r}, {source_label})")

        # cover_vertical.png (9:16) — ana versiyon (A)
        if not has_cover_vertical:
            cover_v_path = os.path.join(project_dir, "cover_vertical.png")
            if is_photo:
                oran = 0.13 if character_image else 0.75
                _add_title_text(bg_path, cover_v_path, title, y_center_ratio=oran,
                                out_w=COVER_SIZE_TALL[0], out_h=COVER_SIZE_TALL[1])
            else:
                _add_title_text(bg_path, cover_v_path, title, y_center_ratio=0.5,
                                out_w=COVER_SIZE_TALL[0], out_h=COVER_SIZE_TALL[1])
            print(f"  cover_vertical.png üretildi ({title!r}, {source_label})")

        # Test & Compare için varyant B (YouTube Studio A/B test) — sadece eksikse üretilir
        # Farklı renk paleti ve yerleşim: sol üst logo, sağ alt başlık, kontrast arka plan
        cover_b_path = os.path.join(project_dir, "cover_variant_B.png")
        cover_v_b_path = os.path.join(project_dir, "cover_vertical_variant_B.png")
        need_b = not os.path.isfile(cover_b_path) or not os.path.isfile(cover_v_b_path)
        if need_b:
            _generate_variant_b_covers(bg_path, cover_b_path, cover_v_b_path, title, theme, is_photo)
            print(f"  cover_variant_B.png + cover_vertical_variant_B.png üretildi (A/B test için)")

    finally:
        for tmp_path in cleanup_paths:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)




def _generate_variant_b_covers(bg_path: str, out_wide: str, out_tall: str, title: str, theme: dict, is_photo: bool) -> None:
    """Test & Compare (A/B test) için varyant B kapakları üretir.
    Farklar: farklı renk akenti (temanın accent2), farklı yerleşim (sol üst logo,
    sağ alt başlık), kontrast arka plan (vignette + hafif blur).
    """
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    title_escaped = _escape_drawtext(title)

    accent2 = theme.get("accent2", theme["accent"])
    accent2_hex = f"#{accent2[0]:02x}{accent2[1]:02x}{accent2[2]:02x}"

    # 16:9 varyant B
    out_w, out_h = COVER_SIZE_WIDE
    basis = min(out_w, out_h)
    title_fs = int(basis * 0.12)
    label_fs = int(basis * 0.03)
    logo_h = int(basis * 0.22)

    # Sol üst logo, sağ alt başlık
    logo_x = int(out_w * 0.04)
    logo_y = int(out_h * 0.04)
    title_x = int(out_w * 0.65)
    title_y = int(out_h * 0.85)
    label_x = int(out_w * 0.65)
    label_y = int(out_h * 0.92)

    # Arka plan: vignette + accent2 tonu
    filter_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':"
        f"fontcolor={accent2_hex}:fontsize={title_fs}:"
        f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
        f"x={title_x}:y={title_y},"
        f"drawtext=fontfile={rel_font}:text='{label_escaped}':"
        f"fontcolor=white@0.8:fontsize={label_fs}:"
        f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
        f"x={label_x}:y={label_y}"
    )
    if config.LOGO_PATH and os.path.isfile(config.LOGO_PATH):
        filter_complex = (
            f"[0:v]{filter_chain}[bg];"
            f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
            f"eq=brightness=0.1:saturation=1.5:contrast=1.1,format=rgba[logo];"
            f"[bg][logo]overlay=x={logo_x}:y={logo_y}[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", config.LOGO_PATH,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-frames:v", "1", "-update", "1",
            out_wide,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", filter_chain,
            "-frames:v", "1", "-update", "1",
            out_wide,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Variant B cover (16:9) yazılamadı: {result.stderr[-1000:]}")

    # 9:16 varyant B
    out_w, out_h = COVER_SIZE_TALL
    basis = min(out_w, out_h)
    title_fs = int(basis * 0.1)
    label_fs = int(basis * 0.025)
    logo_h = int(basis * 0.18)

    logo_x = int(out_w * 0.05)
    logo_y = int(out_h * 0.05)
    title_x = int(out_w * 0.55)
    title_y = int(out_h * 0.75)
    label_x = int(out_w * 0.55)
    label_y = int(out_h * 0.88)

    filter_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':"
        f"fontcolor={accent2_hex}:fontsize={title_fs}:"
        f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
        f"x={title_x}:y={title_y},"
        f"drawtext=fontfile={rel_font}:text='{label_escaped}':"
        f"fontcolor=white@0.8:fontsize={label_fs}:"
        f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
        f"x={label_x}:y={label_y}"
    )
    if config.LOGO_PATH and os.path.isfile(config.LOGO_PATH):
        filter_complex = (
            f"[0:v]{filter_chain}[bg];"
            f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
            f"eq=brightness=0.1:saturation=1.5:contrast=1.1,format=rgba[logo];"
            f"[bg][logo]overlay=x={logo_x}:y={logo_y}[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", config.LOGO_PATH,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-frames:v", "1", "-update", "1",
            out_tall,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", filter_chain,
            "-frames:v", "1", "-update", "1",
            out_tall,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Variant B cover (9:16) yazılamadı: {result.stderr[-1000:]}")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kapak/Art üret")
    parser.add_argument("--project", required=True, help="Proje klasörü")
    args = parser.parse_args()
    generate(args.project)