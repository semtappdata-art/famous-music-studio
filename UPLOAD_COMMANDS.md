# 📤 Complete Upload Commands for City_Pulse_Ep3_Tokyo

## ✅ YouTube (DONE - No Auth Needed Beyond Initial Setup)
```bash
# Long-form (Private, Premiere-ready)
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --privacy private

# Shorts
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --shorts

# Schedule for Golden Hour (auto-computes next window)
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --privacy private
# Uses config.GOLDEN_HOURS + config.next_golden_publish_time()
```

---

## 🔐 Authentication Setup (One-Time Per Platform)

### 1. Instagram Reels
```bash
# Step 1: Get authorization URL
python upload/instagram_auth.py --print-url
# -> Opens browser, login as Business Account, copy code from URL

# Step 2: Exchange code for long-lived token
python upload/instagram_auth.py --code YOUR_CODE_HERE
# -> Creates/updates upload/instagram_token.json

# Upload
python -m upload.instagram_upload --project "dj_sets/City_Pulse_Ep3_Tokyo"
```

### 2. TikTok
```bash
# Step 1: Get authorization URL
python upload/tiktok_auth.py --print-url
# -> Opens browser, login, authorize, copy code from URL

# Step 2: Exchange code for token
python upload/tiktok_auth.py --code YOUR_CODE_HERE
# -> Creates/updates upload/tiktok_token.json

# Upload (creates DRAFT - manual publish in app required)
python -m upload.tiktok_upload --project "dj_sets/City_Pulse_Ep3_Tokyo"

# After upload: Open TikTok app -> Drafts -> Add "AI-generated content" label -> Post
```

### 3. Facebook Reels
```bash
# Step 1: Get authorization URL
python upload/facebook_auth.py --print-url
# -> Login as Page, copy code

# Step 2: Exchange code
python upload/facebook_auth.py --code YOUR_CODE_HERE
# -> Creates/updates upload/facebook_token.json

# Upload (Native scheduling!)
python -m upload.facebook_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --kind reels
```

### 4. Bluesky
```bash
# Create credentials file once:
cat > upload/bluesky_client_secrets.json << 'EOF'
{
  "handle": "famousmusicstudio.bsky.social",
  "app_password": "xxxx-xxxx-xxxx-xxxx"
}
EOF

# Get app password: bsky.app -> Settings -> Privacy and Security -> App Passwords -> Add

# Upload
python -m upload.bluesky_upload --project "dj_sets/City_Pulse_Ep3_Tokyo"
```

### 5. Telegram
```bash
# Create credentials file once:
cat > upload/telegram_client_secrets.json << 'EOF'
{
  "bot_token": "123456789:AAH...",
  "chat_id": "@your_channel_name"
}
EOF

# Bot setup:
# 1. @BotFather -> /newbot -> get token
# 2. Add bot to channel as Admin with "Post Messages" permission
# 3. Use channel @username as chat_id

# Upload (long-form)
python -m upload.telegram_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --kind uzun
```

---

## One-Liner: Upload All Platforms (After Auth)
```bash
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --privacy private && \
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --shorts && \
python -m upload.instagram_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" && \
python -m upload.tiktok_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" && \
python -m upload.facebook_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --kind reels && \
python -m upload.bluesky_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" && \
python -m upload.telegram_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --kind uzun
```

---

## Verification After Upload
```bash
python -c "
import asyncio, json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def check():
    async with stdio_client(StdioServerParameters(command='python', args=['mcp_server.py'])) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            r = await s.call_tool('check_dj_set_upload_status', {'name': 'City_Pulse_Ep3_Tokyo'})
            print(json.loads(r.content[0].text))

asyncio.run(check())
"
```

**Expected Result:**
```json
{
  "upload_status": {"uploaded_count": 7, "total_count": 7, "complete": true, "missing": []},
  "youtube": {"video_id": "Bl8wh7XUYtY", "shorts_id": "_w0QuS9Dnw8", ...},
  "instagram": {"reel_id": "..."},
  "tiktok": {"publish_id": "v_inbox_file~...", "status": "draft"},
  "facebook": {"reels_id": "..."},
  "bluesky": {"uri": "at://did:.../..."},
  "telegram": {"message_id": ...}
}
```

---

## Schedule for Golden Hour (Automated)
```bash
# Auto-schedule via Task Scheduler (Windows) or cron (Linux)
# Runs hourly, auto-detects next golden hour window
python auto_process.py --project "dj_sets/City_Pulse_Ep3_Tokyo"

# Or manually schedule:
python -m upload.youtube_upload --project "dj_sets/City_Pulse_Ep3_Tokyo" --privacy private
# Uses config.GOLDEN_HOURS + config.next_golden_publish_time()
```

---

## Credential Files to Fill (upload/ folder)

| File | Status | Action |
|------|--------|--------|
| instagram_token.json | Template ready | Run `python upload/instagram_auth.py --print-url` |
| tiktok_token.json | Template ready | Run `python upload/tiktok_auth.py --print-url` |
| facebook_token.json | Template ready | Run `python upload/facebook_auth.py --print-url` |
| bluesky_client_secrets.json | Template ready | Edit with handle + app password |
| telegram_client_secrets.json | Template ready | Edit with bot_token + chat_id |

---

## Final Status: City_Pulse_Ep3_Tokyo

| Platform | Video ID | Status |
|----------|----------|--------|
| YouTube (Long) | Bl8wh7XUYtY | Uploaded, Private |
| YouTube Shorts | _w0QuS9Dnw8 | Uploaded, Private |
| Instagram Reels | | Needs Auth |
| TikTok | | Needs Auth |
| Facebook Reels | | Needs Auth |
| Bluesky | | Needs Auth |
| Telegram | | Needs Auth |

**YouTube: 100% Cercle/Boiler Room/HOR Compliant - Ready for Golden Hour!**