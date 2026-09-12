# -*- coding: utf-8 -*-
"""`ses_ve_tarz_takibi.md` muhafızı — hem bulguları hem ÇAĞRI YOLUNU doğrular.

NEDEN (2026-09-12): takip dosyası eksik/hatalıydı (üç gerçek üretim tabloda
yoktu), vokal çeşitliliği kuralı YANLIŞ bir geçmişe baktı ve son üç üretimin
üçü de erkek-erkek düet oldu. Dosya elle düzeltildi; bu testler düzeltmenin
değil, KORUMANIN testi.

İki ayrı şeyi birden bekçiliyor, çünkü bu deponun en sık arızası
(CLAUDE.md, "BAĞLANTI seviyesindeki sessiz arıza") fonksiyonun kendisinde
değil bağlantısında oluyor:

  A) Denetim doğru sonuç veriyor mu (temiz dosyada SUSUYOR, bozuk dosyada
     KONUŞUYOR, `(üretilmedi)` satırında yanlış pozitif üretmiyor,
     ayrıştıramadığında SESSİZCE GEÇMİYOR).
  B) Denetim gerçekten ÇAĞRILIYOR mu — auto_process.main()'in finally
     bloğundan saglik_kontrol üzerinden ses_takip_denetimi.denetle()'ye kadar
     zincirin her halkası (`ast` ile, kaynak üzerinden).
"""

import ast
import io
import os
import sys
import types

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import pytest

import saglik_kontrol as SK
import ses_takip_denetimi as STD


def _kaynak_agaci(ad):
    return ast.parse(io.open(os.path.join(_REPO, ad), encoding="utf-8").read())


def _fonksiyon(agac, ad):
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name == ad:
            return d
    return None


def _cagri_adlari(dugum):
    """Bir AST alt ağacındaki tüm çağrıların adları ('f' ve 'mod.f')."""
    adlar = set()
    for n in ast.walk(dugum):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name):
            adlar.add(f.id)
        elif isinstance(f, ast.Attribute):
            adlar.add(f.attr)
            if isinstance(f.value, ast.Name):
                adlar.add("%s.%s" % (f.value.id, f.attr))
    return adlar


# --------------------------------------------------------------------------
# A) Bulgular
# --------------------------------------------------------------------------

def test_gercek_dosya_temiz():
    """BUGÜNKÜ GERÇEK dosya + GERÇEK `projects/` -> tek uyarı bile YOK.

    Bu testin asıl işi yanlış pozitif avlamak: `(üretilmedi)` işaretli Neon
    Kalp satırı, "Gece Sürüşü *(eski adı: Shudhniy L)*" gibi markdown süslü
    adlar ve "elektronik (Afro-House/Arabic EDM)" gibi parantezli tema
    hücreleri burada canlı olarak deneniyor. Uyarı üreten bir muhafız,
    her koşuda gürültü yapan ve bu yüzden görmezden gelinen bir muhafızdır.
    """
    s = STD.denetle()
    assert s["uyarilar"] == [], s["uyarilar"]
    assert s["durum"] == "tamam"
    # Disk gerçekten taranmış olmalı: boş bir küme de "uyarı yok" verirdi.
    assert s["proje_sayisi"] >= 18
    assert s["satir_sayisi"] >= s["proje_sayisi"]


def _bozuk_kopya(tmp_path, silinecek, tema_degis=None):
    """GERÇEK dosyanın bozulmuş bir KOPYASI (gerçek dosyaya DOKUNULMAZ)."""
    metin = io.open(STD.TAKIP_DOSYASI, encoding="utf-8").read()
    yeni = []
    for satir in metin.splitlines(True):
        if silinecek and satir.startswith("| %s |" % silinecek):
            continue
        if tema_degis and satir.startswith("| %s |" % tema_degis[0]):
            satir = satir.replace("| %s |" % tema_degis[1],
                                  "| %s |" % tema_degis[2], 1)
        yeni.append(satir)
    hedef = tmp_path / "ses_ve_tarz_takibi_BOZUK.md"
    hedef.write_text("".join(yeni), encoding="utf-8")
    return str(hedef)


def test_silinen_satir_uyari_uretir(tmp_path):
    """Tablodan bir satır silinince o proje 'diskte var, tabloda yok' olur."""
    yol = _bozuk_kopya(tmp_path, silinecek="Sofraya Gelmedin")
    s = STD.denetle(takip_dosyasi=yol)
    assert s["durum"] == "uyari"
    assert s["eksik_satir"] == ["Sofraya Gelmedin"]
    assert any("Sofraya Gelmedin" in u and "takip tablosunda YOK" in u
               for u in s["uyarilar"]), s["uyarilar"]


def test_degisen_tema_uyari_uretir(tmp_path):
    yol = _bozuk_kopya(tmp_path, silinecek=None,
                       tema_degis=("Kırık Zincir", "rock", "pop"))
    s = STD.denetle(takip_dosyasi=yol)
    assert s["durum"] == "uyari"
    assert s["tema_uyusmazligi"] == [
        {"ad": "Kırık Zincir", "tablo": "pop", "meta": "rock"}]


def test_iki_bozulma_ayni_anda(tmp_path):
    """Bugünkü elle kanıtın testteki karşılığı: bir satır silik, biri yanlış."""
    yol = _bozuk_kopya(tmp_path, silinecek="Sofraya Gelmedin",
                       tema_degis=("Kırık Zincir", "rock", "pop"))
    s = STD.denetle(takip_dosyasi=yol)
    assert len(s["uyarilar"]) == 2, s["uyarilar"]
    assert s["eksik_satir"] and s["tema_uyusmazligi"]


# --- sentetik tablo: yanlış pozitif ve ayrıştırma sınırları ---------------

_BASLIK = "| Şarkı | Tema | BPM | Vokal |\n|---|---|---|---|\n"


def _sahte_katalog(tmp_path, projeler):
    kok = tmp_path / "projects"
    kok.mkdir()
    for ad, tema in projeler.items():
        p = kok / ad
        p.mkdir()
        (p / "meta.json").write_text('{"theme": "%s"}' % tema, encoding="utf-8")
    return str(kok)


def _md(tmp_path, govde, ad="t.md"):
    y = tmp_path / ad
    y.write_text("# başlık\n\nmetin\n\n" + govde, encoding="utf-8")
    return str(y)


def test_uretilmedi_satiri_yanlis_pozitif_DEGIL(tmp_path):
    """`(üretilmedi)` işaretli satırın diskte karşılığı olmaması NORMAL.

    "Neon Kalp" satırı bilerek duruyor (fikir kayıtta kalsın diye). Onu
    hayalet saymak, her saatlik koşuda tekrarlayan bir yanlış pozitif
    demekti — ve tekrarlayan yanlış pozitif uyarıyı tümden değersizleştirir.
    """
    kok = _sahte_katalog(tmp_path, {"Gerçek Şarkı": "pop"})
    yol = _md(tmp_path, _BASLIK
              + "| Gerçek Şarkı | pop | 100 | x |\n"
              + "| Hayalet Fikir **(üretilmedi)** | rock | 120 | y |\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert s["durum"] == "tamam", s["uyarilar"]
    assert s["hayalet_satir"] == []


def test_isaretsiz_hayalet_satir_uyari_uretir(tmp_path):
    """Aynı satır işaret OLMADAN duruyorsa artık uyarı vermeli (karşı kanıt)."""
    kok = _sahte_katalog(tmp_path, {"Gerçek Şarkı": "pop"})
    yol = _md(tmp_path, _BASLIK
              + "| Gerçek Şarkı | pop | 100 | x |\n"
              + "| Hayalet Fikir | rock | 120 | y |\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert s["hayalet_satir"] == ["Hayalet Fikir"]
    assert s["durum"] == "uyari"


def test_sutun_sirasi_degisse_de_calisir(tmp_path):
    """Dosya ELLE düzenleniyor: sütun sırası başlıktan türetiliyor, sabit değil."""
    kok = _sahte_katalog(tmp_path, {"A Şarkı": "pop"})
    yol = _md(tmp_path, "| Vokal | Tema | Şarkı |\n|---|---|---|\n"
                        "| kadın | pop | A Şarkı |\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert s["durum"] == "tamam", s["uyarilar"]


def test_tablo_ayristirilamazsa_SESSIZCE_GECMEZ(tmp_path):
    """Bugünün ana hatası: anlaşılmayan bir şeyi 'temiz' saymak.

    Tablo bulunamadığında dönüş 'tamam' OLAMAZ — aksi hâlde biçim ufak bir
    elle düzenlemeyle bozulduğu gün muhafız sessizce kapanır ve kapandığı
    hiçbir yerde görünmez.
    """
    kok = _sahte_katalog(tmp_path, {"A Şarkı": "pop"})
    yol = _md(tmp_path, "Tablo YOK, sadece düz metin var.\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert s["durum"] == "okunamadi"
    assert any("okunamadı" in u for u in s["uyarilar"]), s["uyarilar"]


def test_dosya_yoksa_SESSIZCE_GECMEZ(tmp_path):
    kok = _sahte_katalog(tmp_path, {"A Şarkı": "pop"})
    s = STD.denetle(takip_dosyasi=str(tmp_path / "olmayan.md"), proje_koku=kok)
    assert s["durum"] == "okunamadi"
    assert any("okunamadı" in u for u in s["uyarilar"]), s["uyarilar"]


def test_sutunu_eksik_satir_raporlanir(tmp_path):
    """Yarım bir satır atlanmaz; atlanırsa 'tabloda yok' sonucu doğar ve
    sebebi görünmez olurdu."""
    kok = _sahte_katalog(tmp_path, {"A Şarkı": "pop"})
    yol = _md(tmp_path, _BASLIK + "| A Şarkı | pop | 100 | x |\n| yarım |\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert any("ayrıştırılamayan satır" in u for u in s["uyarilar"]), s["uyarilar"]


def test_turkce_buyuk_I_tuzagina_dusmuyor(tmp_path):
    """`"İ".lower()` -> `i` + U+0307: eşleşme sessizce kaybolurdu."""
    kok = _sahte_katalog(tmp_path, {"İki Yıldız": "pop"})
    yol = _md(tmp_path, _BASLIK + "| İki Yıldız | pop | 100 | x |\n")
    s = STD.denetle(takip_dosyasi=yol, proje_koku=kok)
    assert s["durum"] == "tamam", s["uyarilar"]


# --------------------------------------------------------------------------
# B) ÇAĞRI YOLU — muhafız gerçekten hatta bağlı mı?
# --------------------------------------------------------------------------

def test_kontrol_et_denetimi_GERCEKTEN_cagiriyor(monkeypatch):
    """saglik_kontrol.kontrol_et() -> ses_takip_denetimi.denetle() (çalışan kanıt).

    Diğer üç adım taklit ediliyor: `netlify_araci` ağa/alt sürece çıkıyor,
    `gorev_tanimlari` PowerShell başlatıyor — testin konusu onlar değil.
    `_bildir` de taklit: bu paket ASLA gerçek bir bildirim göndermemeli.
    """
    cagrildi = []
    monkeypatch.setattr(SK, "instagram_token_suresi", lambda log=print: {"durum": "yok"})
    monkeypatch.setattr(SK, "netlify_araci", lambda log=print: {"durum": "tamam"})
    monkeypatch.setattr(SK, "gorev_tanimlari", lambda log=print: {"durum": "atlandi"})

    sahte = types.ModuleType("ses_takip_denetimi")
    sahte.denetle = lambda: (cagrildi.append(True) or
                             {"durum": "uyari", "uyarilar": ["deneme uyarısı"]})
    sahte.ozet = lambda s, tavan=6: list(s["uyarilar"])
    monkeypatch.setitem(sys.modules, "ses_takip_denetimi", sahte)

    bildirimler = []
    monkeypatch.setattr(SK, "_bildir",
                        lambda b, m, a: bildirimler.append((b, m, a)) or True)

    satirlar = []
    sonuc = SK.kontrol_et(satirlar.append)

    assert cagrildi, "kontrol_et() ses_takip_denetimi.denetle()'yi ÇAĞIRMADI"
    assert sonuc["ses_takibi"]["durum"] == "uyari"
    assert any("ses/tarz takibi" in x for x in satirlar), satirlar
    assert bildirimler and bildirimler[0][2] == "ses_takip_bildirim_gun"


def test_denetim_patlarsa_sessiz_kalmaz(monkeypatch):
    """Muhafızın KENDİSİ patlarsa log'a düşmeli — ve otomasyonu durdurmamalı."""
    sahte = types.ModuleType("ses_takip_denetimi")

    def _patla():
        raise RuntimeError("beklenmedik")

    sahte.denetle = _patla
    monkeypatch.setitem(sys.modules, "ses_takip_denetimi", sahte)
    satirlar = []
    s = SK.ses_takip_tutarliligi(satirlar.append)
    assert s["durum"] == "calistirilamadi"
    assert any("çalıştırılamadı" in x for x in satirlar), satirlar


def test_zincir_kaynakta_kurulu():
    """auto_process.main() finally -> _saglik_kontrol -> kontrol_et -> denetim.

    Davranış testi yukarıda; bu test zincirin KAYNAKTAKİ halkalarını ayrı ayrı
    doğruluyor. Gerekçesi CLAUDE.md'de: bu depoda bulunan on arızanın hiçbiri
    fonksiyon seviyesinde bozuk değildi, hepsi BAĞLANTIDA kırıktı — ve
    `auto_process.main()`'i bir testte gerçekten çalıştırmak mümkün değil.
    """
    ap = _kaynak_agaci("auto_process.py")
    main = _fonksiyon(ap, "main")
    assert main is not None
    finally_cagrilari = set()
    for n in ast.walk(main):
        if isinstance(n, ast.Try) and n.finalbody:
            for g in n.finalbody:
                finally_cagrilari |= _cagri_adlari(g)
    assert "_saglik_kontrol" in finally_cagrilari, sorted(finally_cagrilari)

    sk_cagri = _cagri_adlari(_fonksiyon(ap, "_saglik_kontrol"))
    assert "saglik_kontrol.kontrol_et" in sk_cagri, sorted(sk_cagri)

    sk = _kaynak_agaci("saglik_kontrol.py")
    ke = _cagri_adlari(_fonksiyon(sk, "kontrol_et"))
    assert "ses_takip_tutarliligi" in ke, sorted(ke)

    st = _cagri_adlari(_fonksiyon(sk, "ses_takip_tutarliligi"))
    assert "ses_takip_denetimi.denetle" in st, sorted(st)


def test_proje_listesi_kanonik_yardimcidan_geliyor():
    """Kopya kural yazılmamış olmalı: `.`/`_` filtresi tek yerde (uyumluluk)."""
    std = _kaynak_agaci("ses_takip_denetimi.py")
    assert "uyumluluk.proje_klasorleri" in _cagri_adlari(std)
    kaynak = io.open(os.path.join(_REPO, "ses_takip_denetimi.py"),
                     encoding="utf-8").read()
    assert "os.listdir" not in kaynak, "proje listesi elle taranmamalı"


@pytest.mark.parametrize("hucre,beklenen", [
    ("Gece Sürüşü *(eski adı: Shudhniy L)*", "Gece Sürüşü"),
    ("elektronik (Afro-House/Arabic EDM)", "elektronik"),
    ("Neon Kalp **(üretilmedi)**", "Neon Kalp"),
    ("`Kod`  Adı ", "Kod Adı"),
])
def test_hucre_sadelestirme(hucre, beklenen):
    assert STD._sadelestir(hucre) == beklenen
