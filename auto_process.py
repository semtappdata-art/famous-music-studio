"""Bekleyen (audio.wav hazır) projeleri otomatik render edip YouTube/TikTok/
Instagram'a yükler — Windows Görev Zamanlayıcı ile periyodik çalıştırılmak
üzere tasarlandı.

Suno'da şarkı üretimi ve indirme hâlâ elle yapılmalı (bkz. suno_prompt_hazirlik.md)
— bu script "audio.wav bir proje klasörüne konduktan sonraki her şeyi"
(cover/art üretimi + render + YouTube + TikTok + Instagram) otomatikleştiriyor.
cover.jpg/png veya art.jpg/png elle hazırlanmışsa dokunulmaz; eksikse
generate_cover.py ile meta.json'daki title/theme'e göre otomatik üretilir.

Kullanım:
    python auto_process.py
    python auto_process.py --privacy unlisted
    python auto_process.py --base projects
    python auto_process.py --count 3

**Otomatik kademeleme (varsayılan, `--count` verilmezse):** kaç proje bekliyorsa
(henüz 3 platforma da tam yüklenmemiş) 24 saati o sayıya eşit aralıklara böler
(ör. 9 proje → ~2.7 saatte bir 1 tane, 2 proje → 12 saatte bir 1 tane) ve son
yüklemeden bu hesaplanan aralık kadar süre geçtiyse SADECE O ZAMAN bir proje
işler — aksi halde bu koşuda hiçbir şey yapmadan çıkar. Amaç: aynı anda birden
fazla şarkı paylaşmanın aynı takipçi kitlesinin aynı taramasında birbiriyle
yarışmasını önlemek, kaç dosya biriktiği önemli olmadan gün içine dengeli
yaymak. Bunun işlemesi için Görev Zamanlayıcı'yı SIK çalıştır (ör. saatte bir
tek bir tetikleyici) — script her çağrıldığında "sırası geldi mi" diye kendi
kendine karar verir. `--count N` verirsen bu otomatik kademe DEVRE DIŞI kalır,
tam N kadarı zamanlama beklemeden hemen işlenir.

Kendini iyileştiren mantık: proje için render sadece çıktı dosyaları eksikse
yapılır; her platforma yükleme sadece state.json'da o platforma ait alan
(youtube_video_id / tiktok_publish_id / instagram_media_id) yoksa denenir. Yani
bir platform bir çalıştırmada başarısız olursa, bir sonraki çalıştırmada sadece
o platform tekrar denenir — render veya diğer platformlar tekrarlanmaz.

Çıktı hem konsola hem auto_process.log dosyasına yazılır (Görev Zamanlayıcı
arka planda çalıştığında konsolu görmezsin, log dosyasından takip edersin).
"""

import argparse
import json
import os
import sys
import time

# Windows'ta konsol/log çıktısı varsayılan olarak yerel kod sayfasına (örn.
# cp1252/charmap) düşüyor — bu ne Türkçe karakterleri doğru basabiliyor (loglar
# "Ba�ka bir" gibi bozuk görünüyordu) ne de caption'lardaki emoji'yi (örn. 🎵)
# hiç temsil edemiyor, ikincisi UnicodeEncodeError ile print() çağrısını
# patlatıp upload'ı (henüz gerçek yükleme başlamadan) tamamen durduruyordu —
# bkz. tiktok_upload.py'deki caption print'i. UTF-8'e zorlamak ikisini de çözer.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import config
import generate_cover
import render as render_module
import latest_release
from log_rotate import trim_log
# Merkezi maskeleyici — log'a yazılan HER metin buradan geçiyor (bkz. log()).
# NEDEN import burada: çağrı noktalarına dağıtılmış bir maskeleme, yarın
# eklenecek yeni bir log satırının yine sızdırması demekti.
from gizli_maskele import maskele
from git_sync import auto_pull, push_path

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
RENDER_OUTPUTS = ["youtube_16x9.mp4", "shorts_9x16.mp4"]
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_process.log")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auto_process.lock")
# KİLİT BAYATLIK EŞİĞİ — 2 saatten 4 saate çıkarıldı.
# NEDEN DEĞİŞTİ: eskiden kilidin mtime'ı koşu boyunca HİÇ tazelenmiyordu, yani
# bu sabit "bir koşu en fazla ne kadar sürer" sorusuna cevap vermek zorundaydı —
# ve yanlış cevaplıyordu: bugün tek bir render 74 dakika sürdü, üstüne 266 MB'lık
# bir YouTube yüklemesi binince 2 saat rahatça aşılıyor. Aşıldığında bir sonraki
# saatlik tetik kilidi "bayat" sayıp AYNI projeyi paralel yüklemeye başlıyordu —
# kilidin var olma gerekçesinin tam tersi.
# NEDEN 4 SAAT (8 değil): artık log() her satırda kilidi tazeliyor (nabız), bu
# yüzden eşik "koşu ne kadar sürer"i değil "süreç GERÇEKTEN öldü mü"yü ölçüyor.
# Ölçülmesi gereken tek şey İKİ LOG SATIRI ARASINDAKİ en uzun sessizlik: burada
# bu, tek bir render (bugünkü en uzun ölçüm 74 dk) ya da tek bir platform
# yüklemesi — 4 saat bunun ~3 katı, rahat bir marj.
# NEDEN dj_famous_process'teki 8 saat DEĞİL: oradaki setler ~1 saatlik ses
# içeriyor (tek bir render doğal olarak çok daha uzun), ana katalog 3-5 dakikalık
# şarkılar. Ayrıca ölü bir koşunun kilidi burada 4 saat boyunca hattı tıkıyor ve
# watch_projects.py'nin nabız gözcüsü bunu YAKALAYAMIYOR: kilide takılan koşu
# yine de her saat bir log satırı yazıyor, yani auto_process.log'un mtime'ı taze
# görünüyor. Kurtarma tek başına bu eşiğe kaldığı için cömertlik pahalı.
LOCK_STALE_SECONDS = 4 * 60 * 60
DAILY_WINDOW_SECONDS = 24 * 60 * 60
# YENİ bir şarkı yayını için EN AZ bu kadar ara bırakılır.
# NEDEN: DAILY_WINDOW_SECONDS'ın penceresi 24 saat olduğu için, bir günde 7 dosya
# `projects/` altına düşerse yedisi de AYNI GÜN yayınlanıyordu
# (gap = 24/7 ≈ 3,4 saat). Haftalık sayı doğru çıkıyor ama günlük desen
# YouTube'un "inauthentic content" (toplu üretilmiş, tekrarlayıcı içerik)
# tarifinin ta kendisi — kanalın en büyük tekil riski bu.
# 52 SAAT NEREDEN GELİYOR: hedef haftada 3-4 şarkı; 3 şarkı/hafta = 7*24/3 = 56
# saat eder. Tam 56 yazılmıyor çünkü koşu saatlik ve golden-hour zamanlaması her
# turda yayını ~1 saat ileri kaydırıyor; 56'da yayın günü haftadan haftaya
# sürüklenirdi. 52 = 56 eksi bu sürüklenme payı.
MIN_YAYIN_ARALIGI_SN = 52 * 60 * 60
UPLOAD_TIMESTAMP_KEYS = (
    "youtube_uploaded_at", "youtube_shorts_uploaded_at",
    "tiktok_uploaded_at", "instagram_uploaded_at",
)


# Kilit BİZDE mi? Sadece kendi kilidimizin mtime'ını tazelemek için (bkz. log()).
# Kaybeden süreç de log() çağırıyor; bayrak olmasaydı RAKİBİN kilidini tazeler,
# gerçekten bayat bir kilidin hiç eskimemesine yol açardı. (dj_famous_process.py
# ile aynı desen — iki script'te iki farklı kilit tasarımı olmasın.)
_KILIT_BIZDE = False


def log(msg: str) -> None:
    # 1) MASKELEME — yazmadan ÖNCE. Bir ağ hatasının mesajı tam istek URL'sini
    #    (dolayısıyla sorgu dizesindeki access_token'ı) içerebiliyor;
    #    2026-09-04'te dj_famous_process.log'a gerçek bir Instagram token'ı
    #    böyle düştü. Bu dosyada ~20 yerde `log(f"... HATA: {e}")` var —
    #    maskelemeyi o 20 çağrıya tek tek dağıtmak, yarın eklenecek 21.
    #    çağrının yine sızdırması demekti; tek nokta, unutulamaz.
    #    (watch_projects.py ve log_rotate.py ile aynı desen.)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {maskele(msg)}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    # 2) KİLİT NABZI — yazmadan SONRA, her çağrıda. Kilidin mtime'ı koşu boyunca
    #    tazeleniyor, böylece uzun bir koşu kendi kilidini "bayat" gösterip bir
    #    sonraki saatlik tetiğin AYNI projeyi paralel yüklemesine yol açmıyor.
    #    NEDEN BURADA: tazelemeyi "her platform yüklemesinden sonra" gibi bir
    #    listeye bağlamak, yeni bir adım eklendiğinde güncellenmeyi unutulacak
    #    bir liste demekti. log() bu script'in TEK doğal darboğazı: her anlamlı
    #    adım zaten bir satır basıyor, yani nabız adım listesiyle kendiliğinden
    #    güncel kalıyor. Maliyeti bir utime çağrısı — log zaten dosya açıp
    #    yazıyor, ölçülebilir ek yük yok.
    #    SINIR: iki log satırı arasındaki tek bir uzun işlem (bir render, bir
    #    yükleme) yine tazelenmeden geçiyor; LOCK_STALE_SECONDS bu yüzden hâlâ
    #    o en uzun tek adımın birkaç katı tutuluyor.
    if _KILIT_BIZDE:
        try:
            os.utime(LOCK_PATH, None)
        except OSError:
            pass


def _acquire_lock() -> bool:
    """Kilidi ATOMİK olarak alır; alamazsa False döner.

    İki auto_process.py çalıştırması aynı anda çakışırsa (örn. çakışan Görev
    Zamanlayıcı tetikleyicileri, ya da elle + zamanlanmış çalıştırma çakışması)
    ikisi de AYNI en eski projeyi seçip aynı videoyu iki kez yükleyebilir.

    `O_CREAT | O_EXCL`: dosya zaten varsa işletim sistemi FileExistsError
    fırlatıyor, yani "önce bak, sonra yarat" arasındaki pencere KAPANIYOR.
    Eski sürüm `os.path.isfile()` ile bakıp ayrı bir `open(..., "w")` ile
    yaratıyordu — iki süreç aynı anda "kilit yok" görüp ikisi de devam
    edebilirdi. Pencere teorik değil: watch_projects.py bu script'i DAKİKADA
    BİR, Görev Zamanlayıcı ayrıca saatlik tetikliyor.

    Kilit dosyası LOCK_STALE_SECONDS'tan eskiyse (önceki çalıştırma çökmüş,
    kilidini bırakmamış olabilir) devralınıyor — ama devralma da ikinci bir
    O_EXCL ile korunuyor, yoksa bayat kilidi iki süreç birden devralabilirdi.
    """
    global _KILIT_BIZDE
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - os.path.getmtime(LOCK_PATH)
        except OSError:
            # Kilit tam aramızda kayboldu (sahibi bitirdi) — bu koşuda
            # uğraşmıyoruz, bir sonraki tetik alır. Yanlış sahiplenmektense
            # bir koşu kaçırmak ucuz.
            return False
        if age < LOCK_STALE_SECONDS:
            return False
        log(f"  Eski kilit dosyası bulundu ({age:.0f}s) — önceki çalıştırma muhtemelen "
            f"yarıda kalmış, yok sayılıp devam ediliyor.")
        try:
            os.remove(LOCK_PATH)
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            # Bayat kilidi başka bir süreç bizden önce devraldı (yarış) —
            # ikimiz birden devam edersek kilidin anlamı kalmaz.
            return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    _KILIT_BIZDE = True
    return True


def _release_lock() -> None:
    global _KILIT_BIZDE
    # Bayrak ÖNCE düşüyor: aradaki bir log() satırı silinmiş kilidi yeniden
    # yaratmasın diye (os.utime yaratmaz ama sıralama niyeti açık kalsın).
    _KILIT_BIZDE = False
    if os.path.isfile(LOCK_PATH):
        os.remove(LOCK_PATH)


def _has_any(project_dir: str, names: list) -> bool:
    return any(os.path.isfile(os.path.join(project_dir, n)) for n in names)


def _is_rendered(project_dir: str) -> bool:
    output_dir = os.path.join(project_dir, "output")
    return all(os.path.isfile(os.path.join(output_dir, n)) for n in RENDER_OUTPUTS)


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_ready_projects(base: str) -> list:
    """audio'su hazır olan tüm proje klasörlerini, klasörün oluşturulma zamanına
    göre (en eskiden en yeniye) sıralı döner (zaten tamamen işlenmiş olanlar
    dahil — process_project zaten-yapılmış adımları atlar, bu yüzden burada
    filtrelemeye gerek yok). cover/art artık aranmıyor — eksikse process_project
    render'dan önce otomatik üretir.

    NOT: Önceden burada `sorted(os.listdir(base))` (isim alfabetik sırası)
    kullanılıyordu ve docstring/main() "en eski bekleyen proje" işlendiğini
    iddia ediyordu — ama alfabetik sıra oluşturulma zamanıyla ilgisiz, adı
    alfabetik önde olan YENİ bir proje gerçekten daha uzun süredir bekleyen
    bir projenin önüne geçebiliyordu. os.path.getctime ile gerçek klasör
    oluşturulma zamanına göre sıralanıyor (isim, eşit zaman durumunda
    determinizm için ikincil anahtar)."""
    ready = []
    if not os.path.isdir(base):
        return ready
    for name in os.listdir(base):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if _has_any(project_dir, AUDIO_NAMES):
            ready.append(project_dir)
    ready.sort(key=lambda p: (os.path.getctime(p), p))
    return ready


def _is_fully_done(project_dir: str) -> bool:
    """Tüm platformlara (YouTube uzun format + Shorts, TikTok, Instagram) yüklenmişse
    True — bu proje için yapılacak bir şey kalmadı. Daha önce yüklenmiş ama
    youtube_shorts_video_id'si olmayan projeler (bu alan sonradan eklendi) bu
    kontrolden geçemez, yani bir sonraki çalıştırmada otomatik olarak Shorts
    yüklemesi de yapılır (retroaktif tamamlama).

    BİLEREK `youtube_captions_done`'ı SAYMIYOR: bu alan sadece bir
    `*_sozler.md` dosyası olan projelerde set olabiliyor (bkz.
    youtube_captions.py) — kataloğun çoğunluğunda böyle bir dosya yok, yani
    bunu buraya eklemek o projelerin `_auto_pace_count()`'un kademeleme
    aritmetiğinde SONSUZA KADAR "pending" kalmasına yol açardı.

    ────────────────────────────────────────────────────────────────────
    YENİ BİR PLATFORM EKLERKEN — BURAYA EKLEME. (2026-09-11'de bu tasarım
    bir kez daha gözden geçirildi ve BİLEREK KORUNDU; aşağısı o kararın
    gerekçesi, dördüncü kez aynı arızayı üretmemek için.)

    BU FONKSİYON "her şey bitti mi" sorusuna CEVAP VERMİYOR. Tek cevapladığı
    soru şu: **bu proje için PAHALI ANA HATTI (render + YouTube uzun/Shorts +
    TikTok + Instagram) tekrar çalıştırmalı mıyız?** Adı yanıltıcı, anlamı dar.
    Dördü de dolduğunda proje `pending`den düşer ve bir daha `process_project()`
    görmez — bu DOĞRU davranış, çünkü o dördü tekrar çalıştırılamaz/tekrar
    çalıştırılmamalı işler.

    NEDEN BURAYA PLATFORM EKLENMİYOR — iki ayrı gerekçe, ikisi de yeterli:

      1. BAYRAK/ÖN KOŞUL KAPALIYKEN LİSTE HİÇ BOŞALMAZ. Facebook/Telegram/
         Bluesky opt-in (`config.EK_PLATFORMLAR`); token yoksa, bayrak
         kapalıysa ya da dosya boyutu sınırı aşıyorsa o anahtar ASLA
         dolmayacak. O zaman TÜM katalog sonsuza kadar `pending` görünür ve
         `_auto_pace_count()`'un `DAILY_WINDOW_SECONDS / len(pending)`
         bölümü küçülmeyen bir paydaya bölünür: 18 proje → 1,3 saatlik
         "gerekli ara", yani günlük pencere freni pratikte YOK olur. Geriye
         tek fren olarak 52 saatlik taban kalır, ondan da geri doldurmalar
         MUAF — sonuç: yayın temposu sessizce bozulur. Aynı gerekçe
         `youtube_captions_done` için de geçerli (yukarıdaki paragraf).
      2. HER EK PLATFORMUN KENDİ ZAMANLAMA KISITI VAR ve bu tek bir bool'a
         sığmaz: Instagram konteyneri 24 saatte EXPIRED oluyor, TikTok
         yayını ELLE yapılıyor (API "yayınlandı mı" demiyor), Content ID
         karantinası 2 saat, Facebook/Telegram/Bluesky'da GÜNLÜK TAVAN +
         golden-hour kapısı var. Bunlar "bitti/bitmedi" değil, "şu an sırası
         geldi mi" soruları — `pending` listesi bu soruyu taşıyamaz.

    YANİ DÖRT SÜPÜRGE (`facebook_backfill`, `ek_platform_backfill`,
    `_drain_golden_hour_queue`, `dj_tarama_kontrol`) bu
    (Beşinci bir süpürge daha var — `dj_clips.supur` — ama o BU dosyadan
    DEĞİL, haftalık `dj_famous_process.main()`'den çağrılıyor; kesitlerin
    küresel temposu zaten 7 gün olduğu için saatlik koşuya bağlamanın
    kazancı yok. Burada "beş süpürge" yazmak 2026-09-11'de bir kez yapıldı
    ve YALANDI: `auto_process` `dj_clips`'i hiç import etmiyor. Yalan
    söyleyen yorum, hiç yorum olmamasından kötüdür.)

    tanımın ETRAFINDAN DOLAŞMA DEĞİL, (2)'nin doğrudan sonucudur: her birinin
    kendi tempo kapısı var ve hepsi `pending`den BAĞIMSIZ çalışmak ZORUNDA.
    Asıl hata hiçbir zaman "tanım dar" olması değildi; hata, yeni bir platform
    işinin `pending`e (yani `process_project()`'e) BAĞLANMASIYDI.

    KURAL — yeni bir platform/adım eklerken şu ikisinden BİRİNİ seç, üçüncü
    bir seçenek YOK:

      A) Ucuz, idempotent, dış kota/tavanı olmayan bir TAMAMLAMA işiyse →
         `_drain_golden_hour_queue()` içine koy. O fonksiyon `pending` değil
         **`ready`** (tüm katalog) ile çağrılıyor — `_is_fully_done()`'dan
         geçmiş projeleri de kapsayan TEK yer burası.
      B) Kendi hız sınırı / API kotası / günlük tavanı varsa → AYRI bir
         süpürge modülü yaz ve `main()`'in `finally` bloğundan çağır
         (desen: `upload/facebook_backfill.py`, iki kapı = golden-hour +
         günlük tavan). `finally`, "iş olsun olmasın her koşuda" çalışır.

    TEST: yeni adımın `pending`den bağımsız olduğunu gösteren bir test yaz
    (desen: `tests/test_playlist_shorts_sirasi.py`). "`process_project()`
    içinden çağrılıyor ve başka hiçbir yerden" = platform kataloğun büyük
    kısmı için KALICI OLARAK ÖLÜ demektir; 2026-09-11'de bu üç kez oldu
    (Telegram/Bluesky 14/18 şarkı, playlist 20/20 Shorts, Instagram
    konteyneri) ve hiçbiri log'a tek satır düşürmedi."""
    state = _load_state(project_dir)
    return all(
        key in state
        for key in (
            "youtube_video_id",
            "youtube_shorts_video_id",
            "tiktok_publish_id",
            "instagram_media_id",
        )
    )


def _last_upload_time(project_dirs: list) -> float | None:
    """Tüm projelerin state.json'larına bakıp en son yükleme zaman damgasını
    (hangi platform olursa olsun) bulur — otomatik zamanlamanın referans
    noktası: 'en son ne zaman bir şey paylaştık'. Hiç yükleme yoksa None."""
    latest = None
    for project_dir in project_dirs:
        state = _load_state(project_dir)
        for key in UPLOAD_TIMESTAMP_KEYS:
            ts = state.get(key)
            if not ts:
                continue
            try:
                t = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                continue
            if latest is None or t > latest:
                latest = t
    return latest


def _auto_pace_count(pending: list, ready: list, count: int = 1) -> int:
    """--count elle verilmediğinde kaç proje işleneceğini OTOMATİK belirler:
    bekleyen proje sayısına göre 24 saati eşit aralıklara böler (ör. 9 proje
    bekliyorsa ~2.7 saatte bir 1 tane, 2 proje bekliyorsa 12 saatte bir 1 tane)
    ve son yüklemeden bu hesaplanan aralık kadar süre geçtiyse 1, geçmediyse
    0 döner. Kaç dosya beklediği önemli değil — Görev Zamanlayıcı'nın kendisi
    sık çalıştığı sürece (ör. saatte bir) script kendi kendine "sırası geldi
    mi" diye karar verir, gün içine dengeli yayılır.

    Buna ek olarak YENİ yayınlar için MIN_YAYIN_ARALIGI_SN'lik bir TABAN var:
    24 saati bekleyen sayısına bölmek tek başına bir günde 7 yayına izin
    veriyordu (bkz. sabitin yanındaki not).

    `count` = bu koşuda EN FAZLA kaç proje serbest bırakılacağı (main()'deki
    `batch = pending[:count]` ile BİREBİR aynı dilim). Fonksiyon 0 ya da
    `count` döner; varsayılan 1 olduğu için bugünkü davranış değişmiyor."""
    if not pending:
        return 0
    # Taban SADECE sırada GERÇEKTEN yeni bir yayın varsa uygulanır.
    # NEDEN: pending listesinde YouTube'a çoktan çıkmış ama Instagram'ı (ya da
    # TikTok'u) eksik kalmış "geri doldurma" projeleri de var (2026-09-11'de
    # 3 tane). Onlar yeni bir yayın değil, yarım kalmış bir işin tamamlanması;
    # kanalın yükleme desenini etkilemezler. 52 saatlik tabana takılırlarsa
    # Instagram geri doldurması günlerce sürer.
    #
    # AYIRT ETME — ÖLÇÜT BATCH'İN TAMAMI, `pending[0]` DEĞİL (2026-09-11'de
    # düzeltildi). Eski hâli `"youtube_video_id" not in _load_state(pending[0])`
    # idi ve SADECE sıranın ilkine bakıyordu. Muafiyet "bu koşuda yeni bir şarkı
    # YAYINLANMIYOR" demek zorunda; `count > 1` olduğu anda ilk sıradaki bir
    # geri doldurma projesi, ARKASINDAKİ yeni şarkıya da muafiyet kazandırıyor
    # ve 52 saatlik taban SESSİZCE atlanıyordu — tam olarak bugünkü kuyrukta
    # (3 geri doldurma + sonra gelecek yeni şarkı) oluşacak dizilim. Dilim
    # main()'deki `batch = pending[:count]` ile aynı; batch'te TEK BİR yeni
    # yayın varsa taban uygulanır (any), sırası önemli değil.
    batch = pending[:count] or pending[:1]   # count<=0 gelirse bile en az bir projeye bak
    yeni_yayin = any("youtube_video_id" not in _load_state(p) for p in batch)
    taban = MIN_YAYIN_ARALIGI_SN if yeni_yayin else 0
    required_gap = max(taban, DAILY_WINDOW_SECONDS / len(pending))
    last = _last_upload_time(ready)
    if last is None:
        return count  # hiç yükleme yapılmamış, hemen başla
    elapsed = time.time() - last
    if elapsed >= required_gap:
        return count
    remaining_h = (required_gap - elapsed) / 3600
    # Beklemenin hangi kuraldan geldiğini logda ayırt et: sonraki oturum
    # "neden 2 gündür hiçbir şey çıkmıyor" diye sorduğunda cevap logda olsun.
    sebep = "yeni yayın tabanı" if yeni_yayin else "günlük pencere bölüşümü"
    log(f"  Otomatik zamanlama: {len(pending)} proje bekliyor, sıradaki için "
        f"~{remaining_h:.1f} saat daha var (henüz erken, bu koşuda atlanıyor; "
        f"kural: {sebep}, gerekli ara ~{required_gap / 3600:.1f} saat).")
    return 0


def _log_instagram_result(media_id: str | None) -> None:
    if media_id:
        log(f"  Instagram: tamam, media_id={media_id}")
    else:
        log("  Instagram: konteyner hazır, golden-hour penceresi bekleniyor")


def _check_instagram_pending(project_dir: str) -> None:
    """state.json'da bekleyen bir instagram_creation_id varsa (konteyner
    oluşturulmuş ama golden-hour beklemede) kontrol eder — hazırsa ve şu an
    golden-hour ise yayınlar.

    Zaten yayınlanmış (instagram_media_id dolu) bir projede de çağrılır:
    kararı try_publish_pending() veriyor, konteyner son yayından yeni değilse
    (ya da damgalar eksikse) kendisi çıkıyor — bkz. çağrı noktalarındaki not.

    LOG SATIRI SEBEP KODUNDAN TÜRÜYOR, "None"dan DEĞİL. Eskiden buradaki her
    None "konteyner hazır, golden-hour penceresi bekleniyor" diye loglanıyordu;
    o satır her koşuda 13 kez basılıyor ama gerçekte bekleyen TEK proje vardı —
    yayınlanmış projelerdeki bayat creation_id kayıtları yüzünden. "Ayırt
    etmenin ucuz yolu: temizlik yapıldıysa creation_id state'ten kalkmış olur"
    diye bir tahmin de denendi, ama o SADECE temizlenen dalı yakalıyordu;
    "zaten yayınlanmış, bekleyen yok" dalı yine yanlış satırı basıyordu.
    Artık sebebi try_publish_pending()'in KENDİSİ bildiriyor (sebep_out)."""
    try:
        from instagram_upload import (
            SEBEP_BAYAT_TEMIZLENDI,
            SEBEP_GOLDEN_HOUR,
            SEBEP_ISLENIYOR,
            SEBEP_SURESI_DOLDU,
            SEBEP_ZATEN_YAYINLANMIS,
        )
        from instagram_upload import try_publish_pending as ig_try_publish
        sebep: dict = {}
        media_id = ig_try_publish(project_dir, sebep_out=sebep)
        if media_id:
            _log_instagram_result(media_id)
            return
        kod = sebep.get("kod")
        if kod in (SEBEP_BAYAT_TEMIZLENDI, SEBEP_SURESI_DOLDU):
            ek = "24 saatlik ömrünü aşmış (bayat)" if kod == SEBEP_BAYAT_TEMIZLENDI \
                else "süresi dolmuş (EXPIRED)"
            log(f"  Instagram: bekleyen konteyner {ek}, kaydı temizlendi — "
                "yeniden paylaşım için elle çalıştır (bkz. konsol çıktısı)")
        elif kod == SEBEP_ZATEN_YAYINLANMIS:
            # Gönderi zaten yayında ve state'teki konteyner o yayından ESKİ:
            # bekleyen bir iş YOK. Burada "golden-hour bekleniyor" yazmak
            # tam da yukarıdaki yanlış okumanın kaynağıydı.
            log("  Instagram: zaten yayınlanmış, bekleyen konteyner yok")
        elif kod == SEBEP_ISLENIYOR:
            log("  Instagram: konteyner hâlâ işleniyor, bir sonraki kontrolde tekrar denenecek")
        elif kod == SEBEP_GOLDEN_HOUR:
            # SADECE burada — gerçekten hazır, gerçekten bekleyen konteyner.
            _log_instagram_result(None)
        # SEBEP_BEKLEYEN_YOK: state'te creation_id yok. Çağıran zaten
        # "instagram_creation_id" in state diye bakıyor, yani buraya normalde
        # hiç gelinmez (yarış durumu olursa da sessiz geçmek doğru).
    except Exception as e:
        log(f"  Instagram HATA: {e}")


def _check_tiktok_notification(project_dir: str, state: dict) -> None:
    """state.json'da tiktok_publish_id var (zaten yüklü) ama henüz bildirim
    gönderilmediyse, golden-hour'daysak telefona bildirim gönderir."""
    if state.get("tiktok_notified"):
        log("  TikTok: zaten yüklü, atlanıyor")
        return
    try:
        from tiktok_upload import notify_pending_publish as tt_notify
        if tt_notify(project_dir):
            log("  TikTok: bildirim gönderildi (golden-hour) — uygulamadan yayınla")
        else:
            # notify_pending_publish() False dönmesinin İKİ sebebi var ve
            # eskiden ikisi de aynı (yanıltıcı) satırı basıyordu: (a) gerçekten
            # golden-hour dışındayız, (b) bildirim kanalı hiç kurulu değil.
            # (b) durumunda sebep golden-hour DEĞİL ve 17 bekleyen projede bu
            # satır her koşuda 17 kez yanlış bilgi basıyordu — tiktok_upload.py
            # o durumu zaten koşu başına TEK satır olarak logluyor.
            import notify
            if not notify.is_configured():
                return
            log("  TikTok: zaten yüklü, bildirim golden-hour penceresi bekleniyor")
    except Exception as e:
        log(f"  TikTok bildirim HATA: {e}")


def _check_youtube_captions(project_dir: str, state: dict) -> bool:
    """state.json'da youtube_video_id var ama youtube_captions_done yoksa
    (gerçek sözlerle hizalanmış altyazı henüz yayınlanmadıysa) dener —
    sözler dosyası yoksa ya da YouTube'un ASR'si henüz hazır değilse
    atlar/bir sonraki koşuya bırakır (bkz. youtube_captions.py).

    Döner: bu çağrı GERÇEKTEN bir YouTube API isteği yaptı mı (True) yoksa
    yerel kontrollerle mi çıktı (False) — çağıran taraf bunu, tek bir koşuda
    kaç projenin API'ye gerçekten dokunduğunu (kota tüketimini) sınırlamak
    için kullanır (bkz. _drain_golden_hour_queue).

    False dönen YEREL dallar: zaten yapılmış / video henüz YouTube'da yok /
    `upload/token.json` yok / doğrulanmış sözler dosyası yok / önceki koşuda
    sözler UYUŞMADI ve 24 saatlik soğuma penceresi sürüyor
    (`youtube_captions.UYUSMAZLIK_BEKLEME_SN`, damga state.json'daki
    `youtube_captions_uyusmazlik_at`).

    DOCSTRING DÜZELTMESİ (2026-09-11): burada eskiden "cooldown içinde" ve
    "SESSİZCE çıktı" yazıyordu; ikisi de KARŞILIKSIZDI — kodda hiçbir yerde
    cooldown yoktu ve o dallar log'a tek satır bile bırakmıyordu. Bugün
    ikisi de gerçek oldu: uyuşmazlık soğuma penceresi eklendi ve yerel
    dalların hepsi sebebini yazıyor. Tek SESSİZ dal kaldı — "video henüz
    YouTube'a çıkmamış"; her bekleyen proje için her koşuda satır basmak
    gürültü olurdu (bkz. youtube_captions.sync_captions'ın docstring'i)."""
    if state.get("youtube_captions_done") or not state.get("youtube_video_id"):
        return False
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")
    if not os.path.isfile(os.path.join(upload_dir, "token.json")):
        # SESSİZ DEĞİL: yetki dosyası yoksa altyazı hattı KATALOĞUN TAMAMI için
        # ölüdür ve tek belirtisi "hiçbir videoda düzeltilmiş altyazı yok"
        # olurdu (bkz. CLAUDE.md: "sessizce False dönen bir koruma, OLMAYAN
        # korumadan KÖTÜDÜR"). Proje başına DEĞİL koşu başına tek satır —
        # sebep tek, 18 proje için 18 kez yazmak log'u gürültüye boğardı.
        import notify
        notify.uyar_bir_kez(
            "youtube_captions_token_yok",
            "  YouTube altyazı atlandı: upload/token.json yok — bu koşuda "
            "HİÇBİR projenin altyazısı senkronize edilmeyecek "
            "(yetkilendirme: python upload/youtube_auth.py).")
        return False
    try:
        from youtube_captions import sync_captions as yt_sync_captions
        result = yt_sync_captions(project_dir)
        if result == "done":
            log("  YouTube altyazı: gerçek sözlerle hizalanıp yayınlandı")
            return True
        elif result == "pending":
            log("  YouTube altyazı: ASR henüz hazır değil, sonraki koşuda tekrar denenecek")
            return True
        # "already"/"skipped" yerel kontrollerle sessizce çıkar, API'ye hiç
        # dokunmaz — kota tüketimine saymıyoruz.
        return False
    except Exception as e:
        # Tamamlanmamış söz dosyası arıza DEĞİL: insanın sözleri yazmasını
        # bekliyor. "HATA" olarak loglanınca durum panelinde asla kaybolmayan
        # bir alarma dönüşüyor ve gerçek arızaların yanında gürültü yapıyordu.
        from caption_align import LyricsNotReady
        if isinstance(e, LyricsNotReady):
            log(f"  YouTube altyazı atlandı: {e}")
            return False
        log(f"  YouTube altyazı HATA: {e}")
        return True


def _drain_golden_hour_queue(project_dirs: list) -> None:
    """auto-pace batch seçimine GİRMEYEN projeler için bile, ZATEN başlatılmış
    (Instagram konteyneri oluşturulmuş / TikTok'a yüklenmiş) ama golden-hour'u
    bekleyen aksiyonları kontrol eder — aksi halde bir proje uzun süre batch'e
    girmezse (kaç proje bekliyorsa ona göre kademelenen aralık nedeniyle)
    golden-hour penceresini hiç yakalayamayabilir. Render/YouTube/TikTok
    upload/YENİ Instagram konteyneri BAŞLATMAZ, sadece bekleyeni tamamlar.
    Aynı sebeple YouTube altyazı senkronizasyonu da burada kontrol ediliyor —
    _is_fully_done() bilerek youtube_captions_done'ı SAYMIYOR (bkz. o
    fonksiyonun docstring'i), yani 3 platforma da yüklenmiş ama altyazısı
    henüz senkronize olmamış bir proje `pending` listesinde görünmeyebilir;
    `ready` (sadece `pending` değil) kullanmak bunu da kapsıyor.

    YouTube altyazı kontrolü TEK bir koşuda EN FAZLA BİR projede gerçek bir
    API isteğine dönüşür (`_check_youtube_captions`'ın True dönmesiyle
    anlaşılır) — `captions.list` her proje için ayrı bir istek olduğundan,
    burada TÜM `ready` listesini (kataloğun çoğunda bir `*_sozler.md` olduğu
    için genelde 10+ proje) gezip hepsinde API'ye dokunmak günlük YouTube
    kotasını (10.000 birim) tek bir çalıştırmada tüketip asıl video
    yüklemelerini engelleyebiliyordu (gerçekleşti: 2026-09-06, bkz. CLAUDE.md)."""
    captions_checked_this_run = False
    for project_dir in project_dirs:
        state = _load_state(project_dir)
        # NEDEN "instagram_media_id" KOŞULU YOK: eskiden burada
        # `and "instagram_media_id" not in state` vardı; zaten yayınlanmış bir
        # gönderinin VARLIĞI, sonradan oluşturulmuş YENİ bir konteyneri
        # (ör. "kapak değişti, yeniden paylaş") kalıcı olarak blokluyordu —
        # Gece Sürüşü / Kalbim Oynuyor'da 05 Eylül konteynerleri hiç
        # yayınlanmadı, log'da 6 gün "golden-hour bekleniyor" yazdı. Kararı
        # artık try_publish_pending() veriyor: konteyner son yayından YENİ mi
        # (instagram_upload._konteyner_yayindan_yeni), damga eksikse temkinli
        # davranıp yayınlamıyor. Yani çift yayın koruması KIRILMADI, sadece
        # doğru katmana taşındı.
        if "instagram_creation_id" in state:
            _check_instagram_pending(project_dir)
        if state.get("tiktok_publish_id") and not state.get("tiktok_notified"):
            _check_tiktok_notification(project_dir, state)
        if not captions_checked_this_run:
            if _check_youtube_captions(project_dir, state):
                captions_checked_this_run = True


def process_project(project_dir: str, privacy: str, schedule: bool = True) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    try:
        generate_cover.generate(project_dir)
    except Exception as e:
        log(f"  cover/art üretimi HATA: {e}")
        return

    if not _is_rendered(project_dir):
        log(f"=== Render: {project_dir} ===")
        try:
            if not render_module.render_project(project_dir):
                log(f"  render başarısız, bu proje atlanıyor: {project_dir}")
                return
        except Exception as e:
            log(f"  render HATA: {e}")
            return
    else:
        log(f"=== Zaten render edilmiş, upload kontrolüne geçiliyor: {project_dir} ===")

    # UYUMLULUK KAPISI (bkz. uyumluluk.py). Render'daki kontrolden AYRI:
    # orada uretim oncesi bakiliyor, burada YAYIN oncesi. Bugun iki politika
    # riski de olay olduktan sonra kesfedildi (Content ID eslesmesi, "toplu
    # uretilmis icerik" kurali) - kapinin yayin anina da konmasi bunun icin.
    #
    # HATA varsa yukleme HIC baslamiyor. Kapinin KENDISI cokerse de yukleme
    # baslamiyor: FAIL-CLOSED (2026-09-12). Eski kod `kontrol()`un istisnasini
    # "gormezden geliniyor" diye loglayip DEVAM ediyordu, yani yukaridaki
    # garanti yalnizca kontrol() duzgun DONDUGUNDE geceliydi; istisna dalinda
    # kapi SESSIZCE ACILIYORDU. Bu depoda tam olarak bunun bedeli odendi:
    # `uyumluluk.KOKLER` goreli yolken yanlis cwd'de `os.path.isdir` False
    # doner, kontrol() "hata=0 uyari=0" der ve kapi kendiliginden acilir.
    # "Bilmiyorum" ile "temiz" ayni sey DEGIL. Bu kapiya bagli iki gercek
    # koruma var - City Pulse Set'in acik telif itirazi (`telif_araliklari`) ve
    # 'Kullerimden Gec'/'Yeniden Dogacagim' md5 kopyasi - ve ikisinin de yanlis
    # tarafa dusmesi GERI ALINAMAZ bir yayin demek (Instagram'da yayinlanmis
    # medyayi API'den silmek MUMKUN DEGIL). Ters yonun maliyeti ise bu projenin
    # BIR KOSU gecikmesi: saatlik gorev bir sonraki koseda yeniden dener.
    # Ayni karar bugun depoda dort yerde daha verildi: upload/
    # ek_platform_backfill.py, upload/facebook_backfill.py, dj_clips.py,
    # upload/tiktok_publish_plan.py.
    #
    # KAPSAM - `return` yalnizca BU PROJEYI atliyor, KOSUYU degil: main()'deki
    # `for project_dir in batch` dongusu bir sonraki projeyle devam eder ve
    # finally'deki supurgeler yine calisir. Fail-closed "boru hatti sonsuza
    # kadar dursun" demek DEGIL, "bu proje bu kosuda yayinlanmasin" demek.
    #
    # notify.uyar_bir_kez BILEREK KULLANILMIYOR (supurgelerden farki): o desen
    # ayni projeye HER KOSUDA ve kosu ICINDE birden cok kez bakan supurgeler
    # icin var. `process_project()` proje basina kosuda BIR kez calisir, yani
    # asagidaki satir zaten kosu basina en fazla bir kez dusuyor - ustelik
    # atlanan proje `pending`de kaldigi icin satirin her kosuda tekrarlanmasi
    # GURULTU degil, arizanin surdugunun kaniti.
    try:
        import uyumluluk
        _uh, _uu = uyumluluk.kontrol(project_dir, "yukleme")
    except Exception as e:
        log(f"  uyumluluk kapisi COKTU ({type(e).__name__}: {e}) — fail-closed, "
            f"bu proje bu kosuda yayinlanmiyor")
        return
    # rapor_yaz KAPI KARARINDAN AYRI sarmalandi: o bir RAPORLAMA adimi, karar
    # adimi degil - kararin girdisi (_uh) zaten elimizde. Raporun yazilamamasi
    # temiz cikmis bir yayini durdurmaz; durdurmak korumaya HICBIR SEY eklemez,
    # yalnizca bir log fonksiyonunun arizasini yayin engeline cevirirdi. Ama
    # sessiz de kalmiyor: eksik rapor loga ISMIYLE dusuyor.
    try:
        uyumluluk.rapor_yaz(project_dir, _uh, _uu, log)
    except Exception as e:
        log(f"  uyumluluk raporu yazilamadi ({type(e).__name__}: {e}) — kapi "
            f"karari BUNDAN ETKILENMIYOR, hata/uyari sayisi: "
            f"{len(_uh)}/{len(_uu)}")
    if _uh:
        log("  uyumluluk hatasi nedeniyle bu proje yayinlanmiyor")
        return

    # DİKKAT — `state` bundan sonra BİR DAHA TAZELENMİYOR: aşağıdaki tüm
    # kapılar ("zaten yüklü mü") bu YÜKLEME ÖNCESİ fotoğrafı okuyor. Yani bu
    # koşuda yazılan hiçbir alan (youtube_video_id, youtube_shorts_video_id,
    # tiktok_publish_id, instagram_creation_id...) `state` içinde GÖRÜNMEZ —
    # onları okumak isteyen bir adım state'i DİSKTEN yeniden okumalı.
    # Bunun bedeli 2026-09-11'de ölçüldü: playlist senkronu bu fotoğrafa
    # bakan sync_project'i Shorts yüklemesinden ÖNCE çağırıyordu ve 20
    # Shorts'un hiçbiri hiçbir listeye girmedi (düzeltme: Shorts bloğundan
    # sonraki ikinci sync_project çağrısı). Diğer adımlar bugün KURTULUYOR
    # çünkü her birinin state'i diskten okuyan bir süpürgesi var
    # (_drain_golden_hour_queue, *_backfill, _facebook_yorumlari,
    # _refresh_stats). YENİ bir adım eklerken önce o süpürgeyi sor.
    state = _load_state(project_dir)
    youtube_video_id = state.get("youtube_video_id")

    if youtube_video_id:
        log("  YouTube: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_video as yt_upload
            youtube_video_id = yt_upload(project_dir, privacy, schedule=schedule)
            log(f"  YouTube: tamam, https://youtu.be/{youtube_video_id}")
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    # Tema/tarz playlist'i: video yüklüyse (yeni veya daha önceden), kendi temasının
    # playlist'ine ekler — state.json'da youtube_playlist_id zaten varsa atlar (idempotent),
    # yani daha önce yüklenmiş şarkılar için de retroaktif çalışır.
    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    if youtube_video_id:
        _check_youtube_captions(project_dir, state)

    # YouTube Shorts: zaten render edilen shorts_9x16.mp4'ü AYRICA (uzun formattan
    # bağımsız) bir YouTube Short olarak yükler — küçük/yeni kanallar için Shorts
    # akışı, uzun format önerilen videolar sisteminden çok daha erişilebilir bir
    # keşif kanalı. Uzun format zaten yüklüyse (youtube_video_id var) ona bağlantı
    # veriyor. Önce uzun format yüklenmiş olmalı (linklemek için video id gerekli).
    if "youtube_shorts_video_id" in state:
        log("  YouTube Shorts: zaten yüklü, atlanıyor")
    elif not youtube_video_id:
        log("  YouTube Shorts atlandı: önce uzun format yüklenmeli")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_short as yt_upload_short
            shorts_id = yt_upload_short(project_dir, privacy, youtube_video_id, schedule=schedule)
            log(f"  YouTube Shorts: tamam, https://youtube.com/shorts/{shorts_id}")
        except Exception as e:
            log(f"  YouTube Shorts HATA: {e}")
    else:
        log("  YouTube Shorts atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    # NEDEN İKİNCİ KEZ: yukarıdaki çağrı Shorts yüklemesinden ÖNCE çalışıyor,
    # o an state'te youtube_shorts_video_id YOK — yani Short hiçbir playlist'e
    # girmiyordu ve proje _is_fully_done'dan geçip pending'den düştüğü için bir
    # daha hiç denenmiyordu. sync_project idempotent ve üyeliği YouTube'dan
    # doğruluyor; aynı süreç içindeki ikinci çağrı önbellekten okuduğu için
    # EK KOTA harcamıyor.
    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    if "tiktok_publish_id" in state:
        _check_tiktok_notification(project_dir, state)
    elif os.path.isfile(os.path.join(upload_dir, "tiktok_token.json")):
        try:
            from tiktok_upload import upload_video as tt_upload
            publish_id = tt_upload(project_dir)
            log(f"  TikTok: tamam (taslak/inbox), publish_id={publish_id} — TikTok uygulamasından yayınla")
        except Exception as e:
            log(f"  TikTok HATA: {e}")
    else:
        log("  TikTok atlandı: upload/tiktok_token.json yok (önce tiktok_auth.py çalıştır)")

    # SIRA ÖNEMLİ — "bekleyen konteyner" kontrolü "zaten yüklü" dalının ÖNÜNE
    # alındı. Eskiden `instagram_media_id` dalı başta olduğu için, state'te
    # HEM eski bir media_id HEM de yeni bir creation_id varsa (yeniden paylaşım
    # senaryosu) elif hiç değerlendirilmiyor ve bekleyen konteyner kalıcı
    # olarak "zaten yüklü, atlanıyor" satırına takılıyordu. Bekleyen bir
    # konteyner varsa kararı try_publish_pending() vermeli (o, konteynerin son
    # yayından yeni olup olmadığına bakıyor); creation_id yoksa eski davranış
    # aynen geçerli.
    if "instagram_creation_id" in state:
        _check_instagram_pending(project_dir)
    elif "instagram_media_id" in state:
        log("  Instagram: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "instagram_token.json")):
        try:
            from instagram_upload import upload_video as ig_upload
            _log_instagram_result(ig_upload(project_dir))
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    else:
        log("  Instagram atlandı: upload/instagram_token.json yok (önce instagram_auth.py çalıştır)")

    _ek_platformlari_isle(project_dir, state, upload_dir, schedule)


# (bayrak, ad, state anahtarı, kimlik dosyası, modül, fonksiyon,
#  zamanlama_destegi, kurulum ipucu)
# zamanlama_destegi: fonksiyon `schedule` argümanı alıyor mu. Sadece
# Facebook alıyor (video_state=SCHEDULED). Telegram ve Bluesky'da
# zamanlanmış yayın kavramı yok — onlara `schedule` geçmek TypeError olurdu,
# ama daha sinsisi: geçmemek --no-schedule'ı Facebook'ta sessizce yok saymaktı.
# Bayrak açıkça yazılıyor, modül adından TÜRETİLMİYOR: modül bir gün yeniden
# adlandırılırsa türetme sessizce yanlış anahtara bakar ve platform hiç
# çalışmadığı hâlde hata da vermezdi.
# Üçü de aynı sözleşmeye uyuyor: fonksiyon project_dir alır, state.json'ı
# kendi yazar, hata durumunda istisna fırlatır.
_EK_PLATFORMLAR = [
    ("facebook", "Facebook", "facebook_reels_id", "facebook_token.json",
     "facebook_upload", "upload_reels", True,
     "önce facebook_auth.py çalıştır"),
    ("telegram", "Telegram", "telegram_message_id", "telegram_client_secrets.json",
     "telegram_upload", "upload_video", False,
     "BotFather'dan token al, botu kanala yönetici ekle"),
    ("bluesky", "Bluesky", "bluesky_post_uri", "bluesky_client_secrets.json",
     "bluesky_upload", "upload_video", False,
     "pip install atproto + bsky.app App Password"),
]


def _ek_platformlari_isle(project_dir: str, state: dict, upload_dir: str,
                          schedule: bool) -> None:
    """Facebook / Telegram / Bluesky — hepsi OPT-IN ve hepsi hatasız-geçer.

    Üç kapı sırayla:
      1. config.EK_PLATFORMLAR[bayrak] True mu — kapalıysa hiç denenmez, log da
         basılmaz (her saat 3 satır gürültü üretmesin).
      2. state'te zaten yüklendi işareti var mı.
      3. Kimlik dosyası var mı.

    Hiçbir hata otomasyonu durdurmaz: bu platformlar boru hattının ASIL işi
    (YouTube/TikTok/Instagram) değil, ekidir. Yeni bir platformdaki geçici bir
    API arızası yüzünden saatlik koşunun geri kalanının düşmesi kabul edilemez —
    bu yüzden her biri kendi try/except'i içinde ve yalnızca log'a yazıyor.
    """
    for (bayrak, ad, durum_anahtari, kimlik_dosyasi, modul_adi, fonksiyon,
         zamanlama_destegi, ipucu) in _EK_PLATFORMLAR:
        if not config.EK_PLATFORMLAR.get(bayrak, False):
            continue
        if durum_anahtari in state:
            log(f"  {ad}: zaten yüklü, atlanıyor")
            continue
        if not os.path.isfile(os.path.join(upload_dir, kimlik_dosyasi)):
            log(f"  {ad} atlandı: upload/{kimlik_dosyasi} yok ({ipucu})")
            continue
        try:
            modul = __import__(modul_adi)
            islev = getattr(modul, fonksiyon)
            sonuc = (islev(project_dir, schedule=schedule)
                     if zamanlama_destegi else islev(project_dir))
            log(f"  {ad}: tamam — {sonuc}")
        except Exception as e:
            log(f"  {ad} HATA: {e}")


def _refresh_latest_listing() -> None:
    """docs/latest.html'i (yayındaki TÜM şarkıların listesi — bkz. latest_release.py)
    HER çalıştırmada yeniden üretip SADECE o dosyayı push eder — sadece yeni
    yükleme anında değil, çünkü golden-hour zamanlamasıyla yüklenen bir video
    private→public'e YouTube tarafından SONRADAN (bu script'in bilgisi dışında)
    geçebiliyor; bir sonraki çalıştırma bunu otomatik yakalar (idempotent,
    değişiklik yoksa push_path zaten no-op, gereksiz commit atmaz). Hiçbir
    hata otomasyonu durdurmaz."""
    try:
        latest_release.regenerate()
        push_path(
            os.path.dirname(os.path.abspath(__file__)),
            "docs/latest.html",
            "docs: şarkı listesini güncelle (otomatik)",
            log,
        )
    except Exception as e:
        log(f"  latest.html güncelleme HATA: {e}")


def _facebook_backfill() -> None:
    """Katalogda Facebook'a hic gitmemis parcalari gunlere yayarak yukler.

    Neden ayri bir adim: _is_fully_done() Facebook'u SAYMIYOR (bilerek —
    saymak, bayrak kapaliyken tum katalogu sonsuza kadar "bekleyen"
    gosterirdi), dolayisiyla zaten tamamlanmis projeler bir daha hic
    islenmiyor ve geri doldurma kendiliginden olmuyor.

    Kendi kapilari var (bkz. facebook_backfill.backfill): bayrak kapaliysa,
    golden-hour disindaysak veya gunluk tavan (2) dolduysa hicbir sey yapmaz.
    Hicbir hata otomasyonu durdurmaz.
    """
    try:
        from facebook_backfill import backfill
        s = backfill(limit=1)
        if s.get("durum") == "tamam" and s.get("islenen"):
            for x in s["islenen"]:
                if x.get("hata"):
                    log(f"  Facebook geri doldurma HATA ({x['proje']}): {x['hata']}")
                else:
                    log(f"  Facebook geri doldurma: {x['proje']} -> {x['video_id']} "
                        f"(kalan {s.get('kalan', '?')})")
    except Exception as e:
        log(f"  Facebook geri doldurma HATA: {e}")


def _dj_tarama() -> None:
    """DJ setlerinin Content ID taramasini kontrol edip yayini acar.

    Neden SAATLIK kosuda: dj_famous_process.py haftada bir calisiyor, ikinci
    asama bir sonraki haftaya kalirdi. Bkz. dj_tarama_kontrol modul notu.
    Hicbir hata otomasyonu durdurmaz.
    """
    try:
        import dj_tarama_kontrol
        # Ozet satirlarini artik kontrol_et()'in KENDISI basiyor (bakilan=0
        # olsa bile, erken/damgasiz kovalariyla birlikte). Burada tekrar
        # basmak ayni bilgiyi iki satira bolüyordu; asil onemli olan sey
        # "hic satir yok" durumunun ORTADAN KALKMASI ve o garanti artik
        # modulun icinde (bkz. dj_tarama_kontrol._tara aciklamasi).
        dj_tarama_kontrol.kontrol_et(log)
    except Exception as e:
        log(f"  DJ tarama kontrolu HATA: {e}")


def _facebook_veri_erisimi() -> None:
    """Facebook veri erisimi suresi dolmadan once uyarir (log + telefon).

    Token SURESIZ ama Meta'nin ayri 90 gunluk `data access` sayaci var; o
    dolunca istekler sessizce yetkisiz donmeye basliyor - gonderiler bir gun
    aniden gitmiyor ve sebebi anlasilmiyor. Bu adim o sessiz arizayi
    onceden gorunur yapiyor.

    Push bildirimi GUNDE BIR: sayac 14 gun geri sayiyor, saatlik kosuda her
    seferinde telefon calmasi uyariyi degersizlestirirdi.
    """
    try:
        import notify
        from facebook_upload import veri_erisimi_durumu
        s = veri_erisimi_durumu()
        if not s.get("uyari"):
            return
        kalan = s.get("kalan_gun")
        mesaj = (f"Facebook veri erisimi {kalan} gun sonra doluyor "
                 "- upload/facebook_auth.py ile yeniden yetkilendir")
        log(f"  UYARI: {mesaj}")

        bugun = time.strftime("%Y-%m-%d")
        if s.get("bildirildi_gun") != bugun:
            try:
                notify.send("Facebook yetkisi yenilenmeli", mesaj)
            except Exception:
                pass
            s["bildirildi_gun"] = bugun
            try:
                from facebook_upload import VERI_ERISIMI_CACHE
                with open(VERI_ERISIMI_CACHE, "w", encoding="utf-8") as f:
                    json.dump(s, f, ensure_ascii=False, indent=2)
            except OSError:
                pass
    except Exception as e:
        log(f"  Facebook veri erisimi kontrolu HATA: {e}")


def _ek_platform_backfill() -> None:
    """Telegram/Bluesky'ya hic gitmemis sarkilari geri doldurur.

    NEDEN AYRI SUPURGE: _is_fully_done() bu iki platformu SAYMIYOR, dolayisiyla
    dort ana platformu tamamlayan proje pending'den kalici olarak dusuyor ve
    _ek_platformlari_isle() bir daha hic calismiyor. 2026-09-11 taramasi: 18
    sarkidan Telegram'a 1, Bluesky'a 1 gitmis; 14'u kalici dislanmis ve loga
    tek satir bile dusmemis. Facebook'un ayni bosluk icin zaten kendi geri
    doldurmasi vardi (_facebook_backfill), bu onun karsiligi.

    Hicbir hata otomasyonu durdurmaz.
    """
    try:
        from ek_platform_backfill import backfill
        s = backfill(log=log)
        for x in s.get("islenen", []):
            if x.get("hata"):
                log(f"  {x['platform']} geri doldurma HATA ({x['proje']}): {x['hata']}")
            else:
                log(f"  {x['platform']} geri doldurma: {x['proje']} -> {x.get('sonuc','')}")
        # Gunluk tavan devreye girdiginde loga HICBIR iz kalmiyordu: o gun
        # "kalan" sayisi degismiyor ama sebebi gorunmuyor, yani hat calisiyor mu
        # yoksa sessizce mi durdu ayirt edilemiyordu. Bu modul tam da o "sessiz
        # durus" desenini yakalamak icin var (bkz. docstring) — tavani da yaz.
        for ad, sebep in (s.get("tavan") or {}).items():
            log(f"  {ad} geri doldurma: gunluk tavan dolu ({sebep})")
        for ad, kalan in (s.get("kalan") or {}).items():
            if kalan:
                log(f"  {ad}: {kalan} sarki hala eksik")
    except Exception as e:
        log(f"  Ek platform geri doldurma HATA: {e}")


def _saglik_kontrol() -> None:
    """Sessizce duran hatlari yakalar (bkz. saglik_kontrol.py).

    Depoda bu is icin yazilmis IKI koruma vardi ve ikisi de hic calismiyordu:
    netlify_kontrol.py (hicbir yerden cagrilmiyordu) ve weekly_report'taki
    Instagram token suresi kontrolu (weekly_report zamanlayiciya bagli degil).
    netlify_kontrol'un kendi docstring'i, yakalamak icin yazildigi arizanin
    2026-09-08'de olup 25+ kosu boyunca fark edilmedigini yaziyor.

    Bildirimler gunde bir. Hicbir hata otomasyonu durdurmaz.
    """
    try:
        import saglik_kontrol
        saglik_kontrol.kontrol_et(log)
    except Exception as e:
        log(f"  Saglik kontrolu HATA: {e}")


def _izlenme_raporu() -> None:
    """Haftalik izlenme SURESI (watch-time) raporu — saatlik kosudan.

    upload/youtube_analytics.py dogru yazildi ama tek cagirani weekly_report.py'ydi
    ve o dosya hicbir Gorev Zamanlayici gorevine bagli degil (bkz. saglik_kontrol
    docstring'i, madde 2) — yani olcum pratikte HIC calismiyordu. saglik_kontrol
    ile ayni desen, tek farkla: damga gunluk degil HAFTALIK (izlenme raporu
    haftalik bir sey). Damga kontrolu fonksiyonun icinde: bu cagri haftanin
    geri kalaninda hicbir sey yapmaz, API'ye dokunmaz. Analytics izni hic
    alinmamissa haftada bir gurultusuz hatirlatma birakir.
    """
    try:
        from weekly_report import izlenme_raporu
        izlenme_raporu(log)
    except Exception as e:
        log(f"  İzlenme raporu HATA: {e}")


def _facebook_yorumlari() -> None:
    """Canliya cikmis zamanlanmis Facebook gonderilerine YouTube yorumunu ekler.

    Bu adim bugune kadar HIC calismiyordu: facebook_upload.post_pending_comment()
    yazilmisti ama depoda onu cagiran tek bir satir yoktu. Etkisi yalnizca
    ZAMANLANMIS gonderilerde gorunuyor - golden-hour icinde yuklenen gonderiler
    hemen yayinlandigi icin yorumu _finalize zaten o anda ekliyor. Katalogta
    zamanlanmis gonderi olusmadigi surece kimse fark etmedi.
    """
    try:
        from facebook_upload import bekleyen_yorumlari_tamamla
        s = bekleyen_yorumlari_tamamla()
        if s.get("tamamlanan"):
            log(f"  Facebook yorumu: {s['tamamlanan']} gönderiye eklendi "
                f"(kalan {s.get('kalan', '?')})")
        for h in s.get("hatalar", []):
            log(f"  Facebook yorumu HATA: {h}")
    except Exception as e:
        log(f"  Facebook yorumu HATA: {e}")


def _refresh_comments() -> None:
    """Yanit bekleyen YouTube yorumlarini onbellege yazar (saatte bir).

    Depoda bugune kadar yorum OKUYAN kod YOKTU — 11 gercek yorum (4-8 Eylul,
    5 ayri kisiden) hic gorulmemisti. Pano bunlari `comments_cache.json`'dan
    okuyor; YANIT bu hattan GONDERILMIYOR, panodan tek tek onaylaniyor.

    Kota: allThreadsRelatedToChannelId ile tum kanal yorumlari tek istekte
    geliyor — sayfa basina 1 birim. Tazeleme araligi modulun icinde.
    """
    try:
        from youtube_comments import fetch_comments
        veri = fetch_comments()
        if veri.get("istek"):
            log(f"  Yorumlar: {len(veri.get('bekleyen', []))} yanıt bekliyor "
                f"({veri['istek']} istek)")
    except Exception as e:
        log(f"  Yorum güncelleme HATA: {e}")


def _refresh_stats(base: str) -> None:
    """Katalogun YouTube istatistiklerini gunde bir tazeler.

    Neden burada: `youtube_stats.py` depoda vardi ama HIC cagrilmiyordu —
    18 projenin hicbirinin state.json'inda `youtube_views` yoktu. Depo ne
    yayinladigini biliyordu, nasil gittigini bilmiyordu.

    Maliyet ihmal edilebilir: 18 uzun + 18 Shorts = 36 id, videos.list tek
    istekte 50 id aliyor, yani 1 istek = **1 kota birimi** (gunluk 10.000'in
    on binde biri). Tazeleme araligi kontrolu get_stats_batch icinde: saatlik
    kosuda gun icinde ikinci kez cagrildiginda hic istek atmaz.

    Hicbir hata otomasyonu durdurmaz — olcum, yayin isinin eki.
    """
    try:
        from youtube_stats import get_stats_batch
        sonuc = get_stats_batch(base)
        if sonuc.get("istek"):
            log(f"  İstatistik: {sonuc['video']} video, {sonuc['proje']} proje "
                f"({sonuc['istek']} istek)")
    except Exception as e:
        log(f"  İstatistik güncelleme HATA: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Bekleyen (audio hazır) projeleri otomatik render edip yükler."
    )
    parser.add_argument(
        "--privacy", default="public", choices=["private", "unlisted", "public"],
        help="Yeni YouTube yüklemeleri için görünürlük (varsayılan: public)",
    )
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    parser.add_argument(
        "--no-schedule", action="store_true",
        help=(
            "YouTube'un golden-hour zamanlamasını (config.GOLDEN_HOURS, 12:00-14:00/"
            "18:00-22:00 TR) devre dışı bırakır — video hemen public yüklenir. "
            "VARSAYILAN: render/upload anı otomatik kademelemeyle (saatte bir kontrol) "
            "günün her saatine denk gelebildiği için, privacy=public olan videolar "
            "YouTube'a private+publishAt ile yüklenir ve bir sonraki golden-hour "
            "penceresinde otomatik public olur (YouTube bunu kendisi yapar, script "
            "tekrar çağrılmasına gerek yok)."
        ),
    )
    parser.add_argument(
        "--count", type=int, default=None,
        help=(
            "Bu koşuda işlenecek en fazla proje sayısı. VERİLMEZSE OTOMATİK kademelenir: "
            "kaç proje bekliyorsa 24 saate eşit aralıklarla yayılır (ör. 9 proje bekliyorsa "
            "~2.7 saatte bir 1 tane, 2 proje bekliyorsa 12 saatte bir 1 tane) — Görev "
            "Zamanlayıcı'yı sık çalıştır (ör. saatte bir), script sırası gelmemiş "
            "projeleri kendiliğinden atlar. Elle bir sayı verirsen bu otomatik kademe "
            "DEVRE DIŞI kalır, tam o kadarı hemen (zamanlama beklemeden) işlenir."
        ),
    )
    args = parser.parse_args()

    trim_log(LOG_PATH)
    auto_pull(os.path.dirname(os.path.abspath(__file__)), log)

    if not _acquire_lock():
        log("Başka bir auto_process.py çalışması zaten sürüyor (kilit dosyası var) — "
            "bu çalıştırma atlanıyor, çakışan yükleme riski önlendi.")
        return

    try:
        ready = find_ready_projects(args.base)
        if not ready:
            log("İşlenecek proje yok (audio hazır olan bulunamadı).")
            return

        # NOT: _drain_golden_hour_queue aşağıda her dönüşte `ready` (sadece
        # `pending` değil) ile çağrılıyor — _is_fully_done() tiktok_notified'ı
        # SAYMIYOR (bilerek: "yüklendi mi" ile "bildirim gönderildi mi" ayrı
        # şeyler), yani Instagram/YouTube/TikTok'un hepsi zaten yüklenmiş ama
        # TikTok bildirimi henüz gönderilmemiş bir proje `pending`'de değil
        # görünebilir; `ready` kullanmak bu projeyi de kapsar (drain zaten
        # ucuz/idempotent — bekleyeni yoksa hiçbir şey yapmaz).
        pending = [p for p in ready if not _is_fully_done(p)]
        if not pending:
            _drain_golden_hour_queue(ready)
            log("Tüm hazır projeler zaten 3 platforma da yüklenmiş, yapılacak bir şey yok.")
            return

        # _auto_pace_count'un 3. parametresi (varsayılan 1) aşağıdaki
        # `batch = pending[:count]` dilimiyle AYNI olmak ZORUNDA: 52 saatlik
        # yeni-yayın tabanının muafiyeti o dilimin TAMAMINA bakarak veriliyor
        # (bkz. o fonksiyondaki "AYIRT ETME" notu). Burada bir gün 1'den büyük
        # bir kademe istenirse, aynı sayı oraya da geçilmeli.
        count = args.count if args.count is not None else _auto_pace_count(pending, ready)
        if count == 0:
            # Bu koşuda yeni bir proje işlenmeyecek olsa bile, ZATEN başlatılmış
            # (Instagram konteyneri / TikTok yüklemesi) ama golden-hour'u bekleyen
            # aksiyonlar olabilir — onları yine de kontrol et.
            _drain_golden_hour_queue(ready)
            # "İşlenecek proje yok" — durum panelinin _RUN_START_RE'si bu ifadeyi
            # bir koşunun BAŞLANGICI olarak tanıyor. (Panel 2026-09'da
            # Desktop/jarvis-panel'den Hermes eklentisine taşındı:
            # %LOCALAPPDATA%/hermes/plugins/jarvis-hud/dashboard/plugin_api.py
            # — aynı kalıbı orası da kullanıyor.) Bu satır
            # olmadan bu erken-dönüş yolu hiçbir "koşu başlangıcı" işareti
            # bırakmıyordu, bu yüzden panel widget'ı BİR ÖNCEKİ koşunun (artık
            # çözülmüş) hatalarını süresiz göstermeye devam ediyordu — gerçek
            # bir örnekte (2026-09-08) çözülen bir "Temiz Sözler eksik" hatası
            # kullanıcıya hâlâ mevcutmuş gibi sesli/yazılı aktarılmıştı.
            log("İşlenecek proje yok bu koşuda (count=0), sadece golden-hour kontrolü yapıldı.")
            return

        batch = pending[:count]
        log(f"{len(pending)} bekleyen proje var, bu koşuda işlenecek ({len(batch)}): "
            f"{', '.join(os.path.basename(p) for p in batch)}")
        for project_dir in batch:
            process_project(project_dir, args.privacy, schedule=not args.no_schedule)

        _drain_golden_hour_queue([p for p in ready if p not in batch])
        log("Çalıştırma tamamlandı.")
    finally:
        _refresh_latest_listing()
        # base=None => youtube_stats.KOKLER (projects + dj_sets + derlemeler).
        # Onceden args.base ("projects") geciyordu ve cok-kok duzeltmesi olu
        # dalda kaliyordu: dj_sets'teki iki set bir kez elle olculmus, delta
        # hic hesaplanmamisti.
        _refresh_stats(None)
        _refresh_comments()
        _facebook_backfill()
        _ek_platform_backfill()
        _facebook_yorumlari()
        _facebook_veri_erisimi()
        _dj_tarama()
        _saglik_kontrol()
        _izlenme_raporu()
        _release_lock()


if __name__ == "__main__":
    main()
