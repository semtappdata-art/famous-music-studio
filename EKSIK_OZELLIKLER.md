# Eksik Özellik Raporu

**Tarih:** 2026-10-21  
**Üreten:** `python eksik_ozellik_raporu.py`

Bu rapor, testlerin beklediği ama repoda **bulunmayan** API'leri listeler.
Bunlar geliştirme sırasında yazılıp bırakılmış testlerdir — kırmızı çizgi
değildir, ancak her biri ayrı bir özellik işidir.

| Eksik API | Etkilenen test dosyası |
|---|---|
| `ffmpeg_utils.bastaki_sessizlik` | 2 |
| `render.find_intro_cover` | 2 |
| `auto_process.RENDER_OUTPUTS` | 2 |
| `auto_process._is_rendered` | 2 |
| `auto_process._tiktok_kit_sirasi` | 2 |
| `saglik_kontrol.METRIKLER` | 1 |
| `auto_process._ek_platform_backfill` | 1 |
| `auto_process._facebook_backfill` | 1 |
| `youtube_upload.build_clip_snippet` | 1 |
| `youtube_upload._golden_publish_at` | 1 |
| `youtube_upload._dakika_damgasi` | 1 |
| `auto_process._gunluk_izlenme` | 1 |
| `render._FFPROBE_YOK_UYARILDI` | 1 |
| `render.video_butun_mu` | 1 |
| `render.PARCALI_SONEK` | 1 |
| `ffmpeg_utils.ses_olc` | 1 |
| `ffmpeg_utils.limiter_filtresi` | 1 |
| `render.limiter_gerekli` | 1 |
| `auto_process._tiktok_yayin_dogrulama` | 1 |
| `auto_process._turev_takvimi` | 1 |

## Modül bazlı dağılım

- **auto_process** (8): `auto_process.RENDER_OUTPUTS`, `auto_process._ek_platform_backfill`, `auto_process._facebook_backfill`, `auto_process._gunluk_izlenme`, `auto_process._is_rendered`, `auto_process._tiktok_kit_sirasi`, `auto_process._tiktok_yayin_dogrulama`, `auto_process._turev_takvimi`
- **render** (5): `render.PARCALI_SONEK`, `render._FFPROBE_YOK_UYARILDI`, `render.find_intro_cover`, `render.limiter_gerekli`, `render.video_butun_mu`
- **ffmpeg_utils** (3): `ffmpeg_utils.bastaki_sessizlik`, `ffmpeg_utils.limiter_filtresi`, `ffmpeg_utils.ses_olc`
- **youtube_upload** (3): `youtube_upload._dakika_damgasi`, `youtube_upload._golden_publish_at`, `youtube_upload.build_clip_snippet`
- **saglik_kontrol** (1): `saglik_kontrol.METRIKLER`
