#!/usr/bin/env python3
"""Create og-cover.jpg (1200x630) for Famous Music Studio Open Graph"""
from PIL import Image, ImageDraw, ImageFont
import os

WIDTH, HEIGHT = 1200, 630
BG_COLOR = (10, 10, 15)  # #0a0a0f
ACCENT_COLOR = (233, 69, 96)  # #e94560
GOLD_COLOR = (255, 215, 0)  # #ffd700
TEXT_COLOR = (224, 224, 224)  # #e0e0e0
TEXT_MUTED = (136, 136, 136)  # #888888

img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
draw = ImageDraw.Draw(img)

# Gradient background
for y in range(HEIGHT):
    ratio = y / HEIGHT
    r = int(BG_COLOR[0] + (26 - BG_COLOR[0]) * ratio * 0.3)
    g = int(BG_COLOR[1] + (26 - BG_COLOR[1]) * ratio * 0.3)
    b = int(BG_COLOR[2] + (47 - BG_COLOR[2]) * ratio * 0.3)
    draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

# Accent line at top
draw.line([(0, 0), (WIDTH, 0)], fill=ACCENT_COLOR, width=4)

# Try to load fonts
font_paths = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
font_large = None
font_medium = None
font_small = None

for path in font_paths:
    if os.path.exists(path):
        try:
            if font_large is None:
                font_large = ImageFont.truetype(path, 72)
            if font_medium is None:
                font_medium = ImageFont.truetype(path, 36)
            if font_small is None:
                font_small = ImageFont.truetype(path, 24)
        except:
            pass

if font_large is None:
    font_large = ImageFont.load_default()
if font_medium is None:
    font_medium = ImageFont.load_default()
if font_small is None:
    font_small = ImageFont.load_default()

# Center coordinates
cx = WIDTH // 2

# Main title
title = "Famous Music Studio"
title_bbox = draw.textbbox((0, 0), title, font=font_large)
title_w = title_bbox[2] - title_bbox[0]
draw.text((cx - title_w // 2, 180), title, font=font_large, fill=TEXT_COLOR)

# AI badge
badge_text = "AI-Assisted Music Production"
badge_bbox = draw.textbbox((0, 0), badge_text, font=font_medium)
badge_w = badge_bbox[2] - badge_bbox[0]
badge_x = cx - badge_w // 2
badge_y = 280
# Badge background
draw.rounded_rectangle(
    [badge_x - 20, badge_y - 10, badge_x + badge_w + 20, badge_y + 50],
    radius=25, fill=(30, 30, 50), outline=ACCENT_COLOR, width=2
)
draw.text((badge_x, badge_y), badge_text, font=font_medium, fill=ACCENT_COLOR)

# Tagline
tagline = "Gece Masalları Album · Night Drive DJ Sets"
tagline_bbox = draw.textbbox((0, 0), tagline, font=font_small)
tagline_w = tagline_bbox[2] - tagline_bbox[0]
draw.text((cx - tagline_w // 2, 370), tagline, font=font_small, fill=TEXT_MUTED)

# Genre tags
genres = ["Turkish Pop", "R&B", "Trap", "Arabesk", "Melodic Techno"]
genre_y = 430
genre_x_start = cx - 300
for i, genre in enumerate(genres):
    g_bbox = draw.textbbox((0, 0), genre, font=font_small)
    g_w = g_bbox[2] - g_bbox[0]
    g_h = g_bbox[3] - g_bbox[1]
    x = genre_x_start + (i % 3) * 200
    y = genre_y + (i // 3) * 50
    draw.rounded_rectangle(
        [x - 15, y - 8, x + g_w + 15, y + g_h + 8],
        radius=15, fill=(233, 69, 96, 30), outline=ACCENT_COLOR, width=1
    )
    draw.text((x, y), genre, font=font_small, fill=ACCENT_COLOR)

# Bottom accent line
draw.line([(100, HEIGHT - 4), (WIDTH - 100, HEIGHT - 4)], fill=GOLD_COLOR, width=2)

# Website URL
url_text = "famousmusicstudio.com"
url_bbox = draw.textbbox((0, 0), url_text, font=font_small)
url_w = url_bbox[2] - url_bbox[0]
draw.text((cx - url_w // 2, HEIGHT - 60), url_text, font=font_small, fill=GOLD_COLOR)

# Save
output_path = "C:/Users/ACER/Desktop/ilk-projem/site/og-cover.jpg"
img.save(output_path, "JPEG", quality=95, optimize=True)
print(f"Saved: {output_path}")
print(f"Size: {WIDTH}x{HEIGHT}")