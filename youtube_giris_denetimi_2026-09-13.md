# YouTube giriş denetimi — 2026-09-13

Salt okunur bir denetim. YouTube'a hiçbir yazma çağrısı yapılmadı; `state.json`, token ve git dosyalarına dokunulmadı.

**Dürüstlük notu:** planlanan canlı okuma (`videos.list` ile 42 id, `playlistItems.list`, 3 × `captions.list`) daha ilk istekte **`403 quotaExceeded`** aldı. Günlük ortak kota zaten tükenmişti; `auto_process.log` 00:05 ve 01:05 satırlarında da aynı hata var. Ortak kota Pasifik gece yarısında, yani **TR 10:00'da** sıfırlanıyor. Bu yüzden "Gerçek videoda" sütunları, en son yerel ölçümlerden dolduruldu ve her birinin tarihi yanında yazıyor:

- `state.json` istatistik/gizlilik okuması: 2026-09-12 13:05
- `upload/ai_beyani_onarim.json` + `ai_beyani_onar.log`: 2026-09-12 21:27
- `denetim_bulgulari`/`buyume_kontrol_listesi` D1 playlist dökümü: 2026-09-11

Canlı teyit gerektirenler (d) bölümünde "belirsiz" olarak listelendi.

Durum işaretleri: ✅ tam · ⚠️ eksik · ❌ yanlış · 🔒 yalnız Studio. Studio'daki Türkçe alan adları yaklaşıktır; arayüz sürümüne göre küçük farklar olabilir.

---

## 0) UYGULAMA — "Sabah Senin" (`projects/Sabah Senin/`)

**Çerçeve: YÜKLENİRKEN.** 02:18 itibarıyla `state.json` yok ve `output/.youtube_16x9.partial.mp4` hâlâ yazılıyor. Otomasyon bu şarkıyı 02:05 koşusunda sıraya aldı (`auto_process.log`: "bu koşuda işlenecek (1): Sabah Senin").

Render bitince kod şunu yapacak: golden-hour dışında olunduğu için uzun video ve Shorts **`private` + `publishAt = 2026-09-13T09:00:00Z` (TR 12:00)** ile yüklenecek (`config.next_golden_publish_time()` çıktısı; `upload/youtube_upload.py:433-443`, `:300-302`).

Aşağıdaki değerlerin hepsi `build_snippet` / `build_shorts_snippet` fonksiyonları salt okunur çağrılarak **kodun kendisinden** üretildi. Uzunluk ölçümleri:

- **Uzun başlık:** 43 karakter
- **Uzun açıklama:** 452 bayt
- **Uzun etiketler:** 150 karakter (boşluklu etiketlerin tırnakları dahil)
- **Shorts başlık:** 19 karakter
- **Shorts açıklama:** 309 bayt
- **Shorts etiketler:** 120 karakter
- **"Suno" geçiyor mu:** hiçbir alanda geçmiyor ✅

> ### ⚠️ BUGÜNE ÖZEL TUZAK — önce bunu oku
>
> Ortak kota TR 10:00'a kadar sıfırda. `videos.insert` 2026-06-01'den beri **ayrı kovada** olduğu için yükleme geçer (`denetim_bulgulari_2026-09-12.md:1050-1052`). Ama **`thumbnails.set` (50 birim) 403 alır**. `upload_video` bu hatayı yalnızca `print` eder (`upload/youtube_upload.py:456-461`). `auto_process.py`, `dj_famous_process.py` ve `saglik_kontrol.py` içinde **küçük resim için yeniden deneme süpürgesi YOK** (grep: 0 eşleşme).
>
> Sonuç: video 12:00'de **YouTube'un otomatik seçtiği kareyle** public olur.
>
> Playlist eklemesi de 403 alır. Proje `pending`de kaldığı sürece sonraki koşularda yeniden denenir. Bu, büyük olasılıkla doğru ama doğrulanmadı.
>
> **Yapılacak (10:00–12:00 arası, bir kez):**
> - Studio → İçerik → Sabah Senin → Küçük resim → `projects/Sabah Senin/cover.png`; Shorts için `cover_vertical.png`.
> - Ya da terminalden: `python upload/youtube_upload.py --project "projects/Sabah Senin" --thumbnail-only` (2 × 50 = 100 birim).
> - Ardından kontrol: `python upload/youtube_playlists.py --durum` (salt okuma, playlist başına 1 birim).

### Adım 1 — Dosya seçme (Select files)

| Öğe | Değer | Otomasyon yapıyor mu? |
|---|---|---|
| Uzun video dosyası | `projects/Sabah Senin/output/youtube_16x9.mp4` (1920×1080, H.264 High, 30 fps, AAC-LC 48 kHz stereo 192k) | Evet (`youtube_upload.py:446-452`) |
| Shorts dosyası | `output/shorts_9x16.mp4` (1080×1920, 45,0 sn, AAC 48 kHz) | Evet (`:472-480`) |
| Yükleme yolu | API `videos.insert` (1 çağrı, ayrı kova, günde 100) | Evet |

- 🎯 **Önerilen kodlama ayarları.** H.264 High, kapalı GOP, 48 kHz ses, stereo için **384 kbps**. Kapsayıcı MP4 olmalı ve **moov atomu başta** (Fast Start) durmalı; SDR için **BT.709** önerilir. Bizde ses 192k (`config.py:540`) ve ffmpeg komutunda `-movflags +faststart` ya da renk etiketi yok (`ffmpeg_utils.py:561-573`); çıktıda `yuvj420p` ve `color_primaries=unknown` görülüyor. Etkisi düşük, çünkü görüntü statik bir kart. Kaynak: <https://support.google.com/youtube/answer/1722171>
- 🎯 **Yükleme varsayılanları (Upload defaults) API yüklemelerini etkilemez.** Yardım sayfasına göre bu ayarlar yalnız web yüklemelerine uygulanır. Yani otomasyon için değer kodda sabitlenmeli (şu an öyle). Studio'dan elle yapılan yüklemeler içinse varsayılanları ayarlamak yine faydalı. Kaynak: <https://support.google.com/youtube/answer/2660027>
- ⚠️ **Aynı ses iki kez yüklenmesin.** `Küllerimden Geç` / `Yeniden Doğacağım` md5-eşit çifti bu kanalda yaşandı. `uyumluluk.py`'nin md5 kapısı yükleme öncesi HATA verir; "Sabah Senin" için kapı geçti (log'da HATA yok). Elle yüklemede bu kapı yok, o yüzden aynı `audio.wav`'ı başka bir başlıkla yükleme.

### Adım 2 — Ayrıntılar (Details)

| Studio alanı (TR / EN) | Uzun video — kopyala-yapıştır | Shorts — kopyala-yapıştır | Otomasyon yapıyor mu? |
|---|---|---|---|
| Başlık / Title | `Sabah Senin (Sözleri) \| Türkçe Rock Şarkısı` | `Sabah Senin #Shorts` | Evet (`youtube_upload.py:166`, `:260`) |
| Açıklama / Description | aşağıda (A) | aşağıda (B) | Evet (`:201-209`, `:252-254`) |
| Küçük resim / Thumbnail | `projects/Sabah Senin/cover.png` (1600×900, 1,34 MB → kod JPEG q3'e çevirip gönderiyor) | `cover_vertical.png` (900×1600, 1,47 MB) | Evet, ama **bugün 403 alacak** (tuzak kutusu) |
| Oynatma listeleri / Playlists | **Rock Şarkılar — Famous Music Studio** + **Türkçe Şarkılar — Kesintisiz Dinle \| Famous Music Studio** (`_tum_sarkilar`) | **Kısa Kesitler — Famous Music Studio** (`_shorts`) | Evet (`youtube_playlists.py:473-583`; `auto_process.py:1164-1172`, `:1199-1207`) |
| Kitle: Çocuklara özel mi? / Audience: Made for kids | Hayır | Hayır | Evet (`selfDeclaredMadeForKids: False`, `:291`) |
| Yaş kısıtlaması (gelişmiş) / Age restriction | Hayır | Hayır | Yalnız Studio (API'de ayrı alan yok) |

**(A) Uzun video açıklaması — kodun ürettiği metin:**

```
Gece benden, sabah senin 🌙

Sabah Senin | Famous Music Studio

“Ayakkabım elimde, yerler serin / Uyuyorsun, yüzünde dünkü gülüş”

Sıradaki parça için takipte kal 🔔

📷 Instagram: https://instagram.com/famous_music_studio
🎵 TikTok: https://www.tiktok.com/@famousmusicstudio
🌐 Website: https://famousmusicstudio.com

Eve döndüğünde ilk ne yaparsın? 👇

#FamousMusicStudio #fyp #keşfet #foryou #Rock #Alternative #Punk
```

**(A′) Öneri: yan yana, koddan farkı iki nokta.** Öneri yalnız yeni videolar içindir. `config.py` / `social_text.py` şu an başka ajanda olduğu için kod değişikliği yapılmadı.

1. **Hashtag sırası.** Görünen ilk üç hashtag türü söylesin, TikTok'a özgü `#fyp` / `#foryou` YouTube açıklamasından çıksın:
   `#Rock #TürkçeRock #FamousMusicStudio #türkçemüzik #keşfet`
2. **Başlıktaki "(Sözleri)" vaadini karşılasın.** `sabah_senin_sozler.md:129-…` "Temiz Sözler" bloğunun tamamı, beyitten sonra "Sözler:" başlığıyla eklensin. Ek yük yaklaşık 1,2 KB; toplam 5000 baytın çok altında kalır.

AI satırı **eklenmez** (karar). Link bloğu aynen kalır: CLAUDE.md'deki dış bağlantı yasağı yalnız Instagram/TikTok caption'larını kapsıyor, YouTube uzun açıklamasındaki link bloğu bilinçli.

**(B) Shorts açıklaması — kodun ürettiği metin** (`UZUN_VIDEO_ID` yükleme anında gerçek id ile doluyor):

```
Gece benden, sabah senin 🌙

Sabah Senin 🎵

Kesit yaparsan bu ses tam oturur 🔥

Sıradaki parça için takipte kal 🔔

Eve döndüğünde ilk ne yaparsın? 👇

#FamousMusicStudio #fyp #keşfet #foryou #Rock #Alternative #Punk

🎧 Şarkının tamamı kanalımızda: https://youtu.be/UZUN_VIDEO_ID
```

🎯 **Adım 2 püf noktaları**

- **Başlık:** en fazla 100 karakter, `<` ve `>` yasak. Bizimki 43 karakter; şarkı adı ve "Sözleri" arama kalıbı zaten ilk 40 karakterde. "İlk 40 karakter" kuralı resmî değil, yaygın uygulama. Kaynak: <https://developers.google.com/youtube/v3/docs/videos>
- **Açıklamanın ilk satırları:** yardım sayfası "ilk birkaç satır" izleyicinin önce gördüğü yer diyor ("it's what viewers will see first"). Bizde ilk satır hook, ikinci satır marka. Arama niyeti için ilk satıra şarkı adı + "sözleri" koymak bir seçenek. Kaynak: <https://support.google.com/youtube/answer/12948449>
- **Hashtag'ler:** başlığın yanında en fazla **3** hashtag görünür, **60'tan fazlası** varsa hepsi yok sayılır, alakasız/yanıltıcı hashtag yasak. Bizde 7 hashtag var (sınırın içinde), ama görünen ilk üçü `#FamousMusicStudio #fyp #keşfet`, yani türü söylemiyor. Kaynak: <https://support.google.com/youtube/answer/6390658>
- **Küçük resim:** önerilen 16:9 (Shorts 9:16), en az 640 px genişlik, **API ve mobilde 2 MB** sınırı. Hesabın doğrulanmış olması gerekir. Bizim 1600×900 kapak uygun; kod her zaman JPEG'e yeniden kodladığı için 2 MB sınırı korunuyor (`youtube_upload.py:377-388`). Kaynaklar: <https://support.google.com/youtube/answer/72431>, <https://developers.google.com/youtube/v3/docs/thumbnails/set>
- **Yayından sonra başlık/küçük resim değiştirme:** etkisini ölçen resmî bir kaynak bulunamadı; "ilk 24–48 saatte sık değiştirme" deneyime dayalı yaygın uygulama, resmî değil. Bu kanalda toplu `--description-only --all` = 42 × 50 = 2.100 birim ve toplu metadata değişikliği demek; yapma.

⚠️ **Adım 2 tuzakları (bu kanalda yaşandı)**

- **Metin sızıntısı:** kamuya açık hiçbir metinde "Suno" geçmez (kontrol edildi, geçmiyor). Etiketli sözler (`[Verse]`) açıklamaya sızmaz; alıntı "Temiz Sözler"den geliyor (`social_text.py:127-206`).
- **Playlist üyeliği için karar kaynağı:** `state.json`'daki `youtube_playlist_id` bir İDDİA, kapı değil. "Beton Krallığı" bu yüzden listesiz kaldı. Üyelik YouTube'dan okunmalı (`CLAUDE.md` playlist maddesi).

### Adım 3 — Daha fazla göster (Show more)

| Studio alanı (TR / EN) | Bu şarkı için değer | Otomasyon yapıyor mu? |
|---|---|---|
| Ücretli promosyon / Paid promotion | Hayır (`hasPaidProductPlacement` varsayılanı false) | Gönderilmiyor; varsayılan doğru ✅ |
| Yapay zekâ kullanımı (eski adı "Değiştirilmiş içerik") / AI use (Altered content) | **Evet** | Evet (`containsSyntheticMedia: True`, `youtube_upload.py:298`) |
| Otomatik bölümler / Automatic chapters | Tek şarkı; bölüm yok | — |
| Etiketler / Tags | aşağıda (C) | Evet (`:213`, `:257`) |
| Dil ve altyazı sertifikası / Language | Video dili **Türkçe (tr)**, ses dili **tr** | Evet (`defaultLanguage`/`defaultAudioLanguage`, `:227-228`) |
| Kayıt tarihi ve konum / Recording date & location | Boş bırak (isteğe bağlı; konum API'de **deprecated**) | Gönderilmiyor |
| Lisans / License | Standart YouTube Lisansı (`youtube`) | Gönderilmiyor; varsayılan ✅ |
| Yerleştirmeye izin ver / Allow embedding | Açık | Gönderilmiyor; varsayılan ✅ |
| Abone akışında yayınla ve bildir / Publish to subscriptions feed and notify | Açık | Gönderilmiyor; `notifySubscribers` varsayılanı `true` ✅ |
| Shorts remiksleme / Shorts remixing | Uzun video: izin ver (keşif). Shorts için kapatılamaz. | Yalnız Studio |
| Kategori / Category | Müzik (10) | Evet (`categoryId: "10"`) |
| Yorumlar ve puanlar / Comments and ratings | "Uygunsuz olabilecekleri incelemeye al"; beğeni sayısı görünür | Yalnız Studio |

**(C) Etiketler — uzun video (kodun ürettiği):**
`Rock, Alternative, Punk, Famous Music Studio, keşfet, fyp, viral, keşfetteyiz, müzik, şarkı, yenişarkı, türkçemüzik, foryou, Sabah Senin sözleri, sözleri, lyrics`

**Etiketler — Shorts:**
`Rock, Alternative, Punk, Famous Music Studio, Shorts, keşfet, fyp, viral, keşfetteyiz, müzik, şarkı, yenişarkı, türkçemüzik, foryou`

🎯 **Adım 3 püf noktaları**

- **Etiketler:** keşifte "minimal" rol oynar ("tags play a minimal role"); asıl işe yarayan başlık, küçük resim ve açıklama. Etiketler en çok sık yanlış yazılan adlarda faydalı. Toplam 500 karakter; virgüller de sayılır. Bizimki 150 karakter ✅. Kaynaklar: <https://support.google.com/youtube/answer/146402>, <https://developers.google.com/youtube/v3/docs/videos>
- **AI kullanımı:** yardım sayfası açıklama gerektiren örnekler arasında **AI ile üretilmiş müziği** sayıyor. Beyan edilince etiket, gerçekçi içerikte oynatıcıda, gerçekçi olmayanda genişletilmiş açıklamada görünüyor. Studio'da alan 2026'da yükleme akışında "AI use" adıyla yer alıyor; API alanı hâlâ `containsSyntheticMedia`. Kaynaklar: <https://support.google.com/youtube/answer/14328491>, <https://developers.google.com/youtube/v3/docs/videos>
- **Kayıt konumu:** `recordingDetails.location` 2017'den beri deprecated. Kaynak: <https://developers.google.com/youtube/v3/docs/videos>

⚠️ **Adım 3 tuzakları**

- **`set_privacy` AI beyanını siliyordu.** `videos.update` kısmi güncelleme yapmaz ve `videos.list(part=status)` `containsSyntheticMedia`'yı **geri döndürmez**. Eski `set_privacy.py` 42 videoda beyanı sildi; 2026-09-12 21:27'de onarıldı ("KALAN 0"). Gizlilik değiştirecek her kod `guvenli_status_govdesi` kullanmalı (`upload/set_privacy.py:62-85`). Elle `videos.update` yazma.

### Adım 4 — Video öğeleri (Video elements)

| Studio alanı (TR / EN) | Değer | Otomasyon yapıyor mu? |
|---|---|---|
| Altyazı ekle / Add subtitles | Dil **tr**, zamanlı parça: ASR zamanlaması + `sabah_senin_sozler.md` "Temiz Sözler" (ASR hazır olunca) | Evet (`youtube_captions.py:388-400`; `auto_process.py:1174` + drain'de yeniden deneme) |
| Bitiş ekranı / End screen | Son 5–20 sn: (1) "Türkçe Şarkılar — Kesintisiz Dinle" listesi, (2) Abone ol, (3) "En iyi eşleşme" video | **Yalnız Studio** |
| Kartlar / Cards | 1 kart, nakarattan sonra: Rock Şarkılar listesi | **Yalnız Studio** |

🎯 **Adım 4 püf noktaları**

- **Altyazı:** zamanlı dosya yüklenebiliyor; otomatik senkron seçeneği için önce video dili ayarlanmalı. `captions.insert`'teki `sync` parametresi **13 Mart 2024'te deprecated** oldu; kod `sync=False` gönderiyor (`youtube_captions.py:390`). Zararsız ama gereksiz. Maliyetler: `captions.list` 50, `insert` 400, `update` 450 birim. Kaynaklar: <https://support.google.com/youtube/answer/2734796>, <https://developers.google.com/youtube/v3/docs/captions>, <https://developers.google.com/youtube/v3/determine_quota_cost>
- **Bitiş ekranı:** yalnız son **5–20 saniyeye** eklenir, video en az **25 sn** olmalı, en fazla 4 öğe. Shorts'ta ve "çocuklara özel" videoda yok. Kaynak: <https://support.google.com/youtube/answer/6388789>
- **Kartlar ve bitiş ekranları Data API v3'te yok;** yalnız Studio (CLAUDE.md, playlist maddesi).

⚠️ **Adım 4 tuzakları**

- **Kota tükenmesi:** 2026-09-06'da `_drain_golden_hour_queue` her projede `captions.list` çağırıp kotayı bitirdi. Artık koşu başına en fazla 1 gerçek altyazı isteği var; bu kuralı bozma.
- **Türkçe küçük harf:** `"İ".lower()` tuzağı (`caption_align._norm_word`).

### Adım 5 — Kontroller (Checks)

| Studio alanı | Değer | Otomasyon yapıyor mu? |
|---|---|---|
| Telif hakkı / Copyright | "Sorun bulunamadı" beklenir | **Yalnız Studio** (Data API partner olmayan kanala Content ID itirazlarını göstermiyor) |
| Reklam uygunluğu / Ad suitability | Kanal YPP'de değil → gösterilmez | — |

⚠️ **Adım 5 tuzağı:** DJ setleri ve derlemeler 2 saatlik `private` karantinadan geçer (`dj_tarama_kontrol.py`). Ana katalog şarkısı geçmez; "Sabah Senin" için Kontroller sekmesi yükleme sonrası Studio'dan bir kez açılmalı.

### Adım 6 — Görünürlük (Visibility)

| Studio alanı | Değer | Otomasyon yapıyor mu? |
|---|---|---|
| Planla / Schedule | **2026-09-13 12:00 TR** (uzun + Shorts aynı an) | Evet (`private` + `publishAt`, `youtube_upload.py:300-302`) |
| Premiere olarak ayarla / Set as Premiere | Hayır | Hayır (API'de yok) |

🎯 **Adım 6 püf noktaları**

- **`publishAt`:** yalnız `private` iken ve video **hiç yayınlanmamışsa** geçerli. Kaynak: <https://developers.google.com/youtube/v3/docs/videos>
- **Premiere ile planlı yayın farkı:** Premiere geri sayım ve canlı sohbet getirir, hatırlatma ayarlayanlara ~30 dk önce bildirim gider. Shorts desteklenmez. Küçük kanalda boş bir premiere sohbeti ters etki yapabilir; bu değerlendirme resmî değil, yaygın uygulama. Kaynak: <https://support.google.com/youtube/answer/9080341>
- **`notifySubscribers`:** varsayılan `true`. İleride yeniden yükleme (ör. `Bu Gece Kazandık` yeni render) için `false` düşünülebilir; aynı şarkı abonelere ikinci kez "yeni video" diye gider. Kaynak: <https://developers.google.com/youtube/v3/docs/videos/insert>

⚠️ **Adım 6 tuzakları**

- **Önceden yayınlanmış videoya `publishAt` gönderilemez** (`invalidPublishAt`). Bunun için `youtube_gorunurluk_plani` kuyruğu var.
- **52 saat tempo tabanı:** "Sabah Senin" 12:00'de çıkınca sıradaki **yeni** şarkı en erken **15 Eylül 16:00**'da çıkabilir (`auto_process.MIN_YAYIN_ARALIGI_SN`). Elle `--count` verme.
- **`Bu Gece Kazandık` bekletmede** (`yayin_beklet`). Bekletme alanı silinmeden yayınlanmaz.

### Adım 7 — Yayından sonraki ilk 24 saat

| İş | Değer / metin | Otomasyon yapıyor mu? |
|---|---|---|
| Küçük resim gerçekten kapak mı? | Studio'da kartta başlıklı kapak görünmeli (tuzak kutusu) | Hayır, bugün elle |
| Shorts → İlgili video / Related video | Shorts `Sabah Senin #Shorts` → uzun "Sabah Senin (Sözleri) \| Türkçe Rock Şarkısı" | **Yalnız Studio** |
| Sabitlenmiş yorum / Pinned comment | aşağıda (D) | **Yalnız Studio** (sabitleme API'de yok; yorum atmak 50 birim) |
| Playlist üyeliği | `python upload/youtube_playlists.py --durum` | Evet (ekleme); kontrol elle |
| Altyazı | `state.json` → `youtube_captions_done: true` | Evet (ASR hazır olunca) |
| Gizlilik kayması | `saglik_kontrol.youtube_gizlilik_kaymasi` | Evet (uyarı) |

**(D) Sabitlenmiş yorum önerisi (kanal hesabından, elle):**

```
Gece vardiyasından eve dönen herkese 🌅 Sabahını kime bırakıyorsun?
Bütün şarkılar kesintisiz tek listede: <"Türkçe Şarkılar — Kesintisiz Dinle" liste bağlantısı>
```

🎯 **Adım 7 püf noktaları**

- **Shorts ilgili video:** Short'un altına tıklanabilir bir bağlantı ekler. **Gelişmiş özellik erişimi** gerekir; seçilen video public ya da unlisted olmalı. Shorts açıklamasındaki `youtu.be` satırı bunun yerine geçmez. Kaynak: <https://support.google.com/youtube/answer/14075157>
- **Gelişmiş özellik gerektirenler:** yorum sabitleme, uzun video açıklamasında tıklanabilir bağlantı, **bölüm ekleme**, çok dilli özellikler. Özel küçük resim ise ara düzey (telefon doğrulaması). Kaynak: <https://support.google.com/youtube/answer/9890437>

⚠️ **Adım 7 tuzağı:** geçmişte bir Shorts, playlist senkronu yükleme öncesinde çağrıldığı için hiçbir listeye girmedi. Artık Shorts sonrası ikinci bir senkron var (`auto_process.py:1199-1207`); bugün ise ikisi de kota yüzünden düşebilir.

### Adım 8 — İlk hafta

| İş | Nasıl | Otomasyon yapıyor mu? |
|---|---|---|
| Arama terimleri | Studio → Analiz → "İzleyiciler videonuzu nasıl buluyor" → gelen terim açıklamada var mı? | Hayır |
| Bitiş ekranı tıklama oranı | Studio → Analiz → video → Etkileşim | Hayır |
| Yanıt bekleyen yorumlar | `python upload/youtube_comments.py --print` → yanıtlar tek tek, onaylı | Okuma evet; yanıt elle (`yorum_gonder.py`) |
| Reporting API (son tarih 2026-10-11) | `denetim_bulgulari` E-2 (kapalı görünüyor) | — |

🎯 **Adım 8 püf noktası:** yardım sayfası, "nasıl buluyor" raporundaki terimlerin açıklamada geçmesini öneriyor. Kaynak: <https://support.google.com/youtube/answer/12948449>

⚠️ **Adım 8 tuzağı:** 10'dan fazla şablon yanıtı toplu göndermek "high-volume, repetitive" spam tanımına girer. Yanıtlar tek tek gitmeli (`upload/yorum_gonder.py` docstring).

---

## a) Adım adım yükleme kontrol listesi (tüm kanal)

"Gerçek videoda" sütunu **son yerel ölçümdür**; bugün canlı okuma yapılamadı. Örnek set: Sessiz Mektup (uzun, TR, public), Sessiz Mektup Shorts, Yeniden Doğacağım (uzun, unlisted, kopya), Küllerimden Geç (uzun), Just Relax (DJ, EN, public), Gece Seansı Vol. 1 (derleme), Bu Gece Kazandık (unlisted + bekletme).

### Ayrıntılar

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| `snippet.title` | ≤100 karakter, `<` `>` yasak ([videos](https://developers.google.com/youtube/v3/docs/videos)) | Şarkı: `<ad> (Sözleri) \| Türkçe <Tür> Şarkısı`; DJ: set adı; derleme: tür + adet | `youtube_upload.py:152-167`, Shorts `:260`, kesit `:549-553` | Ölçülemedi (kota); state'te 2026-09-12 13:05 istatistik okuması başarılı | ✅ | API (insert; `update` 50 birim) |
| `snippet.description` | ≤5000 bayt, `<` `>` yasak | Hook + marka + beyit + link bloğu + soru + ≤3 alakalı hashtag önde | `:201-209`; Shorts `build_caption` + tam versiyon linki `:252-254` | Ölçülemedi | ⚠️ İlk 3 hashtag `#FamousMusicStudio #fyp #keşfet`; tür yok | API |
| Hashtag'ler | En fazla 3'ü görünür; 60+ ise hepsi yok sayılır; alakasız yasak ([6390658](https://support.google.com/youtube/answer/6390658)) | Tür hashtag'i önde; `#fyp` / `#foryou` YouTube'da yok | `config.py:267`, `:276-280`; `youtube_upload.py:175` | — | ⚠️ | API (config değişikliği) |
| Bölümler (chapters) | İlk damga 00:00, ≥3 bölüm, her biri ≥10 sn ([9884579](https://support.google.com/youtube/answer/9884579)); gelişmiş özellik ([9890437](https://support.google.com/youtube/answer/9890437)) | Derleme ve **DJ setleri** | Yalnız derleme: `:187-191` (`0:00` biçimi) | Gece Seansı'nda "Parçalar:" listesi var (meta); bölümler oynatıcıda görünüyor mu belirsiz | ⚠️ DJ setlerinde yok | API (açıklama) |
| `snippet.tags` | Toplam 500 karakter, virgüller dahil; keşifte minimal rol ([146402](https://support.google.com/youtube/answer/146402)) | Tür + marka + "sözleri" + yazım varyantları | `:213`, `:257`, `:562` | — | ✅ (`fyp`/`viral` gereksiz) | API |
| `snippet.categoryId` | `videos.update`'te zorunlu | 10 (Music) | `:219`, `:263`, `:568` | — | ✅ | API |
| `defaultLanguage` / `defaultAudioLanguage` | BCP-47 | tr (ana katalog), en (DJ) | `:227-228`, `:271-272`, `:569-570` | 2026-09-10 öncesi videolar "İngilizce (ABD)" görünüyordu; sonra `--description-only` ile düzeltildi mi belirsiz | ⚠️ belirsiz | API |
| `localizations` | Başlık/açıklama çevirisi; orijinal dil önce ayarlı olmalı ([4792576](https://support.google.com/youtube/answer/4792576)) | Ana katalog: şimdilik yok. DJ setleri: TR çeviri isteğe bağlı | Gönderilmiyor (grep: 0) | — | ⚠️ (düşük öncelik) | API (`part=localizations`) |
| Küçük resim | 16:9 / Shorts 9:16; ≥640 px; API 2 MB; doğrulanmış hesap ([72431](https://support.google.com/youtube/answer/72431), [thumbnails.set](https://developers.google.com/youtube/v3/docs/thumbnails/set)) | `cover.png` / `cover_vertical.png` | `:377-414`, `:456-461`, `:483-490`; **yeniden deneme yok** | 40 video 2026-09-11 15:20'de `v2_buyuk_baslik` damgalı; derleme `Gece Seansı Vol. 1`'de damga yok | ⚠️ Yeniden deneme yok; derlemede belirsiz | API (50 birim) |
| Oynatma listeleri | `playlistItems.insert` 50 birim, `list` 1 birim | Tarz + ana zincir / derleme rafı + `_shorts` | `youtube_playlists.py:473-583`; `auto_process.py:1164-1172`, `:1199-1207` | D1 dökümü (09-11): hayalet `PLceMWZWzfCPQ`, Arabesk'te `kZML9g4GdBs` çift kayıt, 9 "Deleted video"; `Yeniden Doğacağım` unlisted olduğu hâlde Arabesk + zincirde duruyor olabilir | ⚠️ Temizlik Studio'da, silme API'de yok | Ekleme API, temizlik elle |
| Kitle: `selfDeclaredMadeForKids` | Yalnız sahibe döner | false | `:291`; `set_privacy.py:84`; `dj_tarama_kontrol.py:220` | 42 video 2026-09-12 21:27'de yeniden yazıldı | ✅ | API |
| Yaş kısıtlaması | Studio ayarı ([2802167](https://support.google.com/youtube/answer/2802167)) | Yok | — | — | 🔒 | Elle |

### Daha fazla göster

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| Ücretli promosyon | `paidProductPlacementDetails.hasPaidProductPlacement` varsayılan false ([videos](https://developers.google.com/youtube/v3/docs/videos), [154235](https://support.google.com/youtube/answer/154235)) | false | Gönderilmiyor | — | ✅ | API mümkün; gerek yok |
| `containsSyntheticMedia` / "AI use" | AI müzik açıklama gerektirir ([14328491](https://support.google.com/youtube/answer/14328491)); list ile okunmaz | true (karar) | `youtube_upload.py:298`; `set_privacy.py:83`; `dj_tarama_kontrol.py:219`; `auto_process.py:811` | 42 video 2026-09-12 21:27'de geri yazıldı (log "KALAN 0"); sonrası Studio'da doğrulanmadı | ✅ (API'den kanıtlanamaz) | API |
| `recordingDetails.recordingDate` | ISO 8601; konum deprecated | İsteğe bağlı; boş kalabilir | Gönderilmiyor | — | ✅ (gerek yok) | API |
| `status.license` | youtube / creativeCommon | youtube | Gönderilmiyor (varsayılan); `set_privacy` round-trip korur | 2026-09-11 okumasında alan dönüyordu | ✅ | API |
| `status.embeddable` | Varsayılan izinli | true | Gönderilmiyor; round-trip korur | — | ✅ | API |
| `status.publicStatsViewable` | Varsayılan görünür | true | Gönderilmiyor; round-trip korur | — | ✅ | API |
| `notifySubscribers` | Varsayılan true ([insert](https://developers.google.com/youtube/v3/docs/videos/insert)) | Yeni şarkı true; yeniden yüklemede false | Gönderilmiyor | — | ✅ / ⚠️ yeniden yükleme için | API parametresi |
| Shorts remiksleme | Uzun videoda seçilebilir; Shorts'ta kapatılamaz ([14946424](https://support.google.com/youtube/answer/14946424)) | İzin ver | — | — | 🔒 | Elle / Upload defaults |
| Yorumlar | Studio | "Uygunsuz olabilecekleri incelemeye al" | — | — | 🔒 | Elle / Upload defaults |

### Video öğeleri

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| Altyazı / sözler | `language`, `name` ≤150, `isDraft`; `sync` deprecated; list 50 / insert 400 / update 450 ([captions](https://developers.google.com/youtube/v3/docs/captions)) | Sözler dosyası olan her şarkıda tr zamanlı parça | `youtube_captions.py:381-400` (`name: ""`, `isDraft: False`, `sync=False`) | 18/18 ana katalog projesinde `youtube_captions_done: true` (state). DJ ve derleme için sözler kuralı yok. 3 örnekte `captions.list` planlanmıştı, **kota yüzünden yapılamadı** | ✅ ana katalog / ⚠️ Shorts'ta altyazı yok | API |
| Bitiş ekranı | Son 5–20 sn; ≥25 sn video; Shorts'ta yok ([6388789](https://support.google.com/youtube/answer/6388789)) | Liste + abone + en iyi eşleşme | API'de yok | Belirsiz | 🔒 | Elle (Studio'da "şablon içe aktar") |
| Kartlar | API'de yok | 1 liste kartı | — | Belirsiz | 🔒 | Elle |

### Kontroller

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| Telif hakkı | Content ID itirazları partner olmayan kanala API'de yok | Temiz | DJ/derleme karantinası `dj_tarama_kontrol.py`; `regionRestriction` varsayımı | City Pulse, Just Relax, Gece Seansı: Studio'da "hak talebi yok" (2026-09-12, state) | 🔒 | Elle |
| Gelir / reklam | YPP: 1.000 abone + 4.000 saat (12 ay) ya da 10M Shorts izlenmesi (90 gün); Shorts akışı izlenmesi 4.000 saate sayılmaz ([72851](https://support.google.com/youtube/answer/72851)) | YPP yok → uygulanmaz | — | 28 günde +28 abone (CLAUDE.md) | — | — |

### Görünürlük

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| `privacyStatus` | private / public / unlisted | public (golden-hour) | `youtube_upload.py:300-304`; `set_privacy.py:62-106`; görünürlük planı `auto_process.py:843-986` | State (09-12 13:05): Yeniden Doğacağım unlisted ✅; **Küllerimden Geç state'te `unlisted`, CLAUDE.md'ye göre YouTube'da public** (kayma bekleniyor); Bu Gece Kazandık unlisted + bekletme | ⚠️ state ↔ gerçek kayması | API |
| `publishAt` | Yalnız private + hiç yayınlanmamış | Sonraki golden-hour | `:433-443`; kesit `:501-519` | Kumdan Denize, Sessiz Mektup vb. `…Z` damgalı | ✅ | API |
| Premiere | Shorts yok, >1080p yok ([9080341](https://support.google.com/youtube/answer/9080341)) | Kullanma | — | — | 🔒 | Elle |
| Shorts → ilgili video | Gelişmiş özellik; hedef public/unlisted ([14075157](https://support.google.com/youtube/answer/14075157)) | Her Short → kendi uzun videosu | Yok; açıklamada `youtu.be` satırı var | Belirsiz (Studio'da görülmeli) | 🔒 ⚠️ | Elle |
| Sabitlenmiş yorum | Gelişmiş özellik; API'de sabitleme yok | Liste bağlantılı kısa yorum | Yok (`yorum_gonder.py` yalnız yanıt) | Belirsiz | 🔒 | Elle |

### Ses, dil, kanal

| Alan | Resmî sınır/kural | Önerilen değer | Bizde kodda | Gerçek videoda | Durum | Nasıl otomatikleşir |
|---|---|---|---|---|---|---|
| Otomatik dublaj / çoklu ses | Çoklu ses gelişmiş özellik ([13338784](https://support.google.com/youtube/answer/13338784)); yalnız müzik içeren videolar dublaja uygun değil (ikincil kaynak) | Şarkılarda kapalı | — | Belirsiz | 🔒 | Elle |
| Art Track / OAC | Distribütörle teslim edilmiş resmî yayın gerekir ([7336634](https://support.google.com/youtube/answer/7336634)) | Şimdilik uygulanmaz | — | — | — | Distribütör |
| Yükleme varsayılanları | Yalnız web yüklemelerine uygulanır ([2660027](https://support.google.com/youtube/answer/2660027)) | tr, Müzik, yorum incelemesi, AI kullanımı "Evet" (alan varsa) | — | Belirsiz | 🔒 | Elle |
| Kaynak dosya kodlaması | H.264 High, 48 kHz, stereo 384 kbps, MP4 moov başta, BT.709 ([1722171](https://support.google.com/youtube/answer/1722171)) | Ses 384k, `+faststart`, bt709 etiketi | `ffmpeg_utils.py:561-573`, `config.py:538-542` (192k, CRF 20) | Sessiz Mektup / Just Relax ffprobe: 192k AAC, `yuvj420p`, renk etiketsiz, moov başta değil (kaba tespit) | ⚠️ düşük etki | Kod |

---

## b) Farklar ve öneriler (öncelik sırasıyla)

1. **Küçük resim yeniden denemesi yok; bugün "Sabah Senin" otomatik kareyle çıkacak.**
   - **Etki:** yüksek. Kapak başlığı feed'deki tek kimlik; `Yeniden Doğacağım` kopya kararının sebebi de boş karttı.
   - **Kota:** 100 birim (uzun + Shorts), TR 10:00 sonrası.
   - **Risk:** yok. Yayın öncesi yapılır, tempo etkilenmez.
   - **Kalıcı çözüm:** `state.json`'da `youtube_thumbnail_updated_at` yoksa drain'de koşu başına en fazla 1 deneme (captions deseniyle aynı).
   - **Geçmiş videolar:** yalnız damgası olmayanlara (`Gece Seansı Vol. 1` ve Shorts'u) tek tek; `--all` değil.
2. **Ortak kota 13 Eylül Pasifik günü başlamadan tükendi, sebebi kayıtlı değil.**
   - **Bilinenler:** 2026-09-12 21:27 AI beyanı onarımı yaklaşık 42 × 51 = 2.142 birim; aynı gün başka ajan denetimleri de vardı.
   - **Etki:** yüksek. Küçük resim, playlist, altyazı ve yorum okuması düşüyor.
   - **Öneri:** elle kampanyalardan önce kota hesabı yapılsın; `auto_process` başında kota tükenmişse "YouTube yan adımları atlandı" bildirimi (`saglik_kontrol` adımı) eklensin.
   - **Kota:** 0 birim. **Risk:** yok. **Geçmiş videolar:** uygulanmaz.
3. **Görünen hashtag'ler ve etiketler TikTok'a göre kurulmuş (`#fyp #foryou #viral`).**
   - **Etki:** orta. İlk 3 hashtag türü söylemiyor; resmî kurala göre "alakasız hashtag" riski düşük ama sıfır değil.
   - **Kota:** 0 birim (yalnız yeni videolar).
   - **Risk:** `config.py` başka ajanda; ona iletilmeli.
   - **Geçmiş videolar:** **uygulanmamalı**. 42 × 50 = 2.100 birim ve toplu metadata değişikliği "inauthentic" sinyali tarafında gereksiz risk.
4. **Shorts → ilgili video bağlantısı hiçbir Short'ta yapılmamış olabilir.**
   - **Etki:** yüksek. Shorts kanal izlenmesinin %41'i, izlenme süresinin %4'ü; uzun videoya tıklanabilir tek köprü bu.
   - **Kota:** 0 birim (Studio). **Risk:** yok.
   - **Geçmiş videolar:** **evet**, 20+ Short için elle (gelişmiş özellik erişimi gerekir).
5. **DJ setlerinde bölüm yok.**
   - **Etki:** orta-yüksek. 40–80 dakikalık setler kanalın en çok izlenme süresi üreten videoları; bölümler gezinme sağlıyor ve bir küratörlük sinyali veriyor.
   - **Kota:** yeni setlerde 0 birim; geçmiş 2 set için 2 × 50 = 100 birim.
   - **Risk:** telif aralıkları (City Pulse) bölüm adına yazılmamalı.
   - **Geçmiş videolar:** evet, ama tek tek ve eksiksiz snippet ile (`update_metadata.py` deseni).
6. **Başlık "(Sözleri)" diyor, açıklamada yalnız bir beyit var.**
   - **Etki:** orta. Arama niyetini karşılar, açıklamayı videoya özgü kılar.
   - **Kota:** 0 birim (yeni videolar).
   - **Risk:** düşük. Açıklama benzerliğini düşürür, "inauthentic" riskine karşı yardımcı olur.
   - **Geçmiş videolar:** hayır; toplu güncelleme yok.
7. **Playlist temizliği (D1: hayalet liste, çift kayıt, 9 ölü satır, unlisted kopyanın listede kalması).**
   - **Etki:** orta. Kanalın en verimli yüzeyi.
   - **Kota:** 0 birim (Studio).
   - **Risk:** yalnız `Yeniden Doğacağım` satırı kaldırılır, `Küllerimden Geç` kalır.
   - **Geçmiş videolar:** evet (tek seferlik).
8. **Küllerimden Geç: state `unlisted`, gerçekte public.**
   - **Etki:** orta. Bio sayfası ve geri doldurmalar state'e bakıyor.
   - **Kota:** 1 birim (istatistik okuması düzeltir).
   - **Risk:** görünürlük planı uygulanınca tempo sayacı. CLAUDE.md'ye göre yalnız gerçekten değişen videoya damga yazılır.
   - **Geçmiş videolar:** — (izleme).
9. **Bitiş ekranı ve kartlar.**
   - **Etki:** orta. **Kota:** 0 birim (Studio, API yok). **Risk:** yok.
   - **Geçmiş videolar:** evet, uzun videolara bir şablon içe aktarılarak.
10. **Kodlama (ses 384k, `+faststart`, BT.709 etiketi).**
    - **Etki:** düşük. **Kota:** 0 birim. **Risk:** `config.py` başka ajanda.
    - **Geçmiş videolar:** hayır; yeniden yükleme = yeni video.
11. **`notifySubscribers=False` yalnız yeniden yüklemelerde (ör. `Bu Gece Kazandık`).**
    - **Etki:** düşük-orta. **Kota:** 0 birim.
    - **Risk:** yeniden yükleme yine de tempo tabanına sayılır; bu karar ayrı verilmeli.
    - **Geçmiş videolar:** hayır.
12. **`captions.insert(sync=False)` deprecated parametre ve `name: ""`.**
    - **Etki:** yok/düşük. **Kota:** 0 birim. **Geçmiş videolar:** hayır.
13. **`localizations` (DJ setlerine TR başlık/açıklama).**
    - **Etki:** düşük. **Kota:** set başına 50 birim (update).
    - **Risk:** metadata değişikliği. **Geçmiş videolar:** hayır.

Uygulanmayacaklar (kararlaştırılmış kurallar):

- Açıklamaya AI satırı eklenmez; `containsSyntheticMedia=True` aynen kalır.
- AI vurgulu hashtag ve hook kullanılmaz.
- "Suno" hiçbir kamuya açık metinde geçmez.
- 52 saat tempo tabanı ve golden-hour kuyruğu korunur.
- Yayınlanmış videoya `publishAt` gönderilmez.

---

## c) Elle yapılacaklar (yalnız Studio)

**Bugün, TR 10:00–12:00 arası (masaüstü):**

1. Sabah Senin → Küçük resim `cover.png`; Shorts'u → `cover_vertical.png`. Terminal alternatifi: `--thumbnail-only`.
2. Sabah Senin Shorts → **İlgili video** → uzun "Sabah Senin".

**Bu hafta (masaüstü):**

3. Tüm Shorts → İlgili video → kendi uzun videosu (toplu düzenleme yok; tek tek).
4. Uzun videolara bitiş ekranı: bir videoda kur, diğerlerinde "Videodan içe aktar".
5. Playlist temizliği: hayalet `PLceMWZWzfCPQ` sil; Arabesk'teki çift `kZML9g4GdBs` satırını ve 9 "Deleted video" satırını kaldır; `Yeniden Doğacağım`'ı zincir ve Arabesk'ten çıkar.
6. Ayarlar → **Yükleme varsayılanları**: dil Türkçe, kategori Müzik, yorumlar "incelemeye al", (varsa) AI kullanımı "Evet".
7. Ayarlar → Kanal → **Özellik uygunluğu**: gelişmiş özellikler açık mı? İlgili video, sabitleme ve bölümler buna bağlı.
8. 3 örnek videoda (Sessiz Mektup, Just Relax, Gece Seansı) Ayrıntılar → **AI kullanımı = Evet** görünüyor mu (API'den okunamıyor)?
9. Gece Seansı Vol. 1 → oynatıcıda bölümler görünüyor mu?

**Telefon (YouTube Studio uygulaması):**

10. Yeni yayında sabitlenmiş yorum (D) + yanıt bekleyen 1 yorum.
11. Kontroller/Kısıtlamalar: Sabah Senin'de "telif sorunu yok" teyidi.

---

## d) Doğrulanamayanlar — belirsiz

- **Canlı API okumalarının hepsi belirsiz** (kota tükenmiş): başlık/açıklama/etiket/dil alanlarının YouTube'daki hâli, `localizations`, `recordingDetails`, `topicDetails`, playlist üyelikleri ve 3 örnek videonun altyazı parçaları. Tekrar için TR 10:00 sonrası yaklaşık 165 birim (1 `videos.list` + 1 `playlists.list` + ~10 `playlistItems.list` + 3 × 50 `captions.list`).
- **Kota nasıl tükendi:** belirsiz (bkz. b-2).
- **`containsSyntheticMedia`'nın 42 videoda hâlâ yerinde olması:** belirsiz. API döndürmüyor; onarımdan sonra `set_privacy` çalıştı mı kaydı yok.
- **Kanalın gelişmiş özellik erişimi var mı:** belirsiz. Özel küçük resim çalıştığına göre en az ara düzey var.
- **"Sabah Senin" playlist eklemesinin sonraki koşularda otomatik tekrarlanması:** belirsiz. Proje `pending`de kaldıkça `process_project` yeniden çağrılıyor gibi görünüyor, ama tempo sayacı ve drain etkileşimi test edilmedi.
- **2026-09-10 öncesi yüklenen videolarda ses dili hâlâ "İngilizce (ABD)" mi:** belirsiz.
- **Studio "AI use" alanının Türkçe arayüzdeki tam adı ve yükleme akışındaki yeri:** yardım sayfası "AI use" diyor, Türkçe etiket doğrulanmadı.
- **Otomatik dublajın vokalli şarkılara uygulanıp uygulanmadığı:** resmî sayfa yalnız "sadece müzik" durumunu anıyor (ikincil kaynak); belirsiz.
- **Derleme bölümlerinde `0:00` biçiminin kabulü:** resmî metin "00:00" diyor; pratikte `0:00` da çalıştığı bilinir ama bu kanalda doğrulanmadı.
- **`upload/playlist_ids.json` değerleri 13 karakter:** YouTube playlist id'leri genelde daha uzun. Dosyada gerçekten böyle mi saklanıyor, yoksa bir maskeleme mi var, belirsiz. Önceki senkronlar çalıştığı için muhtemelen sorun değil.
- **11 Eylül derlemesinin 52 saatlik tabana sayılıp sayılmadığı:** otomasyon "Sabah Senin"i sıraya aldı; hangi kuralın geçirdiği bu denetimde incelenmedi.

---

## Kaynaklar

- **Data API:**
  - Videos kaynağı: <https://developers.google.com/youtube/v3/docs/videos>
  - videos.insert: <https://developers.google.com/youtube/v3/docs/videos/insert>
  - thumbnails.set: <https://developers.google.com/youtube/v3/docs/thumbnails/set>
  - Captions: <https://developers.google.com/youtube/v3/docs/captions>
  - Kota maliyetleri: <https://developers.google.com/youtube/v3/determine_quota_cost>
- **Yardım — metin ve keşif:**
  - Bölümler: <https://support.google.com/youtube/answer/9884579>
  - Hashtag: <https://support.google.com/youtube/answer/6390658>
  - Etiketler: <https://support.google.com/youtube/answer/146402>
  - Açıklama ipuçları: <https://support.google.com/youtube/answer/12948449>
  - Çeviri: <https://support.google.com/youtube/answer/4792576>
- **Yardım — medya ve öğeler:**
  - Küçük resim: <https://support.google.com/youtube/answer/72431>
  - Altyazı: <https://support.google.com/youtube/answer/2734796>
  - Bitiş ekranı: <https://support.google.com/youtube/answer/6388789>
  - Kodlama: <https://support.google.com/youtube/answer/1722171>
- **Yardım — beyanlar ve ayarlar:**
  - AI beyanı: <https://support.google.com/youtube/answer/14328491>
  - Ücretli promosyon: <https://support.google.com/youtube/answer/154235>
  - Remiks: <https://support.google.com/youtube/answer/14946424>
  - Yaş kısıtlaması: <https://support.google.com/youtube/answer/2802167>
  - Yükleme varsayılanları: <https://support.google.com/youtube/answer/2660027>
- **Yardım — yayın, erişim ve kanal:**
  - Premiere: <https://support.google.com/youtube/answer/9080341>
  - Shorts ilgili video: <https://support.google.com/youtube/answer/14075157>
  - Özellik erişimi: <https://support.google.com/youtube/answer/9890437>
  - Çoklu dil sesi: <https://support.google.com/youtube/answer/13338784>
  - OAC: <https://support.google.com/youtube/answer/7336634>
  - YPP: <https://support.google.com/youtube/answer/72851>
