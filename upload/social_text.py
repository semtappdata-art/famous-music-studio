"""Instagram/TikTok paylaşım metinleri (caption) için ortak şablon.

YouTube açıklamasından farklı olarak burada linkler yerine hashtag ağırlıklı,
kısa bir caption üretilir — Instagram/TikTok'ta caption içindeki linkler zaten
tıklanabilir değildir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def _hashtag(text: str) -> str:
    return "#" + "".join(ch for ch in text if ch.isalnum())


def _pick_hook(title: str) -> str:
    """Şarkı başlığına göre deterministik bir hook satırı seçer — aynı şarkı hep aynı
    hook'u alır, farklı şarkılar arasında çeşitlilik olur (bkz. feedback_growth_tavsiyeleri)."""
    index = sum(ord(ch) for ch in title) % len(config.HOOK_LINES)
    return config.HOOK_LINES[index]


def build_caption(meta: dict) -> str:
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_hashtags = [_hashtag(theme["label"])] + [_hashtag(t) for t in theme.get("related", [])]

    hashtags = " ".join(config.BRAND_HASHTAGS + genre_hashtags)
    hook = _pick_hook(title)

    return (
        f"{hook}\n\n{title} 🎵\n\n"
        f"Bu sesi edit/kesit videolarında kullanabilirsin 🔥\n\n"
        f"Yeni şarkılar için takipte kalın\n\n{hashtags}"
    )
