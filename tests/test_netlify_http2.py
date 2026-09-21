# -*- coding: utf-8 -*-
"""`upload.instagram_upload._upload_to_netlify()` HTTP/2 sözleşmesi (2026-09-14).

NEDEN VAR: `_upload_to_netlify` `requests`ten (HTTP/1.1) `httpx.Client(http2=True)`
taşındı — makinede api.netlify.com'a HTTP/1.1 ile büyük gövde (5MB+) PUT'u
`TimeoutError: The write operation timed out` ile kesiliyordu, HTTP/2 ile
~12sn'de geçiyor (ölçülmüş, 2026-09-14). Geriye HTTP/1.1'e dönüş ise aynı
sessiz bağlantı arızasını getirir ve YouTube/IG hattı görünürde çalışmaya
devam eder.

BEŞ İDDİA:
  1. istemci `http2=True` ile kuruluyor (sözleşmenin özü).
  2. İstemci timeout'ları eski requests (connect, read) eşleniği — client
     `Timeout(30.0, connect=10.0)`, dosya PUT'u `Timeout(300.0, connect=10.0)`.
  3. Dosyalar `data=` değil `content=` (bytes) ile gidiyor.
  4. Digest deploy sözleşmesi: yalnız `required` listesindeki SHA1'ler PUT
     ediliyor; Netlify zaten pakette tutuyorsa bayt taşınmıyor.
  5. Deploy `ready` olana kadar DURUM GET'leri sürüyor; dönüş
     `ssl_url/<dosya_adı>`.

Gerçek ağa ÇIKILMIYOR: gerçek `netlify_client_secrets.json` dosyasına ve
medya dosyalarına DOKUNULMUYOR — ikisi de tmp'ye yazılan sahteler. Uyuma
olmaması için `time.sleep` yutar ve durum GET'i ilk denemede `ready` döner.
"""

import hashlib
import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import upload.instagram_upload as mod                        # noqa: E402


class _Yanit:
    def __init__(self, status_code, govde=None):
        self.status_code = status_code
        self._govde = govde or {}
        self.text = json.dumps(self._govde)

    def json(self):
        return self._govde

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Istemci:
    """httpx.Client yerine geçer; çağrıları kaydeder, hazır yanıtlar döner."""

    def __init__(self, http2=None, timeout=None):
        self.http2 = http2
        self.timeout = timeout
        self.cagrilar = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None):
        self.cagrilar.append(("POST", url, headers, json))
        # gerçek SHA1'ler: aynı içeriği "daha önce gördüğü" için 'required'da
        # HİÇBİRİ yok demek — tersi, istemcinin taklit etmesi gereken tek şey.
        return _Yanit(200, {"id": "dep1", "required": list(json["files"].values())})

    def put(self, url, headers=None, content=None, timeout=None):
        self.cagrilar.append(("PUT", url, headers, content, timeout))
        return _Yanit(200, {})

    def get(self, url, headers=None):
        self.cagrilar.append(("GET", url, headers))
        return _Yanit(200, {"state": "ready", "ssl_url": "https://cdn.example.com"})


class _IstemciRequired:
    """İkinci iskambil: deploy yalnız bir dosyanın SHA'sını 'required' görür."""

    def __init__(self, http2=None, timeout=None):
        self.puts = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None):
        dosyalar = json["files"]
        only = next(iter(dosyalar.keys()))                      # ilk dosya
        return _Yanit(200, {"id": "dep2", "required": [dosyalar[only]]})

    def put(self, url, headers=None, content=None, timeout=None):
        self.puts.append(url)
        return _Yanit(200, {})

    def get(self, url, headers=None):
        return _Yanit(200, {"state": "ready", "ssl_url": "https://cdn.example.com"})


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    """Sahte secrets + iki sahte medya dosyası + sleep'siz + taklit istemci."""
    gizli = tmp_path / "netlify_client_secrets.json"
    gizli.write_text(json.dumps({"token": "tok", "site_id": "site1"}),
                     encoding="utf-8")
    monkeypatch.setattr(mod, "NETLIFY_SECRETS_PATH", str(gizli))
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)

    f1 = tmp_path / "gorsel.png"
    f1.write_bytes(b"PNGBYTES" * 100)
    f2 = tmp_path / "video.mp4"
    f2.write_bytes(b"MP4BYTES" * 100)

    istemci = _Istemci()
    monkeypatch.setattr(mod.httpx, "Client", lambda **kw: (
        istemci.__init__(**kw) or istemci))
    return istemci, (str(f1), str(f2))


def test_http2_sözlesmesi_ve_ssl_url(ortam):
    istemci, dosyalar = ortam
    sonuc = mod._upload_to_netlify(list(dosyalar))
    assert istemci.http2 is True
    assert set(sonuc) == {"gorsel.png", "video.mp4"}
    assert all(v.startswith("https://cdn.example.com/") for v in sonuc.values())
    # ilk çağrı deploy POST'u, son çağrı durum GET'i
    assert istemci.cagrilar[0][0] == "POST"
    assert istemci.cagrilar[-1][0] == "GET"
    assert istemci.cagrilar[-1][1] == "https://api.netlify.com/api/v1/deploys/dep1"


def test_istemci_timeoutlari_eski_requestsle_eslenik(ortam):
    istemci, dosyalar = ortam
    mod._upload_to_netlify(list(dosyalar))
    co = istemci.timeout
    assert co.connect == 10.0 and co.read == 30.0


def test_dosya_put_uzun_timeout_ve_bytes(ortam):
    istemci, dosyalar = ortam
    mod._upload_to_netlify(list(dosyalar))
    putlar = [c for c in istemci.cagrilar if c[0] == "PUT"]
    assert len(putlar) == 2
    for _t, url, _h, govde, timeout in putlar:
        assert url.startswith("https://api.netlify.com/api/v1/deploys/dep1/files/")
        assert isinstance(govde, bytes), "dosya content= (bytes) ile gitmeli"
        assert timeout.connect == 10.0 and timeout.read == 300.0


def test_required_disindaki_dosya_put_edilmez(tmp_path, monkeypatch):
    """Digest deploy sözleşmesi: 'required' dışındaki SHA'lar PUT edilmez.

    Netlify paketi zaten tutuyorsa 'required'da değildir ve bayt taşınmaz.
    İkinci dosya 'required' DIŞINA düşsün diye deploy'a yalnız İLK dosyanın
    SHA'sı bildiriliyor; ikinci için PUT ÇAĞRILMAMALI."""
    gizli = tmp_path / "secrets.json"
    gizli.write_text(json.dumps({"token": "tok", "site_id": "s"}), encoding="utf-8")
    monkeypatch.setattr(mod, "NETLIFY_SECRETS_PATH", str(gizli))
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)

    f1 = tmp_path / "a.png"; f1.write_bytes(hashlib.sha1(b"A" * 50).digest() * 2)
    f2 = tmp_path / "b.mp4"; f2.write_bytes(b"B" * 50)

    istemci = _IstemciRequired()
    monkeypatch.setattr(mod.httpx, "Client", lambda **kw: istemci)
    mod._upload_to_netlify([str(f1), str(f2)])
    assert len(istemci.puts) == 1
    assert istemci.puts[0].endswith("/files/a.png")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))