# Sabah Senin — Orijinal Sözler (Rock)

Suno'nun Lyrics kutusuna aynen yapıştırılabilir.

> Yeni bir şarkı prompt'u yazmadan önce `ses_ve_tarz_takibi.md`'ye bak —
> vokal cinsiyeti/dokusu art arda tekrarlanmasın.

**Bu, `sabah_senin_sozler.md`'nin 2026-09-12 tarihli İKİNCİ yazımıdır.** Prodüksiyon
kararları (rock, kadın vokal, düet DEĞİL, 78 BPM, smoky husky low-register) ve tema
(emek / gece vardiyası / eve dönüş) aynen korundu — kullanıcı temayı reddetmedi.
Önceki turun yapısal kazanımları da korundu: çapa nakaratta açıp kapanıyor, kafiye
kökte, vurgusuz ekle biten satır yok, bölüm-içi hece SD düşük. Değişen İKİ şey var ve
ikisi de `suno_prompt_hazirlik.md`'ye bugün yazılan yeni kurallardan geliyor:
**muhatap açıldı** ve **Kova B sözlüğü temizlendi**.

**Başlık DEĞİŞMEDİ.** "Sabah senin" hâlâ çapanın kendisi: zaman sözcüğü, 4 hece,
2 kelime, muhatabı içinde taşıyor — ve yeni muhatapla daha da iyi çalışıyor, çünkü
"sabahı sana bırakmak" bir ebeveynin çocuğuna söyleyebileceği kadar bir sevgilinin
sevgilisine de söyleyebileceği bir şey. `projects/Sabah Senin/meta.json` ve
`stock_art._slugify("Sabah Senin") -> sabah_senin` eşleşmesi bu yüzden hiç dokunulmadan
geçerli kaldı.

## Muhatap — neden değişti, üç kişi testi

Eski muhatap **uyuyan küçük çocuktu** ve ölçüm şunu gösterdi: metin muhatapsız değildi
(19 "sen", kataloğun en yükseği, medyanın 4,75 katı) ama o "sen"in yeri dinleyiciye
KAPALIYDI — "yastığında süt kokun", "derin olsun uykun" satırlarını ancak küçük çocuğu
olan bir ebeveyn kendi hayatıyla doldurabiliyordu. Kullanıcının "diyalog kısıtlı,
dinleyici kitlesine" itirazı tam olarak buydu.

**Yeni muhatap: eve dönülen kişi — ilişki adı BİLEREK konmadı.** Metinde ne "çocuğum",
ne "sevgilim", ne "karım/kocam" geçiyor; muhatap yalnızca *gece ben çalışırken evde
uyuyan, sabahı ona bıraktığım kişi* olarak tarif ediliyor.

**Üç kişi testi** (`suno_prompt_hazirlik.md` → "Açık muhatap testi"):

| Dinleyici "sen"in yerine kimi koyabilir? | Metinde tıkanan bir satır var mı? |
|---|---|
| **Sevgili / eş** — "Üstünü örterim", "kapına varırım", "Sabah senin" | Yok |
| **Evde bekleyen aile bireyi** (anne, kardeş, ev arkadaşı) | Yok |
| **Küçük çocuk** (eski muhatap — hâlâ geçerli, ama artık TEK seçenek değil) | Yok |
| **Gece çalışıp eve dönen dinleyicinin kendisi** — "gece benden, sabah senin" | Yok |

**Nakarat kapısı:** *"Bu 4 satırı sevgilisine söyleyen biri kulağa saçma gelir mi?"*
— Hayır. Eski nakarat bu testten "süt kokun" yüzünden düşüyordu; yeni nakaratta o satır
yok ve nakaratta muhatabı tek bir role kilitleyen hiçbir kelime kalmadı.

## Stil Etiketi (Suno Style kutusuna yapıştır)

```
opens cold on the vocal with no instrumental intro, guitars enter on the second line, Turkish rock ballad, slow-burning and defiant, smoky husky low-register Turkish female vocals, baglama saz accent over live drums, dark dramatic storm-lit atmosphere, 78 BPM, wall of distorted guitars only in the final chorus, strong final hit ending, no abrupt cutoff
```

Etiket üç yerde değişti, üçü de "Stil etiketinde AÇILIŞ tanımı" kuralından:
1. **Açılış tanımı eklendi** (`opens cold on the vocal with no instrumental intro`) —
   bölüm iskeleti nakaratla açıldığı için vokalin hemen başlaması ŞART.
2. **Tırmanış makrosu bölündü**: `clean electric guitar arpeggio building into a wall of
   distorted guitars` tek cümlede hem açılışı hem doruğu veriyordu; artık doruk ayrı ve
   yeri belli (`only in the final chorus`).
3. **Sıra kalıbı kırıldı**: etiket `Turkish rock ballad` ile DEĞİL açılış tanımıyla
   başlıyor (katalogda 16 etiketin 15'i `Turkish <tür>, <mood>` ile başlıyordu).

## Bölüm iskeleti

`index = sha256("Sabah Senin")[:8] % 4` → **1** → nakaratla soğuk açılış:

```
[Chorus] > [Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Bridge] > [Chorus] > [Outro]
```

`[Intro]` YOK — katalogda üretilmiş 17 şarkının 17'si `[Intro]` ile başlıyordu ve
"hep aynı başlangıç" şikâyetinin tek en büyük sayısal sebebi buydu. Intro kuralı
(ilk satır temayı doğrudan adlandırmaz) bu iskelette açılıştan sonraki ilk kıtaya
kayıyor: `[Verse 1]`in ilk satırı "Servisin camında alnım, şehir akar" — somut bir an,
tema adı yok.

## Sözler (Suno Lyrics kutusuna yapıştır)

```
[Chorus]
Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

[Verse 1]
Servisin camında alnım, şehir akar
Vardiya bitti, ellerim hâlâ sıcak
Işıklar tek tek söner, sokak ağarır
Bu yol beni bilir, dosdoğru sana varır

[Pre-Chorus]
Saat altı, gökyüzü yeni açılır
Geceden ne kaldıysa sokakta kalır
Anahtar cebimde, kapına varırım
Eşiği yalnız sabah geçsin, bir de ben

[Chorus]
Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

[Verse 2]
Anahtar kilitte iki kez döner
Ayakkabım elimde, yerler serin
Uyuyorsun, yüzünde dünkü gülüş
Üstünü örterim, gece bende kalsın

[Bridge]
Şehir uyanır, ben gözümü kaparım
Bin pencere karanlık, birinde sen varsın
Yüreğim yorgun, gücümü senden alırım
Yol uzun ama sonunda senin sıcağın

[Chorus]
Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

[Outro]
Sabah senin, perdeyi biraz aralarım
Işık yüzüne düşsün, gölgeyi saklarım
```

## Temiz Sözler (YouTube açıklaması için kopyala-yapıştır)

```
Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

Servisin camında alnım, şehir akar
Vardiya bitti, ellerim hâlâ sıcak
Işıklar tek tek söner, sokak ağarır
Bu yol beni bilir, dosdoğru sana varır

Saat altı, gökyüzü yeni açılır
Geceden ne kaldıysa sokakta kalır
Anahtar cebimde, kapına varırım
Eşiği yalnız sabah geçsin, bir de ben

Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

Anahtar kilitte iki kez döner
Ayakkabım elimde, yerler serin
Uyuyorsun, yüzünde dünkü gülüş
Üstünü örterim, gece bende kalsın

Şehir uyanır, ben gözümü kaparım
Bin pencere karanlık, birinde sen varsın
Yüreğim yorgun, gücümü senden alırım
Yol uzun ama sonunda senin sıcağın

Sabah senin, ilk ışık sende olsun
Kapıyı açarım, sabah dolsun
Gece benden, bu karanlık benim
Sabah senin, bu yorgun eller senin

Sabah senin, perdeyi biraz aralarım
Işık yüzüne düşsün, gölgeyi saklarım
```

## Notlar

- Vokal dili: Türkçe ("smoky husky low-register Turkish female vocals" + Türkçe
  sözler). Tekli anlatıcı — düet DEĞİL.
- `config.py`'deki `theme` alanı için: `"rock"` (accent kırmızı). `meta.json`:
  `{"title": "Sabah Senin", "theme": "rock"}` — bu dosya `meta.json`'a DOKUNMADI.
- Tema: emek / gece vardiyası / eve dönüş. Eksen aynı kaldı: işyeri belgeseli değil,
  eve varış. **Emek hissi artık kelimeyle değil DURUMLA kuruluyor** — saat altı,
  sönen ışıklar, ağaran sokak, ayakkabıyı elde taşımak, şehir uyanırken gözünü
  kapatmak. Mesleği adlandıran tek kelime (`vardiya`) metinde bir kez geçiyor ve
  nakaratta yok.
- Kapanış: Outro İKİ TAM cümle, `...` yok; stil etiketinde
  `strong final hit ending, no abrupt cutoff` var.
- "Temiz Sözler" bölümü etiketli bölümden PROGRAMATİK olarak türetildi ve
  `caption_align.extract_clean_lyrics()` ile okunup BİREBİR doğrulandı
  (157 kelime, 30 söz satırı) — 0,25 eşleşme eşiği bu dosyayı okuyor.
- Dosya: UTF-8, BOM yok, satır sonu **CRLF** (önceki sürümle ve katalog çoğunluğuyla
  aynı), kaçak kontrol karakteri yok. `stock_art._slugify("Sabah Senin")` ->
  `sabah_senin`, `find_lyrics_file("Sabah Senin")` -> bu dosya. `"Sabaha Kadar"` ile
  çakışma YOK (difflib 0,522; eşik 0,85).

### Kova B temizliği (ne çıktı, ne geldi)

Önceki sürümde Kova B'den **5 kelime** vardı ve ikisi nakaratın merkezindeydi.
Yenisinde **2 kalıyor**, ikisi de nakaratın DIŞINDA:

| Çıkan | Nereye gitti |
|---|---|
| `makine yağı`, `demir` | → `Servisin camında alnım, şehir akar` (aynı yapı, Kova A kelimeleri) |
| `termosta kalan son yudum` | → `Vardiya bitti, ellerim hâlâ sıcak` |
| `fabrikanın düdüğü` | → `Işıklar tek tek söner, sokak ağarır` |
| `battaniyen kaymış`, `saçını koklarım` | → `Ayakkabım elimde, yerler serin` |
| `yastığında süt kokun` (NAKARAT) | → `ilk ışık sende olsun` |
| `derin olsun uykun` (NAKARAT) | → `Kapıyı açarım, sabah dolsun` |
| `Çocuk uyumuş, yanağında dünkü gülüş` | → `Uyuyorsun, yüzünde dünkü gülüş` (muhatap kilidi kalktı, `df` yükseldi) |

**Kalan 2 Kova B kelimesi:** `servis` (Verse 1) ve `vardiya` (Verse 1). Gerekçe: bu
ikisi olmadan metin "gece dışarıda kalmış biri"ne de okunabiliyordu; temanın EMEK olduğu
en az bir kez söylenmeli. İkisi de aynı kıtada, art arda, ve şarkının geri kalanı
onlara bir daha dönmüyor — kural gereği en fazla 2, nakaratta 0.

### Ölçümler (yazıldıktan sonra sayıldı)

| # | Ölçüt | Hedef | Yeni | Önceki sürüm |
|---|---|---|---|---|
| 1 | Katalogla 3+ harfli sözcük örtüşmesi | ≥%45 | **%68,8** (64/93) | %59,0 (59/100) |
| 1b | Aynı ölçüm, ön-ek gövde eşleşmesiyle | ≥%45 | **%75,3** (70/93) | — |
| 2 | Kova B kelime sayısı | ≤2 | **2** (`servis`, `vardiya`) | 5 |
| 3 | Nakaratta Kova B | 0 | **0** | 2 (`süt`, `yastık`) |
| 4 | Nakarattaki her ismin `df`'si | ≥2 | **sabah 9 · ışık 10 · kapı 7 · gece 15 · karanlık 5 · el 2** | süt 0, yastık 0 |
| 5 | Muhatap — `sen` zamiri | ≥4 | **17** | 19 |
| 5b | Üç kişi testi | geçmeli | **GEÇTİ** (4 farklı muhatapla doldurulabiliyor) | DÜŞTÜ (tek rol) |
| 6 | Duygu/iç dünya sözcüğü | ≥4 | **5** (yorgun, sıcak, yalnız, gülüş, yüreğim) | 5 |
| 7 | Saf redif oranı (kafiye çiftlerinde) | ≤%40 | **%12,5** (8 çiftin 1'i) | %0 |
| 8 | Vurgusuz ekle biten satır — nakarat / metin | %0 / ≤%20 | **%0 / %0** (0/30) | %0 / %0 |
| 9 | Hece bandı | 8-13 | **10-13**, ortalama 11,5 | 10-13 |
| 10 | Bölüm-içi hece SD | ≤1,0 | **en yüksek 0,50** | en yüksek 0,83 |
| 11 | Nakarat satır başına kelime | 4-6 | **6 / 4 / 5 / 6** | 5-6 |
| 12 | Çapa ("Sabah senin") — nakarat içi / metin | ≥2 / ≥5 | **2 / 7** | 2 / 7 |
| 13 | 4+ kelimelik birebir örtüşme (19 yayın dosyası) | 0 | **0** | 2 (bilerek, `vardiya` ile) |
| 14 | Yasak kalıp taraması | 0 | **0** | 0 |
| 15 | Somut isim / kıta — YALNIZ Kova A'dan | ≥2 | **3-5** | (kota Kova B ile doluyordu) |

Bölüm-içi hece dizilimleri: Chorus 11/10/10/11 (SD 0,50) · Verse 1 12/12/12/13 (0,43) ·
Pre-Chorus 12/12/12/12 (0,00) · Verse 2 11/11/11/12 (0,43) · Bridge 12/13/13/13 (0,43) ·
Outro 13/13 (0,00).

- **Çapa dönüşü (N1):** "Sabah senin" nakaratın 1. VE 4. satırında; Outro da onunla
  açıyor. ✓
- **Kafiye (redif DEĞİL):** nakarat AABB → `olsun / dolsun` (kök **ol** ortak, tam) ve
  `benim / senin` (kök **en** ortak, ekler farklı — redif değil). Verse 1 →
  `ağarır / varır` (kök **ar**, tam). Pre-Chorus → `açılır / kalır` (kök-sonu **l**,
  yarım). Verse 2 → `serin / kalsın` (yarım, **n**). Bridge → `kaparım / alırım`
  (yarım, **a**) ve `varsın / sıcağın` — **tek saf redif çifti, 8'de 1**. Outro →
  `aralarım / saklarım` (kök-sonu **la**, tam).
- **Nakarat ölçüsü:** 11 / 10 / 10 / 11 hece; 1↔3 = ±1, 2↔4 = ±1. En uzun kelime 3 hece
  (`karanlık`) — 4 hece sınırının altında. ✓
- **Tekrar bütçesi:** nakarat **3 kez** (hedef 3-5), Outro çapayı 1 kez daha veriyor.
  Nakaratta tek bir kelimenin yığılması yok (`senin` 3, `sabah` 3 — ikisi de çapanın
  parçası).
- **Satır başı denetimi:** hiçbir satır `Ben / Sen / Kimse / Herkes / Ama / Belki /
  Artık / Şimdi` ile başlamıyor (katalogda satırların %24'ü böyle başlıyor — kusur).
  30 satırın 26'sı somut bir isimle açıyor.
- **Anlam/deyim denetimi — satır satır yapıldı.** Önceki turda "Kira da benim"
  (Türkçede "kira bana ait" demek) yüzünden bir ret alınmıştı; bu yüzden her yüklem ve
  her iyelik yapısı tek tek okundu:
  - `Gece benden` = "gecenin yükü/ödemesi bana ait" — Türkçede tam olarak bu anlama
    gelen yerleşik yapı (`benim` DEĞİL, `benden`). ✓
  - `bu yorgun eller senin` = "bu eller sana ait" — sahiplik yönü doğru: emeğin
    muhataba adanması. ✓
  - `bu karanlık benim` = karanlığı ben üstleniyorum; `benden` ile aynı cümlede
    kullanılmadı, yani yön karışmıyor. ✓
  - `sokak ağarır` = "sokak aydınlanıyor/şafak söküyor" — `ağarmak` bu anlamda yerleşik. ✓
  - `Bu yol beni bilir` = yolun ezberlenmişliğini yoldan yana çevirmek; günlük Türkçede
    kurulan bir devrik (`yol beni tanır` ile aynı sınıf). ✓
  - `Eşiği yalnız sabah geçsin, bir de ben` = "eşikten sadece sabah geçsin, bir de ben" —
    `bir de ben` yerleşik ekleme yapısı. ✓
  - `gece bende kalsın` = geceyi ben tutayım; `Gece benden` ile tutarlı, çelişmiyor. ✓
  - `Şehir uyanır, ben gözümü kaparım` = tersine dönmüş gün — "gözünü kapamak"
    (uyumak) yerleşik. ✓
  - `gücümü senden alırım` = yerleşik. `Yol uzun ama sonunda senin sıcağın` = yüklemsiz
    devrik, katalogda sık (`Camda yağmur, içim kurur`). ✓
  - `Işık yüzüne düşsün, gölgeyi saklarım` = ışığı ona, gölgeyi kendine ayırmak;
    nakaratın "gece benden / sabah senin" denklemini kapanışta tekrarlıyor. ✓
  - **Kaldırılan yapılar:** `omuz verdim` (çelişik), `Kira da benim` (yanlış yön) zaten
    önceki turda atılmıştı; bu turda ayrıca `üstünü örterim, derin olsun uykun`
    ikilisinin nakarattaki hâli kaldırıldı (muhatap kilidi), `üstünü örterim` tek başına
    Verse 2'de kaldı — o satır bir sevgiliye de söylenebilir.
- **Tek tema:** biri geceyi taşır, biri sabaha uyanır. İkinci bir tema yok.
