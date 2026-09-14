"""Yayındaki TÜM şarkıları listeleyen `docs/latest.html`'i günceller.

NEDEN VAR: Instagram/TikTok'ta caption/yorum içindeki linkler tıklanamıyor
(platform kısıtı, WebSearch ile doğrulandı) — tek gerçekten tıklanabilir yer
profildeki "bio link". Kullanıcı bio linkini `famousmusicstudio.com/latest.html`
olarak ayarlayınca, herhangi bir paylaşımı gören biri bio'ya gittiğinde bu
sayfada TÜM yayındaki şarkıları (en yeni en üstte) görüp istediğine tıklayarak
YouTube'a ulaşabiliyor — sadece "en son"a değil, ESKİ bir paylaşımı görüp gelen
biri de aradığı şarkıyı bulabiliyor.

auto_process.py, her koşusunun `finally` bloğunda (`_refresh_latest_listing`)
regenerate()'i çağırıp `git_sync.push_path()` ile SADECE bu dosyayı commit'leyip
push ediyor (kullanıcı onayı, 2026-09-05 — projects/*/state.json gibi diğer
commit'siz değişikliklere dokunmuyor).

TASARIM NOTLARI (2026-09-11 denetimi — bkz. CLAUDE.md "sessiz arıza"):

- **Sayfa MOBİL bir sayfadır, masaüstü değil**: izleyicilerin tamamı
  Instagram/TikTok uygulamasının İÇİNDEKİ tarayıcıdan geliyor. Bu yüzden
  dış yazı tipi/CDN bağlantısı YOK (eskiden Google Fonts'tan iki `preconnect`
  + bir render-bloklayan stylesheet vardı — yavaş mobil bağlantıda ilk
  boyamayı geciktiren, markaya hiçbir dönüşüm getirmeyen bir maliyet),
  dokunma hedefleri en az 56 px, yazı 16 px.
- **Görseller YouTube'un KENDİ küçük resmi** (`i.ytimg.com/vi/<id>/mqdefault.jpg`):
  depoya 40 kapak kopyalamak yerine kaynağından çekiliyor, böylece kapak
  yenilendiğinde (`youtube_thumbnail_updated_at`) sayfa kendiliğinden
  güncel kalıyor. Yüklenemezse satır yine tıklanabilir — tasarım görsele
  BAĞIMLI değil.
- **Yayınlanmamış içerik sızıntısına karşı İKİ kapı var**: `youtube_privacy`
  alanı state.json'a EN SON BİZİM yazdığımızın aynası, YouTube'daki canlı
  gerçek değil (ör. `upload/set_privacy.py` videoyu unlisted'a çekerken
  state.json'a HİÇBİR ŞEY yazmıyor). Bu yüzden Content ID karantinası
  bayrakları (`dj_tarama_bekliyor`/`dj_tarama_engelli`) privacy alanından
  BAĞIMSIZ olarak ayrıca kontrol ediliyor."""

import glob
import html
import json
import os
import re
from datetime import datetime, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(REPO_DIR, "docs")
LATEST_HTML_PATH = os.path.join(DOCS_DIR, "latest.html")

# Sayfaya giren TÜM kökler, (klasör, başlık) — gösterim sırasıyla.
# NEDEN LİSTE: `derlemeler/` buraya HİÇ eklenmemişti (kök, DJ setleri
# eklenirken gözden kaçtı) — yani derleme hattının tamamı bio linkinden
# görünmez durumdaydı. Yeni bir yayın kökü açılırsa TEK yapılacak iş bu
# listeye bir satır eklemek.
KOKLER = (
    ("projects", "Şarkılar"),
    ("dj_sets", "DJ Famous Setleri"),
    ("derlemeler", "Derlemeler"),
)

# YouTube video kimliği karakter kümesi. Bozuk/beklenmedik bir kimlik
# HTML'e enjeksiyon olarak sızmasın diye satır tamamen atlanıyor.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{5,20}$")


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        # Bozuk/yarım bir state.json'ı "{}" saymak burada GÜVENLİ yön:
        # boş sözlük tüm kapılarda "yayında değil" demek, yani satır
        # listeye GİRMEZ. (uyumluluk.py'deki asimetriyle aynı mantık.)
        return {}
    return data if isinstance(data, dict) else {}


def _already_live(state: dict) -> bool:
    """state.json'daki youtube_privacy="public", golden-hour zamanlaması
    kullanıldığında (youtube_publish_at dolu) videonun O AN gerçekten canlı
    olduğu anlamına GELMİYOR — YouTube, publishAt zamanına kadar videoyu
    private tutup kendisi public'e çeviriyor (bkz. config.next_golden_publish_time,
    youtube_upload.py::_compute_publish_at). publish_at varsa geçmiş olmalı,
    yoksa (zamanlamasız yüklendi) doğrudan public sayılır."""
    publish_at = state.get("youtube_publish_at")
    if not publish_at:
        return True
    try:
        return datetime.fromisoformat(str(publish_at).replace("Z", "+00:00")) <= datetime.now(timezone.utc)
    except ValueError:
        # ESKİDEN burada True dönülüyordu ("anlayamadım, canlı say").
        # Yanlış yön: elimizde bir zamanlama damgası VAR ama okuyamıyoruz —
        # yani video henüz private olabilir. Herkese açık bir sayfada
        # yayınlanmamış içerik listelemenin bedeli, bir satırın bir koşu
        # geç görünmesinden çok daha ağır. Şüphede LİSTELEME.
        return False


def _yayinda_mi(state: dict) -> bool:
    """Bu proje herkese açık bir sayfada listelenebilir mi?

    Üç ayrı kapı (hepsi geçilmeli):
    1. `youtube_privacy == "public"` — unlisted (ör. Küllerimden Geç) ve
       private (ör. karantinadaki bir derleme) dışarıda kalır.
    2. Content ID karantinası — `dj_tarama_bekliyor` (henüz taranıyor,
       YouTube'da private) ya da `dj_tarama_engelli` (engel bulundu, private
       bırakıldı). Bu bayraklar `youtube_privacy`den BAĞIMSIZ kontrol
       ediliyor: dj_tarama_kontrol.py temiz çıkınca privacy'yi "public"e
       çeviriyor, ama ters yönde (yükleme anında) privacy alanı bazı
       akışlarda "public" kalabiliyor — iki bayrağın varlığı tek başına
       "bu video YouTube'da private" demek.
    3. Gerçekten canlı mı (`_already_live`, golden-hour publishAt)."""
    if state.get("youtube_privacy") != "public":
        return False
    if state.get("dj_tarama_bekliyor") or state.get("dj_tarama_engelli"):
        return False
    return _already_live(state)


def _collect(base: str) -> list[tuple[str, str, str]]:
    """(uploaded_at, title, youtube_video_id) üçlülerini, GERÇEKTEN canlı +
    geçerli youtube_video_id olan projeler için, en yeni önce sıralı döner."""
    rows = []
    for state_path in glob.glob(os.path.join(REPO_DIR, base, "*", "state.json")):
        project_dir = os.path.dirname(state_path)
        # `_` ön eki bu depoda "bu klasörü yok say" demek (dj_clips.py,
        # watch_projects.py aynı kuralı uyguluyor: `_arda`, `_iptal`).
        # Burada YOKTU: yayınlanmış bir projeyi `_` ekleyerek arşivleyen
        # kullanıcı boru hattının geri kalanından düşürüyor ama HERKESE AÇIK
        # sayfada listelenmeye devam ediyordu — arşivleme jesti sessizce
        # yarım çalışıyordu. Sızıntı kapısı olarak burası da aynı kuralı uygular.
        if os.path.basename(project_dir).startswith("_"):
            continue
        state = _load_json(state_path)
        video_id = str(state.get("youtube_video_id") or "")
        if not _VIDEO_ID_RE.match(video_id) or not _yayinda_mi(state):
            continue
        meta = _load_json(os.path.join(project_dir, "meta.json"))
        title = meta.get("title") or os.path.basename(project_dir)
        rows.append((str(state.get("youtube_uploaded_at") or ""), str(title), video_id))
    rows.sort(reverse=True)
    return rows


def _section(heading: str, rows: list[tuple[str, str, str]], liste_class: str = "eserler",
             bolum: str = "") -> str:
    if not rows:
        return ""
    items = "\n".join(
        '    <li data-ad="{ad}"><a href="https://youtu.be/{vid}">'
        '<img src="https://i.ytimg.com/vi/{vid}/mqdefault.jpg" alt="" '
        'width="88" height="50" loading="lazy" decoding="async">'
        "<span>{ad}</span></a></li>".format(vid=video_id, ad=html.escape(title))
        for _, title, video_id in rows
    )
    data_bolum = ' data-bolum="{}"'.format(html.escape(bolum)) if bolum else ""
    return '  <h2>{}</h2>\n  <ul class="{}"{}>\n{}\n  </ul>\n'.format(
        html.escape(heading), liste_class, data_bolum, items)


# --- "Bizi takip et" bölümü: TEK KAYNAK -----------------------------------
# Kök sayfa (docs/index.html) ve bio sayfası (docs/latest.html) platform
# linklerini BURADAN alıyor. latest.html her koşuda `regenerate()` ile, kök
# sayfanın işaretli bölgesi `index_takip_guncelle()` ile üretilir
# (`tests/test_takip_linkleri.py` iki sayfanın bu listeyle aynı kaldığını denetler).
#
# Her URL 2026-09-13'te HTTP ile doğrulandı:
# - YouTube: @Famous_musics_studio -> kanal UCbbcH8rtQTtz8R66jfKoSZg
#   (config.YOUTUBE_HANDLE). DİKKAT: youtube.com/@famousmusicstudio BAŞKA bir
#   kanal (UCwqTrdy6ATCWJ4vca-HJH4A) — ASLA kullanma.
# - TikTok / Instagram: config.SOCIAL_HANDLES.
# - Telegram: @hermes_famous_asistan (config.EK_PLATFORMLAR yorumu; t.me
#   sayfa başlığı "Famous Music Studio").
# - Bluesky: famousmusicstudio.bsky.social (upload/bluesky_upload.py; public
#   API displayName "Famous Music Studio").
# - Facebook: sayfa "Famous Music Studio" (Müzisyen/Grup), sayfa kimliği
#   61593802007949; kullanıcı adı `famousmusicstudio` 2026-09-13'te alındı
#   (facebook.com/famousmusicstudio og:url + userID aynı kimliğe gidiyor,
#   elle_islem defteri EI-20260913-125942-87e1).
#
# İkonlar: Simple Icons 13.21.0 (https://simpleicons.org), lisans CC0 1.0 —
# satır içi SVG, dış istek yok. Marka adları/logoları sahiplerinin ticari markasıdır.
PLATFORM_LINKLERI = (
    ("youtube", "YouTube", "https://www.youtube.com/@Famous_musics_studio",
     "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"),
    ("tiktok", "TikTok", "https://www.tiktok.com/@famousmusicstudio",
     "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"),
    ("instagram", "Instagram", "https://www.instagram.com/famous_music_studio/",
     "M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077"),
    ("facebook", "Facebook", "https://www.facebook.com/famousmusicstudio",
     "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"),
    ("telegram", "Telegram", "https://t.me/hermes_famous_asistan",
     "M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"),
    ("bluesky", "Bluesky", "https://bsky.app/profile/famousmusicstudio.bsky.social",
     "M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z"),
)

TAKIP_BASLA = "<!--TAKIP-BASLA-->"
TAKIP_BITIR = "<!--TAKIP-BITIR-->"
# Satır sonları chr() ile: bu depoda kaçış dizileri araç zincirinde yutuldu
# (CLAUDE.md, 'Dosya YAZARKEN ters eğik çizgi yutuluyor').
_LF = chr(10)
_CRLF = chr(13) + chr(10)


def takip_bolumu_html() -> str:
    """"Bizi takip et" bölümünün HTML'i (her iki sayfada birebir aynı)."""
    ogeler = _LF.join(
        '      <li><a class="takip-{k}" href="{url}" target="_blank" rel="noopener" '
        'aria-label="Famous Music Studio {ad} (yeni sekmede açılır)">'
        '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" '
        'aria-hidden="true" focusable="false"><path d="{d}"/></svg>'
        "<span>{ad}</span></a></li>".format(
            k=k, url=html.escape(url, quote=True), ad=html.escape(ad), d=d)
        for k, ad, url, d in PLATFORM_LINKLERI
    )
    return _LF.join((
        '  <section class="takip" aria-labelledby="takip-baslik">',
        '    <h2 id="takip-baslik">Bizi takip et</h2>',
        '    <ul class="takip-liste">',
        ogeler,
        "    </ul>",
        "  </section>",
        "",
    ))


def index_takip_guncelle(yol: str | None = None) -> bool:
    """docs/index.html'deki TAKIP-BASLA/BITIR arasını tek kaynaktan yeniden yazar.

    Saatlik hatta BAĞLI DEĞİL (bilerek): auto_process yalnız latest.html'i
    commit'liyor; kök sayfayı her koşuda yazmak çalışma ağacını kirletip
    `git pull --ff-only`'i tıkayabilirdi. Liste değişince elle çağrılır:
    `python -c "import latest_release; latest_release.index_takip_guncelle()"`.
    Satır sonları korunur. Değişiklik yaptıysa True döner."""
    yol = yol or os.path.join(DOCS_DIR, "index.html")
    with open(yol, "r", encoding="utf-8", newline="") as f:
        eski = f.read()
    bas, bit = eski.find(TAKIP_BASLA), eski.find(TAKIP_BITIR)
    if bas < 0 or bit < bas:
        raise ValueError("index.html'de takip işaretleri yok: " + yol)
    nl = _CRLF if _CRLF in eski else _LF
    govde = (TAKIP_BASLA + _LF + takip_bolumu_html() + "  ").replace(_LF, nl)
    yeni = eski[:bas] + govde + eski[bit:]
    if yeni == eski:
        return False
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(yeni)
    return True


# NEDEN `.format()` DEĞİL, `replace()` (aşağıda): şablon baştan sona CSS
# süslü parantezi içeriyor; `.format()` kullanmak hepsini `{{ }}` diye
# ikilemeyi gerektiriyordu ve tek bir unutulan parantez sayfayı sessizce
# bozuyordu. Tek bir yer tutucu + `replace` bu sınıf hatayı tamamen kaldırıyor.
_YER_TUTUCU = "<!--BOLUMLER-->"
_TAKIP_YER_TUTUCU = "<!--TAKIP-->"

_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Famous Music Studio — Şarkılar</title>
<meta name="description" content="Famous Music Studio'nun tüm yayındaki şarkıları — YouTube'da dinle.">
<meta name="theme-color" content="#0a0806">
<style>
  :root {
    --bg: #0a0806;
    --bg-alt: #131009;
    --text: #ece6da;
    --text-dim: #a89b84;
    --gold: #c9a15a;
    --gold-bright: #e6c17e;
    --border: rgba(201, 161, 90, 0.25);
    --kart: rgba(255, 255, 255, 0.035);
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    min-height: 100vh;
    /* dvh: Instagram/TikTok içi tarayıcıda adres çubuğu kayarken
       100vh yanlış (fazla) yükseklik veriyor. Destekleyen tarayıcı
       ikinci satırı alır, desteklemeyen birinciyle kalır. */
    min-height: 100dvh;
    background-color: var(--bg);
    background-image: radial-gradient(ellipse at 50% 0%, var(--bg-alt) 0%, var(--bg) 65%);
    color: var(--text);
    /* Sistem yazı tipi yığını — dış yazı tipi indirmesi YOK (bkz. modül
       docstring'i: in-app tarayıcıda render-bloklayan istek). */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    -webkit-text-size-adjust: 100%;
    padding: 4vh 1rem calc(4vh + env(safe-area-inset-bottom, 0px));
  }

  main { max-width: 60rem; width: 100%; margin: 0 auto; }

  /* Marka bloğu: logo + ad + slogan. Logo ortada, altın hale — ana
     sayfadaki (index.html) aynı kimlik diliyle. */
  .kimlik { text-align: center; margin-bottom: 0.8rem; }

  .logo-wrap {
    position: relative;
    width: clamp(72px, 16vw, 96px);
    margin: 0 auto 0.85rem;
    border-radius: 50%;
    overflow: hidden;
    box-shadow:
      0 0 22px 5px rgba(230, 193, 126, 0.4),
      0 0 60px 12px rgba(201, 161, 90, 0.25);
  }

  .logo {
    display: block;
    width: 100%;
    height: auto;
    filter: brightness(1.15) saturate(1.3) contrast(1.1);
  }

  h1 {
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 600;
    font-size: clamp(1.45rem, 4.5vw, 1.8rem);
    margin: 0 0 0.2rem;
    color: var(--gold-bright);
  }

  .alt {
    margin: 0 0 0.2rem;
    text-align: center;
    font-size: 0.84rem;
    color: var(--text-dim);
  }

  h2 {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 1.9rem 0 0.8rem;
  }
  /* Bölüm başlığının iki yanında ince altın çizgi — düz metinden
     ayrıştırıyor. (Yalnız içerik bölümleri; takip başlığı ortalanır.) */
  h2::before, h2::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border) 30%, var(--border) 70%, transparent);
  }

  ul { list-style: none; margin: 0; padding: 0; }

  /* Arama motoru: kutu + bölüm filtre çipleri. Satır içi script — dış
     istek YOK (ağ kapalıyken sayfa tam çalışır, filtre çalışmaz sadece).
     Hızlı izleyiciye basit tutuldu: ad eşleşmesi + bölüm filtresi. */
  .arama { margin: 0 0 1.4rem; }
  .arama label {
    display: block;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
  }
  #fms-ara {
    width: 100%;
    padding: 0.75rem 0.9rem;
    font-size: 1rem;
    color: var(--text);
    background: var(--bg-alt);
    border: 1px solid var(--border);
    border-radius: 12px;
    -webkit-appearance: none;
    appearance: none;
  }
  #fms-ara::placeholder { color: rgba(168, 155, 132, 0.6); }
  #fms-ara:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; border-color: var(--gold); }
  .filtre-cubugu { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.6rem; }
  .filtre {
    border: 1px solid var(--border);
    background: var(--kart);
    color: var(--text-dim);
    font-size: 0.85rem;
    min-height: 38px;
    padding: 0.4rem 0.85rem;
    border-radius: 999px;
    cursor: pointer;
    -webkit-tap-highlight-color: rgba(201, 161, 90, 0.25);
  }
  .filtre.aktif { border-color: var(--gold); color: var(--gold-bright); background: rgba(201, 161, 90, 0.10); }
  .filtre:active { border-color: var(--gold); color: var(--gold-bright); }
  @media (hover: hover) {
    .filtre:hover { border-color: var(--gold); color: var(--gold-bright); }
  }
  .filtre:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
  .arama-bos { margin-top: 1.1rem; text-align: center; color: var(--text-dim); }
  li[hidden] { display: none; }

  /* Üst düzen: DJ setleri + derlemeler YAN YANA iki blok (.blok); her blok
     kendi içinde AŞAĞI kayan kart ızgarası. */
  .ikili {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    align-items: start;
  }
  .ikili > .blok { min-width: 0; }
  .ikili .blok h2::before, .ikili .blok h2::after { display: none; }

  /* Hizmetler: kart ızgarası. Küçük resim üstte, başlık altta.
     AŞAĞI akar (yatay kayma YOK — kullanıcı kararı 2026-09-14).
     `auto-fill + minmax`: geniş ekranda satıra kaç kart sığarsa
     o kadar sütun; dar/mobilde 3-4 kart. Sayfayı etkili kullanır. */
  .eserler {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr));
    gap: 0.6rem;
  }
  .eserler.genis { grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); }

  .eserler a {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    /* 56 px: parmakla güvenli dokunma hedefi. Eski sürümde satır
       yüksekliği ~43 px'e düşebiliyordu. */
    min-height: 56px;
    padding: 0;
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    background: var(--kart);
    color: var(--text);
    text-decoration: none;
    font-size: 1rem;
    line-height: 1.3;
    -webkit-tap-highlight-color: rgba(201, 161, 90, 0.25);
  }

  .eserler a:hover { color: inherit; }

  .eserler a img {
    flex: 0 0 auto;
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    /* Görsel hiç yüklenmezse (ağ yok / i.ytimg engelli) kart
       kaymasın diye yer baştan ayrılmış. */
    background: var(--bg-alt);
  }

  .eserler a span {
    /* Sabit 2 satır + ellipsis: uzun Türkçe adlar 2 satıra sarıyor ve
       aynı sıradaki kartlar farklı yükseklikte kalıyordu (taraklı ızgara).
       Clamp metni satır sayısına kilitler; min-height iki satırın yerini
       baştan ayırır ki kısa adlar o sırayı kısaltmasın. (Ajan önerisi.) */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: calc(2 * 1.3rem + 1.1rem);
    padding: 0.55rem 0.5rem;
    text-align: center;
  }

  /* Dokunmatikte :hover yok — geri bildirim :active ile veriliyor. */
  .eserler a:active { border-color: var(--gold); background: rgba(201, 161, 90, 0.10); }

  @media (hover: hover) {
    .eserler a:hover { border-color: var(--gold); color: var(--gold-bright); background: rgba(201, 161, 90, 0.06); }
  }

  .eserler a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

  /* Filtre/arama bir bölümü BÜSBÜTÜN boşalttığında başlığı da gizle —
     boş h2 + boş ızgara ekranda düzensizlik gibi duruyor. JS `hidden`
     atıyor; soldaki kural onu gerçekten kaldırıyor. */
  h2[hidden], ul[hidden] { display: none; }

  /* Mobil: DJ/derleme blokları yan yana ~140px'e daralıyordu — kartlar
     okunamaz hale geliyordu. Dar ekranda blokları TEK sütuna yığıyoruz;
     masaüstünde (sayfa zaten geniş) iki sütun korunuyor. (Ajan önerisi.) */
  @media (max-width: 40rem) {
    .ikili { grid-template-columns: 1fr; }
  }
  .ikili[hidden] { display: none; }

  /* "Bizi takip et": şarkı satırlarıyla aynı kart dili, iki sütun ızgara. */
  .takip h2 { text-align: center; }
  .takip h2::before, .takip h2::after { display: none; }
  .takip-liste { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
  .takip-liste li + li { margin-top: 0; }
  .takip-liste a {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    min-height: 56px;
    padding: 0.5rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--kart);
    color: var(--text);
    text-decoration: none;
    -webkit-tap-highlight-color: rgba(201, 161, 90, 0.25);
  }
  .takip-liste svg { flex: 0 0 auto; width: 22px; height: 22px; color: var(--gold-bright); }
  /* Tek sayıda platformda son öğe yarım kalmasın, tam satırı kaplasın. */
  .takip-liste li:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .takip-liste a:active { border-color: var(--gold); background: rgba(201, 161, 90, 0.10); }
  @media (hover: hover) {
    .takip-liste a:hover { border-color: var(--gold); color: var(--gold-bright); background: rgba(201, 161, 90, 0.06); }
  }
  .takip-liste a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

  footer {
    margin-top: 2.6rem;
    text-align: center;
    font-size: 0.78rem;
    color: rgba(168, 155, 132, 0.55);
    letter-spacing: 0.03em;
  }

  /* Giriş animasyonu — yalnız hareket azaltma KAPALIYSa. */
  @media (prefers-reduced-motion: no-preference) {
    .kimlik { animation: yukari 0.55s ease-out both; }
    li { animation: yukari 0.45s ease-out both; }
    li:nth-child(2) { animation-delay: 0.04s; }
    li:nth-child(3) { animation-delay: 0.08s; }
    li:nth-child(4) { animation-delay: 0.12s; }
    li:nth-child(5) { animation-delay: 0.16s; }
    li:nth-child(6) { animation-delay: 0.20s; }
    li:nth-child(7) { animation-delay: 0.24s; }
    li:nth-child(8) { animation-delay: 0.28s; }
  }

  @keyframes yukari {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
</head>
<body>
<main>
  <header class="kimlik">
    <div class="logo-wrap">
      <img class="logo" src="assets/logo.png" alt="Famous Music Studio logosu">
    </div>
    <h1>Famous Music Studio</h1>
    <p class="alt">Dinlemek için dokun — hepsi YouTube'da.</p>
  </header>
  <div class="arama" role="search">
    <label for="fms-ara">Ara / filtrele</label>
    <input id="fms-ara" type="search" placeholder="Şarkı adı yaz…" autocomplete="off" spellcheck="false">
    <div class="filtre-cubugu" role="group" aria-label="Bölüm filtresi">
      <button type="button" class="filtre aktif" data-bolum="">Tümü</button>
      <button type="button" class="filtre" data-bolum="sarkilar">Şarkılar</button>
      <button type="button" class="filtre" data-bolum="dj">DJ Setleri</button>
      <button type="button" class="filtre" data-bolum="derlemeler">Derlemeler</button>
    </div>
    <p class="arama-bos" hidden>Sonuç bulunamadı.</p>
  </div>
<!--BOLUMLER-->
<!--TAKIP-->
  <footer>
    &copy; 2026 Famous Music Studio &middot; Söz ve m&uuml;zik: Famous Music Studio
  </footer>
</main>
<script>
(function () {
  var kutu = document.getElementById("fms-ara");
  var listeler = document.querySelectorAll(".eserler");
  var bolum = "";
  var bos = document.querySelector(".arama-bos");
  function norm(s) { return (s || "").toLocaleLowerCase("tr").trim(); }
  function onlari_gizle(ul, gizle) {
    // Bir bölümün TÜM kartları filtreden düştüyse h2'sini de gizle.
    var h2 = ul.previousElementSibling;
    if (h2 && h2.tagName && h2.tagName.toLowerCase() === "h2") h2.hidden = gizle;
    ul.hidden = gizle;
  }
  function guncelle() {
    var terim = norm(kutu ? kutu.value : "");
    var gosterilen = 0;
    for (var i = 0; i < listeler.length; i++) {
      var ul = listeler[i];
      var ulBolum = ul.getAttribute("data-bolum") || "";
      var kartlar = ul.querySelectorAll("li");
      var ulGosterilen = 0;
      for (var j = 0; j < kartlar.length; j++) {
        var li = kartlar[j];
        var gor = true;
        if (bolum && ulBolum !== bolum) gor = false;
        if (gor && terim && norm(li.getAttribute("data-ad")).indexOf(terim) === -1) gor = false;
        li.hidden = !gor;
        if (gor) gosterilen += 1;
        if (gor) ulGosterilen += 1;
      }
      onlari_gizle(ul, ulGosterilen === 0);
      // İkili blok (DJ+derlemeler): İKİ bölüm de boşaldıysa bloğu yok say.
      // ul -> section.blok -> div.ikili zinciri üzerinden bulunuyor;
      // parentNode TEK seviye olduğu için section'dan çıkılıyor.
      var blok = ul.parentNode && ul.parentNode.parentNode;
      if (blok && blok.classList.contains("ikili")) {
        var hepsiBos = true;
        var blokUlleri = blok.querySelectorAll("ul.eserler");
        for (var k = 0; k < blokUlleri.length; k++) {
          if (!blokUlleri[k].hidden) hepsiBos = false;
        }
        blok.hidden = hepsiBos;
      }
    }
    if (bos) bos.hidden = gosterilen !== 0;
  }
  if (kutu) kutu.addEventListener("input", guncelle);
  var cips = document.querySelectorAll(".filtre");
  for (var k = 0; k < cips.length; k++) {
    cips[k].addEventListener("click", function () {
      for (var t = 0; t < cips.length; t++) cips[t].classList.remove("aktif");
      this.classList.add("aktif");
      bolum = this.getAttribute("data-bolum") || "";
      guncelle();
    });
  }
})();
</script>
</body>
</html>
"""

_BOS_DURUM = ('  <section class="bos">\n'
              '    <p class="alt">Yayındaki şarkılar birazdan burada olacak.</p>\n'
              '  </section>\n')


def regenerate() -> int:
    """docs/latest.html'i yeniden üretir; sayfaya giren satır sayısını döner.

    Dönen sayı çağıran için zorunlu değil (auto_process yok sayıyor) ama
    testlerin ve elle bir kontrolün "kaç giriş var" sorusunu ağ/HTML
    ayrıştırma olmadan cevaplamasını sağlıyor.

    Düzen: DJ Famous setleri + derlemeler üstte YAN YANA (ikili blok),
    şarkılar altta tek geniş yatay kayar şerit — kullanıcı kararı
    (2026-09-14): katalog büyüyünce sayfa sınırsız uzamasın."""
    bolumler = ""
    adet = 0

    # Ana içerik EN ÜSTTE: şarkılar — geniş ızgara, AŞAĞI doğru akar.
    # (2026-09-14 ajan önerisi: bio linkine "en son şarkılar" için gelen
    # izleyici ilk ekranda ASIL kataloğu görmeli, yan işleri değil.)
    sarkilar = _collect("projects")
    adet += len(sarkilar)
    bolumler += _section("Şarkılar", sarkilar, "eserler genis", "sarkilar")

    # Alt: DJ setleri + derlemeler YAN YANA iki blok; her biri kartların
    # AŞAĞI aktığı normal ızgara (yatay kayma YOK — kullanıcı kararı).
    # Her bölüm kendi "blok"una sarılıyor — `.ikili`'nin grid'inde başlık
    # ve listesi AYNI hücre sütununda kalsın diye (ayrı item olurlarsa
    # başlık bir sütuna, listesi diğerine düşer).
    ust = ""
    for kok, baslik in KOKLER:
        if kok == "projects":
            continue
        satirlar = _collect(kok)
        adet += len(satirlar)
        bolum = "dj" if kok == "dj_sets" else "derlemeler"
        parca = _section(baslik, satirlar, "eserler", bolum)
        if parca:
            ust += "    <section class=\"blok\">\n%s    </section>\n" % parca
    if ust:
        bolumler += "  <div class=\"ikili\">\n%s  </div>\n" % ust

    rendered = _TEMPLATE.replace(_YER_TUTUCU, bolumler or _BOS_DURUM)
    rendered = rendered.replace(_TAKIP_YER_TUTUCU, takip_bolumu_html().rstrip(_LF))
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(LATEST_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(rendered)
    return adet
