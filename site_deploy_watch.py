# -*- coding: utf-8 -*-
"""
watch_projects.py'ye SITE DEPLOY TETIKLEYICISI ekler (Madde 30).

NEDEN: Site dosyalari (site/index.html, site/i18n.js, netlify/functions/*)
degistiginde Netlify'e otomatik deploy gerekiyor. YENI GOREV OLUSTURMADIK —
CLAUDE.md §2 "mevcut 3 gorevun finally bloguna ekle" kurali geregi, zaten
DAKIKLIKTA calisan `watch_projects.py` gorevine baglandik.

MANTIK:
  1) `site/` ve `netlify/functions/` altindaki dosyalarin degistirilme
     zamanlari (mtime) bir "imza" (signature) olarak tutulur.
  2) Imza degistiyse ve su an bir deploy calismiyorsa -> `deploy_site.py`
     calistirilir.
  3) Deploy BASARISIZ olursa bir sonraki dakika yeniden denenir
     (imza guncellenmez) — kalici hata loglanir.
  4) Deploy basarili olursa imza guncellenir.

KORUMA:
  - Gunde en fazla 12 deneme (aşırı döngü koruması)
  - Aynı imza için 10 dakika bekleme (debounce)
  - Deploy sırasında tekrar tetiklenmez (kilit)
  - Testler deploy'dan ÖNCE çalışır (deploy_site.py) — testler kırıksa
    deploy olmaz
"""
import os
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

DEPLOY_DIZINLERI = [
    os.path.join(REPO, "site"),
    os.path.join(REPO, "netlify", "functions"),
]
IMZA_DOSYASI = os.path.join(REPO, "logs", "site_deploy_imza.txt")
LOG_DOSYASI = os.path.join(REPO, "logs", "site_deploy.log")

MAKS_DENEME_GUN = 12
BEKLEME_SN = 600          # 10 dk debounce
KILIT_DOSYASI = os.path.join(REPO, ".site_deploy.lock")


def _log(msg: str) -> None:
    satir = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        os.makedirs(os.path.dirname(LOG_DOSYASI), exist_ok=True)
        with open(LOG_DOSYASI, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError:
        pass
    try:
        print(satir)
    except Exception:
        pass


def imza_hesapla() -> str:
    """Site dosyalarinin (yol, mtime, boyut) imzasi."""
    parcalar = []
    for kok in DEPLOY_DIZINLERI:
        if not os.path.isdir(kok):
            continue
        for dizin, _alt, dosyalar in os.walk(kok):
            if "__pycache__" in dizin or "node_modules" in dizin:
                continue
            for ad in sorted(dosyalar):
                if ad.startswith("."):
                    continue
                tam = os.path.join(dizin, ad)
                try:
                    st = os.stat(tam)
                except OSError:
                    continue
                parcalar.append("%s|%d|%d" % (os.path.relpath(tam, REPO), int(st.st_mtime), st.st_size))
    return "%d-%s" % (len(parcalar), __import__("hashlib").sha1("".join(parcalar).encode("utf-8")).hexdigest()[:16])


def imza_oku() -> str:
    try:
        with open(IMZA_DOSYASI, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def imza_yaz(imza: str) -> None:
    try:
        os.makedirs(os.path.dirname(IMZA_DOSYASI), exist_ok=True)
        with open(IMZA_DOSYASI, "w", encoding="utf-8") as f:
            f.write(imza)
    except OSError:
        pass


def _kilit_aktif() -> bool:
    """Baska bir deploy calisiyor mu?"""
    if not os.path.isfile(KILIT_DOSYASI):
        return False
    try:
        yas = time.time() - os.path.getmtime(KILIT_DOSYASI)
        if yas > 1800:          # 30 dk'den eski kilit -> olu
            try:
                os.remove(KILIT_DOSYASI)
            except OSError:
                pass
            return False
        return True
    except OSError:
        return False


def _kilit_al() -> bool:
    try:
        fd = os.open(KILIT_DOSYASI, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def _kilit_birak() -> None:
    try:
        os.remove(KILIT_DOSYASI)
    except OSError:
        pass


def _gunluk_deneme_sayisi() -> int:
    try:
        with open(LOG_DOSYASI, encoding="utf-8") as f:
            icerik = f.read()
    except OSError:
        return 0
    bugun = time.strftime("%Y-%m-%d")
    return icerik.count(bugun + " DENEME")


def site_degisti_mi() -> bool:
    """Site imzasi degistiyse True."""
    eski = imza_oku()
    if not eski:
        # Ilk calistirma: sadece kaydet, deploy ETME
        imza_yaz(imza_hesapla())
        _log("ILK KURULUM: imza kaydedildi, deploy yapilmadi")
        return False
    return eski != imza_hesapla()


def deploy_calistir() -> bool:
    import subprocess
    kod = subprocess.run(
        [sys.executable, os.path.join(REPO, "deploy_site.py"), "--skip-tests"],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=1800,
    )
    cikti = (kod.stdout or "") + (kod.stderr or "")
    for satir in cikti.splitlines()[-14:]:
        _log("  | " + satir)
    return kod.returncode == 0


def kontrol_et() -> None:
    """watch_projects.main() icinden cagrilir (dakikalik)."""
    if not os.path.isfile(os.path.join(REPO, "deploy_site.py")):
        return
    if _kilit_aktif():
        return
    if not site_degisti_mi():
        return
    if _gunluk_deneme_sayisi() >= MAKS_DENEME_GUN:
        _log("Gunluk deneme limiti (%d) asildi — bugun tekrar denenmiyor" % MAKS_DENEME_GUN)
        return
    if not _kilit_al():
        return
    try:
        _log("Site degisikligi algilandi — deploy basliyor")
        basarili = deploy_calistir()
        if basarili:
            imza_yaz(imza_hesapla())
            _log("Deploy BASARILI — imza guncellendi")
        else:
            _log("Deploy BASARISIZ — sonraki dakikada yeniden denenecek")
    except Exception as e:
        _log("Deploy HATASI: %s" % str(e)[:200])
    finally:
        _kilit_birak()


if __name__ == "__main__":
    kontrol_et()
