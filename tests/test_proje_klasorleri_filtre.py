# -*- coding: utf-8 -*-
"""`uyumluluk.proje_klasorleri()` `.` ve `_` on ekli klasorleri ELIYOR mu.

NEDEN VAR (2026-09-11): fonksiyon uc soruyu tek yerde topluyordu ("kok var mi",
"alt oge klasor mu", "sirali mi") ama DORDUNCUSUNU sormuyordu: "bu klasor zaten
yok sayilmali mi". Iki ayri kanit:

  * `.` — `derleme.py` uretimi once `derlemeler/.tmp-<ad>` altinda yapip sonda
    `os.replace` ile hedefe tasiyor; o klasor uretim boyunca YARIM duruyor.
    `dj_famous_process.find_pending_sets()` bu filtreyi ZATEN uyguluyordu
    (dj_famous_process.py:213, gerekcesi orada yazili: yarim bir derlemeyi
    yayina sokmamak). `proje_klasorleri()` uygulamiyordu — ve cagiranlarinin
    cogu (facebook_backfill, ek_platform_backfill, bluesky_upload,
    tiktok_upload, youtube_comments) yayin hatti. Bugun pratik zarar yoktu
    cunku `.tmp-` klasorunde state.json olmuyor; ama bu bir yazma SIRASI
    tesadufu, garanti degil. GORUNEN etki: `validate_project --all` yarim
    klasor icin sahte hata basiyordu.

  * `_` — bu depoda `_` on eki "YOK SAY" demek (`dj_clips._set_klasorleri()`,
    `watch_projects._stray_images()`, `latest_release`). Diskte iki ornek var ve
    ikisi de PROJE DEGIL: `dj_sets/_arda` (ham portre fotograflari) ve
    `derlemeler/_iptal` (yalnizca bir KAPSAYICI). Ikincisi somut zarar
    veriyordu: `_kok()` ona "derlemeler" dedigi icin `kontrol()` derleme dalina
    giriyor ve meta.json HIC olmadigi icin her taramada IKI SAHTE uyari
    basiyordu.

Bu testin ikinci isi bir SINIRI cakmak: `_iptal/` ALTINDA park edilmis gercek
derleme filtreden ETKILENMIYOR, cunku `proje_klasorleri()` TEK seviye tariyor —
o klasor zaten hicbir zaman taranmiyordu. Filtre bir kayip yaratmiyor; bunu
yazili bir testle sabitlemek, yarin "filtre gercek bir derlemeyi mi eliyor"
sorusunu bir daha elle arastirmamak demek.

UCUNCU is: `kontrol()` icindeki IKI guvenlik dongusunun (md5 tekrar taramasi ve
gunluk yukleme sayaci) BILEREK filtrelemedigini sabitlemek. Oralarda filtre
uygulamak korumayi ZAYIFLATIR — gerekce ilgili yorumlarda.
"""

import io
import json
import os
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import uyumluluk                                   # noqa: E402


def _sahte_kok(tmp_path, adlar):
    """Verilen adlarda klasor iceren tek bir sahte kok kurar; kokun yolunu doner."""
    kok = tmp_path / "derlemeler"
    kok.mkdir()
    for ad in adlar:
        (kok / ad).mkdir()
    return str(kok)


def test_nokta_on_ekli_klasor_taranmiyor(tmp_path):
    """`.tmp-<ad>` = yarim uretilmis derleme; hicbir cagirana verilmemeli."""
    kok = _sahte_kok(tmp_path, ["Gercek Derleme", ".tmp-Gercek Derleme"])
    adlar = [os.path.basename(y) for y in uyumluluk.proje_klasorleri(kok)]
    assert adlar == ["Gercek Derleme"]


def test_alt_cizgi_on_ekli_klasor_taranmiyor(tmp_path):
    """`_` on eki bu depoda "yok say" demek (dj_clips / watch_projects /
    latest_release ayni kurali uyguluyor)."""
    kok = _sahte_kok(tmp_path, ["Gercek Derleme", "_iptal", "_arda"])
    adlar = [os.path.basename(y) for y in uyumluluk.proje_klasorleri(kok)]
    assert adlar == ["Gercek Derleme"]


def test_dosyalar_ve_sira_degismedi(tmp_path):
    """Filtre eklenirken eski davranis (dosyalari ele, alfabetik sirala)
    korunmus olmali — regresyon capasi."""
    kok = _sahte_kok(tmp_path, ["Ccc", "Aaa", "Bbb"])
    (tmp_path / "derlemeler" / "README.md").write_text("x", encoding="utf-8")
    adlar = [os.path.basename(y) for y in uyumluluk.proje_klasorleri(kok)]
    assert adlar == ["Aaa", "Bbb", "Ccc"]


def test_iptal_altindaki_derleme_zaten_taranmiyordu(tmp_path):
    """SINIR: `_` filtresi bir KAYIP yaratmiyor.

    `derlemeler/_iptal/En Cok Dinlenenler` gercek bir park edilmis derleme ama
    `proje_klasorleri()` TEK seviye tariyor; o klasor filtre EKLENMEDEN ONCE de
    sonuca girmiyordu. Filtrenin eledigi sey yalnizca KAPSAYICININ kendisi.
    """
    kok = _sahte_kok(tmp_path, ["_iptal"])
    (tmp_path / "derlemeler" / "_iptal" / "En Cok Dinlenenler").mkdir()
    yollar = list(uyumluluk.proje_klasorleri(kok))
    assert yollar == []
    # Filtre olmasaydi bile derinlemesine inilmiyordu: taramanin uretebilecegi
    # EN IYI sonuc kapsayicinin kendisiydi, park edilen derleme DEGIL.
    assert not any("En Cok Dinlenenler" in y for y in yollar)


def test_iptal_kapsayicisi_artik_sahte_uyari_uretmiyor(tmp_path):
    """`_iptal` bir KAPSAYICI: meta.json'i yok, ama `_kok()` ona "derlemeler"
    diyordu — yani `kontrol()` derleme dalina girip IKI sahte uyari basiyordu.
    Artik tarama onu hic gormedigi icin uyari da uretilmiyor."""
    kok = _sahte_kok(tmp_path, ["_iptal"])
    assert list(uyumluluk.proje_klasorleri(kok)) == []
    # kontrol() DOGRUDAN cagrilirsa hala uyari uretir (fonksiyon kendisine
    # verilen yola guvenir) — filtre ENUMERASYON katmaninda, dogru yer orasi.
    _h, u = uyumluluk.kontrol(str(tmp_path / "derlemeler" / "_iptal"), "render")
    assert len(u) == 2


def test_md5_tekrar_taramasi_BILEREK_filtrelemiyor(tmp_path, monkeypatch):
    """Guvenlik dongusu GENIS taranir: `_` ile kenara cekilmis bir klasorde
    duran ses de "bu sarki kanalda zaten var" kanitidir. Filtrelenirse
    tekrar-icerik kontrolu SESSIZCE zayiflar."""
    kok = tmp_path / "projects"
    (kok / "Yeni Sarki").mkdir(parents=True)
    (kok / "_arsiv").mkdir()
    ses = b"AYNI SES BAYTLARI" * 100
    (kok / "Yeni Sarki" / "audio.wav").write_bytes(ses)
    (kok / "_arsiv" / "audio.wav").write_bytes(ses)
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    h, u = uyumluluk.kontrol(str(kok / "Yeni Sarki"), "render")
    # Bu testin konusu taramanin `_arsiv`i GORUP gormedigi; bulgunun SIDDETI
    # ayri bir kural (isaretsiz kopya artik HATA — bkz.
    # tests/test_uyumluluk_kopya_kapisi.py), o yuzden iki listeye de bakiliyor.
    assert any("BİREBİR AYNI" in x and "_arsiv" in x for x in h + u), (h, u)


def test_gunluk_sayac_BILEREK_filtrelemiyor(tmp_path, monkeypatch):
    """Yukleme GERCEKLESTIKTEN sonra klasoru `_` ile arsivlemek o yuklemeyi
    geri almiyor. Sayac filtrelenirse esik tetiklenmez ve "toplu uretim"
    uyarisi sessizce kaybolur."""
    import time
    bugun = time.strftime("%Y-%m-%d")
    kok = tmp_path / "projects"
    for ad in ("Bir", "_iki", "_uc"):
        (kok / ad).mkdir(parents=True)
        (kok / ad / "state.json").write_text(
            json.dumps({"youtube_uploaded_at": bugun + "T10:00:00"}),
            encoding="utf-8")
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    _h, u = uyumluluk.kontrol(str(kok / "Bir"), "yukleme")
    assert any("bugün zaten 3 yükleme" in x for x in u), u
