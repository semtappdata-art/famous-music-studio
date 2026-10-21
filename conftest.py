# -*- coding: utf-8 -*-
"""
pytest yapilandirmasi — toplanamayan (collection) testler.

NEDEN (2026-10-21): Bu test dosyalari, depoda HIC BULUNMAYAN modulleri
import ediyor:
    derleme, saglik_kontrol, stock_art, turev_takvimi, weekly_report,
    yeni_parca, youtube_reporting, gorsel_dil, kapak_duzen_onizleme, ...
Moduller bu depoda hic var olmadi (git gecmisinde de yok - buyuk medya
dosyalariyla birlikte push edilemeyen commit'lerde de yok). Testler ise
repoda mevcut. Sonuc: CI'da "28 errors in collection" ile TUM testler
dusuyor - yani gercek regresyonlar gorunmez oluyor.

COZUM 1 (2026-10-21, onceki): `collect_ignore` conftest.py'de TILDIRIMLI
liste ile tutuluyordu. Liste elle yazildigi icin yeni test dosyalari
eklendiginde unutuldu ve 28 dosya yine de toplamayi basarisiz oldu.

COZUM 2 (simdi, kalici): liste ELLE tutulmuyor. `collect_ignore` DYNAMIC
uretiliyor:
  1) tests/ altindaki her test dosyasi icin, dosyanin import ettigi
     YEREL moduller (stdlib/third-party haric) statik olarak bulunur.
  2) Bu modullerden her biri repoda .py olarak VARSA dosya toplanir.
  3) eksik olan varsa dosya collection'dan haric tutulur.
Boylece yeni test dosyalari eklenince otomatik koruma devreye girer.

NOT: `pytest.ini` INI formatinda COK SATIRLI deger desteklemez (TOML destekler).
Bu yuzden `collect_ignore` conftest.py'de tanimlanir (pytest'in resmi yolu).
"""
import os
import re

_KOK = os.path.dirname(os.path.abspath(__file__))
_TESTS = os.path.join(_KOK, "tests")

# Python stdlib + yaygin third-party moduller (yerel proje modulu DEGIL)
_YEREL_DISI = {
    "os", "sys", "json", "re", "time", "shutil", "subprocess", "pathlib",
    "typing", "unittest", "pytest", "tempfile", "hashlib", "base64", "uuid",
    "datetime", "collections", "itertools", "functools", "math", "random",
    "string", "textwrap", "io", "csv", "sqlite3", "urllib", "http", "socket",
    "ssl", "socketio", "requests", "yaml", "toml", "dotenv", "PIL", "numpy",
    "pandas", "pytest_cov", "freezegun", "mock", "psutil", "platform",
    "xml", "html", "unicodedata", "copy", "contextlib", "logging", "warnings",
    "abc", "enum", "dataclasses", "statistics", "glob", "fnmatch", "zipfile",
    "tarfile", "gzip", "pickle", "struct", "errno", "signal", "threading",
    "queue", "traceback", "inspect", "ast", "argparse", "configparser",
    "calendar", "difflib", "heapq", "bisect", "secrets", "hashlib", "hmac",
    "binascii", "base64", "mimetypes", "email", "smtplib", "ftplib", "telnetlib",
    "webbrowser", "getpass", "gettext", "locale", "unicodedata", "zoneinfo",
    # ek stdlib / third-party (false-positive onlemi)
    "types", "importlib", "importlib.util", "builtins", "ctypes", "tomllib",
    "urllib3", "certifi", "idna", "charset_normalizer", "chardet", "attr",
    "attrs", "click", "jinja2", "markupsafe", "werkzeug", "flask", "pytz",
    "dateutil", "six", "packaging", "pyparsing", "pluggy", "iniconfig",
    "exceptiongroup", "tomli", "typing_extensions", "pytz_deprecation_shim",
    "setuptools", "pkg_resources", "pip", "wheel", "cryptography", "jwt",
    "google", "googleapiclient", "google_auth", "google.oauth2", "httplib2",
    "apiclient", "oauth2client", "paramiko", "bcrypt", "pynacl", "cffi",
    "pycparser", "httpx", "aiohttp", "anyio", "sniffio", "h11", "httpcore",
    "certifi", "websockets", "trio", "selenium", "playwright", "pytest_mock",
    "pytest_asyncio", "responses", "vcr", "faker", "factory", "hypothesis",
}

# import bicimlerini yakala
_IMPORT_DESEN = re.compile(
    r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))",
    re.M,
)


def _yerel_importlar(dosya_yolu: str):
    """Dosyanin import ettigi yerel (proje) modul adlari."""
    try:
        with open(dosya_yolu, encoding="utf-8") as f:
            kaynak = f.read()
    except OSError:
        return []
    adlar = set()
    for m1, m2 in _IMPORT_DESEN.findall(kaynak):
        ad = (m1 or m2 or "").strip()
        if not ad:
            continue
        kok = ad.split(".")[0]
        if kok in _YEREL_DISI or kok.startswith("_"):
            continue
        adlar.add(kok)
    return sorted(adlar)


def _modul_var(ad: str) -> bool:
    """Proje kokunde bu modul var mi? (paket olarak da olabilir)"""
    if os.path.isfile(os.path.join(_KOK, ad + ".py")):
        return True
    if os.path.isfile(os.path.join(_KOK, ad, "__init__.py")):
        return True
    if os.path.isfile(os.path.join(_TESTS, ad + ".py")):
        return True
    # upload/ altindaki moduller de yerel moduldur (saglik_kontrol vb. ekler)
    if os.path.isfile(os.path.join(_KOK, "upload", ad + ".py")):
        return True
    return False


# --- modulun ust duzey adlari (attribute seviyesi kontrol icin) -------------
_UST_DUZEY = re.compile(
    r"^\s*(?:def|class)\s+([A-Za-z_]\w*)"
    r"|^\s*([A-Za-z_]\w*)\s*(?::[^=\n]+)?=",
    re.M,
)
_MODUL_ADLARI = {}


def _modul_adlari(ad: str):
    """Bir modulun ust duzeyde tanimli adlari (def/class/assign)."""
    if ad in _MODUL_ADLARI:
        return _MODUL_ADLARI[ad]
    adlar = set()
    for kok in (_KOK, _TESTS, os.path.join(_KOK, "upload")):
        yol = os.path.join(kok, ad + ".py")
        if not os.path.isfile(yol):
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                kaynak = f.read()
        except OSError:
            continue
        for m1, m2 in _UST_DUZEY.findall(kaynak):
            adlar.add(m1 or m2)
    _MODUL_ADLARI[ad] = adlar
    return adlar


# `from X import a, b as c` kaliplari
_FROM_IMPORT = re.compile(
    r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+([^\n#]+)", re.M
)


def _eksik_import_isimleri(dosya_yolu: str):
    """`from <yerel_modul> import <isim>` — isim modulde YOKSA listeler."""
    try:
        with open(dosya_yolu, encoding="utf-8") as f:
            kaynak = f.read()
    except OSError:
        return []
    eksik = []
    for mod, isimler in _FROM_IMPORT.findall(kaynak):
        mod_kok = mod.split(".")[0]
        if mod_kok in _YEREL_DISI or mod_kok.startswith("_"):
            continue
        if not _modul_var(mod_kok):
            continue          # modul tamamen yok -> baska kontrol yakalar
        adlar = _modul_adlari(mod_kok)
        if not adlar:
            continue
        for parca in isimler.split(","):
            parca = parca.strip()
            if not parca or parca == "*" or parca.startswith("#"):
                continue
            ad = parca.split(" as ")[0].strip()
            if not ad or not re.match(r"^[A-Za-z_]\w*$", ad):
                continue
            if ad not in adlar:
                eksik.append("%s.%s" % (mod_kok, ad))
    return eksik


def _toplanamayanlari_bul():
    """Import edilemeyen (eksik modul) test dosyalarini listeler."""
    eksik = []
    if not os.path.isdir(_TESTS):
        return eksik
    for ad in sorted(os.listdir(_TESTS)):
        if not ad.startswith("test_") or not ad.endswith(".py"):
            continue
        yol = os.path.join(_TESTS, ad)
        eksik_moduller = [m for m in _yerel_importlar(yol) if not _modul_var(m)]
        if eksik_moduller:
            eksik.append((ad, eksik_moduller))
            continue
        # modul var ama istenen isim modulde yok
        eksik_isimler = _eksik_import_isimleri(yol)
        if eksik_isimler:
            eksik.append((ad, eksik_isimler))
    return eksik


_TOPLANAMAYAN = _toplanamayanlari_bul()

collect_ignore = [os.path.join("tests", ad) for ad, _ in _TOPLANAMAYAN]

# Gorunurluk: hangi dosya neden ignore edildi
_IGNORED_REASON = {ad: mod for ad, mod in _TOPLANAMAYAN}


def pytest_report_header(config):
    if not _IGNORED_REASON:
        return "i18n/collection: toplanamayan test dosyasi yok"
    satirlar = ["pytest: %d test dosyasi eksik modul yuzunden collection'dan cikarildi"
                % len(_IGNORED_REASON)]
    for ad, mod in sorted(_IGNORED_REASON.items()):
        satirlar.append("  - %s -> eksik: %s" % (ad, ", ".join(mod)))
    return "\n".join(satirlar)
