"""Render edilmiş bir projeyi Telegram kanalına yükler (Bot API / sendVideo).

Kullanım:
    python upload/telegram_upload.py --project "projects/Son Kez"
    python upload/telegram_upload.py --project "projects/Son Kez" --kind her-ikisi
    python upload/telegram_upload.py --project "projects/Son Kez" --dry-run

NEDEN TELEGRAM? Diğer platformlardan (YouTube/TikTok/Instagram) farklı olarak
Telegram'da keşfet/For You algoritması YOK — dağıtım tamamen abone tabanlı.
Bunun iki sonucu var ve bu modülün tasarımı ikisine de dayanıyor:
  1. Kanal KALICI BİR ARŞİV: yüklenen video kanalda kalır, "algoritma gösterdi/
     göstermedi" diye bir kaygı yok. Bu yüzden burada asıl gönderilmek istenen
     16:9 UZUN video (şarkının tamamı), dikey 45 sn'lik teaser değil — dikey
     sürüm sadece isteğe bağlı (--kind dikey / her-ikisi).
  2. LİNK CEZASI YOK: Instagram/TikTok'ta caption'a YouTube linki koymak keşfet
     dağıtımını düşürebildiği için oralarda link paylaşımdan SONRA bir yoruma
     ekleniyor (bkz. social_text.build_youtube_comment ve instagram_upload.py).
     Telegram'da böyle bir dağıtım mekanizması olmadığı için o numaraya gerek
     yok: YouTube linki DOĞRUDAN caption'ın içine giriyor (bkz.
     _build_telegram_caption). Kanalın "YouTube'a trafik kapısı" işlevi tam da
     bu satır sayesinde çalışıyor.

KURULUM (kullanıcı tarafında, elle, bir kere):
  1. Telegram'da @BotFather ile konuş: /newbot -> bota bir ad ve kullanıcı adı
     ver. BotFather sana bir TOKEN verir ("123456789:AAF...").
  2. Kanalını aç (yoksa oluştur) -> Kanal bilgisi -> Yöneticiler -> Yönetici
     ekle -> az önce oluşturduğun botu ekle. Bota EN AZINDAN "Mesaj gönder"
     ("Post messages") yetkisi VERİLMELİ; bot kanalda yönetici değilse
     sendVideo "chat not found" / "not enough rights" hatası döner.
  3. upload/telegram_client_secrets.json dosyasını şu içerikle oluştur:
         {"bot_token": "123456789:AAF...", "chat_id": "@kanaladi"}
     chat_id, herkese açık kanallarda "@kanaladi" olabilir; kanal gizliyse
     sayısal id gerekir (-100... ile başlar; bota kanalda bir mesaj gönderip
     https://api.telegram.org/bot<token>/getUpdates çıktısından okunabilir).
     Örnek dosya: upload/telegram_client_secrets.json.example (kopyalayıp
     .example uzantısını sil, içine kendi değerlerini yaz). Gerçek dosya
     .gitignore'da — asla commit edilmemeli.

DOSYA BOYUTU SINIRI — 50 MB (Bot API):
  Resmî dokümantasyonda (core.telegram.org/bots/api, sendVideo, 2026-09-10'da
  teyit edildi) aynen şöyle geçiyor: "Bots can currently send video files of up
  to 50 MB in size, this limit may be changed in the future."
  Bizim çıktılarımız bu sınırın çok altında (ölçüm, 2026-09-10, 18 proje:
  dikey 3-5 MB, 16:9 uzun 8-21 MB; en büyüğü "Kumdan Denize" ~20 MiB) — yani
  bugün için sorun YOK. Yine de şarkı uzadıkça/bit hızı arttıkça sınıra
  yaklaşılabileceği için _ensure_size_ok() dosyayı göndermeden ÖNCE ölçüyor ve
  aşılırsa Bot API'ye boşuna yükleme yapmadan anlamlı bir hata veriyor.
  Sınır aşılırsa alternatif: Pyrogram gibi bir MTProto istemcisi (Bot API'nin
  değil, Telegram'ın asıl protokolünün üzerinde çalışır) 2 GB'a kadar dosya
  gönderebiliyor. Pyrogram bu depoda KURULU DEĞİL ve bilerek kullanılmıyor —
  bot token'ının yanında ayrıca api_id/api_hash (my.telegram.org) gerektiriyor,
  yani yeni bir kimlik bilgisi yüzeyi açıyor. 20 MB'lık videolar için bu takas
  mantıksız; sınır gerçekten aşılmaya başlarsa o zaman değerlendirilmeli.

RATE LIMIT: Telegram aynı kanala dakikada ~20 mesajda sınırlıyor. Biz proje
başına 1-2 mesaj gönderdiğimiz için pratikte bu sınıra çarpmıyoruz; yine de
_api_post() 429 yanıtında yanıtın parameters.retry_after alanını okuyup o kadar
bekleyip tekrar deniyor (ResponseParameters.retry_after: "the number of seconds
left to wait before the request can be repeated").
"""

import argparse
import json
import os
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_io
import ag_yeniden_deneme as ag
from ffmpeg_utils import get_audio_duration
from social_text import build_caption, resolve_language

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = os.path.join(UPLOAD_DIR, "telegram_client_secrets.json")

API_BASE = "https://api.telegram.org"

# Bot API'nin dosya gönderme sınırı (bkz. modül docstring'i). Telegram "50 MB"
# derken ondalık MB kastediyor gibi görünüyor ama emin olmadığımız için MiB
# (daha KÜÇÜK olan, yani daha temkinli olan) üzerinden hesaplıyoruz — böylece
# sınırın hemen altındaki bir dosyada "geçer sandık, API reddetti" durumuna
# düşmüyoruz.
MAX_FILE_BYTES = 50 * 1024 * 1024

# sendVideo caption sınırı: "0-1024 characters after entities parsing"
# (core.telegram.org/bots/api, 2026-09-10). Bizim caption'larımız 200-252
# karakter aralığında, yani sorun yok — ama YouTube linki de eklendiği için
# yine de _clamp_caption() ile kontrol ediliyor.
MAX_CAPTION_CHARS = 1024

# --kind seçeneği -> (video dosyası, state.json anahtar öneki, insan okunur ad).
# Anahtar deseni depodaki YouTube deseniyle aynı: uzun sürüm sade anahtarı
# (telegram_message_id) alır, dikey sürüm "_shorts_" ekli anahtarı alır
# (bkz. state.json'daki youtube_video_id / youtube_shorts_video_id).
KINDS = {
    "uzun": (os.path.join("output", "youtube_16x9.mp4"), "telegram", "16:9 uzun video"),
    "dikey": (os.path.join("output", "shorts_9x16.mp4"), "telegram_shorts", "9:16 dikey video"),
}


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
    """state.json'a alan ekler/günceller — ATOMİK (state_io.durum_yaz).

    NEDEN: eskiden hedefin ÜSTÜNE doğrudan yazılıyordu; `open(..., "w")`
    dosyayı önce SIFIRLIYOR, `json.dump` bitmeden süreç ölürse diskte YARIM
    bir JSON kalıyor. `uyumluluk._durum()` sertleştirildikten sonra bozuk bir
    state.json artık sessizce {} sayılmıyor — boru hattını DURDURUYOR.
    Ayrıca `auto_process` (saatlik) ve `dj_famous_process` (haftalık) AYRI
    kilitler kullanıp aynı state.json'a yazabiliyor; kaybolan bir
    `telegram_message_id` bu platformda İKİNCİ bir yükleme demek."""
    state = _load_state(project_dir)
    state.update(updates)
    state_io.durum_yaz(project_dir, state)


def _load_credentials() -> dict:
    """telegram_client_secrets.json'u okur. Dosya yoksa/eksikse KURULUMU ANLATAN
    bir hata verir — diğer servislerde olduğu gibi sessizce boş token'la API'ye
    gidip anlamsız bir 401 almak yerine, kullanıcıya ne yapması gerektiğini
    doğrudan söylüyoruz (BotFather adımları modül docstring'inde de var)."""
    if not os.path.isfile(SECRETS_PATH):
        raise FileNotFoundError(
            f"{SECRETS_PATH} bulunamadı.\n"
            "Telegram kanalına yükleme yapmak için bir bot kimliği gerekiyor:\n"
            "  1. Telegram'da @BotFather ile konuş, /newbot komutuyla bir bot oluştur, "
            "sana verdiği token'ı kopyala.\n"
            "  2. Kanalında: Kanal bilgisi > Yöneticiler > Yönetici ekle > bu botu ekle "
            "(en azından 'Mesaj gönder' yetkisiyle) — bot kanalda yönetici değilse "
            "Telegram 'chat not found' der.\n"
            "  3. Şu dosyayı oluştur:\n"
            f"     {SECRETS_PATH}\n"
            '     {"bot_token": "123456789:AAF...", "chat_id": "@kanaladi"}\n'
            f"  Örnek dosya hazır: {SECRETS_PATH}.example"
        )
    with open(SECRETS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)
    eksik = [k for k in ("bot_token", "chat_id") if not creds.get(k)]
    if eksik:
        raise ValueError(
            f"{SECRETS_PATH} içinde şu alan(lar) eksik ya da boş: {', '.join(eksik)}. "
            'Beklenen biçim: {"bot_token": "123456789:AAF...", "chat_id": "@kanaladi"}'
        )
    return creds


def _probe_dimensions(video_path: str) -> tuple[int | None, int | None]:
    """Videonun genişlik/yüksekliğini ffprobe ile okur.

    NOT: Süre için depodaki hazır yardımcı (ffmpeg_utils.get_audio_duration)
    kullanılıyor — adı "audio" olsa da `format=duration` sorgusu konteyner
    seviyesinde çalıştığı için mp4'te de doğru sonucu veriyor, ayrı bir kopya
    yazmaya gerek yok. Genişlik/yükseklik için ffmpeg_utils'te hazır bir
    fonksiyon YOK (orada ffprobe sadece süre için kullanılıyor), o yüzden bu
    küçük yardımcı burada duruyor.

    Ölçüm başarısız olursa None döner — width/height/duration Bot API'de
    ZORUNLU DEĞİL (hepsi "Optional"), gönderilmezse Telegram videoyu yine de
    kabul eder, sadece istemci oynatıcı önizlemeyi/en-boy oranını kendi
    tahmin eder. Yani ffprobe yoksa yükleme çökmesin, sadece kalitesi düşsün.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print("  UYARI: ffprobe bulunamadı — width/height gönderilmeyecek.")
        return None, None
    if result.returncode != 0:
        print(f"  UYARI: ffprobe boyut okuyamadı: {result.stderr.strip()}")
        return None, None
    try:
        width, height = result.stdout.strip().split("x")[:2]
        return int(width), int(height)
    except ValueError:
        print(f"  UYARI: ffprobe beklenmedik boyut çıktısı verdi: {result.stdout!r}")
        return None, None


def _probe_duration(video_path: str) -> int | None:
    """Süreyi saniye (tam sayı) olarak döndürür — Bot API duration alanı Integer."""
    try:
        return int(round(get_audio_duration(video_path)))
    except (RuntimeError, FileNotFoundError, OSError) as e:
        print(f"  UYARI: süre okunamadı, duration gönderilmeyecek: {e}")
        return None


def _ensure_size_ok(video_path: str) -> int:
    """Dosya boyutunu ölçer; 50 MB sınırı aşılıyorsa yüklemeye HİÇ başlamadan
    anlamlı bir hata verir (bkz. modül docstring'i — Pyrogram/MTProto notu).
    Boyutu bayt olarak döndürür."""
    size = os.path.getsize(video_path)
    if size > MAX_FILE_BYTES:
        raise ValueError(
            f"{video_path} dosyası {size / 1024 / 1024:.1f} MB — Telegram Bot API'nin "
            f"sendVideo sınırı 50 MB, bu dosya gönderilemez.\n"
            "Seçenekler: (a) videoyu daha düşük bit hızıyla yeniden render et, "
            "(b) sadece dikey sürümü gönder (--kind dikey), "
            "(c) 2 GB'a kadar destekleyen bir MTProto istemcisi (ör. Pyrogram) kullan — "
            "bu depoda KURULU DEĞİL, ayrıca api_id/api_hash gerektirir."
        )
    return size


def _youtube_link_line(video_id: str, lang: str) -> str:
    """Caption'ın sonuna eklenecek YouTube satırı.

    social_text.build_youtube_comment() BİLEREK kullanılmıyor: o metin
    Instagram/TikTok'a özel — "@handle hesabına dokun, bio'daki linkten de
    ulaşabilirsin" diyor, çünkü o platformlarda düz metin URL'ler tıklanamıyor
    ve tek tıklanabilir eleman mention oluyor. Telegram'da bu sorunların İKİSİ
    de yok: düz metin URL'ler otomatik olarak tıklanabilir hale geliyor ve
    caption'da link bulundurmanın dağıtıma bir zararı yok. O yüzden burada
    doğrudan, sade bir link satırı üretiliyor."""
    url = f"https://youtu.be/{video_id}"
    if lang == "en":
        return f"🎧 Full track on YouTube: {url}"
    return f"🎧 Şarkının tamamı YouTube'da: {url}"


def _clamp_caption(caption: str) -> str:
    """Caption'ı Telegram'ın 1024 karakter sınırına sığdırır.

    Pratikte devreye girmesi beklenmiyor (bizim caption'larımız YouTube linkiyle
    birlikte bile ~300 karakter) ama şablon/hashtag havuzu büyürse sessizce API
    hatası almak yerine burada kırpmak daha iyi. Kırpma satır sınırından
    yapılıyor — hashtag bloğunun ortasından kesip yarım hashtag bırakmasın."""
    if len(caption) <= MAX_CAPTION_CHARS:
        return caption
    print(f"  UYARI: caption {len(caption)} karakter, {MAX_CAPTION_CHARS} sınırına kırpılıyor.")
    kirpik = caption[:MAX_CAPTION_CHARS - 1]
    son_satir_sonu = kirpik.rfind("\n")
    if son_satir_sonu > MAX_CAPTION_CHARS // 2:
        kirpik = kirpik[:son_satir_sonu]
    return kirpik.rstrip() + "…"


def _build_telegram_caption(project_dir: str, meta: dict) -> str:
    """Ortak caption şablonuna (social_text.build_caption) YouTube linkini
    ekler. Link, state.json'daki youtube_video_id'den geliyor — yani YouTube
    yüklemesi henüz yapılmadıysa (ya da başarısız olduysa) caption linksiz
    gider, kanal yine de arşiv işlevini görür."""
    caption = build_caption(meta)
    video_id = _load_state(project_dir).get("youtube_video_id")
    if video_id:
        caption = f"{caption}\n\n{_youtube_link_line(video_id, resolve_language(meta))}"
    else:
        print("  NOT: state.json'da youtube_video_id yok — caption'a YouTube linki eklenmedi.")
    return _clamp_caption(caption)


def _api_post(bot_token: str, method: str, data: dict, files: dict | None = None,
              max_retries: int = 3, proje: str = "", anahtar: str = "") -> dict:
    """Bot API'ye bir istek gönderir ve 'result' alanını döndürür.

    AĞ HATASINDA YENİDEN DENEME — SINIFLANDIRARAK (2026-09-12'de eklendi):
    bu docstring ve aşağıdaki `seek(0)` mantığı yeniden denemeyi ZATEN
    varsayıyordu ama kod ilk ağ istisnasında `raise` ediyordu; kendi niyetini
    uygulamıyordu. Canlı bedeli `auto_process.log` satır 3400'de duruyor
    ("Telegram sendVideo: ağ hatası (ConnectionError)" — o yükleme kayboldu).
    KÖRÜ KÖRÜNE düzeltmek yasaktı: `sendVideo` idempotent DEĞİL, bağlantı
    gövde gittikten sonra koparsa yeniden deneme kanala İKİNCİ bir video atar
    ve bu, deponun en büyük riskinin ("toplu üretilmiş AI içerik") ta kendisi.
    Bu yüzden karar `ag_yeniden_deneme.sinifla()`ya devredildi: bağlantı HİÇ
    kurulamadıysa (ConnectTimeout/DNS — requests belgesi aynen "safe to retry"
    diyor) yeniden denenir; yanıt beklenirken koptuysa (ReadTimeout vb.)
    DENENMEZ, state.json'a "belirsiz" işareti bırakılır.
    TELEGRAM'DA DOĞRULAMA YOK (`dogrula=None`): Bot API'nin yöntem listesinde
    bir sohbetin geçmişini okuyan yöntem yok, `getUpdates` de yalnızca GELEN
    ("New incoming ... post") güncellemeleri veriyor — botun kendi gönderdiği
    mesaj oradan okunamıyor. Yani tek dürüst seçenek "sessiz kalma".

    429 (flood control) yanıtında Telegram, yanıtın parameters.retry_after
    alanında kaç saniye beklenmesi gerektiğini söylüyor — o kadar bekleyip
    tekrar deniyoruz. Kanal başına dakikada ~20 mesaj sınırı var; biz proje
    başına 1-2 mesaj gönderdiğimiz için buraya normalde hiç düşülmemeli, ama
    aynı anda birden çok proje işlenirse (auto_process.py toplu çalıştırması)
    bu koruma işe yarar.

    DİKKAT: files verildiğinde dosya nesnesi tüketiliyor, o yüzden tekrar
    denemeden önce dosyanın başına geri sarılıyor (seek(0)) — aksi halde
    ikinci deneme 0 baytlık bir video gönderirdi.

    GÜVENLİK — ağ istisnaları BURADA yakalanıp token'sız yeniden fırlatılıyor:
    bot token URL'in YOLUNDA (`/bot<token>/<method>`) ve `requests`'in ağ
    istisnaları (ConnectionError/ReadTimeout) mesajlarının içinde TAM isteği
    URL'sini taşıyor. İstisna yukarı çıkıp `log(f"... HATA: {e}")` ile
    yazılırsa bot token düz metin olarak log'a düşer — bot token tek başına
    kanala mesaj göndermeye/silmeye yeter. Bu tam olarak 2026-09-04'te
    Instagram token'ıyla yaşanan olayın aynısı (bkz. gizli_maskele.py);
    orada bir ağ kesintisi yetmişti, saldırgan gerekmedi."""
    url = f"{API_BASE}/bot{bot_token}/{method}"

    def _basa_sar():
        # DİKKAT: files verildiğinde dosya nesnesi tüketiliyor, o yüzden HER
        # denemeden önce başa sarılıyor — aksi halde ikinci deneme 0 baytlık
        # bir video gönderirdi. `hazirla` ilk denemede de çalışır, yani
        # "sadece yeniden denemede hazırlanan" bir yol kalmıyor.
        if files:
            for f in files.values():
                if hasattr(f, "seek"):
                    f.seek(0)

    for deneme in range(max_retries):
        # Yükleme uzun sürebildiği için okuma zaman aşımı bilerek geniş (300 sn).
        # DIŞ döngü 429 (rate limit) içindir — o bir AĞ hatası değil, BAŞARILI
        # bir yanıt; sınıflandırıcının işi değil, davranışı aynen korunuyor.
        resp = ag.guvenli_istek(
            lambda: requests.post(url, data=data, files=files, timeout=(10, 300)),
            ne=f"Telegram {method}",
            hazirla=_basa_sar,
            proje=proje, anahtar=anahtar, platform="Telegram",
        )

        if resp.status_code == 429:
            try:
                retry_after = int(resp.json().get("parameters", {}).get("retry_after", 5))
            except (ValueError, json.JSONDecodeError):
                retry_after = 5
            print(f"  Telegram rate limit (429) — {retry_after} sn bekleniyor...")
            time.sleep(retry_after + 1)
            continue

        try:
            payload = resp.json()
        except json.JSONDecodeError:
            # `resp.raise_for_status()` BİLEREK kullanılmıyor: requests'in
            # HTTPError mesajı "... for url: <tam url>" içeriyor, o URL'in
            # yolunda da bot token var. Aynı bilgiyi (HTTP kodu) token'sız
            # veriyoruz.
            raise RuntimeError(
                f"Telegram {method}: HTTP {resp.status_code}, beklenmedik yanıt "
                f"{resp.text[:200]!r}"
            ) from None

        if not payload.get("ok"):
            raise RuntimeError(
                f"Telegram {method} hatası ({payload.get('error_code')}): "
                f"{payload.get('description')}"
            )
        return payload["result"]

    raise RuntimeError(f"Telegram {method}: rate limit nedeniyle {max_retries} denemede gönderilemedi.")


def upload_video(project_dir: str, kind: str = "uzun", dry_run: bool = False) -> int | None:
    """Tek bir videoyu (kind: 'uzun' ya da 'dikey') kanala gönderir.
    message_id döner; --dry-run'da hiçbir şey göndermez, None döner."""
    if kind not in KINDS:
        raise ValueError(f"Bilinmeyen --kind: {kind!r} (beklenen: {', '.join(KINDS)})")
    rel_path, state_prefix, etiket = KINDS[kind]
    durum_anahtari = f"{state_prefix}_message_id"

    # KOPYA KAPISI: önceki bir koşuda bu gönderi "belirsiz" kaldıysa (gövde
    # gitti, yanıt gelmedi) YENİDEN YÜKLEME. Kapı burada, çağıranda DEĞİL:
    # bu fonksiyonu üç ayrı yol çağırıyor (auto_process._ek_platformlari_isle,
    # upload/ek_platform_backfill süpürgesi, elle --project) ve süpürge
    # projeyi "hiç gitmemiş" görüp her koşuda yeniden denemeye hazır —
    # kopyayı üretecek olan tam olarak orası.
    ag.kapi(project_dir, durum_anahtari, "Telegram")

    video_path = os.path.join(project_dir, rel_path)
    if not os.path.isfile(video_path):
        raise FileNotFoundError(
            f"{video_path} bulunamadı — önce render.py ile bu projeyi render et."
        )

    size = _ensure_size_ok(video_path)
    width, height = _probe_dimensions(video_path)
    duration = _probe_duration(video_path)
    meta = _load_meta(project_dir)
    caption = _build_telegram_caption(project_dir, meta)

    print(f"  {etiket}: {video_path} ({size / 1024 / 1024:.1f} MB, "
          f"{width}x{height}, {duration} sn)")

    if dry_run:
        # Kimlik bilgisi henüz kurulmamış olabilir — kuru çalıştırmada bunu
        # HATA saymıyoruz, amaç zaten kullanıcının göndermeden önce ne
        # gideceğini görebilmesi (BotFather adımlarını yapmadan da çalışsın).
        try:
            chat_id = _load_credentials()["chat_id"]
        except (FileNotFoundError, ValueError):
            chat_id = "(kimlik bilgisi yok)"
            print(f"  NOT: {os.path.basename(SECRETS_PATH)} henüz yok/eksik — gerçek "
                  "gönderimden önce oluşturulmalı (bkz. modül docstring'i, BotFather adımları). "
                  "Kuru çalıştırma sürdürülüyor.")
        print(f"  [dry-run] hedef chat_id: {chat_id}")
        print(f"  [dry-run] supports_streaming=True, caption ({len(caption)}/{MAX_CAPTION_CHARS} karakter):")
        for satir in caption.split("\n"):
            print(f"    | {satir}")
        print("  [dry-run] gönderim YAPILMADI.")
        return None

    creds = _load_credentials()
    chat_id = creds["chat_id"]

    data = {
        "chat_id": chat_id,
        "caption": caption,
        # supports_streaming: video tamamen indirilmeden oynatılabilsin diye —
        # olmadan Telegram istemcisi dosyayı önce baştan sona indiriyor.
        "supports_streaming": "true",
        # parse_mode BİLEREK gönderilmiyor: caption'da hashtag'ler, emoji ve
        # tırnak/altçizgi gibi karakterler var; Markdown/HTML modunda bunların
        # kaçırılması (escape) gerekirdi ve tek bir kaçırılmamış karakter tüm
        # gönderimi "can't parse entities" hatasıyla düşürürdü. Düz metinde
        # Telegram URL'leri ve #hashtag'leri zaten kendisi tıklanabilir yapıyor.
    }
    if duration is not None:
        data["duration"] = duration
    if width and height:
        data["width"] = width
        data["height"] = height

    print(f"  Telegram'a gönderiliyor ({chat_id})...")
    with open(video_path, "rb") as video_file:
        result = _api_post(
            creds["bot_token"], "sendVideo", data,
            files={"video": (os.path.basename(video_path), video_file, "video/mp4")},
            # proje/anahtar: belirsiz kalırsa işaret DOĞRU state alanına
            # (süpürgenin baktığı anahtara) yazılsın diye.
            proje=project_dir, anahtar=durum_anahtari,
        )

    message_id = result["message_id"]
    print(f"  tamam: message_id={message_id}")

    _save_state(project_dir, {
        durum_anahtari: message_id,
        f"{state_prefix}_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "telegram_chat_id": chat_id,
    })
    return message_id


def upload_project(project_dir: str, kind: str = "uzun", dry_run: bool = False) -> dict:
    """--kind 'her-ikisi' ise iki videoyu da (önce uzun, sonra dikey) gönderir.
    {kind: message_id} sözlüğü döner."""
    kinds = ["uzun", "dikey"] if kind == "her-ikisi" else [kind]
    sonuc = {}
    for i, k in enumerate(kinds):
        if i:
            # İki mesaj arasında küçük bir nefes — dakikada 20 mesaj sınırına
            # yaklaşmıyoruz ama arka arkaya iki büyük yükleme yapmanın flood
            # kontrolünü tetiklemesine gerek yok.
            time.sleep(2)
        sonuc[k] = upload_video(project_dir, k, dry_run)
    return sonuc


def main():
    parser = argparse.ArgumentParser(
        description="Render edilmiş bir projeyi Telegram kanalına yükler (Bot API / sendVideo)."
    )
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. \"projects/Son Kez\")")
    parser.add_argument(
        "--kind", default="uzun", choices=["dikey", "uzun", "her-ikisi"],
        help="Hangi video gönderilsin: 'uzun' (output/youtube_16x9.mp4, VARSAYILAN — "
             "kanal kalıcı arşiv olduğu için şarkının tamamı gönderiliyor), "
             "'dikey' (output/shorts_9x16.mp4) ya da 'her-ikisi'.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Hiçbir şey göndermez — ne gönderileceğini (dosya, boyut, süre, caption) yazdırır.",
    )
    args = parser.parse_args()

    upload_project(args.project, args.kind, args.dry_run)


if __name__ == "__main__":
    main()
