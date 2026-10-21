# Ultra Code Agent — Hızlı Başlangıç

## Model
**gemma2:2b** (ollama, 1.6GB, ücretsiz, en hızlı)
- 2-3sn basit sorular
- 8-15sn code/arch/debug
- <300 token/sorgu

## Kurulum
```bash
# Ollama zaten kurulu
ollama pull gemma2:2b  # 1.6GB indirir
ollama serve &         # arka planda çalıştır
```

## Kullanım
```python
from agent_core import ask, code, debug, arch, review, test, opt, fix, kb_add, report

# Basit soru
ask("5+3 kacar?")
# [A] 8 kacar.
# [C] result = 5 + 3; print(result)
# [W]  This code calculates...

# Code generation
code("async context manager for db pool")
code("retry decorator with exponential backoff", lang="python")

# Debug
debug("kod...", "AttributeError: 'NoneType'...")

# Architecture
arch("microservice with event sourcing")

# Code review
review("kod...")

# Tests
test("fonksiyon...")

# Optimization
opt("slow query in postgres")

# Project fix
fix("proje_adi", "hata mesaji")

# Knowledge base
kb_add("python", "venv", "python -m venv .venv && .venv/Scripts/activate")

# Report
report()
# KB:1.5KB | FB:0 | avg:0.0/5
```

## CLI
```bash
python -m agent_core "soru"
python -m agent_core code "async context manager"
python -m agent_core debug "kod" "hata"
python -m agent_core arch "servis tasarimi"
python -m agent_core review "kod"
python -m agent_core test "kod"
python -m agent_core opt "slow query"
python -m agent_core fix "proje" "hata"
```

## KB Format
`.agent_core/kb.jsonl` — domain:key:value
- `python:venv:python -m venv .venv`
- `docker:build:docker build -t name .`

## Feedback Loop
```python
ask("soru", fb=True)  # 1-5 puan + düzeltme → KB'ye yazar
```

## Performans
| Task | Süre | Token |
|------|------|-------|
| Matematik | ~2-3s | ~50 |
| Basit code | ~8-12s | ~150 |
| Complex arch | ~12-18s | ~250 |

## Not
- Model CPU-only (8GB RAM, 8 core) — GPU yoksa yavaştır
- `num_predict=128` — kısa ama yeterli
- KB otomatik büyür, feedback ile zekileşir