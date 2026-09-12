# -*- coding: utf-8 -*-
"""`saglik_kontrol.kacan_kosu()` — kaçan saatlik koşuyu yakalayan kontrol.

GERÇEK VAKA (regresyon çapası): `auto_process.log`'da 11 Eylül 21:12 ile
12 Eylül 06:46 arasında 9,5 saatlik bir boşluk var. Dokuz saatlik tetik
(22:12, 23:12, 00:12 ... 06:12) kaçtı ve log'a TEK BİR SATIR bile düşmedi —
kaçan koşunun imzası tam olarak budur: geriye hiçbir iz bırakmaz. Sebep:
üç Görev Zamanlayıcı görevi de `DisallowStartIfOnBatteries` /
`StopIfGoingOnBatteries` ile kurulu, makine fişten çıkınca otomasyonun tamamı
sessizce duruyor; dakikalık Watcher da aynı sebeple ölü olduğu için ikinci
emniyet ağı da yoktu.

BU TESTLERDE GERÇEK BİR ŞEY ÇALIŞMIYOR: `notify` modülü, saat (`time.time`),
güç durumu sorgusu (`_guc_durumu`, yani PowerShell/WMI) ve durum dosyası
tamamen monkeypatch'li. Hiçbir ağ çağrısı, hiçbir PowerShell süreci yok —
sahte katman kurulmadan bir gönderim denenirse test bilerek patlar.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import pytest

import saglik_kontrol as SK

SAAT = 3600.0


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    """Durum dosyası tmp'de, notify sahte, PowerShell KESİNLİKLE kapalı.

    `_guc_durumu` varsayılan olarak "patlat" — böylece bir testte güç dalını
    kurmayı unutmak sessizce geçmez, gürültüyle görünür.
    """
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))

    gonderilen = []
    m = types.ModuleType("notify")
    m.send = lambda baslik, mesaj, *a, **k: (gonderilen.append((baslik, mesaj)), True)[1]
    monkeypatch.setitem(sys.modules, "notify", m)

    def _yasak():
        raise AssertionError("test güç durumunu kurmadı — gerçek PowerShell çağrılamaz")

    monkeypatch.setattr(SK, "_guc_durumu", _yasak)
    return types.SimpleNamespace(gonderilen=gonderilen, tmp=tmp_path,
                                 monkeypatch=monkeypatch)


def _saati_sabitle(monkeypatch, t):
    monkeypatch.setattr(SK.time, "time", lambda: t)


def _guc(monkeypatch, uyanik_sn, pilde=False, yuzde=17):
    """`_guc_durumu()` taklidi. uyanik_sn=None => "okunamadı" dalı."""
    if uyanik_sn is None:
        monkeypatch.setattr(SK, "_guc_durumu", lambda: None)
        return
    monkeypatch.setattr(SK, "_guc_durumu", lambda: {
        "acik_sn": uyanik_sn, "uyanma_sn": uyanik_sn, "uyanik_sn": uyanik_sn,
        "pil_durumu": 1 if pilde else 2, "pil_yuzde": yuzde, "pilde": pilde,
    })


# --- (d) ilk kurulum: damga yok -------------------------------------------

def test_ilk_kosu_cokmez_ve_sessiz_kalir(ortam):
    """Damga yokken hiçbir iddia yok: sessizce damgalanır, telefon çalmaz."""
    _saati_sabitle(ortam.monkeypatch, 1_000_000.0)
    satirlar = []
    s = SK.kacan_kosu(log=satirlar.append)

    assert s["durum"] == "ilk_kosu"
    assert ortam.gonderilen == []
    assert satirlar == []
    # Damga ATILMIŞ olmalı, yoksa ikinci koşu da kör kalırdı.
    assert SK._durum()[SK.SON_KOSU_ANAHTARI] == 1_000_000.0


def test_bozuk_damga_ilk_kosu_gibi_ele_alinir(ortam):
    """Durum dosyasındaki damga metin/None ise çökmemeli (eski sürüm kalıntısı)."""
    SK._kaydet({SK.SON_KOSU_ANAHTARI: "bozuk"})
    _saati_sabitle(ortam.monkeypatch, 2_000_000.0)
    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "ilk_kosu"
    assert ortam.gonderilen == []
    assert SK._durum()[SK.SON_KOSU_ANAHTARI] == 2_000_000.0


# --- (b) tek kaçan koşu = gürültü -----------------------------------------

@pytest.mark.parametrize("bosluk_saat", [1.0, 2.0, 3.0, 3.9])
def test_tek_iki_uc_kacan_kosu_bildirim_gondermez(ortam, bosluk_saat):
    """Eşiğin ALTI: kısa uyku, `-StartWhenAvailable` kayması ya da 2 saat
    süren bir koşunun yuttuğu tetikler. Telefon çalmamalı, log da susmalı."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + bosluk_saat * SAAT)

    satirlar = []
    s = SK.kacan_kosu(log=satirlar.append)

    assert s["durum"] == "tamam"
    assert ortam.gonderilen == []
    assert satirlar == []
    assert SK._durum()[SK.SON_KOSU_ANAHTARI] == t0 + bosluk_saat * SAAT


# --- (a) 9 saatlik boşluk: gerçek vaka ------------------------------------

def test_dokuz_saatlik_bosluk_makine_acikken_bildirim_gonderir(ortam):
    """11-12 Eylül vakası, makine AYAKTAYKEN: bu gerçek bir arıza."""
    t0 = 1_700_000_000.0
    bosluk = 9 * SAAT + 34 * 60                      # 21:12 -> 06:46
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + bosluk)
    # Makine 20 saattir kesintisiz ayakta -> boşluğu açıklamıyor.
    _guc(ortam.monkeypatch, uyanik_sn=20 * SAAT, pilde=True, yuzde=17)

    satirlar = []
    s = SK.kacan_kosu(log=satirlar.append)

    assert s["durum"] == "bosluk"
    assert s["makine_vardi"] is True
    assert s["kacan"] == 9, "9,57 saatlik boşluk -> ~9 kaçan tetik"
    assert s["bildirildi"] is True

    assert len(ortam.gonderilen) == 1
    baslik, mesaj = ortam.gonderilen[0]
    assert baslik == "Otomasyon sessiz kaldı"
    # EYLEME DÖNÜK olmalı: kaç koşu, hangi aralık, ilk bakılacak yer.
    assert "9 sa 34 dk" in mesaj
    assert "~9 koşu kaçtı" in mesaj
    assert " -> " in mesaj                            # aralık
    # Süs karakteri YOK: bu metin cp1254 konsoldan da basılabilmeli
    # (`python saglik_kontrol.py`). Bkz. kacan_kosu içindeki gerekçe.
    mesaj.encode("cp1254")
    assert baslik.encode("cp1254")
    assert "Görev Zamanlayıcı" in mesaj
    assert "setup_task_scheduler.ps1" in mesaj
    assert "PİLDE" in mesaj and "17" in mesaj
    # Log'a da düşmeli: bildirim hattı ölü olsa bile bilgi kaybolmasın.
    assert any("kaçan koşu" in x for x in satirlar)
    # Damga TAZELENMELİ, yoksa aynı boşluk sonsuza kadar raporlanırdı.
    assert SK._durum()[SK.SON_KOSU_ANAHTARI] == t0 + bosluk


def test_guc_durumu_okunamazsa_yine_bildirilir(ortam):
    """"Bilmiyorum" masumiyet karinesi DEĞİL — sessiz kalmak tam da bu modülün
    yakalamak için var olduğu deseni geri getirirdi."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 9 * SAAT)
    _guc(ortam.monkeypatch, uyanik_sn=None)

    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "bosluk"
    assert len(ortam.gonderilen) == 1
    assert "OKUNAMADI" in ortam.gonderilen[0][1]


# --- makine kapalı/uykuda = normal ----------------------------------------

def test_gece_kapali_dizustu_sabah_alarm_calmaz(ortam):
    """Kullanıcı kuralı: gece boyunca kapalı bir dizüstü için her sabah alarm
    çalmamalı. Boşluk 9,5 saat ama makine 20 dakikadır ayakta -> açıklanmış."""
    t0 = 1_700_000_000.0
    bosluk = 9.5 * SAAT
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + bosluk)
    _guc(ortam.monkeypatch, uyanik_sn=20 * 60)

    satirlar = []
    s = SK.kacan_kosu(log=satirlar.append)

    assert s["durum"] == "bosluk_aciklandi"
    assert s["makine_vardi"] is False
    assert ortam.gonderilen == [], "makine kapalıyken telefon çalmamalı"
    # Ama GÖRÜNMEZ de olmamalı: log'da izi kalıyor.
    assert any("KAPALI/UYKUDA" in x for x in satirlar)


def test_makine_kapali_olsa_bile_24_saat_sessizlik_bildirilir(ortam):
    """24 saatten sonra sebep önemsiz: kanal durmuş, tek eylem "makineyi aç"."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 26 * SAAT)
    _guc(ortam.monkeypatch, uyanik_sn=10 * 60)

    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "bosluk"
    assert s["makine_vardi"] is False
    assert len(ortam.gonderilen) == 1
    assert "KAPALI/UYKUDA" in ortam.gonderilen[0][1]


def test_uyku_uptime_ile_gizlenemez(ortam):
    """UYKU `LastBootUpTime`'ı SIFIRLAMAZ. Sadece uptime'a bakan bir kontrol
    gece uyuyan dizüstüyü "sürekli açıktı" sanırdı — `uyanik_sn` iki damganın
    KÜÇÜĞÜ olduğu için bu yakalanıyor."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 9 * SAAT)
    # 30 gündür açık (uptime), ama 15 dk önce uyandı.
    ortam.monkeypatch.setattr(SK, "_guc_durumu", lambda: {
        "acik_sn": 30 * 86400, "uyanma_sn": 15 * 60, "uyanik_sn": 15 * 60,
        "pil_durumu": 2, "pil_yuzde": 80, "pilde": False,
    })
    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "bosluk_aciklandi"
    assert ortam.gonderilen == []


# --- (c) aynı arıza ikinci kez: bastırılır --------------------------------

def test_ayni_ariza_ikinci_kosuda_telefonu_bir_daha_titretmez(ortam):
    """`_bildir`'in mevcut günde-bir mekanizması (anahtar + `_durum`) —
    saatlik koşuda aynı arıza için ikinci bildirim gitmemeli."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 9 * SAAT)
    _guc(ortam.monkeypatch, uyanik_sn=20 * SAAT)
    assert SK.kacan_kosu(log=lambda *a: None)["bildirildi"] is True
    assert len(ortam.gonderilen) == 1

    # Arıza sürüyor: bir saat sonra damga yine 9 saat geriye çekiliyor.
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0 + 1 * SAAT})
    _saati_sabitle(ortam.monkeypatch, t0 + 10 * SAAT)
    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "bosluk"
    assert s["bildirildi"] is False
    assert len(ortam.gonderilen) == 1, "aynı gün ikinci bildirim gitmemeli"


def test_bildirim_gonderilemezse_damga_atilmaz_ve_tekrar_denenir(ortam):
    """`notify.send` False dönerse (ağ yok / kanal kurulu değil) günlük damga
    atılmamalı — aksi hâlde uyarı o gün tamamen kaybolurdu."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 9 * SAAT)
    _guc(ortam.monkeypatch, uyanik_sn=20 * SAAT)

    olu = types.ModuleType("notify")
    olu.send = lambda *a, **k: False
    ortam.monkeypatch.setitem(sys.modules, "notify", olu)

    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["bildirildi"] is False
    assert "kacan_kosu_bildirim_gun" not in SK._durum()


# --- (e) log döndürülmesi yanlış alarm vermez -----------------------------

def test_log_dondurulmesi_yanlis_alarm_vermez(ortam, tmp_path):
    """KAYNAK LOG DEĞİL — kanıt.

    `log_rotate.trim_log()` 7 günden eski satırları atıp dosyayı yeniden
    yazıyor; maskeleme yaptığında satır sayısı değişmese bile yeniden yazıyor.
    Log'un son satırına ya da mtime'ına bağlı bir kontrol burada ya kör kalır
    ya da yanlış alarm verirdi. Bu test log dosyasını GERÇEKTEN döndürüyor
    (tamamen boşaltıp yeniden yazıyor) ve sonucun DEĞİŞMEDİĞİNİ gösteriyor.
    """
    import log_rotate

    log_dosyasi = tmp_path / "auto_process.log"
    log_dosyasi.write_text(
        "[2020-01-01 10:00:00] cok eski satir\n"
        "[2020-01-01 11:00:00] bu da eski\n", encoding="utf-8")

    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})

    # Döndürme: 7 günden eski her satır gidiyor, dosya bomboş kalıyor.
    log_rotate.trim_log(str(log_dosyasi))
    assert log_dosyasi.read_text(encoding="utf-8") == ""

    _saati_sabitle(ortam.monkeypatch, t0 + 2 * SAAT)
    s = SK.kacan_kosu(log=lambda *a: None)
    assert s["durum"] == "tamam", "log boşaldı diye alarm verilmemeli"
    assert ortam.gonderilen == []

    # Ve log tamamen silinse bile ölçüm aynı damgadan devam ediyor.
    log_dosyasi.unlink()
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 3 * SAAT)
    assert SK.kacan_kosu(log=lambda *a: None)["durum"] == "tamam"
    assert ortam.gonderilen == []


def test_kaynak_log_dosyasi_degil_damga(ortam):
    """Sağlamlaştırıcı: modül `auto_process.log` okumuyor.

    NEDEN AST/kaynak DEĞİL de böyle: `kacan_kosu` çalışırken hiçbir dosya
    açılmamalı (durum dosyası hariç). `open` sarmalanıp izleniyor."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0})
    _saati_sabitle(ortam.monkeypatch, t0 + 9 * SAAT)
    _guc(ortam.monkeypatch, uyanik_sn=20 * SAAT)

    acilanlar = []
    gercek_open = open

    def _izleyen_open(dosya, *a, **k):
        acilanlar.append(str(dosya))
        return gercek_open(dosya, *a, **k)

    import builtins
    ortam.monkeypatch.setattr(builtins, "open", _izleyen_open)
    SK.kacan_kosu(log=lambda *a: None)

    assert not any("auto_process.log" in y for y in acilanlar), acilanlar
    assert all("saglik_durum" in y or "tmp" in y.lower() for y in acilanlar), acilanlar


# --- saat geri alınması ---------------------------------------------------

def test_saat_geri_alinirsa_alarm_vermez(ortam):
    """Damga GELECEKTE (NTP düzeltmesi / elle saat değişimi): ölçüm anlamsız,
    damga sıfırlanır, telefon çalmaz."""
    t0 = 1_700_000_000.0
    SK._kaydet({SK.SON_KOSU_ANAHTARI: t0 + 5 * SAAT})
    _saati_sabitle(ortam.monkeypatch, t0)

    satirlar = []
    s = SK.kacan_kosu(log=satirlar.append)
    assert s["durum"] == "atlandi"
    assert ortam.gonderilen == []
    assert SK._durum()[SK.SON_KOSU_ANAHTARI] == t0
    assert any("saati" in x for x in satirlar)


# --- BAĞLANTI: kontrol_et gerçekten çağırıyor mu? -------------------------

def test_kontrol_et_kacan_kosuyu_cagiriyor(ortam, monkeypatch):
    """Bu deponun EN SIK arızası "yazıldı ama bağlanmadı" — `auto_process.py`
    yalnızca `kontrol_et()` çağırıyor, dolayısıyla kayıt ORADA olmak zorunda.
    """
    cagrildi = {}

    def sahte(log=print):
        cagrildi["log"] = log
        return {"durum": "tamam"}

    monkeypatch.setattr(SK, "kacan_kosu", sahte)
    monkeypatch.setattr(SK, "instagram_token_suresi", lambda log=print: {})
    monkeypatch.setattr(SK, "netlify_araci", lambda log=print: {})
    monkeypatch.setattr(SK, "gorev_tanimlari", lambda log=print: {})
    monkeypatch.setattr(SK, "ses_takip_tutarliligi", lambda log=print: {})

    sonuc = SK.kontrol_et(log=lambda *a: None)
    assert "kacan_kosu" in sonuc, "kontrol_et() toplayıcısına kaydedilmemiş"
    assert sonuc["kacan_kosu"] == {"durum": "tamam"}
    assert cagrildi.get("log") is not None, "log geçirilmemiş"


# --- güç sorgusu: gerçek PowerShell olmadan ayrıştırma --------------------

def test_guc_durumu_powershell_yoksa_none(monkeypatch):
    monkeypatch.setattr(SK, "_powershell_yolu", lambda: None)
    assert SK._guc_durumu() is None


def test_guc_durumu_ciktiyi_ayristiriyor(monkeypatch):
    """PowerShell ÇALIŞTIRILMIYOR — çıktısı taklit ediliyor."""
    monkeypatch.setattr(SK, "_powershell_yolu", lambda: "powershell.exe")

    class _P:
        returncode = 0
        stdout = json.dumps({"acik_sn": 72000, "uyanma_sn": 900,
                             "pil_durumu": 1, "pil_yuzde": 17}).encode("utf-8")
        stderr = b""

    monkeypatch.setattr(SK.subprocess, "run", lambda *a, **k: _P())
    g = SK._guc_durumu()
    assert g["uyanik_sn"] == 900, "kesintisiz ayakta = iki damganın KÜÇÜĞÜ"
    assert g["pilde"] is True
    assert g["pil_yuzde"] == 17


def test_guc_durumu_bozuk_ciktida_none(monkeypatch):
    monkeypatch.setattr(SK, "_powershell_yolu", lambda: "powershell.exe")

    class _P:
        returncode = 0
        stdout = b"bu JSON degil"
        stderr = b""

    monkeypatch.setattr(SK.subprocess, "run", lambda *a, **k: _P())
    assert SK._guc_durumu() is None


def test_guc_durumu_pil_yoksa_pilde_degil(monkeypatch):
    """Masaüstünde Win32_Battery hiç yok: pil_durumu 0 -> "pilde" olmamalı."""
    monkeypatch.setattr(SK, "_powershell_yolu", lambda: "powershell.exe")

    class _P:
        returncode = 0
        stdout = json.dumps({"acik_sn": 100, "uyanma_sn": -1,
                             "pil_durumu": 0, "pil_yuzde": -1}).encode("utf-8")
        stderr = b""

    monkeypatch.setattr(SK.subprocess, "run", lambda *a, **k: _P())
    g = SK._guc_durumu()
    assert g["pilde"] is False
    assert g["uyanik_sn"] == 100, "uyanma olayı yoksa (-1) sadece uptime sayılır"


def test_guc_sorgusu_sadece_okuyan_fiiller_iceriyor():
    """`Register-`/`Set-`/`Unregister-`/`Start-ScheduledTask` ASLA girmemeli —
    bir sağlık kontrolü Görev Zamanlayıcı'yı DEĞİŞTİREMEZ."""
    for yasak in ("Register-", "Set-Scheduled", "Unregister-", "Start-Scheduled",
                  "Remove-", "Stop-Process", "Restart-"):
        assert yasak not in SK._PS_GUC, yasak
    assert "Get-CimInstance" in SK._PS_GUC
