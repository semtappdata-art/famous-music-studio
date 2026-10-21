# Onaylı Git Planı — 2026-09-29 (üretim checkout, main)

Durum: `HEAD == origin/main` (çekilecek 0 commit). Kirli 53 dosya + untracked yeni klasörler.

## Kural
- Üretim `main`'e direkt commit YOK. Kod → ayrı dal + PR. Runtime (`state.json`, `ozgunluk_olcum.json`, `elle_islemler.jsonl`) → bilinçli karar.
- `git reset --hard` / `clean -f` YASAK (83cd3a2 dersi).

## Sınıflandırma (git_envanter.txt'ten)
- Kod (PR'lık): `auto_process.py`, `config.py`, `ffmpeg_utils.py`, `stock_video.py`, `uyumluluk.py`, `saglik_kontrol.py`, `upload/*`, `suno_stil.py`, `tests/*`, `.github/workflows/ci_cd.yml`, `Dockerfile`, `RUNBOOK.md` vb.
- Runtime (otomasyon yazdı): `projects/*/state.json` (19), `dj_sets/*/state.json` (3), `derlemeler/*/state.json`, `ozgunluk_olcum.json`, `elle_islemler.jsonl`
- Yeni/untracked: `dj_sets/Deep-Medusa/` (meta düzeltmeli), `.scratchpad/onayli_2026-09-29/`

## Önerilen sıra (siz koşun, ben koşmadım)
```
git checkout -b claude/onayli-2026-09-29
git add <kod dosyaları tek tek>  # state.json'ları KATMA
git commit -m "..."
git push -u origin claude/onayli-2026-09-29
# PR → main merge → üretim bir sonraki saatlik koşuda pull alır
```
Runtime'lar için ayrı karar: commitlenecekse ikinci commit, değilse .gitignore.
