# -*- coding: utf-8 -*-
"""YouTube görünürlük PLANI: önceden yayınlanmış bir videoyu golden-hour'da public'e alma.

NEDEN VAR (2026-09-12, kullanıcı kararı): `Küllerimden Geç` (yeni görselli
sürüm) kalacak, `Yeniden Doğacağım` (videoda kapak kartı eksik) liste dışı.
`Küllerimden Geç`in Shorts'u unlisted duruyor ve public'e dönmesi gerekiyor.
YouTube'un kendi zamanlaması burada İŞE YARAMIYOR: `status.publishAt` yalnız
HİÇ yayınlanmamış videoda kabul ediliyor, önceden public olmuş bir videoda
`invalidPublishAt` dönüyor (2026-09-12'de ölçüldü). Bu yüzden public anını
saatlik koşu golden-hour içinde KENDİSİ tetikliyor.

SÖZLEŞME (state alanları):
  * `youtube_gorunurluk_plani = {"hedef": "public", "sebep": ..., "istendi_at": ...}`
    — varsa uygulanacak iş. Başarıda SİLİNİR; hatada KALIR ve
    `son_hata_at`/`son_hata` eklenir.
  * Başarıda: `youtube_privacy`/`youtube_shorts_privacy` = hedef,
    `youtube_publish_at`/`youtube_shorts_publish_at` = GERÇEK public anı (UTC
    "...Z" — `auto_process._son_yeni_yayin_ani` uzun formatınkini 52 saatlik
    tempo tabanına sayıyor) YALNIZ gizliliği gerçekten DEĞİŞEN videoya (bkz.
    bölüm 7; `tempo_sayilir: False` -> `youtube_public_ani_tempo_disi`),
    `youtube_gorunurluk_uygulandi_at` = pencere kuralının damgası.

KURALLAR: yalnız golden-hour içinde; pencere başına EN FAZLA BİR proje (iki
şarkı aynı anda yayına dönmesin); hata sonrası aynı projeye saatte bir
`videos.update` harcanmaz; `yayin_beklet` ya da `uyumluluk` HATASI varsa
uygulanmaz; gövde `set_privacy.guvenli_status_govdesi` ile kurulur (AI beyanı
KORUNUR — `videos.update` gövdede olmayan alanları siler).

AĞA ÇIKILMIYOR: YouTube servisi sahte, soket bağlantısı patlatılıyor.
"""

import json
import os
import socket
import sys
from datetime import datetime, timedelta, timezone

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import auto_process as ap                            # noqa: E402
import config                                        # noqa: E402
import uyumluluk                                     # noqa: E402

TR = config.TR_TZ
PENCERE_ICI = datetime(2026, 9, 13, 12, 30, tzinfo=TR)
PENCERE_DISI = datetime(2026, 9, 13, 9, 30, tzinfo=TR)


@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    def _patla(*a, **k):
        raise AssertionError("test ağa çıkmaya çalıştı")
    monkeypatch.setattr(socket.socket, "connect", _patla)
    monkeypatch.setattr(socket, "create_connection", _patla)


class _SahteYouTube:
    """videos().list/update — gizliliği bellekte tutar, gövdeleri kaydeder."""

    def __init__(self, gizlilik, update_patlat=False):
        self.gizlilik = dict(gizlilik)
        self.guncellemeler = []
        self.listeler = 0
        self.update_patlat = update_patlat
        self._is = None

    def videos(self):
        return self

    def list(self, part, id, **kw):
        self._is = ("list", id.split(","))
        return self

    def update(self, part, body, **kw):
        self._is = ("update", body)
        return self

    def execute(self):
        tur, veri = self._is
        if tur == "list":
            self.listeler += 1
            return {"items": [
                {"id": v, "status": {"uploadStatus": "processed",
                                     "privacyStatus": self.gizlilik[v],
                                     "license": "youtube", "embeddable": True,
                                     "publicStatsViewable": True,
                                     "madeForKids": False,
                                     "selfDeclaredMadeForKids": False}}
                for v in veri if v in self.gizlilik]}
        if self.update_patlat:
            raise RuntimeError("quotaExceeded")
        self.guncellemeler.append(veri)
        self.gizlilik[veri["id"]] = veri["status"]["privacyStatus"]
        return {"id": veri["id"]}


def _plan(istendi="2026-09-12T22:50:00", **ek):
    p = {"hedef": "public", "sebep": "kullanıcı kararı", "istendi_at": istendi}
    p.update(ek)
    return p


def _proje(kok, ad, durum):
    d = kok / ad
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps(durum, ensure_ascii=False),
                                  encoding="utf-8")
    return str(d)


def _oku(p):
    with open(os.path.join(p, "state.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    kok = tmp_path / "projects"
    kok.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    satirlar = []
    monkeypatch.setattr(ap, "log", satirlar.append)
    saat = {"simdi": PENCERE_ICI}
    monkeypatch.setattr(ap, "_tr_simdi", lambda: saat["simdi"])
    servis = {"yt": None}

    def _servis():
        if servis["yt"] is None:
            raise AssertionError("YouTube servisi beklenmedik şekilde istendi")
        return servis["yt"]
    monkeypatch.setattr(ap, "_youtube_servisi", _servis)
    return type("O", (), {"kok": kok, "log": satirlar, "saat": saat,
                          "servis": servis})


def _kg(ortam, **ek):
    d = {"youtube_video_id": "-CQ7MmUygTQ", "youtube_privacy": "unlisted",
         "youtube_publish_at": None,
         "youtube_shorts_video_id": "jN78mJrZd3c",
         "youtube_shorts_privacy": "unlisted", "youtube_shorts_publish_at": None,
         "youtube_gorunurluk_plani": _plan()}
    d.update(ek)
    return _proje(ortam.kok, "Kullerimden Gec", d)


# --- 1. pencere dışında hiçbir şey yapılmıyor ------------------------------

def test_pencere_disinda_hicbir_sey_yapilmiyor(ortam):
    p = _kg(ortam)
    ortam.saat["simdi"] = PENCERE_DISI
    ap._youtube_gorunurluk_planlarini_uygula([p])   # servis istenirse patlar
    assert _oku(p)["youtube_gorunurluk_plani"]["hedef"] == "public"


# --- 2. pencerede tek proje uygulanıyor, state alanları doğru ---------------

def test_pencerede_uygulaniyor_state_alanlari_ve_plan_siliniyor(ortam):
    p = _kg(ortam, youtube_privacy="public")        # uzun format zaten public
    yt = _SahteYouTube({"-CQ7MmUygTQ": "public", "jN78mJrZd3c": "unlisted"})
    ortam.servis["yt"] = yt
    ap._youtube_gorunurluk_planlarini_uygula([p])

    d = _oku(p)
    assert "youtube_gorunurluk_plani" not in d
    assert d["youtube_privacy"] == "public"
    assert d["youtube_shorts_privacy"] == "public"
    beklenen = PENCERE_ICI.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 2026-09-13: bu satır eskiden `== beklenen` idi — yani ARIZAYI sabitliyordu
    # (zaten public uzun formata damga -> 52 saatlik taban yeniden başlıyordu).
    assert d["youtube_publish_at"] is None
    assert d["youtube_shorts_publish_at"] == beklenen
    assert d["youtube_gorunurluk_uygulandi_at"]
    # zaten public olan uzun formata videos.update HARCANMADI
    assert [g["id"] for g in yt.guncellemeler] == ["jN78mJrZd3c"]
    assert yt.gizlilik == {"-CQ7MmUygTQ": "public", "jN78mJrZd3c": "public"}
    assert any("public" in s and "Kullerimden Gec" in s for s in ortam.log)


def test_publish_at_tempo_sayacinin_okuyabilecegi_bicimde(ortam):
    p = _kg(ortam)
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "unlisted",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert ap._son_yeni_yayin_ani([p]) == PENCERE_ICI.timestamp()


def test_pencerede_en_fazla_bir_proje_ve_sira_istendi_at(ortam):
    bgk = _proje(ortam.kok, "Ikinci", {
        "youtube_video_id": "b1", "youtube_privacy": "unlisted",
        "youtube_gorunurluk_plani": _plan(istendi="2026-09-12T22:51:00")})
    kg = _kg(ortam)
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "unlisted",
                                        "jN78mJrZd3c": "unlisted",
                                        "b1": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([bgk, kg])  # liste sırası ters
    assert "youtube_gorunurluk_plani" not in _oku(kg), "önce istenen önce uygulanmalı"
    assert "youtube_gorunurluk_plani" in _oku(bgk), "aynı koşuda ikinci proje YOK"


# --- 3. aynı pencerede ikinci proje bekliyor, sonraki pencerede uygulanıyor --

def test_ayni_pencerede_ikinci_proje_bekliyor(ortam):
    uygulandi = (PENCERE_ICI - timedelta(minutes=25)).isoformat()
    kg = _proje(ortam.kok, "Kullerimden Gec", {
        "youtube_video_id": "-CQ7MmUygTQ", "youtube_privacy": "public",
        "youtube_gorunurluk_uygulandi_at": uygulandi})
    bgk = _proje(ortam.kok, "Ikinci", {
        "youtube_video_id": "b1", "youtube_privacy": "unlisted",
        "youtube_gorunurluk_plani": _plan()})
    ap._youtube_gorunurluk_planlarini_uygula([kg, bgk])   # servis istenirse patlar
    assert "youtube_gorunurluk_plani" in _oku(bgk)
    assert any("bekliyor" in s for s in ortam.log), ortam.log

    ortam.saat["simdi"] = datetime(2026, 9, 13, 18, 10, tzinfo=TR)
    ortam.servis["yt"] = _SahteYouTube({"b1": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([kg, bgk])
    assert "youtube_gorunurluk_plani" not in _oku(bgk)


# --- 4. hata: plan kalıyor, aynı projeye saatte bir update harcanmıyor -------

def test_hata_olunca_plan_kaliyor_ve_soguma_uygulaniyor(ortam):
    p = _kg(ortam)
    yt = _SahteYouTube({"-CQ7MmUygTQ": "unlisted", "jN78mJrZd3c": "unlisted"},
                       update_patlat=True)
    ortam.servis["yt"] = yt
    ap._youtube_gorunurluk_planlarini_uygula([p])
    d = _oku(p)
    assert d["youtube_gorunurluk_plani"]["hedef"] == "public"
    assert d["youtube_gorunurluk_plani"]["son_hata_at"]
    assert "quotaExceeded" in d["youtube_gorunurluk_plani"]["son_hata"]
    assert d["youtube_privacy"] == "unlisted", "başarısız uygulama state'i değiştirmemeli"
    assert "youtube_gorunurluk_uygulandi_at" not in d
    assert any("HATA" in s for s in ortam.log)

    # bir saat sonraki koşu: soğuma sürüyor, servis İSTENMEMELİ
    ortam.servis["yt"] = None
    ortam.saat["simdi"] = PENCERE_ICI + timedelta(hours=1)
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert _oku(p)["youtube_gorunurluk_plani"]["son_hata"]

    # soğuma bitti (akşam penceresi): yeniden deneniyor ve başarıyor
    ortam.saat["simdi"] = datetime(2026, 9, 13, 18, 10, tzinfo=TR)
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "unlisted",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert "youtube_gorunurluk_plani" not in _oku(p)


def test_geri_okuma_hedefi_dogrulamazsa_hata_sayiliyor(ortam):
    p = _kg(ortam)

    class _Yutan(_SahteYouTube):
        def execute(self):
            if self._is[0] == "update":
                self.guncellemeler.append(self._is[1])
                return {}                      # kabul etti gibi ama değiştirmedi
            return super().execute()
    ortam.servis["yt"] = _Yutan({"-CQ7MmUygTQ": "unlisted", "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    d = _oku(p)
    assert "youtube_gorunurluk_plani" in d and d["youtube_privacy"] == "unlisted"


# --- 5. gövde AI beyanını koruyor ------------------------------------------

def test_status_govdesi_ai_beyanini_koruyor(ortam):
    p = _kg(ortam)
    yt = _SahteYouTube({"-CQ7MmUygTQ": "unlisted", "jN78mJrZd3c": "unlisted"})
    ortam.servis["yt"] = yt
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert len(yt.guncellemeler) == 2
    for govde in yt.guncellemeler:
        st = govde["status"]
        assert st["privacyStatus"] == "public"
        assert st["containsSyntheticMedia"] is True
        assert st["selfDeclaredMadeForKids"] is False
        assert st["license"] == "youtube" and st["embeddable"] is True
        assert "uploadStatus" not in st


# --- 6. kapılar: bekletme ve uyumluluk -------------------------------------

def test_bekletilen_projede_uygulanmiyor(ortam):
    p = _kg(ortam, yayin_beklet={"sebep": "yeniden render"})
    ap._youtube_gorunurluk_planlarini_uygula([p])   # servis istenirse patlar
    assert "youtube_gorunurluk_plani" in _oku(p)


def test_uyumluluk_hatasi_varsa_public_yapilmiyor(ortam, monkeypatch):
    """Aynı sesin ikinci kopyasını public'e çıkarmak da bir YAYINDIR."""
    p = _kg(ortam)
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama="render": (["sesi 'X' ile BİREBİR AYNI (md5)"], []))
    ap._youtube_gorunurluk_planlarini_uygula([p])   # servis istenirse patlar
    d = _oku(p)
    assert "youtube_gorunurluk_plani" in d
    assert any("uyumluluk" in s for s in ortam.log)


def test_plansiz_katalogda_servis_hic_istenmiyor(ortam):
    p = _proje(ortam.kok, "Sade", {"youtube_video_id": "x", "youtube_privacy": "public"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert ortam.log == []


def test_drain_plani_uyguluyor(ortam, monkeypatch):
    """Bağlantı: fonksiyon yazılmış ama saatlik kuyruk çağırmıyorsa ölüdür."""
    cagrilar = []
    monkeypatch.setattr(ap, "_youtube_gorunurluk_planlarini_uygula",
                        lambda dirs: cagrilar.append(list(dirs)))
    monkeypatch.setattr(ap, "_check_youtube_captions", lambda p, s: False)
    p = _proje(ortam.kok, "Sade", {})
    ap._drain_golden_hour_queue([p])
    assert cagrilar == [[p]]


# --- 7. TEMPO: publish_at YALNIZ gerçekten değişen videoya (2026-09-13) ------
#
# ARIZA (doğrulama turu 2, bulgu 3): plan her iki öneke de `*_publish_at`
# yazıyordu. `Küllerimden Geç`in uzun formatı ZATEN public (kullanıcı Studio'dan
# açtı); plan yalnız Shorts'u açacak. Ama `youtube_publish_at` = plan anı
# yazılınca `_son_yeni_yayin_ani` bunu YENİ YAYIN saydı ve 52 saatlik taban
# yeniden başladı: `Sabah Senin` 28 saat geri itildi. Ölçüt artık API'den okunan
# ÖNCEKİ gizlilik: değişmeyen videoya damga yazılmaz. Gerçek bir unlisted ->
# public UZUN format geçişi tempoya sayılmaya DEVAM eder (`tempo_sayilir`
# varsayılanı True); False verilirse o an ayrı bir alana yazılır.

import time as _time


def _dun_pencerede():
    """Gerçek saate göre DÜN 12:30 TR: pencere içinde, her zaman geçmişte ve
    52 saatten YAKIN — yani tabanı başlatırsa mutlaka bekletir."""
    return (datetime.now(TR) - timedelta(days=1)).replace(
        hour=12, minute=30, second=0, microsecond=0)


def _yerel_damga(saat_once):
    return _time.strftime("%Y-%m-%dT%H:%M:%S",
                          _time.localtime(_time.time() - saat_once * 3600))


def _utc(an):
    return an.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_youtubeda_uygula_gercekten_degisen_kimlikleri_dondurur():
    yt = _SahteYouTube({"a": "public", "b": "unlisted"})
    assert ap._gorunurlugu_youtubeda_uygula(yt, ["a", "b"], "public") == ["b"]
    assert [g["id"] for g in yt.guncellemeler] == ["b"]


def test_zaten_public_uzun_formatin_publish_at_i_yazilmaz_degisen_shorts_unki_yazilir(ortam):
    # state BAYAT ("unlisted") ama YouTube'da uzun format zaten public —
    # canlı `Küllerimden Geç` state'inin birebir eşi. Ölçüt state değil API.
    p = _kg(ortam, youtube_privacy="unlisted")
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "public",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    d = _oku(p)
    assert "youtube_gorunurluk_plani" not in d
    assert d["youtube_publish_at"] is None, "değişmeyen uzun formata damga yazıldı"
    assert d["youtube_shorts_publish_at"] == _utc(PENCERE_ICI)
    assert d["youtube_privacy"] == "public" and d["youtube_shorts_privacy"] == "public"
    assert "youtube_public_ani_tempo_disi" not in d


def test_shorts_only_plan_sonrasi_yeni_sarkinin_52_saatlik_tabani_baslamaz(ortam):
    ortam.saat["simdi"] = _dun_pencerede()
    p = _kg(ortam, youtube_privacy="public", youtube_uploaded_at=_yerel_damga(100))
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "public",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    assert "youtube_gorunurluk_plani" not in _oku(p)
    yeni = _proje(ortam.kok, "Sabah Senin", {})
    assert ap._auto_pace_count([yeni], [p, yeni], 1) == 1, (
        "yalnız Shorts açıldı; yeni şarkının tabanı yeniden BAŞLAMAMALI")


def test_tempo_sayilir_varsayilaninda_gercek_unlisted_public_uzun_format_tabani_baslatir(ortam):
    ortam.saat["simdi"] = _dun_pencerede()
    p = _kg(ortam, youtube_uploaded_at=_yerel_damga(100))
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "unlisted",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    d = _oku(p)
    assert d["youtube_publish_at"] == _utc(ortam.saat["simdi"])
    yeni = _proje(ortam.kok, "Sabah Senin", {})
    assert ap._auto_pace_count([yeni], [p, yeni], 1) == 0, "kural GEVŞEMEMELİ"


def test_tempo_sayilir_false_uzun_format_anini_ayri_alana_yazar_taban_baslamaz(ortam):
    ortam.saat["simdi"] = _dun_pencerede()
    p = _kg(ortam, youtube_uploaded_at=_yerel_damga(100),
            youtube_gorunurluk_plani=_plan(tempo_sayilir=False))
    ortam.servis["yt"] = _SahteYouTube({"-CQ7MmUygTQ": "unlisted",
                                        "jN78mJrZd3c": "unlisted"})
    ap._youtube_gorunurluk_planlarini_uygula([p])
    d = _oku(p)
    an = _utc(ortam.saat["simdi"])
    assert d["youtube_publish_at"] is None
    assert d["youtube_public_ani_tempo_disi"] == an
    assert d["youtube_shorts_publish_at"] == an
    assert "youtube_public_ani_tempo_disi" not in ap.YENI_YAYIN_PUBLIC_ANI_KEYS
    yeni = _proje(ortam.kok, "Sabah Senin", {})
    assert ap._auto_pace_count([yeni], [p, yeni], 1) == 1


class _GecikmeliYouTube(_SahteYouTube):
    """update 200 döner ama ilk geri okuma ESKİ değeri verir (yayılma gecikmesi):
    canlı vaka 2026-09-13 12:06, Küllerimden Geç Shorts jN78mJrZd3c."""

    def __init__(self, gizlilik, gecikme_okuma=1):
        super().__init__(gizlilik)
        self.bekleyen = {}
        self.gecikme_okuma = gecikme_okuma

    def execute(self):
        tur, veri = self._is
        if tur == "update":
            self.bekleyen[veri["id"]] = veri["status"]["privacyStatus"]
            self.guncellemeler.append(veri)
            return veri
        # list: gecikme dolana kadar eski değer (sayaç super().execute'ta artar)
        if self.listeler + 1 > 1 + self.gecikme_okuma:
            self.gizlilik.update(self.bekleyen)
        return super().execute()


def test_geri_okuma_gecikirse_ikinci_denemede_dogrulanir(monkeypatch):
    uykular = []
    monkeypatch.setattr(ap.time, "sleep", uykular.append)
    yt = _GecikmeliYouTube({"s": "unlisted"}, gecikme_okuma=1)
    assert ap._gorunurlugu_youtubeda_uygula(yt, ["s"], "public") == ["s"]
    assert uykular == [ap.config.GORUNURLUK_GERI_OKUMA_BEKLEME_SN]
    assert yt.listeler == 3          # önce + 2 geri okuma


def test_geri_okuma_iki_denemede_de_tutmazsa_hata(monkeypatch):
    monkeypatch.setattr(ap.time, "sleep", lambda s: None)
    yt = _GecikmeliYouTube({"s": "unlisted"}, gecikme_okuma=5)
    with pytest.raises(RuntimeError, match="geri okuma hedefi"):
        ap._gorunurlugu_youtubeda_uygula(yt, ["s"], "public")
    assert yt.listeler == 1 + ap.config.GORUNURLUK_GERI_OKUMA_DENEME
