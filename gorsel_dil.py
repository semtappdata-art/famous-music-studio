"""Şarkıdan türetilen görsel dil: nabız, doku, ton, huzme (beams) ve kapak imzası.

Kurallar (CLAUDE.md'deki sentezden):
  1) Her görsel parametre şarkıyı dinler: nabız=BPM, ton=art dominant/theme accent,
     desen=şarkı-hash, her şey deterministik.
  2) Kart içi (art.jpg) asla değişmez — efektler yalnız backdrop + huzme + kart kenarı.
  3) Nabız = offline librosa BPM → gömülü sinüs (eq brightness, eval=frame).
  4) Bütçe max ~%30 brightest-flash; sınıf tavanı; fotoepilepsi < 3 flash/sn.
  5) Sinematik doku: deterministik noise (all_seed) + tema grade.
  6) Kapak imzası: scrim + accent divider + logo koyu çip; 2-3 şablon.
  7) Huzme cache'te üretilip ucuz pan/hue ile hareket ettirilir — kare başına maliyet yok.

Tüm fonksiyonlar SAF ve STATELESS — yan etki yok, dosya yazmaz (PNG üretenler hariç).
"""

import hashlib
import math
import os
import subprocess
from typing import Optional

import config
from kapak_duzen_onizleme import mood_bul, stil_etiketi

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
ENERJI_SAKIN = "sakin"
ENERJI_ORTA = "orta"
ENERJI_ENERJIK = "enerjik"

# Sınıf → (nabız genliği, nabız frekans böleni)
# f_div=1 → her vuruş, f_div=2 → her 2. vuruş, f_div=4 → her 4. vuruş
NABIZ_SINIFLARI = {
    ENERJI_SAKIN:   {"amp": 0.12, "f_div": 2},
    ENERJI_ORTA:    {"amp": 0.20, "f_div": 1},
    ENERJI_ENERJIK: {"amp": 0.30, "f_div": 4},
}

# Huzme parametreleri (beams)
BEAM_COUNT_MIN = 3
BEAM_COUNT_MAX = 5
BEAM_SHARPNESS = 3.0      # cos^sharpness → dar ışınlar
BEAM_OPAKLIK = 0.10       # backdrop üzerine blend opacity
BEAM_RADIAL_R = 0.30      # max(W,H) oranında tepe yarıçapı
BEAM_RADIAL_SIGMA = 0.18  # max(W,H) oranında gaussian sigma

# Doku (grain)
GRAIN_AMPLITUDE = 7       # noise alls

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _song_hash(title: str) -> int:
    return int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)


def enerji_sinifi(bpm: float) -> str:
    if bpm < 85:
        return ENERJI_SAKIN
    if bpm <= 110:
        return ENERJI_ORTA
    return ENERJI_ENERJIK


def _max_flash_per_sec(bpm: float, f_div: int) -> float:
    """Her saniyedeki max parlama sayısı — fotoepilepsi kontrolü."""
    return bpm / 60.0 / f_div


# ---------------------------------------------------------------------------
# BPM Ölçümü
# ---------------------------------------------------------------------------

def measure_bpm(audio_path: str) -> tuple[float, float]:
    """librosa beat_track ile BPM ve şarkı süresi (sn) döner.

    Returns:
        (bpm, duration_seconds)
    """
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = len(y) / sr
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    return max(bpm, 40.0), duration


# ---------------------------------------------------------------------------
# Hakim Renk
# ---------------------------------------------------------------------------

def hakim_renk(art_path: str) -> tuple[int, int, int]:
    """art.jpg'den dominiant RGB rengini 1 piksel çözünürlükte okur.

    ffmpeg scale=1:1 → ham rgb24 bayt → (R, G, B). Hata olursa tema accent fallback."""
    try:
        cmd = [
            "ffmpeg", "-v", "error", "-i", art_path,
            "-vf", "scale=1:1:flags=fast_bilinear,format=rgb24",
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]
        ham = subprocess.run(cmd, capture_output=True, timeout=30).stdout
        if len(ham) >= 3:
            return (ham[0], ham[1], ham[2])
    except Exception:
        pass
    return config.THEMES[config.DEFAULT_THEME]["accent"]


# ---------------------------------------------------------------------------
# Nabız (Pulse) — Eq Brightness İfadesi
# ---------------------------------------------------------------------------

def nabiz_ifadesi(bpm: float) -> tuple[str, float, int]:
    """Nabız eq brightness ifadesi, flash frekansı ve sınıf id döner.

    Returns:
        (expression_str, flash_hz, flash_per_sec)

    expression_str = ``"A*pow(max(0,sin(2*PI*F*t)),8)"`` — eq brightness
    için doğrudan kullanılabilir: ``eq=brightness='<expr>':eval=frame``.
    Virgüller düz olmalı —(eq içinde tek tırnak ile korunuyor).
    """
    cls = enerji_sinifi(bpm)
    p = NABIZ_SINIFLARI[cls]
    actual_bpm = max(bpm, 40.0)
    f = actual_bpm / 60.0 / p["f_div"]
    amp = p["amp"]
    flash_per_sec = _max_flash_per_sec(actual_bpm, p["f_div"])
    expr = f"{amp:.2f}*pow(max(0,sin(2*PI*{f:.4f}*t)),8)"
    return expr, f, flash_per_sec


# ---------------------------------------------------------------------------
# Mood
# ---------------------------------------------------------------------------

def mood_olc(title: str) -> Optional[str]:
    """Şarkı adından stil etiketi → mood çıkarır; bulamazsa None."""
    try:
        return mood_bul(stil_etiketi(title))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Doku (Grain) + Renk Derecelendirme (Grade) Filtresi Zinciri
# ---------------------------------------------------------------------------

def doku_filtresi(seed: int) -> str:
    """Deterministik grain — her karede farklı desen, sabit seed."""
    return f"noise=alls={GRAIN_AMPLITUDE}:all_seed=0x{seed & 0xFFFF:04x}"


def derecelendirme_filtresi(mood: Optional[str], theme_accent: tuple[int, int, int]) -> str:
    """Mood + tema accent'e göre sinematik renk derecelendirmesi.

    Tüm stiller için hafif çapraz tonlama (shadows→soğuk, highlights→sıcak)
    + minimal kontrast/saturation artışı. Mood'a göre subtillar ayarlanır."""

    # Temel grade: çapraz tonlama
    bs, gs, rs = 0.04, 0.02, 0.01  # shadows → soğuk-mavi
    rh, gh, bh = 0.03, 0.01, -0.02  # highlights → sıcak-altın
    contrast = 1.04
    saturation = 1.06

    if mood == "dark":
        bs, rh = 0.06, 0.02
        contrast = 1.06
    elif mood == "energetic":
        saturation = 1.10
        contrast = 1.05
    elif mood == "calm":
        bs, saturation = 0.03, 1.02
        contrast = 1.02
    elif mood == "nostalgic":
        bs, bh = 0.02, 0.00
        saturation = 0.98
        contrast = 1.03
    elif mood == "romantic":
        rh = 0.05
        saturation = 1.08
    elif mood == "dreamy":
        bs, saturation = 0.05, 1.00
        contrast = 1.02

    parts = [
        f"colorbalance=bs={bs:.3f}:gs={gs:.3f}:rs={rs:.3f}"
        f":rh={rh:.3f}:gh={gh:.3f}:bh={bh:.3f}",
        f"eq=contrast={contrast:.2f}:saturation={saturation:.2f}",
    ]
    return ",".join(parts)


# ---------------------------------------------------------------------------
# Huzme (Beams) PNG Üretimi
# ---------------------------------------------------------------------------

def _huzme_aci_degerleri(seed: int, n: int) -> list[float]:
    """Deterministik huzme açıları (radyan, 0..2π)."""
    angles = []
    rng_seed = seed
    for i in range(n):
        rng_seed = (rng_seed * 1103515245 + 12345) & 0x7FFFFFFF
        angles.append((rng_seed / 0x7FFFFFFF) * 2 * math.pi)
    return angles


def huzme_png_uret(out_path: str, width: int, height: int, seed: int) -> str:
    """Beyaz huzmeler siyah zeminde PNG üretir (ekran blend için).

    Döngüsal cos deseni: ``pow((cos(N*angle + phase)+1)/2, sharp)`` × radyal gauss.
    Tek seferlik geq çağrısı, backdrop cache ile birlikte pan/hue'da bedava hareket.

    Returns:
        Üretilen PNG yolu.
    """
    if os.path.isfile(out_path):
        return out_path

    n_beams = BEAM_COUNT_MIN + (seed % (BEAM_COUNT_MAX - BEAM_COUNT_MIN + 1))
    cx, cy = width / 2.0, height / 2.0
    phase_degerleri = _huzme_aci_degerleri(seed + 999, n_beams)
    r_max = max(width, height) * BEAM_RADIAL_R
    sigma_r = max(width, height) * BEAM_RADIAL_SIGMA

    # cos deseni: her huzme için cos(angle - theta_i) → toplam
    # Tek ifadede toplamak için literal açıları ekle
    angle_parts = []
    for theta in phase_degerleri:
        angle_parts.append(
            f"cos({n_beams}*atan2(Y-{cy:.1f},{cx:.1f}-X)+{theta:.4f})"
        )
    angular_sum = "+".join(angle_parts)

    # Huzme genliği: (sum + n_beams) / (2 * n_beams) → 0..1 aralığına normalize
    angular_norm = f"(({angular_sum})+{n_beams})/{2 * n_beams}"

    # Radyal gauss: tepe r_max'te, merkeze ve kenara doğru sönme
    radial = f"exp(-pow((hypot(X-{cx:.1f},Y-{cy:.1f})-{r_max:.1f})/{sigma_r:.1f},2))"

    # Nihai parlaklık: amp × angular^sharp × radial
    peak_amp = 220  # 0-255 aralığında tepe parlaklık
    expr_r = f"clip({peak_amp}*pow(max(0,{angular_norm}),{BEAM_SHARPNESS:.1f})*{radial}\\,0\\,255)"
    expr_g = f"clip({peak_amp}*pow(max(0,{angular_norm}),{BEAM_SHARPNESS:.1f})*{radial}\\,0\\,255)"
    expr_b = f"clip({int(peak_amp * 1.05)}*pow(max(0,{angular_norm}),{BEAM_SHARPNESS:.1f})*{radial}\\,0\\,255)"

    vf = f"geq=r='{expr_r}':g='{expr_g}':b='{expr_b}'"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}",
        "-vf", vf,
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Huzme PNG üretilemedi: {result.stderr[-800:]}")
    return out_path


def huzmeli_backdrop_uret(art_path: str, width: int, height: int,
                          seed: int, cache_dir: Optional[str] = None) -> str:
    """Backdrop PNG üzerine huzmeleri ekran (screen blend) ile bindirir.

    Düzenli backdrop + huzme PNG → tek seferlik blend → cache'li sonuç.
    Pan/hue zaten render sırasında uygulanıyor, huzme bedava hareket ediyor.

    Returns:
        Huzmeli backdrop PNG yolu.
    """
    from ffmpeg_utils import ensure_art_backdrop

    if cache_dir is None:
        cache_dir = os.path.dirname(art_path)
    backdrop_path = os.path.join(cache_dir, f"_backdrop_huzmeli_{width}x{height}.png")
    if os.path.isfile(backdrop_path):
        return backdrop_path

    base_backdrop = ensure_art_backdrop(art_path, width, height)
    # Huzme boyutu TAHMİNİ DEĞİL, GERÇEK: base PNG'nin boyutu "ideal" panned
    # boyuttan 1px sapabiliyor (gblur/crop yuvarlama) — blend iki girdinin
    # boyutunun AYNI olmasını şart koşuyor, yoksa "input link parameters do
    # not match" ile çöker. Huzmeyi base'in GERÇEK boyutunda üretiyoruz.
    gercek = _video_boyut(base_backdrop) or _panned_size(width, height)
    bg_w, bg_h = gercek
    beams_path = os.path.join(cache_dir, f"_beams_{bg_w}x{bg_h}_{seed:08x}.png")
    huzme_png_uret(beams_path, bg_w, bg_h, seed)

    # Screen blend: backdrop + beams → huzmeli backdrop
    blend_opacity = BEAM_OPAKLIK
    cmd = [
        "ffmpeg", "-y",
        "-i", base_backdrop,
        "-i", beams_path,
        "-filter_complex",
        f"blend=all_mode=screen:all_opacity={blend_opacity:.2f}",
        "-frames:v", "1", "-update", "1",
        backdrop_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Huzmeli backdrop üretilemedi: {result.stderr[-800:]}")
    return backdrop_path


def _panned_size(width: int, height: int) -> tuple[int, int]:
    """ffmpeg_utils._panned_size ile aynı mantık — huzmeli backdrop için."""
    margin = config.BACKDROP_PAN_MARGIN_RATIO
    return int(width * (1 + margin)), int(height * (1 + margin))


def _video_boyut(path: str) -> tuple[int, int]:
    """ffprobe ile video/görselin (w, h) boyutunu okur. Hata olursa None."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        w_s, h_s = r.stdout.strip().split("x")
        return int(w_s), int(h_s)
    except Exception:                                    # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Kapak Kompozisyonu (Cover Composition) — Yeni Görsel Dil
# ---------------------------------------------------------------------------

def kapak_duzeni_sec(title: str) -> str:
    """Şarkı hash'ine göre kapak düzeni şablonu: 'A' (ortalanmış) veya 'B' (sol-alt)."""
    h = _song_hash(title)
    return "A" if (h % 2 == 0) else "B"


def kapak_uret(
    bg_path: str, out_path: str, title: str,
    accent: tuple[int, int, int],
    out_w: int, out_h: int,
    konsept: str = "threshold",
) -> None:
    """Yeni görsel dil kapak kompozisyonu (iki versiyon seçebilirsin).

    bg_path = art.jpg veya prosedürel arka plan.
    konsept:
      threshold — posterize (siyah + tek accent rengi) + siyah bantta başlık
      split    — diyagonal degradé bölünme + koyu zeminde başlık
      negatif  — mat siyah zeminde biçilmiş fotoğraf penceresi + beyaz başlık

    Girdi her zaman önce out_w x out_h'e normalize edilir (scale+crop).
    """
    import generate_cover as gc

    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    basis = min(out_w, out_h)
    accent_hex = "%02x%02x%02x" % accent
    en_buyuk = int(basis * 0.14)
    kullanilabilir = out_w * 0.86
    title_escaped, title_fs, satir = gc._basligi_sigdir(
        title, rel_font_bold, kullanilabilir, en_buyuk)

    if konsept == "threshold":
        _kapak_threshold(bg_path, out_path, title_escaped, title_fs, satir,
                         accent, accent_hex, out_w, out_h, basis,
                         rel_font_bold)
    elif konsept == "split":
        _kapak_split(bg_path, out_path, title_escaped, title_fs, satir,
                     out_w, out_h, basis, rel_font_bold)
    else:
        _kapak_negatif(bg_path, out_path, title_escaped, title_fs, satir,
                       out_w, out_h, basis, rel_font_bold)


# ── konsept yardimcilari ────────────────────────────────────────────────────

def _run(cmd: list[str]) -> None:
    """Tek satır ffmpeg; hata olursa RuntimeError fırlat."""
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg hatasi: " + result.stderr[-600:])


def _kapak_threshold(bg_path, out_path, title_escaped, title_fs, satir,
                     accent, accent_hex, out_w, out_h, basis, rel_font_bold):
    """Posterize (siyah + accent) + siyah bantta baslik (accent renginde)."""
    RA, GA, BA = accent
    THR = 115
    # Canvas TAM out_w x out_h; posterize fotograi siyah cerceve icinde ortala.
    cw = int(basis * 0.06)          # sag/sol cerceve
    ct = int(basis * 0.05)          # ust cerceve
    cb = int(basis * 0.10)          # alt bant (baslik alani)
    ic_w, ic_h = out_w - 2 * cw, out_h - ct - cb
    normalize = (f"scale={ic_w}:{ic_h}:"
                 f"force_original_aspect_ratio=increase,crop={ic_w}:{ic_h},")
    # posterize: gblur -> geq threshold -> renk
    # geq icinde L = 0.299*R + 0.587*G + 0.114*B
    luma = "0.299*r(X,Y)+0.587*g(X,Y)+0.114*b(X,Y)"
    geq = (f"geq=r='if(gt({luma},{THR}),{RA},0)'"
           f":g='if(gt({luma},{THR}),{GA},0)'"
           f":b='if(gt({luma},{THR}),{BA},0)'")
    title_y = ct + ic_h + int(cb * 0.30)
    fc = (
        f"[0:v]{normalize}"
        f"format=rgb24,"
        f"gblur=sigma=0.6,"
        f"{geq},"
        f"pad={out_w}:{out_h}:{cw}:{ct}:color=black,"
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':"
        f"fontcolor=0x{accent_hex}:fontsize={title_fs}:"
        f"shadowcolor=black@0.65:shadowx=2:shadowy=2:"
        f"x=(w-text_w)/2:y={title_y}[out]"
    )
    _run(["ffmpeg", "-y", "-i", bg_path,
          "-filter_complex", fc, "-map", "[out]",
          "-frames:v", "1", "-update", "1", out_path])


def _kapak_split(bg_path, out_path, title_escaped, title_fs, satir,
                 out_w, out_h, basis, rel_font_bold):
    """Diyagonal degradé bolunme + koyu zeminde baslik."""
    normalize = (f"scale={out_w}:{out_h}:"
                 "force_original_aspect_ratio=increase,crop={}:{},".format(out_w, out_h))
    is_dikey = out_h > out_w
    if is_dikey:
        yt = int(out_h * 0.62)
        FALL = int(out_h * 0.10)
        title_x = int(basis * 0.07)
        title_y = int(out_h * 0.78)
        title_w = out_w - 2 * int(basis * 0.07)
        # dikey: ust tam acik, alt karartma (Y > yt icin karanlik)
        dark_factor = f"min(1,max(0,({yt}-Y)/{FALL}+1))"
    else:
        xs = int(out_w * 0.55)
        slope = 0.35
        FALL = int(out_w * 0.09)
        edge_at_bottom = xs + int(out_h * slope)
        title_x = int(out_w * 0.68)
        title_y = int(out_h * 0.22)
        title_w = int(out_w * 0.27)
        # yatay: soldan saga dogru karartma, soldaki diyagonal cizgiden saga
        dark_factor = f"min(1,max(0,({xs}+Y*{slope}-X)/{FALL}+1))"

    geq = (
        f"geq="
        f"r='r(X,Y)*{dark_factor}'"
        f":g='g(X,Y)*{dark_factor}'"
        f":b='b(X,Y)*{dark_factor}'"
    )
    fc = (
        f"[0:v]{normalize}"
        f"format=rgb24,"
        f"{geq},"
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':"
        f"fontcolor=white:fontsize={title_fs}:"
        f"shadowcolor=black@0.70:shadowx=2:shadowy=2:"
        f"x={title_x}:y={title_y}"
        f"[out]"
    )
    _run(["ffmpeg", "-y", "-i", bg_path,
          "-filter_complex", fc, "-map", "[out]",
          "-frames:v", "1", "-update", "1", out_path])


def _kapak_negatif(bg_path, out_path, title_escaped, title_fs, satir,
                   out_w, out_h, basis, rel_font_bold):
    """Mat siyah zeminde bicilmis fotograf penceresi + beyaz baslik."""
    is_dikey = out_h > out_w
    if is_dikey:
        win_w = out_w - 2 * int(basis * 0.06)
        win_h = int(out_h * 0.22)
        win_x = int(basis * 0.06)
        win_y = int(out_h * 0.68)
        rot = 0.0
        title_x = int(basis * 0.07)
        title_y = int(basis * 0.10)
    else:
        win_w = int(out_w * 0.48)
        win_h = int(out_h * 0.46)
        win_x = out_w - win_w - int(basis * 0.06)
        win_y = out_h - win_h - int(basis * 0.05)
        rot = 0.035
        title_x = int(basis * 0.07)
        title_y = int(basis * 0.10)

    # siyah tuval (tek kare)
    bg_spec = f"color=black:s={out_w}x{out_h}:d=1"
    # foto: normalize -> crop-to-fit + rotate + olcule
    photo_vf = (
        f"scale={win_w}:{win_h}:"
        "force_original_aspect_ratio=increase,"
        f"crop={win_w}:{win_h},"
        f"rotate={rot}:fillcolor=none"
    )
    fc = (
        f"[0:v]{photo_vf}[wnd];"
        f"[1:v][wnd]overlay={win_x}:{win_y}[base];"
        f"[base]drawtext=fontfile={rel_font_bold}:text='{title_escaped}':"
        f"fontcolor=white:fontsize={title_fs}:"
        f"shadowcolor=black@0.75:shadowx=3:shadowy=3:"
        f"x={title_x}:y={title_y}[out]"
    )
    _run(["ffmpeg", "-y",
          "-i", bg_path,
          "-f", "lavfi", "-i", bg_spec,
          "-filter_complex", fc, "-map", "[out]",
          "-frames:v", "1", "-update", "1", out_path])
