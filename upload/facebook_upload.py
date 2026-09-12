"""Render edilmiş bir projeyi Facebook Sayfası'na yükler (Facebook Graph API).

Kullanım:
    python upload/facebook_upload.py --project "projects/beni bırakma"
    python upload/facebook_upload.py --project "projects/beni bırakma" --kind her-ikisi
    python upload/facebook_upload.py --project "projects/beni bırakma" --no-schedule

İki format destekleniyor:
  - "reels"  -> output/shorts_9x16.mp4, 3 fazlı Reels API'si (video_reels)
  - "uzun"   -> output/youtube_16x9.mp4, klasik Sayfa video ucu (/{page_id}/videos)

BU MODÜL instagram_upload.py'den KOPYALANDI ama İKİ NOKTADA BİLEREK AYRILIYOR —
oradaki deseni buraya geri taşımaya çalışma, ikisi de gerekli DEĞİL:

1. NETLIFY ADIMI YOK. instagram_upload.py'de `_upload_to_netlify()` var çünkü
   Instagram Graph API dosya yüklemeyi DESTEKLEMİYOR, sadece HERKESE AÇIK bir
   `video_url` kabul ediyor — videoyu önce bir yere barındırmak zorundaydık.
   Facebook'ta ham binary DOĞRUDAN gidiyor: Reels'te rupload.facebook.com'a
   (faz 2), uzun formatta multipart `source` alanıyla graph-video.facebook.com'a.
   Yani aracı barındırma (ve netlify_client_secrets.json) burada GEREKMİYOR —
   bir dosya daha az, bir hata kaynağı daha az.

2. ZAMANLAMA YERLİ (native). instagram_upload.py KENDİ golden-hour kuyruğunu
   tutuyor (`instagram_creation_id` state.json'a yazılıp bir sonraki koşuda
   `try_publish_pending()` ile yayınlanıyor) çünkü Instagram Graph API'de
   zamanlanmış yayın YOK. Facebook'ta VAR: Reels'te `video_state=SCHEDULED` +
   `scheduled_publish_time`, uzun formatta `published=false` +
   `scheduled_publish_time`. Bu yüzden burada KUYRUK YOK, `try_publish_pending()`
   benzeri bir fonksiyon da YOK — zamanlamayı Facebook'un kendisine bırakıyoruz
   (YouTube'un `status.publishAt`'iyle birebir aynı desen, bkz. youtube_upload.py).
   `config.next_golden_publish_time()` None dönerse ŞU AN golden-hour içindeyiz,
   hemen yayınlanır; datetime dönerse o ana zamanlanır.

Doğrulanmış uçlar (resmî Meta dokümantasyonu):
  - Reels 3 fazlı akış: developers.facebook.com/docs/video-api/guides/reels-publishing/
  - Uzun format parametreleri (source/description/title/published/
    scheduled_publish_time/thumb): developers.facebook.com/docs/graph-api/reference/page/videos/
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ag_yeniden_deneme as ag
import config
import state_io
from facebook_auth import get_access_token
from gizli_maskele import maskele_istisna
from social_text import build_caption, build_youtube_comment, resolve_language
# Kok listesi TEK kaynaktan: bkz. uyumluluk.KOK_ADLARI'nin uzerindeki not ve
# bekleyen_yorumlari_tamamla()'nin docstring'i.
from uyumluluk import proje_klasorleri

GRAPH_VERSION = "v21.0"
GRAPH_API = f"https://graph.facebook.com/{GRAPH_VERSION}"
# Büyük dosyalar için Meta ayrı bir host öneriyor — uzun format (multipart
# `source`) bu hosttan gidiyor. Reels'in faz 2'si zaten faz 1'in döndürdüğü
# `upload_url`'i (rupload.facebook.com) kullanıyor, orada host seçimi bize ait değil.
GRAPH_VIDEO_API = f"https://graph-video.facebook.com/{GRAPH_VERSION}"

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]

# Facebook zamanlanmış gönderiyi en erken 10 dakika sonrası için kabul ediyor
# (Reels: 10 dk - 29 gün, uzun format: 10 dk - 6 ay). Otomatik kademeleme
# (auto_process._auto_pace_count) bizi golden-hour'un HEMEN öncesine denk
# getirebilir — ör. 11:56'da koşarsak bir sonraki pencere 12:00, yani 4 dakika
# sonra: bu API tarafından REDDEDİLİR. O yüzden eşiğin altındaki farkları
# zamanlamıyoruz, doğrudan yayınlıyoruz (4 dakika erken çıkmak, hata alıp hiç
# çıkmamaktan iyi — pratikte zaten pencerenin içindeyiz sayılır).
MIN_SCHEDULE_LEAD_SECONDS = 15 * 60


class FacebookAPIError(RuntimeError):
    """Graph API'nin gövdede döndürdüğü hata — bkz. _graph_json()."""


def _find_cover(project_dir: str, vertical: bool) -> str | None:
    """Kapak dosyasını bulur. `vertical=True` ise önce cover_vertical.*'a bakar
    (9:16 içerik için tam kadraj), yoksa 16:9 cover.*'a düşer; `vertical=False`
    ise doğrudan 16:9 tercih edilir (uzun format videosu 16:9).

    NOT: Kapak SADECE uzun formatta kullanılabiliyor (`thumb` parametresi,
    resmî dokümanda doğrulandı). Reels'in 3 fazlı akışında kapak/thumbnail
    parametresi RESMÎ DOKÜMANDA YOK — Facebook Reels'in kapağını videonun
    kendi karelerinden seçiyor. Yanlış/teyitsiz bir alan adı göndermek her
    yüklemede hataya yol açacağı için (bkz. instagram_upload.py'deki
    `is_ai_generated` notu — aynı gerekçe) Reels tarafına kapak EKLENMEDİ.
    """
    names = (COVER_VERTICAL_NAMES + COVER_NAMES) if vertical else (COVER_NAMES + COVER_VERTICAL_NAMES)
    for name in names:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


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
    bir JSON kaliyor. `uyumluluk._durum()` sertlestirildikten sonra bozuk bir
    state.json artik sessizce {} sayilmiyor — boru hattini DURDURUYOR. Ayrica
    `auto_process` (saatlik) ve `dj_famous_process` (haftalik) AYRI kilitler
    kullanip ayni state.json'a yazabiliyor; kaybolan bir `facebook_video_id`
    bu platformda IKINCI bir yukleme demek."""
    state = _load_state(project_dir)
    state.update(updates)
    state_io.durum_yaz(project_dir, state)


def _graph_json(resp: requests.Response, ne_yapiliyordu: str) -> dict:
    """Graph API yanıtını sözlüğe çevirir ve HATA VARSA anlamlı bir istisna atar.

    `raise_for_status()` TEK BAŞINA YETMİYOR: Graph API bazı hataları HTTP 200
    ile, gövdedeki `{"error": {...}}` bloğunda döndürüyor (özellikle Reels
    faz 2/faz 3'te). Sessizce "başarılı" saymak, state.json'a var olmayan bir
    video_id yazmak demek — bu yüzden hem HTTP kodu hem gövde kontrol ediliyor.
    Hata mesajına `code`/`error_subcode` de konuyor: Meta'nın hata kataloğunda
    asıl teşhis oradan çıkıyor (ör. 190 = token geçersiz, 200 = izin eksik,
    368 = geçici blok), `fbtrace_id` ise Meta desteğine bildirmek için gerekli.
    """
    try:
        data = resp.json()
    except ValueError:
        raise FacebookAPIError(
            f"{ne_yapiliyordu}: Facebook JSON olmayan bir yanıt döndü "
            f"(HTTP {resp.status_code}): {resp.text[:500]}"
        )

    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        raise FacebookAPIError(
            f"{ne_yapiliyordu}: {err.get('message', 'bilinmeyen hata')} "
            f"(code={err.get('code')}, error_subcode={err.get('error_subcode')}, "
            f"type={err.get('type')}, fbtrace_id={err.get('fbtrace_id')}, "
            f"HTTP {resp.status_code})"
        )

    if resp.status_code >= 400:
        raise FacebookAPIError(
            f"{ne_yapiliyordu}: HTTP {resp.status_code}, gövdede `error` alanı yok: {resp.text[:500]}"
        )

    if not isinstance(data, dict):
        raise FacebookAPIError(f"{ne_yapiliyordu}: beklenmeyen yanıt tipi: {data!r}")

    return data


def _uzun_video_bul(page_id: str, access_token: str, baslik: str,
                    aciklama: str, kesin: bool, pencere_sn: int = 1800):
    """Uzun format yüklemesi BELİRSİZ kaldığında "gitti mi" sorusunu sorar.

    `POST /{page_id}/videos` TEK istekte hem dosyayı hem meta veriyi
    gönderiyor ve İDEMPOTENT DEĞİL — ikinci bir çağrı Sayfa'ya İKİNCİ bir
    video koyar. Reels'in aksine burada faz 1'den gelen sabit bir `video_id`
    yok, o yüzden tek dürüst yol listeyi okumak:
    `GET /{page_id}/videos` (resmî /{page-id}/videos referansı — bu modülün
    docstring'inde zaten kaynak olarak anılıyor).

    `kesin=False` ise "bulamadım" cevabı GÜVENİLİR DEĞİLDİR ve BILINMIYOR
    dönülür. Bu, gönderi ZAMANLANMIŞ (published=false) olduğunda geçerli:
    yayınlanmamış bir videonun bu listede görünüp görünmediği resmî
    dokümanda garanti EDİLMİYOR, ve "yok" sanıp yeniden yüklemek tam olarak
    kaçınmaya çalıştığımız kopyayı üretirdi. Temkinli taraf her zaman
    "bilmiyorum".

    Dönüş: video id (str) | None (kesinlikle yok) | ag.BILINMIYOR.
    """
    try:
        resp = requests.get(
            f"{GRAPH_API}/{page_id}/videos",
            params={"fields": "id,title,description,created_time",
                    "limit": 10, "access_token": access_token},
            timeout=(10, 30),
        )
        ogeler = _graph_json(resp, "Facebook video listesi (doğrulama)").get("data") or []
    except Exception:
        return ag.BILINMIYOR      # doğrulamanın kendisi patladı

    simdi = datetime.now().astimezone()
    for oge in ogeler:
        ayni = ((baslik and (oge.get("title") or "") == baslik)
                or (aciklama and (oge.get("description") or "") == aciklama))
        if not ayni:
            continue
        damga = oge.get("created_time") or ""
        try:
            olusma = datetime.strptime(damga, "%Y-%m-%dT%H:%M:%S%z")
            if (simdi - olusma).total_seconds() > pencere_sn:
                continue          # eski bir yükleme, bu koşunun ürünü değil
        except ValueError:
            pass                  # damga okunamadı: eşleşmeye güven (temkinli)
        return oge.get("id")
    return None if kesin else ag.BILINMIYOR


def _yorum_zaten_var_mi(object_id: str, access_token: str, message: str):
    """YouTube linki yorumu BELİRSİZ kaldıysa: aynı yorum zaten düşmüş mü?

    `POST /{object_id}/comments` de idempotent değil — aynı gönderinin altına
    iki kere aynı yorum düşmesi mümkün. Zararı bir kopya videodan KÜÇÜK ama
    aynı sınıftan bir hata; `GET /{object_id}/comments` ucu ucuz olduğu için
    burada da doğrulanıyor.
    """
    try:
        resp = requests.get(
            f"{GRAPH_API}/{object_id}/comments",
            params={"fields": "id,message", "limit": 25,
                    "access_token": access_token},
            timeout=(10, 30),
        )
        ogeler = _graph_json(resp, "Facebook yorum listesi (doğrulama)").get("data") or []
    except Exception:
        return ag.BILINMIYOR
    for oge in ogeler:
        if (oge.get("message") or "").strip() == (message or "").strip():
            return oge.get("id") or True
    return None


def _compute_scheduled_time(schedule: bool, ek_dakika: int = 0) -> tuple[int | None, datetime | None]:
    """(unix_timestamp, datetime) döner; ikisi de None ise HEMEN yayınlanmalı.

    `config.next_golden_publish_time()` None dönerse ŞU AN golden-hour
    penceresinin içindeyiz — zamanlamaya gerek yok, hemen yayınla. Datetime
    dönerse bir sonraki pencerenin başlangıcıdır. MIN_SCHEDULE_LEAD_SECONDS'ten
    yakınsa (bkz. o sabitin notu) zamanlama yerine yine hemen yayınlanır.
    """
    if not schedule:
        return None, None

    target = config.next_golden_publish_time()
    if target is None:
        return None, None

    # ek_dakika: aynı pencereye BİRDEN FAZLA gönderi düşerken araya mesafe
    # koymak için. next_golden_publish_time() her çağrıda pencerenin AYNI
    # başlangıç anını döndürüyor, dolayısıyla arka arkaya iki yükleme aynı
    # saniyeye zamanlanıyordu — aynı Sayfadan aynı anda çıkan iki Reel
    # birbirinin erişimini bölüyor. Katalogda bu sorun yok çünkü
    # facebook_backfill saatte bir çalışıp tek gönderi atıyor (GUNLUK_TAVAN);
    # elle toplu geri doldurmada ise aralığı çağıran veriyor.
    if ek_dakika:
        target = target + timedelta(minutes=ek_dakika)

    lead = (target - datetime.now(target.tzinfo)).total_seconds()
    if lead < MIN_SCHEDULE_LEAD_SECONDS:
        print(f"  Facebook: golden-hour'a {int(lead // 60)} dk kaldı "
              "(Facebook'un 10 dk alt sınırına çok yakın), zamanlamadan hemen yayınlanıyor")
        return None, None

    return int(target.timestamp()), target


def _post_youtube_comment(object_id: str, access_token: str, project_dir: str) -> bool:
    """YouTube linkini gönderiye İLK YORUM olarak ekler; başarılıysa True döner.

    Link neden açıklamada değil: Instagram/TikTok'takiyle AYNI gerekçe (bkz.
    social_text.build_caption ve CLAUDE.md) — off-platform link taşıyan gönderiler
    dağıtımda cezalandırılıyor. Facebook'un haber kaynağı sıralaması da dışa link
    veren gönderilere aynı şekilde davranıyor, bu yüzden link paylaşımdan SONRA
    ayrı bir yoruma konuyor.

    Yorum başarısız olsa bile ana yükleme zaten tamamlandığı için HATA
    FIRLATMIYORUZ, sadece logluyoruz (instagram_upload._publish_container ile
    aynı davranış) — çağıran False'u görüp state'e "beklemede" yazabilir.
    """
    video_id = _load_state(project_dir).get("youtube_video_id")
    if not video_id:
        return False

    lang = resolve_language(_load_meta(project_dir))
    # platform="instagram": build_youtube_comment'in @handle havuzunda (
    # config.SOCIAL_HANDLES) henüz "facebook" anahtarı YOK. Instagram handle'ı
    # Facebook yorumunda TIKLANABİLİR bir mention DEĞİL, sadece düz metin —
    # yine de doğru hesap adını gösteriyor. config.SOCIAL_HANDLES'a bir
    # "facebook" anahtarı eklenirse burası da ona çevrilmeli.
    message = build_youtube_comment(f"https://youtu.be/{video_id}", lang, platform="instagram")

    # ÖNCEKİ KOŞUDAN KALAN BELİRSİZLİK: yorum POST'u gövdeden sonra koptuysa
    # bayrak `pending` kaldı ve BU çağrı, hiçbir şey sormadan İKİNCİ bir yorum
    # atacaktı. Önce doğrula: varsa tamam say, kesinlikle yoksa normal akışa
    # devam et, okunamadıysa bu koşuda hiç dokunma (bayrak beklemede kalır).
    if ag.belirsiz_mi(project_dir, "facebook_comment"):
        durum = _yorum_zaten_var_mi(object_id, access_token, message)
        if durum is ag.BILINMIYOR:
            print("  UYARI: bekleyen YouTube yorumu doğrulanamadı, bu koşuda "
                  "yeniden denenmiyor (kopya yorum riski).")
            return False
        ag.belirsizi_temizle(project_dir, "facebook_comment")
        if durum is not None:
            print("  YouTube linki yorumu zaten eklenmiş (doğrulandı).")
            return True

    try:
        data = ag.guvenli_istek(
            lambda: _graph_json(
                requests.post(
                    f"{GRAPH_API}/{object_id}/comments",
                    data={"message": message, "access_token": access_token},
                    timeout=(10, 30),
                ),
                "YouTube linki yorumu"),
            ne="Facebook yorum (POST /comments)",
            # Yorum ucu da idempotent DEĞİL — aynı yorum iki kez düşebilir.
            # Zararı bir kopya videodan küçük ama sınıf aynı, ve doğrulama
            # (GET /comments) ucuz.
            dogrula=lambda: _yorum_zaten_var_mi(object_id, access_token, message),
            proje=project_dir, anahtar="facebook_comment", platform="Facebook",
        )
        if isinstance(data, dict):
            print(f"  YouTube linki yorum olarak eklendi: {data.get('id')}")
        else:
            print("  YouTube linki yorumu doğrulandı (zaten vardı).")
        return True
    except (FacebookAPIError, ag.AgHatasi, ag.BelirsizSonuc,
            requests.exceptions.RequestException) as e:
        # maskele_istisna: bir ag hatasinin mesaji tam istek URL'sini
        # tasiyabiliyor; bu ciktinin gittigi yer auto_process'in konsolu,
        # yani sonunda bir log dosyasi.
        print(f"  UYARI: YouTube linki yorumu eklenemedi: {maskele_istisna(e)}")
        return False


def _finalize(project_dir: str, access_token: str, object_id: str, id_key: str,
              scheduled_at: datetime | None) -> None:
    """Yükleme sonrası ortak iş: state.json'a yaz + (mümkünse) YouTube yorumu.

    ZAMANLANMIŞ bir gönderiye YORUM EKLENEMEZ — gönderi henüz canlı değil,
    yorum ucu (`POST /{object_id}/comments`) onu bulamıyor. Bu durumda state'e
    `facebook_comment_pending: true` yazılıyor; gönderi canlıya çıktıktan sonra
    `post_pending_comment()` (auto_process'in bir sonraki koşusundan çağrılabilir)
    yorumu ekleyip bayrağı temizliyor.
    """
    updates = {
        id_key: object_id,
        "facebook_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if scheduled_at is not None:
        updates["facebook_scheduled_for"] = scheduled_at.isoformat()
        updates["facebook_comment_pending"] = True
        print(f"  Facebook: {scheduled_at.strftime('%Y-%m-%d %H:%M')} için zamanlandı "
              "(yorum, gönderi canlıya çıkınca eklenecek)")
    else:
        if not _post_youtube_comment(object_id, access_token, project_dir):
            # Yorum ya hiç denenmedi (henüz youtube_video_id yok — YouTube
            # yüklemesi Facebook'tan sonra çalışmış olabilir) ya da API
            # reddetti (Reels yayından hemen sonra birkaç saniye "işleniyor"
            # olabiliyor). İkisi de kalıcı hata değil, sonraki koşuda tekrar denensin.
            updates["facebook_comment_pending"] = True

    _save_state(project_dir, updates)


def upload_reels(project_dir: str, description: str | None = None, schedule: bool = True,
                 ek_dakika: int = 0) -> str:
    """output/shorts_9x16.mp4'ü Sayfa'ya Reels olarak yükler, video_id döner.

    Üç faz (resmî dokümanla doğrulandı):
      1. start  -> video_id + upload_url alınır
      2. binary -> upload_url'e ham dosya POST edilir (Authorization: OAuth ...)
      3. finish -> video_state=PUBLISHED (ya da SCHEDULED + scheduled_publish_time)

    AĞ HATASINDA YENİDEN DENEME — REELS AKIŞI BUNA ZATEN UYGUN (2026-09-12):
    üç fazın da `belirsiz_guvenli=True` ile yeniden denenebilmesinin gerekçesi
    akışın KENDİ tasarımında:
      * Faz 1 (start) gönderi ÜRETMİYOR, sadece bir oturum açıyor. Belirsiz
        kalıp yeniden denenirse en fazla bitirilmemiş bir oturum kalır —
        bitirilmeyen oturum ASLA Sayfa'ya çıkmaz.
      * Faz 2 (binary) RESMEN devam ettirilebilir: dokümanda `offset` alanı
        "the byte offset of the first byte being uploaded in this request.
        Generally should be set to 0, unless resuming an interrupted upload"
        diye tanımlı ve `GET /{video-id}?fields=status` ile `bytes_transfered`
        sorulabiliyor. Yeniden deneme AYNI `video_id`'ye yazar.
      * Faz 3 (finish) `video_id`yi PARAMETRE olarak alıyor — yani yeniden
        denemek İKİNCİ bir video OLUŞTURAMAZ, aynı nesneyi yayınlar.
    Yani bu üç fazda "gövde gönderildikten sonra koptu" durumu kopya riski
    TAŞIMIYOR. Uzun format (`upload_long`) İÇİN AYNISI GEÇERLİ DEĞİL — orada
    tek bir POST hem dosyayı hem yayını taşıyor, bkz. o fonksiyon.
    """
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    # KOPYA KAPISI: önceki koşuda belirsiz kaldıysa yeniden yükleme
    # (facebook_backfill bu projeyi hâlâ "Facebook'a hiç gitmemiş" görüyor).
    ag.kapi(project_dir, "facebook_reels_id", "Facebook")

    token = get_access_token()
    page_id = token["page_id"]
    access_token = token["page_access_token"]

    if description is None:
        description = build_caption(_load_meta(project_dir))

    # 1) Yukleme oturumu baslat (bitirilmeyen oturum Sayfa'ya CIKMAZ -> guvenli)
    start_resp = ag.guvenli_istek(
        lambda: requests.post(
            f"{GRAPH_API}/{page_id}/video_reels",
            data={"upload_phase": "start", "access_token": access_token},
            timeout=(10, 30),
        ),
        ne="Facebook Reels faz 1 (start)",
        belirsiz_guvenli=True,
        platform="Facebook",
    )
    start_data = _graph_json(start_resp, "Reels upload_phase=start")
    video_id = start_data["video_id"]
    upload_url = start_data["upload_url"]
    print(f"  Facebook Reels: oturum açıldı, video_id={video_id}")

    # 2) Ham binary'yi upload_url'e gonder. Dosya TEK PARÇADA gidiyor (offset=0,
    # file_size=tamami): shorts_9x16.mp4 bu boru hattinda ~45 sn / 3-5 MB, yani
    # parcali (resumable) yukleme karmasikligina girmeye deger bir boyut degil.
    # Yeniden deneme gerekirse ayni upload_url'e offset > 0 ile devam edilebilir.
    file_size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        binary = f.read()

    # Yeniden deneme AYNI video_id'ye yaziyor (offset=0'dan bastan) — resmi
    # dokuman bu fazi devam ettirilebilir tanimliyor, yani kopya riski YOK.
    upload_resp = ag.guvenli_istek(
        lambda: requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(file_size),
            },
            data=binary,
            timeout=(10, 600),
        ),
        ne="Facebook Reels faz 2 (binary)",
        belirsiz_guvenli=True,
        platform="Facebook",
    )
    upload_data = _graph_json(upload_resp, "Reels binary yükleme (faz 2)")
    if not upload_data.get("success"):
        raise FacebookAPIError(f"Reels binary yükleme başarısız (success alanı yok/False): {upload_data}")
    print(f"  Facebook Reels: {file_size} bayt yüklendi")

    # 3) Yayinla ya da zamanla
    scheduled_ts, scheduled_at = _compute_scheduled_time(schedule, ek_dakika)
    finish_params = {
        "upload_phase": "finish",
        "video_id": video_id,
        "description": description,
        "title": _load_meta(project_dir).get("title", ""),
        "access_token": access_token,
    }
    if scheduled_ts is None:
        finish_params["video_state"] = "PUBLISHED"
    else:
        finish_params["video_state"] = "SCHEDULED"
        finish_params["scheduled_publish_time"] = scheduled_ts

    # finish, video_id'yi PARAMETRE aliyor: yeniden deneme IKINCI bir video
    # olusturamaz, ayni nesneyi yayinlar -> belirsizlik kopya uretmiyor.
    finish_resp = ag.guvenli_istek(
        lambda: requests.post(
            f"{GRAPH_API}/{page_id}/video_reels",
            data=finish_params,
            timeout=(10, 60),
        ),
        ne="Facebook Reels faz 3 (finish)",
        belirsiz_guvenli=True,
        platform="Facebook",
    )
    finish_data = _graph_json(finish_resp, "Reels upload_phase=finish")
    if not finish_data.get("success"):
        raise FacebookAPIError(f"Reels finish başarısız (success alanı yok/False): {finish_data}")

    print(f"  tamam: facebook reels video_id={video_id}")
    _finalize(project_dir, access_token, video_id, "facebook_reels_id", scheduled_at)
    return video_id


def upload_long(project_dir: str, description: str | None = None, schedule: bool = True) -> str:
    """output/youtube_16x9.mp4'ü Sayfa'ya klasik (uzun format) video olarak
    yükler, video id'sini döner.

    Reels'in aksine TEK istekte gidiyor: multipart/form-data içinde `source`
    alanı dosyanın kendisi. Zamanlama burada `video_state` ile değil,
    `published=false` + `scheduled_publish_time` ikilisiyle yapılıyor (resmî
    /{page-id}/videos referansıyla doğrulandı) — Reels'in enum'u ile
    KARIŞTIRMA, iki uç iki farklı sözleşme kullanıyor.

    AĞ HATASINDA — REELS'TEN FARKLI (2026-09-12): burada faz yok, TEK bir POST
    hem dosyayı hem yayın kararını taşıyor ve önceden sabitlenmiş bir
    `video_id` YOK. Yani gövde gittikten sonra kopan bir bağlantıda körü
    körüne yeniden denemek Sayfa'ya İKİNCİ bir video koyar. Bu yüzden tek
    yeniden deneme biçimi DOĞRULAYARAK yeniden deneme (`_uzun_video_bul`),
    ve zamanlanmış yüklemede doğrulama "bilmiyorum" dediği için yeniden
    deneme HİÇ yapılmaz — state'e belirsiz işareti bırakılır.
    """
    video_path = os.path.join(project_dir, "output", "youtube_16x9.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    ag.kapi(project_dir, "facebook_video_id", "Facebook")

    token = get_access_token()
    page_id = token["page_id"]
    access_token = token["page_access_token"]

    meta = _load_meta(project_dir)
    if description is None:
        description = build_caption(meta)

    scheduled_ts, scheduled_at = _compute_scheduled_time(schedule)
    data = {
        "title": meta.get("title", ""),
        "description": description,
        "access_token": access_token,
    }
    if scheduled_ts is None:
        data["published"] = "true"
    else:
        # published=false + scheduled_publish_time: Facebook gonderiyi o ana
        # kadar yayinlanmamis tutup kendisi canliya aliyor.
        data["published"] = "false"
        data["scheduled_publish_time"] = scheduled_ts

    # Kapak: uzun formatta `thumb` alani RESMEN destekleniyor (ham gorsel verisi).
    # YouTube'da tespit edilen ayni sorun burada da gecerli — kapak verilmezse
    # Facebook rastgele/basliksiz bir kare seciyor. 16:9 video oldugu icin
    # cover.png (yatay) tercih ediliyor.
    cover_path = _find_cover(project_dir, vertical=False)

    # Dosya tutamaklari HER denemede YENIDEN aciliyor. NEDEN: multipart govde
    # tutamaklari SONUNA KADAR tuketiyor; ayni tutamakla ikinci bir deneme
    # 0 baytlik bir video gonderirdi (telegram_upload'daki seek(0) notunun
    # ayni tuzagi, burada seek yetmiyor cunku iki ayri dosya var).
    acik = {}

    def _kapat():
        for _, handle, _ in acik.values():
            try:
                handle.close()
            except Exception:
                pass
        acik.clear()

    def _hazirla():
        _kapat()
        acik["source"] = (os.path.basename(video_path),
                          open(video_path, "rb"), "video/mp4")
        if cover_path:
            acik["thumb"] = (os.path.basename(cover_path),
                             open(cover_path, "rb"), "image/jpeg")

    def _gonder() -> str:
        resp = requests.post(
            f"{GRAPH_VIDEO_API}/{page_id}/videos",
            data=data,
            files=acik,
            timeout=(10, 900),
        )
        sonuc = _graph_json(resp, "Uzun format video yükleme (/videos)")
        vid = sonuc.get("id")
        if not vid:
            raise FacebookAPIError(f"Uzun format yüklemesi id döndürmedi: {sonuc}")
        return vid

    try:
        video_id = ag.guvenli_istek(
            _gonder,
            ne="Facebook uzun format (/videos)",
            hazirla=_hazirla,
            # `kesin`: yalnizca HEMEN yayinlanan videoda "listede yok" cevabi
            # guvenilir. Zamanlanmis (published=false) videonun bu listede
            # gorunecegi resmi dokumanda garanti degil — o durumda doğrulama
            # BILINMIYOR doner ve yeniden deneme YAPILMAZ.
            dogrula=lambda: _uzun_video_bul(
                page_id, access_token, data.get("title") or "",
                description, kesin=(scheduled_ts is None)),
            proje=project_dir, anahtar="facebook_video_id", platform="Facebook",
        )
    finally:
        _kapat()

    print(f"  tamam: facebook video_id={video_id}")
    _finalize(project_dir, access_token, video_id, "facebook_video_id", scheduled_at)
    return video_id


def post_pending_comment(project_dir: str) -> bool:
    """Zamanlanmış (ya da yorumu o an eklenemeyen) bir gönderi için bekleyen
    YouTube linki yorumunu ekler. Eklendiyse True döner.

    NEDEN AYRI BİR FONKSİYON: zamanlanmış gönderi henüz canlı olmadığı için
    yorum ucu onu bulamıyor — yorum, gönderi yayına girdikten SONRA
    eklenebiliyor. auto_process.py'nin bir sonraki koşusundan çağrılabilir
    (instagram'ın `try_publish_pending()`'iyle aynı "sonraki koşuda tamamla"
    deseni — ama burada YAYINI değil, sadece YORUMU tamamlıyor: yayını
    Facebook kendisi yapıyor, bkz. modül docstring'i, 2. fark).
    """
    state = _load_state(project_dir)
    if not state.get("facebook_comment_pending"):
        return False
    if not state.get("youtube_video_id"):
        return False  # Yorumun icerigi henuz yok, sonraki kosuda tekrar bakilir.

    scheduled_for = state.get("facebook_scheduled_for")
    if scheduled_for:
        try:
            target = datetime.fromisoformat(scheduled_for)
            now = datetime.now(target.tzinfo) if target.tzinfo else datetime.now()
            if now < target:
                return False  # Gonderi daha canliya cikmadi, bosuna API'ye dokunma.
        except ValueError:
            pass  # Bozuk kayit yuzunden yorum hic eklenmesin istemiyoruz, dene.

    token = get_access_token()
    access_token = token["page_access_token"]

    object_ids = [state[k] for k in ("facebook_reels_id", "facebook_video_id") if state.get(k)]
    if not object_ids:
        return False

    hepsi_tamam = True
    for object_id in object_ids:
        if not _post_youtube_comment(object_id, access_token, project_dir):
            hepsi_tamam = False

    if hepsi_tamam:
        _save_state(project_dir, {"facebook_comment_pending": False})
    return hepsi_tamam


# Veri erisimi uyarisi kac gun kala verilsin. 14 gun, yeniden yetkilendirme
# icin rahat bir pencere: Meta panosunda izin duzenlemek + auth turu atmak
# yarim saatlik is, ama tatile/yogunluga denk gelebilir.
VERI_ERISIMI_UYARI_GUN = 14

# Debug_token'a ne siklikta sorulsun. Gunde bir yeterli - bu tarih 90 gunluk
# bir sayac, saatlik kosuda her seferinde API'ye dokunmak anlamsiz.
VERI_ERISIMI_TAZELEME_SN = 23 * 60 * 60

VERI_ERISIMI_CACHE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "facebook_veri_erisimi.json")


def veri_erisimi_durumu(force: bool = False) -> dict:
    """Sayfa token'inin VERI ERISIMI son kullanma tarihini dondurur.

    Token'in kendisi suresiz (long-lived kullanici token'indan turedigi icin,
    bkz. facebook_auth.py) - ama Meta'nin ayri bir 90 gunluk `data access`
    sayaci var. O dolunca token hala "gecerli" gorunur, sadece istekler
    yetkisiz donmeye baslar. Yani sessiz bir arizadir: gonderiler bir gun
    aniden gitmemeye baslar ve sebebi anlasilmaz. Bu yuzden onceden uyariyoruz.

    Sonuc onbellege yaziliyor (VERI_ERISIMI_TAZELEME_SN); pano da API'ye hic
    dokunmadan ayni dosyayi okuyor.
    """
    simdi = time.time()
    onbellek = {}
    try:
        with open(VERI_ERISIMI_CACHE, "r", encoding="utf-8") as f:
            onbellek = json.load(f)
    except (OSError, ValueError):
        pass

    if not force and onbellek.get("bakildi_ts"):
        if simdi - float(onbellek["bakildi_ts"]) < VERI_ERISIMI_TAZELEME_SN:
            return onbellek

    try:
        from facebook_auth import CLIENT_SECRETS_PATH
        with open(CLIENT_SECRETS_PATH, "r", encoding="utf-8") as f:
            gizli = json.load(f)
        token = get_access_token()
        uygulama_tokeni = "%s|%s" % (gizli["app_id"], gizli["app_secret"])
        r = requests.get(
            "%s/debug_token" % GRAPH_API,
            params={"input_token": token["page_access_token"],
                    "access_token": uygulama_tokeni},
            timeout=(10, 30),
        )
        veri = r.json().get("data") or {}
        if veri.get("error"):
            raise RuntimeError(veri["error"].get("message", "bilinmeyen"))
        bitis = veri.get("data_access_expires_at") or 0
        sonuc = {
            "bakildi_ts": simdi,
            "gecerli": bool(veri.get("is_valid")),
            "veri_erisimi_bitis": int(bitis) if bitis else 0,
            "izinler": sorted(veri.get("scopes") or []),
            "hata": "",
        }
    except Exception as e:
        # Onbellekteki son BASARILI olcumu koru: gecici bir ag hatasi
        # yuzunden panoda "bilinmiyor" yazmasi, gercek bir tarihi
        # gostermekten daha kotu.
        sonuc = dict(onbellek)
        sonuc["bakildi_ts"] = simdi
        # GUVENLIK: burada istisnanin METNI DEGIL, TIPI yaziliyor.
        # NEDEN: yukaridaki istek TEK ag cagrisi ki token'lari SORGU
        # DIZESINDE tasiyor (`params={"input_token": ..., "access_token":
        # ...}`). Bir ConnectionError/ReadTimeout'un mesaji tam istek
        # URL'sini icerdigi icin `str(e)` sayfa erisim token'ini duz metin
        # olarak `upload/facebook_veri_erisimi.json` dosyasina yazardi —
        # bu dosya bir log bile degil, kalici bir onbellek. Tip adi
        # ("ConnectionError"/"FacebookAPIError") teshis icin yeterli,
        # ayrinti zaten konsola/loga maskelenmis olarak dusuyor.
        sonuc["hata"] = type(e).__name__

    bitis = sonuc.get("veri_erisimi_bitis") or 0
    sonuc["kalan_gun"] = int((bitis - simdi) // 86400) if bitis else None
    sonuc["uyari"] = (sonuc["kalan_gun"] is not None
                      and sonuc["kalan_gun"] <= VERI_ERISIMI_UYARI_GUN)
    try:
        with open(VERI_ERISIMI_CACHE, "w", encoding="utf-8") as f:
            json.dump(sonuc, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return sonuc


def bekleyen_yorumlari_tamamla(kokler=None, limit: int = 5) -> dict:
    """`facebook_comment_pending` isaretli TUM projeleri tarar, yorumu ekler.

    NEDEN SUPURGE GEREKIYOR: post_pending_comment() tek bir projeye bakiyor,
    ama bayragi tasiyan proje genellikle o kosuda ISLENEN proje DEGIL -
    zamanlanmis bir gonderi saatler sonra canliya cikiyor ve o sirada
    otomasyon bambaska bir sarkiyi isliyor. Tek-proje cagrisi bu yuzden
    hicbir zaman dogru ana denk gelmezdi; bayrak taranmadan birikiyordu.
    (Ayni gerekcelerle facebook_backfill de ayri bir supurge.)

    `limit` bir kosuda en fazla kac yorum atilacagini sinirliyor: Facebook
    yorum ucunda toplu istek spam olarak gorulebiliyor ve bu is acil degil,
    bir sonraki saatlik kosuda kalanlar tamamlanir.

    KOK LISTESI (2026-09-11 duzeltmesi): varsayilan ELLE sayilmis
    ("projects", "dj_sets") idi. IKI ayri sessiz ariza vardi ve ikisi de
    CLAUDE.md'deki "yanlis kumeye bakan dogru kod" sinifindandi:
      1. `derlemeler/` YOKTU. `dj_famous_process.py` `--base derlemeler` ile de
         calisiyor ve tek cagiran (`auto_process._facebook_yorumlari()`) bu
         fonksiyonu ARGUMANSIZ cagiriyor — yani zamanlanmis bir derlemenin
         YouTube linkini tasiyan Facebook yorumu hicbir zaman tamamlanamazdi.
      2. Yollar GORELIYDI. Yanlis cwd'de `os.path.isdir` False doner, fonksiyon
         `bakilan=0` ile sessizce doner ve "yapilacak is yoktu" gibi gorunur
         (uyumluluk.KOKLER'de ayni gun duzeltilen tuzagin aynisi).
    Artik tek kanonik kaynak: `uyumluluk.KOKLER` (mutlak, uc kok).

    Hicbir hata otomasyonu durdurmaz.
    """
    import os

    sonuc = {"bakilan": 0, "tamamlanan": 0, "kalan": 0, "hatalar": []}
    bekleyenler = []
    for proje in proje_klasorleri(kokler):
        if not os.path.isfile(os.path.join(proje, "state.json")):
            continue
        if _load_state(proje).get("facebook_comment_pending"):
            bekleyenler.append(proje)

    sonuc["bakilan"] = len(bekleyenler)
    for proje in bekleyenler[:limit]:
        try:
            if post_pending_comment(proje):
                sonuc["tamamlanan"] += 1
        except Exception as e:
            sonuc["hatalar"].append("%s: %s" % (os.path.basename(proje), e))

    # Kalan SONRADAN yeniden sayiliyor: post_pending_comment basarili olunca
    # bayragi temizliyor, dolayisiyla bastaki listeden dusmek yaniltici olurdu
    # (zaman penceresi yuzunden atlanmis olanlar da "kalan"a dahil).
    kalan = 0
    for proje in bekleyenler:
        if _load_state(proje).get("facebook_comment_pending"):
            kalan += 1
    sonuc["kalan"] = kalan
    return sonuc


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi Facebook Sayfası'na yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument(
        "--kind", default="reels", choices=["reels", "uzun", "her-ikisi"],
        help="reels: shorts_9x16.mp4 (varsayılan) | uzun: youtube_16x9.mp4 | her-ikisi: ikisi de",
    )
    parser.add_argument(
        "--no-schedule", action="store_true",
        help="Golden-hour zamanlamasını kapat, hemen yayınla (youtube_upload.py ile aynı bayrak).",
    )
    args = parser.parse_args()

    schedule = not args.no_schedule
    if args.kind in ("reels", "her-ikisi"):
        upload_reels(args.project, schedule=schedule)
    if args.kind in ("uzun", "her-ikisi"):
        upload_long(args.project, schedule=schedule)


if __name__ == "__main__":
    main()
