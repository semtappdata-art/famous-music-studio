# Haftalık İş Akışı — Famous Music Studio

> **Bu belge ne için:** "bugün ne yapmalıyım" sorusunun tek cevap yeri. 30 günlük bir liste
> değil, **her hafta aynı şekilde dönen bir çevrim.** Tarihli işler ve tek seferlik onarımlar
> çevrimin içindeki yuvalara yerleşir (§4).
>
> Yazıldığı tarih: 2026-09-12. Çevrimin ilk turu: **Pazartesi 2026-09-14** (§6).

---

## 0. Önce şunu bil: neyin kendiliğinden olduğu

Bunları **kontrol etme, tetikleme, merak etme.** Üç zamanlayıcı görevi: `watch_projects.py`
dakikada bir · `auto_process.py` saatte bir · `dj_famous_process.py` Cuma 18:00.

| Kendiliğinden olan | Nerede |
|---|---|
| Yeni ses dosyasını `audio.wav` yapıp boru hattını tetiklemek | `watch_projects.py` |
| Render (uzun format + Shorts), kapak, kart, altyazı hizalama | saatlik koşu |
| YouTube / Shorts / TikTok taslağı / Instagram, golden-hour zamanlaması | saatlik koşu |
| Facebook / Telegram / Bluesky geri doldurma | saatlik koşu, günlük tavan 1 |
| `docs/latest.html` (bio linki) tazeleme + push · playlist üyeliği | her koşu |
| İzlenme + izlenme süresi istatistiği | günlük / haftalık |
| Telif taraması, md5 ikiz kapısı, politika kapıları | her koşu, fail-closed |
| **Haftalık özet bildirimi** | `weekly_report.haftalik_gozden_gecirme()`, Pzt 09:00+ |

**Elle kalan her şey aşağıdaki çevrimde.** Listede olmayan bir işi elle yapma.

> ⚠ Hafızadaki "dizüstü pile geçince üç görev de durur" notu **2026-09-12 itibarıyla
> geçersiz** — `DisallowStartIfOnBatteries` / `StopIfGoingOnBatteries` üç görevde de `False`.
> "Log'da koşu yok" şikâyetinde artık ilk bakılacak yer makinenin kapalı olup olmadığı.

---

## 1. Haftalık çevrim

Elle geçen toplam süre: **~1,5–2,5 saat/hafta.** Boş günler bilerek boş.

| Gün | İş | Süre | Otomatik / Elle |
|---|---|---|---|
| **Pazartesi** | Haftalık raporu oku → bakım yuvasını doldur (§4) | 10 dk + 20–40 dk | rapor OTOMATİK, bakım ELLE |
| **Salı** | **Üretim vardiyası** — Suno'dan yeni parça (§2) | 45–60 dk | ELLE |
| **Çarşamba** | — (boru hattı render/yayın yapıyor) | 0 | OTOMATİK |
| **Perşembe** | **Dağıtım vardiyası** — TikTok taslakları, Instagram bakımı | 15–25 dk | ELLE |
| **Cuma** | **DOKUNMA GÜNÜ** | 0 | OTOMATİK |
| **Cumartesi** | — | 0 | — |
| **Pazar** | **Defter kapanışı** — takip dosyalarını güncelle | 10–15 dk | ELLE |

### Pazartesi — rapor ve bakım

- **Haftalık özeti oku (5 dk).** 09:00 sonrası ilk saatlik koşuda düşer; golden-hour'a
  (12–14, 18–22) denk gelirse bir sonraki saate kayar. Makine kapalıysa **kaybolmaz**,
  haftanın ilk açık gününde gelir. Altı blok: `YAYIN (son 7 gün)` · `BEKLEYEN` · geri
  doldurma kuyrukları · `ÖLÇÜM` · `SAĞLIK` · `SENİN İŞİN`.
- **Üç soruyla oku (5 dk):** `SAĞLIK`'ta **uyarı** var mı (varsa haftanın bakım işi odur;
  "not" kovası acil değil, "bakılamadı" demek) · `BEKLEYEN` ana hatta 0'dan büyük mü
  (öyleyse bu hafta üretim yok, §5-E) · `SENİN İŞİN`'de 14 günün altına düşen var mı.
- **Bakım yuvasını doldur (20–40 dk)** — §4'teki sıradaki madde(ler). Yuva bir SÜRE
  bütçesi: 5 dakikalık üç küçük iş aynı yuvaya girer, 40 dakikalık bir iş tek başına
  doldurur. Bütçeyi aşan işi gelecek Pazartesi'ye yaz, ikiye bölme.
- **`SAĞLIK` uyarısında nereye bakılır:** `auto_process.log`'un son 30 satırı, sonra
  `gorev_izleri/*.log`. Uyarı adı hangi adımın düştüğünü söylüyor.
- **Kota yoğun işler bu güne, 10:15'e.** Kota TR 10:00'da (kışın 11:00) sıfırlanıyor; tek
  yayın ~4.150 birim (%42), AI beyanı kampanyası 2.142 (%21,4). **Cuma asla** (DJ koşusu
  +3.454…5.104). Rapor "bugün yayın var" diyorsa **Çarşamba 10:15**.

### Salı — üretim vardiyası

Haftanın tek Suno günü. **Varsayılan: haftada 1 indirme = 1 şarkı.** Adımlar §2.
Neden 1: 52 saatlik taban ayda ~13 slot veriyor ama gerçek tavan o değil — en büyük risk
"toplu üretilmiş AI içerik" ve o risk **video sayısına** bakıyor. Haftada 1 şarkı = ayda
4-5 indirme (20'lik kotanın %20-25'i); kalan pay DJ setine ve derlemeye kalıyor.
Rapor `BEKLEYEN`'de iş gösterdiyse **bu gün boş geçer.**

### Çarşamba / Cumartesi — boş

Salı indirilen parça render edilip kuyruğa giriyor. **İlk yayına kabaca 2,5–3 gün var**
(kuyruk sırası + 52 saatlik taban) — tasarım, arıza değil. "Hiçbir şey olmadı" normal.
Elle `--count` verme: kotayı öldüren tek düğme o.

### Perşembe — dağıtım vardiyası

Üretilmiş ama izleyiciye ulaşmamış içeriği ilerletme günü. **Haftada bir kutu:**

1. **TikTok taslakları (15 dk).** Bekleyenlerden **3-5 tanesini** elle yayınla, sonra
   `python upload/tiktok_publish_plan.py --yayinlandi-hepsi` ile işaretle. API "yayınlandı
   mı" sorusunu cevaplamıyor — işaretleme **tek doğruluk kaynağı.** ⚠ Docstring "20 taslak"
   diyor, gerçek **21**. ⚠ `City Pulse Set` (telif) ve `Küllerimden Geç` (kopya) hariç.
2. Kutu boşalınca sırayla: Instagram bakımı → Facebook/Bluesky varlıkları → D1 playlist
   temizliği. Kuyruk bitene kadar "trend ses ile ek TikTok paylaşımı" **askıda.**

### Cuma — dokunma

`dj_famous_process.py` 18:00'de koşuyor ve kota yiyor. Elle API işi yok, `--count` yok.

### Pazar — kapanış (10–15 dk)

1. **`ses_ve_tarz_takibi.md`** — bu hafta **ÜRETİLEN** şarkı için tabloya satır ekle
   (Şarkı | Tema | BPM | Vokal) **ve en üstteki "SON DURUM" satırını güncelle.** Dosya
   üretim sırasını tutuyor, yayın sırasını değil — parça henüz yayınlanmamış olsa da
   Salı'da indirildiyse bu hafta yazılır. İkisinden biri unutulursa bir sonraki karar
   yanlış geçmişe bakar.
2. **Bu hafta yayına çıkan varsa gözle doğrula** — video canlı mı, açıklamada Temiz Sözler
   var mı, bio linki (`famousmusicstudio.com/latest.html`) yeni içeriği gösteriyor mu.
3. Bakım işi yarım kaldıysa **ertele, ikiye bölme.**

---

## 2. Üretim akışı — 15 adımlık kontrol listesi

Salı vardiyasında sırayla. Şablon: **`vardiya_sozler.md`** ("Vardiya", rock, kadın vokal,
78 BPM).

**A. Karar (10 dk)**

1. **`ses_ve_tarz_takibi.md`'nin "SON DURUM" satırını oku.** Vokal cinsiyeti/dokusu ve BPM
   art arda tekrarlanmayacak. Tema: `projects/*/meta.json`'daki `theme` alanlarından **en az
   kullanılan ve en uzun süredir boşta olan**. Geçerli liste (`config.THEMES`):
   `pop, rock, elektronik, akustik, hiphop, arabesk`. `arabesk` seçilirse **düet zorunlu**.
2. **Konu seç — katalogla çakışmayacak.** `*_sozler.md` dosyalarında anahtar kelime ara;
   işlenmiş temayı ikinci kez yazma.

**B. Dosyalar — Suno'ya GİTMEDEN ÖNCE (15 dk)**

> **İskeleyi TEK KOMUTLA kur — 3., 4. ve 5. adımı birlikte yapar:**
> ```
> python yeni_parca.py "Vardiya" --tema rock            # yazar
> python yeni_parca.py "Vardiya" --tema rock --dry-run  # sadece ne yapacağını gösterir
> ```
> Komut: `projects/<Ad>/` açar, `meta.json`'ı (`title` + `theme`) yazar, repo
> köküne `<slug>_sozler.md` **şablonunu** koyar (üç zorunlu bölüm + "Temiz Sözler"
> başlığı zaten içinde) ve stil etiketi **taslağını** üretir (dil/mood
> `config.THEMES`'ten, vokal `ses_ve_tarz_takibi.md`'nin SON DURUM satırından,
> kapanış tanımı Outro kuralından). Slug'ı `stock_art._slugify` üretiyor — elle
> türetme. **Tema `config.THEMES`'te yoksa DURUR**, sessizce `hiphop`'a düşmez;
> aynı adda proje ya da sözler dosyası varsa da DURUR, üzerine yazmaz.
> **Uydurmadığı tek şey sözlerin kendisi** — aşağıdaki 3. adım yer tutucuları
> doldurmaktır. Komut sonunda Suno adımlarını ve tuzakları da basıyor.

3. **Sözler dosyasını yaz** (komutun bıraktığı şablonu DOLDUR): repo **KÖKÜNDE**
   `<slug>_sozler.md` — `projects/` altında DEĞİL.
   "Vardiya" → `vardiya_sozler.md`. Üç bölüm zorunlu: `## Stil Etiketi` (BPM **etikete
   yazılacak**, sonda kapanış tanımı — yumuşak temalarda `gentle fade-out ending`, sert
   temalarda `strong final hit ending, no abrupt cutoff`) · `## Sözler` (etiketli) ·
   `## Temiz Sözler` (etiketsiz, aynı satır listesi).
   Intro: **ilk satır temayı doğrudan adlandırmaz**, somut bir an/duyu imgesiyle açar.
   Outro: **iki TAM cümle, `...` yok.**
   Dosya yoksa YouTube altyazı hizalaması sessizce atlanır ve kapak şarkıya özel imgeden
   değil temanın varsayılanından seçilir.
4. **Proje klasörü: `projects/<Şarkı Adı>/`** — `yeni_parca.py` açtı, sadece doğrula.
   ⚠ **İNDİRMEDEN ÖNCE** var olmalı: `watch_projects.py` yalnızca **zaten var olan**
   klasörleri tarıyor, kendisi klasör açmıyor — klasör yoksa indirilen dosya hiç
   fark edilmez. (Boş klasör canlı hattı TETİKLEMEZ: tetikleyen şey SES dosyası.)
5. **`meta.json`** — `yeni_parca.py` yazdı: `{"title": "Şarkı Adı", "theme": "rock"}`.
   Sözler bittikten SONRA elle eklenebilecek tek şey `custom_hooks`/`custom_questions`
   (sözlerden türetilir; yoksa caption genel havuzdan seçilir, bozulmaz).
   ⚠ `theme` yoksa varsayılan **`hiphop`** olur: kapak, kart rengi, caption dili, Pexels
   sorgusu hepsi yanlış tarzdan gelir, hata vermeden. `title` yoksa **klasör adı** YouTube
   başlığı olur. Yazım hatası render'ı durdurur — bu doğru davranış.

**C. Suno (20–30 dk)**

6. **Chrome'un otomatik çevirisini kapat** (Ayarlar > Diller). Çeviri açıkken şarkının
   **adı** bile değişiyor ("Gece Sürüşü" → "Gece Gezintü", doğrulandı).
7. **Style kutusunu TEMİZLE**, kendi etiketini yapıştır — Suno alakasız öneri koyuyor.
8. **Sözleri parça parça yapıştır** (`[Intro]`, `[Verse 1]`, …); tek blok editörü donduruyor.
9. **Üret ve bekle** — süre görünmesi yetmez, **oynatma ikonu (▶) görünene kadar.**
10. ⚠ **"Görüntülenen Şarkı Sözleri" bloğunu KOPYALAMA.** O Suno'nun kendi hizalaması,
    **orijinal değil.** Dosyaya giren metin, Lyrics kutusuna **senin girdiğin** metindir.

**D. İndirme ve doğrulama (10 dk)**

11. **Tek varyant indir, doğrudan 4. adımdaki klasöre**, Suno'nun verdiği adla.
    ⚠ İki varyantı aynı klasöre koyma: aynı md5 artık UYARI değil **HATA**, boru hattını
    durdurur. İkinciyi repo **dışında** sakla.
    ⚠ Tetikleme yolu 2026-09-12'de değişti; ilk parçada doğrula. Koşu 5. dakikada ölüyorsa
    dosyayı doğrudan `audio.wav` adıyla bırak — iş saatlik göreve kalır (limit 2 saat).
12. **Tetiklemeyi doğrula (2 dk):** `gorev_izleri/watch_projects.log` → `BAŞLADI`;
    `auto_process.log` → projenin adı. 10 dakikada iz yoksa klasör adını/konumunu kontrol et.
13. **`output/` klasöründeki iki mp4'ü aç ve oynat.** Yarım kalan render diskte "var"
    görünür ve yüklemeye geçilir; 5 saniyelik kontrol bu riski kapatır.

**E. Yayın sonrası**

14. **Bekle — 2,5–3 gün.** Elle tetikleme yok, `--count` yok.
15. **Pazar kapanışında `ses_ve_tarz_takibi.md`'yi güncelle** (tablo satırı + SON DURUM —
    üretim haftasında, yayını bekleme); TikTok taslağını bir sonraki Perşembe vardiyasında
    yayınla ve işaretle.

---

## 3. Aylık ritim

Ayrı liste yok — hepsi **Pazartesi bakım yuvasına** düşüyor.

| Ayın haftası | Pazartesi bakım yuvasında | Süre |
|---|---|---|
| **1. hafta** | **Kota planlaması.** Bu ay kaç indirme kaldı? Yeni kota dönemi başladı mı? Ayın planı: kaç şarkı, set var mı, derleme var mı. | 15 dk |
| **2. hafta** | **Telif kontrolü — Studio, elle.** YouTube Data API Content ID itirazlarını **göstermiyor**; tek yol Studio → Kısıtlamalar. Üç satır: City Pulse Set, Gece Seansı Vol. 1, Just Relax. | 10 dk |
| **3. hafta** | **Derleme değerlendirmesi (koşullu, §5).** Suno kotasına dokunmayan tek uzun format. Ayda en fazla 1. | 20 dk |
| **4. hafta** | **Ölçüm.** `olcum_temel_cizgi.py --dry-run` → `--cek` → `--karsilastir`, + Studio > Analizler > Erişim CSV (CTR API'de YOK). Birincil metrik `audienceWatchRatio` %2/%3. | 30 dk |
| **her ay** | **Yedek P2** — harici diske 3,8 GB (4. hafta ile aynı oturum). | 10 dk |

⚠ **Gürültü tabanı 21,2 puan.** İçerik farkı sıfır olan kopya çiftte bile izlenme farkı
%25, beğeni farkı 6,3 kat. **Tek videonun sayısına bakma** — yalnızca 7+ videonun
ortalamasındaki YÖN okunabilir.

---

## 4. 30 günlük planın maddeleri — çevrimdeki yerleri

Ayrı bir liste yok. Her madde bir Pazartesi bakım yuvasına ya da bir Perşembe dağıtım
kutusuna düşüyor. Sıra **etkiye göre**, ön koşullar korunarak.

| Hafta | Yuva | Madde | Neden burada |
|---|---|---|---|
| 14–20 Eyl | Pzt bakım | **E-2 · Reporting API'yi aç** (5 dk) | Son tarih **10-11**; job yalnızca kurulmadan ÖNCEKİ 30 günü dolduruyor — her gecikme günü temel çizgiden bir gün siliyor. |
| 14–20 Eyl | Pzt bakım | **E-13 · ntfy aboneliğini doğrula** (3 dk) | Yapılmadıysa haftalık rapor dahil **dokuz** emniyet ağı sağır. |
| 14–20 Eyl | Pzt bakım | **E-10 P1 · robocopy yedek** (5 dk) | ~11 MB hiçbir koşulda geri gelmez. Hedef klasör paylaşıma kapalı — sır içeriyor. |
| 14–20 Eyl | Prş dağıtım | **E-9 + E-11 · Instagram arşivleme** (5 dk) | Kopya Reel `18087131705485174` "tekrarlayan içerik" tarifine giren **tek canlı yüzey**. + 4 eski kapak. |
| 14–20 Eyl | Prş dağıtım | **E-12 · bekleyen 1 yorum** (2 dk) | 5 gerçek kişiden 11 yorumun sonuncusu. |
| 21–27 Eyl | Pzt bakım | **E-3 · push'u aç** → **E-14 · bio linki** (30 dk) | `push_path()` dal `main` değilse sessizce çıkıyor; bio sayfası 7 gündür bayat, 20 içerikten 6'sı yok. ⚠ Üretim checkout'unda `git reset --hard`/`clean -f` **asla**. |
| 21–27 Eyl | Pzt 10:15 | **E-5 · AI beyanı kampanyası** (10 dk) | 42 videonun hiçbiri onarılmamış. 2.142 birim. `--dry-run --limit 100` → `--uygula --limit 42`. Cuma değil, yayın günüyle çakıştırma. |
| 21–27 Eyl | Prş dağıtım | **E-6 · TikTok taslakları** (haftada 3-5) | 21 taslak, yayınlanan 0. Tek seferde 19'u "toplu işlem" deseninin kendisi. |
| 28 Eyl–4 Eki | Pzt bakım | **E-4 · Instagram token** → **E-16** (15 dk) | Token mtime 09-01, 60 günlük sayaç ~31 Ekim'de doluyor; üç projenin yarım IG dağıtımı buna bağlı. |
| 28 Eyl–4 Eki | Pzt bakım | **C-5 · açıklama tekrarını kır** (kod) | 18 açıklamanın %61'i birebir aynı kelime → ~%35-40. Kısa formatta ortak satır zaten 0. |
| 28 Eyl–4 Eki | Pzt bakım | **C-3 · AI beyanı IG/FB/TG/Bluesky** (kod, 1 satır) | 29 gönderide hiç yok (YouTube'da 40/40 var). `build_caption()` → `build_ai_disclosure_line()`. |
| 5–11 Eki | Pzt bakım | **09 Ekim ölçümü** + **E-10 P2** | Kaçarsa 40 kapak değişikliğinin işe yarayıp yaramadığı hiçbir zaman bilinemez. |
| 5–11 Eki | Pzt bakım | **K-1/C · Shorts kapatma kararı** (§5) | Ölçüm sonrası, önce değil. |
| Sıra gelmez | — | K-4 tavan · yeni platform · `dj_clips` · tek video optimizasyonu · `Küllerimden Geç` yeni ses | Beşi de bilerek dışarıda, gerekçe §5 sonu. |

---

## 5. Karar noktaları — "dur ve karar ver" anları

Bu beş soru belirli yuvalarda sorulur; **arada sorulmaz.**

**K-A · Kota: bu ay kaç indirme? → Ayın 1. Pazartesi'si.** Varsayılan haftada 1 şarkı =
ayda 4-5 indirme; kota 20-60. Ay sonunda kotanın yarısından fazlası boşsa K-B'ye bak.
Kotanın %70'i tükendiyse kalan haftalarda Salı boş geçer, Perşembe kutusu büyür.

**K-B · Night Drive seti ne zaman indirilir? → Ayın 1. Pazartesi'si, ÜÇ koşul birden.**
12 indirme = kotanın %20-60'ı, karşılığı **tek** video. İndirme başına izlenme süresi
şarkıda 84,5 dk, sette 43-57 dk — kota başına şarkı önde; setin tek avantajı **video
sayısı**. Koşullar: (1) City Pulse itirazı Studio'dan elle kapatıldı, (2) yeni kota dönemi
başladı, (3) kotanın en az 20'si boşta. İndirilirse **12 parça, 16 değil** (45-60 dk tavan)
ve adlandırma `_segments/Night Drive 1.wav … 12.wav` — `merge_dj_set_segments.py` sırayı
**sadece** bu numaradan okuyor.

**K-C · Derleme #2 yapılsın mı? → Ayın 3. Pazartesi'si, koşullu.** Derleme Suno kotasına
**hiç dokunmuyor** ve küratörlük katmanı "toplu üretilmiş" riskini **azaltan** tek
mekanizma. Ama önce **Gece Seansı Vol. 1 ölçülmeli**: bugünkü "0 izlenme" performans değil
**ölçüm yokluğu** (15:15'te yüklendi, 16:12'de 0 ile ölçüldü, bir daha ölçülmedi). Zayıf
çıkarsa yapılmaz. **Ayda en fazla 1** — bu kural kodda ve testte YOK, elle korunuyor.

**K-D · Shorts kapatılsın mı (K-1/C)? → 09 Ekim ölçümünden sonra.** Uygulanırsa YouTube'a
giden video sayısı **42 → 21**; bedeli ölçüldü: %1,94 izlenme süresi, 0 abone, 0 paylaşım,
0 yorum. Bu bir kod haftası:
⚠ **Sıra kritik** — önce `auto_process._is_fully_done()` ve
`dj_famous_process.find_pending_sets()`'teki anahtar demetini koşullu yap, **sonra** bayrak.
Ters sırada `youtube_shorts_video_id` asla dolmaz, katalog kalıcı `pending` görünür, günlük
yayın freni sessizce devre dışı kalır (bu arıza burada üç kez yaşandı).
⚠ `config.PLATFORMS`'a dokunma — dikey render dosyasına altı platform bağlı.
⚠ Mevcut 21 Shorts **silinmez/gizlenmez**: 1.363 izlenme + 22 beğeni kalıcı gider, ve 21
videoyu tek seferde silmek "toplu işlem" deseninin kendisi.

**K-E · Bu hafta üretim yapılsın mı? → Her Pazartesi, raporun `BEKLEYEN` satırından.**
`BEKLEYEN` ana hatta 0'dan büyükse **hayır.** Yeni parça kuyruğun sonuna giriyor
(`find_ready_projects()` klasör oluşturma zamanına göre sıralıyor) ve önündeki geri
doldurmalar bitmeden hiç işlenmez.

### Kapalı kalacaklar — bir daha açma

1. **Shorts üretmeye devam etmek** — 1.363 izlenme → 70 dk izlenme süresi (%1,94),
   0 abone/paylaşım/yorum. Keşif gerekçesinin üç göstergesi de sıfır.
2. **Telegram/Bluesky/Facebook tavanını yükseltmek** — tarifte bakılan şey haftalık toplam
   değil **günlük desen**, kazanç ise ölçülemiyor. Tavan 1.
3. **Yeni platform eklemek** — gerçek tavan Suno kotası, platform sayısı değil.
4. **`dj_clips` kesit hattı** — küratörlük eklemiyor, yalnızca hacim ekliyor. ⚠ Onay
   gelmeden `Just Relax`'e `dj_tarama_temiz: true` **yazılmasın** — o işaret konduğu an
   bir sonraki koşu kesidi otomatik yükler.
5. **Tek video / başlık optimizasyonu** — gürültü tabanı 21,2 puan; başlık korelasyonu tek
   bir toplu yükleme çıkarılınca **ters dönüyor**. Örüntü değil, gürültü.

> **Çerçeve:** YPP tarihini hedefleme. Darboğaz izlenme saati değil **abone**: net +28/28
> gün → 1.000 abone ~2,7 yıl. İzlenen iki oran: **Suno birimi başına izlenme dakikası** ve
> **video başına abone**.

---

## 6. Bu hafta — 2026-09-14 → 2026-09-20 (ISO 2026-W38)

Bugün **Cumartesi 12 Eylül**. Çevrimin ilk turu Pazartesi başlıyor; hafta sonu boş
(boru hattı iki geri doldurmayı — Kader Ortakları, Bu Gece Kazandık → Instagram — kendi
işliyor).

| Tarih | Yapılacak | Süre |
|---|---|---|
| **14 Eyl Pzt** | **09:00+ · ilk haftalık özet telefona düşer.** ⚠ `ÖLÇÜM` satırı "ilk hafta – temel çizgi kaydedildi" diyecek; **değişim sayısı olmaması normal.** Özet hiç gelmezse ntfy aboneliği yok demektir → E-13'ü ilk işe al. | 5 dk |
| 14 Eyl Pzt | **E-2 · Reporting API'yi aç** (Google Cloud Console, tek tık; bugün `cekilebildi_mi=false`, 403) | 5 dk |
| 14 Eyl Pzt | **E-13 · ntfy aboneliğini doğrula** (telefonda konuya abone ol, test bildirimi gelsin) | 3 dk |
| 14 Eyl Pzt | **E-10 P1 · robocopy yedek** (111 MB, hedef klasör paylaşıma kapalı) | 5 dk |
| **15 Eyl Sal** | **Üretim · "Vardiya"** (rock, kadın vokal, 78 BPM). `vardiya_sozler.md` **yazıldı** — §2'nin 1-3. adımları bitti, **4. adımdan başla**: `projects/Vardiya/` klasörünü aç → `{"title": "Vardiya", "theme": "rock"}` → Chrome çevirisi kapalı → stil etiketi + sözler → indir. ⚠ Pazartesi raporu `BEKLEYEN`'de iş gösteriyorsa **bu günü atla.** | 45 dk |
| 16 Eyl Çar | — (render + kuyruk, otomatik) | 0 |
| **17 Eyl Prş** | **E-9 + E-11 ·** Instagram'da kopya Reel `18087131705485174`'ü **arşivle** (silme) + 4 eski kapaklı gönderiyi kaldır. Aynı oturumda **E-12 ·** bekleyen 1 yorumu yanıtla. | 10 dk |
| 17 Eyl Prş | **E-6 ilk kutu ·** 3-5 TikTok taslağı yayınla + `--yayinlandi-hepsi` ile işaretle (City Pulse Set ve Küllerimden Geç hariç) | 15 dk |
| 18 Eyl Cum | **Dokunma** — DJ görevi 18:00'de koşuyor | 0 |
| 19 Eyl Cmt | — | 0 |
| **20 Eyl Paz** | **Kapanış ·** `ses_ve_tarz_takibi.md`'ye Vardiya satırı (rock / 78 / smoky husky low-register female) **+ SON DURUM satırı** ("son üretim KADIN vokal, tekli"). Vardiya bu tarihe kadar yayına çıkmamış olabilir — **satır yine de yazılır** (dosya üretim sırasını tutuyor). Bio linkini gözle doğrula. | 15 dk |

**Toplam: ~1 saat 45 dakika.**

**Bu hafta bilerek YAPILMAYACAKLAR:** Night Drive indirilmeyecek (K-B üç koşulu sağlanmadı)
· E-5 kampanyası çalıştırılmayacak (gelecek hafta, E-3'ten sonra) · Shorts'a
dokunulmayacak (09 Ekim ölçümünden sonra) · elle `--count` verilmeyecek.
