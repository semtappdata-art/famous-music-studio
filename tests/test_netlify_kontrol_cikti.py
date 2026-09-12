# -*- coding: utf-8 -*-
"""`netlify_kontrol.py`'nin çıktı akışı davranışı + depo genelinde import yan etkisi muhafızı.

NEDEN VAR (2026-09-12, üçüncü duman koşusu): `netlify_kontrol.py` modül düzeyinde
`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` yapıyordu. Import eden
herkesin stdout'u yerinden ediliyor, pytest altında eski sarmalayıcı GC edilince
ORTAK tampon kapanıp sonraki her test "I/O operation on closed file" ile
düşüyordu (32 ERROR). Üretimde `pythonw.exe` (`sys.stdout is None`) olduğu için
sessizdi. Düzeltme: `reconfigure()` tabanlı `_cikti_utf8()`, yalnızca `main()`
içinde. "Import stdout'u değiştirmemeli" kanıtı
`tests/test_entegrasyon_duman3.py::test_netlify_kontrol_import_aninda_stdoutu_degistirmemeli`
— burada TEKRARLANMIYOR; bu dosya kalan üç şeyi koruyor:

  1. `main()` cp1254'e yönlendirilmiş bir stdout'ta (boru/dosya — bu makinede
     tam olarak böyle) çökmeden UTF-8 basıyor ve `sys.stdout` AYNI nesne kalıyor
     (sarmalayıcı yaratılmıyor). Ağa çıkmayan yol: eksik alanlı sahte secrets.
  2. `_cikti_utf8()` `sys.stdout is None` (pythonw) ve `reconfigure`suz akış
     karşısında sessizce geçiyor — sağlık kontrolü ASLA bundan ötürü durmamalı.
  3. DEPO GENELİ MUHAFIZ: kök ve `upload/` altındaki hiçbir .py MODÜL DÜZEYİNDE
     `sys.stdout =` / `sys.stderr =` ataması yapmıyor (üst düzey `if`/`try`
     blokları dahil). Fonksiyon içindeki geçici, geri alınan atamalar
     (`gorev_sarmalayici.calistir`) FARKLI ve serbest; `reconfigure()` çağrıları
     da serbest (sarmalayıcı yaratmıyor).

Gerçek token dosyasına DOKUNULMUYOR: `GIZLI` alt süreçte sahte dosyaya çekiliyor.
"""
import ast
import glob
import json
import os
import subprocess
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alt_surec(kod: str, **env_ek):
    env = dict(os.environ, **env_ek)
    return subprocess.run([sys.executable, "-c", kod], capture_output=True,
                          timeout=60, env=env)


def test_main_cp1254_borusunda_utf8_basar_ve_stdout_nesnesini_korur(tmp_path):
    sahte = tmp_path / "sahte_secrets.json"
    sahte.write_text(json.dumps({"token": "", "site_id": ""}), encoding="utf-8")
    kod = (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "import netlify_kontrol as NK\n"
        "NK.GIZLI = %r\n"
        "once = sys.stdout\n"
        "kod = NK.main()\n"
        "print('KOD', kod, 'AYNI', sys.stdout is once, 'ENC', sys.stdout.encoding)\n"
        "print('GEÇERLİ ✓ ışğ')\n"
    ) % (_KOK, str(sahte))
    p = _alt_surec(kod, PYTHONIOENCODING="cp1254")
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    metin = p.stdout.decode("utf-8")          # cp1254 kalsaydı ✓ burada çökerdi
    assert "SONUÇ: eksik alan var" in metin    # ağa çıkmayan yol, Türkçe düzgün
    assert "KOD 2 AYNI True ENC utf-8" in metin
    assert "GEÇERLİ ✓ ışğ" in metin


def test_cikti_utf8_stdout_none_ve_reconfiguresuz_akista_sessiz():
    kod = (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "import netlify_kontrol as NK\n"
        "class Sagir:\n"
        "    def write(self, s): return len(s)\n"
        "    def flush(self): pass\n"
        "sys.stdout = None\n"
        "sys.stderr = Sagir()\n"
        "NK._cikti_utf8()\n"
        "sys.stdout = sys.__stdout__; sys.stderr = sys.__stderr__\n"
        "print('OK')\n"
    ) % _KOK
    p = _alt_surec(kod)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    assert p.stdout.decode().strip() == "OK"


# ---------------------------------------------------------------------------
# 3. Depo geneli muhafız
# ---------------------------------------------------------------------------

def _modul_duzeyi_std_atamalari(kaynak: str):
    """Modül düzeyindeki (fonksiyon/sınıf gövdesine GİRMEDEN) `sys.stdout =` /
    `sys.stderr =` atamalarının satır numaraları."""
    agac = ast.parse(kaynak)
    bulgular = []

    def _hedef_std(h):
        return (isinstance(h, ast.Attribute) and isinstance(h.value, ast.Name)
                and h.value.id == "sys" and h.attr in ("stdout", "stderr"))

    def gez(govde):
        for dugum in govde:
            if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue                      # çalışma anı, geri alınabilir — serbest
            if isinstance(dugum, ast.Assign) and any(_hedef_std(h) for h in dugum.targets):
                bulgular.append(dugum.lineno)
            for alan in ("body", "orelse", "finalbody"):
                alt = getattr(dugum, alan, None)
                if isinstance(alt, list):
                    gez(alt)
            for h in getattr(dugum, "handlers", []) or []:
                gez(h.body)
    gez(agac.body)
    return bulgular


def test_muhafiz_kendi_desenini_yakalar():
    assert _modul_duzeyi_std_atamalari(
        "import sys, io\nif hasattr(sys.stdout, 'buffer'):\n"
        "    sys.stdout = io.TextIOWrapper(sys.stdout.buffer)\n") == [3]
    assert _modul_duzeyi_std_atamalari(
        "import sys\ndef f():\n    sys.stderr = open('x')\n") == []
    assert _modul_duzeyi_std_atamalari(
        "import sys\nfor s in (sys.stdout, sys.stderr):\n"
        "    s.reconfigure(encoding='utf-8')\n") == []


def test_hicbir_modul_import_aninda_stdout_stderr_atamiyor():
    dosyalar = sorted(glob.glob(os.path.join(_KOK, "*.py"))
                      + glob.glob(os.path.join(_KOK, "upload", "*.py")))
    assert dosyalar, "tarama boş — yol yanlış"
    kirli = {}
    for yol in dosyalar:
        with open(yol, encoding="utf-8") as f:
            satirlar = _modul_duzeyi_std_atamalari(f.read())
        if satirlar:
            kirli[os.path.relpath(yol, _KOK)] = satirlar
    assert not kirli, (
        "Modül düzeyinde sys.stdout/sys.stderr ataması — import yan etkisi, pytest'i "
        "kırar (bkz. netlify_kontrol._cikti_utf8 NEDEN yorumu). reconfigure() kullan, "
        "main() içinde: %r" % kirli)
