# -*- coding: utf-8 -*-
"""Geri doldurma süpürgeleri POLİTİKA KAPISINDAN geçiyor mu?

NEDEN (2026-09-12 denetimi): `uyumluluk.kontrol()` bu deponun politika kapısı
ve İKİ aşamada otomatik çalışıyor — render'dan önce (`validate_project.py`) ve
yüklemeden önce (`auto_process.py` / `dj_famous_process.py`). Ama İKİ geri
doldurma süpürgesi (`upload/ek_platform_backfill.py`,
`upload/facebook_backfill.py`) o kapının DIŞINDAN yayın yapıyordu: ikisi de
`uyumluluk`u import ediyordu ama SADECE `KOKLER` / `proje_klasorleri()` için,
yani kök listesini almak için — `kontrol()` hiçbirinde çağrılmıyordu. Bu,
CLAUDE.md'deki "BAĞLANTI seviyesindeki sessiz arıza" sınıfının tam örneği:
fonksiyon doğru, import var, çağrı YOK.

Bedeli somut: süpürgeler TÜM kataloğu geziyor ve `_is_fully_done()`'dan geçmiş,
ana hattın bir daha DOKUNMADIĞI projeleri de yayınlıyor. Tek koruma
`youtube_privacy in ("unlisted","private")` satırıydı — o bir KOD KAPISI değil,
ELLE yapılmış bir YouTube ayarının yerel AYNASI. 'Küllerimden Geç' ('Yeniden
Doğacağım' ile aynı `audio.wav` md5'i) bugün sadece o ayna sayesinde duruyor;
biri onu public'e çekerse ya da alan bayatlarsa kopya Facebook, Telegram ve
Bluesky'a giderdi.

Testlerin kapsadığı beş gerçek senaryo:
  (a) `uyumluluk` HATA veren proje ATLANIYOR ve gönderilmiyor,
  (b) temiz proje normal gönderiliyor,
  (c) `kontrol()` istisna fırlatırsa FAIL-CLOSED (sessizce açılmıyor),
  (d) atlanan proje GÜNLÜK TAVANI tüketmiyor (tavan "kanal bugün kaç kez
      gönderdi"i sayar — atlanan bir proje gönderi DEĞİLDİR),
  (e) atlama SESSİZ değil ama log'u da boğmuyor (koşu başına tek satır).

HİÇBİR TESTTE gerçek yükleme/ağ yolu çalışmıyor: ya `dry_run=True`, ya doğrudan
saf fonksiyonlar. Kimlik dosyası kontrolü gerçek `upload/` klasörüne değil,
tmp'deki sahte bir klasöre bakıyor (gerçek token'lara dokunulmasın diye) ve
`notify.uyar_bir_kez` monkeypatch'li — gerçek bildirim gitmiyor.
"""

import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import config                                       # noqa: E402
import notify                                       # noqa: E402
import uyumluluk                                    # noqa: E402
import ek_platform_backfill as E                    # noqa: E402
import facebook_backfill as F                       # noqa: E402


# --- ortak kurulum --------------------------------------------------------

def _proje(kok_yolu, ad, durum, ses=None,
           videolar=("youtube_16x9.mp4", "shorts_9x16.mp4")):
    d = os.path.join(kok_yolu, ad)
    os.makedirs(os.path.join(d, "output"), exist_ok=True)
    for v in videolar:
        with open(os.path.join(d, "output", v), "wb") as f:
            f.write(b"x" * 8)
    if ses is not None:
        with open(os.path.join(d, "audio.wav"), "wb") as f:
            f.write(ses)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False)
    return d


def _kur(tmp_path, monkeypatch):
    """Tek kök (`projects/`) + iki süpürgenin de kapıları AÇIK hâli."""
    base = str(tmp_path / "projects")
    os.makedirs(base)
    monkeypatch.setattr(E, "BASE", base)
    monkeypatch.setattr(F, "BASE", base)
    # Golden-hour ve bayraklar bu testlerin konusu değil: hep "içerideyiz".
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(config, "EK_PLATFORMLAR",
                        {"facebook": True, "telegram": True, "bluesky": True})
    sahte = tmp_path / "sahte_upload"
    sahte.mkdir()
    for p in E.PLATFORMLAR:
        (sahte / p[5]).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(E, "UPLOAD_DIR", str(sahte))
    # Kapı önbelleği/uyarı seti PROCESS ömürlü (bir zamanlayıcı koşusu =
    # bir process). Testler birbirini kirletmesin diye her testte taze.
    monkeypatch.setattr(E, "_UYARILANLAR", set())
    monkeypatch.setattr(F, "_UYARILANLAR", set())
    E._KAPI_ONBELLEGI.clear()
    return base


def _log_yakala(monkeypatch):
    """`notify.uyar_bir_kez` GERÇEKTEN çağrılıyor mu — satırları toplar.

    Monkeypatch şart: gerçek uyar_bir_kez log dosyasına/stderr'e yazar, ve bu
    testlerin hiçbiri gerçek bildirim kanalına dokunmamalı.
    """
    satirlar = []
    monkeypatch.setattr(notify, "uyar_bir_kez",
                        lambda anahtar, mesaj: satirlar.append((anahtar, mesaj)))
    return satirlar


def _kontrol_sahte(monkeypatch, engelli_adlar, patlat=False):
    """`uyumluluk.kontrol`u davranışa göre taklit eder (ağa çıkmaz zaten).

    Gerçek kapının kendisi AYRICA test ediliyor (bkz. sondaki md5 testi); bu
    yardımcı, süpürgenin kapının cevabına NE YAPTIĞINI izole ediyor.
    """
    def sahte(proje, asama="render"):
        assert asama == "yukleme", "süpürge YÜKLEME aşamasını sormalı"
        if patlat:
            raise RuntimeError("kapı çöktü")
        if os.path.basename(os.path.normpath(proje)) in engelli_adlar:
            return (["telif eşleşmesi kayıtlı — yeniden yayınlanmamalı"], [])
        return ([], [])
    monkeypatch.setattr(uyumluluk, "kontrol", sahte)


# --- (a) HATA veren proje atlanıyor --------------------------------------

def test_ek_supurge_uyumluluk_hatasini_gondermiyor(tmp_path, monkeypatch):
    base = _kur(tmp_path, monkeypatch)
    satirlar = _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, {"Kirli"})
    _proje(base, "Kirli", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = E.backfill(dry_run=True)
    assert s["islenen"] == [], s
    assert [x["proje"] for x in s["engellenen"]["Telegram"]] == ["Kirli"]
    assert [x["proje"] for x in s["engellenen"]["Bluesky"]] == ["Kirli"]
    assert any("Kirli" in m and "ATLANDI" in m for _a, m in satirlar), satirlar


def test_facebook_supurgesi_uyumluluk_hatasini_gondermiyor(tmp_path, monkeypatch):
    base = _kur(tmp_path, monkeypatch)
    satirlar = _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, {"Kirli"})
    _proje(base, "Kirli", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = F.backfill(dry_run=True)
    assert s["islenen"] == [], s
    assert [x["proje"] for x in s["engellenen"]] == ["Kirli"]
    assert any("Kirli" in m and "ATLANDI" in m for _a, m in satirlar), satirlar


# --- (b) temiz proje normal gönderiliyor ---------------------------------

def test_temiz_proje_iki_supurgede_de_gonderiliyor(tmp_path, monkeypatch):
    base = _kur(tmp_path, monkeypatch)
    _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, set())
    _proje(base, "Temiz", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = E.backfill(dry_run=True)
    assert sorted((x["platform"], x["proje"]) for x in s["islenen"]) == [
        ("Bluesky", "Temiz"), ("Telegram", "Temiz")]
    assert "engellenen" not in s

    f = F.backfill(dry_run=True)
    assert f["islenen"] == ["Temiz"]
    assert "engellenen" not in f


# --- (c) kapı çökerse FAIL-CLOSED ----------------------------------------

def test_kapi_cokerse_fail_closed_ek_supurge(tmp_path, monkeypatch):
    """İstisna = "bilmiyorum". "Bilmiyorum" ile "temiz" aynı şey DEĞİL.

    Bu deponun ödediği bedel: `uyumluluk.KOKLER` göreli yolken `os.path.isdir`
    False dönüyordu, `kontrol()` hata=0 uyarı=0 diyordu ve kapı KENDİLİĞİNDEN
    AÇILIYORDU. Süpürge burada gönderiyi ERTELER; ertelenen gönderi geri
    alınabilir, yayınlanan kopya alınamaz.
    """
    base = _kur(tmp_path, monkeypatch)
    satirlar = _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, set(), patlat=True)
    _proje(base, "Temiz", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = E.backfill(dry_run=True)
    assert s["islenen"] == [], "kapı çöktüğünde gönderim OLMAMALI"
    sebep = s["engellenen"]["Telegram"][0]["sebep"]
    assert "ÇALIŞTIRILAMADI" in sebep and "RuntimeError" in sebep, sebep
    assert any("fail-closed" in m for _a, m in satirlar), satirlar


def test_kapi_cokerse_fail_closed_facebook(tmp_path, monkeypatch):
    base = _kur(tmp_path, monkeypatch)
    _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, set(), patlat=True)
    _proje(base, "Temiz", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = F.backfill(dry_run=True)
    assert s["islenen"] == [], "kapı çöktüğünde gönderim OLMAMALI"
    assert "ÇALIŞTIRILAMADI" in s["engellenen"][0]["sebep"]


# --- (d) atlanan proje kotayı/tavanı tüketmiyor --------------------------

def test_engellenen_proje_gunluk_tavani_tuketmiyor(tmp_path, monkeypatch):
    """Engelli proje kuyruğun BAŞINDA olsa bile sıradaki temiz proje gider.

    İKİ ayrı iddia:
      * bir projenin engeli diğerlerini BLOKLAMIYOR (koşu tavanı 1 olsa bile),
      * atlanan proje GÜNLÜK TAVANI tüketmiyor — tavan `*_uploaded_at`
        damgalarını sayıyor, atlanan projede damga oluşmuyor.
    """
    base = _kur(tmp_path, monkeypatch)
    _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, {"Kirli"})
    # "Kirli" DAHA ESKİ: sıralama eskiden yeniye, yani kuyruğun BAŞINDA.
    _proje(base, "Kirli", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})
    _proje(base, "Temiz", {"youtube_video_id": "v2",
                           "youtube_uploaded_at": "2026-09-02"})

    s = E.backfill(dry_run=True)
    assert [x["proje"] for x in s["islenen"]] == ["Temiz", "Temiz"], s
    assert [x["proje"] for x in s["engellenen"]["Telegram"]] == ["Kirli"]
    # Gönderi yapılmadığı için hiçbir damga yazılmadı: tavan sayacı 0.
    telegram = [p for p in E.PLATFORMLAR if p[0] == "telegram"][0]
    assert E.bugun_yuklenen(E._damga_anahtarlari(telegram)) == 0

    f = F.backfill(dry_run=True)
    assert f["islenen"] == ["Temiz"], f
    assert F.bugun_yuklenen() == 0


# --- (e) atlama sessiz değil ama log'u da boğmuyor -----------------------

def test_atlama_log_satiri_kosu_basina_bir_kez(tmp_path, monkeypatch):
    """Aynı proje iki platform için de sınanıyor ve her koşuda atlanacak.

    Süpürge saatlik koşuyor; engelli proje kalıcı olarak engelli kalacak. Satır
    hiç yazılmasa "sessizce False dönen koruma" olurdu; her sınamada yazılsa
    log'u boğardı. Doğru orta yol notify.uyar_bir_kez deseni: koşu (process)
    başına TEK satır.
    """
    base = _kur(tmp_path, monkeypatch)
    satirlar = _log_yakala(monkeypatch)
    _kontrol_sahte(monkeypatch, {"Kirli"})
    _proje(base, "Kirli", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    E.backfill(dry_run=True)               # Telegram + Bluesky = iki sınama
    E.backfill(dry_run=True)               # aynı process içinde ikinci koşu
    engel_satirlari = [m for _a, m in satirlar if "ATLANDI" in m]
    assert len(engel_satirlari) == 1, engel_satirlari


def test_uyumluluk_uyarisi_kapiyi_KAPATMIYOR_ama_loga_yaziliyor(
        tmp_path, monkeypatch):
    """UYARI ≠ HATA: uyarı yayını durdurmaz, sadece görünür olur."""
    base = _kur(tmp_path, monkeypatch)
    satirlar = _log_yakala(monkeypatch)
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda p, asama="render": ([], ["bugün zaten 3 yükleme"]))
    _proje(base, "Temiz", {"youtube_video_id": "v1",
                           "youtube_uploaded_at": "2026-09-01"})

    s = E.backfill(dry_run=True)
    assert [x["proje"] for x in s["islenen"]] == ["Temiz", "Temiz"]
    assert any("uyumluluk uyarısı" in m for _a, m in satirlar), satirlar


# --- GERÇEK kapı: taklit değil, uyumluluk.kontrol()'ün kendisi ------------

def test_gercek_kapi_ayni_md5_kopyasini_iki_supurgede_de_durduruyor(
        tmp_path, monkeypatch):
    """'Küllerimden Geç' vakasının birebir kurgusu — taklit YOK.

    İki proje AYNI `audio.wav` md5'ini taşıyor, ikisi de yayında ve hiçbirinde
    `kopya_notu` yok: `uyumluluk.kontrol()` bunu 2026-09-11'den beri UYARI
    değil HATA sayıyor. Bu test kapının GERÇEKTEN bağlandığını doğruluyor —
    monkeypatch'li bir kapı "çağrı var" der ama "doğru kapı mı" demez.

    `uyumluluk.KOKLER` tmp köke çevriliyor (modül dosyasına dokunulmuyor):
    `kontrol()` md5 taramasını KOKLER üzerinde yapıyor.
    """
    base = _kur(tmp_path, monkeypatch)
    monkeypatch.setattr(uyumluluk, "KOKLER", (base,))
    _log_yakala(monkeypatch)
    ayni_ses = b"AYNI SES" * 64
    _proje(base, "Yeniden Doğacağım",
           {"youtube_video_id": "v1", "youtube_uploaded_at": "2026-09-01",
            "youtube_privacy": "public"}, ses=ayni_ses)
    _proje(base, "Küllerimden Geç",
           {"youtube_video_id": "v2", "youtube_uploaded_at": "2026-09-02",
            "youtube_privacy": "public"}, ses=ayni_ses)

    # Ön koşul: kapı gerçekten HATA veriyor (test kurgusu doğru mu).
    hatalar, _u = uyumluluk.kontrol(os.path.join(base, "Küllerimden Geç"),
                                    "yukleme")
    assert any("md5" in h for h in hatalar), hatalar

    s = E.backfill(dry_run=True)
    assert s["islenen"] == [], s
    assert len(s["engellenen"]["Telegram"]) == 2

    f = F.backfill(dry_run=True)
    assert f["islenen"] == [], f
    assert len(f["engellenen"]) == 2


def test_kapi_cagrisi_kaynakta_var_supurgelerde():
    """Muhafız: `uyumluluk.kontrol` çağrısı iki süpürgeden de SİLİNMESİN.

    Bu deponun en sık arızası "yazıldı ama çağrılmıyor". Davranış testleri
    monkeypatch'li olduğu için çağrının KENDİSİNİ de kaynakta doğruluyoruz —
    `tests/test_entegrasyon_duman.py`'nin `ast` ile çağrı arayan deseni.
    """
    import ast
    for yol in (E.__file__, F.__file__):
        agac = ast.parse(open(yol, encoding="utf-8").read())
        cagrilar = [d for d in ast.walk(agac)
                    if isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Attribute)
                    and d.func.attr == "kontrol"
                    and isinstance(d.func.value, ast.Name)
                    and d.func.value.id == "uyumluluk"]
        assert cagrilar, "uyumluluk.kontrol() çağrısı YOK: %s" % yol
        # Aşama "yukleme" olmalı: render aşaması yükleme kontrollerini
        # (günlük yığılma) hiç çalıştırmaz.
        assert any(
            any(isinstance(a, ast.Constant) and a.value == "yukleme"
                for a in c.args)
            for c in cagrilar), yol


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
