# Suno Ses → Çoklu Platform Video Otomasyonu

Suno'da ürettiğin şarkılardan tüm platformlar için otomatik video üretir:

- **YouTube** (16:9) → `output/youtube_16x9.mp4`
- **YouTube Shorts / TikTok / Instagram Reels** (9:16) → `output/shorts_9x16.mp4`
- **Instagram post / Facebook kare** (1:1) → `output/square_1x1.mp4`

Facebook için ayrı bir video yok — 16:9 (`youtube_16x9.mp4`) veya 1:1 (`square_1x1.mp4`)
dosyalarını doğrudan Facebook'a da yükleyebilirsin.

Videolar: ortada yuvarlak köşeli albüm kartı + kayan künye yazısı + sabit marka satırı +
ilerleme çubuğu + derinlikli arka plan içerir. Tamamen otomatik, elle video düzenleme gerekmez.

## Adım Adım Kullanım

1. **Ses dosyasını ekle** — Suno'dan indirdiğin şarkıyı şu klasöre kaydet:
   ```
   projects/<sarki-adi>/audio.wav
   ```
   (`.mp3` veya `.m4a` da olur — `.wav` sıkıştırmasız olduğu için kalite açısından önerilir,
   script otomatik algılar.)

2. **Kapak görseli ekle** — Suno'nun ürettiği kapak veya kendi görselin:
   ```
   projects/<sarki-adi>/cover.jpg
   ```
   (`.jpeg` veya `.png` da olur)

3. **(Opsiyonel) Başlık ve tür ekle** — videoya başlık metni ve türe göre renk teması
   bindirmek istersen:
   ```
   projects/<sarki-adi>/meta.json
   ```
   içeriği:
   ```json
   {"title": "Şarkı Adı", "theme": "pop"}
   ```
   `theme` seçenekleri: `pop`, `rock`, `elektronik`, `akustik`, `hiphop` — waveform ve
   başlık etrafındaki eko halkalarının rengini belirler. Belirtilmezse varsayılan `hiphop`
   (altın) kullanılır.

4. **Render et:**
   ```bash
   python render.py --project projects/<sarki-adi>
   ```

5. **Çıktıları al** — `projects/<sarki-adi>/output/` klasöründe 3 hazır video seni bekliyor,
   ilgili platforma yükleyebilirsin.

### Birden fazla şarkı

Tüm proje klasörlerini tek seferde render etmek için:
```bash
python render.py --all
```

## Ayarları değiştirmek

Çözünürlükler, zoom hızı, waveform rengi, font gibi tüm görünüm ayarları [config.py](config.py)
dosyasında — kodun geri kalanına dokunmadan oradan değiştirebilirsin.

## YouTube'a Otomatik Yükleme (Faz 2)

Video render edildikten sonra YouTube'a otomatik yüklemek için:

1. **Bir kerelik kurulum:** Google Cloud Console'da bir proje aç, YouTube Data API v3'ü
   etkinleştir, OAuth consent screen kur, bir Desktop app OAuth Client ID oluştur ve
   `upload/client_secrets.json` olarak kaydet.
2. **Bir kerelik kimlik doğrulama:**
   ```bash
   python upload/youtube_auth.py
   ```
   Tarayıcıda açılan linki tamamla — `upload/token.json` otomatik yazılır.
3. **Render + upload'ı tek komutla çalıştır:**
   ```bash
   python run_pipeline.py --project "projects/sarki-adi"
   ```
   Varsayılan görünürlük `private`. `--privacy public` veya `--privacy unlisted` ile
   değiştirilebilir. `--skip-upload` ile sadece render (upload olmadan) yapılabilir.

Tek başına upload (render zaten yapılmışsa):
```bash
python upload/youtube_upload.py --project "projects/sarki-adi"
```

## Sonraki adım (Faz 3+)

TikTok/Instagram otomatik yükleme ve analitik takibi — geliştirici hesabı onayları
gerektirdiği için ayrı bir sonraki adım. Detaylı yol haritası: proje planı dosyasında.
