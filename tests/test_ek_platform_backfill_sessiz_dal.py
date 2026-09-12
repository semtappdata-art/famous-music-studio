# -*- coding: utf-8 -*-
"""ek_platform_backfill — İKİ SESSİZ `continue` dalı (B6, 2026-09-11).

NEDEN: bu modülün TAMAMI "sessizce duran hattı yakalamak" için yazıldı ve
`tavan`/`kalan`/`atlanan` dallarının hepsi özenle loglanıyor — ama iki dal
istisnaydı:

    if not config.EK_PLATFORMLAR.get(bayrak, False):
        continue          # log YOK, sonuç sözlüğünde iz YOK
    if not os.path.isfile(os.path.join(UPLOAD_DIR, kimlik)):
        continue          # log YOK, sonuç sözlüğünde iz YOK

Yani bayrak kapanırsa ya da kimlik dosyası kaybolursa (Netlify/Instagram'da
2026-09-08'de tam olarak bu oldu: kimlik bilgisi bozuldu, hat 25+ koşu boyunca
sessizce durdu) süpürge SONSUZA KADAR sessizce hiçbir şey yapar ve "config'te
kapattık" ile "kod bozuk" ayırt edilemez. `dj_tarama_kontrol.kontrol_et()`
aynı sınıftaki dalı doğru yapıyor ("config.DJ_ON_TARAMA kapalı, karantina
kapısı atlandı") — desen oradan alındı.

Testler AĞA ÇIKMAZ: iki dal da yükleyici modüller import edilmeden ÖNCE
`continue` ediyor; kimlik dosyası kontrolü de gerçek `upload/` yerine boş bir
geçici klasöre bakıyor (diskteki GERÇEK token dosyalarına dokunulmuyor).
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

import config
import ek_platform_backfill as E


def _ortam(tmp_path, monkeypatch, bayraklar, kimlikler_var):
    """Golden-hour içinde, boş bir katalog ve sahte bir `upload/` klasörü."""
    base = str(tmp_path / "projects")
    os.makedirs(base)
    monkeypatch.setattr(E, "BASE", base)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR", dict(bayraklar))

    sahte_upload = str(tmp_path / "upload")
    os.makedirs(sahte_upload)
    if kimlikler_var:
        for p in E.PLATFORMLAR:
            with open(os.path.join(sahte_upload, p[5]), "w", encoding="utf-8") as f:
                f.write("{}")
    monkeypatch.setattr(E, "UPLOAD_DIR", sahte_upload)

    satirlar = []
    return satirlar, lambda m: satirlar.append(m)


def test_bayrak_kapaliysa_log_ve_sonuc_izi_var(tmp_path, monkeypatch):
    satirlar, log = _ortam(tmp_path, monkeypatch,
                           {"telegram": False, "bluesky": False},
                           kimlikler_var=True)
    sonuc = E.backfill(log=log)

    assert sonuc.get("kapali") == {"Telegram": "telegram", "Bluesky": "bluesky"}
    assert len(satirlar) == 2
    for satir in satirlar:
        assert "kapalı" in satir and "EK_PLATFORMLAR" in satir
    # Kapalı platform için yükleme denenmedi.
    assert sonuc["islenen"] == []


def test_kimlik_dosyasi_yoksa_log_ve_sonuc_izi_var(tmp_path, monkeypatch):
    satirlar, log = _ortam(tmp_path, monkeypatch,
                           {"telegram": True, "bluesky": True},
                           kimlikler_var=False)
    sonuc = E.backfill(log=log)

    assert sonuc.get("kimlik_yok") == {
        "Telegram": "telegram_client_secrets.json",
        "Bluesky": "bluesky_client_secrets.json",
    }
    assert len(satirlar) == 2
    for satir in satirlar:
        assert "yok" in satir and "atlandı" in satir
    assert sonuc["islenen"] == []


def test_tek_platform_kapaliyken_digeri_calismaya_devam_ediyor(tmp_path,
                                                               monkeypatch):
    """Sessiz dalın log'a düşmesi hattı DURDURMAMALI — sadece görünür kılmalı."""
    satirlar, log = _ortam(tmp_path, monkeypatch,
                           {"telegram": False, "bluesky": True},
                           kimlikler_var=True)
    sonuc = E.backfill(log=log)

    assert list(sonuc.get("kapali") or {}) == ["Telegram"]
    # Bluesky dalı sonuna kadar gitti: aday yok ama "kalan" sayacı yazıldı.
    assert "Bluesky" in sonuc["kalan"]
    assert "Telegram" not in sonuc["kalan"]
