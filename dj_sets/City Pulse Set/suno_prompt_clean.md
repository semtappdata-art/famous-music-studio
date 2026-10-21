# Suno Prompt — City Pulse Temiz Sürüm (telifli 3 segmentin yerine)

ÖNCE: Studio → Telif → "Tümünü göster"den eşleşen 3 eserin SÜRE ARALIKLARINI al.
Aşağıdaki prompt'lar o aralıkların yerine üretilecek enstrümantal dolgular içindir.
KURAL: vokal YOK (melodi çakışma riskini düşürür), sanatçı adı YOK, hazır şarkı sözü YOK.

## Ana stil promptu (tüm segmentlere baz)
```
progressive house meets melodic techno DJ set filler, instrumental only,
driving four-on-the-floor kick, rolling bassline, atmospheric pads,
subtle arp motif (original, 2-bar loop), no vocals, no lyrics,
no breakdown vocal chops, clean mix, club ready, seamless loop feel,
124 BPM, minor key, dark but euphoric
```

## Segment varyantları (BPM + enerji uyarlı)
- Build Up (124 BPM, 0.5): ana prompt + `rising tension, snare rolls, filter sweeps opening, no drop vocal`
- Peak (126-128 BPM, 0.8-0.9): ana prompt + `peak-time energy, punchier kick, acid arp layer, hands-in-the-air groove, no melody quote`
- Deep/Breakdown (118-120 BPM, 0.2-0.4): ana prompt + `half-time feel, deep dub chords, spacious reverb, breathing room, no kick for first 8 bars`
- Outro (116 BPM, 0.3): ana prompt + `cool-down, fading energy, warm pads, gentle outro, vinyl-style fade`

## Exclude (her üretimde)
```
vocals, lyrics, singing, vocal chops, famous melodies, artist names,
pop song structure, abrupt ending, crowd noise, low quality, distortion
```

## Üretim ayarları
- Model: Suno v6 (mevcut katalog standardı) | Süre: maksimum (Extend ile hedef aralık boyuna)
- Her segment için 2 varyant üret → merkez/yan enerji + kapanış testiyle seç
  (ölçüt: vokal önde değil ENSTRÜMAN dengesi + son akor tam seviyede tutup sönsün)
- Seçilen varyantın Suno clip ID'si + prompt'u bu dosyanın altına işlenir (izlenebilirlik)

## Yerleştirme
- Temiz segmentler DJ mix geçişiyle (8-16 bar crossfade) eski aralığın yerine konur
- Yeni audio.wav → MD5 değişir → uyumluluk MD5 kapısı sıfırdan bakar (eski telif kaydı
  bu sese ait kalır, yeni ses TEMİZ sayılır — kapı dosyaya değil sese bakar)
- Sonra: validate → render → yeni video olarak yükle (eski ID'ye dokunulmaz)
