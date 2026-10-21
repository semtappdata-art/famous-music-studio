# Famous Music Studio - Automation Pipeline

AI-powered music generation, cover art, video rendering, and multi-platform publishing automation.

## Quick Start

```bash
# 1. Add API keys to .env
echo "GROQ_API_KEY=gsk_xxx" >> .env

# 2. Test models
python -m universal_model "5+3?"
python -m universal_model --model f&f "async retry"

# 3. Check pipeline status
python -m universal_model fms-status

# 4. Check API keys
python -m universal_model env

# 5. Web UI
python web_ui.py  # http://localhost:8000
```

## Architecture

```
audio.wav → generate_cover.py → validate_project.py → render.py → auto_process.py
                                                              ↓
                                          upload/*.py (YouTube, TikTok, IG, FB, Telegram, Bluesky)
```

## Features

- **Universal Model Connector** - 50+ models, auto-fallback, cost tracking
- **f&f Brand** - Free & Famous local models (gemma2:2b, phi3.5, qwen3.5:4b)
- **Özgür Ünlü** - Turkish brand aliases for local models
- **Streaming** - Real-time response streaming
- **Web UI** - FastAPI web interface
- **FMS Integration** - Direct pipeline control
- **Cost Tracking** - Per-call cost logging
- **Turkish Encoding** - Windows cp1254 fix
- **KB + Feedback** - Self-learning knowledge base

## API Keys

| Provider | Key | Free? |
|----------|-----|-------|
| OpenRouter | `OPENROUTER_API_KEY` | ✅ Free tier |
| Anthropic | `ANTHROPIC_API_KEY` | ❌ Paid |
| NVIDIA | `NVIDIA_API_KEY` | ✅ Free tier |
| Kling | `KLING_API_KEY` | ✅ Free tier |
| Groq | `GROQ_API_KEY` | ✅ Free tier |
| Together | `TOGETHER_API_KEY` | ✅ Free tier |
| Google AI | `GOOGLE_API_KEY` | ✅ Free tier |

## Models

### Local (Free)
- `gemma2:2b` - Fastest, 1.6GB
- `phi3.5:latest` - Reasoning, 2.1GB
- `qwen3.5:4b` - Best code, 3.3GB

### Cloud Free
- `nemotron-3.5-lightning` - 550B MoE
- `ling-3.1-flash` - Fast
- `apodex-mini` - Reasoning

### Brand Aliases
- `f&f` → gemma2:2b
- `özgür-ünlü` → gemma2:2b
- `f&f-code` → qwen3.5:4b
- `özgür-ünlü-kod` → qwen3.5:4b

## CLI

```bash
python -m universal_model "soru"
python -m universal_model code "async retry"
python -m universal_model --model f&f "prompt"
python -m universal_model cost
python -m universal_model env
python -m universal_model stream "prompt"
python -m universal_model models --local
python -m universal_model fms-status
python -m universal_model fms-fix render.py "issue"
```

## Project Structure

```
ilk-projem/
├── universal_model.py      # Main model connector
├── web_ui.py               # FastAPI web UI
├── benchmark.py            # Model benchmark
├── .env                    # API keys (NOT committed)
├── .env.template           # Key template
├── .gitignore              # Git ignore
├── CLAUDE.md               # Project rules
├── tests/                  # Integration tests
│   ├── test_kurallar.py    # Rule tests
│   └── test_integration.py # Pipeline tests
├── upload/                 # Platform publishers
│   ├── youtube.py
│   ├── tiktok.py
│   ├── instagram.py
│   └── ...
└── .universal_kb/          # Knowledge base
└── .feedback/              # Feedback loop
```

## Rules (CLAUDE.md)

- State writes only via `state_io.atomic_write()`
- Fail-closed: error = skip project, continue pipeline
- 7 policy gate checkpoints
- Turkish lower: İ→i, I→ı BEFORE lower()
- No `\n` in drawtext, use `chr(10)`
- No AI hashtags

## CI/CD

```bash
# Run tests
python -m pytest -q -p no:cacheprovider --basetemp="C:\pytest_tmp"

# Lint
ruff check .

# Type check
mypy --strict .
```

## Notification System

```python
from universal_model import notify

# Slack
notify.send("Slack", message="Pipeline started", webhook_url=os.getenv("SLACK_WEBHOOK_URL"))

# Teams
notify.send("Teams", message="Pipeline started", webhook_url=os.getenv("TEAMS_WEBHOOK_URL"))

# Telegram
notify.send("Telegram", message="Pipeline started", bot_token=os.getenv("TELEGRAM_TOKEN"), chat_id=os.getenv("TELEGRAM_CHAT_ID"))
```

## Backup

```bash
# Auto-backup .env and state files
python -c "
import shutil, datetime
date = datetime.datetime.now().strftime('%Y%m%d')
shutil.copy2('.env', f'.env.backup.{date}')
shutil.copy2('state.json', f'state.backup.{date}.json')
print(f'Backed up to .env.backup.{date}')
"
```

## License

MIT