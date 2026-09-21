# -*- coding: utf-8 -*-
"""İÇERİK KÖKÜ listesini ELLE sayan kodun muhafızı.

NEDEN VAR (2026-09-11): bu depoda üç içerik kökü var — `projects/` (ana
katalog), `dj_sets/` (DJ Famous) ve `derlemeler/` (o gün eklendi). Kök listesini
elle sayan her yer yeni kökü ATLADI. Bu, CLAUDE.md'deki "bağlantı seviyesinde
sessiz arıza" sınıfının alt türü ve grep'le "çağrılmayan fonksiyon" aramak
hiçbirini yakalamıyor: kod doğru, çağrılıyor, ama YANLIŞ KÜMEYE bakıyor.

Gerçekleşmiş üç örnek:
  * `youtube_stats.get_stats_batch(base)` hep `"projects"` ile çağrılıyordu —
    kataloğun yarısı hiç ölçülmedi.
  * `facebook_upload.bekleyen_yorumlari_tamamla()` varsayılanı
    `("projects", "dj_sets")` idi. Tek çağıranı (`auto_process.
    _facebook_yorumlari()`) argümansız çağırıyor, yani bir derlemenin bekleyen
    Facebook yorumu (YouTube linkini taşıyan yorum) HİÇBİR ZAMAN tamamlanamazdı.
  * `bluesky_upload._todays_upload_count()` günlük kota sayacını sadece
    `projects/` üzerinden sayıyordu; oysa setler ve derlemeler de Bluesky'a
    çıkıyor — eksik sayan bir tavan, olmayan tavandan farksız.

BU DOSYA İKİ ŞEY YAPIYOR:
  1. KAYNAK TARAMASI (ast): yeni kod `("projects", "dj_sets")` gibi EKSİK bir
     kök listesi yazarsa kırılır. Ayrıca ÜÇ kökü birden elle sayan her literal
     gerekçesiyle kayıtlı olmak zorunda — dördüncü bir kök açıldığında
     dokunulması gereken yerlerin listesi kendiliğinden çıksın diye.
  2. DAVRANIŞ TESTLERİ: düzeltilen üç fonksiyon `derlemeler/` altındaki bir
     projeyi GERÇEKTEN görüyor mu. Kaynak taraması tek başına yeterli değil —
     bir fonksiyon kök listesini hiç literal yazmadan da (tek bir `"projects"`
     sabitiyle) dar kalabilir.

YANLIŞ POZİTİF YOK: tarama yalnızca TAM eşleşen kök ADLARINI (`"projects"`,
`"dj_sets"`, `"derlemeler"`) ve yalnızca bir tuple/list/set literali İÇİNDE
sayıyor. Yani `if kok == "projects":` (ana kataloğa özel dallar) ya da
`--base` varsayılanları gibi tekil kullanımlar KAPSAM DIŞI — onların çoğu
bilerek tekil. Bilerek dar olan ÇOKLU listeler ise aşağıdaki muafiyet
sözlüklerinde gerekçeleriyle duruyor.
"""

import ast
import io
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import uyumluluk                                   # noqa: E402

ADLAR = set(uyumluluk.KOK_ADLARI)

# Taramanın girmediği klasörler. İçerik kökleri (projects/dj_sets/derlemeler)
# bilerek dışarıda: orada .py yok, ama olursa da bu kuralın konusu değil.
# `.claude/worktrees` eski dal kopyalarını tutuyor — kullanılmayan kod.
ATLANAN_KLASORLER = {
    ".claude", ".git", ".github", ".pytest_cache", ".stock_video_cache",
    "__pycache__", "tests", "projects", "dj_sets", "derlemeler",
}

# --- MUAFİYETLER ---------------------------------------------------------
# Anahtar: (repo'ya göreli dosya yolu, listede geçen kök adları — sıralı).
# Değer: NEDEN bilerek dar/ayrı olduğu. Gerekçesiz muafiyet eklenmesin diye
# değer boş olamaz (aşağıda kontrol ediliyor).

# 1) Kökleri EKSİK sayan (üçünden azını içeren) ÇOKLU listeler.
EKSIK_MUAFIYETLERI = {
    ("dj_tarama_kontrol.py", ("derlemeler", "dj_sets")):
        "BİLEREK. Content ID karantinası (önce private yükle, 2 saat bekle) "
        "sadece DJ setleri ve derlemeler için var: ikisi de üçüncü taraf "
        "eserlerle eşleşme riski taşıyor (City Pulse Set gerçekten eşleşti). "
        "Ana katalog şarkıları Suno'nun kendi üretimi — onları da karantinaya "
        "sokmak HER şarkıyı 2 saat geciktirirdi, kazancı sıfır.",

    ("upload/ek_platform_backfill.py", ("derlemeler", "dj_sets")):
        "BİLEREK. Bu bir KÖK LİSTESİ değil, bir SAPMA listesi: Telegram'da "
        "DJ setleri ve derlemeler `kind=\"dikey\"` ile gönderiliyor "
        "(telegram_shorts_message_id + shorts_9x16.mp4), çünkü o iki kökte "
        "`output/youtube_16x9.mp4` 130-540 MB, yani Telegram bot API'sinin "
        "50 MB sınırının kat kat üstünde (ana katalogda 8-21 MB, sınırın "
        "altında). dj_famous_process._EK_PLATFORMLAR'daki tablonun birebir "
        "karşılığı. `projects` burada YOK olmalı — varsayılan varyant zaten o. "
        "Kapsanan kök KÜMESİ hâlâ uyumluluk.KOKLER (bkz. BASE).",
}

# 2) ÜÇ kökü birden elle sayan listeler. İçerikleri DOĞRU, ama kopya oldukları
#    için dördüncü bir kök açıldığında tek tek gezilmeleri gerekiyor.
#    `uyumluluk.py` kanonik kaynak olduğu için listede yok (kod onu atlıyor).
TAM_KOPYA_MUAFIYETLERI = {
    ("latest_release.py", ("derlemeler", "dj_sets", "projects")):
        "BİLEREK AYRI. Bu liste sadece kök adı değil, sayfadaki GÖRÜNEN "
        "BAŞLIĞI da taşıyor (('dj_sets', 'DJ Famous Setleri')) ve gösterim "
        "sırasını belirliyor — uyumluluk.KOKLER'den türetilemez. Modülün "
        "kendi yorumu da 'yeni kök açılırsa buraya bir satır ekle' diyor.",
}


def _py_dosyalari():
    for dizin, alt_klasorler, isimler in os.walk(_KOK):
        alt_klasorler[:] = [d for d in alt_klasorler
                            if d not in ATLANAN_KLASORLER]
        for ad in sorted(isimler):
            if ad.endswith(".py") and ".bak." not in ad:
                yield os.path.join(dizin, ad)


def _goreli(yol):
    return os.path.relpath(yol, _KOK).replace(os.sep, "/")


def _kok_listeleri():
    """(goreli_yol, satir, (kok_adlari...)) üçlüleri — her literal için bir kez.

    Neden literal İÇİNDE arıyoruz: `BASELER = (os.path.join(_KOK, "dj_sets"),
    os.path.join(_KOK, "derlemeler"))` gibi yollar da yakalansın diye
    tuple'ın TAMAMI dolaşılıyor, sadece doğrudan elemanları değil.
    """
    for yol in _py_dosyalari():
        try:
            agac = ast.parse(io.open(yol, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError) as e:   # pragma: no cover
            pytest.fail("%s ayrıştırılamadı: %s" % (_goreli(yol), e))
        gorulen = set()
        for dugum in ast.walk(agac):
            if not isinstance(dugum, (ast.Tuple, ast.List, ast.Set)):
                continue
            bulunan = set()
            for alt in ast.walk(dugum):
                if (isinstance(alt, ast.Constant)
                        and isinstance(alt.value, str)
                        and alt.value in ADLAR):
                    bulunan.add(alt.value)
            if len(bulunan) < 2:
                # Tekil kullanımlar (ör. `--base` varsayılanı, `kok ==
                # "projects"` dalı) bilerek kapsam dışı — çoğu bilerek tekil.
                continue
            anahtar = (dugum.lineno, tuple(sorted(bulunan)))
            if anahtar in gorulen:
                continue          # iç içe tuple'lar aynı satırı iki kez verir
            gorulen.add(anahtar)
            yield _goreli(yol), dugum.lineno, tuple(sorted(bulunan))


# --- 1) Kaynak taraması --------------------------------------------------

def test_eksik_kok_listesi_eklenmemis():
    """ASIL MUHAFIZ: `("projects", "dj_sets")` biçiminde EKSİK bir liste."""
    ihlaller = []
    for yol, satir, adlar in _kok_listeleri():
        if set(adlar) == ADLAR:
            continue
        if (yol, adlar) in EKSIK_MUAFIYETLERI:
            continue
        ihlaller.append(
            "%s:%d — %s (eksik: %s)"
            % (yol, satir, list(adlar), sorted(ADLAR - set(adlar))))
    assert not ihlaller, (
        "İçerik kökü listesi ELLE ve EKSİK sayılmış. Bu, kodu bozmaz — sadece "
        "yanlış kümeye baktırır ve SESSİZCE eksik iş yapar (bkz. bu dosyanın "
        "docstring'i). Doğru çözüm: `from uyumluluk import KOKLER` ya da "
        "`uyumluluk.proje_klasorleri()`. Gerçekten bilerek darsa "
        "EKSIK_MUAFIYETLERI'ne GEREKÇESİYLE ekle.\n  " + "\n  ".join(ihlaller))


def test_tam_kok_listesinin_kopyalari_kayitli():
    """Üç kökü birden elle sayan her liste gerekçesiyle kayıtlı olmalı.

    NEDEN: içerikleri bugün doğru, ama DÖRDÜNCÜ bir kök açıldığında tek tek
    gezilmesi gereken yerler bunlar. Kayıt altında olmazlarsa aynı sessiz
    arıza birebir tekrar eder.
    """
    kayitsiz = []
    for yol, satir, adlar in _kok_listeleri():
        if set(adlar) != ADLAR:
            continue
        if yol == "uyumluluk.py":
            continue          # kanonik kaynak — kopya değil, aslı
        if (yol, adlar) in TAM_KOPYA_MUAFIYETLERI:
            continue
        kayitsiz.append("%s:%d" % (yol, satir))
    assert not kayitsiz, (
        "Kök listesinin kayıtsız bir kopyası var. Ya `uyumluluk.KOKLER`'i "
        "kullan ya da TAM_KOPYA_MUAFIYETLERI'ne neden ayrı durduğunu yaz.\n  "
        + "\n  ".join(kayitsiz))


def test_muafiyetlerin_hepsinin_gerekcesi_var():
    """Gerekçesiz muafiyet, muafiyet listesini çöplüğe çevirir."""
    for sozluk in (EKSIK_MUAFIYETLERI, TAM_KOPYA_MUAFIYETLERI):
        for anahtar, gerekce in sozluk.items():
            assert gerekce and len(gerekce) > 40, anahtar


def test_muafiyetler_bayatlamamis():
    """Düzeltilen bir satır muafiyet listesinde UNUTULMASIN.

    Muafiyet kalıcı bir bağışıklık değil; kaynakta karşılığı kalmayan bir
    kayıt, bir sonraki okuyucuya yanlış bilgi verir.
    """
    gercek = {(yol, adlar) for yol, _, adlar in _kok_listeleri()}
    for sozluk, ad in ((EKSIK_MUAFIYETLERI, "EKSIK_MUAFIYETLERI"),
                       (TAM_KOPYA_MUAFIYETLERI, "TAM_KOPYA_MUAFIYETLERI")):
        for anahtar in sozluk:
            assert anahtar in gercek, (
                "%s içindeki %r artık kaynakta yok — muafiyet satırını sil."
                % (ad, anahtar))


def test_uyumluluk_kokleri_mutlak_ve_uc_tane():
    """Kanonik listenin kendisi: mutlak yol + üç kök.

    Mutlak yol ZORUNLU — göreli bırakılırsa yanlış cwd'de `os.path.isdir`
    False döner ve tarayan her fonksiyon SESSİZCE boş sonuç verir.
    """
    assert uyumluluk.KOK_ADLARI == ("projects", "dj_sets", "derlemeler")
    assert len(uyumluluk.KOKLER) == 3
    for yol in uyumluluk.KOKLER:
        assert os.path.isabs(yol), yol
    assert [os.path.basename(y) for y in uyumluluk.KOKLER] == \
        list(uyumluluk.KOK_ADLARI)


# --- 2) Davranış testleri: düzeltilen fonksiyonlar derlemeleri görüyor mu --

def _sahte_katalog(tmp_path, kok_adi, proje_adi, durum):
    """Üç kökü de oluşturur, birine tek bir proje koyar; kök listesini döner."""
    kokler = []
    for ad in uyumluluk.KOK_ADLARI:
        d = tmp_path / ad
        d.mkdir(exist_ok=True)
        kokler.append(str(d))
    proje = tmp_path / kok_adi / proje_adi
    proje.mkdir(parents=True)
    (proje / "state.json").write_text(
        json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    return tuple(kokler), str(proje)


def test_facebook_bekleyen_yorum_derlemeleri_de_tariyor(tmp_path, monkeypatch):
    """EN YÜKSEK ÖNCELİKLİ DÜZELTME. Varsayılan ("projects", "dj_sets") iken
    bu senaryoda `bakilan=0` dönüyordu — hiçbir hata, hiçbir log satırı."""
    import facebook_upload

    kokler, proje = _sahte_katalog(
        tmp_path, "derlemeler", "Gece Seansi Vol. 1",
        {"facebook_comment_pending": True, "youtube_video_id": "O2VGj5SUz30",
         "facebook_reels_id": "1050913767816193"})
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)

    # AĞA ÇIKMA YOK: gerçek post_pending_comment get_access_token() çağırır ve
    # bu makinede GERÇEK bir facebook_token.json duruyor.
    cagrilanlar = []

    def _sahte_yorum(p):
        cagrilanlar.append(p)
        return True

    monkeypatch.setattr(facebook_upload, "post_pending_comment", _sahte_yorum)

    sonuc = facebook_upload.bekleyen_yorumlari_tamamla()
    assert sonuc["bakilan"] == 1, sonuc
    assert sonuc["tamamlanan"] == 1, sonuc
    assert [os.path.basename(p) for p in cagrilanlar] == ["Gece Seansi Vol. 1"]
    assert os.path.dirname(cagrilanlar[0]) == os.path.dirname(proje)


def test_bluesky_gunluk_sayac_derlemeleri_de_sayiyor(tmp_path, monkeypatch):
    """Kota sayacı eksik sayarsa tavan hiç tetiklenmez — olmayan tavan."""
    import datetime

    import bluesky_upload

    bugun = datetime.date.today().isoformat()
    kokler, _ = _sahte_katalog(
        tmp_path, "derlemeler", "Gece Seansi Vol. 1",
        {"bluesky_uploaded_at": "%sT18:15:46" % bugun})
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)

    assert bluesky_upload._todays_upload_count() == 1


def test_tiktok_bekleyen_kapaklar_derlemeleri_de_listeliyor(
        tmp_path, monkeypatch, capsys):
    """Kapak ELLE seçiliyor; listede görünmeyen iş yapılmayan iştir."""
    import tiktok_upload

    kokler, _ = _sahte_katalog(
        tmp_path, "derlemeler", "Gece Seansi Vol. 1",
        {"tiktok_publish_id": "v_inbox_file~v2.768",
         "tiktok_cover_hint": "derlemeler/Gece Seansi Vol. 1/cover_vertical.png"})
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)

    tiktok_upload.print_pending_covers()
    cikti = capsys.readouterr().out
    assert "Gece Seansi Vol. 1" in cikti
    assert "cover_vertical.png" in cikti


def test_youtube_stats_ve_comments_kanonik_listeyi_kullaniyor():
    """İkisi de kendi kopyasını tutuyordu; artık aynı nesneyi paylaşıyorlar."""
    import youtube_comments
    import youtube_stats

    assert youtube_stats.KOKLER == uyumluluk.KOKLER
    assert youtube_comments.KOKLER == uyumluluk.KOKLER


def test_validate_project_all_uc_kokun_hepsini_geziyor(tmp_path, monkeypatch):
    """`validate_project.py --all` sadece `projects/` tarıyordu.

    Etkisi düşük ama gerçek: boru hattı validate()'i zaten proje bazında
    çağırıyor (render.py), ama ELLE yapılan tam-katalog koşusunda ("her şey
    sağlam mı") DJ setleri ve derlemeler hiç görünmüyordu — yani "sorun yok"
    çıktısı kataloğun bir bölümü için hiçbir şey söylemiyordu.
    """
    import validate_project

    kokler = []
    for ad in uyumluluk.KOK_ADLARI:
        d = tmp_path / ad
        (d / ("%s_proje" % ad)).mkdir(parents=True)
        kokler.append(str(d))
    monkeypatch.setattr(uyumluluk, "KOKLER", tuple(kokler))

    gorulen = []

    def _sahte_validate(p):
        gorulen.append(p)
        return [], []

    monkeypatch.setattr(validate_project, "validate", _sahte_validate)
    monkeypatch.setattr(sys, "argv", ["validate_project.py", "--all"])
    with pytest.raises(SystemExit) as e:
        validate_project.main()

    assert e.value.code == 0
    assert [os.path.basename(p) for p in gorulen] ==         ["%s_proje" % ad for ad in uyumluluk.KOK_ADLARI]
    for p in gorulen:
        assert os.path.isabs(p), p          # mutlak yol: cwd'den bağımsız


# --- 3) Toplu YouTube düzeltmeleri (eski xfail izleyici) -----------------
# 2026-09-11'de burası `xfail(strict)` bir İZLEYİCİYDİ: upload/youtube_upload.py
# o gün YAZILAMAZ listesindeydi. Boşluk kapatıldı, marker kaldırıldı; testler
# normal regresyon testi olarak duruyor.

def test_youtube_upload_toplu_duzeltme_derlemeleri_kapsamali():
    """`--thumbnail-only --all` / `--description-only --all` ÜÇ kökü de kapsamalı.

    GEÇMİŞ: varsayılan önce `("projects",)`, sonra `("projects", "dj_sets")`
    idi; her genişlemede bir kök unutuldu. Etkisi görünmez ama gerçek: bir
    derlemenin YouTube kapağı/açıklaması bozuksa toplu düzeltme onu hiç
    görmüyordu — DJ setlerinde birebir aynı arıza yaşanmıştı (City Pulse
    Set'in kapağı YouTube'da hiç görünmüyordu, kullanıcı bildirdi).
    Bu test 2026-09-11'de xfail(strict) bir İZLEYİCİYDİ (dosya o gün
    YAZILAMAZ listesindeydi); boşluk kapatıldığı için artık normal bir
    regresyon testi.
    """
    import inspect

    import youtube_upload

    for fn in (youtube_upload.fix_all_thumbnails,
               youtube_upload.fix_all_descriptions):
        varsayilan = inspect.signature(fn).parameters["bases"].default
        assert set(varsayilan) == ADLAR, (fn.__name__, varsayilan)
        # Kopya bir liste DEĞİL, kanonik nesnenin KENDİSİ olmalı: aynı içerikli
        # ayrı bir tuple, dördüncü kök açıldığında sessizce geride kalırdı.
        assert varsayilan is uyumluluk.KOK_ADLARI, fn.__name__


def test_youtube_upload_toplu_duzeltme_cwd_bagimsiz(tmp_path, monkeypatch):
    """Kök adları GÖRELİ; repo kökü dışından çağrılınca hiçbir şey bulunmamalı mı?

    Hayır — `_kok_yolu()` göreli kök adını repo köküne bağlıyor. Eskiden
    `os.path.isdir("projects")` doğrudan cwd'ye bakıyordu: script başka bir
    klasörden çağrıldığında toplu düzeltme SESSİZCE hiçbir proje bulmadan
    bitiyordu (bu deponun en sık arıza sınıfı).
    """
    import youtube_upload

    monkeypatch.chdir(tmp_path)
    gorulen = []
    monkeypatch.setattr(youtube_upload, "_fix_all_thumbnails_in",
                        lambda base: gorulen.append(base))
    youtube_upload.fix_all_thumbnails()

    assert [os.path.basename(b) for b in gorulen] == list(uyumluluk.KOK_ADLARI)
    for b in gorulen:
        assert os.path.isabs(b), b
