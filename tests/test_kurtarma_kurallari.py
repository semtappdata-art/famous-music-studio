# -*- coding: utf-8 -*-
"""
Madde 32 — Kurtarma + tutarlilik kurallari (2026-10-21).

NEDEN bu dosya: 2026-10-21'de yapilan incelemede, onceki turdeki
`git filter-branch` medya temizligi sirasinda 7 KRITIK modul yanlislikla
silinmis bulundu:

    derleme.py, generate_cover.py, saglik_kontrol.py, stock_art.py,
    dj_clips.py, dj_tarama_kontrol.py, weekly_report.py

= 22.270 satirlik kod (7 modul + 49 test dosyasi) repo disinda kalmisti.
Sonuc: "testler geciyor" izlenimi yanilticiydi — kaybolan testler
kaybolan kodu da tasiyamazdi.

Bu dosya:
  1) Bu modullerin repoda KALMASI icin regresyon korumasi yapar.
  2) Geri getirme sirasinda duzeltilen uyumsuzluklari sabitler
     (sentry opsiyonel, find_highlights, ApprovalResult, tempo 52 saat).
  3) conftest'in DINAMIK toplama korumasini test eder.
"""
import ast
import io
import os
import re

REPO_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Silinmesi ASLA gerekmeyen kritik moduller (CLAUDE.md referanslari)
KRITIK_MODULLER = [
    "derleme.py",              # §5 derleme damgasi politika kapisi
    "generate_cover.py",       # §1 mimari + §6 kapak standardi
    "saglik_kontrol.py",       # saglik kapisi
    "stock_art.py",            # §13 art zorunlulugu
    "dj_clips.py",             # §3/§7 kesit yayini + politika kapisi
    "dj_tarama_kontrol.py",    # §3 DJ tarama
    "weekly_report.py",        # §12 haftalik + gunluk rapor
]

# CLAUDE.md'de adi gecen, repoda OLMAMASI bir regresyon sayilan moduller
CLAUDE_REFERANSLARI = [
    "auto_process.py", "validate_project.py", "render.py", "state_io.py",
    "uyumluluk.py", "notify.py", "gorev_sarmalayici.py", "watch_projects.py",
    "dj_famous_process.py", "ffmpeg_utils.py", "config.py", "elle_islem.py",
]


def _oku(yol):
    p = os.path.join(REPO_KOK, yol)
    assert os.path.isfile(p), "EKSIK DOSYA: %s" % yol
    with io.open(p, encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------------------ moduller
def test_kritik_moduller_repoda_var():
    """2026-10-21'de yanlislikla silinen 7 modul repoda OLMALI."""
    eksik = [m for m in KRITIK_MODULLER
             if not os.path.isfile(os.path.join(REPO_KOK, m))]
    assert not eksik, (
        "KRITIK MODUL SILINMIS: %s\n"
        "Geri getirme: git checkout <silme-commit>^ -- <dosya>" % ", ".join(eksik)
    )


def test_kritik_moduller_import_edilebilir():
    """Modul var ama IMPORT edilemiyorsa (ornegin sentry zinciri) yine olur."""
    import importlib
    for m in KRITIK_MODULLER:
        ad = m[:-3]
        try:
            importlib.import_module(ad)
        except Exception as e:
            pytest_fail = "%s: %s: %s" % (ad, type(e).__name__, str(e)[:120])
            raise AssertionError("IMPORT BASARISIZ — " + pytest_fail)


def test_claude_md_referans_modulleri_var():
    eksik = [m for m in CLAUDE_REFERANSLARI
             if not os.path.isfile(os.path.join(REPO_KOK, m))]
    assert not eksik, "CLAUDE.md'de anilan ama repoda olmayan modul: %s" % eksik


def test_derleme_dosyasi_import_edilebilir():
    """derleme.py: md5 kopya kapisinin kaynagi."""
    ic = _oku("derleme.py")
    assert "md5" in ic.lower()


# ------------------------------------------------------ duzeltilen uyumsuzluklar
def test_sentry_opsiyonel_import():
    """saglik_kontrol sentry'yi ZORUNLU import etmemeli.

    NEDEN: sentry_sdk -> eventlet -> `ssl.wrap_socket` (Python 3.14'te kaldirildi)
    zinciri PATLATIYORDU ve saglik_kontrol hic yuklenemiyordu.
    """
    ic = _oku("saglik_kontrol.py")
    assert "try:" in ic and "import sentry_sdk" in ic
    assert "_SENTRY_VAR" in ic, "sentry opsiyonel bayragi yok"
    # import'un try icinde olmasi
    m = re.search(r"try:\s*\n\s*import sentry_sdk", ic)
    assert m, "sentry importu try/except icinde DEGIL"


def test_audio_highlight_coklu_surum_var():
    """dj_clips.py `find_highlights` bekliyor (coklu + enerji sirasi)."""
    ic = _oku("audio_highlight.py")
    assert "def find_highlights(" in ic
    assert "def find_highlight(" in ic
    # parametreler
    m = re.search(r"def find_highlights\(([^)]*)\)", ic)
    assert m, "find_highlights imzasi okunamadi"
    imza = m.group(1)
    assert "count" in imza, "count parametresi yok"
    assert "min_gap" in imza, "min_gap parametresi yok"


def test_approval_result_indekslenebilir():
    """uyumluluk.kontrol()[0] calismali (eski cagri noktalari)."""
    ic = _oku("tools/approval.py")
    assert "def __getitem__" in ic
    assert "def __iter__" in ic
    assert "def __bool__" in ic


def test_approval_result_liste_tipi():
    """hatalar/uyarilar LISTE olmali — `hatalar == []` karsilastirmasi."""
    ic = _oku("tools/approval.py")
    assert "hatalar: List[str]" in ic
    assert "uyarilar: List[str]" in ic
    assert "hatalar=tuple(" not in ic, "tuple'a donmus olmali (liste kalmali)"


def test_tempo_tabani_52_saat():
    """CLAUDE.md §14: 'Tempo tabanı — 52 saat minimum ara'."""
    ic = _oku("config.py")
    m = re.search(r"MIN_YENI_SARKI_ARALIK_SAAT\s*=\s*(\d+)\s*\*\s*(\d+)", ic)
    assert m, "MIN_YENI_SARKI_ARALIK_SAAT tanimi bulunamadi"
    saat = int(m.group(1))
    assert saat == 52, "Tempo tabani %d saat olmali (CLAUDE.md §14: 52)" % saat


def test_auto_process_tempo_tek_kaynak():
    """auto_process 52 saati config'ten okumali (tek kaynak)."""
    ic = _oku("auto_process.py")
    assert "MIN_YAYIN_ARALIGI_SN = config.MIN_YENI_SARKI_ARALIK_SAAT" in ic


def test_upload_timestamp_keys_tum_platformlar():
    """Günlük pencere YouTube + Shorts + TikTok + Instagram saymali."""
    ic = _oku("auto_process.py")
    m = re.search(r"UPLOAD_TIMESTAMP_KEYS\s*=\s*\(([^)]*)\)", ic, re.S)
    assert m, "UPLOAD_TIMESTAMP_KEYS bulunamadi"
    icerik = m.group(1)
    for anahtar in ("youtube_uploaded_at", "youtube_shorts_uploaded_at",
                    "tiktok_uploaded_at", "instagram_uploaded_at"):
        assert anahtar in icerik, "UPLOAD_TIMESTAMP_KEYS'te %s yok" % anahtar
    # ZAMANLANMIS yayin sayilmaz
    assert "youtube_publish_at" not in icerik, (
        "youtube_publish_at (zamanlanmis) gunluk pencerede sayilmamali")


def test_gunluk_pencere_yeni_sarki_icinde_de():
    """Pencere kuralı 'az önce bir şey paylaştık mı' — platformdan bagimsiz.

    `and not batch_yeni` koşulu geri doldurma paylaşimlarini saymiyordu."""
    ic = _oku("auto_process.py")
    # Yorum satiri "koşulu kaldırıldı" der; KOD koşulu bakilir.
    assert "pencere_kalan > 0 and not batch_yeni" not in ic, (
        "gunluk pencere yeni sarki icinde uygulanmiyor (regresyon)")
    assert "pencere_kalan > 0:" in ic, "gunluk pencere kontrolu bulunamadi"


# ------------------------------------------------------------------ conftest
def test_conftest_dinamik_toplama_korumasi():
    """conftest ELLE liste tutmamali — yeni test dosyalari otomatik korunmali."""
    ic = _oku("conftest.py")
    assert "_toplanamayanlari_bul" in ic, "dinamik tespit fonksiyonu yok"
    assert "collect_ignore" in ic
    # elle yazilmis dosya listesi OLMAZ
    assert "test_netlify_tekrar.py" not in ic, (
        "conftest'te elle dosya listesi var — dinamik olmali")


def test_conftest_attribute_seviyesi_kontrol():
    """`from X import _yok` (X var ama _yok yok) de yakalanmali."""
    ic = _oku("conftest.py")
    assert "_eksik_import_isimleri" in ic
    assert "_modul_adlari" in ic


# ------------------------------------------------------------------ i18n
def test_i18n_tum_sayfalarda():
    """Madde 31: privacy/epk/404 sayfalari da TR/EN olmali."""
    for sayfa in ("site/index.html", "site/privacy.html",
                  "site/epk/bio.html", "site/404.html"):
        ic = _oku(sayfa)
        assert "i18n.js" in ic, "%s: i18n.js yok" % sayfa
        assert "i18n.css" in ic, "%s: i18n.css yok" % sayfa
        assert 'data-dil-btn="en"' in ic, "%s: dil toggle yok" % sayfa
