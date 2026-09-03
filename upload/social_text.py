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


def _pick(title: str, options: list, salt: int = 0) -> str:
    """Şarkı başlığına (+ salt) göre deterministik bir satır seçer — aynı şarkı hep
    aynı satırı alır, farklı şarkılar arasında çeşitlilik olur. salt, aynı başlıktan
    türeyen birden fazla seçimin (hook + engagement question gibi) her zaman aynı
    ikilide eşleşmemesi için kullanılıyor."""
    index = (sum(ord(ch) for ch in title) + salt) % len(options)
    return options[index]


def build_caption(meta: dict) -> str:
    """Caption BİLİNÇLİ olarak başka bir platforma yönlendirme içermiyor — Instagram/
    TikTok'un keşfet/For You dağıtımı, caption'da "başka platforma git" mesajı olan
    içeriği hafifçe cezalandırıyor olabilir (resmi olarak açıklanmıyor ama yaygın
    growth pratiği bu yönde). YouTube linki bunun yerine build_youtube_comment() ile
    paylaşımdan SONRA bir yorum olarak ekleniyor — bkz. instagram_upload.py."""
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_hashtags = [_hashtag(theme["label"])] + [_hashtag(t) for t in theme.get("related", [])]

    hashtags = " ".join(config.BRAND_HASHTAGS + config.DISCOVERY_HASHTAGS + genre_hashtags)
    hook = _pick(title, config.HOOK_LINES)
    engagement_question = _pick(title, config.ENGAGEMENT_QUESTIONS, salt=7)

    return (
        f"{hook}\n\n{title} 🎵\n\n"
        f"Bu sesi edit/kesit videolarında kullanabilirsin 🔥\n\n"
        f"Yeni şarkılar için takipte kalın\n\n"
        f"{engagement_question}\n\n{hashtags}"
    )


def build_ai_disclosure_line() -> str:
    """DJ Famous gibi GERÇEK, tanınabilir bir kişiyi (bkz. dj_sets/README.md)
    konu alan içeriklerde caption'a eklenen tek satırlık AI-üretimi bildirimi.
    Meta'nın Graph API'sinde resmi bir 'is_ai_generated' alanı ikincil
    kaynaklarda geçiyor ama developers.facebook.com'da doğrulanamadı (bkz.
    instagram_upload.py'deki not) — bu yüzden en küçük/en az göze batan
    güvenilir alternatif olarak caption'ın SONUNA (en az dikkat çeken yer)
    tek satır ekleniyor. Ana kataloğun (kurgusal temalar/karakterler) normal
    build_caption() çıktısına eklenmiyor, sadece gerçek kişi içeren içerikte
    kullanılır."""
    return "Bu içerik yapay zeka ile üretilmiştir."


def build_youtube_comment(youtube_url: str) -> str:
    """Paylaşımdan SONRA ilk yorum olarak eklenecek kısa metin — caption'ın aksine
    yorumların keşfet dağıtımını etkilediğine dair bir kaygı yok, o yüzden link
    burada güvenle kullanılabiliyor."""
    return f"🎧 Şarkının tamamı YouTube'da: {youtube_url}"
