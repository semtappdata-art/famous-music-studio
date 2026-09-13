# YouTube CANLI YAYIN planı: Famous Music Studio

Hazırlanma: 2026-09-13 (Pazar) 07:50 · Bakış açısı: `sosyal-medya-danismani` (salt okunur; kod, state, git ve YouTube yazması yok)
Kanal: `UCbbcH8rtQTtz8R66jfKoSZg` (`docs/index.html`)
Eş belge: `tiktok_live_plani.md` (aynı gün). Ortak kararlar: **yüz yok · ilk format "Söz Defteri CANLI" · Pazar 21:00 (geçici) · haftada +2 insan emeği gönderisi.**

> **Kaynak güvenilirliği notu.** YouTube Help sayfaları bu ortamdan metin olarak okundu. Etiketler:
> - **[R]** resmî metin okundu (URL §9'da)
> - **[R-yok]** resmî sayfaya bakıldı, konu orada **yazmıyor**
> - **[İ]** ikincil kaynak ya da yaygın uygulama, **doğrulanmadı**
>
> **API okuması YAPILMADI.** Çalışma saati 07:47-07:50'ydi; ortak kota TR 10:00'da sıfırlanıyor. Abone sayısı §2a'da.
>
> **Türkiye farkı:** Super Chat/Super Stickers ve genişletilmiş YPP'nin ülke listesinde Türkiye **var** [R]. Canlı yayın açma koşullarında Türkiye'ye özgü bir fark bulunamadı.

---

## 0. Kısa sonuç

1. **YouTube'da masaüstünden (webcam ya da OBS) canlı yayın için abone eşiği yazmıyor** [R]. 50 abone eşiği yalnız **telefondan** yayında var. TikTok'un aksine YouTube'da kapıyı abone sayısı değil **hazırlık ve kitle** belirliyor.
2. Açma koşulları:
   - **telefonla kanal doğrulaması**
   - **son 90 günde canlı yayın kısıtlaması olmaması**
   - 16+ yaş
   İlk etkinleştirme **24 saate kadar** sürebiliyor, bu yüzden **bugün** açılmalı.
3. **Önerilen ilk format "Söz Defteri CANLI":** masaüstü OBS, **720p30 yatay**, yüz yok, gerçek ses. TikTok'la aynı format. Çoklu yayın **şimdilik yok**.
4. **7/24 "Famous Music Radio" döngüsü: HAYIR.** Ne bu makinede ne başka altyapıda (§3d).
5. **İlk canlı yayın önerisi: Pazar 11 Ekim 21:00.** Öncesinde iki özel test yayını yapılır, 9 Ekim ölçümü de bitmiş olur. Planlama **elle Studio'dan**, API'den değil.

---

## 1. Koşullar tablosu

### 1a. Canlı yayını açma

| Koşul | Resmî ifade (≤15 kelime) | Bizim durum | Eksik | Kaynak |
|---|---|---|---|---|
| Kanal doğrulaması (telefon) | "you need to verify your channel" | **Dolaylı kanıt: büyük olasılıkla yapılmış.** Özel küçük resim doğrulanmış hesap istiyor ve 11 Eyl'de 40 kapak API'yle yüklendi. **Teyit edilmedi** | Studio → Ayarlar → Kanal → **Özellik uygunluğu** | [R] 2474026 · [R] 72431 |
| 90 gün kuralı | "no live streaming restrictions in the past 90 days" | Canlı yayın hiç yapılmadı; kısıtlama bilinmiyor | Aynı ekran | [R] 2474026 |
| Topluluk kuralı ihtarı | "A strike will prevent you from live streaming for 14 days." | Bilinen ihtar yok. City Pulse'taki Content ID **hak talebidir, ihtar değildir** | Studio → Telif hakkı kontrolü | [R] 2474026 · `project_telif_itirazi_dj_set.md` |
| Yaş | "You must be at least 16 years old to live stream." | Hesap sahibi yetişkin varsayıldı | — | [R] 2474026 |
| İlk etkinleştirme bekleme | "Enabling a live stream for the first time may take up to 24 hours." | Etkinleştirilmedi (varsayım) | **Bugün** Studio → Oluştur → Canlı yayın başlat | [R] 2907883 |
| **Masaüstü: webcam** | "compatible with Chrome 60+ and Firefox 53+" · abone şartı yazmıyor | Makine uygun | Masa açısı kadraj (yüz yok) | [R] 9228389 |
| **Masaüstü: encoder (OBS, stream key)** | "copy the stream key from YouTube and paste it" · abone şartı yazmıyor | Makine uygun (§3c) | OBS kurulumu + 2 test | [R] 2907883 |
| **Mobil: abone eşiği** | "At least 50 subscribers." (güncel sayı 50) | **Bilinmiyor** (§2a); tahmin 50'nin altında | Yalnız telefondan yayın için gerekli | [R] 9228390 |
| Mobil: 50-1.000 arası | "We may limit the number of viewers on your mobile live stream" | — | Resmî metin bu kısıtı yalnız mobil için yazıyor | [R] 9228390 |
| Mobil: arşiv | "archived live stream will be set to private by default" | — | — | [R] 9228390 |
| Mobil: kısıtın kalkması | 1.000'e ulaşınca "may take several weeks to remove" | — | — | [R] 9228390 |
| Özellik düzeyleri | "phone verification, you'll get access to intermediate features" · sabitlenmiş yorum **gelişmiş** özellik | Plandaki "sabit yorum" adımı gelişmiş düzeye bağlı | Özellik uygunluğu ekranında "Gelişmiş" durumu | [R] 9891124 |
| Planlı yayın fragmanı | "more than 1,000 subscribers and no Community Guideline strikes" | Uygun değil | — | [R] 9228389 |

### 1b. Gelir özellikleri

| Özellik | Resmî koşul | Bizim durum | Eksik | Kaynak |
|---|---|---|---|---|
| YPP tam (reklam dahil) | 1.000 abone + 4.000 saat (12 ay) ya da 10M Shorts izlenmesi (90 gün) | Yok. Darboğaz abone (+28/28 gün → ~2,7 yıl, CLAUDE.md) | — | [R] 72851 |
| **Genişletilmiş YPP (fan funding)** | "500 subscribers with 3 valid public uploads in the last 90 days" + 3.000 saat ya da 3M Shorts | Yok. **Türkiye listede** | 500 abone + 3.000 saat | [R] 13429240 |
| Super Chat / Super Stickers | Fan funding asgari koşulları + uygun ülke (**Türkiye listede**). Liste dışı, gizli, çocuklara özel ve yaş kısıtlı içerikte yok | Uygun değil | Genişletilmiş YPP | [R] 9277801 |
| Kanal üyelikleri | YPP + "Some music channels may not be eligible for channel memberships". Müzik hak talepli videolar uygunsuz sayılır | Uygun değil. **Müzik kanalı notu bir risk** | Genişletilmiş YPP + temiz Content ID geçmişi | [R] 7636690 |
| Canlı yayın reklamları | YPP (tam) | Uygun değil | — | [R] 72851 |
| Yaş (gelir) | Super Chat sayfası yaşı ayrıca yazmıyor; ödeme hesabı 18+ [İ] | — | — | [R-yok] 9277801 |

**Sonuç:** 500 aboneden önce gelir özelliği yok. **Canlı yayın bu aşamada gelir değil, abone ve etkileşim aracı.**

### 1c. Canlı içerik kuralları

| Kural | İfade / durum | Bizim için anlamı | Kaynak |
|---|---|---|---|
| Önceden kaydedilmiş içeriği "canlı" diye yayınlamak | Spam politikasında ve canlı yayın kısıtlama sayfasında **ayrı madde yok** [R-yok] | Açık yasak bulunamadı. Ama gelir politikası "mass-produced, generic, repetitive" içeriği dışlıyor, TikTok'ta ise bu açık ihlal. **Yapılmaz** | [R-yok] 2801973, 2853834 · [R] 1311392 |
| **Premiere ile farkı** | Premiere: "watch and experience a new video together in real time". Hazır video, geri sayım, canlı sohbet. Shorts premiere edilemez | Hazır içeriği birlikte izletmenin **doğru** aracı Premiere; canlı yayın canlı insan içindir | [R] 9080341 |
| 7/24 döngü / "lofi radyo" | Resmî sayfalarda ayrı madde yok [R-yok]. İkincil kaynak: kısa döngü "fastest way to get flagged" [İ]. 12 saati aşan yayın arşivlenmeyebilir [R] | §3d: **HAYIR** | [R-yok] 1311392 · [R] 6247592 · [İ] upstream.so |
| Şablon / toplu AI içerik | "AI-generated content made with generic or unoriginal templates" gelire uygun değil | Kanalın ana riski. Canlı insan katkısı bu riski **düşüren** nadir araçlardan biri | [R] 1311392 |
| AI müzikle yayın | Canlı yayında AI müziği yasaklayan madde yok [R-yok]. Beyan sayfası "AI generated music"ı örnek sayıyor | Kendi şarkımızı çalmak serbest; **beyan gerekli** kabul edilir | [R] 14328491 |
| AI ses (TTS, klon) ile sunum | Canlı yayına özgü madde yok [R-yok] | Kararla uyumlu: sunucu **gerçek kişi sesi**. TTS ve avatar yok (TikTok planıyla aynı) | — |
| **Content ID (canlı)** | "A placeholder image may replace your live stream"; içerik kalırsa yayın kesilir ya da sonlandırılır | Kendi AI çıktımız da eşleşebilir (City Pulse "Bring Me To Life"). **Kesinti canlı yayın kısıtı riski taşır** | [R] 3367684 |
| Content ID (arşiv) | "Content ID claims are only made after you complete your live streams" (arşivlenirse) | Arşiv sonradan hak talebi alabilir; bu, YPP'de üyelik uygunluğunu etkiler | [R] 3367684 |
| Canlı yayında telif ihtarı | "Your active live stream gets a copyright strike" → kısıtlama | DJ set ve telif işaretli parça **çalınmaz** | [R] 2853834 |
| **`containsSyntheticMedia` canlıda** | Beyan sayfası yalnız yükleme akışını anlatıyor [R-yok]. `liveBroadcast` kaynağında AI beyan alanı **yok** [R] | API'den canlı yayına beyan yazılamaz. Önerilen yol: (1) Studio canlı kurulumunda "AI kullanımı" alanı varsa **Evet** (**doğrulanmadı**, ilk kurulumda bakılır); (2) ilk 3 dakikada **sözlü beyan**; (3) arşiv videosunda Studio → AI kullanımı **Evet**. Açıklamaya yazılı satır **eklenmez** (karar). "Suno" geçmez | [R-yok] 14328491 · [R] liveBroadcasts kaynağı |
| Başka kanaldan yayın | "prohibited from using another channel to live stream" | Kısıtı ikinci kanalla atlatma yok | [R] 2853834 |
| Otomatik sohbet | Görev kuralı | Hermes, sesli asistan ve otomatik yanıt canlı sohbete **bağlanmaz** | `reference_olcum_yorum_api.md` |

### 1d. Yaptırımlar

| Yaptırım | Tetikleyen | Süre | Kaynak |
|---|---|---|---|
| Canlı yayın erişiminin kapanması | Topluluk kuralı ihtarı ya da **canlı yayının kaldırılması** | İhtarda 14 gün, ihtar aktif kaldıkça. Açma koşulu "son 90 günde kısıtlama yok" | [R] 2853834, 2474026 |
| Telif ihtarı | Aktif yayında telif ihtarı; eşleşen yayın | İhtar süresince | [R] 2853834 |
| Yayının kesilmesi | Content ID eşleşmesi kalırsa | Anında | [R] 3367684 |
| Günlük yayın sınırı | Sınıra ulaşılırsa | 24 sa sonra sıfırlanır | [R] 2853834 |
| Gelir yaptırımı (YPP'ye girince) | inauthentic / reused içerik | Sınırlı gelir → askı → kanal kapatma | [R] 1311392 · `project_inauthentic_content_riski.md` |

### 1e. API: planlamayı API mi yapsın?

| Konu | Durum | Kaynak |
|---|---|---|
| Uç noktalar | `liveBroadcasts` (insert/bind/transition/update) + `liveStreams` (insert). Alanlar: `enableAutoStart`, `enableAutoStop`, `latencyPreference`, `enableDvr`, `monitorStream` | [R] liveBroadcasts kaynağı |
| Kapsam | `youtube` ya da `youtube.force-ssl`. Mevcut token'da `force-ssl` **var**, yeniden yetkilendirme gerekmez | [R] liveBroadcasts.insert · CLAUDE.md |
| **Kota maliyeti** | Resmî kota tablosu canlı yayın metotlarını **LİSTELEMİYOR**. 13 Eyl'de ham sayfa tarandı; tabloda yalnız `channels.list` 1, `videos.update` 50, `thumbnails.set` 50 gibi değerler var. Metot sayfalarında da "quota" geçmiyor. Yaygın kabul: yazma 50, list 1 [İ, **doğrulanmadı**] | [R-yok] determine_quota_cost |
| AI beyanı | `liveBroadcast`'ta alan yok; API yolu beyanı **yapamaz** | [R] |
| Sohbet API'si | `liveChatMessages.list` sürekli yoklama istiyor, kota tüketir | [R] liveChatMessages.list |

**Öneri: API ile planlama YOK, elle Studio.**
- Haftada bir yayın var, elle kurulum ~3 dk sürüyor.
- AI beyanı API'den yapılamıyor; Studio yolu zaten şart.
- Kota defteri 12→13 Eyl gecesi ortak havuzun bittiğini gösterdi (`upload/youtube_kota.py`, `YOUTUBE_KOTA_YAYIN_REZERVI = 950`). Maliyeti doğrulanmamış yeni bir çağrı ailesi bu havuza girmesin.
- Kalıcı stream key (Studio "önceki ayarlar") OBS'ye bir kez girilir. **Dosyaya, log'a ve depoya yazılmaz.**

---

## 2. Mevcut durum (salt okunur)

### 2a. Abone sayısı: **bilinmiyor**
- Saat 07:47'ydi (10:00'dan önce), bu yüzden `channels.list` **çağrılmadı**.
- State ve dosyalarda **mutlak abone alanı yok**. `upload/saglik_durum.json → haftalik_ozet_olcum` yalnız izlenme tutuyor (`izlenme: 3843`).
- Bilinen tek veri: `olcum_temel_cizgi.json` (11 Eyl), 28 günde **+29 / −1**, 7 günde **+18 / −1**.
- **VARSAYIM (doğrulanmadı):** ilk yükleme 31 Ağu. 28 günlük pencere kanalın neredeyse tüm ömrünü kapsıyor, yani 11 Eyl'de ~28-30 abone, bugün ~30-40. 50'ye mesafe 10-20 abone; son 7 günün hızıyla 1-2 hafta, 28 günlük ortalamayla 2-3 hafta.
- **10:00'dan sonra 1 birimle okunur:** `channels.list(part=statistics, mine=True)`, `upload/youtube_auth.py` servisiyle. Token yazdırılmaz. Sonuç §4e'deki okuma tablosuna işlenir.

### 2b. Doğrulama ve özellik uygunluğu: **API göstermiyor**
Kullanıcı **Studio → Ayarlar → Kanal → Özellik uygunluğu**'ndan üç satır okuyacak:
1. Standart / orta düzey (telefon) / gelişmiş: hangisi "etkin"?
2. "Canlı yayın" durumu: etkin / beklemede / kısıtlı.
3. Topluluk kuralları ve telif hakkı durumu: ihtar var mı?

Bu çalışmada tarayıcı kullanılmadı.

### 2c. Performans (`olcum_temel_cizgi.json`, 14 Ağu - 11 Eyl; state 12 Eyl)

| Ölçüt | Değer | Canlı yayın için anlamı |
|---|---|---|
| 28 gün | 4.286 izlenme · 3.608 dk · ortalama izleme %23,1 · 12 yorum | Sohbet eden kitle çok küçük |
| **Cihaz** | **TV 2.257 dk (%62,6)** · mobil 1.047 · masaüstü 226 · tablet 74 | İzleme **arka planda ve TV'de**. Canlı yayın **yatay 16:9** olmalı; arşiv TV'de izlenir |
| Abone olan / olmayan | 187 / 4.082 izlenme (%4 abone) | Kitle keşiften geliyor; planlı yayın sayfası tek başına izleyici getirmez |
| Trafik (izlenme / dk) | Shorts 1.494 / 52 · İlgili video 1.104 / 759 · Kanal 707 / 689 · Playlist 212 / **725** · Bitiş ekranı 10 / 40 | Playlist izlenme başına en uzun (3,4 dk). Shorts çok izleniyor ama süre ~0. Bitiş ekranı neredeyse hiç çalışmıyor |
| State izlenme (12 Eyl) | 21 video grubu: uzun 2.383, Shorts 1.460 | — |
| İyi gidenler (`suno_kalite_onerileri.md`) | Uzun formatta **akustik ve arabesk** (Son Kez 317, Yeraltı 240, Yürek Yarası 231). Shorts'ta **hiphop** (Sokaklar Beni Tanır 250) | İlk yayında çalınacak ≤3 parça buradan |
| DJ | Video başına 8,2× izlenme süresi (CLAUDE.md) | Canlı DJ cazip, ama telif riski en yüksek (§3b-c) |
| Shorts → abone | Shorts'ta 0 abone (`denetim_bulgulari_2026-09-12.md`) | Abone Shorts'tan değil, uzun format ve bağlantılardan geliyor |

---

## 3. Plan

### 3a. Eşiğe ve kitleye ulaşma (yalnız organik)

**İki hedef:**
- **(1) Teknik eşik:** masaüstü için yok; 50 abone yalnız mobil yedek içindir.
- **(2) Anlamlı kitle:** ilk yayında ≥5 eşzamanlı izleyici. Asıl hedef bu.

**Yok:** abone satın alma, abone-için-abone, bot yorum, "abone olana şarkı".

`yayin_sonrasi_takvim_plani.md` E1/E2/E6 işleri sıraya kondu:

| # | Adım | Veriye dayanak | Ne zaman | Yayın takvimiyle uyum |
|---|---|---|---|---|
| 1 | **Shorts → "İlgili video":** her Shorts kendi uzun videosuna bağlanır (Studio, elle) | Shorts 1.494 izlenme / 52 dk; 0 abone | Yeni Shorts'ta T0+0-1 sa (E1). Eski 21 Shorts: Pazartesi bakım yuvasında haftada 5'er | E1 aynen; toplu API düzenlemesi YOK |
| 2 | **Bitiş ekranı:** son 5-20 sn'de "Kesintisiz Dinle" listesi + **Abone ol** + en iyi eşleşme | Bitiş ekranından 10 izlenme; playlist 3,4 dk/izlenme | Yeni uzun videolarda T0+0-1 sa; eskilerde "şablon içe aktar" | `youtube_giris_denetimi` Adım 4 |
| 3 | **Oynatma listesi:** kanal ana sayfasında "Türkçe Şarkılar — Kesintisiz Dinle" ilk rafta | TV payı %62,6 + playlist verimi | Aşama 0 | Mevcut `_tum_sarkilar` |
| 4 | **Sabitlenmiş yorum** (her yeni uzun videoda): bir soru, Aşama 2'den 2 hafta önce "Pazar 21:00 canlı Söz Defteri" satırı | 28 günde 12 yorum | E1 | Özellik "gelişmiş" değilse yapılamaz (§1a) |
| 5 | **Topluluk gönderisi:** söz alıntısı + anket (E2), haftada 1. Canlı haftasında duyuru anketin yerine geçer | Anket düşük maliyetli etkileşim | T0+1 gün (E2) | Topluluk sekmesinin bu kanalda açık olduğu **doğrulanmadı** |
| 6 | **Yorumlara elle yanıt:** her yorum 24 sa içinde, yoruma özgü metinle | Geçmişte 11 yanıtsız yorum birikti | Her gün | Otomatik yanıt YOK |
| 7 | **Kanal ana sayfası:** abone olmayanlara öne çıkan video en iyi akustik ya da arabesk şarkı | İzlenmelerin %96'sı abone olmayanlardan | Aşama 0 | — |
| 8 | **Çapraz yönlendirme:** TikTok/IG bio ve hikâyede "YouTube'da canlı Söz Defteri" (ayda 1-2) | TikTok planı §3a-6 | Aşama 1 | TikTok caption'ında dış link YOK |
| 9 | **+2 insan emeği gönderisi** (Söz Defteri + kulis) YouTube Topluluk'ta da | TikTok kararı | Haftalık | YouTube'a **video** yüklemez; 52 sa tabanına ve türev YouTube tavanına girmez |

**Kaçınılacak:** canlı yayını duyurmak için **yeni Shorts yüklemek.** Bu, video yükleyen bir türev olur, haftada 1'lik tavanı yer ve video sayısını artırır.

### 3b. Format seçenekleri ve riskleri (yüz yok, gerçek ses)

| # | Format | Nasıl | Kural riski | Telif riski | inauthentic riski | Değerlendirme |
|---|---|---|---|---|---|---|
| **a** | **"Söz Defteri CANLI"** | Masa üstü kadraj (defter, eller) + mikrofon. Sohbetten tema al, canlı nakarat yaz, ≤3 kısa dinleme | Düşük | Düşük (yalnız temiz parçalar) | **En düşük** | **İLK FORMAT.** TikTok'la aynı akış (§5b) |
| b | **Yeni şarkı dinleme partisi** | Premiere ya da canlı yayın | Premiere düşük. Yalnız müzik çalan canlı yayın orta | **Canlıda yüksek:** yeni parça Content ID'den geçmemiş, kesinti riski var | Orta | **Ayrı etkinlik YAPILMAZ.** Premiere doğru araç, ama Data API'de premiere alanı yok. Şarkı otomasyon hattının (uyumluluk kapısı, md5, golden-hour) **dışında** elle yüklenmek zorunda kalır; bu kanalda elle yükleme kopya kazasına yol açtı. Canlıda yeni şarkı çalmak da eşleşme riski taşıyor. **Öneri:** dinleme (a)'nın içinde kalsın, yalnız ≥48 sa public ve hak talebi almamış şarkıyla. Premiere ileride yalnız aylık **derleme** için düşünülsün (DJ karantinasıyla çakıştığı için ayrı karar) |
| c | **DJ Famous canlı miks** | Gerçek kişi, gerçek kontrol, kendi kataloğumuz | Orta | **Yüksek.** City Pulse'ta eşleşmelerin %65'i ilk 6 dakikadaydı ("Bring Me To Life"). Canlıda eşleşme **yayını keser** ve kısıt getirebilir; canlıda itiraz yolu yok | Düşük | **Aşama 3'te bile şartlı:** yalnız 2 sa karantinadan temiz çıkmış ve Studio'da hak talebi olmayan parçalar. City Pulse parçaları hiç çalınmaz. DJ Famous'un **ayrı canlı onayı** ve önce **özel (private)** test yayını şart |
| d | **7/24 "Famous Music Radio"** | Döngü | **Yüksek** (canlı insan yok; 12 sa arşiv sınırı) | Yüksek (7/24 eşleşme penceresi) | **Maksimum** | **HAYIR** (§3d) |
| ✗ | Hazır render mp4'ünü "canlı" oynatmak | — | Gri alan, yanıltıcı | — | Maksimum | **ASLA** |
| ✗ | AI avatar / TTS sunucu | — | Yüksek | — | Yüksek | **Yok** |

**Çoklu yayın (TikTok + YouTube aynı anda):**
- **Kural:** YouTube'da başka platforma eşzamanlı yayını yasaklayan madde bulunamadı [R-yok]; ikincil kaynaklar serbest diyor [İ]. TikTok'ta da resmî yasak bulunamadı (TikTok planı).
- **Teknik yol:** OBS tek çıkıştan iki RTMP hedefine, eklentiyle ya da ücretli çoklu yayın servisiyle [İ].
- **Engeller:**
  1. TikTok stream key herkese açık değil ve önce LIVE Studio geçmişi gerekiyor (TikTok planı §1a). Bugün **imkânsız.**
  2. Biçim çakışıyor: YouTube kitlesi TV'de (yatay), TikTok dikey. İki tuval iki kodlama demek; i5-1035G1'de QSV ile iki kodlama **sınırda** [İ].
  3. Tek kişi iki sohbeti okuyamaz; iki tarafta da "canlı insan katkısı" düşer.
  4. YouTube'un tek sohbetli yatay + dikey çift biçimi 16 Eyl 2025'te "Soon" diye duyuruldu [R blog]. Bu kanalda açık olduğu **doğrulanmadı**.
- **Öneri: çoklu yayın yok, ayrı günler** (§4b).

### 3c. Teknik kurulum

**Yol: masaüstünde OBS (encoder) → YouTube.**
- Abone eşiği yok; mobilin izleyici sınırı ve özel arşiv kısıtı da yok.
- Yedek: Chrome'dan webcam yayını [R 9228389].

**Makine: i5-1035G1 (4 çekirdek / 8 iş parçacığı) · 7,8 GB RAM · MX330 (NVENC yok) · Intel Quick Sync var**

| Ayar | Değer | Gerekçe |
|---|---|---|
| Kodlayıcı | **QuickSync H.264** (OBS'de "QSV"), x264 değil | MX330'da NVENC yok [İ]. x264 bu 4 çekirdeği 720p30'da bile doldurur |
| Çözünürlük | **1280×720, 30 fps**; tuval de 720p (ölçekleme yok) | Kadraj durağan bir masa. 1080p30 QSV'de çalışabilir ama ısı, RAM ve render çakışmasıyla marj kalmaz. Defter yazısı TV'de 720p'de okunur |
| Video bit hızı | **CBR 4.000 kbps** (ilk testte yayın sağlığı "iyi" değilse 3.000) | YouTube CBR ve çözünürlüğe göre aralık öneriyor [R 2853702]. Sayfadaki aralık içinde, upload hızına göre ayarlanır |
| Anahtar kare | **2 sn** | "Recommended 2 seconds" [R] |
| Ses | **AAC 128 kbps, 44,1 kHz stereo** | "128-Kbps for stereo" · "44.1 KHz" [R] |
| Protokol | **RTMPS** | Şifreli [R] |
| Gecikme | **Düşük gecikme** (ultra düşük değil) | Sohbetle etkileşim; ultra düşük tamponu azaltır |
| DVR | Açık | [R] 9854503 |
| Upload | ≥6-8 Mbps sabit (bit hızının ~1,5-2 katı) [İ]; mümkünse kablo | Canlıdan önce hız testi |

**Mikrofon:**
- İlk yayında kulaklık mikrofonu ya da eldeki USB mikrofon; ikinci testten sonra gerekirse USB kardioid.
- OBS filtre sırası: gürültü azaltma (RNNoise) → gürültü kapısı → sıkıştırıcı → limitör (−1 dB).
- **Kulaklık zorunlu.**

**Kamera (yüz yok):** üstten masa açısı.
- En ucuz yol telefonu USB webcam olarak kullanmak (bazı Android sürümlerinde yerleşik [İ]) ya da kollu bir USB webcam.
- Dizüstü kamerası masayı göremez.

**Sahne düzeni (OBS, 3 sahne):**
1. **"Açılış":** masa kamerası tam ekran + alt bant "Söz Defteri CANLI · Famous Music Studio" ve amblem.
2. **"Yazım":** masa kamerası %75 + sağ şerit, sohbetten gelen 3 kelime. Şerit **elle yazılan** metin kaynağı, bot değil.
3. **"Dinleme":** kapak (`cover.png`) + ses dalgası + köşede küçük masa kamerası. **Kamera köşede kalır, ekran hiç durağan olmaz.**

**Ses yönlendirme:**
- Müzik yalnız yerel dosyalardan ve ayrı bir oynatıcıdan çalar.
- OBS "Uygulama Ses Yakalama" **yalnız o oynatıcıyı** alır; bildirim sesleri yayına sızmaz.
- Konuşurken müzik kısılır (ducking).

**Yerel kayıt:** OBS'de "yayın + kayıt" açık (MKV, sonra remux).
- 12 saatin altındaki yayın otomatik arşivleniyor [R 6247592].
- Yerel kopya yine de iki işe yarar: Content ID kesintisinde kanıt ve Söz Defteri gönderisi için ham malzeme.

**Güvenlik:**
- OBS'de **ekran/masaüstü yakalama kaynağı YOK**; token, `.json`, e-posta ve Telegram görünmesin.
- Stream key yalnız OBS profilinde durur, ekran görüntüsü alınmaz.

**Bu makineye özgü çakışmalar:**
- **Render:** saatlik `auto_process.py`, yeni bir şarkıyı render ederken ~17 dk CPU'yu %100 kullanıyor (`yayin_sonrasi_takvim_plani.md` ölçümü). Yayın sırasında render başlarsa QSV kodlaması kare düşürür.
  - Canlıdan 30 dk önce `gorev_izleri/auto_process.log`'da süren koşu olup olmadığına bakılır.
  - Yayın haftasında Pazar 18:00-22:00'ye yeni bir şarkının public anı (golden-hour `publishAt`) düşmüyor mu, kontrol edilir.
  - **Görevleri durdurmak önerilmez:** geri açmayı unutma riski var ve sessiz duruş bu deponun en sık arızası.
- **Cuma 18:00 DJ koşusu:** Cuma akşamı yayın yok.
- **Priz şart** (`project_pil_ve_zamanlayici.md`).
- **RAM 7,8 GB:** yayında Chrome, Claude Code oturumları ve Hermes/Jarvis HUD kapalı.
- **Isı:** ince bir dizüstü 60 dk QSV yayını kaldırır [İ]; altına yükseltici koy, havalandırmayı açık tut.

### 3d. 7/24 "Famous Music Radio": NET ÖNERİ **HAYIR**

İzleme süresinin %62,6'sının TV'den gelmesi bu fikri cazip gösteriyor, ama:

1. **inauthentic:** yayında canlı insan yok, aynı katalog döngüde dönüyor. Gelir politikasındaki "repetitive or mass-produced" ve "generic or unoriginal templates" tarifine birebir uyuyor [R 1311392]. Kanalın en büyük riski tam olarak bu.
2. **Katalog küçük:** 19 şarkı ≈ 60 dk, yani her saat aynı şarkılar. Kısa döngü, ikincil kaynaklarda bile en hızlı işaretlenme sebebi [İ].
3. **Content ID:** 7/24 açık bir eşleşme penceresi demek. Tek eşleşme yayını keser ve canlı yayın kısıtı getirir. **"Son 90 gün" koşulu yüzünden Söz Defteri CANLI da kapanır** [R 3367684, 2474026].
4. **Arşiv ve ölçüm:** 12 saati aşan yayın arşivlenmeyebilir, DVR sınırlı kalır [R 6247592].
5. **Bu makine sürdürülemez:** dizüstü, pil ve uyku, saatlik ffmpeg render'ı, 7,8 GB RAM, ısı. Bulut altyapısı ücretli ve riski değiştirmiyor.
6. **Kazanç yok:** YPP olmadığı için reklam da yok.
7. **Kota:** döngüyü API'yle yönetmek (`transition`, sohbet yoklaması) maliyeti doğrulanmamış çağrılarla ortak havuzu yer.

**TV kitlesi için yerine:**
- "Türkçe Şarkılar — Kesintisiz Dinle" oynatma listesi ana sayfanın ilk rafında ve bitiş ekranında (§3a-2/3).
- Aylık **derleme** (`derleme.py`: küratörlüklü, 40 dk).
- DJ setleri.

**Yeniden değerlendirme şartı:** YPP + 60'tan fazla şarkılık katalog + 3 ay ihlalsiz canlı yayın geçmişi. O zaman bile insan sunumlu "dinleme gecesi" tercih edilir.

### 3e. Moderasyon

YouTube canlı sohbet araçları [R 9826490]:
- **Engellenen kelimeler** (Studio → Ayarlar → Topluluk). İlk liste:
  - küfür ve taciz kalıpları
  - "sub4sub", "abone ol bana", "takip et geri takip"
  - link ve telefon kalıpları: ".com", "t.me", "wa.me", "bit.ly", telefon numaraları
  - "suno" (marka kararı). Sohbette sorulursa sözlü yanıt: "AI destekli üretim, sözler ve seçim bizim."
- **"Uygunsuz olabilecek mesajları incelemeye al":** açık.
- **Yavaş mod:** 10 sn; küçük kitlede sohbeti öldürmesin.
- **Yalnız abonelere sohbet:** kapalı, çünkü kitlenin %96'sı abone değil. Taciz olursa yayın sırasında açılır.
- **Moderatör:** 1 güvenilir gerçek kişi, standart moderatör. Yoksa inceleme kuyruğu ve zaman aşımı elle yönetilir.
- **Sohbet tekrarı:** açık.
- **Bot yok:** Hermes, sesli asistan, otomatik selamlama, otomatik yanıt ve sohbet API yoklaması kullanılmaz.

---

## 4. Takvim

### 4a. Aşamalar

| Aşama | Zaman | Hedef | Çıkış ölçütü |
|---|---|---|---|
| **0: bugün** | 13 Eyl (Pazar) | Doğrulama, canlı yayını etkinleştirme (24 sa), abone okuması | Özellik uygunluğundaki 3 satır okundu; canlı yayın "etkin"; abone sayısı 10:00 sonrası 1 birimle okundu; OBS kurulu |
| **1: hazırlık ve kitle** | 14 Eyl → 10 Eki | Organik adımlar (§3a) + 2 özel test yayını | 2 test "iyi" yayın sağlığıyla bitti; Söz Defteri gönderileri başladı; mobil yedek için ≥50 abone |
| **2: ilk canlı** | **Pazar 11 Eki 21:00** (öneri) | 55 dk Söz Defteri CANLI | ≥25 dk yayın; kesinti ve uyarı yok; ≥5 eşzamanlı izleyici |
| **3: düzenli** | 18 Eki'den itibaren | Haftada 1 sabit yuva; ayda 1 dinleme ağırlıklı yayın; DJ yalnız ayrı onayla | 4 hafta ihlalsiz; yayın başına abone kazanımı ölçüldü |

**Neden 11 Ekim?**
- 9 Ekim kapak ölçümü penceresi kirlenmez.
- Abone okumaları (27 Eyl, 11 Eki) TikTok planıyla aynı günlere düşer.
- 4 haftalık organik hazırlık ve iki özel test için iki Pazar kalır.

Hazırlık erken biterse 4 Ekim de mümkün (karar 1).

### 4b. Haftalık program (TikTok'la çakışmasız)

**Öneri: çoklu yayın YOK, ayrı günler.**
- **Şimdi** (TikTok LIVE kapalı, ≥1.000 takipçi yok): YouTube canlı yuvası **Pazar 21:00-22:00.** Kullanıcının seçtiği saat; alışkanlık kurulur.
- **TikTok LIVE açıldığında:** Pazar 21:00 TikTok'a geçer (TikTok kararı), YouTube **Çarşamba 21:00**'e kayar. Bu saat Cuma DJ koşusundan, Pazartesi raporundan ve Perşembe dağıtım vardiyasından uzak.

| Gün (TR) | Saat | İş | Platform |
|---|---|---|---|
| Pazartesi | 09:00+ | Haftalık özet + bakım: 5 eski Shorts'a "İlgili video", bitiş ekranı | YouTube Studio (elle) |
| Salı | 20:30 | Söz Defteri #N (insan emeği 1) | TikTok + YouTube Topluluk (metin/görsel) |
| Çarşamba | — | (TikTok LIVE açılınca YouTube canlı yuvası) | — |
| Perşembe | 15-25 dk | Dağıtım vardiyası; canlı haftasında L−3 Topluluk duyurusu | TikTok / YouTube |
| Cuma | 18:00 | DJ koşusu (otomatik). **Canlı yok** | — |
| Cumartesi | 13:00 | Kulis / A-B sorusu (insan emeği 2) | TikTok + YouTube Topluluk anketi |
| **Pazar** | **21:00-22:00** | **YouTube canlı** (Aşama 2'den itibaren; Aşama 1'de **özel** testler) | YouTube |
| Pazar | 22:15 | Defter kapanışı + canlı analizleri | elle |

### 4c. İlk 4 hafta

| Hafta | Tarih | Yapılacak |
|---|---|---|
| **H0** | 13 Eyl (Pazar) | §6 Aşama 0 kontrol listesi. 10:00 sonrası tek `channels.list` (1 birim) → abone sayısı. Canlı yayını etkinleştir. OBS'yi kur, profil: 720p30 QSV |
| **H1** | 14-20 Eyl | §3a adım 1, 2, 3 ve 7: ilk 5 Shorts'a İlgili video, ana sayfa rafı. İlk Topluluk anketi. **Pazar 20 Eyl 21:00: özel test #1** (15 dk, private; ses, kadraj ve yayın sağlığı) |
| **H2** | 21-27 Eyl | 5 Shorts daha. Söz Defteri #2. **27 Eyl: abone okuması #2** → büyüme hızı. **Pazar 27 Eyl: özel test #2** (40 dk tam akış provası, render çakışması provası dahil) |
| **H3** | 28 Eyl-4 Eki | Kalan Shorts. Engellenen kelimeler + moderatör. **4 Eki (Pazar): planlı yayın sayfası** oluşturulur (11 Eki 21:00) ve L−7 duyurusu yapılır |
| **H4** | 5-11 Eki | 8 Eki Perşembe: L−3 Topluluk. 9 Eki: ölçüm randevusu (`olcum_temel_cizgi.py`). 10 Eki Cumartesi: L−1 kontrol listesi. **11 Eki: sabah Reporting API'yi aç (5 dk), abone okuması #3, İLK CANLI 21:00** |

### 4d. Türev takvimi: `youtube_live_duyuru` türü? (öneri, KOD YOK)

**Öneri: EKLENMESİN.**
- `turev_plani` her şarkının T0'ından türüyor ve T0+21'de kapanıyor. Canlı yayın ise **kanal düzeyinde** ve haftalık.
- Şarkıya bağlanırsa her yeni şarkı bir canlı duyurusu doğurur. Bu, kaçınılan şablon desenin kendisi.
- YouTube'daki duyuru araçları (planlı yayın sayfası, Topluluk, sabit yorum) **video yüklemiyor**; korunması gereken bir türev tavanı yok.
- TikTok planındaki `tiktok_live_duyuru` önerisi dinleme partisine bağlıydı. YouTube'da dinleme ayrı bir etkinlik olmadığı için karşılığı yok.

**En küçük uygulanabilir adımlar:**
- `haftalik_is_akisi.md`'ye elle bir "canlı haftası" satırı.
- Canlı yayının kendisi `elle_islemler.jsonl`'a (platform `youtube`). Sözlükte `canli_yayin` işlemi yoksa eklenmesi **ayrı küçük bir kod işi** (TikTok planıyla ortak).
- İleride: `turev_takvimi.py` çakışma kontrolü "Pazar 20:00-22:30'a yeni şarkı public'i düşmesin" bilgisini tanıyabilir. Bugün yalnız elle kontrol.

### 4e. Ölçüm

| Metrik | Nereden | Ne zaman | Karar eşiği (öneri) |
|---|---|---|---|
| Abone sayısı | `channels.list` 1 birim (10:00 sonrası) ya da Studio | 13 Eyl, 27 Eyl, 11 Eki; sonra 2 haftada bir | Hız → Aşama 2 tarihi |
| **En yüksek eşzamanlı izleyici** | Studio → canlı yayın analizi | Her canlı | İki yayın üst üste <3 → yuva ya da saat değişir |
| **Ortalama izleme süresi** (canlı + arşiv) | Aynı | Her canlı + 7 gün sonra | Canlıda <2 dk → akış değişir (müzik payı ayarlanır) |
| **Yayın başına abone kazanımı** | Studio canlı analizi | Her canlı | <2 → sıklık iki haftada bire iner |
| Sohbet mesajı / tekil sohbetçi | Aynı | Her canlı | Etkileşim sinyali; hedef değil |
| Arşiv videosunun izlenme süresi | Studio; ileride Analytics `liveOrOnDemand` boyutu (**doğrulanmadı**) | Haftalık özet günü | Arşiv TV'de izleniyorsa public kalır |
| Kesinti / uyarı / hak talebi | Studio → Telif hakkı + bildirimler | Her canlıdan sonra ve +48 sa | **Tek kesinti → o parça listeden çıkar. Tek ihtar → canlıya ara, format gözden geçirilir** |

| Okuma | Tarih | Abone | Kaynak |
|---|---|---|---|
| #1 | 13 Eyl (10:00 sonrası) | _bilinmiyor, doldurulacak_ | `channels.list` |
| #2 | 27 Eyl | — | — |
| #3 | 11 Eki | — | — |

---

## 5. İlk canlı yayın (11 Eki 21:00)

### 5a. Format
**"Söz Defteri CANLI":** masaüstü OBS, yatay 720p30, masa kadrajı, gerçek ses, sohbetten canlı nakarat, **≤3 kısa dinleme.**

Çalınacak her şarkı:
- YouTube'da ≥48 saattir public olmalı
- Studio → Telif hakkı'nda hak talebi taşımamalı
- `telif_*`, `kopya_notu` ya da `yayin_beklet` taşımamalı

Aday parçalar: Son Kez (akustik), Yürek Yarası (arabesk düet), Sokaklar Beni Tanır (hiphop).

### 5b. Akış (55 dk)

| Dakika | Bölüm | İçerik | Kural notu |
|---|---|---|---|
| −10-0 | Bekleme ekranı | "Açılış" sahnesi, "21:00'de başlıyoruz"; **müzik yok** | Content ID riski sıfır |
| 0-3 | Açılış | Selam; "bugün sizinle bir nakarat yazıyoruz"; **sözlü beyan:** "sözler bizden, müzik AI destekli" | İlk andan konuşma |
| 3-10 | Tanışma | Sohbeti oku, isimleri an; "nereden izliyorsun, TV'den mi?" | TV kitlesine hitap |
| 10-14 | Parça 1 | 1 dk "bu satırın hikâyesi" + Son Kez | "Dinleme" sahnesi, kamera köşede |
| 14-30 | **Canlı söz yazımı** | Sohbetten 3 kelime → defterde 4 satırlık nakarat; seçenekleri sesli oku, sohbette oylat | Yayının çekirdeği: sürekli hareket ve ses |
| 30-34 | Parça 2 | Yürek Yarası | Müzik payı ≤%40 |
| 34-45 | Soru-cevap | "Nasıl üretiyorsunuz?" → süreç anlatılır, **araç adı söylenmez** | Beyan tutarlılığı |
| 45-50 | Nakarat final | Son hâli oku; "bir sonraki şarkıda kullanalım mı?" | Söz Defteri gönderisine kanca |
| 50-55 | Kapanış | Sokaklar Beni Tanır'ın ilk 30 sn'si + teşekkür + "Kesintisiz Dinle" listesi + **sonraki canlı günü** | "Abone ol karşılığında…" teşviki yok |

Toplam müzik ≈ 7 dk / 55 dk (%13).

### 5c. Duyuru takvimi (L = 11 Eki)

| Zaman | Yer | İçerik |
|---|---|---|
| L−7 (4 Eki) | **Planlı yayın sayfası** (Studio → Oluştur → Canlı yayın başlat → Planla; kalıcı stream key) | **Başlık:** `Söz Defteri CANLI #1 · Sizinle Nakarat Yazıyoruz \| Famous Music Studio`. **Açıklama:** 2 satır, insan odaklı; AI satırı yok, "Suno" yok. **Küçük resim:** defter + başlık, 16:9, ≤2 MB. İzleyici hatırlatıcı kurabilir [R 2907883] |
| L−7 | Son uzun videonun sabit yorumu | "Pazar 21:00 canlı: nakaratı sizinle yazıyoruz → [planlı yayın linki]" |
| L−3 (8 Eki, Perşembe) | **Topluluk gönderisi** | Anket: "Nakaratın teması ne olsun?" (3 seçenek) + link. O haftanın E2 anketinin yerine |
| L−3 | TikTok Söz Defteri gönderisi (insan emeği) | Sonunda sözlü "Pazar YouTube'da canlı". Caption'da dış link yok |
| L−1 (10 Eki) | Instagram hikâye | Geri sayım çıkartması + profil bio linki |
| **Shorts duyurusu** | **YOK** | Yeni video yüklemesi olur (§3a sonu); fragman için 1.000 abone gerekiyor [R] |
| L+0 22:00 | Arşiv | **Liste dışı** kalır → Studio: Telif hakkı kontrolü + AI kullanımı "Evet" → karar 3 |
| L+1 | TikTok + YouTube Topluluk | Yazılan nakarat "Söz Defteri #N" olur (yeni çekim, canlı kaydı değil) |

Telegram ve Bluesky duyurusu yok.

---

## 6. Kontrol listeleri

**Aşama 0 (bugün, 13 Eyl)**
- [ ] 10:00'dan sonra tek `channels.list(part=statistics)` → abone sayısı (token yazdırılmaz; başka API çağrısı yok)
- [ ] Studio → Ayarlar → Kanal → **Özellik uygunluğu**: standart / orta / gelişmiş durumu (ekran görüntüsü)
- [ ] Aynı ekranda **Canlı yayın**: etkin değilse Oluştur → Canlı yayın başlat (24 sa bekleme başlar)
- [ ] Studio → **Telif hakkı**: City Pulse dışında hak talebi ya da ihtar var mı; Topluluk kuralları ihtarı yok mu
- [ ] Kanal ana sayfası: "Kesintisiz Dinle" ilk rafta; abone olmayanlara öne çıkan video seçildi
- [ ] OBS kurulumu: 720p30, QSV, CBR 4.000, 2 sn anahtar kare, AAC 128 kbps / 44,1 kHz. Stream key yalnız OBS'de
- [ ] Suno aboneliğinin ticari kullanım koşulları canlı yayını da kapsıyor mu, bir kez kontrol et (`suno_prompt_hazirlik.md` lisans notu)
- [ ] Okumaları `elle_islemler.jsonl`'a yaz: `python elle_islem.py sozluk` ile uygun işlemi bul, sonra `ekle --platform youtube ...`

**Canlıdan 1 gün önce**
- [ ] ≤3 şarkı: her biri ≥48 sa public, Studio'da hak talebi yok, `telif_*` / `kopya_notu` / `yayin_beklet` yok
- [ ] Engellenen kelimeler, "incelemeye al", yavaş mod 10 sn, moderatör
- [ ] Planlı yayın sayfası: başlık ve açıklamada "Suno" yok; **"AI kullanımı" alanı varsa Evet**
- [ ] 5 dk **özel** test: ses seviyesi, ducking, kadrajda kişisel bilgi yok, yayın sağlığı "iyi"
- [ ] Defter, kalem, akış çıktısı, kulaklık; telefon-webcam şarjda

**Canlıdan 30 dk önce**
- [ ] Priz takılı; altlık ve havalandırma
- [ ] `gorev_izleri/auto_process.log`: BAŞLADI'sı olup BİTTİ'si olmayan koşu yok; Pazar 18-22 arası yeni şarkı public'i yok
- [ ] Chrome, Claude Code, Hermes/Jarvis HUD kapalı; Rahatsız Etme açık; Telegram ve ntfy sessiz
- [ ] Upload hız testi ≥6 Mbps
- [ ] OBS'de ekran yakalama kaynağı yok; yerel kayıt açık

**Canlı sırasında**
- [ ] İlk 3 dk'da sözlü beyan
- [ ] 2 dk'dan uzun durağan ekran ya da sessizlik yok
- [ ] Bot yok, kayıtlı video yok, abonelik karşılığı teşvik yok
- [ ] Yer tutucu görsel ya da kesinti uyarısı gelirse parça **hemen** durur ve bir daha çalınmaz

**Canlıdan sonra (aynı gece ve +48 sa)**
- [ ] Studio canlı analizi → §4e metrikleri deftere
- [ ] Arşiv: Telif hakkı sekmesi; AI kullanımı **Evet**; +48 sa sonra görünürlük kararı (karar 3), deftere yazılır
- [ ] Ertesi günün Söz Defteri gönderisi planlandı

---

## 7. Kullanıcıya sorulacak kararlar

1. **İlk YouTube canlı yayın tarihi:** Pazar 11 Ekim 21:00 mı, hazırlık erken biterse 4 Ekim mi?
   **Önerim: 11 Ekim.** 20 ve 27 Eylül'de iki özel test yapılır, 9 Ekim ölçümü kirlenmez, abone okumaları TikTok planıyla aynı günlere düşer.
2. **İki platformun yuvası:** TikTok LIVE açıldığında aynı Pazar 21:00'de çoklu yayın mı, ayrı günler mi?
   **Önerim: ayrı günler.** Şimdilik YouTube Pazar 21:00'de. TikTok açılınca Pazar 21:00 TikTok'a geçer, YouTube Çarşamba 21:00'e kayar. Çoklu yayın bugün teknik olarak imkânsız (TikTok stream key yok); biçimler de çakışıyor (TV yatay, TikTok dikey) ve tek kişi iki sohbeti birden okuyamaz.
3. **Arşiv görünürlüğü:** canlı bitince arşiv public mi kalsın?
   **Önerim: 48 saat liste dışı, sonra Studio kontrolüyle public.** Telif hakkı temiz çıkıp AI kullanımı "Evet" yapıldıktan sonra açılsın. Arşiv kanala insan emeği taşıyan uzun bir video ekler, bu inauthentic riskine iyi gelir; ama hak talepleri yayından sonra geliyor [R 3367684].
4. **Kamera ve mikrofon:** para harcansın mı?
   **Önerim: iki test ücretsiz yapılsın.** Telefon USB webcam olarak, ses için kulaklık mikrofonu. İkinci testte ses zayıf çıkarsa yalnız bir USB kardioid mikrofon alınsın; kamera alınmasın.
5. **7/24 "Famous Music Radio" ve DJ canlı miksi kapalı kalsın mı?**
   **Önerim:** 7/24 kalıcı olarak kapalı; TV kitlesine oynatma listesi ve aylık derleme sunulsun. DJ canlı miksi Aşama 3'e kadar kapalı. Sonra yalnız şu üç şartla: DJ Famous'un ayrı canlı onayı, karantinadan temiz çıkmış parçalar ve önce özel test.

---

## 8. Doğrulanmayanlar
- Bugünkü abone sayısı; kanal doğrulamasının ve "gelişmiş özellik" durumunun gerçek hâli; canlı yayının etkin olup olmadığı.
- `liveBroadcasts` / `liveStreams` kota maliyeti (resmî tabloda yok).
- Studio'nun canlı yayın kurulumunda "AI kullanımı" alanı bulunup bulunmadığı.
- Topluluk (Posts) sekmesinin bu kanalda açık olduğu.
- Yatay + dikey tek sohbetli çift biçimin bu kanalda kullanılabilirliği (blog "Soon", 16 Eyl 2025).
- MX330'da NVENC olmadığı (ikincil kaynak) ve QSV'nin 60 dk yayında ısıl davranışı.
- Arşiv için Analytics `liveOrOnDemand` boyutu.
- Telefonun USB webcam modu (cihaza ve Android sürümüne bağlı).
- Masaüstü yayında 50-1.000 abone arası kanallara izleyici sınırı konup konmadığı (resmî metin bunu yalnız mobil için yazıyor).

## 9. Kaynaklar

**YouTube Help (resmî, 2026-09-13'te okundu):**
- Canlı yayına başlama (doğrulama, 90 gün, 16 yaş, 14 gün): https://support.google.com/youtube/answer/2474026
- Mobil canlı yayın (50 abone, 24 sa, izleyici sınırı, özel arşiv): https://support.google.com/youtube/answer/9228390
- Webcam ile canlı yayın (tarayıcı, fragman 1.000 abone): https://support.google.com/youtube/answer/9228389
- Encoder ile canlı yayın (24 sa, stream key, planlama): https://support.google.com/youtube/answer/2907883
- Encoder ayarları ve bit hızları: https://support.google.com/youtube/answer/2853702
- Canlı yayın ayarları (gecikme, DVR): https://support.google.com/youtube/answer/9854503
- Canlı yayın arşivi (12 saat): https://support.google.com/youtube/answer/6247592
- Canlı yayın kısıtlamaları: https://support.google.com/youtube/answer/2853834
- Canlı yayında telif / Content ID: https://support.google.com/youtube/answer/3367684
- Özellik düzeyleri / uygunluk: https://support.google.com/youtube/answer/9891124
- Özel küçük resim (doğrulama): https://support.google.com/youtube/answer/72431
- Canlı sohbet moderasyonu: https://support.google.com/youtube/answer/9826490
- Premiere: https://support.google.com/youtube/answer/9080341
- YPP genel: https://support.google.com/youtube/answer/72851
- Genişletilmiş YPP (500 abone, Türkiye): https://support.google.com/youtube/answer/13429240
- Super Chat / Super Stickers uygunluğu (Türkiye): https://support.google.com/youtube/answer/9277801
- Kanal üyelikleri: https://support.google.com/youtube/answer/7636690
- Kanal para kazanma politikası (inauthentic / reused): https://support.google.com/youtube/answer/1311392
- Spam ve yanıltıcı uygulamalar: https://support.google.com/youtube/answer/2801973
- Değiştirilmiş / sentetik içerik beyanı: https://support.google.com/youtube/answer/14328491
- Dikey canlı yayınlar: https://support.google.com/youtube/answer/13822251

**Google Developers (resmî):**
- Kota maliyeti tablosu: https://developers.google.com/youtube/v3/determine_quota_cost
- liveBroadcasts kaynağı: https://developers.google.com/youtube/v3/live/docs/liveBroadcasts
- liveBroadcasts.insert: https://developers.google.com/youtube/v3/live/docs/liveBroadcasts/insert
- liveStreams.insert: https://developers.google.com/youtube/v3/live/docs/liveStreams/insert
- liveChatMessages.list: https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list

**YouTube Blog:** Canlı yayın güncellemeleri (16 Eyl 2025, çift biçim "Soon"): https://blog.youtube/news-and-events/live-updates/

**İkincil (doğrulanmamış):**
- 7/24 döngü riski: https://upstream.so/blog/24-7-live-stream-on-youtube-no-obs/ · https://blog.livereacting.com/how-to-create-a-24-7-lofi-radio/
- Çoklu yayın: https://streamscharts.com/news/multistreaming-guide-2026-rules-explained · https://streamyard.com/blog/how-to-multistream-to-youtube-twitch-tiktok-facebook-and-more
- MX330 / NVENC: https://obsproject.com/forum/threads/obs-nvenc-nvidia-geforce-mx350-support-or-not.155290/

**Depo içi (salt okundu):**
- **Belgeler:** `CLAUDE.md`, `tiktok_live_plani.md`, `youtube_giris_denetimi_2026-09-13.md`, `yayin_sonrasi_takvim_plani.md`, `suno_kalite_onerileri.md`, `haftalik_is_akisi.md`, `suno_prompt_hazirlik.md` (lisans notu)
- **Veri:** `olcum_temel_cizgi.json`, `projects|dj_sets|derlemeler/*/state.json` (izlenme alanları), `upload/saglik_durum.json`
- **Kod ve ayar:** `upload/youtube_kota.py`, `config.py` (`YOUTUBE_KOTA_YAYIN_REZERVI`), `docs/index.html` (kanal id)
- **Hafıza:** `project_inauthentic_content_riski.md`, `project_telif_itirazi_dj_set.md`, `feedback_ai_beyani_suno_yok.md`, `feedback_studio_web_kalici_onay.md`, `project_pil_ve_zamanlayici.md`, `reference_olcum_yorum_api.md`

## Kullanıcı kararları (2026-09-13)

Kullanıcı "tüm işlemleri sen yap" dedi; önerilen kararların hepsi kabul edildi:

1. İlk YouTube canlı yayını **11 Ekim 2026, 21:00**, 55 dk, "Söz Defteri CANLI", yüz gösterilmeden.
2. TikTok LIVE açılınca yayınlar **ayrı günlerde**: TikTok Pazar 21:00, YouTube Çarşamba 21:00. Çoklu yayın yok.
3. Yayın kaydı **48 saat liste dışı** kalır, Studio kontrolünden sonra herkese açılır.
4. İlk iki test **ücretsiz ekipmanla** yapılır: telefon webcam olarak, ses için kulaklık mikrofonu.
5. **7/24 yayın kalıcı olarak kapalı**, DJ canlı miksi Aşama 3'e kadar kapalı.

Sıradaki adımlar:
- Studio → Ayarlar → Kanal → Özellik uygunluğu kontrolü ve canlı yayın etkinleştirme: Claude, Chrome'dan (kalıcı onay).
- Abone okuması: TR 10:00'dan sonra 1 birim.
