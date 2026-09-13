# TikTok LIVE planı: @famousmusicstudio

Hazırlanma: 2026-09-13 · Bakış açısı: `sosyal-medya-danismani` (salt okunur; kod, state ve git değişikliği yok)
Kapsam: LIVE açma koşulları, bu koşulları oluşturma planı, LIVE formatları ve riskleri, teknik kurulum, takvim.

> **Kaynak güvenilirliği notu.** TikTok'un resmî Destek, Topluluk Kuralları ve LIVE Center sayfaları
> JavaScript ile yükleniyor. Bu ortamdan metin olarak okunamadılar; sayfa gövdesi boş geldi. Aşağıda
> iki tür kaynak var:
> - **[R] resmî metin okundu:** TikTok Müzik Hizmet Şartları, TikTok Newsroom, TikTok LIVE Creator Networks.
> - **[R-arama] / [İ]:** resmî sayfanın arama motoru özeti ya da ikincil kaynak. Bunlar **doğrulanmamış**
>   sayılmalı. Kullanıcı uygulamada Profil → ☰ → Creator araçları → LIVE ekranından teyit etmeli.
>
> Türkiye'ye özel resmî bir fark bulunamadı. Resmî destek metni takipçi eşiği için "bölgeye göre
> değişebilir" diyor. Türkçe ikincil kaynaklar "16 yaş ile yayın, 18 yaş ile hediye" diyor. TikTok
> Newsroom ise yayın sunmak için 18 yaş diyor. Güvenli varsayım: **18+.**

---

## 1. Koşullar tablosu

### 1a. Hesap uygunluğu

| Koşul | Resmî ifade / değer | Bizim durum | Eksik | Kaynak |
|---|---|---|---|---|
| Yaş (LIVE açma) | "mindestens 18 Jahre alt … um einen Livestream zu hosten" | Hesap sahibi yetişkin varsayıldı, **doğrulanmadı** | Hesaptaki doğum tarihi 18+ olmalı | [R] Newsroom (aşağıda) |
| Takipçi eşiği | "1,000 followers to go LIVE (may vary across regions)" | **Bilinmiyor** (bkz. §2) | Muhtemelen büyük açık | [R-arama] About TikTok LIVE |
| Türkiye eşiği | Resmî TR sayfası okunamadı. Türkçe ikincil kaynaklar 1.000 diyor | — | Uygulamada teyit | [İ] Shopify TR |
| "1.000 hâlâ geçerli mi?" | Standart eşik 1.000. Bazı hesaplara daha düşük eşikle kademeli erişim verildiği iddiası var, **resmî değil** | — | Uygulamada "LIVE" düğmesi görünüyor mu, bakılmalı | [İ] demandsage |
| Hesap yaşı | İkincil kaynak: 30 gün (LIVE Studio için) | İlk gönderi 1 Eyl. 30 gün en geç Ekim başında dolar | Hesap açılış tarihi teyit | [İ] tiklivestudio |
| İhlal geçmişi | "account in good standing" | Bilinen ihlal yok. Ama 4-5 Eyl'deki dakikalar içinde 6'şar gönderi deseni risk | Studio → hesap durumu kontrolü | [R] Creator Networks |
| LIVE Gifts (hediye alma) | "at least 18 years old (or 19 in South Korea)" + bölge + iyi durum | Türkiye'de hediye özelliği ikincil kaynaklarda geçiyor | LIVE erişimi + 18+ | [R] Creator Networks; [R-arama] LIVE Gifts SSS |
| LIVE Subscription | Resmî eşik okunamadı. İkincil kaynaklar: 18+, düzenli LIVE geçmişi, bölgeye göre kademeli | Uygun değil | Aşama 3 sonrası | [İ] tiktokstats |
| Masaüstü: LIVE Studio | İkincil kaynak: 1.000 takipçi, 30 günlük hesap, son 180 günde en az bir 25+ dk LIVE, son 30 günde LIVE cezası yok | **Uygun değil.** Önce telefondan en az bir 25+ dk LIVE gerekiyor | Telefon LIVE geçmişi | [İ] tiklivestudio (resmî kılavuz okunamadı) |
| Masaüstü: stream key (OBS) | Herkese açık değil, ayrıca veriliyor. Anahtar oturum başına yenileniyor | Uygun değil | LIVE Studio geçmişi sonrası | [İ] hollyland |

### 1b. LIVE içerik kuralları

| Kural | İfade (≤15 kelime) | Bizim için anlamı | Kaynak |
|---|---|---|---|
| Önceden kaydedilmiş / döngü / tekrar yayın | "reproduced, rebroadcast, automated, or otherwise inauthentic forms of presentation" | Hazır videoyu, döngüyü ya da boru hattı render'ını "canlı" diye oynatmak **ihlal.** Öneri havuzundan (For You) ve para kazanmadan düşer | [R-arama] LIVE Monetization Guidelines |
| Uygunluk ölçütü | "authenticity, interaction, and creator participation" | Canlı konuşma, sohbete yanıt ve gerçek iş şart | [R-arama] aynı |
| Statik görsel | TikTok Shop LIVE kuralı: ekranın %50'sini aşan durağan içerik yasak | Shop kuralı ama tespit mantığının yönünü gösteriyor. **Kapak görseli + şarkı = statik yayın** | [İ-resmî] TikTok Shop kalite kuralları |
| "Yalnız müzik çalan" yayın | Ayrı bir madde okunamadı; üstteki üç kuralın kesişimi | **Yalnız şarkı çalan, insan bulunmayan, sabit kapaklı yayın = İHLAL.** Öneri dışı kalma ve LIVE'dan geçici men riski | Yukarıdaki üç satır |
| Gerçek insan | "creator participation" | Kullanıcının kendisi bulunmalı. Yüz zorunlu değil, **ses ve etkileşim zorunlu** sayılmalı | [R-arama] |
| AI ses / seslendirme | Shop kuralı: canlı yayında AI ile üretilmiş ses veya dış ses yok | Sunucu sesi **gerçek insan sesi** olmalı. TTS ya da klonlanmış ses kullanılmaz | [İ-resmî] TikTok Shop |
| AI avatar | Gerçekçi AI içerik etiketlenmeli, yanıltıcı olan yasak | AI avatarla "canlı sunucu" **önerilmez.** Hem etiket hem "creator participation" riski | [R-arama] Integrity & Authenticity |
| AI üretimi müzik çalmak | Ayrı bir LIVE yasağı bulunamadı | Kendi şarkını **dinletmek** mümkün. Ama yayının ağırlığı insan katkısı olmalı (sohbet, söz hikâyesi) | — |
| Telifli müzik | "You cannot use Sounds or Commercial Sounds in a live stream." | TikTok ses kütüphanesi (CML dahil) LIVE'da **kullanılamaz** | [R] Müzik Şartları |
| Kendi müziğin | "music … that you do not own, you must have all rights and permissions" | Sahip olduğun müzik serbest. Üretim aracındaki ticari kullanım hakkı abonelik planına bağlı (`suno_prompt_hazirlik.md` lisans notu). **Hakkın geçerli olduğu planı teyit et** | [R] aynı |
| Otomatik kesinti (Content ID benzeri) | Şartlar: şüpheli müzik kullanımında ses kısılabilir ya da kaldırılabilir; ses tanıma var | **City Pulse Set'in "Bring Me To Life" eşleşmesi** gösterdi ki çıktılar eşleşme alabiliyor. Telif işareti olan hiçbir parça LIVE'da çalınmaz | [R] aynı; `project_telif_itirazi_dj_set.md` |
| DJ set | Başkasının eserini miksleme hakkı yok. Kendi parçalarınla mikslemek hak olarak mümkün | DJ Famous yalnız **kendi kataloğumuzdan**, CANLI miksleyerek. Hazır set dosyasını oynatmak "rebroadcast" sayılır. City Pulse Set parçaları yok | [R] Müzik Şartları + [R-arama] LIVE kuralı |
| Beyan | Gerçekçi AI içerik etiketlenmeli | LIVE başlığında ya da sabit yorumda tek satır: "Söz: Famous Music Studio · Müzik ve vokal: AI destekli" + ilk dakikalarda sözlü beyan. **Üretim aracı adı geçmez** | `feedback_ai_beyani_suno_yok.md`, CLAUDE.md |
| Bot / otomasyon | TikTok Hizmet Şartları md. 5 | LIVE'da sohbet botu, otomatik yanıt, otomatik yayın **yok.** Hermes LIVE'a bağlanmaz | Görev tanımı |

### 1c. Yaptırımlar

| Yaptırım | Özet | Tetikleyen | Kaynak |
|---|---|---|---|
| Yayının durdurulması + LIVE'dan geçici men | İhlalde oturum durdurulabilir, geçici LIVE kısıtı gelir | Sahte canlı (döngü, kayıt), telifli müzik, topluluk kuralı ihlali | [İ] sociallyin |
| Para kazanma kısıtı | Uygulama içi uyarı, geçici ya da kalıcı para kazanma kısıtı | LIVE para kazanma kuralı ihlali (etkileşim/ödül manipülasyonu, orijinal olmayan içerik) | [R-arama] LIVE Monetization Guidelines |
| Kalıcı LIVE erişimi kaybı / hesap yasağı | Tekrarlanan ya da ağır ihlal, kısıtı atlatma girişimi | Tekrar | [İ] sociallyin |
| LIVE Studio'ya etkisi | Son 30 günde LIVE askısı, LIVE Studio erişimini engelliyor | Herhangi bir LIVE cezası | [İ] tiklivestudio |
| Sesin kısılması | Ses tanıma şüpheli müziği kısar | Eşleşen parça | [R] Müzik Şartları |

---

## 2. Mevcut durum (salt okunur)

### 2a. Takipçi sayısı: **bilinmiyor**
- `upload/tiktok_token.json` scope'u: `user.info.basic,video.upload`. **`user.info.stats` YOK.** Bu yüzden `user/info` çağrısı **yapılmadı** (token değeri okunmadı ve yazdırılmadı; yalnız scope alanına bakıldı).
- `tiktok_envanteri_2026-09-12.md` ve state dosyalarında takipçi alanı yok.
- **Kullanıcı bakacak:** TikTok Studio (web) → Analizler → Takipçiler. Toplam takipçi, son 7/28 gün net kazanım ve **takipçilerin etkin olduğu saatler.**

### 2b. İçerik performansı (1-12 Eyl, 30 gönderi, envanter)
- Toplam **6.171 izlenme · 103 beğeni · 2 yorum.** Gönderi başına medyan izlenme 160.
- En iyi iki gönderi **abart formatında**, 28-30 sn ve **golden-hour**'da: 6 Eyl 18:00 → 616, 6 Eyl 12:00 → 583. 45 sn'lik standart render'ların çoğu 100-180 bandında.
- 5 Eyl 03:29-03:34'teki 6 gönderi 137-397 aldı. Saat kötü olmasına rağmen fena değil, ama desen "dakikalar içinde toplu yükleme". Bu, inauthentic sinyalinin ta kendisi.
- **Yorum/izlenme oranı ≈ %0,03.** LIVE'ın temel yakıtı sohbet ve bugün sohbet eden bir kitle yok. Açık yalnız takipçi sayısında değil, **etkileşimde** de.
- Profil jenerik görünüyor: 14 herkese açık gönderinin başlığı yalnız `#FamousMusicStudio`, bir kısmında başlık içerikle uyuşmuyor.

### 2c. Eşiğe mesafe
- **Veri yok:** takipçi sayısı ve büyüme hızı bilinmiyor, tahmin yapılamaz.
- Yalnız ölçek fikri vermek için **VARSAYIM** (doğrulanmamış): haftada ~3.000 izlenme ve izlenmeden takipçiye %0,5-1 dönüşüm → haftada 15-30 takipçi → 1.000'e **8-15 ay.** Dönüşüm %2'ye çıkarsa ~4 ay.
- **Gerçek hesap:** Studio'dan (a) bugünkü takipçi ve (b) son 28 gün net takipçi okununca → `(1000 − a) / (b / 4)` = hafta.
- 27 Eyl ve 11 Eki okumalarıyla yeniden hesaplanır (§4c).

---

## 3. Koşulları oluşturma planı

### 3a. Takipçi büyümesi (yalnız organik)
**Yok:** takipçi satın alma, etkileşim grupları, takip-geri-takip, bot yorum, "hediye at" teşvikleri.

**İçerik formatları:**

| Format | Neden | inauthentic riski | Not |
|---|---|---|---|
| **Söz yazım süreci** (defter, eller, sesli anlatım: "bu satırı neden değiştirdim") | İnsan emeğini gösteren en net format; sözler gerçekten insan yazımı | **Düşürür** | Seri adı önerisi: "Söz Defteri #N". Eller + defter + ses, yüz yok |
| **Kulis** (kapak seçimi, tarz kararı, "A mı B mi?") | Küratörlük katmanını görünür yapar; soru formatı yorum getirir | Düşürür | Üretim aracının ekranı gösterilirse **araç adı ve logosu görünmesin** |
| **Nakarat kesiti** (mevcut kit, abart kalıbı) | Keşif motoru; en iyi iki gönderi bu formatta | Orta: **aynı kalıp art arda gelirse artar** | 28-30 sn, golden-hour, aynı şarkının ikinci kopyası yok |
| DJ Famous kısa miks anı | Gerçek kişi, gerçek miks | Düşük | Gerçek kişi onayı; yalnız kendi kataloğumuz |

**Paylaşım sıklığı: tavan değişmeli mi?**
- **Render gönderileri (şarkı kesiti) için tavan AYNEN kalsın:** günde 1, haftada 4, arada 36 sa (`config.TIKTOK_KIT_*`). Gerekçe: kanalın en büyük riski toplu üretilmiş görünmek; 4-5 Eyl desenini tekrar etmemek bu tavanın varlık sebebi.
- **Öneri: haftada +2 insan yapımı gönderi** (Söz Defteri / kulis) tavanın **dışında** sayılsın, toplam 6.
  - Aynı güne iki gönderi düşmez; render gönderisiyle arada en az 12 sa olur.
  - Gerekçe: bu gönderiler render değil. Riski azaltan içeriği riskin sayacına koymak ters etki yapar.
  - Bu bir kural önerisi; koda dokunulmadı (karar 4).
- **Web "Planla" akışı:**
  - Haftalık Perşembe dağıtım vardiyasında (`haftalik_is_akisi.md`) bir sonraki haftanın planı tek oturumda kurulabilir.
  - Planlama ekranının kaç gün ileriye izin verdiği uygulamada teyit edilsin ([İ] ~10 gün).
  - **Aynı oturumda planlamak sorun değil; yayın anları dağınık kalmalı.**

**Diğer büyüme araçları:**
1. **Yorumlara yanıt:** en ucuz kaldıraç. Her gönderinin ilk 2 saatinde elle yanıt. "Yoruma videoyla yanıt" Söz Defteri serisine içerik üretir. Otomatik yanıt **yok** (`reference_olcum_yorum_api.md`).
2. **Düet ve stitch açık:** web Planla ekranında her gönderide kontrol edilsin.
3. **Seriler ve oynatma listeleri:** "Söz Defteri", "Nakaratlar", "DJ Famous". Oynatma listesi özelliği hesapta açık değilse, en iyi 3 gönderi sabitlensin.
4. **Profil optimizasyonu:**
   - Bio tek satır, insan odaklı ve araç adı yok. Örnek: "Sözler bizden, müzik AI destekli · her hafta yeni şarkı".
   - Bio linki `famousmusicstudio.com/latest.html` (C3, doğrulanmadı). Link alanı hesapta görünmüyorsa (eşik olabilir, [İ]) YouTube/Instagram profil bağlantı alanları kullanılsın.
   - Sabitlenecek 3 gönderi: 616'lık gönderi (içerik Beni Bırakma), açık Küllerimden Geç gönderisi, ilk Söz Defteri.
5. **Profil hijyeni (büyüme itişinden önce):**
   - Envanterdeki belirsiz `#FamousMusicStudio` grubu ve 5 Eyl 03:29-03:34 kümesi için görünürlük kararı kullanıcıda (E-6).
   - Karar **içeriğe bakarak** verilmeli, başlığa göre değil.
   - Yapılan her değişiklik önceki durumuyla `elle_islemler.jsonl`'a yazılsın.
6. **Çapraz yönlendirme:**
   - YouTube uzun format ve Shorts açıklamalarına "TikTok: @famousmusicstudio" satırı.
   - YouTube Topluluk ve Instagram hikâyesinde ayda 1-2 "TikTok'ta Söz Defteri serisi" duyurusu.
   - TikTok açıklamalarına dış link **eklenmez** (CLAUDE.md, For You riski).
7. **Trend:** trend ses (D5) askıda, CML müziği işe yaramıyor. Trend **format** kullanılsın: soru/cevap, "bu satırı yazarken…".

### 3b. İnsan faktörü: LIVE format seçenekleri ve riskleri

Kural özeti: **yüz zorunlu değil; canlı insan katkısı zorunlu.** Ses, eller, gerçek zamanlı iş ve sohbete yanıt.

| # | Format | Nasıl | Kural riski | Telif riski | inauthentic riski | Değerlendirme |
|---|---|---|---|---|---|---|
| 1 | **Sesli sunum + eller** | Masa üstü kadraj: defter, kulaklık. Kullanıcı konuşur, sohbeti okur | Düşük | Yok | Düşük | **Temel format**; diğerleri bunun üstüne kurulur |
| 2 | **Stüdyo ekranı** (ses dosyası, kapak seçimi) | Ekran paylaşımı + mikrofon | Orta: ekran uzun süre durağan kalırsa "statik" sayılabilir; sürekli hareket ve anlatım şart | Düşük | Düşük | Telefonda sınırlı, **masaüstü aşamasında** (Aşama 3) |
| 3 | **Söz yazma / üretim sürecini canlı gösterme** | Sohbetten kelime ya da tema al, canlı söz yaz. Üretim aracı canlı kullanılırsa arayüzde **araç adı ve logosu görünmesin** | Düşük | Orta: yeni üretilen parça Content ID'den geçmemiş; tanıma yanlış eşleşebilir | **En düşük**: insan emeğinin canlı kanıtı | **En güçlü aday.** Üretim beklerken sohbet; uzun sessiz bekleme yok |
| 4 | **Dinleme partisi** (yeni şarkı ilk kez + sohbet) | Şarkı çalar; öncesinde ve sonrasında söz hikâyesi, sohbet | **Yüksek, eğer yalnız çalarsa.** Şarkılar arasında 2-3 dk konuşma; müzik yayının %40'ını geçmesin | Orta. **Kural: yalnız YouTube'da ≥48 sa public olup telif itirazı almamış şarkılar** | Orta | 1+3 ile birleşik iyi. Tek başına "şarkı çalma yayını" **yapılmaz** |
| 5 | **DJ Famous canlı miks** | Gerçek kişi, gerçek kontrol, kendi kataloğumuzdan parçalar | Orta: hazır set dosyası oynatılırsa "rebroadcast" | **Yüksek:** City Pulse Set ve telif işaretli her şey hariç; başkasının eseri asla | Düşük | DJ Famous'un kendisi seste veya görüntüde olmalı; **LIVE için ayrı onay.** Aşama 3 |
| ✗ | **Kapak görseli + şarkı listesi, kimse konuşmuyor** | — | **İHLAL**: rebroadcast/statik; öneri dışı, LIVE'dan geçici men | Yüksek | **Maksimum** | **ASLA** |
| ✗ | Boru hattı videolarını (render mp4) oynatmak | — | İHLAL (önceden kaydedilmiş) | — | Maksimum | **ASLA** |
| ✗ | AI avatar / TTS sunucu | — | Yüksek | — | Yüksek | **Yok** |

**LIVE'da çalınmayacaklar:**
- `telif_eser` / `telif_araliklari` taşıyan her proje (City Pulse Set)
- `kopya_notu` (Yeniden Doğacağım)
- `yayin_beklet`
- YouTube'da public olmayan ya da Content ID karantinasındaki her şey
- TikTok ses kütüphanesi

### 3c. Teknik hazırlık

**Önerilen sıra: telefon → LIVE Studio → (TikTok izin verirse) OBS.**

1. **İlk LIVE telefondan.** LIVE Studio için "son 180 günde 25+ dk LIVE" geçmişi gerekiyor ([İ]); bu geçmiş ancak telefonla kurulur. En sade ve en az arızalı yol da bu.
   - Dikey kadraj için telefon sehpası, üstten masa açısı.
   - Harici mikrofon (USB-C ya da yaka mikrofonu).
   - Şarkıyı ikinci cihazın hoparlöründen çalmak yankı yapar. Dinleme bölümünü kısa tut ya da masaüstü aşamasına bırak.
2. **LIVE Studio (Windows, erişim açılınca).** TikTok'un kendi aracı; stream key gerekmez. Sahne, ekran penceresi ve uygulama sesi yakalama var.
3. **OBS + stream key:** yalnız TikTok erişim verirse. Anahtar oturum başına yenileniyor ([İ]); **hiçbir dosyaya ve log'a yazılmaz.**

**Bu makine: i5-1035G1 · 7,8 GB RAM · MX330. Kaldırır mı?**
- **MX330'da NVENC donanım kodlayıcı YOK** ([İ] OBS forumu, Wikipedia NVENC). OBS'de NVIDIA kodlayıcı görünmez.
- **i5-1035G1 (Ice Lake) Intel Quick Sync (QSV) H.264 kodlayıcısına sahip.** OBS'de "QuickSync H.264" seçilir.
- **Sonuç: 720×1280 dikey, 30 fps, 2.500-3.000 kbps, QSV ile kaldırır.** 1080p60 ya da x264 (yazılım kodlama) **kaldırmaz.**
- **RAM 7,8 GB sınırda:** LIVE sırasında Chrome, Claude Code oturumları ve Hermes kapalı olsun.
- **Çakışma riski:**
  - Aynı makinede saatlik `auto_process.py` ffmpeg render'ı CPU'yu doldurabilir; Cuma 18:00'de haftalık DJ koşusu var.
  - Masaüstü LIVE Cuma akşamı yapılmasın.
  - LIVE öncesi `auto_process.log`'da süren bir render olup olmadığına bakılsın.
  - Görevleri LIVE için durdurmak **önerilmez:** geri açmayı unutma riski var ve sessiz duruş bu deponun en sık arızası.
- **Priz şart** (`project_pil_ve_zamanlayici.md`).
- **Upload:** en az 5 Mbps sabit ([İ]). LIVE öncesi hız testi; mümkünse kablo.

**Ses yönlendirme (masaüstü):**
- **Mikrofon:** USB mikrofon ya da kulaklık mikrofonu. OBS'de gürültü kapısı + sıkıştırıcı filtreleri.
- **Müzik:**
  - Yalnız kendi dosyalarımız, ayrı bir oynatıcıdan.
  - OBS "Uygulama Ses Yakalama" ile **yalnız o oynatıcı** yakalanır, masaüstü sesinin tamamı değil. Böylece Telegram/ntfy bildirim sesleri yayına sızmaz.
  - Konuşurken müzik kısılsın (ducking).
- **Kulaklık zorunlu** (geri besleme).

### 3d. Moderasyon ve güvenlik
- **Anahtar kelime filtresi** (200 kelimeye kadar, [R] Newsroom). İlk liste:
  - küfür/taciz kalıpları
  - "takip et geri takip", "hediye at"
  - link kalıpları (".com", "t.me", "wa.me") ve telefon numarası kalıpları
  - "suno": marka kararı. Sohbette sorulursa sözlü yanıt: "AI destekli üretim, sözler ve seçim bizim".
- **Moderatör** (LIVE başına 20'ye kadar, [R-arama]): ilk yayında güvenilir 1 gerçek kişi. Yoksa yorumlar "yalnız takipçiler".
- **Hermes / sesli asistan / bot:** LIVE sohbetine **bağlanmaz.** Otomatik selamlama, otomatik yanıt, "hediye teşekkür botu" yok. "Yalnız eşleşmiş Hermes" ayarı Telegram tarafına ait; TikTok LIVE'da hiçbir otomasyon yok.
- **Kişisel güvenlik:**
  - Kadrajda adres, zarf, pencere manzarası ya da ekran bildirimi görünmesin.
  - Masaüstünde **tek pencere** paylaşılır, tüm ekran değil (token, `.json`, e-posta).
- **Hediye isteme yok:** "hediye atana şarkı" gibi teşvikler "manipulates engagement or rewards" kapsamına girer.

---

## 4. Takvim

### 4a. Aşamalar

| Aşama | Zaman | Hedef | Çıkış ölçütü |
|---|---|---|---|
| **0: bugün** | 13 Eyl | Gerçek veriyi al, profili düzelt | Takipçi + etkin saatler okundu; bio ve sabitler yapıldı; 18+ ve hesap durumu teyit edildi |
| **1: eşiğe kadar** | 14 Eyl → takipçi ≥1.000 (tarih bilinmiyor) | Organik büyüme + etkileşim | Uygulamada "LIVE" düğmesi görünüyor |
| **2: ilk LIVE** | Eşikten sonraki ilk uygun Pazar | 45-60 dk telefon LIVE, "Söz Defteri CANLI" | ≥25 dk yayın; ihlal bildirimi yok |
| **3: düzenli LIVE** | Aşama 2'den 2 hafta sonra | Haftada 1 sabit yuva; ayda 1 dinleme partisi; LIVE Studio'ya geçiş | 4 hafta üst üste ihlalsiz; LIVE başına takipçi kazanımı ölçüldü |

### 4b. Haftalık program (Aşama 1)

> **Saatler VARSAYIM.** TikTok Studio → Analizler → Takipçiler → etkin saatler henüz okunmadı.
> Dayanak: `trend_hashtag_notlari.md` (TR 12:00-14:00 / 18:00-22:00) ve envanterdeki en iyi iki gönderi (12:00, 18:00).
> Analizler okununca bu tablo güncellenmeli.

| Gün (TR) | Saat | İş | Tür |
|---|---|---|---|
| Pazartesi | 19:00 | Nakarat kesiti (Planla) | render (tavan içi) |
| Salı | 20:30 | **Söz Defteri #N** | insan yapımı (+2 önerisi) |
| Çarşamba | 12:30 | Nakarat kesiti | render |
| Perşembe | 15-25 dk | Dağıtım vardiyası: önümüzdeki haftayı Planla ile kur, yorum turu | elle |
| Cuma | 18:30 | Nakarat kesiti ya da DJ Famous kesiti (Planla ile önceden kurulu) | render |
| Cumartesi | 13:00 | **Kulis** (A/B sorusu) | insan yapımı |
| Pazar | 20:00 | Nakarat kesiti (haftanın 4.'sü) | render |
| Her gün | gönderi +0-2 sa | Yorumlara elle yanıt | elle |

**Aşama 3 LIVE yuvası (varsayım): Pazar 21:00-22:00.**
- Pazar 20:00 gönderisi LIVE öncesi ısınma işlevi görür.
- Cuma akşamı DJ koşusundan ve Pazartesi raporundan uzak.
- Analizler başka bir saat gösterirse o kazanır.

### 4c. İlk 4 hafta

| Hafta | Tarih | Yapılacak |
|---|---|---|
| **H0** | 13 Eyl (Paz) | Studio → Analizler: takipçi, 28 gün net kazanım, etkin saatler (ekran görüntüsü + defter kaydı). Bio + 3 sabit. Hesap durumu ve 18+ kontrolü. Düet/stitch varsayılanı açık |
| **H1** | 14-20 Eyl | 4 render + ilk Söz Defteri (Salı) + ilk kulis (Cumartesi). Her gönderide 2 sa yorum turu. 17 Eyl Prş: E-6 işleriyle birlikte H2 planı Planla'ya |
| **H2** | 21-27 Eyl | Aynı ritim. Söz Defteri #2, gelen bir yoruma **video yanıtı** olarak. YouTube açıklamalarına TikTok mention satırı (yeni yüklemelerde, elle). **27 Eyl: ikinci takipçi okuması → ilk gerçek varış tahmini** |
| **H3** | 28 Eyl-4 Eki | Seri/oynatma listesi kontrolü. Instagram hikâyesinde tek "TikTok'ta Söz Defteri" duyurusu. Söz Defteri ile nakarat kesitinin takipçi dönüşümü karşılaştırması |
| **H4** | 5-11 Eki | 9 Eki ölçüm randevusuyla aynı hafta TikTok 28 gün karşılaştırması. **11 Eki: üçüncü takipçi okuması.** Karar: +2 insan yapımı gönderi sürsün mü, format ağırlığı değişsin mi. Eşiğe 8 haftadan az kaldıysa ilk LIVE hazırlığı (§5d) başlar |

**Bu 4 haftada LIVE yok.** Takipçi ≥1.000 olup düğme görünmeden LIVE planlanmaz.

---

## 5. İlk LIVE

### 5a. Önerilen format
**"Söz Defteri CANLI":** sesli sunum + eller + sohbetten canlı söz yazımı + en fazla 3 kısa dinleme.
- Telefon, masa üstü kadraj, yüz yok.
- Çalınacak her şarkı YouTube'da ≥48 sa public olmalı ve telif işareti taşımamalı.

### 5b. Akış şeması (55 dk)

| Dakika | Bölüm | İçerik | Kural notu |
|---|---|---|---|
| 0-3 | Açılış | Selam; "bugün sizinle bir nakarat yazıyoruz"; sözlü beyan: "sözler bizden, müzik AI destekli" | Boş bekleme yok; ilk andan konuşma |
| 3-10 | Tanışma | Sohbeti oku, isimleri an, "nereden dinliyorsun?" | Etkileşim sinyali |
| 10-14 | Parça 1 | 1 dk "bu satırın hikâyesi" + en iyi performanslı şarkılardan biri (ör. Beni Bırakma) | Şarkı boyunca sohbete sesli dönüş |
| 14-30 | **Canlı söz yazımı** | Sohbetten 3 kelime/tema al; defterde 4 satırlık nakarat; seçenekleri sesli oku, oylat | Yayının çekirdeği: sürekli hareket + ses |
| 30-34 | Parça 2 | Farklı tarzdan bir şarkı | Müzik payı ≤%40 |
| 34-45 | Soru-cevap | "Nasıl üretiyorsunuz?" → süreç anlatılır, **araç adı söylenmez** | Beyan tutarlılığı |
| 45-50 | Nakarat final | Nakaratın son hâli; "bir sonraki şarkıda kullanalım mı?" oylaması | Sonraki Söz Defteri gönderisi için kanca |
| 50-55 | Kapanış | Parça 3'ün ilk 30 sn'si + teşekkür + bir sonraki LIVE günü/saati | Hediye isteme yok |

Toplam müzik ≈ 10 dk / 55 dk (%18). **Yayın 25 dk'nın altına düşmesin** (LIVE Studio geçmişi).

### 5c. Duyuru takvimi (LIVE günü = L)

| Zaman | Kanal | İçerik |
|---|---|---|
| L−7 gün | TikTok **LIVE Event** | Etkinlik oluştur (başlık, saat). Etkinlik sayfasından yayın, planlanan saatin 10 dk yakınında başlatılabiliyor ([R-arama]). Özellik hesapta yoksa duyuru videosu yeterli |
| L−3 gün | TikTok duyuru videosu | Söz Defteri formatında 20-30 sn: "Pazar 21:00'de nakaratı sizinle yazıyoruz". Etkinlik varsa videoya bağlanır. Render tavanına sayılmaz |
| L−2 gün | YouTube Topluluk | Saat + "TikTok'ta @famousmusicstudio" |
| L−1 gün | Instagram hikâye | Geri sayım çıkartması + TikTok profil bağlantısı |
| L+1 gün | TikTok | LIVE'da yazılan nakarat → "Söz Defteri #N" (LIVE kaydı değil, yeni çekim) |

Telegram ve Bluesky duyurusu yok.

### 5d. Kontrol listeleri

**Aşama 0 (bugün)**
- [ ] Studio → Analizler → Takipçiler: toplam, 28 gün net, etkin saatler (ekran görüntüsü)
- [ ] Ayarlar: hesaptaki doğum tarihi 18+
- [ ] Hesap durumu: ihlal/uyarı yok
- [ ] Bio tek satır (araç adı yok), link alanı, 3 sabit gönderi
- [ ] Düet/stitch/yorum varsayılanları açık
- [ ] Okumaları `elle_islemler.jsonl`'a yaz (`python elle_islem.py sozluk` ile uygun işlem adını seç, sonra `ekle --platform tiktok ...`)

**LIVE'dan 1 gün önce**
- [ ] ≤3 şarkı seçildi; her biri YouTube'da ≥48 sa public ve `telif_*` / `kopya_notu` / `yayin_beklet` yok
- [ ] Anahtar kelime filtresi girildi
- [ ] Moderatör eklendi ya da yorumlar "yalnız takipçiler"
- [ ] Aynı kurulumla 5 dk'lık kamera kaydıyla ses/ışık denemesi (yayınlanmaz)
- [ ] Mikrofon, kulaklık, sehpa, şarj
- [ ] Defter, kalem, akış şeması çıktısı

**LIVE'dan 30 dk önce**
- [ ] Priz
- [ ] Rahatsız Etme açık; Telegram/ntfy sessiz
- [ ] Kadrajda kişisel bilgi yok
- [ ] Upload ≥5 Mbps
- [ ] (Masaüstünde) Chrome ve ağır uygulamalar kapalı; `auto_process.log`'da süren render yok

**LIVE sırasında**
- [ ] İlk 3 dk'da sözlü beyan
- [ ] 2 dk'dan uzun sessiz ve durağan ekran yok
- [ ] Hediye isteme yok, bot yok, kayıtlı video yok
- [ ] Ses kısılma uyarısı gelirse o parça hemen durdurulur ve bir daha çalınmaz

**LIVE'dan sonra (aynı gün)**
- [ ] LIVE analizleri okunup deftere yazıldı (§6b)
- [ ] Uyarı/kısıtlama bildirimi kontrolü
- [ ] Ertesi günün Söz Defteri gönderisi Planla'ya kuruldu

---

## 6. Türev takvimiyle bağlantı ve ölçüm

### 6a. `turev_takvimi.py`'ye "tiktok_live" türü? (öneri, KOD YOK)

**Öneri: LIVE, şarkı türevi olarak EKLENMESİN.**
- `turev_plani` her projenin T0'ından türüyor ve T0+21 günde kapanıyor; LIVE ise haftalık ve kanal seviyesinde.
- LIVE şarkıya bağlanırsa her yeni şarkı bir LIVE doğurur ve LIVE sayısı yayın sayısına kilitlenir. Bu, kaçınılan "şablon" desenin ta kendisi.

**Yalnız dinleme partisi duyurusu için dar bir tür eklenebilir: `tiktok_live_duyuru`.**
- **Kalıp:**
  - T0+3 … T0+14 gün
  - platform `tiktok`, elle, risk `orta`
  - dosya yok: insan yapımı duyuru videosu
- **Koşul:**
  - YouTube uzun formatın `*_privacy_gercek` değeri ≥48 sa `public`
  - `telif_*` / `kopya_notu` / `yayin_beklet` yok
- **Kurallar:**
  - `TUREV_GUNLUK_TAVAN`'a **sayılır**: aynı gün başka türev yok.
  - `TIKTOK_KIT_*` render tavanına **sayılmaz**.
  - `TUREV_YENI_YAYIN_BANDI_SAAT` (±24 sa) **uygulanır**.
  - `TUREV_AYNI_SARKI_ARA_SAAT` (48 sa) uygulanır.
  - `uyumluluk` fail-closed kapısı aynen geçerli.
  - **Yayın otomasyonu yok:** yalnız hatırlatma, `TUREV_HATIRLATMA_AKTIF` şalteriyle. LIVE'ı başlatan ve duyuruyu atan insan.
- **Yan etki sınırları:**
  - `_is_fully_done`'a eklenmez.
  - LIVE damgası `UPLOAD_TIMESTAMP_KEYS`'e ve 52 sa tabanına girmez; LIVE bir yükleme değil.
- **Kayıt:** LIVE'ın kendisi `elle_islemler.jsonl`'a yazılır. Sözlükte uygun işlem yoksa `canli_yayin` işleminin eklenmesi ayrı bir küçük kod işi olarak önerilir.

### 6b. Ölçüm

| Metrik | Nereden | Ne zaman | Karar eşiği (öneri) |
|---|---|---|---|
| Toplam takipçi, net kazanım (7/28 gün) | Studio web → Analizler → Takipçiler | Aşama 1'de 2 haftada bir (27 Eyl, 11 Eki, …) | Haftalık hız → eşik tarihi |
| Takipçi etkin saatleri | Aynı ekran | Ayda 1 | Program saatleri |
| Gönderi başına takipçi kazanımı | Studio → gönderi analizi | Her Perşembe | Söz Defteri nakarat kesitinin yarısının altında kalırsa format ağırlığı değişir |
| Yorum/izlenme oranı | Studio gönderi analizi | Haftalık | Bugün ~%0,03 → 4 haftada %0,3 hedefi |
| LIVE: toplam izleyici, en yüksek eşzamanlı, ortalama izleme süresi | LIVE sonu özet + Studio/LIVE Center → LIVE analizleri | Her LIVE | Ortalama izleme <1 dk ise format değişir |
| LIVE: yeni takipçi | Aynı | Her LIVE | LIVE başına <5 ise sıklık iki haftada bire iner |
| LIVE: yorum sayısı, hediye (elmas) | Aynı (hediye LIVE Gifts açıksa) | Her LIVE | Hediye hedef değil, yan metrik |
| İhlal / kısıtlama | Uygulama bildirimleri, hesap durumu | Her LIVE sonrası | Tek uyarı → format durdurulur ve gözden geçirilir |

API'den takipçi okumak `user.info.stats` scope'u gerektiriyor. Şimdilik elle okunur ve deftere yazılır.

---

## 7. Kullanıcıya sorulacak kararlar

1. **Yüz gösterme:** LIVE'da yüz görünsün mü?
   **Öneri: hayır.** Eller + ses + defter yeterli; kuralın istediği yüz değil, canlı insan katkısı.
2. **İlk LIVE formatı:** Söz Defteri CANLI mı, dinleme partisi mi, DJ Famous miksi mi?
   **Öneri: Söz Defteri CANLI.** En düşük kural ve telif riski, inauthentic riskini en çok düşüren format. DJ miksi Aşama 3'te, DJ Famous'un ayrı LIVE onayıyla.
3. **Gün ve saat:** LIVE yuvası Pazar 21:00 olsun mu?
   **Öneri: geçici olarak evet.** Studio → Analizler → etkin saatler okununca kesinleşsin.
4. **Gönderi sıklığı:** render tavanı (günde 1, haftada 4) aynen kalırken haftada **+2 insan yapımı** gönderi (Söz Defteri + kulis) tavan dışı sayılsın mı?
   **Öneri: evet**, aynı güne iki gönderi düşmemesi şartıyla.
5. **Takipçi verisi:** takipçi elle mi okunsun, yoksa TikTok izni `user.info.stats` ile genişletilsin mi?
   **Öneri: Aşama 1'de elle** (2 haftada bir, 2 dk). Scope genişletmek yeniden yetkilendirme ve kod işi; mevcut yükleme token'ını bozma riski taşıyor (YouTube `analytics_token` dersiyle aynı sınıf).

---

## 8. Kaynaklar

**Resmî (metin okundu):**
- TikTok Müzik Hizmet Şartları (LIVE'da müzik): https://www.tiktok.com/legal/page/global/music-terms-eea/en
- TikTok Newsroom, LIVE özellikleri (18 yaş, 200 kelimelik filtre, LIVE Events): https://newsroom.tiktok.com/neue-funktionen-fuer-live-auf-tiktok?lang=de-DE
- TikTok LIVE Creator Networks, para kazanma uygunluğu: https://www.tiktok.com/live/creator-networks/en/blog/tiktok-live-monetization-requirements

**Resmî (sayfa JS ile yükleniyor; yalnız arama özeti okundu, doğrulanmalı):**
- About TikTok LIVE: https://www.tiktok.com/support/faq_detail?id=7543604790438451768
- LIVE Gifts: https://www.tiktok.com/support/faq_detail?id=7543897462415579704
- LIVE Monetization Guidelines: https://www.tiktok.com/live/creators/en-US/rules_and_guidance/live_monetization_guidelines
- Topluluk Kuralları, Hesaplar ve Özellikler: https://www.tiktok.com/community-guidelines/en/accounts-features
- Topluluk Kuralları, Bütünlük ve Özgünlük: https://www.tiktok.com/community-guidelines/en/integrity-authenticity
- LIVE Studio kılavuzu: https://livecenter.tiktok.com/help_center/article/1023/tiktok-live-studio-operation-manual_en-US?lang=en
- TikTok Shop LIVE kalite kuralları: https://seller-us.tiktok.com/university/essay?knowledge_id=4581457528243969

**İkincil (doğrulanmamış):**
- https://tiklivestudio.com/blog/en/tiktok-live-studio-system-requirements
- https://www.demandsage.com/followers-needed-for-tiktok-live/
- https://www.hollyland.com/blog/topics/get-your-tiktok-stream-key
- https://sociallyin.com/blog/tiktok-live-stream-rules/
- https://tiktokstats.com/guides/tiktok-live-content-monetization-requirements-2026-guide
- https://www.shopify.com/tr/blog/tiktokta-canli-yayin-nasil-acilir
- MX330 / NVENC: https://obsproject.com/forum/threads/obs-nvenc-nvidia-geforce-mx350-support-or-not.155290/ · https://en.wikipedia.org/wiki/Nvidia_NVENC

**Depo içi:** `tiktok_envanteri_2026-09-12.md`, `buyume_kontrol_listesi.md` (A4, C3, D5, E1), `haftalik_is_akisi.md`, `yayin_sonrasi_takvim_plani.md`, `turev_takvimi.py`, `config.py` (`TIKTOK_KIT_*`, `TUREV_*`), `trend_hashtag_notlari.md`, `upload/tiktok_token.json` (yalnız scope alanı).
