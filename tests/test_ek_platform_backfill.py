# -*- coding: utf-8 -*-
"""upload/ek_platform_backfill.py — GÜNLÜK tavan ve platform başına ön koşul.

NEDEN (2026-09-11 denetimi): modülün ilk sürümünde tek kapı golden-hour'du ve
`KOSU_TAVANI = 1` koşu BAŞINAYDI, gün başına değil. Golden-hour günde 6 saat
(config.GOLDEN_HOURS) ve auto_process saatlik tetikleniyor — yani gerçek tavan
günde 6 Telegram + 6 Bluesky gönderisiydi ve 14 eksik şarkı ~1,2 günde
boşalıyordu. Tam olarak modülün engellemek için yazıldığı şey.

İkinci arıza: ön koşul `output/shorts_9x16.mp4`e bakıyordu ama Telegram boş
kwargs ile çağrılıyor -> `upload_video(kind="uzun")` -> gerçekte
`output/youtube_16x9.mp4` yükleniyor. Sadece shorts'u olan bir projede
FileNotFoundError.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import config
import ek_platform_backfill as E


def _proje(base, ad, state, videolar):
    d = os.path.join(base, ad)
    os.makedirs(os.path.join(d, "output"))
    for v in videolar:
        with open(os.path.join(d, "output", v), "wb") as f:
            f.write(b"x")
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return d


def _katalog(tmp_path, monkeypatch, damga=None, videolar=("youtube_16x9.mp4",
                                                          "shorts_9x16.mp4")):
    base = str(tmp_path / "projects")
    os.makedirs(base)
    monkeypatch.setattr(E, "BASE", base)
    # Golden-hour kapısı bu testlerin konusu değil; hep "içerideyiz".
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    # Kimlik dosyaları: CI'da (ve temiz bir checkout'ta) gerçekten yok, sahte
    # bir UPLOAD_DIR ile ikisi de var sayılıyor.
    sahte_upload = str(tmp_path / "upload")
    os.makedirs(sahte_upload, exist_ok=True)
    for p in E.PLATFORMLAR:
        with open(os.path.join(sahte_upload, p[5]), "w", encoding="utf-8") as f:
            f.write("{}")
    monkeypatch.setattr(E, "UPLOAD_DIR", sahte_upload)
    monkeypatch.setattr(config, "EK_PLATFORMLAR",
                        {"facebook": True, "telegram": True, "bluesky": True})
    if damga:
        _proje(base, "00_gecmis", {
            "youtube_video_id": "v0", "youtube_uploaded_at": "2026-09-01",
            "telegram_message_id": 3, "telegram_uploaded_at": damga,
            "bluesky_post_uri": "at://x", "bluesky_uploaded_at": damga},
            videolar)
    for i in range(1, 4):
        _proje(base, "sarki_%d" % i,
               {"youtube_video_id": "v%d" % i,
                "youtube_uploaded_at": "2026-09-0%d" % i}, videolar)
    return base


def test_bugun_yuklenen_sadece_bugunu_sayar(tmp_path, monkeypatch):
    bugun = time.strftime("%Y-%m-%dT%H:%M:%S")
    _katalog(tmp_path, monkeypatch, damga=bugun)
    assert E.bugun_yuklenen("telegram_uploaded_at") == 1
    assert E.bugun_yuklenen("bluesky_uploaded_at") == 1

    dun = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400)) + "T10:00:00"
    _katalog(tmp_path / "b", monkeypatch, damga=dun)
    assert E.bugun_yuklenen("telegram_uploaded_at") == 0


def test_gunluk_tavan_ayni_gun_ikinci_kosuyu_engeller(tmp_path, monkeypatch):
    """ASIL REGRESYON: aynı gün içinde ikinci koşu hiçbir şey göndermemeli."""
    _katalog(tmp_path, monkeypatch)
    s1 = E.backfill(dry_run=True)
    assert [x["platform"] for x in s1["islenen"]] == ["Telegram", "Bluesky"]
    assert not s1["tavan"]

    # Gönderiler gerçekleşmiş gibi BUGÜN damgası at (dry_run state yazmıyor).
    for ad in ("sarki_1",):
        p = os.path.join(E.BASE, ad, "state.json")
        st = json.load(open(p, encoding="utf-8"))
        st.update({"telegram_message_id": 9,
                   "telegram_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "bluesky_post_uri": "at://y",
                   "bluesky_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        json.dump(st, open(p, "w", encoding="utf-8"))

    s2 = E.backfill(dry_run=True)
    assert s2["islenen"] == []          # golden-hour içindeyiz ama tavan dolu
    assert set(s2["tavan"]) == {"Telegram", "Bluesky"}
    assert s2["kalan"]["Telegram"] == 2  # eksikler duruyor, sadece ertelendi


def test_golden_hour_disinda_hicbir_sey_yapmaz(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: "18:00")
    s = E.backfill(dry_run=True)
    assert s["durum"] == "golden-hour disinda"
    assert s["islenen"] == []


def test_telegram_on_kosulu_16x9_shorts_degil(tmp_path, monkeypatch):
    """Sadece shorts'u olan proje Telegram'a ADAY OLMAMALI.

    Telegram gerçekte youtube_16x9.mp4 yüklüyor (kind='uzun'); eski ön koşul
    shorts'a bakıyordu ve böyle bir projede FileNotFoundError veriyordu.
    """
    _katalog(tmp_path, monkeypatch, videolar=("shorts_9x16.mp4",))
    tg = E.eksik_projeler("telegram_message_id",
                          os.path.join("output", "youtube_16x9.mp4"))
    bs = E.eksik_projeler("bluesky_post_uri",
                          os.path.join("output", "shorts_9x16.mp4"))
    assert tg == []                      # 16x9 yok -> Telegram aday değil
    assert len(bs) == 3                  # Bluesky shorts kullanıyor -> aday

    s = E.backfill(dry_run=True)
    assert [x["platform"] for x in s["islenen"]] == ["Bluesky"]


def test_platform_tanimi_gercek_yuklenen_dosyayla_tutarli():
    """PLATFORMLAR'daki 'gerekli video' ile modülün varsayılanı aynı olmalı."""
    import telegram_upload
    tg = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]
    varsayilan_kind = "uzun"
    assert tg[4] == telegram_upload.KINDS[varsayilan_kind][0]
    assert tg[3] == telegram_upload.KINDS[varsayilan_kind][1] + "_uploaded_at"
