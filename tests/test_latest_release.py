# -*- coding: utf-8 -*-
"""docs/latest.html üreticisinin testleri.

NEDEN VAR: bu sayfa Instagram/TikTok izleyicisinin YouTube'a gidebildiği TEK
tıklanabilir yol (bkz. latest_release.py docstring'i) ve bugüne kadar hiç
testi yoktu. En kritik iki soru:
  1. Yayınlanmamış (unlisted/private/karantinada) bir video herkese açık bu
     sayfaya SIZIYOR mu?
  2. Kataloğun bir hattı (derlemeler) sayfadan EKSİK mi?
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import latest_release


def _proje(kok, ad, state, meta=None):
    d = os.path.join(kok, ad)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    if meta is not None:
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f)
    return d


@pytest.fixture
def sahte_repo(tmp_path, monkeypatch):
    """latest_release'i geçici bir repo köküne yönlendirir."""
    kok = str(tmp_path)
    monkeypatch.setattr(latest_release, "REPO_DIR", kok)
    monkeypatch.setattr(latest_release, "DOCS_DIR", os.path.join(kok, "docs"))
    monkeypatch.setattr(latest_release, "LATEST_HTML_PATH",
                        os.path.join(kok, "docs", "latest.html"))
    for alt, _ in latest_release.KOKLER:
        os.makedirs(os.path.join(kok, alt), exist_ok=True)
    return kok


def _html(kok):
    with open(os.path.join(kok, "docs", "latest.html"), encoding="utf-8") as f:
        return f.read()


# --- 1. SIZINTI: yayınlanmamış içerik sayfada GÖRÜNMEMELİ -------------------

def test_unlisted_video_sayfaya_girmez(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Gizli",
           {"youtube_privacy": "unlisted", "youtube_video_id": "GIZLI123456"})
    assert latest_release.regenerate() == 0
    assert "GIZLI123456" not in _html(sahte_repo)


def test_private_video_sayfaya_girmez(sahte_repo):
    _proje(os.path.join(sahte_repo, "derlemeler"), "Derleme",
           {"youtube_privacy": "private", "youtube_video_id": "PRIV123456"})
    assert latest_release.regenerate() == 0
    assert "PRIV123456" not in _html(sahte_repo)


def test_karantinadaki_video_privacy_public_olsa_bile_girmez(sahte_repo):
    """`youtube_privacy` state.json'a EN SON BİZİM yazdığımızın aynası;
    Content ID karantinası bayrağı ondan BAĞIMSIZ ikinci kapı."""
    _proje(os.path.join(sahte_repo, "dj_sets"), "Karantina",
           {"youtube_privacy": "public", "youtube_video_id": "KARANT12345",
            "dj_tarama_bekliyor": True})
    assert latest_release.regenerate() == 0
    assert "KARANT12345" not in _html(sahte_repo)


def test_content_id_engelli_video_girmez(sahte_repo):
    _proje(os.path.join(sahte_repo, "dj_sets"), "Engelli",
           {"youtube_privacy": "public", "youtube_video_id": "ENGEL123456",
            "dj_tarama_engelli": True})
    assert latest_release.regenerate() == 0
    assert "ENGEL123456" not in _html(sahte_repo)


def test_golden_hour_beklemedeki_video_girmez(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Zamanli",
           {"youtube_privacy": "public", "youtube_video_id": "ZAMAN123456",
            "youtube_publish_at": "2099-01-01T12:00:00Z"})
    assert latest_release.regenerate() == 0
    assert "ZAMAN123456" not in _html(sahte_repo)


def test_bozuk_publish_at_sizdirmaz(sahte_repo):
    """Okunamayan bir zamanlama damgası = "bilmiyoruz" — şüphede listelemiyoruz."""
    _proje(os.path.join(sahte_repo, "projects"), "Bozuk",
           {"youtube_privacy": "public", "youtube_video_id": "BOZUK123456",
            "youtube_publish_at": "yarin aksam"})
    assert latest_release.regenerate() == 0
    assert "BOZUK123456" not in _html(sahte_repo)


def test_alt_cizgili_klasor_sayfaya_girmez(sahte_repo):
    """`_` ön eki bu depoda "yok say" demek (dj_clips.py, watch_projects.py
    aynı kuralı uyguluyor). Yayınlanmış bir projeyi `_` ekleyerek arşivleyen
    kullanıcı, onu HERKESE AÇIK sayfadan da düşürmüş olmalı — eskiden
    arşivlenen proje sayfada listelenmeye devam ediyordu."""
    _proje(os.path.join(sahte_repo, "dj_sets"), "_arsiv",
           {"youtube_privacy": "public", "youtube_video_id": "ARSIV123456"},
           {"title": "Arşivlenmiş Set"})
    assert latest_release.regenerate() == 0
    h = _html(sahte_repo)
    assert "ARSIV123456" not in h
    assert "Arşivlenmiş Set" not in h


def test_bozuk_state_json_sizdirmaz(sahte_repo):
    d = os.path.join(sahte_repo, "projects", "YarimJson")
    os.makedirs(d)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        f.write('{"youtube_privacy": "public", "youtube_vid')
    assert latest_release.regenerate() == 0


# --- 2. KAPSAM: her yayın kökü sayfada olmalı -------------------------------

def test_uc_kok_de_sayfaya_giriyor(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Sarki",
           {"youtube_privacy": "public", "youtube_video_id": "SARKI123456"},
           {"title": "Bir Şarkı"})
    _proje(os.path.join(sahte_repo, "dj_sets"), "Set",
           {"youtube_privacy": "public", "youtube_video_id": "SETSET12345"},
           {"title": "Bir Set"})
    _proje(os.path.join(sahte_repo, "derlemeler"), "Derleme",
           {"youtube_privacy": "public", "youtube_video_id": "DERLEM12345"},
           {"title": "Bir Derleme"})
    assert latest_release.regenerate() == 3
    h = _html(sahte_repo)
    for vid in ("SARKI123456", "SETSET12345", "DERLEM12345"):
        assert "https://youtu.be/%s" % vid in h
    for baslik in ("Şarkılar", "DJ Famous Setleri", "Derlemeler"):
        assert baslik in h


def test_derlemeler_kokunun_basligi_tanimli():
    """Regresyon: `derlemeler` kökü listede HİÇ yoktu — derleme hattının
    tamamı bio linkinden görünmüyordu."""
    assert "derlemeler" in dict((k, b) for k, b in latest_release.KOKLER)


def test_en_yeni_en_ustte(sahte_repo):
    p = os.path.join(sahte_repo, "projects")
    _proje(p, "Eski", {"youtube_privacy": "public", "youtube_video_id": "ESKI1234567",
                       "youtube_uploaded_at": "2026-01-01T00:00:00"}, {"title": "Eski"})
    _proje(p, "Yeni", {"youtube_privacy": "public", "youtube_video_id": "YENI1234567",
                       "youtube_uploaded_at": "2026-09-01T00:00:00"}, {"title": "Yeni"})
    latest_release.regenerate()
    h = _html(sahte_repo)
    assert h.index("YENI1234567") < h.index("ESKI1234567")


# --- 3. SAYFANIN KENDİSİ ----------------------------------------------------

def test_baslikta_html_kacisi_var(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Kotu",
           {"youtube_privacy": "public", "youtube_video_id": "KOTU1234567"},
           {"title": "<script>alert(1)</script>"})
    latest_release.regenerate()
    h = _html(sahte_repo)
    assert "<script>alert(1)</script>" not in h
    assert "&lt;script&gt;" in h


def test_gecersiz_video_id_satiri_atlanir(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Enjeksiyon",
           {"youtube_privacy": "public",
            "youtube_video_id": '"><script>alert(1)</script>'})
    assert latest_release.regenerate() == 0


def test_bos_katalogda_sayfa_yine_de_uretilir(sahte_repo):
    assert latest_release.regenerate() == 0
    h = _html(sahte_repo)
    assert "<h1>Famous Music Studio</h1>" in h
    assert latest_release._YER_TUTUCU not in h


def test_dis_yazi_tipi_bagimliligi_yok(sahte_repo):
    """Sayfa Instagram/TikTok içi tarayıcıda açılıyor — render-bloklayan
    dış stylesheet ilk boyamayı geciktiriyordu."""
    latest_release.regenerate()
    h = _html(sahte_repo)
    assert "fonts.googleapis.com" not in h
    assert "<script" not in h


def test_mobil_temel_gereksinimler(sahte_repo):
    _proje(os.path.join(sahte_repo, "projects"), "Sarki",
           {"youtube_privacy": "public", "youtube_video_id": "SARKI123456"},
           {"title": "Bir Şarkı"})
    latest_release.regenerate()
    h = _html(sahte_repo)
    assert 'name="viewport"' in h and "width=device-width" in h
    assert "min-height: 56px" in h          # dokunma hedefi
    assert 'loading="lazy"' in h            # küçük resimler tembel yükleniyor
    assert "i.ytimg.com" in h               # küçük resim GÖSTERİLİYOR
    assert "font-size: 1rem" in h           # 16 px satır yazısı
