# Eksik Özellik Raporu

**Tarih:** 2026-10-21  
**Üreten:** `python eksik_ozellik_raporu.py`

Bu rapor, testlerin beklediği ama repoda **bulunmayan** API'leri listeler.
Bunlar geliştirme sırasında yazılıp bırakılmış testlerdir — kırmızı çizgi
değildir, ancak her biri ayrı bir özellik işidir.

| Eksik API | Etkilenen test dosyası |
|---|---|
| `auto_process._tiktok_kit_sirasi` | 2 |
| `saglik_kontrol.METRIKLER` | 1 |
| `auto_process._ek_platform_backfill` | 1 |
| `auto_process._facebook_backfill` | 1 |
| `auto_process._gunluk_izlenme` | 1 |
| `auto_process._tiktok_yayin_dogrulama` | 1 |
| `auto_process._turev_takvimi` | 1 |

## Modül bazlı dağılım

- **auto_process** (6): `auto_process._ek_platform_backfill`, `auto_process._facebook_backfill`, `auto_process._gunluk_izlenme`, `auto_process._tiktok_kit_sirasi`, `auto_process._tiktok_yayin_dogrulama`, `auto_process._turev_takvimi`
- **saglik_kontrol** (1): `saglik_kontrol.METRIKLER`
