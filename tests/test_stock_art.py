"""stock_art.py testleri — ağ ERİŞİMİ OLMADAN çalışır (requests monkeypatch'lenir).

Buradaki kritik davranış: fetch_art HİÇBİR koşulda exception fırlatmamalı.
generate_cover.generate() başarısızlıkta prosedürel üretime düşüyor; bir
istisna sızarsa auto_process.py'nin tüm koşusu düşer, otomasyon durur.
"""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stock_art


# --- build_query: arama terimi önceliği ---

def test_meta_art_query_overrides_theme():
    meta = {"art_query": "empty train station at dawn"}
    theme = {"art_query": "rainy window night"}
    assert stock_art.build_query(meta, theme) == "empty train station at dawn"


def test_meta_art_query_also_overrides_lyrics(monkeypatch):
    monkeypatch.setattr(stock_art, "query_from_lyrics", lambda *a, **k: "sözlerden gelen")
    meta = {"art_query": "elle yazılmış"}
    assert stock_art.build_query(meta, {}, "Bir Şarkı") == "elle yazılmış"


def test_lyrics_query_beats_theme_default(monkeypatch):
    monkeypatch.setattr(stock_art, "query_from_lyrics", lambda *a, **k: "moody empty street")
    q = stock_art.build_query({}, {"art_query": "tema varsayılanı"}, "Bir Şarkı")
    assert q.startswith("moody empty street")
    assert "tema varsayılanı" not in q


def test_falls_back_to_theme_query_when_meta_has_none():
    q = stock_art.build_query({}, {"art_query": "rainy window night"})
    assert q.startswith("rainy window night")


def test_generated_queries_get_the_style_suffix():
    """Stil eki, belgesel tarzı (çoğu zaman TABELALI) sokak karesi yerine
    sanatsal kare gelmesi için otomatik sorgulara ekleniyor — bkz. modüldeki
    not: 'neon night' aramasında dev Kiril tabelalı bir kare gelmişti."""
    q = stock_art.build_query({}, {"art_query": "neon city"})
    assert q.endswith(stock_art.STYLE_SUFFIX)


def test_explicit_meta_query_does_not_get_the_style_suffix():
    """Elle yazılmış sorguya dokunulmaz — kullanıcı ne istediğini biliyor."""
    q = stock_art.build_query({"art_query": "misty lake dawn"}, {"art_query": "x"})
    assert q == "misty lake dawn"


# --- sözlerden anahtar kelime çıkarımı ---

def test_keywords_are_ranked_by_frequency():
    lyrics = "gece gece gece sokakta yağmur"
    terms = stock_art.keywords_from_lyrics(lyrics)
    assert terms[0] == "night"


def test_only_setting_words_matched_not_objects():
    """Nesne terimleri (zincir/masa/gitar) BİLEREK sözlükte yok — stok
    fotoğrafta katalog çekimi ve yanlış anlam getiriyorlardı (bkz. modül
    içindeki not: 'Kırık Zincir' -> bisiklet zinciri)."""
    terms = stock_art.keywords_from_lyrics("zincir masa gitar mektup saat")
    assert terms == []


def test_turkish_suffixes_still_match():
    """Türkçe sondan eklemeli: 'sokakta'/'sokakları' da eşleşmeli."""
    assert "empty street" in stock_art.keywords_from_lyrics("sokakta sokakları yağmur yağmurda")


def test_query_from_lyrics_prepends_theme_mood(tmp_path, monkeypatch):
    lyrics = tmp_path / "test_sarki_sozler.md"
    lyrics.write_text("gece gece sokakta yağmur yağmur", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))

    q = stock_art.query_from_lyrics("Test Şarkı", {"art_mood": "melancholy moody"})
    assert q.startswith("melancholy moody")
    assert "night" in q


def test_mood_and_lyric_terms_are_deduplicated(tmp_path, monkeypatch):
    """Tema modu 'neon night' + sözlerden 'neon'/'night' -> tekrar etmemeli."""
    lyrics = tmp_path / "neon_test_sozler.md"
    lyrics.write_text("neon neon gece gece ışık", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))

    q = stock_art.query_from_lyrics("Neon Test", {"art_mood": "neon night"})
    assert q.split().count("neon") == 1
    assert q.split().count("night") == 1


def test_too_few_imagery_matches_falls_back_to_theme(tmp_path, monkeypatch):
    lyrics = tmp_path / "az_imge_sozler.md"
    lyrics.write_text("seni seviyorum çok özledim", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))

    assert stock_art.query_from_lyrics("Az İmge", {"art_mood": "x"}) is None


def test_missing_lyrics_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))
    assert stock_art.query_from_lyrics("Hiç Olmayan Şarkı", {}) is None


# --- sözler dosyasını bulma (Türkçe slug + ünsüz yumuşaması) ---

def test_finds_lyrics_file_by_exact_turkish_slug(tmp_path, monkeypatch):
    (tmp_path / "yurek_yarasi_sozler.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))
    found = stock_art.find_lyrics_file("Yürek Yarası")
    assert found and os.path.basename(found) == "yurek_yarasi_sozler.md"


def test_finds_lyrics_file_despite_consonant_mutation(tmp_path, monkeypatch):
    """"Beton Krallığı" -> slug "beton_kralligi" ama dosya "beton_krallik"
    (k -> ğ yumuşaması). Benzerlik eşleşmesi bunu yakalamalı."""
    (tmp_path / "beton_krallik_sozler.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))
    found = stock_art.find_lyrics_file("Beton Krallığı")
    assert found and os.path.basename(found) == "beton_krallik_sozler.md"


def test_unrelated_title_does_not_match_a_lyrics_file(tmp_path, monkeypatch):
    (tmp_path / "yurek_yarasi_sozler.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))
    assert stock_art.find_lyrics_file("Neon Kalp") is None


def test_blank_meta_query_falls_back_to_theme():
    meta = {"art_query": "   "}
    assert stock_art.build_query(meta, {"art_query": "neon city"}).startswith("neon city")


def test_returns_none_when_neither_has_a_query():
    assert stock_art.build_query({}, {}) is None


# --- fetch_art: her hata yolunda False, asla istisna ---

def test_no_api_key_returns_false(monkeypatch, tmp_path):
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: None)
    out = str(tmp_path / "art.jpg")
    assert stock_art.fetch_art("Bir Şarkı", "neon city", out) is False
    assert not os.path.exists(out)


def test_network_error_returns_false(monkeypatch, tmp_path):
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: "key")

    def boom(*args, **kwargs):
        raise requests.ConnectionError("ağ yok")

    monkeypatch.setattr(stock_art.requests, "get", boom)
    assert stock_art.fetch_art("Bir Şarkı", "neon city", str(tmp_path / "art.jpg")) is False


def test_empty_result_set_returns_false(monkeypatch, tmp_path):
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: "key")
    monkeypatch.setattr(stock_art.requests, "get", lambda *a, **k: _FakeResponse({"photos": []}))
    assert stock_art.fetch_art("Bir Şarkı", "hiç sonuç yok", str(tmp_path / "art.jpg")) is False


def test_failed_download_leaves_no_partial_file(monkeypatch, tmp_path):
    """İndirme yarıda kalırsa dosya SİLİNMELİ — yoksa bir sonraki koşu onu
    'art zaten var' sanıp bozuk bir görselle render eder."""
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: "key")
    out = str(tmp_path / "art.jpg")

    calls = {"n": 0}

    def fake_get(url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResponse({"photos": [{"src": {"large2x": "http://x/photo.jpg"}}]})
        # ikinci çağrı = görselin kendisi; yarım dosya bırakıp patlat
        with open(out, "wb") as f:
            f.write(b"yarim")
        raise requests.ConnectionError("indirme koptu")

    monkeypatch.setattr(stock_art.requests, "get", fake_get)
    assert stock_art.fetch_art("Bir Şarkı", "neon city", out) is False
    assert not os.path.exists(out)


# --- deterministik seçim ---

def test_same_title_always_picks_the_same_photo(monkeypatch, tmp_path):
    """Aynı şarkı yeniden işlenince kapağı değişmemeli (projenin genelindeki
    deterministik üretim ilkesi)."""
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: "key")
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"}} for i in range(15)]
    picked = []

    def fake_get(url, **kwargs):
        if url == stock_art.API_URL:
            return _FakeResponse({"photos": photos})
        picked.append(url)
        return _FakeResponse(b"", raw=b"jpegbytes")

    monkeypatch.setattr(stock_art.requests, "get", fake_get)

    for _ in range(3):
        assert stock_art.fetch_art("Yürek Yarası", "rainy window", str(tmp_path / "a.jpg")) is True

    assert len(set(picked)) == 1, "aynı başlık farklı fotoğraflar seçti"


def test_different_titles_can_pick_different_photos(monkeypatch, tmp_path):
    monkeypatch.setattr(stock_art, "_load_api_key", lambda: "key")
    photos = [{"src": {"large2x": f"http://x/{i}.jpg"}} for i in range(15)]
    picked = []

    def fake_get(url, **kwargs):
        if url == stock_art.API_URL:
            return _FakeResponse({"photos": photos})
        picked.append(url)
        return _FakeResponse(b"", raw=b"jpegbytes")

    monkeypatch.setattr(stock_art.requests, "get", fake_get)

    for title in ("Yürek Yarası", "Neon Kalp", "Kırık Zincir", "Sessiz Mektup"):
        stock_art.fetch_art(title, "aynı sorgu", str(tmp_path / "a.jpg"))

    assert len(set(picked)) > 1, "tüm şarkılar aynı fotoğrafa düştü"


class _FakeResponse:
    def __init__(self, payload, raw: bytes = b""):
        self._payload = payload
        self.content = raw

    def raise_for_status(self):
        return None

    def json(self):
        if not isinstance(self._payload, dict):
            raise ValueError("json değil")
        return self._payload
