# Platform davranışları — standart belgesi (2026-09-29)

Her platformın yükleme/zamanlama/gizlilik/AI-beyan/takip katmanı.
Varyantlar: `config.GOLDEN_HOURS` (TR 12-14 / 18-22), `auto_process` saatlik,
`dj_famous_process` haftalık.

## 1. YouTube (uzun + Shorts)
| Katman | Davranış | Kapanan |
|---|---|---|
| Yükleme | `youtube_upload.upload_video` — `videos.insert`, metadata + kapak + playlist | — |
| Zamanlama | `private` + `publishAt` golden-hour'da; `--no-schedule` devre dışı | ✅ |
| Gizlilik | `youtube_privacy` = istenen; `youtube_privacy_gercek` = API ölçümü (aynı değil) | ✅ |
| AI beyanı | `containsSyntheticMedia: True` ZORUNLU; açıklama satırı YOK (karar: beyan açıklama satırında yok) | ✅ |
| Altyazı | `caption_align` → ASR zamanlama + sözler dosyası eşleşmesi; sözler yoksa atla | ✅ |
| Kopya muafiyeti | md5 + `kopya_notu` + karşı taraf çekilmiş mi → fail-closed | ✅ |
| Studio planı | `youtube_studio.py` — private + Planla, tempo kaydırma | ✅ |
| Kota | `youtube_kota.py`, günlük tavan, kapak telafisi | ✅ |
| Analytics | `youtube_analytics.py` — token ayrı (`analytics_token.json`, `yt-analytics.readonly`) | 🔄 29 Eyl OAuth yenilendi |

## 2. TikTok
| Katman | Davranış | Kapanan |
|---|---|---|
| Yol | **Web planı ONLY** (`TIKTOK_AKIS=web_planla`); API taslak yolu DONDURULDU | ✅ 29 Eyl |
| Kapak | Telefon üzerinden yükle, `tiktok_cover_hint` state'te | ✅ |
| Açıklama/AI | Kit: beyan satırı + hashtag, AI-anahtarı KAPALI | ✅ |
| Zamanlama | Studio "Planla", `web_planlanan_an` | ✅ |
| Onay | `yayinlandi`/`iptal` komutu, state+defter | ✅ |
| Bayat | +48sa `(N gündür)` rozeti + kapanış komutları | ✅ 29 Eyl |
| Paket | 24sa kala kapak+açıklama+ayarlar (Telegram) | ✅ 29 Eyl |
| Test | `test_tiktok_web*` + `test_tiktok_akis_kilidi` | ✅ |
| Temizlik | Eski `tiktok_publish_id` alanları胶囊 akışı ile temizlenmeli | ⏳ |

## 3. Instagram
| Katman | Davranış | Kapanan |
|---|---|---|
| Yol | Konteyner (`creation_id`) + `media_publish` golden-hour'da | ✅ |
| Zamanlama | Golden-hour kuyruğu, `_konteyner_yayindan_yeni` | ✅ |
| Ölü konteyner | 23sa kapı + `_konteyner_bayat` temizlik | ✅ |
| AI beyanı | Caption satırı (Meta API alanı doğrulanmadı) | ✅ |
| 5xx kuralı | Yalnız gerçek 5xx + `is_transient: true` tekrar; taşımada BİLEREK deneme | 🔄 Madde 2 |

## 4. Facebook
| Katman | Davranış | Kapanan |
|---|---|---|
| Yol | Native `scheduled_publish_time` + long/short ayrım | ✅ |
| Gizlilik | state'den okunur | ✅ |
| Kapılar | telif_araliklari + youtube_privacy + public-anı + golden-hour + günlük tavan | ✅ `facebook_backfill.py` |
| Belgelendirme | Ayrı belge: `upload/facebook_backfill.md` | ⏳ Madde 1 |

## 5. Telegram / Bluesky
| Katman | Davranış | Kapanan |
|---|---|---|
| Yol | **yalnız `ek_platform_backfill.py`** — ana hattan bağlanmaz | ✅ |
| Kapılar | golden-hour + günlük tavan + politika + public-anı | ✅ |
| State senkronu | Her iki platforma ayrı "yayınlandı" işareti | 🔄 Madde 2 |

## 6. Cross-platform (hepsi)
| Kural | Detay |
|---|---|
| Fail-closed | `uyumluluk.kontrol()` her yüklemeden önce, HATA → atla, log |
| Atomik state | `state_io.durum_yaz` (tmp+flush+replace) |
| Defter | `elle_islem.py` — her elle iş bir satır, tekrar yazma |
| Nabız | `watch_projects.py` 4sa kontrol, ntfy bildirim |
| Sağlık | `saglik_kontrol` 10 adım, saatlik `finally` |
| AI beyanı | YouTube API + caption satırı; TikTok/IG Meta alanı yoksa caption |
| Hook/hashtag | `HOOK_LINES` kaldırıldı; AI-vurgulu ibareler KULLANILMIYOR |
