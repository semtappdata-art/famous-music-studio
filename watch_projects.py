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

from log_rotate import trim_log
import notify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DJ_SETS_DIR = os.path.join(BASE_DIR, "dj_sets")
LOG_PATH = os.path.join(BASE_DIR, "watch_projects.log")
AUTO_PROCESS_LOG_PATH = os.path.join(BASE_DIR, "auto_process.log")
HEARTBEAT_MARKER_PATH = os.path.join(BASE_DIR, ".watchdog_alerted")

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
COVER_NAMES = {"cover.jpg", "cover.jpeg", "cover.png"}
ART_NAMES = {"art.jpg", "art.jpeg", "art.png"}


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
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
        ext = os.path.splitext(name)[1].lower()
        if ext in IMAGE_EXTS and name not in COVER_NAMES and name not in ART_NAMES:
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


def _trigger_script(script_name: str) -> None:
    try:
        subprocess.run([sys.executable, os.path.join(BASE_DIR, script_name)], cwd=BASE_DIR)
    except Exception as e:
        log(f"  {script_name} tetiklenemedi: {e}")


def _scan_dir(base_dir: str, trigger_script: str) -> None:
    """base_dir altındaki her proje klasörünü tarar: sahipsiz görselleri
    cover.*/art.* olarak yerleştirir (audio'dan bağımsız, her turda dener) ve
    sahipsiz bir ses dosyası bulup audio.* adına çevirdiğinde trigger_script'i
    (auto_process.py ya da dj_famous_process.py) tetikler."""
    if not os.path.isdir(base_dir):
        return
    for name in sorted(os.listdir(base_dir)):
        project_dir = os.path.join(base_dir, name)
        if not os.path.isdir(project_dir):
            continue

        _place_stray_images(project_dir)

        if _has_audio(project_dir):
            continue
        stray = _find_stray_audio(project_dir)
        if not stray:
            continue
        if not _is_stable(stray):
            continue  # muhtemelen indirme sürüyor, bir sonraki turda tekrar bakılacak
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
    try:
        _check_heartbeat()
    except Exception as e:
        log(f"HATA (heartbeat kontrolü): {e}")

    trim_log(LOG_PATH)
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
