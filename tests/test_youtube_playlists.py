# -*- coding: utf-8 -*-
"""upload/youtube_playlists.py — ÜÇ katmanlı playlist yapısı.

NEDEN BU TESTLER VAR (2026-09-11, kanalın gerçek durumu ölçüldükten sonra):
kanalda 41 videonun 21'i HİÇBİR playlist'te değildi ve bunu haber veren hiçbir
mekanizma yoktu. İki ayrı sessiz arıza vardı, ikisi de "fonksiyon doğru ama
BAĞLANTI eksik" sınıfından (bkz. CLAUDE.md):

  1. `sync_project` sadece `youtube_video_id`'ye (uzun format) bakıyordu;
     `youtube_shorts_video_id` hiç okunmuyordu. 20 Shorts'un tamamı kapsam
     dışıydı ve log'a tek satır düşmedi.
  2. Kapı `state.json`daki `youtube_playlist_id` idi — YEREL bir iddia.
     "Beton Krallığı"nda o alan DOLU ama video listede DEĞİL (eski video
     silinip yeniden yüklendi); alan dolu olduğu için bir daha DENENMEDİ.

Aşağıdaki testler bu iki davranışı çiviliyor.
"""

import importlib.util
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))


def _yukle(tmp_path):
    """Modülü BAĞIMSIZ yükler ve playlist_ids.json'ı tmp'ye çeker.

    Üretimdeki `upload/playlist_ids.json` gerçek kanal ID'lerini tutuyor ve
    repoya commit'li — bir test onu üzerine yazarsa kanalın playlist'leri
    "kayıp" görünür ve bir sonraki koşuda İKİNCİ kopyaları oluşturulur."""
    spec = importlib.util.spec_from_file_location(
        "yt_playlists_test", os.path.join(_KOK, "upload", "youtube_playlists.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["yt_playlists_test"] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop("yt_playlists_test", None)
    mod.PLAYLIST_IDS_PATH = str(tmp_path / "playlist_ids.json")
    mod._UYE_ONBELLEK.clear()
    return mod


class _Istek:
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        return self._sonuc


class _PlaylistItems:
    def __init__(self, api):
        self._api = api

    def list(self, part=None, playlistId=None, maxResults=None):
        self._api.okuma += 1
        return _Istek({"items": [
            {"contentDetails": {"videoId": v}}
            for v in self._api.icerik.get(playlistId, [])
        ]})

    def list_next(self, req, resp):
        return None                      # tek sayfa yeter

    def insert(self, part=None, body=None):
        pid = body["snippet"]["playlistId"]
        vid = body["snippet"]["resourceId"]["videoId"]
        self._api.eklemeler.append((pid, vid))
        self._api.icerik.setdefault(pid, []).append(vid)
        return _Istek({"id": "PLI_%d" % len(self._api.eklemeler)})


class _Playlists:
    def __init__(self, api):
        self._api = api

    def insert(self, part=None, body=None):
        self._api.olusturulan.append(body["snippet"]["title"])
        yeni = "PLYENI%d" % len(self._api.olusturulan)
        self._api.icerik[yeni] = []
        return _Istek({"id": yeni})


class SahteYouTube:
    """playlistItems.list/insert + playlists.insert taklidi.

    `okuma` ve `eklemeler` KOTA sayaçları: okuma 1 birim, ekleme 50 birim."""

    def __init__(self, icerik=None):
        self.icerik = dict(icerik or {})
        self.eklemeler = []
        self.olusturulan = []
        self.okuma = 0

    def playlistItems(self):
        return _PlaylistItems(self)

    def playlists(self):
        return _Playlists(self)


def _proje(tmp_path, kok, ad, state, theme="pop"):
    d = tmp_path / kok / ad
    d.mkdir(parents=True)
    (d / "meta.json").write_text(
        json.dumps({"title": ad, "theme": theme}), encoding="utf-8")
    (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(d)


# --- kota koruması --------------------------------------------------------


def test_zaten_ekliyse_insert_cagrilmaz(tmp_path):
    """50 birimlik yazımdan önce 1 birimlik okuma — yoksa her koşu kotayı yer."""
    m = _yukle(tmp_path)
    yt = SahteYouTube({"PL1": ["VID1"]})
    assert m.ekle(yt, "PL1", "VID1") is False
    assert yt.eklemeler == []


def test_eksikse_eklenir_ve_onbellek_tazelenir(tmp_path):
    m = _yukle(tmp_path)
    yt = SahteYouTube({"PL1": []})
    assert m.ekle(yt, "PL1", "VID1") is True
    assert yt.eklemeler == [("PL1", "VID1")]
    # İkinci çağrı ARTIK yazmamalı: önbellek güncellendiyse yeni okuma da yok.
    okuma_once = yt.okuma
    assert m.ekle(yt, "PL1", "VID1") is False
    assert yt.okuma == okuma_once
    assert len(yt.eklemeler) == 1


def test_playlist_basina_tek_okuma(tmp_path):
    """`auto_process.py` her projede sync_project çağırıyor; önbellek olmasa
    her proje için ayrı bir liste okuması yapılırdı."""
    m = _yukle(tmp_path)
    yt = SahteYouTube({"PL1": ["A", "B"]})
    m.playlist_videolari(yt, "PL1")
    m.playlist_videolari(yt, "PL1")
    assert yt.okuma == 1


# --- kapı artık YEREL state DEĞİL ----------------------------------------


def test_state_dolu_ama_video_listede_degilse_YİNE_eklenir(tmp_path):
    """"Beton Krallığı" vakası: state `youtube_playlist_id` DOLU ama video
    playlist'te yok (silinip yeniden yüklendi). Eski sürüm bu alana bakıp
    atlıyordu — kapsam boşluğu sessizce kalıcı oluyordu."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, "projects", "Beton", {
        "youtube_video_id": "YENIID",
        "youtube_playlist_id": "PLTARZ",     # yerel iddia — YANLIŞ
    }, theme="hiphop")
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps({"hiphop": "PLTARZ", "_tum_sarkilar": "PLZINCIR"}),
        encoding="utf-8")
    yt = SahteYouTube({"PLTARZ": ["ESKIID"], "PLZINCIR": []})
    m.sync_project(yt, p)
    assert ("PLTARZ", "YENIID") in yt.eklemeler


# --- Shorts ---------------------------------------------------------------


def test_shorts_de_bir_playliste_giriyor(tmp_path):
    """Asıl regresyon: 20 Shorts'un tamamı hiçbir listede değildi."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, "projects", "Sarki", {
        "youtube_video_id": "UZUN1",
        "youtube_shorts_video_id": "KISA1",
    })
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps({"pop": "PLPOP", "_tum_sarkilar": "PLZ", "_shorts": "PLS"}),
        encoding="utf-8")
    yt = SahteYouTube({"PLPOP": [], "PLZ": [], "PLS": []})
    m.sync_project(yt, p)
    assert ("PLS", "KISA1") in yt.eklemeler
    durum = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    assert durum["youtube_shorts_playlist_id"] == "PLS"


def test_shorts_uzun_formatin_zincirine_KARISMAZ(tmp_path):
    """Her Short aynı şarkının dikey kesiti — aynı listede olsalardı dinleyici
    şarkıyı arka arkaya iki kez duyardı; ayrıca 30 sn'lik öğeler playlist'in
    izlenme süresi ortalamasını (8,2 dk) aşağı çeker."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, "projects", "Sarki", {
        "youtube_video_id": "UZUN1",
        "youtube_shorts_video_id": "KISA1",
    })
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps({"pop": "PLPOP", "_tum_sarkilar": "PLZ", "_shorts": "PLS"}),
        encoding="utf-8")
    yt = SahteYouTube({"PLPOP": [], "PLZ": [], "PLS": []})
    m.sync_project(yt, p)
    hedefler = {pid for pid, vid in yt.eklemeler if vid == "KISA1"}
    assert hedefler == {"PLS"}
    assert ("PLZ", "UZUN1") in yt.eklemeler
    assert ("PLPOP", "UZUN1") in yt.eklemeler


# --- kök ayrımı -----------------------------------------------------------


@pytest.mark.parametrize("kok", ["dj_sets", "derlemeler"])
def test_dj_ve_derleme_ana_zincire_girmez(tmp_path, kok):
    """dj_sets/ 40-79 dakikalık İngilizce setler, derlemeler/ ise zaten aynı
    şarkıların birleşimi — ikisi de şarkı zincirinde tekrar/kopukluk üretir."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, kok, "Set", {"youtube_video_id": "SETID"}, theme="dj")
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps({"dj": "PLDJ", "_tum_sarkilar": "PLZ"}), encoding="utf-8")
    yt = SahteYouTube({"PLDJ": [], "PLZ": []})
    m.sync_project(yt, p)
    assert ("PLDJ", "SETID") in yt.eklemeler
    assert all(pid != "PLZ" for pid, _ in yt.eklemeler)


def test_hic_yuklenmemis_proje_playlist_olusturmaz(tmp_path):
    """Boş bir state 50 birimlik bir `playlists.insert`e yol açmamalı."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, "projects", "Yeni", {})
    yt = SahteYouTube()
    assert m.sync_project(yt, p) == []
    assert yt.olusturulan == []
    assert yt.eklemeler == []


# --- enerji eğrisi --------------------------------------------------------


def test_enerji_sirasi_egri_kuruyor(tmp_path, monkeypatch):
    """derleme.sec()'in eğrisiyle AYNI şekil: ikinci en sakin açar, en
    sakinler sona dağılır."""
    m = _yukle(tmp_path)
    yollar = []
    for i, e in enumerate([0.5, 0.1, 0.9, 0.2, 0.7, 0.3]):
        d = tmp_path / ("p%d" % i)
        d.mkdir()
        (d / "audio.wav").write_bytes(b"x")
        yollar.append(str(d))

    enerjiler = {yollar[0]: 0.5, yollar[1]: 0.1, yollar[2]: 0.9,
                 yollar[3]: 0.2, yollar[4]: 0.7, yollar[5]: 0.3}
    import derleme
    monkeypatch.setattr(derleme, "_enerji",
                        lambda yol: enerjiler[os.path.dirname(yol)])

    sira = m.enerji_sirasi(yollar)
    # artan enerji: p1(.1) p3(.2) p5(.3) p0(.5) p4(.7) p2(.9)
    assert sira[0] == yollar[3]                  # ikinci en sakin açılış
    assert sira[-1] == yollar[1]                 # en sakin en sonda
    assert set(sira) == set(yollar)              # hiçbir parça kaybolmuyor
    assert len(sira) == len(yollar)              # ve tekrarlanmıyor


def test_enerji_olculemezse_sira_korunur(tmp_path, monkeypatch):
    """librosa yoksa/ses okunamazsa otomasyon DURMAMALI — sıra olduğu gibi."""
    m = _yukle(tmp_path)
    yollar = []
    for i in range(6):
        d = tmp_path / ("q%d" % i)
        d.mkdir()
        (d / "audio.wav").write_bytes(b"x")
        yollar.append(str(d))
    import derleme
    monkeypatch.setattr(derleme, "_enerji", lambda yol: 0.0)
    assert m.enerji_sirasi(yollar) == yollar


# --- atomik yazım ---------------------------------------------------------


def test_update_state_state_io_kullaniyor(tmp_path, monkeypatch):
    """Yarım bir state.json artık `uyumluluk._durum()` üzerinden o projeyi
    TAMAMEN yayın dışı bırakıyor; bu yüzden yazım atomik olmak zorunda."""
    m = _yukle(tmp_path)
    p = _proje(tmp_path, "projects", "Atomik", {"a": 1})
    hedef = os.path.join(p, "state.json")

    import state_io
    cagrildi = {}
    gercek = state_io._atomik_yaz

    def izle(yol, veri):
        cagrildi["yol"] = yol
        return gercek(yol, veri)

    monkeypatch.setattr(state_io, "_atomik_yaz", izle)
    m._update_state(p, {"b": 2})
    assert os.path.abspath(cagrildi.get("yol", "")) == os.path.abspath(hedef)
    kayit = json.loads(open(hedef, encoding="utf-8").read())
    assert kayit == {"a": 1, "b": 2}
