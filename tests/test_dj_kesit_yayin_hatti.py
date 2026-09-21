# -*- coding: utf-8 -*-
"""İkinci dalga kesit hattının YÜKLEME UCU — `tests/test_dj_clips.py`'nin
kapsamadığı üç parça: `build_clip_snippet`, `_golden_publish_at` ve
`kesit_yayinla`'nın state yazımı.

NEDEN AYRI BİR DOSYA: `test_dj_clips.py` hacim kapılarını (set başına 1, koşu
başına 1, haftalık küresel tempo) çiviliyor ve `kesit_yayinla`'yı her yerde
monkeypatch'liyor — yani hattın YouTube'a bakan yarısı orada HİÇ çalışmıyor.
2026-09-11 doğrulamasında bu üç parça yalnızca ELLE koşturularak görüldü;
buradaki testler o elle koşuyu kalıcılaştırıyor.

Üç ayrı arıza sınıfı kilitleniyor:

1. **Aynı başlık = tekrarlayıcı içerik.** Kesit, setin kendi Shorts'uyla aynı
   başlıkla çıkarsa kanalda neredeyse aynı iki video aynı adla durur — bu,
   kanalın en büyük riski olan "inauthentic content" politikasının tarifi
   (bkz. `dj_clips.py` modül notu). Başlığın FARKLI olması bir yorum değil,
   test edilen bir garanti olmalı.

2. **`_golden_publish_at`'in None tuzağı.** `config.next_golden_publish_time`,
   verilen an ZATEN bir golden-hour penceresindeyse `None` döner ("hemen
   yayınla"). Kaydırılmış anı o None ile "zamanlama yok"a çevirmek kesidi
   BUGÜN yayınlardı — yani 3 günlük ertelemenin tamamen kaybolması, ve hattın
   var oluş sebebi olan hacim kısıtının sessizce delinmesi. Aşağıdaki test
   günün 24 saatinin HEPSİNİ deniyor; tuzak yalnızca golden-hour'a düşen
   saatlerde görünür.

3. **Tekrar gönderimi engelleyen state anahtarları.** `upload_clip` bilerek
   state'e YAZMIYOR (docstring'inde yazıyor); yazan taraf `kesit_yayinla`.
   O anahtarlar yazılmazsa ikinci koşu aynı kesidi ikinci kez yükler.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import config
import dj_clips
import youtube_upload


META = {"title": "Just Relax", "theme": "dj"}


# --- 1) Başlık/açıklama: setin kendi Shorts'uyla ÇAKIŞMAMALI ---------------


def test_kesit_basligi_setin_kendi_shortsundan_FARKLI():
    kesit = youtube_upload.build_clip_snippet(META, "wo2xZBU6VjU", 332.53)
    shorts = youtube_upload.build_shorts_snippet(META, "wo2xZBU6VjU")
    assert kesit["title"] != shorts["title"]
    # Farkı sağlayan şey dakika damgası — "#Shorts" son eki ikisinde de var.
    assert "5:32" in kesit["title"]
    assert kesit["description"].splitlines()[0] != shorts["description"].splitlines()[0]


def test_kesit_aciklamasi_kuratorluk_satiriyla_basliyor_ve_tam_sete_baglaniyor():
    s = youtube_upload.build_clip_snippet(META, "wo2xZBU6VjU", 1491.35)
    assert s["description"].startswith("A different moment from the same set")
    assert "24:51" in s["description"].splitlines()[0]
    assert "https://youtu.be/wo2xZBU6VjU" in s["description"]


def test_tam_video_id_yoksa_aciklamada_link_yok():
    """Set henüz yüklenmemişse kırık/boş bir link basılmamalı."""
    s = youtube_upload.build_clip_snippet(META, None, 10.0)
    assert "youtu.be" not in s["description"]


@pytest.mark.parametrize("saniye,beklenen", [
    (0, "0:00"), (59.9, "0:59"), (60, "1:00"),
    (332.53, "5:32"), (1491.35, "24:51"), (2101.41, "35:01"),
    (-5, "0:00"),  # bozuk/negatif damga 0'a kırpılıyor, "-1:-5" basmıyor
])
def test_dakika_damgasi(saniye, beklenen):
    assert youtube_upload._dakika_damgasi(saniye) == beklenen


# --- 2) Zamanlama: 3 gün SONRAKİ golden-hour, "bugün" ASLA -----------------


class _SabitDatetime(datetime):
    SIMDI = None

    @classmethod
    def now(cls, tz=None):
        return cls.SIMDI.astimezone(tz) if tz else cls.SIMDI


@pytest.mark.parametrize("saat", list(range(24)))
@pytest.mark.parametrize("dakika", [0, 59])
def test_golden_publish_at_her_zaman_3_gun_sonra_ve_golden_hour_icinde(
        monkeypatch, saat, dakika):
    """En kritik test: kaydırılmış an ZATEN golden-hour içindeyse
    next_golden_publish_time None döner; o None "zamanlama yok"a çevrilseydi
    kesit BUGÜN yayınlanırdı."""
    simdi = datetime(2026, 9, 11, saat, dakika, tzinfo=config.TR_TZ)
    _SabitDatetime.SIMDI = simdi
    monkeypatch.setattr(youtube_upload, "datetime", _SabitDatetime)

    damga = youtube_upload._golden_publish_at(dj_clips.KESIT_ERTELEME_GUN)
    assert damga.endswith("Z")
    an = datetime.fromisoformat(damga.replace("Z", "+00:00")).astimezone(config.TR_TZ)

    # (a) En az KESIT_ERTELEME_GUN gün ileride — "bugün" ya da yarın OLAMAZ.
    assert an - simdi >= timedelta(days=dj_clips.KESIT_ERTELEME_GUN)
    # (b) Gerçekten bir golden-hour penceresinin içinde.
    assert any(bas <= an.hour < son for bas, son in config.GOLDEN_HOURS), an


# --- 3) kesit_yayinla: doğru argümanlar + tekrar gönderimi engelleyen state -


def _hazir_set(tmp_path, ad="Sim Set"):
    d = tmp_path / ad
    (d / "output").mkdir(parents=True)
    for n in ("clip_01.mp4", "clip_02.mp4", "clip_03.mp4"):
        (d / "output" / n).write_bytes(b"x")
    (d / "meta.json").write_text(json.dumps(META), encoding="utf-8")
    st = {
        "youtube_video_id": "wo2xZBU6VjU",
        "youtube_shorts_video_id": "BBB",
        "youtube_shorts_uploaded_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(time.time() - dj_clips.KESIT_MIN_ARA_SN - 3600)),
        "dj_tarama_temiz": True,
        "dj_clips": [
            {"dosya": "clip_01.mp4", "bas": 332.53, "son": 377.53, "enerji": 3},
            {"dosya": "clip_02.mp4", "bas": 1491.35, "son": 1536.35, "enerji": 1},
            {"dosya": "clip_03.mp4", "bas": 2101.41, "son": 2146.41, "enerji": 2},
        ],
    }
    (d / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return str(d)


@pytest.fixture
def sahte_upload_clip(monkeypatch):
    """GERÇEK yükleyiciyi sys.modules üzerinden değiştiriyor: kesit_yayinla
    `from youtube_upload import upload_clip`'i FONKSİYON İÇİNDE yapıyor, yani
    çağrı anında modül nesnesinden okunuyor. Ağa/token'a hiç dokunulmuyor."""
    cagri = {}

    def sahte(project_dir, clip_name, full_video_id=None, bas_sn=0.0,
              gun_ertele=0, privacy="public"):
        cagri.update(dict(project_dir=project_dir, clip_name=clip_name,
                          full_video_id=full_video_id, bas_sn=bas_sn,
                          gun_ertele=gun_ertele, privacy=privacy))
        return "SAHTE_VID", "2026-09-14T15:00:00Z"

    monkeypatch.setattr(youtube_upload, "upload_clip", sahte)
    return cagri


def test_kesit_yayinla_dogru_argumanlarla_cagiriyor(tmp_path, sahte_upload_clip):
    set_dir = _hazir_set(tmp_path)
    kesit = dj_clips.kesit_sec(set_dir)
    dj_clips.kesit_yayinla(set_dir, kesit, log=lambda *a: None)

    assert sahte_upload_clip["clip_name"] == "clip_02.mp4"      # en enerjili
    assert sahte_upload_clip["bas_sn"] == 1491.35               # damga bundan türüyor
    assert sahte_upload_clip["full_video_id"] == "wo2xZBU6VjU"  # tam sete link
    # 3 günlük erteleme bir "güzel olur" değil, hacim kısıtının kendisi.
    assert sahte_upload_clip["gun_ertele"] == dj_clips.KESIT_ERTELEME_GUN


def test_kesit_yayinla_state_yaziyor_ve_dj_clips_kaydini_KORUYOR(
        tmp_path, sahte_upload_clip):
    set_dir = _hazir_set(tmp_path)
    dj_clips.kesit_yayinla(set_dir, dj_clips.kesit_sec(set_dir), log=lambda *a: None)

    st = json.load(open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    assert st["youtube_clip_video_id"] == "SAHTE_VID"
    assert st["youtube_clip_dosya"] == "clip_02.mp4"
    assert st["youtube_clip_publish_at"] == "2026-09-14T15:00:00Z"
    assert st["youtube_clip_uploaded_at"]
    # Üretim kaydının üstüne yazılmamalı: süpürgenin okuduğu alan bu.
    assert len(st["dj_clips"]) == 3
    # Setin KENDİ Shorts kaydı da ezilmemeli (ayrı anahtar ailesi olmasının sebebi).
    assert st["youtube_shorts_video_id"] == "BBB"


def test_yayinlanmis_set_ikinci_kosuda_TEKRAR_gonderilmiyor(tmp_path, sahte_upload_clip):
    """Küresel tempo kapısı açık olsa bile (yayın 30 gün önce) set kapısı
    tutmalı — iki kapı BİRBİRİNDEN bağımsız olmalı."""
    set_dir = _hazir_set(tmp_path)
    dj_clips.kesit_yayinla(set_dir, dj_clips.kesit_sec(set_dir), log=lambda *a: None)

    st = json.load(open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    st["youtube_clip_uploaded_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 30 * 86400))
    with open(os.path.join(set_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)

    sahte_upload_clip.clear()
    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)
    assert sonuc["yayinlanan"] == 0
    assert sahte_upload_clip == {}
    assert any("zaten" in a["sebep"] for a in sonuc["atlanan"])
