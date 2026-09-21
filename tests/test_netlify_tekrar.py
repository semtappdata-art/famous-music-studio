# -*- coding: utf-8 -*-
"""`netlify_kontrol.main()` tek ağ hıçkırığında SAHTE alarm üretmemeli (C-13).

NEDEN VAR (2026-09-12 denetimi): bu modülün dönüş kodu
`saglik_kontrol.netlify_araci()` → `_bildir()` → **telefon** zincirine bağlı.
İki GET'te de yeniden deneme yoktu; tek bir geçici hata (bağlantı kopması ya da
502) "Netlify/Instagram hattı arızalı" diye gerçek olmayan bir bildirim
üretiyordu. Sahte alarm, gerçek alarmın güvenilirliğini yiyor.

DÖRT İDDİA:
  1. İlk GET bir kez patlayıp sonra başarılı olursa SONUÇ SAĞLIKLI (kod 0).
  2. İlk GET bir kez 502 verip sonra başarılı olursa SONUÇ SAĞLIKLI (kod 0).
  3. İkinci GET (site_id) için de aynısı geçerli — tekrar TEK GET'e değil,
     ikisine de bağlanmalı.
  4. KALICI arıza hâlâ ALARM üretiyor (kod != 0): tekrar, gerçek arızayı
     susturan bir maskeye dönüşmemeli.
  5. 4xx TEKRARLANMIYOR: 401 = süresi dolmuş token; tekrar yalnızca hız
     sınırını yakar ve arızayı bir koşu geciktirir.

Gerçek ağa ÇIKILMIYOR ve gerçek `upload/netlify_client_secrets.json` dosyasına
DOKUNULMUYOR: `GIZLI` tmp'deki sahte bir dosyaya, `requests.get` de sayaç tutan
bir taklide çevriliyor. Bekleme süresi 0'a çekiliyor (testler uyumaz).
"""

import json
import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import netlify_kontrol                                   # noqa: E402


class _Yanit:
    def __init__(self, status_code, govde=None):
        self.status_code = status_code
        self._govde = govde or {}
        self.text = json.dumps(self._govde)

    def json(self):
        return self._govde


_KULLANICI = {"email": "x@example.com"}
_SITE = {"name": "fms", "ssl_url": "https://example.com"}


@pytest.fixture
def kurulum(tmp_path, monkeypatch):
    """Sahte secrets + uyumayan tekrar. Gerçek dosyaya/ağa dokunulmaz."""
    gizli = tmp_path / "netlify_client_secrets.json"
    gizli.write_text(json.dumps({"token": "t" * 20, "site_id": "s1"}),
                     encoding="utf-8")
    monkeypatch.setattr(netlify_kontrol, "GIZLI", str(gizli))
    monkeypatch.setattr(netlify_kontrol, "_TEKRAR_BEKLEME_SN", 0)
    return gizli


def _requests_taklidi(monkeypatch, senaryo):
    """`senaryo`: url parçasına göre sırayla dönülecek yanıt/istisna listesi."""
    import requests
    cagrilar = []

    def sahte_get(url, headers=None, timeout=None):
        cagrilar.append(url)
        anahtar = "user" if url.endswith("/user") else "site"
        sonraki = senaryo[anahtar].pop(0)
        if isinstance(sonraki, Exception):
            raise sonraki
        return sonraki

    monkeypatch.setattr(requests, "get", sahte_get)
    return cagrilar


def test_ilk_getteki_ag_hickirigi_alarm_uretmiyor(kurulum, monkeypatch):
    import requests
    cagrilar = _requests_taklidi(monkeypatch, {
        "user": [requests.ConnectionError("hıçkırık"), _Yanit(200, _KULLANICI)],
        "site": [_Yanit(200, _SITE)],
    })
    assert netlify_kontrol.main() == 0
    assert len([u for u in cagrilar if u.endswith("/user")]) == 2


def test_ilk_getteki_502_alarm_uretmiyor(kurulum, monkeypatch):
    cagrilar = _requests_taklidi(monkeypatch, {
        "user": [_Yanit(502), _Yanit(200, _KULLANICI)],
        "site": [_Yanit(200, _SITE)],
    })
    assert netlify_kontrol.main() == 0
    assert len([u for u in cagrilar if u.endswith("/user")]) == 2


def test_ikinci_get_de_tekrarlaniyor(kurulum, monkeypatch):
    """Tekrar TEK GET'e değil, ikisine de bağlanmalı."""
    import requests
    cagrilar = _requests_taklidi(monkeypatch, {
        "user": [_Yanit(200, _KULLANICI)],
        "site": [requests.ReadTimeout("hıçkırık"), _Yanit(200, _SITE)],
    })
    assert netlify_kontrol.main() == 0
    assert len([u for u in cagrilar if not u.endswith("/user")]) == 2


def test_kalici_ariza_HALA_alarm_uretiyor(kurulum, monkeypatch):
    """Tekrar, gerçek arızayı susturan bir maske olmamalı."""
    import requests
    _requests_taklidi(monkeypatch, {
        "user": [requests.ConnectionError("kapalı"),
                 requests.ConnectionError("kapalı")],
        "site": [],
    })
    assert netlify_kontrol.main() != 0


def test_kalici_502_de_alarm_uretiyor(kurulum, monkeypatch):
    _requests_taklidi(monkeypatch, {
        "user": [_Yanit(502), _Yanit(502)],
        "site": [],
    })
    assert netlify_kontrol.main() != 0


def test_401_TEKRARLANMIYOR(kurulum, monkeypatch):
    """4xx = kimlik/izin/kota. Tekrar yalnızca hız sınırını yakar."""
    cagrilar = _requests_taklidi(monkeypatch, {
        "user": [_Yanit(401)],
        "site": [],
    })
    assert netlify_kontrol.main() == 1
    assert len(cagrilar) == 1, "401 yeniden denenmemeli"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
