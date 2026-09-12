"""DJ Famous — haftalık, GERÇEK bir kişiyi (bkz. dj_sets/README.md) konu alan,
tamamen AI-üretimi set videolarını render edip YouTube/TikTok/Instagram'a
yükler. auto_process.py'nin (günlük 6 üretimlik ana katalog) işlediği
projects/ klasörüne HİÇ dokunmaz — ayrı bir dj_sets/ klasörünü işler, ayrı
bir kilit dosyası kullanır, kendi log dosyasına yazar.

Kullanım:
    python dj_famous_process.py
    python dj_famous_process.py --privacy unlisted
    python dj_famous_process.py --no-schedule

Ana kataloğun aksine burada otomatik kademeleme YOK — haftada bir kez
Görev Zamanlayıcı ile çalıştırılması yeterli (bkz. setup_task_scheduler.ps1),
her çalıştırmada dj_sets/ altında bekleyen (audio hazır, henüz 3 platforma
tam yüklenmemiş) HER seti işler.

ÖNEMLİ — AI-üretimi olduğu GİZLENMEZ (kullanıcıyla netleştirilen tasarım
kararı, bkz. dj_sets/README.md):
  - YouTube: containsSyntheticMedia=True (youtube_upload.py'de zaten her
    yüklemede otomatik set ediliyor, burada ek bir şey gerekmiyor).
  - TikTok: tiktok_upload.py yüklerken "AI-generated content" etiketini
    TikTok uygulamasından elle açman gerektiğini zaten hatırlatıyor (genel,
    her proje için geçerli bir reminder).
  - Instagram: Meta'nın resmi 'is_ai_generated' API alanı doğrulanamadığı
    için (bkz. instagram_upload.py'deki not) caption'ın SONUNA
    social_text.build_ai_disclosure_line() ile tek, göze az batan bir satır
    ekleniyor — ana katalogda BU SATIR YOK, sadece DJ Famous'ta.
"""

import argparse
import json
import os
import sys
import time

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
import state_io
# Merkezi maskeleyici — log'a yazılan HER metin buradan geçiyor (bkz. log()).
# NEDEN import burada (çağrı noktalarında değil): bu dosyada 14 tane
# `log(f"... HATA: {e}")` var; maskelemeyi onlara tek tek dağıtmak, yarın
# eklenecek 15.'sinin yine sızdırması demekti. (auto_process.py ve
# watch_projects.py ile AYNI desen.)
#
# UYARI — bu yorum 2026-09-11'e kadar YALANDI: import yazılmıştı ama `log()`
# `maskele()`'yi HİÇ ÇAĞIRMIYORDU, yani dosyadaki tek geçiş import satırının
# kendisiydi. Gerçek bedeli de tam burada ödendi: 2026-09-04'te gerçek bir
# Instagram erişim token'ının düştüğü log dosyası `dj_famous_process.log`'du.
# Bu deponun "yazıldı, kendi içinde doğru, ama hiçbir yerden çağrılmıyor"
# arıza sınıfının ders niteliğinde örneği — ve yorumun doğru olduğunu
# söylemesi, arızanın grep'le bile görünmemesini sağlıyordu. Yorumun yalan
# söylemesi hiç yorum olmamasından KÖTÜ. Koruma artık `log()` içinde,
# testi: tests/test_entegrasyon_duman.py.
from gizli_maskele import maskele
from git_sync import auto_pull
from log_rotate import trim_log

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
RENDER_OUTPUTS = ["youtube_16x9.mp4", "shorts_9x16.mp4"]
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dj_famous_process.log")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dj_famous_process.lock")
# Ana kataloğun kilidinden (2 saat) çok daha yüksek — bir set ~1 saatlik ses
# içerebilir, render+3 platform yükleme normalde de çok daha uzun sürer.
LOCK_STALE_SECONDS = 8 * 60 * 60
# Bir set art arda kac kosu HIC ilerlemezse kuyrukta geri plana atilsin
# (kuyruk basi tikanmasi — bkz. _yayin_denemesini_guncelle). Tavan
# dj_tarama_kontrol.DJ_KALAN_DENEME_TAVANI ile ayni tutuldu (3): ayni boru
# hattinda iki farkli sabir esigi olmasi kafa karistirir.
DJ_YAYIN_DENEME_TAVANI = 3


# Kilit BİZDE mi? Sadece kendi kilidimizin mtime'ını tazelemek için (bkz. log()).
# Kaybeden süreç de log() çağırıyor; bayrak olmasaydı RAKİBİN kilidini tazeler,
# gerçekten bayat bir kilidin hiç eskimemesine yol açardı.
_KILIT_BIZDE = False


def log(msg: str) -> None:
    # 1) MASKELEME — yazmadan ÖNCE (auto_process.py:log() ile AYNI sıra).
    #    Bir ağ hatasının mesajı tam istek URL'sini (dolayısıyla sorgu
    #    dizesindeki access_token'ı) içerebiliyor; 2026-09-04'te BU dosyanın
    #    log'una gerçek bir Instagram token'ı böyle düştü. Bu script'te 14
    #    tane `log(f"... HATA: {e}")` var (Instagram 562/575, TikTok 537,
    #    YouTube 469/524, ek platformlar 321) — maskelemeyi o 14 çağrıya tek
    #    tek dağıtmak, yarın eklenecek 15.'sinin yine sızdırması demekti.
    #    Tek nokta, unutulamaz.
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {maskele(msg)}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    # 2) KİLİT NABZI — yazmadan SONRA. Kilidin mtime'ı koşu boyunca
    # tazeleniyor. NEDEN BURADA:
    # tazelemeyi "her platform yüklemesinden sonra" gibi bir listeye bağlamak,
    # yeni bir adım eklendiğinde güncellenmeyi unutulacak bir liste demekti
    # (deponun bugün bulduğu "yazıldı ama çalışmadı" deseni). log() bu
    # script'in TEK doğal darboğazı: her anlamlı adım zaten bir satır basıyor,
    # yani nabız adım listesiyle kendiliğinden güncel kalıyor. Maliyeti bir
    # utime çağrısı — log zaten dosya açıp yazıyor, ölçülebilir bir ek yük yok.
    # SINIR: iki log satırı arasındaki tek bir uzun işlem (ör. bir set
    # render'ı) yine tazelenmeden geçiyor; LOCK_STALE_SECONDS bu yüzden hâlâ
    # cömert (8 saat) tutuluyor.
    if _KILIT_BIZDE:
        try:
            os.utime(LOCK_PATH, None)
        except OSError:
            pass


def _acquire_lock() -> bool:
    """Kilidi ATOMİK olarak alır; alamazsa False döner.

    `O_CREAT | O_EXCL`: dosya zaten varsa işletim sistemi FileExistsError
    fırlatıyor, yani "önce bak, sonra yarat" arasındaki pencere KAPANIYOR.
    Eski sürüm `os.path.isfile()` ile bakıp ayrı bir `open(..., "w")` ile
    yaratıyordu — iki süreç aynı anda "kilit yok" görüp ikisi de devam
    edebilirdi. Pencere teorik değil: watch_projects.py DAKİKADA BİR,
    Görev Zamanlayıcı ayrıca saatlik tetikliyor, dj_tarama_kontrol de
    bağımsız olarak bu script'i çağırıyor.
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


def _kaydet_durum(project_dir: str, guncelleme: dict) -> None:
    """state.json'a alan ekler/gunceller (varsa okuyup birlestirir).

    ATOMIK yazim (state_io.durum_yaz) — eskiden hedefin USTUNE dogrudan
    yaziliyordu. `open(..., "w")` dosyayi once SIFIRLIYOR; `json.dump` bitmeden
    surec olurse (Gorev Zamanlayici timeout'unda TerminateProcess, guc
    kesintisi) diskte YARIM bir JSON kalıyordu. Bunun bedeli bugun buyudu:
    `uyumluluk._durum()` sertlestirildi, bozuk state.json artik sessizce {}
    sayilmiyor — HATA uretip yayini tamamen durduruyor. Ortak yardimci
    (dj_tarama_kontrol._kaydet ve upload/youtube_upload._update_state de ayni
    modulu cagiriyor) uc kopyayi tek yerde topluyor.
    """
    st = _load_state(project_dir)
    st.update(guncelleme)
    state_io.durum_yaz(project_dir, st)


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_pending_sets(base: str) -> list:
    """audio'su hazır olan ve henüz 3 platforma da tam yüklenmemiş TÜM
    dj_sets/ klasörlerini, oluşturulma zamanına göre sıralı döner."""
    pending = []
    if not os.path.isdir(base):
        return pending
    for name in os.listdir(base):
        # `.` ile baslayan klasorler ATLANIYOR. derleme.py bugunden itibaren
        # derlemeyi once `.tmp-<ad>` klasorunde uretip `os.replace` ile hedefe
        # TASIYOR; o gecici klasor uretim sirasinda diskte audio.wav'li ama
        # yarim halde duruyor. Tarayici onu gorurse yarim bir derlemeyi yayina
        # sokardi.
        if name.startswith("."):
            continue
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if not _has_any(project_dir, AUDIO_NAMES):
            continue
        # meta.json YOKSA KLASOR HIC "pending" SAYILMIYOR. Kanitlanmis zarar:
        # youtube_upload.build_snippet({}) ile video "Untitled (Sözleri) |
        # Türkçe Hip-Hop Şarkısı" basligiyla CANLI yuklendi; bolum damgalari ve
        # kuratorluk notu da meta'dan geldigi icin derlemenin "inauthentic
        # content"e karsi var olus sebebinin TAMAMI kayboluyor. uyumluluk.py
        # bunu yakaliyor ama sadece UYARI olarak — yukleme yine devam ediyordu.
        # Kaynak (derleme.py) bugun atomik hale getirildi, ama elle olusturulan
        # ve eski yarim klasorler hala mumkun; kapi yayin tarafinda da gerekli.
        # Sessiz ATLAMIYOR: ses dosyasi olan ama meta'si olmayan bir klasor
        # gercek bir anomali, operator bunu loga bakinca gorebilmeli.
        if not os.path.isfile(os.path.join(project_dir, "meta.json")):
            log(f"  meta.json yok — bekleyen sayılmadı, yayına girmiyor: {project_dir}")
            continue
        state = _load_state(project_dir)
        fully_done = all(
            key in state
            for key in (
                "youtube_video_id", "youtube_shorts_video_id",
                "tiktok_publish_id", "instagram_media_id",
            )
        )
        if not fully_done:
            pending.append(project_dir)
    pending.sort(key=lambda p: (os.path.getctime(p), p))
    return pending


def _yayin_denemesini_guncelle(project_dir: str, onceki_anahtarlar: set) -> None:
    """Bir koşunun İLERLEME kaydedip kaydetmediğini state.json'a yazar.

    NEDEN (kuyruk başı tıkanması / head-of-line blocking): find_pending_sets
    ctime'a göre EN ESKİYİ veriyor ve --limit varsayılanı 1. Kalıcı olarak
    takılmış bir set (render her koşuda başarısız, cover üretilemiyor, token
    kaybolmuş) kuyruğun başında oturup KENDİSİNDEN YENİ her seti SÜRESİZ
    bloklardı.

    "İlerleme" ölçüsü: koşu sonunda state.json'da YENİ bir anahtar oluştu mu.
    Platform bazlı bir başarı listesi yerine bu genel ölçü seçildi — yeni bir
    platform eklendiğinde burasının güncellenmesi UNUTULAMAZ (deponun bugün
    bulduğu "yazıldı ama çalışmadı" deseni tam olarak böyle doğuyor).

    dj_tarama_bekliyor / dj_tarama_engelli setleri SAYILMIYOR: onlarda
    process_set zaten iş yapmadan dönüyor ve main'de sınırın DIŞINDA
    tutuluyorlar — "başarısız" saymak sayacı yanıltırdı.

    TAVANDA PES EDİLMİYOR, sadece sıra kaybediliyor — dj_tarama_kontrol'un
    dj_kalan_deneme deseninden BİLEREK farklı: orada bırakılan iş bir bildirim,
    burada bırakılan iş yayının kendisi olurdu. Set kuyruğun sonuna düşüyor,
    önünde yeni set yoksa yine işlenmeye devam ediyor.
    """
    st = _load_state(project_dir)
    if st.get("dj_tarama_bekliyor") or st.get("dj_tarama_engelli"):
        return
    if set(st) - set(onceki_anahtarlar) - {"dj_yayin_deneme"}:
        if st.get("dj_yayin_deneme"):
            _kaydet_durum(project_dir, {"dj_yayin_deneme": 0})
        return
    deneme = int(st.get("dj_yayin_deneme") or 0) + 1
    _kaydet_durum(project_dir, {"dj_yayin_deneme": deneme})
    if deneme == DJ_YAYIN_DENEME_TAVANI:
        log(f"  {os.path.basename(project_dir)}: {deneme} koşudur hiç ilerleme yok — "
            "kuyrukta geri plana atıldı, yeni setler öne geçebilir")


# (bayrak, ad, state anahtari, kimlik dosyasi, modul, fonksiyon, ek kwargs, ipucu)
# auto_process.py'deki tablonun DJ karsiligi. Ayri duruyor cunku iki fark var:
#
# 1. Telegram'da `kind="dikey"`. Varsayilan "uzun" (youtube_16x9.mp4) - katalogda
#    3-4 dakikalik bir sarki icin dogru, ama burada set 41-81 dakika ve o dosya
#    Telegram'in 50 MB bot sinirinin kat kat ustunde. Her seferinde
#    _ensure_size_ok'ta patlardi. 45 saniyelik dikey kesit gonderiliyor.
# 2. Zamanlama YOK - `schedule: False` ACIKCA veriliyor. Ilk surum {} birakmisti
#    ve upload_reels'in varsayilani `schedule=True` oldugu icin golden-hour
#    disindaki her kosuda Reel ZAMANLANIYORDU; yorum "hemen yayinlaniyor"
#    diyordu, kod tersini yapiyordu. DJ setleri Content ID kapisindan gectikten
#    SONRA yayinlaniyor ve o an golden-hour olmayabilir.
#
# Facebook ve Bluesky zaten shorts_9x16.mp4 kullaniyor (Reels 90 sn, Bluesky
# 3 dk sinirli) - onlarda ek argumana gerek yok.
_EK_PLATFORMLAR = [
    ("facebook", "Facebook", "facebook_reels_id", "facebook_token.json",
     "facebook_upload", "upload_reels", {"schedule": False},
     "once facebook_auth.py calistir"),
    ("telegram", "Telegram", "telegram_shorts_message_id", "telegram_client_secrets.json",
     "telegram_upload", "upload_video", {"kind": "dikey"},
     "BotFather'dan token al, botu kanala yonetici ekle"),
    ("bluesky", "Bluesky", "bluesky_post_uri", "bluesky_client_secrets.json",
     "bluesky_upload", "upload_video", {},
     "pip install atproto + bsky.app App Password"),
]


def _ek_platformlari_isle(project_dir: str, upload_dir: str) -> None:
    """Facebook / Telegram / Bluesky - hepsi OPT-IN ve hepsi hatasiz-gecer.

    state BURADA yeniden okunuyor, disaridan alinmiyor: YouTube/TikTok/
    Instagram adimlari state.json'i kendileri yazdi, process_set'in basinda
    okunan kopya artik bayat. Bayat kopyayla "zaten yuklu" kontrolu yapmak,
    ayni seti ikinci kez yuklemek demekti.

    Hicbir hata seti durdurmaz: bu ucu boru hattinin ASIL isi
    (YouTube/TikTok/Instagram) degil, ekidir.
    """
    state = _load_state(project_dir)
    for (bayrak, ad, durum_anahtari, kimlik_dosyasi, modul_adi, fonksiyon,
         ek, ipucu) in _EK_PLATFORMLAR:
        if not config.EK_PLATFORMLAR_DJ.get(bayrak, False):
            continue
        if durum_anahtari in state:
            log(f"  {ad}: zaten yuklu, atlaniyor")
            continue
        if not os.path.isfile(os.path.join(upload_dir, kimlik_dosyasi)):
            log(f"  {ad} atlandi: upload/{kimlik_dosyasi} yok ({ipucu})")
            continue
        try:
            modul = __import__(modul_adi)
            islev = getattr(modul, fonksiyon)
            sonuc = islev(project_dir, **ek)
            log(f"  {ad}: tamam - {sonuc}")
        except Exception as e:
            log(f"  {ad} HATA: {e}")


def _kesitleri_uret(project_dir: str) -> None:
    """Setin ek dikey kesitlerini (output/clip_XX.mp4) üretir — bkz. dj_clips.py.

    SADECE dj_sets/ altındaki setler için: process_set aynı zamanda
    derlemeler/ kökü için de çalışıyor (bkz. dj_tarama_kontrol) ve bir derleme
    zaten yayınlanmış şarkıların kurgusu — ondan kesit çıkarmak aynı sesi
    üçüncü kez yayınlamak olurdu.

    Zaten üretilmişse tekrar render EDİLMİYOR: kesit render'ı setin
    uzunluğuyla orantılı, ucuz değil.

    Hata seti DURDURMAZ: kesitler ana hattın (YouTube/TikTok/Instagram) işi
    değil, ekidir — _ek_platformlari_isle ile aynı "hatasız-geçer" deseni.
    """
    kok = os.path.basename(os.path.dirname(os.path.normpath(os.path.abspath(project_dir))))
    if kok != "dj_sets":
        return
    if _load_state(project_dir).get("dj_clips"):
        log("  DJ kesit: zaten üretilmiş, atlanıyor")
        return
    try:
        import dj_clips
        sonuc = dj_clips.clip_uret(project_dir)
        if sonuc.get("hata"):
            log(f"  DJ kesit üretimi atlandı: {sonuc['hata']}")
        else:
            log(f"  DJ kesit: {len(sonuc.get('uretilen') or [])} kesit üretildi "
                "(diskte bekliyor, yayını ayrı ve kısıtlı — bkz. dj_clips.py)")
    except Exception as e:
        log(f"  DJ kesit üretimi HATA (görmezden geliniyor): {e}")


def _kesit_yayini(base: str) -> None:
    """İKİNCİ DALGA: setlerden en fazla BİR kesidi yayına gönderir.

    NEDEN process_set'in İÇİNDE DEĞİL: find_pending_sets tamamlanmış setleri
    listeden düşürüyor (4 ana platform bitince set artık 'pending' değil).
    Kesit yayını setin kendi Shorts'undan GÜNLER sonra olacağı için, o an
    geldiğinde set çoktan pending olmaktan çıkmış oluyor — process_set'e
    konsaydı hiçbir kesit hiçbir zaman yayınlanmazdı. Bu süpürge pending'den
    bağımsız, base altındaki TÜM klasörlere bakıyor (auto_process'in
    _drain_golden_hour_queue'suyla aynı gerekçe).

    Hacim kısıtı süpürgenin kendisinde: koşu başına en fazla 1, set başına en
    fazla 1, küresel olarak en fazla haftada 1 (bkz. dj_clips.py modül notu).

    POLİTİKA KAPISI BU YOLDA DEĞİL, SÜPÜRGENİN İÇİNDE (2026-09-12): bu
    fonksiyon `main()`'in `finally` bloğundan koşuyor, yani `process_set`in
    ~493. satırındaki `uyumluluk.kontrol(..., "yukleme")` çağrısına HİÇ
    uğramıyor. Kapıyı buraya koymak da yetmezdi — süpürge hangi seti seçeceğine
    kendi karar veriyor. Bu yüzden kapı `dj_clips.uyumluluk_kapisi()` olarak
    kararın verildiği yere (`yayina_uygun_mu`) ve ağa çıkılan son noktaya
    (`kesit_yayinla`) kondu; ikisi de FAIL-CLOSED. Buradaki `atlanan` sebep
    satırları uyumluluk gerekçesini de basıyor.
    """
    try:
        import dj_clips
        s = dj_clips.supur(base, log)
        atlanan = s.get("atlanan") or []
        if s.get("bakilan") and not s.get("yayinlanan"):
            log(f"  DJ kesit yayını: {s['bakilan']} sete bakıldı, yayınlanacak kesit yok")
            # SEBEPLERİ YAZ. Eskiden `supur` her set için ayrıntılı bir sebep
            # üretiyor, sözlüğe koyuyor ve BURADA ATILIYORDU. Operatör
            # "Just Relax'in dj_tarama_temiz'i yok, elle eklemen gerekiyor"
            # mesajını ancak elle `--yayin-kuru` koşarsa görebiliyordu — ki
            # bunu yapması için zaten sorunu bilmesi gerekirdi. CLAUDE.md'nin
            # üçüncü sorusu ("çalışmadığını nasıl anlarız?") cevapsız kalıyordu.
            for a in atlanan[:6]:
                log(f"    - {a.get('set')}: {a.get('sebep')}")
            if len(atlanan) > 6:
                log(f"    - (+{len(atlanan) - 6} set daha)")
        elif not s.get("bakilan"):
            # Kök yoksa/boşsa `supur` tek satır bile yazmadan dönüyordu:
            # yanlış cwd ya da yanlış kök = TAM SESSİZLİK.
            log(f"  DJ kesit yayını: '{base}' altında bakılacak set yok")

        # Elle yapılacak TEK adım için bildirim: Content ID işareti eksik
        # olduğu için takılan set varsa operatörün Studio'da bakması gerekiyor.
        # Hattın başka hiçbir yerinde notify yok, oysa kanalın diğer emniyet
        # ağlarının (token süresi, Netlify, nabız, karantina) hepsinde var.
        bekleyen = [a for a in atlanan
                    if "tarama" in (a.get("sebep") or "").lower()]
        if bekleyen:
            try:
                import notify
                notify.uyar_bir_kez(
                    "dj_kesit_tarama_isareti",
                    "DJ kesit yayını bekliyor: %s — Studio'da telif bölümüne "
                    "bakıp state.json'a dj_tarama_temiz: true ekle."
                    % ", ".join(a.get("set", "?") for a in bekleyen[:3]))
            except Exception:
                pass
    except Exception as e:
        log(f"  DJ kesit yayını HATA (görmezden geliniyor): {e}")


def process_set(project_dir: str, privacy: str, schedule: bool) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    # IKINCI EMNIYET KEMERI — meta.json yoksa bu klasor HICBIR sey yapmadan
    # donuyor. find_pending_sets zaten ayni kapiyi koyuyor; NEDEN IKISI BIRDEN:
    #   1. Oradaki kapi bir SIRALAMA filtresi (klasor "bekleyen" sayilmiyor),
    #      buradaki bir YAYIN kapisi. Iki farkli sorumluluk; process_set disaridan
    #      da cagrilabilen bir giris noktasi (bkz. dj_tarama_kontrol'un
    #      --base ile tetikledigi kalan-platform akisi ve elle onarim kosulari).
    #   2. Tarama ile yayin arasinda dakikalar/saatler var (render + 6 platform).
    #      Bu arada meta.json silinir/bozulursa tek kapili tasarim yakalamazdi.
    #   3. Maliyeti 3 satir, engelledigi zarar GERI ALINAMAZ (canli "Untitled"
    #      yukleme). Asimetrik bahis.
    # Kasitli olarak uyumluluk kapisindan DAHA ERKEN: render de bosa gitmesin.
    if not os.path.isfile(os.path.join(project_dir, "meta.json")):
        log(f"  meta.json yok — yayın atlandı: {project_dir}")
        return

    try:
        generate_cover.generate(project_dir)
    except Exception as e:
        log(f"  cover/art üretimi HATA: {e}")
        return

    if not _is_rendered(project_dir):
        # Arka plan videosu render'dan ÖNCE hazırlanmalı — render.py klasörde
        # backdrop.mp4 arıyor. Başarısız olursa sessizce eski (bulanık art.jpg)
        # arka planına düşülüyor; seti yayınlamamak için bir sebep değil.
        if config.DJ_ARKA_PLAN_VIDEO:
            try:
                import stock_video
                log("  arka plan videosu hazırlanıyor (stok klipler)...")
                yol = stock_video.set_icin_arka_plan(project_dir)
                log(f"  arka plan: {yol or 'üretilemedi, art.jpg arka planına düşülüyor'}")
            except Exception as e:
                log(f"  arka plan videosu HATA (görmezden geliniyor): {e}")

        log(f"=== Render: {project_dir} ===")
        try:
            if not render_module.render_project(project_dir):
                log(f"  render başarısız, bu set atlanıyor: {project_dir}")
                return
        except Exception as e:
            log(f"  render HATA: {e}")
            return
    else:
        log(f"=== Zaten render edilmiş, upload kontrolüne geçiliyor: {project_dir} ===")

    # KESİT ÜRETİMİ — render'dan hemen sonra, yayın adımlarından ÖNCE.
    # Üretim ile YAYIN bilerek AYRI: kesitleri üretmek sadece diske yazmak
    # (bedava, Suno kotasına dokunmuyor), yayınlamaksa "inauthentic content"
    # riski taşıyan bir hacim kararı. Bu yüzden burada sadece üretiliyor;
    # hangisinin ne zaman yayınlanacağını _kesit_yayini/dj_clips.supur
    # belirliyor (bkz. dj_clips.py modül notu).
    _kesitleri_uret(project_dir)

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
    # "Bilmiyorum" ile "temiz" ayni sey DEGIL. Bu hat icin bahis somut: City
    # Pulse Set'in state.json'inda ACIK bir telif itirazi kayitli
    # (`telif_eser` + `telif_araliklari`) ve onu yeniden yayina sokan tek sey
    # bu kapinin acilmasi olurdu. Yayin GERI ALINAMAZ (Instagram'da yayinlanmis
    # medyayi API'den silmek MUMKUN DEGIL); ters yonun maliyeti ise bu setin
    # BIR KOSU gecikmesi. Ayni karar bugun depoda dort yerde daha verildi:
    # upload/ek_platform_backfill.py, upload/facebook_backfill.py, dj_clips.py,
    # upload/tiktok_publish_plan.py.
    #
    # KAPSAM - `return` yalnizca BU SETI atliyor, KOSUYU degil: main()'deki
    # `for project_dir in islenecek` dongusu bir sonraki setle devam eder ve
    # `finally`deki ikinci dalga (kesit yayini, supurgeler) yine calisir.
    # Fail-closed "boru hatti sonsuza kadar dursun" demek DEGIL, "bu set bu
    # kosuda yayinlanmasin" demek. Kesit yayini ayrica KENDI kapisina sahip
    # (`dj_clips.uyumluluk_kapisi`, o da fail-closed), yani bu `return`
    # kesitleri kapi acik birakarak gecmiyor.
    #
    # notify.uyar_bir_kez BILEREK KULLANILMIYOR (supurgelerden farki): o desen
    # ayni klasore HER KOSUDA ve kosu ICINDE birden cok kez bakan supurgeler
    # icin var. `process_set()` set basina kosuda BIR kez calisir - ustelik bu
    # hat HAFTALIK, yani satirin tekrari gurultu degil, arizanin surdugunun
    # kanitidir.
    try:
        import uyumluluk
        _uh, _uu = uyumluluk.kontrol(project_dir, "yukleme")
    except Exception as e:
        log(f"  uyumluluk kapisi COKTU ({type(e).__name__}: {e}) — fail-closed, "
            f"bu set bu kosuda yayinlanmiyor")
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

    state = _load_state(project_dir)
    youtube_video_id = state.get("youtube_video_id")

    if youtube_video_id:
        log("  YouTube: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_video as yt_upload
            # Ön tarama açıkken set ÖNCE private yükleniyor: Content ID
            # taraması gizlilikten bağımsız çalışıyor, böylece itiraz varsa
            # video herkese açılmadan ve diğer platformlara gitmeden görülüyor.
            # schedule da kapatılıyor - zamanlanmış yayın, tarama sonucunu
            # beklemeden videoyu kendiliğinden açardı.
            if config.DJ_ON_TARAMA:
                youtube_video_id = yt_upload(project_dir, "private", schedule=False)
            else:
                youtube_video_id = yt_upload(project_dir, privacy, schedule=schedule)
            log(f"  YouTube: tamam, https://youtu.be/{youtube_video_id}")
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    # --- Content ID kapısı -------------------------------------------------
    # Buradan sonrası (Shorts, TikTok, Instagram, Facebook, Telegram, Bluesky)
    # tarama TEMİZ çıkana kadar çalışmıyor. auto_process.py'nin saatlik koşusu
    # süreyi doldurunca kontrol ediyor; temizse videoyu public yapıyor VE bu
    # script'i yeniden tetikliyor (dj_tarama_kontrol -> _kalan_platformlari_isle),
    # böylece kısa formatlar haftalık koşuyu beklemiyor.
    # `youtube_video_id` KOŞULU YOK, bilerek: ilk sürüm `and youtube_video_id`
    # yazıyordu ve YouTube yüklemesi başarısız olduğunda (kota, ağ, token yok)
    # kapı tamamen devre dışı kalıyordu — set taranmadan TikTok/Instagram/
    # Facebook/Telegram/Bluesky'a gidiyordu. Tam da kapının önlemek için var
    # olduğu senaryo. YouTube'a çıkamamış bir set zaten hiçbir yere gitmemeli.
    if config.DJ_ON_TARAMA:
        durum = _load_state(project_dir)
        if durum.get("dj_tarama_engelli"):
            log("  Content ID ENGELİ var: diğer platformlara gönderilmiyor. "
                "Studio'da bölümü kesip state.json'dan dj_tarama_engelli'yi sil.")
            return
        if not durum.get("dj_tarama_temiz"):
            if not youtube_video_id:
                log("  YouTube'a yüklenemedi: tarama yapılamayacağı için diğer "
                    "platformlar da atlanıyor")
                return
            if not durum.get("dj_tarama_bekliyor"):
                _kaydet_durum(project_dir, {
                    "dj_tarama_bekliyor": True,
                    "dj_tarama_yuklendi_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                })
                log("  Content ID taraması bekleniyor: video private yüklendi, "
                    "%d saat sonra kontrol edilip devamı getirilecek"
                    % (config.DJ_TARAMA_BEKLEME_SN // 3600))
            else:
                log("  Content ID taraması hâlâ bekleniyor, diğer platformlar atlanıyor")
            return

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

    # NEDEN İKİNCİ KEZ: yukarıdaki çağrı Content ID kapısından ve Shorts
    # yüklemesinden ÖNCE çalışıyor, o an state'te youtube_shorts_video_id YOK —
    # yani Short hiçbir playlist'e girmiyordu (derlemenin Short'unda gerçekleşti:
    # 6Ha3xm3mw74, 2026-09-11 18:13, elle eklenmek zorunda kalındı).
    # sync_project idempotent ve üyeliği YouTube'dan doğruluyor
    # (playlistItems.list, süreç ömrü boyunca önbellekli); aynı süreç içindeki
    # ikinci çağrı önbellekten okuduğu için EK KOTA harcamıyor.
    # İlk çağrı KALDIRILMADI: o, karantinada bekleyen (buradan hiç geçemeyen)
    # uzun formatı listeye koyuyor — Content ID kapısı `return` ettiğinde
    # buraya hiç gelinmiyor.
    if os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import sync_project as yt_sync_playlist, get_authenticated_service as yt_service
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    if "tiktok_publish_id" in state:
        log("  TikTok: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "tiktok_token.json")):
        try:
            from tiktok_upload import upload_video as tt_upload
            publish_id = tt_upload(project_dir)
            log(f"  TikTok: tamam (taslak/inbox), publish_id={publish_id} — TikTok uygulamasından "
                f"yayınla, 'AI-generated content' etiketini açmayı UNUTMA")
        except Exception as e:
            log(f"  TikTok HATA: {e}")
    else:
        log("  TikTok atlandı: upload/tiktok_token.json yok (önce tiktok_auth.py çalıştır)")

    def _log_instagram_result(media_id: str | None) -> None:
        if media_id:
            log(f"  Instagram: tamam, media_id={media_id}")
        else:
            log("  Instagram: konteyner hazır, golden-hour penceresi bekleniyor")

    if "instagram_media_id" in state:
        log("  Instagram: zaten yüklü, atlanıyor")
    elif "instagram_creation_id" in state:
        # Önceki çalıştırmada konteyner oluşturulmuş ama golden-hour dışında
        # kaldığı için yayınlanamamıştı (bkz. instagram_upload.try_publish_pending).
        # NOT: DJ Famous haftada bir çalıştığı için (varsayılan Cuma 18:00 —
        # BİLEREK config.GOLDEN_HOURS'un akşam penceresiyle örtüşüyor) bu dal
        # normalde hiç tetiklenmemeli; -DjFamousTime golden-hour DIŞINA
        # ayarlanırsa konteyner 24 saat içinde expire olabilir (bir sonraki
        # kontrol ancak bir hafta sonra gelir) — DjFamousTime'ı GOLDEN_HOURS
        # içinde tutmak en güvenlisi.
        try:
            from instagram_upload import try_publish_pending as ig_try_publish
            _log_instagram_result(ig_try_publish(project_dir))
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    elif os.path.isfile(os.path.join(upload_dir, "instagram_token.json")):
        try:
            from instagram_upload import upload_video as ig_upload
            from social_text import build_caption, build_ai_disclosure_line, resolve_language
            meta_path = os.path.join(project_dir, "meta.json")
            meta = {}
            if os.path.isfile(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            caption = build_caption(meta) + "\n\n" + build_ai_disclosure_line(resolve_language(meta))
            _log_instagram_result(ig_upload(project_dir, caption=caption))
        except Exception as e:
            log(f"  Instagram HATA: {e}")
    else:
        log("  Instagram atlandı: upload/instagram_token.json yok (önce instagram_auth.py çalıştır)")

    _ek_platformlari_isle(project_dir, upload_dir)

    # Zamanlanmis Facebook gonderilerinin YouTube yorumu. Setin KENDI
    # gonderisi bu anda henuz canli olmayabilir (golden-hour'a zamanlandi);
    # supurge tum projelere baktigi icin ONCEKI setlerin/sarkilarin bekleyen
    # yorumlari burada tamamlaniyor. Kendisininki bir sonraki kosuda.
    try:
        from facebook_upload import bekleyen_yorumlari_tamamla
        s = bekleyen_yorumlari_tamamla()
        if s.get("tamamlanan"):
            log(f"  Facebook yorumu: {s['tamamlanan']} gönderiye eklendi "
                f"(kalan {s.get('kalan', '?')})")
    except Exception as e:
        log(f"  Facebook yorumu HATA: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="dj_sets/ altında bekleyen DJ Famous setlerini render edip yükler."
    )
    parser.add_argument(
        "--privacy", default="public", choices=["private", "unlisted", "public"],
        help="Yeni YouTube yüklemeleri için görünürlük (varsayılan: public)",
    )
    parser.add_argument("--base", default="dj_sets", help="Set klasörlerinin kök dizini")
    parser.add_argument("--limit", type=int, default=1,
                        help="Bu koşuda en fazla kaç YENİ set işlensin (varsayılan 1). "
                             "Content ID kapısında bekleyenler bu sayıya dahil değil.")
    parser.add_argument(
        "--no-schedule", action="store_true",
        help="YouTube'un golden-hour zamanlamasını (config.GOLDEN_HOURS) devre dışı "
             "bırakıp hemen public yükler (bkz. auto_process.py --no-schedule).",
    )
    args = parser.parse_args()

    auto_pull(os.path.dirname(os.path.abspath(__file__)), log)

    if not _acquire_lock():
        log("Başka bir dj_famous_process.py çalışması zaten sürüyor (kilit dosyası var) — "
            "bu çalıştırma atlanıyor.")
        return

    try:
        # LOG BUDAMA — `trim_log` import'u bu dosyada yazılmış ama HİÇ
        # çağrılmıyordu (maskeleme ile aynı "yazıldı, bağlanmadı" arızası).
        # KALDIRMAK yerine ÇAĞIRMAK seçildi, iki nedenle:
        #  (1) auto_process.py ve watch_projects.py kendi log'larını her
        #      koşuda buduyor; bu dosya budamasaydı `dj_famous_process.log`
        #      depodaki TEK sınırsız büyüyen log olarak kalırdı.
        #  (2) `trim_log` sadece budamıyor, TUTTUĞU satırları da yeniden
        #      maskeliyor (bkz. log_rotate.py) — yani diskte HÂLİHAZIRDA
        #      duran 2026-09-04 sızıntısını temizleyen ikinci savunma hattı.
        #      watch_projects.py:323 bunu dakikada bir çağırıyor ama
        #      `_is_running` kapısı var: sızıntının YAZILDIĞI an tam da
        #      koşunun sürdüğü andır, yani o hafifletici tam o anda devre
        #      dışı. Buradaki çağrı o boşluğu kapatıyor.
        # NEDEN KİLİTTEN SONRA (auto_process.py kilitten ÖNCE çağırıyor):
        # trim_log dosyayı tümden okuyup yeniden YAZIYOR; paralel bir koşu
        # o sırada append ediyorsa satır kaybolabilir. Kilit alındıktan sonra
        # başka bir dj_famous_process koşusu olmadığı garanti.
        trim_log(LOG_PATH)

        pending = find_pending_sets(args.base)
        if not pending:
            # Yeni set olmaması kesit yayınını ENGELLEMEMELİ: ikinci dalga
            # tam olarak "yeni set yokken de kanalda bir şey çıksın" için
            # var. Eskiden burada return vardı, süpürge hiç çalışmazdı.
            # `_kesit_yayini` BURADA ÇAĞRILMIYOR: `finally` bloğu her
            # çıkış yolunda çalıştırıyor (aşağıdaki gerekçe).
            log("İşlenecek DJ Famous seti yok.")
            log("Çalıştırma tamamlandı.")
            return

        # KOŞU BAŞINA SINIR. Önceden hepsi tek koşuda işleniyordu; 3 set
        # hazırlanırsa üçü de AYNI GÜN yayınlanırdı. İki sakıncası var:
        # yayın temposu bozuluyor ve toplu yükleme, YouTube'un "inauthentic
        # content" politikasındaki "toplu üretilmiş" tarifine yaklaşıyor.
        #
        # Content ID kapısında BEKLEYEN setler sınırın DIŞINDA tutuluyor:
        # onlar için process_set zaten erken dönüyor (iş yapmıyor, sadece
        # log basıyor). Sınıra dahil edilselerdi, kapıda bekleyen tek bir set
        # arkasındaki tüm setleri süresiz bloklardı.
        #
        # `dj_tarama_engelli` de sınırın DIŞINDA — eskiden değildi ve bu, tam
        # da yukarıdaki gerekçenin gözden kaçmış ikizi: Content ID ENGELİ almış
        # bir set (process_set onda da erken dönüyor) `yeniler`in başında
        # kalıyor ve engel ancak İNSAN Studio'da bölümü kesip bayrağı silince
        # kalktığı için, arkasındaki her yeni seti günlerce bloklayabiliyordu.
        bekleyenler, yeniler = [], []
        for pd in pending:
            _d = _load_state(pd)
            (bekleyenler if (_d.get("dj_tarama_bekliyor") or _d.get("dj_tarama_engelli"))
             else yeniler).append(pd)

        # KUYRUK BAŞI TIKANMASI: tavanı doldurmuş (art arda
        # DJ_YAYIN_DENEME_TAVANI koşudur hiç ilerlemeyen) setler kuyruğun
        # SONUNA alınıyor. sort STABİL olduğu için iki grup da kendi içinde
        # ctime sırasını koruyor — sağlıklı setlerin sırası değişmiyor.
        yeniler.sort(key=lambda p: 1 if int(
            _load_state(p).get("dj_yayin_deneme") or 0) >= DJ_YAYIN_DENEME_TAVANI else 0)

        islenecek = bekleyenler + yeniler[:max(1, args.limit)]
        atlanan = len(yeniler) - len(yeniler[:max(1, args.limit)])
        log(f"{len(pending)} bekleyen set var, {len(islenecek)} işlenecek"
            + (f" ({atlanan} tanesi sonraki koşuya bırakıldı)" if atlanan else "")
            + f": {', '.join(os.path.basename(p) for p in islenecek)}")
        for project_dir in islenecek:
            # state anahtarlarının koşu ÖNCESİ fotoğrafı — ilerleme ölçüsü bu
            # kümenin büyüyüp büyümediği (bkz. _yayin_denemesini_guncelle).
            onceki = set(_load_state(project_dir))
            process_set(project_dir, args.privacy, schedule=not args.no_schedule)
            _yayin_denemesini_guncelle(project_dir, onceki)

        log("Çalıştırma tamamlandı.")
    finally:
        # İKİNCİ DALGA `finally`DE (auto_process.main() ile AYNI desen: orada
        # da tüm arka plan süpürgeleri `finally`den koşuyor). Eskiden döngüden
        # sonra, try'ın İÇİNDEYDİ: `process_set()` yakalanmamış bir istisna
        # atarsa süpürge o koşuda HİÇ çalışmıyordu. Etki küçük değil — kesit
        # yayını zaten küresel olarak haftada bir (dj_clips.KESIT_ARA_SN), yani
        # tek bir istisna ikinci dalgayı bir sonraki HAFTAYA atıyordu.
        # Kendi try'ı var: süpürgenin hatası kilidin bırakılmasını engellememeli
        # (bırakılmayan kilit bir sonraki koşuyu da bloklar, LOCK_STALE_SECONDS
        # dolana kadar 4 saat).
        try:
            _kesit_yayini(args.base)
        except Exception as e:
            log(f"  DJ kesit yayını HATA: {str(e)[:200]}")
        _release_lock()


if __name__ == "__main__":
    main()
