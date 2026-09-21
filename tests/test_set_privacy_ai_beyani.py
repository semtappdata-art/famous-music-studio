# -*- coding: utf-8 -*-
"""upload/set_privacy.py — gizlilik değişince ZORUNLU AI beyanı SİLİNMESİN.

NEDEN VAR: `videos.update` kısmi güncelleme YAPMAZ — `part` içinde yer alıp
gövdede verilmeyen mutable alanlar SİLİNİR. `set_privacy.py`'nin ilk sürümü
gövdeye yalnızca `privacyStatus` koyuyordu, yani her çalıştırmasında o videonun
`containsSyntheticMedia` (YouTube'un zorunlu AI-üretimi beyanı) ve
`selfDeclaredMadeForKids` alanlarını sessizce siliyordu. Betik ölü değil:
2026-09-07'de kataloğun TAMAMI (16 proje, uzun format + Shorts) bu yolla
unlisted'a çekilip geri public yapıldı.

ARIZA API'DEN GÖRÜLEMİYOR: `videos.list(part="status")` `containsSyntheticMedia`
alanını GERİ DÖNDÜRMÜYOR. Yani ne "silindi mi" diye bakılabiliyor, ne de
oku-birleştir-yaz (round-trip) tek başına alanı koruyabiliyor — o alan HER
yazımda AÇIKÇA yeniden set edilmek zorunda. Bu testin varlık sebebi tam olarak
bu: CLAUDE.md'nin kuralı gereği bir GARANTİ iddia eden yorum, o garantiyi
doğrulayan test olmadan yazılmaz.

YouTube API'sinin tamamı monkeypatch — hiçbir ağ çağrısı yok.
"""

import ast
import io
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import set_privacy as S


class _Istek:
    def __init__(self, sonuc, kayit=None, cagri=None):
        self._sonuc = sonuc
        self._kayit = kayit
        self._cagri = cagri

    def execute(self):
        if self._kayit is not None:
            self._kayit.append(self._cagri)
        return self._sonuc


class _Videos:
    def __init__(self, liste_sonucu):
        self.liste_sonucu = liste_sonucu
        self.guncellemeler = []
        self.liste_cagrilari = []

    def list(self, part=None, id=None):
        self.liste_cagrilari.append({"part": part, "id": id})
        return _Istek(self.liste_sonucu)

    def update(self, part=None, body=None):
        return _Istek({}, self.guncellemeler, {"part": part, "body": body})


class _Youtube:
    def __init__(self, liste_sonucu):
        self._videos = _Videos(liste_sonucu)

    def videos(self):
        return self._videos


# `videos.list(part="status")`'ın GERÇEKTE döndürdüğü alanlar (2026-09-11'de
# canlı bir videoda ölçüldü). containsSyntheticMedia BİLEREK yok — API onu
# döndürmüyor; testin anlamlı olması için taklit de döndürmemeli.
_CANLI_STATUS = {
    "uploadStatus": "processed",
    "privacyStatus": "public",
    "license": "youtube",
    "embeddable": True,
    "publicStatsViewable": True,
    "madeForKids": False,
    "selfDeclaredMadeForKids": False,
}


def _kos(monkeypatch, privacy="unlisted", status=None, ogeler=None):
    if ogeler is None:
        ogeler = [{"status": dict(_CANLI_STATUS if status is None else status)}]
    yt = _Youtube({"items": ogeler})
    monkeypatch.setattr(S, "get_authenticated_service", lambda: yt)
    S.set_privacy("VID123", privacy)
    return yt._videos


def test_ai_beyani_gercekten_gonderiliyor(monkeypatch):
    """KIRMIZI/YEŞİL çekirdeği: update gövdesinde containsSyntheticMedia=True."""
    v = _kos(monkeypatch)
    assert len(v.guncellemeler) == 1
    govde = v.guncellemeler[0]["body"]
    assert govde["id"] == "VID123"
    durum = govde["status"]
    assert durum["containsSyntheticMedia"] is True, (
        "AI beyanı gövdede YOK — bu update videonun zorunlu beyanını SİLER "
        "ve silindiği API'den GÖRÜLEMEZ"
    )
    assert durum["selfDeclaredMadeForKids"] is False
    assert durum["privacyStatus"] == "unlisted"


def test_govde_sadece_privacystatus_degil(monkeypatch):
    """Eski arızanın imzası: tek anahtarlı `{"privacyStatus": ...}` gövdesi."""
    v = _kos(monkeypatch)
    durum = v.guncellemeler[0]["body"]["status"]
    assert set(durum) != {"privacyStatus"}
    assert len(durum) > 1


def test_mevcut_status_once_okunuyor(monkeypatch):
    v = _kos(monkeypatch)
    assert v.liste_cagrilari == [{"part": "status", "id": "VID123"}]


def test_diger_mutable_alanlar_korunuyor(monkeypatch):
    v = _kos(monkeypatch)
    durum = v.guncellemeler[0]["body"]["status"]
    assert durum["license"] == "youtube"
    assert durum["embeddable"] is True
    assert durum["publicStatsViewable"] is True


def test_salt_okunur_alanlar_geri_gonderilmiyor(monkeypatch):
    v = _kos(monkeypatch, status=dict(
        _CANLI_STATUS, failureReason="codec", rejectionReason="duplicate"))
    durum = v.guncellemeler[0]["body"]["status"]
    for alan in ("uploadStatus", "failureReason", "rejectionReason"):
        assert alan not in durum


def test_publishat_public_yaparken_dusuruluyor(monkeypatch):
    """publishAt sadece privacyStatus="private" ile kabul ediliyor."""
    v = _kos(monkeypatch, privacy="public", status=dict(
        _CANLI_STATUS, privacyStatus="private",
        publishAt="2026-09-20T19:00:00Z"))
    assert "publishAt" not in v.guncellemeler[0]["body"]["status"]


def test_publishat_private_kalirken_korunuyor(monkeypatch):
    v = _kos(monkeypatch, privacy="private", status=dict(
        _CANLI_STATUS, privacyStatus="private",
        publishAt="2026-09-20T19:00:00Z"))
    durum = v.guncellemeler[0]["body"]["status"]
    assert durum["publishAt"] == "2026-09-20T19:00:00Z"
    assert durum["containsSyntheticMedia"] is True


def test_status_okunamazsa_hic_yazilmiyor(monkeypatch):
    """Kapı kendiliğinden AÇILMASIN: eksik gövdeyle yazmaktansa dur."""
    yt = _Youtube({"items": []})
    monkeypatch.setattr(S, "get_authenticated_service", lambda: yt)
    with pytest.raises(RuntimeError):
        S.set_privacy("YOKVID", "public")
    assert yt._videos.guncellemeler == []


def _youtube_upload_status_sabitleri():
    """youtube_upload.py'nin yükleme sırasında gönderdiği sabit status alanları."""
    yol = os.path.join(_REPO, "upload", "youtube_upload.py")
    with io.open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    bulunan = {}
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Dict):
            continue
        anahtarlar = [k.value for k in dugum.keys
                      if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if "containsSyntheticMedia" not in anahtarlar:
            continue
        for k, d in zip(dugum.keys, dugum.values):
            if (isinstance(k, ast.Constant)
                    and k.value in ("containsSyntheticMedia",
                                    "selfDeclaredMadeForKids")
                    and isinstance(d, ast.Constant)):
                bulunan[k.value] = d.value
    return bulunan


def test_yukleme_ile_tutarli():
    """Bu betik yüklemenin KARARINI yeniden üretir, ondan sapmaz.

    `youtube_upload.py` her yüklemede KOŞULSUZ `containsSyntheticMedia=True` +
    `selfDeclaredMadeForKids=False` gönderiyor. set_privacy de ikisini koşulsuz
    yazıyor — "koru" (round-trip) değil "yeniden yaz", çünkü birincisi okunamıyor
    ve ikisinin de doğru değeri kanal seviyesinde sabit.
    """
    yukleme = _youtube_upload_status_sabitleri()
    assert yukleme.get("containsSyntheticMedia") is True
    assert yukleme.get("selfDeclaredMadeForKids") is False
    durum = S.guvenli_status_govdesi({}, "public")
    assert durum["containsSyntheticMedia"] is yukleme["containsSyntheticMedia"]
    assert durum["selfDeclaredMadeForKids"] is yukleme["selfDeclaredMadeForKids"]
