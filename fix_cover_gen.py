import re

with open('C:/Users/ACER/Desktop/ilk-projem/cover_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the _add_series_title_text function
old_func_start = content.find('def _add_series_title_text(')
old_func_end = content.find('\ndef _add_title_text(')

if old_func_start == -1 or old_func_end == -1:
    print('Function not found!')
    exit(1)

old_func = content[old_func_start:old_func_end]

new_func = '''def _add_series_title_text(
    bg_path: str, out_path: str, series_text: str, landmark: str,
    template: dict, out_w: int, out_h: int
) -> None:
    """Series-specific thumbnail text overlay (silhouette + landmark + logo style).
    Landmark silüeti görseli kullanır (text yerine)."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\\\", "/")

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


def _add_title_text('''

# Replace the function
new_content = content[:content.find('def _add_series_title_text(')] + new_func + content[content.find('\ndef _add_title_text('):]

with open('C:/Users/ACER/Desktop/ilk-projem/cover_generator.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Function replaced successfully')