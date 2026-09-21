# Sunrise Session — Suno üretim tarifi

`set_style: organic_morning` (bkz. `config.SET_STILLERI`). Bu set, mevcut üç
setin (gece/lounge) aksine **kanaldaki İLK aydınlık/gündüz seti**: "sunrise
mix", "morning music", "organic house" aramalarını yakalıyor. Deep house'un
(lounge/relax) ve techno_chill'in (focus/night drive) ayrı bir kitlesi.
118 bpm + dünya perküsyonu + marimba ile iki komşusundan kesin çizgiyle ayrılıyor.

## Suno stil satırı (Style of Music alanına aynen)

```
organic house, warm analog synth, gentle marimba melody, soft latin percussion, no vocals, 118 bpm, sunrise terrace, uplifting calm
```

**Vokal YOK** — bilinçli. Enstrümantal set "arka planda çalınan müzik"
aramalarına giriyor (çalışma/sabah ritüeli), vokalli set girmiyor.
`theme: "dj"` olduğu için paylaşım metinleri İngilizce (`language: en`).

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
| 1-3 | Giriş | Marimba + pad, davul yavaş giriyor, tan yerinden ilk ışık hissi |
| 4-9 | Gövde | Latin perküsyon tam oturuyor, en yoğun bölüm burada |
| 10-13 | Düşüş | Davul incelir, analog synth öne çıkar |
| 14-16 | Kapanış | Marimba tek başına, sönümlenerek biter |

Kapanışın sönümlenerek bitmesi önemli: `merge_dj_set_segments.py` parçaları
geçişleri KESİNTİSİZ biliyor (kenar sessizlik kırpma + equal-power `qsin`
eğri, ortada dip yok). İlk parça müzikle açılır, son parçanın kuyruğu
korunur (sönümlenerek bitiş). Detay: `merge_dj_set_segments.py` docstring'i.

## Dosya adlandırma — ZORUNLU

İndirilen parçalar `_segments/` altına, **adının sonunda sıra numarasıyla**:

```
_segments/Sunrise Session 1.wav
_segments/Sunrise Session 2.wav
...
```

`merge_dj_set_segments.py` sırayı sadece bu numaradan okuyor; numarası olmayan
dosyayı atlıyor, aynı numaradan iki tane varsa hata veriyor.

## Kapak/video görseli — Arda referansı BEKLENİYOR

Bu setin kapak ve video görselleri, onaylanan plan gereği **Arda'nın fotoğraf
referanslarıyla üretilecek sahnelerden** gelecek (`dj_sets/_arda/`). O üretim
adımı gelene kadar Suno tarafı tamamlanacak; sahne üretimi yapılınca bu
klasörün `art.jpg`/`cover*.png`'si ondan üretilecek. Geçici olarak Pexels
`art_query` çalışır (güneş doğuşu/ocean/palm), otomasyon durmaz.

## Sonrası (sırayla)

```bash
python merge_dj_set_segments.py "dj_sets/Sunrise Session"   # _segments/ -> audio.wav
python stock_video.py --set "dj_sets/Sunrise Session" --build   # -> backdrop.mp4
python dj_famous_process.py                                  # render + yayın
```