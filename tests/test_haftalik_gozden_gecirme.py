# -*- coding: utf-8 -*-
"""`weekly_report.haftalik_gozden_gecirme()` — haftalık gözden geçirme özeti.

NEDEN BU TESTLER: bu modül haftada BİR kez, saatlik `auto_process` koşusunun
`finally` bloğundan çalışıyor. Yani bozulduğunda bunu fark etmek için en fazla
bir hafta (kötü ihtimalle hiç) var — CLAUDE.md'nin "BAĞLANTI seviyesindeki
sessiz arıza" bölümünün tarif ettiği durum. Altı şey kilitleniyor:

  (a) HAFTADA BİR çalışıyor; aynı hafta ikinci kez çalışmıyor; pazartesi
      sabahından önce ve golden-hour'da beklemeye geçiyor.
  (b) Damga dosyası yoksa/bozuksa/beklenmedik tipteyse ÇÖKMÜYOR.
  (c) Bildirim metni cp1254'e kodlanabiliyor (bu makinenin konsolu cp1254; bu
      tuzak bu depoda iki kez arıza üretti).
  (d) `auto_process.main()`in `finally` bloğu GERÇEKTEN çağırıyor (`ast`).
  (e) Rapor üretilemezse SESSİZ KALMIYOR (ayrı bildirim, hafta damgası YOK).
  (f) YouTube API'ye HİÇ istek atmıyor.

Ağ ve bildirim tamamen monkeypatch'li — hiçbir test gerçek bir istek atmaz.
"""

import ast
import io
import json
import os
import sys
import time

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import weekly_report                                    # noqa: E402


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def _an(yil, ay, gun, saat, dakika=5):
    """Yerel saatte bir an -> epoch saniye.

    `_zamani_mi` `time.localtime()` kullanıyor; test de aynı yerel saat
    ekseninde kurulmalı, yoksa UTC farkı olan makinelerde saat kaymaları
    testi kırar (CI Linux/UTC, geliştirme makinesi TR).
    """
    return time.mktime((yil, ay, gun, saat, dakika, 0, 0, 1, -1))


# 2026-09-14 Pazartesi, 2026-09-16 Çarşamba (takvimle doğrulandı).
PAZARTESI = (2026, 9, 14)
CARSAMBA = (2026, 9, 16)


@pytest.fixture
def durum(tmp_path):
    return str(tmp_path / "saglik_durum.json")


@pytest.fixture
def sahte_saglik():
    """`kontrol_et()` yerine geçen, ağa çıkmayan yedi adımlık taklit."""
    def _fn(log=print):
        return {
            "instagram_token": {"durum": "tamam"},
            "netlify": {"durum": "tamam"},
            "gorev_tanimlari": {"durum": "tamam"},
            "ses_takibi": {"durum": "tamam"},
            "git_senkron": {"durum": "geride", "geride_sn": 99999},
            "yayin_durgunlugu": {"durum": "bekleyen_yok"},
            "kacan_kosu": {"durum": "tamam"},
        }
    return _fn


@pytest.fixture
def bildirimler(monkeypatch):
    """`notify.send` taklidi — GERÇEK bildirim gitmez. Gönderilenleri toplar."""
    import notify
    kayit = []

    def _send(baslik, mesaj):
        kayit.append((baslik, mesaj))
        return True

    monkeypatch.setattr(notify, "send", _send)
    return kayit


@pytest.fixture
def agsiz(monkeypatch):
    """HER ağ çağrısını ve YouTube kimlik doğrulamasını PATLATIR.

    Bu fixture testi değil, İDDİAYI kuruyor: haftalık özet "YouTube API'ye
    ek istek atmamalı" diye tasarlandı; tek gerçek kanıtı, istek atmanın
    imkânsız olduğu bir ortamda sorunsuz çalışması.
    """
    sayac = {"istek": 0}

    def _patla(*a, **k):
        sayac["istek"] += 1
        raise AssertionError("haftalık özet ağa/YouTube API'ye çıktı: %r" % (a[:1],))

    try:
        import requests
        for ad in ("request", "get", "post", "put", "patch", "delete"):
            monkeypatch.setattr(requests, ad, _patla, raising=False)
    except ImportError:                       # pragma: no cover
        pass
    try:
        import youtube_auth
        monkeypatch.setattr(youtube_auth, "get_authenticated_service", _patla,
                            raising=False)
    except ImportError:                       # pragma: no cover
        pass
    try:
        import youtube_stats
        monkeypatch.setattr(youtube_stats, "get_stats_batch", _patla, raising=False)
        monkeypatch.setattr(youtube_stats, "get_stats", _patla, raising=False)
    except ImportError:                       # pragma: no cover
        pass
    return sayac


def _calistir(durum, sahte_saglik, **kw):
    kw.setdefault("saglik_fn", sahte_saglik)
    return weekly_report.haftalik_gozden_gecirme(
        log=lambda *a, **k: None, durum_dosyasi=durum, **kw)


# ---------------------------------------------------------------------------
# (a) HAFTADA BİR
# ---------------------------------------------------------------------------
def test_pazartesi_sabahi_calisir_ve_hafta_damgalanir(durum, sahte_saglik,
                                                      bildirimler):
    t = _an(*PAZARTESI, 10)
    s = _calistir(durum, sahte_saglik, simdi=t)
    assert s["durum"] == "tamam"
    assert len(bildirimler) == 1
    with open(durum, encoding="utf-8") as f:
        d = json.load(f)
    assert d[weekly_report.HAFTALIK_ANAHTARI] == weekly_report._hafta(t)


def test_ayni_hafta_ikinci_kez_calismaz(durum, sahte_saglik, bildirimler):
    t = _an(*PAZARTESI, 10)
    assert _calistir(durum, sahte_saglik, simdi=t)["durum"] == "tamam"
    # Aynı hafta içindeki BAŞKA bir saatlik koşu (perşembe).
    s = _calistir(durum, sahte_saglik, simdi=_an(2026, 9, 17, 15))
    assert s["durum"] == "atlandi"
    assert len(bildirimler) == 1, "aynı hafta ikinci bildirim gitti"


def test_pazartesi_sabahindan_once_beklenir(durum, sahte_saglik, bildirimler):
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 7))
    assert s["durum"] == "atlandi"
    assert bildirimler == []


def test_golden_hour_sonraki_kosuya_birakilir(durum, sahte_saglik, bildirimler):
    """Pazartesi 13:00 golden-hour (config.GOLDEN_HOURS) — yayın işi var."""
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 13))["durum"] == "atlandi"
    assert bildirimler == []
    # 14:00'te pencere kapanıyor, rapor çıkıyor.
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 14))["durum"] == "tamam"


def test_pazartesi_kacarsa_hafta_ici_telafi_edilir(durum, sahte_saglik,
                                                   bildirimler):
    """Makine pazartesi kapalıysa (pilde duran görevler: gerçek vaka) rapor
    KAYBOLMAZ — golden-hour kaçınması sonraki günlerde uygulanmıyor."""
    s = _calistir(durum, sahte_saglik, simdi=_an(*CARSAMBA, 13))
    assert s["durum"] == "tamam"
    assert len(bildirimler) == 1


def test_yeni_haftada_tekrar_calisir(durum, sahte_saglik, bildirimler):
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["durum"] == "tamam"
    assert _calistir(durum, sahte_saglik, simdi=_an(2026, 9, 21, 10))["durum"] == "tamam"
    assert len(bildirimler) == 2


def test_gonderilemezse_hafta_damgalanmaz_ama_gun_damgalanir(
        durum, sahte_saglik, monkeypatch):
    """Bildirim kanalı bozuksa: hafta YANMAZ (yarın tekrar denenir), ama aynı
    gün saatte bir yeniden denenmez — o, `saglik_kontrol.kontrol_et()`i günde
    24 kez çalıştırmak demekti."""
    import notify
    monkeypatch.setattr(notify, "send", lambda b, m: False)
    t = _an(*PAZARTESI, 10)
    assert _calistir(durum, sahte_saglik, simdi=t)["durum"] == "gonderilemedi"
    with open(durum, encoding="utf-8") as f:
        d = json.load(f)
    assert weekly_report.HAFTALIK_ANAHTARI not in d
    assert d[weekly_report.HAFTALIK_DENEME_ANAHTARI] == "2026-09-14"
    # Aynı gün, bir sonraki saatlik koşu: tekrar denemiyor.
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 11))["durum"] == "atlandi"
    # Ertesi gün: yeniden deniyor.
    assert _calistir(durum, sahte_saglik,
                     simdi=_an(2026, 9, 15, 10))["durum"] == "gonderilemedi"


# ---------------------------------------------------------------------------
# (b) BOZUK/EKSİK DAMGA -> ÇÖKMEZ
# ---------------------------------------------------------------------------
def test_damga_dosyasi_yoksa_calisir(durum, sahte_saglik, bildirimler):
    assert not os.path.exists(durum)
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["durum"] == "tamam"


def test_bozuk_json_cokmez(durum, sahte_saglik, bildirimler):
    with open(durum, "w", encoding="utf-8") as f:
        f.write("{bu gecerli JSON degil")
    assert _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["durum"] == "tamam"


@pytest.mark.parametrize("bozuk", [
    {"haftalik_ozet_hafta": 42},                       # damga sayı
    {"haftalik_ozet_olcum": "bu bir sözlük değil"},    # anlık görüntü metin
    {"haftalik_ozet_olcum": {"izlenme": "abc"}},       # sayı yerine metin
    {"izlenme_rapor_ozet": [1, 2, 3]},                 # özet liste
    {"izlenme_rapor_ozet": {"projects": "bozuk"}},     # kök değeri metin
])
def test_beklenmedik_damga_tipleri_cokmez(durum, sahte_saglik, bildirimler, bozuk):
    with open(durum, "w", encoding="utf-8") as f:
        json.dump(bozuk, f)
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert s["durum"] == "tamam", s


# ---------------------------------------------------------------------------
# (c) cp1254
# ---------------------------------------------------------------------------
def test_bildirim_metni_cp1254e_kodlanabiliyor(durum, sahte_saglik, bildirimler):
    """Bu makinenin konsolu cp1254 ve modül ELLE de çalıştırılıyor.

    `tiktok_publish_plan.py` tam olarak bunun yüzünden caption'ı hiç
    basamıyordu; `buyume_kontrol_listesi.md`'nin bir BAŞLIĞINDA duran `≈`
    (U+2248) bu rapora doğrudan sızabilecek gerçek bir karakter.
    """
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    baslik, mesaj = bildirimler[0]
    baslik.encode("cp1254")          # patlarsa test kırılır
    mesaj.encode("cp1254")
    assert "≈" not in mesaj and "→" not in mesaj


def test_cp1254_guvenli_kodlanamayanlari_temizler():
    ham = "ok -> → yaklasik ≈ emoji \U0001F600 bitti"
    temiz = weekly_report._cp1254_guvenli(ham)
    temiz.encode("cp1254")
    assert "->" in temiz and "~" in temiz


def test_turkce_harfler_korunuyor():
    """cp1254 Türkçeyi TAŞIYOR — koruma metni ASCII'ye düşürmemeli."""
    temiz = weekly_report._cp1254_guvenli("ÖLÇÜM: şğıİÇÜÖ — bitti")
    assert temiz == "ÖLÇÜM: şğıİÇÜÖ — bitti"


def test_proje_adindaki_emoji_raporu_kirmaz(durum, sahte_saglik, bildirimler,
                                            monkeypatch, tmp_path):
    """Rapora DİNAMİK metin giriyor (proje adları, istisna mesajları) — sabit
    metinleri temiz yazmak tek başına yetmez."""
    kok = tmp_path / "projects" / "Tuhaf \U0001F600 Ad"
    kok.mkdir(parents=True)
    (kok / "audio.wav").write_bytes(b"x")
    (kok / "state.json").write_text(
        json.dumps({"youtube_uploaded_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(_an(*PAZARTESI, 9) - 3600))}),
        encoding="utf-8")
    import uyumluluk
    monkeypatch.setattr(uyumluluk, "proje_klasorleri", lambda *a, **k: [str(kok)])
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    bildirimler[0][1].encode("cp1254")


# ---------------------------------------------------------------------------
# (d) auto_process GERÇEKTEN ÇAĞIRIYOR (bağlantı muhafızı)
# ---------------------------------------------------------------------------
def _auto_process_agaci():
    with io.open(os.path.join(_KOK, "auto_process.py"), encoding="utf-8") as f:
        return ast.parse(f.read())


def test_auto_process_finallyden_cagiriyor():
    """CLAUDE.md'nin İKİNCİ sorusu: hangi zamanlayıcı görevinden?

    Cevap saatlik `auto_process` — ve bunun TEK kanıtı `main()`in `finally`
    bloğunda duran çağrı. `finally` şart: "iş olsun olmasın her koşuda"
    çalışan tek yer orası; `try` içine konsa, işlenecek proje olmayan bir
    koşuda (kademeleme yüzünden koşuların çoğu böyle) erken `return` ile
    atlanırdı.
    """
    agac = _auto_process_agaci()
    main = next(d for d in ast.walk(agac)
                if isinstance(d, ast.FunctionDef) and d.name == "main")
    deneme = next(d for d in ast.walk(main) if isinstance(d, ast.Try) and d.finalbody)
    adlar = {d.func.id for d in ast.walk(ast.Module(body=deneme.finalbody, type_ignores=[]))
             if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
    assert "_haftalik_gozden_gecirme" in adlar, \
        "haftalık özet kancası main()'in finally bloğundan çağrılmıyor"


def test_auto_process_kancasi_dogru_fonksiyonu_cagiriyor():
    """Kanca VAR ama boş/yanlış adı çağırıyor olabilir — bu deponun
    'çağrı var, ama hattın dışında' alt sınıfı."""
    agac = _auto_process_agaci()
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == "_haftalik_gozden_gecirme")
    cagrilar = {d.func.id for d in ast.walk(fn)
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
    assert "haftalik_gozden_gecirme" in cagrilar
    kaynaklar = {a.module for a in ast.walk(fn) if isinstance(a, ast.ImportFrom)}
    assert "weekly_report" in kaynaklar


def test_auto_process_yeni_zamanlayici_gorevi_eklemedi():
    """CLAUDE.md: ÜÇ görev var, dördüncüsü YOK. Bu kanca yeni bir görev
    değil, mevcut saatlik göreve bağlı bir kanca olmalı."""
    with io.open(os.path.join(_KOK, "setup_task_scheduler.ps1"),
                 encoding="utf-8-sig") as f:
        ps = f.read()
    # Satır BAŞINDAKİ çağrılar sayılıyor: dosyada bir de yorum satırının
    # ORTASINDA geçen "Register-ScheduledTask" var (terk edilen -AtLogOn
    # denemesinin notu), o bir görev kurmuyor.
    kurulan = [s for s in ps.splitlines() if s.startswith("Register-ScheduledTask ")]
    assert len(kurulan) == 3, kurulan
    assert "weekly_report" not in ps


# ---------------------------------------------------------------------------
# (e) RAPOR ÜRETİLEMEZSE SESSİZ KALMIYOR
# ---------------------------------------------------------------------------
def test_rapor_uretilemezse_bildirim_gidiyor(durum, sahte_saglik, bildirimler,
                                             monkeypatch):
    def _patla(*a, **k):
        raise RuntimeError("tarama çöktü")
    monkeypatch.setattr(weekly_report, "_haftalik_satirlar", _patla)
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert s["durum"] == "hata"
    assert len(bildirimler) == 1
    assert "üretilemedi" in bildirimler[0][0].lower() or \
           "üretilemedi" in bildirimler[0][1]
    bildirimler[0][1].encode("cp1254")
    # Hafta damgalanMADI: sorun çözülünce rapor yine çıkar.
    with open(durum, encoding="utf-8") as f:
        assert weekly_report.HAFTALIK_ANAHTARI not in json.load(f)


def test_hata_bildirimi_gunde_bir(durum, sahte_saglik, bildirimler, monkeypatch):
    def _patla(*a, **k):
        raise RuntimeError("tarama çöktü")
    monkeypatch.setattr(weekly_report, "_haftalik_satirlar", _patla)
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 11))
    assert len(bildirimler) == 1, "saatlik koşuda hata bildirimi tekrarlıyor"


def test_tek_bolum_coktugunde_rapor_yine_cikiyor(durum, sahte_saglik,
                                                 bildirimler, monkeypatch):
    """Bir bölümün arızası raporun TAMAMINI kaybettirmemeli; arıza GÖRÜNÜR
    bir satır olarak durmalı."""
    def _patla(*a, **k):
        raise RuntimeError("katalog okunamadı")
    monkeypatch.setattr(weekly_report, "_katalog_taramasi", _patla)
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert s["durum"] == "tamam"
    assert "taranamadı" in bildirimler[0][1]
    assert "SAĞLIK" in bildirimler[0][1], "diğer bölümler de kayboldu"


def test_saglik_kontrolu_patlarsa_gorunur(durum, bildirimler):
    def _patla(log=print):
        raise RuntimeError("powershell yok")
    s = _calistir(durum, _patla, simdi=_an(*PAZARTESI, 10))
    assert s["durum"] == "tamam"
    assert "çalıştırılamadı" in bildirimler[0][1]


def test_saglik_uyarilari_raporda_adiyla_geciyor(durum, sahte_saglik, bildirimler):
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    mesaj = bildirimler[0][1]
    assert "git_senkron" in mesaj, "uyarı veren adım rapora girmemiş"
    assert "7 adım" in mesaj and "1 uyarı" in mesaj


def test_atlanan_adim_temiz_gorunmuyor(durum, bildirimler):
    """Bir adımın ATLANMASI "sorun yok" DEĞİL, "bakılamadı" demek —
    temiz saymak sessizce ölmüş bir korumayı sağlıklı göstermek olurdu."""
    def _fn(log=print):
        return {"netlify": {"durum": "tamam"},
                "gorev_tanimlari": {"durum": "atlandi", "sebep": "windows degil"},
                "git_senkron": {"durum": "geride_esik_alti"}}
    _calistir(durum, _fn, simdi=_an(*PAZARTESI, 10))
    mesaj = bildirimler[0][1]
    assert "hepsi temiz" not in mesaj
    assert "2 not" in mesaj and "gorev_tanimlari(atlandi)" in mesaj
    assert "uyarı" not in mesaj, "atlandı UYARI sayıldı — yanlış alarm"


def test_hepsi_tamamsa_tek_satir(durum, bildirimler):
    def _fn(log=print):
        return {"a": {"durum": "tamam"}, "b": {"durum": "yok"},
                "c": {"durum": "bekleyen_yok"}}
    _calistir(durum, _fn, simdi=_an(*PAZARTESI, 10))
    assert "3 adımın hepsi temiz" in bildirimler[0][1]


# ---------------------------------------------------------------------------
# (f) YOUTUBE API'YE EK İSTEK YOK
# ---------------------------------------------------------------------------
def test_hic_youtube_istegi_atmiyor(durum, sahte_saglik, bildirimler, agsiz):
    """Haftalık özet SIFIR YouTube isteği atar.

    Sayılar `state.json`'lardan (günde bir `youtube_stats` tazeliyor) ve
    `izlenme_raporu()`nun bıraktığı özetten okunuyor. Bu testin taban sayısı
    SIFIR; bir gün gerçekten istek atmak gerekirse buradaki sayı bilinçli
    olarak değiştirilmeli.
    """
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert s["durum"] == "tamam"
    assert agsiz["istek"] == 0


def test_izlenme_suresi_kayitli_ozetten_okunuyor(durum, sahte_saglik,
                                                 bildirimler, agsiz):
    """`izlenme_raporu()` özeti damga dosyasına yazıyor; haftalık rapor onu
    OKUYOR — Analytics'e ikinci bir istek atmıyor (ayrı kota havuzu)."""
    with open(durum, "w", encoding="utf-8") as f:
        json.dump({weekly_report.IZLENME_OZET_ANAHTARI: {
            "projects": {"video": 18, "izlenme": 300, "dakika": 900,
                         "ort_izlenme_sn": 60}}}, f)
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert "900 dk" in bildirimler[0][1]
    assert agsiz["istek"] == 0


def test_izlenme_raporu_ozeti_damgaya_yaziyor(durum, monkeypatch, tmp_path):
    """Bağlantı testi: özet KAYDEDİLMEZSE haftalık rapor izlenme süresini
    sonsuza kadar 'veri yok' gösterir — sessizce."""
    ozet = {os.path.join("C:", "x", "projects"):
            {"video": 2, "izlenme": 10, "dakika": 40, "ort_izlenme_sn": 30}}
    sonuc = weekly_report.izlenme_raporu(
        log=lambda *a, **k: None, durum_dosyasi=durum,
        rapor_fn=lambda: {"ozet": ozet}, token_yolu=None)
    assert sonuc["durum"] == "tamam"
    with open(durum, encoding="utf-8") as f:
        kayit = json.load(f)[weekly_report.IZLENME_OZET_ANAHTARI]
    assert kayit["projects"]["dakika"] == 40, "kök adı kısaltılmadı ya da yazılmadı"


# ---------------------------------------------------------------------------
# İÇERİK — raporun cevapladığı beş soru
# ---------------------------------------------------------------------------
@pytest.fixture
def sahte_katalog(monkeypatch, tmp_path):
    """İki projelik sahte katalog: biri bu hafta yayınlandı, biri yarım."""
    t = _an(*PAZARTESI, 9)
    yeni = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t - 2 * 86400))
    eski = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t - 40 * 86400))
    kokler = []
    for ad, st in (
        ("Yeni Sarki", {"youtube_video_id": "a", "youtube_shorts_video_id": "b",
                        "tiktok_publish_id": "c", "instagram_media_id": "d",
                        "youtube_uploaded_at": yeni, "tiktok_uploaded_at": yeni,
                        "youtube_views": 100, "youtube_shorts_views": 50}),
        ("Yarim Sarki", {"youtube_video_id": "e",
                         "youtube_uploaded_at": eski, "youtube_views": 7}),
    ):
        p = tmp_path / "projects" / ad
        p.mkdir(parents=True)
        (p / "audio.wav").write_bytes(b"x")
        (p / "state.json").write_text(json.dumps(st), encoding="utf-8")
        kokler.append(str(p))
    import uyumluluk
    monkeypatch.setattr(uyumluluk, "proje_klasorleri", lambda *a, **k: list(kokler))
    return kokler


def test_rapor_bes_soruyu_da_cevapliyor(durum, sahte_saglik, bildirimler,
                                        sahte_katalog):
    mesaj = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["metin"]
    assert "YAYIN (son 7 gün): 2 gönderi" in mesaj      # 1) ne yayınlandı
    assert "youtube 1" in mesaj and "tiktok 1" in mesaj
    assert "BEKLEYEN (2 proje)" in mesaj                # 2) ne bekliyor
    assert "youtube_shorts 1" in mesaj and "instagram 1" in mesaj
    assert "ÖLÇÜM: izlenme 157" in mesaj                # 3) ölçüm
    assert "SAĞLIK:" in mesaj                           # 4) sağlık
    assert "SENİN İŞİN:" in mesaj                       # 5) eldeki işler


def test_kirk_gun_onceki_yayin_bu_haftaya_sayilmiyor(durum, sahte_saglik,
                                                     bildirimler, sahte_katalog):
    mesaj = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["metin"]
    assert "YAYIN (son 7 gün): 2 gönderi" in mesaj


def test_izlenme_degisimi_gecen_haftayla_karsilastiriliyor(
        durum, sahte_saglik, bildirimler, sahte_katalog):
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    assert "ilk hafta" in bildirimler[0][1]
    # Bir hafta sonra: aynı katalog, delta sıfır ama AÇIKÇA yazılıyor.
    _calistir(durum, sahte_saglik, simdi=_an(2026, 9, 21, 10))
    assert "izlenme 157 (+0)" in bildirimler[1][1]


def test_gonderilemeyen_hafta_temel_cizgiyi_kaydirmaz(
        durum, sahte_saglik, sahte_katalog, monkeypatch):
    """Gönderilemeyen bir hafta anlık görüntüyü yenilerse, bir sonraki
    haftanın 'değişim' sayısı sessizce yanlış olur."""
    import notify
    monkeypatch.setattr(notify, "send", lambda b, m: False)
    _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))
    with open(durum, encoding="utf-8") as f:
        assert weekly_report.HAFTALIK_OLCUM_ANAHTARI not in json.load(f)


def test_tarihli_isler_markdownden_okunuyor(durum, sahte_saglik, bildirimler):
    """Tarihler KODA GÖMÜLÜ DEĞİL: `buyume_kontrol_listesi.md` + `CLAUDE.md`
    başlıklarından geliyor. Kullanıcı tarihi değiştirdiğinde kod değişmemeli."""
    satirlar = weekly_report._tarihli_isler(_an(*PAZARTESI, 10))
    metin = "\n".join(satirlar)
    assert "2026-10-09" in metin and "2026-10-11" in metin
    assert "YEDEK LİSTE" not in metin, "markdown okunamadı, yedeğe düşüldü"


def test_markdown_okunamazsa_yedek_liste_ve_GORUNUR(monkeypatch):
    monkeypatch.setattr(weekly_report, "TARIH_KAYNAKLARI", ("yok_boyle_bir_dosya.md",))
    metin = "\n".join(weekly_report._tarihli_isler(_an(*PAZARTESI, 10)))
    assert "2026-10-11" in metin
    assert "YEDEK LİSTE" in metin, "yedeğe düşüldüğü sessiz kaldı"


def test_gecmis_tarih_gectI_diye_isaretleniyor(monkeypatch):
    monkeypatch.setattr(weekly_report, "TARIH_KAYNAKLARI", ())
    metin = "\n".join(weekly_report._tarihli_isler(_an(2026, 10, 20, 10)))
    assert "GEÇTİ" in metin, "kaçırılmış son tarih sessizce kayboldu"


def test_geri_doldurma_tavani_ana_hatti_da_sayiyor():
    """Günlük tavan ana hattın gönderilerini de sayıyor (`bugun_yuklenen`
    docstring'i) — kalan süre tahmini bunu hesaba katmalı."""
    # Yedi günün yedisinde de gönderi var -> kuyruk ilerlemiyor.
    dolu = {"%02d" % g for g in range(1, 8)}
    assert "ilerlemiyor" in weekly_report._kuyruk_satiri("X", 10, 1, dolu)
    # Hiç gönderi yok -> günde 1 x 7 gün.
    assert "~1 hafta" in weekly_report._kuyruk_satiri("X", 7, 1, set())
    assert "kuyruk boş" in weekly_report._kuyruk_satiri("X", 0, 1, set())


def test_telegram_dikey_varyanti_da_tavani_dolduruyor():
    """DJ/derleme kökleri `telegram_shorts_uploaded_at` yazıyor; tavan
    İKİSİNİ birden sayıyor, tahmin de saymalı."""
    yayin_gun = {"telegram": {"2026-09-10"},
                 "telegram_shorts": {"2026-09-11"},
                 "bluesky": {"2026-09-12"}}
    assert weekly_report._dolu_gunler(yayin_gun, "telegram") == \
        {"2026-09-10", "2026-09-11"}


def test_rapor_kisa_kaliyor(durum, sahte_saglik, bildirimler, sahte_katalog):
    """Telefonda okunacak: uzun rapor okunmaz."""
    mesaj = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10))["metin"]
    assert len(mesaj.split("\n")) <= 16, mesaj
    assert len(mesaj) <= 1200, len(mesaj)


def test_elle_kosu_bildirim_gondermiyor(durum, sahte_saglik, bildirimler,
                                        sahte_katalog):
    """`--haftalik` telefonu çaldırmamalı ve hafta damgasını YAKMAMALI —
    yaksaydı otomatik rapor o hafta hiç çıkmazdı."""
    s = _calistir(durum, sahte_saglik, simdi=_an(*PAZARTESI, 10), gonder=False,
                  zorla=True)
    assert s["durum"] == "uretildi"
    assert bildirimler == []
    assert not os.path.exists(durum) or \
        weekly_report.HAFTALIK_ANAHTARI not in json.load(open(durum, encoding="utf-8"))
