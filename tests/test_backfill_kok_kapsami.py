# -*- coding: utf-8 -*-
"""Geri doldurma süpürgeleri ÜÇ içerik kökünü de görüyor mu (+ yeni kapılar).

NEDEN (2026-09-11): `upload/facebook_backfill.py` ve
`upload/ek_platform_backfill.py` yalnızca `projects/` tarıyordu. Bir DJ setinin
ya da derlemenin Facebook/Telegram/Bluesky yüklemesi yarım kalırsa HİÇBİR
süpürge onu tamamlamıyordu — `dj_famous_process` tek denemeden sonra seti
bırakıyor, yani kayıp KALICI ve log'a tek satır bile düşmüyor (bu deponun
"bağlantı seviyesinde sessiz arıza" sınıfı).

Kapsam genişletilirken çıkan İKİ tuzak da burada test ediliyor, çünkü ikisi de
"genişlettim, bitti" denseydi ÜRETİMDE patlardı:

  1. Telegram'da DJ/derleme kökleri farklı dosya + farklı state anahtarı
     kullanıyor (`kind="dikey"`, `telegram_shorts_message_id`): bir setin
     `output/youtube_16x9.mp4` dosyası 130-540 MB, Telegram bot sınırı 50 MB.
     Varsayılan varyantla genişletilseydi üç set/derleme "hiç gitmemiş"
     görünür, her koşuda hata alır ve GÜNLÜK TEK SLOTU kalıcı işgal ederdi.
  2. Günlük tavan sayaçları da üç kökü saymalı, yoksa o gün normal hattan çıkan
     bir setin paylaşımı tavana girmez — eksik sayan tavan, olmayan tavandan
     farksız (`bluesky_upload._todays_upload_count`'un düzeltilen hatası).

HİÇBİR TESTTE gerçek yükleme yolu çalışmıyor: ya `dry_run=True`, ya doğrudan
saf (ağa çıkmayan) yardımcı fonksiyonlar çağrılıyor. Kimlik dosyası kontrolü de
gerçek `upload/` klasörüne değil, tmp'deki sahte bir klasöre bakıyor — gerçek
token'lara yanlışlıkla dokunulmasın diye.
"""

import json
import os
import sys
import time

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import config                                       # noqa: E402
import ek_platform_backfill as E                    # noqa: E402
import facebook_backfill as F                       # noqa: E402
import uyumluluk                                    # noqa: E402


def _proje(kok_yolu, ad, durum, videolar=("youtube_16x9.mp4", "shorts_9x16.mp4"),
           boyut=8):
    d = os.path.join(kok_yolu, ad)
    os.makedirs(os.path.join(d, "output"), exist_ok=True)
    for v in videolar:
        with open(os.path.join(d, "output", v), "wb") as f:
            f.write(b"x" * boyut)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False)
    return d


def _katalog(tmp_path):
    """Üç kökü de oluşturur; {kok_adi: yol} döner."""
    kokler = {}
    for ad in uyumluluk.KOK_ADLARI:
        d = tmp_path / ad
        d.mkdir(exist_ok=True)
        kokler[ad] = str(d)
    return kokler


def _kok_demeti(kokler):
    return tuple(kokler[ad] for ad in uyumluluk.KOK_ADLARI)


# --- Facebook süpürgesi ---------------------------------------------------

def test_facebook_supurgesi_dj_ve_derlemeyi_de_goruyor(tmp_path, monkeypatch):
    kokler = _katalog(tmp_path)
    monkeypatch.setattr(F, "BASE", _kok_demeti(kokler))
    _proje(kokler["projects"], "Son Kez",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-01"})
    _proje(kokler["dj_sets"], "Night Drive",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-02"})
    _proje(kokler["derlemeler"], "Gece Seansi Vol. 2",
           {"youtube_video_id": "v3", "youtube_uploaded_at": "2026-09-03"})

    adlar = [os.path.basename(p) for p in F.eksik_projeler()]
    assert adlar == ["Son Kez", "Night Drive", "Gece Seansi Vol. 2"]


def test_facebook_supurgesi_telif_ve_liste_disini_atliyor(tmp_path, monkeypatch):
    """Kapsam genişleyince TEORİK olmaktan çıkan iki kapı.

    City Pulse Set gerçekten `telif_araliklari` taşıyor (Content ID eşleşmesi),
    "Küllerimden Geç" gerçekten `unlisted`. İkisini de Facebook'a taşımak,
    uyumluluk.kontrol()'ün engellediği şeyin süpürge üzerinden yapılması olurdu.
    """
    kokler = _katalog(tmp_path)
    monkeypatch.setattr(F, "BASE", _kok_demeti(kokler))
    _proje(kokler["dj_sets"], "City Pulse Set",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-01",
            "telif_araliklari": [[0, 12]], "telif_eser": "Bring Me To Life"})
    _proje(kokler["projects"], "Kullerimden Gec",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-02",
            "youtube_privacy": "unlisted"})
    _proje(kokler["projects"], "Son Kez",
           {"youtube_video_id": "v3", "youtube_uploaded_at": "2026-09-03"})

    assert [os.path.basename(p) for p in F.eksik_projeler()] == ["Son Kez"]


def test_facebook_gunluk_sayaci_uc_kokten_sayiyor(tmp_path, monkeypatch):
    """Tavan, o gün DJ/derleme hattından çıkan paylaşımı da saymalı."""
    kokler = _katalog(tmp_path)
    monkeypatch.setattr(F, "BASE", _kok_demeti(kokler))
    bugun = time.strftime("%Y-%m-%dT%H:%M:%S")
    _proje(kokler["derlemeler"], "Gece Seansi Vol. 1",
           {"youtube_video_id": "v1", "facebook_reels_id": "1",
            "facebook_uploaded_at": bugun})
    _proje(kokler["dj_sets"], "Just Relax",
           {"youtube_video_id": "v2", "facebook_reels_id": "2",
            "facebook_uploaded_at": bugun})

    assert F.bugun_yuklenen() == 2      # eskiden 0 — tavan hiç dolmuyordu


# --- Telegram / Bluesky süpürgesi ----------------------------------------

def _ek_kur(tmp_path, monkeypatch):
    kokler = _katalog(tmp_path)
    monkeypatch.setattr(E, "BASE", _kok_demeti(kokler))
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR",
                        {"facebook": True, "telegram": True, "bluesky": True})
    # Kimlik dosyaları GERÇEK upload/ klasörüne BAKMASIN (orada gerçek token'lar
    # duruyor) — sahte bir klasör yeterli.
    sahte = tmp_path / "sahte_upload"
    sahte.mkdir()
    for p in E.PLATFORMLAR:
        (sahte / p[5]).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(E, "UPLOAD_DIR", str(sahte))
    return kokler


def test_telegram_dj_varyanti_dikey_dosyayi_ve_shorts_anahtarini_kullaniyor(
        tmp_path, monkeypatch):
    """DJ/derleme köklerinde Telegram'ın varyantı `kind="dikey"` olmalı."""
    _ek_kur(tmp_path, monkeypatch)
    telegram = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]

    varyantlar = {os.path.basename(k): v
                  for v in E._varyantlar(telegram) for k in v["kokler"]}
    assert varyantlar["projects"]["anahtar"] == "telegram_message_id"
    assert varyantlar["projects"]["gerekli_video"].endswith("youtube_16x9.mp4")
    for ad in ("dj_sets", "derlemeler"):
        assert varyantlar[ad]["anahtar"] == "telegram_shorts_message_id"
        assert varyantlar[ad]["gerekli_video"].endswith("shorts_9x16.mp4")
        assert varyantlar[ad]["ek"] == {"kind": "dikey"}


def test_dikey_gonderilmis_set_tekrar_aday_olmuyor(tmp_path, monkeypatch):
    """ASIL REGRESYON: naif genişletme burada bitmeyen bir tıkaç üretirdi.

    Diskteki üç set/derlemenin hepsinde `telegram_shorts_message_id` DOLU ama
    `telegram_message_id` YOK. Varsayılan varyantla bakılsaydı üçü de "eksik"
    sayılır, her koşuda 130-540 MB'lık 16:9 dosyayı yüklemeye çalışır ve tek
    günlük slotu kalıcı olarak yakardı.
    """
    kokler = _ek_kur(tmp_path, monkeypatch)
    _proje(kokler["dj_sets"], "City Pulse Set",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-01",
            "telegram_shorts_message_id": 6, "bluesky_post_uri": "at://x"})
    _proje(kokler["derlemeler"], "Gece Seansi Vol. 1",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-02",
            "telegram_shorts_message_id": 7, "bluesky_post_uri": "at://y"})

    telegram = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]
    assert E.adaylar(telegram) == []

    s = E.backfill(dry_run=True)
    assert s["islenen"] == [], s


def test_yarim_kalmis_set_supurgeye_takiliyor(tmp_path, monkeypatch):
    """Kapsam genişletmesinin ASIL kazancı: yarım kalan set tamamlanıyor."""
    kokler = _ek_kur(tmp_path, monkeypatch)
    _proje(kokler["dj_sets"], "Night Drive",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-05"})

    s = E.backfill(dry_run=True)
    assert sorted((x["platform"], x["proje"]) for x in s["islenen"]) == [
        ("Bluesky", "Night Drive"), ("Telegram", "Night Drive")]

    telegram = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]
    (proje, varyant), = E.adaylar(telegram)
    assert os.path.basename(proje) == "Night Drive"
    assert varyant["ek"] == {"kind": "dikey"}       # 16:9 DEĞİL, dikey kesit


def test_boyutu_asan_aday_eleniyor_ve_sebebi_loglaniyor(tmp_path, monkeypatch):
    """Yüklenemeyecek bir aday kuyruğun başında oturup slotu yakmamalı.

    Elenmesi SESSİZ de olmamalı: gidecek başka aday yokken sebebi log'a düşer
    ("tıkandı" ile "iş bitti" aynı şey değil).
    """
    kokler = _ek_kur(tmp_path, monkeypatch)
    tg = list([p for p in E.PLATFORMLAR if p[0] == "telegram"][0])
    tg[9] = 16                                  # sahte "50 MB" sınırı: 16 bayt
    monkeypatch.setattr(E, "PLATFORMLAR", [tuple(tg)])
    _proje(kokler["projects"], "Kocaman Sarki",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-01"},
           boyut=64)

    gerekli = os.path.join("output", "youtube_16x9.mp4")
    assert E.eksik_projeler("telegram_message_id", gerekli, 16) == []
    assert E.boyutu_asanlar("telegram_message_id", gerekli, 16) == ["Kocaman Sarki"]

    satirlar = []
    s = E.backfill(dry_run=True, log=satirlar.append)
    assert s["islenen"] == []
    assert s["atlanan"]["Telegram"] == ["Kocaman Sarki"]
    assert any("boyut" in x and "Kocaman Sarki" in x for x in satirlar), satirlar


def test_telegram_gunluk_tavani_iki_damgayi_birden_sayiyor(tmp_path, monkeypatch):
    """Ana katalog ve DJ kökü FARKLI damga yazıyor; tavan ikisini de saymalı."""
    kokler = _ek_kur(tmp_path, monkeypatch)
    bugun = time.strftime("%Y-%m-%dT%H:%M:%S")
    _proje(kokler["dj_sets"], "Just Relax",
           {"youtube_video_id": "v1", "telegram_shorts_message_id": 6,
            "telegram_shorts_uploaded_at": bugun, "bluesky_post_uri": "at://x"})
    _proje(kokler["projects"], "Son Kez",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-01"})

    telegram = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]
    assert E.bugun_yuklenen(E._damga_anahtarlari(telegram)) == 1

    # Tavan (1) o gün DJ hattından çıkan gönderiyle DOLDU: "Son Kez" bugün
    # gitmemeli, yarın gitmeli.
    s = E.backfill(dry_run=True)
    assert [x["proje"] for x in s["islenen"] if x["platform"] == "Telegram"] == []
    assert "Telegram" in s["tavan"]
    assert s["kalan"]["Telegram"] == 1
