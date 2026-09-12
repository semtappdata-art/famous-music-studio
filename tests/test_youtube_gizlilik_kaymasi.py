# -*- coding: utf-8 -*-
"""YouTube gizlilik KAYMASI: state'in istediği ile YouTube'da gerçekleşen ayrışıyor mu?

NEDEN VAR (2026-09-12, ölçülmüş arıza): `Bu Gece Kazandık`ın iki videosu
(LWGZGtw6UCY, 2OHEA5Fp3-E) 8 Eylül'de public yüklendi, sonra kayıtsız şekilde
unlisted'a çekildi. `state.json` hâlâ `youtube_privacy: "public"` diyordu ve
kayma 4 gün görünmedi, çünkü:
  1. `youtube_upload` state'e İSTENEN gizliliği yazıyor, gerçekleşeni değil;
  2. saatlik istatistik okuması (`get_stats_batch`) yalnız `part=statistics`
     çekiyordu — gizliliği hiç okumuyordu.
Bedeli: state'e güvenen modüller (latest_release, backfill'ler, derleme)
unlisted bir şarkıyı başka platformlara sokuyordu.

İKİ PARÇA, İKİ SÖZLEŞME:
  - `youtube_stats.get_stats_batch` gerçek `privacyStatus`'u AYNI istekte
    (`part=statistics,status`, hâlâ 1 birim) okuyup AYRI alana yazar:
    `youtube_privacy_gercek` / `youtube_shorts_privacy_gercek` + ölçüm damgası.
    `youtube_privacy` alanına ASLA yazmaz — o alan dört modülün sözleşmesi.
  - `saglik_kontrol.youtube_gizlilik_kaymasi` state'i OKUR (ağ yok), her koşuda
    log'a UYARI yazar, telefona günde en fazla bir bildirim gönderir.
    Karar vermez: hiçbir şeyi durdurmaz, hiçbir alanı düzeltmez.

BU TESTLERDE AĞA ÇIKILMIYOR: YouTube servisi sahte, `notify` sahte modül,
soket bağlantısı patlatılıyor; tüm state dosyaları `tmp_path` altında.
"""

import ast
import json
import os
import socket
import sys
import time
import types

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import pytest

import saglik_kontrol as SK
import youtube_stats

T0 = 1_760_000_000.0          # sabit "şimdi"
SAAT = 3600.0
_SK_KAYNAK = os.path.join(_REPO, "saglik_kontrol.py")


def _damga(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def _utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    """Herhangi bir gerçek bağlantı denemesi testi PATLATIR."""
    def _patla(*a, **k):
        raise AssertionError("test ağa çıkmaya çalıştı")
    monkeypatch.setattr(socket.socket, "connect", _patla)
    monkeypatch.setattr(socket, "create_connection", _patla)


# --- Sahte YouTube --------------------------------------------------------

class _SahteYouTube:
    def __init__(self, gizlilik: dict):
        self.gizlilik = gizlilik        # video_id -> privacyStatus
        self.istekler = []              # (part, id listesi)

    def videos(self):
        return self

    def list(self, part, id, **kw):
        self.istekler.append((part, id.split(",")))
        self._son = (part, id.split(","))
        return self

    def execute(self):
        part, idler = self._son
        parcalar = part.split(",")
        items = []
        for v in idler:
            if v not in self.gizlilik:
                continue
            x = {"id": v}
            if "statistics" in parcalar:
                x["statistics"] = {"viewCount": "5", "likeCount": "1",
                                   "commentCount": "0"}
            if "status" in parcalar:
                x["status"] = {"privacyStatus": self.gizlilik[v]}
            items.append(x)
        return {"items": items}


def _proje(kok, ad, state):
    d = kok / ad
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                  encoding="utf-8")
    return d


def _oku(d):
    return json.loads((d / "state.json").read_text(encoding="utf-8"))


# --- (1) istek `status` parçasını içeriyor --------------------------------

def test_toplu_istek_status_parcasini_iceriyor_ve_tek_istek(tmp_path, monkeypatch):
    kok = tmp_path / "projects"
    _proje(kok, "A", {"youtube_video_id": "a1", "youtube_shorts_video_id": "a2",
                      "youtube_privacy": "public", "youtube_shorts_privacy": "public"})
    sahte = _SahteYouTube({"a1": "public", "a2": "public"})
    monkeypatch.setattr(youtube_stats, "get_authenticated_service", lambda: sahte)

    youtube_stats.get_stats_batch(base=str(kok), force=True)

    assert len(sahte.istekler) == 1, "ek istek atılmamalı (kota)"
    parcalar = sahte.istekler[0][0].split(",")
    assert "status" in parcalar, "videos.list isteğinde status parçası yok"
    assert "statistics" in parcalar


# --- (2) gerçek gizlilik AYRI alana, youtube_privacy'ye ASLA -------------

def test_gercek_gizlilik_ayri_alana_yaziliyor_youtube_privacy_degismiyor(
        tmp_path, monkeypatch):
    kok = tmp_path / "projects"
    d = _proje(kok, "Bu Gece Kazandık", {
        "youtube_video_id": "LWGZGtw6UCY", "youtube_shorts_video_id": "2OHEA5Fp3-E",
        "youtube_privacy": "public", "youtube_shorts_privacy": "public"})
    sahte = _SahteYouTube({"LWGZGtw6UCY": "unlisted", "2OHEA5Fp3-E": "unlisted"})
    monkeypatch.setattr(youtube_stats, "get_authenticated_service", lambda: sahte)

    youtube_stats.get_stats_batch(base=str(kok), force=True)

    st = _oku(d)
    assert st["youtube_privacy"] == "public", "istenen alanın üzerine yazıldı"
    assert st["youtube_shorts_privacy"] == "public"
    assert st["youtube_privacy_gercek"] == "unlisted"
    assert st["youtube_shorts_privacy_gercek"] == "unlisted"
    assert SK._damga_ts(st["youtube_privacy_gercek_at"]) is not None
    assert st["youtube_views"] == 5, "istatistik yazımı bozulmamalı"


def test_youtube_privacy_yoksa_OLUSTURULMAZ(tmp_path, monkeypatch):
    kok = tmp_path / "projects"
    d = _proje(kok, "Eski", {"youtube_video_id": "e1"})
    monkeypatch.setattr(youtube_stats, "get_authenticated_service",
                        lambda: _SahteYouTube({"e1": "private"}))

    youtube_stats.get_stats_batch(base=str(kok), force=True)

    st = _oku(d)
    assert "youtube_privacy" not in st
    assert st["youtube_privacy_gercek"] == "private"


def test_tekil_get_stats_de_youtube_privacy_yazmaz(tmp_path, monkeypatch):
    d = _proje(tmp_path, "Tek", {"youtube_video_id": "t1",
                                 "youtube_privacy": "public"})
    monkeypatch.setattr(youtube_stats, "get_authenticated_service",
                        lambda: _SahteYouTube({"t1": "unlisted"}))

    youtube_stats.get_stats(str(d))

    st = _oku(d)
    assert st["youtube_privacy"] == "public"
    assert st["youtube_privacy_gercek"] == "unlisted"


def test_kaynakta_youtube_privacy_alanina_atama_yok():
    """Muhafız: `youtube_stats.py` içinde `st["youtube_privacy"] = ...` ya da
    `"%s_privacy" % onek` biçiminde İSTENEN alana atama bulunmamalı."""
    kaynak = open(os.path.join(_REPO, "upload", "youtube_stats.py"),
                  encoding="utf-8").read()
    agac = ast.parse(kaynak)
    yasak = {"youtube_privacy", "youtube_shorts_privacy"}
    for dugum in ast.walk(agac):
        if not isinstance(dugum, (ast.Assign, ast.AugAssign)):
            continue
        hedefler = dugum.targets if isinstance(dugum, ast.Assign) else [dugum.target]
        for h in hedefler:
            if isinstance(h, ast.Subscript) and isinstance(h.slice, ast.Constant):
                assert h.slice.value not in yasak, (
                    "youtube_stats.py satır %d: istenen gizlilik alanına yazıyor"
                    % dugum.lineno)


# --- (3) saglik_kontrol adımı --------------------------------------------

@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    import uyumluluk
    kok = tmp_path / "projects"
    kok.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))

    gonderilen = []
    sonuc = {"deger": True}
    m = types.ModuleType("notify")
    m.send = lambda baslik, mesaj, *a, **k: (gonderilen.append((baslik, mesaj)),
                                            sonuc["deger"])[1]
    monkeypatch.setitem(sys.modules, "notify", m)
    monkeypatch.setattr(SK.time, "time", lambda: T0)
    return types.SimpleNamespace(kok=kok, gonderilen=gonderilen, sonuc=sonuc)


def _kaymali_state(**ek):
    st = {"youtube_video_id": "LWGZGtw6UCY", "youtube_shorts_video_id": "2OHEA5Fp3-E",
          "youtube_privacy": "public", "youtube_shorts_privacy": "public",
          "youtube_privacy_gercek": "unlisted",
          "youtube_shorts_privacy_gercek": "unlisted",
          "youtube_privacy_gercek_at": _damga(T0 - 2 * SAAT)}
    st.update(ek)
    return st


def test_kayma_log_satiri_ve_bildirim(ortam):
    _proje(ortam.kok, "Bu Gece Kazandık", _kaymali_state())
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)

    assert s["durum"] == "kayma"
    assert len(s["kaymalar"]) == 2
    uyarilar = [x for x in loglar if "UYARI" in x]
    assert len(uyarilar) == 2, loglar
    birlesik = "\n".join(uyarilar)
    assert "Bu Gece Kazandık" in birlesik
    assert "LWGZGtw6UCY" in birlesik and "2OHEA5Fp3-E" in birlesik
    assert "state: public, gerçek: unlisted" in birlesik

    assert len(ortam.gonderilen) == 1, "tek koşuda tek bildirim"
    baslik, mesaj = ortam.gonderilen[0]
    assert "Bu Gece Kazandık" in mesaj
    assert "LWGZGtw6UCY" in mesaj
    assert "state: public, gerçek: unlisted" in mesaj
    assert s["bildirildi"] is True


def test_ayni_gun_log_her_kosuda_bildirim_bir_kez(ortam):
    _proje(ortam.kok, "Bu Gece Kazandık", _kaymali_state())
    for _ in range(3):
        loglar = []
        SK.youtube_gizlilik_kaymasi(log=loglar.append)
        assert any("UYARI" in x for x in loglar), "her koşuda log satırı olmalı"
    assert len(ortam.gonderilen) == 1, "günde en fazla bir bildirim"


def test_gonderim_basarisizsa_damga_atilmaz(ortam):
    _proje(ortam.kok, "Bu Gece Kazandık", _kaymali_state())
    ortam.sonuc["deger"] = False
    SK.youtube_gizlilik_kaymasi(log=lambda *_: None)
    assert SK._durum().get("youtube_gizlilik_bildirim_gun") is None
    ortam.sonuc["deger"] = True
    SK.youtube_gizlilik_kaymasi(log=lambda *_: None)
    assert len(ortam.gonderilen) == 2, "başarısız gönderim ertesi koşuda yeniden denenmeli"


def test_kopya_notu_bilincli_istisna(ortam):
    _proje(ortam.kok, "Küllerimden Geç", {
        "youtube_video_id": "-CQ7MmUygTQ", "youtube_privacy": "public",
        "youtube_privacy_gercek": "unlisted",
        "youtube_privacy_gercek_at": _damga(T0 - SAAT),
        "kopya_notu": "aynı kaydın iki ismi"})
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)
    assert s["durum"] == "tamam"
    assert not any("UYARI" in x for x in loglar)
    assert ortam.gonderilen == []


def test_istenen_ile_gercek_ayniysa_sessiz(ortam):
    _proje(ortam.kok, "Küllerimden Geç", {
        "youtube_video_id": "-CQ7MmUygTQ", "youtube_privacy": "unlisted",
        "youtube_privacy_gercek": "unlisted",
        "youtube_privacy_gercek_at": _damga(T0 - SAAT)})
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)
    assert s["durum"] == "tamam"
    assert loglar == [] or not any("UYARI" in x for x in loglar)
    assert ortam.gonderilen == []


def test_gelecekteki_publish_at_ve_private_kayma_sayilmaz(ortam):
    _proje(ortam.kok, "Zamanli", {
        "youtube_video_id": "z1", "youtube_privacy": "public",
        "youtube_publish_at": _utc(T0 + 5 * SAAT),
        "youtube_privacy_gercek": "private",
        "youtube_privacy_gercek_at": _damga(T0 - SAAT)})
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)
    assert s["durum"] == "tamam"
    assert not any("UYARI" in x for x in loglar)
    assert ortam.gonderilen == []


def test_olcum_publish_at_ONCESINDE_alinmissa_private_kayma_sayilmaz(ortam):
    """publishAt artık geçmişte ama gerçek değer o andan ÖNCE ölçülmüş:
    'private' o ölçüm anında normaldi; bayat ölçümle alarm çalınmaz."""
    _proje(ortam.kok, "Zamanli", {
        "youtube_video_id": "z1", "youtube_privacy": "public",
        "youtube_publish_at": _utc(T0 - SAAT),
        "youtube_privacy_gercek": "private",
        "youtube_privacy_gercek_at": _damga(T0 - 3 * SAAT)})
    s = SK.youtube_gizlilik_kaymasi(log=lambda *_: None)
    assert s["durum"] == "tamam"
    assert ortam.gonderilen == []


def test_publish_at_gecmis_ve_olcum_sonrasinda_private_KAYMADIR(ortam):
    """İstisna fazla geniş olmamalı: yayın anı geçmiş ve ölçüm ondan SONRA
    alınmışken hâlâ private ise bu gerçek bir kayma."""
    _proje(ortam.kok, "Zamanli", {
        "youtube_video_id": "z1", "youtube_privacy": "public",
        "youtube_publish_at": _utc(T0 - 5 * SAAT),
        "youtube_privacy_gercek": "private",
        "youtube_privacy_gercek_at": _damga(T0 - SAAT)})
    s = SK.youtube_gizlilik_kaymasi(log=lambda *_: None)
    assert s["durum"] == "kayma"
    assert len(ortam.gonderilen) == 1


def test_olcum_yoksa_sessiz(ortam):
    _proje(ortam.kok, "Olcumsuz", {"youtube_video_id": "o1",
                                   "youtube_privacy": "public"})
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)
    assert s["durum"] == "tamam"
    assert ortam.gonderilen == []


def test_adim_state_dosyalarina_YAZMAZ(ortam):
    """Karar vermeyen kapı: youtube_privacy düzeltilmez, state'e dokunulmaz."""
    d = _proje(ortam.kok, "Bu Gece Kazandık", _kaymali_state())
    once = (d / "state.json").read_bytes()
    SK.youtube_gizlilik_kaymasi(log=lambda *_: None)
    assert (d / "state.json").read_bytes() == once


def test_tarama_patlarsa_sessiz_kalmaz(ortam, monkeypatch):
    import uyumluluk

    def _patla():
        raise RuntimeError("disk yok")
    monkeypatch.setattr(uyumluluk, "proje_klasorleri", _patla)
    loglar = []
    s = SK.youtube_gizlilik_kaymasi(log=loglar.append)
    assert s["durum"] == "calistirilamadi"
    assert loglar


def test_alan_adlari_iki_modulde_AYNI():
    """saglik_kontrol youtube_stats'ı import etmiyor (ağır kimlik zinciri);
    sabitler kopya, sürüklenirse adım sessizce hiçbir şey görmez."""
    assert SK.GIZLILIK_GERCEK_SONEKI == youtube_stats.GIZLILIK_ALANI_SONEKI
    assert SK.GIZLILIK_OLCUM_DAMGASI == youtube_stats.GIZLILIK_OLCUM_DAMGASI
    assert "status" in youtube_stats.VIDEOS_LIST_PARCALARI.split(",")


def test_kontrol_et_adimi_cagiriyor_ve_kacan_kosudan_ONCE():
    agac = ast.parse(open(_SK_KAYNAK, encoding="utf-8").read())
    hedef = next(d for d in ast.walk(agac)
                 if isinstance(d, ast.FunctionDef) and d.name == "kontrol_et")
    anahtarlar = [k.value for d in ast.walk(hedef) if isinstance(d, ast.Dict)
                  for k in d.keys if isinstance(k, ast.Constant)]
    assert "youtube_gizlilik" in anahtarlar
    assert anahtarlar.index("youtube_gizlilik") < anahtarlar.index("kacan_kosu")


def test_uretilen_metinler_cp1254_uyumlu(ortam):
    _proje(ortam.kok, "Bu Gece Kazandık", _kaymali_state())
    loglar = []
    SK.youtube_gizlilik_kaymasi(log=loglar.append)
    for metin in loglar + [b + "\n" + m for b, m in ortam.gonderilen]:
        metin.encode("cp1254")
