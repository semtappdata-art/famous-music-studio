# -*- coding: utf-8 -*-
"""Altyazı hattında API'den ÖNCE yerel ön kontrol + dar hata soğuması.

NEDEN (2026-09-12, log'dan ölçüldü):

1. `caption_align.align()` sözler dosyasında "## Temiz Sözler" bölümü yoksa düz
   bir RuntimeError atıyordu — ama `align()` `captions.list` + `download`
   (~250 birim) HARCANDIKTAN SONRA çağrılıyor. `auto_process._check_youtube_captions`
   istisnayı "API'ye dokunuldu" (True) sayıyor, `_drain_golden_hour_queue` koşu
   başına tek API hakkını her koşuda o bozuk projeye veriyordu: `Sofraya
   Gelmedin` 08 Eyl 20:12 -> 10 Eyl 08:12 arası 33 ardışık HATA, bu sürede
   `Kader Ortakları` ve `Bu Gece Kazandık` 37,8 saat altyazısız bekledi.

2. Ters hata: `LyricsNotReady` da API harcandıktan sonra atılıyor ama False
   sayılıyordu — hak tükenmediği için döngü sıradaki projede de API'ye gidiyor,
   kota katlanıyordu.

Düzeltme: sözler dosyasının kullanılabilirliği (`align()`'ın kullandığı AYNI
okuyucuyla) API'den önce yerelde kontrol ediliyor; API'de patlayan beklenmedik
istisnalar da proje başına 6 saatlik soğuma damgası bırakıyor (kota hariç).

Ağa ÇIKMAZ: YouTube istemcisi, ffprobe ve MediaFileUpload sahte.
"""

import io
import json
import os
import sys
import time

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap
import caption_align
import notify
import stock_art
import youtube_captions


LYRICS = """Sokak lambasi yanar gece boyunca
Kapiyi kapatirken usulca dondum
Sabah olunca hicbir sey hatirlamam
Yine de burada beklerim seni"""

DAMGA = "%Y-%m-%dT%H:%M:%S"


# --- sahte düzen -----------------------------------------------------------

def _asr_srt(lyrics=LYRICS):
    def ts(x):
        ms = int(round(x * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        sn, ms = divmod(ms, 1000)
        return "%02d:%02d:%02d,%03d" % (h, m, sn, ms)
    bloklar = []
    t = 1.0
    for i, satir in enumerate(lyrics.splitlines()):
        bloklar.append("%d\n%s --> %s\n%s\n" % (i + 1, ts(t), ts(t + 2.4), satir))
        t += 2.7
    return "\n".join(bloklar).encode("utf-8")


class _Istek:
    def __init__(self, sonuc=None, hata=None):
        self._sonuc = sonuc
        self._hata = hata

    def execute(self):
        if self._hata is not None:
            raise self._hata
        return self._sonuc


class _Captions:
    def __init__(self, kayit, list_hatasi=None):
        self.kayit = kayit
        self.list_hatasi = list_hatasi

    def _say(self, ad):
        self.kayit[ad] = self.kayit.get(ad, 0) + 1

    def list(self, **kw):
        self._say("list")
        self.kayit.setdefault("list_video", []).append(kw.get("videoId"))
        if self.list_hatasi is not None:
            return _Istek(hata=self.list_hatasi)
        return _Istek({"items": [{"id": "ASR1", "snippet": {"trackKind": "asr"}}]})

    def download(self, **kw):
        self._say("download")
        return _Istek(_asr_srt())

    def insert(self, **kw):
        self._say("insert")
        return _Istek({"id": "MANUEL1"})

    def update(self, **kw):
        self._say("update")
        return _Istek({"id": "MANUEL1"})


class _Media:
    def __init__(self, path, mimetype=None):
        self._fd = open(path, "rb")

    def stream(self):
        return self._fd


@pytest.fixture
def hat(tmp_path, monkeypatch):
    """Ağsız hat. `kayit["servis"]` = get_authenticated_service çağrı sayısı."""
    kayit = {"servis": 0, "list_hatasi": None}

    class _Youtube:
        def __init__(self):
            self._c = _Captions(kayit, kayit["list_hatasi"])

        def captions(self):
            return self._c

    def servis():
        kayit["servis"] += 1
        return _Youtube()

    monkeypatch.setattr(youtube_captions, "get_authenticated_service", servis)
    monkeypatch.setattr(youtube_captions.ffmpeg_utils, "get_audio_duration",
                        lambda p: 20.0)
    monkeypatch.setattr(youtube_captions, "MediaFileUpload", _Media)
    sayac = []

    def mkdtemp(prefix=""):
        d = tmp_path / ("gecici_%d" % len(sayac))
        sayac.append(1)
        d.mkdir()
        return str(d)

    monkeypatch.setattr(youtube_captions.tempfile, "mkdtemp", mkdtemp)
    # "koşu başına bir kez" hafızası her testte temiz; uyar_bir_kez'in log
    # hedefi (çalışan betiğin LOG_PATH'i) geçici dosyaya.
    monkeypatch.setattr(notify, "_uyarilanlar", set())
    kayit["main_log"] = str(tmp_path / "main.log")
    monkeypatch.setattr(sys.modules["__main__"], "LOG_PATH", kayit["main_log"],
                        raising=False)
    return kayit


def _proje(tmp_path, ad="Test Sarkisi", state=None, baslik=None):
    d = tmp_path / ad
    (d / "output").mkdir(parents=True)
    (d / "output" / youtube_captions.VIDEO_FILENAME).write_bytes(b"sahte mp4")
    (d / "meta.json").write_text(
        json.dumps({"title": baslik or ad, "theme": "pop"}), encoding="utf-8")
    (d / "state.json").write_text(
        json.dumps(state if state is not None else {"youtube_video_id": "VID_" + ad}),
        encoding="utf-8")
    return str(d)


def _md(tmp_path, stem, icerik):
    p = tmp_path / ("%s_sozler.md" % stem)
    p.write_text(icerik, encoding="utf-8")
    return str(p)


def _temiz_md(lyrics=LYRICS):
    return "# Başlık\n\n## Temiz Sözler\n```\n%s\n```\n" % lyrics


BOLUMSUZ_MD = "# Sofraya Gelmedin\n\n## Suno\n[Verse 1]\nbir iki uc\n"
EKSIK_MD = "## Sözler (ekran görüntülerinden — EKSİK, tamamlanmalı)\nbir iki\n"


def _log_metni(kayit):
    parcalar = []
    for yol in (kayit["main_log"], youtube_captions.LOG_PATH):
        if os.path.isfile(yol):
            parcalar.append(io.open(yol, encoding="utf-8").read())
    return "\n".join(parcalar)


def _state(d):
    return json.load(io.open(os.path.join(d, "state.json"), encoding="utf-8"))


def _api_dokunulmadi(kayit):
    assert kayit["servis"] == 0, "get_authenticated_service çağrıldı"
    for ad in ("list", "download", "insert", "update"):
        assert ad not in kayit, "captions.%s çağrıldı" % ad


# --- (a) yerel ön kontrol --------------------------------------------------

def test_temiz_sozler_eksikse_api_cagrisi_yok(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", BOLUMSUZ_MD))
    d = _proje(tmp_path)
    assert youtube_captions.sync_captions(d) == "skipped"
    _api_dokunulmadi(hat)
    assert "Temiz Sözler" in _log_metni(hat)
    assert "Test Sarkisi" in _log_metni(hat)


def test_temiz_sozler_eksik_satiri_kosu_basina_bir_kez(tmp_path, monkeypatch, hat):
    """process_project + drain aynı projeyi aynı koşuda iki kez görebilir."""
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", BOLUMSUZ_MD))
    d = _proje(tmp_path)
    youtube_captions.sync_captions(d)
    youtube_captions.sync_captions(d)
    assert _log_metni(hat).count("Temiz Sözler") == 1


def test_sozler_dosyasi_yoksa_api_cagrisi_yok(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file", lambda t: None)
    assert youtube_captions.sync_captions(_proje(tmp_path)) == "skipped"
    _api_dokunulmadi(hat)


def test_eksik_isaretli_sozler_api_den_once_atlanir(tmp_path, monkeypatch, hat):
    """LyricsNotReady artık API'den ÖNCE: istisna yok, "skipped", çağrı yok."""
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", EKSIK_MD))
    d = _proje(tmp_path)
    assert youtube_captions.sync_captions(d) == "skipped"
    _api_dokunulmadi(hat)
    assert "tamamlanmamış" in _log_metni(hat)


def test_on_kontrol_align_ile_ayni_okuyucuyu_kullanir(tmp_path, monkeypatch, hat):
    """İki ayrı ayrıştırıcı zamanla sapar: ön kontrol ve align() aynı
    `caption_align.temiz_sozleri_oku`dan geçmeli."""
    cagrilar = []
    gercek = caption_align.temiz_sozleri_oku

    def izle(yol):
        cagrilar.append(yol)
        return gercek(yol)

    monkeypatch.setattr(caption_align, "temiz_sozleri_oku", izle)
    yol = _md(tmp_path, "test_sarkisi", _temiz_md())
    monkeypatch.setattr(stock_art, "find_lyrics_file", lambda t: yol)
    assert youtube_captions.sync_captions(_proje(tmp_path)) == "done"
    assert cagrilar == [yol, yol], "ön kontrol + align() aynı okuyucuyu kullanmalı"


def test_temiz_sozler_varsa_hat_normal_calisir(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md()))
    d = _proje(tmp_path)
    assert youtube_captions.sync_captions(d) == "done"
    assert hat["list"] == 1 and hat["insert"] == 1


# --- (b) dar hata soğuması -------------------------------------------------

def test_api_hatasi_sogume_damgasi_birakir_ve_istisna_tasir(tmp_path, monkeypatch, hat):
    hat["list_hatasi"] = RuntimeError("beklenmedik patlama")
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md()))
    d = _proje(tmp_path)
    # İstisna TAŞINMALI: API'ye dokunuldu, auto_process bunu hak tüketimi sayar.
    with pytest.raises(RuntimeError):
        youtube_captions.sync_captions(d)
    st = _state(d)
    assert st.get("youtube_captions_hata_at")
    assert not st.get("youtube_captions_done")


def test_hata_sogumasindaki_proje_api_ye_gitmez(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md()))
    d = _proje(tmp_path, state={
        "youtube_video_id": "VID1",
        "youtube_captions_hata_at": time.strftime(DAMGA),
    })
    assert youtube_captions.sync_captions(d) == "skipped"
    _api_dokunulmadi(hat)
    assert "soğuma" in _log_metni(hat)


def test_hata_sogumasi_6_saat_sonra_biter(tmp_path, monkeypatch, hat):
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md()))
    eski = time.strftime(DAMGA, time.localtime(time.time() - 6 * 3600 - 60))
    d = _proje(tmp_path, state={"youtube_video_id": "VID1",
                                "youtube_captions_hata_at": eski})
    assert youtube_captions.sync_captions(d) == "done"
    assert hat["list"] == 1


def test_hata_sogumasi_suresi_6_saat():
    assert youtube_captions.HATA_BEKLEME_SN == 6 * 3600


def _kota_hatasi():
    from googleapiclient.errors import HttpError

    class _Yanit(dict):
        status = 403
        reason = "Forbidden"

    govde = json.dumps({"error": {
        "code": 403,
        "message": "The request cannot be completed because you have exceeded your quota.",
        "errors": [{"message": "quota", "domain": "youtube.quota",
                    "reason": "quotaExceeded"}]}}).encode("utf-8")
    return HttpError(_Yanit(status="403"), govde, uri="https://sahte")


def test_kota_403_sogume_damgasi_yazmaz(tmp_path, monkeypatch, hat):
    """Kota KANAL düzeyinde; damga yanlış projeyi 6 saat cezalandırırdı."""
    hat["list_hatasi"] = _kota_hatasi()
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md()))
    d = _proje(tmp_path)
    with pytest.raises(Exception):
        youtube_captions.sync_captions(d)
    assert "youtube_captions_hata_at" not in _state(d)


def test_uyusmazlik_hata_damgasi_yazmaz(tmp_path, monkeypatch, hat):
    """LyricsMismatch kendi 24 saatlik soğumasında kalır; ikinci damga yok."""
    alakasiz = "\n".join(["Bambaska bir dilde bambaska kelimeler",
                          "Ortak hicbir seyimiz kalmadi artik",
                          "Yeni bir sayfa acildi oralarda"])
    monkeypatch.setattr(stock_art, "find_lyrics_file",
                        lambda t: _md(tmp_path, "test_sarkisi", _temiz_md(alakasiz)))
    d = _proje(tmp_path)
    with pytest.raises(caption_align.LyricsMismatch):
        youtube_captions.sync_captions(d)
    st = _state(d)
    assert st.get("youtube_captions_uyusmazlik_at")
    assert "youtube_captions_hata_at" not in st


# --- sözleşme: drain'de yerel atlanan proje hakkı TÜKETMEZ -----------------

def _drain_duzeni(tmp_path, monkeypatch, projeler):
    """projeler: [(ad, md_icerigi)] — gerçek _check_youtube_captions +
    gerçek sync_captions; yalnız ağ/ffprobe sahte."""
    dosyalar = {}
    dirs = []
    for ad, icerik in projeler:
        dosyalar[ad] = _md(tmp_path, stock_art._slugify(ad), icerik)
        dirs.append(_proje(tmp_path, ad=ad))
    monkeypatch.setattr(stock_art, "find_lyrics_file", lambda t: dosyalar.get(t))
    # Görünürlük planı drain'in sonunda çalışıyor ve bu testin konusu değil.
    monkeypatch.setattr(ap, "_youtube_gorunurluk_planlarini_uygula", lambda p: None)
    # `_check_youtube_captions` gerçek upload/token.json'a bakıyor; CI'da yok.
    gercek_isfile = os.path.isfile

    def isfile(p):
        if os.path.basename(str(p)) == "token.json":
            return True
        return gercek_isfile(p)

    monkeypatch.setattr(ap.os.path, "isfile", isfile)
    return dirs


def test_drain_bolumsuz_proje_hakki_tuketmez(tmp_path, monkeypatch, hat):
    """Sofraya Gelmedin vakası: A'nın Temiz Sözler'i yok, B sağlam. A hakkı
    TÜKETMEMELİ — B aynı koşuda altyazısını almalı."""
    a, b = _drain_duzeni(tmp_path, monkeypatch, [
        ("Sofraya Gelmedin", BOLUMSUZ_MD),
        ("Kader Ortaklari", _temiz_md()),
    ])
    ap._drain_golden_hour_queue([a, b])
    assert hat.get("list_video") == ["VID_Kader Ortaklari"]
    assert _state(b).get("youtube_captions_done") is True
    assert not _state(a).get("youtube_captions_done")


def test_drain_eksik_isaretli_proje_kotayi_katlamaz(tmp_path, monkeypatch, hat):
    """Ters hata: eksik işaretli A API'ye gidip False dönüyordu, döngü B'de de
    API'ye gidiyordu (koşu başına İKİ proje). Artık tam olarak bir proje."""
    a, b, c = _drain_duzeni(tmp_path, monkeypatch, [
        ("Eksik Sarki", EKSIK_MD),
        ("Ikinci Sarki", _temiz_md()),
        ("Ucuncu Sarki", _temiz_md()),
    ])
    ap._drain_golden_hour_queue([a, b, c])
    assert hat.get("list_video") == ["VID_Ikinci Sarki"]
    assert hat["servis"] == 1
