# -*- coding: utf-8 -*-
"""turev_takvimi — Aşama 1: plan, takvim, kurallar, engeller, hatırlatma, bağlantılar.

Kullanıcı kararları (2026-09-13): türevler 52 saatlik tabana SAYILMAZ; günde en
fazla 1 türev (golden-hour), YouTube'a video yükleyen türev haftada 1, yeni şarkı
yayınının ±24 saatinde türev yok, aynı şarkının iki türevi arası ≥48 saat, pencere
21 gün, şarkı için YouTube ikinci kesiti 2026-10-09'dan önce yok, DJ kulisi ayrı
onay, hatırlatma bayrağı varsayılan KAPALI. Bu aşamada YAYIN YOK.

Ağa ÇIKMAZ (soket + notify patlatılıyor), gerçek state'e YAZMAZ (her şey tmp_path).
"""

import ast
import datetime
import io
import json
import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import config                                             # noqa: E402
import uyumluluk                                          # noqa: E402
import turev_takvimi as TT                                # noqa: E402

TR = datetime.timezone(datetime.timedelta(hours=3))


def T(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).timestamp()


def iso(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).isoformat()


SS = {"youtube_video_id": "Ozn9", "youtube_uploaded_at": "2026-09-13T02:22:17",
      "youtube_publish_at": "2026-09-13T09:00:00Z"}          # T0 = 13 Eyl 12:00 TR
JR = {"youtube_video_id": "wo2", "youtube_uploaded_at": "2026-09-07T16:18:34",
      "youtube_publish_at": None, "dj_tarama_temiz": True}  # T0 = 07 Eyl 16:18


@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    import socket
    import notify

    def _yasak(*a, **k):
        raise AssertionError("türev testi ağa/bildirime çıktı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)
    for ad in ("send", "send_text", "send_photo"):
        monkeypatch.setattr(notify, ad, _yasak)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    for ad in ("projects", "dj_sets"):
        (tmp_path / ad).mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER",
                        (str(tmp_path / "projects"), str(tmp_path / "dj_sets")))
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    monkeypatch.setattr(TT, "DJ_KILIT_YOLU", str(tmp_path / "yok.lock"))
    return tmp_path


def _proje(kok, ad, st, kok_adi="projects", meta=None, ses=True):
    p = kok / kok_adi / ad
    p.mkdir(parents=True)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps(meta or {"title": ad, "theme": "pop"},
                                            ensure_ascii=False), encoding="utf-8")
    if ses:
        (p / "audio.wav").write_bytes(b"x")
    return str(p)


def _st(p):
    with io.open(os.path.join(p, "state.json"), encoding="utf-8") as f:
        return json.load(f)


def _yaz(p, st):
    with io.open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False))


def _kayit(p, tur):
    return next(k for k in _st(p)["turev_plani"] if k["tur"] == tur)


def _olay(tk, proje_ad, tur, liste="olaylar"):
    return next(o for o in tk[liste] if o["proje"] == proje_ad and o["tur"] == tur)


# --- 1. Plan -------------------------------------------------------------------

SARKI_TURLERI = {"studio_isleri", "topluluk_soz_anket", "carousel_soz_kartlari", "kulis",
                 "d7_karar", "derleme_adayligi", "tg_bs_hatirlatma", "tiktok_ikinci_kesit"}


def test_plan_deterministik_kuru_varsayilan_ve_sema(kok):
    p = _proje(kok, "Sabah Senin", SS)
    a = TT.plan_uret(p, simdi=T(2026, 9, 13, 4))
    b = TT.plan_uret(p, simdi=T(2026, 9, 13, 4))
    assert a["eklenecek"] == b["eklenecek"] and a["eklenecek"]
    assert not a["yazildi"] and "turev_plani" not in _st(p)       # varsayılan KURU
    assert {k["tur"] for k in a["eklenecek"]} == SARKI_TURLERI
    top = next(k for k in a["eklenecek"] if k["tur"] == "topluluk_soz_anket")
    assert top["id"] == "TRV-sabah-senin-topluluk_soz_anket"
    assert top["hedef_an"] == iso(2026, 9, 14, 12) and top["t0"] == iso(2026, 9, 13, 12)
    assert top["durum"] == "planlandi" and top["elle"] is True
    for alan in ("id", "tur", "platform", "hedef_an", "en_erken", "en_gec", "durum",
                 "dosyalar", "bagimliliklar", "iptal_kosulu", "tempo_sayilir", "yayin"):
        assert alan in top, alan
    assert top["tempo_sayilir"] is False
    assert max(k["en_gec"] for k in a["eklenecek"]) <= iso(2026, 10, 4, 22)


def test_plan_uygula_mevcut_kaydi_ezmez_yalniz_eksigi_ekler(kok):
    p = _proje(kok, "Sabah Senin", SS)
    r = TT.plan_uret(p, simdi=T(2026, 9, 13, 4), uygula=True)
    assert r["yazildi"]
    st = _st(p)
    n = len(st["turev_plani"])
    st["turev_plani"][0]["durum"] = "iptal"
    st["turev_plani"][0]["iptal_sebebi"] = "elle"
    silinen = next(k for k in st["turev_plani"] if k["tur"] == "kulis")
    st["turev_plani"].remove(silinen)
    _yaz(p, st)
    r2 = TT.plan_uret(p, simdi=T(2026, 9, 13, 5), uygula=True)
    assert [k["id"] for k in r2["eklenecek"]] == [silinen["id"]]
    st2 = _st(p)
    assert len(st2["turev_plani"]) == n
    assert st2["turev_plani"][0]["durum"] == "iptal"
    assert st2["turev_plani"][0]["iptal_sebebi"] == "elle"
    assert st2["youtube_video_id"] == "Ozn9" and st2["turev_plani_surumu"] == 1


def test_plan_dj_seti_kesit_var_carousel_yok_kulis_bayrakla(kok, monkeypatch):
    d = _proje(kok, "Just Relax", JR, kok_adi="dj_sets", meta={"title": "Just Relax", "theme": "dj"})
    turler = {k["tur"] for k in TT.plan_uret(d, simdi=T(2026, 9, 13, 5))["eklenecek"]}
    assert "dj_kesit" in turler and "carousel_soz_kartlari" not in turler
    assert "kulis" not in turler
    monkeypatch.setattr(config, "TUREV_DJ_KULIS_ONAYLI", True)
    turler = {k["tur"] for k in TT.plan_uret(d, simdi=T(2026, 9, 13, 5))["eklenecek"]}
    assert "kulis" in turler


def test_plan_dj_tarama_temiz_degilse_yok(kok, monkeypatch):
    monkeypatch.setattr(config, "DJ_ON_TARAMA", True)
    d = _proje(kok, "Yeni Set", dict(JR, dj_tarama_temiz=False), kok_adi="dj_sets")
    r = TT.plan_uret(d, simdi=T(2026, 9, 13, 5))
    assert r["eklenecek"] == [] and "tarama" in r["sebep"]


def test_plan_yirmi_bir_gun_penceresi(kok):
    p = _proje(kok, "Sabah Senin", SS)
    r = TT.plan_uret(p, simdi=T(2026, 10, 5, 12))
    assert r["eklenecek"] == [] and "pencere" in r["sebep"]
    turler = {k["tur"] for k in TT.plan_uret(p, simdi=T(2026, 9, 20, 13))["eklenecek"]}
    assert "studio_isleri" not in turler and "topluluk_soz_anket" not in turler
    assert "kulis" in turler


def test_sarki_youtube_kesiti_2026_10_09_kapisi(kok, monkeypatch):
    monkeypatch.setattr(config, "TUREV_SARKI_YOUTUBE_KESIT_AKTIF", True)

    def turler(ad, publish, simdi):
        p = _proje(kok, ad, dict(SS, youtube_publish_at=publish))
        return {k["tur"] for k in TT.plan_uret(p, simdi=simdi)["eklenecek"]}

    assert "sarki_youtube_kesit" not in turler("A", "2026-09-13T09:00:00Z", T(2026, 9, 13, 13))
    assert "sarki_youtube_kesit" not in turler("B", "2026-09-28T09:00:00Z", T(2026, 9, 28, 13))
    assert "sarki_youtube_kesit" in turler("C", "2026-10-05T09:00:00Z", T(2026, 10, 5, 13))
    monkeypatch.setattr(config, "TUREV_SARKI_YOUTUBE_KESIT_AKTIF", False)
    assert "sarki_youtube_kesit" not in turler("D", "2026-10-05T09:00:00Z", T(2026, 10, 5, 13))


# --- 2. Zamanlama kuralları -------------------------------------------------------

def test_yeni_sarki_yayininin_24_saatinde_turev_yok(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a])
    assert _olay(tk, "Sabah Senin", "topluluk_soz_anket")["an"] == iso(2026, 9, 14, 12)
    b = _proje(kok, "Yeni Sarki", {"youtube_video_id": "b",
                                    "youtube_publish_at": "2026-09-14T17:00:00Z"})  # 20:00 TR
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a, b])
    olay = _olay(tk, "Sabah Senin", "topluluk_soz_anket")
    assert olay["an"] == iso(2026, 9, 16, 12), olay
    assert any(y["proje"] == "Yeni Sarki" for y in tk["yeni_yayinlar"])


def test_bekleyen_sesli_proje_tahmini_yeni_yayin_sayilir(kok):
    a = _proje(kok, "Sabah Senin", SS)
    c = _proje(kok, "Siradaki", {})
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a, c])
    tah = [y for y in tk["yeni_yayinlar"] if y["proje"] == "Siradaki"]
    assert tah and tah[0]["tahmini"] is True
    assert tah[0]["an"] == iso(2026, 9, 15, 18)                  # 13 Eyl 12:00 + 52 sa -> 18:00


def test_ayni_sarkinin_iki_turevi_arasi_48_saat(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    st = _st(a)
    for k in st["turev_plani"]:
        if k["tur"] == "carousel_soz_kartlari":
            k["hedef_an"] = k["en_erken"] = iso(2026, 9, 15, 12)
    _yaz(a, st)
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a])
    assert _olay(tk, "Sabah Senin", "topluluk_soz_anket")["an"] == iso(2026, 9, 14, 12)
    assert _olay(tk, "Sabah Senin", "carousel_soz_kartlari")["an"] == iso(2026, 9, 16, 12)


def test_youtube_video_yukleyen_turev_haftada_bir_dj_kesit_sayaci_ortak(kok):
    x = _proje(kok, "Set X", JR, kok_adi="dj_sets")
    TT.plan_uret(x, simdi=T(2026, 9, 13, 5), uygula=True)
    y = _proje(kok, "Set Y", {"youtube_video_id": "y", "youtube_uploaded_at": "2026-09-01T10:00:00",
                              "youtube_clip_video_id": "c",
                              "youtube_clip_uploaded_at": "2026-09-15T10:00:00"},
               kok_adi="dj_sets")
    tk = TT.takvim(gun=14, simdi=T(2026, 9, 13, 5), klasorler=[x, y])
    olay = _olay(tk, "Set X", "dj_kesit")
    assert olay["an"] == iso(2026, 9, 22, 12), olay
    assert olay["youtube_video"] is True


def test_katalog_genelinde_kural_degismezleri(kok):
    """Zengin bir katalogda: günde en fazla 1 yüzey türevi, hepsi golden-hour
    başında/içinde, aynı proje ≥48 sa, yeni yayın ±24 sa bandı dışında."""
    ps = [_proje(kok, "Sabah Senin", SS),
          _proje(kok, "Eski", dict(SS, youtube_publish_at="2026-09-10T09:00:00Z")),
          _proje(kok, "Daha Eski", dict(SS, youtube_publish_at="2026-09-08T15:00:00Z"))]
    for p in ps:
        TT.plan_uret(p, simdi=T(2026, 9, 13, 4), uygula=True)
    ps.append(_proje(kok, "Set X", JR, kok_adi="dj_sets"))
    TT.plan_uret(ps[-1], simdi=T(2026, 9, 13, 4), uygula=True)
    tk = TT.takvim(gun=21, simdi=T(2026, 9, 13, 5), klasorler=ps)
    yuzey = [o for o in tk["olaylar"] if o["yuzey"] and o["etkin"] in ("planli", "kosullu")]
    assert len(yuzey) >= 6
    gunler = [o["an"][:10] for o in yuzey]
    assert len(gunler) == len(set(gunler)), gunler
    for o in tk["olaylar"]:
        saat = int(o["an"][11:13])
        assert any(b <= saat < s for b, s in config.GOLDEN_HOURS), o
    bantlar = [datetime.datetime.fromisoformat(y["an"]).timestamp() for y in tk["yeni_yayinlar"]]
    for o in yuzey:
        t = datetime.datetime.fromisoformat(o["an"]).timestamp()
        assert all(abs(t - b) >= 24 * 3600 for b in bantlar), o
        ayni = [datetime.datetime.fromisoformat(x["an"]).timestamp() for x in yuzey
                if x["proje"] == o["proje"] and x["id"] != o["id"]]
        assert all(abs(t - u) >= 48 * 3600 for u in ayni), o
    for o in tk["olaylar"]:
        assert o["an"] <= o["en_gec"], o


# --- 3. Engeller -----------------------------------------------------------------

@pytest.mark.parametrize("alan,deger", [("yayin_beklet", {"sebep": "yeniden render"}),
                                        ("kopya_notu", "aynı ses"),
                                        ("telif_araliklari", [[1, 2]]),
                                        ("telif_eser", "Bring Me To Life")])
def test_engel_tum_turevleri_durdurur(kok, alan, deger):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    st = _st(a)
    st[alan] = deger
    _yaz(a, st)
    tk = TT.takvim(gun=21, simdi=T(2026, 9, 13, 5), klasorler=[a])
    assert not [o for o in tk["olaylar"] if o["proje"] == "Sabah Senin"]
    dur = [o for o in tk["durdurulanlar"] if o["proje"] == "Sabah Senin"]
    assert dur and all(o["engel"] for o in dur)
    b = _proje(kok, "Engelli Yeni", dict(SS, **{alan: deger}))
    r = TT.plan_uret(b, simdi=T(2026, 9, 13, 4))
    assert r["eklenecek"] == [] and "engel" in r["sebep"]


def test_kesit_beklet_yalniz_dj_kesidini_durdurur(kok):
    x = _proje(kok, "Set X", dict(JR, kesit_beklet={"sebep": "kullanıcı"}), kok_adi="dj_sets")
    TT.plan_uret(x, simdi=T(2026, 9, 13, 5), uygula=True)
    tk = TT.takvim(gun=21, simdi=T(2026, 9, 13, 5), klasorler=[x])
    assert _olay(tk, "Set X", "dj_kesit", "durdurulanlar")["engel"]
    assert any(o["proje"] == "Set X" and o["tur"] != "dj_kesit" for o in tk["olaylar"])


def test_bozuk_durum_fail_closed_atlanir(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    st = _st(a)
    st["turev_plani"][1]["durum"] = "yayinda"
    _yaz(a, st)
    tk = TT.takvim(gun=21, simdi=T(2026, 9, 13, 5), klasorler=[a])
    ids = {o["id"] for o in tk["olaylar"] + tk["durdurulanlar"] + tk["dusenler"]}
    assert st["turev_plani"][1]["id"] not in ids
    assert tk["atlanan_kayitlar"] == 1


# --- 4. Hatırlatma -----------------------------------------------------------------

def test_hatirlatma_bayragi_varsayilan_kapali():
    assert config.TUREV_HATIRLATMA_AKTIF is False


def test_bayrak_kapaliyken_hicbir_sey_gonderilmez_yazilmaz(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    once = open(os.path.join(a, "state.json"), "rb").read()
    satirlar = []
    patla = lambda *x: (_ for _ in ()).throw(AssertionError("gönderdi"))
    r = TT.hatirlatma_sirasi(satirlar.append, simdi=T(2026, 9, 14, 12, 30),
                             klasorler=[a], gonder=patla)
    TT.sirasi(satirlar.append, simdi=T(2026, 9, 14, 12, 30), klasorler=[a], gonder=patla)
    assert r["gonderilen"] is None
    assert open(os.path.join(a, "state.json"), "rb").read() == once
    assert any("kapalı" in s for s in satirlar)


@pytest.fixture
def acik(monkeypatch):
    monkeypatch.setattr(config, "TUREV_HATIRLATMA_AKTIF", True)
    giden = []

    def gonder(metin):
        giden.append(metin)
        return True
    return giden, gonder


def test_hatirlatma_gunde_bir_ve_onceki_yanitlanmadan_yenisi_yok(kok, acik):
    giden, gonder = acik
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    log = lambda *x: None

    r1 = TT.hatirlatma_sirasi(log, simdi=T(2026, 9, 14, 12, 30), klasorler=[a], gonder=gonder)
    assert r1["gonderilen"] and len(giden) == 1
    assert "Sabah Senin" in giden[0] and "Suno" not in giden[0]
    bekleyen = [k for k in _st(a)["turev_plani"] if k["durum"] == "onay_bekliyor"]
    assert len(bekleyen) == 1 and bekleyen[0]["hatirlatildi_at"]

    r2 = TT.hatirlatma_sirasi(log, simdi=T(2026, 9, 14, 12, 40), klasorler=[a], gonder=gonder)
    assert r2["gonderilen"] is None and "yanıt" in r2["sebep"] and len(giden) == 1

    st = _st(a)
    for k in st["turev_plani"]:
        if k["durum"] == "onay_bekliyor":
            k["durum"] = "yayinlandi"
            k["yayin"] = {"an": iso(2026, 9, 14, 12, 45), "kimlik": None, "kaynak": "elle:test"}
    _yaz(a, st)
    r3 = TT.hatirlatma_sirasi(log, simdi=T(2026, 9, 14, 13, 0), klasorler=[a], gonder=gonder)
    assert r3["gonderilen"] is None and "gün" in r3["sebep"] and len(giden) == 1


def test_hatirlatma_golden_hour_disinda_gitmez(kok, acik):
    giden, gonder = acik
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    r = TT.hatirlatma_sirasi(lambda *x: None, simdi=T(2026, 9, 14, 15, 0), klasorler=[a],
                             gonder=gonder)
    assert r["gonderilen"] is None and giden == []


def test_hatirlatma_uyumluluk_hatasinda_gitmez(kok, acik, monkeypatch):
    giden, gonder = acik
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": (["md5 kopya"], []))
    r = TT.hatirlatma_sirasi(lambda *x: None, simdi=T(2026, 9, 14, 12, 30), klasorler=[a],
                             gonder=gonder)
    assert r["gonderilen"] is None and giden == []
    assert not [k for k in _st(a)["turev_plani"] if k["durum"] != "planlandi"]


def test_hatirlatma_engelli_projeye_gitmez(kok, acik):
    giden, gonder = acik
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    st = _st(a)
    st["yayin_beklet"] = {"sebep": "x"}
    _yaz(a, st)
    TT.hatirlatma_sirasi(lambda *x: None, simdi=T(2026, 9, 14, 12, 30), klasorler=[a],
                         gonder=gonder)
    assert giden == []


# --- 5. Elle yayın eşleşmesi (elle_islem kancası) ------------------------------------

@pytest.fixture
def defter(tmp_path, monkeypatch):
    import elle_islem as EI
    yol = tmp_path / "defter" / "elle_islemler.jsonl"
    monkeypatch.setenv(EI.ORTAM_DEGISKENI, str(yol))
    return EI


def test_elle_yayin_tek_aday_yayinlandi_olur(kok, defter):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    s = defter.ekle("instagram", "yayinladi", "carousel telefondan", proje="Sabah Senin",
                    zaman="2026-09-17T19:10", kaynak="claude", proje_klasorleri=[a],
                    simdi=T(2026, 9, 17, 19, 20))
    k = _kayit(a, "carousel_soz_kartlari")
    assert k["durum"] == "yayinlandi"
    assert k["yayin"]["kaynak"] == "elle:" + s["kayit"]["id"]
    assert k["id"] in (s["kayit"]["state_etkisi"] or "")


def test_elle_yayin_coklu_aday_isaretlenmez_raporlanir(kok, defter):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    s = defter.ekle("youtube", "yayinladi", "Studio'dan", proje="Sabah Senin",
                    zaman="2026-09-13T20:00", kaynak="claude", proje_klasorleri=[a],
                    simdi=T(2026, 9, 13, 20, 5))
    assert all(k["durum"] == "planlandi" for k in _st(a)["turev_plani"])
    assert "aday" in s["mesaj"] and s["durum"] == "eklendi"


def test_elle_yayin_36_saat_disinda_eslesmez(kok, defter):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    defter.ekle("instagram", "yayinladi", "eski", proje="Sabah Senin",
                zaman="2026-09-13T20:00", kaynak="claude", proje_klasorleri=[a],
                simdi=T(2026, 9, 13, 20, 5))
    assert _kayit(a, "carousel_soz_kartlari")["durum"] == "planlandi"


# --- 6. Bağlantılar ----------------------------------------------------------------------

def _agac(dosya):
    with io.open(os.path.join(_REPO, dosya), encoding="utf-8") as f:
        return ast.parse(f.read())


def test_auto_process_finally_sirasi_ve_is_fully_done_dokunulmadi():
    agac = _agac("auto_process.py")
    main = next(d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef) and d.name == "main")
    deneme = next(d for d in ast.walk(main) if isinstance(d, ast.Try) and d.finalbody)
    satir = {}
    for d in ast.walk(ast.Module(body=deneme.finalbody, type_ignores=[])):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            satir.setdefault(d.func.id, d.lineno)
    assert "_turev_takvimi" in satir, sorted(satir)
    assert satir["_tiktok_kit_sirasi"] < satir["_turev_takvimi"] < satir["_release_lock"]
    fonks = {d.name: d for d in ast.walk(agac) if isinstance(d, ast.FunctionDef)}
    sarmal = fonks["_turev_takvimi"]
    assert any(isinstance(x, ast.Try) for x in sarmal.body)
    assert "turev_takvimi" in ast.unparse(sarmal)
    assert "turev" not in ast.unparse(fonks["_is_fully_done"])
    assert "turev" not in ast.unparse(fonks["process_project"])
    for d in agac.body:
        if isinstance(d, ast.Assign) and any(
                isinstance(h, ast.Name) and ("TIMESTAMP_KEYS" in h.id or h.id.startswith("YENI_YAYIN"))
                for h in d.targets):
            assert "turev" not in ast.unparse(d.value)


def test_patlayan_turev_kancasi_yutuluyor(monkeypatch):
    import auto_process
    satirlar = []
    monkeypatch.setattr(TT, "sirasi", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(auto_process, "log", satirlar.append)
    auto_process._turev_takvimi()
    assert any("Türev takvimi HATA" in s for s in satirlar), satirlar


def test_gunluk_rapor_turev_satiri_yalniz_doluyken(kok, tmp_path):
    import weekly_report as wr
    a = _proje(kok, "Sabah Senin", SS)
    durum = str(tmp_path / "saglik_durum.json")
    r = wr.gunluk_izlenme_raporu(lambda *x: None, zorla=True, durum_dosyasi=durum,
                                 gonder=False, simdi=T(2026, 9, 14, 10), klasorler=[a])
    assert "türev" not in r["metin"].lower()
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    r = wr.gunluk_izlenme_raporu(lambda *x: None, zorla=True, durum_dosyasi=durum,
                                 gonder=False, simdi=T(2026, 9, 14, 10), klasorler=[a])
    assert "Bugün/yarın türev" in r["metin"]
    assert "Sabah Senin" in r["metin"].split("Bugün/yarın türev")[1]


def test_takvim_json_bicimi_ve_sirada_ne(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a])
    json.dumps(tk, ensure_ascii=False)
    for alan in ("surum", "uretildi_at", "aralik", "olaylar", "durdurulanlar", "dusenler",
                 "yeni_yayinlar", "kurallar", "atlanan_kayitlar"):
        assert alan in tk, alan
    o = tk["olaylar"][0]
    for alan in ("id", "proje", "kok", "tur", "tur_adi", "platform", "yuzey", "elle",
                 "youtube_video", "kosul", "risk", "durum", "etkin", "an", "hedef_an",
                 "en_gec", "engel"):
        assert alan in o, alan
    assert tk["olaylar"] == sorted(tk["olaylar"], key=lambda x: (x["an"], x["id"]))
    s = TT.sirada_ne(simdi=T(2026, 9, 13, 5), klasorler=[a])
    assert s["id"] == tk["olaylar"][0]["id"]


def test_sirasi_yalniz_yeni_t0_planlar_dj_kilidinde_seti_atlar_tek_ozet(kok):
    a = _proje(kok, "Sabah Senin", SS)
    eski = _proje(kok, "Eski", dict(SS, youtube_publish_at="2026-09-01T09:00:00Z"))
    x = _proje(kok, "Set X", dict(JR, youtube_uploaded_at="2026-09-13T10:00:00"), kok_adi="dj_sets")
    kilit = kok / "dj.lock"
    kilit.write_text("1")
    os.utime(str(kilit), (T(2026, 9, 13, 12, 30), T(2026, 9, 13, 12, 30)))   # 30 dk önce tazelendi
    TT.DJ_KILIT_YOLU = str(kilit)
    satirlar = []
    TT.sirasi(satirlar.append, simdi=T(2026, 9, 13, 13), klasorler=[a, eski, x])
    assert "turev_plani" in _st(a)
    assert "turev_plani" not in _st(eski)
    assert "turev_plani" not in _st(x)
    assert len([s for s in satirlar if s.startswith("  Türev takvimi:")]) == 1, satirlar


def test_iptal(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    kid = _kayit(a, "kulis")["id"]
    r = TT.iptal(kid, sebep="kullanıcı istemedi", klasorler=[a])
    assert r["durum"] == "iptal" and _kayit(a, "kulis")["iptal_sebebi"] == "kullanıcı istemedi"
    with pytest.raises(TT.TurevHatasi):
        TT.iptal("TRV-yok", klasorler=[a])


def test_gercek_koke_testte_yazim_reddedilir(kok, monkeypatch):
    a = _proje(kok, "Sabah Senin", SS)
    monkeypatch.setattr(TT, "GERCEK_KOKLER", (str(kok / "projects"),))
    once = open(os.path.join(a, "state.json"), "rb").read()
    with pytest.raises(TT.TurevHatasi):
        TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    assert open(os.path.join(a, "state.json"), "rb").read() == once


def test_gercek_kokler_uyumluluk_kokleriyle_ayni():
    beklenen = tuple(os.path.join(os.path.dirname(os.path.abspath(uyumluluk.__file__)), k)
                     for k in uyumluluk.KOK_ADLARI)
    assert tuple(TT.GERCEK_KOKLER) == beklenen


def test_cli_cp1254_kuru_plan_ve_takvim_json(kok):
    a = _proje(kok, "Küllerimden Ğeç", SS)
    once = open(os.path.join(a, "state.json"), "rb").read()
    env = dict(os.environ, PYTHONIOENCODING="cp1254")
    betik = os.path.join(_REPO, "turev_takvimi.py")
    p = subprocess.run([sys.executable, betik, "plan", "--proje", a,
                        "--simdi", "2026-09-13T04:00:00+03:00"],
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    cikti = p.stdout.decode("utf-8")
    assert "KURU" in cikti and "Küllerimden Ğeç" in cikti
    assert open(os.path.join(a, "state.json"), "rb").read() == once
    p = subprocess.run([sys.executable, betik, "takvim", "--gun", "7", "--json",
                        "--kok", str(kok / "projects"), "--simdi", "2026-09-13T05:00:00+03:00"],
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    veri = json.loads(p.stdout.decode("utf-8"))
    assert veri["surum"] == 1 and isinstance(veri["olaylar"], list)
