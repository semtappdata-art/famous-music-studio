---
name: fms-tiktok-yayin
description: Famous Music Studio'nun render edilmiş bir parçasını higgsfield MCP bağlayıcısı üzerinden TikTok'a yayınlama akışı. Kullanıcı "şu parçayı TikTok'a yayınla / gönder / at" dediğinde, panodaki TikTok bekleyen listesini işlerken, ya da TikTok yayınının neden otomatikleşemediği sorulduğunda kullan. DIRECT_POST geri alınamaz — bu skill onay ve doğrulama sırasını tanımlar.
---

# TikTok Yayını — higgsfield MCP üzerinden

## Bu neden elle bir adım (ve neden öyle kalıyor)

Deponun kendi TikTok uygulamasında **`video.publish` izni yok**. App review
"Uygulamalar özel veya kişisel kullanım için olmamalıdır" gerekçesiyle
reddediyor ve bu tek kişilik operasyon için aşılabilir değil. Alternatiflerin
hepsi elendi: denetimsiz DIRECT_POST `SELF_ONLY` + gizli hesap şartı getiriyor
(mevcut akıştan kötü), sandbox herkese açık yayına kapalı, TikTok for Business
aynı duvarı istiyor, TikTok Shop Türkiye'de yok, Postiz/Mixpost yine senin
onaylı app'ini istiyor.

Çalışan tek yol: **higgsfield MCP bağlayıcısı** — onaylı bir Content Posting
API istemcisi, ücretsiz, hesap zaten bağlı.

**Ama higgsfield'ın genel REST API'sinde sosyal yayın YOK** (docs.higgsfield.ai
endpoint listesi: kimlik doğrulama, istek yaşam döngüsü, dosya yükleme, hata,
faturalama, SDK — hepsi üretken medya). TikTok bağlayıcısı yalnızca MCP
katmanında ve claude.ai hesabına bağlı. Görev Zamanlayıcı'dan koşan
`auto_process.py` ona erişemez.

Sonuç — iş bilerek ikiye bölündü:
1. Boru hattı videoyu render eder ve yayın planını üretir.
2. **Bu skill** ile asistan, kullanıcı istediğinde MCP'den gönderir.

## Adım 1 — Planı al (caption'ı ASLA uydurma)

```bash
python upload/tiktok_publish_plan.py --project "projects/<Şarkı Adı>" --json
```

Salt okunur, hiçbir şey göndermez. Döndürdüğü alanlar:

| alan | ne için |
|---|---|
| `video` | `output/shorts_9x16.mp4` tam yolu |
| `caption` | `description` alanına gider (4000 sınır) |
| `baslik_150` | `title` alanına gider — TikTok'un 150 karakter sınırı |
| `ilk_yorum` | yayından SONRA elle eklenecek YouTube linki |
| `kapak` | `cover_vertical.png` — TikTok uygulamasından elle yüklenir |
| `aigc` | her zaman `true` (şarkı Suno üretimi) |
| `onerilen_gizlilik` | `SELF_ONLY` ya da `PUBLIC_TO_EVERYONE` |
| `hazir` / `engel` | `hazir` false ise **gönderme** — `engel` sebebini söyler |
| `uyumluluk_hatalari` / `uyumluluk_uyarilari` | politika kapısının TAMAMI (sadece ilk engel değil) |
| `taslak_id` | `tiktok_publish_id` — boru hattının yüklediği taslağın kimliği |

**Plan 2026-09-12'den beri POLİTİKA KAPISINDAN geçiyor**: `build_plan()`
`uyumluluk.kontrol(..., "yukleme")` + TikTok'a özel ikiz kapısını
(`_tiktok_ikiz_kapisi`) çalıştırıyor. `hazir: false` ise **yayınlama**, önce
`engel` alanını oku. Bugün gerçek katalogda iki taslak engel alıyor:
`projects/Küllerimden Geç` (ikiz — `Yeniden Doğacağım` ile aynı md5, meşru
taraf O) ve `dj_sets/City Pulse Set` (telif eşleşmesi kayıtlı). Kapı çökerse
`hazir` yine **false** olur, sessizce açılmaz.

**Caption deponun `social_text.build_caption()` fonksiyonundan gelir, senin
kafandan değil.** Böylece MCP'den giden metin boru hattının ürettiğiyle birebir
aynı olur. Metni düzenleme, kısaltma, "iyileştirme" — kullanıcı açıkça
istemedikçe olduğu gibi gönder.

**`title` vs `description`:** 18/18 caption 150 karakteri aşıyor (200-252),
bu yüzden tam caption `description`'a, ilk satır (hook) `title`'a gider.
Hangisinin TikTok'ta görüneceği ilk `SELF_ONLY` gönderisinde gözle
doğrulanmalı — bu henüz teyit edilmedi.

## Adım 2 — MCP zinciri

`connector_id`: `tiktok_accounts` ile al (status `active` olmalı).

1. `media_upload` — `filename` + `content_type: video/mp4` → presigned URL + `media_id`
2. `curl -X PUT -H "Content-Type: video/mp4" --data-binary @<video> "<upload_url>"` → HTTP 200 şart
3. `media_confirm` — `type: video`, `media_id`
4. `tiktok_prepare_publish` — `mode: DIRECT_POST`, `media_type: VIDEO`,
   `video_url` (**higgsfield-hosted olmalı**, yerel yol veya başka domain kabul
   edilmiyor), `title`, `description`, `is_aigc: true`, `privacy_level`
   → `publish_session_id` + `required_confirmations`
5. `tiktok_publish` — `publish_session_id`, `user_confirmed: true`,
   `preview_confirmed: true` ve prepare'in `required_confirmations` listesindeki
   **her bayrak** → `publish_id`
6. `tiktok_publish_status` — `PROCESSING_DOWNLOAD` → yayınlandı

Medya sınırları (prepare çağrılmadan önce kontrol et): MP4/WebM/MOV, ≤1 GB,
3-600 sn, her kenar ≥360 px, 23-60 FPS. Projenin `shorts_9x16.mp4` dosyaları
1080x1920 / 30 FPS / 3-5 MB — hepsi uygun.

## Adım 3 — state.json'a yaz (ELLE YAZMA — komutla işaretle)

Gönderim başarılıysa `tiktok_published_at` ve `tiktok_dogrulandi` alanlarını
`state.json`'a **elle yazma**; deponun kendi işaretleyicisini çalıştır. Atomik
yazım (`state_io`), `tiktok_publish_id` önkoşulu ve idempotenslik oradan geliyor
(`upload/tiktok_publish_plan.py`, "ELLE YAYIN SONRASI İŞARETLEME" docstring'i):

```bash
python upload/tiktok_publish_plan.py --yayinlandi "projects/<Şarkı Adı>"
python upload/tiktok_publish_plan.py --dogrulandi "projects/<Şarkı Adı>"   # ilk SELF_ONLY gönderi gözle doğrulandıktan sonra, BİR KEZ
```

- `--yayinlandi` → `tiktok_published_at` (panodaki bekleyen listesi bunu okuyup
  satırı düşürür; ikiz kapısının "ikiz zaten yayınlanmış → ENGEL" kuralını da bu
  besler). `state.json`'da `tiktok_publish_id` yoksa REDDEDER ("hiç yüklenmemiş");
  zaten işaretliyse hata değil, "değişiklik yok" der. `tiktok_dogrulandi`'yı
  BİLEREK yazmaz — yayınlamak doğrulamak değildir.
- `--dogrulandi` → `tiktok_dogrulandi: true`, **yalnızca** kullanıcı SELF_ONLY
  gönderisinde başlık/açıklama/AIGC etiketini gözle doğruladıktan sonra. Önkoşul:
  o proje `--yayinlandi` ile işaretlenmiş olmalı. Bayrak **KANAL seviyesinde**
  okunuyor (`_kanal_dogrulandi`): bir kez, tek bir projede yazılması yeter — her
  projede tekrar gerekmiyor; ondan sonra plan tüm kanal için `PUBLIC_TO_EVERYONE`
  önerir.
- `tiktok_publish_id` (dönen `publish_id`) ve `tiktok_privacy` (kullanılan
  `privacy_level`) için ayrı bir komut yok. MCP yolunda taslak boru hattından
  gelmediyse bu ikisini `state_io.durum_yaz(proje, durum)` ile yaz — `open(..., "w")`
  ile DEĞİL (CLAUDE.md kuralı) — ve `--yayinlandi`'yı ONDAN SONRA çalıştır
  (önkoşulu `tiktok_publish_id`).

## Kırmızı çizgiler

- **`DIRECT_POST` geri alınamaz.** Kullanıcının o gönderi için açık onayı
  olmadan `tiktok_publish` çağırma. Bir parça için verilen onay diğerine geçmez.
- **Sıra:** önce `SELF_ONLY` ile bir gönderi → kullanıcı TikTok'ta başlığı,
  açıklamayı ve AIGC etiketini gözle doğrular → `--dogrulandi` ile BİR KEZ
  işaretlenir (kanal seviyesi) → sonra `PUBLIC_TO_EVERYONE`.
- **Kota:** dakikada 5, 24 saatte 13 gönderi (yuvarlanan; TikTok'un tavanı 6/dk,
  15/gün). Ret kodu `cadence_burst`/`cadence_daily` gelirse `retry_after_seconds`
  kadar bekle, tekrar deneme. Başarısız denemeler ve taslaklar kotadan düşmez.
- **Commercial Music Library'ye bakma.** TR çartı stok müzik; videoda zaten
  kendi Suno şarkısı çalıyor, üstüne CML parçası eklemek onu bastırır.
- **`ilk_yorum` caption'a girmez.** YouTube linki açıklamaya konursa For You
  dağıtımı riski var — yayından sonra ayrı yorum olarak eklenir (elle).

## Doğrulanmayı bekleyen

`is_aigc: true` gönderiliyor ama TikTok'ta "AI-generated content" etiketinin
gerçekten açık geldiği **henüz teyit edilmedi**.

**Yürürlükteki uyum kuralı: TikTok'ta AI etiketi UYGULAMADAN ELLE açılmalı.**
Yani gönderiyi yayınlarken (taslaksa yayınlarken, DIRECT_POST ise sonrasında
kontrol ederek) TikTok uygulamasındaki "AI-generated content" anahtarı elle
açılır. API'nin `is_aigc` bayrağına TEK BAŞINA güvenilmiyor: etiketin gerçekten
açık geldiğini API'den okumanın bir yolu yok, ve bu etiket kanalın en büyük
riski olan "inauthentic / toplu üretilmiş AI içerik" politikasına karşı verilen
bildirimin ta kendisi.

(Bu kural eskiden `fms-yayin-uyum` skill'ine havale ediliyordu. O skill depoda
DEĞİL, makineye özel bir yerde — `%LOCALAPPDATA%\hermes\skills\` — duruyor;
depoyu klonlayan biri için havale boşa düşüyordu. Kural tek satır olduğu için
havalenin kazancı yoktu, maliyeti ise atfın boşa düşmesiydi: bu yüzden buraya
satır içi yazıldı.)

İlk gerçek gönderide kontrol et: etiket API'nin bayrağıyla KENDİLİĞİNDEN açık
geliyorsa yukarıdaki elle-açma kuralı güncellenmeli ve bu bölüm kapatılabilir.
