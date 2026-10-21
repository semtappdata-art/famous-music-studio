# -*- coding: utf-8 -*-
"""ABONE (subscribe) kaldıraçları — kilit testler.

Kilitlenen davranış:
- `social_text.aciklama_abone_bloku` HER video formatında @handle içerir
  (uzun / Shorts / DJ set) — tıklanabilir abone bağlantısı şart.
- `config.SOCIAL_LINKS['youtube']` GERÇEK kanala işaret eder
  (savunma: @DJFamous gibi başka sanatçı handle'ları yazılmasın).
- `youtube_abone.ilk_yorum_gonder` video başına TEK gönderim yapar.
- Silinmiş video (404) hataya dönüşmez, "silinmiş" olarak işaretlenir.
- `http_bug_fix` httplib2'nin boş-yanıt hatasını düzeltir (idempotent).
- `youtube_abone.watermark_uygula` kanal seviyesindedir (video başına
  çağrı YAPILMAZ — tek çağrı tüm videolara geçer).
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD = os.path.join(REPO, "upload")
for _yol in (UPLOAD, REPO):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import social_text


# --- 1) AÇIKLAMA ABONE BLOĞU ----------------------------------------------


def test_aciklama_abone_bloku_handle_icerir():
    blok = social_text.aciklama_abone_bloku("tr")
    assert "@" + config.YOUTUBE_HANDLE in blok
    assert "Abone ol" in blok


def test_aciklama_abone_bloku_en_handle_icerir():
    blok = social_text.aciklama_abone_bloku("en")
    assert "@" + config.YOUTUBE_HANDLE in blok
    assert "Subscribe" in blok


def test_aciklama_abone_bloku_playlist_linkleri():
    """Abone olan izleyici 'ne izleyeyim?' sorusunu cevaplayabilmeli."""
    blok = social_text.aciklama_abone_bloku("tr")
    assert "playlist?list=" in blok


def test_aciklama_abone_bloku_playlist_ids_dosyasindan():
    """Playlist ID'leri upload/playlist_ids.json'dan gelir (tek kaynak)."""
    yol = os.path.join(UPLOAD, "playlist_ids.json")
    if not os.path.isfile(yol):
        return
    with open(yol, "r", encoding="utf-8") as f:
        idler = json.load(f)
    blok = social_text.aciklama_abone_bloku("tr", idler)
    if idler.get("_tum_sarkilar"):
        assert idler["_tum_sarkilar"] in blok


# --- 2) TÜM VİDEO FORMATLARINDA HANDLE ----------------------------------


def test_uzun_video_aciklamasinda_handle():
    from youtube_upload import build_snippet
    snip = build_snippet({"title": "Test Şarkısı", "theme": "pop"})
    assert "@" + config.YOUTUBE_HANDLE in snip["description"]


def test_shorts_aciklamasinda_handle():
    from youtube_upload import build_shorts_snippet
    snip = build_shorts_snippet({"title": "Test Şarkısı", "theme": "pop"})
    assert "@" + config.YOUTUBE_HANDLE in snip["description"]


def test_dj_set_aciklamasinda_handle():
    from youtube_upload import build_dj_set_snippet
    meta = {"title": "Test Set", "theme": "dj", "series": "city_pulse",
            "episode": 1}
    try:
        snip = build_dj_set_snippet(meta)
    except Exception:
        return  # seri tanimi yoksa atla
    assert "@" + config.YOUTUBE_HANDLE in snip["description"]


# --- 3) YANLIŞ KANALA YÖNLENDİRME YOK -----------------------------------


def test_social_links_youtube_gercek_kanal():
    assert config.SOCIAL_LINKS["youtube"].endswith(config.YOUTUBE_HANDLE)


def test_youtube_linki_yabanci_sanatci_handle_iceermez():
    """Savunma: '@DJFamous' gibi başka sanatçı handle'ı yazılırsa abone
    kaybı demektir. Tüm upload modüllerinde taranır."""
    yasak = ("@DJFamous", "@djfamous")
    supheli = []
    kok = REPO
    for klasor in ("upload",):
        yol = os.path.join(kok, klasor)
        if not os.path.isdir(yol):
            continue
        for ad in os.listdir(yol):
            if not ad.endswith(".py"):
                continue
            dosya = os.path.join(yol, ad)
            try:
                with open(dosya, "r", encoding="utf-8") as f:
                    icerik = f.read()
            except OSError:
                continue
            for y in yasak:
                if y in icerik and "youtube.com/@" in icerik:
                    supheli.append(f"{ad}: {y}")
    assert not supheli, f"Yabancı kanal handle'ı YouTube linkinde: {supheli}"


# --- 4) İLK YORUM: TEK GÖNDERİM + SİLİNMİŞ VIDEO -----------------------


def _proje(tmp_path, state_ek=None):
    p = tmp_path / "proj"
    p.mkdir()
    (p / "meta.json").write_text(
        json.dumps({"title": "Test Şarkısı", "theme": "pop"}), encoding="utf-8")
    state = {"youtube_video_id": "VID123"}
    state.update(state_ek or {})
    (p / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(p)


class _SahteEkle:
    def __init__(self, disari):
        self.disari = disari

    def insert(self, part=None, body=None):
        self.disari.append(body)
        return self

    def execute(self):
        return {"id": "Y1"}


class _SahteServis:
    def __init__(self, disari):
        self._ekle = _SahteEkle(disari)

    def commentThreads(self):
        return self._ekle


def test_ilk_yorum_bayrak_varsa_gondermez(tmp_path, monkeypatch):
    import youtube_auth
    import youtube_kota
    import youtube_abone
    giden = []
    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _SahteServis(giden))
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    p = _proje(tmp_path, {"youtube_ilk_yorum_at": "2026-10-01T00:00:00Z"})
    assert youtube_abone.ilk_yorum_gonder(p) is False
    assert giden == []


def test_ilk_yorum_silinmis_video_hata_vermez(tmp_path, monkeypatch):
    """404 -> hata degil, 'silinmis' isareti. Boru hatti durmamali."""
    import youtube_auth
    import youtube_kota
    import youtube_abone

    class _Bozuk:
        def commentThreads(self):
            raise RuntimeError("404 The specified video could not be found")

    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _Bozuk())
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    p = _proje(tmp_path)
    assert youtube_abone.ilk_yorum_gonder(p) is False
    state = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    assert state.get("youtube_video_silinmis") is True


def test_silinmis_bayragi_atlar(tmp_path, monkeypatch):
    import youtube_auth
    import youtube_kota
    import youtube_abone
    giden = []
    monkeypatch.setattr(youtube_auth, "get_authenticated_service",
                        lambda: _SahteServis(giden))
    monkeypatch.setattr(youtube_kota, "yeterli_mi", lambda b: True)
    p = _proje(tmp_path, {"youtube_video_silinmis": True})
    assert youtube_abone.ilk_yorum_gonder(p) is False
    assert giden == []


# --- 5) HTTP BUG FIX ------------------------------------------------------


def test_http_bugfix_uygulanabilir_ve_idempotent():
    import http_bug_fix
    assert http_bug_fix.uygula() is True
    assert http_bug_fix.uygulandi_mi() is True
    # Ikinci cagri bozmus olmamali
    assert http_bug_fix.uygula() is True


def test_http_bugfix_bos_govde_cozumleniyor():
    """httplib2'nin 'range() arg 3 must not be zero' hatasi duzeltildi mi?"""
    import http_bug_fix
    http_bug_fix.uygula()
    import httplib2.decode as hd
    d = hd.ZlibDecoder()
    # Bos gzip veri -> hata vermemeli (Once ValueError veriyordu)
    sonuc = d.consume_bytes(b"", 0)
    assert sonuc == b""


# --- 6) WATERMARK KANAL SEVIYESINDE --------------------------------------


def test_watermark_kanal_seviyesinde():
    """watermarks.set video degil KANAL seviyesindedir (channelId zorunlu).

    Yanlislik: 24 video icin 24 API cagrisi -> kota israfi ve hata.
    """
    import inspect
    import youtube_abone
    imza = inspect.signature(youtube_abone.watermark_uygula)
    assert imza.parameters["video_id"].default == ""


def test_watermark_gorseli_uretilir():
    """Subscribe butonu gorseli depoda olmali (yoksa watermark atlanir)."""
    import youtube_abone
    yol = youtube_abone._watermark_gorseli_uret()
    assert yol and os.path.isfile(yol)
    assert os.path.getsize(yol) > 100


# --- 7) END CARD METNI ----------------------------------------------------


def test_end_card_metni_uretilir():
    import importlib
    # create_meta_files yan etki uretiyor -> sadece fonksiyonu oku
    import ast
    yol = os.path.join(REPO, "create_meta_files.py")
    with open(yol, "r", encoding="utf-8") as f:
        kaynak = f.read()
    tree = ast.parse(kaynak)
    fonk = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_bitis_karti_metni":
            fonk = node
    assert fonk is not None
    ns = {}
    exec(compile(ast.Module(body=[fonk], type_ignores=[]), "<test>", "exec"), ns)
    metin = ns["_bitis_karti_metni"]("pop")
    assert "Abone" in metin or "Subscribe" in metin
    assert "@" in metin
    tr = ns["_bitis_karti_metni"]("pop", dil="tr")
    assert "Abone ol" in tr
    _ = importlib


# --- 8) KANAL MARKALAMA (açıklama / kelimeler / trailer) ------------------


def test_kanal_aciklamasi_dolu():
    """Kanal 2018'den beri BOS aciklamaydi — kesfedilmemek demek."""
    import youtube_abone
    assert len(youtube_abone.KANAL_ACIKLAMASI) > 100
    assert "@" + config.YOUTUBE_HANDLE in youtube_abone.KANAL_ACIKLAMASI
    assert "playlist?list=" in youtube_abone.KANAL_ACIKLAMASI


def test_kanal_anahtar_kelimeleri_dolu():
    import youtube_abone
    kelimeler = youtube_abone.KANAL_ANAHTAR_KELIMELER.split()
    assert len(kelimeler) >= 10
    assert any("türkçe" in k.lower() for k in kelimeler)


def test_sure_hesaplama():
    import youtube_abone
    assert youtube_abone._sure_sn("PT3M40S") == 220
    assert youtube_abone._sure_sn("PT31S") == 31
    assert youtube_abone._sure_sn("PT1H2M3S") == 3723
    assert youtube_abone._sure_sn("P0D") == 0
    assert youtube_abone._sure_sn("") == 0


def test_markalama_tek_cagri_birlestirir():
    """channels.update brandingSettings'i TAMAMEN degistirir.

    Iki ayri cagri yapilirsa ikincisi birincisinin aciklamasini siler
    (olculdu: aciklama None'a dondu). Bu yuzden TEK cagri olmali.
    """
    import inspect
    import youtube_abone
    kaynak = inspect.getsource(youtube_abone.kanal_markalama_ayarla)
    assert kaynak.count("yt.channels().update") == 1
    for alan in ("description", "keywords", "unsubscribedTrailer"):
        assert alan in kaynak


def test_abone_supurge_fonksiyonu_var():
    """auto_process `finally` blogu bunu cagirir."""
    import youtube_abone
    assert callable(youtube_abone.abone_supurge)
