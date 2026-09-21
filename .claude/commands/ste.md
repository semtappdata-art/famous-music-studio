# /ste — Basit İletişim Standardı

Bu komut, yanıtı STE biçimine çevirir veya mevcut iş için kısa STE durumu üretir.

## Kullanım

- `/ste plan <konu>`: İşe başlamadan kısa plan ver.
- `/ste durum`: Mevcut çalışma durumunu özetle.
- `/ste karar <konu>`: Kullanıcıdan karar gereken noktayı açıkla.
- `/ste risk <konu>`: Üretim/veri riski varsa net uyar.
- `/ste test`: Test durumunu yaz.
- `/ste teslim`: Biten işi kısa teslim formatında özetle.

## Cevap biçimi

Her yanıtta şu üç başlığı kullan:

1. **Özet** — 1-3 madde.
2. **Durum** — dosya/komut/test/karar bilgisi.
3. **Eylem** — net sonraki adım veya teslim sonucu.

## Etiketler

- `STE:PLAN`
- `STE:DURUM`
- `STE:KARAR`
- `STE:RİSK`
- `STE:TEST`
- `STE:TESLİM`

## İlke

Kısa, doğrudan ve üretim risklerini görünür yapan Türkçe iletişim kullan. `CLAUDE.md` ile çelişme olursa `CLAUDE.md` kazanır.
