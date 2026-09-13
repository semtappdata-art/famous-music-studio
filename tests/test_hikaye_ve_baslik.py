# -*- coding: utf-8 -*-
"""Hikâye paragrafı + "neden bu şarkı" notu kapısı ve YouTube başlık kalıbı rotasyonu
(ozgunluk_plani.md §2c, onaylanan kararlar 2 ve 3, 2026-09-13).

Kilitlenenler:
  * Alan YOKSA uzun açıklama BAYT BAYT eskisi (arşiv: tests/build_snippet_arsivi_2026-09-13.json,
    kod değişmeden ÖNCE gerçek metalardan üretildi).
  * Hikâye uzun açıklamada hook'tan SONRA, link bloğundan ÖNCE; Shorts/IG/FB/TikTok kısa
    metinlerine GİRMEZ. Yasak kelime/dış link taşıyan hikâye açıklamaya HİÇ girmez.
  * Kapı: `config.HIKAYE_KAPISI_TARIHI` öncesi UYARI, o gün ve sonrası HATA (fail-closed,
    `uyumluluk.kontrol(..., "yukleme")`); yalnız YENİ şarkı (youtube_video_id yok).
  * Başlık: "Sözleri" her kalıpta; seçim deterministik; ardışık iki yayında aynı kalıp yok;
    eski videolar (kalıp kaydı yok) `fix_description` ile K1'de kalır.
  * AI bayrağı (`containsSyntheticMedia: True`) değişmez.
Ağa çıkmaz; gerçek state/meta'ya yazmaz.
"""

import datetime
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _y in (_REPO, _UPLOAD):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import config
import ozgun_metin as OM
import social_text
import uyumluluk
import youtube_upload as Y

_ARSIV = os.path.join(_REPO, "tests", "build_snippet_arsivi_2026-09-13.json")

HIKAYE = ("Sözlerin ilk hâli serviste, yolda geçiyordu ve dört buçuk dakika sürdü. "
          "İkinci yazımda hikâyeyi evin içine taşıdık. "
          "Nakaratın çapası tek satıra indi: gece benden, sabah senin.")
NEDEN = "Gece çalışıp sabahı sevdiğine bırakan herkes için yazıldı."


def _meta(**ek):
    m = {"title": "Deneme Şarkı", "theme": "rock",
         "custom_hooks": ["İlk satır burada 🎸"], "custom_questions": ["Sen ne dersin?"]}
    m.update(ek)
    return m


# --- arşiv: alan yokken bayt bayt aynı ---------------------------------------------

def test_hikaye_yokken_aciklama_ve_baslik_arsivle_bayt_bayt_ayni():
    with open(_ARSIV, "r", encoding="utf-8") as f:
        arsiv = json.load(f)
    assert len(arsiv) >= 20
    for ad, kayit in arsiv.items():
        s = Y.build_snippet(dict(kayit["meta"]))
        assert s["title"] == kayit["title"], ad
        assert s["description"] == kayit["description"], ad
        assert s["tags"] == kayit["tags"], ad


# --- hikâye paragrafının yeri ve kapsamı ----------------------------------------------

def test_hikaye_hooktan_sonra_link_blogundan_once():
    yok = Y.build_snippet(_meta())["description"]
    var = Y.build_snippet(_meta(hikaye=HIKAYE, neden_bu_sarki=NEDEN))["description"]
    assert HIKAYE in var
    assert var.index("İlk satır burada") < var.index(HIKAYE) < var.index("📷 Instagram")
    assert var.replace("\n\n" + HIKAYE, "", 1) == yok


def test_hikaye_kisa_metinlere_girmez():
    m = _meta(hikaye=HIKAYE, neden_bu_sarki=NEDEN)
    assert HIKAYE not in Y.build_shorts_snippet(m, "VID")["description"]
    assert HIKAYE not in social_text.build_caption(m)
    assert HIKAYE not in social_text.build_caption(m, ai_beyani=True)


@pytest.mark.parametrize("kotu", [
    "Bu şarkı Suno ile yapıldı. İkinci cümle. Üçüncü cümle.",
    "Yapay zekâ ile ürettik. İkinci cümle burada.",
    "Bir AI denemesiydi. Sonra değiştirdik.",
    "Sözler değişti. Detaylar https://ornek.com adresinde.",
    "Sözler değişti. Detaylar www.ornek.com adresinde.",
])
def test_yasak_kelime_ya_da_link_tasiyan_hikaye_aciklamaya_girmez(kotu):
    s = Y.build_snippet(_meta(hikaye=kotu, neden_bu_sarki=NEDEN))["description"]
    assert kotu not in s
    assert any("yasak" in h for h in OM.hikaye_hatalari(_meta(hikaye=kotu,
                                                              neden_bu_sarki=NEDEN)))


def test_yasak_regex_sinirlari():
    assert OM.yasak_bul("SUNO") and OM.yasak_bul("yapay zeka") and OM.yasak_bul("Ai'yla")
    for temiz in ("Biz yazdık.", "Kaide", "maison", "Bir yazım yardımcısıyla hazırladık."):
        assert not OM.yasak_bul(temiz), temiz


def test_cumle_sayisi_kurallari():
    assert OM.hikaye_hatalari(_meta(hikaye=HIKAYE, neden_bu_sarki=NEDEN)) == []
    assert any("2-4" in h for h in OM.hikaye_hatalari(_meta(hikaye="Tek cümle.",
                                                            neden_bu_sarki=NEDEN)))
    bes = " ".join("Cümle %d." % i for i in range(5))
    assert any("2-4" in h for h in OM.hikaye_hatalari(_meta(hikaye=bes, neden_bu_sarki=NEDEN)))
    assert any("1 cümle" in h for h in OM.hikaye_hatalari(
        _meta(hikaye=HIKAYE, neden_bu_sarki="Bir. İki.")))
    assert any("eksik" in h for h in OM.hikaye_hatalari(_meta()))


# --- kapı: tarih öncesi uyarı, sonrası hata ----------------------------------------------

@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(config, "HIKAYE_KAPISI_TARIHI", "2026-09-21", raising=False)
    return k


def _proje(kok, ad, meta, state=None):
    p = kok / ad
    p.mkdir()
    (p / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    if state is not None:
        (p / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(p)


def _gun(monkeypatch, tarih):
    monkeypatch.setattr(OM, "_bugun", lambda: datetime.date.fromisoformat(tarih))


def test_kapi_tarihten_once_uyari(kok, monkeypatch):
    _gun(monkeypatch, "2026-09-20")
    p = _proje(kok, "Yeni", _meta())
    h, u = uyumluluk.kontrol(p, "yukleme")
    assert not any("hikâye" in x for x in h)
    assert any("hikâye" in x and "2026-09-21" in x for x in u)


def test_kapi_tarihte_ve_sonra_hata(kok, monkeypatch):
    for tarih in ("2026-09-21", "2026-10-02"):
        _gun(monkeypatch, tarih)
        p = _proje(kok, "Yeni" + tarih, _meta())
        h, _u = uyumluluk.kontrol(p, "yukleme")
        assert any("hikâye" in x for x in h), tarih


def test_kapi_gecerli_alanla_temiz(kok, monkeypatch):
    _gun(monkeypatch, "2026-09-25")
    p = _proje(kok, "Tam", _meta(hikaye=HIKAYE, neden_bu_sarki=NEDEN))
    h, u = uyumluluk.kontrol(p, "yukleme")
    assert not any("hikâye" in x for x in h + u)


def test_kapi_yayinlanmis_derleme_dj_ve_render_asamasi_muaf(kok, monkeypatch, tmp_path):
    _gun(monkeypatch, "2026-09-25")
    eski = _proje(kok, "Eski", _meta(), {"youtube_video_id": "v"})
    assert not any("hikâye" in x for x in sum(uyumluluk.kontrol(eski, "yukleme"), []))
    der = _proje(kok, "Derleme", _meta(derleme=True, derleme_notu="n",
                                        derleme_liste=[{"zaman": "0:00", "ad": "a"}] * 3))
    assert not any("hikâye" in x for x in sum(uyumluluk.kontrol(der, "yukleme"), []))
    dj = _proje(kok, "Set", {"title": "Set", "theme": "dj"})
    assert not any("hikâye" in x for x in sum(uyumluluk.kontrol(dj, "yukleme"), []))
    yeni = _proje(kok, "Yeni", _meta())
    assert not any("hikâye" in x for x in uyumluluk.kontrol(yeni, "render")[0])


def test_ai_bayragi_kaynakta_degismedi():
    with open(os.path.join(_UPLOAD, "youtube_upload.py"), "r", encoding="utf-8") as f:
        kaynak = f.read()
    assert '"containsSyntheticMedia": True' in kaynak


# --- başlık kalıbı rotasyonu ---------------------------------------------------------------

def test_tum_kaliplarda_sozleri_var_ve_config_te():
    kaliplar = OM.baslik_kaliplari()
    assert [k["id"] for k in kaliplar][:2] == ["K1", "K2"] and len(kaliplar) >= 3
    m = _meta(baslik_eki="Gece Vardiyasından Sonra")
    for k in kaliplar:
        baslik = Y.build_snippet(m, baslik_kalibi=k["id"])["title"]
        assert "Sözleri" in baslik and "Deneme Şarkı" in baslik, (k, baslik)


def test_varsayilan_kalip_k1_bugunku_baslik():
    assert Y.build_snippet(_meta())["title"] == "Deneme Şarkı (Sözleri) | Türkçe Rock Şarkısı"
    assert Y.build_snippet(_meta(), baslik_kalibi="K1")["title"] == \
        "Deneme Şarkı (Sözleri) | Türkçe Rock Şarkısı"
    assert Y.build_snippet(_meta(), baslik_kalibi="K2")["title"] == \
        "Deneme Şarkı — Sözleri | Famous Music Studio"


def test_k3_baslik_eki_yoksa_secilmez():
    ids = [k["id"] for k in OM.uygun_kaliplar(_meta())]
    assert "K3" not in ids
    assert "K3" in [k["id"] for k in OM.uygun_kaliplar(_meta(baslik_eki="Üç Kelime"))]


def test_secim_deterministik_ve_oncekiyle_ayni_degil():
    for onceki in ("K1", "K2", "K3", None):
        for ad in ("A", "Sabah Senin", "Yükseliş", "Bir Başka Şarkı"):
            m = _meta(title=ad, baslik_eki="Ek")
            s1, s2 = OM.kalip_sec(m, onceki), OM.kalip_sec(m, onceki)
            assert s1 == s2 and s1 != onceki


def test_ardisik_alti_yayinda_ayni_kalip_yok():
    onceki, dizi = "K1", []
    for i in range(6):
        k = OM.kalip_sec(_meta(title="Şarkı %d" % i, baslik_eki="Ek %d" % i), onceki)
        dizi.append(k)
        onceki = k
    assert all(a != b for a, b in zip(["K1"] + dizi, dizi))


def test_onceki_kalip_katalogdan_kayitsiz_eski_video_k1(kok):
    _proje(kok, "Eski", _meta(), {"youtube_video_id": "a",
                                   "youtube_uploaded_at": "2026-09-08T20:00:00"})
    assert OM.onceki_kalip([str(kok / "Eski")]) == "K1"
    _proje(kok, "Yeni", _meta(), {"youtube_video_id": "b", "youtube_baslik_kalibi": "K2",
                                   "youtube_uploaded_at": "2026-09-10T20:00:00"})
    assert OM.onceki_kalip([str(kok / "Eski"), str(kok / "Yeni")]) == "K2"
    assert OM.onceki_kalip([str(kok / "Eski"), str(kok / "Yeni")],
                           haric=str(kok / "Yeni")) == "K1"


class _Istek:
    def __init__(self, sonuc=None):
        self.sonuc = sonuc or {}

    def execute(self):
        return self.sonuc


class _Videolar:
    def __init__(self, kayit):
        self.kayit = kayit

    def update(self, part=None, body=None):
        self.kayit.append(body)
        return _Istek()


class _SahteYT:
    def __init__(self):
        self.guncellemeler = []

    def videos(self):
        return _Videolar(self.guncellemeler)


def test_yeni_yukleme_kalibi_doner_ve_state_e_yazar(kok, monkeypatch):
    monkeypatch.setattr(config, "YOUTUBE_BASLIK_ROTASYONU_AKTIF", True, raising=False)
    _proje(kok, "Onceki", _meta(), {"youtube_video_id": "a", "youtube_baslik_kalibi": "K2",
                                     "youtube_uploaded_at": "2026-09-12T20:00:00"})
    p = _proje(kok, "Yeni", _meta(title="Yeni"), {})
    gonderilen = []
    monkeypatch.setattr(Y, "_upload", lambda yol, snip, priv, publish_at=None:
                        gonderilen.append(snip) or "VIDX")
    monkeypatch.setattr(Y, "upload_thumbnail", lambda *a, **k: None)
    monkeypatch.setattr(Y, "get_authenticated_service", lambda: None)
    assert Y.upload_video(p, "public", schedule=False) == "VIDX"
    st = json.load(open(os.path.join(p, "state.json"), encoding="utf-8"))
    assert st["youtube_baslik_kalibi"] in ("K1", "K3") and st["youtube_baslik_kalibi"] != "K2"
    assert gonderilen[0]["title"] == Y.build_snippet(_meta(title="Yeni"),
                                                     baslik_kalibi=st["youtube_baslik_kalibi"])["title"]


def test_eski_video_aciklama_duzeltmesinde_basligi_degismez(kok, monkeypatch):
    p = _proje(kok, "Eski", _meta(title="Eski"), {"youtube_video_id": "OLD"})
    yt = _SahteYT()
    monkeypatch.setattr(Y, "get_authenticated_service", lambda: yt)
    Y.fix_description(p)
    assert yt.guncellemeler[0]["snippet"]["title"] == "Eski (Sözleri) | Türkçe Rock Şarkısı"
    p2 = _proje(kok, "Donen", _meta(title="Donen"),
                {"youtube_video_id": "NEW", "youtube_baslik_kalibi": "K2"})
    Y.fix_description(p2)
    assert yt.guncellemeler[1]["snippet"]["title"] == "Donen — Sözleri | Famous Music Studio"
