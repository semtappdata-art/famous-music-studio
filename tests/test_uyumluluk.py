# -*- coding: utf-8 -*-
"""uyumluluk.kontrol() için testler — politika kapısının SESSİZCE AÇILDIĞI
durumları kilitliyor.

Bu modül boru hattının içinde otomatik çalışıyor ve iki ayrı yerden (render +
yükleme) çağrılıyor; bir denetim (2026-09-11) kapının üç ayrı yoldan sessizce
açılabildiğini gösterdi: bozuk state.json'un {} sayılması, göreli kök yolları
ve md5 bloğunu tümüyle yutan `except OSError: pass`. Testlerin çoğu tam olarak
o üç yolu koruyor.
"""

import json
import os

import pytest

import uyumluluk


def _proje(kok, ad, durum=None, meta=None, ses=b"ses-verisi"):
    """tmp içinde sahte bir proje klasörü kurar."""
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    if durum is not None:
        (p / "state.json").write_text(durum, encoding="utf-8")
    if meta is not None:
        (p / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                     encoding="utf-8")
    if ses is not None:
        (p / "audio.wav").write_bytes(ses)
    return str(p)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    """KOKLER'i tmp'ye yönlendirir — testler gerçek katalogu taramasın."""
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


# --- 1. Bozuk state.json: kapı SESSİZCE açılmamalı -------------------------

def test_bozuk_state_json_hata_uretir(kok):
    """Yarım yazılmış state.json = "bilmiyorum", "temiz" DEĞİL.

    Eskiden _durum() ValueError'ı yutup {} dönüyordu; telif_araliklari boş
    çıkıyor ve Content ID eşleşmesi almış bir set yeniden yayına girebiliyordu.
    """
    p = _proje(kok, "Yarim", durum='{"telif_araliklari": [[10, 40]], "telif_ese')
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert hatalar, "bozuk state.json HATA üretmeli, kapı açık kalmamalı"
    assert any("state.json" in h for h in hatalar)


def test_state_json_yoksa_hata_yok(kok):
    """Dosya yokluğu normal: henüz hiç yayınlanmamış proje."""
    p = _proje(kok, "Yeni", durum=None)
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert hatalar == []


def test_telif_kaydi_varsa_hata(kok):
    p = _proje(kok, "City", durum=json.dumps(
        {"telif_araliklari": [[10, 40]], "telif_eser": "Bring Me To Life"}))
    hatalar, _ = uyumluluk.kontrol(p, "yukleme")
    assert any("telif" in h for h in hatalar)


def test_bozuk_komsu_state_json_gunluk_sayacta_uyari(kok):
    """Sayaç eksik kalabilir — bu da sessiz kalmamalı."""
    _proje(kok, "Bozuk Komsu", durum="{bu json degil")
    p = _proje(kok, "Temiz", durum="{}")
    _, uyarilar = uyumluluk.kontrol(p, "yukleme")
    assert any("Bozuk Komsu" in u for u in uyarilar)


# --- 2. Kök yolları mutlak olmalı ------------------------------------------

def test_kokler_mutlak_yol():
    """Göreli bırakılırsa yanlış cwd'de isdir False döner ve md5 tekrar
    kontrolü + günlük sayaç TAMAMEN atlanır (hata=0 uyarı=0 = "temiz")."""
    assert uyumluluk.KOKLER
    for k in uyumluluk.KOKLER:
        assert os.path.isabs(k), k


def test_yanlis_cwd_de_de_calisir(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    a = _proje(k, "A", ses=b"ayni-ses")
    _proje(k, "B", ses=b"ayni-ses")
    baska_yer = tmp_path / "baska"
    baska_yer.mkdir()
    monkeypatch.chdir(baska_yer)          # cwd repo kökü DEĞİL
    # Bu testin derdi ŞİDDET değil, kontrolün ÇALIŞIP çalışmadığı: göreli kök
    # yolunda hiçbir bulgu üretilmiyordu. Bulgu artık (işaretsiz kopya olduğu
    # için) HATA tarafında düşüyor — bkz. tests/test_uyumluluk_kopya_kapisi.py.
    hatalar, uyarilar = uyumluluk.kontrol(a, "render")
    assert any("md5" in b for b in hatalar + uyarilar)


# --- 3. md5 tembel hesaplanmalı --------------------------------------------

def test_md5_boyut_eslesmezse_hic_hesaplanmaz(kok, monkeypatch):
    """Kendi md5'imiz artık koşulsuz değil: 935 MB'lik bir sette 11 sn."""
    a = _proje(kok, "A", ses=b"kisa")
    _proje(kok, "B", ses=b"cok-daha-uzun-baska-ses")
    cagri = []
    gercek = uyumluluk._md5
    monkeypatch.setattr(uyumluluk, "_md5",
                        lambda y: (cagri.append(y), gercek(y))[1])
    uyumluluk.kontrol(a, "render")
    assert cagri == [], "boyutu eşleşen aday yokken md5 hesaplanmamalı"


def test_md5_boyut_eslesirse_hesaplanir_ve_bildirir(kok, monkeypatch):
    # Adı eskiden "..._ve_uyarir" idi; bulgunun ŞİDDETİ artık duruma göre
    # değişiyor (işaretsiz kopya = HATA), bu testin konusu ise hesabın YAPILIP
    # bulgunun RAPORLANMASI. Şiddet kuralı: tests/test_uyumluluk_kopya_kapisi.py
    a = _proje(kok, "Küllerimden", ses=b"ayni-ses")
    _proje(kok, "Yeniden", ses=b"ayni-ses")
    cagri = []
    gercek = uyumluluk._md5
    monkeypatch.setattr(uyumluluk, "_md5",
                        lambda y: (cagri.append(y), gercek(y))[1])
    hatalar, uyarilar = uyumluluk.kontrol(a, "render")
    assert cagri, "boyut eşleşince md5 hesaplanmalı"
    assert any("Yeniden" in b and "md5" in b for b in hatalar + uyarilar)


# --- 4. Okunamayan ses sessizce yutulmamalı --------------------------------

def test_md5_okunamazsa_uyari_uretir(kok, monkeypatch):
    """Eskiden `except OSError: pass` tüm bloğu yutuyordu: ses dosyası
    kilitliyse tekrar-içerik kontrolü sessizce devre dışı kalıyordu."""
    a = _proje(kok, "A", ses=b"ayni-ses")
    _proje(kok, "B", ses=b"ayni-ses")

    def _patlat(yol):
        raise OSError("dosya kilitli")

    monkeypatch.setattr(uyumluluk, "_md5", _patlat)
    _, uyarilar = uyumluluk.kontrol(a, "render")
    assert any("md5" in u for u in uyarilar), "sessiz geçilmemeli"
