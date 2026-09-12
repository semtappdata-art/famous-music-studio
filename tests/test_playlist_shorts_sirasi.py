# -*- coding: utf-8 -*-
"""auto_process.process_project() — playlist senkronu Shorts yüklemesinden
SONRA da çalışmalı.

NEDEN BU TEST VAR (2026-09-11 denetimi, kanalın gerçek durumu):
`process_project()` içinde `sync_project` çağrısı Shorts yüklemesinden ÖNCE
duruyordu. O anda `state.json`da `youtube_shorts_video_id` HENÜZ YOK — yani
Short hiçbir playlist'e girmiyordu. Daha kötüsü proje hemen ardından
`_is_fully_done()`dan geçip `pending`den düşüyor, `sync_project` bir daha HİÇ
çağrılmıyordu: kanaldaki 20 Shorts'un hiçbiri listede değildi ve log'a tek
satır bile düşmedi (bkz. CLAUDE.md "BAĞLANTI seviyesindeki sessiz arıza").

Bu dosya iki şeyi çiviliyor:
  1. Shorts yüklendikten SONRA yapılan ikinci `sync_project` çağrısı, diske
     yeni yazılmış `youtube_shorts_video_id`yi GERÇEKTEN görüyor.
  2. O ikinci çağrı zaten yapılmış iş için EK KOTA harcamıyor: tarz ve ana
     zincir playlist'leri `_UYE_ONBELLEK`ten okunuyor, yeni bir
     `playlistItems.list` (1 birim) ya da `playlistItems.insert` (50 birim)
     üretmiyor. Harcanan tek kota, daha önce HİÇ yapılmayan Shorts eklemesi.

Ağa ÇIKILMIYOR: YouTube servisi, `youtube_upload` ve tüm kimlik dosyası
kontrolleri sahteleniyor.
"""

import importlib.util
import json
import os
import sys
import types

import auto_process as ap

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_KOK, "upload")


# --- YouTube taklidi (kota sayaçlı) --------------------------------------


class _Istek:
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        return self._sonuc


class _PlaylistItems:
    def __init__(self, api):
        self._api = api

    def list(self, part=None, playlistId=None, maxResults=None):
        self._api.okuma += 1                      # 1 kota birimi
        return _Istek({"items": [
            {"contentDetails": {"videoId": v}}
            for v in self._api.icerik.get(playlistId, [])
        ]})

    def list_next(self, req, resp):
        return None

    def insert(self, part=None, body=None):
        pid = body["snippet"]["playlistId"]
        vid = body["snippet"]["resourceId"]["videoId"]
        self._api.eklemeler.append((pid, vid))     # 50 kota birimi
        self._api.icerik.setdefault(pid, []).append(vid)
        return _Istek({"id": "PLI"})


class _Playlists:
    def __init__(self, api):
        self._api = api

    def insert(self, part=None, body=None):
        self._api.olusturulan.append(body["snippet"]["title"])
        yeni = "PLYENI%d" % len(self._api.olusturulan)
        self._api.icerik[yeni] = []
        return _Istek({"id": yeni})


class SahteYouTube:
    def __init__(self, icerik):
        self.icerik = dict(icerik)
        self.eklemeler = []
        self.olusturulan = []
        self.okuma = 0

    def playlistItems(self):
        return _PlaylistItems(self)

    def playlists(self):
        return _Playlists(self)


# --- kurulum --------------------------------------------------------------


def _gercek_playlist_modulu(tmp_path, monkeypatch, youtube):
    """`upload/youtube_playlists.py`nin GERÇEK kodunu bağımsız yükler.

    Sahte bir sync_project yazmak bu testi anlamsız kılardı: kanıtlanmak
    istenen şey tam olarak gerçek `sync_project`in state'i DİSKTEN yeniden
    okuduğu. Sadece playlist_ids.json yolu (üretim dosyası, repoya commit'li)
    ve kimlik doğrulama sahteleniyor."""
    spec = importlib.util.spec_from_file_location(
        "youtube_playlists", os.path.join(_UPLOAD, "youtube_playlists.py"))
    mod = importlib.util.module_from_spec(spec)
    # setitem: test bitince sys.modules eski hâline dönsün — yoksa silinmiş bir
    # tmp klasörünü gösteren bir modül sonraki testlere sızardı.
    monkeypatch.setitem(sys.modules, "youtube_playlists", mod)
    spec.loader.exec_module(mod)
    mod.PLAYLIST_IDS_PATH = str(tmp_path / "playlist_ids.json")
    mod._UYE_ONBELLEK.clear()
    mod.get_authenticated_service = lambda: youtube
    return mod


def _sahte_youtube_upload(cagrilar):
    """upload_short: gerçeğinin TEK gözlenebilir yan etkisini taklit eder —
    `youtube_shorts_video_id`yi state.json'a YAZAR (bkz. youtube_upload.py,
    `_update_state(project_dir, {"youtube_shorts_video_id": video_id, ...})`)."""
    mod = types.ModuleType("youtube_upload")

    def upload_short(project_dir, privacy, uzun_id, schedule=True):
        cagrilar.append(project_dir)
        yol = os.path.join(project_dir, "state.json")
        with open(yol, "r", encoding="utf-8") as f:
            st = json.load(f)
        st["youtube_shorts_video_id"] = "KISA1"
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(st, f)
        return "KISA1"

    mod.upload_short = upload_short
    return mod


def _kur(tmp_path, monkeypatch):
    """Tam bir `process_project()` koşusunu ağa çıkmadan hazırlar."""
    proje = tmp_path / "projects" / "Sarki"
    proje.mkdir(parents=True)
    (proje / "meta.json").write_text(
        json.dumps({"title": "Sarki", "theme": "pop"}), encoding="utf-8")
    # youtube_captions_done BİLEREK dolu: gerçek altyazı adımı ağa çıkardı.
    (proje / "state.json").write_text(json.dumps({
        "youtube_video_id": "UZUN1",
        "youtube_captions_done": True,
    }), encoding="utf-8")

    (tmp_path / "playlist_ids.json").write_text(json.dumps({
        "pop": "PLPOP", "_tum_sarkilar": "PLZ", "_shorts": "PLS",
    }), encoding="utf-8")

    yt = SahteYouTube({"PLPOP": [], "PLZ": [], "PLS": []})
    _gercek_playlist_modulu(tmp_path, monkeypatch, yt)

    cagrilar = []
    monkeypatch.setitem(sys.modules, "youtube_upload",
                        _sahte_youtube_upload(cagrilar))

    # Render/kapak/uyumluluk adımları bu testin konusu değil.
    monkeypatch.setattr(ap.generate_cover, "generate", lambda p: None)
    monkeypatch.setattr(ap, "_is_rendered", lambda p: True)
    import uyumluluk
    monkeypatch.setattr(uyumluluk, "kontrol", lambda *a, **k: ([], []))
    monkeypatch.setattr(uyumluluk, "rapor_yaz", lambda *a, **k: None)

    # SADECE upload/token.json "var" sayılıyor. Bu makinede tiktok/instagram/
    # facebook kimlik dosyaları GERÇEKTEN duruyor — dokunmadan bırakılırsa
    # test gerçek bir yükleme başlatırdı.
    gercek_isfile = os.path.isfile
    sahte_yok = {os.path.join(_UPLOAD, ad) for ad in (
        "tiktok_token.json", "instagram_token.json", "facebook_token.json",
        "telegram_client_secrets.json", "bluesky_client_secrets.json")}

    def isfile(yol):
        if yol == os.path.join(_UPLOAD, "token.json"):
            return True
        if yol in sahte_yok:
            return False
        return gercek_isfile(yol)

    monkeypatch.setattr(os.path, "isfile", isfile)
    return str(proje), yt, cagrilar


def _durum(proje):
    with open(os.path.join(proje, "state.json"), encoding="utf-8") as f:
        return json.load(f)


# --- testler --------------------------------------------------------------


def test_shorts_yuklendikten_sonra_playliste_giriyor(tmp_path, monkeypatch):
    """ASIL REGRESYON: tek bir process_project() koşusunda Short hem yüklenip
    hem de Shorts playlist'ine eklenmiş olmalı."""
    proje, yt, cagrilar = _kur(tmp_path, monkeypatch)

    ap.process_project(proje, "public", schedule=False)

    assert cagrilar == [proje], "Shorts yüklemesi hiç çalışmadı"
    assert ("PLS", "KISA1") in yt.eklemeler, (
        "Short hiçbir playlist'e girmedi — ikinci sync_project çağrısı "
        "state'teki youtube_shorts_video_id'yi görmüyor")
    st = _durum(proje)
    assert st["youtube_shorts_playlist_id"] == "PLS"
    assert "PLS" in st["youtube_playlists"]


def test_uzun_format_playlistleri_bozulmuyor(tmp_path, monkeypatch):
    """İkinci çağrı uzun formatın listelerini TEKRAR eklememeli."""
    proje, yt, _ = _kur(tmp_path, monkeypatch)

    ap.process_project(proje, "public", schedule=False)

    assert yt.eklemeler.count(("PLPOP", "UZUN1")) == 1
    assert yt.eklemeler.count(("PLZ", "UZUN1")) == 1
    assert yt.olusturulan == [], "Var olan playlist yeniden oluşturuldu (50 birim)"


def test_ikinci_cagri_ek_kota_harcamiyor(tmp_path, monkeypatch):
    """KOTA KANITI.

    İki çağrının toplam maliyeti, tek bir tam senkronun maliyetine EŞİT:
    üç playlist için ÜÇ okuma (playlist başına bir, `_UYE_ONBELLEK` süreç
    ömrü boyunca geçerli) ve ÜÇ ekleme. İkinci çağrı tarz/zincir listelerini
    önbellekten okuyor — ne yeni bir `playlistItems.list` (1 birim) ne de
    tekrar bir `playlistItems.insert` (50 birim) üretiyor. Harcadığı tek
    kota, daha önce HİÇ yapılmayan Shorts eklemesi (1 okuma + 1 ekleme)."""
    proje, yt, _ = _kur(tmp_path, monkeypatch)

    ap.process_project(proje, "public", schedule=False)

    assert yt.okuma == 3, f"beklenen 3 okuma, olan {yt.okuma}"
    assert sorted(yt.eklemeler) == sorted([
        ("PLPOP", "UZUN1"), ("PLZ", "UZUN1"), ("PLS", "KISA1")])


def test_shorts_id_ikinci_cagriyi_DISKTEN_besliyor(tmp_path, monkeypatch):
    """Arızanın çekirdeği: `process_project`in yerel `state` sözlüğü, Shorts
    yüklemesinden ÖNCE okunmuş BAYAT bir kopya — içinde hiçbir zaman
    `youtube_shorts_video_id` olmuyor. İkinci sync_project'in çalışmasının
    tek sebebi state'i DİSKTEN yeniden okuması."""
    proje, yt, _ = _kur(tmp_path, monkeypatch)
    gorulen = []

    yp = sys.modules["youtube_playlists"]
    gercek_sync = yp.sync_project

    def izleyen_sync(youtube, project_dir, dry_run=False):
        with open(os.path.join(project_dir, "state.json"), encoding="utf-8") as f:
            gorulen.append(json.load(f).get("youtube_shorts_video_id"))
        return gercek_sync(youtube, project_dir, dry_run)

    monkeypatch.setattr(yp, "sync_project", izleyen_sync)
    ap.process_project(proje, "public", schedule=False)

    assert gorulen == [None, "KISA1"], (
        "birinci çağrı Shorts'u göremez (henüz yüklenmedi), ikincisi görmeli; "
        f"görülen: {gorulen}")
