# Özgünlük planı: "toplu üretilmiş / özgün olmayan içerik" riskini azaltma

> Yazıldığı an: **2026-09-13 (Pazar)**. Bu belge **salt okunur** bir denetimin ürünüdür.
> Kod, state, git, API, tarayıcı ve Telegram kullanılmadı. Paket kurulmadı: görseller Pillow
> olmadan, **ffmpeg ile gri ham piksele çözülüp** saf Python ile hashlendi. Geçici betikler
> `AppData/Local/Temp/ozgunluk/` altındaydı ve silindi.
> Kapsam (kullanıcı kararı): kapak çeşitliliği, yayın aralığı, küratörlük. Ses ve metin tarafı
> ölçüldü, planda ikincil.

## 0. Kısa sonuç

- **Asıl tekrar fotoğrafta değil, şablonda.**
  - Kapak fotoğrafları birbirinden çok farklı. 16:9 kapaklarda pHash ortalaması 30/63; 253 çiftten yalnız 1'i ≤10 ve o çift bilinen kopya.
  - Buna karşın **20 şarkı kapağının 19'u birebir aynı düzende** (%95): ortalı üst başlık, aynı font, aynı gölge, başlığın hemen altında ortada aynı logo.
  - Tam görüntü pHash'i bu tekrarı **göremiyor**. Ölçüm ve kapı düzen düzeyinde kurulmalı.
- **Metinde tekrar başlıkta ve uzun açıklamada.**
  - YouTube başlık kalıbı 20/20 (%100) aynı.
  - Uzun açıklamalarda ortalama benzerlik 0,46 ve satırların %47'si başka açıklamalarda da geçiyor.
  - Hook ve soru iyi durumda: 20/20 ve 19/20 farklı, 17 şarkıda şarkıya özel.
  - Şarkıya özgü "hikâye" paragrafı: **0/20**.
- **Ritimdeki toplu desen ana katalogda kapandı, üç yerde hâlâ açık.**
  - 52 saatlik taban (11 Eylül) sonrasında aynı gün iki yeni uzun yükleme yok.
  - Açık 1: DJ/derleme hattı tabanı okumuyor.
  - Açık 2: geri doldurmalar platformlar arası dakikalar içinde patlıyor.
  - Açık 3: bir şarkının tüm platformları aynı dakikada çıkıyor.
- **İnsan emeği sinyali sıfır.** ~93 kamuya açık gönderinin **0'ı** kulis, söz defteri, topluluk gönderisi ya da kişisel açıklama. İlk ikisi 15 ve 19 Eylül'e planlı.
- **`cover-mood-variation` ana dala girmemiş** ve birleştirilemez: eski tabanda, 126 dosya ayrışmış, testleri siliyor. Yalnız fikri ve `MOOD_COLOR_MODIFIERS` tablosu yeniden kullanılabilir (§2a).

---

## 1. Ölçümler

### 1.1 Kapak ve görsel benzerliği

**Yöntem:**

- **pHash:** 32×32 gri → DCT → sol üst 8×8 (DC hariç 63 bit) → medyan eşiği.
- **aHash / dHash:** 8×8 ve 9×8.
- **Bindirme maskesi:** kapak ile **kendi `art.*`'ı** aynı kırpımla 160×90'a indirildi; farkı >45 olan pikseller başlık ve logonun kendisidir.
- **Katalog:** 20 şarkı + 2 DJ seti + 1 derleme = 23 proje × 3 görsel.

| Görsel | n | Çift | pHash ort. / medyan / min | ≤10 | ≤18 | ≤22 | aHash ≤10 | dHash ≤10 |
|---|---|---|---|---|---|---|---|---|
| `cover.png` (16:9) | 23 | 253 | 30,1 / 30 / 4 | 1 | 2 | 11 | 3 | 5 |
| `cover_vertical.png` (9:16) | 23 | 253 | 31,0 / 32 / 12 | 0 | 3 | 7 | 4 | 1 |
| `art.jpg` / `art.png` | 23 | 253 | 31,7 / 32 / 0 | 1 | 1 | 3 | 6 | 4 |

**En benzer 5 kapak çifti (16:9, pHash):**

| # | Çift (yollar) | pHash | aHash | Yorum |
|---|---|---|---|---|
| 1 | `projects/Küllerimden Geç/cover.png` ↔ `projects/Yeniden Doğacağım/cover.png` | **4** | 1 | Aynı `art.jpg` (pHash 0). Bilinen kopya; `Yeniden Doğacağım` bilerek unlisted |
| 2 | `projects/Kader Ortakları/cover.png` ↔ `projects/Sofraya Gelmedin/cover.png` | 18 | 28 | İkisi de karanlık, düşük kontrastlı gece karesi |
| 3 | `projects/Bir Bahar Daha/cover.png` ↔ `dj_sets/Just Relax/cover.png` | 20 | 12 | Koyu, doygunluğu düşük (s ≤0,05) |
| 4 | `projects/Kader Ortakları/cover.png` ↔ `projects/Sabaha Kadar/cover.png` | 20 | 17 | Sıcak-koyu ton |
| 5 | `projects/Beni Bırakma/cover.png` ↔ `projects/Kumdan Denize/cover.png` | 20 | 28 | Sınırda; yapı farklı |

Dikey kapaklarda ilk iki çift (kopya dışında):

- `projects/Sessiz Mektup/cover_vertical.png` ↔ `dj_sets/City Pulse Set/cover_vertical.png` (18)
- `projects/Bir Bahar Daha/cover_vertical.png` ↔ `dj_sets/Just Relax/cover_vertical.png` (18)

**Yapısal benzerlik: şablon tekrar oranı**

Bindirme kutusu (başlık + logo), 160×90 ızgarada:

| Kapak grubu | Adet | Bindirme kutusu | Düzen |
|---|---|---|---|
| Şarkı kapakları (fotoğraf yolu) | **19/20** | Yatayda ortalı (x ≈ 25-134, merkez 80), dikeyde **y 5-40** (yüksekliğin %6-44'ü) | Aynı |
| DJ setleri | 2/2 | Aynı kutu | Aynı |
| `Yükseliş` | 1/20 | x 0-159, y 37-89 | Farklı: prosedürel "zengin" düzen (sol hizalı kalın başlık, ayraç, sol altta logo, alt şerit) |
| `Gece Seansı Vol. 1` (derleme) | 1 | Mozaik | Farklı |

- **Şablon tekrar oranı:** ana katalogda **%95 (19/20)**, tüm kanalda **%91 (21/23)**.
- **Kaynak kod yolu:**
  - `generate_cover.py:696-718`: `is_photo` doğruysa `_add_title_text(..., y_center_ratio=0.13)`.
  - Başlık: `x=(w-text_w)/2`, punto kısa kenar × 0,14, `FONT_PATH` (normal kalınlık), beyaz, `shadowcolor=black@0.75`.
  - Logo: yükseklik × 0,26, `(main_w-overlay_w)/2`, başlığın hemen altında.
- **Glif IoU** (maskelerin piksel örtüşmesi) düşük: 16:9'da ort. 0,17, dikeyde 0,11. Sebep başlık harflerinin farklı olması; düzen aynı. Glif örtüşmesinin en yüksek olduğu çiftler: dikey `Kırık Zincir`↔`Sabah Senin` 0,69, 16:9 `Sabah Senin`↔`Sessiz Mektup` 0,53.
- **Görsel doğrulama:** `Kırık Zincir`, `Yeraltı` (16:9) ve `Sessiz Mektup` (9:16) kapaklarına bakıldı. Konum, font ve logo üçünde de aynı. `Yükseliş`'in farklı düzeni de gözle doğrulandı.

**Renk paleti (16:9 şarkı kapakları, ortalama HSV):**

- Ortalama parlaklık V = 0,35.
- **12/20 kapak V < 0,35** (karanlık).
- **7/20 kapakta doygunluk ≤ 0,10**, yani neredeyse siyah-beyaz: Beton Krallığı, Bir Bahar Daha, Gece Sürüşü, Kalbim Oynuyor, Kumdan Denize, Kırık Zincir, Yürek Yarası.
- Kaynak: 6 temanın 4'ünün `art_mood`'u gece ya da karanlık (`neon night`, `gritty urban night`, `dark dramatic moody`, `melancholy moody rainy`), bkz. `config.THEMES`.

**Sonuç:** fotoğraf çeşitliliği yeterli. Tekrar **düzen, tipografi, logo konumu ve karanlık-desatüre palette**. Bir pHash kapısı tek başına bugünkü kataloğu "çeşitli" sayardı, oysa izleyici feed'de aynı şablonu görüyor.

### 1.2 Metin tekrarı

`build_snippet`, `build_shorts_snippet`, `build_caption` ve `build_tiktok_kit_caption` 20 şarkının `meta.json`'ı ile **kuru** çalıştırıldı; ağ yok, yazım yok.

| Metin | Ölçüt | Değer |
|---|---|---|
| YouTube uzun başlık | `"X (Sözleri) \| Türkçe Y Şarkısı"` kalıbı | **20/20 (%100)**; Y yalnız 6 değer |
| Uzun açıklama (`build_snippet`) | Ort. SequenceMatcher / maks. | **0,46** / 0,63 (12 Eyl denetimi 0,79 ölçmüştü) |
| | Başka açıklamada da geçen satır oranı | **%47** (3 link satırı 20/20, bilinçli marka) |
| Shorts açıklaması | Ort. benzerlik / ortak satır | 0,41 / %51 ("Şarkının tamamı kanalımızda", "TikTok'ta" 20/20) |
| Kısa caption (`build_caption`) | Ort. benzerlik / ortak satır | 0,17 / %35 |
| | Kullanım satırı ("Bu sesi edit…") | Yalnız **8 farklı / 20** (en sık 4×) |
| | Takip satırı | Yalnız **8 farklı / 20** (en sık 4×) |
| Hook | Farklı / toplam | 20/20 (17'si `custom_hooks`) |
| Etkileşim sorusu | Farklı / toplam | 19/20. Tek tekrar: "Yeniden başlamak zor mu geldi?" (kopya çifti) |
| TikTok kit açıklaması | Ort. benzerlik | 0,34. AI beyan satırı 20/20 (zorunlu, **dokunulmaz**) |
| Söz alıntısı (beyit) | Olan açıklama | 20/20 |
| Şarkıya özgü hikâye / "neden bu şarkı" paragrafı | Olan açıklama | **0/20** |

Ek: YouTube'da görünen hashtag bloğu `#fyp #keşfet #foryou` ile başlıyor (`youtube_giris_denetimi_2026-09-13.md` b-3).

### 1.3 Ses ve tarz tekrarı

Kaynaklar: `ses_ve_tarz_takibi.md` ve `*_sozler.md` içindeki `## Stil Etiketi` blokları.

| Ölçüt | Değer |
|---|---|
| Stil etiketi arşivlenmiş söz dosyası | 16/21. İlk 3 şarkı ve `Küllerimden Geç` kayıtsız; `neon_kalp` üretilmedi |
| Stil kelime kümesi Jaccard ort. / maks. | **0,15** / 0,37 (`sokaklar_beni_tanir`↔`yukselis`, `bir_bahar_daha`↔`sessiz_mektup`) |
| Tekrarlanan ifadeler | `gentle fade-out ending` 5, `strong final hit ending` + `no abrupt cutoff` 5 (Outro kuralı gereği, bilinçli), `deep 808 bass` 3 |
| Sık doku sıfatları | `warm` 7, `deep` 7, `gritty` 4 |
| BPM yazılı | 13/16 |
| BPM kümeleri | 122-124: Kalbim Oynuyor, Sabaha Kadar, Kumdan Denize · 90-92: Kader Ortakları, Son Kez, Yeraltı · 76-78: Sessiz Mektup, Yürek Yarası, Sabah Senin |
| Tema dağılımı | hiphop **6/20 (%30)**, pop 4, arabesk 4, elektronik 2, rock 2, akustik 2 |
| Vokal (kayıtlı 15) | Erkek solo 6, kadın solo 5, düet 4 (3'ü erkek-erkek) |

**Sonuç:** ses tarafı üç eksenin en çeşitli olanı. Zayıf noktalar hiphop yoğunluğu, eksik arşiv, BPM kümeleri ve erkek-erkek düet tekrarı.

**Belge tutarsızlığı:** `ses_ve_tarz_takibi.md` "100-110 aralığı hiç kullanılmadı" diyor, ama `Bir Bahar Daha` 104 BPM.

### 1.4 Yayın ritmi

Kaynak: tüm `state.json` damgaları ve `tiktok_envanteri_2026-09-12.md`.

| Ölçüt | Değer |
|---|---|
| YouTube uzun yükleme | 20 (17 şarkı + 2 set + 1 derleme), 31 Ağu-11 Eyl |
| Gün başına uzun yükleme | **5 Eyl: 6** · 1 Eyl: 3 · 7 Eyl: 3 · 3 Eyl: 2 · diğer günler 1 |
| Ardışık 19 aralık | **5'i < 1 sa**, 15'i < 24 sa, **yalnız 1'i ≥ 52 sa** |
| 5 Eylül | 6 uzun video **02:12-03:26 (74 dk)** yüklendi. `publishAt` 04:30 / 05:00 / 05:30 / 06:00 / 06:30 (30 dk arayla, golden-hour dışında) + 09:00. Shorts'lar aynı anlarda |
| TikTok toplu yayın (envanter) | **5 Eyl 03:29-03:34: 7 gönderi** · 4 Eyl 07:41-07:43: 5 gönderi · 1 Eyl 21:50-21:53: 3 gönderi |
| Tüm platform yükleme olayı / gün | 5 Eyl **26** · 11 Eyl 17 · 7 Eyl 13 |
| Geri doldurma patlamaları | 5 Eyl 13:12-13:21: 9 dk'da 5 IG + 4 TikTok taslağı · 11 Eyl 07:57-07:59: 2 dk'da 6 olay (Bluesky/Telegram/Facebook, 2 set) · 11 Eyl 18:13-18:15: derleme 6 platform |
| Tek şarkının platformları | ör. `Sokaklar Beni Tanır` 20:04-20:06: YouTube + Shorts + TikTok + IG · `Sofraya Gelmedin` 12 Eyl 06:47-06:48: 4 platform |
| Toplu metadata | 11 Eyl: 40 kapak aynı gün değişti |
| Yanıltıcı damga | 13 Eyl 02:23:10'da 5 `tiktok_published_at` aynı saniyede. Bu **API tespit anı**, gerçek yayın değil (CLAUDE.md (e)). Pano ayırmalı |

**Mevcut tempo kuralları bu tekrarı engelliyor mu?**

| Kural | Engellediği | Engellemediği |
|---|---|---|
| 52 sa taban (`auto_process.MIN_YAYIN_ARALIGI_SN`, 11 Eyl) | Ana katalogda aynı gün iki **yeni** uzun yükleme. 11 Eyl sonrası tek yeni uzun yükleme var (Gece Seansı), sonraki aralık 66,8 sa | **DJ/derleme hattı** (`dj_famous_process.py` tabanı okumuyor; set ile şarkı aynı gün çıkabilir). Geri doldurmalar (bilinçli muaf) |
| Günlük pencere bölüşümü (24 sa / bekleyen) | Aynı koşuda çoklu işlem | Tek şarkının 4-6 platformda aynı dakikada çıkması |
| `ek_platform_backfill` günlük tavanı 1 | Telegram/Bluesky günlük sayısı | Instagram/Facebook/TikTok geri doldurma patlamaları. Platformlar arası kaydırma yok |
| `TIKTOK_KIT_*` (günde 1, haftada 4, 36 sa) | Kit açıkken TikTok toplu yayını | **`TIKTOK_KIT_AKTIF = False`**: elle yayında kod koruması yok (5 Eyl deseni) |
| Golden-hour (12-14 / 18-22) | Gece yayını (5 Eyl'deki 04:30-06:30 artık olmaz) | Saatlerin pencere başına yığılması |
| `uyumluluk.GUNLUK_YUKLEME_UYARI = 3` | — | Yalnız uyarı, yayın durmaz |
| Türev takvimi (±24 sa bant, günde 1, T0+21) | Türevlerin yeni yayına yapışması | Ana gönderilerin kendisi |

### 1.5 İnsan emeği sinyali

| Ölçüt | Değer |
|---|---|
| Kamuya açık gönderi (state'e göre) | YouTube uzun 20 + Shorts 20 + TikTok 14 işaretli (envanter 30) + Instagram 19 + Facebook 8 + Bluesky 7 + Telegram 5 = **~93** |
| Yayınlanmış kulis / söz defteri / topluluk gönderisi / kişisel açıklama | **0** |
| **İnsan emeği oranı** | **%0** |
| Planlı | `kanal_takvimi.json`: Söz Defteri #1 (15 Eyl 20:30, TikTok) + Kulis #1 (19 Eyl 13:00, TikTok). `turev_plani`: 4 × `kulis` (YouTube Posts), hepsi `planlandi` |
| YouTube Topluluk gönderisi | 0; `topluluk_soz_anket` türü hiçbir state'te yok. Topluluk sekmesinin açık olduğu **doğrulanmadı** (`youtube_live_plani.md`) |
| YouTube yorum yanıtı | `yorum_taslaklari.json`: 12 yorumun 11'i yanıtlanmış (%92). **1 bekleyen:** `Küllerimden Geç`, @canates8475, 8 Eyl (`comments_cache.json`). State'teki toplam YouTube yorumu 22 |
| Elle işlem defterinde `yorum_yaniti` | 0 kayıt (49 satırın hiçbiri); TikTok yanıtları ölçülmüyor |
| Küratörlük izi (metin) | 17/20 şarkıya özel hook ve soru · 20/20 söz alıntısı · 1 derleme notu. Görünür "neden bu şarkı" ya da süreç anlatısı yok |
| Görünmeyen insan emeği | Söz ret turları (`Vardiya` → `Sabah Senin`), A/B seçimi, kapak arama kuralları: hepsi belgede, hiçbiri kamuya açık değil |

---

## 2. Plan

Ölçekler:

- **Etki** hangi politika gerekçesini hedeflediğini gösterir.
  - **YT-İ:** YouTube "inauthentic content": toplu üretilmiş, jenerik şablon, özgün bakış açısı eklemeyen.
  - **TT-Ö:** TikTok Creator Rewards özgünlüğü: "minimum düzeyde düzenleme", "unoriginal content".
- **Zahmet** ve **Risk:** D = düşük, O = orta, Y = yüksek.

### (a) Kapak çeşitliliği

- **Ne:**
  1. **Düzen kütüphanesi.** 3-4 düzen. Her biri başlık çapası, font ağırlığı, logo köşesi ve boyu, kırpma odağı ve renk derecelendirmesiyle tanımlanır. Adaylar:
     - **D1 "ortalı-üst":** bugünkü düzen.
     - **D2 "alt-sol sade":** başlık sol altta, küçük logo sağ üst köşede; ayraç ve şerit yok.
     - **D3 "alt bant":** başlık alt üçte birde ortalı, logo sağ altta, kırpma odağı üst üçte bir.
     - **D4 "tipografik":** kalın font (`FONT_BOLD_PATH`), tek satır, logo sol üstte.
     - **Sabit kalanlar:** 0,14 punto tavanı, ölçümlü sığdırma (`_basligi_sigdir`), `MAKS_BASLIK_SATIRI = 2`, logonun koyu hâlesi, metinsiz `art.jpg` kuralı.
     - **Eklenmeyecek:** kullanıcının reddettiği dekoratif öğeler (ayraç, alt şerit, büyük logo bloğu). `_compose_cover_rich` aday değil.
  2. **Tema bazlı izinli düzenler.** Örnek: arabesk için D1/D3, hiphop için D2/D4. Seçim deterministik (başlık hash'i + son yayınların düzen kimliği). **Ardışık 3 yeni yayında aynı düzen yok.**
  3. **Renk derecelendirme.** Fotoğrafa hafif `eq` / `colorbalance`. Kaynak: stil etiketinden çıkarılan `mood`.
  4. **Mesafe kapısı (üç koşul birlikte).** Geçmiş tüm kapaklara karşı:
     - tam görüntü pHash ≥ 14;
     - düzen kimliği son 3 yayından farklı;
     - bindirme kutusu IoU'su (§1.1 yöntemi) son 3 yayına karşı < 0,6.

     Kapıdan geçemeyen kapak için önce sıradaki düzen, sonra Pexels sonuç indeksi +1 denenir; yine olmazsa `yayin_beklet` + bildirim.
  5. **Geçmiş kapaklar DEĞİŞMEZ.** Gerekçeler: 11 Eylül'de 40 kapak zaten aynı gün değişti; 2026-10-09 ölçüm penceresi bozulur; toplu metadata değişikliği kendisi bir sinyal.
- **`cover-mood-variation` yeniden kullanımı:**
  - **Durum:** dal `worktree-cover-mood-variation`, commitler `5365b72` ve `ef1792f` (4 Eyl). Ana dala **girmemiş**: commit yalnız worktree dallarında, `main`'de `MOOD_COLOR_MODIFIERS` yok. Dal eski tabanda; `main`'e göre 126 dosya farklı, `stock_art.py` ve 9 test dosyası silinmiş görünüyor. **Birleştirilmez.**
  - **Alınacaklar:**
    - `config.MOOD_COLOR_MODIFIERS` tablosu: 10 ruh hali → HSV kayma, doygunluk, parlaklık.
    - `meta.json` `mood` alanı fikri.
    - `ef1792f`'deki "mood'u stil etiketinden çıkar, tahmin etme" kuralı: dosya yoksa alan eklenmez.
  - **Uyarlama:** o çalışma yalnız **prosedürel** yolda aksan rengini değiştiriyordu. Bugün 19/20 kapak fotoğraf yolunda, yani tablo fotoğraf derecelendirmesine çevrilmeli.
- **Etki:** YT-İ "jenerik şablon" (yüksek). TT-Ö dolaylı: dikey kapak TikTok'ta elle seçiliyor.
- **Zahmet:** O (`generate_cover.py`, `config.py`, testler).
- **Risk:** O.
  - Kullanıcı daha önce bir düzen değişikliğini reddetti, bugünkü düzen de kullanıcı isteği. Kodlamadan **önce önizleme ve onay**.
  - Ölçüm penceresine karışma: yeni düzen yalnız yeni şarkılara, state'e `kapak_duzeni` etiketi.
- **Ölçüm:**
  - Şablon tekrar oranı %95 → **≤ %40** (son 10 yayın).
  - Ardışık aynı düzen: 0.
  - Yeni kapağın geçmişe en küçük pHash mesafesi ≥ 14.
  - Karanlık-desatüre kapak oranı (V < 0,35 ve s ≤ 0,10) izlenir.

### (b) Video formatı çeşitliliği

- **Bugün:** her şarkı videosu aynı kompozisyonda.
  - `youtube_16x9`: açılış kapağı (`INTRO_KAPAK`, 0,9 sn + 1,5 sn çözülme) → yuvarlak köşeli kart (`CARD_SIZE_RATIO 0.45`) → kayan, ton değiştiren bulanık zemin → marquee → ilerleme çubuğu → sabit marka satırı.
  - Shorts: aynı kart, 45 sn kesit.
- **Ne:** üç eksende rotasyon. Kombinasyon kimliği (`video_formati`) state'e yazılır, ardışık 2 yayında aynı kombinasyon yok.
  1. **Kart düzeni:** ortalı kart / sol kart + sağda söz satırı / kartsız tam ekran art + vinyet.
  2. **Alt bilgi:** marquee / statik künye / **gömülü söz altyazısı**.
     - Kaynak: `_sozler.md` "Temiz Sözler" + `caption_align` zamanlaması.
     - Yalnız ASR eşleşme oranı kapısından (≥ 0,25) geçen şarkılarda. ASR ancak yayından sonra geldiği için bu seçenek ilk yüklemede değil, Shorts ya da türev kesitte kullanılır.
  3. **Ses görselleştirme:** yok / ince dalga formu (`showwaves`) / ilerleme çubuğu.
- **Yeni render formatıyla uyum:**
  - Açılış kapağı ve atomik çıktı aynen kalır. Açılış kapağı zaten (a)'daki düzeni taşıdığı için kapak rotasyonu videoya da yansır.
  - Render süresi yeni biçimde **~17 dk / 272 sn (≈3,7×)** ölçüldü (`yayin_sonrasi_takvim_plani.md`). Dalga formu ve gömülü altyazı bunu artırır; her varyant tek şarkıda süre ölçümüyle açılır.
- **Etki:** TT-Ö "minimum düzenleme" (aynı kart + marquee kalıbı) yüksek; YT-İ orta.
- **Zahmet:** Y.
- **Risk:** O. Filtergraph ve `drawtext` tuzakları (CLAUDE.md), render süresi, pilde render.
- **Ölçüm:**
  - Son 10 videoda farklı `video_formati` ≥ 3.
  - Render süre oranı ≤ 4×.
  - Shorts izlenme oranının varyant bazında kıyası (en erken 2026-10-23).

### (c) Metin çeşitliliği

- **Ne:**
  1. **Başlık kalıbı rotasyonu (yalnız yeni videolar).** Arama niyeti için "Sözleri" her kalıpta kalır:
     - K1 `X (Sözleri) | Türkçe Y Şarkısı`
     - K2 `X — Sözleri | Famous Music Studio`
     - K3 `X (Sözleri) · <şarkıya özgü 2-4 kelime>`: `meta.json` `baslik_eki`, yoksa K1.

     Ardışık 2 yeni videoda aynı kalıp yok. Tür kelimesi açıklamanın ilk satırına taşınır.
  2. **Hikâye paragrafı.** `meta.json` `hikaye` alanı, 2-4 cümle: şarkının çıktığı an, reddedilen taslak, değişen bir satır ve nedeni.
     - **Kaynak:** söz yazarı ajanı (`muzik-produksiyon-ajani`) taslak yazar, kullanıcı düzeltir; `hikaye_onay_at`.
     - **Yeri:** `build_snippet`'te söz beytinden önce.
     - **Yasaklar:** AI vurgusu yok, "Suno" ve üretim aracı adı yok. Zorunlu AI beyanı (YouTube bayrağı; TikTok/IG/FB satırı) aynen kalır.
     - Alan yoksa açıklama bayt bayt eskisi gibi; otomasyon durmaz.
  3. **Havuz tekrarı.** `USE_LINES` ve `FOLLOW_LINES` 8'er satır; 20 şarkıda en sık satır 4 kez geçiyor. İkisi de ≥ 16'ya genişler ya da "son 5 yayında kullanılan satır seçilmez" kuralı gelir. Yalnız yeni projeler (`metin_surumu`), çünkü `pick_deterministic` tuzunu değiştirmek geçmiş metinleri de kaydırır.
  4. **YouTube görünen hashtag'lerinden `#fyp #foryou` çıkar** (denetim b-3). `config.py` başka ajandaysa ona iletilir.
- **Etki:** YT-İ "şablon metin" orta-yüksek (başlık feed'de görünen tek metin). TT-Ö düşük.
- **Zahmet:** D-O.
- **Risk:**
  - Başlık için O: "(Sözleri)" eki arama trafiği için eklendi (6 Eyl). Kalıplar bunu korur ve geçmişe dokunulmaz.
  - Hikâye için D.
- **Ölçüm:**
  - Başlık kalıbı tekrarı %100 → ≤ %50 (son 10).
  - Uzun açıklama ort. benzerliği 0,46 → ≤ 0,35.
  - Link bloğu **hariç** ortak satır oranı ayrıca raporlanır.
  - Yeni şarkıların %100'ünde onaylı `hikaye`.

### (d) Yayın ritmi

Kurallar mevcut tempo sistemine eklenir; hiçbiri yenisini icat etmez. Ortak kaynak **tek yardımcı modül** (`yayin_ritmi.py`): tüm yayın anlarını state'lerden okur ve `auto_process`, `dj_famous_process`, geri doldurmalar, TikTok kiti ve türev takvimi aynı fonksiyona "şimdi olur mu" diye sorar.

| # | Kural | Bugün | Bağlandığı yer |
|---|---|---|---|
| R1 | **Kanal geneli yeni yayın tabanı.** DJ seti, derleme ve şarkı aynı sayacı okur ve yazar. Set ↔ şarkı arası ≥ 48 sa (karar 4) | DJ hattı tabanı okumuyor | `auto_process._son_yeni_yayin_ani` → `yayin_ritmi`; `dj_famous_process.process_set` |
| R2 | **Toplu yükleme yasağı.** Platform başına kayan 24 sa'te en fazla 1 yeni kamuya açık gönderi; **geri doldurma dahil**. İki gönderi arası ≥ 6 sa | Yalnız Telegram/Bluesky'de günlük tavan | `ek_platform_backfill`, `facebook_backfill`, `instagram_upload.try_publish_pending`, TikTok kiti |
| R3 | **Platformlar arası kaydırma.** T0 = YouTube uzun formatın public anı. Shorts T0+24 sa · Instagram/Facebook T0 ile T0+26 sa arasında farklı pencere · TikTok kiti ≥ T0+1 gün · Telegram/Bluesky mevcut. **Bir şarkı aynı gün en fazla 2 platformda** | Aynı dakika | `youtube_upload` (Shorts `publishAt`), `instagram_upload` (konteyner oluşturma anı), `facebook_upload` |
| R4 | **Saat çeşitliliği.** Golden-hour içinde sabit pencere başı yerine dönüşümlü slotlar (ör. 12:00 / 13:15 / 18:30 / 20:00) | Pencere başına yığılma | `config.next_golden_publish_time` |
| R5 | **Toplu metadata tavanı.** Günde en fazla 3 videoda kapak/başlık/açıklama değişikliği. 2026-10-09 ve 2026-10-11 pencerelerinde kapak değişikliği yok | 11 Eyl: 40 kapak | `update_metadata.py`, `youtube_upload --thumbnail-only`, `youtube_kota` defteri |
| R6 | **Elle TikTok koruması.** Kit kapalıyken de "yayınladım" onayında son 36 sa içinde başka yayın varsa uyarı + `elle_islem` notu | Yok (5 Eyl: 5 dk'da 7 gönderi) | `upload/tiktok_yayin_onayi.py`, `turev_takvimi` |

- **R4'ün amacı izleyicidir.** Farklı saatlerde farklı dinleyiciye ulaşmak ve Analytics'te hangi slotun çalıştığını öğrenmek için. Bot tespitinden kaçınmak için **değildir**: gönderi sayısı ve ritim zaten gerçek, gizlenen bir şey yok.
- **Etki:** YT-İ "toplu üretilmiş" (günde 6 yükleme deseni) yüksek. TT-Ö "toplu / tekrarlayıcı gönderi" yüksek.
- **Zahmet:** O.
- **Risk:** O.
  - **Instagram:** konteyner 23 saatlik yaş kapısı var; R3'te konteyner geç oluşturulmalı, yoksa bayatlar.
  - **Kuyruk tıkanması:** `fix-pacing-starvation` dersi. R2 bekleyen işi sıraya koyar, düşürmez.
  - **Durgunluk alarmları:** `saglik_kontrol.yayin_durgunlugu` eşiği 78 sa (1,5 × 52 sa). R1 set tabanını eklediği için eşik yeniden hesaplanmalı.
- **Ölçüm (haftalık):**
  - Aynı gün > 1 yeni yayın: 0.
  - Aynı platformda < 6 sa aralıklı gönderi: 0.
  - Bir şarkının T0 günündeki platform sayısı ≤ 2.
  - Public saat dağılımı: en az 3 farklı slot.

### (e) Küratörlük

1. **"Neden bu şarkı" notu.**
   - `meta.json` `kurator_notu` (1-2 cümle): söz yazarı ajanı taslak yazar, kullanıcı onaylar (`kurator_notu_onay_at`).
   - Kullanım: sabitlenmiş yorumun ilk satırı (denetim (D) deseni) ve (c)'deki hikâyenin çekirdeği.
   - **Kapı:** önce uyarı; karar 3 onaylanırsa yeni şarkıda yükleme öncesi `yayin_beklet` (mevcut mekanizma, yeni kapı yok).
2. **Zayıf şarkıyı yayınlamama kapısı.** `meta.json` `kalite_karnesi`:
   - **A/B:** yalnız kazanan indirilir (`suno_ab_secimi.md`, mevcut). Karneye `suno_kalite_onerileri.md` §4 ölçütleri eklenir:
     - süre ≤ 4:00;
     - kanca ≤ 45 sn;
     - son sessizlik ≤ 2 sn;
     - erken sönme yok;
     - kırpılma oranı varyantlar arasında 2 kattan fazla farklı değil;
     - `varyant_farki` "eşit" ise **dinleyerek** seçim.
   - **İnsan kontrol listesi** (§4): nakarat doğru mu, ğ/ı telaffuzu, son 5 sn'de mırıltı.
   - **Söz:** katalogla sözlük örtüşmesi (medyan %53; `Vardiya` %32 ile reddedildi), Intro ve Outro kuralları.
   - **ASR:** yayın öncesi yerel ASR yok. Vekil ölçüt insan kontrolündeki "nakaratın ilk satırı anlaşılıyor mu". Yayından sonra `caption_align` eşleşme oranı < 0,25 ise şarkı **türev ve derleme adaylığından** düşer.
   - **Sonuç** `gecti` / `kaldi` / `elle_onay` olur; `kaldi` → `yayin_beklet`. Silme yok.
3. **Katalog büyüme hızı.**
   - Ayda ≤ 14 şarkı + 3 set + 1 derleme = **18 yükleme**, haftada ≤ 3 yeni şarkı. Bu kalıcı nottaki kota uyumlu öneri ve 52 saatlik tabanla tutarlı.
   - Sayaç `yayin_ritmi`'nden gelir. Aşımda yeni şarkı otomatik `yayin_beklet` ile sıraya girer.
   - Kota yüksek çıkarsa eklenecek olan şarkı değil, set.
- **Etki:** YT-İ "özgün bakış açısı eklemeyen" ve "toplu" yüksek. TT-Ö "özgün yaratıcı katkı" orta.
- **Zahmet:** O. Kullanıcı şarkı başına ~5 dk onay verir.
- **Risk:** O. Yeni kapı yayın durgunluğu yaratabilir; `saglik_kontrol.yayin_durgunlugu` zaten bunu yakalıyor. Onay darboğazı için tek Telegram mesajıyla onay.
- **Ölçüm:**
  - Yeni şarkıların %100'ünde onaylı not ve karne.
  - Kapıdan kalan oranı (0 ise kapı süstür, gözden geçir).
  - Aylık yükleme ≤ 18.

### (f) İnsan emeği

1. **Söz Defteri ve Kulis YouTube'a da.**
   - **Topluluk gönderisi:** TikTok gönderisinden ≥ 12 sa sonra, metin + görsel (defter fotoğrafı, kulis ekran görüntüsü). Önce Topluluk sekmesinin bu kanalda açık olduğu Studio'dan doğrulanır.
   - **Aynı çekimin dikey Shorts'u:** türev YouTube video tavanına (kayan 7 günde 1) sayılır; 52 saatlik tabana sayılmaz (insan emeği, `tempo_sayilir: false`).
   - **Kurallar:** yüz yok, üretim aracının adı ve logosu görünmez, DJ kulisi için ayrı rıza (`TUREV_DJ_KULIS_ONAYLI`).
2. **Yorum yanıtları.**
   - Bugün `Küllerimden Geç`'teki bekleyen yorum yanıtlanır.
   - Her yeni yayının ilk 24 saatinde elle yanıt; aynı cümle iki kişiye yazılmaz (`yorum_yanit_rehberi.md`).
   - Her gün `elle_islem ekle --islem yorum_yaniti`: bugün 0 kayıt var, ölçümün kaynağı bu.
   - Otomatik yanıt **yok**.
3. **Kişisel açıklama:** (c)'deki hikâye paragrafı ve (e)'deki "neden bu şarkı" notu.
- **Etki:** YT-İ "yaratıcının özgün ve otantik bakış açısı"nın doğrudan kanıtı (yüksek). TT-Ö özgünlük (yüksek).
- **Zahmet:** O (kullanıcı zamanı, haftada ~1-2 sa).
- **Risk:** D.
- **Ölçüm:**
  - Haftalık insan emeği gönderisi = 2 (`TUREV_INSAN_EMEGI_HAFTALIK_TAVAN`).
  - İnsan emeği oranı %0 → **≥ %15** (haftalık kamuya açık gönderilerin).
  - Yorum yanıt oranı ≥ %90 ve ortanca yanıt süresi ≤ 24 sa.

### (g) Ölçüm paneli: haftalık özgünlük skoru

- **Ne:** `ozgunluk_skoru.py`, salt okunur. API ve paket yok; görseller bu denetimdeki gibi ffmpeg ile çözülür.
- **Bileşenler** (0-100). Bugünkü taban bu denetimin sayılarıyla hesaplandı:

| Bileşen | Tanım | Bugün |
|---|---|---|
| **K** kapak | 100 × (1 − son 10 yayında şablon tekrar oranı). Ayrıca geçmişe min pHash ve karanlık-desatüre oranı raporlanır | 100 × (1 − 0,95) = **5** |
| **M** metin | 50 × (1 − uzun açıklama ortak satır oranı) + 50 × (1 − başlık kalıbı tekrar oranı), son 10 yayın | 50×0,53 + 50×0 ≈ **27** |
| **İ** insan emeği | 100 × min(1, insan emeği gönderisi ÷ (0,15 × haftalık kamuya açık gönderi)) | **0** |
| **R** ritim | 100 − 20 × (haftalık R1-R3 ihlali), en az 0. Son 7 gün ≥ 5 ihlal: 7 Eyl'de 3 uzun yükleme, 11 Eyl'de 2 dk'da 6 geri doldurma olayı, 12 Eyl'de 1 dk'da 4 platform | **0** |
| **Toplam** | 0,30K + 0,25M + 0,25İ + 0,20R | **≈ 8** |

- **Hedef:** Aşama 1 sonunda (2026-09-20) ≥ 30 · Aşama 2 sonunda (2026-10-04) ≥ 50 · Aşama 3 sonunda ≥ 70.
- **Bağlantı** (CLAUDE.md'nin üç sorusu):
  1. **Kim çağırır:** `weekly_report.haftalik_gozden_gecirme()`. Mesaja tek satır skor + bileşenler eklenir; `ozgunluk_olcum.json`'a haftalık anlık görüntü yazılır. Pano ve Hermes `python ozgunluk_skoru.py --json` okur.
  2. **Hangi görevden:** `auto_process.main()` `finally` → haftalık pencere. Yeni zamanlayıcı görevi yok.
  3. **Çalışmadığını nasıl anlarız:** skor hesaplanamazsa özet satırı "ölçülemedi: <sebep>" yazar, sessizce atlanmaz. Bir test ve entegrasyon duman testi olur.
- **Etki:** diğer maddelerin doğrulaması.
- **Zahmet:** O.
- **Risk:** D.
- **Ölçüm:** haftalık skor zinciri; bileşen düşerse haftalık özette neden satırı.

---

## 3. Aşamalar

**Canlı checkout kuralları:**

- İş worktree'de yapılır, PR ile `main`'e girer. Üretim klasöründe `reset --hard` / `clean -f` yok.
- `config.py`, `social_text.py` ve `youtube_upload.py` başka ajandaysa önce sahiplik netleşir. Bugün canlı checkout'ta yarım bir `build_caption(ai_beyani=...)` düzenlemesi TikTok ve Facebook adımını düşürdü.
- Her yazımdan sonra `ast.parse` ve bayt muhafızı (`tests/test_kaynak_bayt_muhafizi.py`).
- Testler: `python -m pytest -q -p no:cacheprovider --basetemp="<ayrı klasör>"`.

### Aşama 1: bu hafta (14-20 Eylül). En yüksek etki, en düşük risk

| # | İş | Tür | Dosyalar | Testler |
|---|---|---|---|---|
| 1.1 | **Ölçüm tabanı:** `ozgunluk_skoru.py` + haftalık özette satır (bugünkü ≈ 8 temel çizgi) | Kod, salt okunur | `ozgunluk_skoru.py` (yeni), `weekly_report.py` | `tests/test_ozgunluk_skoru.py` (küçük sabit PNG'lerle pHash, ffmpeg yoksa atla; metin benzerliği fikstürü) · `tests/test_entegrasyon_duman*.py` çağrı sırası |
| 1.2 | **R1 + R2:** kanal geneli yeni yayın tabanı (DJ/derleme dahil) ve platform başına 24 sa / ≥ 6 sa toplu yükleme yasağı (geri doldurma dahil) | Kod (kuralı daraltır) | `yayin_ritmi.py` (yeni), `auto_process.py`, `dj_famous_process.py`, `upload/ek_platform_backfill.py`, `upload/facebook_backfill.py`, `upload/instagram_upload.py`, `config.py` (`YAYIN_RITMI_*`), CLAUDE.md tempo maddesi | `tests/test_yayin_ritmi.py`: **5 Eylül deseni fikstür olarak** (74 dk'da 6 uzun yükleme → ilki dışında red; set + şarkı aynı gün → red; 2 dk'da 6 geri doldurma → 1 geçer) · `tests/test_auto_pace_count.py` ve `tests/test_kuyruk_basi_drain.py` regresyon · `ast` ile `dj_famous_process`'in `yayin_ritmi`'ni çağırdığının kontrolü · `saglik_kontrol` durgunluk eşiği testi |
| 1.3 | **Hikâye paragrafı alanı:** `meta["hikaye"]` → `build_snippet` (yoksa bayt bayt aynı). `Sabah Senin` ve `Yükseliş` için söz yazarı ajanı taslağı + kullanıcı onayı | Kod (küçük) + içerik | `upload/youtube_upload.py`, `meta.json` (yalnız bu iki proje, onaydan sonra) | `tests/test_youtube_snippet_hikaye.py`: alan yok → eski çıktı; "Suno" / "yapay zeka" / "AI" geçen hikâye → red; AI bayrağı değişmez |
| 1.4 | **İnsan emeği (elle):** 15 Eyl Söz Defteri #1 ve 19 Eyl Kulis #1 (planlı). Aynı içeriğin YouTube Topluluk sürümü (önce sekme doğrulaması). `Küllerimden Geç` bekleyen yorumuna yanıt. `elle_islem` kayıtları | Elle | `kanal_takvimi.json` (CLI ile), `elle_islemler.jsonl` (CLI ile) | — |
| 1.5 | **Kapak düzeni önizlemesi:** D2/D3/D4 adaylarının `Sabah Senin` ve `Yükseliş` üzerinde scratch çıktısı. Yayına girmez, state yazmaz. Kullanıcı seçer (karar 1) | Tasarım | Scratch (repo dışı) | — |
| 1.6 | **Büyüme tavanı ve "neden bu şarkı" notu** kuralı yazılı hâle gelir; `Yükseliş` üretilmeden önce not + vokal çelişkisi çözümü (`ses_ve_tarz_takibi.md`) | Belge + içerik | `suno_prompt_hazirlik.md`, `ses_ve_tarz_takibi.md` | — |

**Aşama 1 çıkış ölçütü:** skor ≥ 30; son 7 günde R1-R2 ihlali 0; en az 1 insan emeği gönderisi yayında; `Sabah Senin` hikâyeli.

### Aşama 2: 21 Eylül - 4 Ekim

| # | İş | Dosyalar | Testler |
|---|---|---|---|
| 2.1 | **Kapak düzen kütüphanesi** (onaylanan düzenler), rotasyon, üçlü mesafe kapısı, mood → renk derecelendirme (`MOOD_COLOR_MODIFIERS` uyarlaması). Yalnız yeni şarkılar | `generate_cover.py`, `config.py` (`KAPAK_DUZENLERI`, `MOOD_COLOR_MODIFIERS`), `stock_art.py` (kapıdan kalınca sonraki indeks) | `tests/test_kapak_duzen_rotasyonu.py` · `tests/test_kapak_mesafe_kapisi.py` · `tests/test_kapak_ayrac_geometri.py` her düzen için genişletilir · `drawtext` satır sonu tuzağı testi |
| 2.2 | **R3 platform kaydırma** (Shorts T0+24 sa, IG/FB farklı pencere, IG konteynerini geç oluştur) + **R4 saat slotları** + **R5 metadata tavanı** + **R6 elle TikTok uyarısı** | `upload/youtube_upload.py`, `upload/instagram_upload.py`, `upload/facebook_upload.py`, `config.py`, `auto_process.py` (drain), `upload/tiktok_yayin_onayi.py`, `upload/update_metadata.py` | Golden-hour sınır testleri · IG 23 sa yaş kapısı ile kaydırmanın birlikte testi · `tests/test_tiktok_yayin_onayi.py` genişletme |
| 2.3 | **Başlık kalıbı rotasyonu** (karar 2) + `USE_LINES` / `FOLLOW_LINES` genişletme, yalnız `metin_surumu ≥ 2` projeler | `upload/youtube_upload.py`, `config.py`, `upload/social_text.py` | `tests/test_social_text_hashtag.py` arşiv karşılaştırması eski projelerde bayt bayt aynı · yeni kalıp testleri |
| 2.4 | **Küratörlük kapısı:** `kurator_notu` + `kalite_karnesi` alanları; eksikse yeni şarkıda `yayin_beklet` (karar 3); A/B ölçütleri | `uyumluluk.py` (yeni kontrol, fail-closed sözleşmesiyle), `suno_ab_olcum.js`, `suno_ab_secimi.md` | `tests/test_uyumluluk*.py` genişletme: eksik not → bekletme; eski projeler muaf |
| 2.5 | **Söz Defteri Shorts'u** (türev tavanı içinde) + yorum yanıtı rutini ölçümü panoda | `turev_takvimi.py` (`soz_defteri` YouTube yüzeyi), `weekly_report.py` | `tests/test_turev_takvimi.py` genişletme |

**Aşama 2 çıkış ölçütü:** skor ≥ 50; son 10 yayında şablon tekrarı ≤ %60; başlık kalıbı tekrarı ≤ %70.

### Aşama 3: 5 Ekim - 1 Kasım (ölçüm pencerelerinden sonra)

| # | İş | Dosyalar | Testler |
|---|---|---|---|
| 3.1 | **Video formatı rotasyonu** (kart düzeni, gömülü söz altyazısı, dalga formu). Önce tek şarkıda render süre ölçümü. **2026-10-09 ölçümünden sonra**, 11 Eylül açılış değişikliğinin etkisi karışmasın diye | `ffmpeg_utils.py` (`_build_filter_complex`), `render.py`, `config.py` | Filtergraph dizgi testleri · render süre duman testi (ffprobe varsa) · atomik çıktı testi aynen |
| 3.2 | **Skor panoya ve Hermes'e;** eşiğin altındaki haftada "en çok puan kaybettiren bileşen" satırı | `ozgunluk_skoru.py`, pano | JSON sözleşme testi |
| 3.3 | **Değerlendirme:** 2026-10-09 ve 2026-10-23 ölçümleriyle kapak ve format değişikliklerinin yönü; büyüme tavanı ve düzen havuzunun gözden geçirilmesi | `olcum_temel_cizgi.py` (yalnız okuma) | — |

---

## 4. Kullanıcıya sorulacak kararlar

1. **Kapak düzeni: tek düzen mi, rotasyon mu?** Bugünkü "ortalı başlık + ortada logo" düzeni senin "DJ seti yapısı her yerde" isteğinden geliyor ve 19/20 kapakta aynı.
   **Öneri:** 3 düzenlik rotasyon. Önce `Sabah Senin` ve `Yükseliş` üzerinde önizleme gösterilir; dekoratif "zengin" düzen aday değil; geçmiş kapaklara dokunulmaz.
2. **YouTube başlık kalıbı dönüşümlü olsun mu?** Bugün 20/20 "X (Sözleri) | Türkçe Y Şarkısı".
   **Öneri:** evet, 21 Eylül'den itibaren yalnız yeni videolarda. "Sözleri" her kalıpta kalır, tür kelimesi dönüşümlü. Eski başlıklar değişmez (kota + toplu değişiklik riski).
3. **"Neden bu şarkı" notu ve hikâye paragrafı yayın kapısı olsun mu?**
   **Öneri:** Aşama 1'de yalnız uyarı. 21 Eylül'den itibaren yeni şarkıda zorunlu: eksikse `yayin_beklet`, onayı tek Telegram mesajıyla. Metni söz yazarı ajanı taslaklar, sen düzeltirsin.
4. **Ritim: set/derleme ↔ şarkı arası ortak taban kaç saat, Shorts uzun formattan sonraya kaysın mı?**
   **Öneri:** ortak taban 48 sa; Shorts T0+24 sa; bir şarkı aynı gün en fazla 2 platformda. Haftalık set Cuma akşamı olduğu için şarkılar Pazartesi/Çarşamba ritmine oturur.

---

## 5. Yöntem notları ve sınırlar

- **pHash eşikleri** (≤ 10 "neredeyse aynı", ≤ 18 "benzer") yaygın uygulama değerleridir; resmî bir platform eşiği değildir. Platformların hangi benzerlik ölçütünü kullandığı **bilinmiyor**. Bu yüzden planın hedefi hash değil, izleyicinin gördüğü düzen ve metin çeşitliliği.
- **Bindirme maskesi** kapak ile `art.*` farkına dayanır. Kapak kırpımı ile ffmpeg `force_original_aspect_ratio=increase,crop` birebir aynı değilse kenarlarda gürültü olur. Kutu konumları tutarlı çıktığı için sonuç etkilenmiyor.
- **TikTok sayıları** iki kaynakta farklı: state 14 işaretli, envanter 30 gönderi. İnsan emeği oranı hangi payda seçilirse seçilsin %0.
- **Ses ölçümü** yalnız stil etiketi metnine dayanır; ses dosyası analiz edilmedi.
- **Politika metinleri** bu oturumda yeniden doğrulanmadı. Kaynak: kalıcı not (`project_inauthentic_content_riski.md`) ve CLAUDE.md'deki bağlantılar. Kod aşamasından önce `icerik-uyumluluk-ajani` ile güncel metin kontrolü önerilir.
