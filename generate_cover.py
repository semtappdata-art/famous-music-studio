"""meta.json'daki title + theme'e göre otomatik cover.png (başlıklı, platform
thumbnail'i) ve art.png (metinsiz, video kartı + arka plan blur kaynağı) üretir.

Proje bilinçli olarak sadece ffmpeg kullanıyor (Pillow/Playwright gibi ek bir
görsel işleme bağımlılığı eklemiyor) — tema rengine göre radial gradyan arka
plan + şarkı başlığından türetilen deterministik bokeh dokusu + (cover.png
için) ortalanmış başlık metni.

meta.json'da bir "character" alanı varsa (bkz. karakter_roster.md) ve
characters/<karakter-slug>.jpg|jpeg|png dosyası mevcutsa, arka plan kaynağı
olarak o karakterin hazır portresi kullanılır (procedural gradyan yerine) —
art.png bu portrenin AYNISI (metinsiz), cover.png ise üstüne başlık metni
eklenmiş hâli olur. Dosya henüz yoksa (karakter roster'da olup portre daha
hazırlanmamışsa) sessizce procedural gradyana düşülür.

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
import re
import shutil
import subprocess

import config
import stock_art

CANVAS_SIZE = 1600  # art.png (video kartı + backdrop kaynağı) — HER ZAMAN kare, video pipeline'ı bunu varsayıyor
COVER_SIZE_WIDE = (1600, 900)  # cover.png — YouTube uzun-format thumbnail'i (16:9)
COVER_SIZE_TALL = (900, 1600)  # cover_vertical.png — Shorts/TikTok/Instagram kapağı (9:16)
CHARACTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")
# config.LOGO_PATH kaydı düz siyah zemin üzerine koyu/mat bir altın tonuyla
# kaydedilmiş — kapaklarda daha canlı görünsün diye colorkey'den SONRA
# uygulanan bir parlaklık/doygunluk düzeltmesi (kullanıcı geri bildirimiyle
# eklendi, "altın daha parlak olsun").
LOGO_BRIGHTEN_FILTER = "eq=brightness=0.10:saturation=1.9:contrast=1.15,curves=r='0/0 0.5/0.65 1/1':g='0/0 0.5/0.55 1/1'"
_TR_TRANSLATE = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")


def _slugify(name: str) -> str:
    """'Kerem Ateşi' -> 'kerem-atesi' — characters/ klasöründeki portre dosya
    adlarıyla eşleşsin diye (karakter_roster.md'deki isimlerle aynı kurala göre)."""
    ascii_name = name.translate(_TR_TRANSLATE)
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def find_character_image(character_name: str) -> str | None:
    slug = _slugify(character_name)
    for ext in (".jpg", ".jpeg", ".png"):
        path = os.path.join(CHARACTERS_DIR, slug + ext)
        if os.path.isfile(path):
            return path
    return None


def _find_existing_art(project_dir: str) -> str | None:
    for name in ("art.jpg", "art.jpeg", "art.png"):
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


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


def _add_title_text(
    bg_path: str, out_path: str, title: str, y_center_ratio: float = 0.5,
    out_w: int = CANVAS_SIZE, out_h: int = CANVAS_SIZE,
) -> None:
    """bg_path'teki görsele başlık + sabit marka satırını ortalayarak yazar,
    out_path'e yazar (bg_path değiştirilmez). y_center_ratio, başlığın dikey
    merkezinin canvas yüksekliğine oranı — procedural gradyanda tam ortada
    (0.5) durur, ama bir karakter portresi arka planken (bkz. generate())
    büst siluetiyle çakışmasın diye başın ÜSTÜNDEKİ boş alana (küçük bir
    oran) taşınır.

    out_w/out_h çıktı kanvası boyutu — generate() bunu HEM cover.png (16:9,
    COVER_SIZE_WIDE) HEM cover_vertical.png (9:16, COVER_SIZE_TALL) için ayrı
    ayrı çağırır (YouTube uzun-format ile Shorts/TikTok/Instagram farklı
    thumbnail en-boy oranı bekliyor — tek kare görsel ikisinde de kenarlarda
    çirkin pillarbox/letterbox şeridine yol açıyordu, kullanıcı geri
    bildirimiyle tespit edildi). Font boyutları min(out_w,out_h) baz alınarak
    hesaplanıyor ki iki farklı en-boy oranında da orantılı görünsün.

    bg_path kaynağı (procedural arka plan, karakter portresi ya da elle
    sağlanan bir art.jpg) HERHANGİ bir çözünürlükte/en-boy oranında olabilir
    — bu yüzden her zaman önce out_w x out_h'e scale+crop ediliyor (aynı
    normalizasyon ffmpeg_utils.py'nin video kartı için de yaptığı)."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    title_escaped = _escape_drawtext(title)
    label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    basis = min(out_w, out_h)
    title_fontsize = int(basis * 0.075)
    label_fontsize = int(basis * 0.03)
    y_center = int(out_h * y_center_ratio)

    base_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        f"drawtext=fontfile={rel_font}:text='{title_escaped}':"
        f"fontcolor=white:fontsize={title_fontsize}:"
        f"x=(w-text_w)/2:y={y_center}-(text_h/2)"
    )

    if config.LOGO_PATH:
        # Düz "Famous Music Studio" metni yerine gerçek amblem (bkz.
        # _compose_cover_rich'teki aynı yaklaşım/not) — ortalanmış.
        logo_h = int(basis * 0.2)
        logo_y = y_center + int(title_fontsize * 0.85)
        filter_complex = (
            f"[0:v]{base_chain}[bg];"
            f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,{LOGO_BRIGHTEN_FILTER},format=rgba[logo];"
            f"[bg][logo]overlay=x=(main_w-overlay_w)/2:y={logo_y}[out]"
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
            f"fontcolor=white@0.75:fontsize={label_fontsize}:"
            f"x=(w-text_w)/2:y={y_center}+{int(title_fontsize * 0.9)}"
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


def _compose_cover_rich(
    bg_path: str, out_path: str, title: str, accent: tuple[int, int, int],
    out_w: int = CANVAS_SIZE, out_h: int = CANVAS_SIZE,
) -> None:
    """Procedural (temasız arka plan) kapaklar için zenginleştirilmiş kompozisyon:
    sol-alt yaslı düzen (Spotify "Now Playing" tarzı) + harf aralıklı tür etiketi +
    gölgeli kalın başlık + ince ayraç çizgisi + alt gradyan gölgeleme (bokeh dokusu
    metnin altına denk gelirse okunurluk garantisi) + alt kenarda tema-rengi ince bir
    marka şeridi (kataloğun tamamında tutarlı bir görsel imza). Sadece cover.png/
    cover_vertical.png için kullanılır — art.png (kart+backdrop kaynağı) bu
    kompozisyondan ETKİLENMEZ, aynı metinsiz bokeh dokusu kalır.

    out_w/out_h — generate() bunu HEM cover.png (16:9) HEM cover_vertical.png (9:16)
    için ayrı çağırır. Metin bloğu buna göre ALTTAN yukarı doğru istifleniyor (sabit
    bir üstten-oran yerine) ki kısa (900px) bir tuval taşırmasın, uzun (1600px) bir
    tuvalde de gereksiz yere tepede kalmasın. Font boyutları min(out_w,out_h) baz
    alınarak hesaplanıyor — iki oranda da aynı mutlak boyutta, tutarlı görünsün."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    title_escaped = _escape_drawtext(title)
    brand_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    accent_hex = "%02x%02x%02x" % accent
    basis = min(out_w, out_h)

    margin = int(out_w * 0.07)
    title_fs = int(basis * 0.16)
    subtitle_fs = int(basis * 0.048)
    rule_w = int(out_w * 0.09)
    bar_h = int(basis * 0.03)
    use_logo = bool(config.LOGO_PATH)
    # Amblem, düz metinden daha "kalın" göründüğü için daha yüksek bir slot
    # ayrılıyor — küçük thumbnail boyutunda bile "FAMOUS" okunsun diye
    # (kullanıcı geri bildirimiyle büyütüldü: ilk deneme çok küçüktü).
    logo_h = int(basis * 0.30)
    brand_h = logo_h if use_logo else subtitle_fs

    # Alttan yukarı istifleme: şerit -> marka (logo/metin) -> ayraç -> başlık.
    # Tür etiketi ("ARABESK"/"ELEKTRONİK" gibi harf aralıklı üst satır) kullanıcı
    # isteğiyle KALDIRILDI — tarz bilgisi zaten caption/hashtag'lerde var,
    # kapakta yer kaplıyordu. Tema rengi ayraç çizgisinde ve alt şeritte
    # kalmaya devam ediyor, yani görsel tarz kimliği kaybolmadı.
    y_bar = out_h - bar_h
    margin_bottom = int(out_h * 0.05)
    y_brand = y_bar - margin_bottom - brand_h
    y_rule = y_brand - int(out_h * 0.025) - 3
    y_title = y_rule - int(title_fs * 1.15)

    base_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        # Alt ~yarıyı kademeli karart — arka plan ne olursa olsun başlık ve altın
        # amblem okunur kalsın. Katsayı 0.55'ten 0.72'ye çıkarıldı ve karartma
        # daha yukarıdan (%50) başlıyor: prosedürel bokeh dokularında 0.55
        # yetiyordu ama GERÇEK fotoğraflara geçince (bkz. stock_art.py) parlak
        # gündüz kareleri geldi ve o kadar karartmada logo soluk kalıyordu.
        f"geq=r='r(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))':"
        f"g='g(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))':"
        f"b='b(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))',"
        # başlık — hafif gölge + kalın beyaz üst katman
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':fontcolor=black@0.5:"
        f"fontsize={title_fs}:x={margin}+4:y={y_title}+5,"
        f"drawtext=fontfile={rel_font_bold}:text='{title_escaped}':fontcolor=white:"
        f"fontsize={title_fs}:x={margin}:y={y_title},"
        # ayraç çizgisi
        f"drawbox=x={margin}:y={y_rule}:w={rule_w}:h=3:color=0x{accent_hex}@1.0:t=fill"
    )

    if use_logo:
        # Düz "Famous Music Studio" metni yerine gerçek amblem (altın sunburst +
        # wordmark) — logo düz SİYAH zemin üzerine kaydedilmiş (alfasız), colorkey
        # ile siyah şeffaflaştırılıp sadece altın kısım overlay ediliyor.
        filter_complex = (
            f"[0:v]{base_chain}[bg];"
            f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,{LOGO_BRIGHTEN_FILTER},format=rgba[logo];"
            f"[bg][logo]overlay=x={margin}:y={y_brand}[merged];"
            f"[merged]drawbox=x=0:y={y_bar}:w=iw:h={bar_h}:color=0x{accent_hex}@1.0:t=fill[out]"
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
        # Logo asset'i bulunamadı (gitignored, bu makinede henüz konmamış olabilir)
        # — sessizce düz metin marka satırına düş, hata verme.
        filter_complex = (
            f"{base_chain},"
            f"drawtext=fontfile={rel_font}:text='{brand_escaped}':fontcolor=white@0.75:"
            f"fontsize={subtitle_fs}:x={margin}:y={y_brand},"
            f"drawbox=x=0:y={y_bar}:w=iw:h={bar_h}:color=0x{accent_hex}@1.0:t=fill"
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
        raise RuntimeError(f"Kapak kompozisyonu başarısız: {result.stderr[-1000:]}")


def generate(project_dir: str) -> None:
    meta = load_meta(project_dir)
    title = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    character = meta.get("character")

    has_cover = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("cover.jpg", "cover.jpeg", "cover.png")
    )
    has_cover_vertical = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png")
    )
    has_art = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("art.jpg", "art.jpeg", "art.png")
    )
    if has_cover and has_cover_vertical and has_art:
        return

    character_image = find_character_image(character) if character else None
    # has_art ise (elle sağlanmış bir görsel var, ör. karakter roster'ında olmayan
    # bir proje için manuel art.jpg — DJ Famous gibi) cover.png'yi o gerçek görselden
    # türetiyoruz; öncesinde bu durumda cover.png ilgisiz bir procedural gradyandan
    # üretiliyordu (art.jpg tamamen göz ardı ediliyordu) — sağlanan görselle
    # bağlantısız bir kapak çıkması bir hataydı.
    existing_art = _find_existing_art(project_dir) if has_art else None
    cleanup_paths = []
    fetched_stock_photo = False
    if character_image:
        bg_path = character_image
        bg_ext = os.path.splitext(character_image)[1]
        source_label = f"karakter portresi: {character}"
    elif existing_art:
        bg_path = existing_art
        bg_ext = os.path.splitext(existing_art)[1]
        source_label = "elle sağlanan art görseli"
    else:
        # Önce şarkının tarzına/sözlerine uygun GERÇEK bir fotoğraf denenir
        # (Pexels, bkz. stock_art.py) — kullanıcı isteği: kapak soyut bir
        # gradyan değil, tarzın çağrıştırdığı bir mekân/atmosfer olsun.
        # Başarısızsa (anahtar/ağ/sonuç yok) sessizce eski prosedürel bokeh
        # üretimine düşülür, otomasyon asla durmaz.
        stock_path = os.path.join(project_dir, "_stock_art_tmp.jpg")
        stock_query = stock_art.build_query(meta, theme, title)
        if stock_query and stock_art.fetch_art(title, stock_query, stock_path):
            bg_path = stock_path
            bg_ext = ".jpg"
            cleanup_paths = [stock_path]
            source_label = f"Pexels görseli ({stock_query!r})"
            fetched_stock_photo = True
        else:
            seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
            base_path = os.path.join(project_dir, "_bg_base_tmp.png")
            bg_path = os.path.join(project_dir, "_bg_tmp.png")
            bg_ext = ".png"
            _radial_background(base_path, theme["accent"])
            _add_bokeh(base_path, bg_path, theme["accent"], seed)
            cleanup_paths = [base_path, bg_path]
            source_label = f"{theme_key} teması"

    cover_path = os.path.join(project_dir, "cover.png")
    cover_vertical_path = os.path.join(project_dir, "cover_vertical.png")
    art_path = os.path.join(project_dir, f"art{bg_ext}")
    # DJ Famous kapaklarındaki (dj_sets/) sade/ortalanmış düzen — kullanıcı
    # isteğiyle TÜM gerçek fotoğraflara (karakter portresi, elle sağlanan
    # görsel, Pexels stok fotoğrafı) genelleştirildi. "Zengin" sol-alt blok
    # (ayraç + alt marka şeridi + büyük logo) kullanıcı tarafından beğenilmedi
    # ("yapılan değişiklikler hatalı oldu") — artık SADECE gerçek bir fotoğraf
    # hiç bulunamadığında (Pexels de başarısızsa) düşülen saf prosedürel bokeh
    # dokusunda kullanılıyor; bir fotoğrafın üzerine o kadar dekoratif öğe
    # binmesi fotoğrafı bastırıyordu.
    #
    # AYRICA: art.jpg bir kez yazıldıktan sonra "bizim indirdiğimiz stok
    # fotoğraf" ile "kullanıcının elle koyduğu görsel" ayırt EDİLEMİYOR — ikisini
    # aynı düzene bağlamak, yeniden çalıştırmada tasarımın sessizce değişmesini
    # de engelliyor (bu daha önce gerçekten oldu).
    is_photo = bool(character_image or existing_art or fetched_stock_photo)
    try:
        if not has_art:
            shutil.copy(bg_path, art_path)
            print(f"  art{bg_ext} üretildi ({source_label})")
        # cover.png (16:9, YouTube uzun-format thumbnail'i) ve cover_vertical.png
        # (9:16, Shorts/TikTok/Instagram kapağı) AYRI üretiliyor — tek kare görsel
        # ikisinde de kenarlarda pillarbox/letterbox şeridine yol açıyordu
        # (kullanıcı geri bildirimiyle tespit edildi).
        for missing, out_path, (out_w, out_h), label in (
            (not has_cover, cover_path, COVER_SIZE_WIDE, "cover.png"),
            (not has_cover_vertical, cover_vertical_path, COVER_SIZE_TALL, "cover_vertical.png"),
        ):
            if not missing:
                continue
            if is_photo:
                # DJ set stili: başlık üstteki boş alana yaslı, altında ince
                # logo/marka satırı — fotoğrafın kendisi kompozisyonun asıl
                # unsuru kalıyor (karakter portresinde ayrıca büst siluetiyle
                # çakışmayı da önlüyor).
                _add_title_text(bg_path, out_path, title, y_center_ratio=0.13, out_w=out_w, out_h=out_h)
            else:
                _compose_cover_rich(bg_path, out_path, title, theme["accent"], out_w=out_w, out_h=out_h)
            print(f"  {label} üretildi ({title!r}, {source_label})")
    finally:
        for tmp_path in cleanup_paths:
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
