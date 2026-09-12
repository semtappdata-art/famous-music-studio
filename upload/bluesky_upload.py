"""Render edilmiş bir projeyi Bluesky'a video gönderisi olarak yükler (AT Protocol).

Kullanım:
    python upload/bluesky_upload.py --project "projects/Son Kez"
    python upload/bluesky_upload.py --project "projects/Son Kez" --dry-run

NEDEN BLUESKY — Instagram/TikTok'un aksine burada OAuth çemberinden geçmek
gerekmiyor: handle + "app password" yetiyor (aşağıya bak). Ayrıca AI ile
üretilmiş müzik için zorunlu bir etiketleme/bildirim politikası YOK (YouTube'un
containsSyntheticMedia bayrağı ya da Meta'nın "AI Info" etiketi gibi bir
karşılığı bulunmuyor), o yüzden bu modülde AI bildirimi ile ilgili bir alan da
yok. Bir başka fark: Bluesky'ın dağıtımı kronolojik/besleme tabanlı, "başka
platforma link verirsen erişim cezası" diye bir mekanizma bilinmiyor — bu
yüzden YouTube linki burada caption'ın İÇİNE konuyor (Instagram/TikTok'ta
linki paylaşımdan SONRA yoruma koyuyoruz, bkz. social_text.build_caption()
ve instagram_upload.py). Ayrıntılı gerekçe: build_post_text().

KİMLİK BİLGİLERİ — upload/bluesky_client_secrets.json:
    {"handle": "famousmusicstudio.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}

App password nasıl alınır (bir kerelik, 1 dakika):
    1. bsky.app'te hesaba gir → Settings (Ayarlar) → Privacy and Security →
       App Passwords → "Add App Password".
    2. Bir isim ver (örn. "famous-music-studio-otomasyon"), üretilen
       xxxx-xxxx-xxxx-xxxx biçimindeki şifreyi KOPYALA (bir daha gösterilmiyor).
    3. upload/bluesky_client_secrets.json dosyasını yukarıdaki biçimde oluştur.
       Örnek şablon: upload/bluesky_client_secrets.json.example
    "handle" tam handle olmalı (örn. famousmusicstudio.bsky.social) — başına @
    koyma. App password ASIL hesap şifresi DEĞİLDİR; istediğin an Bluesky'dan
    iptal edebilirsin ve bu modül dışında hiçbir yere yazılmaz.
    Kendi PDS'inde barınıyorsan dosyaya "service": "https://pds.example.com"
    ekleyebilirsin (varsayılan: https://bsky.social).

VİDEO YÜKLEME YOLU — bu modülün en kritik kısmı:
    atproto kütüphanesinin kolay yolu client.send_video(), videoyu doğrudan
    PDS'e com.atproto.repo.uploadBlob ile atar. Sorun: PDS'in blob boyut
    limiti ~50 MB ve video PDS'e yüklendikten sonra ancak GÖNDERİ atıldığında
    işlenmeye başlıyor — yani gönderi bir süre "video yükleniyor" plaseholder'ı
    olarak görünüyor. Bizim shorts_9x16.mp4 dosyalarımız 3-5 MB olduğu için
    limite takılmıyor, ama uzun DJ set kesitleri ya da daha yüksek bitrate'e
    geçilmesi hâlinde sınır tam da orada.
    Bu yüzden burada bsky-docs'un ÖNERDİĞİ yol elle yazıldı (kaynak:
    https://github.com/bluesky-social/bsky-docs/blob/main/docs/tutorials/video.mdx
    — 2026-09-10'da doğrulandı):
        1. com.atproto.server.getServiceAuth ile 30 dakikalık, lxm'i
           "com.atproto.repo.uploadBlob"a bağlı bir servis token'ı al
           (aud = did:web:<PDS host>).
        2. POST https://video.bsky.app/xrpc/app.bsky.video.uploadVideo
           ?did=<did>&name=<dosya adı>, Authorization: Bearer <token>,
           Content-Type: video/mp4 — gövde ham dosya. Yanıt: jobStatus.jobId.
        3. https://video.bsky.app/xrpc/app.bsky.video.getJobStatus?jobId=...
           — iş bitene, yani jobStatus.blob dolana kadar yokla (bu uç nokta
           KİMLİK DOĞRULAMASIZ, dokümandaki örnek de public agent kullanıyor).
        4. Dönen blob'u app.bsky.embed.video gömüsünde kullan.
    Böylece video, gönderi atılmadan ÖNCE işlenmiş oluyor (gönderi ilk anından
    itibaren oynatılabilir) ve PDS blob limiti devre dışı kalıyor.

    NOT: video.bsky.app'in kesin üst sınırı (yaygın olarak ~300 MB / 3 dakika
    şeklinde aktarılıyor) resmî dokümanda SAYIYLA yazmıyor, o yüzden burada
    sabit olarak iddia edilmiyor; sadece süre için uyarı basılıyor (bkz.
    MAX_VIDEO_SECONDS).

İKİNCİ TUZAK — aspectRatio:
    app.bsky.embed.video gömüsünde aspectRatio doldurulmazsa oynatıcı videoyu
    varsayılan (yatay) kutuya oturtuyor ve dikey video bozuk/kırpılmış
    görünüyor. Bu yüzden ffprobe ile gerçek genişlik/yükseklik okunup
    dolduruluyor (bkz. _probe_video_size). ffmpeg_utils.py'de ffprobe var ama
    sadece SÜRE okuyan bir yardımcı (get_audio_duration) — boyut okuyan hazır
    bir fonksiyon yok, o yüzden aynı desenle burada yazıldı.

BAĞIMLILIK: `pip install atproto`. Kurulu değilse modül yine de import
edilebilir (--help, --dry-run çalışır); gerçek gönderi anında anlamlı bir
ImportError fırlatılır — bkz. _import_atproto().
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import unicodedata

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ag_yeniden_deneme as ag
import config
import state_io
from social_text import build_caption, resolve_language
# Kok listesi TEK kaynaktan: bkz. uyumluluk.KOK_ADLARI'nin uzerindeki not.
from uyumluluk import proje_klasorleri

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(UPLOAD_DIR)
SECRETS_PATH = os.path.join(UPLOAD_DIR, "bluesky_client_secrets.json")

DEFAULT_SERVICE = "https://bsky.social"
VIDEO_SERVICE = "https://video.bsky.app"

# Bluesky gönderi sınırı: 300 GRAPHEME (kod noktası ya da bayt değil — emoji ve
# birleşik karakterler tek grapheme sayılır). Ayrıca 3000 baytlık bir üst sınır
# daha var ama Türkçe caption'larımız ~250 bayt olduğu için ona hiç yaklaşmıyoruz.
POST_GRAPHEME_LIMIT = 300

# Bluesky video sınırı: 3 dakika (aşan videoyu servis reddediyor). Bizim
# shorts_9x16.mp4 ~45 sn, ama DJ set kesitleri büyürse burada yakalansın.
MAX_VIDEO_SECONDS = 180

# Hesap başına günlük kota: 25 video / 10 GB. Bunu Bluesky'ın
# app.bsky.video.getUploadLimits ucuna sormak yerine YEREL olarak sayıyoruz
# (bkz. _todays_upload_count) — o ucun kimlik doğrulama gereksinimi bu depoda
# doğrulanamadı, yerel sayım ise state.json'lardan kesin okunuyor ve zaten
# günde 1-2 video yüklüyoruz, sınıra yaklaşmak ancak toplu yeniden yüklemede
# mümkün.
DAILY_VIDEO_LIMIT = 25

JOB_POLL_INTERVAL = 2  # saniye
JOB_POLL_TIMEOUT = 600  # saniye (10 dk) — 45 sn'lik bir klip normalde <30 sn'de biter


def _import_atproto():
    """atproto kütüphanesini GEÇ (lazy) import eder.

    Modülün tepesinde import etmiyoruz ki kütüphane kurulu olmayan bir makinede
    de `--help`, `--dry-run` ve caption ölçümü çalışsın; gerçekten gönderi
    atılacağı anda ise ne yapılması gerektiğini söyleyen bir hata alınsın.
    """
    try:
        from atproto import Client, client_utils, models  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "Bluesky yüklemesi için 'atproto' paketi gerekli ama kurulu değil.\n"
            "Kurmak için:  pip install atproto\n"
            "(Sadece metin/uzunluk denemesi yapacaksan --dry-run kullan, o paket "
            "gerektirmez.)"
        ) from e
    return Client, client_utils, models


# --------------------------------------------------------------------------
# proje dosyaları (ev tarzı: instagram_upload.py ile aynı desen)
# --------------------------------------------------------------------------

def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(project_dir: str, updates: dict) -> None:
    """state.json'a alan ekler/gunceller — ATOMIK (state_io.durum_yaz).

    NEDEN: eskiden hedefin USTUNE dogrudan yaziliyordu; `open(..., "w")`
    dosyayi once SIFIRLIYOR, `json.dump` bitmeden surec olurse diskte YARIM
    bir JSON kaliyor ve `uyumluluk._durum()` sertlestirildikten sonra bozuk
    bir state.json boru hattini DURDURUYOR. Ayrica `auto_process` (saatlik)
    ile `dj_famous_process` (haftalik) AYRI kilitler kullanip ayni dosyaya
    yazabiliyor; kaybolan bir `bluesky_post_uri` bu platformda IKINCI bir
    gonderi demek."""
    state = _load_state(project_dir)
    state.update(updates)
    state_io.durum_yaz(project_dir, state)


def _load_credentials() -> dict:
    """bluesky_client_secrets.json'u okur. Dosya yoksa/eksikse, ne yapılacağını
    ADIM ADIM anlatan bir hata fırlatır — bu script çoğunlukla zamanlanmış
    görevden (setup_task_scheduler.ps1) çalıştığı için log'da tek başına
    anlaşılır olması gerekiyor."""
    nasil = (
        "Bluesky app password nasıl alınır:\n"
        "  1. bsky.app → Settings → Privacy and Security → App Passwords →\n"
        "     'Add App Password' → bir isim ver (örn. famous-music-studio-otomasyon)\n"
        "  2. Üretilen xxxx-xxxx-xxxx-xxxx şifresini kopyala (bir daha gösterilmez)\n"
        f"  3. {SECRETS_PATH} dosyasını şu içerikle oluştur:\n"
        '     {"handle": "famousmusicstudio.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}\n'
        "     (şablon: bluesky_client_secrets.json.example — handle'ın başına @ koyma)"
    )
    if not os.path.isfile(SECRETS_PATH):
        raise FileNotFoundError(f"{SECRETS_PATH} bulunamadı.\n{nasil}")
    with open(SECRETS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)
    eksik = [k for k in ("handle", "app_password") if not creds.get(k)]
    if eksik:
        raise ValueError(
            f"{SECRETS_PATH} içinde şu alan(lar) eksik/boş: {', '.join(eksik)}.\n{nasil}"
        )
    creds["handle"] = creds["handle"].lstrip("@").strip()
    creds.setdefault("service", DEFAULT_SERVICE)
    return creds


# --------------------------------------------------------------------------
# metin: 300 grapheme sınırı
# --------------------------------------------------------------------------

def grapheme_len(text: str) -> int:
    """Metnin GRAPHEME (kullanıcının "bir karakter" gördüğü birim) sayısı.

    Bluesky 300'lük sınırı grapheme üzerinden uyguluyor, Python'un len()'i ise
    kod noktası sayıyor — "🎧" gibi tek emoji ikisinde de 1, ama birleşik
    emojiler (ZWJ ile birleşenler, ten rengi modifierları, bayraklar) ve
    Türkçedeki ayrık birleşik işaretler len() ile FAZLA sayılıyor. Sınıra
    yaklaşan bir metni gereksiz yere kırpmamak için burada yaklaşık bir
    grapheme sayımı yapılıyor (harici bağımlılık eklememek adına 'regex'
    paketi yerine elle): birleştirici işaretler, ZWJ ile bağlanan parçalar,
    varyasyon seçicileri ve ten rengi modifierları önceki grapheme'e katılır,
    bölgesel gösterge (bayrak) harfleri ikişer ikişer sayılır.

    Yaklaşık olması sorun değil — HATA PAYI güvenli yönde: gerçek grapheme
    sayısından asla AZ saymaz.
    """
    count = 0
    prev_regional = False
    join_next = False
    for ch in text:
        code = ord(ch)
        # ZWJ: kendisi grapheme değil, bir sonrakini de öncekine bağlar
        if code == 0x200D:
            join_next = True
            prev_regional = False
            continue
        if join_next:
            join_next = False
            prev_regional = False
            continue
        # birleştirici işaretler + varyasyon seçicileri + ten rengi modifierları
        if unicodedata.combining(ch) or 0xFE00 <= code <= 0xFE0F or 0x1F3FB <= code <= 0x1F3FF:
            continue
        # bölgesel gösterge harfleri (bayraklar): ikisi bir grapheme
        if 0x1F1E6 <= code <= 0x1F1FF:
            if prev_regional:
                prev_regional = False
                continue
            prev_regional = True
            count += 1
            continue
        prev_regional = False
        count += 1
    return count


def trim_to_graphemes(text: str, limit: int, suffix: str = "…") -> str:
    """Metni `limit` grapheme'e KELİME SINIRINDAN kırpar, sonuna `suffix` koyar.

    Ortasından bölünmüş bir kelime ("Bu şarkı sana neyi hatır…") amatör
    duruyor, o yüzden son boşluğa kadar geri sarıyoruz. Metinde hiç boşluk
    yoksa (tek uzun kelime) mecburen sert kırpılır.
    """
    if grapheme_len(text) <= limit:
        return text
    budget = limit - grapheme_len(suffix)
    # limit'e sığan en uzun ön eki bul (grapheme sayarak karakter karakter ilerle)
    kesit = ""
    for ch in text:
        aday = kesit + ch
        if grapheme_len(aday) > budget:
            break
        kesit = aday
    bosluk = max(kesit.rfind(" "), kesit.rfind("\n"))
    if bosluk > 0:
        kesit = kesit[:bosluk]
    return kesit.rstrip() + suffix


def _kesif_etiketlerini_at(text: str) -> str:
    """Keşif hashtag'lerini (#viral, #fyp, #explore...) gönderiden çıkarır.

    Bluesky'da bunlar ÖLÜ AĞIRLIK. build_post_text'in kendi notu şunu söylüyor:
    Bluesky beslemesi kronolojik/takip tabanlı, sıralamayı belirleyen bir keşfet
    motoru YOK. "#viral"in bir For You kuyruğuna girmesi diye bir mekanizma
    olmadığına göre o etiket hiçbir şey yapmıyor — buna karşılık "#MelodicTechno"
    Bluesky'da gerçek bir etiket beslemesi, insanlar oradan geliyor.

    Bu yüzden 300 sınırı zorlandığında ilk feda edilecek şey keşif etiketleri:
    tür ve stil etiketleri (config.SET_STILLERI) yerinde kalıyor. Sınır
    zorlanmıyorsa hiç çağrılmıyor — kısa gönderilerde her şey duruyor.
    """
    kesif = {h.lower() for h in
             (config.DISCOVERY_HASHTAGS + config.DISCOVERY_HASHTAGS_EN)}
    satirlar = text.split("\n")
    for i, satir in enumerate(satirlar):
        if not satir.strip().startswith("#"):
            continue
        kalan = [e for e in satir.split() if e.lower() not in kesif]
        satirlar[i] = " ".join(kalan)
    return "\n".join(satirlar).rstrip()


def _hashtaglerden_kirp(text: str, limit: int) -> str:
    """Bütçeye sığmıyorsa SONDAKİ hashtag'lerden başlayarak TAM etiket atar.

    trim_to_graphemes kelime sınırından kırpıyor ve sonuna "…" koyuyor; bu bir
    cümle için doğru ama hashtag satırında yanlış: "#ChilloutMix…" ne geçerli
    bir etiket ne de okunur bir metin — facet olarak da bozuk bir tag üretir.
    Etiketi yarım bırakmaktansa tamamen atmak daha iyi.

    Neden şimdi gerekti: setlere `set_style` eklenince (config.SET_STILLERI)
    hashtag satırına 4 stil etiketi daha bindi ve gönderi 298/300'e dayandı —
    build_post_text'in docstring'indeki "havuzlara yeni hashtag eklenirse sınır
    zorlanabilir" uyarısı tam olarak gerçekleşti. Atılacak etiketler SONDAN
    seçiliyor; build_caption sırayı marka → keşif → tür → stil diye kuruyor,
    yani en sonda duran stil etiketleri... KASITLI olarak korunmuyor: 300
    sınırı aşıldığında hangi etiketin gideceğine karar vermek yerine satırı
    kısaltmak yeterli, çünkü asıl kayıp bozuk etiket üretmekti.
    """
    if grapheme_len(text) <= limit:
        return text

    # Önce Bluesky'da hiçbir işe yaramayan keşif etiketleri gitsin.
    text = _kesif_etiketlerini_at(text)
    if grapheme_len(text) <= limit:
        return text

    satirlar = text.split("\n")
    for i in range(len(satirlar) - 1, -1, -1):
        if not satirlar[i].strip().startswith("#"):
            continue
        etiketler = satirlar[i].split()
        while etiketler:
            etiketler.pop()
            satirlar[i] = " ".join(etiketler)
            aday = "\n".join(satirlar).rstrip()
            if grapheme_len(aday) <= limit:
                return aday
        break

    # Hashtag satırı yok ya da hepsi atılınca bile sığmadı — düz kırpmaya dön.
    return trim_to_graphemes(text, limit)


def build_post_text(meta: dict, youtube_url: str | None = None) -> str:
    """Bluesky gönderi metnini üretir: build_caption(meta) + (varsa) YouTube linki.

    YOUTUBE LİNKİ NEDEN BURADA CAPTION'IN İÇİNDE (Instagram/TikTok'un aksine)?
    social_text.build_caption()'daki not, linkin caption'a KONMAMA gerekçesini
    Instagram/TikTok keşfet algoritmasının "dış platforma yönlendirme"yi
    cezalandırdığı varsayımına dayandırıyor. Bluesky'da bu gerekçe geçersiz:
    besleme kronolojik/takip tabanlı, sıralamayı belirleyen bir keşfet motoru
    yok, dolayısıyla link cezası diye bir mekanizma da yok. Üstelik Bluesky'da
    linkler GERÇEKTEN tıklanabilir (facet ile) — Instagram/TikTok'ta düz metin
    linkin tıklanamamasıydı zaten asıl sorun. Bu yüzden burada link doğrudan
    metne giriyor.

    Karakter bütçesi: ölçtük — projects/* için build_caption() çıktıları
    200-252 grapheme arası (2026-09-10, 18 proje). Link bloğu (boş satır +
    kulaklık emojisi + https://youtu.be/<11 karakterlik id>) 32 grapheme
    ekliyor, yani en uzun
    caption bile 284'te kalıyor, 300 sınırını AŞMIYOR. Yine de havuzlara yeni
    (daha uzun) hook/hashtag eklenirse sınır zorlanabileceği için caption
    gerekirse kelime sınırından kırpılıyor — kırpılan şey CAPTION oluyor, link
    her zaman korunuyor (link, gönderinin tek dönüşüm sağlayan parçası).
    """
    caption = build_caption(meta)
    if not youtube_url:
        return _hashtaglerden_kirp(caption, POST_GRAPHEME_LIMIT)

    ek = f"\n\n🎧 {youtube_url}"
    bütçe = POST_GRAPHEME_LIMIT - grapheme_len(ek)
    return _hashtaglerden_kirp(caption, bütçe) + ek


def _build_rich_text(client_utils, text: str):
    """Düz metni Bluesky'ın "facet"lerine (zengin metin) çevirir.

    Bluesky sunucusu metni KENDİ ayrıştırmıyor: link ve hashtag'ler ancak
    gönderiyle birlikte facet olarak gönderilirse tıklanabilir/#etiket
    beslemelerinde görünür oluyor. Facet göndermezsek caption'daki
    "#FamousMusicStudio" sadece düz yazı olarak kalır — bu da hashtag
    stratejimizin Bluesky ayağını tamamen boşa çıkarır. Bu yüzden metni
    boşluklardan parçalayıp URL'leri .link(), #etiketleri .tag() ile
    işaretliyoruz.
    """
    builder = client_utils.TextBuilder()
    # Metni boşlukları KORUYARAK parçala (boşluklar da metnin parçası, aksi
    # halde satır araları kaybolur).
    parça = ""
    for ch in text:
        if ch.isspace():
            if parça:
                _append_token(builder, parça)
                parça = ""
            builder.text(ch)
        else:
            parça += ch
    if parça:
        _append_token(builder, parça)
    return builder


def _append_token(builder, token: str) -> None:
    """Tek bir kelimeyi uygun facet tipiyle builder'a ekler."""
    if token.startswith("http://") or token.startswith("https://"):
        builder.link(token, token)
    elif token.startswith("#") and len(token) > 1:
        # tag facet'i #'siz değeri ister; görünen metin #'li kalır.
        builder.tag(token, token[1:])
    else:
        builder.text(token)


# --------------------------------------------------------------------------
# video: ffprobe ile boyut/süre
# --------------------------------------------------------------------------

def _probe_video_size(video_path: str) -> tuple[int, int]:
    """ffprobe ile videonun (genişlik, yükseklik) değerini okur.

    aspectRatio gömüde DOLDURULMAZSA Bluesky oynatıcısı videoyu varsayılan
    (yatay) kutuya oturtuyor ve 1080x1920 dikey klibimiz kırpılmış/bozuk
    görünüyor — bu yüzden tahmin etmek yerine dosyadan okuyoruz (render
    ayarları değişirse burası kendiliğinden doğru kalır).
    ffmpeg_utils.get_audio_duration ile aynı çağrı deseni; orada boyut okuyan
    hazır bir yardımcı olmadığı için burada yazıldı.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe video boyutunu okuyamadı: {result.stderr.strip()}")
    try:
        width, height = (int(x) for x in result.stdout.strip().split("x")[:2])
    except ValueError:
        raise RuntimeError(f"ffprobe beklenmedik boyut çıktısı verdi: {result.stdout!r}")
    return width, height


def _probe_video_duration(video_path: str) -> float | None:
    """Videonun süresini saniye olarak döner; okunamazsa None (süre kontrolü
    sadece bir UYARI için kullanılıyor, yüklemeyi bloke etmesin)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


# --------------------------------------------------------------------------
# video.bsky.app servis yolu (getServiceAuth → uploadVideo → getJobStatus)
# --------------------------------------------------------------------------

def _pds_adresi(did: str, varsayilan: str) -> str:
    """Hesabın GERÇEK PDS adresini DID belgesinden çözer.

    Neden gerekli: giriş `bsky.social` üzerinden yapılıyor ama o bir giriş
    kapısı (entryway); hesabın verisi başka bir sunucuda duruyor. Örnek:
    famousmusicstudio.bsky.social → poisonpie.us-west.host.bsky.network.

    Servis token'ının `aud` alanı bu GERÇEK PDS'i göstermeli. `bsky.social`
    yazıldığında video.bsky.app token'ı reddediyor:
      "invalid token audience \"did:web:bsky.social\", should be the user's
       PDS DID \"did:web:poisonpie.us-west.host.bsky.network\""
    Hata mesajı doğru adresi zaten söylüyor ama ona güvenmek yerine DID
    belgesinden okuyoruz — her hesabın PDS'i farklı olabilir.
    """
    if did.startswith("did:plc:"):
        kaynak = "https://plc.directory/%s" % did
    elif did.startswith("did:web:"):
        kaynak = "https://%s/.well-known/did.json" % did[len("did:web:"):]
    else:
        return varsayilan
    try:
        belge = requests.get(kaynak, timeout=20).json()
    except Exception:
        return varsayilan            # ağ sorunu: varsayılanla devam, hata
                                     # yine de aşağıda anlaşılır şekilde çıkar
    for s in belge.get("service", []) or []:
        if s.get("type") == "AtprotoPersonalDataServer" and s.get("serviceEndpoint"):
            return s["serviceEndpoint"]
    return varsayilan


def _service_auth_token(client, service: str) -> str:
    """30 dakikalık, lxm'i com.atproto.repo.uploadBlob'a bağlı servis token'ı alır.

    aud = did:web:<PDS host> — token'ı SADECE o PDS adına uploadBlob için
    geçerli kılıyor; video.bsky.app bu token'a bakıp blob'u bizim adımıza
    PDS'e yazabildiğini doğruluyor. exp'i kısa tutmak (30 dk) dokümanın
    önerisi: token sızsa bile kullanım penceresi dar.
    """
    from urllib.parse import urlparse

    host = urlparse(service).hostname
    if not host:
        raise ValueError(f"Geçersiz Bluesky servis adresi: {service!r}")
    resp = client.com.atproto.server.get_service_auth(
        params={
            "aud": f"did:web:{host}",
            "lxm": "com.atproto.repo.uploadBlob",
            "exp": int(time.time()) + 30 * 60,
        }
    )
    return resp.token


def _upload_to_video_service(did: str, token: str, video_path: str) -> dict:
    """Videoyu video.bsky.app'e yükler, jobStatus sözlüğünü döner.

    Ham requests ile yazıldı çünkü bu uç nokta atproto istemcisinin normal
    XRPC yolundan (PDS) DEĞİL, ayrı bir servisten geçiyor ve gövde JSON değil
    ham video/mp4. did + name sorgu parametreleri zorunlu (name, servisin
    dosyayı adlandırması için).
    """
    with open(video_path, "rb") as f:
        data = f.read()

    # `belirsiz_guvenli=True` — bu isteğin İŞ SEVİYESİNDE idempotent olduğu
    # YERİNDE gerekçelendirilmeli (bkz. ag_yeniden_deneme.guvenli_istek):
    # burada gerekçe hemen aşağıdaki 409 dalı. Servis aynı videoyu ikinci kez
    # aldığında YENİ bir iş yaratmıyor, "already_exists" + AYNI jobStatus
    # dönüyor. Üstelik bu adım GÖNDERİ ATMIYOR — sadece blob'u işliyor;
    # gönderiyi yaratan tek çağrı aşağıdaki send_post. Yani buradaki bir
    # yeniden deneme kanalda ikinci bir gönderi ÜRETEMEZ.
    resp = ag.guvenli_istek(
        lambda: requests.post(
            f"{VIDEO_SERVICE}/xrpc/app.bsky.video.uploadVideo",
            params={"did": did, "name": os.path.basename(video_path)},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(len(data)),
            },
            data=data,
            timeout=(10, 600),
        ),
        ne="Bluesky uploadVideo",
        belirsiz_guvenli=True,
        platform="Bluesky",
    )
    # 409 = "already_exists": aynı video daha önce yüklenmiş. Servis yine de
    # jobStatus döndürüyor, o yüzden bunu hata saymıyoruz — yoklamaya devam.
    if resp.status_code not in (200, 409):
        raise RuntimeError(
            f"video.bsky.app yükleme hatası (HTTP {resp.status_code}): {resp.text[:500]}"
        )
    payload = resp.json()
    job_status = payload.get("jobStatus") or payload
    if not job_status.get("jobId"):
        raise RuntimeError(f"video.bsky.app beklenmedik yanıt verdi: {payload}")
    return job_status


def _wait_for_job(job_id: str) -> dict:
    """getJobStatus'u iş bitene (jobStatus.blob dolana) kadar yoklar.

    Bu uç nokta KİMLİK DOĞRULAMASIZ (bsky-docs örneği de public agent
    kullanıyor) — servis token'ı burada göndermiyoruz, zaten o token
    uploadBlob'a bağlı, başka bir lxm ile kullanılırsa reddedilirdi.
    """
    başlangıç = time.time()
    son_durum = None
    while time.time() - başlangıç < JOB_POLL_TIMEOUT:
        # GET — hiçbir yan etkisi yok, yani her sınıfta yeniden denenebilir
        # (`belirsiz_guvenli=True`). Eskiden tek bir ağ hıçkırığı tüm
        # yüklemeyi düşürüyordu; oysa iş servis tarafında DEVAM EDİYOR.
        resp = ag.guvenli_istek(
            lambda: requests.get(
                f"{VIDEO_SERVICE}/xrpc/app.bsky.video.getJobStatus",
                params={"jobId": job_id},
                timeout=(10, 30),
            ),
            ne="Bluesky getJobStatus",
            belirsiz_guvenli=True,
            platform="Bluesky",
        )
        resp.raise_for_status()
        job_status = resp.json().get("jobStatus", {})
        state = job_status.get("state")
        if state != son_durum:
            print(f"  video işleniyor: {state} ({job_status.get('progress', 0)}%)")
            son_durum = state
        if job_status.get("blob"):
            return job_status
        if state == "JOB_STATE_FAILED":
            raise RuntimeError(
                "Bluesky video işleme başarısız: "
                f"{job_status.get('error')} — {job_status.get('message')}"
            )
        time.sleep(JOB_POLL_INTERVAL)
    raise RuntimeError(
        f"Bluesky video işleme zaman aşımına uğradı ({JOB_POLL_TIMEOUT} sn, jobId={job_id})."
    )


def _todays_upload_count() -> int:
    """Bugün Bluesky'a yüklenmiş video sayısını TÜM kataloğun state.json'larından sayar.

    Bluesky'ın günlük kotası 25 video / 10 GB. Normalde günde 1-2 video
    yüklüyoruz, ama toplu yeniden yükleme (örn. tüm kataloğu bir döngüde
    geçirmek) sınırı sessizce aşıp hesabı geçici olarak kısıtlatabilir —
    bu sayaç o kazayı önlüyor.

    KÖK LİSTESİ (2026-09-11): eskiden SADECE `projects/` sayılıyordu. Oysa DJ
    setleri ve derlemeler de Bluesky'a çıkıyor (`dj_famous_process.py` →
    `_ek_platformlari_isle`; canlı kanıt: `derlemeler/Gece Seansı Vol. 1`
    state.json'ında `bluesky_post_uri` var). Yani kotayı koruyan sayaç
    yüklemelerin bir kısmını GÖRMÜYORDU — eksik sayan bir tavan, olmayan
    tavandan farksız. Artık tek kanonik kaynak: `uyumluluk.KOKLER`.
    """
    bugün = datetime.date.today().isoformat()
    sayı = 0
    for project_dir in proje_klasorleri():
        state_path = os.path.join(project_dir, "state.json")
        if not os.path.isfile(state_path):
            continue
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if str(state.get("bluesky_uploaded_at", "")).startswith(bugün):
            sayı += 1
    return sayı


class _BulunanGonderi:
    """`send_post` belirsiz kaldığında DOĞRULAMA ile bulunan gönderi.

    `client.send_post()`in döndürdüğü nesneyle aynı iki alanı taşıyor (uri,
    cid) — çağıran kod ikisini ayırt etmek zorunda kalmasın diye.
    """

    __slots__ = ("uri", "cid")

    def __init__(self, uri, cid):
        self.uri = uri
        self.cid = cid


def _gonderi_zaten_var_mi(pds: str, did: str, metin: str, pencere_sn: int = 1800):
    """Bu metne sahip bir gönderi SON ANDA repoya yazılmış mı — varsa döner.

    NEDEN BU MÜMKÜN (ve Telegram'da değil): AT Protocol'ün
    `com.atproto.repo.listRecords` uç noktası lexicon'da aynen şöyle
    tarifleniyor: "List a range of records in a repository, matching a
    specific collection. **Does not require auth.**" Yani hesabın kendi
    gönderilerini kimlik doğrulaması olmadan, HERHANGİ bir yan etki
    üretmeden okuyabiliyoruz. `send_post` (com.atproto.repo.createRecord)
    idempotent DEĞİL — her çağrı yeni bir kayıt yaratır — ama "yarattı mı"
    sorusu SORULABİLİYOR. Doğru çözüm bu yüzden "körü körüne yeniden deneme"
    değil, DOĞRULAYARAK yeniden deneme.

    Dönüş sözleşmesi `ag_yeniden_deneme.guvenli_istek`in beklediği gibi:
      * `_BulunanGonderi` -> gönderi VAR, yeniden gönderme
      * `None`            -> gönderi YOK, yeniden denemek güvenli
      * `ag.BILINMIYOR`   -> okuyamadık; karar verme, işaret bırak

    `pencere_sn`: yalnızca SON yarım saatte yazılmış kayıtlar sayılıyor.
    Aynı metnin aylar önce yayınlanmış bir kopyasını "az önce gitti" sanıp
    state'e yazmak, düzeltmeye çalıştığımız hatanın aynası olurdu.
    """
    try:
        resp = requests.get(
            "%s/xrpc/com.atproto.repo.listRecords" % pds.rstrip("/"),
            params={"repo": did, "collection": "app.bsky.feed.post",
                    "limit": 25},
            timeout=(10, 30),
        )
        resp.raise_for_status()
        kayitlar = resp.json().get("records") or []
    except Exception:
        # Doğrulamanın KENDİSİ patladı: hiçbir şey bilmiyoruz. "Yok" demek
        # kopya üretirdi, "var" demek gönderiyi kaybettirirdi.
        return ag.BILINMIYOR

    simdi = datetime.datetime.now(datetime.timezone.utc)
    hedef = (metin or "").strip()
    for kayit in kayitlar:
        deger = kayit.get("value") or {}
        if (deger.get("text") or "").strip() != hedef:
            continue
        damga = deger.get("createdAt") or ""
        try:
            olusma = datetime.datetime.fromisoformat(damga.replace("Z", "+00:00"))
            if olusma.tzinfo is None:
                olusma = olusma.replace(tzinfo=datetime.timezone.utc)
            if (simdi - olusma).total_seconds() > pencere_sn:
                continue
        except ValueError:
            # Damga okunamadıysa metin eşleşmesine güven — temkinli taraf
            # "gönderi VAR" demek (ikinci bir kopya atmamak).
            pass
        return _BulunanGonderi(kayit.get("uri"), kayit.get("cid"))
    return None


# --------------------------------------------------------------------------
# ana akış
# --------------------------------------------------------------------------

def upload_video(project_dir: str, caption: str | None = None, dry_run: bool = False,
                 with_link: bool = True) -> str | None:
    """Projeyi Bluesky'a video gönderisi olarak yükler, gönderi URI'sini döner.

    dry_run=True ise HİÇBİR ağ isteği yapılmaz: gönderi metni, uzunluğu ve
    videonun ffprobe'dan okunan boyutu ekrana basılır, state.json'a
    dokunulmaz. (Gerçek hesap bağlanmadan önce metni/kadrajı doğrulamanın yolu.)
    """
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    meta = _load_meta(project_dir)
    state = _load_state(project_dir)

    # KOPYA KAPISI: önceki bir koşuda gönderi "belirsiz" kaldıysa (createRecord
    # gövdesi gitti, yanıt gelmedi ve doğrulama da okunamadı) yeniden gönderme.
    # Süpürge (`ek_platform_backfill`) bu projeyi hâlâ "hiç gitmemiş" görüyor,
    # kapı bu yüzden yükleyicinin İÇİNDE.
    ag.kapi(project_dir, "bluesky_post_uri", "Bluesky")

    if state.get("bluesky_post_uri"):
        print(f"  Bluesky: bu proje zaten yüklenmiş ({state['bluesky_post_uri']}), atlanıyor")
        return state["bluesky_post_uri"]

    # YouTube linki: state.json'da video id varsa metne ekleniyor (bkz.
    # build_post_text — Bluesky'da link cezası yok, link tıklanabilir).
    youtube_url = None
    if with_link and state.get("youtube_video_id"):
        youtube_url = f"https://youtu.be/{state['youtube_video_id']}"

    if caption is None:
        caption = build_post_text(meta, youtube_url)

    width, height = _probe_video_size(video_path)
    süre = _probe_video_duration(video_path)
    boyut_mb = os.path.getsize(video_path) / (1024 * 1024)

    print(f"  gönderi metni ({grapheme_len(caption)}/{POST_GRAPHEME_LIMIT} karakter):")
    print("  " + caption.replace("\n", "\n  "))
    print(f"  video: {width}x{height}, {boyut_mb:.1f} MB"
          + (f", {süre:.1f} sn" if süre else ""))

    if süre and süre > MAX_VIDEO_SECONDS:
        print(f"  UYARI: video {süre:.0f} sn — Bluesky sınırı {MAX_VIDEO_SECONDS} sn, "
              "servis reddedebilir.")

    if dry_run:
        print("  --dry-run: gönderi ATILMADI, state.json'a yazılmadı.")
        return None

    yüklenen = _todays_upload_count()
    if yüklenen >= DAILY_VIDEO_LIMIT:
        raise RuntimeError(
            f"Bluesky günlük video kotası dolu (bugün {yüklenen}/{DAILY_VIDEO_LIMIT} yükleme). "
            "Yarın tekrar dene."
        )

    Client, client_utils, models = _import_atproto()
    creds = _load_credentials()

    client = Client(base_url=creds["service"])
    profile = client.login(creds["handle"], creds["app_password"])
    did = client.me.did
    print(f"  giriş yapıldı: @{profile.handle} ({did})")

    # 1) servis token'ı  2) video.bsky.app'e yükle  3) iş bitene kadar yokla
    # Servis token'ı GERÇEK PDS adına alınmalı, giriş kapısı adına değil.
    pds = _pds_adresi(did, creds["service"])
    if pds != creds["service"]:
        print("  PDS: %s" % pds)
    token = _service_auth_token(client, pds)
    job_status = _upload_to_video_service(did, token, video_path)
    print(f"  video servise gönderildi: jobId={job_status['jobId']}")
    job_status = _wait_for_job(job_status["jobId"])

    # Dönen blob ham JSON ({"$type":"blob","ref":{"$link":...},"mimeType":...,
    # "size":...}) — atproto'nun BlobRef modeli alias'larla bunu doğrudan
    # doğrulayabiliyor (populate_by_name), o yüzden elle alan eşlemesi yok.
    # BlobRef, `atproto.models` altında DEĞİL — orası lexicon modelleri için
    # dinamik bir yükleyici ve BlobRef'i dışarı vermiyor
    # (AttributeError: module 'atproto_client.models' has no attribute 'BlobRef').
    # Gerçek yeri atproto_client.models.blob_ref.
    from atproto_client.models.blob_ref import BlobRef
    blob = BlobRef.model_validate(job_status["blob"])

    embed = models.AppBskyEmbedVideo.Main(
        video=blob,
        # aspectRatio olmazsa dikey video oynatıcıda bozuk görünüyor (bkz. modül
        # docstring'i). Ham piksel değerleri kabul ediliyor, sadeleştirmeye gerek yok.
        aspect_ratio=models.AppBskyEmbedDefs.AspectRatio(width=width, height=height),
    )

    rich_text = _build_rich_text(client_utils, caption)
    # ASIL İDEMPOTENT OLMAYAN ADIM BURASI: send_post ->
    # com.atproto.repo.createRecord, her çağrı YENİ bir kayıt yaratır. Bu
    # yüzden tek yeniden deneme biçimi DOĞRULAYARAK yeniden deneme:
    # gövdeden sonra kopan bağlantıda önce listRecords ile "gitmiş mi" diye
    # soruluyor (bkz. _gonderi_zaten_var_mi), ancak "kesinlikle gitmemiş"
    # cevabı alınırsa yeniden gönderiliyor. Okunamazsa state.json'a belirsiz
    # işareti bırakılıp DURULUYOR.
    # Not: atproto istemcisi httpx üzerinde çalışıyor, yani buradan gelen
    # istisnalar requests'inkiler DEĞİL — sınıflandırıcı bu yüzden tip ADINA
    # bakıyor (ag_yeniden_deneme modül docstring'i).
    post = ag.guvenli_istek(
        lambda: client.send_post(
            text=rich_text,
            embed=embed,
            # Gönderi dili: stile göre otomatik (bkz. social_text.resolve_language) —
            # Bluesky'ın dil filtreleri bunu kullanıyor, boş bırakılırsa Türkçe
            # gönderi "sadece İngilizce" filtresi olan kullanıcılara da düşer.
            langs=[resolve_language(meta)],
        ),
        ne="Bluesky createRecord (send_post)",
        dogrula=lambda: _gonderi_zaten_var_mi(pds, did, caption),
        proje=project_dir, anahtar="bluesky_post_uri", platform="Bluesky",
    )

    print(f"  tamam: uri={post.uri}")
    _save_state(project_dir, {
        "bluesky_post_uri": post.uri,
        "bluesky_post_cid": post.cid,
        "bluesky_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    return post.uri


def main():
    parser = argparse.ArgumentParser(
        description="Render edilmiş bir projeyi Bluesky'a video gönderisi olarak yükler."
    )
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/Son Kez)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Hiçbir şey gönderme; sadece metni, uzunluğunu ve video boyutunu yazdır")
    parser.add_argument("--caption", default=None,
                        help="Gönderi metni (verilmezse social_text.build_caption'dan üretilir)")
    parser.add_argument("--no-link", action="store_true",
                        help="YouTube linkini gönderi metnine EKLEME (varsayılan: ekler)")
    args = parser.parse_args()

    upload_video(args.project, caption=args.caption, dry_run=args.dry_run,
                 with_link=not args.no_link)


if __name__ == "__main__":
    main()
