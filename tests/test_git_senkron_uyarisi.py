# -*- coding: utf-8 -*-
"""`saglik_kontrol.git_senkron()` — sessizce devre dışı kalan git push hattı.

GERÇEK VAKA (regresyon çapası, 2026-09-05 -> 2026-09-12): Instagram ve TikTok
bio linki `famousmusicstudio.com/latest.html`'e gidiyor; caption'larda dış link
BİLEREK olmadığı için o iki platformdan çıkan TEK tıklanabilir yol bu sayfa.
`latest_release.regenerate()` saatlik hatta doğru bağlıydı ve sayfayı DİSKTE
her koşuda güncelliyordu, ama `git_sync.push_path()` ilk iş olarak dala bakıp
`main` değilse sessizce `return` ediyor. Üretim klasörü `claude/...` dalında
durduğu için push HİÇ olmadı: canlı sayfada 14 giriş, diskte 20 — altı
yayındaki içerik yedi gün boyunca bio linkinden görünmedi ve log'a tek satır,
telefona tek bildirim düşmedi.

Dal kapısının KENDİSİ doğru (gerekçesi git_sync.py'nin docstring'inde) ve bu
testler onu değiştirmiyor; kapının SESSİZLİĞİNİ kapatan kontrolü kilitliyorlar.

BU TESTLERDE GERÇEK BİR ŞEY ÇALIŞMIYOR: git katmanı (`_git_oku`), diskteki
sayfa (`_yerel_sayfa_metni`), saat (`time.time`), `notify` modülü ve durum
dosyası tamamen monkeypatch'li. Fikstür `_git_oku`yu varsayılan olarak
"patlat" yapıyor — bir test git katmanını kurmayı unutursa sessizce gerçek
git'i çağırmak yerine gürültüyle düşer. Hiçbir git YAZMA komutu yok; bunu
ayrıca `ast` ile de doğruluyoruz (test_git_cagrilari_yalnizca_salt_okuma).
"""

import ast
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import pytest

import saglik_kontrol as SK

SAAT = 3600.0
T0 = 1_757_000_000.0

# Canlıdaki 14 + diskteki 20 — gerçek vakanın sayıları.
CANLI_IDS = ["vid%02d" % i for i in range(14)]
YEREL_IDS = ["vid%02d" % i for i in range(20)]


def _sayfa(ids, yeni_sablon=True):
    """`docs/latest.html` taklidi.

    İKİ şablon var ve bu bilerek: canlıdaki sürüm 2026-09-05 tarihli ESKİ
    şablon (satırda düz metin), diskteki sürüm 2026-09-11 tasarım yenilemesi
    (küçük resim `<img>` + `<span>`). Kontrolün ölçütü bu yüzden `<li>` saymak
    DEĞİL, benzersiz YouTube video kimliği kümesi olmak zorunda.
    """
    if yeni_sablon:
        satir = ('    <li><a href="https://youtu.be/{v}">'
                 '<img src="https://i.ytimg.com/vi/{v}/mqdefault.jpg" alt="" '
                 'width="88" height="50" loading="lazy" decoding="async">'
                 '<span>{v} şarkısı</span></a></li>')
    else:
        satir = '    <li><a href="https://youtu.be/{v}">{v} şarkısı</a></li>'
    govde = "\n".join(satir.format(v=v) for v in ids)
    return ('<!DOCTYPE html>\n<html lang="tr"><body><main>\n'
            '  <h2>Şarkılar</h2>\n  <ul>\n%s\n  </ul>\n'
            '</main></body></html>\n' % govde)


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))

    gonderilen = []
    m = types.ModuleType("notify")
    m.send = lambda baslik, mesaj, *a, **k: (gonderilen.append((baslik, mesaj)), True)[1]
    monkeypatch.setitem(sys.modules, "notify", m)

    def _git_yasak(argv, timeout=20):
        raise AssertionError("test git katmanını kurmadı: %r" % (list(argv),))

    def _sayfa_yasak():
        raise AssertionError("test diskteki sayfayı kurmadı")

    monkeypatch.setattr(SK, "_git_oku", _git_yasak)
    monkeypatch.setattr(SK, "_yerel_sayfa_metni", _sayfa_yasak)
    return types.SimpleNamespace(gonderilen=gonderilen, monkeypatch=monkeypatch,
                                 tmp=tmp_path)


def _kur(o, dal, canli, yerel, show_rc=0, git_yok=False):
    """Sahte git + sahte disk sayfası."""
    if git_yok:
        o.monkeypatch.setattr(SK, "_git_oku", lambda argv, timeout=20: None)
    else:
        def sahte(argv, timeout=20):
            argv = list(argv)
            if argv[0] == "rev-parse":
                return 0, dal + "\n"
            if argv[0] == "show":
                assert argv[1] == "origin/main:docs/latest.html", argv
                if show_rc != 0:
                    return show_rc, ""
                return 0, _sayfa(canli, yeni_sablon=False)
            raise AssertionError("beklenmeyen git çağrısı: %r" % (argv,))

        o.monkeypatch.setattr(SK, "_git_oku", sahte)
    o.monkeypatch.setattr(SK, "_yerel_sayfa_metni", lambda: _sayfa(yerel))


def _saat(o, t):
    o.monkeypatch.setattr(SK.time, "time", lambda: t)


# --- (a) dal main değil + canlı sayfa geride -> bildirim gider --------------

def test_dal_main_degil_ve_sayfa_geride_bildirim_gider(ortam):
    _kur(ortam, "claude/analiz-yap-sk8gpf", CANLI_IDS, YEREL_IDS)

    # İlk gözlem: ne kadardır geride olduğunu BİLMİYORUZ -> damga at, sus.
    _saat(ortam, T0)
    loglar = []
    ilk = SK.git_senkron(log=loglar.append)
    assert ilk["durum"] == "geride_yeni"
    assert (ilk["eksik"], ilk["canli"], ilk["yerel"]) == (6, 14, 20)
    assert ortam.gonderilen == []
    assert any("ilk gözlem" in l for l in loglar)

    # Eşiği (6 saat) aşınca telefon çalar.
    _saat(ortam, T0 + 7 * SAAT)
    loglar = []
    s = SK.git_senkron(log=loglar.append)
    assert s["durum"] == "geride"
    assert s["bildirildi"] is True
    assert s["eksik"] == 6
    assert any("UYARI: git senkron" in l for l in loglar)

    baslik, mesaj = ortam.gonderilen[0]
    assert baslik == "Bio linki sayfası bayat"
    # Eyleme dönük mesaj: kaç içerik eksik, hangi dal, düzeltme ne.
    assert "6 yayındaki içerik" in mesaj
    assert "canlıda 14 giriş, olması gereken 20" in mesaj
    assert "claude/analiz-yap-sk8gpf" in mesaj
    assert "'main' dalında çalışır" in mesaj
    assert "git status" in mesaj
    assert "famousmusicstudio.com/latest.html" in mesaj


# --- (b) dal main -> sessiz -------------------------------------------------

def test_dal_main_ve_sayfa_guncel_tamamen_sessiz(ortam):
    _kur(ortam, "main", YEREL_IDS, YEREL_IDS)
    loglar = []
    s = SK.git_senkron(log=loglar.append)
    assert s == {"durum": "tamam", "dal": "main", "canli": 20, "yerel": 20,
                 "eksik": 0}
    assert loglar == []
    assert ortam.gonderilen == []


def test_dal_main_ama_sayfa_geride_mesaj_pushu_suclar(ortam):
    """Dal doğruyken de geri kalabilir: ağ yok / uzak taraf ileride / red.

    Ölçütün dal DEĞİL sonuç olmasının tek sebebi bu: dal kapısı açıkken de
    `push_path()` sessizce vazgeçiyor.
    """
    _kur(ortam, "main", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0)
    SK.git_senkron(log=lambda *a: None)
    _saat(ortam, T0 + 7 * SAAT)
    s = SK.git_senkron(log=lambda *a: None)

    assert s["bildirildi"] is True
    _, mesaj = ortam.gonderilen[0]
    assert "kapı AÇIK" in mesaj
    assert "push'un kendisi" in mesaj
    assert "auto_process.log" in mesaj


# --- (c) dal main değil ama sayfa güncel -> bildirim YOK --------------------

def test_dal_farkli_ama_sayfa_guncelse_telefon_calmaz(ortam):
    """Yanlış alarm yönetiminin kalbi.

    Kullanıcı bilerek başka bir dalda çalışıyor olabilir (şu an öyle). Sayfa
    geri kalmadıysa ORTADA ZARAR YOK: en fazla tek bir log satırı düşer.
    Her saat "dal main değil" diye bağırmak, yanındaki gerçek uyarıları da
    değersizleştirirdi.
    """
    _kur(ortam, "claude/analiz-yap-sk8gpf", YEREL_IDS, YEREL_IDS)
    loglar = []
    s = SK.git_senkron(log=loglar.append)
    assert s["durum"] == "dal_farkli"
    assert s["eksik"] == 0
    assert ortam.gonderilen == []
    assert len(loglar) == 1
    assert "Bildirim gönderilmedi" in loglar[0]
    assert "UYARI" not in loglar[0]


def test_esik_altinda_log_var_bildirim_yok(ortam):
    """Tek koşuluk gecikme arıza değil: `push_path()` zaten yeniden deniyor."""
    _kur(ortam, "main", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0)
    SK.git_senkron(log=lambda *a: None)

    _saat(ortam, T0 + 3 * SAAT)
    loglar = []
    s = SK.git_senkron(log=loglar.append)
    assert s["durum"] == "geride_esik_alti"
    assert "bildirildi" not in s
    assert ortam.gonderilen == []
    assert any("UYARI: git senkron" in l for l in loglar)


# --- (d) origin/main yok / bozuk -> çökmez, sessiz --------------------------

def test_origin_main_refi_yoksa_cokmez_ve_susar(ortam):
    _kur(ortam, "main", CANLI_IDS, YEREL_IDS, show_rc=128)
    loglar = []
    s = SK.git_senkron(log=loglar.append)
    assert s == {"durum": "atlandi", "sebep": "origin/main okunamadi",
                 "dal": "main"}
    assert loglar == []
    assert ortam.gonderilen == []


def test_origin_main_bos_donerse_susar(ortam):
    """rc=0 ama çıktı boş: bozuk/kesilmiş ref. "Bilmiyorum" -> sessiz."""
    def sahte(argv, timeout=20):
        if list(argv)[0] == "rev-parse":
            return 0, "main\n"
        return 0, "   \n"

    ortam.monkeypatch.setattr(SK, "_git_oku", sahte)
    ortam.monkeypatch.setattr(SK, "_yerel_sayfa_metni", lambda: _sayfa(YEREL_IDS))
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "atlandi"
    assert ortam.gonderilen == []


def test_git_yoksa_atlanir(ortam):
    """Git deposu olmayan bir checkout / CI: gürültü üretme."""
    _kur(ortam, "main", CANLI_IDS, YEREL_IDS, git_yok=True)
    s = SK.git_senkron(log=lambda *a: None)
    assert s == {"durum": "atlandi", "sebep": "git okunamadi"}
    assert ortam.gonderilen == []


def test_diskteki_sayfa_yoksa_atlanir(ortam):
    def sahte(argv, timeout=20):
        return 0, "main\n"

    ortam.monkeypatch.setattr(SK, "_git_oku", sahte)
    ortam.monkeypatch.setattr(SK, "_yerel_sayfa_metni", lambda: None)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "atlandi"
    assert s["sebep"] == "yerel sayfa yok"
    assert ortam.gonderilen == []


# --- (e) aynı arıza ikinci kez -> bastırılır --------------------------------

def test_ayni_gun_ikinci_bildirim_bastirilir(ortam):
    _kur(ortam, "claude/dal", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0)
    SK.git_senkron(log=lambda *a: None)
    _saat(ortam, T0 + 7 * SAAT)
    assert SK.git_senkron(log=lambda *a: None)["bildirildi"] is True

    # Saatlik hat bir saat sonra aynı arızayı yine görüyor: telefon SUSAR.
    _saat(ortam, T0 + 8 * SAAT)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "geride"
    assert s["bildirildi"] is False
    assert len(ortam.gonderilen) == 1


def test_gonderim_basarisizsa_damga_atilmaz_ve_yeniden_denenir(ortam):
    """`_bildir` sözleşmesi: damga YALNIZCA gönderim başarılıysa.

    Aynı tuzak bu modülde bir kez düzeltildi (bkz. _bildir docstring'i);
    yeni bir çağıran onu geri getirmesin diye burada da kilitli.
    """
    import notify
    ortam.monkeypatch.setattr(notify, "send", lambda *a, **k: False)
    _kur(ortam, "claude/dal", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0)
    SK.git_senkron(log=lambda *a: None)
    _saat(ortam, T0 + 7 * SAAT)
    assert SK.git_senkron(log=lambda *a: None)["bildirildi"] is False

    ortam.monkeypatch.setattr(notify, "send",
                              lambda b, m, *a, **k: (ortam.gonderilen.append((b, m)), True)[1])
    _saat(ortam, T0 + 8 * SAAT)
    assert SK.git_senkron(log=lambda *a: None)["bildirildi"] is True
    assert len(ortam.gonderilen) == 1


# --- Ölçüt ve damga davranışı ----------------------------------------------

def test_sablon_degisse_de_sayim_dogru(ortam):
    """Canlı ESKİ şablon, disk YENİ şablon, aynı videolar -> geri kalma YOK.

    `<li>` saymak da bu vakada doğru cevabı verirdi; kimlik kümesi ise satır
    düzeni tamamen değişse bile verir. Ölçüt markup'a bağlı OLMAMALI.
    """
    _kur(ortam, "main", YEREL_IDS, YEREL_IDS)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "tamam"
    assert s["canli"] == s["yerel"] == 20


def test_canlida_fazla_giris_alarm_uretmez(ortam):
    """Yön tek taraflı: "diskte var, canlıda yok". Tersi bir geri çekilmedir."""
    _kur(ortam, "main", YEREL_IDS, CANLI_IDS)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "tamam"
    assert s["eksik"] == 0
    assert ortam.gonderilen == []


def test_sayfa_yetisince_damga_silinir_ve_sayac_sifirlanir(ortam):
    """Eşik "kaç saattir GERİDE"yi ölçüyor, "kaç saattir başka dalda"yı değil."""
    _kur(ortam, "claude/dal", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0)
    SK.git_senkron(log=lambda *a: None)
    assert SK._durum().get(SK.GIT_SENKRON_DAMGASI) == T0

    # Push yetişti.
    _kur(ortam, "claude/dal", YEREL_IDS, YEREL_IDS)
    _saat(ortam, T0 + 2 * SAAT)
    SK.git_senkron(log=lambda *a: None)
    assert not SK._durum().get(SK.GIT_SENKRON_DAMGASI)

    # Yeniden geri kaldı: ESKİ damgadan devam edip anında bağırmamalı.
    _kur(ortam, "claude/dal", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0 + 3 * SAAT)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "geride_yeni"
    assert ortam.gonderilen == []


def test_damga_gelecekteyse_sifirlanir(ortam):
    """Sistem saati geri alınmış: ölçüm anlamsız, alarm verme."""
    _kur(ortam, "claude/dal", CANLI_IDS, YEREL_IDS)
    _saat(ortam, T0 + 10 * SAAT)
    SK.git_senkron(log=lambda *a: None)
    _saat(ortam, T0)
    s = SK.git_senkron(log=lambda *a: None)
    assert s["durum"] == "geride_yeni"
    assert ortam.gonderilen == []
    assert SK._durum().get(SK.GIT_SENKRON_DAMGASI) == T0


# --- Türkçe konsol tuzağı (cp1254) -----------------------------------------

def test_tum_metinler_cp1254e_kodlanabiliyor(ortam):
    """Bu modül `python saglik_kontrol.py` ile ELLE de çalıştırılıyor ve bu
    makinede `sys.stdout.encoding` ANSI kod sayfası (cp1254).

    Türkçenin `ı İ ş ğ` harfleri cp1254'te VAR ama `→` `✓` `•` gibi süs
    karakterleri YOK. Aynı tuzak bu depoda İKİ kez arıza üretti
    (`upload/tiktok_publish_plan.py` caption emojisi, `kacan_kosu`'nun ok
    işareti) — biri modülün TEK işini `UnicodeEncodeError` ile çökertmişti.
    Burada hem log satırları hem bildirim başlığı/gövdesi kilitli.

    Süre metni GÜN formatını da geçsin diye boşluk 7 gün (gerçek vakanın
    süresi): `_geri_kalma_metni` 48 saatten sonra "7 gün 0 sa" yazıyor.
    """
    _kur(ortam, "claude/analiz-yap-sk8gpf", CANLI_IDS, YEREL_IDS)
    loglar = []
    _saat(ortam, T0)
    SK.git_senkron(log=loglar.append)
    _saat(ortam, T0 + 7 * 24 * SAAT)
    SK.git_senkron(log=loglar.append)

    # Dal farklı + sayfa güncel dalının log satırı da dahil olsun.
    _kur(ortam, "claude/analiz-yap-sk8gpf", YEREL_IDS, YEREL_IDS)
    SK.git_senkron(log=loglar.append)

    baslik, mesaj = ortam.gonderilen[0]
    assert "7 gün" in mesaj
    for metin in loglar + [baslik, mesaj]:
        metin.encode("cp1254")   # patlarsa elle koşu çöker


# --- Bağlantı ve güvenlik korumaları ---------------------------------------

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KAYNAK = os.path.join(_KOK, "saglik_kontrol.py")

# `_git_oku`ya girmesine izin verilen git fiilleri — hepsi SALT OKUMA.
# Ağa çıkan (fetch/pull/push) ve yazan (add/commit/checkout/branch/reset/
# stash/merge/rebase) fiiller BİLEREK yok: bu bir TANI adımı, bir sağlık
# kontrolünün yan etkisi olarak depo durumu değişemez.
_IZINLI_GIT_FIILLERI = {"rev-parse", "show", "status", "log", "ls-files",
                        "cat-file", "diff"}


def test_git_cagrilari_yalnizca_salt_okuma():
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    cagrilar = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Call):
            continue
        ad = dugum.func.id if isinstance(dugum.func, ast.Name) else None
        if ad != "_git_oku":
            continue
        assert dugum.args, "_git_oku argümansız çağrılmış"
        liste = dugum.args[0]
        assert isinstance(liste, ast.List) and liste.elts, (
            "_git_oku'ya git argümanları DÜZ BİR LİSTE olarak verilmeli — "
            "değişkenden gelen bir komut bu koruma tarafından denetlenemez")
        fiil = liste.elts[0]
        assert isinstance(fiil, ast.Constant) and isinstance(fiil.value, str)
        cagrilar.append(fiil.value)

    assert cagrilar, "saglik_kontrol.py artık git okumuyor mu?"
    for fiil in cagrilar:
        assert fiil in _IZINLI_GIT_FIILLERI, (
            "SALT OKUMA olmayan git fiili: %r" % fiil)


def test_kontrol_et_git_senkronu_cagiriyor():
    """CLAUDE.md'nin birinci dersi: yazıldı ama HİÇBİR YERDEN çağrılmıyor.

    `auto_process.main()`in `finally` bloğu `kontrol_et()`i zaten çağırıyor;
    tek eksik halka bu sözlük anahtarı. `ast` ile doğrulanıyor, çünkü
    fonksiyonu çalıştırmak gerçek PowerShell/ağ/token dosyalarına dokunurdu.
    """
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    hedef = next(d for d in ast.walk(agac)
                 if isinstance(d, ast.FunctionDef) and d.name == "kontrol_et")
    anahtarlar = [k.value for d in ast.walk(hedef)
                  if isinstance(d, ast.Dict)
                  for k in d.keys
                  if isinstance(k, ast.Constant)]
    assert "git_senkron" in anahtarlar
