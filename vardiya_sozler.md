# Vardiya — Orijinal Sözler (Rock)

Suno'nun Lyrics kutusuna aynen yapıştırılabilir.

> Yeni bir şarkı prompt'u yazmadan önce `ses_ve_tarz_takibi.md`'ye bak —
> vokal cinsiyeti/dokusu art arda tekrarlanmasın.

**Neden bu tema:** Katalogda `rock` en az kullanılan slot (tek örnek: Kırık Zincir)
ve o tek örnek ERKEK vokal — yani **kadın rock** hiç denenmemiş. Son üç üretimin
üçü de erkekti (Sokaklar Beni Tanır, Kader Ortakları, Bu Gece Kazandık), bu yüzden
sıradaki şarkı kadın ve düet DEĞİL (bkz. `ses_ve_tarz_takibi.md`, "SON DURUM").
Doku olarak **smoky husky low-register** seçildi: mevcut kadın dokularının dördü de
(soft breathy / bright breathy / powerful belting / polished) kullanılmış durumda.
Tempo da bilinçli: son dört ölçülebilir üretim 90/92/118/122 BPM ile kümelenmişti,
76-80 BPM aralığı Sessiz Mektup'tan (76) beri hiç kullanılmadı — bu şarkı 78 BPM.

**Konu — emek ve ev aidiyeti:** Kataloğun 19 sözler dosyasında "vardiya / fabrika /
kira / nöbet / fatura" imgeleri HİÇ geçmiyor; katalog büyük ölçüde gece-şehir-ayrılık
ekseninde. Bu şarkı o boş damarı dolduruyor: gece vardiyasından dönen bir kadın,
öfkeyle değil İNATLA anlatıyor ("slow-burning and defiant"). Ev, acınacak bir yük
değil sahip çıkılan bir mülk — nakaratın "benim" tekrarı bu yüzden var.

## Stil Etiketi (Suno Style kutusuna yapıştır)

```
Turkish rock ballad, slow-burning and defiant, smoky husky low-register Turkish female vocals, clean electric guitar arpeggio building into a wall of distorted guitars, baglama saz accent over live drums, dark dramatic storm-lit atmosphere, 78 BPM, strong final hit ending, no abrupt cutoff
```

## Sözler (Suno Lyrics kutusuna yapıştır)

```
[Intro]
Servisin camında buz tutmuş nefesim
Şoför radyoyu kısıyor, kimse konuşmuyor

[Verse 1]
Kartı okuttum, kapı bir kez bip dedi
Demir kapı ardımdan ağır ağır kapandı
Avucumda makine yağı, tırnağımda is
Sayaç döner durur, ben de onunla dönerim

[Pre-Chorus]
Termosun dibinde kalan son yudum
İkiye bölünür, söz bile gerekmez
Yoruldum demedim, demeyeceğim de
Bu kapı açılmadan bitmiyor hesabım

[Chorus]
Vardiya benim, bu gece de benim
Ellerimin izi soğuk demirde kalır
Kira da benim, bu çatı da benim
Eğilmedim ben, sadece omuz verdim

[Verse 2]
Sabah altıda anahtar döner sessizce
Çocuk uyumuş, yanağında dünkü gülüş
Battaniyeyi çekerim, saçını koklarım
Dışarıdaki bütün gürültü burada susar

[Chorus]
Vardiya benim, bu gece de benim
Ellerimin izi soğuk demirde kalır
Kira da benim, bu çatı da benim
Eğilmedim ben, sadece omuz verdim

[Bridge]
Fabrikanın düdüğü şehre yayılır
Kimse saymaz, ben her sesini sayarım
Ne kahramanım ne kurban, sadece buradayım
Bu evi ben tutuyorum, kimse görmese de

[Outro]
Vardiya benim, bu çatı da benim
Eğilmedim ben, bu işi ayakta bitirdim
```

## Temiz Sözler (YouTube açıklaması için kopyala-yapıştır)

```
Servisin camında buz tutmuş nefesim
Şoför radyoyu kısıyor, kimse konuşmuyor

Kartı okuttum, kapı bir kez bip dedi
Demir kapı ardımdan ağır ağır kapandı
Avucumda makine yağı, tırnağımda is
Sayaç döner durur, ben de onunla dönerim

Termosun dibinde kalan son yudum
İkiye bölünür, söz bile gerekmez
Yoruldum demedim, demeyeceğim de
Bu kapı açılmadan bitmiyor hesabım

Vardiya benim, bu gece de benim
Ellerimin izi soğuk demirde kalır
Kira da benim, bu çatı da benim
Eğilmedim ben, sadece omuz verdim

Sabah altıda anahtar döner sessizce
Çocuk uyumuş, yanağında dünkü gülüş
Battaniyeyi çekerim, saçını koklarım
Dışarıdaki bütün gürültü burada susar

Vardiya benim, bu gece de benim
Ellerimin izi soğuk demirde kalır
Kira da benim, bu çatı da benim
Eğilmedim ben, sadece omuz verdim

Fabrikanın düdüğü şehre yayılır
Kimse saymaz, ben her sesini sayarım
Ne kahramanım ne kurban, sadece buradayım
Bu evi ben tutuyorum, kimse görmese de

Vardiya benim, bu çatı da benim
Eğilmedim ben, bu işi ayakta bitirdim
```

## Notlar

- Vokal dili: Türkçe ("smoky husky low-register Turkish female vocals" + Türkçe
  sözler). Tekli anlatıcı — düet DEĞİL.
- Vokal cinsiyeti/dokusu: üç erkek üretimin ardından kadına dönüldü; doku
  "smoky husky low-register", katalogda daha önce kullanılmamış.
- Tema: emek, vardiya, ev aidiyeti, inat — kataloğun gece/ayrılık eksenine
  girmeyen ilk şarkı. Anlatıcı kadın, ton öfke değil sessiz direnç.
- `config.py`'deki `theme` alanı için: `"rock"` (accent kırmızı). `meta.json`:
  `{"title": "Vardiya", "theme": "rock"}`.
- Intro kuralına uygun: ilk satır temayı doğrudan adlandırmıyor ("Servisin
  camında buz tutmuş nefesim" — somut duyu imgesi; servis minibüsü, buzlu cam,
  susan radyo vardiyayı DOLAYLI hissettiriyor, kelime ilk kez Chorus'ta geçiyor).
  "Vardiyam bitti, yoruldum" gibi tez cümlesi bilerek kullanılmadı.
- Kapanış: stil etiketinde `strong final hit ending, no abrupt cutoff` var
  (enerjik/sert tema), Outro İKİ TAM cümle — `...` yok, düşünce yarım
  bırakılmadı (bkz. `suno_prompt_hazirlik.md`, "Kapanış (Outro) kuralı").
- "Temiz Sözler" bölümü etiketli bölümden PROGRAMATİK olarak türetildi (aynı
  satır listesi, sadece köşeli parantez etiketleri çıkarılmış) — `caption_align`
  0,25 eşleşme eşiğiyle bu dosyayı okuyor, iki bölüm arasında sapma olmamalı.
