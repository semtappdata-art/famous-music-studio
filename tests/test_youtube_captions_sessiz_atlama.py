# -*- coding: utf-8 -*-
"""`upload/youtube_captions.py`'nin SESSİZ dallarının artık sessiz olmadığı +
geçici dosya sızıntısının kapandığı.

NEDEN (2026-09-11 denetimi):

1. `sync_captions()` beş ayrı yerden `return "skipped"` diyordu ve HİÇBİRİ iz
   bırakmıyordu; `auto_process._check_youtube_captions()` yalnızca
   "done"/"pending" için log basıyor. Yani "altyazı hattı bu proje için hiç
   çalışmadı"yı öğrenmenin tek yolu videoyu açıp bakmaktı — CLAUDE.md'deki
   "sessizce dönen bir koruma, OLMAYAN korumadan KÖTÜDÜR" maddesinin ta kendisi.

2. `%TEMP%` içinde 19 adet artık `yt_captions_*` klasörü bulundu, her birinde
   yayınlanmış `aligned.srt`. Sebep: `MediaFileUpload` dosyayı açıyor ve HİÇ
   kapatmıyor, Windows açık dosyayı sildirmiyor, `finally`deki `os.remove`
   `OSError` alıp sessizce geçiyordu (`asr.srt`ler `with` ile kapandığı için
   siliniyordu — tam da bu asimetri teşhisi verdi).

Ağa ÇIKMAZ: YouTube istemcisi, ffprobe ve MediaFileUpload sahte.
Log yolu `tests/conftest.py` tarafından geçici klasöre çekiliyor (LOG_PATH).
"""

import io
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import caption_align
import stock_art
import youtube_captions


LYRICS = """Sokak lambasi yanar gece boyunca
Kapiyi kapatirken usulca dondum
Sabah olunca hicbir sey hatirlamam
Yine de burada beklerim seni"""


_VARSAYILAN = object()


def _proje(tmp_path, state=_VARSAYILAN, baslik="Test Sarkisi"):
    d = tmp_path / "Test Sarkisi"
    (d / "output").mkdir(parents=True)
    (d / "output" / youtube_captions.VIDEO_FILENAME).write_bytes(b"sahte mp4")
    (d / "meta.json").write_text(json.dumps({"title": baslik, "theme": "pop"}),
                                 encoding="utf-8")
    # `state={}` BOŞ BİR DURUM demek (video henüz yüklenmemiş) — `or` ile
    # varsayılana düşmemeli, o dal tam olarak test edilen şey.
    if state is _VARSAYILAN:
        state = {"youtube_video_id": "VID123"}
    (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(d)


def _sozler_dosyasi(tmp_path, lyrics=LYRICS, stem="test_sarkisi"):
    p = tmp_path / ("%s_sozler.md" % stem)
    p.write_text("## Temiz Sözler\n```\n%s\n```\n" % lyrics, encoding="utf-8")
    return str(p)


def _asr_srt(lyrics=LYRICS):
    bloklar = []
    t = 1.0
    for i, satir in enumerate(lyrics.splitlines()):
        def ts(x):
            ms = int(round(x * 1000))
            h, ms = divmod(ms, 3600000)
            m, ms = divmod(ms, 60000)
            sn, ms = divmod(ms, 1000)
            return "%02d:%02d:%02d,%03d" % (h, m, sn, ms)
        bloklar.append("%d\n%s --> %s\n%s\n" % (i + 1, ts(t), ts(t + 2.4), satir))
        t += 2.7
    return "\n".join(bloklar).encode("utf-8")


class _SahteIstek:
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        return self._sonuc


class _SahteCaptions:
    def __init__(self, kayit, asr_var=True):
        self.kayit = kayit
        self.asr_var = asr_var

    def list(self, **kw):
        self.kayit.setdefault("list", 0)
        self.kayit["list"] += 1
        items = ([{"id": "ASR1", "snippet": {"trackKind": "asr"}}] if self.asr_var else [])
        return _SahteIstek({"items": items})

    def download(self, **kw):
        self.kayit.setdefault("download", 0)
        self.kayit["download"] += 1
        return _SahteIstek(_asr_srt())

    def insert(self, **kw):
        self.kayit["insert"] = kw
        return _SahteIstek({"id": "MANUEL1"})

    def update(self, **kw):
        self.kayit["update"] = kw
        return _SahteIstek({"id": "MANUEL1"})


class _SahteYoutube:
    def __init__(self, kayit, asr_var=True):
        self._c = _SahteCaptions(kayit, asr_var)

    def captions(self):
        return self._c


class _SahteMedia:
    """Gerçek `MediaFileUpload` gibi dosyayı AÇAR ve kendiliğinden kapatmaz."""
    acik = []

    def __init__(self, path, mimetype=None):
        self._fd = open(path, "rb")
        _SahteMedia.acik.append(self)

    def stream(self):
        return self._fd


@pytest.fixture
def hat(tmp_path, monkeypatch):
    """Ağsız bir sync_captions hattı kurar; kayıt sözlüğünü döner."""
    kayit = {}
    _SahteMedia.acik = []
    monkeypatch.setattr(youtube_captions, "get_authenticated_service",
                        lambda: _SahteYoutube(kayit))
    monkeypatch.setattr(youtube_captions.ffmpeg_utils, "get_audio_duration",
                        lambda p: 20.0)
    monkeypatch.setattr(youtube_captions, "MediaFileUpload", _SahteMedia)

    gecici_kokler = []

    def sahte_mkdtemp(prefix=""):
        d = tmp_path / ("gecici_%s%d" % (prefix, len(gecici_kokler)))
        d.mkdir()
        gecici_kokler.append(str(d))
        return str(d)

    monkeypatch.setattr(youtube_captions.tempfile, "mkdtemp", sahte_mkdtemp)
    kayit["gecici"] = gecici_kokler
    return kayit


def _log_metni():
    if not os.path.isfile(youtube_captions.LOG_PATH):
        return ""
    return io.open(youtube_captions.LOG_PATH, encoding="utf-8").read()


# --- 1) sessiz atlama yok --------------------------------------------------

def test_sozler_dosyasi_yoksa_sebebi_loglanir(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file", lambda t: None)
    assert youtube_captions.sync_captions(_proje(tmp_path)) == "skipped"
    assert "sozler" in _log_metni().lower() or "sözler" in _log_metni().lower()
    assert hat.get("list") is None, "sözler yokken API'ye dokunulmamalı"


def test_render_ciktisi_yoksa_sebebi_loglanir(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    d = _proje(tmp_path)
    os.remove(os.path.join(d, "output", youtube_captions.VIDEO_FILENAME))
    assert youtube_captions.sync_captions(d) == "skipped"
    assert youtube_captions.VIDEO_FILENAME in _log_metni()


def test_gevsek_slug_eslesmesi_reddedilir_ve_loglanir(tmp_path, monkeypatch, hat):
    """Başlık "Test Sarkisi", bulunan dosya `bambaska_bir_sarki` — ön-ek/difflib
    eşleşmesi bunu döndürebiliyor, altyazı hattı KABUL ETMEMELİ."""
    monkeypatch.setattr(
        stock_art, "find_lyrics_file",
        lambda t: _sozler_dosyasi(tmp_path, stem="bambaska_bir_sarki"))
    assert youtube_captions.sync_captions(_proje(tmp_path)) == "skipped"
    assert "benzemiyor" in _log_metni()
    assert hat.get("list") is None


def test_video_yoksa_sessiz_kalir(tmp_path, monkeypatch, hat):
    """TEK sessiz dal: henüz YouTube'a çıkmamış proje. Her koşuda log'a satır
    basmak gürültü olurdu (katalogdaki her bekleyen proje için bir satır)."""
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    once = _log_metni()
    assert youtube_captions.sync_captions(_proje(tmp_path, state={})) == "skipped"
    assert _log_metni() == once


# --- 2) yanlış şarkı kapısı + soğuma penceresi -----------------------------

def test_uyusmazlik_yayinlamaz_ve_damga_birakir(tmp_path, monkeypatch, hat):
    alakasiz = ("Bambaska bir dilde bambaska kelimeler\n"
                "Ortak hicbir seyimiz kalmadi artik\n"
                "Yeni bir sayfa acildi buralarda\n")
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path, lyrics=alakasiz))
    d = _proje(tmp_path)
    # "skipped" DEĞİL, istisna: bu koşuda captions.list+download zaten
    # harcandı; `auto_process` yalnızca istisna/"done"/"pending" hâlinde
    # koşunun geri kalanında başka projeye dokunmayı bırakıyor.
    with pytest.raises(caption_align.LyricsMismatch):
        youtube_captions.sync_captions(d)
    assert "insert" not in hat and "update" not in hat, "yanlış sözler YAYINLANDI"
    st = json.load(io.open(os.path.join(d, "state.json"), encoding="utf-8"))
    assert st.get("youtube_captions_uyusmazlik_at")
    assert not st.get("youtube_captions_done")


def test_uyusmazlik_sogumasi_kotayi_korur(tmp_path, monkeypatch, hat):
    """İkinci koşu API'ye HİÇ dokunmamalı — aksi halde her saat 250 birim."""
    import time
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    d = _proje(tmp_path, state={
        "youtube_video_id": "VID123",
        "youtube_captions_uyusmazlik_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    assert youtube_captions.sync_captions(d) == "skipped"
    assert hat.get("list") is None
    assert "soğuma" in _log_metni()


def test_bozuk_damga_sogumayi_kilitlemez(tmp_path, monkeypatch, hat):
    """Damga okunamıyorsa bekleme YOK — bozuk bir alan altyazıyı KALICI olarak
    engellememeli (sessiz arıza tam olarak böyle doğuyor)."""
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    d = _proje(tmp_path, state={"youtube_video_id": "VID123",
                                "youtube_captions_uyusmazlik_at": "bozuk-damga"})
    assert youtube_captions.sync_captions(d) == "done"


# --- 3) mutlu yol + geçici dosya sızıntısı ---------------------------------

def test_basarili_kosu_gecici_klasor_birakmaz(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    d = _proje(tmp_path)
    assert youtube_captions.sync_captions(d) == "done"
    assert "insert" in hat
    for kok in hat["gecici"]:
        assert not os.path.exists(kok), "geçici klasör sızdı: %s" % kok
    st = json.load(io.open(os.path.join(d, "state.json"), encoding="utf-8"))
    assert st["youtube_captions_done"] is True
    assert st["youtube_captions_synced_at"]


def test_media_dosya_tanitici_kapatiliyor(tmp_path, monkeypatch, hat):
    """Asıl kök neden: açık kalan tanıtıcı yüzünden Windows dosyayı sildirmiyor."""
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    youtube_captions.sync_captions(_proje(tmp_path))
    assert _SahteMedia.acik, "MediaFileUpload hiç kurulmadı — test anlamsız"
    for m in _SahteMedia.acik:
        assert m.stream().closed, "MediaFileUpload tanıtıcısı açık kaldı"


def test_asr_hazir_degilse_pending(tmp_path, monkeypatch):
    kayit = {}
    monkeypatch.setattr(youtube_captions, "get_authenticated_service",
                        lambda: _SahteYoutube(kayit, asr_var=False))
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path))
    assert youtube_captions.sync_captions(_proje(tmp_path)) == "pending"
    assert "download" not in kayit


def test_uyusmazlik_gecici_klasor_birakmaz(tmp_path, monkeypatch, hat):
    """İstisna yolunda da `finally` çalışmalı — sızıntı yalnızca mutlu
    yolda kapanmış olmamalı."""
    alakasiz = chr(10).join(["Bambaska bir dilde bambaska kelimeler",
                             "Ortak hicbir seyimiz kalmadi artik",
                             "Yeni bir sayfa acildi oralarda"])
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _sozler_dosyasi(tmp_path, lyrics=alakasiz))
    with pytest.raises(caption_align.LyricsMismatch):
        youtube_captions.sync_captions(_proje(tmp_path))
    for kok in hat["gecici"]:
        assert not os.path.exists(kok), "geçici klasör sızdı: %s" % kok
