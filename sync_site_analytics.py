#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py -> site/analytics.js senkronizasyonu (Madde 28).

config.py tek dogruluk kaynagi (source of truth). Bu script, config'deki
analytics ayarlarini site/analytics.js'e yazar. Yapilandirmada degisiklik
olursa calistir:

    python sync_site_analytics.py

Test kilidi: tests/test_buyume_onerileri.py::test_site_analytics_config_eslesik
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import config  # noqa: E402

HEDEF = os.path.join(REPO, "site", "analytics.js")

# analytics.js icindeki degistirilecek degerler
ALANLAR = {
    "SAGLAYICI": "ANALITIK_SAGLAYICI",
    "UYGULAMA": "ANALITIK_UYGULAMA_ADI",
    "PLAUSIBLE_DOMAIN": "ANALITIK_PLAUSIBLE_DOMAIN",
    "UMAMI_SCRIPT": "ANALITIK_UMAMI_SCRIPT",
    # NOT: ENDPOINT artik sabit string degil, dinamik ifade:
    #   var ENDPOINT = ((window.FMS_API_BASE || '') + '/api/analytics');
    # Bu yuzden sync listesinde DEGIL — API tabani sayfada
    # <script>window.FMS_API_BASE = '...';</script> ile ayarlanir.
}

# Deger JS string literal'a cevrilir
def _js_str(deger: str) -> str:
    if deger == "":
        return "''"
    return "'" + str(deger).replace("\\", "\\\\").replace("'", "\\'") + "'"


def senkronla() -> list:
    """Degisismis alanlari gunceller. [(alan, eski, yeni), ...] doner."""
    with open(HEDEF, encoding="utf-8") as f:
        icerik = f.read()

    degisen = []
    for js_adi, cfg_adi in ALANLAR.items():
        yeni_deger = _js_str(getattr(config, cfg_adi, ""))
        # ornek: var SAGLAYICI = 'self_hosted';
        desen = re.compile(
            r"(var\s+" + re.escape(js_adi) + r"\s*=\s*)(['\"][^'\"]*['\"])(\s*;)",
        )
        eslesme = desen.search(icerik)
        if not eslesme:
            raise SystemExit(f"HATA: analytics.js icinde '{js_adi}' bulunamadi")
        eski = eslesme.group(2)
        if eski != yeni_deger:
            icerik = desen.sub(lambda m: m.group(1) + yeni_deger + m.group(3), icerik, count=1)
            degisen.append((js_adi, eski, yeni_deger))

    if degisen:
        with open(HEDEF, "w", encoding="utf-8") as f:
            f.write(icerik)
    return degisen


def eslesiyor_mu() -> bool:
    """analytics.js config ile eslesiyor mu (test icin)."""
    with open(HEDEF, encoding="utf-8") as f:
        icerik = f.read()
    for js_adi, cfg_adi in ALANLAR.items():
        beklenen = _js_str(getattr(config, cfg_adi, ""))
        desen = re.compile(r"var\s+" + re.escape(js_adi) + r"\s*=\s*(['\"][^'\"]*['\"])\s*;")
        m = desen.search(icerik)
        if not m or m.group(1) != beklenen:
            return False
    return True


def main():
    degisen = senkronla()
    if not degisen:
        print("analytics.js zaten config ile eslesik — degisiklik yok.")
        return 0
    for alan, eski, yeni in degisen:
        print(f"  {alan}: {eski} -> {yeni}")
    print(f"analytics.js guncellendi ({len(degisen)} alan).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
