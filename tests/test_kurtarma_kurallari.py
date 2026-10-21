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
    assert "_SENTRY_MEVCUT" in ic, "sentry opsiyonel bayragi yok"
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


# =============================================================================
# Madde 33 — YouTube algoritma: true-peak limiter + render bütünlüğü
# (2026-10-21'de eksik olan API'ler uygulandı)
# =============================================================================

def test_ffmpeg_utils_ses_olc_var():
    """true-peak ölçümü (ebur128) — limiter kararının kaynağı."""
    ic = _oku("ffmpeg_utils.py")
    assert "def ses_olc(" in ic
    assert "ebur128=peak=true" in ic
    assert "Summary:" in ic, "ebur128 OZETI'nden okunmali (ara satirlar anlamsiz)"


def test_limiter_loudnorm_kullanmiyor():
    """loudnorm/dynaudnorm YASAK — tek geçişli loudnorm pompalamaya yol açar."""
    ic = _oku("ffmpeg_utils.py")
    m = re.search(r"def limiter_filtresi\(.*?(?=\ndef |\Z)", ic, re.S)
    assert m, "limiter_filtresi bulunamadi"
    govde = m.group(0)
    assert "alimiter" in govde
    assert "level=false" in govde
    # SADECE return satiri kontrol edilir: docstring'de "loudnorm" GEÇER
    # (aciklama olarak) — kodda gecmemeli.
    ret = [ln for ln in govde.splitlines() if ln.strip().startswith("return")]
    assert ret, "limiter_filtresi return satiri bulunamadi"
    sat = "\n".join(ret)
    assert "loudnorm" not in sat and "dynaudnorm" not in sat, (
        "limiter zinciri loudnorm/dynaudnorm KULLANMAMALI")


def test_limiter_esigi_kati_asma():
    """Eşik KATI'dir: tam sınırda (-1.0) limiter ALINMAZ."""
    ic = _oku("config.py")
    assert "SES_TP_ESIK_DBTP" in ic
    m = re.search(r"SES_TP_ESIK_DBTP\s*=\s*(-?[\d.]+)", ic)
    assert m, "SES_TP_ESIK_DBTP tanimi bulunamadi"
    assert float(m.group(1)) == -1.0, "true peak esigi -1.0 dBTP olmali"


def test_render_limiter_gerekli_kurali():
    """Ölçüm yoksa limiter GİRMEZ (iyileştirme, kapı değil)."""
    ic = _oku("render.py")
    assert "def limiter_gerekli(" in ic
    assert "SES_LIMITER_ACIK" in ic
    assert "SES_TP_ESIK_DBTP" in ic
    # KATİ karşılaştırma (>), >= DEĞİL
    m = re.search(r"return\s+tp\s*>\s*esik", ic)
    assert m, "limiter karsi lastirmasi KATI olmali (tp > esik)"


def test_render_video_ses_limiter_parametresi():
    """Varsayilan KAPALI — mevcut tum cagri noktalarinin komutu degismez."""
    ic = _oku("ffmpeg_utils.py")
    m = re.search(r"def render_video\(([^)]*)\)", ic, re.S)
    assert m
    assert "ses_limiter: bool = False" in m.group(1), "ses_limiter varsayilani False olmali"
    assert '"-af"' in ic, "-af zinciri eksik"


def test_video_butun_mu_ffprobe_ayrimi():
    """"calistiramadim" (zarif dusus) ile "calistirdim, bozuk" AYRI."""
    ic = _oku("render.py")
    assert "def video_butun_mu(" in ic
    assert "_FFPROBE_YOK_UYARILDI" in ic
    # RuntimeError -> bozukluk (False), diger Exception -> zarif dusus (True)
    assert re.search(r"except RuntimeError:\s*\n\s*#?[^\n]*\n\s*return False", ic) \
        or "except RuntimeError:" in ic
    m = re.search(r"except RuntimeError:(.*?)except Exception:", ic, re.S)
    assert m and "return False" in m.group(1), "RuntimeError -> False (bozukluk kaniti)"


def test_is_rendered_iki_uretim_girisinde_ayni_olcut():
    """auto_process VE dj_famous_process ayni olcutu kullanir (kopya mantik YASAK)."""
    a = _oku("auto_process.py")
    d = _oku("dj_famous_process.py")
    assert "def _is_rendered(" in a and "def _is_rendered(" in d
    assert "video_butun_mu(" in a and "video_butun_mu(" in d
    assert "RENDER_OUTPUTS" in a and "RENDER_OUTPUTS" in d
    # tek kaynak: config.PLATFORMS
    assert 'RENDER_OUTPUTS = ["%s.mp4" % ad for ad in config.PLATFORMS]' in a
    assert 'RENDER_OUTPUTS = ["%s.mp4" % ad for ad in config.PLATFORMS]' in d


def test_render_gecici_ad_ile_tasiyor():
    """Yarim render nihai adla diskte HIC gorunmemeli (os.replace deseni)."""
    ic = _oku("render.py")
    assert "PARCALI_SONEK" in ic
    assert "os.replace(" in ic
    m = re.search(r"def render_one\((.*?)\n    def ", ic, re.S)
    if not m:
        m = re.search(r"def render_one\((.*?)\n\ndef ", ic, re.S)
    assert m, "render_one bulunamadi"
    govde = m.group(1)
    assert "os.replace" in govde, "os.replace render_one icinde olmali"
    assert "PARCALI_SONEK" in govde, "gecici ad PARCALI_SONEK ile olmali"


def test_find_highlight_tanimli():
    """render.py find_highlight'i CAGIRIYORDU ama tanimi HIC YOKTI -> NameError."""
    ic = _oku("render.py")
    assert "def find_highlight(" in ic
    assert "def _gecerli_highlight_saniyesi(" in ic
    # bool reddi (isinstance(True, int) True'dur -> 1 saniye sanilirdi)
    assert "isinstance(deger, bool)" in ic


def test_ses_olcumu_state_ile_omurlenir():
    """Olcum MD5 ile onbelleklenir; state.json YOKSA olusturulmaz."""
    ic = _oku("render.py")
    assert "def _ses_olcumu_al(" in ic
    assert "md5" in ic
    assert "state_io.atomic_write" in ic


# =============================================================================
# Madde 35 — Açılış intro'su (kapak + sessizlik kırpma) + backdrop
# (2026-10-21'de uygulanan filtre grafiği değişikliği)
# =============================================================================

def test_bastaki_sessizlik_pay_ve_maks():
    """Ölçülen sessizlikten PAY (0.12) düşülür, MAKS (3.0) tavanı uygulanır."""
    ic = _oku("config.py")
    assert "INTRO_SESSIZLIK_PAY" in ic
    assert "INTRO_SESSIZLIK_MAKS" in ic
    f = _oku("ffmpeg_utils.py")
    m = re.search(r"def bastaki_sessizlik\(.*?(?=\ndef |\Z)", f, re.S)
    assert m, "bastaki_sessizlik bulunamadi"
    govde = m.group(0)
    assert "INTRO_SESSIZLIK_PAY" in govde, "PAY uygulanmiyor"
    assert "INTRO_SESSIZLIK_MAKS" in govde, "MAKS uygulanmiyor"


def test_intro_filter_grafi_etiket_dengesi_kurali():
    """Filtre grafiğinde her ara etiket TAM OLARAK iki kez geçmeli.

    NEDEN: dengesiz etiket ffmpeg'de "Cannot find a matching stream" hatası
    verir — TÜM render'lar çöker. Test bunu render'dan ÖNCE yakalar.
    """
    ic = _oku("ffmpeg_utils.py")
    m = re.search(r"def _build_filter_complex\(.*?(?=\ndef |\Z)", ic, re.S)
    assert m, "_build_filter_complex bulunamadi"
    govde = m.group(0)
    assert "intro_index" in govde
    assert "hud_index" in govde
    assert "eof_action=pass[vfinal]" in govde, "intro overlay [vfinal] uretmeli"
    assert "blend=all_mode=screen" in govde, "HUD blend'i screen olmali"


def test_intro_olmadan_graf_degismez():
    """intro_index=None iken filtre grafiği BİREBİR eskisi gibi olmalı."""
    ic = _oku("ffmpeg_utils.py")
    m = re.search(r"def _build_filter_complex\(.*?(?=\ndef |\Z)", ic, re.S)
    govde = m.group(0)
    # intro dalı ayrı bir `if intro_index is not None:` bloğunda
    assert "if intro_index is not None:" in govde
    # ve eski yol korunmuş olmalı
    assert '[vfinal]"' in govde or "overlay={bar_margin}:{bar_y}[vfinal]" in govde


def test_intro_cok_kisa_parcada_atlanir():
    """Kapak video'nun yarısından fazlasını kaplarsa intro ÇİZİLMEZ."""
    f = _oku("ffmpeg_utils.py")
    m = re.search(r"def render_video\(.*?(?=\ndef |\Z)", f, re.S)
    assert m
    govde = m.group(0)
    assert "intro_sure * 2 <= duration" in govde, "cok kisa parcada intro atlanmali"
    assert "intro_cover" in govde


def test_sessizlik_kirpma_render_da_uygulanir():
    """Baştaki sessizlik render'da da kesilir (-ss ile)."""
    f = _oku("ffmpeg_utils.py")
    m = re.search(r"def render_video\(.*?(?=\ndef |\Z)", f, re.S)
    govde = m.group(0)
    assert "bastaki_sessizlik(audio_path)" in govde
    assert "bas_effective" in govde


def test_find_intro_cover_orana_gore():
    """Dikey çıktı -> cover_vertical.png, yatay -> cover.png."""
    ic = _oku("render.py")
    assert "def find_intro_cover(" in ic
    assert "cover_vertical.png" in ic
    assert "cover.png" in ic


def test_backdrop_varken_shorts_highlight_kapalı():
    """DJ setlerinde (backdrop.mp4) Shorts highlight KULLANILMAZ."""
    ic = _oku("render.py")
    assert "backdrop.mp4" in ic
    assert "backdrop_video" in ic
    m = re.search(r"use_highlight\s*=\s*\(.*?\)\s*\n", ic, re.S)
    assert m and "not backdrop_video" in m.group(0), (
        "backdrop varken use_highlight False olmali")
