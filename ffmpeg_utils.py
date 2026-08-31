"""ffprobe/ffmpeg ile süre okuma ve kart tasarımı video render fonksiyonları.

Tasarım: organik bokeh lekeli siyah zemin üzerinde, ekranın büyük kısmını kaplayan
yuvarlak köşeli bir albüm kartı + etrafında iki renk arasında SABİT (dönmeyen) neon
parlama çerçevesi + kartın 4 kenarında gerçek ses frekans verisinden üretilen sese
tepki veren çubuklar + kartın altında kayan künye yazısı + sabit "Famous Music
Studio" marka satırı + en altta bir ilerleme çubuğu. Sadece kart alanı işlenir,
kenarlar düz siyah kalır.
"""

import os
import subprocess

import config


def get_audio_duration(audio_path: str) -> float:
    """ffprobe ile ses dosyasının süresini (saniye) döndürür."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe süre okuyamadı: {result.stderr.strip()}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"ffprobe geçersiz süre döndürdü: {result.stdout!r}")


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")  # tipografik kesme işareti — filtre sözdizimini bozmasın
    text = text.replace("%", "\\%")
    return text


def get_theme_key(theme: str | None) -> str:
    return theme if theme in config.THEMES else config.DEFAULT_THEME


def ensure_card_mask() -> str:
    """Kart için yuvarlak köşe maskesini (luma tabanlı, alphamerge ile kullanılır)
    üretir (yoksa). Tema fark etmeksizin tek bir maske yeterli."""
    mask_path = config.CARD_MASK_ASSET_PATH
    size = config.CARD_ASSET_REF_SIZE

    if not os.path.isfile(mask_path):
        os.makedirs(os.path.dirname(mask_path) or ".", exist_ok=True)
        radius = int(size * config.CARD_CORNER_RATIO)
        half = size / 2
        inner = half - radius
        shape = (
            f"255*(1-clip((hypot(max(abs(X-{half})-{inner}\\,0)\\,"
            f"max(abs(Y-{half})-{inner}\\,0))-{radius})*2\\,0\\,1))"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={size}x{size}",
            "-vf", f"geq=r='{shape}':g='{shape}':b='{shape}'",
            "-frames:v", "1", "-update", "1",
            mask_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Kart maskesi üretilemedi: {result.stderr[-1000:]}")

    return mask_path


def _tonal_pair(rgb: tuple[int, int, int]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Tek bir renkten (accent) AÇIK ve KOYU tonlarını üretir — kutu çevresindeki
    gradyanın iki farklı/zıt renk (accent/accent2) yerine TEK rengin ton farkıyla
    (aynı renk ailesi, açık<->koyu) geçiş yapması için. TONE_LIGHT_MIX beyaza,
    TONE_DARK_MIX siyaha ne kadar yaklaşıldığını belirler."""
    r, g, b = rgb
    lm, dm = config.CARD_TONE_LIGHT_MIX, config.CARD_TONE_DARK_MIX
    light = tuple(c + (255 - c) * lm for c in (r, g, b))
    dark = tuple(c * (1 - dm) for c in (r, g, b))
    return light, dark


def ensure_card_glow(theme_key: str) -> str:
    """Referans görseldeki gibi İKİ AYRI köşe ışık kaynağı: üst-sol köşede turquoise/cyan,
    alt-sağ köşede magenta — her biri kendi Gauss yayılımına sahip, additif karışıyor.
    Bu, tek merkezi blob + diagonal renk gradyanından FARKLI: köşelerde net, saturated
    renk yoğunlaşması yaratır (referans görselde görülen distinct iki renkli köşe efekti)."""
    glow_path = os.path.join(config.CARD_GLOW_ASSET_DIR, f"card_glow_{theme_key}.png")
    if os.path.isfile(glow_path):
        return glow_path

    os.makedirs(os.path.dirname(glow_path) or ".", exist_ok=True)
    size = config.CARD_ASSET_REF_SIZE
    sigma = size * 0.42  # Geniş yayılım, köşeden köşeye kapsasın

    # İki ışık kaynağı: üst-sol (turquoise), alt-sağ (magenta)
    cx1, cy1 = size * 0.22, size * 0.22  # Üst-sol
    cx2, cy2 = size * 0.78, size * 0.78  # Alt-sağ
    d1 = f"hypot(X-{cx1:.1f}\\,Y-{cy1:.1f})"
    d2 = f"hypot(X-{cx2:.1f}\\,Y-{cy2:.1f})"
    a1 = f"exp(-pow({d1}/{sigma:.2f}\\,2))"
    a2 = f"exp(-pow({d2}/{sigma:.2f}\\,2))"

    r_turq, g_turq, b_turq = 0, 220, 255       # Bright cyan
    r_mag, g_mag, b_mag = 255, 60, 200         # Bright magenta

    total = f"({a1}+{a2})"
    r_expr = f"255*(({r_turq:.1f}*{a1}+{r_mag:.1f}*{a2})/max({total}\\,0.0001)/255)*min(1\\,{total})"
    g_expr = f"255*(({g_turq:.1f}*{a1}+{g_mag:.1f}*{a2})/max({total}\\,0.0001)/255)*min(1\\,{total})"
    b_expr = f"255*(({b_turq:.1f}*{a1}+{b_mag:.1f}*{a2})/max({total}\\,0.0001)/255)*min(1\\,{total})"
    a_expr = f"255*min(1\\,{total})"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black@0.0:s={size}x{size}",
        "-vf", f"format=rgba,geq=r='{r_expr}':g='{g_expr}':b='{b_expr}':a='{a_expr}'",
        "-frames:v", "1", "-update", "1",
        glow_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Kart parlaması üretilemedi: {result.stderr[-1000:]}")
    return glow_path


def ensure_vignette(width: int, height: int, theme_key: str) -> str:
    """Arka planı platform+tema başına BİR KEZ üretir ve önbelleğe alır: merkezdeki
    radial falloff + asimetrik tonlu bokeh blob (accent'in açık tonu) → derinlik.
    Bokeh çok yumuşak/bulanık olmalı (soft glow), kart'ı ön plana çıkarmak için.
    Bunu her karede canlı `geq` ile hesaplamak çok yavaştı — statik bir PNG
    üretip bindirmek hızlı."""
    path = f"assets/vignette_{width}x{height}_{theme_key}.png"
    if os.path.isfile(path):
        return path

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    # Merkez falloff + kartın HEMEN ARKASINDA açık tonlu (beyaza yakın) turquoise/magenta
    # glow, + uzak köşelerde daha koyu/saturated aynı renkler → derinlik katmanı.
    br = config.BG_CENTER_BRIGHTNESS
    center_falloff = "max(0,1-hypot(X-W/2\\,Y-H/2)/hypot(W/2\\,H/2))"

    # Kartın hemen arkası (merkeze yakın, DAHA DAR) — AÇIK TON, güçlü kontrast → "boşlukta
    # asılı" hissi için kart çevresi belirgin şekilde parlak, ondan sonrası hızla kararıyor.
    sigma_near = "min(W\\,H)*0.16"
    d_near = "hypot(X-W/2\\,Y-H/2)"
    bokeh_near = f"exp(-pow({d_near}/({sigma_near})\\,2))"
    near_peak = 70

    # Uzak köşe bokehları — GENİŞ yayılım, kenarlara kadar görünür kalsın (derinlik hissi
    # için tamamen siyaha gömülmesin, hafif renk/gradyan uzaklara doğru sürsün).
    sigma_far = "min(W\\,H)*0.65"
    d1 = "hypot(X-W*0.15\\,Y-H*0.15)"
    d2 = "hypot(X-W*0.85\\,Y-H*0.85)"
    bokeh1 = f"exp(-pow({d1}/({sigma_far})\\,2))"
    bokeh2 = f"exp(-pow({d2}/({sigma_far})\\,2))"
    far_peak = 24

    # Açık ton (beyaza %50 karışmış) turquoise/magenta
    r_turq_l, g_turq_l, b_turq_l = 128, 238, 255
    r_mag_l, g_mag_l, b_mag_l = 255, 158, 228
    r_turq, g_turq, b_turq = 0, 220, 255
    r_mag, g_mag, b_mag = 255, 60, 200

    r_expr = (f"clip({br}*0.1*{center_falloff}"
              f"+{near_peak}*{r_turq_l/255:.4f}*{bokeh_near}"
              f"+{far_peak}*{r_turq/255:.4f}*{bokeh1}+{far_peak}*{r_mag/255:.4f}*{bokeh2}\\,0\\,255)")
    g_expr = (f"clip({br}*0.1*{center_falloff}"
              f"+{near_peak}*{g_turq_l/255:.4f}*{bokeh_near}"
              f"+{far_peak}*{g_turq/255:.4f}*{bokeh1}+{far_peak}*{g_mag/255:.4f}*{bokeh2}\\,0\\,255)")
    b_expr = (f"clip({br}*0.15*{center_falloff}"
              f"+{near_peak}*{b_turq_l/255:.4f}*{bokeh_near}"
              f"+{far_peak}*{b_turq/255:.4f}*{bokeh1}+{far_peak}*{b_mag/255:.4f}*{bokeh2}\\,0\\,255)")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}",
        "-vf", f"geq=r='{r_expr}':g='{g_expr}':b='{b_expr}'",
        "-frames:v", "1", "-update", "1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Arka plan üretilemedi: {result.stderr[-1000:]}")
    return path




def _build_filter_complex(width: int, height: int, duration: float, title: str | None, has_art: bool, theme_key: str) -> str:
    fps = config.FPS

    card_size = int(min(width, height) * config.CARD_SIZE_RATIO)
    card_size -= card_size % 2
    glow_margin = int(card_size * config.CARD_GLOW_MARGIN_RATIO)
    glow_size = card_size + 2 * glow_margin
    glow_size -= glow_size % 2
    bar_thick = int(card_size * config.EQ_BAR_THICKNESS_RATIO)
    bar_thick -= bar_thick % 2

    # Kart + alt kenardaki eşitleyici çubuk bandı + künye yazısı + sabit marka satırını
    # bir bütün olarak dikey ortalıyoruz. Referans videoya göre: bu yazılar kartın
    # ALTINDA (küçük bir boşlukla) — alt eşitleyici bandı ile üst üste binmesin diye
    # yazı bloğu bar_thick kadar aşağı kaydırılıyor.
    # Kayan künye yazısı artık sabit "Famous Music Studio" marka satırıyla AYNI
    # boyutta (önceden daha büyüktü, "famous music studio boyu kadar olsun" istendi).
    base_fontsize = int(height * config.FONT_SIZE_RATIO)
    label_fontsize = int(base_fontsize * config.STATIC_LABEL_FONT_RATIO)
    fontsize = label_fontsize
    marquee_strip_h = int(fontsize * 1.3)
    marquee_gap = int(height * config.MARQUEE_GAP_RATIO)
    label_gap = int(height * config.STATIC_LABEL_GAP_RATIO)
    label_strip_h = int(label_fontsize * 1.3)
    total_h = card_size + bar_thick + marquee_gap + marquee_strip_h + label_gap + label_strip_h
    card_y = max(0, (height - total_h) // 2)
    card_x = (width - card_size) // 2

    glow_x = card_x - glow_margin
    glow_y = card_y - glow_margin

    marquee_y = card_y + card_size + bar_thick + marquee_gap
    label_y = marquee_y + marquee_strip_h + label_gap

    # Arka plan: ortada hafif aydınlık + iki asimetrik renkli bokeh lekesi, kenarlara
    # doğru siyaha kararıyor. Önbelleğe alınmış statik bir PNG (her karede geq yerine).
    canvas = f"[3:v]fps={fps}[canvas]"

    # "Famous Music Studio" logosu sadece platform thumbnail'inde (cover.jpg) kullanılıyor —
    # video içindeki kartta GÖSTERİLMİYOR. art_path verilmişse o görsel kare kırpılıp
    # kullanılır (esnek kart içeriği); yoksa düz koyu renkle dolduruluyor (sabit fallback).
    if has_art:
        card_raw = (
            f"[4:v]scale={card_size}:{card_size}:force_original_aspect_ratio=increase,"
            f"crop={card_size}:{card_size},format=rgba[card_raw]"
        )
    else:
        card_raw = (
            f"color=c={config.CARD_ART_COLOR}:s={card_size}x{card_size}:"
            f"d={duration:.3f}:rate={fps},format=rgba[card_raw]"
        )
    mask_scaled = f"[2:v]scale={card_size}:{card_size}[mask_s]"
    card = "[card_raw][mask_s]alphamerge[card]"

    parts = [
        canvas, card_raw, mask_scaled, card,
        f"[canvas][card]overlay={card_x}:{card_y}[bg2]",
    ]
    pre_label = "bg2"

    if title:
        # Künye yazısı (şarkı adı + müzik türü, tekrarlı) kartın ALTINDA, kart
        # genişliğinde (tüm ekran genişliğinde DEĞİL) kayıyor. Altında da sabit
        # "Famous Music Studio" marka satırı duruyor (kaymıyor).
        sep = config.MARQUEE_SEPARATOR
        genre_labels = [config.THEMES[theme_key]["label"]] + config.THEMES[theme_key].get("related", [])
        genre_text = sep.join(genre_labels)
        segment = f"{title}{sep}{genre_text}{sep}"
        marquee_text = _escape_drawtext(segment * config.MARQUEE_REPEAT)
        rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
        speed = config.MARQUEE_SPEED_PX_S

        # Kayan yazının GÖRÜNÜR penceresi artık kart genişliği değil, alttaki sabit
        # "Famous Music Studio" satırıyla aynı genişlikte (ikisi aynı fontta/boyutta
        # olduğu için karakter sayısına göre piksel genişliği kabaca tahmin ediliyor).
        label_width_est = int(len(config.STATIC_LABEL_TEXT) * label_fontsize * config.FONT_CHAR_WIDTH_RATIO)
        marquee_w = min(card_size, max(1, label_width_est))
        marquee_x = card_x + (card_size - marquee_w) // 2

        parts.append(
            f"color=c=black@0.0:s={marquee_w}x{marquee_strip_h}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font}:text='{marquee_text}':"
            f"fontcolor={config.FONT_COLOR}:fontsize={fontsize}:"
            f"x='w-mod(t*{speed}\\,(w+text_w))':y=0[marquee_strip]"
        )
        parts.append(f"[{pre_label}][marquee_strip]overlay={marquee_x}:{marquee_y}[bgm]")
        pre_label = "bgm"

        # Sabit marka satırı: künye yazısıyla AYNI font ve AYNI düz beyaz renk —
        # tek tip, tutarlı bir yazı görünümü için renk animasyonu YOK.
        label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
        parts.append(
            f"[{pre_label}]drawtext=fontfile={rel_font}:text='{label_escaped}':"
            f"fontcolor={config.FONT_COLOR}:fontsize={label_fontsize}:"
            f"x=(w-text_w)/2:y={label_y}[bglabel]"
        )
        pre_label = "bglabel"

    # İlerleme çubuğu: T (mutlak zaman) kullanan bir geq ile dolu/boş kısmı çiziyoruz.
    bar_margin = int(width * config.PROGRESS_BAR_MARGIN_RATIO)
    bar_w = width - 2 * bar_margin
    pbar_h = max(2, int(height * config.PROGRESS_BAR_HEIGHT_RATIO))
    bar_y = height - int(height * config.PROGRESS_BAR_BOTTOM_RATIO)
    filled, empty = config.PROGRESS_BAR_FILLED, config.PROGRESS_BAR_EMPTY
    bar_expr = f"{empty}+{filled - empty}*lt(X\\,W*T/{duration:.3f})"
    parts.append(f"color=c=black:s={bar_w}x{pbar_h}:d={duration:.3f}:rate={fps}[barbg]")
    parts.append(f"[barbg]geq=r='{bar_expr}':g='{bar_expr}':b='{bar_expr}'[bar]")
    parts.append(f"[{pre_label}][bar]overlay={bar_margin}:{bar_y}[vfinal]")

    return ";".join(parts)


def render_video(art_path: str | None, audio_path: str, output_path: str, width: int, height: int, title: str | None = None, theme: str | None = None) -> None:
    duration = get_audio_duration(audio_path)
    theme_key = get_theme_key(theme)
    mask_path = ensure_card_mask()
    glow_path = ensure_card_glow(theme_key)
    vignette_path = ensure_vignette(width, height, theme_key)
    has_art = bool(art_path)
    filter_complex = _build_filter_complex(width, height, duration, title, has_art, theme_key)

    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-loop", "1", "-i", glow_path,
        "-loop", "1", "-i", mask_path,
        "-loop", "1", "-i", vignette_path,
    ]
    if has_art:
        cmd += ["-loop", "1", "-i", art_path]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", "0:a",
        "-t", f"{duration:.3f}",
        "-c:v", config.VIDEO_CODEC,
        "-preset", config.PRESET,
        "-crf", config.CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", config.AUDIO_CODEC,
        "-b:a", config.AUDIO_BITRATE,
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render hatası ({output_path}):\n{result.stderr[-2000:]}")
