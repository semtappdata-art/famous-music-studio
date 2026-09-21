# Midnight Arpeggio A/B seçimi — 4 varyant incelemesi (Night Drive segment #1)

**Durum:** Ölçüldü (2026-09-14, AudioWorklet, 4 kart da `suno.com/create` üzerinden,
indirme kotası harcanmadan). Ham sonuç: `suno_olcum_sonuc.json`.
Önceki oturum referanslarıyla tutarlı (v1: 208.9 / MY 2.12→2.17 / crest 9.62; v2: 233.6 /
MY 2.79→2.62 / crest 12.42→12.56) — ölçüm tekrarlanabilir.

## Adaylar

Tümü V6, `Midnight Arpeggio` segment #1 açılışının alternatifleri, 2 prompt varyantı × 2 üretim:

- **Varyant A** ("hypnotic 16th-note arpeggio, tight four-on-the-floor kick"):
  v1 (3:29) ve v2 (3:54)
- **Varyant B** ("hypnotic repeating arpeggio, restrained four-on-the-floor kick"):
  v3 (3:00) ve v4 (3:00)

## Ölçümler

| Ölçüt | v1 (3:29) | v2 (3:54) | v3 (3:00) | v4 (3:00) |
|---|---|---|---|---|
| Süre | 208.9 sn | 233.6 sn | 179.8 sn | 179.6 sn |
| İlk ses | **0.02 sn** | 0.05 sn | 0.03 sn | 0.10 sn |
| MY ortanca (vokal önde) | 2.17 | **2.62** | 2.14 | 2.41 |
| MY max | 2.89 | 3.48 | 3.79 | 3.30 |
| Nakarat (enerji vekili) | **15 sn** | 30.5 sn | 30.5 sn | 30.5 sn |
| Crest (dinamik) | 9.62 dB | 12.56 dB | 11.84 dB | **12.98 dB** |
| Son tepe oranı (ani kesme) | 0.006 ✓ | 0.051 ✓ | 0.001 ✓ | 0.001 ✓ |
| Sustain (final hit) | **1.25 sn** | 0 | 0 | 0 |
| Son sessizlik (boş kuyruk) | 0.33 sn | **0.03 sn** | 1.05 sn | 0.88 sn |
| Tepe | −3.1 dBFS | −1.7 dBFS | −3.4 dBFS | −1.8 dBFS |
| Kırpılma | 0 olay | 0 | 0 | 0 |
| Erken sönme | hayır (1.41) | hayır (1.10) | hayır (1.40) | hayır (0.89) |
| Süre aşımı (240 sn) | hayır | hayır | hayır | hayır |

## İkili karşılaştırma (`varyant_farki`)

- **v1–v2: belirgin** (skor 0.69) — tek sürükleyici fark nakarat: v1 15 sn'de, v2 30.5 sn'de.
- **v1–v3: belirgin** (0.54) — yine nakarat (15 vs 30.5).
- **v1–v4: belirgin** (0.68) — nakarat + MY.
- **v2–v3: esit_dinleyerek_sec** (0.51) · **v2–v4: esit_dinleyerek_sec** (0.37) ·
  **v3–v4: esit_dinleyerek_sec** (0.21).

## Değerlendirme

Yapısal açıdan 4'ü de geçer: temiz kapanış (ani kesme yok), kırpılma yok, erken sönme
yok, 240 sn aşımı yok, hepsi anında başlıyor. Karar iki eksende:

- **Açılış segmenti olarak (setin 1/12–1/16 parçası):** enerjiye en erken çıkan v1
  (nakarat 15 sn), en sıkı/kompakt prodüksiyon (crest 9.62, kafa payı −3.1 dBFS), temiz
  "strong final hit" sustain ile bitiyor (1.25 sn, kuyruk yok), anında başlıyor. 16th-note
  tight kick daha "sürüş" hissi verir — gece sürüşü açılışı için avantaj.
- **Vokal/ürün büyüklüğü açısından:** v2 en önde vokal (MY 2.62, v1'e göre +%21 göreli —
  `suno_ab_secimi.md`'de Sabah Senin kararının birebir aynı eşiği), en geniş dinamik
  (12.56 dB), en uzun (3:54) — "büyük prodüksiyon" adayı.

## Öneri

**Açılış için v1 (3:29)** — erken enerji + sıkı kick + temiz bitiş; varyant A'yı temsil
eden, setin ilk parçası olarak en doğalı. **Yedek/öncelikli havuz: v2 (3:54)** (en vokal
önde, en dinamik) — farklı bir sette ya da ana katalog adayı olarak. v3/v4 havuzda düşük
öncelikli.

**UYARI:** metrikleri belirleyen tek "belirgin" eksen nakarat zamanlaması (15 vs 30.5 sn)
— ölçümün kendisi enerji vekiliyle çalışıyor, parçanın "güzel" olup olmadığını söylemiyor
(`suno_ab_secimi.md`: *kural uyumu kalite değildir*). v1 vs v2 arasındaki gerçek seçim
**kulakla** yapılmalı: ikisini de bir kez baştan 60 sn dinlemek bu dosyadan daha kesin.

## Kalan iş (üretim)

1. Kazananı indir (yalnızca 1 indirme, kota ~24'te) → `dj_sets/Night Drive/_segments/Night Drive 1.wav`
2. Extend zinciri: 3.0–3.5 dk'lık segmenti art arda Extend ederek 12–16 parça (45–60 dk) üret,
   her birini indir.
3. `merge_dj_set_segments.py` ile kesintisiz (equal-power) birleştir → `audio.wav`.
4. `dj_famous_process.py` render + Content ID karantinası + yayın.