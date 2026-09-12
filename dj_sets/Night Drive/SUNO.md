# Night Drive — Suno üretim tarifi

`set_style: techno_chill` (bkz. `config.SET_STILLERI`). Bu set, "Just Relax"in
(deep house) **aynı kitlesine ikinci kez düşmemek** için var: melodic techno
tarafı YouTube'da "focus music", "work music", "night drive" aramalarını
yakalıyor; deep house daha çok "lounge / relax" tarafında kalıyor.

## Suno stil satırı (Style of Music alanına aynen)

```
melodic techno, hypnotic arpeggio, deep sub bass, airy pads, no vocals, 124 bpm, late night drive
```

**Vokal YOK** — bilinçli. Enstrümantal set "arka planda çalınan müzik"
aramalarına giriyor (çalışma/sürüş/uyku), vokalli set girmiyor. "Just Relax"te
vokal chop'lar var, ayrım da buradan geliyor.

## Süre ve parça sayısı

Hedef **~45-60 dakika**. Suno tek üretimde ~4 dakika veriyor, Extend zinciriyle
uzatılıyor → **12-16 parça**.

> **Kota uyarısı:** Suno indirme kotası ayda 20-60. 16 parçalık bir set, ayın
> indirme bütçesinin büyük kısmını yiyor. Bu ay ana katalog (`projects/`) için
> ne kadar indirme planlandıysa ona göre karar ver — set ile katalog aynı
> kotadan besleniyor.

## Akış (Extend zincirinde tempo/enerji planı)

| Parça | Rol | Not |
|---|---|---|
| 1-3 | Giriş | Sadece arpeggio + pad, davul yavaş giriyor |
| 4-9 | Gövde | Sub bass tam oturuyor, en yoğun bölüm burada |
| 10-13 | Düşüş | Davul incelir, pad öne çıkar |
| 14-16 | Kapanış | Arpeggio tek başına, sönümlenerek biter |

Kapanışın sönümlenerek bitmesi önemli: `merge_dj_set_segments.py` parçaları
crossfade ile birleştiriyor, sert biten bir son parça birleşimde tıkırdıyor.

## Dosya adlandırma — ZORUNLU

İndirilen parçalar `_segments/` altına, **adının sonunda sıra numarasıyla**:

```
_segments/Night Drive 1.wav
_segments/Night Drive 2.wav
...
```

`merge_dj_set_segments.py` sırayı sadece bu numaradan okuyor; numarası olmayan
dosyayı atlıyor, aynı numaradan iki tane varsa hata veriyor.

## Sonrası (sırayla)

```bash
python merge_dj_set_segments.py "dj_sets/Night Drive"   # _segments/ -> audio.wav
python stock_video.py --set "dj_sets/Night Drive" --build   # -> backdrop.mp4
python dj_famous_process.py                                  # render + yayın
```

`--build` adımı zorunlu değil: `dj_famous_process.py` backdrop.mp4 yoksa kendisi
üretmeye çalışıyor. Elle çalıştırmanın faydası, arka planı **yayından önce**
görüp beğenmezsen `--force` ile yenileyebilmen.

`art.jpg` gerekiyor — `art_query` alanı meta.json'da hazır (gece otoyol /
gösterge paneli), `generate_cover.py` kapağı ondan üretir.
