# -*- coding: utf-8 -*-
"""`gorev_sarmalayici.py`'yi GERÇEK `pythonw.exe` altında sınar.

NEDEN AYRI BİR DOSYA (`tests/test_gorev_sarmalayici.py` varken):
o dosya sarmalayıcıyı TEST SÜRECİNİN İÇİNDE (`GS.calistir(...)`) çağırıyor.
Orada `sys.stdout`/`sys.stderr` GERÇEK akışlar — yani sarmalayıcının var olma
sebebi olan ortam (konsolsuz `pythonw.exe`, std handle'ları NULL) HİÇ test
edilmiyordu. Bu deponun en pahalı arıza sınıfı tam olarak bu: "kendi içinde
doğru ama üretimdeki bağlamda hiç denenmemiş kod" (bkz. CLAUDE.md).

ORTAM NASIL BİREBİR KURULUYOR: Görev Zamanlayıcı görevleri `pythonw.exe` ile,
konsolsuz ve devralınan std handle olmadan başlatılıyor; o koşulda CPython
`sys.stdout`/`sys.stderr`/`sys.stdin`'i **None** yapar. `subprocess` bunu
üretemiyor (STARTF_USESTDHANDLES için geçerli handle istiyor), bu yüzden
`CreateProcessW` doğrudan `ctypes` ile çağrılıp üç handle da NULL veriliyor
(+ DETACHED_PROCESS). Kontrol testi (`test_ortam_gercekten_pythonw_gibi`)
bunun GERÇEKTEN sağlandığını doğruluyor — sağlanmazsa aşağıdaki testlerin
hepsi yanlış bir ortamda "geçer" ve hiçbir şey kanıtlamaz.

İZOLASYON: her koşu `tmp_path` altında kendi kopyasıyla yapılıyor
(sarmalayıcı `gorev_izleri/`i KENDİ konumuna göre türetiyor, yani kopya
üretim iz klasörüne TEK BAYT yazmıyor). Sahte betikler `projects/`,
`dj_sets/`, `state.json` ve ağ ile HİÇ temas etmiyor.
"""

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SARMALAYICI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gorev_sarmalayici.py",
)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="pythonw.exe yalnızca Windows'ta var"
)


def _pythonw():
    yol = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return yol if os.path.isfile(yol) else None


def _konsolsuz_calistir(cmdline, cwd):
    """Konsolu ve std handle'ları OLMAYAN bir süreç başlatır, çıkış kodunu döner."""
    import ctypes
    import ctypes.wintypes as w

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    STARTF_USESTDHANDLES = 0x00000100
    INFINITE = 0xFFFFFFFF

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", w.DWORD), ("lpReserved", w.LPWSTR), ("lpDesktop", w.LPWSTR),
            ("lpTitle", w.LPWSTR), ("dwX", w.DWORD), ("dwY", w.DWORD),
            ("dwXSize", w.DWORD), ("dwYSize", w.DWORD),
            ("dwXCountChars", w.DWORD), ("dwYCountChars", w.DWORD),
            ("dwFillAttribute", w.DWORD), ("dwFlags", w.DWORD),
            ("wShowWindow", w.WORD), ("cbReserved2", w.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", w.HANDLE), ("hStdOutput", w.HANDLE),
            ("hStdError", w.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", w.HANDLE), ("hThread", w.HANDLE),
                    ("dwProcessId", w.DWORD), ("dwThreadId", w.DWORD)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    si.dwFlags = STARTF_USESTDHANDLES
    si.hStdInput = si.hStdOutput = si.hStdError = None
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessW(
        None, ctypes.create_unicode_buffer(cmdline), None, None, False,
        DETACHED_PROCESS | CREATE_NO_WINDOW, None, cwd,
        ctypes.byref(si), ctypes.byref(pi),
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    k32.WaitForSingleObject(pi.hProcess, 120000)
    rc = w.DWORD()
    k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(rc))
    k32.CloseHandle(pi.hProcess)
    k32.CloseHandle(pi.hThread)
    return rc.value


@pytest.fixture
def sahne(tmp_path):
    """Sarmalayıcının tmp altındaki kopyası — iz dosyaları da oraya düşer."""
    pyw = _pythonw()
    if pyw is None:
        pytest.skip("pythonw.exe bulunamadı")
    kok = tmp_path / "kok"
    kok.mkdir()
    shutil.copy2(SARMALAYICI, str(kok / "gorev_sarmalayici.py"))

    class Sahne:
        dizin = str(kok)

        def betik(self, ad, govde):
            (kok / ad).write_text(govde, encoding="utf-8")
            return ad

        def kos(self, *args, cwd=None):
            cmd = '"%s" gorev_sarmalayici.py %s' % (pyw, " ".join(args))
            return _konsolsuz_calistir(cmd, cwd or str(kok))

        def iz(self, ad):
            y = kok / "gorev_izleri" / (ad.replace(".py", "") + ".log")
            assert y.is_file(), "iz dosyası hiç oluşmadı: %s" % y
            ham = y.read_bytes()
            ham.decode("utf-8")      # iz dosyası HER ZAMAN geçerli UTF-8 olmalı
            return ham.decode("utf-8")

    return Sahne()


# --- Kontrol testi: ortam gerçekten pythonw gibi mi? ------------------------

def test_ortam_gercekten_pythonw_gibi(sahne):
    """Bu geçmezse aşağıdaki testlerin hiçbiri bir şey KANITLAMAZ.

    Aranan şey `sys.stdout is None` — sarmalayıcının tüm gerekçesi bu.
    """
    sahne.betik(
        "sonda.py",
        "import sys\n"
        "open('rapor.txt','w',encoding='utf-8').write(\n"
        "    'stdout=%s stdin=%s' % (sys.stdout is None, sys.stdin is None))\n",
    )
    assert sahne.kos("sonda.py") == 0
    rapor = (open(os.path.join(sahne.dizin, "rapor.txt"), encoding="utf-8").read())
    assert rapor == "stdout=True stdin=True", rapor


# --- (a) normal biten betik --------------------------------------------------

def test_normal_biten_betik(sahne):
    sahne.betik("duz.py", "open('ok.txt','w').write('x')\n")
    assert sahne.kos("duz.py") == 0
    m = sahne.iz("duz")
    assert "BAŞLADI duz.py" in m
    assert "BİTTİ duz.py rc=0" in m
    assert "ÇÖKTÜ" not in m
    assert os.path.isfile(os.path.join(sahne.dizin, "ok.txt"))


# --- (b) import hatasıyla ölen betik ----------------------------------------

def test_import_hatasi_traceback_birakir(sahne):
    """Sarmalayıcının VAR OLMA sebebi: betik kendi log'unu AÇMADAN ölüyor."""
    sahne.betik("cokuk.py", "import bu_modul_kesinlikle_yok_98765\n")
    assert sahne.kos("cokuk.py") == 1
    m = sahne.iz("cokuk")
    assert "BAŞLADI cokuk.py" in m
    assert "Traceback (most recent call last)" in m
    assert "bu_modul_kesinlikle_yok_98765" in m
    assert "BİTTİ cokuk.py rc=1" in m


# --- (c) Türkçe karakter + emoji --------------------------------------------

def test_turkce_ve_emoji_print_patlatmiyor(sahne):
    """Depoda gerçekleşmiş bir arıza sınıfı: `UnicodeEncodeError` ile ölen print.

    Üç betiğin de `log()`'u her satırı ayrıca `print()` ediyor ve caption'lar
    emoji taşıyor (bkz. `upload/tiktok_publish_plan.py`'nin `cp1254` arızası).
    `pythonw.exe`'de `sys.stdout` None olduğu için `print()` sessiz bir
    no-op'a dönüyor — bu testin kilitlediği davranış BU: betik print'ten
    SONRA da yaşıyor olmalı. Ayrıca betiğin `stderr`'e ve `warnings`'e
    yazdığı Türkçe/emoji, iz dosyasına BOZULMADAN düşmeli.
    """
    sahne.betik(
        "turkce.py",
        "import sys, warnings\n"
        "for _s in (sys.stdout, sys.stderr):\n"          # üç üretim betiğinin başlığı
        "    try:\n"
        "        _s.reconfigure(encoding='utf-8', errors='replace')\n"
        "    except (AttributeError, ValueError):\n"
        "        pass\n"
        "print('Türkçe ışık ĞÜŞİÖÇ 🎵')\n"
        "sys.stderr.write('stderr Türkçe: ışıklı şğüİ 🎵\\n')\n"
        "warnings.warn('uyarı: ışıklı 🎵')\n"
        "open('yasiyorum.txt','w',encoding='utf-8').write('print sonrası hayattayım')\n",
    )
    assert sahne.kos("turkce.py") == 0
    yasiyor = os.path.join(sahne.dizin, "yasiyorum.txt")
    assert os.path.isfile(yasiyor), "print() çağrısı betiği öldürdü"
    m = sahne.iz("turkce")
    assert "BİTTİ turkce.py rc=0" in m
    # stderr yönlendirmesi: Türkçe ve emoji iz dosyasına BOZULMADAN düşüyor.
    assert "stderr Türkçe: ışıklı şğüİ 🎵" in m
    assert "uyarı: ışıklı 🎵" in m


# --- (d) sıfırdan farklı çıkış kodu -----------------------------------------

def test_sifirdan_farkli_cikis_kodu_yayiliyor(sahne):
    """Görev Zamanlayıcı'nın `LastTaskResult`'ı SADECE buradan besleniyor —
    sarmalayıcı hep 0 dönerse gerçek arızalar arayüzde 'başarılı' görünür."""
    sahne.betik("cikis.py", "import sys\nsys.exit(5)\n")
    assert sahne.kos("cikis.py") == 5
    assert "BİTTİ cikis.py rc=5" in sahne.iz("cikis")


# --- Kapanış sırasındaki ölümler (atexit / __del__) -------------------------

def test_kapanis_sirasindaki_hata_da_iz_birakiyor(sahne):
    """2026-09-12'de ölçülerek bulunan boşluğun koruma testi.

    Eski sürüm `finally` içinde stderr akışını KAPATIP `sys.stderr`'i None'a
    geri alıyordu. Ama bir betiğin ölümü `calistir()` döndükten SONRA da
    olabiliyor: `atexit` kancası, `__del__` sonlandırıcısı, arka plan
    thread'i. Bunlar kapanışta `sys.stderr`'e basılıyor ve None'a geri
    alınmış bir stderr'de HİÇBİR İZ bırakmıyorlardı — koşu "BAŞLADI + BİTTİ
    rc=0", yani tertemiz görünüyordu.
    """
    sahne.betik(
        "kapanis.py",
        "import atexit\n"
        "def _patlat():\n"
        "    raise RuntimeError('atexit içinde patladım 💥')\n"
        "atexit.register(_patlat)\n",
    )
    sahne.kos("kapanis.py")
    m = sahne.iz("kapanis")
    assert "BAŞLADI kapanis.py" in m
    assert "BİTTİ kapanis.py" in m
    assert "atexit içinde patladım" in m, (
        "kapanış sırasındaki istisna iz bırakmadı — sessiz ölüm geri geldi:\n%s" % m
    )


# --- Çalışma dizini ---------------------------------------------------------

def test_yanlis_cwd_duzeltiliyor(sahne, tmp_path):
    """Görev `-WorkingDirectory` veriyor, ama sarmalayıcı buna GÜVENMEMELİ.

    Yanlış bir cwd'de boru hattının göreli yolları (`projects/`, `dj_sets/`)
    HATA VERMEZ, sadece boş döner: otomasyon her koşuda "İşlenecek proje yok"
    deyip sessizce hiçbir şey yapmaz — CLAUDE.md'deki `uyumluluk.KOKLER`
    vakasının aynısı.
    """
    baska = tmp_path / "baska_dizin"
    baska.mkdir()
    sahne.betik(
        "cwd.py",
        "import os\n"
        "open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cwd.txt'),\n"
        "     'w', encoding='utf-8').write(os.getcwd())\n",
    )
    # Betik MUTLAK yolla veriliyor: cwd yanlışken sarmalayıcının kendisi de
    # göreli yoldan bulunamazdı (o durumda hiç iz kalmaz, bkz. rapor).
    rc = _konsolsuz_calistir(
        '"%s" "%s" "%s"' % (_pythonw(),
                            os.path.join(sahne.dizin, "gorev_sarmalayici.py"),
                            os.path.join(sahne.dizin, "cwd.py")),
        str(baska),
    )
    assert rc == 0
    gorulen = open(os.path.join(sahne.dizin, "cwd.txt"), encoding="utf-8").read()
    assert os.path.normcase(gorulen) == os.path.normcase(sahne.dizin), (
        "sarılan betik YANLIŞ dizinde koştu: %s" % gorulen
    )
    assert "CWD DÜZELTİLDİ" in sahne.iz("cwd")


# --- Argüman geçişi ---------------------------------------------------------

def test_argumanlar_geciriliyor(sahne):
    sahne.betik(
        "argvli.py",
        "import sys\n"
        "open('argv.txt','w',encoding='utf-8').write('|'.join(sys.argv[1:]))\n",
    )
    assert sahne.kos("argvli.py", "--count", "2", "--no-schedule") == 0
    assert (open(os.path.join(sahne.dizin, "argv.txt"), encoding="utf-8").read()
            == "--count|2|--no-schedule")


# --- Budama: iz dosyası sonsuza kadar büyümüyor ------------------------------

def test_iz_dosyasi_budaniyor_ve_atomik(sahne):
    """`watch_projects.py` DAKİKADA BİR koşuyor (koşu başına ~2 satır), yani
    budama olmadan iz dosyası sınırsız büyürdü. Budama `.tmp` + `os.replace`
    ile atomik: yarıda öldürülen bir koşu (pile geçiş / ExecutionTimeLimit)
    dosyayı SIFIRLAMAMALI."""
    import gorev_sarmalayici as GS

    iz = os.path.join(sahne.dizin, "gorev_izleri", "buyuk.log")
    os.makedirs(os.path.dirname(iz), exist_ok=True)
    with open(iz, "w", encoding="utf-8") as f:
        f.writelines("satır %d ışık\n" % i for i in range(5000))

    GS._buda(iz, maks=100)

    satirlar = open(iz, encoding="utf-8").read().splitlines()
    assert len(satirlar) == 100
    assert satirlar[0] == "satır 4900 ışık"
    assert satirlar[-1] == "satır 4999 ışık"
    assert not os.path.isfile(iz + ".tmp"), "geçici dosya ortada bırakılmış"
