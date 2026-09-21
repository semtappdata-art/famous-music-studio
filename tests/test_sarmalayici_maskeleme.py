# -*- coding: utf-8 -*-
"""`gorev_sarmalayici.py`'nin iz dosyasına giden ÜÇ yolunun da MASKELİ
olduğunu kanıtlar.

NEDEN VAR (2026-09-12 güvenlik denetimi): sarmalayıcı, üç Görev Zamanlayıcı
görevinin de giriş noktası olacak ve ÜÇÜNCÜ bir log ailesi yazıyor
(`gorev_izleri/*.log`). Yazıldığı gün `gizli_maskele`'yi hiç import
etmiyordu — yani:

  * `_yaz()` ham yazıyordu,
  * `sys.stderr` doğrudan iz dosyasına bağlanıyordu,
  * `traceback.format_exc()` ham düşüyordu,

ve `log_rotate.trim_log()` o klasöre UĞRAMIYOR, yani sonradan da
temizlenmiyordu. Gerekli tek şey, `try/except` ile sarılmamış bir `requests`
çağrısı ve bir ağ kesintisiydi: `ConnectionError` mesajı TAM istek URL'ini
(token sorgu dizesinde) taşır. 2026-09-04'te `dj_famous_process.log`'a gerçek
bir Instagram token'ının düşmesine yol açan zincirin birebir aynısı.

CLAUDE.md kuralı: "Bir yorum bir GARANTİ ifade ediyorsa, o garantiyi
doğrulayan bir test olmadan yazma." Sarmalayıcının docstring'i artık
"iz dosyasına giden ÜÇ yol da maskeleyiciden geçiyor" diyor; bu dosya o
cümlenin bedelini ödüyor.

KAPSAM:
  1. `_yaz()` (BAŞLADI/BİTTİ/ÇÖKTÜ/UYARI satırlarının hepsi buradan geçer)
  2. yönlendirilmiş `sys.stderr` (`_MaskeliAkis`)
  3. `traceback` yazımı (uçtan uca: gerçekten çöken bir betikle)
  + korumalı import (maskeleyici yoksa sarmalayıcı ÇALIŞMAYA DEVAM eder ama
    SESSİZ kalmaz) ve özyineleme kilidi.

TÜM TOKEN DEĞERLERİ SAHTEDİR — açıkça "SAHTE" yazan uydurma dizeler.
İZOLASYON: `IZ_DIZIN` her testte `tmp_path`'e çekiliyor; sahte betikler
`projects/`, `dj_sets/`, `derlemeler/`, `state.json` ve ağ ile HİÇ temas
etmiyor.
"""

import importlib.util
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gizli_maskele
import gorev_sarmalayici as GS

SARMALAYICI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gorev_sarmalayici.py",
)
MASKELEYICI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gizli_maskele.py",
)

# Hepsi UYDURMA. Gerçek bir kimlik bilgisi bu dosyaya ASLA yazılmaz.
SAHTE_IG = "IGQWRSAHTE1234567890abcdefGHIJKLMNOP"
SAHTE_URL = ("https://graph.instagram.com/v21.0/me?fields=id"
             "&access_token=" + SAHTE_IG)
MASKE = gizli_maskele.MASKE


@pytest.fixture
def izler(tmp_path, monkeypatch):
    """İz klasörünü tmp'ye çeker ve süreç durumunu geri yükler.

    (`tests/test_gorev_sarmalayici.py` ile AYNI desen — `calistir()` sarılan
    betik için `sys.argv`/`sys.path`'i değiştiriyor.)
    """
    d = tmp_path / "izler"
    monkeypatch.setattr(GS, "IZ_DIZIN", str(d))
    eski_argv = list(sys.argv)
    eski_path = list(sys.path)
    yield d
    sys.argv[:] = eski_argv
    sys.path[:] = eski_path


def _betik_yaz(tmp_path, ad, govde):
    y = tmp_path / ad
    y.write_text(govde, encoding="utf-8")
    return str(y)


def _iz_metni(izler, ad):
    y = izler / (ad.replace(".py", "") + ".log")
    assert y.is_file(), "iz dosyası hiç oluşmadı: %s" % y
    return y.read_text(encoding="utf-8")


class _SahteAkis:
    """`_MaskeliAkis`'in alt akışı — diske hiç dokunmadan ne yazıldığını tutar."""

    buffer = "HAM BAYT KATMANI"          # maskeleyiciyi atlatma girişimi için

    def __init__(self):
        self.parcalar = []

    def write(self, metin):
        self.parcalar.append(metin)
        return len(metin)

    def flush(self):
        pass

    @property
    def metin(self):
        return "".join(self.parcalar)


# --- 1) `_yaz()` yolu -------------------------------------------------------

def test_yaz_token_maskeliyor(tmp_path):
    yol = str(tmp_path / "izler" / "deneme.log")
    GS._yaz(yol, "[2026-09-12 10:00:00] HATA " + SAHTE_URL + "\n")

    metin = open(yol, encoding="utf-8").read()
    assert SAHTE_IG not in metin, "SIZINTI (_yaz ham yazdı): %r" % metin
    assert MASKE in metin
    assert "graph.instagram.com" in metin      # teşhis bilgisi KAYBOLMUYOR


def test_normal_satirlar_bozulmuyor(tmp_path):
    """Maskeleme, iz dosyasının ASIL işini (BAŞLADI/BİTTİ damgaları) bozmamalı."""
    yol = str(tmp_path / "izler" / "duz.log")
    GS._yaz(yol, "[2026-09-12 10:00:00] BAŞLADI auto_process.py pid=1234\n")
    GS._yaz(yol, "[2026-09-12 10:00:05] BİTTİ auto_process.py rc=0 süre=5.0sn\n")

    metin = open(yol, encoding="utf-8").read()
    assert "BAŞLADI auto_process.py pid=1234" in metin
    assert "BİTTİ auto_process.py rc=0 süre=5.0sn" in metin
    assert MASKE not in metin                  # yanlış pozitif yok


# --- 2) traceback yolu (uçtan uca, gerçekten çöken betik) -------------------

def test_coken_betigin_tracebacki_maskeli(tmp_path, izler):
    """Denetimin ASIL senaryosu: `try/except` ile sarılmamış bir ağ çağrısı.

    `requests` gerçek bir `ConnectionError`'ın mesajına TAM istek URL'ini
    koyar; token sorgu dizesinde olduğu için traceback token taşır.
    """
    betik = _betik_yaz(tmp_path, "aglayan.py", (
        "raise RuntimeError("
        "'HTTPSConnectionPool(host=graph.instagram.com, port=443): "
        "Max retries exceeded with url: " + SAHTE_URL + "')\n"
    ))

    assert GS.calistir(["gorev_sarmalayici.py", betik]) == 1

    metin = _iz_metni(izler, "aglayan")
    assert "ÇÖKTÜ aglayan.py" in metin
    assert "Traceback (most recent call last)" in metin
    assert SAHTE_IG not in metin, "SIZINTI (traceback ham yazıldı):\n%s" % metin
    assert MASKE in metin
    assert "BİTTİ aglayan.py rc=1" in metin    # sözleşme KIRILMADI


# --- 3) yönlendirilmiş `sys.stderr` yolu -----------------------------------

def test_yonlendirilen_stderr_maskeli(tmp_path, izler, monkeypatch):
    """`pythonw.exe` ortamının birebir koşulu: `sys.stderr is None`.

    Sarmalayıcı stderr'i iz dosyasına bağlıyor; ham bir dosya nesnesi
    bağlansaydı bu yol maskeleyiciyi ATLARDI.
    """
    monkeypatch.setattr(sys, "stderr", None)
    betik = _betik_yaz(tmp_path, "stderrli.py", (
        "import sys\n"
        "print('Instagram HATA: " + SAHTE_URL + "', file=sys.stderr)\n"
    ))

    try:
        assert GS.calistir(["gorev_sarmalayici.py", betik]) == 0
    finally:
        akis = sys.stderr
        if akis is not None and hasattr(akis, "close"):
            try:
                akis.close()       # sarmalayıcı BİLEREK kapatmıyor (bkz. finally)
            except Exception:
                pass

    metin = _iz_metni(izler, "stderrli")
    assert SAHTE_IG not in metin, "SIZINTI (stderr ham bağlandı):\n%s" % metin
    assert MASKE in metin
    assert "Instagram HATA" in metin           # satırın kendisi duruyor


def test_maskeli_akis_yazim_yollarinin_hepsini_kapsiyor():
    alt = _SahteAkis()
    akis = GS._MaskeliAkis(alt)

    akis.write("bir: " + SAHTE_URL)
    akis.writelines(["iki: " + SAHTE_URL, " üç: " + SAHTE_URL])

    assert SAHTE_IG not in alt.metin, "SIZINTI: %r" % alt.metin
    assert alt.metin.count(MASKE) >= 3


def test_maskeli_akis_ham_bayt_katmanini_kapatiyor():
    """`buffer`/`raw`/`detach` maskeleyicinin ETRAFINDAN dolaşmanın yoludur."""
    akis = GS._MaskeliAkis(_SahteAkis())
    for ad in ("buffer", "raw", "detach"):
        with pytest.raises(AttributeError):
            getattr(akis, ad)
    assert akis.isatty() is False
    assert akis.writable() is True


def test_maskeli_akis_bilinmeyen_ozniteligi_devrediyor():
    """Üretim betiklerinin başındaki `reconfigure(encoding=...)` döngüsü
    çalışmaya devam etmeli — yoksa sarmalayıcı sessiz bir davranış değişikliği
    getirirdi."""
    alt = _SahteAkis()
    alt.encoding = "utf-8"
    assert GS._MaskeliAkis(alt).encoding == "utf-8"


# --- Özyineleme kilidi ------------------------------------------------------

def test_maskeleyici_stderr_e_yazarsa_sonsuz_donguye_girmiyor(monkeypatch):
    """Bugün `maskele()` hiçbir şey YAZMIYOR (saf `re`), yani döngü YOK.

    Ama stderr==maskeleyen akış olduğu için, maskeleyicinin (ya da alt
    katmanın) tek bir `warnings.warn`'ı sonsuz özyineleme demek olurdu.
    Kilit thread-yerel: yeniden girişte metin TEK sefer, maskelenmeden yazılıp
    dönülüyor — `RecursionError` ile ölmek, sarmalayıcının ASLA yapmaması
    gereken şey.
    """
    alt = _SahteAkis()
    akis = GS._MaskeliAkis(alt)
    monkeypatch.setattr(sys, "stderr", akis)

    def _yazan_maskeleyici(metin):
        sys.stderr.write("maskeleyicinin kendi uyarısı")   # yeniden giriş
        return gizli_maskele.maskele(metin)

    monkeypatch.setattr(GS, "_maskele", _yazan_maskeleyici)

    akis.write("access_token=" + SAHTE_IG)

    assert "maskeleyicinin kendi uyarısı" in alt.metin
    assert SAHTE_IG not in alt.metin
    assert len(alt.parcalar) == 2               # döngü yok: iki yazım, o kadar


def test_maskeleyici_patlarsa_iz_yine_birakiliyor(tmp_path, monkeypatch):
    """`_maskeli()` asla yukarı istisna sızdırmamalı: patlarsa BİTTİ damgası
    yazılmaz ve koşu üretimde 'asılı kalmış' diye YANLIŞ sınıflandırılır."""
    def _patlayan(metin):
        raise ValueError("maskeleyici bozuk")

    monkeypatch.setattr(GS, "_maskele", _patlayan)
    yol = str(tmp_path / "izler" / "patlak.log")
    GS._yaz(yol, "[2026-09-12 10:00:00] BAŞLADI x.py\n")

    assert "BAŞLADI x.py" in open(yol, encoding="utf-8").read()


# --- Korumalı import --------------------------------------------------------

def _maskeleyicisiz_yukle(monkeypatch):
    """Sarmalayıcıyı `gizli_maskele` YOKKEN yeniden yükler.

    `sys.modules[ad] = None` CPython'da o adın import'unu `ImportError` ile
    patlatır — dosyayı gerçekten silmeden aynı arızayı üretmenin yolu.
    """
    monkeypatch.setitem(sys.modules, "gizli_maskele", None)
    spec = importlib.util.spec_from_file_location("gs_maskesiz", SARMALAYICI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_maskeleyici_yuklenemezse_sarmalayici_calismaya_devam_ediyor(
        tmp_path, monkeypatch):
    """Sarmalayıcı EN ALT katman: kendi başarısızlığı zinciri KIRMAMALI.

    "Betik ölürse iz kalsın" sözleşmesi maskelemeden ÖNCE gelir — maskelenmemiş
    yazmak, hiç yazmamaktan iyidir.
    """
    mod = _maskeleyicisiz_yukle(monkeypatch)
    assert mod.MASKELEYICI_HATASI, "import koruması hiç devreye girmedi"

    mod.IZ_DIZIN = str(tmp_path / "izler")
    betik = _betik_yaz(tmp_path, "sade.py", "x = 1 + 1\n")
    eski_argv, eski_path = list(sys.argv), list(sys.path)
    try:
        assert mod.calistir(["gorev_sarmalayici.py", betik]) == 0
    finally:
        sys.argv[:] = eski_argv
        sys.path[:] = eski_path

    metin = _iz_metni(tmp_path / "izler", "sade")
    assert "BAŞLADI sade.py" in metin
    assert "BİTTİ sade.py rc=0" in metin


def test_maskeleyici_yuklenemezse_bu_SESSIZ_olmuyor(tmp_path, monkeypatch):
    """Sessizce ham yazan bir sarmalayıcı, "iz maskeli" sanısını doğrulanamaz
    bir varsayıma çevirirdi (CLAUDE.md: sessizce bozulan koruma, olmayan
    korumadan kötüdür)."""
    mod = _maskeleyicisiz_yukle(monkeypatch)
    mod.IZ_DIZIN = str(tmp_path / "izler")
    betik = _betik_yaz(tmp_path, "sessiz.py", "x = 1\n")
    eski_argv, eski_path = list(sys.argv), list(sys.path)
    try:
        mod.calistir(["gorev_sarmalayici.py", betik])
    finally:
        sys.argv[:] = eski_argv
        sys.path[:] = eski_path

    metin = _iz_metni(tmp_path / "izler", "sessiz")
    assert "MASKELEYİCİ YÜKLENEMEDİ" in metin, metin


# --- Uçtan uca: GERÇEK `pythonw.exe` ---------------------------------------
# Sarmalayıcının VAR OLMA sebebi olan ortam (`sys.stdout`/`sys.stderr` None).
# Ortam kurulumu `tests/test_gorev_sarmalayici_pythonw.py`'den ALINIYOR —
# `CreateProcessW` + NULL std handle'ları ikinci kez yazmak, iki kopyanın
# sessizce ayrışması demek olurdu.

pythonw_testi = pytest.mark.skipif(
    sys.platform != "win32", reason="pythonw.exe yalnızca Windows'ta var"
)


@pythonw_testi
def test_pythonw_altinda_iz_hem_yaziliyor_hem_maskeli(tmp_path):
    import shutil

    from test_gorev_sarmalayici_pythonw import _konsolsuz_calistir, _pythonw

    pyw = _pythonw()
    if pyw is None:
        pytest.skip("pythonw.exe bulunamadı")

    kok = tmp_path / "kok"
    kok.mkdir()
    shutil.copy2(SARMALAYICI, str(kok / "gorev_sarmalayici.py"))
    shutil.copy2(MASKELEYICI, str(kok / "gizli_maskele.py"))
    (kok / "sizdiran.py").write_text(
        "import sys\n"
        "print('stderr sızıntısı: " + SAHTE_URL + "', file=sys.stderr)\n"
        "raise RuntimeError('Max retries exceeded with url: " + SAHTE_URL + "')\n",
        encoding="utf-8",
    )

    rc = _konsolsuz_calistir(
        '"%s" gorev_sarmalayici.py sizdiran.py' % pyw, str(kok))
    assert rc == 1

    iz = kok / "gorev_izleri" / "sizdiran.log"
    assert iz.is_file(), "pythonw altında iz dosyası hiç oluşmadı"
    metin = iz.read_bytes().decode("utf-8")
    assert "BAŞLADI sizdiran.py" in metin
    assert "BİTTİ sizdiran.py rc=1" in metin
    assert "MASKELEYİCİ YÜKLENEMEDİ" not in metin   # maskeleyici GERÇEKTEN yüklendi
    assert SAHTE_IG not in metin, "SIZINTI (pythonw altında):\n%s" % metin
    assert metin.count(MASKE) >= 2                  # hem stderr hem traceback
