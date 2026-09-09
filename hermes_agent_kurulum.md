# Hermes Agent Kurulumu (Nous Research)

[Hermes Agent](https://github.com/NousResearch/hermes-agent), Nous Research'ün açık kaynak
(MIT) terminal ajanı: bir LLM sağlayıcısına bağlanır, dosya okur/yazar, komut çalıştırır,
deneyimlerinden "skill" üretir, Telegram/Discord gibi kanallardan da konuşabilir ve kendi
cron zamanlayıcısı vardır. Bu repoda Claude Code'un yanında **ikinci bir ajan** olarak
kullanılabilir — Claude Code'un yerini almaz, aynı `CLAUDE.md` bağlamını okur.

Bu belge, üretim makinesine (Windows 10/11) Hermes'i kurup bu repoyu tanıtmayı anlatır.

## 1. Kurulum (Windows, admin gerekmez)

Repo kökünde PowerShell:

```powershell
.\setup_hermes_agent.ps1
```

Script sırasıyla:

1. Resmi installer'ı (`scripts/install.ps1`, GitHub `main`) indirip çalıştırır. Installer
   `%LOCALAPPDATA%\hermes\` altına `uv` + Python 3.11 + Node.js + PortableGit + Hermes'in
   kendisini kurar, `hermes` komutunu **User PATH**'e ekler ve `HERMES_HOME` env
   değişkenini ayarlar. Mevcut Python/git kurulumuna dokunmaz (`venv\Scripts` PATH'e
   KONMAZ, `python` komutunu gölgelemez).
2. Sonunda `hermes setup` sihirbazı açılır: model/sağlayıcı seçimi (aşağıya bak).
3. Bu repoyu `hermes skills trust` ile güvenilir işaretler (bkz. bölüm 3).
4. `hermes doctor` ile doğrular.

Seçenekler:

| Komut | Ne zaman |
|---|---|
| `.\setup_hermes_agent.ps1 -SkipSetup` | Sihirbazı sonra çalıştırmak için (`hermes setup`) |
| `.\setup_hermes_agent.ps1 -TrustOnly` | Hermes zaten kuruluysa, sadece repoyu tanıt |

Kurulum bitince **yeni bir terminal aç** (PATH güncellemesi eski pencerede görünmez).

Elle kurmak istersen (script kullanmadan) resmi tek satır:

```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

Linux/macOS/WSL2 için: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
(veri `~/.hermes/`, kod `~/.hermes/hermes-agent/`).

## 2. Model / sağlayıcı seçimi

En az bir LLM sağlayıcısı gerekir. `hermes model` ile istediğin zaman değiştirilir.

| Sağlayıcı | Nasıl | Not |
|---|---|---|
| **Anthropic (API anahtarı)** | `hermes model` → Anthropic → API key, ya da `%LOCALAPPDATA%\hermes\.env` içine `ANTHROPIC_API_KEY=...` | Kullanım başına ücret, Claude aboneliğinden bağımsız. Claude Code kullanıyorsan mevcut kimlik bilgilerini de otomatik okuyabiliyor (`hermes chat --provider anthropic`). |
| **Anthropic (OAuth / Claude Max)** | `hermes model` → Anthropic OAuth | **SADECE Claude Max + satın alınmış ekstra kullanım kredisi** ile çalışıyor; Pro planla ÇALIŞMIYOR (resmi doküman). |
| **OpenRouter** | `.env` → `OPENROUTER_API_KEY=...` | 300+ model tek anahtar. |
| **Nous Portal** | `hermes setup --portal` | Ücretli abonelik; model + web arama/görsel/TTS araçları tek girişle. |
| **OpenCode Free** | `hermes model` → `free` | Anahtar gerektirmiyor, anonim; deneme için. |

Gizli anahtarlar `%LOCALAPPDATA%\hermes\.env` dosyasında durur — repoya ASLA koyma
(`.gitignore` zaten `*_secrets.json`/`*_token.json` desenlerini kapsıyor, `.env` bu repoda
kullanılmıyor).

## 3. Bu repo ile entegrasyon (ne otomatik, ne değil)

Repo kökünde `hermes` çalıştırıldığında:

- **`CLAUDE.md` otomatik yüklenir.** Hermes proje bağlamı için sırayla `.hermes.md` →
  `AGENTS.md` → `CLAUDE.md` arar, ilk bulduğunu sistem promptuna ekler. Bu repoda
  `CLAUDE.md` var, bu yüzden ayrıca bir `AGENTS.md`/`.hermes.md` YAZILMADI — iki ayrı
  bağlam dosyası zamanla birbirinden uzaklaşır, tek kaynak `CLAUDE.md` kalsın.
- **`.hermes/skills/famous-music-studio/SKILL.md` proje skill'i yüklenir** — ama SADECE
  repo bir kez `hermes skills trust` ile güvenilir işaretlendiyse (setup scripti bunu
  yapıyor; elle: repo kökünde `hermes skills trust`). Güvenlik kararı: Hermes klonlanan
  rastgele repoların skill'lerini otomatik yüklemiyor. Skill sohbette `/famous-music-studio`
  ile de çağrılır; hangi script'in ne zaman çalıştırılacağını, `state.json`/`git reset`
  gibi tuzakları ve doğrulama adımlarını anlatır. Detaylı ffmpeg bilgisi için Claude
  Code'un `.claude/skills/suno-video-render/SKILL.md` dosyasına yönlendirir (Hermes bunu
  `read_file` ile okur).
- Güvenilir repolar `%LOCALAPPDATA%\hermes\config.yaml` → `skills.trusted_project_dirs`
  altında tutulur; `hermes skills untrust` ile geri alınır.

Kontrol: repo kökünde `hermes skills list` çıktısında `famous-music-studio` görünmeli.

## 4. Günlük kullanım örnekleri

```powershell
cd <repo-kökü>
hermes                                   # sohbet (TUI için: hermes --tui)
```

Sohbette:

```
/famous-music-studio projects/yeni_sarki klasörünü render et ve kareleri doğrula
auto_process.log'daki son hatayı bul ve nedenini açıkla
ses_ve_tarz_takibi.md'ye göre sıradaki şarkı için hangi vokal/tema uygun?
```

Faydalı komutlar: `hermes doctor` (sağlık), `hermes model` (sağlayıcı), `hermes update`
(güncelle), `hermes skills list`, `hermes cron list`, `hermes gateway setup` (Telegram vb.).

## 5. Neye DOKUNMAMALI (bilinçli sınırlar)

- **Görev Zamanlayıcı görevlerini Hermes cron'a TAŞIMA.** Saatlik `auto_process.py` +
  dakikalık `watch_projects.py` + haftalık DJ Famous görevleri `setup_task_scheduler.ps1`
  ile kurulu ve `pythonw.exe` ile çalışıyor; kademeleme/golden-hour mantığı script'lerin
  içinde. Hermes cron'u en fazla haftalık rapor/hatırlatma gibi yan işler için kullan —
  aynı işi iki zamanlayıcıdan tetiklemek çift yükleme riski demek.
- **`git reset --hard` / `git clean -f` ASLA** (bkz. `CLAUDE.md`, `state.json` kazası).
  Skill dosyası bunu Hermes'e de söylüyor, ama ajanın önerdiği her komutu onaylamadan
  önce oku.
- **Gizli dosyalar** (`upload/*_secrets.json`, `*_token.json`, `notify_config.json`,
  `stock_art_config.json`) ajana okutulmamalı. Hermes'in kendi `config.yaml`'ında
  `skills.write_approval: true` ve `memory.write_approval: true` açılırsa ajanın skill/
  hafıza yazmaları onaya düşer — paylaşılan makinede önerilir.
- Hermes Windows'ta komutları **Git Bash** üzerinden çalıştırır (installer PortableGit
  kuruyor). PowerShell'e özgü komutlar (`Register-ScheduledTask` vb.) Hermes'e değil,
  doğrudan PowerShell'e yazılmalı.

## 6. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `hermes: command not found` | Yeni terminal aç; hâlâ yoksa `%LOCALAPPDATA%\hermes\bin` User PATH'te mi bak |
| `API key not set` | `hermes model` ile sağlayıcı seç |
| Türkçe karakterler bozuk | Hermes konsolu otomatik UTF-8'e çeviriyor; bozuksa Windows Terminal kullan |
| Proje skill'i listede yok | Repo kökünde `hermes skills trust`; `config.yaml`'da `skills.project_discovery: false` olmasın |
| Genel | `hermes doctor` eksik olan her şeyi ve düzeltme komutunu yazar |

## 7. Bu ortamda ne doğrulandı (2026-09-08)

Kurulum bu repoyu geliştiren Claude Code on the web konteynerinde (Linux) kaynak koddan
(`uv venv` + `uv pip install -e .`, Hermes v0.21.1) denendi: `hermes doctor` temiz,
`hermes skills trust` sonrası `hermes skills list` proje skill'ini `enabled` olarak
gösterdi. Windows installer'ı (`install.ps1`) bu ortamdan çalıştırılamadı — parametre
adları ve kurulum yerleşimi resmi dokümandan (`website/docs/user-guide/windows-native.md`,
aynı commit) alındı. İlk Windows kurulumunda `setup_hermes_agent.ps1` çıktısında bir
sorun görürsen bu belgeye not düş.
