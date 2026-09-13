# -*- coding: utf-8 -*-
""""Bizi takip et" bölümünün testleri (docs/latest.html + docs/index.html).

NEDEN VAR: platform linkleri tek kaynaktan (`latest_release.PLATFORM_LINKLERI`)
iki sayfaya basılıyor. Korunan hatalar:
  1. `youtube.com/@famousmusicstudio` BAŞKA bir kanal — sayfaya girmemeli.
  2. Üretim aracının adı kamuya açık metinde geçmemeli.
  3. Elle yazılan kök sayfa tek kaynaktan kopup bayatlamamalı.
"""
import os
import re
import sys
from html.parser import HTMLParser

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

import latest_release

BEKLENEN = {
    "youtube": "https://www.youtube.com/@Famous_musics_studio",
    "tiktok": "https://www.tiktok.com/@famousmusicstudio",
    "instagram": "https://www.instagram.com/famous_music_studio/",
    "facebook": "https://www.facebook.com/famousmusicstudio",
    "telegram": "https://t.me/hermes_famous_asistan",
    "bluesky": "https://bsky.app/profile/famousmusicstudio.bsky.social",
}
YANLIS_KANAL_RE = re.compile(r"youtube\.com/@famousmusicstudio\b", re.I)


class _Toplayici(HTMLParser):
    """Linkleri toplar ve açılıp kapanmayan etiketleri yakalar."""
    BOS = {"meta", "link", "img", "br", "hr", "input", "path", "rect", "circle"}

    def __init__(self):
        super().__init__()
        self.linkler = []
        self.yigin = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.linkler.append(dict(attrs))
        if tag not in self.BOS:
            self.yigin.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == "a":
            self.linkler.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag in self.BOS:
            return
        assert self.yigin and self.yigin[-1] == tag, (tag, self.yigin[-3:])
        self.yigin.pop()


def _ayristir(metin):
    p = _Toplayici()
    p.feed(metin)
    p.close()
    assert p.yigin == [], p.yigin
    return p


def _takip_linkleri(p):
    return {a["class"][len("takip-"):]: a for a in p.linkler
            if a.get("class", "").startswith("takip-")}


def _denetle(metin):
    p = _ayristir(metin)
    linkler = _takip_linkleri(p)
    assert {k: a["href"] for k, a in linkler.items()} == BEKLENEN
    for a in linkler.values():
        assert a.get("target") == "_blank"
        assert "noopener" in a.get("rel", "")
        assert a.get("aria-label")
    assert "Bizi takip et" in metin
    assert not YANLIS_KANAL_RE.search(metin)
    assert not re.search(r"suno", metin, re.I)


def test_tek_kaynak_dogru():
    assert {k: url for k, _, url, _ in latest_release.PLATFORM_LINKLERI} == BEKLENEN


def test_platform_sirasi():
    assert [k for k, _, _, _ in latest_release.PLATFORM_LINKLERI] == [
        "youtube", "tiktok", "instagram", "facebook", "telegram", "bluesky"]


def test_uretilen_latest_html(tmp_path, monkeypatch):
    monkeypatch.setattr(latest_release, "REPO_DIR", str(tmp_path))
    monkeypatch.setattr(latest_release, "DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setattr(latest_release, "LATEST_HTML_PATH",
                        str(tmp_path / "docs" / "latest.html"))
    latest_release.regenerate()
    metin = (tmp_path / "docs" / "latest.html").read_text(encoding="utf-8")
    _denetle(metin)
    assert "<!--TAKIP-->" not in metin
    # Dış istek yok: ikonlar satır içi.
    assert "<script" not in metin and "cdn" not in metin.lower()


@pytest.mark.parametrize("ad", ["index.html", "latest.html"])
def test_diskteki_sayfalar(ad):
    with open(os.path.join(KOK, "docs", ad), encoding="utf-8") as f:
        _denetle(f.read())


def test_index_tek_kaynakla_senkron(tmp_path):
    kaynak = os.path.join(KOK, "docs", "index.html")
    with open(kaynak, "rb") as f:
        ham = f.read()
    kopya = tmp_path / "index.html"
    kopya.write_bytes(ham)
    assert latest_release.index_takip_guncelle(str(kopya)) is False, (
        "docs/index.html bayat: latest_release.index_takip_guncelle() çalıştır")
    assert kopya.read_bytes() == ham


def test_index_guncelleme_satir_sonunu_korur(tmp_path):
    yol = tmp_path / "index.html"
    yol.write_bytes(b"<main>\r\n  <!--TAKIP-BASLA-->eski<!--TAKIP-BITIR-->\r\n</main>\r\n")
    assert latest_release.index_takip_guncelle(str(yol)) is True
    ham = yol.read_bytes()
    assert b"eski" not in ham
    assert ham.count(b"\n") == ham.count(b"\r\n")
    _ayristir(ham.decode("utf-8"))
