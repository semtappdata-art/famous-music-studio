# Büyüme Kontrol Listesi (elle yapılan adımlar)

**Son düzenleme: 2026-09-11 (4. tur)** — liste depodaki GERÇEK duruma göre
yeniden doğrulandı. Yapılmış/artık gereksiz maddeler işaretlenip çıkarıldı,
aynı gün ortaya çıkan yeni elle-işler aciliyet sırasına yerleştirildi.
3. turda her madde `state.json`/`meta.json`/kaynak kodu üzerinden TEK TEK
doğrulandı; diskteki gerçeğe aykırı çıkan eski D1 maddesi ("Küllerimden Geç
unlisted — bilerek mi?") kaldırılıp **E7**'ye kalıcı KAYIT olarak taşındı.
4. turda kod tekrar okundu: **A7** eklendi (Instagram'da aynı sesin ÜÇ canlı
Reels'i), **A4**'e hangi taslağın yayınlanacağı yazıldı, **A5**'in dayandığı
kod satırı gün içinde değiştiği için madde baştan yazıldı.

Buradaki her madde ELLE yapılır: ya API'den mümkün değil, ya da bilerek
otomatikleştirilmiyor (platform kural riski). Sıra **aciliyete** göre:
en üstte "bu yapılmazsa ŞU AN bir hat çalışmıyor".

Biçim: **ne yapılacak · NEREDE · yapılmazsa ne çalışmıyor · süre · kanıt**

---

## A — ŞU AN BİR HAT ÇALIŞMIYOR

### A1. `Gece Seansı Vol. 1`'in TELİF durumunu Studio'dan kontrol et — tek atışlık uyarı KAÇTI

**Ne yapılacak** YouTube Studio → İçerik → `Gece Seansı Vol. 1`
(`https://studio.youtube.com/video/O2VGj5SUz30/edit`) → **Kısıtlamalar**
sütunu. "Telif hakkı talebi" varsa ayrıntıya gir: ya itiraz et, ya etkilenen
bölümü kes/sustur.

**NEREDE** YouTube Studio (tarayıcı). **API'den GÖRÜNMÜYOR.**

**Yapılmazsa ne çalışmıyor (somut)** Video bugün 15:15'te `private` yüklendi,
Content ID karantinası (`dj_tarama_kontrol.py`) 2 saat sonra "temiz" gördü ve
**18:13'te public yaptı — şu an yayında.** "Studio'da telif bölümüne bak"
bildirimi tam o anda gönderildi ama başlığındaki Türkçe harfler yüzünden
(latin-1 arızası, bugün kökünden düzeltildi) telefona **HİÇ ULAŞMADI**.
Üstelik bu bildirim **TEK ATIŞLIK**: `dj_tarama_kontrol.py`,
`dj_tarama_bekliyor` bayrağını `notify.send()`ten ÖNCE `False` yapıyor — yani
bir daha asla gönderilmeyecek. Karantinanın dayandığı
`contentDetails.regionRestriction.blocked` kontrolü zaten bir VARSAYIM:
YouTube Data API, partner olmayan kanallara Content ID itirazlarını
göstermiyor (2026-09-11'de 20 videoda doğrulandı — itiraz varken bile her şey
`processed` görünüyor). Bu videonun telif durumunu bilen TEK yer Studio.

**Süre** ~3 dakika.

**Kanıt** `derlemeler/Gece Seansı Vol. 1/state.json`: `youtube_privacy=public`,
`dj_tarama_temiz=true`, `dj_tarama_kontrol_at=2026-09-11T18:13:21`;
`dj_famous_process.log` 15:15:29 ve 18:13:22 satırları.

> Aynı kontrol `City Pulse Set` için de hâlâ açık — bkz. F2.

---

### A2. Telefonda ntfy konusuna ABONE OL — dosya artık VAR, dinleyici yok

> **YAPILDI (bu maddenin yarısı):** `notify_config.json` repo kökünde artık
> **VAR** (2026-09-11'de oluşturuldu). Eski "dosyayı oluştur" adımı düştü.

**Ne yapılacak**
1. Telefona **ntfy** uygulamasını kur (App Store / Play Store, hesap gerekmiyor).
2. `notify_config.json` içindeki `ntfy_topic` değerini oku ve uygulamada **o
   konuya abone ol**. (Konu adını bu dosyaya YAZMA — adı bilen herkes
   bildirimleri okuyabilir ve sahte bildirim gönderebilir.)

**NEREDE** Telefondaki ntfy uygulaması.

**Yapılmazsa ne çalışmıyor (somut)** `notify.send()` artık ntfy'ye başarıyla
POST ediyor, ama konuyu dinleyen kimse yoksa bildirim hiçbir yere varmıyor.
Dinleyicisiz kalan emniyet ağları:
- TikTok "golden-hour geldi, taslağı yayınla" hatırlatması
  (`tiktok_upload.notify_pending_publish`) — yani A5'i hatırlatacak tek
  mekanizma.
- Instagram token'ı doluyor uyarısı (`saglik_kontrol.instagram_token_suresi`,
  10 gün kala tetikleniyor) — yani B2 sessizce geçip yüklemeler 401 verebilir.
- `watch_projects.py`'nin 4 saatlik **nabız/watchdog** uyarısı — makine
  kapanırsa ya da saatlik Görev Zamanlayıcı görevi bozulursa haberin olmuyor.
- Content ID karantina bildirimi — A1 bunun canlı (ve pahalı) örneği.

**Süre** ~3 dakika.

**Kanıt** `notify_config.json` depo kökünde VAR (2026-09-11 dizin taraması);
abonelik telefonda olduğu için diskten DOĞRULANAMIYOR.

---

### A3. `dj_sets/Night Drive` parçalarını Suno'dan indir — DJ hattı boşta dönüyor

**Ne yapılacak** `dj_sets/Night Drive/_segments/` klasörü **tamamen boş**.
`SUNO.md`'ye göre **12-16 parça** gerekiyor (hedef ~45-60 dakika, Extend
zinciriyle). Suno stil satırı `SUNO.md`'de hazır, kopyala-yapıştır.

Dosya adlandırma **ZORUNLU** — sıra numarası dosya adının SONUNDA:

```
dj_sets\Night Drive\_segments\Night Drive 1.wav
dj_sets\Night Drive\_segments\Night Drive 2.wav
...
```

İndirdikten sonra (SUNO.md'deki sıra):

```
python merge_dj_set_segments.py "dj_sets/Night Drive"
python stock_video.py --set "dj_sets/Night Drive" --build
python dj_famous_process.py
```

**NEREDE** Suno (tarayıcı) → indirme →
`C:\Users\ACER\Desktop\ilk-projem\dj_sets\Night Drive\_segments\`

**Yapılmazsa ne çalışmıyor (somut)** `audio.wav` üretilemiyor;
`dj_famous_process.py` bir klasörü ancak `audio.wav/mp3/m4a` varsa "yeni set"
sayıyor (`AUDIO_NAMES`). `City Pulse Set` ve `Just Relax` zaten yayınlandı,
işlenecek başka set yok → **Cuma 18:00'deki haftalık DJ görevi her hafta
tetikleniyor ama hiçbir yeni set üretmiyor.** Bu hâliyle set render EDİLEMEZ.

**Süre** Suno üretimi + indirme ~1-2 saat. Kota uyarısı (SUNO.md): Suno
indirme kotası ayda 20-60; 16 parçalık set ayın bütçesinin büyük kısmını
yer, `projects/` (ana katalog) aynı kotadan besleniyor.

**Kanıt** `_segments/` boş (dizin listesi); `SUNO.md` "12-16 parça";
`dj_famous_process.py:50 AUDIO_NAMES`.

---

### A4. TikTok gelen kutusundaki taslakları elle yayınla — **20 video bekliyor**

**Ne yapılacak** TikTok uygulaması → Gelen kutusu/Taslaklar → her videoyu aç,
yayınla. Yayınlarken **iki şey elle**:
- Native **"AI-generated content"** etiketini AÇ.
- Kapağı "Yükle" ile galeriden seç (video karesi seçme zorunda değilsin).

Caption ve ilk yorumu **uydurma**, boru hattından al:

```
python upload/tiktok_publish_plan.py --project "projects/<isim>" --json
python upload/tiktok_upload.py --pending-covers      # hepsinin kapak listesi
```

> **YENİ (2026-09-12): bu komut artık POLİTİKA KAPISINDAN geçiyor ve bu
> makinede İLK KEZ gerçekten çalışıyor.** Öncesinde iki ayrı arıza vardı:
> (1) `uyumluluk.kontrol()` render ve yükleme hattında çalışıyordu ama TikTok'un
> ELLE yayın yolunu hiç kapsamıyordu — yani aşağıdaki "20'nin ikisi aynı ses"
> uyarısı yalnızca bu düz metinde duruyordu; (2) Windows kod sayfası (`cp1254`)
> emoji'yi kodlayamadığı için komut tam caption satırında çöküyordu, yani
> caption'ı hiç veremiyordu. İkisi de düzeltildi. Çıktıda artık şunlar var:
> `Hazır: False` + `!! ENGEL` satırı yayınlanmaması gerekenlerde,
> `* UYARI` satırı dikkat edilmesi gerekenlerde.
>
> Bugünkü kuru tarama (21 klasör) **iki ENGEL** buluyor:
> - `dj_sets/City Pulse Set` → telif eşleşmesi kayıtlı (Bring Me To Life —
>   Tiesto, FORS). **Bu taslağı YAYINLAMA** (bkz. F2).
> - `projects/Küllerimden Geç` → `Yeniden Doğacağım` ile aynı md5 ve YouTube'da
>   public olan taraf O. Aşağıdaki kutunun kararının ta kendisi, artık kodda.
>
> Yani "hepsini yayınla" demeden önce her taslak için bu komutu çalıştırmak
> yeterli — hangisinin yayınlanmayacağını kendisi söylüyor.

**Her yayından SONRA depoya İŞARETLE** (2026-09-12'de eklendi). TikTok API
"yayınlandı mı" sorusunu cevaplamıyor (`video.list` scope'u yok) — bu olgunun
TEK kaynağı sensin. İşaretlemezsen taslak bekleyen listesinden hiç düşmez ve
aşağıdaki ikiz kapısı "ikiz zaten yayınlanmış" kuralını hiç göremez
(o güne kadar 22 klasörün hiçbirinde bu alan yoktu — kural ölü daldı):

```
python upload/tiktok_publish_plan.py --yayinlandi "projects/<isim>"   # HER yayından sonra, o proje için
python upload/tiktok_publish_plan.py --yayinlandi-hepsi --dry-run     # bekleyen liste + hazir=True/False sütunu (yazmaz)
python upload/tiktok_publish_plan.py --yayinlandi-hepsi               # tek tek sorarak toplu işaretleme
python upload/tiktok_publish_plan.py --dogrulandi "projects/<isim>"   # SADECE İLK gönderi için, bir kez
```

`--dogrulandi`: ilk gönderide başlık/açıklama/AIGC etiketinin doğru göründüğünü
gözle teyit ettikten sonra, **bir kez** — bayrak KANAL seviyesinde okunuyor, ondan
sonra plan tüm kanal için `PUBLIC_TO_EVERYONE` önerir. Yayınlamak doğrulamak
değildir: `--yayinlandi` bu bayrağı yazmaz. Zaten işaretli bir proje hata
vermez ("değişiklik yok"), `tiktok_publish_id` olmayan projeyi reddeder.

**NEREDE** TikTok mobil uygulaması (API'den yayın mümkün değil, bkz. E1).

**Yapılmazsa ne çalışmıyor (somut)** `tiktok_privacy: DRAFT_INBOX` olan her
kayıt gelen kutusunda kalır, hiç yayınlanmaz. 2026-09-11 18:15 itibarıyla
**20 kayıt**: `projects/` altında 17 (Sofraya Gelmedin hariç hepsi),
`dj_sets/City Pulse Set`, `dj_sets/Just Relax` ve YENİ:
`derlemeler/Gece Seansı Vol. 1`.

> TikTok API'sinden bir taslağın gerçekten yayınlanıp yayınlanmadığını
> öğrenmenin yolu YOK — bu 20 sayısı "yüklendi" kaydıdır, bir kısmını zaten
> yayınlamış olabilirsin. Tek kesin kontrol TikTok uygulamasının kendisi.

> **DİKKAT — 20'nin ikisi AYNI ses. "Hepsini yayınla" talimatını KÖRÜ KÖRÜNE
> uygulama.** `Küllerimden Geç` ile `Yeniden Doğacağım` aynı kaydın iki ismi
> (`audio.wav` md5'leri eşit) ve İKİSİ de hâlâ taslakta.
> **Yayınlanacak olan: `Yeniden Doğacağım`** — orijinal, YouTube'da `public`
> olan, diğer platformlardaki kayıtla tutarlı olan taraf.
> **`Küllerimden Geç` TASLAKTA KALACAK** (ya da ⋯ → Sil ile taslaklardan
> kaldırılacak). İkisi birden yayınlanırsa aynı ses TikTok'ta iki kez yayına
> girer. Ayrıntı ve kanıt: **E7**.
>
> Bu uyarı artık KODDAN da görünüyor: `--yayinlandi-hepsi --dry-run` listesinde
> `Küllerimden Geç` `hazir=False` satırı olarak çıkıyor (bugünkü koşu: 20 taslağın
> 2'si `hazir=False` — `Küllerimden Geç` ve `City Pulse Set`) ve toplu modda
> düz "e" yetmiyor, açıkça "EVET" istiyor. Bu düz metin yine de KALIYOR —
> iki katman: kod kapısı + insan okuması.
>
> TikTok API'si bir taslağın yayınlanıp yayınlanmadığını söylemediği için
> (`tiktok_auth.py` scope'u `user.info.basic,video.upload` — `video.list` YOK),
> taslaklara bakmadan ÖNCE yayınlanmış videolarına da bak: ikisi de yayındaysa
> orada da elle bir silme işi var.

**Süre** Video başına ~2 dakika.

**Bu KALICI bir iş** — her yeni yüklemede tekrar gerekiyor.

**Kanıt** 20 `state.json`'da `tiktok_privacy=DRAFT_INBOX`; hiçbirinde
`tiktok_published_at` yok (`--yayinlandi-hepsi --dry-run` 2026-09-12: 20 satır).

---

### A5. Instagram: "Gece Sürüşü" ve "Kalbim Oynuyor" yeni kapaklı gönderisi HİÇ yayınlanmadı

**Durum (2026-09-05 kapak migrasyonunun kapanmamış ucu)** Bu iki şarkı için
2026-09-05 14:19/14:21'de Instagram konteyneri oluşturuldu ama golden-hour
gelmeden 24 saatte EXPIRED oldu. `instagram_media_id` hâlâ **2026-09-01
tarihli ESKİ kapaklı** gönderiyi gösteriyor.

**Otomasyon bunu YİNE DE kendiliğinden yayınlamayacak — ama SEBEP değişti
(2026-09-11).** Eski not `instagram_upload.py:207`'deki
`if not creation_id or state.get("instagram_media_id"): return None` kapısını
gösteriyordu; **o kapı bugün KALDIRILDI** (tam da bu iki proje yüzünden, bkz.
`_konteyner_yayindan_yeni()` docstring'i: "6 gün boyunca yanlışlıkla
golden-hour bekleniyor yazdı"). Artık `try_publish_pending()` "bekleyen
konteyner SON yayından yeni mi" diye soruyor ve bu iki projede cevap **EVET**
(konteyner 05 Eylül, yayın 01 Eylül) — yani fonksiyon ARTIK İÇERİ GİRİYOR.
İçeri girince ne oluyor: konteyneri EXPIRED buluyor, bayat
`instagram_creation_id`/`instagram_container_created_at` kaydını **siliyor** ve
konsola `python upload/instagram_upload.py --project "..."` komutunu basıp
çıkıyor. Yeni konteyneri yalnızca `upload_video()` üretir, o da bu projelerde
otomatik çalışmaz (`instagram_media_id` dolu → `_is_fully_done` "bitmiş" der).
Yani karar hâlâ SENDE, ama artık bir ÜÇÜNCÜ (ve en ucuz) seçenek var.

**Ne yapılacak** Karar ver, üçünden biri:
- (a) **Bırak** — eski kapaklı gönderi Instagram'da kalsın. Hiçbir şey yapma.
- (b) **Tek komutla yeniden paylaş** (ÖNERİLEN, otomasyonun kendi yolu):
  ```
  python upload/instagram_upload.py --project "projects/Gece Sürüşü"
  python upload/instagram_upload.py --project "projects/Kalbim Oynuyor"
  ```
  Konteyneri sıfırdan kurar; golden-hour içindeysen hemen yayınlar, değilsen
  saatlik koşu yayınlar. Sonra ESKİ gönderiyi elle sil (A6 deseni, API'den
  silinemiyor — E2).
- (c) **Elle paylaş** — Instagram uygulamasından:
  `projects\Gece Sürüşü\output\shorts_9x16.mp4` ve
  `projects\Kalbim Oynuyor\output\shorts_9x16.mp4`; sonra eskisini sil.

> **(b) ile (c)'yi AYNI ANDA yapma** — ikisi de yayınlarsa aynı ses profilde
> bir kez daha çoğalır (A7'nin ta kendisi).

**Süre** (a) 0 dk · (b) ~2 dk · (c) ~10 dk.

**Kanıt** İki `state.json`'da `instagram_creation_id` +
`instagram_container_created_at` (05 Eylül 14:19/14:21) ile
`instagram_media_id` + `instagram_uploaded_at` (01 Eylül 18:50/18:53) birlikte
duruyor; `upload/instagram_upload.py:334` (`_konteyner_yayindan_yeni` kapısı)
ve `:350-365` (EXPIRED dalı — yeniden oluşturmuyor).

---

### A6. Instagram'da ESKİ kapaklı gönderileri sil (migrasyonun kalanı)

**Ne yapılacak** Instagram uygulamasından şu 4 gönderiyi sil — yeni kapaklı
versiyonları zaten canlı:

| Şarkı | Silinecek ESKİ media_id | Canlı YENİ media_id |
|---|---|---|
| Bir Bahar Daha | 17989399238849006 | 17890753710432077 |
| Sabaha Kadar | 18016641764731825 | 18086124917679232 |
| Beni Bırakma | 18416877271155090 | 18329976520278038 |
| Yeniden Doğacağım | 18134444965723339 | 18112778338817977 |

**NEREDE** Instagram mobil uygulaması (`@famous_music_studio` profili).

**Yapılmazsa ne çalışmıyor** Aynı şarkının iki kopyası profilde yan yana
duruyor — biri eski/çirkin kapakla. Kanal "toplu üretilmiş tekrar içerik"
görüntüsü veriyor.

**Süre** ~5 dakika.

**API'den YAPILAMAZ** — bkz. E2. Zaten yapmışsan bu maddeyi çiz.

> **Uygulamayı zaten açmışken A7'yi de yap** — oradaki iki silmeden biri
> (`Yeniden Doğacağım`ın 1 Eylül tarihli eski kapaklısı) bu tablodaki 4.
> satırın ta kendisi.

**Kanıt** `state.json`'lardaki yeni `instagram_media_id` değerleri eski
kimliklerden farklı → yeni gönderiler canlı, eskiler duruyor.

---

### A7. Instagram'da AYNI SESİN ÜÇ canlı Reels'i var — ikisini sil

**Ne yapılacak** Instagram **mobil uygulaması** → `@famous_music_studio` →
Reels. Bu sesin (`audio.wav` md5 `21093024291b9898e490b8eb021b5e8c`) üç
gönderisi var; **ikisini sil, birini bırak.**

| Karar | Gönderi | Link | media_id |
|---|---|---|---|
| **SİL** | `Küllerimden Geç` (7 Eyl, ikinci yükleme) | `instagram.com/reel/Dc-5CR9j2XO/` | `18087131705485174` |
| **SİL** | `Yeniden Doğacağım` — ESKİ kapak (1 Eyl) | `instagram.com/reel/Dcv6i1PjYUy/` | `18134444965723339` |
| **BIRAK** | `Yeniden Doğacağım` — yeni kapak (5 Eyl) | `instagram.com/reel/Dc5vAXxgGIf/` | `18112778338817977` |

Gönderiyi aç → sağ üst **⋯ → Sil → Sil**.

**NEREDE** Instagram mobil uygulaması. **API'den YAPILAMAZ** — doğrulandı,
bkz. E2 (`IGApiException code 100 / error_subcode 33`). Koda eklemeye ÇALIŞMA.

**Yapılmazsa ne çalışmıyor (somut)** Hiçbir hat durmuyor — ama profilde aynı
ses ÜÇ KEZ duruyor ve bu, kanalın en büyük tekil riski olan "inauthentic /
toplu üretilmiş AI içerik" tarifinin tam merkezi (telif değil, bu). Instagram
bu sesin gerçek kopya sorunu olan TEK platformu: YouTube temiz
(`Küllerimden Geç`in ikisi de unlisted), Facebook/Telegram/Bluesky'a hiç
gitmemiş, TikTok'ta ikisi de hâlâ taslak (bkz. A4).

**BIRAKILACAK olanı yanlışlıkla silme** — `Dc5vAXxgGIf`
(`18112778338817977`) `projects/Yeniden Doğacağım/state.json`'daki
`instagram_media_id`'nin ta kendisi; silinirse kayıt ile gerçek birbirinden
kopar.

**Süre** ~5 dakika (A6 ile aynı oturumda yapılırsa +0).

**Kanıt** Üçü de canlı API ile doğrulandı (`GET graph.instagram.com/v21.0/
<media-id>`, HTTP 200 × 3, 2026-09-11); iki `state.json`/`meta.json`'daki
`kopya_notu`; md5 ve dosya boyutu eşitliği (E7).

---

## B — TARİHLİ: YAKINDA SESSİZCE DURACAK

### B1. YouTube Reporting API'yi aç — **SON TARİH 2026-10-11, kaçarsa veri GERİ GELMEZ**

**Ne yapılacak**
1. https://console.developers.google.com/apis/api/youtubereporting.googleapis.com/overview?project=1026223060773
   → **ETKİNLEŞTİR**.
2. Etkinleştikten sonra bir "reporting job" oluşturulması gerekiyor — bu kod
   tarafı, API kapalıyken yazılamıyordu.

**NEREDE** Google Cloud Console (tarayıcı), proje `1026223060773`.
Şu anki durum: HTTP 403 **`SERVICE_DISABLED`**.

**NEDEN TARİHLİ (ertelenirse telafisi YOK)** Küçük resim **gösterimi** ve
**tıklanma oranı** (`video_thumbnail_impressions`,
`video_thumbnail_impressions_ctr`) YouTube **Analytics** API'de YOK; sadece
**Reporting** API'nin `channel_reach_basic_a1` / `channel_reach_combined_a1`
raporlarında var. Ve bir reporting job oluşturulduğunda YouTube yalnızca
**oluşturulmadan ÖNCEKİ 30 günü** geriye dönük üretiyor. 2026-09-11'de
kanalın **40 kapağı birden** değiştirildi (başlık puntosu 2x, logo kontrastı)
— yani "değişiklik öncesi" temel çizgi tam da o 30 günlük pencerenin içinde.
Her gecikme günü temel çizgiden bir gün siler; **2026-10-11'den sonra
açılırsa değişiklik öncesi dönem GERİ GELMEZ** ve 40 kapağın işe yarayıp
yaramadığı hiçbir zaman ölçülemez.

**YEDEK PLAN (API bugün açılamazsa)** Studio → Analizler → Gelişim (Reach),
tarih aralığı 2026-08-14..2026-09-10, "Gösterimler" + "Gösterimlerin tıklanma
oranı" sütunlarıyla CSV dışa aktar ve repoya kaydet.

**Süre** ~5 dakika.

**Kanıt** `olcum_temel_cizgi.json` → `gosterim_ctr_durumu.reporting_api`
(durum, zaman kritiği ve kaynak linkleri orada).

---

### B2. Instagram token'ını YENİDEN YETKİLENDİR — artık ertelenmez (log'a sızdı)

**Ne yapılacak**

```
python upload/instagram_auth.py --print-url
# çıkan linki tarayıcıda aç, izin ver, callback sayfasındaki kodu kopyala
python upload/instagram_auth.py --code KOPYALADIGIN_KOD
```

**NEREDE** Repo kökünde terminal + tarayıcı (Instagram giriş ekranı).

**Neden ŞİMDİ — iki sebep, birincisi YENİ**
1. **Mevcut değer artık güvenilmez.** 2026-09-04'te GERÇEK bir Instagram
   erişim token'ı düz metin olarak `dj_famous_process.log`'a düştü: o dosyada
   `maskele()` import edilmişti ama `log()` içinde hiç çağrılmıyordu (bugün
   düzeltildi; `log_rotate.trim_log` artık diskte duran satırları da yeniden
   maskeliyor). Log **gitignored**, yani GitHub'a gitmedi — ama değer bir süre
   korumasız durdu. Doğrusu yeniden yetkilendirip eskisini geçersiz kılmak.
2. **Süre.** Token 2026-09-01 10:00'da yazıldı, ömrü 60 gün → **bitiş
   2026-10-31 10:00** (2026-09-11 itibarıyla kalan ~49,8 gün). Yeniden
   yetkilendirme bu sayacı da sıfırlıyor — iki iş tek adımda bitiyor.

**Yapılmazsa ne çalışmıyor** Token dolduğu an tüm Instagram yüklemeleri 401
veriyor ve **sessizce** duruyor. Bu daha önce yaşandı (2026-09-08 Netlify
401'i, 25+ koşu fark edilmedi — `saglik_kontrol.py` docstring).
`saglik_kontrol.py` 10 gün kala (≈2026-10-21) uyarmayı deniyor — ama o uyarı
telefona ancak **A2 yapılırsa** ulaşır.

**Süre** ~5 dakika.

**Kanıt** `upload/instagram_token.json` mtime = 2026-09-01 10:00;
`dj_famous_process.py`'nin başındaki maskeleme notu (sızıntının tarihi ve
dosyası orada yazılı).

---

### B3. Facebook veri erişimi yenilemesi — **son tarih ≈2026-12-09**

**Ne yapılacak** Süre dolmadan:

```
python upload/facebook_auth.py --print-url
python upload/facebook_auth.py --code KOPYALADIGIN_KOD
```

**Ne zaman** Kalan **89 gün** (`upload/facebook_veri_erisimi.json`,
`veri_erisimi_bitis`). Uyarı bayrağı şu an kapalı (`uyari: false`).

**Yapılmazsa ne çalışmıyor** Facebook Reels yüklemeleri ve
`facebook_upload.post_pending_comment` (ilk yorum) durur.

**Süre** ~5 dakika. Şimdi acil değil — takvime not.

---

## C — KALICI ELLE İŞLER (otomatikleştirilmeyecek)

### C1. YouTube yorumları — **sadece 1 yanıt onay bekliyor** (10'u gönderilmiş)

> **DÜZELTME:** Bu madde "10 hazır yanıt bekliyor" diyordu, bu artık YANLIŞ.
> 2026-09-11'de `commentThreads.list` ile İKİ KEZ bağımsız doğrulandı: o 10
> yanıtın **10'u da 2026-09-10'da elle gönderilmiş** ve kanalın yanıtı
> yorumlarda GÖRÜNÜYOR. Tekrar göndermek 10 gerçek kişiye aynı cümlenin
> ikinci kez gitmesi olurdu.

**Kalan tek iş** `Kader Ortakları` altındaki @Ataseven-c8y yorumuna yanıt
(`yorum_taslaklari.json`'da `durum: onay_bekliyor` olan tek taslak).

```
python upload/yorum_gonder.py                     # dry-run: ne gönderilecek?
python upload/yorum_gonder.py --gonder --limit 1  # metni okuyup onayladıysan
```

**NEREDE** Repo kökünde terminal — ya da metni `yorum_taslaklari.json`'dan
kopyalayıp YouTube Studio → Yorumlar'dan elle yapıştır.

`atlanan` bölümündeki 1 yorum (aynı kişinin aynı videoya birebir aynı ikinci
yorumu) **bilerek yanıtsız** — ikisine de yanıt vermek "tekrar eden yanıt"
görüntüsü yaratır.

**Süre** ~2 dakika.

**NEDEN OTOMATİK DEĞİL — kalıcı karar:** `upload/yorum_gonder.py` artık var,
ama `--gonder` bayrağı olmadan hiçbir şey göndermiyor, her koşuda `--limit`
tavanı uyguluyor ve göndermeden önce thread'i API'den tazeden okuyor.
**Görev Zamanlayıcı'ya ya da `auto_process.main()`'e BAĞLAMA.** Üç sebep:
(a) şablon yanıtları toplu göndermek YouTube'un "inauthentic /
high-volume, repetitive" tanımının tam ortası — kanalın en büyük tekil riski;
(b) `comments.insert` adet başına **50 birim** kota (2026-09-06'da
`captions.list` döngüsü günlük kotayı bir kez tüketip ASIL yükleme hattını
durdurdu); (c) yanlış ya da tekrar eden bir yanıtın geri dönüşü yok, gerçek
bir insana kanal adına yazılıyor. Bu madde her yorum dalgasında tekrar
gelecek — "eksik özellik" sanma.

**Kanıt** `yorum_taslaklari.json`: 11 taslağın 10'u `zaten_yanitlandi`
(`gonderildi_at: 2026-09-10`), 1'i `onay_bekliyor`; `comments_cache.json`
`bekleyen` = 2 (biri `atlanan`daki bilinçli atlama).

---

### C2. Haftalık takip raporu

```
python weekly_report.py                # istatistik + Instagram token kontrolü
python weekly_report.py --izlenme      # sadece izlenme SÜRESİ raporu
```

**NEREDE** Repo kökünde terminal (ya da Remote Control oturumundan).

**Yapılmazsa ne çalışmıyor** `weekly_report.py` **hiçbir Görev
Zamanlayıcı görevine bağlı değil** — kayıtlı görevler sadece
`auto_process.py`, `dj_famous_process.py`, `watch_projects.py`. Çalıştırmazsan
izlenme/izlenme-süresi tablosu hiç güncellenmiyor.

Düz bir çizgi 2-3 hafta sürerse reklam/boost bütçesi konuşmaya değer.

**Süre** ~2 dakika.

> **DÜZELTME — yalnızca YETKİLENDİRME adımı bitti, madde DEĞİL:**
> `python upload/youtube_analytics.py --auth` YAPILDI;
> `upload/analytics_token.json` doğru kapsamla (`yt-analytics.readonly`) ve
> `refresh_token` ile duruyor, kendini yeniliyor. Ama `weekly_report.py` hâlâ
> hiçbir Görev Zamanlayıcı görevine bağlı DEĞİL — raporu üretmek için
> yukarıdaki komutu yine ELLE çalıştırman gerekiyor. Madde duruyor.

---

### C3. Instagram ve TikTok bio linkini bağla (tek seferlik — doğrulanamıyor)

**Ne yapılacak** İki uygulamada da: Profili düzenle → Web sitesi/Bio link →

```
https://famousmusicstudio.com/latest.html
```

**NEREDE** Instagram uygulaması (`@famous_music_studio`), TikTok uygulaması
(`@famousmusicstudio`).

**Yapılmazsa ne çalışmıyor** Her paylaşımdan sonra eklenen yorumdaki
"@hesap'a dokun, bio'daki linkten de ulaşabilirsin 🔗" satırı boşa gidiyor —
Instagram/TikTok yorumlarında düz metin link TIKLANAMIYOR, tek tıklanabilir
yer bio linki. `latest.html` sayfası hazır ve her koşuda otomatik tazeleniyor
(`latest_release.regenerate()` + `git_sync.push_path()`).

**Süre** ~3 dakika.

**DOĞRULANAMADI** — bu bir platform profil ayarı, diskten kontrol edilemiyor.
Zaten yaptıysan bu maddeyi çiz.

---

## D — İYİ OLUR (hat durmuyor, büyümeye katkı)

### D1. YouTube playlist temizliği — hayalet liste, çift kayıt, 9 ölü satır

Üçü de **Studio'dan**: `upload/youtube_playlists.py` yalnızca EKLİYOR, silme
işlevi bilerek yok (geri dönüşü olmayan işlem + 50 birim kota).

**(a) Hayalet playlist `PLceMWZWzfCPQ` — SİL.** Aynı adlı İKİNCİ bir "DJ Set
Şarkılar — Famous Music Studio" listesi (2026-09-04'te oluşmuş, içinde tek
video: `ph_qlIpHx_A` / City Pulse Set). Gerçek liste `PLV3ve3aiAwU4` (3 video)
ve `upload/playlist_ids.json`'da kayıtlı olan o. Sebep: ID önbelleğe girmeden
`playlists.insert` ikinci kez çağrılmıştı; `_save_playlist_ids` artık
`state_io` ile atomik yazdığı için tekrarlamaz.

**(b) Arabesk listesinde ÇİFT kayıt.** `PLcJHfZF85FI0` içinde `kZML9g4GdBs`
("Yeniden Doğacağım") **0. ve 1. sırada iki kez** duruyor. Birini kaldır.

**(c) 9 adet "Deleted video" satırı**, 5 ayrı tarz listesinde:

| Playlist | Liste | Ölü satır |
|---|---|---|
| `PLKsOiTu3OtV8` | Pop | 3 (`K3IJ5lEDhzQ`, `JbbY8n_g0F0`, `5EBYKXF_g_A`) |
| `PLamU8IEtNO2k` | Hip-Hop | 2 (`psdj0Jt9aqI`, `Jnbt7sb9UcM`) |
| `PLBgc_mrlH_1Q` | Elektronik | 2 (`VpzmEjVZQgU`, `4WfdT3u9Cwc`) |
| `PLcJHfZF85FI0` | Arabesk | 1 (`3EaaWKF4hSI`) |
| `PLV3ve3aiAwU4` | DJ Set | 1 (`0sAbz3hoEqw`) |

**Yapılmazsa ne çalışmıyor** Otomasyon etkilenmiyor. Ama izleyiciye liste
"bakımsız" görünüyor: silinmiş videoların yerinde gri "Deleted video"
satırları duruyor, aynı şarkı arka arkaya iki kez çıkıyor ve aramada aynı
isimli iki DJ listesi yan yana beliriyor. Playlist bu kanalın izlenme başına
EN ÇOK süre üreten yüzeyi (3,7 dk/izlenme, kanal ortalaması 0,84) — buradaki
kir doğrudan o yüzeye zarar veriyor.

**Süre** ~10 dakika.

**Kanıt** `playlistItems.list` dökümü (2026-09-11): yukarıdaki konumlar
birebir. NOT: o döküm yeni `_tum_sarkilar`/`_shorts` zincirleri kurulmadan
ÖNCE alındı, yani bu üç sorun tarz listelerine ait.

---

### D2. Facebook sayfa varlıklarını yükle (dosyalar HAZIR, bekliyor)

Üretilmiş ama hiçbir yere yüklenmemiş dosyalar:

| Dosya | Ne | Nereye |
|---|---|---|
| `marka\facebook_kapak.png` (1640x856) | Sayfa kapak görseli | Facebook Sayfası → Kapak fotoğrafını düzenle |
| `marka\facebook_metinleri.txt` | Kısa tanıtım (About) + uzun açıklama + kullanıcı adı önerisi | Sayfa → Ayarlar → Sayfa bilgileri |

`facebook_metinleri.txt` içindeki üç blok, kopyala-yapıştır hazır:
- **Kısa tanıtım (About):** "Yapay zekâ ile üretilen orijinal müzik. Her hafta yeni şarkı."
- **Uzun açıklama (Description):** platform listesi + famousmusicstudio.com
- **Kullanıcı adı (@):** `famousmusicstudio` — TikTok ile birebir aynı.
  Yol: Sayfa → Ayarlar → Sayfa adı ve kullanıcı adı.

**Yapılmazsa ne çalışmıyor** Otomasyon etkilenmiyor (Reels yüklemesi
çalışıyor, City Pulse Set 2026-09-11'de Facebook'a yüklendi). Ama sayfa
kapaksız/tanıtımsız ve `@kullanıcıadı` yoksa paylaşılabilir düzgün bir
sayfa URL'i de yok.

**Süre** ~10 dakika.

**Kapak notu** Kapakta logo kartı BİLEREK yok — profil fotoğrafı zaten aynı
logo ve Facebook onu kapağın üstüne bindiriyordu; metin de bu yüzden yukarı
taşındı (`marka/facebook_kapak_uret.py` docstring).

---

### D3. Bluesky banner'ını yükle

`marka\bluesky_banner.png` (1500x500) üretildi, yüklenmedi.
**NEREDE** bsky.app → Profil → Edit Profile → Banner.
**Yapılmazsa** Bluesky yüklemeleri çalışmaya devam eder (City Pulse Set
2026-09-11'de gönderildi), sadece profil çıplak görünür.
**Süre** ~2 dakika.

---

### D4. İlk 20-30 gerçek takipçiyi elle bul

İlgili topluluklarda (Reddit r/SunoAI, Türkçe AI-müzik Discord sunucuları)
hesabı paylaş. İlk birkaç düzine gerçek etkileşim, algoritmanın hesaba
güvenmeye başlaması için kritik — otomasyonun yapamayacağı sosyal bir adım.
**Süre** dağınık, birkaç saat.

---

### D5. Trend ses/format ile ara sıra TikTok paylaşımı

Kendi orijinal müziğin zaten otomatik paylaşılıyor. Ek olarak ara sıra o anki
trend bir sesi kullanan kısa bir video (duet/stitch) paylaş — trend sesler
"Keşfet" akışına çok daha hızlı taşıyor.
**Süre** paylaşım başına ~15 dakika.

---

## E — KAPALI YOLLAR ve GERİ ALINMAYACAK KARARLAR (bir daha araştırma/açma)

### E1. TikTok `video.publish` / otomatik yayın — KAPALI
Başvuru **daha önce bir kez REDDEDİLDİ**, gerekçe: *"Uygulamalar özel veya
kişisel kullanım için olmamalıdır."* (`.claude/skills/fms-tiktok-yayin/SKILL.md`,
`upload/tiktok_publish_plan.py` docstring). Demo video
(`upload/assets/tiktok_review_demo.mp4`) ve başvuru materyali zaten üretilmişti
— yani tam bir başvuru turu yapıldı ve reddedildi.

Ayrıca iki ayrı kapı var ve **ikisi de** gerekiyor: App Review (scope) **ve**
Content Posting API Audit. Audit'siz `video.publish` işe yaramaz — resmî
doküman: *"All content posted by unaudited clients will be restricted to
private viewing mode"*, ayrıca herkese açık hesaba hiç gönderilemiyor. Yani
onaysız hâli mevcut taslak/gelen-kutusu akışından **daha kötü**.

**Sonuç:** A4 (elle yayın) kalıcıdır. Yeniden başvuru düşünülürse hazırlanmış
dosya bu oturumun scratchpad'inde `tiktok_basvuru.md` olarak duruyor — ama
aynı materyalle tekrar göndermek aynı reddi getirir.

### E2. Instagram'da yayınlanmış medyayı API'den silme — MÜMKÜN DEĞİL
Bu projenin kullandığı "Instagram API with Instagram Login"
(`graph.instagram.com`) media delete endpoint'ini desteklemiyor; sadece eski
"Facebook Login" akışı destekliyor (WebSearch ile doğrulandı 2026-09-05).
Denendiğinde `IGApiException code 100 / error_subcode 33`. Koda eklemeye
ÇALIŞMA → A6 elle yapılır.

### E3. TikTok'ta yayınlanmış/taslak gönderiyi silme — API'de endpoint YOK.

### E4. TikTok kapak görseli API'den ayarlama — MÜMKÜN DEĞİL
`video_cover_image_url` sadece audit'ten geçmiş Direct Post akışında var.
→ A4'teki elle kapak seçimi kalıcıdır.

### E5. Meta Verified (Reels'e özel tıklanabilir link) — REDDEDİLDİ
$49,99/ay'dan başlıyor ve Content Publishing API ile uyumluluğu
doğrulanamadı. Yerine ücretsiz bio-link + mention çözümü seçildi (C3).

### E6. `setup_task_scheduler.ps1` yeniden çalıştırma — ŞU AN GEREKMİYOR
Kayıtlı üç görev de doğru: `FamousMusicStudio-AutoProcess` (saatlik),
`FamousMusicStudio-DjFamousProcess` (Cuma 18:00),
`FamousMusicStudio-Watcher` (dakikalık) — üçü de `pythonw.exe` ile,
`C:\Python314\pythonw.exe`, State=Ready/Running (2026-09-11 kontrolü).

`setup_task_scheduler.ps1` bugün (2026-09-11 13:25) değişti ama değişiklik
`-DjFamousDayOfWeek` parametresinin artık **dizi** kabul etmesi — varsayılan
hâlâ `@("Friday")` ve kayıtlı görev zaten Cuma. Yani mevcut görev tanımı
güncel, yeniden çalıştırmaya **gerek yok**.

**Sadece şunu istersen yeniden çalıştır:** haftada birden fazla gün DJ seti
(her koşuda 1 yeni set işleniyor):

```
powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1 -DjFamousDayOfWeek Tuesday,Friday,Sunday
```

> Unutma: Görev TANIMINI (tetikleyici, hangi script, hangi python.exe)
> etkileyen değişiklikler `git pull` ile YAYILMAZ — o durumda bu script'in
> elle yeniden çalıştırılması şart.

### E7. `Küllerimden Geç` YouTube'da BİLEREK `unlisted` — public YAPMA
`Yeniden Doğacağım` (`kZML9g4GdBs`, 1 Eylül, `public`) ile **AYNI kayıt**:
`audio.wav` md5'leri (`21093024291b9898e490b8eb021b5e8c`) ve dosya boyutları
(42.108.076 bayt) birebir eşit. `Küllerimden Geç` (`-CQ7MmUygTQ` uzun format +
`jN78mJrZd3c` Shorts) 7 Eylül'deki **İKİNCİ** yüklemedir; 2026-09-11'de liste
dışına alındı — **silinmedi**, izlenmesi (182 + 112) ve 7 yorumu duruyor,
caption satırları orijinal projeye taşındı.

**Public YAPMA.** Üç sebep: (a) aynı ses kanalda iki kez yayına girer —
kanalın en büyük riski telif değil, "inauthentic / toplu üretilmiş AI içerik"
politikasıdır; (b) `derleme.py`, `latest_release.py`,
`upload/ek_platform_backfill.py` ve `upload/facebook_backfill.py` dördü de bu
kaydı "unlisted = kopya" kuralıyla BİLEREK dışlıyor — public yapmak bu
kapıları aynı anda açar ve kopya derlemeye, `latest.html`'e ve geri
doldurmaya sızar; (c) `uyumluluk.py`'nin md5 kapısı 2026-09-11'de UYARI'dan
**HATA**'ya çekildi ve muafiyetlerinden biri tam olarak "çiftin bir tarafı
yayından çekilmiş" — public yapmak muafiyeti kaldırır, yani İKİ projenin de
yükleme/geri doldurma hattı HATA verip DURUR.

**Kanıt (diskten doğrulandı, 2026-09-11)** `projects/Küllerimden Geç/state.json`
→ `kopya_notu`; karşı tarafı `projects/Yeniden Doğacağım/meta.json` →
`kopya_notu` (iki `meta.json`'ın `custom_hooks`/`custom_questions` blokları da
birebir aynı); `yeniden_dogacagim_sozler.md` satır 3-4 ("AYNI PARÇADIR",
kullanıcı teyidi 2026-09-10); `ses_ve_tarz_takibi.md` satır 24 ("yeni kayıt yok
— 'Yeniden Doğacağım'ın sesi yeniden markalandı"); `derleme.py:24-25` ve `:129`;
`latest_release.py:98-103`; `upload/ek_platform_backfill.py:224`;
`upload/facebook_backfill.py:97`; `uyumluluk.py`'nin md5 bloğu
(`_kopya_notu_var` / `_yayindan_cekilmis` + `kontrol()`'ün 2. maddesi — md5
tekrar kontrolünün VAR OLMA sebebi bu olay). *Satır numaraları gün içinde
kayıyor; arama terimi olarak `kopya_notu` ve `BİREBİR AYNI (md5)` kullan.*

> **Kapanmamış uçlar.** TikTok'ta İKİSİ de hâlâ `DRAFT_INBOX` — hangisinin
> yayınlanacağı **A4**'te yazılı (`Yeniden Doğacağım`). Instagram'da ise iki
> değil **ÜÇ** canlı Reels var (5 Eylül kapak migrasyonundan kalan eski
> kapaklı `Yeniden Doğacağım` da sayılınca) — silme listesi, linkler ve
> "hangisi kalacak" kararı **A7**'de.

---

## F — DOĞRULANAMADI

### F1. Facebook `pages_manage_metadata` izni
Bu iznin Business Login yapılandırmasına (`config_id 1051793590797173`)
eklenmesi gerektiği söylendi — **depodan doğrulanamadı.**

Bulunanlar:
- `pages_manage_metadata` ifadesi depoda ve bu oturumun scratchpad'inde
  **HİÇBİR YERDE geçmiyor** (tam metin araması).
- `upload/facebook_auth.py` docstring'i config_id için sadece şunları
  şart koşuyor: `pages_show_list` + `pages_manage_posts` + `pages_read_engagement`.
- Hesaba **verilmiş** izinler (`upload/facebook_veri_erisimi.json`,
  2026-09-11): `pages_manage_engagement`, `pages_manage_posts`,
  `pages_read_engagement`, `pages_read_user_content`, `pages_show_list`,
  `public_profile` — `pages_manage_metadata` yok, ama onu isteyen bir kod da yok.
- `facebook_upload.py`'de sayfa meta verisi (kullanıcı adı, hakkında,
  webhook aboneliği) yazan HİÇBİR fonksiyon yok — sadece Reels/uzun video
  yükleme, yorum ve veri-erişimi kontrolü var.

**Sonuç:** Eklenmezse neyin çalışmayacağı tespit EDİLEMEDİ. Bu maddeyi
"yapılacak iş" olarak kabul etmeden önce hangi işlevin buna bağlandığı
netleşmeli. (D2'deki sayfa kapağı/hakkında/kullanıcı adı işleri zaten
Facebook arayüzünden ELLE yapılıyor, API izni gerektirmiyor.)

### F2. City Pulse Set telif itirazı
`dj_sets/City Pulse Set/state.json`'da `telif_eser`
("Bring Me To Life - Tiesto, FORS"), `telif_araliklari` (4 aralık) ve
`_telif_bolumleri/` altında 4 kesik ses dosyası var. Ama **itirazın güncel
durumu API'den görünmüyor** — tek kontrol yolu YouTube Studio → İçerik →
Kısıtlamalar sütunu. Bu oturumda giriş yapılmadığı için durumu
doğrulanamadı. **A1'i yaparken aynı ekranda bu satıra da bak** — ikisi de
`dj_famous_process.py` hattından çıkan içerik.

---

## Zaten OTOMATİK olan (bu listede DEĞİL — elle yapma)

- Trend hashtag'ler → `config.DISCOVERY_HASHTAGS`, her caption'a otomatik
- Yorum artırma sorusu → her caption'ın sonunda otomatik
- Paylaşım saatleri → `config.GOLDEN_HOURS`; `auto_process.py` saatte bir
  çalışıp "sırası geldi mi" kararını kendisi veriyor
- YouTube golden-hour zamanlaması → `publishAt` ile YouTube kendi yapıyor
- Instagram golden-hour kuyruğu → `try_publish_pending()` (istisna: A5)
- YouTube altyazı hizalama → `*_sozler.md` olan projelerde otomatik
- `latest.html` tazeleme + push → her koşuda otomatik
- İzlenme SÜRESİ ölçümü → `analytics_token.json` alındı, çalışıyor
- Facebook / Telegram / Bluesky yüklemeleri → `auto_process.py`'ye bağlı,
  üçünün de anahtarları dolu ve 2026-09-11'de gerçek gönderi yapıldı
- YouTube playlist üyeliği → `youtube_playlists.sync_project()`, her yüklemede
  otomatik; uzun format tarz listesine + ana zincire, Shorts kendi listesine
  girer. Üyelik YouTube'dan okunarak doğrulanıyor, elle eklemeye gerek yok
  (mevcut listelerin TEMİZLİĞİ ayrı iş — bkz. D1)
