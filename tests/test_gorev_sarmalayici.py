# -*- coding: utf-8 -*-
"""`gorev_sarmalayici.py` — üç arıza biçiminin de İZ bıraktığını doğrular.

NEDEN VAR: `gorev_sarmalayici.py`'nin docstring'i bu dosyanın adını
2026-09-11'e kadar "izole olarak test edilebiliyor" gerekçesiyle ANIYORDU ama
dosya DİSKTE YOKTU — yani günün en önemli yeni korumasının tek bir testi bile
yoktu. (CLAUDE.md: "Bir yorum bir GARANTİ ifade ediyorsa, o garantiyi
doğrulayan bir test olmadan yazma.")

Sarmalayıcının sözleşmesi ÜÇ satır ve bu dosya üçünü de tek tek kilitliyor:

  * çöktü            → BAŞLADI + ÇÖKTÜ + tam traceback + BİTTİ
  * normal bitti     → BAŞLADI + BİTTİ rc=0
  * takıldı/öldü     → BAŞLADI var, eşleşen BİTTİ YOK

Üçüncü satır, ilk ikisinin doğru çalışmasına BAĞLI: BİTTİ damgası herhangi bir
çıkış yolunda atlanırsa, o yol üretimde "süreç asıldı" diye YANLIŞ okunur.
2026-09-11'de tam olarak böyle bir kırık vardı — "betik bulunamadı" dalı
`try/finally`'den ÖNCE `return 2` ediyordu (bkz. `test_betik_bulunamazsa_*`).

İZOLASYON: `IZ_DIZIN` her testte `tmp_path`'e çekiliyor — gerçek
`gorev_izleri/` klasörüne, `auto_process.log`'a ya da kilit dosyalarına TEK
BAYT yazılmıyor (aynı gerekçe: `tests/conftest.py`).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gorev_sarmalayici as GS


@pytest.fixture
def izler(tmp_path, monkeypatch):
    """İz klasörünü tmp'ye çeker ve süreç durumunu geri yükler.

    `calistir()` sarılan betik için `sys.argv`/`sys.path`'i DEĞİŞTİRİYOR
    (üretimde doğru olan bu — betik kendi argümanlarını görmeli); test
    sürecinde bunu geri almazsak sonraki testler bozuk bir argv ile koşar.
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


def test_iz_dizini_gercekten_yonlendirildi(izler):
    """Koruma korumasının kendisi: testler ÜRETİM izlerine yazmamalı."""
    assert "gorev_izleri" not in GS.IZ_DIZIN
    assert GS.iz_yolu("auto_process.py").startswith(str(izler))


# --- (a) import hatası veren betik ------------------------------------------

def test_import_hatasi_cokme_izi_birakir(tmp_path, izler):
    """Sarmalayıcının VAR OLMA sebebi: betik KENDİ log'unu açmadan ölüyor.

    `pythonw.exe`'de stdout/stderr None olduğu için böyle bir ölüm üretimde
    geriye tek bayt bırakmıyordu; iz dosyası bu boşluğu kapatan tek kaynak.
    """
    betik = _betik_yaz(
        tmp_path, "cokuk.py",
        "import bu_modul_kesinlikle_yok_12345\n",
    )
    kod = GS.calistir(["gorev_sarmalayici.py", betik])

    assert kod == 1
    m = _iz_metni(izler, "cokuk")
    assert "BAŞLADI cokuk.py" in m
    assert "ÇÖKTÜ cokuk.py" in m
    # Tam traceback — "bir şey oldu" değil, NE olduğu yazmalı.
    assert "Traceback (most recent call last)" in m
    assert "bu_modul_kesinlikle_yok_12345" in m
    assert "BİTTİ cokuk.py rc=1" in m
    # Sıra da sözleşmenin parçası: BAŞLADI önce, BİTTİ en sonda.
    assert m.index("BAŞLADI") < m.index("ÇÖKTÜ") < m.index("BİTTİ")


# --- (b) normal biten betik --------------------------------------------------

def test_normal_biten_betik_rc0(tmp_path, izler):
    isaret = tmp_path / "kostu.txt"
    betik = _betik_yaz(
        tmp_path, "duz.py",
        "open(%r, 'w').write('ok')\n" % str(isaret),
    )
    kod = GS.calistir(["gorev_sarmalayici.py", betik])

    assert kod == 0
    assert isaret.read_text() == "ok"        # betik GERÇEKTEN koştu
    m = _iz_metni(izler, "duz")
    assert "BAŞLADI duz.py" in m
    assert "BİTTİ duz.py rc=0" in m
    assert "ÇÖKTÜ" not in m


def test_betigin_argumanlari_gecirilliyor(tmp_path, izler):
    """Sarmalayıcı şeffaf olmalı: kendi argv'sini betiğe sızdırmamalı."""
    isaret = tmp_path / "argv.txt"
    betik = _betik_yaz(
        tmp_path, "argvli.py",
        "import sys\nopen(%r, 'w').write('|'.join(sys.argv[1:]))\n" % str(isaret),
    )
    kod = GS.calistir(["gorev_sarmalayici.py", betik, "--count", "2"])

    assert kod == 0
    assert isaret.read_text() == "--count|2"


# --- (c) sys.exit(3) ---------------------------------------------------------

def test_sys_exit_kodu_aynen_donuyor(tmp_path, izler):
    """Dönüş kodu Görev Zamanlayıcı'nın 'sonuc' sütununa düşen TEK sinyal —
    sarmalayıcı onu 0/1'e yuvarlarsa gerçek arıza görünmez olur."""
    betik = _betik_yaz(tmp_path, "cikisli.py", "import sys\nsys.exit(3)\n")
    kod = GS.calistir(["gorev_sarmalayici.py", betik])

    assert kod == 3
    m = _iz_metni(izler, "cikisli")
    assert "BAŞLADI cikisli.py" in m
    assert "BİTTİ cikisli.py rc=3" in m
    assert "ÇÖKTÜ" not in m


def test_sys_exit_sifir_temiz_sayilir(tmp_path, izler):
    betik = _betik_yaz(tmp_path, "cikis0.py", "import sys\nsys.exit(0)\n")
    assert GS.calistir(["gorev_sarmalayici.py", betik]) == 0
    assert "BİTTİ cikis0.py rc=0" in _iz_metni(izler, "cikis0")


# --- Düzeltilen kırık: betik bulunamazsa da BİTTİ yazılmalı ------------------

def test_betik_bulunamazsa_bitti_damgasi_da_yazilir(tmp_path, izler):
    """2026-09-11 kırığının koruma testi.

    Eski kod bu dalda ÇÖKTÜ yazıp `try/finally`'den ÖNCE `return 2` ediyordu:
    BAŞLADI vardı, eşleşen BİTTİ YOKTU. Modülün kendi sözleşmesine göre
    ("BAŞLADI var, BİTTİ yok = takıldı/öldü") bu, bir yazım hatasını ya da
    yeniden adlandırılmış bir betiği "süreç asılı kaldı" diye okuturdu —
    yani sarmalayıcı arızayı YANLIŞ sınıflandırırdı.
    """
    yok = str(tmp_path / "hicyok.py")
    kod = GS.calistir(["gorev_sarmalayici.py", yok])

    assert kod == 2
    m = _iz_metni(izler, "hicyok")
    assert "BAŞLADI hicyok.py" in m
    assert "ÇÖKTÜ hicyok.py" in m
    assert "betik bulunamadı" in m
    assert "BİTTİ hicyok.py rc=2" in m


@pytest.mark.parametrize(
    "ad,govde",
    [
        ("a_duz.py", "x = 1\n"),
        ("b_cokuk.py", "raise RuntimeError('patladi')\n"),
        ("c_cikis.py", "import sys\nsys.exit(7)\n"),
        ("d_yok.py", None),          # hiç yazılmayan betik
    ],
)
def test_her_yolda_basladi_ve_bitti_esit_sayida(tmp_path, izler, ad, govde):
    """Sözleşmenin TEK cümlelik hâli — yeni bir çıkış yolu eklenirse bu düşer.

    "BAŞLADI var, BİTTİ yok" üretimde 'süreç asıldı' anlamına geldiği için,
    damga sayılarının eşitliği tanının TAMAMININ dayandığı varsayım.
    """
    yol = (_betik_yaz(tmp_path, ad, govde) if govde is not None
           else str(tmp_path / ad))
    GS.calistir(["gorev_sarmalayici.py", yol])

    m = _iz_metni(izler, ad.replace(".py", ""))
    assert m.count("BAŞLADI ") == 1
    assert m.count("BİTTİ ") == 1
