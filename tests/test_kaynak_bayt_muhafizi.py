# -*- coding: utf-8 -*-
"""Kaynak dosyalara SIZAN bozuk baytların muhafızı.

NEDEN VAR (2026-09-11): tek bir oturumda BEŞ ayrı kez, bir yama uygulanırken
ters eğik çizgi araç katmanlarında yutuldu ve diske kaçış dizisi yerine
GERÇEK kontrol baytı yazıldı. Her seferinde suçlu farklı bir katmandı:

  1. JSON araç parametresi kaçışı bir kez çözdü -> `generate_cover.py` içine
     GERÇEK bir NUL baytı (0x00) yazıldı.
  2. Bash heredoc kaçışı çözdü -> `upload/youtube_upload.py`de kaçış dizisi
     olması gereken satır sonu, GERÇEK 0x0A olarak diske indi (iki kez).
  3. Regex yazarken kaçış hatası -> `gizli_maskele.py`ye üç adet 0x08
     (backspace) baytı girdi.
  4. Yine heredoc -> `saglik_kontrol.py` aynı şekilde bozuldu.

Hepsi yalnızca o gün ELLE yapılan `ast.parse` + kontrol karakteri taraması
sayesinde yakalandı. O tarama bir alışkanlıktı, bir GÜVENCE değildi; bu dosya
onu güvenceye çeviriyor. Sınıf, CLAUDE.md'deki "sessiz arıza"nın en kötü
türü: dosya gözle bakınca DOĞRU görünüyor (0x08 terminalde görünmez, 0x00
editörde çoğu zaman hiç çizilmez) ama çalışma zamanında ya sözdizimi hatası
ya da sessizce yanlış davranış üretiyor.

BU, CLAUDE.md'deki ffmpeg `drawtext` tuzağıyla AYNI ŞEY DEĞİL: orada metni
bozan ffmpeg'in filtre ayrıştırıcısı (çalışma zamanı), burada dosyayı YAZAN
araç zinciri (geliştirme zamanı).

NE TARANIYOR
  * NUL (0x00) — kaynak dosyada hiçbir gerekçesi yok.
  * Diğer C0 kontrol baytları + 0x7F (DEL). Sekme/LF/CR muaf.
  * Sözdizimi (`ast.parse`) — dolaylı olarak zaten testlerin import'u sınıyor
    ama açık tarama HANGİ dosya diye tek satırda söylüyor; ayrıca hiçbir
    testin import etmediği betikleri (`run_pipeline`, `netlify_kontrol` ...)
    de kapsıyor.
  * AYNI dosyada hem CRLF hem LF (yalnızca .py/.md).

YANLIŞ POZİTİF YOK — ölçüldü (2026-09-11, depo geneli): 116 .py, 29 .md,
23 .json dosyasının HİÇBİRİNDE kontrol baytı ve karışık satır sonu yok.
Emoji, Türkçe karakter ve BOM alarm üretmiyor: tarama BAYT düzeyinde ve
yalnızca 0x20 altındaki baytlara bakıyor, UTF-8 çok baytlı diziler ile BOM
(0xEF 0xBB 0xBF) bu eşiğin üstünde kalıyor. `setup_task_scheduler.ps1`
(BOM'lu, hassas) zaten uzantı süzgecinin dışında.

SATIR SONU KURALI NEDEN "KARIŞIK MI" ŞEKLİNDE: depoda 39 CRLF ve 77 LF .py
bir arada yaşıyor, yani tek bir doğru üslup YOK ve dosya başına üslubu
sabitlemek bakımı unutulacak bir manifest demekti. Bozulma işareti olan şey
üslubun kendisi değil, bir yamanın dosyanın YARISINI çevirmesi. (Dürüst
sınır: bir dosyayı BAŞTAN SONA LF'e çeviren bir yama — o gün `render.py`de
bir kez oldu, ajan fark edip geri aldı — bu testten geçer; `git diff` onu
zaten gürültülü biçimde gösteriyor.)

`.claude/` kapsam dışı: orada ajan worktree kopyaları var, bu deponun kaynağı
değiller. İçerik kökleri (`projects/`, `dj_sets/`, `derlemeler/`) de kapsam
dışı — orası üretim çıktısı, kaynak değil.

DİKKAT — bu dosyanın KENDİSİ de aynı tuzağın menzilinde: aşağıdaki sahte
bozuk fikstürlerde ters eğik çizgi İÇEREN hiçbir dizgi literali YOK, hepsi
`chr(92)` / `chr(10)` / `chr(0)` ile kuruluyor. Bir kaçış dizisi yazılsaydı
ve araç katmanı onu yutsaydı, muhafız testi sessizce kendi hedefini test
etmez hâle gelirdi.
"""

import ast
import io
import os

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `.claude` = ajan worktree kopyaları; içerik kökleri = üretim çıktısı.
ATLANAN_KLASORLER = {
    ".git", ".claude", ".pytest_cache", ".stock_video_cache", "__pycache__",
    "projects", "dj_sets", "derlemeler", "gorev_izleri",
}

# Sekme, satır sonu, satır başı: metin dosyasında meşru olan tek üç kontrol
# baytı. Geri kalan her C0 baytı ile 0x7F (DEL) bozulma işareti.
IZINLI_KONTROL = frozenset((0x09, 0x0A, 0x0D))

TARANAN_UZANTILAR = (".py", ".md", ".json")
# Satır sonu disiplini yalnızca ELLE düzenlenen kaynak için anlamlı; .json'ların
# bir kısmını üretim çalışırken kendisi yazıyor (durum/önbellek dosyaları).
SATIR_SONU_UZANTILARI = (".py", ".md")


def _dosyalar(uzantilar):
    """Depodaki taranacak dosyaların mutlak yolları."""
    for kok, klasorler, adlar in os.walk(_KOK):
        klasorler[:] = [k for k in klasorler if k not in ATLANAN_KLASORLER]
        for ad in adlar:
            if ad.endswith(uzantilar):
                yield os.path.join(kok, ad)


def _oku(yol):
    with io.open(yol, "rb") as f:
        return f.read()


# --------------------------------------------------------------------------
# Denetçiler. Ayrı fonksiyon olmalarının NEDENİ: aşağıdaki "kanıt" testleri
# aynı mantığı SAHTE bozuk dosyalara uygulayıp gerçekten ateşlediğini
# gösterebilsin — yoksa "depo temiz" testi, hiçbir şeyi kontrol etmeyen bir
# testten ayırt edilemezdi.
# --------------------------------------------------------------------------

def kontrol_baytlari(ham):
    """(ofset, bayt) listesi — kaynakta bulunmaması gereken kontrol baytları."""
    bulunan = []
    for ofset, bayt in enumerate(bytearray(ham)):
        if bayt == 0x7F or (bayt < 0x20 and bayt not in IZINLI_KONTROL):
            bulunan.append((ofset, bayt))
    return bulunan


def karisik_satir_sonu(ham):
    """Dosyada hem CRLF hem yalın LF varsa (crlf, lf) sayıları, yoksa None."""
    crlf = ham.count(b"\r\n")
    lf = ham.count(b"\n") - crlf
    if crlf and lf:
        return (crlf, lf)
    return None


def sozdizimi_hatasi(ham, ad):
    """Kaynak `ast.parse` edilemiyorsa hata metni, ediliyorsa None.

    `utf-8-sig`: BOM'lu bir .py de sorunsuz çözülsün diye (depoda şu an yok,
    ama bir aracın BOM eklemesi bu testi yanlış yere düşürmemeli).
    """
    try:
        metin = ham.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        return "UTF-8 değil: %s" % e
    try:
        ast.parse(metin, filename=ad)
    except (SyntaxError, ValueError) as e:
        # İKİSİ de yakalanıyor: NUL baytı Python sürümüne göre SyntaxError
        # ("source code string cannot contain null bytes", 3.14) ya da
        # ValueError (eski sürümler) üretiyor — tür sabit değil.
        return "%s: %s" % (type(e).__name__, e)
    return None


def _kisa(bulunan):
    """Hata mesajı için özet. İÇERİK BASILMIYOR: taranan dosyalar arasında
    gitignore'lu token .json'ları da var, bir arıza onların içini log'a
    dökmemeli — yalnızca ofset ve bayt kodu."""
    return ", ".join("ofset %d = 0x%02X" % (o, b) for o, b in bulunan[:10])


# --------------------------------------------------------------------------
# Depo geneli
# --------------------------------------------------------------------------

def test_kaynakta_nul_bayti_yok():
    """Vaka 1'in muhafızı: `generate_cover.py`ye giren gerçek 0x00."""
    kirli = []
    for yol in _dosyalar(TARANAN_UZANTILAR):
        if b"\x00" in _oku(yol):
            kirli.append(os.path.relpath(yol, _KOK))
    assert not kirli, "NUL baytı taşıyan dosya(lar): %s" % kirli


def test_kaynakta_kacak_kontrol_karakteri_yok():
    """Vaka 3'ün muhafızı: `gizli_maskele.py`ye giren 0x08'ler."""
    kirli = []
    for yol in _dosyalar(TARANAN_UZANTILAR):
        bulunan = kontrol_baytlari(_oku(yol))
        if bulunan:
            kirli.append("%s (%s)" % (os.path.relpath(yol, _KOK), _kisa(bulunan)))
    assert not kirli, "Kontrol baytı taşıyan dosya(lar): %s" % kirli


def test_tum_py_dosyalari_ayristirilabiliyor():
    """Vaka 2 ve 4'ün muhafızı: kaçış dizisi yerine diske inen gerçek 0x0A,
    dizgi literalini ortadan ikiye bölüp sözdizimini bozuyor."""
    kirli = []
    for yol in _dosyalar((".py",)):
        hata = sozdizimi_hatasi(_oku(yol), yol)
        if hata:
            kirli.append("%s -> %s" % (os.path.relpath(yol, _KOK), hata))
    assert not kirli, "Ayrıştırılamayan dosya(lar): %s" % kirli


def test_dosya_ici_satir_sonu_karisik_degil():
    """Yarım çevrilmiş satır sonları (bkz. üstteki 'dürüst sınır' notu)."""
    kirli = []
    for yol in _dosyalar(SATIR_SONU_UZANTILARI):
        karisik = karisik_satir_sonu(_oku(yol))
        if karisik:
            kirli.append("%s (crlf=%d, lf=%d)"
                         % ((os.path.relpath(yol, _KOK),) + karisik))
    assert not kirli, "Karışık satır sonu: %s" % kirli


def test_tarama_gercekten_dosya_goruyor():
    """Süzgeç/atlama listesi bir gün her şeyi eleyip testleri SESSİZCE boşa
    çıkarmasın diye alt sınır. (Bu deponun tekrarlayan 'hiçbir şeye bakmayan
    yeşil test' tuzağı.)"""
    py = list(_dosyalar((".py",)))
    hepsi = list(_dosyalar(TARANAN_UZANTILAR))
    assert len(py) >= 100, "Beklenenden az .py tarandı: %d" % len(py)
    assert len(hepsi) >= len(py) + 40, "md/json taraması kapsam dışı kalmış"
    # Worktree kopyaları kapsam dışı kalmalı, yoksa her ajan dalı depo
    # kalitesini bozabilir hâle gelir.
    assert not [y for y in hepsi if (os.sep + ".claude" + os.sep) in y]


# --------------------------------------------------------------------------
# KANIT: 2026-09-11'in beş vakasının SAHTE kopyaları. Her biri denetçilerden
# en az birini ateşlemeli; ayrıca temiz bir kontrol dosyası HİÇBİRİNİ
# ateşlememeli (yanlış pozitif kanıtı).
# --------------------------------------------------------------------------

def _yaz(tmp_path, ad, metin):
    """Fikstürü BAYT olarak yazar: `io.open(..., 'w')` Windows'ta satır
    sonlarını kendiliğinden çevirip fikstürü bozardı."""
    yol = tmp_path / ad
    with io.open(str(yol), "wb") as f:
        f.write(metin.encode("utf-8"))
    return str(yol)


def test_kanit_vaka1_nul_bayti(tmp_path):
    """generate_cover.py: üç tırnaklı dizgi içine giren gerçek NUL."""
    bozuk = 'SABIT = """ab' + chr(0) + 'cd"""' + chr(10)
    ham = _oku(_yaz(tmp_path, "vaka1.py", bozuk))
    assert b"\x00" in ham
    assert kontrol_baytlari(ham)                 # kontrol taraması yakalar
    assert sozdizimi_hatasi(ham, "vaka1.py")     # ast.parse da yakalar


def test_kanit_vaka2_heredoc_satir_sonu(tmp_path):
    """youtube_upload.py: kaçış dizisi olması gereken satır sonu diske GERÇEK
    0x0A olarak inmiş -> dizgi literali ortadan bölünmüş."""
    temiz = 'mesaj = "satir1' + chr(92) + 'nsatir2"' + chr(10)
    bozuk = 'mesaj = "satir1' + chr(10) + 'satir2"' + chr(10)

    temiz_ham = _oku(_yaz(tmp_path, "vaka2_temiz.py", temiz))
    bozuk_ham = _oku(_yaz(tmp_path, "vaka2.py", bozuk))

    assert sozdizimi_hatasi(temiz_ham, "vaka2_temiz.py") is None
    assert sozdizimi_hatasi(bozuk_ham, "vaka2.py")
    # Kontrol baytı taraması bunu GÖRMEZ (0x0A izinli) — iki denetçinin de
    # gerekli olmasının nedeni tam olarak bu.
    assert not kontrol_baytlari(bozuk_ham)


def test_kanit_vaka3_backspace_bayti(tmp_path):
    """gizli_maskele.py: regex kaçışı bozulunca giren 0x08.

    BU VAKA'nın dersi: dosya sözdizimsel olarak GEÇERLİ kalıyor, yani
    `ast.parse` onu ASLA yakalamazdı — desen sessizce yanlış eşleşirdi."""
    bozuk = 'DESEN = "' + chr(8) + 'token"' + chr(10)
    ham = _oku(_yaz(tmp_path, "vaka3.py", bozuk))

    bulunan = kontrol_baytlari(ham)
    assert [b for _, b in bulunan] == [0x08]
    assert sozdizimi_hatasi(ham, "vaka3.py") is None     # ast tek başına kör


def test_kanit_vaka4_saglik_kontrol_ayni_desen(tmp_path):
    """saglik_kontrol.py: vaka 2'nin aynısı, bu kez tek tırnaklı literalde."""
    bozuk = ("def f():" + chr(10) +
             "    return 'a" + chr(10) + "b'" + chr(10))
    assert sozdizimi_hatasi(_oku(_yaz(tmp_path, "vaka4.py", bozuk)), "vaka4.py")


def test_kanit_vaka5_karisik_satir_sonu(tmp_path):
    """render.py: bir yamanın dosyanın yalnızca BİR KISMINI LF'e çevirmesi."""
    crlf = chr(13) + chr(10)
    lf = chr(10)
    bozuk = "a = 1" + crlf + "b = 2" + lf + "c = 3" + crlf
    ham = _oku(_yaz(tmp_path, "vaka5.py", bozuk))
    assert karisik_satir_sonu(ham) == (2, 1)
    assert sozdizimi_hatasi(ham, "vaka5.py") is None      # sözdizimi sağlam


@pytest.mark.parametrize("kodlama", ["utf-8", "utf-8-sig"])
def test_kanit_temiz_dosya_alarm_uretmiyor(tmp_path, kodlama):
    """YANLIŞ POZİTİF kanıtı: emoji, Türkçe karakter, sekme ve BOM temiz."""
    temiz = ("# -*- coding: utf-8 -*-" + chr(10) +
             'BASLIK = "Yeniden Doğacağım 🎵 ışİĞÜŞÇÖ"' + chr(10) +
             "def f():" + chr(10) +
             chr(9) + "return BASLIK" + chr(10))
    yol = str(tmp_path / ("temiz_%s.py" % kodlama.replace("-", "_")))
    with io.open(yol, "wb") as f:
        f.write(temiz.encode(kodlama))
    ham = _oku(yol)

    assert kontrol_baytlari(ham) == []
    assert karisik_satir_sonu(ham) is None
    assert sozdizimi_hatasi(ham, yol) is None
    if kodlama == "utf-8-sig":
        assert ham.startswith(b"\xef\xbb\xbf")    # BOM gerçekten vardı
