# Ek platformlar iş planı: Telegram · Facebook · Bluesky

Hazırlanma: 2026-09-13 (Pazar) · Bakış açısı: `sosyal-medya-danismani` (salt okunur; kod, state, git, API, tarayıcı ve Telegram mesajı yok)
Eş belgeler (aynı gün): `tiktok_live_plani.md`, `youtube_live_plani.md`, `ozgunluk_plani.md`, `yayin_sonrasi_takvim_plani.md`.
Bağlı kararlar: **aynı gün bir şarkı en fazla 2 platformda · set ↔ şarkı 48 sa · TG/BS türevleri günlük tavan 1'e dahil · kamuya açık metinde "Suno" yok · AI beyan satırı Facebook'ta var, Telegram/Bluesky'da yok · insan emeği serileri: Söz Defteri, Kulis.**

> **Kaynak güvenilirliği notu.**
> - **[R]** resmî metin okundu (URL §9'da) · **[R-özet]** resmî sayfanın yalnız özeti okundu · **[İ]** ikincil kaynak, **doğrulanmadı** · **[D]** depo içi kanıt (dosya/state/log).
> - **API okuması YAPILMADI.** Takipçi ve abone sayıları görev tanımındaki elle okumalardan (13 Eyl). Facebook, Telegram ve Bluesky için depoda **hiç etkileşim verisi yok** (`olcum_temel_cizgi.json`'da bu platformların alanı yok).
> - Bluesky takipçi sayısı **bilinmiyor**.

---

## 0. Kısa sonuç

1. **Üç platformun asıl sorunu içerik değil, desen.** State'lere göre bu platformlardaki 20 gönderinin çoğu, aynı şarkının 2-3 platforma **aynı dakikada** çıkması şeklinde yayınlandı (12 Eyl 06:48'de `Sofraya Gelmedin` 33 sn içinde FB+TG+BS). **Bugün de sürüyor:** `Sabah Senin` 13 Eyl 12:00'de YouTube uzun + Shorts + Facebook (+ Instagram, + 12:05'te TG/BS geri doldurması) ile **5-6 yüzeye** çıkacak. Facebook'ta aynı 12:00'ye **iki Reels** planlı (`Kader Ortakları` + `Sabah Senin`). "Aynı gün en fazla 2 platform" kararı kodda henüz yok (özgünlük R3, Aşama 2).
2. **Roller:**
   - **Telegram = stüdyo defteri ve ilk duyuru.** Sadık dinleyici, tam şarkı arşivi, T0 günü.
   - **Facebook = Türkçe geniş kitle, Reels vitrini.** T0+2 gün.
   - **Bluesky = yaratıcı topluluğu ve keşif akışları.** T0+3 gün, süreç anlatımı.
3. **Önerilen merdiven:** Gün 0 YouTube + Telegram · Gün 1 Shorts + Instagram · Gün 2 TikTok + Facebook · Gün 3 Bluesky.
4. **En acil düzeltmeler:**
   - Telegram kanal açıklaması **yanlış YouTube kanalına** gidiyor; kullanıcı adı marka dışı.
   - `Kader Ortakları` Telegram gönderisi **belirsiz** (gitmiş olabilir).
   - `marka/facebook_metinleri.txt` "Tüm içerik yapay zekâ ile üretilmiştir" diyor; "sözler insan yazımı, AI destekli" kararıyla çelişiyor.
   - `City Pulse Set` (telif eşleşmeli) üç platformda da yayında.
5. **Tavan yükseltilmiyor, daraltılıyor.** Bugünkü kodla haftada TG 7 + BS 7 + FB 7-14 geri doldurma çıkabilir. Önerilen: haftalık TG 3, FB 2, BS 2 geri doldurma; kalan yuvalar insan emeği ve yeni şarkı için.
6. **Hedef ölçeği gerçekçi:** 90 günde Telegram 2 → 40 abone, Facebook 5 → 120 takipçi, Bluesky +100 takipçi. Yalnız organik yollar.

---

## 1. Ortak zemin (bugünkü veri)

### 1a. Gönderi envanteri [D] (state'ler, 13 Eyl 10:07)

Uygun katalog = public ve yayına uygun 17 şarkı. Hariç tutulanlar: `Bu Gece Kazandık` (`yayin_beklet`) ve `Yeniden Doğacağım` (`kopya_notu`). Buna ek olarak 2 DJ seti ve 1 derleme var.

| Platform | Yayında | Planlı / belirsiz | Eksik şarkı | Son gönderi | Kaynak |
|---|---|---|---|---|---|
| **Telegram** | **5**: Yeraltı (uzun, msg 3), Just Relax / City Pulse / Gece Seansı (dikey, msg 5-7), Sofraya Gelmedin (uzun, msg 8) | **1 belirsiz:** Kader Ortakları (12 Eyl 22:07, bağlantı gövdeden sonra koptu) | **15** (log: "15 şarkı hâlâ eksik") | 12 Eyl 06:48 | state + `auto_process.log` |
| **Facebook** | **7 Reels**: Yeraltı, Just Relax, City Pulse, Beni Bırakma, Gece Seansı, Sofraya Gelmedin, Gece Sürüşü | **2 planlı, ikisi de 13 Eyl 12:00:** Kader Ortakları, Sabah Senin | **11** | 12 Eyl 13:05 | state |
| **Bluesky** | **7 video**: Yeraltı, Just Relax, City Pulse, Beni Bırakma, Gece Seansı, Sofraya Gelmedin, Kader Ortakları | — | **13** | 12 Eyl 22:07 | state |

- Telegram mesaj numaraları 3, 5, 6, 7, 8. **4 numara state'te yok** (test ya da silinmiş olabilir; doğrulanmadı).
- `Beni Bırakma` ve `Yeraltı`'da `facebook_cope_tasindi` var: eski Reels id'leri 11 Eyl'de "çöpe taşındı". Facebook'ta gerçekten kalkıp kalkmadıkları **doğrulanmadı**.
- Otomasyon (CLAUDE.md, 13 Eyl'den beri):
  - **Facebook** ana hatta. Native planlama yapıyor, Reels 45 sn dikey, YouTube linki ilk yorumda.
  - **Telegram ve Bluesky** yalnız `upload/ek_platform_backfill.py` ile gönderiyor. Kapılar: golden-hour, günlük tavan 1, politika, public anı. Sıra: yeni public şarkı önde.
  - `facebook_backfill` günlük tavanı 2.
  - Telegram yayını 16:9 **uzun** (tam şarkı; setlerde dikey). Linkler metin içinde.
  - Bluesky yayını dikey video, `langs` dolu, facet'li hashtag ve link. **Alt metin yok.**

### 1b. Kurallarla çelişen desenler [D]

| # | Ne oldu | Hangi kurala aykırı | Durum |
|---|---|---|---|
| P1 | 11 Eyl 07:57-07:59: 2 set × BS/TG/FB = **2 dk'da 6 olay** | Toplu yükleme (R2), inauthentic deseni | Geçmiş |
| P2 | 11 Eyl 18:13-18:16: Beni Bırakma BS + Gece Seansı FB/TG/BS = 3 dk'da 4 olay | R2 | Geçmiş |
| P3 | 12 Eyl 06:48:23-06:48:56: **Sofraya Gelmedin FB + TG + BS, 33 sn.** TG/BS golden-hour dışında | R3 (aynı gün ≤2 platform), golden-hour | Geçmiş (13 Eyl düzeltmesinden önce) |
| P4 | 12 Eyl 22:06-22:07: Kader FB (planlı) + TG (belirsiz) + BS. 22:07 pencere dışı | R3, golden-hour | Geçmiş, **TG belirsizliği açık** |
| P5 | **13 Eyl 12:00: Facebook'ta iki Reels aynı dakikaya planlı** (Kader + Sabah Senin). `facebook_backfill` 12:05'te günlük sayacı 1 görebilir (bugün damgalı yalnız Sabah Senin'in `uploaded_at`'i), yani **üçüncü** bir katalog Reels'i de atabilir | R2 (24 sa'te 1, ≥6 sa) | **BUGÜN** |
| P6 | **13 Eyl Sabah Senin:** YouTube uzun + Shorts 12:00, FB 12:00, IG drain, TG/BS geri doldurma ("yeni public önde") 12:05 → aynı gün **5-6 yüzey** | R3 | **BUGÜN** |
| P7 | `City Pulse Set` (`telif_eser`: "Bring Me To Life") FB/TG/BS'de yayında. Bugünkü politika kapısı `telif_araliklari`'yı dışlıyor ama 11 Eyl gönderileri duruyor | Meta Müzik Yönergeleri, Rights Manager eşleşme riski | Açık |
| P8 | Eski 7 Facebook gönderisinde AI beyan satırı yok. Satır yalnız 13 Eyl'den sonraki yeni gönderilere giriyor; Sabah Senin FB açıklamasında olup olmadığı **doğrulanmadı** | Meta "AI info" | Açık (geriye dönük değişiklik yok kararı) |

### 1c. Konumlandırma (özet)

| Platform | Rol | Kime | Ne zaman (merdiven) | Neden bu rol |
|---|---|---|---|---|
| **Telegram** | **Stüdyo defteri + ilk duyuru** | Zaten bizi bilen sadık dinleyici | **Gün 0**, YouTube public anından sonraki ilk pencere | Öneri algoritması yok; dağıtım aboneye gider [R]. Keşif kaybı yok, değer derinlikte: tam şarkı, söz hikâyesi, defter fotoğrafı. Link cezası yok. 1000 aboneye kadar gelir kapısı kapalı, bu yüzden hedef sadakat |
| **Facebook** | **Türkçe geniş kitle + Reels vitrini** | TR'de 25-45+ yaş, duygusal/akustik/arabesk dinleyen kitle ([İ], yaygın gözlem) | **Gün 2** (T0+48 sa) | Takipçi dışına öneri yapan tek ek platform (Reels). Ama Mart 2026 orijinallik politikası ve Müzik Yönergeleri [R] "yalnız şarkı dinletme" içeriğini cezalandırıyor. İnsan emeği Reels'i burada en çok işe yarar |
| **Bluesky** | **Yaratıcı topluluğu + keşif akışları** | Müzisyen/yazar/tasarımcı, TR + uluslararası | **Gün 3** (T0+72 sa) | Kronolojik akış + özel akışlar [R]. Metin ağırlıklı, alt metin kültürü güçlü. AI içeriğe karşı hassas bir topluluk ([İ]) → süreç anlatan Kulis içerikleri burada en güvenli ve en değerli format |

**Tekrarı önleyen kural:** aynı dosya üç platforma aynı metinle gitmez.
- **Telegram:** tam şarkı (16:9) + hikâye paragrafı.
- **Facebook:** 45 sn Reels + soru + AI beyan satırı + ilk yorumda link.
- **Bluesky:** dikey kesit + 300 grafemlik kişisel cümle + alt metin.

### 1d. Yeni şarkı merdiveni (öneri, Karar 1)

| Gün | Platform 1 | Platform 2 | Bu belgenin sorumluluğu |
|---|---|---|---|
| **Gün 0** (T0 = YouTube uzun public) | YouTube uzun | **Telegram** (T0 + 5 dk … 2 sa, aynı pencere) | Telegram |
| Gün 1 | YouTube Shorts (özgünlük R3: T0+24 sa) | Instagram Reels | — |
| **Gün 2** | TikTok (elle Planla) | **Facebook Reels** (native planlama, T0+48 sa, golden-hour) | Facebook |
| **Gün 3** | **Bluesky** (T0+72 sa, golden-hour) | (boş: türev yuvası) | Bluesky |

- **Set ↔ şarkı 48 sa** tabanı olduğu için iki yeni yayının merdivenleri üst üste binebilir. Kural **şarkı başına** "gün başına ≤2 platform"; **platform başına** "gün başına ≤1 gönderi". İkisi birlikte uygulanır.
- İnsan emeği sürümleri (Söz Defteri/Kulis) ilgili şarkının o günkü platform sayısına **dahildir**.

---

## 2. TELEGRAM

### 2.1 Mevcut durum

| Alan | Değer | Kaynak |
|---|---|---|
| Kanal | "Famous Music Studio", herkese açık, `t.me/hermes_famous_asistan`, id `-1004337174284` | hafıza + state |
| Abone | **2** | görev tanımı (13 Eyl elle) |
| Gönderi | 5 kesin + 1 belirsiz (§1a) | state |
| Bot | `@hermes_famous_bot` ("Hermes asistan"). **Hermes gateway ile ortak**; kanal yayını yalnız `sendVideo`. `getUpdates` ve webhook **YASAK** | hafıza, görev |
| Yapılandırma | `chat_id` **sayısal** (`-100…`) → kullanıcı adı değişince otomasyon **kırılmaz** | `upload/telegram_client_secrets.json` (yalnız tip okundu) |
| Otomasyon | `ek_platform_backfill`: günde 1, golden-hour, yeni public önde, DJ/derleme dikey sapması, 50 MB ön kontrol. Metin: `build_caption` + "🎧 Şarkının tamamı YouTube'da: youtu.be/…". AI beyanı yok (karar) | kod |

**Eksikler ve hatalar**
- **T-H1:** Kanal açıklaması **yanlış YouTube kanalına** (`@famousmusicstudio`) yönlendiriyor. Doğrusu `youtube.com/@Famous_musics_studio` (`docs/index.html`).
- **T-H2:** Kullanıcı adı `hermes_famous_asistan` marka dışı ve iç araç adını (Hermes) dışarı sızdırıyor. Sitede iki yerde bu link var (`docs/index.html:217`, `docs/latest.html:158`).
- **T-H3:** `Kader Ortakları` gönderisi belirsiz (`yukleme_belirsiz.telegram_message_id`). Kanal elle kontrol edilmedikçe durum bilinmez. Elle **yeniden gönderilirse kopya riski** var.
- **T-H4:** Caption'da şarkıya özel bir cümle yok; TikTok/IG ile aynı `build_caption` şablonu. Telegram'ın "defter" rolüne uymuyor.
- **T-H5:** Sabitlenmiş tanıtım mesajı, tartışma grubu ve tepkiler: durumları **bilinmiyor** (API'ye bakılmadı).
- **T-H6:** Aynı bot hem asistan hem yayıncı. Bugün çakışmıyor ama bot token'ı iptal edilirse ikisi birden düşer. Kanal gönderileri Hermes'e de ulaşıyor (yok sayılıyor).

### 2.2 Güncel resmî kurallar ve fırsatlar

| Konu | Kural / olgu (alıntı ≤15 kelime) | Bizim için anlamı | Kaynak |
|---|---|---|---|
| Kanal ve grup | "a channel can have an unlimited number of subscribers". Kanala tartışma grubu bağlanabilir | Kanal doğru yapı. Tartışma grubu yorum düğmesi açar ama moderasyon ister (spam botları). **Öneri: 40 aboneye kadar grup yok, tepkiler açık** | [R] telegram.org/faq_channels |
| İlk 200 davet | Sahip ilk 200 kişiyi kendisi davet edebilir | Tanıdık dinleyicileri tek tek davet etmek mümkün ama **toplu davet spam gibi görünür**. Yalnız gerçekten dinleyen tanıdıklar | [R] telegram.org/faq |
| Keşif | Aramada herkese açık kanallar çıkar. "Benzer kanallar": "selected automatically based on similarities in their subscriber bases" | Kanal adı ve kullanıcı adı **aranabilir kelime** içermeli ("famous music"). Benzer kanal listesine girmenin eşiği yazmıyor; 2 aboneyle abone örtüşmesi oluşmaz | [R] telegram.org/blog/similar-channels, core.telegram.org/api/recommend |
| Kullanıcı adı | "a-z, 0-9 and underscores. Usernames are case-insensitive" | Önerilen ad: `famousmusicstudio` (TikTok ve FB önerisiyle aynı). Doluysa `famousmusicstudio_tr`. **Eski adın ne zaman serbest kalacağı resmî metinde yok.** Eski link hemen kırılır; site iki yerde güncellenmeli | [R] telegram.org/faq |
| Fragment | Kanal bir normal ad + koleksiyon adları alabilir; normal ad açık artırmayla satılabilir | Gerek yok. **Ad satın alma yok** | [R] fragment.com/about |
| Reklam geliri | "public channels with at least 1000 subscribers can be rewarded" (%50, TON) | 1000 aboneye çok uzağız. Plan dışı | [R] telegram.org/blog/monetization-for-channels |
| Türkiye | "may be partially or fully unavailable to certain … geographical regions" | Türkiye uygunluğu **resmî olarak doğrulanmadı** | [R] telegram.org/tos/content-creator-rewards |
| Stars | Star tepkilerinin %100'ü kanala. Aylık Stars aboneliği var. Ücretli medya yalnız foto/video (ses değil) | 90 gün içinde **açılmaz.** Tek kişilik küçük kanalda ücretli içerik sadakati bozar. Çekim 2FA ve TON cüzdanı ister | [R] telegram.org/blog/superchannels-star-reactions-subscriptions, core.telegram.org/api/stars |
| Bot sınırları | "send files of any type of up to 50 MB in size". Caption "0-1024 characters". Gruplara dk'da 20 mesaj | Şarkı 16:9 dosyaları 8-21 MB, sorun yok. Setler 254-540 MB olduğu için **dikey** gidiyor (doğru). Hikâye paragrafı 1024 karakter sınırına sığmalı | [R] core.telegram.org/bots/api (Bot API 10.3, 24 Ağu 2026), core.telegram.org/bots/faq |
| Bot yetkisi | Kanala gönderi için bot admin olmalı | Mevcut: `can_post_messages: True`. Açıklama ya da ad değişikliği bota **yaptırılmaz** (Hermes ortak botu, gereksiz yetki) | [R] core.telegram.org/bots/features |
| Otomatik gönderi | ToS: "Use our service to send spam or scam users." Otomatik gönderi için ayrı madde yok | Günde 1 gönderi spam değil. Risk Telegram'dan değil, **kanal geneli desenden** geliyor (§1b) | [R] telegram.org/tos |

### 2.3 Konumlandırma
**Telegram = "Stüdyo defteri".** Abone bir şarkıyı **ilk burada** duyar, tamamını burada dinler, nasıl yazıldığını burada okur.
- **Neden ilk duyuru:** algoritma olmadığı için erken paylaşım kimsenin keşfini bozmaz. Küçük ama sadık bir kitleye T0 anında haber vermek YouTube'un ilk saatlerine gerçek dinleyici getirir.
- **Neden defter:** metin + fotoğraf formatı Telegram'da doğal. Söz Defteri'nin **yazılı** hâli ("eski dize → yeni dize → neden") burada videodan daha iyi okunur.
- **Ne yapmaz:** keşif için hashtag yığını, Reels kopyası, tekrar gönderi.

### 2.4 İçerik formatları ve haftalık ritim

| Format | İçerik | Otomatik mi | Sıklık | Tavan |
|---|---|---|---|---|
| **T0 duyurusu** | 16:9 tam şarkı + 1-2 cümle hikâye (O-T1 sonrası) + YouTube linki | **Otomatik** (`ek_platform_backfill`, yeni public önde) | Yeni şarkı başına 1 | Günlük 1 |
| **Söz Defteri (yazılı)** | Defter fotoğrafı + "eski dize / yeni dize / neden" (3-5 satır) + soru | **Elle** (kullanıcı, uygulamadan) | Haftada 1, TikTok'tan ≥24 sa sonra | Günlük 1'e dahil |
| **Katalog geri doldurma** | Eksik 15 şarkı | Otomatik | **Önerilen haftada 3** (bugün 7) | Karar 2 |
| **E9 hatırlatma** (türev) | Metin + link + soru, video yok | Koşullu (D+7 "aç") | Şarkı başına ≤1 | Günlük 1'e dahil |
| **Ayın notu** | Ayda 1 "bu ay stüdyoda": yayınlar, bir reddedilen taslak, sonraki ay | Elle | Ayın son Pazarı | Günlük 1'e dahil |

- **Metin kuralları:**
  - "Suno" geçmez; AI beyan satırı yok (karar).
  - Söz Defteri'nde "biz" dili kullanılır (paketteki dürüstlük notu: yazım yardımcısı + insan seçimi).
  - Emoji en fazla 1; hashtag en fazla 2.
- **Elle gönderi günü** geri doldurma o platformda çıkmamalı. Bugünkü kod bunu bilmiyor (O-T3); bu hafta kod değişmezse o gün 2 gönderi olur. Telegram'da algoritma olmadığı için **kabul edilebilir**; elle gönderi 12:05 geri doldurmasından ≥6 sa sonra atılır.

### 2.5 Büyüme hedefleri (yalnız organik)

| Metrik | Bugün | 30 gün (11 Eki) | 60 gün (8 Kas) | 90 gün (13 Ara) | Nereden |
|---|---|---|---|---|---|
| Abone | 2 | 12 | 25 | 40 | Kanal bilgisi (elle) |
| Gönderi başına görüntülenme (medyan) | bilinmiyor | ≥ abone × 1,5 | ≥ abone × 1,5 | ≥ abone × 1,5 | Gönderideki göz sayacı (elle; Bot API okuyamaz) |
| Tepki / gönderi | bilinmiyor | ≥1 | ≥2 | ≥3 | Gönderi altı (elle) |
| Söz Defteri (yazılı), toplam | 0 | 4 | 8 | 12 | `elle_islemler.jsonl` |

**Organik yollar:**
1. Sitedeki link: kullanıcı adı düzelince aranabilir olur.
2. YouTube kanal "bağlantılar" alanına Telegram (Studio, elle; YouTube'da kalıcı onay var).
3. Instagram/TikTok bio'sunda **tek** link sitede kalır, Telegram site üzerinden gelir.
4. Ayda 1 YouTube Topluluk gönderisinde "Söz defterinin yazılı hâli Telegram'da" satırı.
5. Tanıdık dinleyicilere birebir davet (toplu değil).

**Yok:** abone satın alma, "abone ol, şarkı kazan" çekilişi, kanal takası, bot davet.

### 2.6 Düzeltmeler

| # | Düzeltme | Kim | Onay | Not |
|---|---|---|---|---|
| T-D1 | **Kanal açıklaması:** yanlış YouTube linki → `youtube.com/@Famous_musics_studio` + tek satır rol: "Yeni şarkılar ilk burada · söz defteri · famousmusicstudio.com". "Suno" yok, AI satırı yok | **Kullanıcı** (Telegram uygulaması, 1 dk) | Kullanıcının kendisi | Claude: Telegram Web Chrome'dan teknik olarak mümkün ama **kalıcı onay yok**; açık onay gerekir. Bot API ile (`setChatDescription`) **yapılmaz** (ortak bot) |
| T-D2 | **Kullanıcı adı:** `hermes_famous_asistan` → `famousmusicstudio` (doluysa `famousmusicstudio_tr`) | **Kullanıcı** | Kullanıcı | Aynı saatte `docs/index.html` + `docs/latest.html` linki (web bölümü sahibi ajan) ve `marka/` metinleri. `chat_id` sayısal olduğu için otomasyon etkilenmez. **Eski link anında kırılır** |
| T-D3 | **Kader Ortakları belirsizliği:** kanalda son mesajlara elle bak. Gönderi varsa state'e işaretleme ana oturumun işi (`elle_islem` + state CLI); yoksa belirsiz işareti kaldırılır, geri doldurma yeniden dener | **Kullanıcı** bakar, ana oturum işler | State yazımı için onay | `getUpdates` ile bakılmaz |
| T-D4 | Sabitlenmiş tanıtım mesajı: "Burada ne var" (3 satır) | Kullanıcı | — | T-D1'den sonra |
| T-D5 | Kanal fotoğrafı logo mu? Tepkiler açık mı? | Kullanıcı bakar | — | Bilinmiyor |

### 2.7 Otomasyon değişiklik önerileri (KOD YOK)

| # | Öneri | Dosya | Risk | Test |
|---|---|---|---|---|
| **O-T1** | **Şarkıya özel kısa hikâye:** `meta["hikaye"]` (özgünlük planı 1.3 alanı) varsa ilk 1-2 cümlesi caption'ın başına; yoksa bugünkü çıktı bayt bayt aynı. "Suno"/"yapay zeka"/"AI" geçen hikâye reddedilir. 1024 sınırında önce hashtag kırpılır, hikâye ve link korunur | `upload/telegram_upload.py` (`_build_telegram_caption`) | Düşük. Tek risk sınırı aşan metin (kırpma zaten var) | `tests/test_telegram_caption_hikaye.py`: alan yok → eski çıktı · yasaklı kelime → red · 1024 sınırı → link korunur |
| **O-T2** | **Merdiven gecikmesi:** platform başına "public anından sonra en erken" alanı; TG 0 sa, BS 72 sa | `upload/ek_platform_backfill.py` (`_public_ani` çevresi), `config.py` (ör. `EK_PLATFORM_GECIKME_SAAT`) | Orta: aday sırası değişir. "Yeni public önde" kuralı gecikmeyle birlikte test edilmeli | Fikstür: 13 Eyl Sabah Senin deseni → TG 12:05 geçer, BS 16 Eyl'e kadar red |
| **O-T3** | **Elle gönderi rezervasyonu:** `kanal_takvimi.json`'da o gün o platforma planlı insan emeği gönderisi varsa geri doldurma o gün çıkmaz. Türev damgaları (`telegram_turev_uploaded_at`) `bugun_yuklenen` sayacına girer (takvim planı §4b) | `upload/ek_platform_backfill.py`, `turev_takvimi.py` | Orta: takvim dosyası bozuksa uyarı yazılır ve bugünkü davranış sürer (kuyruk tıkanmasın) | Planlı gün → 0 gönderi · bozuk JSON → uyarı + 1 gönderi |
| **O-T4** | **Haftalık tavan** (Karar 2): Telegram 3 / Bluesky 2, kayan 7 gün; yeni public şarkı ve türevler muaf | `upload/ek_platform_backfill.py`, `config.py` | Düşük (daraltır). `saglik_kontrol` durgunluk alarmı eşiği gözden geçirilmeli | 7 günde 3 → 4.'sü red; yeni public şarkı geçer |
| O-T5 | (Uzun vade) **Ayrı yayın botu:** kanal yayını Hermes botundan ayrılır | `upload/telegram_client_secrets.json` (kullanıcı), kod değişmez | Düşük-orta: kullanıcı BotFather + admin ekleme yapar; token dosyası değişir | `--dry-run` + tek gönderi. `getUpdates` yine yok |

---

## 3. FACEBOOK

### 3.1 Mevcut durum

| Alan | Değer | Kaynak |
|---|---|---|
| Sayfa | "Famous Music Studio", id `61593802007949` | görev |
| Takipçi | **5** | görev (13 Eyl elle) |
| Kullanıcı adı | **Şu an başka bir ajan alıyor**. `marka/facebook_metinleri.txt` önerisi: `famousmusicstudio` | görev, marka |
| Gönderi | 7 Reels yayında + 2 planlı (§1a) | state |
| Kapak | `marka/facebook_kapak.png` 12 Eyl'de yüklendi | `buyume_kontrol_listesi.md` E-15 |
| Token / izin | `pages_manage_posts`, `pages_manage_engagement`, `pages_read_engagement`, `pages_read_user_content`; veri erişimi ~88 gün (≈9 Ara) | `upload/facebook_veri_erisimi.json` |
| Otomasyon | Ana hat: `facebook_upload.upload_reels`, native planlama (`next_golden_publish_time`), ilk yorumda YouTube linki (`facebook_comment_pending` akışı). `facebook_backfill`: günde 2, golden-hour. AI beyan satırı yeni açıklamalarda (13 Eyl kararı) | kod, CLAUDE.md |

**Eksikler ve hatalar**
- **F-H1:** 13 Eyl 12:00'de **iki Reels aynı dakikada**, üstüne 12:05'te olası geri doldurma (P5).
- **F-H2:** Sabah Senin Reels'i YouTube ile **aynı an** (T0) planlı. Merdivenle çelişiyor (P6).
- **F-H3:** `marka/facebook_metinleri.txt` kararla çelişiyor:
  - "Yapay zekâ ile üretilen orijinal müzik" ve "Tüm içerik yapay zekâ ile üretilmiştir": sözler insan yazımı; karar dili "AI destekli".
  - "arabesk, hiphop ve elektronik": katalogda rock, pop, akustik de var.
  - Sayfaya yüklenip yüklenmediği **bilinmiyor**.
- **F-H4:** `City Pulse Set` Reels'i telif eşleşmeli bir set (P7). Meta'da Rights Manager eşleşmesi sayfaya uyarı getirebilir.
- **F-H5:** Sitede Facebook linki **yok** (kullanıcı adı bitince eklenmeli).
- **F-H6:** Etkileşim hiç ölçülmüyor. İzin var (`pages_read_engagement`) ama okuyan kod yok.
- **F-H7:** Eski 7 gönderide AI satırı yok. Karar gereği geriye dönük değişmez; not olarak kalır.

### 3.2 Güncel resmî kurallar ve fırsatlar

| Konu | Kural / olgu (alıntı ≤15 kelime) | Bizim için anlamı | Kaynak |
|---|---|---|---|
| Sayfa ve profesyonel mod | Sayfa marka ya da işletme içindir; profesyonel mod kişisel profili geniş kitleye açar | **Sayfa doğru.** Kişisel profil kullanılmaz (gerçek kimlik, gizlilik) | [R] facebook.com/help/203141666415461 |
| Reels | "Reels on Facebook will also not have any length or format restrictions" (Haziran 2025) | 45 sn dikey uygun. Söz Defteri çekimi (35-45 sn) doğrudan Reels olur. Asgari süre ve oran için resmî gereksinim sayfası **okunamadı** | [R] about.fb.com/news/2025/06 |
| Orijinallik (Mart 2026) | Yeniden yükleme ya da "minor edits to another creator's post" orijinal sayılmaz; ağırlıktaysa öneri ve para kazanma kapanır | Kendi şarkımız "başkasının içeriği" değil. Ama **aynı şablondan seri Reels** (aynı kapak düzeni + aynı metin kalıbı) "tekrarlayan" okunabilir. **İnsan emeği Reels'i oranı önemli** | [R] about.fb.com/news/2026/03/rewarding-original-creators-on-facebook, facebook.com/business/help/262834734651607 |
| AI info | Meta, AI izi tespit edince ya da "when people disclose that they're uploading AI-generated content" etiket koyar | Açıklama satırı (karar) kalır. "Gerçekçi ses" için **araçla beyan zorunluluğu** resmî metinden bu turda **okunamadı** ([İ]). AI vokal "gerçekçi ses" sayılabilir → **Karar 4** | [R] about.fb.com/news/2024/04, transparency.meta.com/governance/tracking-impact/labeling-ai-content |
| Planlama | Sayfa gönderileri "20 dakika ile 29 gün arasında" planlanabilir | Business Suite'ten Söz Defteri Reels'i Perşembe dağıtım vardiyasında planlanır. API planlaması zaten var | [R] facebook.com/help/389849807718635 |
| Müzik Yönergeleri | "içeriğin asıl amacı ses kaydı olmamalıdır"; görsel bileşen şart | **En önemli kural.** Durağan kapak + tam şarkı **riskli** → Facebook'ta 16:9 uzun format **açılmaz**; Reels'te hareket ve söz kartı kalır. İnsan emeği Reels'i (defter, eller, ses) doğrudan uyumlu | [R] facebook.com/legal/music_guidelines |
| Rights Manager | Hak sahipliğini kanıtlayana verilir; sayfa adminleri başvurabilir; 3 red sonrası 60 gün | **Başvurma (90 gün içinde yok).** AI müzikte hak kanıtı üretim aracının plan lisansına bağlı; City Pulse eşleşmesi çıktıların başkasının eseriyle eşleşebildiğini gösterdi. Red sayacı riski | [R-özet] facebook.com/business/help/705604373650775 |
| Para kazanma | Facebook Content Monetization tek programda birleşti. Türkiye ülke listesi **okunamadı** ([İ] Aralık 2025 listelerinde var) | 5 takipçiyle plan dışı. 60. gün Profesyonel Pano → Para kazanma ekranına **yalnız bakılır** | [R] creators.facebook.com/introducing-facebook-content-monetization |
| Instagram çapraz paylaşım | Aynı Hesaplar Merkezi şart; FB → IG reel yalnız mobilden, oluştururken | **Otomatik çapraz paylaşım KAPALI olmalı.** Otomasyon iki platforma ayrı yüklüyor; açık olursa aynı Reels iki kez çıkar (P1 sınıfı) | [R] facebook.com/help/932731427414654, help.instagram.com/459497729122868 |
| Otomasyon / spam | Spam: "either manually or automatically, at very high frequencies" | Günde ≤1 Reels "yüksek sıklık" değil. Asıl risk P5 gibi aynı dakika kümeleri | [R] transparency.meta.com/policies/community-standards/spam |

### 3.3 Konumlandırma
**Facebook = "Türkçe vitrin".** Merdivende **Gün 2**. YouTube ve Telegram'daki ilk dinleyiciden sonra geniş Türkçe kitleye Reels ile gider.
- **Neden geniş kitle:** üç platform içinde takipçi dışına öneri yapan tek yüzey (Reels). TR'de Facebook kullanıcıları duygusal/akustik/arabesk tarzlara yakın [İ].
- **Neden Gün 2:** YouTube'la aynı anda çıkmak (bugünkü davranış) R3'e aykırı. 48 saatlik aralık iki kitleyi farklı günlerde yakalar.
- **Ne yapmaz:** tam şarkı dinletme (Müzik Yönergeleri), kanal geneli duyuru yığını, sayfa dışı gruplara paylaşım.

### 3.4 İçerik formatları ve haftalık ritim

| Format | İçerik | Otomatik mi | Sıklık | Not |
|---|---|---|---|---|
| **Yeni şarkı Reels** | 45 sn dikey + hook + soru + AI beyan satırı + hashtag; YouTube linki ilk yorumda | **Otomatik** (native planlama; O-F1 sonrası T0+48 sa) | Yeni şarkı başına 1 | Bu hafta O-F1 yoksa: Business Suite'ten elle erteleme (Karar 1) |
| **Söz Defteri Reels** | TikTok çekiminin **aynısı**, yeni açıklama (Facebook kitlesine soru). Şarkı kesiti içeriyorsa AI beyan satırı | **Elle** (Business Suite planla) | Haftada 1, TikTok'tan ≥48 sa sonra | İnsan emeği; Müzik Yönergeleri açısından en güvenli format |
| **Kulis (fotoğraf/karusel)** | Kapak seçimi: reddedilen ve seçilen görsel + 3 cümle | Elle | 2 haftada 1 | Bluesky Kulis'iyle **aynı gün değil** |
| **Katalog geri doldurma** | 11 eksik şarkı | Otomatik | **Önerilen haftada 2** (bugün ≤14) | Karar 2 |
| **Yorum sohbeti** | Her Reels'in ilk 24 sa'inde elle yanıt; aynı cümle iki kişiye yazılmaz | Elle (Business Suite gelen kutusu) | Günlük 5 dk | Otomatik yanıt **yok** |

### 3.5 Büyüme hedefleri (yalnız organik)

| Metrik | Bugün | 30 gün | 60 gün | 90 gün | Nereden |
|---|---|---|---|---|---|
| Takipçi | 5 | 30 | 60 | 120 | Profesyonel Pano (elle) |
| Reels medyan izlenme (gönderi başına) | **bilinmiyor** | ilk okuma = temel çizgi | temel × 1,5 | temel × 2 | Business Suite → İçerik |
| İnsan emeği Reels oranı | %0 | ≥%20 | ≥%25 | ≥%25 | `elle_islemler.jsonl` |
| Yorum yanıt oranı | — | ≥%90 | ≥%90 | ≥%90 | Elle |
| Aynı gün 2+ Reels | 13 Eyl'de 2-3 | 0 | 0 | 0 | state damgaları |

**Organik yollar:**
1. Sitede Facebook linki (kullanıcı adı bitince).
2. Sayfa "Hakkında" düzeltmesi (F-D2).
3. Söz Defteri Reels (insan emeği → orijinallik sinyali).
4. Yorumlara hızlı yanıt.
5. Instagram profilinde "Facebook" bağlantısı (Hesaplar Merkezi; çapraz paylaşım kapalı).

**Yok:** beğeni/takipçi satın alma, "sayfayı beğen" davet yığını, grup spam'i, reklam (90 gün).

### 3.6 Düzeltmeler

| # | Düzeltme | Kim | Onay | Not |
|---|---|---|---|---|
| F-D1 | **Bugün 12:00'den önce (mümkünse):** Business Suite → Planlanan içerik → `Sabah Senin` Reels'i 15 Eyl 20:00'ye ertele. Kader 12:00'de kalsın | Kullanıcı ya da Claude (Chrome) | **Açık onay** (Facebook kalıcı onay listesinde değil) | 12:00 geçtiyse iş yok; §5 takvimi buna göre kayar. `facebook_comment_pending` akışı yayın anını beklediği için yorum gecikir ama bozulmaz ([D] `_finalize`); yine de ertesi koşu log'u kontrol edilir |
| F-D2 | **Sayfa metni:** "Hakkında" → "Sözler bizden, müzik ve vokal AI destekli. Her hafta yeni şarkı." Uzun açıklamada tür listesi "pop, rock, akustik, arabesk, hiphop, elektronik"; "Tüm içerik yapay zekâ ile üretilmiştir" yerine karar satırı: "Söz: Famous Music Studio · Müzik ve vokal: AI destekli". Önce `marka/facebook_metinleri.txt` (ana oturum), sonra sayfa | Dosya: ana oturum · Sayfa: kullanıcı ya da Claude (Chrome) | Sayfa değişikliği için **açık onay** | Karar 4 |
| F-D3 | **Kullanıcı adı:** başka ajan bitirince sitede Facebook linki ve TikTok/YouTube bağlantı alanları | Web ajanı + kullanıcı | — | Çakışma olmasın diye bu belge kullanıcı adına dokunmaz |
| F-D4 | **Instagram çapraz paylaşım:** Hesaplar Merkezi → "Reels'i Facebook'ta paylaş" **kapalı** mı? | Kullanıcı bakar; kapatma Claude (Chrome) | Açık onay | Açıksa çift Reels |
| F-D5 | **City Pulse Set Reels'i:** "Yalnız ben" ya da sil | Kullanıcı | Açık onay | Karar 6 |
| F-D6 | **Eski kopya Reels:** `facebook_cope_tasindi` kayıtlarındaki eski id'ler (Beni Bırakma, Yeraltı) sayfada görünüyor mu? | Kullanıcı bakar | — | Görünüyorsa aynı şarkı iki kez yayında |
| F-D7 | Veri erişimi yenilemesi ≈ 9 Ara | Kullanıcı (`facebook_auth.py`) | — | Zaten izleniyor (B3) |

### 3.7 Otomasyon değişiklik önerileri (KOD YOK)

| # | Öneri | Dosya | Risk | Test |
|---|---|---|---|---|
| **O-F1** | **Merdiven planlaması:** yeni şarkıda `scheduled_publish_time` = YouTube T0 + 48 sa sonrası ilk golden-hour yuvası (29 gün sınırı içinde). Geri doldurmada değişiklik yok | `upload/facebook_upload.py` (`_compute_scheduled_time`), `config.py` | Orta: YouTube T0 bilinmiyorsa (`publishAt` yok) bugünkü davranışa dön. `facebook_comment_pending` akışı gelecekteki yayını zaten destekliyor | Fikstür Sabah Senin: T0 13 Eyl 12:00 → 15 Eyl 12:00 · T0 yok → şimdiki yuva |
| **O-F2** | **Platform başına 24 sa / ≥6 sa kapısı** (R2): ana hat + geri doldurma **aynı sayaçla**. Sayaç `uploaded_at` değil **yayın anı** (`facebook_scheduled_for`) üzerinden sayar; P5'in kök nedeni bu | `upload/facebook_backfill.py` (`bugun_yuklenen`), `yayin_ritmi.py` (özgünlük 1.2) | Orta: yanlış sayaç kuyruğu tıkar; R2 **düşürmez, sıraya koyar** | 13 Eyl deseni: 12:00'ye 2 planlı → 3.'sü red, 2.'si 18:00'e kayar |
| O-F3 | **Haftalık tavan 2** (Karar 2), yeni şarkı muaf | `upload/facebook_backfill.py` | Düşük | 7 günde 2 → 3.'sü red |
| O-F4 | **Reels açıklamasına hikâye cümlesi** (`meta["hikaye"]` ilk cümle). AI satırı ve hashtag sırası değişmez | `upload/social_text.py` (`build_caption` platform dalı) | Orta: `build_caption` ortak fonksiyon, TikTok/IG/TG/BS etkilenmemeli (13 Eyl yarım düzenleme dersi) | Diğer platform çıktıları bayt bayt aynı · `tests/test_ai_beyan_satiri.py` yeşil |
| O-F5 | **Salt okunur ölçüm:** haftada 1 Reels başına izlenme ve izleme süresi, takipçi → rapora satır | `weekly_report.py` (yeni fonksiyon) | Düşük: mevcut izin yeterli ([D] izin listesi) | Sahte yanıt fikstürü; token yoksa UYARI, sessiz değil |
| O-F6 | `telif_eser` ya da `telif_araliklari` taşıyan proje Meta'ya **hiç** gitmesin (ana hat dahil) | `auto_process.py` (`_EK_PLATFORMLAR` döngüsü), `dj_famous_process.py` | Düşük | City Pulse fikstürü → FB adımı atlanır, log satırı var |

---

## 4. BLUESKY

### 4.1 Mevcut durum

| Alan | Değer | Kaynak |
|---|---|---|
| Hesap | `famousmusicstudio.bsky.social`, did `did:plc:nrovntwqdz5sbbcy7zp3qodk`, 10 Eyl'de açıldı; e-posta doğrulandı (video için şart) | hafıza |
| Takipçi | **bilinmiyor** (API'ye bakılmadı) | — |
| Gönderi | 7 video (§1a) | state |
| Profil | Banner yüklü ("Her hafta yeni şarkı") | `buyume_kontrol_listesi.md` E-15 |
| Otomasyon | `ek_platform_backfill`: günde 1. `bluesky_upload`: video.bsky.app servis yolu, PDS DID'den çözülüyor, `langs` dolu, hashtag/link facet'li, 300 grafem kırpma, kopya kontrolü (`_gonderi_zaten_var_mi`). **Alt metin yok, `tags` alanı yok**, AI satırı yok (karar) | kod |

**Eksikler ve hatalar**
- **B-H1:** Alt metin yok. Bluesky'da erişilebilirlik kültürü güçlü; alt metinsiz video topluluk içinde "otomatik hesap" gibi okunur [İ].
- **B-H2:** Metin TikTok/IG ile aynı `build_caption` şablonu (hook + soru + hashtag bloğu). Bluesky'ın konuşma diliyle uyuşmuyor ve 300 grafemin çoğunu hashtag yiyor.
- **B-H3:** Gönderiler yalnız otomatik; **tek bir yanıt, repost ya da takip kaydı yok** (state/defterde). Topluluk platformunda tek yönlü yayın büyümez.
- **B-H4:** Aynı gün FB/TG ile birlikte çıktı (P3, P4).
- **B-H5:** Handle `.bsky.social`. `famousmusicstudio.com` alan adı sitede var; alan adı handle'ı marka doğrulaması sağlar (B-D2).

### 4.2 Güncel resmî kurallar ve fırsatlar

| Konu | Kural / olgu (alıntı ≤15 kelime) | Bizim için anlamı | Kaynak |
|---|---|---|---|
| Özel akışlar | Akışa girmek akış sahibinin kuralına bağlı (anahtar kelime, hashtag, link). Örnek müzik akışı: metinde "music" geçen ya da müzik sitesine link veren gönderiler | Resmî başvuru yok. Gönderi metninde **doğal olarak** "müzik"/"music", "şarkı", tür adı ve YouTube linki geçmeli. Kelime doldurma yok | [R] docs.bsky.app/docs/starter-templates/custom-feeds; örnek akış bsky.app/profile/did:plc:ke6e3skfhjdsnky5d3ojauh3/feed/music |
| Etiketler | Metin içi hashtag + gönderi başına **en fazla 8 `tags`** (≤64 karakter), metinde görünmez | **Fırsat:** keşif etiketleri görünmez `tags` alanına, görünür metin kişisel cümleye kalır (O-B2) | [R] atproto lexicon `app/bsky/feed/post.json` |
| Self-label | Değerler: !hide, !warn, porn, sexual, nudity, graphic-media, **bot**. AI için resmî değer **yok** | "bot" etiketi **konmaz**: hesabı bir insan yönetiyor, gönderiler insan kararıyla planlanıyor. Otomatik yanıt, takip ve beğeni **yok** | [R] atproto lexicon `com/atproto/label/defs.json` |
| AI labeler | Yalnız üçüncü taraf AI labeler'ları var; kullanıcı kendisi abone olur | Kararla uyumlu: gönderide AI satırı yok. **Risk:** bir labeler hesabı etiketlerse o labeler'a abone kullanıcılarda uyarı görünür. Ölçüm günlerinde profil etiketlerine bakılır | [R-özet] bluesky-labelers.io |
| Topluluk kuralları | "Do not send spam or repeatedly post content in ways that disrupt" (19 Eyl 2025) | Günde ≤1 gönderi uygun. Aynı şablon metinle 13 şarkıyı ardı ardına basmak "tekrarlayan" okunur → haftada 2 geri doldurma | [R] bsky.social/about/support/community-guidelines |
| Rate limit | "5,000 points per hour and 35,000 points per day"; oluşturma 3 puan; oturum 5 dk'da 30, günde 300 | Hacmimizde sorun yok. Oturum saatlik koşuda **gönderi olmadan** açılmamalı (günde 300 sınırı) | [R] bsky.network/docs/rate-limits |
| Video | "May be up to 300mb, formerly limited to 100mb"; en fazla 20 altyazı; e-posta doğrulaması şart; günlük video sınırı var, sayı yok | 45 sn dikey (3-5 MB) rahat. Süre sınırı resmî olarak **doğrulanmadı** ([İ] 3 dk → 10 dk). **Söz altyazısı** fırsat | [R] atproto lexicon `app/bsky/embed/video.json`, bsky.network/docs/about-bluesky-content/video |
| Metin / görsel | 300 grafem; en fazla 4 görsel, her biri ≤2 MB; alt metin şemada sınırsız ([İ] uygulama 2000) | Kulis gönderisi: 2 görsel + alt metin. Alt metin ≤300 karakter hedeflenir | [R] lexicon `post.json` |
| Link kartı | `app.bsky.embed.external` destekli | Video gönderisinde link metin içinde kalır (tek embed). Kulis metninde link kartı kullanılabilir | [R] lexicon `post.json` |

### 4.3 Konumlandırma
**Bluesky = "süreç anlatan yaratıcı".** Merdivende **Gün 3**, en geç ve en kişisel yüzey.
- **Neden topluluk:** metin ağırlıklı, konuşma odaklı. Müzisyen, yazar ve tasarımcılar süreç paylaşımına yanıt veriyor [İ]. Kulis ("kapak nasıl seçildi", "bu dize neden değişti") burada ürün tanıtımından çok daha iyi karşılanır.
- **Neden keşif:** özel akışlar kelime ve link ile doluyor [R]. Algoritma yerine **doğru kelime + doğru topluluk.**
- **Neden Gün 3:** T0 kalabalığından uzak. Aynı hafta içinde şarkıyı farklı bir günde yeniden görünür yapar.
- **Risk notu:** Bluesky topluluğu AI içeriğe hassas [İ]. Karar gereği gönderide AI satırı yok. Bu yüzden gönderiler **şarkı hakkında insan cümlesi** taşımalı; şablon metin + video "toplu AI hesabı" algısını büyütür. Bu strateji kararı değiştirmeden riski düşürür.

### 4.4 İçerik formatları ve haftalık ritim

| Format | İçerik | Otomatik mi | Sıklık | Not |
|---|---|---|---|---|
| **Şarkı videosu** | Dikey kesit + **1 kişisel cümle** (hikâye paragrafından) + tür + YouTube linki; keşif etiketleri `tags`'te; alt metin | **Otomatik** (O-B1/O-B2/O-T2 sonrası T0+72 sa) | Yeni şarkı başına 1 | Bugün şablon metin |
| **Kulis (metin + 2 görsel)** | "Bu kapak neden seçildi / neden reddedildi" + alt metin | **Elle** (bsky.app) | Haftada 1, TikTok'tan ≥24 sa sonra | İnsan emeği |
| **Söz Defteri (metin)** | "Eski dize → yeni dize" (300 grafem) + defter fotoğrafı + alt metin | Elle | 2 haftada 1 (Telegram'la aynı gün değil) | — |
| **Topluluk etkileşimi** | Takip edilen müzisyenlere gerçek yanıt; akış keşfi | **Elle** | Günde 5-10 dk, haftada 3 gün | Gönderi değil, tavana sayılmaz. Otomatik beğeni/takip **yok** |
| **Katalog geri doldurma** | 13 eksik şarkı | Otomatik | **Önerilen haftada 2** (bugün 7) | Karar 2 |

### 4.5 Büyüme hedefleri (yalnız organik)

| Metrik | Bugün | 30 gün | 60 gün | 90 gün | Nereden |
|---|---|---|---|---|---|
| Takipçi | **bilinmiyor → 27 Eyl ilk okuma = X** | X + 25 | X + 50 | X + 100 | Profil (elle) |
| Gönderi başına beğeni + repost + yanıt (medyan) | bilinmiyor | ≥3 | ≥5 | ≥8 | Gönderi (elle) |
| Alt metinli gönderi oranı | %0 | %100 (yeni) | %100 | %100 | Elle / O-B1 |
| Verilen gerçek yanıt (hafta) | 0 | ≥10 | ≥10 | ≥15 | `elle_islemler.jsonl` |
| Müzik akışında görünme | bilinmiyor | 1 gönderi | 3 gönderi | 5 gönderi | Akış sayfası (elle bakış) |

**Organik yollar:** Kulis ve Söz Defteri metinleri, gerçek yanıtlar, alan adı handle'ı, sitedeki link, doğru kelime ve `tags`.
**Yok:** takip-geri-takip, otomatik beğeni/takip botu, starter pack'e eklenme ricası yığını, labeler'dan kaçmak için metin oyunları.

### 4.6 Düzeltmeler

| # | Düzeltme | Kim | Onay | Not |
|---|---|---|---|---|
| B-D1 | **Bio:** "Sözler bizden · her hafta yeni şarkı · famousmusicstudio.com" (araç adı yok, AI satırı yok) | Kullanıcı ya da Claude (Chrome) | **Açık onay** | Mevcut bio okunmadı |
| B-D2 | **Alan adı handle'ı:** `famousmusicstudio.com`. Bluesky ayarlarında alan adı seçeneği; doğrulama DNS TXT ya da sitede `/.well-known/atproto-did` dosyası | Site dosyası: web ajanı · ayar: kullanıcı | Açık onay | Handle değişince `bluesky_client_secrets.json`'daki `handle` güncellenmeli (ana oturum). DID değişmediği için eski gönderilerin durması beklenir ([İ], doğrulanmalı) |
| B-D3 | **Sabit gönderi:** tanıtım, Söz Defteri #1 çıktıktan sonra o gönderi | Kullanıcı | — | 15 Eyl'den sonra |
| B-D4 | Hesap etiketleri: profilde üçüncü taraf etiket görünüyor mu? | Kullanıcı bakar | — | Ölçüm günlerinde |

### 4.7 Otomasyon değişiklik önerileri (KOD YOK)

| # | Öneri | Dosya | Risk | Test |
|---|---|---|---|---|
| **O-B1** | **Alt metin:** video embed'inin `alt` alanı = "{şarkı adı}: {tür} şarkı videosu. {kapak betimi}. Söz kartları ekranda." Kapak betimi `meta`'dan ya da kapak arama sorgusundan; yoksa betimsiz kısa sürüm. "Suno" yok | `upload/bluesky_upload.py` (`upload_video`, embed kurulumu) | Düşük: alan opsiyonel. Yanlış alan adı yayını düşürür → önce `--dry-run` ile kayıt dökümü | `tests/test_bluesky_alt_metin.py`: alan dolu, ≤300 karakter, yasaklı kelime yok; meta eksik → kısa sürüm |
| **O-B2** | **Görünmez keşif etiketleri:** `DISCOVERY_HASHTAGS` görünür metinden `tags` alanına (≤8, ≤64). Görünür metinde en fazla 1 marka hashtag'i | `upload/bluesky_upload.py` (`build_post_text`, `send_post`) | Orta: `_hashtaglerden_kirp` ve facet testleri etkilenir; `tests/test_bluesky_grapheme.py` yeşil kalmalı | 8 sınırı · tekrar eleme · görünür metin ≤300 |
| **O-B3** | **Bluesky'a özel metin:** hook/soru havuzu yerine `meta["hikaye"]` ilk cümle + tür + link; hikâye yoksa bugünkü `build_caption` | `upload/bluesky_upload.py` | Orta: hikâye alanı henüz 2 projede taslak. Geri dönüş yolu şart | alan yok → eski çıktı |
| O-B4 | **Söz altyazısı** video embed'ine; kaynak YouTube altyazı hattındaki zamanlı sözler | `upload/bluesky_upload.py`, `upload/youtube_captions.py` (okuma) | Orta: zamanlama kayması | 60. gün sonrası |
| O-B5 | **Merdiven gecikmesi 72 sa + haftalık tavan 2:** O-T2 ve O-T4 ile aynı değişiklik | `upload/ek_platform_backfill.py` | bkz. O-T2/T4 | — |
| O-B6 | **Salt okunur ölçüm:** herkese açık profil ve gönderi uçları (kimliksiz) haftada 1 → rapora beğeni/repost/takipçi | `weekly_report.py` | Düşük; oturum açmaz (günde 300 oturum sınırına dokunmaz) | Sahte yanıt fikstürü |

---

## 5. Ortak haftalık takvim: 14–20 Eylül (öneri)

**Dayanaklar:**
- `kanal_takvimi.json`: Söz Defteri #1 TikTok 15 Eyl 20:30 · Topluluk 16 Eyl 20:30 · Kulis #1 TikTok 19 Eyl 13:00 · Topluluk 20 Eyl 13:00.
- `elle_islemler.jsonl`: TikTok Planla 15 Eyl 18:00 Bir Bahar Daha, 17 Eyl 18:00 Kader Ortakları.
- `yayin_sonrasi_takvim_plani.md` §5.
- **Bu Gece Kazandık T0 ≈ 15 Eyl 18:00** (Sabah Senin + ~52 sa; yeniden render yapılıp `yayin_beklet` kaldırılırsa. Kayarsa satırlar birlikte kayar).

**Varsayım:** F-D1 yapıldı (Sabah Senin FB 15 Eyl'e ertelendi). Yapılmadıysa 15 Eyl FB hücresi boşalır ve Sabah Senin FB 13 Eyl'de kalır.

| Gün | Sabit planlar (başka belgeler) | Telegram | Facebook | Bluesky | Şarkı başına kontrol (≤2 platform/gün) |
|---|---|---|---|---|---|
| **13 Paz** (bugün, bilgi) | Sabah Senin YT uzun + Shorts 12:00; Kader IG | Oto 12:05: **Sabah Senin T0** (merdivenle uyumlu) | Kader 12:00 (planlı) · Sabah Senin → F-D1 ile 15 Eyl | Oto 12:05: Sabah Senin olabilir (**merdivene aykırı; kod değişmeden engellenemez**) | Sabah Senin: YT + TG (+BS = 3 ✗, bilinen açık) |
| **14 Pzt** | 10:15 telif kontrolü · 12:00 YT Topluluk E2 (Sabah Senin) | Oto 12:05: katalog (sıradaki eksik) | — (13 Eyl çift Reels sonrası soğuma) | — | Sabah Senin: YT ✓ |
| **15 Sal** | **Bu Gece Kazandık T0 ~18:00** · TikTok Bir Bahar Daha 18:00 · **TikTok Söz Defteri #1 20:30** | Oto 18:05: **BGK T0** | **Sabah Senin Reels 20:00** (T0+56 sa; F-D1) | — | BGK: YT + TG ✓ · Sabah Senin: TikTok (SD) + FB ✓ · Bir Bahar Daha: TikTok ✓ |
| **16 Çar** | 19:00 YT Topluluk E2-DJ (Just Relax) · 20:30 YT Topluluk SD #1 | **21:15 Söz Defteri #1 yazılı** (elle: defter fotoğrafı + 3 dize) | Oto 12:05: katalog (haftanın 1.'si) | Oto 12:05: katalog (haftanın 1.'si) | Sabah Senin: YT Topluluk + TG = 2 ✓ (Sabah Senin BS'ye 13 Eyl'de çıkmadıysa 17 Eyl'e) |
| **17 Prş** | TikTok Kader 18:00 · 19:00 IG Carousel E3 (Sabah Senin) · dağıtım vardiyası (15-25 dk) | — (T-D3 Kader kanal kontrolü, elle) | **BGK Reels 20:00** (T0+50 sa; bugünkü kod T0'da planlarsa Business Suite'ten ertele, açık onay) | (13 Eyl'de çıkmadıysa Sabah Senin 12:05) | Sabah Senin: IG (+ BS) = ≤2 ✓ · BGK: FB ✓ · Kader: TikTok ✓ |
| **18 Cum** | 18:0x DJ koşusu (Just Relax kesit kararı açık) | Oto 12:05: katalog (haftanın 2.'si) | **Söz Defteri #1 Reels 13:00** (elle; 17 Eyl vardiyasında Business Suite'ten planlanır; TikTok'tan +64 sa) | **BGK video 19:05** (T0+73 sa) | Sabah Senin: FB ✓ · BGK: BS ✓ |
| **19 Cmt** | **TikTok Kulis #1 13:00** (Kırık Zincir) | — | Oto 12:05: katalog (haftanın 2.'si; Kırık Zincir değil) | — | Kırık Zincir: TikTok ✓ |
| **20 Paz** | 12:05 E5 D+7 kararı (Sabah Senin) · 13:00 YT Topluluk Kulis #1 · 18:00 YT Topluluk E4 (Sabah Senin) · 21:00 YouTube özel test #1 | Oto 12:05: katalog (haftanın 3.'sü) | — | **19:30 Kulis #1 metin + 2 görsel + alt metin** (elle: bisiklet zinciri ↔ seçilen kapak) | Kırık Zincir: YT Topluluk + BS = 2 ✓ · Sabah Senin: YT Topluluk ✓ |

**Hafta toplamı (öneri, 14-20 Eyl):**
- **Telegram 5:** 1 T0 (BGK), 1 Söz Defteri, 3 katalog.
- **Facebook 5:** 2 yeni Reels (Sabah Senin, BGK), 1 Söz Defteri, 2 katalog.
- **Bluesky 3-4:** 1-2 şarkı (BGK, gerekirse Sabah Senin), 1 katalog, 1 Kulis.
- Bu üç platformda insan emeği 3/13-14 ≈ **%21-23.** Hiçbir platformda aynı gün 2 gönderi yok.

**Bugünkü kodla aynı hafta (fark):**
- Her gün golden-hour'un ilk koşusunda TG 1 + BS 1 katalog ya da yeni gönderi çıkar; FB'de günde 2'ye kadar. Tahmini **TG 7, BS 7, FB 9-14.**
- BGK FB'de YouTube'la aynı an, BS 15 Eyl 18:05'te → **BGK T0 günü 4 yüzey.**
- Elle gönderi günlerinde (16 Eyl TG, 18 Eyl FB, 20 Eyl BS) o platformda **2 gönderi** olur.
- Kod değişmeden öneriye en çok yaklaşmanın yolu: elle erteleme (F-D1) ve elle gönderiyi geri doldurmadan ≥6 sa sonraya koymak. Gerisi O-T2/O-T3/O-T4/O-F1/O-F2 ile gelir.

**Kontrol listesi (Perşembe dağıtım vardiyası, +10 dk):**
- [ ] Önümüzdeki haftanın FB Söz Defteri Reels'i Business Suite'te planlandı (≤29 gün)
- [ ] Yeni şarkının FB planı YouTube T0 ile aynı andaysa ertelendi (açık onayla)
- [ ] Telegram/Bluesky elle metinleri hazır; "Suno" yok; Söz Defteri "biz" dili
- [ ] Bluesky görsellerinin alt metni yazıldı
- [ ] Her elle gönderi `python elle_islem.py ekle --platform <telegram|facebook|bluesky> ...` ile deftere (önce `python elle_islem.py sozluk`)

---

## 6. Ortak metrikler ve ölçüm günleri

| Gün | Ne okunur | Süre | Nereye |
|---|---|---|---|
| **27 Eyl (Paz)** | TG abone + son 5 gönderi göz sayacı · FB takipçi + Reels izlenmeleri (Business Suite) · **BS takipçi ilk okuma (temel çizgi)** + gönderi etkileşimleri | 10 dk | `elle_islemler.jsonl` (`kontrol_etti`); TikTok/YouTube okumalarıyla aynı gün |
| **9 Eki (Cum)** | `olcum_temel_cizgi.py` randevusu. Bu üç platform için yalnız not: ölçüm penceresinde toplu gönderi var mı | 5 dk | Aynı |
| **11 Eki (Paz) = 30. gün** | §2.5/§3.5/§4.5 tabloları · **Karar gözden geçirme:** haftalık tavanlar (Karar 2), merdiven (Karar 1), Meta AI anahtarı (Karar 4) | 15 dk | Aynı + bu belgenin sonuna "30. gün" notu |
| **8 Kas (Paz) = 60. gün** | Aynı + FB Para kazanma ekranına **bakış** (başvuru yok) + O-B4 altyazı kararı | 15 dk | Aynı |
| **13 Ara (Paz) = 90. gün** | Aynı + FB veri erişimi yenilendi mi (≈9 Ara) + platform rolleri korunsun mu | 20 dk | Aynı |

**Ortak özgünlük göstergeleri (haftalık; `yayin_ritmi` gelince otomatik):**
- Aynı şarkının aynı gün 3+ platformda olması: **0.**
- 10 dk içinde 2+ platforma gönderi kümesi: **0** (11-13 Eyl'de 4 küme).
- Platform başına 24 sa'te 2+ gönderi: **0.**
- Bu üç platformda insan emeği oranı: **≥%15.**

**Durdurma eşikleri:**
- Herhangi bir platformdan uyarı ya da kısıtlama bildirimi gelirse o platformun geri doldurması **durur**, format gözden geçirilir.
- Bluesky profilinde AI labeler etiketi görülürse Bluesky metin stratejisi yeniden açılır (karar metni değişmeden).
- FB'de bir Reels'in sesi kısılır ya da engellenirse o şarkı Meta'ya bir daha gitmez.

---

## 7. Kullanıcıya sorulacak kararlar

1. **Yayın merdiveni:** yeni şarkı Gün 0 YouTube + Telegram · Gün 1 Shorts + Instagram · Gün 2 TikTok + Facebook · Gün 3 Bluesky olsun mu? Kod gelene kadar Facebook planları Business Suite'ten elle ertelensin mi (F-D1)?
   **Önerim: evet.** "Aynı gün ≤2 platform" kararının uygulanabilir tek biçimi bu. 13 Eyl deseni (5-6 yüzey, FB'de aynı dakikaya iki Reels) tam da kaçınılan toplu desen. Elle erteleme Facebook hesabında değişiklik olduğu için **her seferinde açık onay** gerekir.
2. **Geri doldurma haftalık tavanı:** günlük tavanlar aynen kalırken haftada **TG 3, FB 2, BS 2** katalog geri doldurması olsun mu? Yeni şarkı ve insan emeği gönderileri bunun dışında kalır; elle gönderi günü o platformda geri doldurma çıkmaz.
   **Önerim: evet.** Tavan yükseltilmiyor, daraltılıyor; "tavanı yükseltme" kapalı listesiyle uyumlu. 15 eksik şarkı yaklaşık 5 haftada biter. Aynı şablon metinle arka arkaya katalog basmak Bluesky ve Facebook'ta en zayıf halka.
3. **Telegram kimliği:** kullanıcı adı `hermes_famous_asistan` → `famousmusicstudio` (doluysa `famousmusicstudio_tr`) ve açıklama düzeltmesi ne zaman, kim tarafından?
   **Önerim:** açıklama **bugün**, kullanıcı adı **site linkleri güncellenirken aynı saatte**. İkisini de sen uygulamadan yap (2 dk). Bot API ile yapılmaz; Claude'un Telegram için kalıcı onayı yok.
4. **Facebook sayfa metni ve Meta "AI info":** sayfa açıklamasındaki "Tüm içerik yapay zekâ ile üretilmiştir" karar diline ("Söz: Famous Music Studio · Müzik ve vokal: AI destekli") çevrilsin mi? Reels'te Meta'nın kendi AI beyan anahtarı da kullanılsın mı?
   **Önerim:** metin **evet**; sözlerin insan yazımı olduğunu doğru anlatır ve kararla tutarlıdır. Anahtar **şimdilik hayır**; 13 Eyl kararındaki açıklama satırı yeterli sayılır. Meta'nın "gerçekçi ses" için araçla beyan zorunluluğu resmî metinden okunamadı. 11 Eki gözden geçirmesinde resmî metin okunur; zorunluysa anahtar açılır.
5. **İnsan emeği serilerinin sürümleri:** Söz Defteri Telegram'da yazılı hâliyle, Facebook'ta aynı çekimin Reels'i olarak (TikTok'tan ≥48 sa sonra); Kulis Bluesky'da metin + görsel + alt metinle. `kanal_takvimi.json`'a Topluluk sürümleri gibi `kaynak_id`'li kayıt olarak girsin; TikTok'un haftalık 2 insan emeği tavanına sayılmasın, platformun günlük tavanına sayılsın. Onaylıyor musun?
   **Önerim: evet.** Çekim zaten var, maliyet sıfır. Her platforma haftada 1 gerçek insan emeği gönderisi ekler, bu üç platformdaki oranı %0'dan ~%20'ye çıkarır ve aynı gün ≤2 platform kuralına uyar.
6. **City Pulse Set (telif eşleşmeli) gönderileri:** Facebook Reels'i "yalnız ben" yapılsın mı, Telegram/Bluesky gönderileri kalsın mı?
   **Önerim:** Facebook'ta **gizle**; Meta ses tanıma ve Müzik Yönergeleri yüzünden sayfa geneline uyarı riski tek gönderinin değerinden büyük. Telegram ve Bluesky'da **kalsın**; içerik tanıma yok, arşiv değeri var. O-F6 ile telif işaretli projeler Meta'ya hiç gitmesin. Gizleme Facebook hesap işlemi olduğu için **açık onay** ister.

---

## 8. Doğrulanmayanlar
- **Genel:** Bluesky takipçi sayısı; üç platformda gönderi başına izlenme ve etkileşim (depoda veri yok).
- **Telegram:**
  - `Kader Ortakları` gönderisinin kanalda olup olmadığı; mesaj 4'ün ne olduğu.
  - `famousmusicstudio` adının boş olup olmadığı; eski kullanıcı adının serbest kalma süresi.
  - "Benzer kanallar" eşiği; Türkiye'de reklam geliri uygunluğu.
- **Facebook:**
  - Sabah Senin Reels açıklamasında AI satırı var mı; `marka/facebook_metinleri.txt` sayfaya yüklenmiş mi.
  - Eski kopya Reels'ler sayfadan kalkmış mı; Instagram çapraz paylaşım ayarı.
  - Reels asgari gereksinimleri; Türkiye'de Content Monetization uygunluğu.
  - "Gerçekçi ses" için araçla beyan zorunluluğu; Rights Manager ayrıntılı koşulları.
- **Bluesky:**
  - Video süre sınırı (3 dk mı, 10 dk mı) ve günlük video sayısı; alt metin uygulama sınırı.
  - Alan adı handle'ına geçişte eski `.bsky.social` bağlantılarının yönlenmesi.
  - Hesabın bir AI labeler'da etiketli olup olmadığı; mevcut bio.
- **Bugün:** 13 Eyl 12:05'te `facebook_backfill`'in üçüncü Reels'i gerçekten atıp atmayacağı (koşu sonrası log'dan görülür).
- **Bu hafta:** Bu Gece Kazandık'ın 15 Eyl T0'ı (`yayin_beklet` hâlâ state'te; yeniden render ve bekletmenin kaldırılması gerekiyor).

## 9. Kaynaklar

**Telegram (resmî):**
- SSS (kullanıcı adı, ilk 200 davet): https://telegram.org/faq
- Kanal SSS (sınırsız abone, tartışma grubu): https://telegram.org/faq_channels
- Benzer kanallar: https://telegram.org/blog/similar-channels · https://core.telegram.org/api/recommend
- Fragment: https://fragment.com/about
- Reklam geliri: https://telegram.org/blog/monetization-for-channels · https://core.telegram.org/api/revenue
- İçerik üreticisi ödül şartları (bölge): https://telegram.org/tos/content-creator-rewards
- Stars, abonelik, ücretli medya: https://telegram.org/blog/superchannels-star-reactions-subscriptions · https://core.telegram.org/api/paid-media · https://core.telegram.org/api/stars
- Bot API (10.3, 24 Ağu 2026): https://core.telegram.org/bots/api · https://core.telegram.org/bots/faq · https://core.telegram.org/bots/features
- Hizmet şartları: https://telegram.org/tos

**Facebook / Meta (resmî):**
- Sayfa ve profesyonel mod: https://www.facebook.com/help/203141666415461
- Reels, Haziran 2025: https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/
- Orijinallik, Mart 2026: https://about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/ · https://www.facebook.com/business/help/262834734651607
- AI etiketleme: https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/ · https://transparency.meta.com/governance/tracking-impact/labeling-ai-content/ · https://transparency.meta.com/policies/community-standards/manipulated-media/
- Planlama (20 dk - 29 gün): https://www.facebook.com/help/389849807718635
- Müzik Yönergeleri: https://www.facebook.com/legal/music_guidelines
- Rights Manager: https://www.facebook.com/business/help/705604373650775 · https://www.facebook.com/business/help/1824313947806360
- Content Monetization: https://creators.facebook.com/introducing-facebook-content-monetization · ülke listesi (okunamadı): https://www.facebook.com/business/help/267128784014981 · Ortaklar İçin Para Kazanma İlkeleri (okunamadı): https://www.facebook.com/business/help/169845596919485
- Instagram çapraz paylaşım: https://www.facebook.com/help/932731427414654 · https://help.instagram.com/459497729122868
- Platform Terms: https://developers.facebook.com/terms/ · Spam: https://transparency.meta.com/policies/community-standards/spam/

**Bluesky (resmî):**
- Özel akışlar: https://docs.bsky.app/docs/starter-templates/custom-feeds · örnek müzik akışı: https://bsky.app/profile/did:plc:ke6e3skfhjdsnky5d3ojauh3/feed/music
- Gönderi şeması (300 grafem, tags, görsel, link kartı): https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/post.json
- Etiket değerleri: https://github.com/bluesky-social/atproto/blob/main/lexicons/com/atproto/label/defs.json
- Video şeması ve belge: https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/embed/video.json · https://bsky.network/docs/about-bluesky-content/video/
- Rate limit: https://bsky.network/docs/rate-limits/
- Topluluk kuralları (19 Eyl 2025): https://bsky.social/about/support/community-guidelines
- Video yükleme yolu: https://github.com/bluesky-social/bsky-docs/blob/main/docs/tutorials/video.mdx

**İkincil (doğrulanmamış):** https://www.bluesky-labelers.io/ · Bluesky video süre sınırı haberleri (TechCrunch, Mart 2025) · Facebook Content Monetization ülke listeleri (üçüncü taraf, Aralık 2025).

**Depo içi:**
- State'ler (`projects/*`, `dj_sets/*`, `derlemeler/*`) · `auto_process.log` (12-13 Eyl) · `elle_islemler.jsonl` · `kanal_takvimi.json` · `olcum_temel_cizgi.json` (bu platformlar için alan yok)
- `config.py` (`EK_PLATFORMLAR`, `GOLDEN_HOURS`, `AI_BEYAN_SATIRLARI`, `TUREV_*`)
- `upload/telegram_upload.py` · `upload/facebook_upload.py` · `upload/facebook_backfill.py` · `upload/bluesky_upload.py` · `upload/ek_platform_backfill.py` · `upload/facebook_veri_erisimi.json` · `upload/telegram_client_secrets.json` (yalnız `chat_id` tipi)
- `marka/facebook_metinleri.txt` · `docs/index.html` · `docs/latest.html`
- `CLAUDE.md` · `ozgunluk_plani.md` · `yayin_sonrasi_takvim_plani.md` · `haftalik_is_akisi.md` · `denetim_bulgulari_2026-09-12.md` (K-4, C-3) · `buyume_kontrol_listesi.md` (B3, D2, D3, E-15)
- `icerik_paketleri/2026-09-14_haftasi/` · hafıza: `reference_telegram_bluesky_kurulum.md`, `feedback_ai_beyani_suno_yok.md`, `project_inauthentic_content_riski.md`, `reference_platform_genisleme.md`
