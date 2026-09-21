# -*- coding: utf-8 -*-
"""TikTok WEB PLANLAMA (`upload/tiktok_web.py`, `config.TIKTOK_AKIS`, 2026-09-13).

Kullanıcı kararı: TikTok'ta her şey TikTok Studio web + "Planla" ile yapılır. Bu testler
kod tarafını kilitler: web modunda API taslağı yüklenmez, `_is_fully_done` TikTok yüzünden
proje bekletmez, kit web planlı projeye gitmez, planlama kuralları, işaretleme reddi, geçen
an otomatik "yayınlandı" YAPMAZ, günde 1 hatırlatma, elle/Telegram onayı eşlemesi,
metin kitle aynı, cp1254 CLI.

Hiçbir test ağa çıkmaz (notify göndericileri patlar), gerçek `projects/`e ve gerçek
deftere yazmaz (KOKLER + ELLE_ISLEMLER_DEFTERI + DURUM_DOSYASI tmp_path).
"""

import ast
import io
import json
import os
import subprocess
import sys
from datetime import datetime

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import auto_process as ap
import config
import elle_islem as EI
import notify
import saglik_kontrol as SK
import struct
import tiktok_publish_plan as TPP
import tiktok_upload
import tiktok_web as TW
import tiktok_yayin_dogrulama as DOG
import tiktok_yayin_kiti as K
import tiktok_yayin_onayi as ONAY
import turev_takvimi as TT
import uyumluluk
import weekly_report as WR

SAAT = 3600
GUN = 24 * SAAT


def _an(g, s, dk=0, ay=9):
    return datetime(2026, ay, g, s, dk, tzinfo=config.TR_TZ).timestamp()


# 2026-09-14 10:00 TR — golden-hour DIŞI.
T = _an(14, 10)


def _png(yol, w=900, h=1600):
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)


def _proje(kok, ad, durum=None, simdi=T, youtube=True):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    d = {}
    if youtube:
        d.update({"youtube_video_id": "yt-" + ad, "youtube_shorts_video_id": "s-" + ad,
                  "youtube_privacy": "public",
                  "youtube_uploaded_at": K._damga(simdi - 300 * SAAT),
                  "instagram_media_id": "ig-" + ad})
    d.update(durum or {})
    (p / "state.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": "pop"}, ensure_ascii=False),
                                 encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + ad).encode("utf-8"))
    (p / "output").mkdir(exist_ok=True)
    (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    _png(str(p / "cover_vertical.png"))
    return str(p)


def _st(p):
    with open(os.path.join(p, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _yaz(p, **alan):
    d = _st(p)
    d.update(alan)
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def _web(p, an_ts, durum="planlandi"):
    _yaz(p, tiktok_web={"durum": durum, "planlanan_an": TW._iso(an_ts),
                        "yuklendi_at": TW._iso(an_ts - 30 * SAAT), "studio_id": None,
                        "aciklama_sha1": "x", "kaynak": "claude"})


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(config, "TIKTOK_AKIS", "web_planla", raising=False)
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", False)
    monkeypatch.setattr(config, "TIKTOK_WEB_KONTROL_HATIRLATMA", True, raising=False)
    monkeypatch.setattr(config, "TIKTOK_WEB_PLANLA_MAX_GUN", 10, raising=False)
    monkeypatch.setattr(config, "TIKTOK_WEB_PLANLA_MIN_DAKIKA", 60, raising=False)
    monkeypatch.setattr(K, "_KOSUDA_GONDERILDI", False)
    monkeypatch.setattr(TW, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    defter = tmp_path / "elle_islemler.jsonl"
    monkeypatch.setenv(EI.ORTAM_DEGISKENI, str(defter))

    def _yasak(*a, **kw):
        raise AssertionError("test gerçek notify göndericisine gitmemeli")

    for ad in ("send", "send_photo", "send_text"):
        monkeypatch.setattr(notify, ad, _yasak, raising=False)
    return k


def _defter(kok):
    yol = kok.parent / "elle_islemler.jsonl"
    if not yol.exists():
        return []
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]


# --------------------------------------------------------------------------
# 1. Mod: API yüklemesi yok, _is_fully_done / pencere paydası
# --------------------------------------------------------------------------

def test_config_varsayilan_web_planla():
    import importlib
    kaynak = open(os.path.join(_REPO, "config.py"), encoding="utf-8").read()
    agac = ast.parse(kaynak)
    degerler = {h.targets[0].id: h.value.value for h in agac.body
                if isinstance(h, ast.Assign) and isinstance(h.targets[0], ast.Name)
                and isinstance(h.value, ast.Constant)}
    assert degerler.get("TIKTOK_AKIS") == "web_planla"
    assert degerler.get("TIKTOK_WEB_PLANLA_MAX_GUN") == 10
    assert degerler.get("TIKTOK_WEB_KONTROL_HATIRLATMA") is True
    assert importlib.import_module("config").tiktok_web_modu() in (True, False)


def test_web_modunda_api_yuklemesi_cagrilmiyor(kok, tmp_path, monkeypatch):
    p = _proje(kok, "Yeni")
    upload_dir = tmp_path / "upload"
    upload_dir.mkdir()
    (upload_dir / "tiktok_token.json").write_text("{}", encoding="utf-8")
    cagri, satirlar = [], []
    monkeypatch.setattr(tiktok_upload, "upload_video", lambda d: cagri.append(d) or "pid")
    monkeypatch.setattr(ap, "log", lambda m: satirlar.append(str(m)))

    ap._tiktok_adimi(p, _st(p), str(upload_dir))
    assert cagri == []
    assert any("web" in s.lower() for s in satirlar)

    monkeypatch.setattr(config, "TIKTOK_AKIS", "api_taslak")
    ap._tiktok_adimi(p, _st(p), str(upload_dir))
    assert cagri == [p], "api_taslak modunda eski yol aynen çalışmalı"


def test_process_project_tiktok_adimini_kullaniyor():
    agac = ast.parse(open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read())
    fn = next(d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == "process_project")
    adlar = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)}
    assert "_tiktok_adimi" in adlar
    assert "tt_upload" not in adlar, "API yüklemesi yalnız _tiktok_adimi içinde (kapının arkasında)"


def test_dj_hatti_da_web_modunda_api_yuklemiyor():
    kaynak = open(os.path.join(_REPO, "dj_famous_process.py"), encoding="utf-8").read()
    bas = kaynak.index('if "tiktok_publish_id" in state:')
    govde = kaynak[bas:kaynak.index("tt_upload(project_dir)", bas)]
    assert "tiktok_web_modu()" in govde


def test_is_fully_done_web_modunda_tiktok_sart_degil(kok, monkeypatch):
    uc = _proje(kok, "UcAnahtar")                       # YouTube+Shorts+IG, TikTok yok
    hic = _proje(kok, "Hic", youtube=False)
    tam = _proje(kok, "Tam", {"tiktok_publish_id": "pid"})
    ready = [uc, hic, tam]

    monkeypatch.setattr(config, "TIKTOK_AKIS", "api_taslak")
    assert [p for p in ready if not ap._is_fully_done(p)] == [uc, hic]

    monkeypatch.setattr(config, "TIKTOK_AKIS", "web_planla")
    pending = [p for p in ready if not ap._is_fully_done(p)]
    assert pending == [hic], "web modunda TikTok yüzünden pending kalmamalı"
    # Pencere paydası: api'de 2 -> 24/2 = 12 sa; web'de 1 -> 24 sa (TikTok'u eksik proje
    # paydayı artık küçültmüyor, yani günlük fren gevşemiyor).
    assert ap.DAILY_WINDOW_SECONDS / len(pending) == 24 * SAAT


def test_ayirici_web_modunda_tiktok_eksigini_saymaz(kok, monkeypatch):
    p = _proje(kok, "IG", {"instagram_creation_id": "c1",
                           "instagram_container_created_at": K._damga(ap.time.time() - 600)})
    d = _st(p)
    d.pop("instagram_media_id")
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump(d, f)
    monkeypatch.setattr(config, "TIKTOK_AKIS", "web_planla")
    secilebilir, drain = ap._yalniz_drain_bekleyenleri_ayir([p])
    assert drain == [p] and secilebilir == []


def test_saglik_anahtarlari_mod_ile_ayni(kok, monkeypatch):
    for mod in ("api_taslak", "web_planla"):
        monkeypatch.setattr(config, "TIKTOK_AKIS", mod)
        anahtarlar = SK.ana_platform_anahtarlari()
        d = kok / ("m-" + mod)
        d.mkdir()
        (d / "state.json").write_text(json.dumps({k: "x" for k in anahtarlar}), encoding="utf-8")
        assert ap._is_fully_done(str(d)) is True
        assert ("tiktok_publish_id" in anahtarlar) is (mod == "api_taslak")


# --------------------------------------------------------------------------
# 2. Kit / hatırlatma / doğrulama kapıları
# --------------------------------------------------------------------------

def _taslak(kok, ad, simdi=T, **ek):
    d = {"tiktok_publish_id": "v~" + ad, "tiktok_uploaded_at": K._damga(simdi - 100 * SAAT),
         "tiktok_publish_status": "SEND_TO_USER_INBOX",
         "tiktok_status_checked_at": K._damga(simdi - 2 * SAAT)}
    d.update(ek)
    return _proje(kok, ad, d, simdi)


def test_kit_web_planli_projeye_gitmiyor(kok):
    p = _taslak(kok, "Taslak")
    assert K.siradaki_kit_adayi([p], T)["aday"] == p
    _web(p, T + 30 * SAAT)
    assert K.siradaki_kit_adayi([p], T)["aday"] is None


def test_onay_bekleyen_kit_web_planlandiysa_hatirlatma_ve_blok_yok(kok):
    p = _taslak(kok, "Bekleyen")
    kod = tiktok_upload.yayin_kodu(_st(p)["tiktok_publish_id"])
    _yaz(p, tiktok_kit_gonderildi_at=K._damga(T - 50 * SAAT), tiktok_kit_kodu=kod)
    assert K._onay_bekliyor(_st(p)) is True
    _web(p, T + 40 * SAAT)
    assert K._onay_bekliyor(_st(p)) is False


def test_kit_temposu_web_planini_sayiyor(kok):
    p = _taslak(kok, "Kit")
    w = _proje(kok, "Web")
    _web(w, _an(15, 12))
    durumlar = [(x, _st(x)) for x in (p, w)]
    assert K._tempo_engeli(durumlar, _an(14, 19)) is not None
    assert K._tempo_engeli(durumlar, _an(17, 12)) is None


def test_duz_hatirlatma_web_planli_projeye_gitmiyor(kok, monkeypatch):
    p = _taslak(kok, "Duz")
    _web(p, T + 30 * SAAT)
    monkeypatch.setattr(notify, "is_configured", lambda: True)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a: None)
    assert tiktok_upload.notify_pending_publish(p) is False


def test_dogrulama_web_projesini_sorgulamiyor(kok):
    p = _taslak(kok, "Sorgu")
    assert [x[0] for x in DOG.adaylari_bul(T)] == [p]
    _web(p, T + 30 * SAAT)
    assert DOG.adaylari_bul(T) == []


# --------------------------------------------------------------------------
# 3. Aday sınıflandırması
# --------------------------------------------------------------------------

def test_aday_siniflari(kok):
    uygun = _proje(kok, "Uygun")
    taze = _taslak(kok, "TazeTaslak")
    okunmamis = _proje(kok, "Okunmamis", {"tiktok_publish_id": "v~o"})
    tamam = _proje(kok, "Tamam", {"tiktok_publish_id": "v~t",
                                  "tiktok_publish_status": "PUBLISH_COMPLETE"})
    bekle = _proje(kok, "Bekle", {"yayin_beklet": {"sebep": "test"}})
    unlisted = _proje(kok, "Liste", {"youtube_privacy": "unlisted"})
    yayinli = _proje(kok, "Yayinli", {"tiktok_published_at": "2026-09-01T12:00:00"})

    sonuc = TW.plan_oner(gun=10, simdi=T)
    oneri = {o["proje"] for o in sonuc["oneriler"]}
    kontrol = {k["proje"] for k in sonuc["icerik_kontrolu_gerekli"]}
    degil = {k["proje"]: k["sebep"] for k in sonuc["aday_degil"]}
    assert oneri == {"Uygun", "TazeTaslak"}
    assert kontrol == {"Okunmamis"}
    assert "PUBLISH_COMPLETE" in degil["Tamam"]
    assert degil["Bekle"].startswith("hazir=False")
    assert "public değil" in degil["Liste"]
    assert "yayınlandı" in degil["Yayinli"]
    assert uygun and taze and okunmamis and tamam and bekle and unlisted and yayinli


# --------------------------------------------------------------------------
# 4. Planlama kuralları
# --------------------------------------------------------------------------

def _bag(simdi=T, **ek):
    b = TW._baglam(simdi)
    b.update(ek)
    return b


def test_kural_golden_hour_ve_max_gun(kok):
    p = _proje(kok, "A")
    st = _st(p)
    assert any("golden-hour" in i for i in TW._kural_ihlalleri(_an(15, 15), p, st, _bag(), T))
    assert TW._kural_ihlalleri(_an(15, 18), p, st, _bag(), T) == []
    assert any("sınırı" in i for i in TW._kural_ihlalleri(_an(24, 18, ay=9) + 2 * GUN, p, st,
                                                           _bag(), T))
    assert TW.plan_oner(gun=30, simdi=T)["gun"] == 10


def test_kural_36_saat(kok):
    p = _proje(kok, "A")
    w = _proje(kok, "W")
    _web(w, _an(15, 12))
    st = _st(p)
    assert any("36" in i for i in TW._kural_ihlalleri(_an(16, 21, 45), p, st, _bag(), T))
    assert TW._kural_ihlalleri(_an(17, 12), p, st, _bag(), T) == []


def test_kural_gunluk_ve_haftalik_tavan(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_ARALIK_SAAT", 0)
    p = _proje(kok, "A")
    for i, g in enumerate((15, 16, 17, 18)):
        _web(_proje(kok, "W%d" % i), _an(g, 12))
    st = _st(p)
    assert any("günlük" in i for i in TW._kural_ihlalleri(_an(16, 19), p, st, _bag(), T))
    assert any("haftalık" in i for i in TW._kural_ihlalleri(_an(19, 19), p, st, _bag(), T))
    assert not any("haftalık" in i for i in TW._kural_ihlalleri(_an(22, 19), p, st, _bag(), T))


def test_kural_youtube_public_oncesi_yok(kok):
    p = _proje(kok, "A", {"youtube_publish_at": "2026-09-16T15:00:00Z"})   # 18:00 TR
    st = _st(p)
    ihlal = TW._kural_ihlalleri(_an(16, 12), p, st, _bag(), T)
    assert any("public anından" in i for i in ihlal)


def test_kural_yeni_yayin_24_saat(kok):
    p = _proje(kok, "A")
    _proje(kok, "YeniSarki", {"youtube_publish_at": "2026-09-16T09:00:00Z"})  # 12:00 TR
    st = _st(p)
    assert any("yeni yayın" in i for i in TW._kural_ihlalleri(_an(16, 19), p, st, _bag(), T))
    assert not any("yeni yayın" in i for i in TW._kural_ihlalleri(_an(17, 12), p, st, _bag(), T))


def test_kural_turev_cakismasi(kok, monkeypatch):
    p = _proje(kok, "A")
    olay = {"proje": "B", "tur": "kulis", "platform": "youtube", "yuzey": True,
            "etkin": "planli", "an": TW._iso(_an(15, 12))}
    monkeypatch.setattr(TT, "takvim", lambda **kw: {"olaylar": [olay]})
    st = _st(p)
    assert any("türev" in i for i in TW._kural_ihlalleri(_an(15, 13), p, st, _bag(), T))
    assert TW._kural_ihlalleri(_an(15, 18), p, st, _bag(), T) == []


def test_plan_oner_deterministik_ve_kurallara_uyuyor(kok):
    for ad in ("C", "A", "B"):
        _proje(kok, ad)
    s1 = TW.plan_oner(gun=10, simdi=T)
    s2 = TW.plan_oner(gun=10, simdi=T)
    assert [(o["proje"], o["onerilen_an"]) for o in s1["oneriler"]] == \
           [(o["proje"], o["onerilen_an"]) for o in s2["oneriler"]]
    anlar = [TW._ts(o["onerilen_an"]) for o in s1["oneriler"]]
    assert len(anlar) == 3
    assert all(TW._golden_icinde(a) for a in anlar)
    assert all(b - a >= 36 * SAAT for a, b in zip(anlar, anlar[1:]))
    assert anlar[0] == _an(14, 12), "ilk uygun an: bugünkü öğle penceresi"
    o = s1["oneriler"][0]
    for alan in ("video", "kapak", "aciklama", "aciklama_sha1", "ayarlar", "onerilen_an"):
        assert o[alan]
    assert {a["alan"] for a in o["ayarlar"]} >= {
        "Kimler görebilir", "Yorum", "İçeriği yeniden kullanma", "AI ile oluşturulmuş içerik",
        "Gönderi içeriğini açıklayın", "HD yükleme", "Planla", "Kapak yükleyin"}


def test_kit_rezervi_web_onerisini_iter(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", True)
    _taslak(kok, "KitSirasi")
    _proje(kok, "WebAday")
    sonuc = TW.plan_oner(gun=10, simdi=T)
    assert sonuc["kit_rezervi"]["an"] == TW._iso(_an(14, 12))
    assert [o["proje"] for o in sonuc["oneriler"]] == ["WebAday"]
    assert TW._ts(sonuc["oneriler"][0]["onerilen_an"]) >= _an(14, 12) + 36 * SAAT
    assert "KitSirasi" in {k["proje"] for k in sonuc["icerik_kontrolu_gerekli"]}


# --------------------------------------------------------------------------
# 5. İşaretleme
# --------------------------------------------------------------------------

def test_isaretle_kural_disi_ani_reddediyor_ve_yazmiyor(kok):
    p = _proje(kok, "A")
    once = _st(p)
    with pytest.raises(TW.TiktokWebHatasi) as e:
        TW.planlandi_isaretle(p, TW._iso(_an(15, 15)), simdi=T)
    assert "golden-hour" in str(e.value)
    assert _st(p) == once and _defter(kok) == []


def test_isaretle_sha1_uyusmazligini_reddediyor(kok):
    p = _proje(kok, "A")
    with pytest.raises(TW.TiktokWebHatasi):
        TW.planlandi_isaretle(p, TW._iso(_an(15, 18)), simdi=T, sha1_beklenen="yanlis")
    assert "tiktok_web" not in _st(p)


def test_isaretle_yaziyor_ve_deftere_ekliyor(kok):
    p = _proje(kok, "A")
    pk = TW.paket(p, simdi=T)
    sonuc = TW.planlandi_isaretle(p, pk["onerilen_an"], studio_id="7777", simdi=T,
                                  sha1_beklenen=pk["aciklama_sha1"])
    w = _st(p)["tiktok_web"]
    assert w["durum"] == "planlandi" and w["planlanan_an"] == pk["onerilen_an"]
    assert w["aciklama_sha1"] == pk["aciklama_sha1"] and w["studio_id"] == "7777"
    satirlar = _defter(kok)
    assert len(satirlar) == 1
    assert satirlar[0]["kaynak"] == "claude" and satirlar[0]["islem"] == "planladi"
    assert satirlar[0]["platform"] == "tiktok" and satirlar[0]["proje"] == "A"
    assert sonuc["durum"] == "planlandi"
    with pytest.raises(TW.TiktokWebHatasi):
        TW.planlandi_isaretle(p, pk["onerilen_an"], simdi=T)       # ikinci kez yok


def test_isaretle_gercek_koke_testte_yazmiyor(kok):
    gercek = os.path.join(TW.GERCEK_KOKLER[0], "Olmayan Test Projesi")
    with pytest.raises(TW.TiktokWebHatasi) as e:
        TW.planlandi_isaretle(gercek, TW._iso(_an(15, 18)), simdi=T)
    assert "GERÇEK" in str(e.value)


# --------------------------------------------------------------------------
# 6. Geçen an, hatırlatma, onay eşlemeleri
# --------------------------------------------------------------------------

def test_planlanan_an_gecince_otomatik_yayinlandi_yok(kok):
    p = _proje(kok, "A")
    _web(p, _an(14, 12))
    once = _st(p)
    sonuc = TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(14, 13),
                                  klasorler=[p], gonder=lambda *a: True)
    assert _st(p)["tiktok_web"]["durum"] == "planlandi"
    assert "tiktok_published_at" not in _st(p)
    assert {k: v for k, v in _st(p).items()} == once
    d = TW.durum(simdi=_an(14, 13), klasorler=[p])
    assert d["dogrulanmadi"] == ["A"]
    assert sonuc["gonderilen"] == "A"


def test_hatirlatma_gunde_bir_golden_ve_bayrak(kok, monkeypatch):
    p = _proje(kok, "A")
    _web(p, _an(14, 9))
    giden = []
    gonder = lambda b, m: giden.append((b, m)) or True          # noqa: E731
    TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(14, 10), klasorler=[p], gonder=gonder)
    assert giden == [], "golden-hour dışında gitmez"
    TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(14, 12), klasorler=[p], gonder=gonder)
    TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(14, 19), klasorler=[p], gonder=gonder)
    assert len(giden) == 1 and "TikTok'ta çıktı mı? A" in giden[0][1]
    assert "yayınladım A" in giden[0][1]
    TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(15, 12), klasorler=[p], gonder=gonder)
    assert len(giden) == 2, "ertesi gün yeniden"
    monkeypatch.setattr(config, "TIKTOK_WEB_KONTROL_HATIRLATMA", False)
    TW.kontrol_hatirlatma(log=lambda m: None, simdi=_an(16, 12), klasorler=[p], gonder=gonder)
    assert len(giden) == 2


def test_elle_islem_yayinladi_web_kaydini_isaretliyor(kok):
    p = _proje(kok, "A")
    an = _an(14, 12)
    _web(p, an)
    sonuc = EI.ekle("tiktok", "yayinladi", "TikTok'ta göründü", proje="A",
                    zaman=TW._iso(an + SAAT), kaynak="claude", simdi=an + 2 * SAAT)
    st = _st(p)
    assert st["tiktok_web"]["durum"] == "yayinlandi"
    assert st["tiktok_published_at"] == "2026-09-14T12:00:00"
    assert st["tiktok_published_kaynak"] == "TikTok Studio web (Planla 2026-09-14T12:00:00+03:00)"
    assert "tiktok_web" in (sonuc["kayit"]["state_etkisi"] or "")


def test_elle_islem_yayinladi_an_gelmeden_reddediyor(kok):
    p = _proje(kok, "A")
    _web(p, _an(16, 12))
    with pytest.raises(EI.ElleIslemHatasi):
        EI.ekle("tiktok", "yayinladi", "erken", proje="A", zaman=TW._iso(_an(14, 12)),
                kaynak="claude", simdi=_an(14, 13))
    assert _st(p)["tiktok_web"]["durum"] == "planlandi"
    assert _defter(kok) == []


def test_telegram_onayi_web_kaydini_isaretliyor(kok):
    p = _proje(kok, "Sarki")
    _web(p, _an(14, 12))
    kod, metin = ONAY.onayla("Sarki", zaman="2026-09-14T13:00:00")
    assert kod == 0, metin
    assert _st(p)["tiktok_web"]["durum"] == "yayinlandi"
    assert _st(p)["tiktok_published_at"] == "2026-09-14T12:00:00"


# --------------------------------------------------------------------------
# 7. Metin, görünürlük, CLI
# --------------------------------------------------------------------------

def test_paket_metni_build_kit_ile_ayni_suno_yok(kok):
    p = _proje(kok, "A")
    pk = TW.paket(p, simdi=T)
    kit = K.build_kit(p)
    assert pk["aciklama"] == kit["aciklama"]
    assert pk["aciklama_sha1"] == TW.sha1(kit["aciklama"])
    assert pk["ai_beyani"] == "aciklama"
    assert "suno" not in pk["aciklama"].lower()
    assert pk["video"].endswith(os.path.join("output", "shorts_9x16.mp4"))
    assert pk["kapak"].endswith("cover_vertical.png")


def test_modul_build_kit_cagiriyor_kopyalamiyor():
    kaynak = open(os.path.join(_UPLOAD, "tiktok_web.py"), encoding="utf-8").read()
    assert "K.build_kit(" in kaynak
    assert "build_tiktok_kit_caption" not in kaynak


def test_gunluk_rapor_satiri(kok):
    p = _proje(kok, "A")
    assert WR._tiktok_web_bolumu(T, [p]) == ""
    _web(p, _an(15, 18))
    assert "TikTok planlı: A 15.09 18:00" in WR._tiktok_web_bolumu(T, [p])


def test_auto_process_finally_web_sirasini_kitten_sonra_cagiriyor():
    kaynak = open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read()
    govde = kaynak.split("\n    finally:\n")[-1]
    assert govde.index("_tiktok_kit_sirasi()") < govde.index("_tiktok_web_sirasi()")


def test_cli_cp1254_cokmez(kok, monkeypatch):
    p = _proje(kok, "Kırık Şarkı")
    _web(p, _an(15, 18))
    for argv in (["durum", "--json"], ["paket", "--proje", "Kırık Şarkı", "--json"],
                 ["plan-oner", "--json"]):
        tampon = io.BytesIO()
        akis = io.TextIOWrapper(tampon, encoding="cp1254")
        monkeypatch.setattr(sys, "stdout", akis)
        assert TW.main(argv) == 0
        akis.flush()
        monkeypatch.setattr(sys, "stdout", sys.__stdout__)
        cikti = tampon.getvalue().decode("utf-8")
        assert "Kırık Şarkı" in cikti
        json.loads(cikti)


def test_cli_alt_surec_cp1254_durum_json():
    ortam = dict(os.environ, PYTHONIOENCODING="cp1254")
    r = subprocess.run([sys.executable, os.path.join(_UPLOAD, "tiktok_web.py"), "durum", "--json"],
                       capture_output=True, env=ortam, timeout=120)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    veri = json.loads(r.stdout.decode("utf-8"))
    assert set(veri) >= {"surum", "planli", "yayinlandi", "iptal", "dogrulanmadi", "web_modu"}
