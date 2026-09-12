"""Instagram/TikTok paylaşım metinleri (caption) için ortak şablon.

YouTube açıklamasından farklı olarak burada linkler yerine hashtag ağırlıklı,
kısa bir caption üretilir — Instagram/TikTok'ta caption içindeki linkler zaten
tıklanabilir değildir.
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def hashtag(text: str) -> str:
    return "#" + "".join(ch for ch in text if ch.isalnum())


def pick_deterministic(title: str, options: list, salt: int = 0) -> str:
    """Şarkı başlığına (+ salt) göre deterministik bir satır seçer — aynı şarkı hep
    aynı satırı alır, farklı şarkılar arasında çeşitlilik olur. salt, aynı başlıktan
    türeyen birden fazla seçimin (hook + engagement question gibi) her zaman aynı
    ikilide eşleşmemesi için kullanılıyor. Public (youtube_upload.build_snippet de
    aynı hook/soru havuzlarından aynı mantıkla seçim yapmak için kullanıyor)."""
    index = (sum(ord(ch) for ch in title) + salt) % len(options)
    return options[index]


def pick_subset(title: str, options: list, count: int, salt: int = 0) -> list:
    """Havuzdan `count` tane seçer — şarkı başlığına göre DETERMİNİSTİK.

    Aynı şarkı her koşuda aynı seti alır (yeniden üretim arşivi bozmasın),
    şarkılar arasında set değişir. Adım da başlığa göre kayıyor; sabit adımda
    havuzun hep aynı üçlüsü seçiliyordu.
    """
    n = len(options)
    if n == 0:
        return []
    count = min(count, n)
    seed = int(hashlib.sha256((title + str(salt)).encode("utf-8")).hexdigest()[:8], 16)
    adim = 1 if n < 2 else 1 + seed % (n - 1)
    secilen, i = [], 0
    while len(secilen) < count and i < n * 3:
        aday = options[(seed + i * adim) % n]
        if aday not in secilen:
            secilen.append(aday)
        i += 1
    return secilen


def resolve_language(meta: dict) -> str:
    """Paylaşım metinlerinin dilini belirler: meta.json'da açık bir "language"
    varsa o öncelikli (istisna/override için), yoksa Suno'da üretilen müziğin
    STİLİNE (theme) göre varsayılana düşülür (config.THEMES[...]["language"]) —
    kullanıcı isteği: dil hazırlığı stile göre otomatik olsun, her projede elle
    yazmaya gerek kalmasın. Hiçbiri yoksa "tr"."""
    if meta.get("language"):
        return meta["language"]
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    return config.THEMES.get(theme_key, {}).get("language", "tr")


def stil_etiketleri(meta: dict) -> list:
    """DJ setinin muzik stiline ozel etiketler (config.SET_STILLERI).

    Tema etiketlerine EK olarak donuyor, onlarin yerine degil: "DJ Set"/"Mix"
    marka sinyali olarak kalmali, stil etiketleri ise seti kendi kitlesine
    tasiyor. meta.json'da `set_style` yoksa bos liste - eski setler etkilenmez.
    """
    stil = config.set_stili(meta)
    return list(stil["etiketler"]) if stil else []


def build_caption(meta: dict) -> str:
    """Şarkıya ÖZEL metin varsa genel havuzun önüne geçer (2026-09-10):
    meta.json içindeki `custom_hooks` / `custom_questions`, o şarkının
    SÖZLERİNDEN türetilmiş satırlardır ("Masada iki tabak, biri hep boş" gibi).
    Yoksa config.py'deki genel havuza düşülür — söz dosyası olmayan ilk üç
    şarkı (Gece Sürüşü, Beni Bırakma, Yeniden Doğacağım) o yolda kalır.
    """
    """Caption BİLİNÇLİ olarak başka bir platforma yönlendirme içermiyor — Instagram/
    TikTok'un keşfet/For You dağıtımı, caption'da "başka platforma git" mesajı olan
    içeriği hafifçe cezalandırıyor olabilir (resmi olarak açıklanmıyor ama yaygın
    growth pratiği bu yönde). YouTube linki bunun yerine build_youtube_comment() ile
    paylaşımdan SONRA bir yorum olarak ekleniyor — bkz. instagram_upload.py.

    Dil resolve_language() ile belirlenir — stile (theme) göre otomatik, meta.json'da
    açık bir "language" varsa o öncelikli. "en" ise İngilizce şablon/hashtag kullanılır
    (bkz. config.py'deki *_EN sabitleri) — değilse (ana katalogdaki gibi) Türkçe."""
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_hashtags = ([hashtag(theme["label"])]
                      + [hashtag(t) for t in theme.get("related", [])]
                      + [hashtag(t) for t in stil_etiketleri(meta)])

    if resolve_language(meta) == "en":
        discovery_hashtags = pick_subset(title, config.DISCOVERY_HASHTAGS_EN,
                                         config.DISCOVERY_HASHTAG_COUNT, salt=13)
        hashtags = " ".join(config.BRAND_HASHTAGS + discovery_hashtags + genre_hashtags)
        hook = pick_deterministic(title, meta.get("custom_hooks") or config.HOOK_LINES_EN)
        engagement_question = pick_deterministic(
            title, meta.get("custom_questions") or config.ENGAGEMENT_QUESTIONS_EN, salt=7)
        use_line = pick_deterministic(title, config.USE_LINES_EN, salt=3)
        follow_line = pick_deterministic(title, config.FOLLOW_LINES_EN, salt=11)
        return (
            f"{hook}\n\n{title} 🎵\n\n"
            f"{use_line}\n\n"
            f"{follow_line}\n\n"
            f"{engagement_question}\n\n{hashtags}"
        )

    discovery_hashtags = pick_subset(title, config.DISCOVERY_HASHTAGS,
                                     config.DISCOVERY_HASHTAG_COUNT, salt=13)
    hashtags = " ".join(config.BRAND_HASHTAGS + discovery_hashtags + genre_hashtags)
    hook = pick_deterministic(title, meta.get("custom_hooks") or config.HOOK_LINES)
    engagement_question = pick_deterministic(
        title, meta.get("custom_questions") or config.ENGAGEMENT_QUESTIONS, salt=7)
    use_line = pick_deterministic(title, config.USE_LINES, salt=3)
    follow_line = pick_deterministic(title, config.FOLLOW_LINES, salt=11)

    return (
        f"{hook}\n\n{title} 🎵\n\n"
        f"{use_line}\n\n"
        f"{follow_line}\n\n"
        f"{engagement_question}\n\n{hashtags}"
    )


def build_ai_disclosure_line(lang: str = "tr") -> str:
    """DJ Famous gibi GERÇEK, tanınabilir bir kişiyi (bkz. dj_sets/README.md)
    konu alan içeriklerde caption'a eklenen tek satırlık AI-üretimi bildirimi.
    Meta'nın Graph API'sinde resmi bir 'is_ai_generated' alanı ikincil
    kaynaklarda geçiyor ama developers.facebook.com'da doğrulanamadı (bkz.
    instagram_upload.py'deki not) — bu yüzden en küçük/en az göze batan
    güvenilir alternatif olarak caption'ın SONUNA (en az dikkat çeken yer)
    tek satır ekleniyor. Ana kataloğun (kurgusal temalar/karakterler) normal
    build_caption() çıktısına eklenmiyor, sadece gerçek kişi içeren içerikte
    kullanılır. lang="en" ise İngilizce metin döner (bkz. meta.json'daki
    "language" alanı, ilk kullanım: DJ Famous)."""
    if lang == "en":
        return "This content was created using artificial intelligence."
    return "Bu içerik yapay zeka ile üretilmiştir."


def build_youtube_comment(youtube_url: str, lang: str = "tr", platform: str = "instagram") -> str:
    """Paylaşımdan SONRA ilk yorum olarak eklenecek kısa metin — caption'ın aksine
    yorumların keşfet dağıtımını etkilediğine dair bir kaygı yok, o yüzden link
    burada güvenle kullanılabiliyor. lang="en" ise İngilizce metin döner (bkz.
    meta.json'daki "language" alanı). platform "instagram" ya da "tiktok" —
    hangi hesabın @handle'ının etiketleneceğini belirler (config.SOCIAL_HANDLES).

    İkinci satır BİLİNÇLİ olarak eklendi (kullanıcı kararı, 2026-09-05):
    Instagram/TikTok yorumlarında düz metin linkler TIKLANAMIYOR (WebSearch ile
    doğrulandı) — youtu.be linki yine de kopyalanabilir metin olarak kalıyor.
    Gerçekten tıklanabilir tek yer profildeki "bio link" — ama caption/yoruma
    düz "profildeki linkten..." yazmak yerine, hesabın kendisini `@handle` ile
    ETİKETLEMEK (mention) caption/yorumda GERÇEKTEN tıklanabilir bir eleman
    oluşturuyor (düz URL'den FARKLI bir mekanizma, WebSearch ile doğrulandı) —
    tıklanınca doğrudan profile açılır, orada bio linki (famousmusicstudio.com/
    latest.html, bkz. latest_release.py) görünür/tıklanabilir. Bio linkinin
    kendisini o adrese bağlamak kullanıcının uygulamadan elle yapması gereken,
    tek seferlik bir profil ayarı."""
    # Facebook'ta @handle satiri YOK ve olmamali. Iki ayri sebep:
    #   1. Ikinci satirin tek varlik sebebi Instagram/TikTok'ta duz linklerin
    #      TIKLANAMAMASI. Facebook yorumundaki link zaten tiklanabilir, yani
    #      satir orada bir sorunu cozmuyor.
    #   2. config.SOCIAL_HANDLES'da "facebook" anahtari yok ve varsayilan
    #      Instagram handle'ina dusuyordu — Facebook yorumuna baska bir
    #      platformun hesap adi, o sayfanin adiymis gibi yaziliyordu.
    #      Sayfanin vanity URL'i de alinmamis durumda (username: None),
    #      yani mention teknik olarak zaten mumkun degil.
    if platform == "facebook":
        if lang == "en":
            return f"🎧 Full track on YouTube: {youtube_url}"
        return f"🎧 Şarkının tamamı YouTube'da: {youtube_url}"

    handle = config.SOCIAL_HANDLES.get(platform, config.SOCIAL_HANDLES["instagram"])
    if lang == "en":
        return f"🎧 Full track on YouTube: {youtube_url}\nTap @{handle} above and check the link in bio 🔗"
    return f"🎧 Şarkının tamamı YouTube'da: {youtube_url}\n@{handle} hesabına dokun, bio'daki linkten de ulaşabilirsin 🔗"
