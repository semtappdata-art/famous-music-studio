# -*- coding: utf-8 -*-
"""Görev Zamanlayıcı görevleri için minimal "iz bırakan" sarmalayıcı.

NEDEN VAR (2026-09-11 üretim sağlık denetimi):
`setup_task_scheduler.ps1` üç görevi de `pythonw.exe` ile kuruyor — pencere
açmasın diye, ve bu karar gerekçesiyle birlikte CLAUDE.md'de yazılı. Ama
`pythonw.exe`'de `sys.stdout`/`sys.stderr` **None**'dır ve Görev
Zamanlayıcı'nın stderr'i yönlendireceği bir yer yoktur: bir betik KENDİ log
dosyasını açmadan ÖNCE ölürse (import hatası, sözdizimi hatası, eksik
bağımlılık, DLL yüklenememesi) geriye HİÇBİR iz kalmıyor — ne log satırı, ne
konsol çıktısı. TaskScheduler Operational olay günlüğü de bu makinede KAPALI
(`wevtutil gl Microsoft-Windows-TaskScheduler/Operational` → `enabled: false`),
yani "görev çalıştı mı, ne döndürdü" sorusunun ikinci bir kaynağı da yok.

Somut olay: 2026-09-11'de `auto_process.log`'da 12:12, 13:12 ve 14:12 saatlik
koşuları HİÇ görünmüyor. Yerlerinde 13:32 ve 14:34 damgalı (≈+20/+22 dakika,
`-StartWhenAvailable` kaçırılmış tetik telafisinin imzası) koşular var. Yayın
kaybı olmadı — o saatlerde işlenecek proje yoktu — ama nedeni KANITLANAMADI,
çünkü ölen (ya da hiç başlamayan) bir görev tek bir bayt bile bırakmıyor.
Aynı sınıftan ikinci bir kanıt aynı gün log'da duruyor: 02:12'de "Eski kilit
dosyası bulundu (10732s)" — yani 09-10 23:13 civarı başlayan bir koşu kilidini
bırakmadan ÖLDÜ (muhtemelen görevin `ExecutionTimeLimit`'iyle sonlandırıldı) ve
bu ölüm de hiçbir iz bırakmadı; 00:12 ve 01:12 koşuları o yüzden atlandı.

NE YAPAR (üç satırlık sözleşme):
  1. Sarılan betiğin adını yazan bir **BAŞLADI** damgası atar — HERHANGİ bir
     proje modülü import EDİLMEDEN önce. Bu damga "görev gerçekten tetiklendi"
     sorusunu tek başına cevaplar.
  2. Betiği `runpy` ile çalıştırır; import/sözdizimi hatası dahil HER istisnayı
     yakalayıp tam `traceback`'i aynı dosyaya yazar (**ÇÖKTÜ**).
  3. Çıkışta **BİTTİ** damgası + dönüş kodu + süre yazar. Bu damga,
     BAŞLADI atıldıktan sonraki HER çıkış yolunda yazılır (başarı, çöküş,
     `sys.exit`, betiğin hiç bulunamaması) — aksi hâlde aşağıdaki
     "takıldı/öldü" sınıfı YANLIŞ POZİTİF verir.

Böylece üç arıza biçimi de görünür oluyor:
  * çöktü        → ÇÖKTÜ + traceback
  * takıldı/öldü → BAŞLADI var, eşleşen BİTTİ YOK
  * hiç tetiklenmedi → o saate ait BAŞLADI bile yok (bugün kanıtlanamayan şey)

NEDEN `cmd /c ... 2>>` SARMALAYICISI DEĞİL: `cmd.exe` bir konsol uygulaması ve
görevler `LogonType Interactive` ile kullanıcının oturumunda koşuyor —
`python.exe`'yi terk etmemizin sebebi olan "her tetiklenişte açılıp kapanan
pencere" sorunu (dakikada bir koşan izleyicide dayanılmazdı) aynen geri gelirdi.
Bunu görev KAYDETMEDEN doğrulamanın da bir yolu yok, ve görev kaydetmek bu
düzeltmenin kapsamı dışında. `pythonw.exe` + saf-stdlib bir Python sarmalayıcı
ise pencere açmadığı KESİN (aynı yorumlayıcı, aynı bayrak) ve izole olarak test
edilebiliyor (`tests/test_gorev_sarmalayici.py` — bu dosyanın adı 2026-09-11'e
kadar burada GEÇİYOR ama dİSKTE YOKTU; yazıldı).

NEDEN `sys.excepthook`/en dış `try/except` DEĞİL: o kancayı kurmak için önce
betiğin kendisinin import edilmesi gerekir — kaçırdığımız arıza biçiminin ta
kendisi (import sırasında ölmek) tam olarak o kancadan ÖNCE gerçekleşir.
Sarmalayıcı, import'u KENDİ `try` bloğunun içine aldığı için bu boşluğu kapatır.

BASİT TUTULDU (bugünün dersi: karmaşık bir koruma kendisi sessizce bozulur):
stdlib (`os`, `sys`, `threading`, `time`, `runpy`, `traceback`) + TEK bir
proje modülü (`gizli_maskele`, aşağıya bkz.), tek bir dosyaya append, hiçbir
ağ/işlem çağrısı yok.
Yazma hatalarının HEPSİ yutuluyor — bu sarmalayıcı otomasyonu ASLA durdurmamalı.

MASKELEME (2026-09-12, güvenlik denetimi): iz dosyasına giden ÜÇ yol var ve
ÜÇÜ DE `gizli_maskele.maskele`'den geçiyor:
  1. `_yaz()` — modüldeki TEK yazma noktası (BAŞLADI/BİTTİ/ÇÖKTÜ/CWD/UYARI
     satırlarının hepsi buradan geçiyor),
  2. `traceback.format_exc()` — ayrı bir yol DEĞİL, `_yaz()`'a veriliyor,
  3. yönlendirilmiş `sys.stderr` — `_MaskeliAkis` sarmalayıcısı üzerinden
     (ham dosya nesnesi sys.stderr'e ASLA doğrudan bağlanmıyor).
NEDEN: token taşıyan bir `requests` çağrısı `try/except` ile sarılmamışsa,
`ConnectionError` mesajındaki TAM URL (token sorgu dizesinde) traceback
üzerinden bu dosyaya düşer — 2026-09-04'te `dj_famous_process.log`'a gerçek
bir Instagram token'ının düşmesine yol açan zincirin birebir aynısı. Üstelik
`log_rotate.trim_log()` bu klasöre UĞRAMIYOR (bilerek, bkz. `_buda`), yani
buraya düşen bir sızıntı sonradan TEMİZLENMEZ — maskeleme YAZARKEN olmak
zorunda. Garanti `tests/test_sarmalayici_maskeleme.py` ile kilitli.
`gizli_maskele` import'u KORUMALI: yüklenemezse sarmalayıcı ÇALIŞMAYA DEVAM
eder (maskelenmemiş iz, izsizlikten iyidir) ama bu SESSİZ olmaz — iz
dosyasına koşu başına bir kez "MASKELEYİCİ YÜKLENEMEDİ" satırı düşer.

KULLANIM (Görev Zamanlayıcı bunu `setup_task_scheduler.ps1` üzerinden kurar):
    pythonw.exe gorev_sarmalayici.py auto_process.py [betiğin kendi argümanları]

İZ DOSYASI: `gorev_izleri/<betik adı>.log` (betik başına AYRI dosya — dakikada
bir koşan izleyici, saatte bir koşan ana hattın izlerini boğmasın ve her
dosyanın kendi mtime'ı tek başına anlamlı bir sinyal olsun).
`gorev_izleri/` `.gitignore`'da ZATEN var (74. satır) — bu satır önceden
"eklenmeli" diyordu, yani yanlıştı; CLAUDE.md'nin "yalan söyleyen yorum, hiç
yorum olmamasından kötüdür" kuralına göre düzeltildi (2026-09-12).

ÖLÇÜLMÜŞ `pythonw.exe` DAVRANIŞI (2026-09-12, konsolsuz + std handle'ları NULL
olan gerçek bir süreçte sınandı — Görev Zamanlayıcı'nın kurduğu koşulun
birebir aynısı; `tests/test_gorev_sarmalayici_pythonw.py` aynı senaryoları
otomatik tekrar ediyor):
  * `sys.stdout` GERÇEKTEN `None` oluyor. Ama `print()` bu durumda İSTİSNA
    ATMIYOR: CPython'un `print`'i `sys.stdout is None` ise sessizce hiçbir şey
    yapmadan dönüyor. Yani `auto_process.log()`/`watch_projects.log()`
    içindeki `print(line)` çağrıları bu ortamda ÇÖKMÜYOR (dosyaya yazan ikinci
    yarı çalışmaya devam ediyor). Türkçe karakter + emoji de aynı sebeple
    sorunsuz — hiç kodlanmıyor.
  * ÜÇ betiğin de başındaki `_stream.reconfigure(encoding="utf-8")` döngüsü
    `None` üzerinde `AttributeError` atıyor ve o döngü bunu zaten yakalıyor.
    `sys.stderr` bu sarmalayıcı tarafından bir DOSYAYA bağlandığı için orada
    `reconfigure` gerçekten çalışıyor (dosya zaten UTF-8 açılıyor).
  * `sys.stdin` de `None`. Boru hattında `input()` çağrısı YOK (tarandı) —
    olsaydı `RuntimeError: input(): lost sys.stdin` ile ölürdü.
`sys.stdout` BİLEREK yönlendirilmiyor (aşağıdaki gerekçe) — yani bir gün bir
modül `sys.stdout.write()` derse bu ortamda patlar, ama artık SESSİZ değil:
traceback iz dosyasına düşer.
"""

import os
import runpy
import sys
import threading
import time
import traceback

KOK = os.path.dirname(os.path.abspath(__file__))
IZ_DIZIN = os.path.join(KOK, "gorev_izleri")

# --- MASKELEYİCİ: KORUMALI IMPORT -------------------------------------------
# Sarmalayıcı en ALT katman: kendi başarısızlığı zinciri KIRMAMALI. Bu yüzden
# `gizli_maskele` yüklenemezse (dosya silinmiş, sözdizimi hatası, bozuk kurulum)
# burada ÖLMEK yerine kimliğe eşit bir yedeğe düşülüyor — iz bırakamamak,
# maskelenmemiş iz bırakmaktan DAHA kötü. Ama sessiz kalınmıyor: `calistir()`
# koşu başına BİR kez iz dosyasına "MASKELEYİCİ YÜKLENEMEDİ" satırı yazıyor
# (CLAUDE.md: sessizce bozulan bir koruma, olmayan korumadan kötüdür).
# `sys.path` eklemesi burada ŞART: sarmalayıcı mutlak bir yolla çağrıldığında
# (Görev Zamanlayıcı tam olarak öyle yapıyor) script dizini sys.path[0] olsa da
# `runpy` öncesi bu import'un kökü görmesi garanti olsun diye.
if KOK not in sys.path:
    sys.path.insert(0, KOK)

try:
    from gizli_maskele import maskele as _maskele
    MASKELEYICI_HATASI = ""
except Exception as _hata:          # ImportError, SyntaxError, bozuk dosya...
    MASKELEYICI_HATASI = "%s: %s" % (type(_hata).__name__, _hata)

    def _maskele(metin):            # yedek: kimlik fonksiyonu
        return metin if isinstance(metin, str) else str(metin)

# Dosya başına tutulan en fazla satır. İzleyici (dakikada bir) koşu başına 2
# satır yazıyor → ~2880 satır/gün, yani bu sınır kabaca bir günlük geçmiş
# demek. Budama SADECE başlangıçta ve SADECE sınır aşıldığında yapılıyor:
# oku-hepsini/yaz-hepsini deseni eşzamanlı bir yazıcıyla yarışabilir (bugün
# `auto_process.log`'da tam olarak bu şüpheleniliyor), bu yüzden dosyalar
# betik başına AYRI ve pratikte tek yazıcılı.
MAKS_SATIR = 3000


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _maskeli(metin) -> str:
    """Metni maskeleyiciden geçirir; maskeleyici PATLARSA ham metni döner.

    Aynı gerekçe: bu sarmalayıcının işi iz bırakmak, iz bırakamamak en kötü
    sonuç. `maskele()` saf `re` + `str` işlemleri, pratikte atmıyor — ama
    burada yakalanmazsa `_yaz()` bir istisnayla patlar ve BİTTİ damgası
    yazılmaz, yani koşu üretimde "asılı kalmış" gibi YANLIŞ sınıflandırılır.
    """
    try:
        return _maskele(metin)
    except Exception:
        return metin if isinstance(metin, str) else str(metin)


# Özyineleme kilidi THREAD YERELİ. Neden global bir bayrak DEĞİL: arka plan
# thread'i stderr'e yazarken ana thread kilidi tutuyorsa, o thread'in metni
# MASKELENMEDEN geçerdi — korumanın tam da kapatmak istediği delik.
_akis_yerel = threading.local()


class _MaskeliAkis:
    """Yönlendirilmiş `sys.stderr` — her yazım maskeleyiciden geçer.

    NEDEN SARMALAYICI NESNE, neden düz dosya DEĞİL (2026-09-12): `sys.stderr`
    ham bir dosya nesnesine bağlandığında C-seviyesi uyarılar, thread
    istisnaları, `warnings` çıktısı ve kapanış sırasındaki traceback'ler iz
    dosyasına MASKELENMEDEN düşüyordu. `try/except` ile sarılmamış tek bir
    `requests` çağrısı, mesajında tam istek URL'i (token sorgu dizesinde)
    olan bir `ConnectionError` ile ölmeye yeter.

    ÖZYİNELEME: `maskele()` hiçbir şey YAZMIYOR (saf `re`), yani bugün doğrudan
    bir döngü yok. Ama bir gün maskeleyici bir `warnings.warn` ederse ya da alt
    akışın `write()`'ı patlayıp yorumlayıcı hatayı stderr'e basarsa,
    stderr==bu nesne olduğu için sonsuz döngü olurdu. Thread-yerel bayrak bunu
    kesiyor: yeniden girişte metin maskelenmeden TEK sefer yazılıp dönülüyor
    (kilitlenmek ya da yığını taşırmak, sarmalayıcının ASLA yapmaması gereken
    şey). `tests/test_sarmalayici_maskeleme.py` bu dalı da sınıyor.

    `buffer`/`raw`/`detach` BİLEREK kapalı: ikisi de metin katmanını ATLAYIP
    ham bayt yazmanın yolu olurdu, yani maskeleyicinin etrafından dolaşmak.
    Diğer öznitelikler (`encoding`, `fileno`, `reconfigure`, ...) alt akışa
    devrediliyor — üç üretim betiğinin başındaki `reconfigure(encoding=...)`
    döngüsü bu sayede çalışmaya devam ediyor.
    """

    _KAPALI_OZNITELIKLER = ("buffer", "raw", "detach")

    def __init__(self, akis):
        self._akis = akis

    def write(self, metin) -> int:
        if not isinstance(metin, str):
            metin = str(metin)
        if getattr(_akis_yerel, "icerde", False):
            # Yeniden giriş: maskelemeden, TEK sefer yaz ve dön.
            try:
                self._akis.write(metin)
            except Exception:
                pass
            return len(metin)
        _akis_yerel.icerde = True
        try:
            try:
                self._akis.write(_maskeli(metin))
            except Exception:
                pass
        finally:
            _akis_yerel.icerde = False
        return len(metin)

    def writelines(self, satirlar) -> None:
        # AYRI TANIMLANMAK ZORUNDA: `__getattr__` ile alt akışa devredilseydi
        # maskeleyiciyi ATLARDI (traceback modülü bu yolu kullanabiliyor).
        for satir in satirlar:
            self.write(satir)

    def flush(self) -> None:
        try:
            self._akis.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def __getattr__(self, ad):
        if ad.startswith("_") or ad in _MaskeliAkis._KAPALI_OZNITELIKLER:
            raise AttributeError(ad)
        return getattr(self._akis, ad)


def iz_yolu(betik: str) -> str:
    """Sarılan betiğin adından iz dosyasının yolunu türetir."""
    ad = os.path.basename(betik)
    if ad.lower().endswith(".py"):
        ad = ad[:-3]
    guvenli = "".join(c if (c.isalnum() or c in "-_") else "_" for c in ad)
    return os.path.join(IZ_DIZIN, (guvenli or "gorev") + ".log")


def _yaz(yol: str, metin: str) -> None:
    """İz dosyasına ekler. HİÇBİR hata yukarı sızmaz — iz bırakamamak
    otomasyonu durdurmaktan iyidir.

    Modüldeki TEK yazma noktası ve metin buradan geçerken maskeleniyor:
    BAŞLADI/BİTTİ/CWD satırları zararsız, ama ÇÖKTÜ satırı bir
    `traceback.format_exc()` taşıyor ve orada token'lı bir istek URL'i
    olabilir (bkz. modül docstring'i)."""
    metin = _maskeli(metin)
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "a", encoding="utf-8", errors="replace") as f:
            f.write(metin)
            f.flush()
    except Exception:
        pass


def _buda(yol: str, maks: int = MAKS_SATIR) -> None:
    """İz dosyasını son `maks` satıra indirir — ATOMİK olarak.

    NEDEN `.tmp` + `os.replace` (2026-09-12): eski sürüm hedefi doğrudan
    `open(yol, "w")` ile açıyordu, yani dosyayı ÖNCE sıfırlayıp sonra
    dolduruyordu. Bu makinede süreçler `TerminateProcess` ile ölüyor (pile
    geçiş, `ExecutionTimeLimit`) ve bu budama HER koşunun İLK işi — dakikada
    bir koşan izleyicide günde 1440 kez. O pencerede öldürülmek, tam da
    ölümün kanıtı olacak dosyayı SIFIRLAMAK demekti. `state_io.py` aynı dersi
    `state.json` için zaten öğrenmişti (bkz. CLAUDE.md).
    `os.replace` Windows'ta da atomik. Başarısız olursa (ör. dosya başka bir
    süreçte açık) budama yapılmaz, dosya büyümeye devam eder — veri kaybından
    iyidir.
    """
    gecici = yol + ".tmp"
    try:
        if not os.path.isfile(yol):
            return
        with open(yol, "r", encoding="utf-8", errors="replace") as f:
            satirlar = f.readlines()
        if len(satirlar) <= maks:
            return
        with open(gecici, "w", encoding="utf-8", errors="replace") as f:
            f.writelines(satirlar[-maks:])
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except Exception:
        try:
            if os.path.isfile(gecici):
                os.remove(gecici)
        except Exception:
            pass


def calistir(argv) -> int:
    """argv: [sarmalayici.py, hedef_betik.py, hedefin argümanları...]"""
    if len(argv) < 2:
        # Konsolsuz (pythonw) bağlamda stderr None olabilir; yine de iz bırak.
        _yaz(os.path.join(IZ_DIZIN, "gorev.log"),
             "[%s] KULLANIM HATASI: hedef betik verilmedi\n" % _ts())
        return 2

    betik = argv[1]
    if not os.path.isabs(betik):
        betik = os.path.join(KOK, betik)
    ad = os.path.basename(betik)
    iz = iz_yolu(betik)

    _buda(iz)
    _yaz(iz, "[%s] BAŞLADI %s pid=%s\n" % (_ts(), ad, os.getpid()))

    # Maskeleyici yüklenemediyse bu KOŞU BOYUNCA iz satırları ham yazılacak.
    # Sarmalayıcı yine de çalışıyor (bilinçli karar), ama bunu SESSİZCE
    # yapmıyor: aşağıdaki satır olmadan "iz dosyası maskeli" sanısı
    # doğrulanamaz bir varsayıma dönerdi.
    if MASKELEYICI_HATASI:
        _yaz(iz, "[%s] UYARI %s — MASKELEYİCİ YÜKLENEMEDİ (%s); iz satırları"
                 " MASKELENMEDEN yazılıyor\n" % (_ts(), ad, MASKELEYICI_HATASI))

    # ÇALIŞMA DİZİNİ — `-WorkingDirectory $repoRoot`'a GÜVENİLMİYOR.
    # NEDEN (2026-09-12): boru hattı göreli yollarla çalışıyor (`--base
    # projects`, `dj_sets`, `upload/`). Yanlış bir cwd'de bunlar HATA
    # VERMİYOR, sadece "bulunamadı" oluyor: `find_ready_projects()` boş liste
    # döner, log'a "İşlenecek proje yok" yazılır ve otomasyon HER KOŞUDA
    # başarıyla hiçbir şey yapmaz. Bu, CLAUDE.md'deki `uyumluluk.KOKLER`
    # vakasının birebir aynısı (göreli yol + yanlış cwd = kapı sessizce
    # AÇILIR / kontrol sessizce BOŞ döner). Görev Zamanlayıcı bugün doğru
    # dizini veriyor, ama sarmalayıcının tüm işi "sessiz varsayımları
    # görünür kılmak" — o yüzden hem düzeltiyor hem de fark varsa İZ bırakıyor.
    try:
        onceki_cwd = os.getcwd()
    except OSError:                       # silinmiş bir dizinden başlatılmış olabilir
        onceki_cwd = None
    if onceki_cwd is None or os.path.normcase(os.path.abspath(onceki_cwd)) != os.path.normcase(KOK):
        try:
            os.chdir(KOK)
            _yaz(iz, "[%s] CWD DÜZELTİLDİ %s: %s -> %s\n"
                     % (_ts(), ad, onceki_cwd, KOK))
        except OSError:
            _yaz(iz, "[%s] UYARI %s — cwd %s yapılamadı, göreli yollar bozuk olabilir\n"
                     % (_ts(), ad, KOK))

    # pythonw.exe'de sys.stderr None'dır: bir C-seviyesi uyarı, bir thread
    # istisnası ya da `warnings` çıktısı hiçbir yere gitmez. Aşağıdaki
    # yönlendirme onları da iz dosyasına düşürüyor.
    # sys.stdout'a BİLEREK DOKUNULMUYOR: `auto_process.log()` her satırı
    # ayrıca `print()` ediyor, stdout'u buraya bağlamak tüm üretim log'unu
    # ikinci bir dosyaya kopyalamak olurdu. (Ve ölçüldü: `sys.stdout is None`
    # iken `print()` istisna ATMIYOR, sessizce hiçbir şey yapmıyor — yani
    # dokunmamanın bir bedeli de yok. Bkz. modül docstring'i.)
    # `_MaskeliAkis` ŞART: ham dosya nesnesi doğrudan `sys.stderr`'e
    # bağlanırsa bu yol maskeleyiciyi ATLAR (bkz. sınıfın docstring'i).
    hata_akisi = None
    if sys.stderr is None:
        try:
            hata_akisi = _MaskeliAkis(
                open(iz, "a", encoding="utf-8", errors="replace", buffering=1))
            sys.stderr = hata_akisi
        except Exception:
            hata_akisi = None

    # runpy.run_path düz bir .py dosyası için sys.path'e DOKUNMAZ (yalnızca
    # dizin/zip argümanlarında ekler) — `import config` gibi depo-içi
    # import'ların çalışması için kökü kendimiz eklemeliyiz.
    if KOK not in sys.path:
        sys.path.insert(0, KOK)
    sys.argv = [betik] + list(argv[2:])

    bas = time.time()
    kod = 0
    try:
        # "Betik bulunamadı" kontrolü BİLEREK try/finally'nin İÇİNDE.
        # NEDEN (2026-09-11, ikinci düzeltme): eskiden bu blok try'dan ÖNCEYDİ
        # ve `return 2` ile çıkıyordu — yani ÇÖKTÜ damgası yazılıp EŞLEŞEN
        # BİTTİ damgası HİÇ yazılmıyordu. Modülün kendi sözleşmesine göre
        # ("BAŞLADI var, BİTTİ yok = süreç takıldı/öldürüldü") bir yazım
        # hatası ya da yeniden adlandırılmış bir betik, üretimde ASILI KALMIŞ
        # BİR SÜREÇ gibi YANLIŞ okunurdu. Sarmalayıcının tüm amacı arızayı
        # doğru SINIFLANDIRMAK; yanlış sınıflandıran bir iz, izsizlikten iyi
        # değil. Ayrıca `finally` cwd'yi geri alıyor ve stderr akışını
        # boşaltıyor — eski erken `return` ikisini de atlıyordu.
        if not os.path.isfile(betik):
            kod = 2
            _yaz(iz, "[%s] ÇÖKTÜ %s — betik bulunamadı: %s\n"
                     % (_ts(), ad, betik))
        else:
            runpy.run_path(betik, run_name="__main__")
    except SystemExit as e:
        if e.code is None:
            kod = 0
        elif isinstance(e.code, int):
            kod = e.code
        else:
            kod = 1
            _yaz(iz, "[%s] ÇIKIŞ %s — %s\n" % (_ts(), ad, e.code))
    except BaseException:
        kod = 1
        # traceback `_yaz()` üzerinden gidiyor, yani MASKELİ — token'lı bir
        # istek URL'i taşıyan istisna mesajı bu dosyaya ham düşmez.
        _yaz(iz, "[%s] ÇÖKTÜ %s\n%s" % (_ts(), ad, traceback.format_exc()))
    finally:
        _yaz(iz, "[%s] BİTTİ %s rc=%s süre=%.1fsn\n"
                 % (_ts(), ad, kod, time.time() - bas))
        if hata_akisi is not None:
            try:
                hata_akisi.flush()
            except Exception:
                pass
            # AKIŞ BİLEREK KAPATILMIYOR, `sys.stderr` BİLEREK geri alınmıyor.
            # NEDEN (2026-09-12, ÖLÇÜLDÜ): eski sürüm burada akışı kapatıp
            # `sys.stderr`'i `None`'a geri alıyordu — ama bir betiğin ölümü
            # `calistir()` döndükten SONRA da gerçekleşebiliyor: `atexit`
            # kancası, bir `__del__` sonlandırıcısı, ya da arka plan
            # thread'inin istisnası. Bunlar yorumlayıcı kapanışında
            # `sys.stderr`'e basılıyor; `None`'a geri alınmış bir stderr'de
            # HİÇBİR İZ BIRAKMIYORLAR. Sahte bir betikle sınandı: `atexit`
            # ve `__del__` içinde patlayan bir koşu, `pythonw.exe` altında
            # "BAŞLADI + BİTTİ rc=0" (yani TERTEMİZ) görünüyordu — Görev
            # Zamanlayıcı da `LastTaskResult=0` diyordu. Akış açık kalınca
            # o traceback'ler BİTTİ satırının ALTINA düşüyor.
            # Kapatmamanın maliyeti yok: bu noktadan sonra süreç zaten
            # çıkıyor, akış satır tamponlu (her satır anında diskte) ve
            # işletim sistemi handle'ı süreçle birlikte kapatıyor.
        # cwd geri alınıyor: üretimde süreç birazdan çıkacağı için etkisiz,
        # ama `calistir()` testlerde AYNI süreçte defalarca çağrılıyor —
        # kalıcı bir chdir sonraki testlerin göreli yollarını bozardı.
        if onceki_cwd is not None:
            try:
                os.chdir(onceki_cwd)
            except OSError:
                pass
    return kod


if __name__ == "__main__":
    sys.exit(calistir(sys.argv))
