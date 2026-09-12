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


def _section(heading: str, rows: list[tuple[str, str, str]]) -> str:
    if not rows:
        return ""
    items = "\n".join(
        '    <li><a href="https://youtu.be/{vid}">'
        '<img src="https://i.ytimg.com/vi/{vid}/mqdefault.jpg" alt="" '
        'width="88" height="50" loading="lazy" decoding="async">'
        "<span>{ad}</span></a></li>".format(vid=video_id, ad=html.escape(title))
        for _, title, video_id in rows
    )
    return "  <h2>{}</h2>\n  <ul>\n{}\n  </ul>\n".format(html.escape(heading), items)


# NEDEN `.format()` DEĞİL, `replace()` (aşağıda): şablon baştan sona CSS
# süslü parantezi içeriyor; `.format()` kullanmak hepsini `{{ }}` diye
# ikilemeyi gerektiriyordu ve tek bir unutulan parantez sayfayı sessizce
# bozuyordu. Tek bir yer tutucu + `replace` bu sınıf hatayı tamamen kaldırıyor.
_YER_TUTUCU = "<!--BOLUMLER-->"

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

  main { max-width: 28rem; width: 100%; margin: 0 auto; }

  h1 {
    font-family: Georgia, "Times New Roman", serif;
    font-weight: 600;
    font-size: clamp(1.8rem, 6vw, 2.4rem);
    margin: 0 0 0.4rem;
    color: var(--gold-bright);
    text-align: center;
  }

  .alt {
    margin: 0 0 1.6rem;
    text-align: center;
    font-size: 0.9rem;
    color: var(--text-dim);
  }

  h2 {
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 1.8rem 0 0.7rem;
  }

  ul { list-style: none; margin: 0; padding: 0; }

  li + li { margin-top: 0.5rem; }

  a {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    /* 56 px: parmakla güvenli dokunma hedefi. Eski sürümde satır
       yüksekliği ~43 px'e düşebiliyordu. */
    min-height: 56px;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--kart);
    color: var(--text);
    text-decoration: none;
    font-size: 1rem;
    line-height: 1.3;
    -webkit-tap-highlight-color: rgba(201, 161, 90, 0.25);
  }

  a img {
    flex: 0 0 auto;
    width: 88px;
    height: 50px;
    object-fit: cover;
    border-radius: 8px;
    /* Görsel hiç yüklenmezse (ağ yok / i.ytimg engelli) satır
       kaymasın diye yer baştan ayrılmış ve kutu koyu kalıyor. */
    background: var(--bg-alt);
  }

  a span { overflow-wrap: anywhere; }

  /* Dokunmatikte :hover yok — geri bildirim :active ile veriliyor. */
  a:active { border-color: var(--gold); background: rgba(201, 161, 90, 0.10); }

  @media (hover: hover) {
    a:hover { border-color: var(--gold); color: var(--gold-bright); background: rgba(201, 161, 90, 0.06); }
  }

  a:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
</style>
</head>
<body>
<main>
  <h1>Famous Music Studio</h1>
  <p class="alt">Dinlemek için dokun — hepsi YouTube'da.</p>
<!--BOLUMLER-->
</main>
</body>
</html>
"""

_BOS_DURUM = '  <p class="alt">Yayındaki şarkılar birazdan burada olacak.</p>\n'


def regenerate() -> int:
    """docs/latest.html'i yeniden üretir; sayfaya giren satır sayısını döner.

    Dönen sayı çağıran için zorunlu değil (auto_process yok sayıyor) ama
    testlerin ve elle bir kontrolün "kaç giriş var" sorusunu ağ/HTML
    ayrıştırma olmadan cevaplamasını sağlıyor."""
    bolumler = ""
    adet = 0
    for kok, baslik in KOKLER:
        satirlar = _collect(kok)
        adet += len(satirlar)
        bolumler += _section(baslik, satirlar)
    rendered = _TEMPLATE.replace(_YER_TUTUCU, bolumler or _BOS_DURUM)
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(LATEST_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(rendered)
    return adet
