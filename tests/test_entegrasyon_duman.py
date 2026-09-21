# -*- coding: utf-8 -*-
"""ENTEGRASYON duman testleri — modüller ARASINDAKİ sözleşmeler.

NEDEN VAR (2026-09-11): bu depoda o gün ~20 dosya paralel ajanlarla değişti ve
268 birim testi geçiyordu; ama birim testler her modülü TEK BAŞINA doğruluyor.
Uçtan uca ilk koşuda iki kırık çıktı ve ikisi de tam olarak "iki ajan aynı
sözleşmenin iki ucuna ayrı ayrı dokundu" sınıfındaydı:

  1. `dj_famous_process.log()` maskelemiyor. Modül `gizli_maskele.maskele`'yi
     IMPORT ediyor, docstring'i "log'a yazılan HER metin buradan geçiyor"
     diyor, ama `log()` gövdesinde çağrı YOK. `auto_process.log()`'ta var.
     Sızıntının GERÇEKTEN yaşandığı dosya (2026-09-04, Instagram token'ı)
     `dj_famous_process.log`'un ta kendisiydi.
  2. `upload/` altında ÜÇ modül state.json'ı hâlâ hedefin ÜSTÜNE yazıyor
     (`open(..., "w")` + `json.dump`). Bu, `state_io.py`'nin var olma
     sebebinin tam tersi ve bedeli bugün büyüdü: `uyumluluk._durum()` artık
     bozuk bir state.json'ı HATA sayıp boru hattını DURDURUYOR, yani yarım
     kalan tek bir yazım tüm yayını durduruyor.

DURUM (2026-09-11, aynı gün): (1) düzeltildi — `dj_famous_process.log()` artık
`maskele()`'den geçiyor. (2)'nin üçte ikisi düzeltildi:
`upload/youtube_captions.py` ve `upload/youtube_stats.py` (iki yazım noktası da)
`state_io`'ya göçtü; `upload/youtube_playlists.py` de (paralel bir ajan
tarafından) göçmüş durumda. `xfail(strict=True)` işaretlerinin HEPSİ KALDIRILDI —
bu iddialar artık süiti yeşil tutan gerçek korumalar, geri kırılırsa KIRMIZI
yanarlar. (Üçüncü kırık, kapak ayracının başlık kuyruklarını kesmesi, ayrı bir
dosyada: tests/test_kapak_ayrac_geometri.py.)
"""

import importlib.util
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

# Sahte ama gerçek DESENLERE uyan kimlik bilgileri (bkz. gizli_maskele._DESENLER).
SAHTE_META_TOKEN = "EAAGm0PX4ZCpsBO7SAHTEfakeTOKEN99xyz"
SAHTE_BOT_TOKEN = "123456789:AAFsahteBOTtokenABCDEFGHIJKLMNOPQRSTUV"


def _bagimsiz_yukle(dosya_adi, modul_adi, tmp_path):
    """Bir script'i BAĞIMSIZ yükler ve LOCK/LOG yollarını tmp_path'e çeker.

    tests/test_auto_process_kilit.py ile aynı desen: gerçek `.lock` ve `.log`
    dosyalarına dokunulmamalı — bu makinede canlı bir yayın sürüyor olabilir ve
    `watch_projects.py`'nin nabız gözcüsü `auto_process.log`'un mtime'ına
    bakıyor."""
    spec = importlib.util.spec_from_file_location(
        modul_adi, os.path.join(_KOK, dosya_adi))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modul_adi] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(modul_adi, None)
    mod.LOCK_PATH = str(tmp_path / (modul_adi + ".lock"))
    mod.LOG_PATH = str(tmp_path / (modul_adi + ".log"))
    return mod


# --- 1. İKİ SCRIPT'İN log()'u AYNI SÖZLEŞMEYE UYMALI ------------------------

@pytest.mark.parametrize("dosya, ad", [
    ("auto_process.py", "_ent_ap"),
    # xfail KALDIRILDI (2026-09-11): dj_famous_process.log() artık maskele()'den
    # geçiyor. Bu satır bundan sonra gerçek bir koruma — yeniden kırılırsa süit
    # KIRMIZI yanar.
    ("dj_famous_process.py", "_ent_dj"),
])
def test_log_token_sizdirmiyor(dosya, ad, tmp_path):
    """log() ~14-20 `log(f"... HATA: {e}")` çağrısının TEK savunma noktası."""
    m = _bagimsiz_yukle(dosya, ad, tmp_path)
    try:
        raise ConnectionError(
            "HTTPSConnectionPool: /v23.0/me?access_token=%s&fields=id"
            % SAHTE_META_TOKEN)
    except ConnectionError as e:
        m.log(f"  Instagram HATA: {e}")
    try:
        raise ConnectionError(
            "POST https://api.telegram.org/bot%s/sendVideo" % SAHTE_BOT_TOKEN)
    except ConnectionError as e:
        m.log(f"  Telegram HATA: {e}")

    icerik = open(m.LOG_PATH, encoding="utf-8").read()
    assert SAHTE_META_TOKEN not in icerik, "Meta token'ı log'a düz metin düştü"
    assert SAHTE_BOT_TOKEN not in icerik, "Telegram bot token'ı log'a düz metin düştü"
    # Satır TANILANABİLİR kalmalı — maskeleme log'u kullanılmaz hale getirmemeli.
    assert "Instagram HATA" in icerik
    assert "Telegram HATA" in icerik


def test_log_normal_satiri_bozmaz_iki_scriptte_de(tmp_path):
    for dosya, ad in (("auto_process.py", "_ent_ap2"),
                      ("dj_famous_process.py", "_ent_dj2")):
        m = _bagimsiz_yukle(dosya, ad, tmp_path)
        m.log("3 bekleyen proje var (1): gece_surusu")
        assert "gece_surusu" in open(m.LOG_PATH, encoding="utf-8").read()


# --- 2. upload/* state.json YAZIMI ATOMİK OLMALI ---------------------------

def _proje(tmp_path, ad):
    p = tmp_path / ad
    p.mkdir()
    (p / "meta.json").write_text(
        json.dumps({"title": "Duman", "theme": "hiphop"}), encoding="utf-8")
    (p / "state.json").write_text(
        json.dumps({"youtube_video_id": "abc123"}), encoding="utf-8")
    return str(p)


def _atomik_mi(modul_adi, fonksiyon_adi, proje_yolu, monkeypatch):
    """`fn(proje, {...})` çağrısı state.json'a `.tmp` + `os.replace` ile mi yazdı?"""
    modul = __import__(modul_adi)
    fn = getattr(modul, fonksiyon_adi)
    izler = []
    gercek = os.replace

    def izli(src, dst, *a, **kw):
        izler.append((str(src), str(dst)))
        return gercek(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", izli)
    fn(proje_yolu, {"duman": True})
    return any(d.endswith("state.json") and s.endswith(".tmp") for s, d in izler)


@pytest.mark.parametrize("modul, fonksiyon", [
    ("bluesky_upload", "_save_state"),
    ("facebook_upload", "_save_state"),
    ("instagram_upload", "_save_state"),
    ("telegram_upload", "_save_state"),
    ("youtube_upload", "_update_state"),
    # xfail'ler KALDIRILDI (2026-09-11): üç modül de state_io'ya göçtü —
    # youtube_captions/_update_state ve youtube_stats (ayrı testlerde, aşağıda)
    # bu oturumda, youtube_playlists/_update_state ise paralel bir ajan
    # tarafından (state_io.durum_yaz, youtube_playlists.py:142). Üçü de artık
    # gerçek koruma; geri kırılırsa süit KIRMIZI yanar.
    ("youtube_captions", "_update_state"),
    ("youtube_playlists", "_update_state"),
])
def test_state_yazimi_atomik(modul, fonksiyon, tmp_path, monkeypatch):
    """Yarım kalan bir yazım artık YAYINI DURDURUYOR (uyumluluk._durum ->
    DurumBozuk -> HATA), bu yüzden her yazan modül state_io'dan geçmeli."""
    p = _proje(tmp_path, modul)
    assert _atomik_mi(modul, fonksiyon, p, monkeypatch), (
        "%s.%s state.json'ı doğrudan üstüne yazıyor" % (modul, fonksiyon))
    # Yazım gerçekten işini de görmüş olmalı.
    assert json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())["duman"]


class _SahteYouTube:
    """videos().list(...).execute() — AĞA ÇIKMAZ, sabit istatistik döndürür."""

    def __init__(self, istatistik):
        self._ist = istatistik

    def videos(self):
        return self

    def list(self, **kw):
        self._idler = [i for i in kw.get("id", "").split(",") if i]
        return self

    def execute(self):
        return {"items": [{"id": v, "statistics": self._ist} for v in self._idler]}


def test_youtube_stats_toplu_yazim_atomik(tmp_path, monkeypatch):
    """upload/youtube_stats.get_stats_batch state.json'ları ATOMİK yazmalı.

    Eskiden burada bir KAYNAK-GREP testi vardı ("hâlâ doğrudan yazıyor" diye
    işaretleyen) — düzeltme yapılınca silinmesi gerekiyordu. Yerine geçen bu
    test asıl riski sürüyor: `get_stats_batch` saatlik koşuda ONLARCA projenin
    state.json'ını art arda yazıyor (döngü), yani yarıda kesilen tek bir yazım
    `uyumluluk._durum()` -> DurumBozuk -> HATA ile o projeyi yayın dışı
    bırakırdı. Ağa ÇIKMIYOR: get_authenticated_service sahtesiyle değiştirildi.
    """
    import youtube_stats

    kok = tmp_path / "kok"
    kok.mkdir()
    projeler = []
    for i in range(3):
        p = kok / ("proje%d" % i)
        p.mkdir()
        (p / "state.json").write_text(
            json.dumps({"youtube_video_id": "vid%d" % i,
                        "youtube_shorts_video_id": "short%d" % i}),
            encoding="utf-8")
        projeler.append(p)

    monkeypatch.setattr(youtube_stats, "get_authenticated_service",
                        lambda: _SahteYouTube({"viewCount": "42",
                                               "likeCount": "7",
                                               "commentCount": "1"}))

    izler = []
    gercek = os.replace

    def izli(src, dst, *a, **kw):
        izler.append((str(src), str(dst)))
        return gercek(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", izli)
    sonuc = youtube_stats.get_stats_batch(base=str(kok), force=True)

    assert sonuc["proje"] == 3, "üç projenin de state.json'ı yazılmalıydı"
    # Her yazım .tmp -> state.json taşıması olmalı (state_io._atomik_yaz).
    atomik = [(s, d) for s, d in izler
              if d.endswith("state.json") and s.endswith(".tmp")]
    assert len(atomik) == 3, (
        "get_stats_batch state.json'ları doğrudan üstüne yazıyor "
        "(atomik taşıma sayısı: %d)" % len(atomik))
    # Yazım gerçekten işini de görmüş olmalı.
    for p in projeler:
        st = json.loads((p / "state.json").read_text(encoding="utf-8"))
        assert st["youtube_views"] == 42
        assert st["youtube_shorts_views"] == 42


class _SahteYouTubeDurumlu(_SahteYouTube):
    """get_stats `part="statistics,status"` istiyor ve items[0]["status"]'a
    bakıyor — toplu sahteden tek farkı bu alan."""

    def execute(self):
        return {"items": [{"id": v, "statistics": self._ist,
                           "status": {"privacyStatus": "public"}}
                          for v in self._idler]}


def test_youtube_stats_tekil_yazim_atomik(tmp_path, monkeypatch):
    """get_stats() (tekil, --project yolu) da state_io'dan geçmeli."""
    import youtube_stats

    p = tmp_path / "tek"
    p.mkdir()
    (p / "state.json").write_text(json.dumps({"youtube_video_id": "vidX"}),
                                  encoding="utf-8")
    monkeypatch.setattr(
        youtube_stats, "get_authenticated_service",
        lambda: _SahteYouTubeDurumlu({"viewCount": "9", "likeCount": "2",
                                      "commentCount": "0"}))

    izler = []
    gercek = os.replace

    def izli(src, dst, *a, **kw):
        izler.append((str(src), str(dst)))
        return gercek(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", izli)
    youtube_stats.get_stats(str(p))

    assert any(d.endswith("state.json") and s.endswith(".tmp") for s, d in izler), (
        "get_stats state.json'ı doğrudan üstüne yazıyor")
    assert json.loads((p / "state.json").read_text(encoding="utf-8"))["youtube_views"] == 9


# --- 3. BOZUK state.json KAPISI GERÇEKTEN HATTI DURDURUYOR MU --------------

def test_bozuk_state_render_kapisini_durduruyor(tmp_path, monkeypatch):
    """uyumluluk.kontrol -> validate_project.validate -> render.render_project
    zinciri: bozuk state.json RENDER'a hiç girilmemesini sağlamalı."""
    import uyumluluk
    import validate_project

    p = _proje(tmp_path, "bozuk")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(tmp_path),))
    (os.path.join(p, "state.json"))
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        f.write('{"youtube_video_id": "abc", "youtube_view')   # YARIM JSON

    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert any("state.json" in h for h in hatalar), "bozuk state.json HATA üretmedi"

    # validate_project bu hatayı YUKARI TAŞIMALI (render.py buna bakıp duruyor).
    v_hatalar, _ = validate_project.validate(p)
    assert any("state.json" in h for h in v_hatalar), (
        "uyumluluk hatası validate_project'ten dışarı çıkmadı — render durmaz")


def test_bozuk_meta_sadece_uyari(tmp_path, monkeypatch):
    """meta.json'da durum TERS: bozuk meta bir kapı AÇMIYOR, yalnızca uyarı."""
    import uyumluluk

    p = _proje(tmp_path, "bozukmeta")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(tmp_path),))
    with open(os.path.join(p, "meta.json"), "w", encoding="utf-8") as f:
        f.write('{"title": "Bozuk"')

    hatalar, uyarilar = uyumluluk.kontrol(p, "render")
    assert not any("meta.json" in h for h in hatalar)
    assert any("meta.json" in u for u in uyarilar)


# --- 4. ÇAĞRI SIRASI: Shorts playlist'e girmeli ----------------------------

def _cagri_satirlari(fonksiyon_adi, isimler):
    """dj_famous_process.<fonksiyon> içinde verilen çağrıların satır no'ları."""
    import ast

    agac = ast.parse(open(os.path.join(_KOK, "dj_famous_process.py"),
                          encoding="utf-8").read())
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == fonksiyon_adi)
    bulunan = {ad: [] for ad in isimler}
    for d in ast.walk(fn):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
                and d.func.id in bulunan:
            bulunan[d.func.id].append(d.lineno)
    return bulunan


def test_shorts_yuklendikten_SONRA_da_playlist_senkronu_var():
    """Short'un playlist'e girmesi, çağrının SIRASINA bağlı.

    GERÇEK ARIZA (2026-09-11): `process_set` içindeki tek `sync_project`
    çağrısı hem Content ID kapısından hem Shorts yüklemesinden ÖNCEydi — o an
    state.json'da `youtube_shorts_video_id` henüz YOK, yani Short hiçbir
    listeye girmiyordu. Derlemenin Short'unda (6Ha3xm3mw74) gerçekleşti ve
    elle eklenmek zorunda kalındı.

    Bu, deponun klasik "bağlantı arızası": çağrı VAR, kendi içinde doğru,
    grep'le eksik görünmüyor — sadece YANLIŞ YERDE. Bu yüzden varlığı değil
    SIRASI test ediliyor. İlk çağrı da korunmalı: Content ID kapısı `return`
    ettiğinde ikinciye hiç gelinmiyor, karantinadaki uzun formatı listeye
    koyan o ilk çağrıdır."""
    s = _cagri_satirlari("process_set", ("yt_upload_short", "yt_sync_playlist"))
    shorts = s["yt_upload_short"]
    playlist = s["yt_sync_playlist"]

    assert shorts, "process_set içinde Shorts yükleme çağrısı bulunamadı"
    assert len(playlist) >= 2, (
        "process_set içinde %d playlist senkronu var; Shorts ÖNCESİ ve SONRASI "
        "olmak üzere en az iki tane olmalı" % len(playlist))
    assert any(p > max(shorts) for p in playlist), (
        "playlist senkronu yalnızca Shorts yüklemesinden ÖNCE çağrılıyor — "
        "o an youtube_shorts_video_id state'te yok, Short listeye girmez")
    assert any(p < min(shorts) for p in playlist), (
        "Shorts ÖNCESİNDEKİ playlist senkronu kaybolmuş — Content ID "
        "karantinasında bekleyen uzun format hiçbir listeye girmez")
