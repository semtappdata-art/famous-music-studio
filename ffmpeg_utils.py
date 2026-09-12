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

AÇILIŞ (2026-09-11 eklendi): uzun formatta video bu kompozisyonla DEĞİL, projenin
cover.png'siyle (birebir YouTube küçük resmi) tam ekran başlıyor ve ~2,4 saniyede
karta çözülüyor; ayrıca sesin başındaki dijital sessizlik kırpılıyor. Gerekçe ve
ölçüm config.INTRO_KAPAK / config.INTRO_SESSIZLIK_KIRP yorumlarında.
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
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe süre okuyamadı: {result.stderr.strip()}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"ffprobe geçersiz süre döndürdü: {result.stdout!r}")


def bastaki_sessizlik(audio_path: str) -> float:
    """Ses dosyasının BAŞINDAKİ dijital sessizliğin süresini (saniye) döndürür.

    NEDEN: Suno çıktıları başta sessizlikle geliyor (18 projede ölçüldü: 0,15-2,65
    sn, medyan ~1,1 sn). Render bunu aynen kopyaladığı için video ilk saniyesinde
    hem donmuş hem sessiz başlıyordu. Bulunamazsa / ffmpeg hata verirse 0.0 döner
    (kırpma yapılmaz) — bu fonksiyonun bir arızası şarkıyı ASLA kesmemeli.
    Dönen değer config.INTRO_SESSIZLIK_MAKS ile tavanlanmıştır."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", audio_path,
        "-af", f"silencedetect=noise={config.INTRO_SESSIZLIK_ESIGI}:d=0.05",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return 0.0
    if result.returncode != 0:
        return 0.0

    # silencedetect stderr'e şu çiftleri basar:
    #   silence_start: 0
    #   silence_end: 1.10525 | silence_duration: 1.10525
    # Bizi SADECE 0'dan (ya da ona çok yakından) başlayan ilk blok ilgilendiriyor;
    # şarkının ortasındaki duraklamalar kırpılacak bir şey değil.
    basta = False
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].split("|")[0].strip())
            except (ValueError, IndexError):
                return 0.0
            if start > 0.05:
                return 0.0  # ilk sessizlik başta değil → kırpacak bir şey yok
            basta = True
        elif basta and "silence_end:" in line:
            try:
                end = float(line.split("silence_end:")[1].split("|")[0].strip())
            except (ValueError, IndexError):
                return 0.0
            kirp = end - config.INTRO_SESSIZLIK_PAY
            return max(0.0, min(kirp, config.INTRO_SESSIZLIK_MAKS))
    return 0.0


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
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
            # Eskiden sabit eq=brightness=-0.12 kullanılıyordu — bu, koyu/gece
            # temalı art.jpg'lerde (Pexels stok fotoğrafları çoğunlukla gece/
            # yağmur/atmosfer imgeleri, bkz. stock_art.py) güçlü blur'la
            # birleşince arka planı neredeyse tamamen siyaha çöktürüyordu
            # (kullanıcı geri bildirimi: "kapak arkası çok koyu oluyor").
            # Artık pozitif bir brightness + siyahları belirgin şekilde
            # kaldıran bir curves eğrisi kullanılıyor — arka plan kasıtlı
            # olarak KARTIN kendisinden (art.jpg, ham hâli) daha AÇIK tonda
            # duruyor (kullanıcı isteği: "arka fon kapaktan açık tonda olsun")
            # — kart öne çıkıyor, arka plan geride/loş bir hale bürünüyor.
            f"eq=brightness=0.08:saturation=1.2,curves=all='0/0.12 0.5/0.68 1/1'"
        ),
        "-frames:v", "1", "-update", "1",
        backdrop_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
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
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Arka plan üretilemedi: {result.stderr[-1000:]}")
    return path




def _build_filter_complex(
    width: int, height: int, duration: float, title: str | None, has_art: bool,
    theme_key: str, marquee_override: str | None = None,
    backdrop_video: bool = False,
    hud_index: int | None = None,
    kart_goster: bool = True,
    intro_index: int | None = None,
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

    if kart_goster:
        marquee_y = card_y + card_size + bar_thick + marquee_gap
        label_y = marquee_y + marquee_strip_h + label_gap
    else:
        # Kart yokken yazılar dikey ortada asılı kalırdı; sahne modunda
        # alt şeride iniyorlar - kadrajın ortası görüntüye bırakılıyor.
        label_y = height - int(height * 0.085)
        marquee_y = label_y - label_gap - marquee_strip_h

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
    pan_x_range = (bg_pan_w - width) / 2
    pan_y_range = (bg_pan_h - height) / 2
    pan_x = f"{pan_x_range:.1f}+{pan_x_range:.1f}*sin(t*{config.BACKDROP_PAN_SPEED_X})"
    pan_y = f"{pan_y_range:.1f}+{pan_y_range:.1f}*cos(t*{config.BACKDROP_PAN_SPEED_Y})"
    hue_shift = f"{config.BACKDROP_HUE_AMPLITUDE_DEG}*sin(t*{config.BACKDROP_HUE_SPEED})"
    if backdrop_video:
        # DJ setlerinde arka plan statik bir PNG değil, stok kliplerden kurulmuş
        # gerçek bir video (bkz. stock_video.arka_plan_kur). Kendi hareketi
        # olduğu için pan/hue UYGULANMIYOR: üstüne bir de kayan crop penceresi
        # ve ton salınımı eklemek görüntüyü yorucu hale getiriyor. Video
        # _panned_size kadar büyük de değil (1920x1080), o yüzden crop yerine
        # scale+crop ile hedef çerçeveye oturtuluyor.
        # Bulanıklık ve siyah kaldırma BURADA DEĞİL, backdrop.mp4 üretilirken
        # bir kez uygulanıyor (stock_video.arka_plan_kur). Sebep: gblur her
        # karede çalışıyor ve 80 dakikalık bir sette render'a ~%30 ekliyordu;
        # arka plan zaten tek seferlik bir dosya, orada pişirmek bedava.
        canvas = (
            f"[2:v]fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1[canvas]"
        )
    else:
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

    if kart_goster:
        parts = [
            canvas, card_raw, mask_scaled, card,
            f"[canvas][card]overlay={card_x}:{card_y}[bg2]",
        ]
        pre_label = "bg2"
    else:
        # SAHNE MODU: kart yok, görüntünün kendisi kadraj (config.DJ_SAHNE_MODU).
        # card_raw/mask zinciri hiç kurulmuyor - kurulup gizlenseydi her karede
        # boşuna ölçeklenip alphamerge edilirdi.
        parts = [canvas]
        pre_label = "canvas"

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
        # Yazi golgesi SADECE video arka planda. Sabit gorsel arka plan her
        # zaman koyu (kaynak art.jpg koyu bir kapak) ve beyaz yazi orada zaten
        # net okunuyor - oraya golge eklemek gereksiz bir gorsel degisiklik
        # olurdu. Video havuzunda ise parlak klipler var (altin bokeh, gun
        # batimi) ve white@0.95 yazi onlarin uzerinde kayboluyordu; egrinin
        # tepesini bastirmak yetmedi cunku sorun arka planin parlakligi degil,
        # yazi ile zemin arasinda kontrast olmamasi.
        golge = (f":shadowcolor={config.FONT_SHADOW_COLOR}"
                 f":shadowx={config.FONT_SHADOW_OFFSET}"
                 f":shadowy={config.FONT_SHADOW_OFFSET}") if backdrop_video else ""

        label_width_est = int(len(config.STATIC_LABEL_TEXT) * label_fontsize * config.FONT_CHAR_WIDTH_RATIO)
        marquee_w = min(card_size, max(1, label_width_est))
        marquee_x = card_x + (card_size - marquee_w) // 2

        parts.append(
            f"color=c=black@0.0:s={marquee_w}x{marquee_strip_h}:d={duration:.3f}:rate={fps},format=rgba,"
            f"drawtext=fontfile={rel_font}:text='{marquee_text}':"
            f"fontcolor={config.FONT_COLOR}:fontsize={fontsize}{golge}:"
            f"x='w-mod(t*{speed}\\,(w+text_w))':y=0[marquee_strip]"
        )
        parts.append(f"[{pre_label}][marquee_strip]overlay={marquee_x}:{marquee_y}[bgm]")
        pre_label = "bgm"

        # Sabit marka satırı: künye yazısıyla AYNI font ve AYNI düz beyaz renk —
        # tek tip, tutarlı bir yazı görünümü için renk animasyonu YOK.
        label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
        parts.append(
            f"[{pre_label}]drawtext=fontfile={rel_font}:text='{label_escaped}':"
            f"fontcolor={config.FONT_COLOR}:fontsize={label_fontsize}{golge}:"
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
    # Açılış katmanı varsa nihai çıktı bir adım sonra kuruluyor; kompozisyon
    # buraya kadar [vpre] olarak toplanıyor.
    son_etiket = "vpre" if intro_index is not None else "vfinal"
    if hud_index is None:
        parts.append(f"[{pre_label}][bar]overlay={bar_margin}:{bar_y}[{son_etiket}]")
    else:
        parts.append(f"[{pre_label}][bar]overlay={bar_margin}:{bar_y}[vbar]")
        # HUD opak SİYAH üzerine çizilmiş bir PNG (bkz. dj_hud modül notu:
        # drawbox şeffaf zeminde alfaya yazmıyor). `screen` modunda siyah
        # hiçbir şey katmıyor, parlak çizgiler ekleniyor — hem şeffaflık
        # sorununu çözüyor hem HUD'a parıltı veriyor.
        # blend RGB uzayında çalışmalı: yuv420p'de kanal başına harmanlama
        # renk kaymasına yol açıyor, o yüzden gbrp'ye geçip geri dönülüyor.
        parts.append(f"[vbar]format=gbrp[vb_rgb]")
        parts.append(f"[{hud_index}:v]scale={width}:{height},format=gbrp[hud_rgb]")
        parts.append(
            f"[vb_rgb][hud_rgb]blend=all_mode=screen,format=yuv420p[{son_etiket}]")

    if intro_index is not None:
        # AÇILIŞ: projenin kendi cover.png'si (birebir YouTube küçük resmi) tam
        # ekran, sonra karta çözülüyor. Gerekçe config.INTRO_KAPAK'ta yazılı.
        # `trim` ŞART: girdi `-loop 1` ile sonsuz bir akış; çözülme bittikten
        # sonra dalın bitmesi lazım — `eof_action=pass` sayesinde ondan sonrası
        # ana akış olarak devam ediyor ve kalan dakikalarda bu katman için
        # tek bir kare bile işlenmiyor (render maliyeti ~sıfır).
        toplam = config.INTRO_KAPAK_BEKLEME + config.INTRO_KAPAK_COZULME
        parts.append(
            f"[{intro_index}:v]fps={fps},"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=rgba,"
            f"trim=0:{toplam:.3f},setpts=PTS-STARTPTS,"
            f"fade=t=out:st={config.INTRO_KAPAK_BEKLEME:.3f}:"
            f"d={config.INTRO_KAPAK_COZULME:.3f}:alpha=1[intro]"
        )
        parts.append(f"[{son_etiket}][intro]overlay=0:0:eof_action=pass[vfinal]")

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
    backdrop_video: str | None = None,
    hud_path: str | None = None,
    kart_goster: bool = True,
    intro_cover: str | None = None,
) -> None:
    """start_time/end_time verilirse (saniye), sesin/videonun sadece o aralığı
    kullanılır — kısa (Shorts/Reels/TikTok) "highlight" kırpması için.
    marquee_override verilmezse kayan yazı title + tema/tür etiketlerinden
    oluşur (ana katalog); verilirse (ör. DJ Famous için "DJ Famous  •  Hafta 1
    Seti  •  #DJFamous ...") kayan yazı olarak AYNEN kullanılır — sabit alt
    satır ("Famous Music Studio") HER ZAMAN aynı kalır, bundan etkilenmez.
    backdrop_video verilirse arka plan bulanık art.jpg yerine O VİDEO olur
    (`-stream_loop -1` ile süre boyunca döngüye alınır); kart, künye ve marka
    satırı aynen üstünde kalır. Uzun DJ setlerinde tek bir sabit görselin
    sıkıcı olmaması için — kısa formatlarda kullanılmıyor.
    intro_cover verilirse video AÇILIŞTA o görselle (projenin cover.png'si, yani
    birebir YouTube küçük resmi) tam ekran başlayıp karta çözülür — gerekçesi ve
    süreleri config.INTRO_KAPAK'ta. Çok kısa parçalarda (süre < 2× açılış)
    kendiliğinden atlanır."""
    full_duration = get_audio_duration(audio_path)
    if start_time is not None and end_time is not None:
        duration = min(end_time, full_duration) - start_time
    else:
        # Baştaki dijital sessizliği kırp (bkz. config.INTRO_SESSIZLIK_KIRP):
        # ilk saniyede ekran zaten donuk, bir de ses yoksa o saniye tamamen boş
        # geçiyor. Shorts bu yola HİÇ girmiyor — orada start_time/end_time zaten
        # highlight kırpmasından geliyor.
        if config.INTRO_SESSIZLIK_KIRP and start_time is None:
            kirpilan = bastaki_sessizlik(audio_path)
            if kirpilan > 0:
                start_time = kirpilan
        duration = full_duration - (start_time or 0.0)
    theme_key = get_theme_key(theme)
    mask_path = ensure_card_mask()
    has_art = bool(art_path)
    use_backdrop_video = bool(backdrop_video) and os.path.isfile(backdrop_video)
    if use_backdrop_video:
        canvas_path = backdrop_video
    else:
        canvas_path = ensure_art_backdrop(art_path, width, height) if has_art else ensure_vignette(width, height, theme_key)
    # Sahne modunda art.jpg hiç OKUNMUYOR: kart çizilmiyor, arka plan da
    # videodan geliyor. Girdiyi açık bırakmak HUD'un indeksini kaydırırdı.
    if not kart_goster:
        has_art = False
    use_hud = bool(hud_path) and os.path.isfile(hud_path)
    # HUD girdi indeksi: 0=ses, 1=maske, 2=tuval, (3=art varsa). Sıra
    # aşağıdaki cmd kurulumuyla BİREBİR aynı olmalı - yanlış indeks sessizce
    # yanlış akışı harmanlar.
    hud_index = (4 if has_art else 3) if use_hud else None
    # Açılış kapağı girdisi EN SONA ekleniyor — araya girseydi hud_index'i
    # kaydırırdı (yukarıdaki nota bak: yanlış indeks sessizce yanlış akışı harmanlar).
    # Çok kısa parçalarda açılış atlanıyor: 2,4 saniyelik bir kapak, 6 saniyelik
    # bir videonun yarısı demek olurdu (testlerde/sentetik seslerde olan tam bu).
    intro_toplam = config.INTRO_KAPAK_BEKLEME + config.INTRO_KAPAK_COZULME
    use_intro = (
        config.INTRO_KAPAK
        and bool(intro_cover)
        and os.path.isfile(intro_cover)
        and duration >= intro_toplam * 2
    )
    if use_intro:
        intro_index = (hud_index + 1) if hud_index is not None else (4 if has_art else 3)
    else:
        intro_index = None
    filter_complex = _build_filter_complex(width, height, duration, title, has_art, theme_key,
                                           marquee_override, use_backdrop_video, hud_index,
                                           kart_goster, intro_index)

    audio_input = ["-ss", f"{start_time:.3f}"] if start_time is not None else []
    cmd = [
        "ffmpeg", "-y",
        *audio_input, "-i", audio_path,
        "-loop", "1", "-i", mask_path,
    ]
    # Sabit PNG için `-loop 1`, video arka plan için `-stream_loop -1`:
    # ikincisi dosyayı baştan sona tekrar tekrar çalar, `-t` ile setin süresine
    # kırpılır. `-loop 1` bir videoda ilk kareyi dondururdu (asıl tuzak bu).
    if use_backdrop_video:
        cmd += ["-stream_loop", "-1", "-i", canvas_path]
    else:
        cmd += ["-loop", "1", "-i", canvas_path]
    if has_art:
        cmd += ["-loop", "1", "-i", art_path]
    if use_hud:
        cmd += ["-loop", "1", "-i", hud_path]
    if use_intro:
        cmd += ["-loop", "1", "-i", intro_cover]
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

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render hatası ({output_path}):\n{result.stderr[-2000:]}")
