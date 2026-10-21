# -*- coding: utf-8 -*-
"""Madde 30 — deploy kayitlari (deploy_site.py, GitHub Actions durumu)."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ---------------------------------------------------------------- BUYUME
YOL = "BUYUME_ONERILERI.md"
with open(YOL, encoding="utf-8") as f:
    c = f.read()

ESKI = "- Detaylı rehber: `site/DEPLOY.md`."
YENI = """- **TEK KOMUTLU DEPLOY (2026-10-21):** `python deploy_site.py`
  1. Testler (62) — hata varsa DURUR
  2. JS/HTML brace denetimi
  3. `config` -> `analytics.js` senkronu
  4. Netlify deploy (statik + API fonksiyonlari)
  5. Post-deploy smoke test (sayfalar 200 + API 204/200)
  6. GitHub Pages publish (`docs/`)
  Sure: ~110 sn. GitHub Actions'a GEREK YOK.
- **GITHUB ACTIONS KULLANILAMAZ (2026-10-21):** PAT'te `workflow` scope yok ->
  GitHub workflow dosyasi push'unu reddediyor ("refusing to allow an OAuth App to
  create or update workflow ... without `workflow` scope"). Cozum: PAT'e
  `workflow` scope ekle (Settings > Developer settings > Personal access
  tokens) VEYA `gh auth refresh -s workflow` (device flow, tek onay).
  `deploy_site.py` bu gereksinimi **ortadan kaldirir** — GitHub Actions
  olmadan ayni is yepilir.
- **PUSH ENGELI (cozuldu):** repo 4.4 GB + 872 MB `audio.wav` gibi dosyalar
  GitHub'in 100 MB/dosya limitini asiyordu. Cozum: `git filter-branch` ile
  gecmisten uretim medyasi + credential dosyalari (`upload/token.json`,
  `.env*`) temizlendi; `.gitignore`'a eklendi. Artik `git push` calisiyor.
- **`.gitignore` TUZAKI (2026-10-21):** `.gitignore`da `.github/` kalibi
  vardi -> workflow dosyalari HIC commit edilemiyordu (CI hic calismadi).
  Kalip kaldirildi.
- **`pytest.ini` SINIRI:** INI formatinda COK SATIRLI deger desteklemez ->
  `collect_ignore` `pytest.ini`'de CALISMAZ. `conftest.py`'ye tasindi.
- **GIZLI ANAHTAR SIZINTISI (2026-10-21):** `.env.template` icinde 13 gercek
  API anahtari vardi (OpenRouter, Together, Google, HF, Runway, Higgsfield,
  Stability, Luma, Pika, Kling, MiniMax, Haiper, Postwire) + history'de
  YouTube OAuth token'i. Hepsi placeholder yapildi, gecmisten temizlendi.
  **!! Bu anahtarlar rotate EDILMELI (dashboard'dan yenisi alin).**

- Detaylı rehber: `site/DEPLOY.md`."""

if ESKI in c:
    c = c.replace(ESKI, YENI, 1)
    print("  BUYUME_ONERILERI.md: deploy notlari eklendi")
else:
    print("  BUYUME_ONERILERI.md: metin bulunamadi")

with open(YOL, "w", encoding="utf-8") as f:
    f.write(c)

# ---------------------------------------------------------------- CLAUDE
with open("CLAUDE.md", encoding="utf-8") as f:
    k = f.read()

ESKI_K = "Rehber: `site/DEPLOY.md`."
YENI_K = ("Rehber: `site/DEPLOY.md`. **Deploy:** `python deploy_site.py` (tek komut: "
          "test → Netlify → smoke test → GitHub Pages). GitHub Actions PAT'te "
          "`workflow` scope olmadığı için kullanılamıyor; `deploy_site.py` "
          "onun yerini alır.")

if ESKI_K in k:
    k = k.replace(ESKI_K, YENI_K, 1)
    print("  CLAUDE.md: deploy notu guncellendi")
else:
    print("  CLAUDE.md: metin bulunamadi")

with open("CLAUDE.md", "w", encoding="utf-8") as f:
    f.write(k)
print("OK")
