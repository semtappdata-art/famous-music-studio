# Deep Focus — Suno üretim tarifi

`set_style: deep_house` (bkz. `config.SET_STILLERI`). 
Bu set, "Anjunadeep" ve "Bonobo" tarzlarını birleştirerek derin odaklanma ve çalışma ortamı için оптимизирован profundo house müziği sunar; 
tekno setlerinden farklı olarak vokalli elementler ve melodik progression üzerine odaklanıyor.

## Suno stil satırı (Style of Music alanına aynen)

```
deep house, melodic, warm analog bass, soft female vocal chops, 120 bpm, late night lounge
```

**Vokal VAR** — hafif vokal chop'lar içeren bu set "arka planda çalınan müzik" aramalarına giriyor (çalışma/okuma/meditasyon), aynı zamanda vocal içerdiği için daha эмоциональный bir deneyim sunuyor.

## Süre ve parça sayısı

Hedef **~50-70 dakika**. Suno tek üretimde ~4 dakika veriyor, Extend zinciriyle uzatılıyor → **13-18 parça**.

> **Kota uyarısı:** Suno indirme kotası ayda 20-60. 18 parçalık bir set, ayın indirme bütçesinin büyük kısmını yiyor. Bu ay ana katalog (`projects/`) için ne kadar indirme planlandıysa ona göre karar ver — set ile katalog aynı kotadan besleniyor.

## Akış (Extend zincirinde tempo/enerji planı)

| Parça | Rol | Not | Referans İlhami |
|---|---|---|---|
| 1-4 | Giriş | Sadece атмосферный pads + minimal arpeggio, davul yok | Anjunadeep-style giriş |
| 5-10 | Gövde | Sub bass tam oturuyor, vokal chop'lar ekleniyor, ritмik elemanlar芽生える | Bonobo + Melodic House fusión |
| 11-15 | Düşüş | Davul incelir, pad öne çıkar, vokalar daha belirgin | Anjunadeep breakdown |
| 16-18 | Kapanış | Arpeggio ve vokal tek başına, sönümlenerek biter | Únütülmez outro |

## Dosya adlandırma — ZORUNLU

İndirilen parçalar `_segments/` altına, **adının sonunda sıra numarasıyla**:

```
_segments/Deep Focus 1.wav
_segments/Deep Focus 2.wav
...
```

## Sonrası (sırayla)

```bash
python merge_dj_set_segments.py "dj_sets/Deep Focus"
python stock_video.py --set "dj_sets/Deep Focus" --build
python dj_famous_process.py
```

## Notlar

- `art.jpg` gerekiyor — `art_query` alanı meta.json'da "warm golden hour forest sunlight" ile hazır
- Bu set, tekno yoğunluğundan ziyade melodik ve atmosferik üzerine odaklanarak farklı bir kitleni hedefliyor
