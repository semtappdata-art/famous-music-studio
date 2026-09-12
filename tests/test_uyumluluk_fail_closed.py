# -*- coding: utf-8 -*-
"""Politika kapısı FAIL-CLOSED olmalı: kapı ÇÖKERSE yayın BAŞLAMAZ.

NEDEN VAR (2026-09-12 denetimi). `auto_process.process_project()` ve
`dj_famous_process.process_set()` içindeki uyumluluk bloğunun üstünde şu yorum
duruyordu:

    # HATA varsa yukleme HIC baslamiyor; uyari sadece loglaniyor.

Bu bir GARANTİ ifadesiydi ve yalnızca `uyumluluk.kontrol()` DÜZGÜN DÖNDÜĞÜNDE
geçerliydi. `kontrol()` bir istisna fırlattığında `except` dalı satırı
"gormezden geliniyor" diye loglayıp AKIŞA DEVAM ediyordu — yani kapı sessizce
AÇILIYORDU. CLAUDE.md'nin iki ayrı dersinin kesiştiği yer: "yalan söyleyen
yorum hiç yorum olmamasından kötüdür" + "sessizce False dönen bir koruma,
olmayan korumadan kötüdür".

Bahis boş değil, bu kapıya bağlı İKİ gerçek koruma var:
  * `dj_sets/City Pulse Set` — state.json'ında AÇIK bir telif itirazı kayıtlı
    (`telif_eser` + `telif_araliklari`), `uyumluluk.kontrol()` HATA veriyor;
  * `projects/Küllerimden Geç` — `Yeniden Doğacağım` ile aynı audio.wav md5'i.
İkisi de "aynı içeriği ikinci kez yayınlama" sınıfı ve yayın GERİ ALINAMAZ
(Instagram'da yayınlanmış medyayı API'den silmek MÜMKÜN DEĞİL).

Aynı kapı bugün depoda dört yerde fail-closed yapılmıştı
(`upload/ek_platform_backfill.py`, `upload/facebook_backfill.py`,
`dj_clips.py`, `upload/tiktok_publish_plan.py`); ANA HAT deponun geri kalanıyla
ters duruyordu. Bu dosya o tersliği çiviliyor.

KAPSAM ayrımı da test ediliyor: fail-closed "boru hattı sonsuza kadar dursun"
demek DEĞİL — `return` yalnızca O PROJEYİ atlıyor, koşu bir sonraki projeyle
devam ediyor.

AĞA HİÇ ÇIKILMIYOR: youtube_upload / youtube_playlists sahte modüller,
kimlik dosyası kontrolleri monkeypatch'li, `uyumluluk.kontrol` taklit.
"""

import ast
import json
import os
import sys
import types

import pytest

import auto_process as ap
import dj_famous_process as dj
import uyumluluk
import validate_project

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_KOK, "upload")


class KapiCoktu(Exception):
    """`kontrol()`un gerçekte fırlatabileceği sınıfın temsilcisi.

    Gerçek örnekler: `uyumluluk.DurumBozuk` dışında kalan her şey —
    `_md5()`de OSError, `json` katmanında beklenmedik bir TypeError, modülün
    kendisinde bir NameError. Kapı bunları YAKALAMIYOR, yani `kontrol()`
    çağrısı çağırana kadar yükseliyor."""


# --- sahte yükleme modülleri ---------------------------------------------


def _sahte_youtube_upload(yuklenen):
    """Gerçek yüklemenin YERİNE geçen probe: çağrıldıysa YAYIN BAŞLAMIŞTIR."""
    mod = types.ModuleType("youtube_upload")

    def upload_video(project_dir, privacy, schedule=True):
        yuklenen.append(("uzun", os.path.basename(project_dir)))
        return "VID1"

    def upload_short(project_dir, privacy, uzun_id, schedule=True):
        yuklenen.append(("shorts", os.path.basename(project_dir)))
        return "KISA1"

    mod.upload_video = upload_video
    mod.upload_short = upload_short
    return mod


def _sahte_youtube_playlists():
    mod = types.ModuleType("youtube_playlists")
    mod.get_authenticated_service = lambda: object()
    mod.sync_project = lambda servis, proje: None
    return mod


def _sadece_youtube_tokeni(monkeypatch):
    """Bu makinede tiktok/instagram/facebook kimlik dosyaları GERÇEKTEN duruyor.

    Dokunulmadan bırakılırsa test gerçek bir yükleme başlatırdı
    (desen: tests/test_playlist_shorts_sirasi.py)."""
    gercek_isfile = os.path.isfile
    yok = {os.path.join(_UPLOAD, ad) for ad in (
        "tiktok_token.json", "instagram_token.json", "facebook_token.json",
        "telegram_client_secrets.json", "bluesky_client_secrets.json")}

    def isfile(yol):
        if yol == os.path.join(_UPLOAD, "token.json"):
            return True
        if yol in yok:
            return False
        return gercek_isfile(yol)

    monkeypatch.setattr(os.path, "isfile", isfile)


def _proje_yaz(kok, ad):
    p = os.path.join(str(kok), ad)
    os.makedirs(p)
    with open(os.path.join(p, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": ad, "theme": "pop"}, f)
    with open(os.path.join(p, "state.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    return p


# --- auto_process koşum takımı -------------------------------------------


def _kur_auto(tmp_path, monkeypatch, kontrol, rapor_yaz=None, adlar=("Sarki",)):
    projeler = [_proje_yaz(tmp_path / "projects", ad) for ad in adlar]

    monkeypatch.setattr(uyumluluk, "kontrol", kontrol)
    monkeypatch.setattr(uyumluluk, "rapor_yaz",
                        rapor_yaz if rapor_yaz is not None
                        else (lambda *a, **k: None))

    # Render/kapak bu testin konusu değil; ikisi de saatler sürer / ffmpeg ister.
    monkeypatch.setattr(ap.generate_cover, "generate", lambda p: None)
    monkeypatch.setattr(ap, "_is_rendered", lambda p: True)
    monkeypatch.setattr(ap, "_check_youtube_captions", lambda *a, **k: None)
    monkeypatch.setattr(ap, "_check_tiktok_notification", lambda *a, **k: None)
    monkeypatch.setattr(ap, "_check_instagram_pending", lambda *a, **k: None)
    monkeypatch.setattr(ap, "_ek_platformlari_isle", lambda *a, **k: None)

    yuklenen = []
    monkeypatch.setitem(sys.modules, "youtube_upload",
                        _sahte_youtube_upload(yuklenen))
    monkeypatch.setitem(sys.modules, "youtube_playlists",
                        _sahte_youtube_playlists())

    satirlar = []
    monkeypatch.setattr(ap, "log", lambda m: satirlar.append(str(m)))
    _sadece_youtube_tokeni(monkeypatch)
    return projeler, yuklenen, satirlar


# --- dj_famous_process koşum takımı --------------------------------------


def _kur_dj(tmp_path, monkeypatch, kontrol, rapor_yaz=None, adlar=("Set A",)):
    setler = [_proje_yaz(tmp_path / "dj_sets", ad) for ad in adlar]

    monkeypatch.setattr(uyumluluk, "kontrol", kontrol)
    monkeypatch.setattr(uyumluluk, "rapor_yaz",
                        rapor_yaz if rapor_yaz is not None
                        else (lambda *a, **k: None))

    monkeypatch.setattr(dj.generate_cover, "generate", lambda p: None)
    monkeypatch.setattr(dj, "_is_rendered", lambda p: True)
    monkeypatch.setattr(dj, "_kesitleri_uret", lambda p: None)

    yuklenen = []
    monkeypatch.setitem(sys.modules, "youtube_upload",
                        _sahte_youtube_upload(yuklenen))
    monkeypatch.setitem(sys.modules, "youtube_playlists",
                        _sahte_youtube_playlists())

    satirlar = []
    monkeypatch.setattr(dj, "log", lambda m: satirlar.append(str(m)))
    _sadece_youtube_tokeni(monkeypatch)
    return setler, yuklenen, satirlar


def _patlayan_kontrol(*a, **k):
    raise KapiCoktu("KOKLER göreli kaldı, os.path.isdir patladı")


def _metin(satirlar):
    return "\n".join(satirlar)


# --- (a) kapı ÇÖKERSE yayın başlamıyor -----------------------------------


def test_kontrol_patlarsa_auto_process_yayin_baslatmiyor(tmp_path, monkeypatch):
    """ASIL REGRESYON: eski kod burada "gormezden geliniyor" deyip DEVAM ediyordu."""
    (proje,), yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch, _patlayan_kontrol)

    ap.process_project(proje, "public", schedule=False)

    assert yuklenen == [], (
        "uyumluluk kapısı çöktüğü hâlde yükleme başladı — kapı FAIL-OPEN")
    log = _metin(satirlar)
    assert "fail-closed" in log, "atlama sebebi log'a yazılmadı"
    assert "KapiCoktu" in log, "çöken istisnanın türü log'a yazılmadı"


def test_kontrol_patlarsa_dj_hatti_yayin_baslatmiyor(tmp_path, monkeypatch):
    (set_dir,), yuklenen, satirlar = _kur_dj(
        tmp_path, monkeypatch, _patlayan_kontrol)

    dj.process_set(set_dir, "public", schedule=False)

    assert yuklenen == [], (
        "uyumluluk kapısı çöktüğü hâlde set yüklenmeye başladı — FAIL-OPEN")
    log = _metin(satirlar)
    assert "fail-closed" in log
    assert "KapiCoktu" in log


# --- (b) HATA dönerse eskisi gibi yayınlanmıyor ---------------------------


def test_hata_donerse_yayin_yok_auto(tmp_path, monkeypatch):
    (proje,), yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch,
        lambda p, a: (["telif eşleşmesi kayıtlı"], []))

    ap.process_project(proje, "public", schedule=False)

    assert yuklenen == []
    assert "uyumluluk hatasi nedeniyle" in _metin(satirlar)


def test_hata_donerse_yayin_yok_dj(tmp_path, monkeypatch):
    (set_dir,), yuklenen, satirlar = _kur_dj(
        tmp_path, monkeypatch,
        lambda p, a: (["telif eşleşmesi kayıtlı"], []))

    dj.process_set(set_dir, "public", schedule=False)

    assert yuklenen == []
    assert "uyumluluk hatasi nedeniyle" in _metin(satirlar)


# --- (c) SADECE uyarı varsa yayın DEVAM ediyor ---------------------------


def test_sadece_uyari_varsa_yayin_devam_ediyor_auto(tmp_path, monkeypatch):
    """Fail-closed sertleştirmesi UYARI'nın anlamını DEĞİŞTİRMEMELİ.

    Uyarı tanımı gereği "devam edilebilir"; onu da kapıya çevirmek bugün
    yayında olan projelerin geri doldurma/altyazı işlerini durdururdu."""
    rapor = []
    (proje,), yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch,
        lambda p, a: ([], ["bugün zaten 3 yükleme yapıldı"]),
        rapor_yaz=lambda p, h, u, log=print: rapor.append((tuple(h), tuple(u))))

    ap.process_project(proje, "public", schedule=False)

    assert ("uzun", "Sarki") in yuklenen, "sadece uyarı varken yayın durdu"
    assert rapor == [((), ("bugün zaten 3 yükleme yapıldı",))], (
        "uyarılar rapor_yaz'a geçirilmedi — uyarı sessizce kayboluyor")


def test_sadece_uyari_varsa_yayin_devam_ediyor_dj(tmp_path, monkeypatch):
    (set_dir,), yuklenen, satirlar = _kur_dj(
        tmp_path, monkeypatch,
        lambda p, a: ([], ["derlemede bölüm damgası yok"]))

    dj.process_set(set_dir, "public", schedule=False)

    assert ("uzun", "Set A") in yuklenen, "sadece uyarı varken set yayını durdu"


# --- (d) atlanan proje KOŞUYU durdurmuyor --------------------------------


def test_atlanan_proje_kosunun_geri_kalanini_durdurmuyor(tmp_path, monkeypatch):
    """KAPSAM: fail-closed "bu proje bu koşuda yayınlanmasın" demek;
    "boru hattı sonsuza kadar dursun" demek DEĞİL.

    main()'in `for project_dir in batch` döngüsü burada birebir taklit
    ediliyor: `process_project` İSTİSNA FIRLATMAMALI, yoksa döngü kırılır ve
    o koşudaki diğer projelerin hepsi sessizce atlanırdı."""

    def kontrol(proje, asama):
        if os.path.basename(proje) == "Bozuk":
            raise KapiCoktu("state.json yarım")
        return [], []

    projeler, yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch, kontrol, adlar=("Bozuk", "Temiz"))

    for proje in projeler:                      # main()'deki batch döngüsü
        ap.process_project(proje, "public", schedule=False)

    assert ("uzun", "Temiz") in yuklenen, (
        "engellenen proje kendinden SONRAKİ projeyi de bloke etti")
    assert ("uzun", "Bozuk") not in yuklenen
    assert "fail-closed" in _metin(satirlar)


def test_atlanan_set_kosunun_geri_kalanini_durdurmuyor(tmp_path, monkeypatch):
    def kontrol(proje, asama):
        if os.path.basename(proje) == "Bozuk Set":
            raise KapiCoktu("state.json yarım")
        return [], []

    setler, yuklenen, _ = _kur_dj(
        tmp_path, monkeypatch, kontrol, adlar=("Bozuk Set", "Temiz Set"))

    for s in setler:
        dj.process_set(s, "public", schedule=False)

    assert ("uzun", "Temiz Set") in yuklenen
    assert ("uzun", "Bozuk Set") not in yuklenen


def test_kapi_dongu_icinde_cagriliyor_yani_return_tek_projeyi_atliyor():
    """`return`un "tüm koşu" değil "tek proje" anlamına geldiğinin YAPISAL kanıtı.

    Davranış testi `process_project`in istisna fırlatmadığını gösteriyor; bu
    test çağrının GERÇEKTEN bir döngü gövdesinde durduğunu gösteriyor. İkisi
    birlikte "atlanan proje koşuyu durdurmaz"ı çiviliyor. (Desen:
    CLAUDE.md — çağrının VARLIĞI değil YERİ/SIRASI kritik.)"""
    for dosya, fonk in (("auto_process.py", "process_project"),
                        ("dj_famous_process.py", "process_set")):
        with open(os.path.join(_KOK, dosya), encoding="utf-8") as f:
            agac = ast.parse(f.read())
        dongude = False
        for d in ast.walk(agac):
            if not isinstance(d, (ast.For, ast.AsyncFor)):
                continue
            for alt in ast.walk(d):
                if (isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name)
                        and alt.func.id == fonk):
                    dongude = True
        assert dongude, (
            "%s: %s() bir döngü gövdesinden çağrılmıyor — tek projeyi atlayan "
            "`return` tüm koşuyu durduruyor olabilir" % (dosya, fonk))


# --- (e) rapor_yaz patlarsa KARAR ne oluyor ------------------------------


def _patlayan_rapor(*a, **k):
    raise RuntimeError("log dosyası kilitli")


def test_rapor_yaz_patlarsa_temiz_yayin_DURMUYOR(tmp_path, monkeypatch):
    """KARAR: `rapor_yaz` kapının KARARINDAN SONRA çalışan bir RAPORLAMA adımı.

    Kararın girdisi (`_uh`) zaten elde; raporun yazılamaması korumaya HİÇBİR
    ŞEY eklemeden temiz bir yayını bloklardı. Bu yüzden kapı kararından AYRI
    sarmalandı. Sessiz de kalmıyor: satır log'a düşüyor."""
    (proje,), yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch, lambda p, a: ([], ["bir uyarı"]),
        rapor_yaz=_patlayan_rapor)

    ap.process_project(proje, "public", schedule=False)

    assert ("uzun", "Sarki") in yuklenen, (
        "rapor yazılamadı diye TEMİZ bir yayın durduruldu")
    log = _metin(satirlar)
    assert "rapor" in log.lower(), "rapor arızası sessizce yutuldu"
    assert "RuntimeError" in log


def test_rapor_yaz_patlasa_bile_HATA_yayini_durduruyor(tmp_path, monkeypatch):
    """Asıl tuzak: rapor_yaz aynı try içinde kalsaydı, patladığı anda `if _uh`
    satırına HİÇ gelinmez ve HATA'lı proje eski kodda YAYINLANIRDI."""
    (proje,), yuklenen, satirlar = _kur_auto(
        tmp_path, monkeypatch, lambda p, a: (["telif eşleşmesi kayıtlı"], []),
        rapor_yaz=_patlayan_rapor)

    ap.process_project(proje, "public", schedule=False)

    assert yuklenen == [], (
        "rapor_yaz patlayınca HATA kararı kayboldu — yayın başladı")
    assert "uyumluluk hatasi nedeniyle" in _metin(satirlar)


def test_rapor_yaz_patlasa_bile_HATA_yayini_durduruyor_dj(tmp_path, monkeypatch):
    (set_dir,), yuklenen, satirlar = _kur_dj(
        tmp_path, monkeypatch, lambda p, a: (["telif eşleşmesi kayıtlı"], []),
        rapor_yaz=_patlayan_rapor)

    dj.process_set(set_dir, "public", schedule=False)

    assert yuklenen == []
    assert "uyumluluk hatasi nedeniyle" in _metin(satirlar)


# --- validate_project (render aşaması) -----------------------------------


def test_validate_kapi_cokerse_HATA_uretiyor(tmp_path, monkeypatch):
    """KARAR: render aşamasında da FAIL-CLOSED, ama biçimi farklı — bu fonksiyon
    `return` etmiyor, (errors, warnings) DÖNDÜRÜYOR. Fail-closed burada
    "istisna `errors`a düşer" demek: `render.render_project()` errors doluysa
    render'a hiç girmiyor.

    Gerekçe: iki satır yukarıda `kontrol()`un DÖNDÜĞÜ hatalar zaten `errors`a
    giriyor. Kapının "hata var" demesi render'ı durduruyorsa "cevap
    veremiyorum" demesi de durdurmalı — aksi hâlde kapıyı atlatmanın en kolay
    yolu onu BOZMAK olurdu."""
    proje = _proje_yaz(tmp_path / "projects", "Sarki")
    monkeypatch.setattr(uyumluluk, "kontrol", _patlayan_kontrol)

    errors, warnings = validate_project.validate(proje)

    hepsi = " | ".join(errors)
    assert "fail-closed" in hepsi, (
        "kapı çöküşü HATA'ya düşmedi — render fail-open devam ederdi: %r"
        % (errors,))
    assert not any("uyumluluk" in w and "kapi" in w.lower() for w in warnings), (
        "kapı çöküşü hâlâ UYARI'ya yazılıyor")
    # Operatör neden video çıkmadığını ANLAMALI: mesaj hem sebebi hem yapılacağı
    # söylüyor.
    assert "KapiCoktu" in hepsi or "KOKLER" in hepsi


def test_validate_hatasi_render_i_durduruyor():
    """Bağlantı kanıtı: `errors` listesinin render'ı GERÇEKTEN durdurduğu.

    `render.render_project()` CANLI ÇAĞRILMIYOR (ffmpeg, saatler) — kaynak
    `ast` ile okunuyor: `if val_errors:` bloğu `return False` ile bitmeli.
    Bu satır bir gün "sadece uyar"a çevrilirse yukarıdaki HATA kararı sessizce
    anlamsızlaşırdı."""
    with open(os.path.join(_KOK, "render.py"), encoding="utf-8") as f:
        agac = ast.parse(f.read())
    bulundu = False
    for d in ast.walk(agac):
        if not (isinstance(d, ast.If) and isinstance(d.test, ast.Name)
                and d.test.id == "val_errors"):
            continue
        for alt in ast.walk(d):
            if (isinstance(alt, ast.Return) and isinstance(alt.value, ast.Constant)
                    and alt.value.value is False):
                bulundu = True
    assert bulundu, (
        "render.py'de `if val_errors: ... return False` yok — validate'in "
        "ürettiği HATA render'ı durdurmuyor")


# --- (f) MUHAFIZ: except dalı sessizce "devam et"e dönmesin --------------


def _kapi_try_bloklari(dosya):
    """Gövdesinde `uyumluluk.kontrol(...)` çağrısı olan `try` düğümleri."""
    with open(os.path.join(_KOK, dosya), encoding="utf-8") as f:
        agac = ast.parse(f.read())
    bulunan = []
    for d in ast.walk(agac):
        if not isinstance(d, ast.Try):
            continue
        for st in d.body:
            for c in ast.walk(st):
                if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and c.func.attr == "kontrol"
                        and isinstance(c.func.value, ast.Name)
                        and c.func.value.id == "uyumluluk"):
                    bulunan.append(d)
                    break
            else:
                continue
            break
    return bulunan


@pytest.mark.parametrize("dosya", ["auto_process.py", "dj_famous_process.py"])
def test_muhafiz_kapi_except_dali_return_ile_bitiyor(dosya):
    """Gelecekte biri `except` dalını sessizce "devam et"e çevirmesin.

    Sınanan şey DAR ve KASITLI: yalnızca gövdesinde `uyumluluk.kontrol()`
    çağrısı olan `try`. `rapor_yaz`ı saran İKİNCİ try bilerek DIŞARIDA — o
    kapı kararı değil raporlama, `return` etmesi YANLIŞ olurdu (bkz.
    test_rapor_yaz_patlarsa_temiz_yayin_DURMUYOR)."""
    bloklar = _kapi_try_bloklari(dosya)
    assert len(bloklar) == 1, (
        "%s: `uyumluluk.kontrol()` saran try sayısı %d — muhafız hangisine "
        "bakacağını bilemez" % (dosya, len(bloklar)))
    handlerlar = bloklar[0].handlers
    assert handlerlar, "%s: kapı try'ının except dalı yok" % dosya
    for h in handlerlar:
        son = h.body[-1]
        assert isinstance(son, (ast.Return, ast.Raise)), (
            "%s: uyumluluk kapısının `except` dalı `return`/`raise` ile "
            "BİTMİYOR (son ifade: %s) — kapı FAIL-OPEN'a döndürülmüş"
            % (dosya, type(son).__name__))


def test_muhafiz_validate_except_dali_errors_a_yaziyor():
    """validate_project'te fail-closed'ın biçimi FARKLI (fonksiyon `return`
    etmiyor, liste döndürüyor) — muhafız da ona göre: istisna `errors`a
    yazılmalı, `warnings`e DEĞİL."""
    bloklar = _kapi_try_bloklari("validate_project.py")
    assert len(bloklar) == 1
    for h in bloklar[0].handlers:
        hedefler = set()
        for c in ast.walk(h):
            if (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "append"
                    and isinstance(c.func.value, ast.Name)):
                hedefler.add(c.func.value.id)
        assert "errors" in hedefler, (
            "validate_project: kapı çöküşü `errors`a yazılmıyor (%s) — "
            "render fail-open devam eder" % sorted(hedefler))
        assert "warnings" not in hedefler, (
            "validate_project: kapı çöküşü hâlâ `warnings`e yazılıyor — "
            "uyarı render'ı durdurmaz")


def test_muhafiz_yalan_yorum_kalmadi():
    """"gormezden geliniyor" ifadesi uyumluluk kapısının çevresinde ARTIK YOK.

    Yorumun kendisi bir GARANTİ ifade ediyordu ve istisna dalı onu çürütüyordu
    (CLAUDE.md: "yalan söyleyen yorum, hiç yorum olmamasından KÖTÜDÜR")."""
    for dosya in ("auto_process.py", "dj_famous_process.py"):
        with open(os.path.join(_KOK, dosya), encoding="utf-8") as f:
            satirlar = f.read().splitlines()
        for i, s in enumerate(satirlar):
            if "uyumluluk kontrolu HATA (gormezden geliniyor)" in s:
                pytest.fail(
                    "%s:%d — fail-open satırı hâlâ duruyor: %s"
                    % (dosya, i + 1, s.strip()))
