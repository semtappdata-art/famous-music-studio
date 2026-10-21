"""ffprobe/ffmpeg ile süre okuma ve kart tasarımı video render fonksiyonları.

Tasarım (Spotify "Now Playing" tarzı): ekranın büyük kısmını kaplayan yuvarlak köşeli
bir albüm kartı (içeriği o şarkının art.jpg'si) + arka plan, o AYNI art.jpg'nin
bulanıklaştırılmış/karartılmış hâli — statik değil, video boyunca yavaşça kayıyor
(pan) ve dar bir açı aralığında ton değiştiriyor (hue akışı, bkz. _panned_size,
_build_filter_complex'teki pan_x/pan_y/hue_shift). Kartın altında kayan künye yazısı
+ sabit "Famous Music Studio" marka satırı + en altta bir ilerleme çubuğu. Kart
statik durur (zoom yok, sadece backdrop hareketli) — waveform/eşitleyici çubuğu YOK
(önceki bir tasarımda vardı, kaldırıldı). Sadece kart alanı + backdrop işlenir,
kenarlar arka planla dolar (düz siyah değil).
"""

import os
import re
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


# =============================================================================
# SES ÖLÇÜMÜ (2026-10-21) — true-peak limiter için
# =============================================================================

def _sayi_bul(metin: str, desen: str):
    """Desene uyan ilk sayıyı döner; yoksa None."""
    m = re.search(desen, metin)
    if not m:
        return None
    try:
        return float(m.group(1))
    except (TypeError, ValueError):
        return None


def ses_olc(audio_path: str) -> dict:
    """(lufs, tp, lra) ölçümü — ffmpeg `ebur128=peak=true` çıktısından.

    NEDEN: Suno çıktıları zaten −12,9 … −14,8 LUFS; genel normalizasyon
    (loudnorm) bir şey kazandırmaz, üstelik TEK geçişli loudnorm pompalayabilir.
    Gerçek risk TRUE PEAK: iki ses −0,5 dBTP'de ve AAC 192k kodlaması tepesi
    taşırabilir. Bu yüzden yalnızca ÖLÇÜLEN TP eşiği aşarsa limiter girer.

    DÖNER: {"lufs": float, "tp": float, "lra": float}
    HATA: ffmpeg başarısız / özet yok / değer okunamaz (sessiz dosya: -inf)

    ÖNEMLİ: Değerler "Summary:" BLOĞUNDAN okunur. ebur128 her kare için
    satır yazar (I: -70.0 LUFS gibi) — ilk satırdakiler ANLAMLI DEĞİLDİR.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", audio_path,
        "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg ses ölçemedi (ebur128): %s" % (result.stderr or "").strip()[:200])
    cikti = result.stderr or ""
    if "Summary:" not in cikti:
        raise RuntimeError("ebur128 özeti yok — ses ölçülemedi")
    ozet = cikti.split("Summary:", 1)[1]

    lufs = _sayi_bul(ozet, r"I:\s*(-?[\d.]+)\s*LUFS")
    lra = _sayi_bul(ozet, r"LRA:\s*(-?[\d.]+)\s*LU")
    tp = _sayi_bul(ozet, r"Peak:\s*(-?[\d.]+|-inf|-infinity)\s*dBFS")
    if lufs is None or tp is None or lra is None:
        raise RuntimeError("ebur128 özeti okunamadı (lufs=%s tp=%s lra=%s)"
                           % (lufs, tp, lra))
    # -inf (SESSIZ dosya) gecerli bir olcum DEGIL: float('-inf') parse
    # olur ama limiter karari verilemez. Sessiz ses -> olcum basarisiz.
    import math as _math
    if not (_math.isfinite(lufs) and _math.isfinite(tp) and _math.isfinite(lra)):
        raise RuntimeError("ebur128 özeti sonlu değil (lufs=%s tp=%s lra=%s) — "
                           "ses sessiz veya ölçülemedi" % (lufs, tp, lra))
    return {"lufs": lufs, "tp": tp, "lra": lra}


def limiter_filtresi() -> str:
    """True-peak limiter ses filtresi (ffmpeg `-af` değeri).

    NEDEN 4× AŞIRI ÖRNEKLEME: Düz (1×) alimiter, AAC 192k kodlaması
    SONRASI true peak'i KÖTÜLEŞTİRİR (resampler yeni tepe üretir). 4× aşırı
    örneklemeli alimiter ise TP'yi −1 dBTP'nin altına gerçekten çeker —
    katalog dosyalarıyla elle ölçülmüştür (bkz. config.SES_LIMITER_*).

    NEDEN `level=false`: limiter SADECE tepeyi kıstırır. Seviye/loudness
    DEĞİŞMEZ — "loudnorm" veya "dynaudnorm" KULLANILMAZ (tek geçişli
    loudnorm pompalar; loudness hedefi zaten Suno çıktısında doğru).

    Zincir: 192 kHz'e çık → limiter → 48 kHz'e geri in.
    """
    tavan = getattr(config, "SES_LIMITER_TAVAN_DBFS", -2.0)
    asiri = getattr(config, "SES_LIMITER_ASIRI_ORNEKLEME", 192000)
    cikis = getattr(config, "SES_LIMITER_CIKIS_HZ", 48000)
    return ("aresample=%d,alimiter=limit=%sdB:level=false:attack=5:release=50,"
            "aresample=%d" % (asiri, tavan, cikis))


def bastaki_sessizlik(audio_path: str) -> float:
    """Sesi başındaki sessiz bölgenin süresi (saniye). Bulunamazsa 0.0.

    NEDEN: Şarkının başı sessizse cold-open (ön tat) boşluğa denk gelir ve
    izleyici ilk saniyelerde ses duymaz. Ölçüm, sessizliğin gerçekten
    BAŞTA olduğunu doğrular (ortadaki sessizlik sayılmaz).
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", audio_path,
        "-af", "silencedetect=noise=-50dB:d=0.3",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return 0.0
    if result.returncode != 0:
        return 0.0
    cikti = result.stderr or ""
    bas = _sayi_bul(cikti, r"silence_start:\s*(-?[\d.]+)")
    if bas is None or bas > 0.5:
        # Sessizlik ya yok ya da başta değil (ortada bir sessizlik)
        return 0.0
    bit = _sayi_bul(cikti, r"silence_end:\s*([\d.]+)")
    if bit is None:
        return 0.0
    return max(0.0, bit - bas)


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")  # tipografik kesme işareti — filtre sözdizimini bozmasın
    text = text.replace("%", "\\%")
    return text


def _format_hashtag_titlecase(tag: str) -> str:
    """Hashtag'i Title Case'e çevir: #keşfet -> #Keşfet, #fyp -> #Fyp.
    Türkçe karakterler için str.title() uygun çalışır."""
    if not tag:
        return ""
    if tag.startswith("#"):
        tag = tag[1:]
    # '&' ve diğer özel karakterler zaten hashtag() fonksiyonunda temizlenmiş olmalı
    return "#" + tag.title()


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


def _panned_size(width: int, height: int) -> tuple[int, int]:
    """Arka planın pan edilebilmesi için hedef çözünürlükten BACKDROP_PAN_MARGIN_RATIO
    kadar büyük üretilmesi gereken boyut — _build_filter_complex bu fazlalık içinde
    zamanla kayan bir crop penceresi açıyor."""
    margin = config.BACKDROP_PAN_MARGIN_RATIO
    return int(width * (1 + margin)), int(height * (1 + margin))


def ensure_art_backdrop(art_path: str, width: int, height: int) -> str:
    """Spotify Now Playing tarzı: arka plan, kartta gösterilen görselin (art.jpg)
    kendisinin tüm ekranı kaplayacak şekilde büyütülüp güçlü bulanıklaştırılmış
    hâli — böylece arka planın rengi/atmosferi sabit bir tema paletinden değil,
    doğrudan o şarkının kart görselinden geliyor. Şablon (blur + hafif karartma)
    her şarkıda AYNI kalıyor, sadece kaynak görsel değiştiği için sonuç renk
    şarkıdan şarkıya doğal olarak değişiyor. Hedef çözünürlükten biraz BÜYÜK
    üretiliyor (bkz. _panned_size) ki render sırasında içinde yavaşça kayan bir
    pan efekti olsun — arka plan sabit bir kare değil. Proje bazında önbelleğe
    alınır (art.jpg'nin yanına, çözünürlüğe göre) — parça başına bir kez üretilir."""
    backdrop_path = os.path.join(os.path.dirname(art_path), f"_backdrop_pan_{width}x{height}.png")
    if os.path.isfile(backdrop_path):
        return backdrop_path

    bg_w, bg_h = _panned_size(width, height)
    sigma = max(20, int(min(width, height) * 0.045))
    cmd = [
        "ffmpeg", "-y",
        "-i", art_path,
        "-vf", (
            f"scale={bg_w}:{bg_h}:force_original_aspect_ratio=increase,"
            f"crop={bg_w}:{bg_h},"
            f"gblur=sigma={sigma},"
            f"eq=brightness=-0.12:saturation=1.15"
        ),
        "-frames:v", "1", "-update", "1",
        backdrop_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Kart arka planı (blur) üretilemedi: {result.stderr[-1000:]}")
    return backdrop_path


def ensure_vignette(width: int, height: int, theme_key: str) -> str:
    """FALLBACK arka plan — sadece projede art.jpg yokken kullanılır (kart
    art.jpg'siz düz renge düştüğünde, blur alınacak bir görsel olmadığı için).
    Art.jpg varsa bunun yerine ensure_art_backdrop() kullanılır. Platform+tema
    başına BİR KEZ üretir ve önbelleğe alır: merkezdeki radial falloff +
    asimetrik tonlu bokeh blob → derinlik. Bunu her karede canlı `geq` ile
    hesaplamak çok yavaştı — statik bir PNG üretip bindirmek hızlı.
    Hedef çözünürlükten biraz BÜYÜK üretiliyor (bkz. _panned_size) ki
    ensure_art_backdrop gibi bu da render sırasında yavaşça kayan bir pan
    efekti alsın."""
    path = f"assets/vignette_pan_{width}x{height}_{theme_key}.png"
    if os.path.isfile(path):
        return path

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    width, height = _panned_size(width, height)

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




def _build_filter_complex(
    width: int, height: int, duration: float, title: str | None, has_art: bool,
    theme_key: str, marquee_override: str | None = None,
    end_card_text: str | None = None, cta_text: str | None = None,
) -> str:
    fps = config.FPS
    bg_pan_w, bg_pan_h = _panned_size(width, height)

    card_size = int(min(width, height) * config.CARD_SIZE_RATIO)
    card_size -= card_size % 2
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

    marquee_y = card_y + card_size + bar_thick + marquee_gap
    label_y = marquee_y + marquee_strip_h + label_gap

    # Arka plan: art.jpg varsa onun bulanıklaştırılmış hâli (ensure_art_backdrop),
    # yoksa (kart art.jpg'siz düz renge düştüğünde) sabit vignette fallback'i
    # (ensure_vignette) — hangisi olduğu render_video() tarafında seçiliyor,
    # ikisi de aynı [2:v] girişinden geliyor. İkisi de _panned_size() kadar
    # BÜYÜK statik bir PNG (kaynak görsel/desen sabit) — burada, hedef boyutta
    # bir crop penceresini zamanla (sin/cos ile) kaydırarak arka planı hareketli
    # hale getiriyoruz. Zoom yok, sadece pan — crop neredeyse ücretsiz olduğu
    # için performans maliyeti yok (geq'i her karede yeniden hesaplamak yerine).
    # Buna ek olarak `hue` filtresiyle renk akışı: ton zamanla dar bir açı
    # aralığında ileri-geri salınıyor (tam 360° dönmüyor — şarkının kendi tema
    # renginden çok uzaklaşmasın diye), pan ile birlikte "hareketli + renk akan"
    # bir arka plan hissi veriyor. hue de ucuz bir filtre, performans maliyeti yok.
    # BÜYÜME NABZI (madde 7): GORSEL_NABIZ_SURE_SN'de bir hue vurgusu + pan'a
    # hafif ikinci harmonik — bölüm verisi olmasa bile ~25sn'de bir "bir şey
    # oluyor" hissi; virgülsüz ifade (filtre ayrıştırıcıyla çakışmasın diye).
    nabiz_w = 6.283185 / max(1.0, float(getattr(config, 'GORSEL_NABIZ_SURE_SN', 25.0)))
    nabiz_guc = float(getattr(config, 'GORSEL_NABIZ_GUC', 0.9))
    nabiz_pulse = (
        f"(0.5+0.5*sin(t*{nabiz_w:.6f}))*(0.5+0.5*sin(t*{nabiz_w:.6f}))"
    )
    pan_x_range = (bg_pan_w - width) / 2
    pan_y_range = (bg_pan_h - height) / 2
    pan_x = f"{pan_x_range:.1f}+{pan_x_range:.1f}*sin(t*{config.BACKDROP_PAN_SPEED_X})+{pan_x_range * 0.25:.1f}*sin(t*{2 * nabiz_w:.6f})"
    pan_y = f"{pan_y_range:.1f}+{pan_y_range:.1f}*cos(t*{config.BACKDROP_PAN_SPEED_Y})"
    hue_shift = f"{config.BACKDROP_HUE_AMPLITUDE_DEG}*sin(t*{config.BACKDROP_HUE_SPEED})*(1+{nabiz_guc:.2f}*{nabiz_pulse})"
    canvas = (
        f"[2:v]fps={fps},crop={width}:{height}:x='{pan_x}':y='{pan_y}',"
        f"hue=h='{hue_shift}'[canvas]"
    )

    # "Famous Music Studio" logosu sadece platform thumbnail'inde (cover.jpg) kullanılıyor —
    # video içindeki kartta GÖSTERİLMİYOR. art_path verilmişse o görsel kare kırpılıp
    # kullanılır (esnek kart içeriği); yoksa düz koyu renkle dolduruluyor (sabit fallback).
    if has_art:
        card_raw = (
            f"[3:v]scale={card_size}:{card_size}:force_original_aspect_ratio=increase,"
            f"crop={card_size}:{card_size},format=rgba[card_raw]"
        )
    else:
        card_raw = (
            f"color=c={config.CARD_ART_COLOR}:s={card_size}x{card_size}:"
            f"d={duration:.3f}:rate={fps},format=rgba[card_raw]"
        )
    mask_scaled = f"[1:v]scale={card_size}:{card_size}[mask_s]"
    card = "[card_raw][mask_s]alphamerge[card]"

    parts = [
        canvas, card_raw, mask_scaled, card,
        f"[canvas][card]overlay={card_x}:{card_y}[bg2]",
    ]
    pre_label = "bg2"

    if title:
        # Künye yazısı (şarkı adı + müzik türü, tekrarlı) kartın ALTINDA, kart
        # genişliğinde (tüm ekran genişliğinde DEĞİL) kayıyor. Altında da SABİT
        # "Famous Music Studio" marka satırı duruyor (kaymıyor) — bu her içerik
        # için AYNI, override edilmiyor.
        #
        # marquee_override verilmişse (ör. DJ Famous için "DJ Famous  •  Gece
        # Yarısı Seti  •  #DJFamous") kayan yazı bunu gösterir; verilmezse
        # varsayılan olarak title + tema/tür etiketleri kayar (ana katalog).
        sep = config.MARQUEE_SEPARATOR
        if marquee_override:
            segment = f"{marquee_override}{sep}"
        else:
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

    # BÜYÜME CTA (madde 11): videonun %40'ında 1 kez, kısa süre, emir kipi yok —
    # rutin vaat eder ("Her Cuma yeni şehir"). cta_text verilmezse çizilmez.
    if cta_text:
        cta_oran = float(getattr(config, 'ABONE_CTA_ORAN', 0.4))
        cta_sure = float(getattr(config, 'ABONE_CTA_SURE_SN', 4.0))
        cta_start = duration * cta_oran
        cta_end = min(duration, cta_start + cta_sure)
        cta_fs = int(height * 0.022)
        cta_y = int(height * 0.78)
        cta_escaped = _escape_drawtext(cta_text)
        rel_font_cta = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
        parts.append(
            f"color=c=black@0.0:s={width}x{int(cta_fs * 1.6)}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font_cta}:text='{cta_escaped}':"
            f"fontcolor=white@0.9:fontsize={cta_fs}:"
            f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[cta_strip]"
        )
        parts.append(
            f"[{pre_label}][cta_strip]overlay=0:{cta_y}:enable='between(t,{cta_start:.3f},{cta_end:.3f})'[vcta]"
        )
        pre_label = "vcta"

    # BİTİŞ KARTI (madde 10): son END_CARD_SURE_SN saniyede sonraki içerik —
    # end_card_text meta'dan gelir (yoksa çizilmez, oynatma listesinde tutma).
    if end_card_text:
        end_sure = float(getattr(config, 'END_CARD_SURE_SN', 15.0))
        end_start = max(0.0, duration - end_sure)
        end_fs = int(height * 0.028)
        end_y = int(height * 0.12)
        end_escaped = _escape_drawtext(end_card_text)
        rel_font_end = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
        parts.append(
            f"color=c=black@0.55:s={width}x{int(end_fs * 2.2)}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font_end}:text='{end_escaped}':"
            f"fontcolor=white:fontsize={end_fs}:"
            f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[end_strip]"
        )
        parts.append(
            f"[{pre_label}][end_strip]overlay=0:{end_y}:enable='gte(t,{end_start:.3f})'[vend]"
        )
        pre_label = "vend"

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


def _build_speed_ramp_video(base_input: str, plan: dict, duration: float
                            ) -> tuple[str, str]:
    """YouTube "speed ramp" — video zinciri (yavaş → beat'te hızlan).

    Dönüş: (eklenen filtre_metni, temel_video_etiketi)

    NEDEN split+trim+concat (setpts tek ifade yerine): FFmpeg'in `setpts`
    ifadesi zaman eşlemesini tek başına ifade edebilir ama
    `trim`+`concat` yaklaşımı SES tarafıyla birebir aynı zaman eşlemesini
    paylaşır → video/ses kayması imkansız olur.

    NEDEN base_input ikiye bölünüyor: `split` filtresi TEK input'u iki
    çıktıya böler (extra ffmpeg input'u gerekmez).

    Zaman eşlemesi:
        girdi [0, T_in)  -> çıktı [0, t_snap)  hız = kat
        girdi [T_in, ..) -> çıktı [t_snap, ..) hız = 1.0

    NEDEN setpts='T/kat': girdi karesi T anında çıktının T/kat
    konumuna gider → girdi [0,T_in) çıktı [0, T_in/kat) olur.
    atempo=kat ile aynı eşleme (birebir aynı hız çarpanı).
    (Ölçüldü: 'T*kat' + atempo='kat' ters yönde çalışıyordu.)
    """
    T_in = float(plan["T_in"])
    t_snap = float(plan["t_snap"])
    kat = float(plan["kat"])
    rest = max(0.0, duration - t_snap)
    if rest <= 0.0:
        return "", base_input.strip("[]")
    metin = (
        f"{base_input}split=2[ramp_a][ramp_b];"
        f"[ramp_a]trim=0:{T_in:.4f},setpts='T/{kat:.4f}'[ramp_slow];"
        f"[ramp_b]trim=start={T_in:.4f}:end={T_in + rest:.4f},"
        f"setpts=PTS-STARTPTS[ramp_fast];"
        f"[ramp_slow][ramp_fast]concat=n=2:v=1:a=0[canvas_ramp]"
    )
    return metin, "canvas_ramp"


def _build_speed_ramp_audio(audio_label: str, plan: dict, duration: float
                            ) -> tuple[str, str]:
    """YouTube "speed ramp" — ses zinciri (videoyla aynı zaman eşlemesi).

    Dönüş: (eklenen filtre_metni, ses_etiketi)

    NEDEN atempo: `atempo=kat` → çıktı süresi girdi/kat, içerik kat
    hızında çalar. Video tarafındaki `setpts='T/kat'` ile BİREBİR aynı
    zaman eşlemesini üretir (birebir aynı hız çarpanı).
    atempo aralığı [0.5, 2.0] — kat bu aralıkta olmalı.
    """
    T_in = float(plan["T_in"])
    t_snap = float(plan["t_snap"])
    kat = float(plan["kat"])
    rest = max(0.0, duration - t_snap)
    if rest <= 0.0:
        return "", audio_label
    tempo = min(2.0, max(0.5, kat))
    metin = (
        f"[{audio_label}]asplit=2[ramp_aa][ramp_ab];"
        f"[ramp_aa]atrim=0:{T_in:.4f},asetpts=PTS-STARTPTS,"
        f"atempo={tempo:.4f}[ramp_aslow];"
        f"[ramp_ab]atrim=start={T_in:.4f}:end={T_in + rest:.4f},"
        f"asetpts=PTS-STARTPTS[ramp_afast];"
        f"[ramp_aslow][ramp_afast]concat=n=2:v=0:a=1[aout_ramp]"
    )
    return metin, "aout_ramp"


def _build_shorts_filter_complex(
    width: int, height: int, duration: float, title: str | None,
    has_art: bool, theme_key: str, marquee_override: str | None = None,
    end_card_text: str | None = None, cta_text: str | None = None,
    hashtags: list | None = None,
    beat_times: list | None = None, beat_period: float = 0.0,
    base_input: str = "[1:v]",
) -> str:
    """Shorts 9:16 native filter — tam ekran art.jpg + lower third overlay.
    Kart YOK, kart squeeze YOK. Cercle/Boiler Room Shorts stilinde:
    - Tam ekran art.jpg (blur+pan+hue) arka plan
    - Lower third: şarkı adı + sanatçı (alt 1/3, yarı saydam)
    - İlerleme çubuğu (ince, alt)
    - Hook metni (ilk 2.5sn, üst kısım): "🔊 Sesini Aç"
    - Hashtag overlay — Title Case + Mavi renk (alt 1/3'ün üstünde)
    - CTA (Abone CTA) — video %40'ında, 4sn
    - Bitiş kartı — son 15sn'de end_card_text varsa
    - BEAT SYNC (YouTube efekti) — renk/pan ritme kilitli + beat flaşı
    """
    fps = config.FPS
    bg_pan_w, bg_pan_h = _panned_size(width, height)

    # Arka plan: tam ekran art.jpg (blur + pan + hue)
    # BÜYÜME NABZI (Shorts): Shorts'ta daha güçlü nabız (dikey format = hızlı dikkat kaybı)
    nabiz_w_s = 6.283185 / max(1.0, float(getattr(config, 'GORSEL_NABIZ_SURE_SN', 25.0)))
    nabiz_guc_s = float(getattr(config, 'GORSEL_NABIZ_GUC_SHORTS', 1.35))
    nabiz_pulse_s = (
        f"(0.5+0.5*sin(t*{nabiz_w_s:.6f}))*(0.5+0.5*sin(t*{nabiz_w_s:.6f}))"
    )
    pan_x_range = (bg_pan_w - width) / 2
    pan_y_range = (bg_pan_h - height) / 2

    # --- BEAT SYNC (YouTube Shorts efekti) ---------------------------------
    # NEDEN: YouTube'un "Beat sync" özelligi görselleri ritme kilitler.
    # Müzik videosunda (Cercle/HÖR/Boiler Room) görselin ritimle "snap"
    # yapmasi izleyicide profesyonel izlenimi yaratir.
    #
    # NEDEN iki katman:
    #   1) Sürekli ifade (hue/pan) — beat periyoduna göre üstel sönüm.
    #      Gerçek beat listesi yerine periyot kullanilir; boylece ifade
    #      kisa ve ffmpeg bunu hizli hesaplar.
    #   2) Kesin beat listesi (flash) — her beat'te 0.11sn parlaklik.
    #      Bu icin `enable` ifadesi beat listesiyle kurulur.
    beat_pulse_expr = "0"
    beat_hue_extra = ""
    beat_pan_extra = ""
    if getattr(config, 'SHORTS_BEAT_SYNC_AKTIF', True) and beat_period and beat_period > 0:
        import beat_sync as _bs
        beat_pulse_expr = _bs.beat_nabzi_ifadesi(
            beat_period, sertlik=float(getattr(config, 'SHORTS_BEAT_HUE_SERTLIK', 9.0)))
        if getattr(config, 'SHORTS_BEAT_HUE_AKTIF', True):
            beat_hue_extra = (f"+{float(getattr(config, 'SHORTS_BEAT_HUE_DERECE', 26.0)):.1f}"
                              f"*({beat_pulse_expr})")
        if getattr(config, 'SHORTS_BEAT_PAN_AKTIF', True):
            _pan_px = float(getattr(config, 'SHORTS_BEAT_PAN_PIXEL', 14.0))
            beat_pan_extra = (f"+{_pan_px:.1f}*({beat_pulse_expr})"
                              f"*{_pan_px * 0.6:.1f}")

    pan_x = f"{pan_x_range:.1f}+{pan_x_range:.1f}*sin(t*{config.BACKDROP_PAN_SPEED_X})+{pan_x_range * 0.25:.1f}*sin(t*{2 * nabiz_w_s:.6f}){beat_pan_extra}"
    pan_y = f"{pan_y_range:.1f}+{pan_y_range:.1f}*cos(t*{config.BACKDROP_PAN_SPEED_Y})"
    hue_shift = f"{config.BACKDROP_HUE_AMPLITUDE_DEG}*sin(t*{config.BACKDROP_HUE_SPEED})*(1+{nabiz_guc_s:.2f}*{nabiz_pulse_s}){beat_hue_extra}"

    # --- BEAT ZOOM PUNCH (YouTube "cut on beat" görünümü) -----------------
    # NEDEN scale+crop: `crop`'un w/h ifadesi FFmpeg 9'da PER-FRAME
    # değerlendirilmiyor (sadece init'te). `scale` ise `eval=frame`
    # destekliyor: kare başına farklı boyuta ölçekler. Çıktıyı SABİT
    # tutmak için scale'dan sonra SABİT crop geliyor (merkezi alır).
    # Sonuç: beat'te "punch" (zoom into) — gerçek bir kes hissi.
    #
    # NEDEN zoompan DEĞİL: zoompan zinciri yeniden yazıyor ve repoda
    # daha önce sorun çıkarmıştı (bkz. DJ sahne zoom yorum satırı).
    beat_zoom_expr = ""
    if (getattr(config, 'SHORTS_BEAT_SYNC_AKTIF', True)
            and getattr(config, 'SHORTS_BEAT_ZOOM_AKTIF', True)
            and beat_pulse_expr != "0"):
        _zoom_yuzde = float(getattr(config, 'SHORTS_BEAT_ZOOM_YUZDE', 8.0))
        if _zoom_yuzde > 0:
            beat_zoom_expr = (
                f",scale=w='{width}*(1+{_zoom_yuzde / 100:.4f}*({beat_pulse_expr}))'"
                f":h='{height}*(1+{_zoom_yuzde / 100:.4f}*({beat_pulse_expr}))'"
                f":eval=frame:flags=bicubic,crop={width}:{height}"
            )

    canvas = (
        f"{base_input}fps={fps},crop={width}:{height}:x='{pan_x}':y='{pan_y}'"
        f"{beat_zoom_expr},"
        f"hue=h='{hue_shift}'[canvas]"
    )

    parts = [canvas]
    pre_label = "canvas"

    # Hook metni (ilk DIKEY_HOOK_SURE_SN saniye, üst kısım)
    hook_text = getattr(config, "DIKEY_HOOK_METNI", "🔊 Sesini Aç")
    hook_duration = getattr(config, "DIKEY_HOOK_SURE_SN", 2.5)
    hook_y_ratio = 0.12
    hook_fs_ratio = 0.045
    hook_escaped = _escape_drawtext(hook_text)
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    hook_fs = int(height * hook_fs_ratio)
    hook_y = int(height * hook_y_ratio)

    parts.append(
        f"color=c=black@0.0:s={width}x{int(height*0.15)}:d={hook_duration:.3f}:rate={fps},format=rgba,"
        f"drawtext=fontfile={rel_font}:text='{hook_escaped}':"
        f"fontcolor=white@0.95:fontsize={hook_fs}:"
        f"shadowcolor=black@0.8:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2:y=(h-text_h)/2[hook_strip]"
    )
    parts.append(
        f"[{pre_label}][hook_strip]overlay=0:{hook_y}:enable='between(t,0,{hook_duration:.3f})'[vhook]"
    )
    pre_label = "vhook"

    # Lower third (alt 1/3) — şarkı adı + sanatçı
    if title:
        lt_h = int(height * 0.33)  # alt 1/3
        lt_y = height - lt_h
        lt_bg_alpha = 0.6
        title_fs = int(height * 0.035)
        artist_fs = int(height * 0.028)
        title_y = lt_y + int(lt_h * 0.25)
        artist_y = title_y + int(title_fs * 1.4)

        title_escaped = _escape_drawtext(title)
        artist = "DJ Famous" if theme_key == "dj" else config.STATIC_LABEL_TEXT
        artist_escaped = _escape_drawtext(artist)

        parts.append(
            f"color=c=black@{lt_bg_alpha}:s={width}x{lt_h}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font}:text='{title_escaped}':"
            f"fontcolor=white:fontsize={title_fs}:"
            f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y={title_y},"
            f"drawtext=fontfile={rel_font}:text='{artist_escaped}':"
            f"fontcolor=white@0.8:fontsize={artist_fs}:"
            f"shadowcolor=black@0.6:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y={artist_y}[lt_strip]"
        )
        parts.append(f"[{pre_label}][lt_strip]overlay=0:{lt_y}[vlt]")
        pre_label = "vlt"

    # HASHTAG OVERLAY (Shorts için) — Title Case + Mavi renk
    # hashtags parametresi: ['#keşfet', '#fyp', '#viral'] formatında liste
    if hashtags:
        # Title Case'e çevir: #keşfet -> #Keşfet
        formatted_tags = [_format_hashtag_titlecase(tag) for tag in hashtags]
        hashtag_text = " " + " ".join(formatted_tags)
        hashtag_escaped = _escape_drawtext(hashtag_text)
        
        # Hashtag konumu: lower third'in üstünde, ortalanmış
        ht_fs = int(height * 0.025)
        ht_y = lt_y - int(ht_fs * 1.8)  # lower third'in biraz üstünde
        
        parts.append(
            f"color=c=black@0.0:s={width}x{int(ht_fs * 2)}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font}:text='{hashtag_escaped}':"
            f"fontcolor=0x00BFFF@0.95:fontsize={ht_fs}:"  # Mavi (Deep Sky Blue)
            f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[ht_strip]"
        )
        parts.append(
            f"[{pre_label}][ht_strip]overlay=0:{ht_y}[vht]"
        )
        pre_label = "vht"

    # BÜYÜME CTA (madde 11): videonun %40'ında 1 kez, kısa süre, emir kipi yok —
    # rutin vaat eder ("Her Cuma yeni şehir"). cta_text verilmezse çizilmez.
    if cta_text:
        cta_oran = float(getattr(config, 'ABONE_CTA_ORAN', 0.4))
        cta_sure = float(getattr(config, 'ABONE_CTA_SURE_SN', 4.0))
        cta_start = duration * cta_oran
        cta_end = min(duration, cta_start + cta_sure)
        cta_fs = int(height * 0.022)
        cta_y = int(height * 0.78)
        cta_escaped = _escape_drawtext(cta_text)
        rel_font_cta = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
        parts.append(
            f"color=c=black@0.0:s={width}x{int(cta_fs * 1.6)}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font_cta}:text='{cta_escaped}':"
            f"fontcolor=white@0.9:fontsize={cta_fs}:"
            f"shadowcolor=black@0.7:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[cta_strip]"
        )
        parts.append(
            f"[{pre_label}][cta_strip]overlay=0:{cta_y}:enable='between(t,{cta_start:.3f},{cta_end:.3f})'[vcta]"
        )
        pre_label = "vcta"

    # BİTİŞ KARTI (madde 10): son END_CARD_SURE_SN saniyede sonraki içerik —
    # end_card_text meta'dan gelir (yoksa çizilmez, oynatma listesinde tutma).
    if end_card_text:
        end_sure = float(getattr(config, 'END_CARD_SURE_SN', 15.0))
        end_start = max(0.0, duration - end_sure)
        end_fs = int(height * 0.028)
        end_y = int(height * 0.12)
        end_escaped = _escape_drawtext(end_card_text)
        rel_font_end = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
        parts.append(
            f"color=c=black@0.55:s={width}x{int(end_fs * 2.2)}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font_end}:text='{end_escaped}':"
            f"fontcolor=white:fontsize={end_fs}:"
            f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y=(h-text_h)/2[end_strip]"
        )
        parts.append(
            f"[{pre_label}][end_strip]overlay=0:{end_y}:enable='gte(t,{end_start:.3f})'[vend]"
        )
        pre_label = "vend"

    # BEAT FLASH (YouTube "Beat sync" efekti) — her beat'te kısa parlaklık.
    # NEDEN TEK overlay: 30sn'de ~70 beat var; her beat için ayrı filtre
    # filter_complex'i patlatırdı. `enable` ifadesi beat'lerin toplamıdır
    # (o anda en az bir beat penceresi açıksa >0 = truthy).
    if (getattr(config, 'SHORTS_BEAT_SYNC_AKTIF', True)
            and getattr(config, 'SHORTS_BEAT_FLASH_AKTIF', True)
            and beat_times):
        import beat_sync as _bs
        _flash_sure = float(getattr(config, 'SHORTS_BEAT_FLASH_SURE_SN', 0.11))
        _enable = _bs.flash_enable_ifadesi(beat_times, _flash_sure)
        if _enable != "0":
            _flash_alfa = float(getattr(config, 'SHORTS_BEAT_FLASH_ALFA', 0.14))
            parts.append(
                f"color=c=white@{_flash_alfa}:s={width}x{height}:"
                f"d={duration:.3f}:rate={fps},format=rgba[flash_strip]"
            )
            parts.append(
                f"[{pre_label}][flash_strip]overlay=0:0:"
                f"enable='{_enable}'[vflash]"
            )
            pre_label = "vflash"

    # İlerleme çubuğu (ince, alt)
    bar_margin = int(width * config.PROGRESS_BAR_MARGIN_RATIO)
    bar_w = width - 2 * bar_margin
    pbar_h = max(2, int(height * config.PROGRESS_BAR_HEIGHT_RATIO))
    bar_y = height - int(height * config.PROGRESS_BAR_BOTTOM_RATIO) - pbar_h - 10
    filled, empty = config.PROGRESS_BAR_FILLED, config.PROGRESS_BAR_EMPTY
    bar_expr = f"{empty}+{filled - empty}*lt(X\\,W*T/{duration:.3f})"
    parts.append(f"color=c=black:s={bar_w}x{pbar_h}:d={duration:.3f}:rate={fps}[barbg]")
    parts.append(f"[barbg]geq=r='{bar_expr}':g='{bar_expr}':b='{bar_expr}'[bar]")
    parts.append(f"[{pre_label}][bar]overlay={bar_margin}:{bar_y}[vfinal]")

    return ";".join(parts)


def render_video(
    art_path: str | None,
    audio_path: str,
    output_path: str,
    width: int,
    height: int,
    title: str | None = None,
    theme: str | None = None,
    start_time: float | None = None,
    end_time: float | None = None,
    marquee_override: str | None = None,
    chapters_file: str | None = None,
    is_shorts: bool = False,
    cold_open: tuple[float, float, float] | None = None,
    end_card_text: str | None = None,
    cta_text: str | None = None,
    is_dj_set: bool = False,
    hashtags: list | None = None,
    beat_times: list | None = None,
    beat_period: float = 0.0,
    speed_ramp: dict | None = None,
    ses_limiter: bool = False,
) -> None:
    """start_time/end_time verilirse (saniye), sesin/videonun sadece o aralığı
    kullanılır — kısa (Shorts/Reels/TikTok) "highlight" kırpması için.
    marquee_override verilmezse kayan yazı title + tema/tür etiketlerinden
    oluşur (ana katalog); verilirse (ör. DJ Famous için "DJ Famous  •  Hafta 1
    Seti  •  #DJFamous ...") kayan yazı olarak AYNEN kullanılır — sabit alt
    satır ("Famous Music Studio") HER ZAMAN aynı kalır, bundan etkilenmez.
    chapters_file verilirse (chapters.ffmeta), YouTube chapter metadata olarak gömülür.
    is_shorts=True ise Shorts 9:16 native filter kullanılır (tam ekran art + lower third).
    cold_open=(high_start, high_end, preview_sn) ise sesin başına highlight'tan
    kısa bir "ön tat" eklenir (concat: önce zirve, sonra tam şarkı) — video
    süresi de o kadar uzar; chapter dosyası render.py tarafında ötelenir.
    end_card_text/cta_text verilirse ilgili overlay'ler çizilir (yoksa çizilmez).
    beat_times/beat_period verilirse Shorts BEAT SYNC efekti uygulanır
    (YouTube "Beat sync" karşılığı: görseller ritme kilitlenir).
    speed_ramp verilirse YouTube "speed ramp" efekti uygulanır (yavaş
    başla, beat'te hızlan) — video ve ses aynı zaman eşlemesini kullanır.
    AI beyanı videoya YAKILMAZ — sadece YouTube metadata/açıklamasında.
    ses_limiter=True ise true-peak limiter zinciri eklenir (AAC 192k sonrası
    taşan tepe koruması). Varsayılan KAPALI: mevcut tüm çağıranların komutu
    BİREBİR aynı kalır."""
    full_duration = get_audio_duration(audio_path)
    if start_time is not None and end_time is not None:
        duration = min(end_time, full_duration) - start_time
    else:
        duration = full_duration
    preview_dur = 0.0
    if cold_open is not None and start_time is None and end_time is None:
        high_start, high_end, preview_sn = cold_open
        preview_dur = max(0.0, min(preview_sn, high_end - high_start, full_duration))
        duration = full_duration + preview_dur
    theme_key = get_theme_key(theme)
    has_art = bool(art_path)
    canvas_path = ensure_art_backdrop(art_path, width, height) if has_art else ensure_vignette(width, height, theme_key)

    # Build base filter complex (Shorts or normal)
    # --- HIZ RAMPASI (YouTube efekti) --------------------------------------
    # NEDEN burada: video zinciri (canvas) ve ses zinciri AYNI zaman
    # eşlemesini paylaşmalı, yoksa a/v kayması olur. İkisi de aynı
    # plan dict'ini kullanır.
    ramp_video = ""
    ramp_audio = ""
    base_input = "[1:v]" if is_shorts else "[2:v]"
    if is_shorts and speed_ramp:
        ramp_video, base_label = _build_speed_ramp_video(
            base_input, speed_ramp, duration)
        base_input = f"[{base_label}]"
    if is_shorts:
        # Shorts 9:16 native filter — kart yok, mask yok
        filter_complex = _build_shorts_filter_complex(width, height, duration, title, has_art, theme_key, marquee_override,
                                                      end_card_text=end_card_text, cta_text=cta_text, hashtags=hashtags,
                                                      beat_times=beat_times, beat_period=beat_period,
                                                      base_input=base_input)
        pre_label = "vfinal"  # _build_shorts_filter_complex returns filter ending with [vfinal]
    else:
        # Normal 16:9 filter with card
        mask_path = ensure_card_mask()
        filter_complex = _build_filter_complex(width, height, duration, title, has_art, theme_key, marquee_override, end_card_text=end_card_text, cta_text=cta_text)
        pre_label = "vfinal"  # _build_filter_complex returns filter ending with [vfinal]
    
    # DJ Sahne Modu efektleri (DJ setler için) — hem Shorts hem normal için
    if is_dj_set:
        # DJ HUD Nefes efekti
        if getattr(config, 'DJ_HUD_NEFES', True):
            nefes_sure = getattr(config, 'DJ_HUD_NEFES_SURE_SN', 8.0)
            filter_complex += (
                f";color=c=white@0.0:s={width}x{int(height*0.15)}:d={duration:.3f}:rate={config.FPS},format=rgba,"
                f"drawtext=fontfile={os.path.relpath(config.FONT_PATH, os.getcwd()).replace(chr(92), chr(47))}:text='🫁':"
                f"fontcolor=white@0.9:fontsize={int(height*0.05)}:"
                f"shadowcolor=black@0.8:shadowx=2:shadowy=2:"
                f"x=(w-tw)/2:y={int(height*0.05)}[hud];"
                f"[{pre_label}][hud]overlay=0:0:enable='between(t,0,{getattr(config, 'DJ_HUD_NEFES_SURE_SN', 8.0):.1f})'[hud]"  
            )
            pre_label = "hud"
        
        # DJ Sahne Zoom efekti - geçici devre dışı (zoompan filtresi sorunu)
        # if getattr(config, 'DJ_SAHNE_ZOOM', True):
        #     zoom_bitis = getattr(config, 'DJ_SAHNE_ZOOM_BITIS', 1.08)
        #     zoom_expr = f"zoompan=z='if(lte(t,{duration}),1+({zoom_bitis}-1)*t/{duration},1)':d={duration}:s={width}x{height}"
        #     filter_complex += f";[{pre_label}]zoompan={zoom_expr}[zoom]" 
        #     pre_label = "zoom"
        
        # DJ Sahne Blur efekti
        if getattr(config, 'DJ_SAHNE_BLUR_SIGMA', 0) > 0:
            blur_sigma = getattr(config, 'DJ_SAHNE_BLUR_SIGMA', 1.5)
            filter_complex += f";[{pre_label}]gblur=sigma={blur_sigma}[blur]"
            pre_label = "blur"
    
    # Ensure final output is vfinal
    if pre_label != "vfinal":
        filter_complex += f";[{pre_label}]copy[vfinal]"
        pre_label = "vfinal"

    
    audio_input = ["-ss", f"{start_time:.3f}"] if start_time is not None else []
    cmd = [
        "ffmpeg", "-y",
        *audio_input, "-i", audio_path,
    ]
    
    if is_shorts:
        cmd += [
            "-loop", "1", "-i", canvas_path,
        ]
    else:
        cmd += [
            "-loop", "1", "-i", mask_path,
            "-loop", "1", "-i", canvas_path,
        ]
    if has_art:
        cmd += ["-loop", "1", "-i", art_path]

    if preview_dur > 0.0 and cold_open is not None:
        high_start, high_end, _preview_sn = cold_open
        filter_complex += (
            f";[0:a]asplit=2[afull][ahigh]"
            f";[ahigh]atrim=start={high_start:.3f}:end={high_end:.3f},asetpts=PTS-STARTPTS,atrim=0:{preview_dur:.3f}[cold]"
            f";[cold][afull]concat=n=2:v=0:a=1[aout]"
        )
        audio_map = "[aout]"
    else:
        audio_map = "0:a"

    # --- HIZ RAMPASI: ses zinciri (videoyla aynı zaman eşlemesi) ---------
    # NEDEN ses de warp ediliyor: video yavaşladığında ses de yavaşlamazsa
    # konuşma/melodi ile görsel uyumsuzlaşır (a/v kayması).
    #
    # NEDEN audio_map üzerinden: cold-open varsa ses zinciri [aout] ile
    # biter; ramp ONDAN sonra uygulanmalı (cold-open da yavaşlasın).
    if speed_ramp and is_shorts:
        ramp_audio, audio_label = _build_speed_ramp_audio(
            audio_map, speed_ramp, duration)
        filter_complex += ";" + ramp_audio
        audio_map = f"[{audio_label}]"
    if ramp_video:
        filter_complex = ramp_video + ";" + filter_complex

    if chapters_file and os.path.isfile(chapters_file):
        cmd += ["-i", chapters_file]
    # --- TRUE PEAK LIMITER (2026-10-21) ----------------------------------
    # NEDEN burada: limiter zinciri SES zincirinin SONUNA eklenir. Ses
    # filter_complex'te DEĞİLSE (audio_map == "0:a") doğrudan `-af` olarak
    # verilir; filter_complex'te ses varsa (cold-open / speed ramp) `-af`
    # ÇAKIŞIR ("Filtergraph ... both -filter_complex and -af") — o durumda
    # limiter ses zincirinin sonuna filter_complex içinde eklenir.
    limiter = limiter_filtresi() if ses_limiter else None
    if limiter and audio_map == "0:a":
        cmd_extra_audio = ["-af", limiter]
        audio_map = "0:a"
    elif limiter:
        filter_complex += ";[%s]%s[alim]" % (
            audio_map.strip("[]"), limiter)
        audio_map = "[alim]"
    else:
        cmd_extra_audio = []

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", audio_map,
        "-t", f"{duration:.3f}",
        "-c:v", config.VIDEO_CODEC,
        "-preset", config.PRESET,
        "-crf", config.CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", config.AUDIO_CODEC,
        "-b:a", config.AUDIO_BITRATE,
        "-shortest",
    ]
    if cmd_extra_audio:
        # `-af` çıktı zincirine aittir: kodlayıcı seçeneklerinden SONRA,
        # dosya adından ÖNCE gelmeli.
        idx = cmd.index("-shortest")
        cmd = cmd[:idx] + cmd_extra_audio + cmd[idx:]
    if chapters_file and os.path.isfile(chapters_file):
        # Find the chapters input index
        if is_shorts:
            # inputs: 0=audio, 1=canvas, 2=chapters
            chapters_idx = 2
        else:
            # inputs: 0=audio, 1=mask, 2=canvas, 3=art (if has_art), 4/3=chapters
            chapters_idx = 4 if has_art else 3
        cmd += ["-map_metadata", f"{chapters_idx}", "-map_chapters", f"{chapters_idx}"]
    cmd.append(output_path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render hatası ({output_path}):\n{result.stderr[-2000:]}")
