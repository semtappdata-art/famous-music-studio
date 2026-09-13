# Instagram iş planı (`@famous_music_studio`)

> Yazıldığı an: **2026-09-13 (Pazar) 10:10-10:40**. Hesap Chrome'dan **salt okunur** incelendi: paylaşım, silme, arşivleme, düzenleme, yorum, takip ve mesaj okuma yapılmadı.
> Kod, state ve git değişikliği yok. Graph API çağrısı ve Telegram yok.
> **Ön kontrol:** Instagram'a özel bir plan yoktu. `*plan*.md`, `buyume_kontrol_listesi.md` ve `haftalik_is_akisi.md` içinde Instagram yalnız parça parça geçiyor (A5-A7, C3, E2, E3, E-9/E-11/E-12, R2/R3). `ek_platformlar_is_plani.md` bu an diskte **yok**; çıkınca bu belgeyle karşılaştırılmalı.
> Eş belgeler: `ozgunluk_plani.md`, `yayin_sonrasi_takvim_plani.md`, `tiktok_live_plani.md`, `youtube_live_plani.md`, `suno_kalite_onerileri.md`.
> Etiketler: **[R]** resmî kaynak okundu · **[İ]** ikincil kaynak, resmî sayfa okunamadı · **[D]** doğrulanmadı.

---

## 0. Kısa sonuç

- **Hesap küçük ama keşif çalışıyor.**
  - Takipçi 406, takip 448, 24 gönderi.
  - Son 30 günde 4.597 görüntüleme; **%64,3'ü takipçi olmayanlardan**.
  - Profil ziyareti 512, harici bağlantı dokunuşu **yalnız 9** (%1,8).
- **Izgara %100 otomatik Reels ve tek şablon.** Görülen 16 gönderinin 16'sı Reels; Carousel ve fotoğraf yok. Hepsinde üstte başlık, ortada logo. İnsan emeği içeriği 0.
- **Kopya sorunu hâlâ canlı.** `Dcv6i1PjYUy` ve `Dcv5AiRgSsc` yayında; ikisi de eski açıklamayı taşıyor: *"0'dan yapay zeka ile üretilen"* + `#AIMusic #YapayZekaMüzik #AIMusicChallenge`. `Dc5vAXxgGIf` de yayında. Arşivleme yalnız telefonda (E-9, 17 Eyl).
- **Bio linki büyük ölçüde yapılmış.** `famousmusicstudio.com/latest.html` profilde duruyor, ama 4 bağlantının **2.'si**. İlk sırada `?si=` izleme parametreli YouTube linki var.
- **AI beyanı iki katmanda.**
  - Profilde ve her gönderide *"Yapay zeka tarafından oluşturulan profil"* etiketi görünüyor.
  - Görülen 16 açıklamanın **0'ında** "AI destekli" satırı var. Satır yeni gönderilerle gelecek (`config.AI_BEYAN_SATIRLARI`).
- **Yorumların çoğu bizim.** Gönderi başına görünen "1 yorum" genellikle otomasyonun YouTube linki yorumu. Gerçek yorumlar tek emojili alkışlar ve **hiçbiri yanıtlanmamış**.
- **Önerilen rol:** Instagram, kanalın **görsel kimlik ve söz vitrini** olsun. Sırasıyla: söz kartları (Carousel), kulis/Söz Defteri hikâyesi, Reels keşfi. Uzun dinleme YouTube'da, sohbet ve seri TikTok'ta kalsın.

---

## 1. Hesabın gerçek durumu (2026-09-13 10:15, Chrome, salt okunur)

### 1.1 Profil

| Alan | Değer | Not |
|---|---|---|
| Gönderi / takipçi / takip | **24 / 406 / 448** | Takip, takipçiden fazla (bkz. §6 S7) |
| Hesap türü | Profesyonel ("Profesyonel pano", "Reklam araçları" var) · kategori **Müzisyen/Grup** | Web, "içerik üreticisi" ile "işletme" ayrımını göstermiyor [D]. Telefonda Ayarlar → Hesap türü |
| Etiket | **"Yapay zeka tarafından oluşturulan profil"** | Profilde ve her gönderi başlığında görünüyor. Meta'nın 2026 "AI-generated profile" etiketi [İ] |
| Bio metni | "Orijinal müzik, üretim ve yayın. 🎵" | Jenerik; seri ve beyan bilgisi yok |
| Bağlantılar (4) | 1) YouTube `…/@famous_musics_studio?si=…` · 2) **famousmusicstudio.com/latest.html** · 3) TikTok · 4) Facebook paylaşım linki | Sıra ve `?si=` temizliği telefonda |
| Not (Notes) | Profil fotoğrafının üstünde bir Not var ("Not…") | İçeriği okunmadı |
| Öne çıkanlar | **1 adet**, başlığı "Öne Çıkanlar" (jenerik), içeriği bir Reels paylaşımı (~2 gün önce) | Yapı yok (§3.3) |
| Mesaj kutusu | Okunmamış sayı rozeti görünmedi | **Mesajlar açılmadı, içerik okunmadı** |
| Bildirim | 1 yeni takipçi rozeti | — |

Ekran görüntüleri:
- Profil: `C:\Users\ACER\AppData\Local\Temp\claude-chrome-screenshots-IVpomi\screenshot-1789283447037-36.jpg`
- Bağlantılar: `C:\Users\ACER\AppData\Local\Temp\claude-chrome-screenshots-IVpomi\screenshot-1789283538874-37.jpg`
- Profesyonel pano: `C:\Users\ACER\AppData\Local\Temp\claude-chrome-screenshots-IVpomi\screenshot-1789283770161-38.jpg`

### 1.2 Gönderiler

- Web ızgarası gizli sekmede **16/24** gönderi yükledi.
- Kalan 8 gönderi 1-5 Eylül'ün en eski yüklemeleri: `Gece Sürüşü`, `Kalbim Oynuyor`, `Beton Krallığı`, eski kopyalar vb. Bunlardan `Dcv6i1PjYUy` ve `Dcv5AiRgSsc` doğrudan açılıp doğrulandı.
- Tür sütunu hepsi için **Reels**. Tarihler `state.json`'dan (`instagram_uploaded_at`). B = beğeni, Y = görünen yorum sayısı (otomasyonun linkli yorumu dahil), İ = izlenme.

| # | Kod | Şarkı | Tarih | B | Y | İ |
|---|---|---|---|---|---|---|
| 1 | `DdLDijyG557` | Sofraya Gelmedin | 12 Eyl | 5 | 1 | 178 |
| 2 | `DdJtTiAio7s` | Gece Seansı Vol. 1 (derleme) | 11 Eyl | 6 | 1 | 101 |
| 3 | `DdH_R0ejw2y` | Yeraltı | 11 Eyl | 5 | 1 | 103 |
| 4 | `DdHBjOfDZvR` | Yürek Yarası | 10 Eyl | 9 | 1 | 175 |
| 5 | `DdGJ4DaDAyc` | Sessiz Mektup | 10 Eyl | 6 | 1 | 62 |
| 6 | `Dc_8QcOgSDN` | Son Kez | 8 Eyl | 8 | 1 | 107 |
| 7 | `Dc_oLXYD3oh` | City Pulse Set | 7 Eyl | 7 | 1 | 82 |
| 8 | `Dc_NJrQk47b` | Just Relax | 7 Eyl | 4 | 1 | 72 |
| 9 | `Dc_ZJHFCEYf` | Kırık Zincir | 7 Eyl | 9 | 1 | 80 |
| 10 | `Dc-5CR9j2XO` | **Küllerimden Geç** (KALACAK) | 7 Eyl | 7 | 1 | **459** |
| 11 | `Dc9CJ1VD9rs` | Sokaklar Beni Tanır | 6 Eyl | 8 | 2 | 109 |
| 12 | `Dc8OQl4sPCd` | Beni Bırakma | 5 Eyl | 8 | 0 | 97 |
| 13 | `Dc5vAXxgGIf` | Yeniden Doğacağım (**arşivlenecek**) | 5 Eyl | 7 | 2 | 80 |
| 14 | `Dc5uqEHCq6Y` | (5 Eyl toplu yükleme) | 5 Eyl | 8 | 2 | 76 |
| 15 | `Dc5ued5kpal` | Bir Bahar Daha | 5 Eyl | **13** | 3 | 177 |
| 16 | `Dc5uL7nlEke` | (5 Eyl toplu yükleme) | 5 Eyl | 7 | 2 | 75 |
| — | `Dcv6i1PjYUy` | eski tasarım, ses = Küllerimden Geç (**arşivlenecek**) | 1 Eyl | ~11 | ? | ? |
| — | `Dcv5AiRgSsc` | eski tasarımın kopyası (**arşivlenecek**) | 1 Eyl | 12 | 1 | ? |

**Gözlemler**

- **Medyan izlenme ≈ 97**, medyan beğeni 7. Tek sıçrama `Küllerimden Geç` (459).
- **5 Eylül 13:12-13:21 toplu yüklemesi ızgarada da görünüyor:** 9 dakikada 5 Reels, yan yana aynı şablon. Bu, `ozgunluk_plani.md` R2'nin tarif ettiği desen.
- **Izgara tutarlılığı:** 16/16'da üstte başlık, ortada logo, stok fotoğraf. Tek tip ama **şablon tekrarı** (özgünlük planı §1.1, %95).
- **Açıklama katmanları üç kuşak:**
  1. 1 Eyl: "yapay zeka ile üretilen" + AI hashtag'leri. Bugünkü kurala aykırı.
  2. 5-7 Eyl: `#keşfet #fyp #viral`. TikTok kökenli, Instagram'da işlevsiz.
  3. 10-12 Eyl: tema cümlesi + soru.
- **AI beyan satırı hiçbirinde yok.**
- **Otomatik yorum:** "🎧 Şarkının tamamı YouTube'da: https://youtu.be/…" ve "@famous_music_studio hesabına dokun, bio'daki linkten…". Instagram'da tıklanmıyor (tasarım gereği). Yorum sayısını şişiriyor, ölçümde çıkarılmalı.

### 1.3 İstatistikler (Profesyonel pano, **web'de erişilebilir**, son 30 gün)

| Metrik | Değer |
|---|---|
| Görüntüleme | **4.597** (takipçi %35,7 · takipçi olmayan **%64,3**) |
| Görüntüleyen hesap | 1.400 |
| İçerik türüne göre | Reels %79,7 · **Hikâyeler %20,3** (hikâye kaynağı otomasyon değil; elle paylaşım olmalı [D]) |
| Görüntülemeye göre en iyi 5 | 457 (7 Eyl, Küllerimden Geç) · 389 (1 Eyl) · 351 (1 Eyl) · 349 (1 Eyl) · 226 (3 Eyl) |
| Etkileşime göre en iyi 5 | 17 (1 Eyl) · 16 (5 Eyl) · 16 (1 Eyl) · 12 (7 Eyl) · 11 (10 Eyl) |
| Profil hareketi | 521 (ziyaret 512 · harici bağlantı dokunuşu **9**) |
| Takipçi | 406. **30 günlük değişim okunamadı**: alt sayfa gizli sekmede yüklenmedi → telefonda Pano → Takipçiler |
| En aktif zamanlar | Ham değerler 42/45/45/49/41/18/8/20 (3 saatlik dilimler). Gün-saat eşlemesi webde net değil [D] |

**Dikkat:** 1 Eylül'ün eski gönderileri en çok izlenen içerikler arasında (389/351/349). Arşivleme toplam sayıyı silmez, yalnız ızgaradan kaldırır [İ]. Özgünlük kazancı, ızgaradaki "en iyi" görüntüden önemli.

### 1.4 Etkileşim

- **Gerçek yorumlar** (kişi adları maskeli):
  - `Dc5ued5kpal`: aynı hesaptan 2× "👏👏👏👏"
  - `Dc9CJ1VD9rs`: 1× "👏👏👏👏"
  - `Dc-5CR9j2XO`: 1× "👏" (2 gün önce; `haftalik_is_akisi.md` E-12'nin bekleyen yorumu)
  - `Dcv5AiRgSsc`: 1× "👏👏👏👏"
- **Yanıtlanmamış:** okunan 5 gerçek yorumun **5'i**.
- **Beğenenler:** her gönderide aynı küçük çekirdek (3-4 hesap). Organik kitle henüz beğeni ya da yorum bırakmıyor.
- **Mesajlar:** sayı rozeti yok. İçerik okunmadı.

---

## 2. Resmî kurallar ve fırsatlar (2026-09-13'te okundu)

### 2.1 Algoritma ve öneriler

- **Özgün içerik güncellemesi (30 Nisan 2026).** Reels için var olan kural fotoğraf ve Carousel'e genişledi. Çoğunlukla başkasının içeriğini yeniden yükleyen hesaplar önerilerden çıkıyor. [İ] TechCrunch: <https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/>
  - Filigran ya da hız değişikliği "özgün" saymaya yetmiyor.
  - 30 günlük pencerede çoğunluk özgün olunca uygunluk geri geliyor [İ].
- **Öneri uygunluğu:**
  - Resmî sayfalar: <https://help.instagram.com/653964212890722> · <https://creators.instagram.com/original-content-guidelines> · <https://help.instagram.com/1800814370401535/>. Yardım sayfaları JS ile yüklendiği için metin bu çalışmada alınamadı [D].
  - Creators blogu (<https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators>) şunları öneri dışı sayıyor: **filigranlı, bulanık ya da düşük kaliteli** Reels ve **Instagram'a zaten yüklenmiş** bir Reels'in yeniden paylaşımı [R].
  - Aynı blog 9:16 dikey, ilk 3 saniyede kanca ve kısa süre öneriyor.
- **Bizim için sonuçlar:**
  1. **TikTok'tan indirilen dosya Instagram'a asla yüklenmez** (filigran). Söz Defteri ve Kulis çekimleri **ham telefondan** yüklenir.
  2. **Aynı sesin ikinci Reels'i**, "zaten yüklenmiş Reels" sınıfına en yakın durum. Kopyaların arşivi bu yüzden öncelikli. İkinci kesit Reels'i **ERTELE** kararı (`yayin_sonrasi_takvim_plani.md` §1b) aynen kalır.
  3. Sözler insan yazımı, kapak ve kulis elle. İçerik "başkasının işi" değil. Risk "aggregator" değil, **"toplu ve tek şablon"**.

### 2.2 AI beyanı ve telif

- **AI info etiketi:** Meta, sektör standardı AI işaretlerini algılayınca ya da kullanıcı beyan edince "AI info" gösteriyor [R] <https://transparency.meta.com/governance/tracking-impact/labeling-ai-content/>.
  - 2024 duyurusu, fotogerçekçi video ve **gerçekçi ses** için beyan aracının kullanılmasını istiyor: <https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/> [D, bu çalışmada yeniden okunmadı].
- **Profil etiketi:** "AI creator" hesap etiketi Mayıs 2026'da geldi, 31 Ağustos 2026'da "AI-generated profile" adını aldı [İ]. Hesapta **zaten açık**.
- **Bizim satır:** açıklamada "Söz: Famous Music Studio · Müzik ve vokal: AI destekli". Profil etiketiyle birlikte **iki katman** oluyor. Kamuya açık metinde üretim aracının adı geçmez.
- **Müzik telifi:** Meta Rights Manager, eşleşen sesi izleme, gelir ya da engelleme ile yönetiyor [İ].
  - Kendi sesimiz "Orijinal ses" olarak görünüyor.
  - Başka birinin sesiyle eşleşme riski, DJ setlerindeki itiraz dışında gözlenmedi.
  - **Sesi Meta müzik kütüphanesine dağıtıcı üzerinden kaydetmek bu planın dışında.** AI müzikte sahiplik şartı belirsiz; "Orijinal ses" yeterli.

### 2.3 Türkiye'de para kazanma ve hediye uygunluğu

- **Hediyeler (Gifts):** Türkiye 2023 genişlemesinde listede [İ] (<https://www.malaymail.com/news/tech-gadgets/2023/09/19/instagram-rolls-out-its-gifts-option-in-more-countries/91632>).
  - Eşik kaynaklara göre **500 ya da 5.000 takipçi**, 18+, profesyonel hesap, para kazanma politikalarına uyum [İ, çelişkili].
  - Resmî sayfa okunamadı: <https://www.facebook.com/business/help/738469380549477> [D].
  - **406 takipçiyle iki eşiğin de altında.** Telefonda Pano → "Para kazanma durumu" ekranı tek güvenilir kaynak.
- **Uyarı:** para kazanma politikaları "özgün olmayan içerik" ve AI beyanı ihlallerinde uygunluğu kaldırıyor. Kopyaların arşivi burada da ön şart.

### 2.4 Özellikler

| Özellik | Ne yapar | Uygunluk | Bizim için |
|---|---|---|---|
| **Trial Reels** | Reels önce **yalnız takipçi olmayanlara** gösterilir; ~72 saat sonra performansa göre elle ya da otomatik takipçilere açılır [R] <https://creators.instagram.com/blog/instagram-trial-reels> | Profesyonel hesap. 2026'da **≥1.000 takipçi** eşiği bildiriliyor [İ]. Hesapta anahtar var mı telefonda bakılmalı | Anahtar görünürse Söz Defteri/Kulis denemesi (§3.4). Görünmüyorsa 1.000 takipçiye kadar yok |
| **Carousel** | ≤10 görsel/video, tek gönderi sayılır [R] | Herkes | **Söz kartları ana formatı** (E3) |
| **Carousel'e müzik** | Telefonda yalnız **fotoğraflı** Carousel'e kütüphaneden müzik eklenir. Videolu Carousel'e eklenmez; web ve masaüstünde yok [İ] | Kütüphanede olmayan kendi sesimiz eklenemeyebilir [D] | Kartlar **müziksiz** ya da kütüphaneden sakin enstrümantal. Son kart "Sesi profildeki Reels'te" der |
| **Notes** | 60 karakter, 24 saat, karşılıklı takipçiler ya da Yakın Arkadaşlar; gönderi ve Reels'e de eklenebiliyor [İ] <https://blog.hootsuite.com/instagram-notes/> | Herkes | Haftada 2 kısa not: "Salı Söz Defteri", "hangi dize?" |
| **Broadcast kanalı** | Takipçilere tek yönlü duyuru + anket; 2026'da takipçi eşiği yok, profesyonel hesap [İ] | Büyük olasılıkla açık [D] | **Aşama 2** (≥500 takipçi). Bugün 406 kişiye ikinci bir kanal gereksiz iş |
| **Collab gönderisi** | Gönderi ve Reels birden çok profilde; uygulamada 5'e kadar ortak [İ], API'de 3 [R] | Herkes | Söz yazarı ya da ses sanatçısı iş birliği olursa. DJ Famous için **ayrı rıza** (`dj_sets/README.md`) |

### 2.5 Graph API sınırları (bu projenin kullandığı yol: `graph.instagram.com`, **Instagram Login**)

Kaynaklar: <https://developers.facebook.com/docs/instagram-platform/content-publishing/> ve <https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media> [R].

| Konu | Kural | Sonuç |
|---|---|---|
| Günlük yayın | **24 saatlik kayan pencerede 100** API yayını; Carousel 1 sayılır. Canlı değer `GET /<IG_ID>/content_publishing_limit` | Tavan sorun değil. Asıl tavan **bizim R2 kuralımız** (24 sa'te 1) |
| Konteyner ömrü | 24 saat, sonra `EXPIRED` | `KONTEYNER_OMRU_SN = 23 sa` doğru |
| Carousel | `media_type=CAROUSEL`, `children` ≤ 10; **Reels Carousel'e giremez**; oran ilk görsele göre kırpılır; **yalnız JPEG** | Kart üreticisi PNG değil **JPEG** vermeli; Netlify barındırma deseni aynen |
| Hikâye | `media_type=STORIES` destekleniyor (profesyonel hesap) | Instagram Login'de çalıştığı **doğrulanmadı** [D]. Link çıkartması ve müzik API'de yok |
| **Trial Reels** | `trial_params.graduation_strategy` = `MANUAL` / `SS_PERFORMANCE`, yalnız `REELS`. Referans sayfası **"Instagram API with Facebook Login"** için geçerli diyor | **Bugünkü Instagram Login akışıyla kullanılamaz.** Facebook Login'e geçiş ayrı ve riskli iş |
| Collab | `collaborators` ≤ 3; hikâyede yok | Gerekirse |
| Kapak | `cover_url` (Reels sekmesi kapağı), `thumb_offset` | Mevcut |
| Silme ve arşivleme | API'de yok (`buyume_kontrol_listesi.md` E2) | Telefonda |

---

## 3. Plan

### 3.1 Konumlandırma: Instagram'ın rolü

| Platform | Rolü (tekrarsız) |
|---|---|
| YouTube | Uzun dinleme, sözler, derleme, izlenme saati |
| TikTok | Keşif, seri (Söz Defteri #N), sohbet, ileride LIVE |
| **Instagram** | **Görsel kimlik ve söz vitrini:** kaydedilen söz kartları, kulis hikâyeleri, düzenli ızgara, Reels ile ikincil keşif |
| Facebook / Telegram / Bluesky | Dağıtım yankısı (tavan 1) |

Kural: Instagram'daki "insan emeği" içeriği TikTok'un **kopyası değil, uyarlamasıdır**.
- TikTok'ta ses anlatımlı video olan Söz Defteri, Instagram'da **fotoğraflı Carousel ya da hikâye dizisi** olur.
- Aynı video iki platforma yüklenecekse ham dosyadan, ≥ 48 saat arayla ve farklı kanca metniyle.

### 3.2 Grid ve görsel kimlik

1. **Üçlü satır ritmi** (yeni gönderilerden itibaren, geçmişe dokunmadan): `Reels (şarkı) · Carousel (söz kartı) · Reels ya da kulis`. Hedef: 3 gönderide en az 1 Carousel.
2. **Kapak düzeni rotasyonu** özgünlük planıyla aynı: D1 ortalı-üst · D2 alt-sol sade · D3 alt bant · D4 tipografik. Ardışık 3 yayında aynı düzen yok.
   - Instagram'da ek kural: **Carousel kapağı (1. kart) Reels kapağından farklı bir düzen** olmalı. Önerilen: D4 tipografik, fotoğrafsız, tema rengi zemin. Izgarada şablon tekrarını kıran en ucuz yol.
3. **Profil ızgarası kırpması 3:4.** Başlık ve logo 1080×1440 güvenli alanda kalmalı. `cover_url` görseli bunu gözetir. Carousel kartları **1080×1350 (4:5)** ve JPEG.
4. **Sabitlenmiş 3 gönderi** (telefonda):
   - `Dc-5CR9j2XO` (Küllerimden Geç, 459 izlenme)
   - ilk Söz Kartı Carousel'i (`Sabah Senin`, 17 Eyl)
   - ilk Kulis içeriği
5. **Öne çıkanlar yapısı** (telefonda; kapaklar tek renk ikon):
   - **Yeni Şarkı:** son 4 şarkının Reels paylaşımları
   - **Söz Defteri:** defter fotoğrafları, "hangi dize?" anketleri
   - **Kulis:** kapak seçimi, reddedilen taslaklar
   - **Nasıl?:** tek kart. "Sözler bizden, müzik ve vokal AI destekli" + SSS. Üretim aracının adı yok.
   - **DJ Famous:** ayrı rıza gelene kadar **yok**.
   - Mevcut jenerik "Öne Çıkanlar" → "Yeni Şarkı" olarak yeniden adlandırılır.
6. **Bio önerisi** (≤150 karakter, telefonda, taslak; kullanıcı düzeltir):
   `Sözler bizden, müzik ve vokal AI destekli 🎵 · Her hafta yeni şarkı · Salı Söz Defteri` + bağlantı sırası: **1) latest.html**, 2) YouTube (`?si=` temizlenmiş), 3) TikTok, 4) Facebook.

### 3.3 İçerik formatları

| Format | Kaynak | Sıklık | Nasıl | Özgünlük kuralı |
|---|---|---|---|---|
| **A. Otomatik Reels** | `upload/instagram_upload.py` (konteyner + golden-hour drain) | Yeni şarkı başına 1 | Bugünkü gibi. Açıklamaya AI beyan satırı. **Instagram'a özel hashtag seti** (§3.7 O1) | R2: IG'de 24 sa'te ≤1 · R3: YouTube T0'dan farklı pencere |
| **B. Carousel söz kartları (E3)** | `yayin_sonrasi_takvim_plani.md` §1a | Haftada 1 | **İlk ay elle, telefondan.** 5 kart: tipografik kapak · nakarat · Verse beyit · Bridge beyit · "Söz: Famous Music Studio". Açıklamada beyan satırı | Aynı şarkının IG Reels'inden ≥72 sa sonra |
| **C. Söz Defteri / Kulis uyarlaması** | `kanal_takvimi.json` (TikTok #1 15 Eyl, Kulis #1 19 Eyl) | Haftada 1-2 hikâye dizisi, ayda 1-2 Reels | **Hikâye:** 3-5 kare (defter fotoğrafı, eski/yeni dize, anket "hangisi?"). **Reels:** ham çekimden, TikTok'tan ≥48 sa sonra | TikTok dosyası yüklenmez. Yüz yok, araç adı ve logosu yok |
| **D. Trial Reels denemesi** | Uygulama anahtarı (API değil) | Uygun olunca 2 haftada 1 | Söz Defteri Reels'inin **ikinci kancalı** hâli, "Trial" açık, `MANUAL` | Anahtar yoksa atlanır (≥1.000 takipçi) |
| **E. Notes** | Telefon | Haftada 2 | "Salı akşamı Söz Defteri", "Bu hafta hangi dize?" | Şarkı sayacına girmez |
| **F. Broadcast kanalı** | Telefon | Aşama 2 (≥500 takipçi) | Haftalık tek duyuru + anket | — |
| **G. Yeni şarkı hikâyesi** | Telefon | Yeni Reels'ten 1 gün sonra | Reels'i hikâyede paylaş + "Yeni Şarkı" öne çıkanına ekle | Aynı gün değil (R3: günde ≤2 platform) |

**Hikâye ve Notes'un sayılması:**
- Bir şarkıyı konu alan hikâye ya da Carousel, "şarkı aynı gün en fazla 2 platformda" kuralında **Instagram platformu** sayılır.
- Aynı gün aynı şarkı için YouTube + IG olur; YouTube + TikTok + IG olmaz.
- Şarkıya özgü olmayan Notes sayılmaz.

### 3.4 Örnek hafta: 14-20 Eylül 2026

**Varsayımlar:**
- `Sabah Senin` T0 = **13 Eyl 12:00** (YouTube). IG Reels 13 Eyl 12:05 drain.
- `Bu Gece Kazandık` T0 ≈ 52 saat sonra → **15 Eyl 18:00**. Bekletme kalkarsa; kalkmazsa satırlar kayar.
- TikTok 15 ve 17 Eyl · Söz Defteri #1 (TikTok) 15 Eyl 20:30 · Kulis #1 (TikTok) 19 Eyl 13:00 · Topluluk sürümleri 16 Eyl 20:30 ve 20 Eyl 13:00 · E3 Carousel 17 Eyl 19:00.

| Gün | Saat | Instagram işi | Kim | Şarkı → o günkü platformlar | Not |
|---|---|---|---|---|---|
| **13 Paz** (referans) | 12:05 | `Sabah Senin` Reels (otomatik) | Otomasyon | Sabah Senin → YouTube + Shorts + IG (+TG/BS) | ⚠ **Bugünkü kodda R3 yok**: 2'nin üzerinde platform. ⚠ Aynı koşuda `Kader Ortakları` IG konteyneri de golden-hour bekliyor → **aynı pencerede 2 IG Reels** (R2 ihlali). Kod kararı §3.7 O2 |
| **14 Pzt** | 19:00 | **G:** `Sabah Senin` Reels'ini hikâyede paylaş + "Yeni Şarkı" öne çıkanı | Kullanıcı (telefon) | Sabah Senin → YouTube Topluluk (E2 12:00) + IG hikâye = **2** ✓ | 12:30-14:00 arası 13 Eyl Reels'inin yorum turu |
| 14 Pzt | 21:00 | **E:** Note "Yarın akşam Söz Defteri #1" | Kullanıcı | — | Şarkı sayılmaz |
| **15 Sal** | 18:00 | `Bu Gece Kazandık` YouTube T0. **IG Reels bugünkü kodla 18:05'te çıkar** | Otomasyon | Bu Gece → YouTube + Shorts + IG (+FB/TG/BS) | ⚠ R3 kodu gelene kadar kaçınılmaz. Hedef davranış: IG 16 Eyl 12:05 (karar K5) |
| 15 Sal | 20:30 | — (Söz Defteri #1 **TikTok'ta**) | Kullanıcı | Sabah Senin → TikTok = 1 | IG'ye aynı gün yükleme **yok** |
| **16 Çar** | 12:30-14:00 | Yorum turu (`Bu Gece Kazandık` Reels) | Kullanıcı | — | İlk 2 saat kuralı |
| 16 Çar | 21:00 | **C (hikâye):** Söz Defteri #1 uyarlaması. Defter fotoğrafı, eski/yeni dize, anket "hangisi?" | Kullanıcı | Sabah Senin → YouTube Topluluk (20:30) + IG hikâye = **2** ✓ | TikTok'tan 24,5 sa sonra. Video yok, fotoğraf |
| **17 Prş** | 18:00-18:15 | **Telefonda bakım (E-9/E-11/E-12):** 3 kopyayı **arşivle** (`Dc5vAXxgGIf`, `Dcv6i1PjYUy`, `Dcv5AiRgSsc`) · `Dc-5CR9j2XO`'yu sabitle · bekleyen alkış yorumlarını yanıtla · bio bağlantı sırası (latest.html 1.) | Kullanıcı | — | `Dc-5CR9j2XO` **kalıyor** |
| 17 Prş | 19:00 | **B:** `Sabah Senin` Carousel söz kartları (E3, elle) | Kullanıcı | Sabah Senin → IG Carousel + (TikTok 17 Eyl başka şarkıysa) = ≤2 ✓ | 13 Eyl Reels'inden 103 sa ✓ (≥72). ⚠ 17 Eyl TikTok gönderisi **Sabah Senin olmamalı** |
| 17 Prş | 19:00-21:00 | Carousel yorum turu | Kullanıcı | — | Kaydetme sayısını 24 sa sonra not al |
| **18 Cum** | — | IG yayını yok (DJ günü) | — | — | Just Relax kesidi yalnız YouTube'a (`yayin_sonrasi` karar 1) |
| **19 Cmt** | 20:00 | **C (hikâye):** Kulis #1 uyarlaması, "Kırık Zincir'in kapağı nasıl seçildi". 3 kare: aday kapaklar → seçilen → neden. Anket | Kullanıcı | Kırık Zincir → TikTok (13:00) + IG hikâye = **2** ✓ | Ekran görüntüsünde araç adı ve logosu yok |
| 19 Cmt | 21:00 | **E:** Note "Hangi kapağı seçerdin?" | Kullanıcı | — | — |
| **20 Paz** | 13:00 | — (Kulis Topluluk YouTube'da) | — | Kırık Zincir → YouTube Topluluk = 1 | IG'de tekrar yok |
| 20 Paz | 20:30-20:45 | **Haftalık okuma (10 dk):** Pano → 7 günlük görüntüleme, takipçi olmayan oranı, takipçi değişimi, bağlantı dokunuşu; Carousel kaydetme/paylaşma; hikâye anket yanıtı | Kullanıcı | — | `elle_islem.py ekle --platform instagram --islem kontrol_etti` |

**Hafta toplamı (Instagram):**
- 2 otomatik Reels (13 ve 15 Eyl)
- 1 Carousel
- 3 hikâye dizisi
- 2 Note
- 1 bakım oturumu
- Yeni Reels yüklemesi insan eliyle: **0**
- Trial Reels: bu hafta yok (406 takipçi; anahtar yoksa)

### 3.5 Etkileşim rutini (elle, bot yok)

1. **Pencere:** her yeni IG Reels ya da Carousel'den sonraki **ilk 1-2 saat**. Otomatik Reels 12:05 ya da 18:05'te çıktığı için yorum turu **12:30-14:00 / 18:30-20:00**.
2. **Rehber:** `icerik_paketleri/2026-09-14_haftasi/yorum_yanit_rehberi.md` Instagram'da da geçerli (TikTok'a özgü "videoyla yanıtla" yerine "Reels ile yanıtla"). Ek kurallar:
   - **Alkış ve emoji yorumlarına** kalıp 10 ya da 1 ile, **soruyla** yanıt ver. Aynı cümleyi iki kişiye yazma. Kişinin adını ya da gönderinin bir öğesini kullan.
   - "Yapay zeka mı?" sorusuna kalıp 7: "Sözleri biz yazıp seçiyoruz, müzik ve vokal AI destekli." Araç adı yok.
   - Otomasyonun link yorumunu **sabitleme**. Sabitlenecek yorum, gerçek bir dinleyici sorusu ve bizim yanıtımız olmalı.
   - Link, telefon numarası, "takip et, geri takip ederim" yok.
3. **Hikâye anketi yanıtları:** gelen DM'ler yalnız kullanıcı tarafından okunur. Ajan mesaj okumaz.
4. **Otomatik yanıt yok.** Graph API yorum yanıtı teknik olarak mümkün, ama bu kanalın kuralı elle yanıt (`reference_olcum_yorum_api.md`).
5. **Kayıt:** gün sonunda `python elle_islem.py ekle --platform instagram --islem yorum_yaniti --ayrinti "<gönderi>: N yanıt"`.

### 3.6 Mevcut sorunlar ve düzeltmeler

| # | Sorun (kanıt) | Etki | Düzeltme | Kimde |
|---|---|---|---|---|
| S1 | **3 kopya ya da eski Reels canlı:** `Dc5vAXxgGIf`, `Dcv6i1PjYUy`, `Dcv5AiRgSsc` (bugün Chrome'da doğrulandı) | Özgünlük (aynı ses 3-4 kez), öneri uygunluğu | ⋯ → **Arşivle** (silme değil). `Dc-5CR9j2XO` kalır. 17 Eyl | **Kullanıcı, telefon** |
| S2 | Eski açıklamalarda `#AIMusic #YapayZekaMüzik #AIMusicChallenge` ve "yapay zeka ile üretilen" (en az 2 gönderi; kalan 6 eski gönderi okunamadı) | Kural dışı metin | S1 arşivi 2'sini kaldırır. Kalanları **toplu düzenleme yok** (R5: günde ≤3). 20 Eyl'de telefonda kalan 6 eski gönderinin açıklamasına bak; varsa günde ≤3 elle | **Kullanıcı, telefon** |
| S3 | AI beyan satırı 16/16 açıklamada yok | Beyan tutarsızlığı (profil etiketi var) | Yeni gönderilere otomatik gelir (`config.AI_BEYAN_SATIRLARI`). **Eskiler düzenlenmez**; profil etiketi hesap düzeyinde beyan | Otomasyon (yeniler) |
| S4 | Açıklamalarda `#keşfet #fyp #viral` | IG'de işlevsiz, jenerik | IG'ye özel hashtag seti (O1) | **Otomasyon** |
| S5 | Bio: latest.html 2. sırada, YouTube linkinde `?si=`. 512 ziyarete 9 dokunuş | Trafik kaybı | Sırayı değiştir, `?si=` temizle, bio metnini §3.2-6 taslağıyla güncelle | **Kullanıcı, telefon** (web'de yok) |
| S6 | Tek, jenerik öne çıkan | Profil ziyaretçisi yönlendirilmiyor | §3.2-5 yapısı | **Kullanıcı, telefon** |
| S7 | Takip 448 > takipçi 406 | Güven sinyali zayıf | **Toplu takipten çıkma yok** (toplu işlem deseni). İstenirse günde ≤10, ilgisiz hesaplar | Kullanıcı (isteğe bağlı) |
| S8 | 5 gerçek yorumun 5'i yanıtsız | Etkileşim sinyali | §3.5 rutini. İlk tur 17 Eyl | **Kullanıcı** |
| S9 | Izgara 16/16 tek şablon, 0 Carousel | Şablon tekrarı | §3.2 rotasyon + Carousel | Otomasyon (kapak düzeni) + kullanıcı (Carousel) |
| S10 | 13 Eyl: aynı pencerede 2 IG Reels (Kader + Sabah Senin); 5 Eyl'de 9 dk'da 5 Reels | R2 "toplu yükleme" | O2 | **Otomasyon** |
| S11 | Hikâye görüntülemesi %20,3 ama kaynağı belirsiz | Ölçüm | Telefonda Pano → Hikâyeler; hangi hikâyeler olduğunu not et | Kullanıcı |
| S12 | 30 günlük takipçi değişimi webde okunamadı | Hedeflerin temel çizgisi eksik | 20 Eyl haftalık okumada telefondan | Kullanıcı |

### 3.7 Otomasyon değişiklik önerileri (kod yazılmadı, yalnız öneri)

| # | Öneri | Dosya | Risk | Test |
|---|---|---|---|---|
| **O1** | **Instagram'a özel hashtag seti:** IG açıklamasında `#fyp #foryou #viral` yok; 3-5 etiket: marka + tür + Türkçe niş (`#türkçeşarkı`, `#şarkısözleri` gibi, trend notu tazelenerek). AI vurgulu etiket yok | `upload/social_text.py` (`build_caption` platform dalı), `config.py` hashtag sabitleri | Düşük. TikTok ve FB metnini kaydırmamalı (`pick_deterministic` tuzu değişmesin) | Mevcut caption testlerine "instagram çıktısında fyp yok, AI_BEYAN_SATIRLARI var, 'Suno' yok" + TikTok çıktısı bayt bayt aynı |
| **O2** | **R2 + R3 Instagram'da:** (a) `try_publish_pending` IG'de kayan 24 sa içinde yayın varsa ikinci konteyneri bekletsin (düşürmesin). (b) Yeni şarkının IG konteyneri YouTube T0'ın **ertesi golden-hour penceresine** göre geç açılsın (≤23 sa kuralı) | `upload/instagram_upload.py`, `auto_process.py`, önerilen `yayin_ritmi.py` | Orta. Konteyner bayatlama (23 sa), kuyruk tıkanması (`fix-pacing-starvation` dersi), `_is_fully_done` | Sahte saatle: aynı pencerede 2 bekleyen → 1 yayın, 1 bekleme; T0 + 18 sa senaryosunda konteyner yaşı <23 sa; bayat konteyner temizliği regresyonu |
| **O3** | **Carousel otomasyonu (Aşama 2, ilk ay elle sonrası):** kart üreticisi JPEG 1080×1350; `instagram_upload.publish_carousel()` çocuk konteyner ×5 → `CAROUSEL` → golden-hour drain; `turev_plani` E3 kaydı | Yeni `turev_kartlari.py`, `upload/instagram_upload.py`, `turev_takvimi.py`, `config.TUREV_KIT_AKTIF` | Orta. JPEG zorunlu, Netlify barındırmada 6 dosya, kısmi konteyner hatasında yarım Carousel olmaz ama çocuklar boşa yanar; müzik API'de yok | `--dry-run` + mock `requests`: 5 çocuk + 1 ebeveyn çağrısı, JPEG uzantısı, caption'da beyan satırı; bir çocuk `ERROR` → ebeveyn hiç oluşturulmaz; şalter kapalıyken sıfır çağrı |
| **O4** | **Hikâye API'si (düşük öncelik):** yeni Reels'ten 1 gün sonra `STORIES` ile kapak görseli | `upload/instagram_upload.py` | Orta-yüksek. Instagram Login'de desteği doğrulanmadı; link çıkartması, anket ve müzik API'de yok, yani elle hikâyeden zayıf. Otomatik hikâye "insan emeği" sinyali de vermez | Önce elle 4 hafta. Sonra tek hesapta tek deneme + `status_code` kontrolü. **Önerim: yapma** |
| **O5** | **Trial Reels API'si** | `upload/instagram_auth.py` (Facebook Login'e geçiş), `instagram_upload.py` | **Yüksek.** `trial_params` yalnız Facebook Login yolunda; token, izin ve sayfa bağlantısı baştan kurulur. Facebook kurulumundaki 3 gizli engel dersi | **Önerim: yapma.** Uygulamadaki anahtar yeterli |
| **O6** | **Salt okunur haftalık IG ölçümü:** görüntüleme, erişim, takipçi, kaydetme, paylaşım → haftalık rapora 3 satır (otomasyon yorumu yorum sayısından düşülür) | `weekly_report.py` (bağlı değil, `reference_olcum_yorum_api.md`), `upload/instagram_auth.py` kapsamı (`instagram_business_manage_insights`) | Düşük-orta. Yeni izin → yeniden yetkilendirme; token zaten ~31 Ekim'de doluyor (E-4) → **E-4 ile aynı oturumda** | Mock yanıtla rapor satırı; izin yoksa rapor düşmez, "IG ölçümü yok" satırı |
| **O7** | **`kanal_takvimi.json` IG türleri:** `instagram_hikaye`, `instagram_carousel` platform değerleri; "şarkı aynı gün ≤2 platform" kontrolü CLI'da | `turev_takvimi.py` | Düşük | Aynı şarkı + aynı gün 3. platform → uyarı |

Sıra önerisi: **O1 → O2** (21-27 Eyl kod haftası) → **O6** (E-4 ile 28 Eyl-4 Eki) → **O3** (ilk ay elle Carousel ölçümünden sonra, ≥ 13 Eki) → O7. **O4 ve O5 yok.**

### 3.8 Hedefler ve metrikler

Temel çizgi (13 Eyl, 30 gün): 406 takipçi · 4.597 görüntüleme · %64,3 takipçi olmayan · 512 profil ziyareti · 9 bağlantı dokunuşu · Reels medyan 97 izlenme / 7 beğeni · yanıtlanan gerçek yorum %0 · Carousel 0 · insan emeği içerik 0.
Takipçi değişimi temel çizgisi 20 Eyl'de eklenecek (S12). O gün hedefler düzeltilir.

| Metrik | 30 gün (13 Eki) | 60 gün (12 Kas) | 90 gün (12 Ara) |
|---|---|---|---|
| Canlı kopya ya da eski AI-hashtag'li gönderi | **0** (arşiv) | 0 | 0 |
| Yeni gönderilerde AI beyan satırı | %100 | %100 | %100 |
| Aynı gün > 1 IG Reels / 5 dk'da > 1 IG gönderisi | 0 (O2 sonrası) | 0 | 0 |
| Carousel (toplam) | 4 | 8 (O3 kararı) | 12 |
| İnsan emeği (hikâye dizisi + Reels) | 8 | 16 | 24 |
| Takipçi | 440 | 490 | 550 (Hediyeler için 500 eşiği [İ]) |
| 30 günlük görüntüleme | ≥ 5.000 | ≥ 6.000 | ≥ 7.500 |
| Takipçi olmayan oranı | ≥ %55 (Carousel takipçiye döner, düşmesi normal) | ≥ %55 | ≥ %55 |
| Bağlantı dokunuşu / profil ziyareti | ≥ %4 (S5 sonrası) | ≥ %5 | ≥ %6 |
| Yanıtlanan gerçek yorum (24 sa içinde) | %100 | %100 | %100 |
| Carousel başına kaydetme | ölçüm başlar | ≥ 3 | ≥ 5 |
| Trial Reels | — | anahtar kontrolü | 1.000 takipçi yoksa yok |

İzlenen iki oran (kanal çerçevesiyle aynı): **gönderi başına takipçi** ve **Carousel kaydetme / görüntüleme**. Tek gönderinin izlenmesi hedef değil; gürültü yüksek.

---

## 4. Kararlar (en fazla 5)

1. **Instagram'ın rolü "görsel kimlik ve söz vitrini" olsun mu?** Haftada 1 elle Carousel + 1-2 hikâye dizisi; otomatik Reels hacmi aynı, ama R2 (IG'de 24 sa'te ≤1).
   **Önerim: evet.** Carousel ve hikâye Suno kotasına dokunmaz, "insan emeği" sinyali ekler ve ızgaradaki şablon tekrarını kırar.
2. **Carousel ilk ay elle mi?** (`yayin_sonrasi_takvim_plani.md` karar 4 ile aynı.)
   **Önerim: evet, 4 Carousel elle.** Kaydetme ve takipçi dönüşümü ölçülünce (≥ 13 Eki) O3 API otomasyonu.
3. **Eski gönderilerin açıklamaları toplu düzeltilsin mi?** (AI hashtag'leri, `#fyp`, beyan satırı eksikliği)
   **Önerim: hayır.** Yalnız 3 kopya arşivlenir. Kalan eski gönderide kural dışı AI hashtag'i varsa günde ≤3 elle düzeltilir. Beyan satırı eskilere eklenmez; profil etiketi hesap düzeyinde beyan.
4. **"Yapay zeka tarafından oluşturulan profil" etiketi açık kalsın mı?** Açıklama satırından daha görünür.
   **Önerim: açık kalsın.** Gerçekçi vokal Meta'nın beyan istediği sınıfa en yakın durum [D]. Etiketi kapatıp yalnız satıra güvenmek, "zorunluluk dışına çıkmama" kararına ters düşer. Etiket öneri uygunluğunu düşürüyor mu, kanıt yok; 30 günlük takipçi olmayan oranı (%64) şimdilik düşürmediğini gösteriyor.
5. **`Bu Gece Kazandık` IG Reels'i 15 Eyl 18:05'te (bugünkü kod, aynı gün 4+ platform) mı çıksın, yoksa R3 gelene kadar IG'ye elle bekletme mi konsun?**
   **Önerim: bugünkü kodla çıksın, bekletme yazılmasın.** Elle state yazımı ve kuyruk riski, bir günlük kaydırmanın kazancından büyük. R3 21-27 Eyl kod haftasında O2 ile gelir. Yalnız hikâye paylaşımı 16 Eyl'e bırakılır.

---

## 5. Doğrulanmayanlar ve sınırlar

- Web ızgarası gizli sekmede 24 gönderinin 16'sını yükledi. Kalan 8'in açıklamaları okunmadı (ikisi doğrudan açıldı).
- Takipçi değişimi, içerik istatistik listesi ve hikâye ayrıntısı webde yüklenmedi (sekme arka planda). Chrome penceresi öndeydi ama etkin sekme başka bir ajanın TikTok Studio sekmesiydi, ona dokunulmadı.
- Hesap türü (içerik üreticisi / işletme), Trial Reels anahtarı, Broadcast kanalı ve para kazanma durumu **yalnız telefonda** görülür.
- Instagram yardım sayfaları JS ile yüklendiği için metinleri alınamadı. İlgili satırlar [İ] ya da [D] olarak işaretli.
- Hediye eşiği kaynaklarda çelişkili (500 / 5.000).
- `ek_platformlar_is_plani.md` henüz yok. Çıkınca Facebook Reels ile IG Reels'in aynı gün çakışması (R3) oradaki planla eşlenmeli.

## 6. Kaynaklar (2026-09-13)

- Instagram içerik yayınlama: <https://developers.facebook.com/docs/instagram-platform/content-publishing/>
- IG User Media (Carousel, STORIES, `trial_params`, `collaborators`): <https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media>
- Trial Reels (Creators): <https://creators.instagram.com/blog/instagram-trial-reels>
- Trial Reels duyurusu: <https://about.fb.com/news/2024/12/trial-reels-try-content-non-followers-first-see-what-perfoms-best/>
- Öneri uygunluğu (Creators blogu): <https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators>
- Öneri uygunluğu (Yardım): <https://help.instagram.com/653964212890722>
- Özgün içerik rehberi: <https://creators.instagram.com/original-content-guidelines>
- Özgün içerik hakkında: <https://help.instagram.com/1800814370401535/>
- Aggregator güncellemesi (30 Nisan 2026): <https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/>
- Meta AI etiketleme: <https://transparency.meta.com/governance/tracking-impact/labeling-ai-content/>
- Meta AI etiketleme duyurusu (2024): <https://about.fb.com/news/2024/02/labeling-ai-generated-images-on-facebook-instagram-and-threads/>
- AI profil etiketi (ikincil): <https://www.socialmediatoday.com/news/instagram-adds-ai-creator-labels/819267/>
- Hediyeler (resmî, okunamadı): <https://www.facebook.com/business/help/738469380549477>
- Hediyeler ülke genişlemesi (ikincil): <https://www.malaymail.com/news/tech-gadgets/2023/09/19/instagram-rolls-out-its-gifts-option-in-more-countries/91632>
- Notes (ikincil): <https://blog.hootsuite.com/instagram-notes/>
- Broadcast kanalları (ikincil): <https://www.sendible.com/insights/instagram-broadcast-channels>
- Carousel'e müzik (ikincil): <https://metricool.com/how-to-add-music-to-instagram-posts/>
- Collab gönderileri (ikincil): <https://www.inro.social/blog/instagram-collaboration-post-how-to-collab-add-after-posting-more>
