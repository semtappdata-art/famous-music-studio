"""projects/<isim>/ VE dj_sets/<isim>/ klasörlerini TEK SEFERLİK tarayıp
Suno'dan (herhangi bir dosya adıyla) yeni indirilen bir ses dosyasını
yakalayan, audio.wav/mp3/m4a'ya çeviren ve ilgili script'i (auto_process.py /
dj_famous_process.py) hemen tetikleyen hafif bir kontrol scripti. Aynı klasöre
(ör. Pixlr gibi bir tasarım aracından) düşen sahipsiz bir görseli de
cover.*/art.* olarak yerleştirir — bkz. _place_stray_images().

NEDEN VAR: Görev Zamanlayıcı'nın saatlik tetikleyicisi zaten otomatik
kademelemeyi (bkz. auto_process.py, _auto_pace_count) sürekli ilerletiyor —
bu script kademeleme mantığına DOKUNMUYOR, sadece "yeni dosya geldi ->
audio.* adına çevrilip fark edilene kadar" geçen süreyi (saatlerden
dakikalara) kısaltmak için var. Tetiklense bile auto_process.py kendi
"sırası geldi mi" kararını kendisi veriyor, erken paylaşım riski yok.

Kullanım:
    python watch_projects.py
TEK SEFERLİK bir tarama yapıp çıkar — sürekli çalışan bir arkaplan süreci
DEĞİL. setup_task_scheduler.ps1 bunu Görev Zamanlayıcı'da 1 dakikada bir
tekrar eden bir görev olarak kurar (auto_process.py'nin saatlik görevindeki
AYNI kanıtlanmış tetikleyici deseni — bkz. -Once/-RepetitionInterval). İlk
tasarım (sürekli döngü + "oturum açılışında başlat" tetikleyicisi) bu
ortamda "Erişim engellendi" hatasıyla kaydedilemedi — Windows'un logon-tabanlı
tetikleyicileri, arka planda/interaktif olmayan bir bağlamdan (bu Claude Code
oturumu gibi) kaydedilirken izin isteyebiliyor; zaman-tabanlı tekrarlı
tetikleyiciler bu kısıtlamaya takılmıyor. Detay: CLAUDE.md.
"""

import os
import subprocess
import sys
import time

# bkz. auto_process.py'deki aynı blok — Windows konsol/log çıktısı varsayılan
# yerel kod sayfasında (cp1252/charmap) Türkçe karakterleri bozuk basıyor.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from gizli_maskele import maskele, maskele_istisna
from log_rotate import trim_log
import notify
from uyumluluk import proje_klasorleri

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DJ_SETS_DIR = os.path.join(BASE_DIR, "dj_sets")
LOG_PATH = os.path.join(BASE_DIR, "watch_projects.log")
AUTO_PROCESS_LOG_PATH = os.path.join(BASE_DIR, "auto_process.log")
DJ_FAMOUS_LOG_PATH = os.path.join(BASE_DIR, "dj_famous_process.log")
HEARTBEAT_MARKER_PATH = os.path.join(BASE_DIR, ".watchdog_alerted")

# Tetiklenen script'lerin kilit dosyaları — bkz. _trigger_script().
TRIGGER_LOCKS = {
    "auto_process.py": os.path.join(BASE_DIR, ".auto_process.lock"),
    "dj_famous_process.py": os.path.join(BASE_DIR, ".dj_famous_process.lock"),
}

# Bir kilit dosyası bu süreden daha yeniyse "koşu gerçekten sürüyor" sayılır.
# Kasıtlı olarak KISA: burada amaç bayat kilidi tespit etmek değil (onu
# script'in kendisi yapıyor), sadece "az önce başlattığım koşu hâlâ ayakta"
# durumunu ucuza anlamak. Kilit mtime'ı koşu boyunca tazelenmediği için uzun
# bir render'da bu değer aşılabilir; o durumda tetikleme yine yapılır ve
# script'in KENDİ kilidi ikinci koşuyu erken çıkışa yönlendirir — yani bu
# kontrol bir güvenlik mekanizması DEĞİL, gereksiz süreç başlatmayı azaltan
# bir ön eleme.
TRIGGER_LOCK_FRESH_SECONDS = 15 * 60

# Bu KOŞUDA tetiklenen betikler — `_trigger_script()` aynı betiği ikinci kez
# başlatmasın diye (gerekçe orada, "AYNI TARAMADA İKİNCİ KEZ TETİKLEME").
# `main()` başında sıfırlanıyor: üretimde süreç tek tarama yapıp çıkıyor, ama
# testler `main()`'i aynı süreçte defalarca çağırıyor.
_TETIKLENENLER: set = set()

STABILITY_WAIT_SECONDS = 3  # indirme hâlâ sürüyor olabilir, boyut bu süre içinde değişmemeli

# auto_process.py'nin HER çalıştırmasında (yapılacak iş olsun olmasın) log()
# en az bir kez çağrılıyor (bkz. auto_process.py main() — kilit/boş/pace/
# tamamlandı yollarının HEPSİ log basıyor) — yani auto_process.log'un mtime'ı,
# saatlik Görev Zamanlayıcı görevinin gerçekten tetiklendiğinin ucuz ve
# güvenilir bir "nabız" göstergesi. Eşik 4 saat: saatlik tetikleyici +
# ExecutionTimeLimit 2 saat + MultipleInstances IgnoreNew nedeniyle bir
# koşunun uzun sürmesi bir sonraki tetiklemeyi atlatabilir, bu yüzden makul bir
# pay bırakıldı (yanlış alarm güveni azaltır).
#
# SINIR: bu kontrol watch_projects.py'nin İÇİNDE çalıştığı için, sorun
# watch_projects.py'nin kendi Görev Zamanlayıcı görevindeyse (auto_process.py
# değil) tespit edilemez — bu durumda auto_process.py yine de kendi bağımsız
# saatlik tetikleyicisiyle çalışmaya devam eder (watch_projects sadece "yeni
# dosya" tepki süresini kısaltıyordu, kaybı sınırlı), ama BU nabız kontrolü
# devre dışı kalmış olur. Makine tamamen kapalıysa/uyuyorsa zaten hiçbir yerel
# script bir şey gönderemez — bu, harici altyapısı olmayan bir kişisel
# otomasyonun doğal sınırı.
HEARTBEAT_STALE_SECONDS = 4 * 60 * 60

AUDIO_EXT_TO_NAME = {".wav": "audio.wav", ".mp3": "audio.mp3", ".m4a": "audio.m4a"}
AUDIO_NAMES = set(AUDIO_EXT_TO_NAME.values())

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Boru hattının KENDİ ürettiği görsellerin ROL adları — "sahipsiz" SAYILMAYACAK
# olanlar. LİSTE DEĞİL DESEN, bilerek (2026-09-12):
#
# Burada bugüne kadar sabit bir ad listesi vardı (`{"cover.jpg", "cover.jpeg",
# "cover.png"}`) ve `cover_vertical.png` o listede YOKTU. Oysa kapak İKİ ayrı
# oranda üretiliyor (generate_cover.py: `cover.png` 16:9 + `cover_vertical.png`
# 9:16; gerekçesi CLAUDE.md'de yazılı), yani HER projede boru hattının kendi
# ürettiği bir dosya "sahipsiz görsel" sayılıyordu. Bedeli ölçüldü: 21 projede
# 21 dosya, her biri için `_is_stable()` 3 saniye uyuyor. İzleyicinin Görev
# Zamanlayıcı'daki süre limiti 5 DAKİKA; bu tek satırlık eksik, hiçbir iş
# yapmadan o bütçenin dörtte birinden fazlasını yakıyordu
# (`gorev_izleri/watch_projects.log`: `süre=84.2sn`, HER koşuda).
#
# NEDEN DESEN: sabit ad listesi yarın `cover_square.png` / `art_blur.png`
# eklendiğinde AYNI ŞEKİLDE bayatlar — ve bayatladığında HATA VERMEZ, sessizce
# yavaşlar. Desen, boru hattının kendi adlandırma sözleşmesine bağlanıyor:
# `<rol>[_<varyant>].<uzantı>`.
#
# NEDEN BU KADAR DAR — fazla geniş bir desen GERÇEK sahipsiz görselleri gizler,
# yani bu script'in var olma sebebini yok eder: eşleşme "adın içinde geçiyor"
# değil, "adın İLK parçası (ilk `_`e kadar, uzantısız) TAM OLARAK bir rol adı".
#   sahipsiz DEĞİL : cover.png, cover.jpeg, cover_vertical.png, art.jpg,
#                    art_kare.png            (boru hattının ürettikleri)
#   HÂLÂ sahipsiz  : kapak_tasarimi.png, pixlr_export_1234.png,
#                    sahne_art_final.jpg, kart_art_gorseli.png, coverim.png
# Yani kullanıcının indirdiği bir dosyanın adında "cover"/"art" GEÇSE bile
# yakalanmaya devam ediyor; yalnızca dosyanın ROLÜ olarak BAŞLIYORSA eleniyor.
PIPELINE_IMAGE_ROLES = {"cover", "art"}

# Aşağıdaki İKİ liste HÂLÂ AÇIK AD LİSTESİ, bilerek: bunlar "sahipsiz mi"
# sorusunu değil, `_place_stray_images()`'ın "hedef zaten dolu mu / hangi ada
# yazacağım" sorusunu cevaplıyor. Orada SOMUT dosya adı gerekiyor (dosya
# oluşturuluyor), desen işe yaramaz.
COVER_NAMES = {"cover.jpg", "cover.jpeg", "cover.png"}
ART_NAMES = {"art.jpg", "art.jpeg", "art.png"}


def _is_pipeline_image(name: str) -> bool:
    """Bu görsel boru hattının KENDİ ürettiği bir dosya mı — bkz.
    PIPELINE_IMAGE_ROLES'deki gerekçe (desen, liste değil)."""
    stem = os.path.splitext(name)[0].lower()
    return stem.split("_", 1)[0] in PIPELINE_IMAGE_ROLES


def log(msg: str) -> None:
    """Log satırı yazar — yazmadan ÖNCE kimlik bilgisi maskeler.

    NEDEN BURADA (çağrı noktalarında değil): tek nokta, unutulamaz. Bir ağ
    hatasının mesajı tam istek URL'sini (dolayısıyla sorgu dizesindeki
    access_token'ı) içerebiliyor — 2026-09-04'te dj_famous_process.log'a
    gerçek bir Instagram token'ı böyle düştü. Maskelemeyi tek tek
    `log(f"... HATA: {e}")` çağrılarına bırakmak, yarın eklenecek YENİ bir
    çağrının yine sızdırması demekti."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {maskele(msg)}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _has_audio(project_dir: str) -> bool:
    return any(os.path.isfile(os.path.join(project_dir, name)) for name in AUDIO_NAMES)


def _find_stray_audio(project_dir: str) -> str | None:
    """AUDIO_NAMES'ten biri değil ama ses uzantılı bir dosya var mı — Suno'dan
    yeni indirilmiş, henüz yeniden adlandırılmamış bir dosya olabilir."""
    try:
        entries = os.listdir(project_dir)
    except OSError:
        return None
    for name in entries:
        ext = os.path.splitext(name)[1].lower()
        if ext in AUDIO_EXT_TO_NAME and name not in AUDIO_NAMES:
            return os.path.join(project_dir, name)
    return None


def _find_stray_images(project_dir: str) -> list[str]:
    """cover.*/art.* değil ama görsel uzantılı dosyaları döner — Pixlr gibi bir
    tasarım aracından indirilmiş, henüz yerleştirilmemiş kapak/kart görseli
    olabilir. Ada göre sıralı döner (kararlı, tekrarlanabilir işleme sırası)."""
    try:
        entries = sorted(os.listdir(project_dir))
    except OSError:
        return []
    strays = []
    for name in entries:
        if name.startswith("_"):
            continue  # render'ın ürettiği iç dosyalar (_backdrop_pan_*.png, _bg_base_tmp.png, vb.) — kullanıcının bıraktığı bir tasarım dosyası değil
        ext = os.path.splitext(name)[1].lower()
        if ext in IMAGE_EXTS and not _is_pipeline_image(name):
            strays.append(os.path.join(project_dir, name))
    return strays


def _has_any(project_dir: str, names: set) -> bool:
    return any(os.path.isfile(os.path.join(project_dir, name)) for name in names)


def _place_stray_images(project_dir: str) -> None:
    """Sahipsiz görselleri cover.*/art.* olarak yerleştirir. Kural basit ve
    öngörülebilir: dosya adında "art" geçiyorsa art.*, geçmiyorsa (ve henüz
    bir cover.* yoksa) cover.* olur — yaygın durum tek görsel indirmek ve bu
    kapak olarak kullanılmak. Zaten bir cover.* varken "art" içermeyen ikinci
    bir dosya gelirse DOKUNULMAZ — yanlış tahmin etmektense elle bırakılır."""
    for path in _find_stray_images(project_dir):
        if not _is_stable(path):
            continue  # muhtemelen indirme sürüyor, bir sonraki turda tekrar bakılacak
        base_name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        if "art" in base_name.lower():
            if _has_any(project_dir, ART_NAMES):
                continue  # art zaten dolu — cover'a geri düşme, yanlış tahmin olur
            target = os.path.join(project_dir, "art" + ext)
        else:
            if _has_any(project_dir, COVER_NAMES):
                continue  # cover zaten dolu, belirsiz durum, elle yerleştirilmeli
            target = os.path.join(project_dir, "cover" + ext)
        os.rename(path, target)
        log(f"  '{base_name}' -> '{os.path.basename(target)}' olarak yeniden adlandırıldı.")


def _is_stable(path: str) -> bool:
    """Dosya boyutu STABILITY_WAIT_SECONDS sonra da aynı mı (indirme hâlâ
    sürüyorsa boyut değişir, yarım dosyayı işlemeyelim)."""
    try:
        size_before = os.path.getsize(path)
    except OSError:
        return False
    if size_before == 0:
        return False
    time.sleep(STABILITY_WAIT_SECONDS)
    try:
        size_after = os.path.getsize(path)
    except OSError:
        return False
    return size_before == size_after


def _is_running(script_name: str) -> bool:
    """Tetiklenecek script'in kilidi TAZE mi (koşu muhtemelen sürüyor).

    Kullanım yeri: `_scan_dir()` — kilit tazeyse yeniden adlandırma da
    tetikleme de ERTELENİYOR (bkz. oradaki not).

    NEDEN: bu script DAKİKADA BİR çalışıyor (Görev Zamanlayıcı) ve
    auto_process.py ayrıca SAATLİK kendi tetikleyicisiyle koşuyor. Hedef
    script'in kilit alması atomik DEĞİL (`if os.path.isfile(LOCK)` ile
    `open(LOCK, "w")` arasında iki süreç geçebilir — TOCTOU); yani iki
    tetiklemeyi gerçekten aynı saniyeye denk getirmek aynı projeyi iki kez
    yüklemekle sonuçlanabilir. Kilidi ÖNCEDEN görüp süreci hiç başlatmamak,
    o yarışa girme olasılığını büyük ölçüde düşürüyor.

    Bu bir GARANTİ değil (asıl düzeltme hedef script'te `os.O_CREAT|O_EXCL`
    ile atomik kilit almak — o dosyalar başka bir ajanda). Burada yapılan,
    tetikleme tarafından kapatılabilen kısım."""
    lock_path = TRIGGER_LOCKS.get(script_name)
    if not lock_path or not os.path.isfile(lock_path):
        return False
    try:
        age = time.time() - os.path.getmtime(lock_path)
    except OSError:
        return False
    return age < TRIGGER_LOCK_FRESH_SECONDS


def _trigger_script(script_name: str) -> bool:
    """Hedef betigi KOPARARAK baslatir ve HEMEN doner. True = surec baslatildi.

    SARMALAYICIDAN GECIYOR (2026-09-12). Eskiden hedef betik DOGRUDAN
    cagriliyordu ve bu, Gorev Zamanlayici'nin kapattigi deligi izleyici
    tarafinda ACIK birakiyordu: `sys.executable` burada `pythonw.exe`
    (gorevler pencere acmasin diye oyle kuruldu), yani stdout/stderr YOK.
    Tetiklenen `auto_process.py` kendi log'unu ACMADAN olurse (import
    hatasi, sozdizimi hatasi) geriye TEK BAYT iz kalmiyordu — sarmalayicinin
    var olma sebebinin ta kendisi. Suno'dan yeni dosya dustugu an calisan
    yol bu oldugu icin, sessiz olum tam da en cok is yapilan anda olurdu.

    NEDEN ARTIK ENGELLEMIYOR (2026-09-12, ikinci duzeltme — canli olcum):
    burada `subprocess.run(...)` vardi, yani izleyici tetikledigi kosunun
    BITMESINI bekliyordu. Izleyici gorevinin `ExecutionTimeLimit`'i bugun
    2 saatten 5 DAKIKAya cekildi ("tarama saniyeler surer" varsayimiyla), ama
    tek bir sarkinin render'i tek basina 2 dk 26 sn olctu ve tam boru hatti
    bundan uzun. Sonuc: watcher yeni bir parca gorup tetikledigi anda kosu
    5. dakikada `TerminateProcess` ile OLDURULUYORDU. Uc bedeli vardi ve
    ucu de gercek:
      * `.auto_process.lock` ortada kalir (`finally` hic calismaz) ->
        SAATLIK gorev de `LOCK_STALE_SECONDS` (4 saat) boyunca durur;
      * `MAX_PARALLEL_RENDERS=2` ve ffmpeg `-y` ile DOGRUDAN nihai dosyaya
        yazdigi icin iki mp4 "yarim ama VAR" kalir; `auto_process._is_rendered()`
        yalnizca `os.path.isfile` baktigindan True doner -> sonraki kosu
        render'i ATLAR ve BOZUK videoyu yukler (log'da sadece "Zaten render
        edilmis" yazar). Bu ikinci bedel BU dosyadan KAPATILAMIYOR
        (`_is_rendered` `auto_process.py` + `dj_famous_process.py`'de) — ama
        tetikleyicisi buydu ve o kapatildi;
      * sarmalayici izinde `BASLADI` var, eslesen `BITTI` yok.
    Cozum: kosuyu izleyicinin omrunden AYIR. Tetiklenen betik zaten kendi
    log'unu, kendi kilidini ve kendi iz dosyasini tutuyor — izlenmesine gerek
    yok, ve donus kodu ZATEN kullanilmiyordu (`_scan_dir` eskiden de
    yoksayiyordu, `subprocess.run` hata koduna bakmiyordu). Artik "surec
    BASLATILABILDI mi" bilgisi donuyor; "kosu BASARILI mi" bilgisi bu
    fonksiyonun cevaplayabilecegi bir soru DEGIL (ve olmamali).

    NEDEN SADECE `Popen` YETMEZ (Windows): Gorev Zamanlayici gorevi bir JOB
    OBJECT icinde calistiriyor; job oldurulunce cocuk surecler de olur — yani
    duz bir `Popen` kopmayi SAGLAMAZ, sadece beklemeyi kaldirirdi ve kosu 5.
    dakikada yine olurdu. `CREATE_BREAKAWAY_FROM_JOB` cocugu job'dan
    cikariyor, `DETACHED_PROCESS` ise konsol baglantisini kesiyor (ayni
    zamanda script elle `python.exe` ile calistirildiginda pencere acmiyor).
    Bayraklar `sys.platform == "win32"` disinda KULLANILMIYOR (POSIX'te
    karsiligi `start_new_session=True`).

    YEDEK YOL — `CREATE_BREAKAWAY_FROM_JOB`, job `JOB_OBJECT_LIMIT_BREAKAWAY_OK`
    vermiyorsa CreateProcess'i ERROR_ACCESS_DENIED ile DUSURUR (Python'da
    `OSError`/`PermissionError`). O durumda SESSIZ KALINMIYOR (CLAUDE.md:
    sessizce basarisiz olan bir koruma, olmayan korumadan kotudur): log'a
    tek satir dusuyor ve breakaway'siz ikinci bir deneme yapiliyor — job
    icinde ama yine de ENGELLEMEYEN bir kosu. O da olmazsa `False` donuyor
    ve neden log'a yaziliyor. Beklemeye (`subprocess.run`) GERI DUSULMUYOR:
    engelleme, kacinilmaya calisilan arizanin ta kendisi.

    STD AKISLARI BILEREK YONLENDIRILMIYOR (ne DEVNULL ne PIPE): uretimde
    ebeveyn `pythonw.exe` oldugu icin handle'lar zaten NULL ve sarmalayici
    TAM OLARAK `sys.stderr is None` kosuluna bakip kendi iz dosyasina
    yonlendiriyor. `stderr=DEVNULL` vermek o kosulu bozar ve cokme
    traceback'lerini sessizce yutardi.
    """
    if script_name in _TETIKLENENLER:
        # AYNI TARAMADA IKINCI KEZ TETIKLEME (2026-09-12). Engelleyen surumde
        # bu imkansizdi: `subprocess.run` donene kadar dongu ilerlemiyordu, ve
        # ikinci proje sirasi geldiginde `_is_running()` kilidi TAZE goruyordu.
        # Kopmus tetiklemede o koruma YETMIYOR — yeni surec kilidini henuz
        # OLUSTURMAMIS olabilir (yarissa TOCTOU), yani ayni taramada iki yeni
        # parca varsa AYNI betik iki kez baslardi. Kosu-ici hafiza bunu kokten
        # kesiyor; kalan projeler bir sonraki dakikada zaten yeniden taraniyor
        # (`_is_running` kapisi sayesinde kosu bitene kadar erteleniyor).
        log(f"  {script_name} bu taramada zaten tetiklendi, ikinci tetikleme atlandi.")
        return False

    cmd = [sys.executable,
           os.path.join(BASE_DIR, "gorev_sarmalayici.py"),
           script_name]

    if sys.platform == "win32":
        kopuk = (subprocess.CREATE_BREAKAWAY_FROM_JOB
                 | subprocess.DETACHED_PROCESS
                 | subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            subprocess.Popen(cmd, cwd=BASE_DIR, creationflags=kopuk)
            _TETIKLENENLER.add(script_name)
            return True
        except OSError as e:
            # Job `JOB_OBJECT_LIMIT_BREAKAWAY_OK` vermiyor (ERROR_ACCESS_DENIED)
            # ya da baska bir CreateProcess hatasi. Sessiz kalinmiyor.
            log(f"  {script_name}: job'dan kopma reddedildi ({maskele_istisna(e)});"
                " job ICINDE, engellemeyen kosuya dusuluyor — bu kosu izleyicinin"
                " sure limitinde sonlandirilabilir.")
        try:
            subprocess.Popen(
                cmd, cwd=BASE_DIR,
                creationflags=(subprocess.DETACHED_PROCESS
                               | subprocess.CREATE_NEW_PROCESS_GROUP),
            )
            _TETIKLENENLER.add(script_name)
            return True
        except Exception as e:
            log(f"  {script_name} tetiklenemedi: {maskele_istisna(e)}")
            return False

    try:
        subprocess.Popen(cmd, cwd=BASE_DIR, start_new_session=True)
        _TETIKLENENLER.add(script_name)
        return True
    except Exception as e:
        log(f"  {script_name} tetiklenemedi: {maskele_istisna(e)}")
        return False


def _scan_dir(base_dir: str, trigger_script: str) -> None:
    """base_dir altındaki her proje klasörünü tarar: sahipsiz görselleri
    cover.*/art.* olarak yerleştirir (audio'dan bağımsız, her turda dener) ve
    sahipsiz bir ses dosyası bulup audio.* adına çevirdiğinde trigger_script'i
    (auto_process.py ya da dj_famous_process.py) tetikler."""
    if not os.path.isdir(base_dir):
        return
    # KANONİK KLASÖR FİLTRESİ (`uyumluluk.proje_klasorleri`, 2026-09-12).
    # Eskiden burada düz bir `sorted(os.listdir(base_dir))` vardı ve `.`/`_`
    # ön ekli klasörler PROJE SANILIYORDU. Bu bir varsayım değil, GERÇEKLEŞMİŞ
    # bir arıza: `dj_sets/_arda` (DJ Famous'un ham portre fotoğrafları —
    # audio/meta/state YOK, proje DEĞİL) her taramada taranıyordu ve
    # 2026-09-11 09:14'te izleyici oradaki `arda_01_ic_mekan.jpg`'yi
    # `dj_sets/_arda/cover.jpg` yapıp yeniden adlandırdı (log'da duruyor).
    # Kalan 8 fotoğraf da her koşuda "sahipsiz" sayılıp 8 × 3 sn uyku
    # harcatıyordu. `_` bu depoda "YOK SAY" demek ve kural zaten dört yerde
    # uygulanıyor (dj_clips._set_klasorleri, latest_release._collect,
    # uyumluluk.proje_klasorleri, bu dosyadaki DOSYA adı filtresi) — beşincisi
    # burasıydı ve eksikti. Kural KOPYALANMIYOR, kanonik fonksiyon ÇAĞRILIYOR:
    # yarın altıncı bir ön ek eklenirse tek yerde eklenmeli
    # (bkz. tests/test_proje_klasorleri_filtre.py).
    for project_dir in proje_klasorleri(base_dir):
        name = os.path.basename(project_dir)

        _place_stray_images(project_dir)

        if _has_audio(project_dir):
            continue
        stray = _find_stray_audio(project_dir)
        if not stray:
            continue
        if not _is_stable(stray):
            continue  # muhtemelen indirme sürüyor, bir sonraki turda tekrar bakılacak
        if _is_running(trigger_script):
            # Hedef script şu an koşuyor: ne yeniden adlandır ne tetikle.
            # NEDEN ADLANDIRMA DA ERTELENİYOR: dosyayı audio.* yapıp tetiklemeyi
            # atlasaydık, bir sonraki turda `_has_audio()` True dönüp bu proje
            # bir daha HİÇ tetiklenmezdi (sadece saatlik görevle, yani bu
            # script'in var olma sebebi olan gecikme geri gelirdi). Ertelemek,
            # `_is_stable()` başarısızlığıyla aynı desende doğal bir yeniden
            # deneme sağlıyor. Sessiz: dakikada bir çalıştığı için log'a
            # yazmak uzun bir render boyunca onlarca gereksiz satır demek.
            continue
        ext = os.path.splitext(stray)[1].lower()
        target = os.path.join(project_dir, AUDIO_EXT_TO_NAME[ext])
        os.rename(stray, target)
        log(f"{name}: '{os.path.basename(stray)}' -> '{os.path.basename(target)}' olarak yeniden adlandırıldı, {trigger_script} tetikleniyor...")
        _trigger_script(trigger_script)


def _check_heartbeat() -> None:
    """auto_process.log çok uzun süredir güncellenmemişse (saatlik Görev
    Zamanlayıcı görevi tetiklenmiyor demektir — makine kapalı/uykuda, görev
    devre dışı, ya da tekrarlayan bir çökme) telefona bir kereliğine uyarı
    gönderir. auto_process.log henüz hiç oluşmamışsa (ilk kurulum) sessizce
    atlar — bu bir arıza değil. Uyarı, log tekrar tazelenene kadar (sağlık
    geri gelene kadar) bir daha gönderilmez (HEARTBEAT_MARKER_PATH ile)."""
    if not os.path.isfile(AUTO_PROCESS_LOG_PATH):
        return
    age = time.time() - os.path.getmtime(AUTO_PROCESS_LOG_PATH)
    already_alerted = os.path.isfile(HEARTBEAT_MARKER_PATH)

    if age <= HEARTBEAT_STALE_SECONDS:
        if already_alerted:
            try:
                os.remove(HEARTBEAT_MARKER_PATH)
            except OSError:
                pass
        return

    if already_alerted:
        return  # zaten bir kere uyarıldık, log tazelenene kadar tekrar spam yok

    hours = age / 3600
    sent = notify.send(
        "FMS: otomasyon sessiz",
        f"auto_process.log {hours:.1f} saattir güncellenmedi — bilgisayar/"
        "Görev Zamanlayıcı kontrol edilmeli.",
    )
    if sent:
        try:
            open(HEARTBEAT_MARKER_PATH, "w", encoding="utf-8").close()
        except OSError:
            pass
        log(f"UYARI: auto_process.log {hours:.1f} saattir güncellenmedi, telefon bildirimi gönderildi.")
    # sent=False (notify_config.json yok ya da ntfy'ye ulaşılamadı) ise marker
    # yazılmıyor — bir sonraki dakika tekrar denenir.


def main() -> None:
    _TETIKLENENLER.clear()
    try:
        _check_heartbeat()
    except Exception as e:
        log(f"HATA (heartbeat kontrolü): {e}")

    trim_log(LOG_PATH)

    # dj_famous_process.log'u da BURADAN buduyoruz.
    # NEDEN: `dj_famous_process.py` kendi log'unu hiç döndürmüyordu — sızan
    # Instagram token'ı (2026-09-04) 7 günlük sınırı çoktan geçmiş olmasına
    # rağmen hâlâ dosyadaydı. `trim_log()` artık tuttuğu satırları da
    # maskelediği için (bkz. log_rotate.py) bu çağrı hem eski sızıntıyı
    # temizliyor hem de o dosyanın süresiz büyümesini durduruyor.
    # İKİ YAZICI VAR, BİLEREK (yorumun eski hâli "dj_famous_process budamıyor"
    # diyordu; 2026-09-11'de budama oraya da EKLENDİ — `dj_famous_process.py`
    # kilidi aldıktan hemen sonra kendi `trim_log(LOG_PATH)` çağrısını yapıyor.
    # O bayat yorumu okuyan biri aynı gün ikinci bir çağrıyı gereksiz sandı.)
    # İkisi ÇAKIŞMIYOR, çünkü ikisi de aynı kapıdan geçiyor:
    #   * dj tarafı budamayı KİLİDİN İÇİNDE yapıyor — o an başka bir
    #     dj_famous_process koşusu olamaz;
    #   * buradaki çağrı `_is_running` ile koşu sürerken hiç dokunmuyor.
    # `trim_log` dosyayı tümden okuyup yeniden YAZIYOR, yani aynı anda append
    # edilen bir satır kaybolabilirdi; iki kapı da tam bunu engelliyor.
    # İKİSİ DE KALMALI: dj tarafındaki çağrı sızıntının YAZILDIĞI koşuyu
    # (buradaki `_is_running` kapısının kapalı olduğu an) kapsıyor, buradaki
    # çağrı ise dj hattı haftalarca hiç koşmasa bile dosyanın büyümesini ve
    # eski satırların yeniden maskelenmesini dakikada bir garantiliyor.
    if not _is_running("dj_famous_process.py"):
        trim_log(DJ_FAMOUS_LOG_PATH)

    try:
        _scan_dir(PROJECTS_DIR, "auto_process.py")
    except Exception as e:
        log(f"HATA (projects/): {e}")
    try:
        _scan_dir(DJ_SETS_DIR, "dj_famous_process.py")
    except Exception as e:
        log(f"HATA (dj_sets/): {e}")


if __name__ == "__main__":
    main()
