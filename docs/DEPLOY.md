# Famous Music Studio — Site Deploy Rehberi

Statik site + 2 Netlify Function (analitik, topluluk). Site klasörü
`site/`, deploy yapılandırması repo kökünde `netlify.toml`.

## ✅ DURUM (2026-10-21)

| Katman | Durum | Adres |
|--------|-------|-------|
| **Statik site** | ✅ **CANLIDA** | `https://semtappdata-art.github.io/famous-music-studio/` |
| GitHub Pages kaynak | ✅ | `main` branch, `/docs` klasörü |
| API fonksiyonları | ⬜ Netlify gerekli | `/api/analytics`, `/api/topluluk` |

> **GitHub Pages ALTYOL servis eder** (`/famous-music-studio/`) → mutlak
> yollar 404 verir. Bu yüzden tüm iç linkler **göreli** (`privacy.html`,
> `epk/bio.html`) ve API ucu `window.FMS_API_BASE` ile ayarlanabilir.
>
> **GitHub Pages statiktir** → `site/api/*.py` fonksiyonları ÇALIŞMAZ.
> Analitik + topluluk için Netlify (veya Vercel) şart.

## 🚀 Hızlı Yayınlama (GitHub API — push'suz)

Repo 4.4 GB olduğu için `git push` HTTP 408 (timeout) veriyor. Sadece
`docs/` altındaki site dosyalarını API ile yükle:

```bash
python publish_site_github.py --dry-run   # ne yüklenecek
python publish_site_github.py             # yayınla
```
> GitHub PAT: `git credential fill` (protocol=https, host=github.com) veya
> `GITHUB_TOKEN` ortam değişkeni.

## 1. Netlify ile deploy (API fonksiyonları için)

### A. Netlify CLI (hızlı)
```bash
npm install -g netlify-cli
cd C:/Users/ACER/Desktop/ilk-projem
netlify login
netlify init          # site/ + site/api/ seç, netlify.toml otomatik algılanır
netlify deploy --prod
```

### B. Netlify Dashboard (UI)
1. https://app.netlify.com → **Add new site** → **Import an existing project**
2. Repo: `semtappdata-art/famous-music-studio`
3. Build command: **boş bırak**
4. Publish directory: `site`
5. Functions directory: `site/api`
6. **Deploy site**

> Netlify login gerekir (tarayıcı OAuth). `netlify login` → tarayıcıda
> "Authorize" → sonra `netlify deploy --prod`.

### Netlify'e bağlandıktan sonra
1. Netlify site adresini `site/index.html` içindeki
   `<script>window.FMS_API_BASE = '';</script>` satırına yaz:
   ```html
   <script>window.FMS_API_BASE = 'https://<netlify-site>.netlify.app';</script>
   ```
2. `python publish_site_github.py` ile GitHub Pages'e tekrar yayınla
3. Artık ziyaretçiler analitik topluluk formu çalışır durumda olur.

### C. Netlify Dashboard (manuel)
- **Sites** → **Add new site** → **Deploy manually**
- `site/` klasörünü sürükle-bırak
- Sonra: Site settings → Functions → `site/api`

---

## 2. Alan adı

`Site settings` → `Domain management` → **Add custom domain**:
```
famousmusicstudio.com
www.famousmusicstudio.com
```
> Netlify otomatik SSL (Let's Encrypt) verir.

DNS'te CNAME kaydı:
```
famousmusicstudio.com      →  <netlify-site>.netlify.app
www.famousmusicstudio.com  →  <netlify-site>.netlify.app
```

---

## 3. GitHub Actions ile otomatik deploy

`.github/workflows/deploy-site.yml` → her `main` push'unda otomatik deploy.
Gerekli secret: `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID`.

Repo → **Settings** → **Secrets and variables** → **Actions**:
| Name | Value |
|------|-------|
| `NETLIFY_AUTH_TOKEN` | Netlify → Account settings → API tokens → New token |
| `NETLIFY_SITE_ID` | Site settings → General → API ID |

---

## 4. Alternatif: GitHub Pages

`site/` klasörü doğrudan Pages'a gider. **DİKKAT:** GitHub Pages statiktir,
`site/api/*.py` fonksiyonları **çalışmaz** → analitik ve topluluk endpoint'leri
ölmüş olur.

Çözümler:
- **A)** Sadece statik site (analitik/topluluk kapalı) — `site/analytics.js`
  içindeki `SAGLAYICI` değerini `yok` yap.
- **B)** Vercel'e deploy et (`api/` klasörü Vercel'de otomatik fonksiyondur):
  ```bash
  # vercel.json
  { "functions": { "api/analytics.py": {}, "api/topluluk.py": {} } }
  ```
  Vercel'de `api/` klasörü kökte olmalı → `site/api` → kök `api` kopyalanır.

---

## 5. API doğrulama (deploy sonrası)

```bash
# Analitik
curl -X POST https://famousmusicstudio.com/api/analytics \
  -H "Content-Type: text/plain" \
  -d '{"path":"/","device":"masaustu","lang":"tr-TR"}' -i
# → HTTP 204 beklenir

# Topluluk
curl -X POST https://famousmusicstudio.com/api/topluluk \
  -H "Content-Type: text/plain" \
  -d '{"email":"test@example.com","kaynak":"site"}' -i
# → HTTP 204 beklenir

# Sayfalar
curl -s -o /dev/null -w "%{http_code}\n" https://famousmusicstudio.com/
curl -s -o /dev/null -w "%{http_code}\n" https://famousmusicstudio.com/privacy
curl -s -o /dev/null -w "%{http_code}\n" https://famousmusicstudio.com/epk
curl -s -o /dev/null -w "%{http_code}\n" https://famousmusicstudio.com/robots.txt
```

---

## 6. Yerel test (Netlify dev)

```bash
cd C:/Users/ACER/Desktop/ilk-projem
npx netlify dev
# → http://localhost:8888  (API fonksiyonlari dahil)
```
> `netlify dev` olmadan da API'ler çalışır:
> ```bash
> python site/api/analytics.py   # http://127.0.0.1:8792
> python site/api/topluluk.py    # http://127.0.0.1:8793
> ```
> Bu durumda `config.ANALITIK_ENDPOINT` ve topluluk fetch URL'ini
> `http://127.0.0.1:8792/` / `http://127.0.0.1:8793/` yapın.

---

## 7. Dosya haritası

```
site/
├── index.html            ← Ana sayfa
├── privacy.html          ← /privacy
├── 404.html              ← 404
├── analytics.js          ← Analitik istemcisi (Madde 28)
├── robots.txt
├── sitemap.xml
├── package.json          ← netlify-cli
├── og-cover.jpg          ← Open Graph (1200×630)
├── assets/
│   ├── youtube-banner-2560x1440.png
│   └── brand/icon_big.jpg
├── epk/
│   ├── bio.html          ← /epk
│   ├── bio.md / bio.json
│   ├── photos_README.md
│   ├── music_assets_README.md
│   └── booking.md
└── api/
    ├── analytics.py      ← Netlify Function (Madde 28)
    └── topluluk.py       ← Netlify Function (Madde 29)
```

---

## 8. Topluluk/Discord kurulumu (deploy sonrası)

```jsonc
// topluluk_config.json (repo kökü — deploy'a DAHİL EDİLMEZ!)
{
  "discord_webhook_url": "https://discord.com/api/webhooks/..."
}
```
> ⚠️ `topluluk_config.json` **gizlidir**, `.gitignore`'da olmalı.
> Netlify'e yüklemek için environment variable kullan:
> `Site settings → Environment variables → DISCORD_WEBHOOK_URL`
> (kod `config.TOPLULUK_DISCORD_WEBHOOK` ile okur).

Telegram: `upload/telegram_client_secrets.json` içindeki `bot_token` gerçek
olmalı (şu an placeholder `123456789:AA...`).
