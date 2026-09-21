# -*- coding: utf-8 -*-
"""Derlemelerin HANGİ playlist'e girdiği — başlıkla AYNI kuraldan.

NEDEN BU TESTLER VAR (2026-09-11, canlı arıza):
"Gece Seansı Vol. 1" 13 parçalık KARMA bir derleme (en kalabalık tema 5/13
hiphop, yani yarıdan az). `youtube_upload.build_snippet` bunu doğru okuyup
başlığa "13 Şarkılık Türkçe **Müzik** Derlemesi" yazdı — ama playlist seçimi o
kuralı hiç görmüyordu: `meta["theme"]` alanına bakıyordu ve o alan
`derleme.py._baskin_tema()` düşüşü yüzünden "hiphop" diyor. Sonuç: karma bir
derleme Hip-Hop playlist'inde (PLamU8IEtNO2k), state.json ve canlı liste
dökümü ikisi de bunu doğruluyordu.

Arıza "fonksiyon yanlış" değil, "aynı karar İKİ yerde İKİ kuralla veriliyor"
sınıfındandı. Bu yüzden testlerin çoğu davranışı değil, İKİ TARAFIN AYNI
SONUCU VERDİĞİNİ çiviliyor: başlıkta hangi tür yazıyorsa video o tarz
listesinde olmalı; başlık "Müzik" diyorsa HİÇBİR tarz listesinde olmamalı.
"""

import collections
import importlib.util
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import config


def _yukle(tmp_path):
    """Modülü BAĞIMSIZ yükler ve playlist_ids.json'ı tmp'ye çeker.

    Üretimdeki `upload/playlist_ids.json` gerçek kanal ID'lerini tutuyor; bir
    test onu üzerine yazarsa bir sonraki koşuda playlist'lerin İKİNCİ kopyaları
    oluşturulur (kanalda bunun gerçek bir örneği duruyor: iki tane
    "DJ Set Şarkılar")."""
    spec = importlib.util.spec_from_file_location(
        "yt_playlists_derleme_test",
        os.path.join(_KOK, "upload", "youtube_playlists.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["yt_playlists_derleme_test"] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop("yt_playlists_derleme_test", None)
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
        return None

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
    def __init__(self, icerik=None):
        self.icerik = dict(icerik or {})
        self.eklemeler = []
        self.olusturulan = []
        self.okuma = 0

    def playlistItems(self):
        return _PlaylistItems(self)

    def playlists(self):
        return _Playlists(self)


# Kanalın gerçek anahtarları; testler kendi tmp kopyasını kullanıyor.
_IDLER = {
    "pop": "PLPOP", "hiphop": "PLHIPHOP", "arabesk": "PLARABESK",
    "elektronik": "PLELEK", "akustik": "PLAKUSTIK", "rock": "PLROCK",
    "dj": "PLDJ", "_tum_sarkilar": "PLZINCIR", "_shorts": "PLSHORTS",
    "_derlemeler": "PLDERLEME",
}


def _kur(tmp_path, temalar, kok="derlemeler", meta_theme="hiphop",
         state=None, ad="Gece Seansı Vol. 1"):
    """Derleme klasörü + tmp playlist_ids.json. `temalar` = parça temaları."""
    d = tmp_path / kok / ad
    d.mkdir(parents=True)
    meta = {
        "title": ad,
        # KASITLI olarak YANLIŞ/YANILTICI: gerçek derlemelerde bu alan
        # `_baskin_tema()` düşüşüdür, derlemenin türü DEĞİLDİR.
        "theme": meta_theme,
        "derleme": True,
        "derleme_temalari": list(temalar),
        "derleme_liste": [{"sira": i + 1, "ad": "P%d" % i, "zaman": "0:00"}
                          for i in range(len(temalar))],
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                 encoding="utf-8")
    (d / "state.json").write_text(
        json.dumps(state if state is not None
                   else {"youtube_video_id": "DERLEMEVID"}),
        encoding="utf-8")
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps(_IDLER), encoding="utf-8")
    return str(d), meta


# --- asıl regresyon: KARMA derleme tarz listesine girmez -------------------


def test_karma_derleme_hicbir_tarz_listesine_girmez(tmp_path):
    """CANLI ARIZA: 13 parçanın 5'i hiphop -> başlık "Müzik Derlemesi" ama
    video Hip-Hop playlist'ine eklenmişti."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["hiphop"] * 5 + ["arabesk"] * 3 + ["pop"] * 2
                    + ["elektronik"] + ["akustik"] * 2)
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)

    tarz_idleri = {_IDLER[k] for k in config.THEMES}
    girdigi = {pid for pid, _ in yt.eklemeler}
    assert not (girdigi & tarz_idleri), "karma derleme bir tarz listesine girdi"
    assert ("PLDERLEME", "DERLEMEVID") in yt.eklemeler


def test_karma_derleme_state_i_artik_hiphop_demiyor(tmp_path):
    """`youtube_playlist_id` alanını başka modüller/raporlar okuyor — canlı
    state.json'da orada PLamU8IEtNO2k (Hip-Hop) yazıyordu."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["hiphop"] * 5 + ["arabesk"] * 3 + ["pop"] * 5)
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    durum = json.loads(open(os.path.join(p, "state.json"), encoding="utf-8").read())
    assert durum["youtube_playlist_id"] == "PLDERLEME"
    assert durum["youtube_playlists"] == ["PLDERLEME"]


# --- baskın temalı derleme: başlık ne diyorsa o -----------------------------


def test_baskin_temali_derleme_o_tarz_listesine_de_girer(tmp_path):
    """6 parçanın 5'i arabesk -> başlık "Türkçe Arabesk Derlemesi" diyor;
    o hâlde video Arabesk rafında da DURMALI (keşif katmanı)."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["arabesk"] * 5 + ["pop"], meta_theme="pop")
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    assert ("PLARABESK", "DERLEMEVID") in yt.eklemeler
    assert ("PLDERLEME", "DERLEMEVID") in yt.eklemeler
    # meta["theme"] "pop" diyor ama o alan bir SUNUM zorunluluğu — dinlenmemeli.
    assert all(pid != "PLPOP" for pid, _ in yt.eklemeler)


def test_tam_yari_baskin_SAYILMAZ(tmp_path):
    """Eşik "yarıdan FAZLA" (adet*2 > toplam): 4/8 karma demektir.
    Eşiğin kendisi bu dosyada değil `_derleme_tur_bilgisi`'nde — burada
    sadece playlist tarafının o eşiğe UYDUĞU çivileniyor."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["pop"] * 4 + ["rock"] * 4)
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    assert all(pid not in ("PLPOP", "PLROCK") for pid, _ in yt.eklemeler)
    assert ("PLDERLEME", "DERLEMEVID") in yt.eklemeler


def test_derleme_TUM_temalarin_listelerine_girmez(tmp_path):
    """ELENEN SEÇENEK: 13 parçalık derlemeyi 5 tarz listesine birden eklemek.
    Her ekleme 50 birim (250 birim/derleme) VE her rafta tekrar: o raftaki
    parçalar zaten tek tek video olarak duruyor, dinleyici aynı şarkıyı iki
    kez duyardı (Shorts'un ana zincirden ayrılma gerekçesinin aynısı)."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["hiphop"] * 5 + ["arabesk"] * 3 + ["pop"] * 2
                    + ["elektronik"] + ["akustik"] * 2)
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    tarz_idleri = {_IDLER[k] for k in config.THEMES}
    assert len([1 for pid, _ in yt.eklemeler if pid in tarz_idleri]) == 0
    # Toplam yazım: tarz listesi yok + derlemeler rafı = 1 ekleme (50 birim).
    assert len(yt.eklemeler) == 1


# --- ana zincir / Shorts sınırları -----------------------------------------


def test_derleme_ana_zincire_girmez_projects_altinda_olsa_bile(tmp_path):
    """Zincir tek tek ŞARKILARDAN oluşuyor; 39 dakikalık bir derleme zincire
    girseydi dinleyici zincirdeki şarkıların yarısını İKİNCİ kez duyardı.
    Eski kapı sadece KÖK adına bakıyordu — artık meta bayrağına da bakıyor."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["pop"] * 6, kok="projects")
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    assert all(pid != "PLZINCIR" for pid, _ in yt.eklemeler)
    assert ("PLDERLEME", "DERLEMEVID") in yt.eklemeler


def test_derlemenin_shortsu_yine_shorts_listesine_gidiyor(tmp_path):
    """Derlemenin dikey kesiti normal bir Short — yeri değişmedi."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["hiphop"] * 5 + ["pop"] * 8,
                    state={"youtube_video_id": "DERLEMEVID",
                           "youtube_shorts_video_id": "DERLEMEKISA"})
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    m.sync_project(yt, p)
    hedefler = {pid for pid, vid in yt.eklemeler if vid == "DERLEMEKISA"}
    assert hedefler == {"PLSHORTS"}


def test_derleme_playlisti_yoksa_olusturuluyor(tmp_path):
    """Kanalda "Derlemeler" listesi YOK (2026-09-11 salt-okuma dökümüyle
    doğrulandı) — ilk derlemede bir kez oluşturulması gerekiyor."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["pop"] * 3 + ["rock"] * 3)
    idler = dict(_IDLER)
    idler.pop("_derlemeler")
    (tmp_path / "playlist_ids.json").write_text(
        json.dumps(idler), encoding="utf-8")
    yt = SahteYouTube({v: [] for v in idler.values()})
    m.sync_project(yt, p)
    assert len(yt.olusturulan) == 1
    assert "Derlemeler" in yt.olusturulan[0]
    # Yeni ID önbelleğe YAZILMALI, yoksa bir sonraki derlemede İKİNCİ bir
    # "Derlemeler" listesi oluşur (kanalda bunun gerçek bir örneği var).
    kayit = json.loads((tmp_path / "playlist_ids.json").read_text(encoding="utf-8"))
    assert kayit["_derlemeler"] == "PLYENI1"


# --- İKİ TARAFIN AYNI KURALI KULLANDIĞI -------------------------------------


@pytest.mark.parametrize("temalar,beklenen_tur", [
    (["arabesk"] * 5 + ["pop"], "Arabesk"),
    (["hiphop"] * 5 + ["arabesk"] * 3 + ["pop"] * 5, "Müzik"),
    (["pop"] * 4 + ["rock"] * 4, "Müzik"),
    (["rock"] * 3, "Rock"),
])
def test_baslik_turu_ile_playlist_anahtari_ASLA_ayrismaz(tmp_path, temalar,
                                                         beklenen_tur):
    """Asıl çivi: başlıktaki tür ile playlist anahtarı TEK kaynaktan geliyor.
    Biri değişip diğeri kalırsa (arızanın bugünkü hâli) bu test düşer."""
    m = _yukle(tmp_path)
    _p, meta = _kur(tmp_path, temalar)
    from youtube_upload import build_snippet
    baslik = build_snippet(meta)["title"]
    assert f"Türkçe {beklenen_tur} Derlemesi" in baslik

    anahtar = m.derleme_tarz_anahtari(meta)
    if beklenen_tur == "Müzik":
        assert anahtar is None, "başlık KARMA diyor, playlist bir tarz seçti"
    else:
        assert config.THEMES[anahtar]["label"] == beklenen_tur


def test_tur_okunamazsa_tarz_atlanir_ama_otomasyon_durmaz(tmp_path,
                                                          monkeypatch):
    """`youtube_upload` içe aktarılamazsa doğru davranış çökmek değil, tarz
    katmanını atlamak: video yine derlemeler rafına giriyor."""
    m = _yukle(tmp_path)
    p, _meta = _kur(tmp_path, ["pop"] * 6)
    gercek = __import__("builtins").__import__

    def patla(ad, *a, **kw):
        if ad == "youtube_upload":
            raise ImportError("taklit")
        return gercek(ad, *a, **kw)

    monkeypatch.setattr(__import__("builtins"), "__import__", patla)
    yt = SahteYouTube({v: [] for v in _IDLER.values()})
    listeler = m.sync_project(yt, p)
    assert listeler == ["PLDERLEME"]


# --- CANLI VAKA -------------------------------------------------------------


def test_canli_vaka_gece_seansi_karma_cikiyor(tmp_path):
    """Gerçek `derlemeler/Gece Seansı Vol. 1/meta.json` ile (SALT OKUMA).

    Bu meta'da `derleme_temalari` alanı YOK — derleme o alan eklenmeden önce
    üretildi — yani `_derleme_temalari`'nin geriye dönük yolu (parça adlarından
    kaynak projelerin meta.json'ını okuma) da bu testin kapsamında."""
    m = _yukle(tmp_path)
    yol = os.path.join(_KOK, "derlemeler", "Gece Seansı Vol. 1", "meta.json")
    if not os.path.isfile(yol):
        pytest.skip("canlı derleme klasörü yok")
    meta = json.loads(open(yol, encoding="utf-8").read())
    assert meta.get("theme") == "hiphop"          # yanıltıcı alan yerinde duruyor

    from youtube_upload import _derleme_temalari
    sayac = collections.Counter(_derleme_temalari(meta))
    assert sayac.most_common(1)[0][1] * 2 <= sum(sayac.values()), "artık karma değil"
    assert m.derleme_tarz_anahtari(meta) is None
