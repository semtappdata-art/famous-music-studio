# -*- coding: utf-8 -*-
"""upload/yorum_gonder.py — GÖNDERMEME garantileri.

NEDEN (2026-09-11):
  Bu modülün tek riskli yanı `comments().insert`: gerçek insanlara, kanalın
  adına, geri alınamaz biçimde yazıyor ve adedi 50 birim kota. Bu yüzden
  testlerin çoğu "şu koşulda HİÇBİR ŞEY gönderilmedi" iddiasını doğruluyor.

  Somut olay: 2026-09-11'de `yorum_taslaklari.json`'daki 10 taslağın 10'u da
  aslında 10 Eylül'de ELLE gönderilmişti. Dosyadaki `durum` alanına güvenen
  bir akış aynı cümleyi 10 gerçek insana İKİNCİ kez yazardı — onu yakalayan
  şey `calistir()`'in gönderimden ÖNCE thread'i API'den tazeden okuması.
  `test_kanal_yaniti_varsa_gonderilmez` tam olarak o katmanı kilitliyor.
"""

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import yorum_gonder as Y

KANAL = "UC_kanal_bizim"


# --------------------------------------------------------------------------
# Sahte YouTube servisi
# --------------------------------------------------------------------------

class _Istek(object):
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        return self._sonuc


class _Kanallar(object):
    def __init__(self, kanal_id):
        self._kanal_id = kanal_id

    def list(self, **kw):
        return _Istek({"items": [{"id": self._kanal_id}]})


class _Threadler(object):
    def __init__(self, ogeler):
        self._ogeler = ogeler
        self.istek_sayisi = 0
        self.sorulan_idler = []

    def list(self, **kw):
        self.istek_sayisi += 1
        istenen = [i for i in (kw.get("id") or "").split(",") if i]
        self.sorulan_idler.extend(istenen)
        return _Istek({"items": [o for o in self._ogeler if o["id"] in istenen]})


class _Yorumlar(object):
    def __init__(self, patlat=False):
        self.gonderilenler = []
        self._patlat = patlat

    def insert(self, part=None, body=None):
        if self._patlat:
            raise RuntimeError("API patladi")
        self.gonderilenler.append(body)
        return _Istek({"id": "yeni_yanit"})


class SahteYT(object):
    def __init__(self, ogeler, kanal_id=KANAL, patlat=False):
        self._kanallar = _Kanallar(kanal_id)
        self._threadler = _Threadler(ogeler)
        self._yorumlar = _Yorumlar(patlat)

    def channels(self):
        return self._kanallar

    def commentThreads(self):
        return self._threadler

    def comments(self):
        return self._yorumlar


def _thread(yorum_id, metin, kanal_yaniti=False, baskasinin_yaniti=False):
    """API'nin dondurdugu thread yapisini taklit eder."""
    yanitlar = []
    if kanal_yaniti:
        yanitlar.append({"snippet": {"authorChannelId": {"value": KANAL},
                                     "textDisplay": "bizim onceki yanitimiz"}})
    if baskasinin_yaniti:
        yanitlar.append({"snippet": {"authorChannelId": {"value": "UC_baskasi"},
                                     "textDisplay": "ucuncu kisinin yaniti"}})
    return {
        "id": yorum_id,
        "snippet": {"topLevelComment": {"snippet": {"textDisplay": metin}}},
        "replies": {"comments": yanitlar},
    }


def _taslak_dosyasi(tmp_path, taslaklar):
    yol = tmp_path / "yorum_taslaklari.json"
    with io.open(str(yol), "w", encoding="utf-8") as f:
        f.write(json.dumps({"taslaklar": taslaklar}, ensure_ascii=False, indent=2))
    return str(yol)


def _kur(tmp_path, monkeypatch, taslaklar, ogeler, patlat=False):
    yol = _taslak_dosyasi(tmp_path, taslaklar)
    monkeypatch.setattr(Y, "TASLAK_YOLU", yol)
    yt = SahteYT(ogeler, patlat=patlat)
    monkeypatch.setattr(Y, "get_authenticated_service", lambda: yt)
    return yol, yt


def _oku(yol):
    return json.load(io.open(yol, encoding="utf-8"))


def _durum(yol, yorum_id):
    # Varsayilan, adaylar()'in kullandigi varsayilanla AYNI olmali:
    # 'durum' alani hic yazilmamis bir taslak hala onay bekliyor demektir.
    for t in _oku(yol)["taslaklar"]:
        if t["id"] == yorum_id:
            return t.get("durum", "onay_bekliyor")
    return None


# --------------------------------------------------------------------------
# Gec baglama: TASLAK_YOLU degistirilebilir olmali
# --------------------------------------------------------------------------

def test_taslak_yolu_gec_baglaniyor(tmp_path, monkeypatch):
    """`def f(yol=TASLAK_YOLU)` modul yuklenirken baglanir ve monkeypatch
    ETKISIZ kalirdi — bu test o regresyonu yakalar."""
    yol = _taslak_dosyasi(tmp_path, [{"id": "a", "yanit": "x"}])
    monkeypatch.setattr(Y, "TASLAK_YOLU", yol)
    assert Y.taslaklari_oku()["taslaklar"][0]["id"] == "a"

    Y.taslaklari_yaz({"taslaklar": [{"id": "b"}]})
    assert _oku(yol)["taslaklar"][0]["id"] == "b"


def test_taslaklari_yaz_atomik_gecici_dosya_birakmaz(tmp_path, monkeypatch):
    yol = _taslak_dosyasi(tmp_path, [{"id": "a"}])
    Y.taslaklari_yaz({"taslaklar": [{"id": "a", "yanit": "ç ğ ş ı ❤"}]}, yol)
    assert not os.path.exists(yol + ".tmp")
    assert _oku(yol)["taslaklar"][0]["yanit"] == "ç ğ ş ı ❤"


# --------------------------------------------------------------------------
# adaylar()
# --------------------------------------------------------------------------

def test_adaylar_sadece_onay_bekleyeni_alir():
    veri = {"taslaklar": [
        {"id": "a", "yanit": "yanit a", "durum": "onay_bekliyor"},
        {"id": "b", "yanit": "yanit b", "durum": "gonderildi"},
        {"id": "c", "yanit": "yanit c", "durum": "zaten_yanitlandi"},
        {"id": "d", "yanit": "yanit d"},              # durum yok -> onay_bekliyor
        {"id": "e", "yanit": "   ", "durum": "onay_bekliyor"},   # bos metin
        {"id": "f", "durum": "onay_bekliyor"},                   # yanit alani yok
    ]}
    assert [t["id"] for t in Y.adaylar(veri)] == ["a", "d"]


def test_adaylar_id_filtresi():
    veri = {"taslaklar": [{"id": "a", "yanit": "x"}, {"id": "b", "yanit": "y"}]}
    assert [t["id"] for t in Y.adaylar(veri, "b")] == ["b"]


# --------------------------------------------------------------------------
# EN ONEMLI: dry-run ve atlama dallarinda HICBIR SEY gonderilmez
# --------------------------------------------------------------------------

def test_dry_run_varsayilan_hicbir_sey_gondermez(tmp_path, monkeypatch):
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "merhaba", "yorum": "guzel"}],
        [_thread("a", "guzel")])

    sayi = Y.calistir(gonder=False)

    assert sayi == 1                          # "gonderilmeye hazir" sayisi
    assert yt.comments().gonderilenler == []  # ama HICBIR insert yok
    assert _durum(yol, "a") == "onay_bekliyor"   # durum da tuketilmemis


def test_kanal_yaniti_varsa_gonderilmez(tmp_path, monkeypatch):
    """Dosya 'onay_bekliyor' dese BILE, API'de kanalin yaniti varsa gitmez."""
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "ikinci kez ayni cumle", "yorum": "guzel"}],
        [_thread("a", "guzel", kanal_yaniti=True)])

    assert Y.calistir(gonder=True) == 0
    assert yt.comments().gonderilenler == []
    assert _durum(yol, "a") == "zaten_yanitlandi"


def test_baskasinin_yaniti_engellemez(tmp_path, monkeypatch):
    """Ucuncu bir kisi cevaplamissa biz hala yanitlayabiliriz."""
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "bizim yanit", "yorum": "guzel"}],
        [_thread("a", "guzel", baskasinin_yaniti=True)])

    assert Y.calistir(gonder=True) == 1
    assert len(yt.comments().gonderilenler) == 1
    assert _durum(yol, "a") == "gonderildi"


def test_silinmis_yorum_gonderilmez(tmp_path, monkeypatch):
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "yanit", "yorum": "guzel"}],
        [])                                    # API hic dondurmuyor -> silinmis

    assert Y.calistir(gonder=True) == 0
    assert yt.comments().gonderilenler == []
    assert _durum(yol, "a") == "yorum_silinmis"


def test_yorum_degismisse_gonderilmez(tmp_path, monkeypatch):
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "eski yoruma gore yazildi", "yorum": "eski metin"}],
        [_thread("a", "YENI duzenlenmis metin")])

    assert Y.calistir(gonder=True) == 0
    assert yt.comments().gonderilenler == []
    assert _durum(yol, "a") == "yorum_degismis"
    assert _oku(yol)["taslaklar"][0]["guncel_yorum"] == "YENI duzenlenmis metin"


# --------------------------------------------------------------------------
# Gercek gonderim dali
# --------------------------------------------------------------------------

def test_gonderim_dogru_govdeyi_kurar(tmp_path, monkeypatch):
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "yorum_1", "yanit": "Sağ ol ❤", "yorum": "guzel"}],
        [_thread("yorum_1", "guzel")])

    assert Y.calistir(gonder=True) == 1
    govde = yt.comments().gonderilenler[0]
    # parentId = ust duzey yorumun ID'si; textOriginal = ham metin
    assert govde["snippet"]["parentId"] == "yorum_1"
    assert govde["snippet"]["textOriginal"] == "Sağ ol ❤"


def test_gonderilen_taslak_isaretlenir_ve_tekrar_gitmez(tmp_path, monkeypatch):
    """Cift gonderim korumasinin dosya katmani."""
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "yanit", "yorum": "guzel"}],
        [_thread("a", "guzel")])

    assert Y.calistir(gonder=True) == 1
    assert _durum(yol, "a") == "gonderildi"
    assert _oku(yol)["taslaklar"][0]["gonderilen_metin"] == "yanit"

    # Ikinci kosu: ayni dosya, ayni API durumu -> artik aday degil
    assert Y.calistir(gonder=True) == 0
    assert len(yt.comments().gonderilenler) == 1


def test_limit_kosu_tavani_uygulanir(tmp_path, monkeypatch):
    taslaklar = [{"id": "t%d" % i, "yanit": "y%d" % i, "yorum": "m%d" % i}
                 for i in range(5)]
    ogeler = [_thread("t%d" % i, "m%d" % i) for i in range(5)]
    yol, yt = _kur(tmp_path, monkeypatch, taslaklar, ogeler)

    assert Y.calistir(gonder=True, limit=2) == 2
    assert len(yt.comments().gonderilenler) == 2
    # Tavanin ustunde kalanlar TUKETILMEMIS olmali
    assert _durum(yol, "t2") == "onay_bekliyor"


def test_tek_istekte_okunur_video_basina_dongu_yok(tmp_path, monkeypatch):
    """Kota: N taslak icin N istek degil, TEK istek (50'lik parcalar)."""
    taslaklar = [{"id": "t%d" % i, "yanit": "y", "yorum": "m"} for i in range(12)]
    ogeler = [_thread("t%d" % i, "m") for i in range(12)]
    _, yt = _kur(tmp_path, monkeypatch, taslaklar, ogeler)

    Y.calistir(gonder=False)
    assert yt.commentThreads().istek_sayisi == 1
    assert len(yt.commentThreads().sorulan_idler) == 12


def test_api_hatasi_kosuyu_durdurmaz_ve_gonderildi_demez(tmp_path, monkeypatch):
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "yanit", "yorum": "guzel"}],
        [_thread("a", "guzel")], patlat=True)

    assert Y.calistir(gonder=True) == 0
    assert _durum(yol, "a") == "onay_bekliyor"   # yanlislikla 'gonderildi' olmamali


def test_aday_yoksa_api_ye_hic_dokunulmaz(tmp_path, monkeypatch):
    """Kota: gonderilecek bir sey yoksa kimlik dogrulama bile yapilmamali."""
    yol = _taslak_dosyasi(tmp_path, [{"id": "a", "yanit": "y", "durum": "gonderildi"}])
    monkeypatch.setattr(Y, "TASLAK_YOLU", yol)

    def _patla():
        raise AssertionError("aday yokken API'ye gidilmemeli")

    monkeypatch.setattr(Y, "get_authenticated_service", _patla)
    assert Y.calistir(gonder=True) == 0


# --------------------------------------------------------------------------
# CLI kapilari
# --------------------------------------------------------------------------

def test_gonder_tek_basina_reddedilir(monkeypatch):
    """--gonder yalnizsa (--id/--hepsi yok) butun dosyayi gondermemeli."""
    monkeypatch.setattr(sys, "argv", ["yorum_gonder.py", "--gonder"])
    with pytest.raises(SystemExit):
        Y.main()


def test_gonder_ile_dry_run_birlikte_reddedilir(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["yorum_gonder.py", "--gonder", "--hepsi", "--dry-run"])
    with pytest.raises(SystemExit):
        Y.main()


def test_bayraksiz_calistirma_dry_run_dur(tmp_path, monkeypatch):
    """Hicbir bayrak verilmezse VARSAYILAN dry-run olmali."""
    yol, yt = _kur(
        tmp_path, monkeypatch,
        [{"id": "a", "yanit": "yanit", "yorum": "guzel"}],
        [_thread("a", "guzel")])
    monkeypatch.setattr(sys, "argv", ["yorum_gonder.py"])

    Y.main()
    assert yt.comments().gonderilenler == []


def test_docstring_otomatiklestirmeye_karsi_uyariyor():
    """Bu modulu zamanlayiciya baglama uyarisi docstring'den SILINMEMELI —
    silinirse sonraki oturum onu auto_process'in finally blogu icine koyar."""
    d = Y.__doc__ or ""
    assert "OTOMATİK DEĞİL" in d.upper() or "OTOMATIK DEGIL" in d.upper()
    assert "50 birim" in d
