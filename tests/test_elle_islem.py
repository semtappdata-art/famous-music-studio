# -*- coding: utf-8 -*-
"""Elle işlemler defteri (`elle_islem.py`) ve bağlantıları — 2026-09-13.

KULLANICI İSTEĞİ: "Otomasyon verilerine elle yapılan tüm işlemleri de dahil et."

Kilitlenenler:
  (a) Sözleşme biçimi (alanlar, id, +03:00), sözlük dışı RED (hiçbir şey yazılmaz).
  (b) Tekrar koruması (platform, proje, islem, ±10 dk) ve eşzamanlı ekleme
      (iki süreç + thread'ler) — satır bozulmaz, aynı olay bir kez yazılır.
  (c) Bozuk satıra dayanıklı okuma; yarım satırdan sonra ekleme yapışmaz.
  (d) TikTok eşlemesi MEVCUT `isaretle_yayinlandi`yi çağırır; `hazir=False` RED.
  (e) YouTube eşlemesi `youtube_privacy` / `*_privacy_gercek`e DOKUNMAZ.
  (f) backfill KURU hiçbir dosyaya yazmaz; --uygula state'e yazmaz, tekrarlamaz.
  (g) Günlük raporda bölüm yalnız DOLUYKEN; en fazla 8 satır + "+N daha".
  (h) `tiktok_yayin_onayi` defter hatasında DÜŞMEZ; başarıda telegram satırı yazar.
  (i) CLI cp1254 konsolda çökmez.
  (j) Test sırasında GERÇEK deftere yazılamaz (conftest'e dokunmadan).
  (k) Sağlık adımı bozuk satırda UYARI verir; Hermes becerisi dar kalır.

Ağ yok (socket.connect patlatılıyor), gerçek bildirim yok (notify.send taklit).
"""

import datetime
import inspect
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD, os.path.dirname(os.path.abspath(__file__))):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import elle_islem as EI                                  # noqa: E402
import tiktok_publish_plan as TPP                        # noqa: E402
import uyumluluk                                         # noqa: E402
# TOPLAMA anında import: conftest yalnız o an sys.modules'te olan modüllerin
# DURUM_DOSYASI/LOG_PATH yollarını geçici klasöre çekiyor. Test gövdesinde ilk kez
# import edilseydi `saglik_kontrol._bildir` GERÇEK upload/saglik_durum.json'a yazardı.
import saglik_kontrol                                    # noqa: E402,F401
import tiktok_yayin_onayi                                # noqa: E402,F401
import weekly_report                                     # noqa: E402,F401

BETIK = os.path.join(_REPO, "elle_islem.py")
SKILL_DIR = Path(_REPO) / ".hermes" / "skills" / "elle-islem-kaydi"
TZ = datetime.timezone(datetime.timedelta(hours=3))


# --------------------------------------------------------------------------
# Fikstürler
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    import socket

    def _yasak(*a, **k):
        raise AssertionError("elle işlem testi ağa çıktı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)


@pytest.fixture
def defter(tmp_path, monkeypatch):
    yol = tmp_path / "defter" / "elle_islemler.jsonl"
    monkeypatch.setenv(EI.ORTAM_DEGISKENI, str(yol))
    return yol


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


def _proje(kok, klasor, durum=None):
    p = kok / klasor
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": klasor, "theme": "pop"}, ensure_ascii=False),
                                 encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + klasor).encode("utf-8"))
    (p / "output").mkdir(exist_ok=True)
    (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    return str(p)


def _state(p):
    with open(os.path.join(p, "state.json"), encoding="utf-8") as f:
        return json.load(f)


def _satirlar(yol):
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f.read().split(chr(10)) if s.strip()]


def _iso(t):
    return datetime.datetime.fromtimestamp(t, TZ).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# (a) Biçim ve doğrulama
# --------------------------------------------------------------------------

def test_satir_bicimi_sozlesmeye_uyuyor(defter, kok):
    _proje(kok, "Sabah Senin")
    s = EI.ekle("instagram", "arsivledi", "Kopya Reels telefondan arşivlendi",
                proje="projects/Sabah Senin", zaman="2026-09-12T21:15", kanit="Dc5vAXxgGIf")
    assert s["durum"] == "eklendi"
    [k] = _satirlar(defter)
    assert set(k) == {"id", "zaman", "zaman_yaklasik", "kayit_zamani", "platform", "proje",
                      "islem", "ayrinti", "kaynak", "kanit", "state_etkisi"}
    assert re.fullmatch(r"EI-\d{8}-\d{6}-[0-9a-f]{4}", k["id"])
    assert k["zaman"] == "2026-09-12T21:15:00+03:00"
    assert k["kayit_zamani"].endswith("+03:00")
    assert k["zaman_yaklasik"] is False
    assert k["proje"] == "Sabah Senin"            # klasör ADI, yol değil
    assert k["kaynak"] == "cli" and k["kanit"] == "Dc5vAXxgGIf"
    assert k["state_etkisi"] is None               # instagram: yalnız defter


def test_yalniz_tarih_yaklasik_isaretlenir(defter):
    EI.ekle("suno", "uretti", "Sabah Senin iki varyant üretildi", zaman="2026-09-12")
    [k] = _satirlar(defter)
    assert k["zaman_yaklasik"] is True
    assert k["zaman"].startswith("2026-09-12T")


@pytest.mark.parametrize("kw, parca", [
    (dict(platform="tiktok", islem="begendi", ayrinti="x"), "sözlük dışı"),
    (dict(platform="myspace", islem="diger", ayrinti="x"), "platform"),
    (dict(platform="diger", islem="diger", ayrinti="  "), "ayrinti"),
    (dict(platform="diger", islem="diger", ayrinti="x", kaynak="sms"), "kaynak"),
    (dict(platform="diger", islem="diger", ayrinti="x", proje="Olmayan Şarkı"), "proje"),
    (dict(platform="diger", islem="diger", ayrinti="x", zaman="dün akşam"), "zaman"),
    (dict(platform="diger", islem="diger", ayrinti="x", zaman="2099-01-01T10:00"), "gelecek"),
])
def test_gecersiz_girdi_reddedilir_ve_hicbir_sey_yazilmaz(defter, kok, kw, parca):
    with pytest.raises(EI.ElleIslemHatasi) as e:
        EI.ekle(**kw)
    assert parca in str(e.value)
    assert not defter.exists()


# --------------------------------------------------------------------------
# (b) Tekrar koruması ve eşzamanlılık
# --------------------------------------------------------------------------

def test_tekrar_korumasi_on_dakika(defter, kok):
    _proje(kok, "Son Kez")
    a = EI.ekle("youtube", "kapak_degistirdi", "Studio'dan kapak", proje="Son Kez",
                zaman="2026-09-12T10:00")
    b = EI.ekle("youtube", "kapak_degistirdi", "aynı iş, ikinci söyleyiş", proje="Son Kez",
                zaman="2026-09-12T10:09")
    assert a["durum"] == "eklendi" and b["durum"] == "zaten_kayitli"
    assert b["kayit"]["id"] == a["kayit"]["id"]
    assert EI.ekle("youtube", "kapak_degistirdi", "ertesi", proje="Son Kez",
                   zaman="2026-09-12T10:11")["durum"] == "eklendi"
    assert EI.ekle("youtube", "kapak_degistirdi", "proje yok", proje=None,
                   zaman="2026-09-12T10:00")["durum"] == "eklendi"
    assert len(_satirlar(defter)) == 3


def test_iki_surec_ayni_anda_yaziyor_satir_bozulmuyor(defter):
    kod = ("import sys; sys.path.insert(0, sys.argv[1]); import elle_islem as E; "
           "P = int(sys.argv[2]); "
           "[E.ekle('diger', 'diger', 'surec %d satir %d' % (P, i), "
           "zaman='2026-09-%02dT%02d:00:00' % (P, i % 24)) for i in range(24)]; "
           "E.ekle('tiktok', 'yayinladi', 'ayni olay surec %d' % P, zaman='2026-09-05T10:00:00')")
    ortam = dict(os.environ, **{EI.ORTAM_DEGISKENI: str(defter)})
    surecler = [subprocess.Popen([sys.executable, "-c", kod, _REPO, str(p)], env=ortam,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                for p in (1, 2)]
    for s in surecler:
        _, hata = s.communicate(timeout=120)
        assert s.returncode == 0, hata.decode("utf-8", "replace")
    kayitlar, bozuk = EI.oku(str(defter))
    assert bozuk == []
    assert len([k for k in kayitlar if k["islem"] == "diger"]) == 48
    assert len([k for k in kayitlar if k["islem"] == "yayinladi"]) == 1
    assert len({k["id"] for k in kayitlar}) == len(kayitlar)
    assert not os.path.exists(str(defter) + ".kilit")


def test_threadler_ayni_anda_yaziyor(defter):
    hatalar = []

    def _yaz(n):
        try:
            for i in range(15):
                EI.ekle("site", "duzenledi", "thread %d/%d" % (n, i),
                        zaman="2026-08-%02dT%02d:00:00" % (n + 1, i))
        except Exception as e:                            # noqa: BLE001
            hatalar.append(e)

    th = [threading.Thread(target=_yaz, args=(n,)) for n in range(4)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    assert hatalar == []
    kayitlar, bozuk = EI.oku()
    assert len(kayitlar) == 60 and bozuk == []


# --------------------------------------------------------------------------
# (c) Bozuk satır
# --------------------------------------------------------------------------

def test_bozuk_satira_dayanikli_okuma_ve_yarim_satira_yapismama(defter):
    EI.ekle("diger", "diger", "sağlam", zaman="2026-09-10T10:00")
    with open(defter, "ab") as f:
        f.write(b"bu json degil" + bytes([10]))
        f.write(json.dumps({"id": "EI-x", "zaman": "2026-09-10T11:00:00+03:00",
                            "platform": "tiktok", "islem": "uydurma", "kaynak": "cli"}).encode() + bytes([10]))
        f.write(b'{"id": "EI-yarim", "zam')               # yarım kalmış yazım, satır sonu yok
    kayitlar, bozuk = EI.oku()
    assert len(kayitlar) == 1
    assert len(bozuk) == 3
    assert any("sözlük dışı" in b["hata"] for b in bozuk)
    EI.ekle("diger", "diger", "sonra eklenen", zaman="2026-09-10T12:00")
    kayitlar, bozuk = EI.oku()
    assert [k["ayrinti"] for k in kayitlar] == ["sağlam", "sonra eklenen"]
    assert len(bozuk) == 3
    assert EI.listele(gun=10000)[0]["ayrinti"] == "sonra eklenen"
    assert EI.saglik_durumu()["durum"] == "bozuk"


# --------------------------------------------------------------------------
# (d) TikTok eşlemesi
# --------------------------------------------------------------------------

def test_tiktok_yayinladi_mevcut_isaretleme_yolunu_cagirir(defter, kok, monkeypatch):
    p = _proje(kok, "Sabah Senin", {"tiktok_publish_id": "v_inbox_file~v2.1"})
    cagri = []
    gercek = TPP.isaretle_yayinlandi

    def _sarmal(proje, *a, **k):
        cagri.append((proje, k))
        return gercek(proje, *a, **k)

    monkeypatch.setattr(TPP, "isaretle_yayinlandi", _sarmal)
    s = EI.ekle("tiktok", "yayinladi", "telefondan yayınladım", proje="Sabah Senin",
                zaman="2026-09-12T12:30")
    assert s["durum"] == "eklendi", s
    assert len(cagri) == 1 and cagri[0][0] == p
    assert cagri[0][1]["zaman"] == "2026-09-12T12:30:00"
    assert cagri[0][1]["kaynak"].startswith("Elle işlemler defteri (cli, EI-")
    st = _state(p)
    assert st["tiktok_published_at"] == "2026-09-12T12:30:00"
    assert "tiktok_dogrulandi" not in st
    [k] = _satirlar(defter)
    assert k["state_etkisi"] == "tiktok_published_at, tiktok_published_kaynak"


def test_tiktok_hazir_false_reddi_korunur(defter, kok):
    p = _proje(kok, "Bu Gece Kazandık", {
        "tiktok_publish_id": "v~9",
        "yayin_beklet": {"sebep": "kullanıcı: yeniden render", "istendi_at": "2026-09-12T22:56:32+03:00"}})
    assert TPP.build_plan(p)["hazir"] is False
    with pytest.raises(EI.ElleIslemHatasi) as e:
        EI.ekle("tiktok", "yayinladi", "yayınladım", proje="Bu Gece Kazandık")
    assert "REDDEDİLDİ" in str(e.value)
    assert "tiktok_published_at" not in _state(p)
    assert not defter.exists()


# --------------------------------------------------------------------------
# (e) YouTube eşlemesi
# --------------------------------------------------------------------------

@pytest.mark.parametrize("platform, onek", [("youtube", "youtube"),
                                            ("youtube_shorts", "youtube_shorts")])
def test_youtube_gizlilik_privacy_alanlarina_dokunmaz(defter, kok, platform, onek):
    once = {onek + "_video_id": "abcdefghijk", onek + "_privacy": "public",
            onek + "_privacy_gercek": "public", "kopya_notu": "x"}
    p = _proje(kok, "Yeniden Doğacağım", once)
    s = EI.ekle(platform, "liste_disi_yapti", "Studio'dan liste dışı yaptım",
                proje="Yeniden Doğacağım", zaman="2026-09-12T19:00", zaman_yaklasik=True)
    st = _state(p)
    for alan, deger in once.items():
        assert st[alan] == deger, alan
    not_ = st[onek + "_elle_gizlilik_notu"]
    assert not_["deger"] == "unlisted" and not_["video_id"] == "abcdefghijk"
    assert not_["kayit_id"] == s["kayit"]["id"] and not_["zaman_yaklasik"] is True
    assert _satirlar(defter)[0]["state_etkisi"] == onek + "_elle_gizlilik_notu"


def test_youtube_gizlilik_hedefi_ayrintidan_ya_da_parametreden(defter, kok):
    p = _proje(kok, "Son Kez", {"youtube_video_id": "v1", "youtube_privacy": "unlisted"})
    EI.ekle("youtube", "gizlilik_degistirdi", "Studio'dan herkese açık yaptım", proje="Son Kez",
            zaman="2026-09-12T10:00")
    assert _state(p)["youtube_elle_gizlilik_notu"]["deger"] == "public"
    assert _state(p)["youtube_privacy"] == "unlisted"
    EI.ekle("youtube", "gizlilik_degistirdi", "değiştirdim", proje="Son Kez",
            zaman="2026-09-12T12:00", gizlilik="private")
    assert _state(p)["youtube_elle_gizlilik_notu"]["deger"] == "private"


def test_diger_islemler_state_yazmaz(defter, kok):
    p = _proje(kok, "Son Kez", {"youtube_video_id": "v1"})
    once = (Path(p) / "state.json").read_bytes()
    EI.ekle("youtube", "oynatma_listesi", "listeden çıkardım", proje="Son Kez")
    EI.ekle("diger", "bekletmeye_aldi", "beklet", proje="Son Kez", zaman="2026-09-12T10:00")
    assert (Path(p) / "state.json").read_bytes() == once


# --------------------------------------------------------------------------
# (f) backfill
# --------------------------------------------------------------------------

def _backfill_ortami(tmp_path, kok):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text(
        "Kullanıcı `Yeniden Doğacağım` videosunda kapak eksikliği olduğu için onu liste dışı yaptı.\n"
        "kullanıcı telefondan arşivleyecek\n", encoding="utf-8")
    (repo / "buyume_kontrol_listesi.md").write_text("- [x] bir iş\n", encoding="utf-8")
    (repo / "tiktok_envanteri_2026-09-12.md").write_text(
        "| 9 | 5 Eyl 19:36 | başlık | Gece Sürüşü (kesin: başlık) | Herkes | 1 | 1 | 0 | 0:30 | "
        "https://www.tiktok.com/@x/video/7682090856102300949 |\n"
        "| 10 | 5 Eyl 15:35 | #tag | belirsiz | Herkes | 1 | 1 | 0 | 0:45 | "
        "https://www.tiktok.com/@x/video/7682028949559348500 |\n", encoding="utf-8")
    _proje(kok, "Gece Sürüşü", {"tiktok_publish_id": "v~1", "tiktok_published_at": "2026-09-05T19:36:05"})
    _proje(kok, "Kırık Zincir", {"tiktok_publish_id": "v~2", "tiktok_published_at": "2026-09-13T02:23:10",
                                 "tiktok_published_kaynak": "TikTok API PUBLISH_COMPLETE (otomatik)"})
    _proje(kok, "Yeniden Doğacağım", {
        "kopya_notu": "Kullanıcı 2026-09-12 akşamı uzun formatı (kZML9g4GdBs) Studio'dan liste dışına "
                      "aldı; Shorts (Y6eK2nIBXqA) 2026-09-12 22:40'ta API ile unlisted yapıldı."})
    return repo


def _anlik_goruntu(*kokler):
    sonuc = {}
    for k in kokler:
        for yol in Path(k).rglob("*"):
            if yol.is_file():
                sonuc[str(yol)] = (yol.read_bytes(), yol.stat().st_mtime_ns)
    return sonuc


def test_backfill_kuru_hicbir_sey_yazmaz_uygula_yalniz_deftere(defter, kok, tmp_path):
    repo = _backfill_ortami(tmp_path, kok)
    once = _anlik_goruntu(repo, kok)
    s = EI.backfill(yol=str(defter), repo=str(repo))
    assert s["kuru"] is True and s["yazilan"] == 0
    assert _anlik_goruntu(repo, kok) == once
    assert not defter.exists()

    ozet = {(a["platform"], a["proje"], a["islem"]) for a in s["adaylar"]}
    assert ozet == {("tiktok", "Gece Sürüşü", "yayinladi"),
                    ("youtube", "Yeniden Doğacağım", "liste_disi_yapti")}
    # İki kaynak (kopya_notu + CLAUDE.md) aynı olay -> TEK aday.
    [yd] = [a for a in s["adaylar"] if a["proje"] == "Yeniden Doğacağım"]
    assert "kopya_notu" in yd["dayanak"] and "CLAUDE.md" in yd["dayanak"]
    assert yd["zaman"] == "2026-09-12T19:00:00+03:00" and yd["zaman_yaklasik"] is True
    # Otomasyon damgası deftere girmez; "API ile" belirsiz.
    assert any("Kırık Zincir" in x["dayanak"] for x in s["otomasyon_atlandi"])
    assert any("API ile" in x["metin"] for x in s["belirsiz"])
    assert not any(a["proje"] == "Kırık Zincir" for a in s["adaylar"])

    s2 = EI.backfill(uygula=True, yol=str(defter), repo=str(repo))
    assert s2["yazilan"] == 2
    assert {k["kaynak"] for k in _satirlar(defter)} == {"backfill"}
    assert all(k["state_etkisi"] is None for k in _satirlar(defter))
    sonra = _anlik_goruntu(repo, kok)
    assert sonra == once, "backfill --uygula state'e / kaynaklara yazmamalı"
    s3 = EI.backfill(uygula=True, yol=str(defter), repo=str(repo))
    assert s3["yazilan"] == 0 and len(s3["zaten_kayitli"]) == 2
    assert len(_satirlar(defter)) == 2


# --------------------------------------------------------------------------
# (g) Günlük / haftalık rapor
# --------------------------------------------------------------------------

def test_gunluk_raporda_bolum_yalniz_doluyken(defter, tmp_path, monkeypatch):
    import weekly_report as wr
    from test_gunluk_izlenme import Katalog, GUN, _an

    katalog = Katalog(tmp_path, monkeypatch)
    katalog.ekle("Son Kez", uzun=317, uzun_prev=316)
    t = _an(*GUN, 10)
    durum = str(tmp_path / "saglik_durum.json")

    def _metin():
        s = wr.gunluk_izlenme_raporu(log=lambda *a, **k: None, durum_dosyasi=durum,
                                     gonder=False, simdi=t)
        assert s["durum"] == "uretildi", s
        return s["metin"]

    assert "elle yapılanlar" not in _metin().lower()

    EI.ekle("diger", "diger", "eski iş", zaman=_iso(t - 30 * 3600), simdi=t)
    assert "elle yapılanlar" not in _metin().lower(), "24 saatten eski kayıt bölümü açmamalı"

    for i in range(10):
        EI.ekle("instagram", "arsivledi", "arşiv %d" % i, zaman=_iso(t - (i + 1) * 1200), simdi=t)
    metin = _metin()
    assert "Son 24 saatte elle yapılanlar (10)" in metin
    bolum = metin.split("Son 24 saatte elle yapılanlar", 1)[1].split(chr(10))[1:]
    satirlar = [s for s in bolum if s.strip()]
    assert len(satirlar) == 9 and satirlar[-1].strip() == "+2 daha"
    assert "arşiv 0" in satirlar[0]                      # en yeni önce
    metin.encode("cp1254")


def test_gunluk_raporda_api_dogrulanan_tiktok_elle_yayin_olarak_gorunur(defter, tmp_path, monkeypatch):
    import weekly_report as wr
    from test_gunluk_izlenme import Katalog, GUN, _an

    t = _an(*GUN, 10)
    katalog = Katalog(tmp_path, monkeypatch)
    katalog.ekle("Kırık Zincir", uzun=10, uzun_prev=9, tiktok_publish_status="PUBLISH_COMPLETE",
                 tiktok_published_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t - 3600)),
                 tiktok_published_kaynak="TikTok API PUBLISH_COMPLETE (otomatik), yaklaşık")
    s = wr.gunluk_izlenme_raporu(log=lambda *a, **k: None, durum_dosyasi=str(tmp_path / "d.json"),
                                 gonder=False, simdi=t)
    assert "Kırık Zincir: elle yayınlandı (API ile doğrulandı)" in s["metin"]
    assert not defter.exists(), "otomatik doğrulama deftere YAZMAZ"


def test_haftalik_ozette_elle_islem_sayisi_ve_platform_kirilimi(defter, kok, monkeypatch):
    import weekly_report as wr
    t = time.time()
    EI.ekle("tiktok", "diger", "a", zaman=_iso(t - 3600), simdi=t)
    EI.ekle("tiktok", "diger", "b", zaman=_iso(t - 7200), simdi=t)
    EI.ekle("youtube", "kapak_degistirdi", "c", zaman=_iso(t - 3 * 86400), simdi=t)
    EI.ekle("youtube", "kapak_degistirdi", "eski", zaman=_iso(t - 9 * 86400), simdi=t)
    satir = wr._elle_islem_haftalik_satiri(t)
    assert satir == "Bu hafta elle yapılanlar: 3 (TikTok 2, YouTube 1)"
    assert "_elle_islem_haftalik_satiri" in inspect.getsource(wr._haftalik_satirlar)


# --------------------------------------------------------------------------
# (h) Telegram onayı
# --------------------------------------------------------------------------

def test_telegram_onayi_basarida_deftere_telegram_satiri_yazar(defter, kok):
    import tiktok_yayin_onayi as ONAY
    _proje(kok, "Sabah Senin", {"tiktok_publish_id": "v_inbox_file~v2.1"})
    kod, metin = ONAY.onayla("Sabah Senin", zaman="2026-09-12T12:00:00")
    assert kod == 0, metin
    [k] = _satirlar(defter)
    assert (k["platform"], k["proje"], k["islem"], k["kaynak"]) == (
        "tiktok", "Sabah Senin", "yayinladi", "telegram")
    assert k["zaman"] == "2026-09-12T12:00:00+03:00"
    assert k["state_etkisi"] == "tiktok_published_at, tiktok_published_kaynak"


def test_telegram_onayi_defter_hatasinda_dusmez(defter, kok, monkeypatch, capsys):
    import tiktok_yayin_onayi as ONAY
    p = _proje(kok, "Sabah Senin", {"tiktok_publish_id": "v_inbox_file~v2.1"})

    def _patla(*a, **k):
        raise RuntimeError("disk dolu")

    monkeypatch.setattr(EI, "ekle", _patla)
    kod, metin = ONAY.onayla("Sabah Senin")
    assert kod == 0 and metin.startswith("TAMAM"), metin
    assert _state(p)["tiktok_published_at"]
    assert "defter" in capsys.readouterr().err.lower()


def test_telegram_onayi_reddinde_deftere_yazilmaz(defter, kok):
    import tiktok_yayin_onayi as ONAY
    _proje(kok, "Bu Gece Kazandık", {"tiktok_publish_id": "v~9",
                                     "yayin_beklet": {"sebep": "x", "istendi_at": "2026-09-12T22:00:00"}})
    kod, _ = ONAY.onayla("Bu Gece Kazandık")
    assert kod == 2 and not defter.exists()


# --------------------------------------------------------------------------
# (i) CLI / cp1254
# --------------------------------------------------------------------------

def _cli(defter, *argv):
    ortam = dict(os.environ, PYTHONIOENCODING="cp1254", **{EI.ORTAM_DEGISKENI: str(defter)})
    return subprocess.run([sys.executable, BETIK] + list(argv), env=ortam,
                          capture_output=True, timeout=120)


def test_cli_cp1254_konsolda_cokmez(defter):
    r = _cli(defter, "ekle", "--platform", "diger", "--islem", "diger",
             "--ayrinti", "Şarkı düzenlendi \U0001F525 ığüşöç", "--zaman", "2026-09-13T01:00")
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    for argv in (("listele", "--gun", "3650"), ("ozet", "--gun", "3650", "--json"),
                 ("sozluk",), ("listele", "--gun", "3650", "--json")):
        r = _cli(defter, *argv)
        assert r.returncode == 0, (argv, r.stderr.decode("utf-8", "replace"))
        assert b"Traceback" not in r.stderr
    assert "\U0001F525" in _cli(defter, "listele", "--gun", "3650").stdout.decode("utf-8")
    r = _cli(defter, "ekle", "--platform", "diger", "--islem", "uydurma", "--ayrinti", "x")
    assert r.returncode == 2 and "HATA" in r.stdout.decode("utf-8")
    assert len(_satirlar(defter)) == 1


# --------------------------------------------------------------------------
# (j) Gerçek deftere dokunulmaz
# --------------------------------------------------------------------------

def test_testte_gercek_deftere_yazilamaz(monkeypatch):
    monkeypatch.delenv(EI.ORTAM_DEGISKENI, raising=False)
    gercek = EI.GERCEK_DEFTER_YOLU
    assert EI.defter_yolu() == gercek
    once = os.stat(gercek).st_mtime_ns if os.path.exists(gercek) else None
    with pytest.raises(EI.ElleIslemHatasi) as e:
        EI.ekle("diger", "diger", "test sızıntısı")
    assert "test" in str(e.value)
    sonra = os.stat(gercek).st_mtime_ns if os.path.exists(gercek) else None
    assert once == sonra
    assert EI.oku() == ([], [])


# --------------------------------------------------------------------------
# (k) Sağlık adımı ve Hermes becerisi
# --------------------------------------------------------------------------

def test_saglik_adimi_bozuk_satirda_uyari(defter, monkeypatch):
    import notify
    import saglik_kontrol as SK
    gonderilen = []
    monkeypatch.setattr(notify, "send", lambda b, m, *a, **k: (gonderilen.append(b), True)[1])

    log = []
    assert SK.elle_islemler_defteri(log=log.append)["durum"] == "yok"
    EI.ekle("diger", "diger", "sağlam", zaman="2026-09-10T10:00")
    assert SK.elle_islemler_defteri(log=log.append)["durum"] == "tamam"
    assert log == [] and gonderilen == []

    with open(defter, "ab") as f:
        f.write(b"{bozuk" + bytes([10]))
    s = SK.elle_islemler_defteri(log=log.append)
    assert s["durum"] == "bozuk" and s["bozuk_sayisi"] == 1
    assert any("UYARI" in x and "elle_islemler.jsonl" in x for x in log)
    assert len(gonderilen) == 1
    SK.elle_islemler_defteri(log=log.append)
    assert len(gonderilen) == 1, "günde bir bildirim"
    assert "elle_islemler" in SK.kontrol_et.__code__.co_names or \
        "elle_islemler_defteri" in inspect.getsource(SK.kontrol_et)


def _skill_metni():
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_hermes_becerisi_frontmatter_ve_tetikleyiciler():
    from test_hermes_skill import _frontmatter
    ham = (SKILL_DIR / "SKILL.md").read_bytes()
    assert bytes([13, 10]) not in ham
    fm = _frontmatter(_skill_metni())
    assert fm.get("name") == SKILL_DIR.name
    assert fm.get("description") and len(fm["description"]) <= 60
    assert fm["description"].endswith(".")
    metin = _skill_metni()
    for tetik in ("elle yaptım", "Studio'dan", "arşivledim", "sildim", "liste dışı yaptım"):
        assert re.search(r"(?m)^\s+-\s+.*" + re.escape(tetik), metin), tetik


def test_hermes_becerisi_tek_mutlak_ekle_komutu_ve_onay():
    metin = _skill_metni()
    komutlar = re.findall(r"(?m)^\s*python\s+\S+.*$", metin)
    assert komutlar
    for k in komutlar:
        assert "C:/Users/ACER/Desktop/ilk-projem/elle_islem.py" in k, k
        assert re.search(r"elle_islem\.py (ekle|sozluk)\b", k), k
    assert any(" ekle " in k and "--kaynak telegram" in k for k in komutlar)
    assert "onay" in metin.lower()
    for sozcuk in list(EI.ISLEMLER)[:5]:
        assert sozcuk in metin
