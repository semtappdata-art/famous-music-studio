# Peak District — Suno üretim tarifi

`set_style: progressive_node` (bkz. `config.SET_STILLERI`). Bu set, kanaldaki
**en yüksek enerjili** set: "peak time", "workout mix", "driving house"
aramalarını yakalıyor. Night Drive'ın "hipnotik ama sakin" tekno tarafından
BPM (126 vs 124) ve sürükleyici kick ile ayrılıyor — varış noktası, sürüş değil.
`theme: "dj"` olduğu için paylaşım metinleri İngilizce (`language: en`).

## Suno stil satırı (Style of Music alanına aynen)

```
melodic progressive house, driving kick, hypnotic lead synth, layered atmosphere, no vocals, 126 bpm, peak time club, forward motion
```

**Vokal YOK** — bilinçli (tekno hattıyla aynı gerekçe). Prodüksiyon ağırlığı
kasıtlı olarak diğer setlerden yüksek: katalogda açık eksik olan enerji
çeşitliliği bu setle kapanıyor.

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
| 1-3 | Giriş | Karanlık atmosfer, kick uzaktan giriyor |
| 4-8 | Yükseliş | Çift davul katmanı, lead synth hipnoz kuruyor |
| 9-11 | TEPE | En yoğun bölüm — peak time kısmı burada |
| 12-16 | İniş | Katmanlar tek tek iner, kapanışta sönümlenir |

Kapanışın sönümlenerek bitmesi önemli: `merge_dj_set_segments.py` parçaları
crossfade ile birleştiriyor, sert biten bir son parça birleşimde tıkırdıyor.

## Dosya adlandırma — ZORUNLU

İndirilen parçalar `_segments/` altına, **adının sonunda sıra numarasıyla**:

```
_segments/Peak District 1.wav
_segments/Peak District 2.wav
...
```

`merge_dj_set_segments.py` sırayı sadece bu numaradan okuyor; numarası olmayan
dosyayı atlıyor, aynı numaradan iki tane varsa hata veriyor.

## Kapak/video görseli — Arda referansı BEKLENİYOR

Bu setin kapak ve video görselleri, onaylanan plan gereği **Arda'nın fotoğraf
referanslarıyla üretilecek sahnelerden** gelecek (`dj_sets/_arda/`). O üretim
adımı gelene kadar Suno tarafı tamamlanacak; sahne üretimi yapılınca bu
klasörün `art.jpg`/`cover*.png`'si ondan üretilecek. Geçici olarak Pexels
`art_query` çalışır (gece kulübü/lazer/crowd), otomasyon durmaz.

## Sonrası (sırayla)

```bash
python merge_dj_set_segments.py "dj_sets/Peak District"   # _segments/ -> audio.wav
python stock_video.py --set "dj_sets/Peak District" --build   # -> backdrop.mp4
python dj_famous_process.py                                 # render + yayın
```