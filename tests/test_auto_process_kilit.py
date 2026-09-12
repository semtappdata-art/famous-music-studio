"""auto_process.py'nin kilit mekanizması için testler.

NEDEN VAR (güvenlik denetimi, 2026-09-11) — iki ayrı kusur vardı:

1. KİLİT ALMA ATOMİK DEĞİLDİ (TOCTOU): `os.path.isfile()` ile bakılıp ayrı bir
   `open(..., "w")` ile yaratılıyordu. İki süreç aynı anda "kilit yok" görüp
   ikisi de devam edebilirdi. Pencere teorik değil: watch_projects.py bu
   script'i DAKİKADA BİR, Görev Zamanlayıcı ayrıca saatlik tetikliyor.

2. KİLİT NABZI YOKTU: kilidin mtime'ı koşu boyunca hiç tazelenmiyordu, yani
   LOCK_STALE_SECONDS'tan (o zaman 2 saat) uzun süren bir koşu KENDİ kilidini
   bayat gösteriyordu — bir sonraki tetik aynı projeyi paralel yüklemeye
   başlıyordu, yani kilidin var olma gerekçesinin tam tersi. (Gerçek ölçüm:
   tek bir derleme render'ı 74 dakika, üstüne 266 MB'lık YouTube yüklemesi.)

Testler iki "süreci", modülü İKİ KEZ bağımsız yükleyerek taklit ediyor —
`_KILIT_BIZDE` modül düzeyinde bir global olduğu için her yükleme kendi
bayrağını taşıyor, tıpkı ayrı süreçlerde olacağı gibi.
"""

import importlib.util
import os
import sys
import threading
import time

import pytest

_MODUL_YOLU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_process.py"
)


def _surec(tmp_path, ad):
    """auto_process.py'nin BAĞIMSIZ bir kopyasını yükler (= ayrı bir süreç).

    LOCK_PATH/LOG_PATH tmp_path'e çekiliyor — testler ne gerçek kilide ne de
    gerçek auto_process.log'a dokunmalı (bu makinede canlı bir yayın sürüyor
    olabilir)."""
    spec = importlib.util.spec_from_file_location(ad, _MODUL_YOLU)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(ad, None)
    mod.LOCK_PATH = str(tmp_path / "test.lock")
    mod.LOG_PATH = str(tmp_path / "test.log")
    return mod


@pytest.fixture
def iki_surec(tmp_path):
    a = _surec(tmp_path, "_ap_kilit_a")
    b = _surec(tmp_path, "_ap_kilit_b")
    yield a, b
    for mod in (a, b):
        try:
            mod._release_lock()
        except OSError:
            pass


# --- KUSUR 1: atomiklik -----------------------------------------------------

def test_ikinci_surec_kilidi_alamaz(iki_surec):
    a, b = iki_surec
    assert a._acquire_lock() is True
    assert b._acquire_lock() is False, "iki süreç birden kilidi aldı — çift yükleme riski"
    assert a._KILIT_BIZDE is True
    assert b._KILIT_BIZDE is False


def test_esanli_yaris_tek_kazanan(tmp_path):
    """Asıl kanıt: N 'süreç' AYNI ANDA kilit almaya çalışsın, tam biri kazansın.

    Eski (isfile + open) sürüm burada birden fazla kazanan üretebiliyordu;
    O_CREAT|O_EXCL atomik olduğu için kazanan her zaman tektir."""
    n = 8
    surecler = [_surec(tmp_path, f"_ap_yaris_{i}") for i in range(n)]
    kapi = threading.Barrier(n)
    sonuclar = []
    kilit = threading.Lock()

    def dene(mod):
        kapi.wait()              # hepsi tam aynı anda saldırsın
        alindi = mod._acquire_lock()
        with kilit:
            sonuclar.append(alindi)

    isler = [threading.Thread(target=dene, args=(m,)) for m in surecler]
    for t in isler:
        t.start()
    for t in isler:
        t.join()

    assert sonuclar.count(True) == 1, f"{sonuclar.count(True)} süreç birden kilidi aldı"
    assert len(sonuclar) == n
    assert sum(1 for m in surecler if m._KILIT_BIZDE) == 1
    for m in surecler:
        if m._KILIT_BIZDE:
            m._release_lock()


def test_bayat_kilit_devralinir(iki_surec):
    a, b = iki_surec
    assert a._acquire_lock() is True
    # Kilidi eşiğin ÖTESİNE yaşlandır — sahibi öldü sayılır.
    eski = time.time() - (a.LOCK_STALE_SECONDS + 60)
    os.utime(a.LOCK_PATH, (eski, eski))
    assert b._acquire_lock() is True
    assert b._KILIT_BIZDE is True


def test_taze_kilit_devralinmaz(iki_surec):
    a, b = iki_surec
    assert a._acquire_lock() is True
    yeni = time.time() - (a.LOCK_STALE_SECONDS - 60)   # eşiğin BERİSİNDE
    os.utime(a.LOCK_PATH, (yeni, yeni))
    assert b._acquire_lock() is False


# --- KUSUR 2: nabız ---------------------------------------------------------

def test_log_kilit_mtimeini_ilerletir(iki_surec):
    """Nabız GERÇEKTEN çalışıyor mu: log() sonrası mtime ilerlemiş olmalı."""
    a, _ = iki_surec
    assert a._acquire_lock() is True
    geri = time.time() - 3600
    os.utime(a.LOCK_PATH, (geri, geri))
    onceki = os.path.getmtime(a.LOCK_PATH)

    a.log("bir adım tamamlandı")

    sonraki = os.path.getmtime(a.LOCK_PATH)
    assert sonraki > onceki + 3000, "log() kilidin mtime'ını tazelemedi (nabız yok)"


def test_uzun_kosu_kendi_kilidini_bayatlatmaz(iki_surec):
    """Bugünkü gerçek senaryo: koşu eşikten uzun sürüyor ama log basıyor.

    Nabız olmasaydı ikinci tetik kilidi devralır, aynı projeyi paralel
    yüklerdi."""
    a, b = iki_surec
    assert a._acquire_lock() is True
    geri = time.time() - (a.LOCK_STALE_SECONDS + 600)
    os.utime(a.LOCK_PATH, (geri, geri))

    a.log("  render tamamlandı, YouTube yüklemesine geçiliyor")   # nabız

    assert b._acquire_lock() is False, "nabza rağmen kilit bayat sayıldı"


def test_kaybeden_surec_rakibin_kilidini_tazelemez(iki_surec):
    """_KILIT_BIZDE bayrağının varlık sebebi.

    Kaybeden süreç de log() çağırıyor ('başka bir çalışma sürüyor' satırı).
    Bayrak olmasaydı RAKİBİN kilidini tazeler, gerçekten ölmüş bir sahibin
    kilidi hiç eskimez, hat kalıcı olarak tıkanırdı."""
    a, b = iki_surec
    assert a._acquire_lock() is True
    geri = time.time() - 3600
    os.utime(a.LOCK_PATH, (geri, geri))
    onceki = os.path.getmtime(a.LOCK_PATH)

    assert b._acquire_lock() is False
    b.log("Başka bir auto_process.py çalışması zaten sürüyor")

    assert os.path.getmtime(a.LOCK_PATH) == pytest.approx(onceki, abs=1)


def test_release_sonrasi_log_kilidi_yeniden_yaratmaz(iki_surec):
    a, _ = iki_surec
    assert a._acquire_lock() is True
    a._release_lock()
    assert a._KILIT_BIZDE is False
    a.log("çalıştırma tamamlandı")
    assert not os.path.isfile(a.LOCK_PATH)


def test_kilitsiz_log_patlamaz(iki_surec):
    """Kilit hiç alınmadan da log() çağrılıyor (trim_log/auto_pull öncesi)."""
    a, _ = iki_surec
    a.log("kilitten önceki satır")
    assert os.path.isfile(a.LOG_PATH)


# --- EK İŞ: log() üzerinden merkezi maskeleme -------------------------------

def test_log_token_maskeler(iki_surec):
    """~20 `log(f"... HATA: {e}")` çağrısının hepsi tek noktadan korunuyor.

    Gerçek olay: bir ConnectionError'ın mesajı tam istek URL'sini içeriyordu,
    token sorgu dizesinde diske düştü."""
    a, _ = iki_surec
    hata = Exception(
        "HTTPSConnectionPool: /v1/me?access_token=EAAGm0PX4ZCpsBO7sahteToken123&fields=id"
    )
    a.log(f"  Instagram HATA: {hata}")

    with open(a.LOG_PATH, "r", encoding="utf-8") as f:
        icerik = f.read()
    assert "EAAGm0PX4ZCpsBO7sahteToken123" not in icerik
    assert "MASKEL" in icerik
    assert "Instagram HATA" in icerik      # satır hâlâ tanılanabilir olmalı


def test_log_normal_satiri_bozmaz(iki_surec):
    a, _ = iki_surec
    a.log("3 bekleyen proje var, bu koşuda işlenecek (1): gece_surusu")
    with open(a.LOG_PATH, "r", encoding="utf-8") as f:
        assert "gece_surusu" in f.read()
