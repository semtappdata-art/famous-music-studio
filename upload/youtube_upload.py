"""Render edilmiş bir projeyi YouTube'a resumable upload ile yükler.

Kullanım:
    python upload/youtube_upload.py --project "projects/beni bırakma"
    python upload/youtube_upload.py --project "projects/beni bırakma" --privacy public
    python upload/youtube_upload.py --project "projects/beni bırakma" --shorts
    python upload/youtube_upload.py --project "projects/beni bırakma" --thumbnail-only
    python upload/youtube_upload.py --thumbnail-only --all   # TÜM projelerin thumbnail'ini tek seferde düzeltir
    python upload/youtube_upload.py --project "projects/beni bırakma" --description-only
    python upload/youtube_upload.py --description-only --all   # TÜM projelerin açıklamasını tek seferde düzeltir

meta.json'dan title/theme okur, output/youtube_16x9.mp4'ü yükler (upload_video),
sonucu projects/<isim>/state.json'a yazar. --shorts ile output/shorts_9x16.mp4
AYRI bir YouTube video'su (Short) olarak yüklenir (upload_short) — küçük/yeni
kanallar için Shorts akışı, uzun format önerilen videolar sisteminden çok daha
erişilebilir bir keşif kanalı olduğu için. auto_process.py ikisini de otomatik
tetikler (önce uzun format, sonra Short — Short'un açıklamasına tam versiyona
bağlantı eklemek için).
"""

import argparse
import collections
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

import config
import state_io
import uyumluluk
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from social_text import build_caption, hashtag, pick_deterministic, resolve_language, stil_etiketleri
from youtube_auth import get_authenticated_service

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _derleme_temalari(meta: dict) -> list:
    """Derlemedeki her parçanın tema anahtarı (çoklu, seçim sırasıyla).

    Birincil kaynak `meta["derleme_temalari"]` — derleme.py bunu yazıyor.
    GERİYE DÖNÜK YOL: bu alan eklenmeden ÖNCE üretilmiş derlemelerde (ör. bu
    değişiklik yazılırken render'da olan "Gece Seansı Vol. 1") alan yok; o
    durumda temalar `derleme_liste`'deki parça adlarından kaynak projelerin
    meta.json'ına bakılarak okunuyor. Aksi hâlde tür bilgisi hiç bulunamaz ve
    derleme, meta'daki tek `theme` alanına (karma bir derlemede yanıltıcı)
    geri düşerdi. Okuma hatası yutuluyor: eksik tür etiketi yüklemeyi
    durdurmaya değmez.
    """
    temalar = [t for t in (meta.get("derleme_temalari") or []) if t]
    if temalar:
        return temalar
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for parca in meta.get("derleme_liste") or []:
        yol = os.path.join(kok, "projects", str(parca.get("ad", "")), "meta.json")
        try:
            with open(yol, "r", encoding="utf-8") as f:
                tema = json.load(f).get("theme")
        except (OSError, ValueError):
            continue
        if tema:
            temalar.append(tema)
    return temalar


def _derleme_tur_bilgisi(meta: dict) -> tuple:
    """(başlıkta kullanılacak tür adı, etiket listesi) — derlemedeki parçalardan.

    NEDEN: derlemenin meta.json'ındaki tek `theme` alanı derlemeyi anlatmıyor
    (eskiden --en-iyi ile tema verilmediği için config.DEFAULT_THEME'e düşüyor
    ve 13 parçalık karma bir derleme "Türkçe Hip-Hop Şarkısı" diye
    yayınlanıyordu). Tür artık parçaların temalarından türetiliyor.

    Baskın tema parçaların YARISINDAN fazlasını kapsıyorsa başlıkta o türün adı
    kullanılıyor; kapsamıyorsa derleme gerçekten KARMA demektir ve "Müzik"
    deniyor — "Gece Seansı Vol. 1"de en kalabalık tema 13 parçanın 5'i; buna
    "Hip-Hop derlemesi" demek ilk sürümdeki yanlışın daha yumuşak bir hâli
    olurdu. Etiketler (tags) yine TÜM temaları içeriyor: orada çoğulluk
    yanıltıcı değil, arama sinyali.
    """
    temalar = _derleme_temalari(meta)
    sayac = collections.Counter(temalar)
    etiketler = []
    for anahtar, _ in sayac.most_common():
        etiket = config.THEMES.get(anahtar, {}).get("label")
        if etiket and etiket not in etiketler:
            etiketler.append(etiket)
    tur = "Müzik"
    if sayac:
        baskin, adet = sayac.most_common(1)[0]
        if adet * 2 > len(temalar):
            tur = config.THEMES.get(baskin, {}).get("label") or "Müzik"
    return tur, etiketler


def build_snippet(meta: dict) -> dict:
    """Uzun format (youtube_16x9.mp4) açıklaması. Dil resolve_language() ile
    belirlenir (stile göre otomatik, meta.json'daki "language" öncelikli) —
    DJ Famous ("dj" teması, "en") gibi İngilizce projelerde de doğru dilde
    üretilsin diye (eskiden burası hardcoded Türkçe idi, DJ Famous'un uzun
    format videosu bile Türkçe açıklama alıyordu). Hook + keşfet/tür
    hashtag'leri + etkileşim sorusu artık Shorts/TikTok/Instagram'ın kullandığı
    build_caption() ile AYNI havuzlardan (config.HOOK_LINES/DISCOVERY_HASHTAGS/
    ENGAGEMENT_QUESTIONS, aynı deterministik seçim) geliyor — eskiden bu üçü de
    sadece kısa-format caption'da vardı, uzun format elinde tek marka
    hashtag'iyle (#FamousMusicStudio) kalıyordu. Link bloğu (Instagram/TikTok/
    Website) uzun formata ÖZGÜ kalıyor — build_caption bunu içermiyor çünkü
    Instagram/TikTok caption'ında dış link YOK (bkz. build_caption docstring)."""
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    # DERLEME DALI: derleme tek bir şarkı değil, birden çok temadan parça
    # içeriyor — tema etiketleri meta'daki tek `theme` alanından türetilemez
    # (bkz. _derleme_tur_bilgisi). "Derleme"/"Mix" etiketleri de ekleniyor:
    # izleyicinin aradığı şey uzun formatta budur.
    derleme = bool(meta.get("derleme"))
    derleme_tur, derleme_etiketleri = _derleme_tur_bilgisi(meta) if derleme else ("", [])
    if derleme:
        genre_tags = derleme_etiketleri + ["Derleme", "Mix", "Karışık Müzik"]
    else:
        genre_tags = [theme["label"]] + theme.get("related", []) + stil_etiketleri(meta)
    links = config.SOCIAL_LINKS

    if resolve_language(meta) == "en":
        discovery_hashtags = config.DISCOVERY_HASHTAGS_EN
        hook = pick_deterministic(title, config.HOOK_LINES_EN)
        engagement_question = pick_deterministic(title, config.ENGAGEMENT_QUESTIONS_EN, salt=7)
        follow_line = "Follow for more tracks 🎵"
        video_title = title
        lyrics_tags = []
        # DJ Famous setleri için kullanıcının referans aldığı bir YouTube DJ-mix
        # kanalının (ör. "GUESTMIX | ... | MENU") açıklama formatı: kısa,
        # doğrudan "kanala abone ol" + "Instagram'da takip et" satırları,
        # handle'a gerçekten tıklanabilir (@mention) bağlantı veriyor —
        # kullanıcı isteği: "açıklamalarda bu tarz olsun" (2026-09-07).
        if theme_key == "dj":
            follow_line = (
                f"Subscribe to the {config.STATIC_LABEL_TEXT} channel 👉 "
                f"@{config.YOUTUBE_HANDLE}\n"
                f"Follow the journey on Instagram 👉 {links['instagram']}"
            )
    else:
        discovery_hashtags = config.DISCOVERY_HASHTAGS
        hook = pick_deterministic(title, config.HOOK_LINES)
        engagement_question = pick_deterministic(title, config.ENGAGEMENT_QUESTIONS, salt=7)
        follow_line = "Yeni şarkılar için takipte kalın 🎵"
        # "dj" (DJ Famous) enstrümantal/canlı set, "sözleri" arama niyeti taşımıyor —
        # sadece ana kataloğun şarkı temalarına uygulanıyor. Video başlığına arama
        # niyeti (Türkçe dinleyicilerin en sık arama kalıbı: "<şarkı adı> sözleri")
        # eklendi — eskiden başlık sadece şarkı adıydı, YouTube arama trafiği
        # neredeyse sıfırdı (Studio analitiğiyle doğrulandı, 2026-09-06).
        if theme_key == "dj":
            video_title = title
            lyrics_tags = []
        elif derleme:
            # "(Sözleri)" EKİ YOK: derlemenin sözleri yok, 13 ayrı şarkının
            # sözleri var — "<ad> sözleri" arama niyetiyle yayınlamak izleyiciyi
            # yanlış beklentiyle getirir (ve "Hip-Hop Şarkısı" demek 39 dakikalık
            # karma bir derleme için düpedüz yanlıştı). Başlık artık ne olduğunu
            # söylüyor: kaç şarkılık, hangi türde bir DERLEME.
            _adet = len(meta.get("derleme_liste") or [])
            _sayi = f"{_adet} Şarkılık " if _adet else ""
            video_title = f"{title} | {_sayi}Türkçe {derleme_tur} Derlemesi"
            lyrics_tags = []
        else:
            video_title = f"{title} (Sözleri) | Türkçe {theme['label']} Şarkısı"
            lyrics_tags = [f"{title} sözleri", "sözleri", "lyrics"]

    if derleme:
        genre_hashtags = [hashtag(t) for t in derleme_etiketleri] + ["#Derleme", "#Mix"]
    else:
        genre_hashtags = ([hashtag(theme["label"])]
                          + [hashtag(t) for t in theme.get("related", [])]
                          + [hashtag(t) for t in stil_etiketleri(meta)])
    hashtags = " ".join(config.BRAND_HASHTAGS + discovery_hashtags + genre_hashtags)

    # Derleme parca listesi -> YouTube BOLUMLERI (chapters).
    # YouTube'un kurali: ilk damga 0:00 olmali, en az 3 bolum, her biri >=10 sn.
    # derleme.py bu ucunu de sagliyor. Bolumler hem gezinmeyi kolaylastiriyor
    # hem de "inauthentic content" politikasina karsi kuratorluk sinyali veriyor
    # (bkz. derleme.py modul notu) - toplu uretim degil, secilmis bir liste.
    # Kuratorluk gerekcesi -> aciklamanin BASINA, bolum listesinden once.
    # Incelemeci aciklamaya bakiyor; katkinin ne oldugunu yazili gormeli.
    _not = meta.get("derleme_notu")
    kurator = ("\n\n" + _not) if _not else ""

    bolumler = ""
    _liste = meta.get("derleme_liste") or []
    if len(_liste) >= 3:
        _satirlar = [("%s %s" % (x["zaman"], x["ad"])) for x in _liste]
        bolumler = "\n\nParçalar:\n" + "\n".join(_satirlar)

    description = (
        f"{hook}\n\n{title} | {config.STATIC_LABEL_TEXT}{kurator}{bolumler}\n\n"
        f"{follow_line}\n\n"
        f"📷 Instagram: {links['instagram']}\n"
        f"🎵 TikTok: {links['tiktok']}\n"
        f"🌐 Website: {links['website']}\n\n"
        f"{engagement_question}\n\n"
        f"{hashtags}"
    )
    # Tags (arama/öneri sinyali, açıklamada görünmez) — tema etiketlerine ek olarak
    # keşfet hashtag'lerinin # işaretsiz hâli de eklendi (eskiden sadece tema +
    # STATIC_LABEL_TEXT vardı, YouTube'un izin verdiği alana kıyasla dardı).
    tags = genre_tags + [config.STATIC_LABEL_TEXT] + [h.lstrip("#") for h in discovery_hashtags] + lyrics_tags

    return {
        "title": video_title,
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
        # Video dili AYARLANMALI. Boş bırakılınca YouTube tahmin ediyor ve
        # Türkçe şarkıları "İngilizce (ABD)" olarak işaretliyor — Studio'da
        # üç videoda doğrulandı (2026-09-10). Sonuçları: otomatik altyazı
        # (ASR) yanlış dilde deneniyor ya da hiç üretilmiyor, otomatik çeviri
        # ve dublaj yanlış kaynaktan türüyor, öneri algoritması yanlış
        # kitleye gösteriyor. resolve_language() zaten stile göre "tr"/"en"
        # veriyor (DJ Famous "en", ana katalog "tr").
        "defaultLanguage": resolve_language(meta),
        "defaultAudioLanguage": resolve_language(meta),
    }


def build_shorts_snippet(meta: dict, full_video_id: str | None = None) -> dict:
    """Shorts (shorts_9x16.mp4, 45sn highlight) için ayrı bir snippet — uzun format
    künyesi yerine TikTok/Instagram'la AYNI kısa-format caption'ı kullanıyor
    (social_text.build_caption: hook + hashtag'ler + etkileşim sorusu), çünkü
    Shorts algoritması da hashtag/hook odaklı kısa video mantığıyla çalışıyor.
    Başlığa "#Shorts" ekleniyor (YouTube'un Shorts sınıflandırması için ek sinyal —
    video zaten <=60sn ve dikey olduğu için asıl belirleyici bu değil ama önerilen
    pratik). full_video_id verilmişse, izleyiciyi kanaldaki tam versiyona
    yönlendiren bir satır ekleniyor."""
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    # Shorts başlığında "(Sözleri)" zaten yoktu, ama ETİKETLER uzun formattaki
    # aynı hatayı taşıyordu: derlemenin Short'u meta'daki tek `theme` yüzünden
    # "Hip-Hop/Trap/Rap" etiketleniyordu. Uzun formatla AYNI kaynaktan türet.
    if meta.get("derleme"):
        genre_tags = _derleme_tur_bilgisi(meta)[1] + ["Derleme", "Mix", "Karışık Müzik"]
    else:
        genre_tags = [theme["label"]] + theme.get("related", []) + stil_etiketleri(meta)

    description = build_caption(meta)
    if full_video_id:
        description += f"\n\n🎧 Şarkının tamamı kanalımızda: https://youtu.be/{full_video_id}"

    discovery_hashtags = config.DISCOVERY_HASHTAGS_EN if resolve_language(meta) == "en" else config.DISCOVERY_HASHTAGS
    tags = genre_tags + [config.STATIC_LABEL_TEXT, "Shorts"] + [h.lstrip("#") for h in discovery_hashtags]

    return {
        "title": f"{title} #Shorts",
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
        # Video dili AYARLANMALI. Boş bırakılınca YouTube tahmin ediyor ve
        # Türkçe şarkıları "İngilizce (ABD)" olarak işaretliyor — Studio'da
        # üç videoda doğrulandı (2026-09-10). Sonuçları: otomatik altyazı
        # (ASR) yanlış dilde deneniyor ya da hiç üretilmiyor, otomatik çeviri
        # ve dublaj yanlış kaynaktan türüyor, öneri algoritması yanlış
        # kitleye gösteriyor. resolve_language() zaten stile göre "tr"/"en"
        # veriyor (DJ Famous "en", ana katalog "tr").
        "defaultLanguage": resolve_language(meta),
        "defaultAudioLanguage": resolve_language(meta),
    }


def _upload(video_path: str, snippet: dict, privacy: str, publish_at: str | None = None) -> str:
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    youtube = get_authenticated_service()

    # publish_at verilmişse (bkz. config.next_golden_publish_time): video ŞİMDİ
    # private olarak yüklenir, YouTube belirtilen zamanda OTOMATİK public'e
    # çevirir — publishAt sadece privacyStatus="private" ile birlikte kabul
    # ediliyor (resmi API kısıtı). Böylece render/upload anı (auto_process.py'nin
    # kendi kademeleme mantığı) ile videonun canlıya çıktığı an (golden-hour
    # penceresi) birbirinden ayrılıyor.
    status = {
        "selfDeclaredMadeForKids": False,
        # containsSyntheticMedia: YouTube'un "altered or synthetic content" açıklama
        # zorunluluğunun API karşılığı (Ekim 2024'te eklendi, resmi kaynak:
        # support.google.com/youtube/answer/14328491 ve developers.google.com/youtube/
        # v3/revision_history). Bu kanalın TÜM içeriği (vokal+beste+kapak+video) AI
        # üretimi olduğu için True olarak işaretleniyor — hem uzun format hem Shorts
        # (ikisi de bu _upload()'ı kullanıyor).
        "containsSyntheticMedia": True,
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = privacy

    body = {"snippet": snippet, "status": status}

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    if publish_at:
        print(f"  yükleniyor: {snippet['title']} (zamanlı: {publish_at}'te public olacak)")
    else:
        print(f"  yükleniyor: {snippet['title']} ({privacy})")
    response = None
    while response is None:
        try:
            # num_retries=3: googleapiclient'ın kendi kaynağına göre varsayılan 0
            # ("isteği sadece bir kez dener") — yani bu olmadan uzun bir upload
            # sırasındaki geçici bir ağ kesintisi/5xx hatası TÜM yüklemeyi anında
            # iptal ediyordu, bir sonraki deneme saatler sonraki bir sonraki
            # zamanlanmış çalıştırmaya kalıyordu. 3, kütüphanenin kendi exponential
            # backoff'unu (HttpError 5xx ve bağlantı hataları için) devreye sokar.
            status, response = request.next_chunk(num_retries=3)
            if status:
                print(f"    %{int(status.progress() * 100)}")
        except HttpError as e:
            print(f"  HATA: {e}")
            raise

    return response["id"]


def _en_yeni_kapak(project_dir: str, names: list) -> str | None:
    """Verilen adaylar arasından EN YENİ (mtime) olanı döndürür, birden fazla
    aday varsa UYARI basar.

    NEDEN: eskiden liste sırasıyla İLK eşleşen dönüyordu — yani `cover.jpg`
    her zaman `cover.png`'yi yeniyordu, oysa kapak üreticisi
    (`generate_cover.py`) `cover.png` yazıyor. Bir projede eski bir
    `cover.jpg` kalmışsa yenilenen PNG SESSİZCE yok sayılıyor ve ESKİ kapak
    yükleniyordu; hiçbir hata mesajı yoktu. Uyarı satırı bilerek var: asıl
    arıza yanlış dosyanın seçilmesi değil, seçimin sessiz olmasıydı."""
    adaylar = [
        os.path.join(project_dir, ad)
        for ad in names
        if os.path.isfile(os.path.join(project_dir, ad))
    ]
    if not adaylar:
        return None
    # Eşit mtime'da liste sırası korunsun diye sıralama kararlı (stable) kullanılıyor.
    adaylar.sort(key=os.path.getmtime, reverse=True)
    if len(adaylar) > 1:
        digerleri = ", ".join(os.path.basename(p) for p in adaylar[1:])
        print(
            f"  UYARI: birden fazla kapak adayı var ({os.path.basename(project_dir)}), "
            f"en yenisi kullanılıyor: {os.path.basename(adaylar[0])} "
            f"(yok sayılan: {digerleri})"
        )
    return adaylar[0]


def _find_cover(project_dir: str) -> str | None:
    return _en_yeni_kapak(project_dir, COVER_NAMES)


def _find_cover_vertical(project_dir: str) -> str | None:
    """Shorts thumbnail'i için 9:16 kapak — yoksa (eski projeler) 16:9 cover.png'ye
    düşülür (hiç thumbnail'siz kalmaktan iyidir, sadece Shorts'un dikey kutusunda
    üstte/altta ince bir şerit görünebilir)."""
    dikey = _en_yeni_kapak(project_dir, COVER_VERTICAL_NAMES)
    if dikey:
        return dikey
    return _find_cover(project_dir)


def _prepare_thumbnail_jpeg(cover_path: str) -> str:
    """YouTube thumbnails.set 2MB sınırı var — procedural PNG kapaklar (bokeh
    dokusu yüzünden) bunu kolayca aşabiliyor (bir projede 2.7MB'a çıktığı
    görüldü). Kaynak boyutuna bakmadan HER ZAMAN güvenli bir JPEG'e yeniden
    kodluyoruz (PNG boyutu içerik gürültüsüne göre öngörülemez), geçici bir
    dosyaya yazıp döndürüyoruz — çağıran temizlemekten sorumlu."""
    tmp_path = cover_path + "._thumb_tmp.jpg"
    cmd = ["ffmpeg", "-y", "-i", cover_path, "-q:v", "3", tmp_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Thumbnail JPEG'e dönüştürülemedi: {result.stderr[-500:]}")
    return tmp_path


def upload_thumbnail(youtube, video_id: str, project_dir: str, vertical: bool = False) -> None:
    """cover.jpg/png'yi (ya da Shorts için cover_vertical.jpg/png'yi) videonun
    gerçek YouTube thumbnail'i olarak ayarlar. Bunsuz YouTube videodan rastgele
    bir kare seçip thumbnail yapıyordu — kartın başlıksız hâli (art.jpg)
    görünüyordu, tasarlanan başlıklı kapak hiç kullanılmıyordu (kullanıcı geri
    bildirimiyle tespit edildi). vertical=True (Shorts) iken 9:16 kapak
    kullanılır — uzun-format için 16:9 kapağın aynısını kullanmak dikey
    thumbnail kutusunda üstte/altta çirkin bir şeride yol açıyordu (yine
    kullanıcı geri bildirimiyle tespit edildi)."""
    cover_path = _find_cover_vertical(project_dir) if vertical else _find_cover(project_dir)
    if not cover_path:
        print("  Thumbnail atlandı: cover.jpg/png bulunamadı")
        return

    tmp_path = _prepare_thumbnail_jpeg(cover_path)
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(tmp_path, mimetype="image/jpeg"),
        ).execute()
        print("  Thumbnail: tamam")
    finally:
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)


def _update_state(project_dir: str, fields: dict) -> None:
    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state.update(fields)
    # ATOMIK yazim (state_io): bu fonksiyon video ID'si / yukleme damgasi gibi
    # YENIDEN URETILEMEYEN alanlari yaziyor ve tam da uzun bir yukleme bittikten
    # SONRA cagriliyor. Dogrudan `open(..., "w")` hedefi once sifirliyordu —
    # yarida kesilen bir yazim hem bu kaydi hem dosyanin eski icerigini
    # kaybettiriyordu. Ayrica uyumluluk._durum() bozuk state.json'da artik HATA
    # uretip boru hattini durduruyor.
    state_io._atomik_yaz(state_path, state)


def _compute_publish_at(privacy: str, schedule: bool) -> str | None:
    """privacy="public" ve schedule=True ise, şu an bir golden-hour penceresinin
    (config.GOLDEN_HOURS) dışındaysak bir sonraki pencerenin başlangıcını UTC
    ISO8601 ("...Z") olarak döner — içindeysek (ya da schedule kapalıysa/privacy
    public değilse) None döner, hemen (zamanlamasız) yüklenir."""
    if privacy != "public" or not schedule:
        return None
    target = config.next_golden_publish_time()
    if target is None:
        return None
    return target.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def upload_video(project_dir: str, privacy: str, schedule: bool = True) -> str:
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    meta = load_meta(project_dir)
    snippet = build_snippet(meta)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtu.be/{video_id}")

    youtube = get_authenticated_service()
    try:
        upload_thumbnail(youtube, video_id, project_dir, vertical=False)
    except Exception as e:
        # Thumbnail başarısız olsa da video zaten yüklendi — akışı durdurmuyoruz,
        # sadece uyarıyoruz. Video YouTube'un otomatik seçtiği kareyle kalır.
        print(f"  Thumbnail HATA: {e}")

    _update_state(project_dir, {
        "youtube_video_id": video_id,
        "youtube_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_privacy": privacy,
        "youtube_publish_at": publish_at,
    })
    return video_id


def upload_short(project_dir: str, privacy: str, full_video_id: str | None = None, schedule: bool = True) -> str:
    """shorts_9x16.mp4'ü uzun formattan BAĞIMSIZ, ayrı bir YouTube video'su (Short)
    olarak yükler. full_video_id verilmişse açıklamada tam versiyona bağlantı verir."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    meta = load_meta(project_dir)
    snippet = build_shorts_snippet(meta, full_video_id)

    publish_at = _compute_publish_at(privacy, schedule)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtube.com/shorts/{video_id}")

    try:
        upload_thumbnail(get_authenticated_service(), video_id, project_dir, vertical=True)
    except Exception as e:
        # upload_video()'daki ile aynı mantık: thumbnail başarısız olsa da video
        # zaten yüklendi, akışı durdurmuyoruz. Shorts'ta özel thumbnail YouTube
        # Partner Program üyeliğine bağlı olabilir (2026 itibariyle) — HATA
        # burada "desteklenmiyor" anlamına da gelebilir, "video bozuk" değil.
        print(f"  Thumbnail HATA: {e}")

    _update_state(project_dir, {
        "youtube_shorts_video_id": video_id,
        "youtube_shorts_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_shorts_privacy": privacy,
        "youtube_shorts_publish_at": publish_at,
    })
    return video_id


def _golden_publish_at(gun_ertele: int = 0) -> str:
    """`gun_ertele` gun SONRAKI ilk golden-hour'u UTC ISO8601 ("...Z") olarak doner.

    _compute_publish_at ile AYNI mekanizma (config.next_golden_publish_time),
    tek fark baslangic aninin ileri kaydirilmasi -- ikinci dalga kesitleri
    (bkz. dj_clips.py) setin kendi yayin gunune binmesin diye. Yeni bir
    zamanlama mantigi YOK, var olan fonksiyona baska bir `now` veriliyor.

    TUZAK: next_golden_publish_time, verilen an ZATEN bir golden-hour
    penceresinin icindeyse None doner ("hemen yayinla" demek). Burada None'i
    "zamanlama yok"a cevirmek kesidi BUGUN yayinlardi -- tam kacinmak
    istedigimiz sey. O yuzden None gelirse kaydirilmis anin KENDISI
    kullaniliyor (o an zaten bir golden-hour).
    """
    hedef = datetime.now(config.TR_TZ) + timedelta(days=max(0, gun_ertele))
    sonraki = config.next_golden_publish_time(hedef)
    if sonraki is not None:
        hedef = sonraki
    return hedef.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _dakika_damgasi(saniye: float) -> str:
    """123.4 -> "2:03" — kesidin setin neresinden geldigini gosteren damga."""
    tam = max(0, int(saniye))
    return "%d:%02d" % (tam // 60, tam % 60)


def build_clip_snippet(meta: dict, full_video_id: str | None, bas_sn: float) -> dict:
    """Ikinci dalga kesiti (output/clip_XX.mp4, bkz. dj_clips.py) icin snippet.

    build_shorts_snippet'ten AYRI olmasinin tek sebebi BASLIK ve aciklamanin
    ilk satiri. Kesit, setin kendi Shorts'uyla ayni baslikta ("<set> #Shorts")
    cikarsa kanalda ayni adla iki neredeyse-ayni video olur -- bu, YouTube'un
    "inauthentic content" politikasindaki (15 Temmuz 2025'te "repetitious
    content"ten yeniden adlandirildi) tekrarlayici icerik tarifinin ta
    kendisi. Baslikta ve aciklamanin ilk satirinda kesidin setin HANGI
    dakikasindan geldigi ACIKCA yaziyor: hem izleyici icin bilgi, hem de
    inceleyen bir insan icin kuratorluk sinyali -- derleme.py'deki
    `derleme_notu`nun aciklamanin basina konmasiyla AYNI gerekce.
    """
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_tags = [theme["label"]] + theme.get("related", []) + stil_etiketleri(meta)

    damga = _dakika_damgasi(bas_sn)
    lang = resolve_language(meta)
    if lang == "en":
        video_title = f"{title} — Set Highlight {damga} #Shorts"
        kurator = f"A different moment from the same set, starting at {damga}."
        tam_satir = "🎧 Full set on the channel: https://youtu.be/%s"
    else:
        video_title = f"{title} — Setin {damga} Anı #Shorts"
        kurator = f"Aynı setin farklı bir anı — {damga} dakikasından."
        tam_satir = "🎧 Setin tamamı kanalımızda: https://youtu.be/%s"

    description = kurator + "\n\n" + build_caption(meta)
    if full_video_id:
        description += "\n\n" + (tam_satir % full_video_id)

    discovery_hashtags = config.DISCOVERY_HASHTAGS_EN if lang == "en" else config.DISCOVERY_HASHTAGS
    tags = genre_tags + [config.STATIC_LABEL_TEXT, "Shorts"] + [h.lstrip("#") for h in discovery_hashtags]

    return {
        "title": video_title,
        "description": description,
        "tags": tags,
        "categoryId": "10",  # Music
        "defaultLanguage": lang,
        "defaultAudioLanguage": lang,
    }


def upload_clip(project_dir: str, clip_name: str, full_video_id: str | None = None,
                bas_sn: float = 0.0, gun_ertele: int = 0,
                privacy: str = "public") -> tuple[str, str]:
    """output/<clip_name>'i ayri bir Short olarak, `gun_ertele` gun sonraki
    golden-hour'a ZAMANLANMIS sekilde yukler. (video_id, publish_at) doner.

    upload_short'tan AYRI bir fonksiyon: o `shorts_9x16.mp4`'u sabit kodluyor
    ve state'e `youtube_shorts_*` yaziyor -- kesitte ikisi de yanlis olurdu
    (dosya farkli; ayni anahtarlara yazmak setin kendi Shorts kaydini ezerdi).

    state.json'a BURADA yazilmiyor (upload_video/upload_short'tan farkli olarak):
    kesit alanlarinin sahibi dj_clips.kesit_yayinla -- hangi kesidin gittigi,
    tekrar gonderilmemesi ve kuresel tempo ayni yerden yonetiliyor.
    """
    video_path = os.path.join(project_dir, "output", clip_name)
    meta = load_meta(project_dir)
    snippet = build_clip_snippet(meta, full_video_id, bas_sn)

    # gun_ertele HER ZAMAN uygulaniyor (privacy/schedule bayraklarina
    # bakilmiyor): kesidin gecikmesi bir "guzel olsa iyi olur" degil, yayin
    # hacmi kisitinin kendisi. --no-schedule gibi bir bayrakla kazara
    # kapatilabilir olmamali.
    publish_at = _golden_publish_at(gun_ertele)
    video_id = _upload(video_path, snippet, privacy, publish_at=publish_at)
    print(f"  tamam: https://youtube.com/shorts/{video_id} (yayin: {publish_at})")

    try:
        upload_thumbnail(get_authenticated_service(), video_id, project_dir, vertical=True)
    except Exception as e:
        print(f"  Thumbnail HATA: {e}")

    return video_id, publish_at


def fix_thumbnail(project_dir: str) -> None:
    """Zaten yüklenmiş video(lar) için thumbnail'i (yeniden) ayarlar — video
    upload_thumbnail eklenmeden ÖNCE yüklendiyse YouTube'un rastgele seçtiği
    kareyle kalmıştı, bu onu düzeltir. state.json'dan youtube_video_id VE
    (varsa) youtube_shorts_video_id okur, ikisini de dener."""
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        print(f"  HATA: {state_path} yok — bu proje hiç yüklenmemiş.")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    shorts_id = state.get("youtube_shorts_video_id")
    if not video_id and not shorts_id:
        print("  HATA: state.json'da youtube_video_id/youtube_shorts_video_id yok.")
        return

    youtube = get_authenticated_service()
    if video_id:
        print("  uzun format:")
        upload_thumbnail(youtube, video_id, project_dir, vertical=False)
    if shorts_id:
        print("  Shorts:")
        try:
            upload_thumbnail(youtube, shorts_id, project_dir, vertical=True)
        except Exception as e:
            print(f"  Shorts thumbnail HATA: {e}")


def _kok_yolu(base: str) -> str:
    """Kök adını (ya da göreli yolu) repo köküne bağlar.

    NEDEN: `os.path.isdir("projects")` cwd'ye BAĞLI — script başka bir klasörden
    çağrıldığında False döner ve toplu düzeltme hiçbir proje bulamadan SESSİZCE
    biter (bu deponun en sık arızası; aynı not `uyumluluk.KOKLER`'de de var).
    Mutlak bir yol verilirse `os.path.join` onu olduğu gibi döndürür, yani elle
    mutlak yol geçen çağıranlar bozulmaz.
    """
    return os.path.join(REPO_DIR, base)


def fix_all_thumbnails(bases: tuple[str, ...] = uyumluluk.KOK_ADLARI) -> None:
    """--thumbnail-only --all: bases altındaki, YouTube'a zaten yüklü (state.json'da
    youtube_video_id ve/veya youtube_shorts_video_id olan) TÜM projelerin
    thumbnail'ini tek seferde düzeltir. Zaten doğru kapakla yüklü videolarda da
    tekrar çağırmak güvenlidir (thumbnails().set() üzerine yazar, idempotent).
    Varsayılan ÜÇ içerik kökünün hepsi (`uyumluluk.KOK_ADLARI`): ana katalog
    (`projects/`), DJ Famous setleri (`dj_sets/`) ve derlemeler (`derlemeler/`).
    NEDEN kök listesi burada ELLE sayılmıyor: varsayılan önce `("projects",)`,
    sonra `("projects", "dj_sets")` idi ve her genişlemede bir kök unutuldu —
    City Pulse Set'in kapağı YouTube'da hiç görünmüyordu (kullanıcı bildirdi),
    aynı arıza `derlemeler/` eklenince bir derlemenin kapağı için tekrar
    edecekti. Tek kanonik kaynak `uyumluluk.KOK_ADLARI`
    (muhafız: tests/test_kok_listesi_muhafizi.py)."""
    for base in bases:
        kok = _kok_yolu(base)
        if not os.path.isdir(kok):
            continue
        _fix_all_thumbnails_in(kok)


def _fix_all_thumbnails_in(base: str) -> None:
    for name in sorted(os.listdir(base)):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        state_path = os.path.join(project_dir, "state.json")
        if not os.path.isfile(state_path):
            continue
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not state.get("youtube_video_id") and not state.get("youtube_shorts_video_id"):
            continue
        print(f"\n=== {name} ===")
        try:
            fix_thumbnail(project_dir)
        except Exception as e:
            print(f"  HATA: {e}")


def fix_description(project_dir: str) -> None:
    """Zaten yüklenmiş video(lar) için açıklamayı (description/title/tags) güncel
    build_snippet()/build_shorts_snippet() çıktısıyla YENİDEN yazar — video
    upload_thumbnail'daki gibi, videoyu tekrar yüklemeden. Bazı eski videolar
    (özellikle Shorts) açıklama eklenmeden ÖNCEki bir kod sürümüyle yüklendiği
    için eksik/boş açıklamayla kalmıştı (kullanıcı geri bildirimiyle tespit
    edildi, 2026-09-05) — bu onu düzeltir. state.json'dan youtube_video_id VE
    (varsa) youtube_shorts_video_id okur, ikisini de dener. videos().update
    part="snippet" TÜM snippet alanlarını (categoryId dahil) üzerine yazdığı
    için build_snippet/build_shorts_snippet'in ürettiği TAM snippet gönderiliyor,
    eksik alan bırakmıyor."""
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        print(f"  HATA: {state_path} yok — bu proje hiç yüklenmemiş.")
        return
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    shorts_id = state.get("youtube_shorts_video_id")
    if not video_id and not shorts_id:
        print("  HATA: state.json'da youtube_video_id/youtube_shorts_video_id yok.")
        return

    meta = load_meta(project_dir)
    youtube = get_authenticated_service()

    if video_id:
        print("  uzun format:")
        snippet = build_snippet(meta)
        youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
        print("  Açıklama: tamam")
    if shorts_id:
        print("  Shorts:")
        try:
            snippet = build_shorts_snippet(meta, video_id)
            youtube.videos().update(part="snippet", body={"id": shorts_id, "snippet": snippet}).execute()
            print("  Açıklama: tamam")
        except Exception as e:
            print(f"  Shorts açıklama HATA: {e}")


def fix_all_descriptions(bases: tuple[str, ...] = uyumluluk.KOK_ADLARI) -> None:
    """--description-only --all: fix_all_thumbnails ile aynı desen — bases
    altındaki, YouTube'a zaten yüklü TÜM projelerin açıklamasını tek seferde
    günceller. Idempotent (üzerine yazar), zaten doğru olan projelerde de
    güvenle tekrar çağrılabilir. Varsayılan üç içerik kökünün hepsi
    (`uyumluluk.KOK_ADLARI`) — gerekçe fix_all_thumbnails'te."""
    for base in bases:
        kok = _kok_yolu(base)
        if not os.path.isdir(kok):
            continue
        _fix_all_descriptions_in(kok)


def _fix_all_descriptions_in(base: str) -> None:
    for name in sorted(os.listdir(base)):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        state_path = os.path.join(project_dir, "state.json")
        if not os.path.isfile(state_path):
            continue
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not state.get("youtube_video_id") and not state.get("youtube_shorts_video_id"):
            continue
        print(f"\n=== {name} ===")
        try:
            fix_description(project_dir)
        except Exception as e:
            print(f"  HATA: {e}")


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi YouTube'a yükler.")
    parser.add_argument(
        "--project", help="Proje klasörü (örn. projects/sarki-adi) — --thumbnail-only --all ile kullanılmaz",
    )
    parser.add_argument(
        "--privacy", default="private", choices=["private", "unlisted", "public"],
        help="Yükleme görünürlüğü (varsayılan: private)",
    )
    parser.add_argument(
        "--shorts", action="store_true",
        help="Uzun format yerine (veya sonrasında) shorts_9x16.mp4'ü ayrı bir YouTube Short olarak yükle",
    )
    parser.add_argument(
        "--thumbnail-only", action="store_true",
        help="Video zaten yüklüyse (state.json'da youtube_video_id/youtube_shorts_video_id "
             "varsa) sadece thumbnail'i (yeniden) ayarlar, videoyu tekrar yüklemez — geriye "
             "dönük düzeltme için. --project ile tek proje, --all ile TÜM projeler.",
    )
    parser.add_argument(
        "--description-only", action="store_true",
        help="Video zaten yüklüyse sadece açıklama/başlık/etiketleri (yeniden) günceller, "
             "videoyu tekrar yüklemez — güncel build_snippet()/build_shorts_snippet() "
             "çıktısıyla geriye dönük düzeltme için. --project ile tek proje, --all ile "
             "TÜM projeler.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="--thumbnail-only ya da --description-only ile birlikte: projects/ (+ dj_sets/) "
             "altındaki YouTube'a zaten yüklü TÜM projeleri tek seferde düzeltir.",
    )
    parser.add_argument(
        "--no-schedule", action="store_true",
        help="privacy=public olsa bile golden-hour zamanlamasını (config.GOLDEN_HOURS) "
             "devre dışı bırakıp hemen public yükler.",
    )
    args = parser.parse_args()

    if args.thumbnail_only and args.description_only:
        parser.error("--thumbnail-only ve --description-only aynı anda kullanılamaz")
    elif args.thumbnail_only and args.all:
        fix_all_thumbnails()
    elif args.thumbnail_only:
        if not args.project:
            parser.error("--thumbnail-only için --project ya da --all gerekli")
        fix_thumbnail(args.project)
    elif args.description_only and args.all:
        fix_all_descriptions()
    elif args.description_only:
        if not args.project:
            parser.error("--description-only için --project ya da --all gerekli")
        fix_description(args.project)
    elif not args.project:
        parser.error("--project gerekli (ya da --thumbnail-only/--description-only --all)")
    elif args.shorts:
        upload_short(args.project, args.privacy, schedule=not args.no_schedule)
    else:
        upload_video(args.project, args.privacy, schedule=not args.no_schedule)


if __name__ == "__main__":
    main()
