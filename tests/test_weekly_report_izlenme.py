# -*- coding: utf-8 -*-
"""weekly_report.izlenme_raporu() — HAFTALIK damga mantığı.

NEDEN: `upload/youtube_analytics.py` doğru yazılmıştı ama tek çağıranı
`weekly_report.py`'ydi ve o dosya hiçbir Görev Zamanlayıcı görevine bağlı
değil — ölçüm pratikte hiç çalışmıyordu. Artık saatlik `auto_process`
koşusundan çağrılıyor, bu yüzden "haftada bir çalış, gerisinde sus"
davranışının testi gerçek bir regresyon koruması: damga bozulursa saatlik
koşu ya her saat API'ye gider ya da rapor sessizce hiç çalışmaz.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import weekly_report as wr


SAHTE_OZET = {
    # Kasten TAM YOL: youtube_analytics.KOKLER mutlak yollardan oluşuyor,
    # tabloda kısa ad görünmeli.
    os.path.join("C:", os.sep, "x", "projects"): {
        "video": 18, "dakika": 360, "izlenme": 1200, "ort_izlenme_sn": 45},
    os.path.join("C:", os.sep, "x", "dj_sets"): {
        "video": 2, "dakika": 800, "izlenme": 300, "ort_izlenme_sn": 900},
}


def _rapor_fn():
    return {"ozet": SAHTE_OZET, "video_bazinda": {}}


def _durum_yolu(tmp_path):
    return str(tmp_path / "saglik_durum.json")


def test_ilk_calisma_basar_ve_haftayi_damgalar(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "_bildir", lambda *a, **k: True)
    yol = _durum_yolu(tmp_path)
    satirlar = []
    s = wr.izlenme_raporu(log=satirlar.append, durum_dosyasi=yol,
                          rapor_fn=_rapor_fn, token_yolu="")
    assert s["durum"] == "tamam"
    metin = "\n".join(satirlar)
    assert "İZLENME SÜRESİ" in metin
    # Kısa kök adı basılmalı, tam yol DEĞİL.
    assert "projects" in metin and "dj_sets" in metin
    assert "C:" not in metin
    d = json.load(open(yol, encoding="utf-8"))
    assert d[wr.HAFTA_ANAHTARI] == wr._hafta()


def test_ayni_hafta_ikinci_kosuda_api_ye_gitmez(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "_bildir", lambda *a, **k: True)
    yol = _durum_yolu(tmp_path)
    wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                      rapor_fn=_rapor_fn, token_yolu="")

    cagri = {"n": 0}

    def sayan():
        cagri["n"] += 1
        return _rapor_fn()

    s = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                          rapor_fn=sayan, token_yolu="")
    assert s["durum"] == "atlandi"
    assert cagri["n"] == 0          # saatlik koşu API'ye HİÇ dokunmamalı


def test_zorla_damgayi_yok_sayar(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "_bildir", lambda *a, **k: True)
    yol = _durum_yolu(tmp_path)
    wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                      rapor_fn=_rapor_fn, token_yolu="")
    s = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                          rapor_fn=_rapor_fn, token_yolu="", zorla=True)
    assert s["durum"] == "tamam"


def test_token_yoksa_haftada_bir_uyarir(tmp_path, monkeypatch):
    # notify.py ntfy.sh'a GERÇEK HTTP isteği atıyor — testte sahtesi konuyor.
    import types
    gonderilen = []
    sahte = types.ModuleType("notify")
    # `append` None dondurur; gercek notify.send sozlesmesi ise HER ZAMAN bool
    # (bkz. notify.py). `_bildir` artik donus degerine bakip damgayi sadece
    # basarida attigi icin (2026-09-11), None "gonderilemedi" sayiliyordu ve
    # test kendi sahtesi yuzunden kiriliyordu. Sahte gercege yaklastirildi;
    # testin niyeti degismedi. Sessiz False yolunun kendi testi ayri.
    def _sahte_send(b, m, **k):
        gonderilen.append((b, m))
        return True
    sahte.send = _sahte_send
    monkeypatch.setitem(sys.modules, "notify", sahte)
    yol = _durum_yolu(tmp_path)
    yok = str(tmp_path / "analytics_token.json")   # bilerek yok
    satirlar = []
    s = wr.izlenme_raporu(log=satirlar.append, durum_dosyasi=yol,
                          rapor_fn=_rapor_fn, token_yolu=yok)
    assert s["durum"] == "token_yok"
    assert s["bildirim"] is True                  # ilk seferde bildirildi
    assert wr.AUTH_KOMUTU in "\n".join(satirlar)  # kullanıcıya komut söylendi

    assert len(gonderilen) == 1

    s2 = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                           rapor_fn=_rapor_fn, token_yolu=yok)
    assert s2["bildirim"] is False                # aynı hafta ikinci bildirim YOK
    assert len(gonderilen) == 1


def test_veri_gelmezse_hafta_damgalanmaz_gun_damgalanir(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "_bildir", lambda *a, **k: True)
    yol = _durum_yolu(tmp_path)
    s = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                          rapor_fn=lambda: {"ozet": {}}, token_yolu="")
    assert s["durum"] == "veri_yok"
    d = json.load(open(yol, encoding="utf-8"))
    # Hafta damgalanmamalı — tek boş sonuç yüzünden rapor bir hafta kaybolmasın.
    assert wr.HAFTA_ANAHTARI not in d
    assert d[wr.BOS_ANAHTARI]
    # Ama aynı gün tekrar API'ye gitmemeli.
    s2 = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                           rapor_fn=_rapor_fn, token_yolu="")
    assert s2["durum"] == "atlandi"


def test_rapor_patlarsa_otomasyon_durmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(wr, "_bildir", lambda *a, **k: True)
    yol = _durum_yolu(tmp_path)

    def patlayan():
        raise RuntimeError("quotaExceeded")

    s = wr.izlenme_raporu(log=lambda *_: None, durum_dosyasi=yol,
                          rapor_fn=patlayan, token_yolu="")
    assert s["durum"] == "hata"


def test_bildirim_metni_kisa_ad_kullanir():
    m = wr._bildirim_metni(SAHTE_OZET)
    assert "dj_sets: video başına 400 dk (2 video)" in m
    assert "C:" not in m
