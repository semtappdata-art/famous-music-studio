# Suno kalite ve dinlenme önerileri

> Yazıldığı an: **2026-09-13**. Bu belge yalnızca öneri içerir. Kod, state, Suno ya da tarayıcı
> tarafında hiçbir şey değiştirilmedi.
>
> Etiketler:
> - **[RESMÎ]** Suno, Spotify veya YouTube belgesi
> - **[YAYGIN]** üçüncü taraf rehberi, yaygın uygulama ya da deneyim
> - **[ÖLÇÜLDÜ]** bu makinede, bu depodaki dosyalardan ölçüldü

---

## 0. Ölçülen durum

### Ses dosyaları [ÖLÇÜLDÜ]
`projects/*/audio.*` altındaki 19 dosya, `ffmpeg ebur128` ve `silencedetect` ile ölçüldü.

| Ölçüt | Aralık | Yorum |
|---|---|---|
| Entegre loudness | **−12,9 … −14,8 LUFS** | Suno zaten −14 çevresinde teslim ediyor |
| True peak | **−4,4 … −0,5 dBTP** | İki ses sınırda: Küllerimden Geç/Yeniden Doğacağım **−0,5**, Sokaklar Beni Tanır **−0,7** |
| LRA | 2,4 … 8,8 LU | En dinamik dosya Sabah Senin'in eski take'i (8,8 LU) |
| Baştaki sessizlik (−50 dB) | 0,06 … 0,81 sn | `bastaki_sessizlik()` bunu zaten kırpıyor |
| Son 4 sn ortalaması | 15 dosya −14 … −17 dB. Ayrıca Sabaha Kadar −21, Sokaklar −25, Son Kez −27, Yeraltı −39 | Çoğu şarkı **tam seviyede bitiyor**. Kodda son kırpma ya da fade yok |

### Ses zinciri (kod) [ÖLÇÜLDÜ]
- `ffmpeg_utils.py` sese **hiçbir filtre uygulamıyor**: `-map 0:a -c:a aac -b:a 192k`.
- Zincirde `loudnorm`, `alimiter`, EQ ya da `afade` yok.
- Tek ses işlemi `-ss` ile yapılan kırpma. Uzun formatta baştaki sessizlik kırpılıyor
  (`INTRO_SESSIZLIK_*`), Shorts'ta `find_highlight` kesit seçiyor.
- `audio_highlight.find_highlight`, RMS'i en yüksek 45 saniyelik pencereyi seçiyor. Bu genelde son
  nakarata ya da tırmanışa denk geliyor; yani nakaratın **sözüne** değil **enerjisine** göre seçim yapılıyor.

### İzlenme verisi [ÖLÇÜLDÜ]: veri yetersiz
Kaynaklar: `projects/*/state.json` (`youtube_views`) ve `olcum_temel_cizgi.json` (28 günlük pencere,
8 video için tutma eğrisi).

**Neden yetersiz:**
- Katalog **2 haftalık** ve yalnız 19 şarkı var.
- Videoların çoğu 5 Eylül'de **toplu** yüklendi.
- Aynı sesi taşıyan iki video arasındaki gürültü tabanı **21,2 puan**.
- Bu yüzden aşağıdakiler yalnız **yön** gösteriyor, karar dayanağı değil.

**Uzun format izlenmeleri:**

| Şarkı | Tür | Süre | İzlenme |
|---|---|---|---|
| Son Kez | akustik | 3:38 | 317 |
| Yeraltı | hiphop | 2:35 | 240 |
| Yürek Yarası | arabesk | 3:16 | 231 |
| Sessiz Mektup | akustik | — | 183 |
| Küllerimden Geç | arabesk | — | 182 |
| … | | | |
| Kırık Zincir | rock | — | 24 |
| Bu Gece Kazandık | pop | — | 4 |

**Shorts izlenmeleri:** Sokaklar Beni Tanır (hiphop) 250 · Kader Ortakları (hiphop) 172 ·
Gece Sürüşü (pop) 156 · Küllerimden Geç 115 · Yürek Yarası 112. En altta elektronik var:
Sabaha Kadar 4, Kumdan Denize 5.

**Tutma (8 video):**
- Ekranda kalma oranı %2 noktasında 0,75 (Beni Bırakma) ile 0,96 (Küllerimden Geç) arasında.
- İlk %10'luk dilimde izleyicinin **%32-62'si** ayrılıyor. En büyük kayıp ilk 5-20 saniyede.
- En iyi orta bölüm tutması **en kısa şarkıda**: Sokaklar Beni Tanır (2:25), %50 noktasında 0,44,
  ortalama izleme yüzdesi 45,6.
- Kanal ortalaması (28 gün): uzun formatta izleme yüzdesi **%22,6**, Shorts'ta **%73,6**.
- İzlenme süresinin **%63'ü TV'den** geliyor (733 izlenme, 2.257 dk), yani arka planda dinleniyor.
  Uzun formatta "başta tutmak" kadar "sonuna kadar dinlenebilir mix" de önemli.

**Okunabilen zayıf yönler:**
1. Uzun formatta akustik ve arabesk (duygusal, vokal önde) önde.
2. Shorts'ta hiphop önde.
3. Rock ve elektronik iki hatta da geride. Rock'ta tek şarkı var (n=1), bu bir **tür hükmü değil**.
4. Süre ile izlenme arasında ilişki görünmüyor. En kısa şarkı en iyi tutmayı verdi ama n=1.
5. 21 söz dosyasının 7'sinde BPM yazmıyor; tempo ilişkisi **ölçülemez**.

---

## 1. Öncelikli öneri listesi

Ölçek: Y = yüksek, O = orta, D = düşük.

| # | Öneri | Etki | Zahmet | Risk | Nerede |
|---|---|---|---|---|---|
| 1 | **Nakarata en geç ~30-45 sn'de ulaş.** 78 BPM gibi yavaş tempoda Verse + Pre-Chorus 45 sn'yi aşıyor. Nakaratla açılan iskeleti ya da kısa bir Verse 1 kullan. Tutma kaybı ilk 5-20 sn'de [ÖLÇÜLDÜ] | Y | D | D | Suno (söz yapısı), belge |
| 2 | **Söz sonunu `[Outro]` ile kur, en son satıra tek başına `[End]` koy.** Outro 15-25 sn olsun [YAYGIN]. Mevcut "iki tam cümle" kuralını tamamlıyor | O | D | D | Belge: `suno_prompt_hazirlik.md`, Kapanış kuralı |
| 3 | **Süre hedefi 2:45-3:45.** Stil tarifine `concise radio-length arrangement, no long instrumental breaks` ekle. 4:00'ı aşan take A/B'de puan kaybetsin. v6 daha uzun şarkı üretiyor [YAYGIN] | O | D | D | Suno stil tarifi, A/B |
| 4 | **Model olarak v6 seç, v6-wild değil.** v6-wild "daha az öngörülebilir" [RESMÎ v6 FAQ]; kanal kimliği tutarlılık istiyor | O | D | D | Suno |
| 5 | **İki take'e tek take gibi bakma.** Aynı prompt'un iki take'i arasındaki fark, prompt değişikliğinin etkisini geçebiliyor [YAYGIN]. Varyant farkı ölçüte girsin (§4) | O | D | D | A/B betiği, belge |
| 6 | **Exclude alanını 2-3 öğeyle kullan** (Advanced Options → Exclude) [RESMÎ]. Kadın vokalli rock için örnek: `male vocals, autotune, electronic drums` | O | D | D | Suno |
| 7 | **Stil tarifine bir mix/master cümlesi ekle** (şablon §2). Loudness zaten −14 civarında; asıl kazanç vokal netliği ve daha yumuşak üst frekanslar | O | D | D | Suno stil tarifi |
| 8 | **Render öncesi yalnız true peak güvenliği.** TP −1 dBTP'nin üstündeyse −1 dBTP tavan koy. Genel loudnorm **gerekmiyor** (§5) | D-O | O | D | Kod: `ffmpeg_utils.py` ses çıkışı (uygulanmadı) |
| 9 | **Shorts kesiti nakaratın başından başlasın.** RMS penceresi bazen nakaratın ortasından kesiyor. En ucuz yol `meta.json`'a elle `highlight_start` yazmak (kod bunu destekliyor). Kod iyileştirmesi: başlangıcı en yakın ses atağına hizalamak | O | D (elle) / O (kod) | D | `meta.json`, `audio_highlight.py` |
| 10 | **Türkçe telaffuz hatasını satır bazında düzelt.** Yanlış okunan satırı **Replace Section** ile yeniden üret, tüm şarkıyı değil. Bu özellik yardım sayfasına göre Pro ve Premier'de var [RESMÎ]; fiyat sayfası ise "replace or add section"ı Premier altında gösteriyor, hesaptan doğrula. Sözü fonetik yazıma çevirme: altyazı hizalaması `_sozler.md`'yi okuyor | O | O | D | Suno, belge |
| 11 | **Persona/Voice'u kanalın tek sesi yapma.** Alt seri başına en fazla bir Persona kullan ve **private** yap; varsayılanı public [RESMÎ]. Aynı Persona ile aynı tarifin yan yana gelmesi şablon izi bırakır (§7) | O | D | **Y** (yanlış kullanılırsa) | Suno, `ses_ve_tarz_takibi.md` |
| 12 | **A/B betiğine yeni ölçütler ekle:** kanca zamanı, kırpılma/tepe, son sessizlik, erken sönme, crest, süre, varyant farkı (§4) | O | O | D | `suno_ab_olcum.js` (uygulanmadı) |
| 13 | **Ani biten sonlara kısa fade.** Çoğu dosya tam seviyede bitiyor. Yalnız son tepe oranı 0,35'i geçen dosyada 0,6-1,0 sn `afade=out` (§6). Suno'nun kendi editöründe de fade var [RESMÎ] ama bu yeni sürüm ve indirme demek | D | O | D | Kod: `ffmpeg_utils.py` (uygulanmadı) |
| 14 | **Remaster'ı dar kullan.** Yalnız sözü ve yapısı iyi, ama vokali gömülü ya da mix'i bulanık YENİ take'lerde "Subtle" ile dene. Söz ve yapı korunuyor [RESMÎ]. Her sonuç yeni bir indirme | D | O | O | Suno |
| 15 | **Stems ile vokal dengesi ayarlamayı şimdilik yapma** (§6) | — | Y | O | — |

---

## 2. Stil tarifi şablonu

**Kurallar:**
- Stil kutusu sınırı **1.000 karakter** (v4.5-v6) [YAYGIN; sayfadaki `maxlength` ile ölçülmüş].
- Etkili bölge ilk ~200-300 karakter. En önemli bilgiyi başa koy; deponun kuralı gereği açılış tanımı en başta kalır.
- **Sanatçı adı yazma.**
- 8-12 tanımlayıcı yeterli. Çelişen sıfatları bir arada kullanma (`aggressive` + `soft` gibi).

```
<AÇILIŞ: nasıl başlıyor, ilk kaç sn>,
<tür> <alt tür>, <NN BPM>, <mod: minor key / dorian / major>,
<mood: 2 kelime, şarkıya özgü bir imgeyle>,
<vokal: cinsiyet + doku + register + Turkish + clear diction>,
<enstrümantasyon: 2-3 çalgı, hangisi öne çıkıyor>,
<dinamik yol: nerede büyüyor>,
<mix/master: havuzdan 3 ifade>,
<süre/yapı: concise radio-length arrangement>,
<KAPANIŞ: strong final hit ending, no abrupt cutoff | gentle fade-out ending>
```

### Mix ifadeleri havuzu [YAYGIN]
Suno'nun bu kelimelere tepkisi resmî olarak belgelenmiş değil.

| Amaç | İfade |
|---|---|
| Net vokal | `clear upfront lead vocal`, `intelligible Turkish diction`, `dry intimate vocal` (reverb'i azaltır) |
| Üst frekans sertliği / "shimmer" | `smooth controlled highs`, `warm analog mix`, `no harsh cymbals` |
| Davul | `punchy tight drums`, `live drum kit` |
| Stereo genişlik | `wide stereo guitars`. Vokal merkezde kalmalı: `wide vocal` yazma, A/B'deki merkez/yan ölçütünü bozar |
| Yoğunluk | `polished radio mix`, `modern mastered sound` |

**Rotasyon kuralı:** mix cümlesini her şarkıya birebir kopyalama. Havuzdan 3 ifade seç, sırasını değiştir.
Aynı dizi bütün katalogda tekrarlanırsa şablon izi olur (§7).

### Exclude alanı
- 2-3 öğe yaz: istenmeyen vokal cinsiyeti, türe yabancı çalgı, `autotune`.
- Stil kutusunda `no X` yazmak, ayrı Exclude alanından daha az güvenilir [YAYGIN].

### Kaydırıcılar [YAYGIN]
Resmî önerilen değer yok.

| Kaydırıcı | Önerilen | Gerekçe |
|---|---|---|
| Weirdness | 35-50 | Tür dışına kaymasın |
| Style Influence | 65-80 | Uzun ve özenli tarif yazıldığında (v6 varsayılanı %50) |
| Variety (v6) | 0-30 | İki take karşılaştırılabilir kalsın. Resmî FAQ: 0 = tam stil kontrolü |

---

## 3. Meta etiket rehberi

| Etiket | Ne yapar | Kural |
|---|---|---|
| `[Intro]` | Suno bunu **enstrümantal açılış** sayıyor (depo gözlemi, `suno_prompt_hazirlik.md`) | Kullanacaksan süreyi yaz: `[Instrumental Intro (2 bars, clean guitar)]`. Hiç koymamak en kısa açılışı veriyor (Sabah Senin eski take'i 0,16 sn'de sese girdi) |
| İlk bölüm `[Chorus]` | Soğuk açılış; kanca 0-5 sn'de | Shorts kesiti ve tutma için en güçlü seçenek |
| `[Pre-Chorus]` / `[Build]` | Nakarat öncesi gerilim | Yavaş tempoda en fazla 2 satır |
| `[Drop]` | Elektronik/hiphop doruğu | Rock, pop ve akustikte kullanma; türü yanlış yöne çeker |
| `[Instrumental]` / `[Instrumental Break]` | Sözsüz ara | Süreyi uzatır, orta bölüm tutmasını düşürür. Şarkıda en fazla 1 tane, bar sayısıyla: `[Instrumental Break (4 bars, baglama)]` |
| `[Bridge]` | Kontrast | Son nakarattan önce, 4 satır |
| `[Outro]` | Kapanış alanı [YAYGIN] | 2 tam cümle (depo kuralı), 15-25 sn |
| `[End]` | Sert durdurma sinyali [YAYGIN] | **En son satırda, altında boş satır bile olmadan.** Kapanıştan sonra gelen anlamsız müzik kuyruğunu keser |
| `[Fade Out]` | Kademeli sönme; tek başına tutarsız [YAYGIN] | Yalnız sakin şarkılarda, `[Outro]` altında. Enerjik şarkıda kullanma, `strong final hit` ile çelişir |
| `[Verse \| low smoky delivery]` | v6 köşeli parantez içindeki performans yönergesini okuyor [YAYGIN, v6 testi] | Bölüm başına en fazla 3-4 kelime; dil ve söyleyiş tarzı için |

### Erken bitişi ve sönmeyi önleme
1. Son nakaratı Outro'dan önce **tam** yaz; "(tekrar)" gibi kısaltma kullanma.
2. Outro'yu `[End]` ile kapat.
3. Stil tarifinde kapanış tanımı olsun (mevcut kural).
4. Take 2:30'dan önce bitiyorsa Extend ile uzatma, **yeniden üret**. Extend yeni bir parça ve yeni bir ek yeri getirir.

### Türkçe telaffuz [YAYGIN + depo deneyimi]
- `Turkish` kelimesi hem türde hem vokal tanımında geçsin (`Turkish female vocals`). Mevcut uygulama bu.
- Sık bozulan sesler: **ğ** (ağarır, sıcağın, yüreğim), **ı** (ışık, kalır) ve ünsüz kümeleri.
  Bunları nakaratın ilk kelimesine koyma.
- Satır başına 8-13 hece bandı (depo kuralı) telaffuzu da korur; Suno hızlı satırlarda hece yutuyor.
- Hatalı çıkan kelimeyi söz dosyasında fonetik yazıma çevirme. Onun yerine Replace Section ile yalnız o satırı
  yeniden üret. `Temiz Sözler` doğru kalmalı; `caption_align` 0,25 eşiğiyle onu okuyor.
- Büyük harf, ünlem ve `...` vurguyu değiştirir. Noktalamayı tutarlı tut.

---

## 4. A/B ölçüt eklemeleri

Bunlar `suno_ab_olcum.js` için öneri; **uygulanmadı**.

Mevcut betik ilk 14 sn ile son 6,5 sn'yi ölçüyor. Mutlak değerler WAV ölçümünden ~%20 sapıyor. Bu yüzden yeni
ölçütlerin hepsi de **iki varyant arasındaki orana** bakmalı (dosyanın kendi kuralı).

| Yeni ölçüt | Nasıl ölçülür (tarayıcıda, indirmeden) | Karar kuralı |
|---|---|---|
| Süre cezası (`sure_sn` zaten var) | `el.duration` | 4:00'ı aşan varyant −1 puan. İkisi de aşıyorsa kısa olan önde |
| `kanca_sn`: ilk yüksek enerji anı | Baştan 60 sn topla (bugün 14 sn). 0,5 sn'lik kovalarda RMS hesapla. İlk 60 sn'deki tepe ortancasının %70'ini ilk aşan an | Küçük olan önde. Söz yapısından beklenen nakarat saniyesiyle karşılaştır |
| `kirpilma_orani` | Mutlak değeri 0,999 ve üstü olan örneklerin oranı (`getFloatTimeDomainData` zaten kullanılıyor) | İki varyant arasında 2 kattan büyük fark varsa yüksek olan elenir. Akış kod çözümü tepeyi yuvarlıyor; bu kesin TP ölçümü değil |
| `tepe_dbfs` | Pencere başına en büyük mutlak örnek | Yalnız sıralama için. Kesin TP, render öncesinde indirilen WAV'da `ebur128=peak=true` ile ölçülür |
| `crest_db` (dinamik) | 1 sn'lik pencerelerde 20·log10(tepe/RMS) ortancası | ~6 dB ve altı ezilmiş mix demek. Varyantlar arasında 3 dB'yi aşan fark anlamlı |
| `son_sessizlik_sn` | Son 6,5 sn'de RMS'in son tepenin %2'sinin altında kaldığı süre | 2 sn'den uzunsa boş kuyruk var. Render bunu kırpmıyor, izleyici sessizlik görüyor |
| `erken_sonme` | Şarkının %40, %60 ve %80 noktasına `currentTime` ile atla, her birinde 2 sn RMS ölç | %80 noktasındaki RMS, %40 noktasındakinin yarısından azsa şarkı erken sönüyor |
| `varyant_farki` | İki varyantın `MY_ortanca`, `kanca_sn` ve `crest_db` farklarının normalize edilmiş toplamı | Fark çok küçükse seçim **dinleyerek** yapılır; ölçüm "eşit" diyorsa kazanan uydurulmaz |
| Vokal anlaşılırlığı (vekil ölçüt) | `MY_ortanca` + 1-4 kHz bant enerjisinin toplama oranı (`getFloatFrequencyData`) | Yalnız ipucu. Nihai karar insan kulağında: nakaratın ilk satırı Türkçe olarak anlaşılıyor mu? |

Ölçüm süresi ~21 sn'den ~75 sn'ye çıkar ve hâlâ indirme kotası harcamaz.

### İnsan kontrol listesi
Ölçümün göremediği şeyler:
- Nakarat sözleri doğru söylenmiş mi?
- ğ ve ı telaffuzu doğru mu?
- Son nakarattaki distorsiyonlu gitar vokali örtüyor mu?
- Bölüm geçişlerinde "glitch" var mı?
- Son 5 sn'de fazladan söz ya da mırıltı var mı?

---

## 5. Loudness ve hafif mastering

### Platform hedefleri

| Platform | Hedef | Kaynak türü |
|---|---|---|
| Spotify | Normalizasyon **−14 LUFS** (ITU 1770). Master **−1 dBTP**'nin altında olmalı; −14'ten yüksek master için −2 dBTP. Kullanıcı ayarları: Loud −11, Quiet −19 | [RESMÎ] |
| YouTube | Yüksek içeriği ~−14 LUFS'a indiriyor, düşük içeriği yükseltmiyor. "Stats for nerds → content loudness" satırında görülüyor | [YAYGIN]; YouTube sayı yayımlamıyor |
| TikTok / Instagram / Facebook | Yayımlanmış bir müzik hedefi yok. Rehberler −14 LUFS / −1 dBTP öneriyor | [YAYGIN] |

### Bizdeki durum [ÖLÇÜLDÜ]
- Suno çıktıları zaten hedefte: −12,9 … −14,8 LUFS.
- Zincirde loudnorm yok, dolayısıyla "tek geçiş mi, iki geçiş mi" sorusu bugün yok.
- **Öneri: genel bir loudnorm ekleme.**
  - YouTube zaten yüksek sesi kısıyor; −14'e çekmek orada bir şey kazandırmaz.
  - Değişen tek şey −12,9 LUFS'luk dosyanın 1 dB kısılması olur.
  - Tek geçişli `loudnorm` dinamik modda pompalama yapabilir.
- **Tek gerçek risk true peak.** İki dosya −0,5 / −0,7 dBTP'de ve AAC 192k kodlama tepeleri taşırabilir.

### Uygulanacaksa (şu an uygulama yok)
- **Yer:** `ffmpeg_utils.py` render komutu, bugünkü `-map 0:a` çıkışı. Yalnız ölçülen TP −1 dBTP'yi aştığında
  devreye giren bir `-af` zinciri.
- **En hafif iki seçenek:**
  - `alimiter=limit=0.89:level=false` (≈ −1 dBFS örnek tepe; `level=false` otomatik kazancı kapatır).
  - İki geçişli `loudnorm`. Birinci geçişte `print_format=json` ile ölç. İkinci geçişte `measured_*` değerleri,
    `linear=true`, `I=<ölçülen I>` ve `TP=-1.5` ver. Böylece loudness değişmez, yalnız tepe sınırlanır.
- **Önce ölç, sonra işle.** `ebur128=peak=true` sonucunu log/state'e yaz ki "çalıştı mı?" sorusu cevaplanabilsin
  (CLAUDE.md'deki üç soru).
- **Test:** sentetik tepe sinyalinde çıkışın TP'si −1'in altında olmalı; −14 LUFS'luk dosyanın I değeri
  ±0,3 LU'dan fazla değişmemeli.

### EQ, de-esser ve "shimmer"
- AI kaynaklı parlama ve shimmer en çok 8-16 kHz'de duyuluyor.
- Kodda `highshelf=f=10000:g=-1.5` ya da `deesser` gibi işlemleri **toplu uygulama**. Üç sebep:
  - Her şarkının ihtiyacı farklı; toplu EQ iyi bir mix'i matlaştırır.
  - Otomasyonda sonucu kulakla kontrol eden kimse yok.
  - Bu, deponun "sessiz arıza" sınıfına girer: yapıldı görünür, zararı görünmez.
- Önce Suno'da çöz: `smooth controlled highs`, `no harsh cymbals`, gerekirse Remaster "Subtle".

### Riskler
- **Aşırı işleme:** en büyük risk, tonun kimse fark etmeden bozulması.
- **Telif / Content ID:** hafif limiter ya da EQ'nun eşleşmeyi değiştirmesi beklenmez. Content ID içeriğin
  parmak izine bakar. Bu, kaynağı olmayan bir deneyim bilgisi.
- Kapak, tempo ve yayın desenine etkisi yok.

---

## 6. Sessizlik, sonlar ve stems

### Baştaki sessizlik [ÖLÇÜLDÜ]
- `bastaki_sessizlik()` (−50 dB eşik, 0,12 sn pay, 3 sn tavan) doğru ve yeterli.
- Güncel dosyalarda baştaki sessizlik 0,06-0,81 sn. `config.py` yorumundaki 0,15-2,65 sn eski bir ölçüm.
- Değişiklik gerekmiyor.

### Sonlar
- Kodda son kırpma ya da fade yok; `-shortest` sesi sonuna kadar oynatıyor.
- 19 dosyanın 15'i son 4 sn'de hâlâ −14 … −17 dB'de. Bu "güçlü son vuruş" da olabilir, ani kesme de.
  A/B'deki `son_tepe_orani > 0,35` ölçütü tam olarak bu ikisini ayırıyor.
- **Öneri (kod, uygulanmadı):**
  - Sondaki sessizliği `areverse,silencedetect` ile ölç; 1,5 sn'den uzunsa 0,5 sn pay bırakıp kırp.
  - Son tepe oranı 0,35'i geçen dosyada 0,6-1,0 sn `afade=t=out` uygula.
  - Varsayılan kapalı bir bayrak ve bir log satırıyla başla.
  - Etki küçük: uzun formatı TV'den dinleyenler için ani kesme, sonraki videoya geçişte rahatsız ediyor.

### Stems: şimdilik değmez
1. Pro'da 2, Premier'de 3 ayrıştırma türü var [RESMÎ fiyat sayfası]. Bunlar üretim sırasındaki izler değil,
   **sonradan yapılan ayrıştırma**; yeniden birleştirmek artefakt ekler.
2. Her şarkıyı elle mix'lemek "otantik katkı" açısından artı olur. Ama tek kişilik ve kotası dar bir hatta
   zahmeti yüksek ve otomasyona uymuyor.
3. Vokali gömülü bir take için daha ucuz çözümler var: diğer varyant, Remaster "Subtle" ya da stil tarifinde
   `clear upfront lead vocal`.

**İstisna:** DJ setlerinde ve derlemelerde parçalar arasında vokal/enstrüman dengesi çok tutarsızsa, stem yerine
parça başına kazanç eşitleme (`loudnorm` ölçümüyle) daha doğru.

---

## 7. Kanal düzeyi: kimlik ve "inauthentic content"

### Tutarlılık ile çeşitlilik dengesi
- YouTube'un 2025 "inauthentic content" metninin hedefi **jenerik şablonla toplu üretim**.
- Aynı Persona, aynı stil tarifi, aynı bölüm iskeleti, aynı kapak düzeni ve aynı yayın aralığı tek tek sorun
  değil; **üst üste binmeleri** kanalı bu tanıma yaklaştırır.

**Persona / Voice önerisi:**
- "Kanal sesi" diye tek bir Persona kurma. `ses_ve_tarz_takibi.md` zaten vokal cinsiyeti ve dokusu rotasyonu
  yapıyor; tek bir Persona bu rotasyonu kilitler.
- Persona yalnız bir **karakter serisi** için mantıklı (karakter roster'ındaki ASI'nin sabit kimliği gibi).
  Orada "sabit kimlik" bilinçli bir küratörlük kararı.
- Persona'yı **private** yap; varsayılanı public [RESMÎ].
- Voices (kendi ses kaydı + doğrulama) v5.5'e bağlı [RESMÎ Voices FAQ] ve bu kanal için uygun değil.
  Gerçek bir kişinin sesi kullanılmıyor.

**Tutarlılık nerede olmalı:** marka (logo, "Famous Music Studio"), söz zanaatı kuralları, mix kalitesi
standardı, açılış ve kapanış kalitesi.

**Çeşitlilik nerede olmalı:** tür, tempo, vokal, bölüm iskeleti, mix ifadeleri, süre.

### Otantik katkının ucuz kanıtları
- Sözler insan/küratör sürecinden ve ret turlarından geçiyor (örnek: `Vardiya` reddi).
- Açıklamada söz kredisi zaten var (AI beyan satırı).
- Stil tarifinde her şarkıya özgü bir anlatı cümlesi (`storm-lit atmosphere`, `dawn after night shift`)
  jenerik tarif görüntüsünü kırar.

---

## 8. Plan ve özellik tablosu

Hesaptan doğrulanmalı.

| Özellik | Free | Pro | Premier | Kaynak |
|---|---|---|---|---|
| Model | v6-mini | v6, v6-wild | v6, v6-wild | [RESMÎ] fiyat sayfası, v6 FAQ |
| Ticari kullanım | yok | var | var | [RESMÎ] fiyat sayfası |
| Aylık indirme | — | **20** | **60** | [RESMÎ] fiyat sayfası. Depoda kota 27 görüldü; hesabın planını kontrol et |
| Stem ayrıştırma | — | 2 tür | 3 tür | [RESMÎ] fiyat sayfası |
| Replace Section | — | yardım sayfasında var | var ("replace or add section") | [RESMÎ] yardım sayfası ile fiyat sayfası **çelişiyor** |
| Crop / Fade | temel | var | var | [RESMÎ] fiyat sayfası, Song Editor |
| Extend | Song Editor "+" | var | var | [RESMÎ] Song Editor; plan kısıtı belirtilmemiş |
| Remaster (Subtle / Normal / High) | ? | ? | ? | [RESMÎ] özellik var, plan belirtilmemiş |
| Exclude | ? | ? | ? | [RESMÎ] özellik var, plan belirtilmemiş |
| Personas (artık Voices menüsünde) | ? | ? | ? | [RESMÎ] Voices FAQ |
| Suno Studio (çok kanallı, MIDI) | — | — | var | [RESMÎ] fiyat sayfası |
| Weirdness / Style Influence / Variety | ? | ? | ? | Kaydırıcılar var; önerilen değerler [YAYGIN] |

---

## 9. Kaynaklar

### Resmî
- Suno fiyatlandırma: https://suno.com/pricing
- Suno v6 FAQ: https://help.suno.com/en/articles/13924481
- Personas: https://help.suno.com/en/articles/3484161
- Voices FAQ: https://help.suno.com/en/articles/11362433
- Remaster: https://help.suno.com/en/articles/8105281
- Replace Section: https://help.suno.com/en/articles/3271873
- Song Editor (crop, fade, replace, extend): https://help.suno.com/en/articles/6141505
- Exclude: https://help.suno.com/en/articles/3161921 · https://suno.com/release-notes/exclude-styles
- Spotify loudness normalization: https://support.spotify.com/us/artists/article/loudness-normalization/

### Yaygın uygulama (resmî değil)
- Stil 1.000 / söz 5.000 karakter sınırı: https://hookgenius.app/learn/suno-character-limits/
- v6 değişiklikleri, take varyansı, köşeli parantez içi yönerge: https://hookgenius.app/learn/suno-v6-guide/
- Kaydırıcı değerleri: https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/how-to-use-suno-s-advanced-sliders-weirdness-style-audio-influence
- `[Outro]` + `[End]` ve son satır kuralı: https://songsmith.studio/blog/suno-song-endings-cheat-sheet · https://jackrighteous.com/en-us/pages/suno-ai-meta-tags-guide
- YouTube −14 LUFS ve "content loudness": https://productionadvice.co.uk/stats-for-nerds/
- TikTok/Reels loudness (yayımlanmış hedef yok): https://www.criticallisteninglab.com/en/learn/loudness/social-media
- Shorts'ta ilk saniyelerde tutma: https://www.tubeanalytics.net/blog/youtube-shorts-retention-guide
- YouTube "Jump ahead" (Premium; en çok atlanan bölüme atlatıyor, müzik videosunda intro'yu atlatabilir): https://www.androidauthority.com/youtube-jump-ahead-on-tv-3582215/

### Depo içi
- `olcum_temel_cizgi.json`, `projects/*/state.json`
- `suno_ab_secimi.md`, `suno_prompt_hazirlik.md`, `ses_ve_tarz_takibi.md`
- `ffmpeg_utils.py`, `audio_highlight.py`, `config.py`
- Hafıza notu: `project_inauthentic_content_riski`
