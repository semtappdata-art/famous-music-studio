---
name: famous-music-studio
description: "Suno şarkısından çoklu platform video üretim akışı."
version: 1.0.0
author: Famous Music Studio
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [suno, ffmpeg, youtube, tiktok, instagram, automation, music]
triggers:
  - yeni şarkı ekle
  - render et
  - auto_process çalıştır
  - kapak üret
  - videoyu yükle
  - famous music studio
---

# Famous Music Studio Skill

Bu repo, Suno ile üretilen Türkçe şarkılardan otomatik olarak YouTube (uzun format +
Shorts), TikTok ve Instagram Reels videosu üretip yükleyen tek kişilik bir otomasyon
kanalıdır. Bu skill, Hermes'in bu repo içinde çalışırken hangi script'i ne zaman
çalıştıracağını ve nelere DOKUNMAMASI gerektiğini anlatır. Kod yazmaz; mevcut
pipeline'ı doğru sırayla kullandırır.

Detaylı mimari ve tasarım kararları `CLAUDE.md`'de (Hermes bunu proje bağlamı olarak
otomatik yükler). ffmpeg tuzakları ve render doğrulama yöntemi için
`.claude/skills/suno-video-render/SKILL.md` dosyasını `read_file` ile oku.

## When to Use

- Kullanıcı Suno'dan yeni bir şarkı indirdi ve `projects/<isim>/audio.wav` olarak koydu.
- Kullanıcı "render et", "kapak üret", "yükle", "auto_process çalıştır" diyor.
- `auto_process.log` / `watch_projects.log` içinde bir hata araştırılacak.
- `config.py`'deki görünüm ayarları (kart, backdrop, marquee, ilerleme çubuğu) değişecek.
- Haftalık DJ Famous seti işlenecek (`dj_sets/`, `dj_famous_process.py`) — ana katalogdan
  AYRI bir akış, karıştırma.

## Prerequisites

- Python 3 + `pip install -r requirements.txt` (repo kökünde).
- `ffmpeg`/`ffprobe` PATH'te.
- Yükleme için OAuth dosyaları `upload/` altında (gitignored; yoksa ilgili platform atlanır).
- Pexels anahtarı `stock_art_config.json` (gitignored; yoksa prosedürel bokeh'e düşer).
- Tüm komutlar repo KÖKÜNDEN çalıştırılır (`terminal` ile `cd <repo-kökü>` sonrası).

## How to Run

```bash
# Tek şarkıyı sadece render et (yükleme yok)
python render.py --project projects/<sarki-adi>

# Eksik kapak/art üret (render bunu zaten otomatik çağırır)
python generate_cover.py --project projects/<sarki-adi>

# Render öncesi sağlık kontrolü (render.py zaten çağırır, elle de çalıştırılabilir)
python validate_project.py projects/<sarki-adi>

# Tam otomasyon: kapak + render + YouTube (uzun + Shorts) + TikTok + Instagram
python auto_process.py            # otomatik kademeleme: sırası gelmediyse hiçbir şey yapmaz
python auto_process.py --count 1  # kademelemeyi atla, hemen 1 proje işle

# Testler (Windows'ta varsayılan temp klasörü sorunlu, --basetemp ŞART)
python -m pytest -q -p no:cacheprovider --basetemp="<scratchpad>/pytest_tmp"
```

## Quick Reference

| Dosya | Rol |
|---|---|
| `auto_process.py` | Üretim giriş noktası; Görev Zamanlayıcı saatte bir çağırır |
| `render.py` | ffmpeg ile 16:9 + 9:16 video |
| `generate_cover.py` | `cover.png` (16:9) + `cover_vertical.png` (9:16) + metinsiz `art.jpg` |
| `stock_art.py` | Sözlere/tarza uygun Pexels fotoğrafı (deterministik seçim) |
| `validate_project.py` | Bozuk ses / geçersiz `meta.json` / `art == cover` sızıntısı kontrolü |
| `config.py` | Tüm görünüm ve zamanlama ayarları (`THEMES`, `GOLDEN_HOURS`, …) |
| `upload/*.py` | Platform yükleyicileri + OAuth |
| `projects/<isim>/state.json` | Hangi platforma yüklendi (git'e commit'li, otomasyon günceller) |
| `<slug>_sozler.md` | Şarkı sözleri; YouTube altyazı hizalaması bunu kullanır |

## Procedure

1. **Yeni şarkı**: `projects/<isim>/audio.wav` var mı `search_files` ile doğrula. `meta.json`
   yoksa `{"title": "...", "theme": "pop|rock|elektronik|akustik|hiphop|arabesk"}` oluştur.
   Sözler dosyası (`<slug>_sozler.md`) varsa "Temiz Sözler" bölümü olduğundan emin ol.
2. **Görsel**: `art.jpg` METİNSİZ olmalı (kart içeriği + blur backdrop kaynağı). `art.*` ile
   `cover.*` byte-birebir aynıysa bu bir hatadır — `art.jpg`'yi sil, `generate_cover.py`
   yeniden üretsin.
3. **Render**: `python render.py --project ...`. Çıktı `projects/<isim>/output/`.
4. **Doğrulama**: `ffprobe` ile çözünürlük/süre; 2-3 farklı kareden PNG çıkarıp
   (`ffmpeg -vf "select=eq(n\,N)" -frames:v 1 -update 1`) backdrop'un gerçekten hareket
   ettiğini karşılaştır. Tek kare yetmez.
5. **Yükleme**: Elle tetiklemek gerekiyorsa `python auto_process.py --count 1`. Normalde
   Görev Zamanlayıcı'ya bırak; aynı anda birden çok şarkı paylaşma (kademeleme kararı).
6. **Sonuç**: `auto_process.log` son satırlarını `read_file` ile oku, `state.json`'a hangi
   platformların yazıldığını kontrol et.

## Pitfalls

- **`git reset --hard` / `git clean -f` ASLA çalıştırma**: `projects/*/state.json` commit'li ama
  otomasyon tarafından commit'siz güncelleniyor; sert komutlar yükleme kayıtlarını siler
  (daha önce oldu). Önce `git status`, gerekeni commit'le.
- `auto_process.py` zaten `git pull --ff-only` yapıyor; `main` dışında bir daldaysan dokunmaz.
- Instagram'da yayınlanmış medya API'den SİLİNEMEZ; TikTok yalnızca taslak/gelen kutusuna
  yüklenir, kullanıcı uygulamadan elle yayınlar. Bunları "otomatikleştirmeye" çalışma.
- Caption'a YouTube linki KOYMA (yorum olarak gidiyor); "#AIMusic" gibi AI-vurgulu hashtag
  KULLANMA; kapağa müzik türü YAZMA. Bunlar bilinçli kullanıcı kararları (`CLAUDE.md`).
- Görev Zamanlayıcı görevlerini Hermes cron ile ÇİFTLEME: saatlik `auto_process.py` ve
  dakikalık `watch_projects.py` zaten kurulu (`setup_task_scheduler.ps1`). Hermes cron
  yalnızca rapor/hatırlatma gibi yan işler için uygundur.
- `.ps1` dosyaları UTF-8 **BOM'lu** kaydedilmeli (Windows PowerShell 5.1 Türkçe karakter).
- Windows'ta `/tmp` yok; geçici dosyalar için scratchpad/temp dizini kullan.
- `upload/*_secrets.json`, `*_token.json`, `notify_config.json`, `stock_art_config.json`
  gitignored gizli dosyalardır: içeriğini okuma, loglama, commit'leme.

## Verification

- `python -m pytest -q -p no:cacheprovider --basetemp=<temp>` → tüm testler geçmeli.
- `python validate_project.py projects/<isim>` → "HATA" satırı olmamalı.
- `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 projects/<isim>/output/youtube_16x9.mp4` → `1920,1080`; `shorts_9x16.mp4` → `1080,1920`.
- `auto_process.log` son koşuda traceback içermemeli.
