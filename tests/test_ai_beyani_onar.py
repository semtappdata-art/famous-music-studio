# -*- coding: utf-8 -*-
"""upload/ai_beyani_onar.py — geçmişte silinmiş AI beyanını geri yazar.

NE KORUYOR (dört ayrı garanti, hepsi pahalı):

1. **Gizlilik DEĞİŞMEZ.** Betiğin tek işi `containsSyntheticMedia`'yı geri
   yazmak; görünürlüğe dokunması YouTube'da geri alınamayan bir yayın kararı
   demek.
2. **unlisted/private -> public ASLA.** `Küllerimden Geç` (`-CQ7MmUygTQ` +
   Shorts `jN78mJrZd3c`) BİLEREK unlisted (aynı sesin ikinci yüklemesi);
   public yapmak kanalın en büyük riski olan "inauthentic content"
   politikasına doğrudan yem (CLAUDE.md). Güvenlik kemeri kimliğe değil
   GEÇİŞİN YÖNÜNE bakıyor, bu yüzden testler de öyle bakıyor.
3. **Kuru koşu VARSAYILAN ve gerçekten kuru** — ağa tek bir yazım yok.
4. **Devam edebilirlik.** Kota/Ctrl+C ile yarıda kalan koşu ilerlemeyi
   KAYBETMEZ ve bir sonraki koşu onarılmışları tekrar yazmaz.

Ayrıca: gövdede `containsSyntheticMedia: True` GERÇEKTEN bulunuyor mu (asıl
arızanın imzası), ve bu mantık `set_privacy.guvenli_status_govdesi`'nden
ÇAĞRILIYOR mu — KOPYALANMIYOR mu (bu deponun belgelenmiş `derleme._enerji`
hata sınıfı).

YouTube API'sinin TAMAMI monkeypatch — hiçbir ağ çağrısı yok.
"""

import ast
import io
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import ai_beyani_onar as A
import set_privacy
import state_io

_KAYNAK = os.path.join(_REPO, "upload", "ai_beyani_onar.py")

# `videos.list(part="status")`'ın GERÇEKTE döndürdüğü alanlar (canlı ölçüm,
# 2026-09-11). `containsSyntheticMedia` BİLEREK yok — API onu döndürmüyor.
_CANLI_STATUS = {
    "uploadStatus": "processed",
    "privacyStatus": "public",
    "license": "youtube",
    "embeddable": True,
    "publicStatsViewable": True,
    "madeForKids": False,
    "selfDeclaredMadeForKids": False,
}


def _status(privacy="public", **ek):
    return dict(_CANLI_STATUS, privacyStatus=privacy, **ek)


class _Istek:
    def __init__(self, calistir):
        self._calistir = calistir

    def execute(self):
        return self._calistir()


class _Videos:
    """videos().list / videos().update taklidi.

    `tablo`: video_id -> status sözlüğü (yoksa "items": [] dönülür).
    `list_hatasi` / `update_hatasi`: (video_id, kacinci) -> istisna ya da None.
    """

    def __init__(self, tablo, list_hatasi=None, update_hatasi=None):
        self.tablo = tablo
        self.list_hatasi = list_hatasi
        self.update_hatasi = update_hatasi
        self.list_cagrilari = []
        self.guncellemeler = []

    def list(self, part=None, id=None):
        def calistir():
            self.list_cagrilari.append({"part": part, "id": id})
            if self.list_hatasi:
                hata = self.list_hatasi(id, len(self.list_cagrilari))
                if hata:
                    raise hata
            status = self.tablo.get(id)
            if status is None:
                return {"items": []}
            return {"items": [{"status": dict(status)}]}
        return _Istek(calistir)

    def update(self, part=None, body=None):
        def calistir():
            if self.update_hatasi:
                hata = self.update_hatasi(body.get("id"),
                                          len(self.guncellemeler) + 1)
                if hata:
                    raise hata
            self.guncellemeler.append({"part": part, "body": body})
            return {}
        return _Istek(calistir)


class _Youtube:
    def __init__(self, *a, **kw):
        self.videos_nesnesi = _Videos(*a, **kw)

    def videos(self):
        return self.videos_nesnesi


def _proje(kok, ad, **alanlar):
    klasor = os.path.join(str(kok), ad)
    os.makedirs(klasor, exist_ok=True)
    with io.open(os.path.join(klasor, "state.json"), "w", encoding="utf-8") as f:
        json.dump(alanlar, f, ensure_ascii=False)
    return klasor


@pytest.fixture
def kum(tmp_path):
    """Tek projeli (uzun + Shorts) bir içerik kökü + ilerleme dosyası yolu."""
    kok = tmp_path / "projects"
    kok.mkdir()
    _proje(kok, "Son Kez", youtube_video_id="VID_UZUN",
           youtube_shorts_video_id="VID_SHORTS", youtube_privacy="public")
    return {
        "kokler": (str(kok),),
        "durum": str(tmp_path / "ilerleme.json"),
        "kok": kok,
    }


def _kos(kum, youtube, **kw):
    kw.setdefault("uygula", True)
    kw.setdefault("limit", 50)
    return A.onar(youtube=youtube, kokler=kum["kokler"],
                  durum_yolu=kum["durum"], **kw)


# --------------------------------------------------------------------------
# 1) HEDEF LİSTESİ state'ten TÜRETİLİYOR (sabit liste YOK)
# --------------------------------------------------------------------------

def test_hedef_listesi_uc_kokten_ve_iki_anahtardan_turetiliyor(tmp_path):
    kokler = []
    for kok_ad, proje_ad in (("projects", "Son Kez"),
                             ("dj_sets", "City Pulse Set"),
                             ("derlemeler", "Gece Seansı Vol. 1")):
        kok = tmp_path / kok_ad
        kok.mkdir()
        _proje(kok, proje_ad,
               youtube_video_id=proje_ad + "_U",
               youtube_shorts_video_id=proje_ad + "_S")
        kokler.append(str(kok))

    hedefler = A.hedef_videolar(tuple(kokler))
    assert len(hedefler) == 6, "üç kökün ikişer videosu da hedeflenmeli"
    assert {h["video_id"] for h in hedefler} == {
        "Son Kez_U", "Son Kez_S", "City Pulse Set_U", "City Pulse Set_S",
        "Gece Seansı Vol. 1_U", "Gece Seansı Vol. 1_S"}
    assert {h["etiket"] for h in hedefler} == {"uzun", "shorts"}


def test_videosuz_ve_bozuk_state_atlaniyor(tmp_path):
    kok = tmp_path / "projects"
    kok.mkdir()
    _proje(kok, "Henüz Yüklenmedi")                     # video kimliği yok
    _proje(kok, "Var", youtube_video_id="V1")
    bozuk = kok / "Bozuk"
    bozuk.mkdir()
    (bozuk / "state.json").write_text("{yarım", encoding="utf-8")

    hedefler = A.hedef_videolar((str(kok),))
    assert [h["video_id"] for h in hedefler] == ["V1"]


def _kod_metinleri(yol):
    """Kaynaktaki string SABİTLERİ — docstring'ler HARİÇ.

    Ayrım şart: kimliklerin BELGEDE geçmesi (hangi videonun neden unlisted
    olduğu) doğru ve istenen şey; yasak olan, davranışın onlara BAĞLANMASI.
    """
    with io.open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    belgeler = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            govde = getattr(dugum, "body", None) or []
            if (govde and isinstance(govde[0], ast.Expr)
                    and isinstance(govde[0].value, ast.Constant)
                    and isinstance(govde[0].value.value, str)):
                belgeler.add(id(govde[0].value))
    return [d.value for d in ast.walk(agac)
            if isinstance(d, ast.Constant) and isinstance(d.value, str)
            and id(d) not in belgeler]


def test_kaynakta_sabit_video_kimligi_yok():
    """Bayatlayan-sabit-liste hata sınıfı: kimlikler koda GÖMÜLMEZ."""
    metinler = _kod_metinleri(_KAYNAK)
    for kimlik in ("-CQ7MmUygTQ", "jN78mJrZd3c"):
        for metin in metinler:
            assert kimlik not in metin, (
                "video kimliği KODA gömülmüş (%r) — hedefler state'ten "
                "türetilmeli" % metin)
    with io.open(_KAYNAK, encoding="utf-8") as f:
        kaynak = f.read()
    # Kök listesi de elle sayılmıyor: tek kanonik kaynak uyumluluk.
    assert "uyumluluk.proje_klasorleri" in kaynak
    assert A.hedef_videolar((str(os.path.join(_REPO, "yok_boyle_kok")),)) == []


# --------------------------------------------------------------------------
# 2) KURU KOŞU VARSAYILAN ve gerçekten KURU
# --------------------------------------------------------------------------

def test_kuru_kosu_hicbir_yazim_yapmiyor(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet = _kos(kum, yt, uygula=False)
    assert yt.videos_nesnesi.guncellemeler == [], "kuru koşu AĞA YAZDI"
    assert not os.path.exists(kum["durum"]), "kuru koşu ilerleme dosyası yazdı"
    assert ozet["kuru"] == 2 and ozet["onarilan"] == 0


def test_kuru_kosu_gizliligi_gercekten_okuyor(kum):
    """Kuru koşunun raporu tahmine değil OKUMAYA dayanmalı."""
    yt = _Youtube({"VID_UZUN": _status("unlisted"), "VID_SHORTS": _status()})
    _kos(kum, yt, uygula=False)
    assert [c["id"] for c in yt.videos_nesnesi.list_cagrilari] == [
        "VID_UZUN", "VID_SHORTS"]


def test_main_varsayilani_kuru_kosu(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(A, "onar", lambda **kw: cagrilar.append(kw) or {})
    A.main([])
    assert cagrilar[0]["uygula"] is False


def test_main_uygula_ve_dry_run_birlikte_kuru_kaliyor(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(A, "onar", lambda **kw: cagrilar.append(kw) or {})
    A.main(["--uygula", "--dry-run"])
    assert cagrilar[0]["uygula"] is False, "çelişkide GÜVENLİ olan kazanmalı"


def test_is_yoksa_kimlik_dogrulama_yapilmiyor(kum, monkeypatch):
    def patlat():
        raise AssertionError("iş yokken kimlik doğrulamaya gidilmemeli")
    monkeypatch.setattr(A, "get_authenticated_service", patlat)
    ozet = A.onar(kokler=(str(kum["kok"] / "yok"),), durum_yolu=kum["durum"])
    assert ozet["planlanan"] == 0


# --------------------------------------------------------------------------
# 3) MEVCUT GİZLİLİK KORUNUYOR
# --------------------------------------------------------------------------

@pytest.mark.parametrize("gizlilik", ["public", "unlisted", "private"])
def test_mevcut_gizlilik_aynen_geri_yaziliyor(kum, gizlilik):
    yt = _Youtube({"VID_UZUN": _status(gizlilik), "VID_SHORTS": _status(gizlilik)})
    _kos(kum, yt)
    yazilan = [g["body"]["status"]["privacyStatus"]
               for g in yt.videos_nesnesi.guncellemeler]
    assert yazilan == [gizlilik, gizlilik]


def test_kullerimden_gec_unlisted_kaliyor(kum):
    """BİLEREK unlisted olan kayıt unlisted KALMALI (CLAUDE.md)."""
    yt = _Youtube({"VID_UZUN": _status("unlisted"),
                   "VID_SHORTS": _status("unlisted")})
    _kos(kum, yt)
    for g in yt.videos_nesnesi.guncellemeler:
        assert g["body"]["status"]["privacyStatus"] == "unlisted"


def test_gizlilik_state_ten_degil_youtube_dan_okunuyor(kum):
    """`state.json`'daki `youtube_privacy` bir AYNA, gerçek değil."""
    # state "public" diyor, YouTube "unlisted" — YouTube kazanmalı.
    yt = _Youtube({"VID_UZUN": _status("unlisted"), "VID_SHORTS": _status("unlisted")})
    _kos(kum, yt)
    assert all(g["body"]["status"]["privacyStatus"] == "unlisted"
               for g in yt.videos_nesnesi.guncellemeler)


# --------------------------------------------------------------------------
# 4) GÜVENLİK KEMERİ: unlisted/private -> public ASLA
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mevcut", ["unlisted", "private"])
def test_kemer_public_yukseltmesini_reddediyor(mevcut):
    with pytest.raises(A.GizlilikYukseltmeHatasi):
        A.kemer_kontrol(mevcut, "public")


def test_kemer_ayni_gizlilige_izin_veriyor():
    for gizlilik in ("public", "unlisted", "private"):
        A.kemer_kontrol(gizlilik, gizlilik)          # istisna YOK


def test_kemer_boru_hattinda_gercekten_atesleniyor(kum, monkeypatch):
    """Yazılacak gizliliği üreten mantık BOZULSA bile yazım durmalı."""
    monkeypatch.setattr(A, "_hedef_gizlilik", lambda mevcut: "public")
    yt = _Youtube({"VID_UZUN": _status("unlisted"),
                   "VID_SHORTS": _status("private")})
    ozet = _kos(kum, yt)
    assert yt.videos_nesnesi.guncellemeler == [], (
        "KEMER TUTMADI: unlisted/private video public'e yazıldı")
    assert ozet["engellenen"] == 2 and ozet["onarilan"] == 0
    assert not os.path.exists(kum["durum"]), "engellenen video onarılmış sayıldı"


def test_hicbir_koda_yolunda_public_yukseltmesi_yok(kum, monkeypatch):
    """Kaba kuvvet: her gizlilik kombinasyonunda yazılan değer okunanla aynı."""
    for mevcut in ("public", "unlisted", "private"):
        yt = _Youtube({"VID_UZUN": _status(mevcut), "VID_SHORTS": _status(mevcut)})
        if os.path.exists(kum["durum"]):
            os.remove(kum["durum"])
        _kos(kum, yt)
        for g in yt.videos_nesnesi.guncellemeler:
            yazilan = g["body"]["status"]["privacyStatus"]
            assert yazilan == mevcut
            assert not (mevcut != "public" and yazilan == "public")


# --------------------------------------------------------------------------
# 5) GÖVDEDE AI BEYANI GERÇEKTEN VAR ve mantık KOPYALANMIYOR
# --------------------------------------------------------------------------

def test_govdede_ai_beyani_var(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt)
    assert len(yt.videos_nesnesi.guncellemeler) == 2
    for g in yt.videos_nesnesi.guncellemeler:
        durum = g["body"]["status"]
        assert durum["containsSyntheticMedia"] is True, (
            "onarım gövdesinde AI beyanı YOK — betik arızayı TEKRARLIYOR")
        assert durum["selfDeclaredMadeForKids"] is False
        assert set(durum) != {"privacyStatus"}
        assert g["part"] == "status"


def test_diger_status_alanlari_korunuyor(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt)
    durum = yt.videos_nesnesi.guncellemeler[0]["body"]["status"]
    assert durum["license"] == "youtube"
    assert durum["embeddable"] is True
    assert "uploadStatus" not in durum


def test_set_privacy_fonksiyonu_cagriliyor_kopyalanmiyor(kum, monkeypatch):
    """`derleme._enerji` hata sınıfı: mantık paylaşılır, kopyalanmaz."""
    with io.open(_KAYNAK, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    kendi_tanimlari = {d.name for d in ast.walk(agac)
                       if isinstance(d, ast.FunctionDef)}
    assert "guvenli_status_govdesi" not in kendi_tanimlari, (
        "gövde mantığı KOPYALANMIŞ — set_privacy'den import edilmeli")

    cagrildi = []
    gercek = set_privacy.guvenli_status_govdesi

    def casus(mevcut_status, privacy):
        cagrildi.append(privacy)
        return gercek(mevcut_status, privacy)

    monkeypatch.setattr(set_privacy, "guvenli_status_govdesi", casus)
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt)
    assert cagrildi == ["public", "public"]


def test_private_videoda_publishat_korunuyor(kum):
    """Zamanlanmış (golden-hour) bir video yazımda zamanlamasını kaybetmemeli."""
    yt = _Youtube({
        "VID_UZUN": _status("private", publishAt="2026-09-20T19:00:00Z"),
        "VID_SHORTS": _status("private", publishAt="2026-09-20T19:00:00Z")})
    _kos(kum, yt)
    durum = yt.videos_nesnesi.guncellemeler[0]["body"]["status"]
    assert durum["publishAt"] == "2026-09-20T19:00:00Z"


# --------------------------------------------------------------------------
# 6) OKUMA BAŞARISIZSA ATLA (tahminle YAZMA)
# --------------------------------------------------------------------------

def test_video_bulunamazsa_atlaniyor(kum):
    yt = _Youtube({"VID_SHORTS": _status()})            # VID_UZUN yok
    ozet = _kos(kum, yt)
    assert [g["body"]["id"] for g in yt.videos_nesnesi.guncellemeler] == ["VID_SHORTS"]
    assert ozet["atlanan"] == 1 and ozet["onarilan"] == 1


def test_okuma_istisnasinda_atlaniyor(kum):
    def list_hatasi(video_id, kacinci):
        if video_id == "VID_UZUN":
            return RuntimeError("backendError")
        return None
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()},
                  list_hatasi=list_hatasi)
    ozet = _kos(kum, yt)
    assert [g["body"]["id"] for g in yt.videos_nesnesi.guncellemeler] == ["VID_SHORTS"]
    assert ozet["atlanan"] == 1


def test_gizlilik_alani_bossa_atlaniyor(kum):
    eksik = dict(_CANLI_STATUS)
    eksik.pop("privacyStatus")
    yt = _Youtube({"VID_UZUN": eksik, "VID_SHORTS": _status()})
    ozet = _kos(kum, yt)
    assert [g["body"]["id"] for g in yt.videos_nesnesi.guncellemeler] == ["VID_SHORTS"]
    assert ozet["atlanan"] == 1


# --------------------------------------------------------------------------
# 7) --limit
# --------------------------------------------------------------------------

def test_limit_uyuluyor(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet = _kos(kum, yt, limit=1)
    assert len(yt.videos_nesnesi.guncellemeler) == 1
    assert len(yt.videos_nesnesi.list_cagrilari) == 1, "limit OKUMAYI da kapsamalı"
    assert ozet["kalan"] == 1


def test_limit_kota_tahminine_yansiyor(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet = _kos(kum, yt, limit=1)
    assert ozet["tahmini_birim"] == A.VIDEO_BASINA_BIRIM == 51


def test_varsayilan_limit_gunluk_kotanin_kucuk_bir_dilimi():
    assert 0 < A.VARSAYILAN_LIMIT * A.VIDEO_BASINA_BIRIM < A.GUNLUK_KOTA * 0.15


# --------------------------------------------------------------------------
# 8) KOTA: TEMİZ DUR, İLERLEME KAYBOLMASIN
# --------------------------------------------------------------------------

def _kota_hatasi():
    return RuntimeError(
        "<HttpError 403 ... reason: quotaExceeded, The request cannot be "
        "completed because you have exceeded your quota.>")


def test_kota_yazmada_temiz_duruyor_ve_ilerleme_kaliyor(kum):
    def update_hatasi(video_id, kacinci):
        return _kota_hatasi() if video_id == "VID_SHORTS" else None
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()},
                  update_hatasi=update_hatasi)
    ozet = _kos(kum, yt)                     # istisna DIŞARI SIZMAMALI
    assert ozet["kota_durdu"] is True
    assert ozet["onarilan"] == 1 and ozet["kalan"] == 1
    kayit = json.load(io.open(kum["durum"], encoding="utf-8"))
    assert list(kayit) == ["VID_UZUN"], "yarım kalan iş diskte kaybolmuş"


def test_kota_okumada_temiz_duruyor(kum):
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()},
                  list_hatasi=lambda vid, k: _kota_hatasi())
    ozet = _kos(kum, yt)
    assert ozet["kota_durdu"] is True
    assert yt.videos_nesnesi.guncellemeler == []
    assert not os.path.exists(kum["durum"])


def test_kota_imzalari_taniniyor():
    assert A.kota_hatasi_mi(_kota_hatasi())
    assert A.kota_hatasi_mi(RuntimeError("rateLimitExceeded"))
    assert not A.kota_hatasi_mi(RuntimeError("backendError"))


def test_kota_disi_yazim_hatasi_kosuyu_durdurmuyor(kum):
    def update_hatasi(video_id, kacinci):
        return RuntimeError("backendError") if video_id == "VID_UZUN" else None
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()},
                  update_hatasi=update_hatasi)
    ozet = _kos(kum, yt)
    assert ozet["hatali"] == 1 and ozet["onarilan"] == 1
    assert ozet["kota_durdu"] is False


# --------------------------------------------------------------------------
# 9) DEVAM EDEBİLİRLİK
# --------------------------------------------------------------------------

def test_yeniden_calistirma_onarilmislari_atliyor(kum):
    yt1 = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt1, limit=1)
    assert [g["body"]["id"] for g in yt1.videos_nesnesi.guncellemeler] == ["VID_UZUN"]

    yt2 = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet = _kos(kum, yt2)
    assert [g["body"]["id"] for g in yt2.videos_nesnesi.guncellemeler] == ["VID_SHORTS"]
    assert [c["id"] for c in yt2.videos_nesnesi.list_cagrilari] == ["VID_SHORTS"], (
        "onarılmış video için OKUMA bile yapılmamalı (kota)")
    assert ozet["kalan"] == 0

    yt3 = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet3 = _kos(kum, yt3)
    assert yt3.videos_nesnesi.guncellemeler == [], "üçüncü koşu boşa kota yaktı"
    assert ozet3["planlanan"] == 0


def test_ilerleme_atomik_yaziliyor(kum, monkeypatch):
    """state.json'ın atomik yazıcısı KULLANILIYOR, yeni bir tane yazılmadı."""
    cagrilar = []
    gercek = state_io._atomik_yaz

    def casus(yol, veri):
        cagrilar.append(yol)
        return gercek(yol, veri)

    monkeypatch.setattr(state_io, "_atomik_yaz", casus)
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt)
    assert cagrilar == [kum["durum"], kum["durum"]], (
        "ilerleme her videodan SONRA atomik yazılmalı")


def test_ilerleme_uretim_state_json_larina_dokunmuyor(kum):
    """Onarım damgası kataloğun state.json'larına GİRMEZ (ayrı dosya)."""
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    _kos(kum, yt)
    proje_durumu = json.load(io.open(
        os.path.join(str(kum["kok"]), "Son Kez", "state.json"), encoding="utf-8"))
    assert "ai_beyani_onarildi_at" not in proje_durumu
    assert proje_durumu["youtube_privacy"] == "public"


def test_bozuk_ilerleme_dosyasi_kosuyu_durdurmuyor(kum):
    with io.open(kum["durum"], "w", encoding="utf-8") as f:
        f.write("{yarım")
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()})
    ozet = _kos(kum, yt)
    assert ozet["onarilan"] == 2


def test_ctrl_c_temiz_duruyor(kum):
    def update_hatasi(video_id, kacinci):
        return KeyboardInterrupt() if video_id == "VID_SHORTS" else None
    yt = _Youtube({"VID_UZUN": _status(), "VID_SHORTS": _status()},
                  update_hatasi=update_hatasi)
    ozet = _kos(kum, yt)
    assert ozet["kesildi"] is True and ozet["onarilan"] == 1
    assert list(json.load(io.open(kum["durum"], encoding="utf-8"))) == ["VID_UZUN"]


# --------------------------------------------------------------------------
# 10) LOG
# --------------------------------------------------------------------------

def test_log_maskeleniyor(monkeypatch, tmp_path):
    hedef = tmp_path / "onar.log"
    monkeypatch.setattr(A, "LOG_PATH", str(hedef))
    A.log("HATA: https://x/y?access_token=EAAGizliDeger12345&fields=id")
    icerik = hedef.read_text(encoding="utf-8")
    assert "EAAGizliDeger12345" not in icerik
    assert "MASKELİ" in icerik
