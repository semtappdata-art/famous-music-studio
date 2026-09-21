# Üretimden yayına hazır olma süresi (bu makinede ölçüldü)

> Yazıldığı an: **2026-09-12 23:10**. Hiçbir render, yükleme ya da Suno işlemi çalıştırılmadı.
> Kaynaklar yalnızca yerel kayıtlar: `auto_process.log` (06 Eyl 08:34 → 12 Eyl 23:05, 3.357 satır,
> 7 günlük döngü), `gorev_izleri/*.log` (12 Eyl 12:05'ten beri), `projects/*/state.json`
> damgaları, dosya mtime/ctime, `ffprobe` süreleri ve kurulu görev tanımı (`Get-ScheduledTask`).
> Log'daki `sıradaki için ~23.0 / 0.7 / 9.0 saat` dörtlüleri pytest kirliliği; hesaba katılmadı.

**Tek cümle:** Makinenin bir şarkıya harcadığı süre **~10-15 dakika**, Suno ve saatlik bekleme
dahil **~1-1¾ saat**. Takvimde ise **günler** sürüyor. Bunun sebebi makine değil: 52 saatlik
taban, kuyruğun başındaki geri doldurmanın sırayı tutması ve golden-hour kuralları.

---

## 1. Ölçülmüş aşama tablosu

| # | Aşama | Medyan | En kötü | n | Kaynak / not |
|---|---|---|---|---|---|
| 1 | **Suno** — son sözler kaydı → ses indirildi (yapıştırma, 2 varyant, A/B, indirme) | **~22 dk** | **32 dk** | 4 | `*_sozler.md` mtime → `audio.*` mtime. Kader 17,0 · Sokaklar 18,8 · Bu Gece 24,3 · Sabah Senin 32,3 (A/B + iki indirme). Eski projelerde klasör→ses 3,8-17 dk (n=5, sözler sonradan düzenlendiği için zayıf kanıt) |
| 2 | **Fark edilme** — ses klasörde → ilk `auto_process` koşusu | ~1 dk (izleyici) / **≤60 dk** (saatlik) | 60 dk | 1 | Sabah Senin doğrudan `audio.wav` adıyla kondu (20:13:53). İzleyici yalnız farklı adlı dosyayı dönüştürürken tetikliyor, bu yüzden tetiklemedi (kök `watch_projects.log`'da satır yok). Dosyayı ilk gören koşu 21:05 oldu: **51 dk**. İzleyicinin tetiklediği bir render bu log penceresinde yok |
| 3 | **Tempo beklemesi** (KURAL, makine değil) — kuyruğun başında bekleme | ~26 sa | 51,6 sa | 4 | Proje başına "bu koşuda işlenecek" satırının ilk ve son görülüşü: Yürek Yarası 1,0 · Yeraltı 11,3 · Sessiz Mektup 41,0 · Son Kez 51,6 sa. Sabah Senin'in hesaplanan beklemesi: **40 ya da 68 sa** (§4) |
| 4 | **Kapak + art + backdrop** (Pexels dahil) | ~25-35 sn | ~60 sn | 3 | `audio` → `art.jpg` → `cover.png` → "=== Render" satırı: Kader 34 sn, Bu Gece 24 sn, Küllerimden ≤1 sn (art hazırdı). Backdrop PNG'leri +4-7 sn |
| 5a | **Render, duvar saati** (uzun format + Shorts paralel) | **257 sn** | **310 sn** | 5 | `output/*.mp4` ctime → mtime. Ses süresine bölününce **1,41×** (en kötü **1,72×**). Sokaklar 1,72 · Kader 1,51 · Küllerimden 1,41 · Yeniden Doğacağım 1,22 · Bu Gece 1,14 |
| 5b | Render, eski sıralı dönem (05 Eyl) | toplam 1,43× | 1,58× | 10 | Uzun format 0,83-1,23× + Shorts 43-58 sn. **Paralel render (`MAX_PARALLEL_RENDERS=2`) duvar saatini KISALTMIYOR.** İş CPU'ya bağlı, paralel dönemde Shorts tek başına 86-126 sn'ye çıktı |
| 5c | Render, **yeni biçim** (açılış kapağı, sessizlik kırpma, 11 Eyl sonrası) | **ölçülemedi** | — | 0 | Ana katalogdaki son render 08 Eyl 21:19. `ffmpeg_utils.py`/`stock_video.py` 11 Eyl 20:56'da, `render.py` 12 Eyl 17:02'de değişti. Stok video yalnız DJ setlerinde kullanılıyor (`backdrop.mp4`). Vekil olarak DJ/derleme render'ları 0,85-2,26× (n=3, uzun ve farklı içerik) |
| 6 | **Yükleme zinciri** — render bitişi → son platform | ~2,5 dk | ~4 dk | 4 | YouTube +8-10 sn (n=3) · Shorts +5-9 sn · TikTok taslağı +23-28 sn · IG konteyneri/yayını +30-106 sn · FB +13-20 sn · TG +5-13 sn · Bluesky +28-34 sn. Sokaklar 142 sn, Sofraya 119 sn, Kader geri doldurma 152 sn |
| 6b | Render içeren koşunun tamamı | ~5 dk | 6,6 dk | 3 | Kader 304 sn, Bu Gece 265 sn, Sokaklar 397 sn (şarkılar 2:25-3:10) |
| 7 | **YouTube ASR → hizalanmış altyazı** | ASR: **7-47 dk** | **37,9 sa** (boru hattı) | 2 + 3 | Temiz örnek: Kırık Zincir 6,6 dk, Küllerimden 47 dk. Log'da "ASR henüz hazır değil" satırı **toplam 3 kez** geçiyor. Kader 37,8 sa, Bu Gece 37,9 sa ve Sokaklar 18,2 sa gecikmesinin sebebi YouTube değil; bkz. Risk R-2. Eskiler (80-252 sa) kota 403, token ve sonradan eklenen özellik yüzünden |
| 8 | **Instagram** — konteyner → yayın (golden-hour bekleme dahil) | **6,3 sa** | 11,4 sa (ölçülen) / 14,0 sa (Kader, beklenen) | 3 | Yürek Yarası 1,0 · Sofraya 6,3 · Yeraltı 11,4 sa (11 Eyl 12:xx koşusu kaçtı, +1,4 sa). Yayın her zaman golden-hour içindeki bir **hh:05** koşusunda |
| 9 | **Facebook / Telegram / Bluesky** | yeni yayında anında | geri doldurma: gün başına 1 | — | FB zamanlamayı kendisi yapıyor (`scheduled_publish_time`). TG/Bluesky **anında** gönderiliyor, golden-hour beklemiyor (bkz. R-4). Geri doldurma yalnız golden-hour içinde ve günlük tavan 1 |
| 10 | **Makine kapalı/uykuda** | gece 7-10 sa | 9,9 sa | 7 boşluk | Log boşlukları (>75 dk): 06→07 Eyl 7,0 · 07→08 Eyl 9,9 · 11→12 Eyl 9,6 sa (geceler). Gündüz: 2,4 · 5,0 · 4,0 · 2,4 sa. 158 saatin **~40 saati (%25)** kayıp. `WakeToRun=False`, yani uyku koşuyu engelliyor |
| 11 | **Saatlik koşu (render yok)** | **7 sn** | p90 75 sn · maks 30,6 dk | 144 | Log bölütleri. `gorev_izleri`: 7,5 · 17 · 53 · 163,5 sn. Render içeren en uzun koşu 6,6 dk. `LOCK_STALE_SECONDS` = 4 sa (**~35× pay**), `ExecutionTimeLimit` = 2 sa |

**Golden-hour koşularının güvenilirliği** (tam 5 gün, 07-11 Eyl, saat bazında log var mı):
12:xx **4/5** (12 Eyl'de de yok, çünkü görev 12:05'te yeniden kuruldu) · 13:xx **5/5** · 18:xx **3/5** ·
19:xx-21:xx **5/5**. Öğle penceresinin güvenilir koşusu 12:05 değil **13:05**; akşamın 19:05-21:05.

---

## 2. Uçtan uca model — "Suno'da başla → her platformda yayına hazır / zamanlanmış"

Hesaplanan örnek `Sabah Senin` (272 sn, katalogdaki en uzun şarkı).

### 2a. Makinenin aktif çalıştığı süre

| Aşama | Medyan | En kötü |
|---|---|---|
| Suno (elle) | 22 dk | 32 dk |
| Fark edilme | ~1 dk (izleyici) · ort. 30 dk (saatlik) | 60 dk |
| Kapak/art | 0,5 dk | 1 dk |
| Render (272 sn × 1,41 / 1,72) | 6,4 dk | 7,8 dk (yeni biçim ölçülmedi, +%20 pay → ~9,5 dk) |
| Yükleme zinciri (6 platform) | 2,5 dk | 4 dk |
| **Makine işi (kapak+render+yükleme)** | **~10 dk** | **~15 dk** |
| **Suno başından her şey yüklenene kadar** | **~1 sa** | **~1 sa 45 dk** |

Bu sürenin ardından iki kısa iş daha var ve ikisi de ayrı koşularda oluyor: IG yayını (bir sonraki
golden-hour koşusu) ve altyazı (1-3 koşu sonra).

### 2b. Gerçek takvim süresi

```
hazır ses ──► [≤60 dk fark edilme] ──► [TEMPO KAPISI: max(52 sa taban, 24 sa/N pencere) + ~1 sa kayma]
         ──► [~10-15 dk render+yükleme] ──► YouTube: pencere içindeyse hemen public, dışındaysa publishAt
         ──► IG: bir sonraki pencere koşusu (≤14 sa, makine kapalıysa daha uzun)
         ──► altyazı: 1-3 koşu (başka proje takılmadıysa)
```

- **Kuyruk boşken, son public'ten 52 sa geçmişken:** ses → public **~1-2 sa** (pencere içindeyse)
  ya da **≤14 sa** (pencere dışındaysa `publishAt`).
- **Önünde bir şarkı varken:** o şarkının public anı **+52 sa +~1 sa**.
- **Gece kapalılık etkisi:** YouTube'u etkilemiyor, çünkü yükleme her saatte olabilir ve `publishAt`
  pencereyi kendisi tutuyor. Asıl etkilediği şey IG yayını ve tempo kapısının açıldığı koşu.
  Kapı gece açılırsa iş sabahki ilk telafi koşusuna kalıyor (`StartWhenAvailable`; ölçülen
  örnekler 06:46:57 ve 09:04:16).

**Kayma nedir:** Damgalar hh:05:2x'te yazılıyor, koşu ise hh:05:09-12'de başlıyor. Kapı koşudan
birkaç saniye sonra açıldığı için iş bir saat kayıyor. Ölçülen örnek: 21:05 "~0.0 saat daha var",
iş 22:05'te yapıldı.

### Darboğaz sırası

1. **52 saatlik yeni yayın tabanı** (kural). Tek başına günlerin sebebi.
2. **Kuyruk başı tıkanması** (kod, R-1). Golden-hour bekleyen bir geri doldurma, arkasındaki yeni
   şarkının seçilmesini engelliyor. Ölçülen bedel 1-52 sa.
3. **Makine kapalı saatler**, ancak bir pencere koşusuna ya da kapının açıldığı ana denk gelirse.
4. Render: darboğaz **değil** (5-8 dk).

---

## 3. Kural: en geç başlama anı

Bir yayın koşusu (R) üç koşul birden sağlanınca işliyor:
(a) tempo kapısı açık, (b) ses R'den önce klasörde, (c) makine R'de açık ve uyanık.

| Hedef pencere | Önerilen R | Sonuç | Suno'ya en geç başlama | Makine açık/prizde olmalı |
|---|---|---|---|---|
| **12:00-14:00** | **11:05** | Render+yükleme ~11:20'de biter · YouTube `publishAt 12:00` · FB 12:00'ye zamanlı · IG 12:05'te (yedek 13:05) yayınlanır | **10:25** | 10:25-11:25 **ve** 12:00-13:15 (IG) |
| 12:00-14:00 (son çare) | **13:05** | Pencere içinde yüklenir, ~13:15'te her şey birlikte public olur | **12:25** | 12:25-13:25 |
| **18:00-22:00** | **17:05** | YouTube `publishAt 18:00` · IG 18:05 (yedek 19:05) | **16:25** | 16:25-17:25 **ve** 18:00-19:15 |
| 18:00-22:00 (son çare) | **21:05** | ~21:20'de public | **20:25** | 20:25-21:25 |

- **Suno tarafının hesabı:** 32 dk (en kötü) + 3 sn kararlılık beklemesi + ~5 dk pay = R − 40 dk.
  Tempo kapısı çoğu zaman bundan günler önce belirleyici olduğu için **pratik kural: sesi hedef
  pencereden en az bir gün önce indir**, makineyi hedef koşuda açık tut.
- **Render golden-hour içine düşerse:** YouTube pencere içindeyse hemen public, dışındaysa bir
  sonraki pencereye `publishAt`. Render en kötü ~15 dk sürdüğü için 13:05 ve 21:05 koşuları
  pencereyi kaçırmıyor. Kaçırmak için yeni biçimdeki render'ın 55 dk'yı aşması gerekir; bu
  ölçülmedi ama beklenmiyor. Kaçırırsa 14:0x yüklemesi 18:00'e, 22:0x yüklemesi ertesi gün
  12:00'ye zamanlanır.
- **Instagram 23 saatlik ömür:** Konteyner R'de oluşturuluyor. 22:00'ye yakın oluşturulan bir
  konteynerin **dört şansı** var: ertesi gün 12:05 (+14 sa), 13:05, 18:05 ve 19:05-21:05.
  21:05'te yaş ~23 sa sınırında. **Öğle ve akşam pencerelerinin ikisinde de makine kapalıysa
  konteyner bayatlıyor.** Kod onu siliyor ve elle `instagram_upload.py --project` gerekiyor.
  Kader'in konteyneri (12 Eyl 22:06:42) için son makul koşu **13 Eyl 21:05**.

---

## 4. Somut takvim (13 Eylül'den itibaren)

**Bugünkü kuyruk** (`find_ready_projects`, getctime sırası):
Kader Ortakları (08 Eyl 19:59, IG bekliyor) → Bu Gece Kazandık (08 Eyl 20:45, **bekletmede**,
sıra dışı) → Sabah Senin (12 Eyl 16:30, yeni). Küllerimden Geç tamamlanmış görünüyor, ama
state'inde bir görünürlük planı var.

**Kapı saatleri:** Son yükleme damgası Sofraya IG 12 Eyl 13:05:24. Günlük pencere 24/2 = 12 sa,
yani 13 Eyl 01:05 (kayma ile 02:05). Son yeni yayın Bu Gece 08 Eyl 21:19; 52 sa çoktan doldu.

Aşağıda iki senaryo var. Ayrımı paralel ajanın alanındaki bir kapı yapıyor:
`Küllerimden Geç` görünürlük planı `uyumluluk.kontrol(..., "yukleme")`'den geçip uygulanacak mı?
(md5 ikizi Yeniden Doğacağım. İki ses dosyası da 42.108.076 bayt.) **Plan uygulanırsa
`youtube_publish_at` = uygulama anı yazılıyor ve 52 saatlik saat yeniden başlıyor**
(`auto_process.py` 896-897. satır, `_son_yeni_yayin_ani`).

| Sıra | Proje | Başlama (koşu) | Hazır | Public / yayın | Not |
|---|---|---|---|---|---|
| — | **Kader Ortakları** | 13 Eyl 02:05'ten itibaren her koşu (no-op) | hazır | **IG 13 Eyl 12:05** (yedek 13:05; 18:05-21:05). FB 12:00 zamanlı. Bluesky 12 Eyl 22:07'de çıktı. TG **belirsiz**, elle kontrol et | Kuyruğun başında durduğu için Sabah Senin'i 12:05'e kadar tutuyor (R-1) |
| — | **Küllerimden Geç** (plan) | 13 Eyl 12:05 | hazır | **Shorts public 13 Eyl 12:05** (uzun format zaten public) | Pencere başına tek plan. Uyumluluk kapısı düşürürse uygulanmaz, 3 sa sonra tekrar denenir |
| 1 | **Sabah Senin** — **A** (plan uygulandı) | 15 Eyl 16:05 kapısı → kayma ile **17:05** | ~17:20 | **YouTube 15 Eyl 18:00** (`publishAt`) · IG 18:05 · FB 18:00 · TG/Bluesky ~17:20 (erken, R-4) · altyazı ~18:05-20:05 | Salı akşamı. Makine 17:00-19:15 açık olmalı |
| 1 | **Sabah Senin** — **B** (plan uygulanmadı) | 14 Eyl 12:05 kapısı → kayma ile **13:05** | ~13:20 | **Her şey 14 Eyl ~13:15'te** (pencere içinde) | Pazartesi öğlesi. Makine 13:00-13:30 açık olmalı |
| 2 | **Bu Gece Kazandık** (yeni render + yeni YouTube yüklemesi) | Bekletme kalkınca. **A:** 52 sa → **17 Eyl 22:05** · **B:** **16 Eyl 18:05** | +15 dk | **A: YouTube 18 Eyl 12:00** (`publishAt`), IG 18 Eyl 12:05 · **B: 16 Eyl ~18:20** her şey | Hazırlık elle: `output/` temizliği, YouTube kimlikleri, bekletmenin kaldırılması (paralel ajan). **Bekletmeyi Sabah Senin'in `youtube_uploaded_at`'i yazılmadan kaldırma**, yoksa getctime sırasıyla Sabah Senin'in önüne geçer |
| 3 | **Bir sonraki yeni şarkı** (Salı 15 Eyl üretimi) | **A:** 52 sa → **20 Eyl 16:05** · **B:** **18 Eyl 23:05** | +15 dk | **A: 20 Eyl 18:00** (Paz akşamı) · **B: 19 Eyl 12:00** (`publishAt`) | Salı indirilirse ses 5 gün bekler. Maliyeti yok ama gereksiz. **En geç Suno başlangıcı: A için 20 Eyl 15:25, B için 18 Eyl 22:25** |

### Önerilen sıra ve gerekçesi

**Kader IG → Küllerimden Shorts → Sabah Senin → Bu Gece Kazandık → yeni şarkı.**

1. **Sabah Senin, Bu Gece'den önce.** Sabah Senin kanal için yeni içerik. Bu Gece ise 4 gün public
   kalıp unlisted'a çekilmiş bir şarkının yeniden yüklemesi. Aynı sesin ikinci videosu "toplu /
   tekrarlayan içerik" riskine değiyor; araya en az bir tam 52 sa girmesi, ikisini aynı haftanın
   iki ucuna atmaktan iyi. Sıra aracı kod değil **bekletme alanı**: kaldırma anı sırayı belirliyor.
2. **Senaryo A ile B arasındaki fark ~29 sa.** Küllerimden'in uzun formatı zaten public, izleyici
   açısından "yeni şarkı" değil. Yine de kod onu yeni yayın sayıyor. A'da Sabah Senin Salı 18:00'e
   düşüyor (rock için akşam penceresi iyi, Pazartesi 10:15 kota işleriyle de çakışmıyor). Kodu
   değiştirmeye gerek yok. Karar kullanıcının: A kabul edilebilir.
3. **Cuma:** A'da Bu Gece'nin yüklemesi Perşembe 22:05'te yapılıyor, yani kota Perşembe günü
   harcanıyor. Cuma 12:00'de yalnız `publishAt` tetikleniyor; DJ koşusunun (Cuma 18:00) kotasıyla
   çakışma yok.
4. **Yeni şarkının vokali:** `ses_ve_tarz_takibi.md` SON DURUM "Sabah Senin'den sonra kadın üst
   üste ikiye çıkmasın" diyor. Hazır bekleyen `Yükseliş` (hiphop, *smoky laid-back female*) bu
   kurala takılıyor. "Vardiya" profili (rock, kadın, 78 BPM) ise zaten Sabah Senin olarak üretildi.

---

## 5. Riskler

| # | Risk | Ölçülen kanıt | Etki | Önlem (kod değişikliği yok) |
|---|---|---|---|---|
| **R-1** | **Kuyruk başı tıkanması** (kod). `batch = pending[:1]`, golden-hour bekleyen bir geri doldurmayı her koşuda yeniden seçiyor. Arkadaki yeni şarkı kapı açıkken de seçilemiyor | Son Kez 51,6 sa · Sessiz Mektup 41 sa · Yeraltı 11,3 sa başta kaldı. Bugün: Kader 13 Eyl 02:05-12:05 arası Sabah Senin'i tutacak | Yeni yayın 10 sa ile 2 gün arası gecikir | Raporla. IG konteyneri olan projeyi sıra dışı saymak (bekletme deseni gibi) ayrı bir karar |
| **R-2** | **Altyazıda tek-slot açlığı** (kod). `_drain_golden_hour_queue` koşu başına tek API denemesi yapıyor. Hata veren proje (`Temiz Sözler` bölümü eksik) slotu her koşu yeniden alıyor | 08-10 Eyl: Sofraya'ya 33 HATA. Kader ve Bu Gece 37,8 sa bekledi. Sofraya düzelince 09:07, 10:12, 11:12'de saatte birer tamamlandı | Altyazı 1,5 gün gecikir. N proje bekliyorsa N saat | Sözler dosyası şablona uygun mu, yükleme öncesi kontrol |
| **R-3** | **Makine kapalı / uykuda** | %25 saat kayıp. Geceler 7-10 sa. 12:05 koşusu 7 günün 2'sinde, 18:05 koşusu 5 günün 2'sinde yok. `WakeToRun=False` | IG konteyneri bayatlar (iki pencere üst üste kaçarsa). Tempo kapısı kayar | Hedef günlerde 13:05 ve 19:05'i garantile. Uyku ayarı kararı kullanıcıda |
| **R-4** | **Telegram/Bluesky golden-hour beklemiyor** (kod). `_ek_platformlari_isle`'de zamanlama desteği yalnız FB'de | Bluesky Kader için 12 Eyl 22:07'de, Sofraya için 06:48'de gönderildi | Yeni şarkı pencere dışında işlenirse TG/BS YouTube public olmadan önce çıkar (A'da ~40 dk; gece koşusunda saatler) | Raporla. Geri doldurma yolu zaten golden-hour'a bağlı |
| **R-5** | **İzleyici 5 dk sınırı ve uzun şarkı** | Sabah Senin render'ı hesapla 6,4-7,8 dk. Watcher görevi `ExecutionTimeLimit` = **PT5M** | Tetiklenen süreç görevden kopamazsa render yarıda öldürülür ve yarım mp4 "VAR" sayılır | Sabah Senin zaten `audio.wav` olarak kondu, saatlik göreve kalıyor (limit 2 sa). Kopma düzeltmesi render'lı bir koşuda henüz doğrulanmadı |
| **R-6** | **Kilit ve render** | Render en kötü 6,6 dk. `LOCK_STALE` 4 sa, `TRIGGER_LOCK_FRESH` 15 dk | **Sorun yok.** Kilit render'dan ~35× uzun | — |
| **R-7** | **Instagram 23 sa** | Kader konteyneri 12 Eyl 22:06:42 | 13 Eyl'de öğle ve akşam kaçarsa kaybolur | 13 Eyl 12:00-14:00'te makine açık |
| **R-8** | **Saniye kayması** | 21:05 "~0.0 saat", iş 22:05'te | Her kapı +1 sa | Tasarımda var (52 = 56 − kayma) |
| **R-9** | **`gorev_izleri` eksik** | 15:05 BAŞLADI'nın BİTTİ'si yok. 16:05-21:05 arası hiç iz yok, ama `auto_process.log` bu koşuları gösteriyor | "Koşu yok" teşhisi bu dosyaya dayandırılamaz | Önce `auto_process.log`'a, sonra `saglik_durum.json` `son_kosu_ts`'e bak |

---

## 6. Belirsizlik — ölçülmedi, varsayım

- **Yeni biçim render süresi (11 Eyl sonrası):** 0 örnek. 1,41× (en kötü 1,72×) eski biçimden
  alındı, üzerine +%20 pay kondu.
- **İzleyici tetiklemesi → koşu başlangıcı:** bu log penceresinde örnek yok. "~1 dk" koda dayalı
  bir varsayım (3 sn kararlılık + dakikalık görev).
- **Suno aşaması:** n=4, dosya mtime'larından türetildi. Sohbet ya da tarayıcı kaydı yok. Sözler
  dosyası indirmeden sonra düzenlenmiş olabilir. Bugünkü "~1-2 dk üretim + indirme" gözlemi bu
  sürenin yalnız bir parçası.
- **FB/TG/Bluesky'nin yeni yayındaki süresi:** yalnız geri doldurma örnekleri var (n=2 koşu).
- **ASR'nin gerçek süresi:** temiz örnek n=2 (7 ve 47 dk). Diğer bütün gecikmeler boru hattı kaynaklı.
- **Senaryo A/B:** Küllerimden planının uyumluluk kapısından geçip geçmeyeceği paralel ajanın işine
  bağlı. Bu belge onu değiştirmiyor.
- **Bu Gece Kazandık'ın yeniden yüklenme yolu** (state'ten hangi alanların silineceği): paralel
  ajanın ya da kullanıcının kararı. Takvim, bekletme kaldırıldığı an kuyruğa normal bir yeni yayın
  olarak girdiğini varsayıyor.
- **Makine davranışı:** son 7 günden genellendi. Hafta sonu ve iş günü farkı ayrıştırılamadı.

## Doğrulama notu (ana oturum, 2026-09-12 gece)

Yukarıdaki kod bulgularından **"İzleyici görevinin 5 dakikalık süre limiti render'ı yarıda
kesebilir" maddesi YANLIŞ ALARM**: `watch_projects._trigger_script` `auto_process.py`'yi
`subprocess.Popen` + `CREATE_BREAKAWAY_FROM_JOB` (+ `DETACHED_PROCESS`) ile başlatıyor;
çocuk süreç görevin iş nesnesinden (job) kopuyor, bu yüzden görevin `ExecutionTimeLimit`'i
(5 dk) onu öldüremez. Bu, tam olarak 2026-09-12'de kapatılan arızanın düzeltmesi
(fonksiyonun kendi docstring'i: "NEDEN SADECE `Popen` YETMEZ"). Saatlik görevin limiti
2 saat. Diğer bulgular (kuyruk başı tıkanması, altyazı hakkının tek projede tükenmesi,
görünürlük planının tempo tabanını yeniden başlatması, Telegram/Bluesky'ın golden-hour'u
beklememesi, `gorev_izleri` iz boşlukları) doğrulanmadı ve açık görev olarak kayıtlı.

### Doğrulama turu 2 (salt okunur ajan, 2026-09-12 gece)

Kalan beş bulgu koddan ve log'dan tek tek doğrulandı:

| # | Bulgu | Sonuç |
|---|---|---|
| 1 | Kuyruk başı tıkanması (`pending[:1]`) | **DOĞRU** — Son Kez 28, Sessiz Mektup 34, Yeraltı 11 kez yalnız "Instagram konteyneri golden-hour bekliyor" için seçildi. Simülasyon: `Sabah Senin` 14 Eyl 13:05 (baş atlansaydı 13 Eyl 02:05). |
| 2 | Altyazı hakkının tek projede tükenmesi | **KISMEN** — `Sofraya Gelmedin` 33 ardışık hata; soğuma yalnız `LyricsMismatch`'i kapsıyor. Bugün etkisi yok (18/18 altyazı tamam), sınıf açık. Ek ters hata: `LyricsNotReady` API harcandıktan sonra atılıyor ve hakkı tüketmediği için kota katlanıyor. |
| 3 | Görünürlük planı tempo tabanını yeniden başlatıyor | **DOĞRU** — plan zaten public olan uzun formata da `_publish_at` yazıyor; `Sabah Senin`'i 28 saat geri itiyor (15 Eyl 17:05 yerine 14 Eyl 13:05). |
| 4 | Telegram/Bluesky golden-hour beklemiyor | **DOĞRU** — ana hat `_ek_platformlari_isle`'de golden-hour/gizlilik/tavan kapısı yok (geri doldurmada üçü de var); pencere dışında işlenen yeni şarkı YouTube private + `publishAt` iken linkiyle TG/BS'ye düşer. |
| 5 | `gorev_izleri` iz boşlukları | **YANLIŞ ALARM** — 13:05-23:05 arası 11 koşunun hepsinde BAŞLADI/BİTTİ çifti var; izleyicinin tetiklediği koşu da sarmalayıcıdan geçiyor. `auto_process.log`'daki BAŞLADI'sız 20:36-20:55 satırları zamanlayıcı dışı (pytest/elle) koşular. |

Yani bu dosyadaki altı kod bulgusunun **ikisi yanlış alarm** (izleyici 5 dk limiti, iz boşlukları), üçü doğru, biri kısmen doğru. Uygulama kararı ve sırası: `denetim_bulgulari_2026-09-12.md` / görev listesi.
