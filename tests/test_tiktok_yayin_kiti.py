# -*- coding: utf-8 -*-
"""TikTok yayın kiti (`upload/tiktok_yayin_kiti.py`, 2026-09-13).

Taslak (inbox) akışında API açıklama/gizlilik/AI etiketi/duet-stitch alamıyor;
bunlar Direct Post'a özgü. Kit, kullanıcının telefonda ELLE uygulayacağı her
şeyi AYRI Telegram mesajlarında verir (kapak, açıklama, ayar listesi, ilk yorum,
onay satırı). Kapılar: fail-closed durum ön şartı, `hazir`, golden-hour, tempo
(koşu/pencere/gün/hafta, 36 saat), önceki kit onaylanmadan yenisi yok.

Hiçbir test ağa çıkmaz (gönderici fonksiyonlar sahte; varsayılan `notify`
göndericileri patlayacak şekilde değiştirildi), gerçek `projects/`e dokunmaz
(`uyumluluk.KOKLER` tmp_path), gerçek bildirim göndermez.
"""

import ast
import io
import json
import os
import struct
import sys
from datetime import datetime

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import notify
import social_text as ST
import tiktok_publish_plan as TPP
import tiktok_upload
import tiktok_yayin_kiti as K
import tiktok_yayin_onayi as ONAY
import uyumluluk

BETIK = os.path.join(_UPLOAD, "tiktok_yayin_kiti.py")
SAAT = 3600
# 2026-09-14 19:00 TR — golden-hour (18-22) içinde.
T = datetime(2026, 9, 14, 19, 0, tzinfo=config.TR_TZ).timestamp()


# --------------------------------------------------------------------------
# Fikstürler
# --------------------------------------------------------------------------

def _png(yol, w, h):
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
                + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)


def _proje(kok, klasor, durum=None, meta=None, kapak=(900, 1600), simdi=T,
           durum_tam=None):
    p = kok / klasor
    p.mkdir(parents=True, exist_ok=True)
    if durum_tam is not None:
        d = durum_tam
    else:
        d = {"tiktok_publish_id": "v~" + klasor,
             "tiktok_uploaded_at": K._damga(simdi - 100 * SAAT),
             "tiktok_publish_status": "SEND_TO_USER_INBOX",
             "tiktok_status_checked_at": K._damga(simdi - 2 * SAAT)}
        d.update(durum or {})
    (p / "state.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    m = {"title": klasor, "theme": "pop"}
    m.update(meta or {})
    (p / "meta.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + klasor).encode("utf-8"))
    (p / "output").mkdir(exist_ok=True)
    (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    if kapak:
        _png(str(p / "cover_vertical.png"), *kapak)
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _yaz_durum(proje, **alanlar):
    d = _durum(proje)
    d.update(alanlar)
    with open(os.path.join(proje, "state.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def _kit_gitti(proje, ts, yayinlandi=False):
    d = _durum(proje)
    alan = {"tiktok_kit_gonderildi_at": K._damga(ts),
            "tiktok_kit_kodu": tiktok_upload.yayin_kodu(d["tiktok_publish_id"])}
    if yayinlandi:
        alan["tiktok_published_at"] = K._damga(ts + SAAT)
    _yaz_durum(proje, **alan)


class _Kanal:
    def __init__(self, foto_ok=True, metin_sonuclari=None, send_ok=True):
        self.olaylar = []
        self.foto_ok = foto_ok
        self.metin_sonuclari = list(metin_sonuclari or [])
        self.send_ok = send_ok

    def foto(self, yol, aciklama):
        self.olaylar.append(("foto", yol, aciklama))
        return self.foto_ok

    def metin(self, mesaj):
        self.olaylar.append(("metin", mesaj))
        return self.metin_sonuclari.pop(0) if self.metin_sonuclari else True

    def send(self, baslik, mesaj):
        self.olaylar.append(("send", baslik, mesaj))
        return self.send_ok

    def tur(self, ad):
        return [o for o in self.olaylar if o[0] == ad]


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(K, "_KOSUDA_GONDERILDI", False)
    # Kapı testleri NORMAL akışı ölçüyor; ana şalterin kendisi aşağıda ayrı test.
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", True)

    def _yasak(*a, **kw):
        raise AssertionError("kit testi gerçek notify göndericisine gitmemeli")

    for ad in ("send", "send_photo", "send_text"):
        monkeypatch.setattr(notify, ad, _yasak, raising=False)
    return k


def _kos(kanal, simdi=T, yeni_kosu=True, log=None):
    if yeni_kosu:
        K._KOSUDA_GONDERILDI = False
    satirlar = [] if log is None else log
    sonuc = K.kit_gonder_sirasi(log=satirlar.append, simdi=simdi,
                                gonder_foto=kanal.foto, gonder_metin=kanal.metin,
                                gonder=kanal.send)
    return sonuc, satirlar


# --------------------------------------------------------------------------
# 1. Plan engeli ve durum ön şartı (fail-closed)
# --------------------------------------------------------------------------

def test_hazir_false_kit_gitmez_engel_bir_kez_metin_degisince_tekrar(kok):
    p = _proje(kok, "Bekletilen", {"yayin_beklet": "telif incelemesi"})
    kanal = _Kanal()
    sonuc, satirlar = _kos(kanal)
    assert kanal.tur("metin") == [] and kanal.tur("foto") == []
    assert len(kanal.tur("send")) == 1, kanal.olaylar
    assert "Bekletilen" in kanal.tur("send")[0][2]
    assert "tiktok_kit_gonderildi_at" not in _durum(p)
    assert _durum(p).get("tiktok_kit_engel_bildirimi")

    _kos(kanal, simdi=T + 17.5 * SAAT)                       # ertesi gün 12:30, golden-hour
    assert len(kanal.tur("send")) == 1, "aynı engel ikinci kez bildirilmemeli"

    _yaz_durum(p, yayin_beklet="kopya şüphesi, operatör bakacak")
    _kos(kanal, simdi=T + 18.5 * SAAT)                       # 13:30, golden-hour
    assert len(kanal.tur("send")) == 2, "engel metni değişince bir kez daha"


@pytest.mark.parametrize("durum", [
    {"tiktok_publish_status": None},
    {"tiktok_publish_status": "PUBLISH_COMPLETE"},
    {"tiktok_publish_status": "PROCESSING_UPLOAD"},
])
def test_durum_send_to_user_inbox_degilse_kit_gitmez(kok, durum):
    p = _proje(kok, "Sarki")
    d = _durum(p)
    d.update(durum)
    d = {k: v for k, v in d.items() if v is not None}
    if "tiktok_publish_status" not in d:
        d.pop("tiktok_status_checked_at", None)
    _proje(kok, "Sarki", durum_tam=d)
    kanal = _Kanal()
    _kos(kanal)
    assert kanal.olaylar == []
    assert "tiktok_kit_gonderildi_at" not in _durum(p)


def test_durum_hic_okunmamissa_sebep_durum_bekleniyor(kok):
    _proje(kok, "A", durum_tam={"tiktok_publish_id": "v~A"})
    _proje(kok, "B", durum_tam={"tiktok_publish_id": "v~B"})
    secim = K.siradaki_kit_adayi(uyumluluk.proje_klasorleri(), T)
    assert secim["aday"] is None
    assert secim["sebep"].startswith("kimse — durum bekleniyor"), secim["sebep"]


def test_bayat_durum_kit_gondermez(kok):
    eski = T - (config.TIKTOK_KIT_DURUM_TAZELIK_SAAT + 1) * SAAT
    _proje(kok, "Sarki", {"tiktok_status_checked_at": K._damga(eski)})
    kanal = _Kanal()
    _kos(kanal)
    assert kanal.olaylar == []


def test_zaten_yayinlanmis_ya_da_denenmez_aday_degil(kok):
    _proje(kok, "Yayinda", {"tiktok_published_at": K._damga(T - 5 * SAAT)})
    _proje(kok, "Olu", {"tiktok_status_denenmez": "FAILED"})
    secim = K.siradaki_kit_adayi(uyumluluk.proje_klasorleri(), T)
    assert secim["aday"] is None


def test_bekletilen_arkadakini_tikamaz(kok):
    a = _proje(kok, "A_eski", {"yayin_beklet": "telif incelemesi",
                               "tiktok_uploaded_at": K._damga(T - 300 * SAAT)})
    b = _proje(kok, "B_yeni", {"tiktok_uploaded_at": K._damga(T - 50 * SAAT)})
    kanal = _Kanal()
    sonuc, _ = _kos(kanal)
    assert _durum(b).get("tiktok_kit_gonderildi_at")
    assert "tiktok_kit_gonderildi_at" not in _durum(a)
    assert sonuc["gonderilen"] == "B_yeni"


def test_golden_hour_disinda_kit_yok(kok):
    _proje(kok, "Sarki")
    gece = datetime(2026, 9, 14, 3, 0, tzinfo=config.TR_TZ).timestamp()
    kanal = _Kanal()
    _, satirlar = _kos(kanal, simdi=gece)
    assert kanal.olaylar == []
    assert any("golden-hour" in s for s in satirlar), satirlar


def test_ana_salter_varsayilan_kapali():
    assert config.TIKTOK_KIT_AKTIF is False, "canlıda KAPALI başlamalı (commit sonrası elle açılır)"


def test_ana_salter_kapaliyken_hicbir_sey_gonderilmez_state_yazilmaz(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", False)
    p = _proje(kok, "Uygun")                                    # normalde kit alırdı
    e = _proje(kok, "Engelli", {"yayin_beklet": "telif incelemesi"})
    a = _proje(kok, "Onaysiz", {"tiktok_uploaded_at": K._damga(T - 300 * SAAT)})
    _kit_gitti(a, T - 60 * SAAT)                                # hatırlatma da gitmezdi
    once = {x: _durum(x) for x in (p, e, a)}
    kanal = _Kanal()
    sonuc, satirlar = _kos(kanal)
    assert kanal.olaylar == [], "send / send_photo / send_text hiç çağrılmamalı"
    assert satirlar == ["  TikTok kit: kit kapalı (config)"], satirlar
    assert {x: _durum(x) for x in (p, e, a)} == once, "state'e yazılmamalı"
    assert sonuc["gonderilen"] is None and sonuc["hatirlatilan"] is None
    # varsayılan notify göndericileriyle de (fikstürde patlayacak şekilde) çağrı yok
    K._KOSUDA_GONDERILDI = False
    K.kit_gonder_sirasi(log=lambda s: None, simdi=T)


def test_ana_salter_acikken_normal_akis(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", True)
    p = _proje(kok, "Uygun")
    kanal = _Kanal()
    _kos(kanal)
    assert kanal.tur("foto") and kanal.tur("metin")
    assert _durum(p).get("tiktok_kit_gonderildi_at")


# --------------------------------------------------------------------------
# 2. Tempo
# --------------------------------------------------------------------------

def test_kosu_ve_pencere_basina_en_fazla_bir(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_ARALIK_SAAT", 0)
    monkeypatch.setattr(config, "TIKTOK_KIT_GUNLUK_TAVAN", 5)
    monkeypatch.setattr(config, "TIKTOK_KIT_HAFTALIK_TAVAN", 10)
    a = _proje(kok, "A", {"tiktok_uploaded_at": K._damga(T - 90 * SAAT)})
    b = _proje(kok, "B", {"tiktok_uploaded_at": K._damga(T - 80 * SAAT)})
    kanal = _Kanal()
    _kos(kanal)
    assert _durum(a).get("tiktok_kit_gonderildi_at")
    assert "tiktok_kit_gonderildi_at" not in _durum(b)
    _yaz_durum(a, tiktok_published_at=K._damga(T))          # onay geldi
    once = len(kanal.olaylar)
    _kos(kanal, simdi=T + 60, yeni_kosu=False)
    assert len(kanal.olaylar) == once, "aynı koşuda ikinci kit yok"
    _, satirlar = _kos(kanal, simdi=T + 30 * 60)             # yeni koşu, AYNI pencere
    assert len(kanal.olaylar) == once, "aynı golden-hour penceresinde ikinci kit yok"
    assert any("pencere" in s for s in satirlar), satirlar


def test_36_saat_araligi(kok):
    onceki = _proje(kok, "Onceki", {"tiktok_uploaded_at": K._damga(T - 200 * SAAT)})
    _kit_gitti(onceki, T - 30 * SAAT, yayinlandi=True)
    yeni = _proje(kok, "Yeni")
    kanal = _Kanal()
    _, satirlar = _kos(kanal)
    assert kanal.olaylar == []
    assert any("36" in s for s in satirlar), satirlar
    _kit_gitti(onceki, T - 37 * SAAT, yayinlandi=True)
    _kos(kanal)
    assert _durum(yeni).get("tiktok_kit_gonderildi_at")


def test_gunluk_tavan(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_KIT_ARALIK_SAAT", 0)
    onceki = _proje(kok, "Onceki")
    # Bugün 12:30 (öğle penceresi) bir kit gitmiş ve onaylanmış.
    _kit_gitti(onceki, T - 6.5 * SAAT, yayinlandi=True)
    _proje(kok, "Yeni")
    kanal = _Kanal()
    _, satirlar = _kos(kanal)
    assert kanal.olaylar == []
    assert any("günlük" in s for s in satirlar), satirlar


@pytest.mark.parametrize("gunler,gider", [((1, 2, 3, 4), False), ((1, 2, 3), True),
                                          ((1, 2, 3, 8), True)])
def test_haftalik_tavan(kok, monkeypatch, gunler, gider):
    monkeypatch.setattr(config, "TIKTOK_KIT_ARALIK_SAAT", 0)
    for i, g in enumerate(gunler):
        p = _proje(kok, "Eski%d" % i)
        _kit_gitti(p, T - g * 24 * SAAT, yayinlandi=True)
    yeni = _proje(kok, "Yeni")
    kanal = _Kanal()
    _, satirlar = _kos(kanal)
    assert bool(_durum(yeni).get("tiktok_kit_gonderildi_at")) is gider, satirlar
    if not gider:
        assert any("haftalık" in s for s in satirlar), satirlar


def test_onceki_onaysiz_yenisi_gitmez_48_saatte_tek_hatirlatma(kok):
    a = _proje(kok, "Onaysiz", {"tiktok_uploaded_at": K._damga(T - 300 * SAAT)})
    _kit_gitti(a, T - 40 * SAAT)
    b = _proje(kok, "Siradaki")
    kanal = _Kanal()
    _, satirlar = _kos(kanal)
    assert kanal.olaylar == []
    assert any("onay bekliyor" in s for s in satirlar), satirlar

    # 64 saat sonra (ertesi gün 19:00, golden-hour): TEK hatırlatma
    _kos(kanal, simdi=T + 24 * SAAT)
    assert len(kanal.tur("send")) == 1, kanal.olaylar
    assert "yayınladım Onaysiz" in kanal.tur("send")[0][2]
    assert _durum(a).get("tiktok_kit_hatirlatildi_at")
    assert kanal.tur("metin") == [], "hatırlatma yeni kit değil"

    _, satirlar = _kos(kanal, simdi=T + 25 * SAAT)
    _kos(kanal, simdi=T + 48 * SAAT)
    assert len(kanal.tur("send")) == 1, "ikinci hatırlatma YOK"
    assert any("onay bekliyor" in s for s in satirlar), "sonrası yalnız log"
    assert "tiktok_kit_gonderildi_at" not in _durum(b)

    _yaz_durum(a, tiktok_published_at=K._damga(T + 49 * SAAT))
    # Günlük doğrulama sıradakinin durumunu bu arada yeniden okumuş olur; okuma
    # tazelik sınırını (72 sa) aşsaydı kit — doğru olarak — gitmezdi.
    _yaz_durum(b, tiktok_status_checked_at=K._damga(T + 70 * SAAT))
    _kos(kanal, simdi=T + 72 * SAAT)
    assert _durum(b).get("tiktok_kit_gonderildi_at"), "onay gelince sıradaki gider"


def test_bekleyen_kit_taslagi_denenmez_olursa_sirayi_tikamaz(kok):
    a = _proje(kok, "Silinmis", {"tiktok_uploaded_at": K._damga(T - 300 * SAAT)})
    _kit_gitti(a, T - 100 * SAAT)
    _yaz_durum(a, tiktok_status_denenmez="FAILED: taslak yok")
    b = _proje(kok, "Siradaki")
    _kos(_Kanal())
    assert _durum(b).get("tiktok_kit_gonderildi_at")


# --------------------------------------------------------------------------
# 3. Mesajların içeriği ve sırası
# --------------------------------------------------------------------------

def test_mesaj_sirasi_aciklama_yalniz_ilk_yorum_ayri_link_yok(kok):
    p = _proje(kok, "Kırık Zincir", {"youtube_video_id": "abc123XYZ"},
               meta={"theme": "rock"})
    kanal = _Kanal()
    _kos(kanal)
    kit = K.build_kit(p)
    olaylar = kanal.olaylar
    assert olaylar[0][0] == "foto" and olaylar[0][1] == kit["kapak"]
    assert "Kırık Zincir" in olaylar[0][2] and kit["kod"] in olaylar[0][2]
    metinler = [o[1] for o in kanal.tur("metin")]
    assert metinler[0] == kit["aciklama"], "mesaj 2 YALNIZ açıklama + hashtag"
    assert metinler[0] == ST.build_tiktok_kit_caption(json.load(
        io.open(os.path.join(p, "meta.json"), encoding="utf-8")))
    assert "Herkes" in metinler[1]
    assert metinler[2] == kit["ilk_yorum"] and "youtu.be/abc123XYZ" in metinler[2]
    assert "yayınladım Kırık Zincir" in metinler[3]
    for parca in ("http", "www.", "youtu", ".com"):
        assert parca not in kit["aciklama"].casefold(), parca


def test_ilk_yorum_yoksa_mesaji_da_yok(kok):
    p = _proje(kok, "Sarki")
    kit = K.build_kit(p)
    anahtarlar = [m["anahtar"] for m in K.kit_mesajlari(kit, T)]
    assert anahtarlar == ["kapak", "aciklama", "ayarlar", "onay"], anahtarlar


def _ayar(kit, basi):
    return [d for a, d in kit["ayarlar"] if a.startswith(basi)]


_SARKI_META = {"title": "Sarki", "theme": "pop"}


def test_ayar_listesi_varsayilan_ai_beyani_aciklamada_marka_kapali_gizlilik_herkes(kok):
    """Varsayılan `TIKTOK_AI_BEYANI = "aciklama"` (kullanıcı kararı 2026-09-13):
    uygulamadaki AI anahtarı KAPALI + gerekçe, beyan açıklamada tek satır."""
    assert config.TIKTOK_AI_BEYANI == "aciklama"
    kit = K.build_kit(_proje(kok, "Sarki"))
    assert kit["onerilen_gizlilik_uygulama"] == "Herkes"
    assert _ayar(kit, "Kimler izleyebilir")[0].startswith("Herkes")
    ai = _ayar(kit, "Yapay zekayla üretilen içerik")[0]
    assert ai.startswith("KAPALI") and "açıklamada yazılı beyanı kabul" in ai, ai
    assert ST.ai_beyan_satiri(_SARKI_META) in kit["aciklama"]
    assert _ayar(kit, "İçerik açıklaması / marka içeriği")[0].startswith("KAPALI")
    for ad in ("Yorumlar", "Düet", "Stitch", "Yüksek kaliteli yükleme"):
        assert _ayar(kit, ad)[0].startswith("AÇIK"), ad
    metin = [m for m in K.kit_mesajlari(kit, T) if m["anahtar"] == "ayarlar"][0]["metin"]
    assert "Yapay zekayla üretilen içerik" in metin and "Herkes" in metin
    assert "saat" in metin.casefold()


@pytest.mark.parametrize("mod", ["etiket", "aciklama", "etiket+aciklama"])
def test_ai_beyani_uc_mod_her_modda_en_az_bir_yerde(kok, monkeypatch, mod):
    monkeypatch.setattr(config, "TIKTOK_AI_BEYANI", mod)
    kit = K.build_kit(_proje(kok, "Sarki"))
    beyan = ST.ai_beyan_satiri(_SARKI_META)
    etiket_acik = bool(_ayar(kit, "Yapay zekayla üretilen içerik")) and \
        _ayar(kit, "Yapay zekayla üretilen içerik")[0].startswith("AÇIK")
    aciklamada = beyan in kit["aciklama"]
    assert etiket_acik is ("etiket" in mod), mod
    assert aciklamada is ("aciklama" in mod), mod
    assert etiket_acik or aciklamada


def test_ai_beyani_gecersiz_deger_fail_closed_ikisi_birden(kok, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_AI_BEYANI", "yok")
    kit = K.build_kit(_proje(kok, "Sarki"))
    assert _ayar(kit, "Yapay zekayla üretilen içerik")[0].startswith("AÇIK")
    assert ST.ai_beyan_satiri(_SARKI_META) in kit["aciklama"]
    assert any("TIKTOK_AI_BEYANI" in u for u in kit["uyarilar"])


def test_onay_satiri_tiktok_yayin_onayi_ile_eslesir(kok, capsys):
    p = _proje(kok, "Yürek Yarası")
    kit = K.build_kit(p)
    onay = [m for m in K.kit_mesajlari(kit, T) if m["anahtar"] == "onay"][0]["metin"]
    satir = [s for s in onay.splitlines() if "yayınladım " in s][0]
    yanit = satir[satir.index("yayınladım "):].strip()
    assert ONAY.main([yanit]) == 0, capsys.readouterr().out
    assert _durum(p)["tiktok_published_at"]
    assert kit["kod"] in onay


def test_state_yalniz_aciklama_mesaji_basariliysa_yazilir(kok):
    p = _proje(kok, "Sarki")
    kanal = _Kanal(metin_sonuclari=[False])
    _, satirlar = _kos(kanal)
    assert "tiktok_kit_gonderildi_at" not in _durum(p)
    assert len(kanal.tur("metin")) == 1, "açıklama gitmediyse devamı da gönderilmez"


def test_kapak_basarisizsa_log_kit_yine_sayilir(kok):
    p = _proje(kok, "Sarki")
    kanal = _Kanal(foto_ok=False)
    _, satirlar = _kos(kanal)
    d = _durum(p)
    assert d.get("tiktok_kit_gonderildi_at")
    assert d.get("tiktok_kit_kodu") == tiktok_upload.yayin_kodu(d["tiktok_publish_id"])
    assert any("kapak" in s.casefold() for s in satirlar), satirlar


def test_kapak_9_16_degilse_uyari(kok):
    kit = K.build_kit(_proje(kok, "Kare", kapak=(1080, 1080)))
    assert any("9:16" in u for u in kit["uyarilar"]), kit["uyarilar"]
    metin = [m for m in K.kit_mesajlari(kit, T) if m["anahtar"] == "ayarlar"][0]["metin"]
    assert "9:16" in metin
    assert not any("9:16" in u for u in K.build_kit(_proje(kok, "Dik"))["uyarilar"])


def test_build_kit_build_plani_cagiriyor(kok, monkeypatch):
    p = _proje(kok, "Sarki")
    cagri = []
    gercek = TPP.build_plan
    monkeypatch.setattr(TPP, "build_plan", lambda proje: cagri.append(proje) or gercek(proje))
    kit = K.build_kit(p)
    assert cagri == [p]
    assert kit["hazir"] is True


# --------------------------------------------------------------------------
# 4. CLI, kaynak muhafızları, bağlantı
# --------------------------------------------------------------------------

def test_onizle_cp1254_konsolda_cokmuyor_gonderim_yok(kok, monkeypatch):
    p = _proje(kok, "Kırık Zincir 🔥", meta={"theme": "rock"})
    ham = io.BytesIO()
    akis = io.TextIOWrapper(ham, encoding="cp1254", errors="strict")
    monkeypatch.setattr(sys, "stdout", akis)
    kod = K.main(["--project", p, "--onizle"])
    akis.flush()
    metin = ham.getvalue().decode("utf-8")
    assert kod == 0
    assert "Kırık Zincir" in metin and "#FamousMusicStudio" in metin
    assert "tiktok_kit_gonderildi_at" not in _durum(p)


def test_kit_modulunde_requests_ve_getupdates_yok():
    kaynak = io.open(BETIK, encoding="utf-8").read()
    for yasak in ("requests", "getUpdates", "setWebhook", "urllib"):
        assert yasak not in kaynak, yasak


def test_eski_duz_hatirlatma_kit_isaretli_projede_gitmez(kok, monkeypatch):
    giden = []
    monkeypatch.setattr(notify, "is_configured", lambda: True)
    monkeypatch.setattr(notify, "send", lambda t, m: giden.append((t, m)) or True)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    p = _proje(kok, "Yeni", durum_tam={"tiktok_publish_id": "v~1",
                                       "tiktok_hatirlatma": "kit"})
    assert tiktok_upload.notify_pending_publish(p) is False
    assert giden == []
    assert "tiktok_notified" not in _durum(p)


def test_upload_video_yeni_yuklemeyi_kite_isaretliyor():
    agac = ast.parse(io.open(os.path.join(_UPLOAD, "tiktok_upload.py"), encoding="utf-8").read())
    fn = next(d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == "upload_video")
    assert '"tiktok_hatirlatma"' in ast.unparse(fn) or "'tiktok_hatirlatma'" in ast.unparse(fn)


def _auto_process_agaci():
    return ast.parse(io.open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read())


def test_auto_process_finally_kiti_dogrulamadan_sonra_cagiriyor():
    main = next(d for d in ast.walk(_auto_process_agaci())
                if isinstance(d, ast.FunctionDef) and d.name == "main")
    deneme = next(d for d in ast.walk(main) if isinstance(d, ast.Try) and d.finalbody)
    satir = {}
    for d in ast.walk(ast.Module(body=deneme.finalbody, type_ignores=[])):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            satir.setdefault(d.func.id, d.lineno)
    assert "_tiktok_kit_sirasi" in satir, sorted(satir)
    assert satir["_tiktok_yayin_dogrulama"] < satir["_tiktok_kit_sirasi"]


def test_kanca_try_icinde_ve_is_fully_done_a_eklenmedi():
    agac = _auto_process_agaci()
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == "_tiktok_kit_sirasi")
    assert any(isinstance(x, ast.Try) for x in fn.body)
    assert "kit_gonder_sirasi" in ast.unparse(fn)
    tam = next(d for d in ast.walk(agac)
               if isinstance(d, ast.FunctionDef) and d.name == "_is_fully_done")
    assert "tiktok_kit" not in ast.unparse(tam)


def test_patlayan_kit_kancasi_yutuluyor(monkeypatch):
    import auto_process

    def _patla(*a, **k):
        raise RuntimeError("beklenmedik")

    satirlar = []
    # Kanca şalter kapalıyken kit modülüne hiç inmiyor; bu test AÇIK kancanın
    # istisnayı yuttuğunu ölçüyor.
    monkeypatch.setattr(config, "TIKTOK_KIT_AKTIF", True)
    monkeypatch.setattr(K, "kit_gonder_sirasi", _patla)
    monkeypatch.setattr(auto_process, "log", satirlar.append)
    auto_process._tiktok_kit_sirasi()
    assert any("TikTok yayın kiti HATA" in s for s in satirlar), satirlar
