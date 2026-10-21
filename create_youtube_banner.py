#!/usr/bin/env python3
"""Famous Music Studio — YouTube kanal banner'ı (2560x1440, güvenli alan 1546x423).

Mevcut banner'ın marka dilini korur (koyu zemin + turuncu sunburst + sarı vurgu)
ve blueprint gereği PROMO ELEMENTLERİ ekler: yeni albüm, streaming, Ko-fi.

Yerleşim kuralı: YouTube masaüstü güvenli alanı 1546x423 -> dikeyde
(1440-423)/2 = 508 ile 931 arası. Ana mesaj BU ŞERİTTE tutulur; dekor
(ışınlar, logo rozeti) güvenli alan DIŞINDA kalabilir.

Kullanım:
    python create_youtube_banner.py
"""
import math
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
SAFE_TOP = (H - SAFE_H) // 2          # 508
SAFE_BOT = SAFE_TOP + SAFE_H           # 931

BG = (8, 8, 12)
ACCENT = (233, 69, 96)
GOLD = (255, 196, 61)
ORANGE = (255, 140, 40)
TEXT = (245, 245, 248)
MUTED = (155, 155, 165)

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "site", "assets", "youtube-banner-2560x1440.png")
ICON = os.path.join(REPO, "assets", "brand", "icon_big.jpg")
FONT_DIR = "C:/Windows/Fonts"


def font(name, size):
    for cand in (name, name.replace("bd", ""), name.replace("-Bold", ""),
                 "segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        p = os.path.join(FONT_DIR, cand)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def tw(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[2] - b[0]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Dikey gradyan ---
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)],
                  fill=(int(8 + 10 * t), int(8 + 6 * t), int(12 + 22 * t)))

    # --- Sunburst ışınları (dekor — güvenli alan dışı ağırlıklı) ---
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    ox, oy = int(W * 0.5), int(H * 0.5)
    for i in range(0, 360, 8):
        a0, a1 = math.radians(i), math.radians(i + 2.6)
        length = 1500 + (i % 40) * 22
        p1 = (ox + math.cos(a0) * length, oy + math.sin(a0) * length)
        p2 = (ox + math.cos(a1) * length, oy + math.sin(a1) * length)
        alpha = 16 if (i // 8) % 2 == 0 else 6
        rd.polygon([(ox, oy), p1, p2], fill=(255, 150, 50, alpha))
    rays = rays.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img.convert("RGBA"), rays).convert("RGB")

    # --- Radial glow ---
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = W // 2, int(H * 0.5)
    for i in range(40, 0, -1):
        rad = i * 70
        a = int(2 + 3 * (1 - i / 40))
        gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                   fill=(a, int(a * 0.45), int(a * 0.12)))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    bp, gp, px = img.load(), glow.load(), img.load()
    for y in range(H):
        for x in range(W):
            r, g, b = bp[x, y]
            gr, gg, gb = gp[x, y]
            px[x, y] = (min(255, r + gr), min(255, g + gg), min(255, b + gb))

    # --- Logo rozeti (sol kenar, dekor — başlığa dokunmaz) ---
    draw = ImageDraw.Draw(img)
    badge = 250
    bx, by = 190, int(H * 0.5 - badge // 2)
    if os.path.exists(ICON):
        ic = Image.open(ICON).convert("RGBA").resize((badge, badge), Image.LANCZOS)
        mask = Image.new("L", (badge, badge), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, badge, badge], fill=255)
        ring = Image.new("RGBA", (badge + 14, badge + 14), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, badge + 13, badge + 13],
                                     outline=(*ACCENT, 210), width=4)
        img.paste(ic, (bx, by), mask)
        img.paste(ring, (bx - 7, by - 7), ring)
    else:
        draw.ellipse([bx, by, bx + badge, by + badge],
                     fill=(20, 20, 30), outline=ACCENT, width=4)
    draw = ImageDraw.Draw(img)

    # ============ GÜVENLİ ALAN İÇERİĞİ ============
    f_title = font("segoeuib.ttf", 118)
    f_tag = font("segoeui.ttf", 46)
    f_album = font("segoeuib.ttf", 38)
    f_promo = font("segoeui.ttf", 30)

    title = "FAMOUS MUSIC STUDIO"
    tagline = "Her cuma yeni şehir  •  AI-assisted music production from Turkey"

    tx = (W - tw(draw, title, f_title)) // 2
    ty = SAFE_TOP + 24
    # gölge katmanı (2px aşağı) -> sonra asıl metin
    draw.text((tx + 3, ty + 4), title, font=f_title, fill=(120, 20, 40))
    draw.text((tx, ty), title, font=f_title, fill=TEXT)
    # altın alt-çizgi
    draw.rectangle([tx, ty + 148, tx + tw(draw, title, f_title), ty + 155], fill=GOLD)

    # tagline (logodan uzak, ortada)
    draw.text(((W - tw(draw, tagline, f_tag)) // 2, ty + 182),
              tagline, font=f_tag, fill=MUTED)

    # promo kutuları
    boxes = [
        ("YENİ ALBÜM", "GECE MASALLARI", ORANGE),
        ("DİNLE", "SPOTIFY · APPLE", ACCENT),
        ("DESTEK", "KO-FI.COM", GOLD),
    ]
    bw, bh, gap = 430, 92, 32
    total = len(boxes) * bw + (len(boxes) - 1) * gap
    sx = (W - total) // 2
    sy = ty + 258
    for i, (k, v, col) in enumerate(boxes):
        x = sx + i * (bw + gap)
        box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=12,
                             fill=(20, 20, 30, 230), outline=(*col, 190), width=3)
        img.paste(box, (x, sy), box)
        draw = ImageDraw.Draw(img)
        draw.text((x + (bw - tw(draw, k, f_promo)) // 2, sy + 12),
                  k, font=f_promo, fill=col)
        draw.text((x + (bw - tw(draw, v, f_album)) // 2, sy + 48),
                  v, font=f_album, fill=TEXT)

    # handle (dekor, alt kenar)
    handle = "@Famous_musics_studio"
    draw.text(((W - tw(draw, handle, f_promo)) // 2, H - 66),
              handle, font=f_promo, fill=(90, 90, 100))

    # alt kenar çizgisi
    draw.rectangle([0, H - 6, W, H - 1], fill=ACCENT)

    img.save(OUT, "PNG", optimize=True)
    print(f"Banner yazildi: {OUT}")
    print(f"Boyut: {img.size}  ({os.path.getsize(OUT) // 1024} KB)")
    print(f"Guvensli alan dikey: {SAFE_TOP}-{SAFE_BOT}  (icerik: {ty}-{sy + bh})")


if __name__ == "__main__":
    main()
