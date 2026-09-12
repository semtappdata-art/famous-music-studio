"""YouTube'un otomatik (ASR) altyazısını gerçek sözlerle (`<slug>_sozler.md`)
hizalayıp, doğru METİN + doğru ZAMANLAMA içeren bir "Manuel altyazılar"
parçası olarak videoya yükler.

NEDEN GEREKLİ: YouTube'un kendi ASR altyazısı zamanlama açısından güvenilir
ama METNİ kendi ses-tanımasına göre yazıyor — sık sık yanlış kelime/eksik
noktalama üretiyor (bkz. 2026-09-06'da Gece Sürüşü/Sessiz Mektup/Kumdan
Denize/Beni Bırakma için elle yapılan inceleme ve düzeltme). Bu modül o elle
yapılan işi, SADECE gerçek sözleri elimizde olan projeler için otomatikleştiriyor
— `caption_align.align()` ASR'nin zamanlamasını gerçek kelimelerle eşleştiriyor.

NEDEN SADECE SÖZLER DOSYASI VARSA ÇALIŞIYOR: sözler yoksa elimizde ASR'nin
kendi (hatalı olabilecek) metninden başka bir şey yok — bunu "düzeltilmiş"
gibi otomatik yayınlamak, gerçekte hatalı kelimeleri de olduğu gibi
yayınlamak demek olurdu (Beni Bırakma'nın elle incelemesinde bulunan iki
belirsiz bölüm gibi — insan gözden geçirmesi gerektirdi, bkz. o projenin
state.json'ında captions_done hiç set edilmedi). Sözler dosyası yoksa
atlanır — YouTube'un kendi ASR/otomatik-çeviri altyazısı varsayılan kaynak
olarak kalmaya devam eder. ATLAMA ARTIK SESSİZ DEĞİL: sebebi
`auto_process.log`'a bir satır olarak düşüyor (bkz. LOG_PATH'in yanındaki not).

DOSYA EŞLEŞMESİ İKİ KEZ DOĞRULANIYOR: `stock_art.find_lyrics_file()` bulanık
(ön-ek + difflib) eşleşiyor; orada yanlış eşleşmenin bedeli alakasız bir
Pexels arama terimi, BURADA başka bir şarkının sözlerini videoya yazmak.
Bu yüzden (a) slug benzerliği SLUG_BENZERLIK_ESIGI ile burada tekrar
süzülüyor, (b) hizalamanın kendisi de ASR ile sözler arasındaki kelime
eşleşme oranına bakıp uyuşmazsa `caption_align.LyricsMismatch` atıyor.

NEDEN "PENDING" (tekrar deneme) GEREKİYOR: YouTube'un ASR'si yükleme
sonrası HEMEN hazır olmuyor (işleme süresi dakikalar-saatler arası değişken).
auto_process.py bu yüzden `youtube_captions_done` state.json'da set olana
kadar HER koşuda tekrar dener (Instagram'ın golden-hour konteyner kuyruğuyla
AYNI desen, bkz. auto_process.py::_drain_golden_hour_queue) — ASR track'i
henüz yoksa sessizce bir sonraki koşuya bırakılır, hiçbir hata otomasyonu
durdurmaz.

MEVCUT (manuel) BİR ALTYAZI PARÇASI VARSA: insert() değil update() kullanılır
— bu, 2026-09-06'da elle (YouTube Studio üzerinden) düzeltilmiş 4 şarkının
(Gece Sürüşü, Sessiz Mektup, Kumdan Denize, kısmen Beni Bırakma) üzerine
otomasyon tekrar çalıştığında DUPLICATE bir "Manuel altyazılar (2)" parçası
oluşturmak yerine, aynı parçayı (idempotent, zararsız) yeniden yazmasını
sağlıyor.
"""

import difflib
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from googleapiclient.http import MediaFileUpload

import caption_align
import ffmpeg_utils
import state_io
import stock_art
from gizli_maskele import maskele
from social_text import resolve_language
from youtube_auth import get_authenticated_service

VIDEO_FILENAME = "youtube_16x9.mp4"

# SESSİZ ATLAMA YOK: bu modülün her "skipped" dalı eskiden hiçbir iz
# bırakmadan dönüyordu — `auto_process.py` yalnızca "done"/"pending" için log
# basıyor. Bir altyazı hattının çalışmadığını fark etmenin TEK yolu videoyu
# açıp bakmaktı (bkz. CLAUDE.md, "sessizce False dönen bir koruma, OLMAYAN
# korumadan KÖTÜDÜR"). Aynı dosyaya (`auto_process.log`) yazıyoruz ki
# sebep, o koşunun diğer satırlarıyla yan yana okunabilsin; maskeleyici
# `auto_process.log()` ile aynı desende, yazmadan ÖNCE.
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_process.log")

# Sözler dosyası adı ile şarkı başlığının slug'ı arasında istenen en düşük
# benzerlik. `stock_art.find_lyrics_file()` ÖN-EK eşleşmesi de yapıyor ve orada
# bu doğru: yanlış eşleşmenin bedeli alakasız bir Pexels arama terimi. BURADA
# bedeli BAŞKA BİR ŞARKININ SÖZLERİNİ videoya yazmak. Ölçüldü: mevcut 18
# başlığın 17'si birebir, "Beton Krallığı" -> `beton_krallik` 0,889 ile geçiyor
# (ünsüz yumuşaması); ama ön-ek kuralının uzunluk koruması YOKTU (2026-09-11'de eklendi) — "Neon" ->
# `neon_kalp`, "Yeraltı Kralı" -> `yeralti`, "Bu Gece" -> `bu_gece_kazandik`
# hepsi sessizce eşleşiyordu (0,53-0,62 benzerlikte). Altyazı için bu kadarı
# yetmez, doğrulama burada tekrar yapılıyor.
SLUG_BENZERLIK_ESIGI = 0.85

# Uyuşmazlık (yanlış sözler dosyası) tespit edildikten sonra tekrar denemeden
# önce beklenen süre. NEDEN: `auto_process` `youtube_captions_done` set olana
# kadar HER koşuda tekrar deniyor; uyuşmazlık insan müdahalesi gerektiren
# kalıcı bir durum olduğu için her saat 250 birim kota (captions.list 50 +
# captions.download 200) yakardı — günlük 10.000'lik bütçenin yarısından
# fazlası tek bir bozuk projeye giderdi.
UYUSMAZLIK_BEKLEME_SN = 24 * 3600


def _log(mesaj: str) -> None:
    """`auto_process.log`'a tek satır. Maskeleme YAZMADAN ÖNCE (auto_process.log
    ile aynı desen); log'a yazamamak otomasyonu ASLA durdurmamalı."""
    satir = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), maskele(mesaj))
    print(satir)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError:
        pass


def _sozler_dosyasi(title: str):
    """Başlığa GERÇEKTEN ait olduğu doğrulanmış sözler dosyası (yoksa None).

    `stock_art.find_lyrics_file()` bulanık eşleşiyor (ön-ek + difflib 0,85);
    burada sonucu ikinci kez süzüyoruz — bkz. SLUG_BENZERLIK_ESIGI'nin yanındaki
    not. Reddedilen eşleşme SESSİZ DEĞİL: tam olarak bu satır, "bir şarkının
    altyazısına başka şarkının sözleri yazıldı"yı fark etmenin tek yolu."""
    if not title:
        return None
    path = stock_art.find_lyrics_file(title)
    if not path:
        return None
    slug = stock_art._slugify(title)
    stem = os.path.basename(path)[: -len("_sozler.md")]
    if stem == slug:
        return path
    oran = difflib.SequenceMatcher(None, slug, stem).ratio()
    if oran >= SLUG_BENZERLIK_ESIGI:
        return path
    _log("  YouTube altyazı atlandı: '%s' (slug '%s') için bulunan '%s' yeterince "
         "benzemiyor (%.3f < %.2f) — yanlış şarkının sözleri yazılmasın diye "
         "reddedildi." % (title, slug, stem, oran, SLUG_BENZERLIK_ESIGI))
    return None


def _damga_saniye(damga: str) -> float:
    """"2026-09-10T19:12:16" -> epoch saniye; bozuksa 0.0 (yani bekleme yok)."""
    try:
        return time.mktime(time.strptime(damga, "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: str) -> dict:
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _update_state(project_dir: str, fields: dict) -> None:
    state_path = os.path.join(project_dir, "state.json")
    state = _load_json(state_path)
    state.update(fields)
    # ATOMIK yazim (state_io) — eskiden ham `open(state_path, "w")` idi.
    # `open` dosyayi ONCE SIFIRLIYOR; `json.dump` bitmeden surec olurse
    # (Gorev Zamanlayici timeout'u, guc kesintisi) diskte YARIM bir JSON
    # kaliyor. Bedeli bugun buyudu: `uyumluluk._durum()` bozuk state.json'i
    # artik sessizce `{}` saymiyor, `DurumBozuk` -> HATA uretip o projeyi
    # TAMAMEN yayin disi birakiyor. `_atomik_yaz` .tmp + fsync + os.replace
    # ile ya tam eski ya tam yeni hali birakiyor. (youtube_upload.py:435 ile
    # AYNI desen — state.json'i elle yazan yeni kod ekleme.)
    state_io._atomik_yaz(state_path, state)


def _find_caption_tracks(youtube, video_id: str):
    """(asr_track_id, manual_track_id) döner — ikisi de yoksa None. Birden
    fazla manuel parça olması beklenmiyor (bu modül idempotent, üzerine
    yazar) ama varsa ilkini alır."""
    resp = youtube.captions().list(part="snippet", videoId=video_id).execute()
    asr_id = None
    manual_id = None
    for item in resp.get("items", []):
        if (item["snippet"].get("trackKind") or "").lower() == "asr":
            asr_id = item["id"]
        elif manual_id is None:
            manual_id = item["id"]
    return asr_id, manual_id


def sync_captions(project_dir: str) -> str:
    """Döner: "done" (bu koşuda yayınlandı/güncellendi), "already" (daha
    önce yapılmıştı), "skipped" (sözler dosyası/video/render çıktısı yok ya da
    önceki koşudaki uyuşmazlığın soğuma penceresi sürüyor — kalıcı, bu proje
    için bir daha denenmeyecek bir durum DEĞİL, sadece bu koşuda uygulanabilir
    değil), "pending" (video var
    ama YouTube'un ASR'si henüz hazır değil — sonraki koşuda tekrar denenecek).

    "skipped"in HER dalı `auto_process.log`'a sebebini yazar (tek istisna:
    video henüz YouTube'a çıkmamış — o normal ve gürültü olurdu). Dönüş
    sözleşmesi bilerek değişmedi: `auto_process._check_youtube_captions`
    "done"/"pending" dışındaki her şeyi "API'ye dokunulmadı" sayıyor — bu
    yüzden API'ye DOKUNDUKTAN sonra bulunan uyuşmazlık "skipped" DÖNMÜYOR,
    `caption_align.LyricsMismatch` atıyor (aşağıdaki nota bkz.)."""
    ad = os.path.basename(os.path.normpath(project_dir))
    state = _load_json(os.path.join(project_dir, "state.json"))
    if state.get("youtube_captions_done"):
        return "already"

    video_id = state.get("youtube_video_id")
    if not video_id:
        return "skipped"          # henüz YouTube'a çıkmamış — normal, sessiz.

    # Uyuşmazlık soğuma penceresi: bir kere "yanlış sözler" denmişse her saat
    # 250 birim kota yakmadan, günde bir kez tekrar bakılır.
    uyusmazlik = state.get("youtube_captions_uyusmazlik_at")
    if uyusmazlik and (time.time() - _damga_saniye(uyusmazlik)) < UYUSMAZLIK_BEKLEME_SN:
        _log("  YouTube altyazı atlandı (%s): önceki koşuda sözler uyuşmadı, "
             "24 saat soğuma penceresinde." % ad)
        return "skipped"

    meta = _load_json(os.path.join(project_dir, "meta.json"))
    baslik = meta.get("title", "")
    lyrics_path = _sozler_dosyasi(baslik)
    if not lyrics_path:
        _log("  YouTube altyazı atlandı (%s): '%s' için doğrulanmış bir "
             "*_sozler.md yok — ASR metni 'düzeltilmiş' gibi yayınlanmaz."
             % (ad, baslik))
        return "skipped"

    video_path = os.path.join(project_dir, "output", VIDEO_FILENAME)
    if not os.path.isfile(video_path):
        _log("  YouTube altyazı atlandı (%s): render çıktısı yok (%s) — "
             "süre ölçülemiyor." % (ad, VIDEO_FILENAME))
        return "skipped"

    youtube = get_authenticated_service()
    asr_track_id, manual_track_id = _find_caption_tracks(youtube, video_id)
    if not asr_track_id:
        return "pending"

    asr_bytes = youtube.captions().download(id=asr_track_id, tfmt="srt").execute()
    duration = ffmpeg_utils.get_audio_duration(video_path)

    tmp_dir = tempfile.mkdtemp(prefix="yt_captions_")
    asr_path = os.path.join(tmp_dir, "asr.srt")
    out_path = os.path.join(tmp_dir, "aligned.srt")
    media = None
    try:
        with open(asr_path, "wb") as f:
            f.write(asr_bytes)

        try:
            cues = caption_align.align(asr_path, lyrics_path, duration)
        except caption_align.LyricsMismatch as e:
            # SESSİZ YANLIŞ YAYININ durdurulduğu yer. İki şey yapılıyor:
            # (1) damga state'e yazılıyor ki bir sonraki koşu aynı 250 birimi
            #     (captions.list 50 + captions.download 200) tekrar yakmasın —
            #     yukarıdaki soğuma penceresi;
            # (2) istisna YENİDEN ATILIYOR, "skipped" DÖNÜLMÜYOR. Sebep yine
            #     kota: `auto_process._check_youtube_captions()` "done"/"pending"
            #     ve İSTİSNA hâllerinde True dönüyor, `_drain_golden_hour_queue`
            #     o True'yu görünce koşunun geri kalanında başka hiçbir projede
            #     altyazı denemiyor. "skipped" dönseydi bu koşuda GERÇEKTEN
            #     harcanmış istekler sayılmaz, döngü sıradaki projeye geçer ve
            #     kota katlanırdı (2026-09-06'da kotayı tüketen arızanın aynısı).
            # `from None`: istisna zinciri log/traceback'e ikinci kez basılmasın.
            _update_state(project_dir, {
                "youtube_captions_uyusmazlik_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "youtube_captions_uyusmazlik_dosya": os.path.basename(lyrics_path),
            })
            raise caption_align.LyricsMismatch("%s: %s" % (ad, e)) from None
        if not cues:
            _log("  YouTube altyazı atlandı (%s): hizalama hiç cue üretmedi "
                 "(sözler dosyasının 'Temiz Sözler' bölümü boş olabilir)." % ad)
            return "skipped"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(caption_align.format_srt(cues))

        media = MediaFileUpload(out_path, mimetype="application/octet-stream")
        # MediaFileUpload dosyayı AÇAR ve HİÇ KAPATMAZ (googleapiclient'ta
        # close() yok) — Windows'ta açık bir dosya SİLİNEMEZ, bu yüzden
        # aşağıdaki `finally` her koşuda `aligned.srt`i silemeyip klasörü de
        # kaldıramıyordu. Kanıt: %TEMP%'te 19 adet `yt_captions_*` klasörü,
        # her birinde yayınlanmış `aligned.srt` (asr.srt'ler silinmiş, çünkü
        # onlar `with` ile kapatılıyor). Tanı bedava değildi: o dosyalar bu
        # denetimde altyazıların DOĞRU şarkıya gittiğini kanıtlamakta
        # kullanıldı — ama üretimde biriken çöp yine de çöptür.
        if manual_track_id:
            youtube.captions().update(
                part="snippet",
                body={"id": manual_track_id, "snippet": {"isDraft": False}},
                media_body=media,
            ).execute()
        else:
            youtube.captions().insert(
                part="snippet",
                sync=False,
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": resolve_language(meta),
                        "name": "",
                        "isDraft": False,
                    }
                },
                media_body=media,
            ).execute()

        _update_state(project_dir, {
            "youtube_captions_done": True,
            "youtube_captions_synced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        return "done"
    finally:
        # Dosya tanıtıcısını ÖNCE kapat (yukarıdaki nota bkz.), sonra tüm
        # geçici klasörü tek seferde kaldır — `os.remove` + `os.rmdir`
        # ikilisi yeni bir dosya eklendiğinde sessizce eksik kalıyordu.
        if media is not None:
            try:
                media.stream().close()
            except Exception:
                pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
