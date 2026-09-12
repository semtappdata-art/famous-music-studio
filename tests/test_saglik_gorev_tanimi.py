# -*- coding: utf-8 -*-
"""`saglik_kontrol.gorev_tanimlari()` — görev TANIMI denetiminin koruma testi.

NEDEN VAR (2026-09-11 23:15): o gece otomasyon tamamen durmuştu ve sebep
Python'da DEĞİLDİ — Windows'un görev kaydındaydı. İki ayrı arıza üst üste:

  A) `New-ScheduledTaskSettingsSet`'in VARSAYILANI "pilde başlatma" + "pile
     geçince durdur"; `setup_task_scheduler.ps1` bu iki bayrağı yazmadığı için
     dizüstü fişten çekilince üç görev de sessizce öldü.
  B) Kayıtlı görevler hâlâ ESKİ tanımı taşıyordu (`gorev_sarmalayici.py` YOK) —
     görev tanımı `git pull` ile YAYILMADIĞI için ps1'deki düzeltmeler üretime
     hiç ulaşmamıştı.

Bu testler denetimin İKİSİNİ de yakaladığını kilitliyor. Önemlisi: (A)'nın
düzeltmesi `.ps1` dosyasında, yani Python testlerinin göremediği bir yerde —
tek bağlantı bu denetim. Denetim sessizce bozulursa arıza yeniden GÖRÜNMEZ
olur (CLAUDE.md: "Sessizce False/{} dönen bir koruma, OLMAYAN korumadan
KÖTÜDÜR").

`_gorev_tanimlarini_oku()` her testte taklit ediliyor: gerçek
`Get-ScheduledTask` çağrılmıyor, hiçbir görev okunmuyor/değiştirilmiyor ve
test makineden bağımsız (CI'da da koşar).
"""

import io
import os
import re
import sys
import types

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import saglik_kontrol as SK


def _kayit(ad, arg, pilde_baslamasin=False, pilde_dursun=False):
    return {"ad": ad, "arg": arg,
            "pilde_baslamasin": pilde_baslamasin,
            "pilde_dursun": pilde_dursun}


SAGLAM = [
    _kayit("FamousMusicStudio-AutoProcess",
           "gorev_sarmalayici.py auto_process.py"),
    _kayit("FamousMusicStudio-DjFamousProcess",
           "gorev_sarmalayici.py dj_famous_process.py"),
    _kayit("FamousMusicStudio-Watcher",
           "gorev_sarmalayici.py watch_projects.py"),
]

# 2026-09-11 23:15'te GERÇEKTEN ölçülen hâl.
BOZUK_CANLI = [
    _kayit("FamousMusicStudio-AutoProcess", "auto_process.py", True, True),
    _kayit("FamousMusicStudio-DjFamousProcess", "dj_famous_process.py", True, True),
    _kayit("FamousMusicStudio-Watcher", "watch_projects.py", True, True),
]


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    """notify SAHTE (ağa çıkmaz) + durum dosyası tmp'ye (üretim dosyası yok)."""
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "durum.json"))
    gonderilen = []
    m = types.ModuleType("notify")
    m.send = lambda b, msg, **k: (gonderilen.append((b, msg)), True)[1]
    m.is_configured = lambda: True
    m.uyar_bir_kez = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "notify", m)
    # CI (Linux) da bu testleri koşsun diye `os.name` YALNIZCA bu modülde "nt"
    # gösteriliyor. GERÇEK `os` modülüne DOKUNULMUYOR (monkeypatch ile bile):
    # `os.name`'i global olarak değiştirmek, test süresince pytest'in ve
    # stdlib'in kendi platform dallarını da saptırırdı.
    monkeypatch.setattr(
        SK, "os",
        types.SimpleNamespace(name="nt", path=os.path, environ=os.environ))
    return gonderilen


def _kur(monkeypatch, veri):
    monkeypatch.setattr(SK, "_gorev_tanimlarini_oku", lambda: veri)


def test_canli_bozuk_durumu_yakaliyor(ortam, monkeypatch):
    """23:15'te ölçülen tanımlar: HEM sarmalayıcı yok HEM pil ayarları yanlış."""
    _kur(monkeypatch, BOZUK_CANLI)
    satirlar = []
    s = SK.gorev_tanimlari(satirlar.append)

    assert s["durum"] == "bozuk"
    # Üç görev x üç sorun = 9; hiçbiri sessizce yutulmamalı.
    assert len(s["sorunlar"]) == 9
    for ad in SK.GOREV_BETIKLERI:
        assert s["gorevler"][ad]["sarmalayici"] is False
        assert s["gorevler"][ad]["pil_tamam"] is False
    # log'a da düşmeli: bildirim kanalı ölü olsa bile bilgi kaybolmasın.
    assert len(satirlar) == 9
    # Telefona TEK bildirim, ve çözümü SÖYLEYEN bir bildirim.
    assert len(ortam) == 1
    assert "setup_task_scheduler.ps1" in ortam[0][1]


def test_saglam_tanim_sessiz(ortam, monkeypatch):
    _kur(monkeypatch, SAGLAM)
    satirlar = []
    s = SK.gorev_tanimlari(satirlar.append)

    assert s["durum"] == "tamam"
    assert satirlar == []
    assert ortam == []                    # gürültü yok
    assert s["eksik"] == []


def test_sadece_pil_ayari_bozuksa_yakalanir(ortam, monkeypatch):
    """A1'in TEK BAŞINA nüksetmesi — sarmalayıcı doğru kurulmuş olsa bile.

    Bu senaryo tam olarak "ps1 yeniden yazıldı ama pil bayrakları yine
    unutuldu" hâli; denetimin var olma sebeplerinden biri bu.
    """
    veri = [_kayit("FamousMusicStudio-AutoProcess",
                   "gorev_sarmalayici.py auto_process.py",
                   pilde_baslamasin=True, pilde_dursun=True)]
    _kur(monkeypatch, veri)
    s = SK.gorev_tanimlari(lambda _s: None)

    assert s["durum"] == "bozuk"
    assert len(s["sorunlar"]) == 2
    assert all("sarmalay" not in x for x in s["sorunlar"])
    assert s["gorevler"]["FamousMusicStudio-AutoProcess"]["sarmalayici"] is True


def test_sadece_sarmalayici_eksikse_yakalanir(ortam, monkeypatch):
    veri = [_kayit("FamousMusicStudio-Watcher", "watch_projects.py")]
    _kur(monkeypatch, veri)
    s = SK.gorev_tanimlari(lambda _s: None)

    assert s["durum"] == "bozuk"
    assert len(s["sorunlar"]) == 1
    assert "sarmalay" in s["sorunlar"][0]


@pytest.mark.parametrize("veri", [None, []])
def test_gorev_yoksa_sessizce_atlanir(ortam, monkeypatch, veri):
    """Kurulum yapılmamış bir checkout ya da PowerShell'siz bir ortam.

    Bu makineye ÖZEL bir denetim — yokluğunda uyarmak, gerçek uyarıları
    değersizleştiren gürültüdür.
    """
    _kur(monkeypatch, veri)
    satirlar = []
    s = SK.gorev_tanimlari(satirlar.append)

    assert s["durum"] == "atlandi"
    assert satirlar == []
    assert ortam == []


def test_gunde_bir_bildirim(ortam, monkeypatch):
    """Saatlik koşuda telefonun her saat çalması uyarıyı değersizleştirir."""
    _kur(monkeypatch, BOZUK_CANLI)
    SK.gorev_tanimlari(lambda _s: None)
    SK.gorev_tanimlari(lambda _s: None)
    SK.gorev_tanimlari(lambda _s: None)
    assert len(ortam) == 1


def test_kontrol_et_bu_adimi_gercekten_cagiriyor(ortam, monkeypatch):
    """BAĞLANTI testi — bu deponun en sık arıza sınıfı "yazıldı, çağrılmadı".

    `gorev_tanimlari()` doğru olsa bile `kontrol_et()`'e bağlanmazsa hiçbir
    zamanlayıcı görevinden çalışmaz; `saglik_kontrol.kontrol_et` ise
    `auto_process._saglik_kontrol()` üzerinden saatlik hatta bağlı TEK giriş.
    """
    _kur(monkeypatch, SAGLAM)
    monkeypatch.setattr(SK, "instagram_token_suresi", lambda log=print: {"durum": "yok"})
    monkeypatch.setattr(SK, "netlify_araci", lambda log=print: {"durum": "tamam"})
    s = SK.kontrol_et(lambda _s: None)
    assert s["gorev_tanimlari"]["durum"] == "tamam"


def test_modul_hicbir_gorevi_DEGISTIRMIYOR():
    """Salt-okunur sözleşme: `Get-*` dışında bir ScheduledTask fiili olmamalı.

    Bir sağlık kontrolünün yan etkisi olarak görev kaydetmek/silmek/başlatmak,
    tanıyı onarıma çevirir — ve bu script mevcut görevleri SİLİP yeniden
    kuruyor (yükseltilmiş izin isteyebiliyor). O adım bilerek KULLANICININ.
    """
    yol = os.path.join(_REPO, "saglik_kontrol.py")
    kaynak = io.open(yol, encoding="utf-8").read()

    # YORUMLAR ÇIKARILIYOR: modülün kendi açıklaması "Register-/Set-/
    # Unregister-/Start-ScheduledTask BURAYA ASLA GİRMEZ" diye YAZIYOR ve
    # yorumu tarayan bir kontrol tam da o cümleyi ihlal sanardı — yani kuralı
    # yazıya dökmek testi kırardı. Taranan şey ÇALIŞAN kod olmalı.
    import tokenize
    with tokenize.open(yol) as f:
        kod = "".join(
            "" if tok.type == tokenize.COMMENT else tok.string
            for tok in tokenize.generate_tokens(f.readline))

    yasak = re.findall(
        r"\b(Register|Unregister|Set|Start|Stop|Disable|Enable)-ScheduledTask\w*",
        kod)
    assert yasak == [], "yasak fiil(ler): %s" % yasak
    assert "Get-ScheduledTask" in kod          # denetim GERÇEKTEN okuyor
    assert "Get-ScheduledTask" in kaynak
