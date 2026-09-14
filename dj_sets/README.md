# DJ Famous — haftalık özel üretim

Bu klasör, kanalın **ana kataloğundan (günlük 6 üretim, `projects/`) tamamen ayrı**,
haftada bir kez yayınlanan "DJ Famous" setleri içindir. Otomasyonu `auto_process.py`
DEĞİL, `dj_famous_process.py` işler — ikisi birbirine hiç karışmaz, ayrı kilit
dosyaları ve log dosyaları kullanırlar.

## DJ Famous nedir, ana katalogdan farkı ne

- **Ana katalog** (`projects/`): kurgusal temalar/karakterler, Suno ile üretilen
  şarkılar — kimse gerçek bir kişiyi temsil etmiyor.
- **DJ Famous**: **gerçek, tanınabilir bir kişiyi** (kendi rızasıyla, "DJ Famous"
  sahne adıyla) konu alıyor. Set içeriğinin **tamamı AI ile üretiliyor** — bu
  bilinçli bir tasarım kararı ve **hiçbir şekilde gizlenmiyor**:
  - YouTube: her yüklemede otomatik `containsSyntheticMedia=True` (ana katalogla
    aynı, kod tarafında zaten var).
  - TikTok: yüklerken script "AI-generated content" etiketini uygulamadan elle
    açman gerektiğini hatırlatıyor (TikTok'un Taslak/Gelen Kutusu akışında API'den
    ayarlanamıyor — bkz. `upload/tiktok_upload.py`).
  - Instagram: caption'ın sonuna otomatik olarak tek, göze az batan bir satır
    ekleniyor ("Bu içerik yapay zeka ile üretilmiştir.") — Meta'nın resmi API
    alanı (`is_ai_generated`) doğrulanamadığı için bu, en güvenilir yöntem
    (bkz. `upload/social_text.py::build_ai_disclosure_line`).

  Bu üçü de **sadece zorunlu olanı, mümkün olduğunca küçük/göze batmayan** şekilde
  yapıyor — videonun üzerine ekstra bir "AI" yazısı/filigranı EKLENMİYOR, platformların
  kendi resmi, standart mekanizmaları kullanılıyor.

## Görsel/kimlik — ÖNEMLİ

Gerçek bir kişinin fotoğrafından/görüntüsünden AI ile içerik üretmek **o kişinin
kendi açık onayını** gerektirir (aile içi bir karar olsa bile — bu onun kimliği).
Bu proje için onay zaten alındı; yeni bir kullanım/platform eklenecekse tekrar
teyit edilmeli.

## Klasör yapısı

Ana kataloktaki `projects/<isim>/` ile AYNI kurala göre çalışır — render.py,
generate_cover.py, validate_project.py hepsi buradaki klasörleri de tanır:

```
dj_sets/<set-adı>/
    audio.wav          # set kaydı (uzun olabilir, ör. ~1 saat — render süresi/sıkıştırılmış
                        # dosya boyutu buna göre artar, bu normal)
    art.jpg             # Arda'nın (AI ile üretilmiş/işlenmiş) fotoğrafı — kartın içeriği +
                        # arka plan blur kaynağı olarak kullanılır
    meta.json           # {"title": "Gece Yarısı Seti", "theme": "dj",
                        #  "marquee_text": "DJ Famous  •  Gece Yarısı Seti  •  #DJFamous"}
```

**"#AIMusic"/"#YapayZekaMüzik" gibi AI-vurgulu ibareler kullanılmıyor** (kullanıcı
kararı — hiçbir üretimde, ne kayan yazıda ne caption'da ne YouTube etiketlerinde).
Bu, ZORUNLU AI-üretimi bildirimini DEĞİŞTİRMİYOR — o ayrı bir mekanizma ve hâlâ
yerinde (YouTube `containsSyntheticMedia`, TikTok'ta uygulama içi etiket hatırlatması,
Instagram caption'ındaki bildirim satırı). Kaldırılan sadece marka/keşfet amaçlı
hashtag'ler (`config.BRAND_HASHTAGS`, YouTube `tags`) — bkz. `config.py`'deki not.

**Klasör adı ve `title` — "Hafta 1"/"1-2" gibi sıralı/numaralı bir isimlendirme
KULLANILMIYOR.** Her set kendi içeriğine göre betimleyici bir isim alır (ör. "Gece
Yarısı Seti", "Yaz Akşamı Seti") — sıra numarası veya hafta etiketi yok.

`marquee_text` — videonun altındaki SABİT (kaymayan) satır HER ZAMAN "Famous Music
Studio" kalır (`config.STATIC_LABEL_TEXT`, ana katalogla aynı, değişmiyor). Onun
ÜSTÜNDEKİ KAYAN yazı alanına DJ Famous için "DJ Famous" adı + setin içerik/müzik
bilgisi + hashtag'ler gibi özel bir metin koymak için `meta.json`'a `marquee_text`
eklenir — verilmezse ana kataloktaki varsayılana (title + tema/tür etiketleri) düşer.
`title` alanı ayrı kalır (YouTube başlığı/kapak metni için kullanılmaya devam eder,
hashtag İÇERMEMELİ — sadece `marquee_text`'e).

`cover.jpg` elle sağlanmazsa `generate_cover.py` otomatik üretir — artık `art.jpg`
elle sağlanmışsa (karakter roster'ından değil) o görselin üstüne başlık metni
ekleyerek üretir (önceden ilgisiz bir procedural gradyan kullanıyordu, bu düzeltildi).

`theme: "dj"` — ana kataloğun 6 tarzından ayrı, sadece hashtag/etiket üretimi için
yeni bir `config.THEMES` girdisi (`config.py`).

**Paylaşım metinleri (caption/hashtag/YouTube yorumu) otomatik İngilizce** —
`theme: "dj"` bunu kendiliğinden tetikliyor (`config.THEMES["dj"]["language"] =
"en"`, bkz. `social_text.resolve_language()`), `meta.json`'a elle `"language"`
eklemene gerek yok. İstersen `meta.json`'a `"language": "tr"` ekleyip belirli bir
set için bunu geçersiz kılabilirsin.

## Setin müzik stili — `set_style`

Her set `theme: "dj"` kullanıyor; bu MARKA kimliği (DJ Set / Mix / Live Set
etiketleri, İngilizce metinler) ve değişmiyor. Ama tema tek başına kaldığında
deep house bir set ile techno bir set YouTube/TikTok gözünde **birebir aynı
sinyali** veriyordu: aynı hashtag, aynı etiket, aynı stok görüntü. İkinci set
birinci setin kitlesini genişletmiyor, aynı kitleye ikinci kez düşüyordu.

`meta.json`'a `"set_style"` eklenince o stilin kendi hashtag'leri, kendi
YouTube etiketleri ve kendi stok video sorguları devreye giriyor
(`config.SET_STILLERI`). Alan YOKSA hiçbir şey değişmez — eski setler aynen
çalışır.

Tanımlı stiller:

| `set_style` | Hedef arama tarafı | Vokal |
|---|---|---|
| `deep_house` | lounge / relax / chillout | vokal chop'lar |
| `techno_chill` | focus / work / night drive | yok (enstrümantal) |

Yeni bir stil eklemek = `config.SET_STILLERI`'ye bir girdi (label, etiketler,
video_sorgulari, suno_stil). Her setin klasöründe, o stile göre yazılmış bir
`SUNO.md` üretim tarifi bulunur (örnek: `dj_sets/Night Drive/SUNO.md`).

## Arka plan videosu — `backdrop.mp4`

Uzun setlerde arka planda tek bir sabit görselin (bulanık `art.jpg`) durması
sıkıcı; 80 dakika boyunca hiç değişmeyen bir kare izleyiciyi kaçırıyor.
`stock_video.py` setin süresine göre Pexels'ten stok klip indirip çapraz
geçişlerle tek bir `backdrop.mp4` kuruyor, render bunu `-stream_loop -1` ile
döngüye alıyor.

```bash
python stock_video.py --set "dj_sets/<set-adı>" --dry-run   # ne inecek, indirmeden
python stock_video.py --set "dj_sets/<set-adı>" --build     # indir + birleştir
python stock_video.py --set "dj_sets/<set-adı>" --build --force  # mevcut olanı yenile
```

`dj_famous_process.py` render'dan önce bunu kendisi de çağırıyor
(`config.DJ_ARKA_PLAN_VIDEO`); başarısız olursa sessizce eski bulanık `art.jpg`
arka planına düşüyor, set yine de yayınlanıyor.

**Yalnızca uzun formatta (16x9).** Shorts/Reels/TikTok 45 saniye — orada tek
görsel zaten sorun değil, üstelik dikey çerçevede yatay stok klip kırpılınca
kayba uğruyor.

Klipler `.stock_video_cache/` altında (git dışı) toplanıyor ve setler arasında
paylaşılıyor — ikinci set aynı sorgudan gelen klipleri tekrar indirmiyor.

## Yayınlanan platformlar ve onay kaydı

| Platform | Dosya | Bayrak |
|---|---|---|
| YouTube (uzun) | `output/youtube_16x9.mp4` | — (her zaman) |
| YouTube Shorts / TikTok / Instagram | `output/shorts_9x16.mp4` | — (her zaman) |
| Facebook Reels | `output/shorts_9x16.mp4` | `config.EK_PLATFORMLAR_DJ` |
| Telegram | `output/shorts_9x16.mp4` | `config.EK_PLATFORMLAR_DJ` |
| Bluesky | `output/shorts_9x16.mp4` | `config.EK_PLATFORMLAR_DJ` |

**Onay kaydı:** Facebook / Telegram / Bluesky için ayrı teyit **2026-09-10**'da
alındı ("Bağla"). Yukarıdaki "yeni bir kullanım/platform eklenecekse tekrar
teyit edilmeli" kuralı gereği kaydediliyor. Bundan SONRAKİ her yeni platform
için teyit yine ayrıca alınacak.

**Bayraklar ana katalogdan AYRI** (`EK_PLATFORMLAR_DJ` ≠ `EK_PLATFORMLAR`).
Tek bir sözlük olsaydı, katalog için bir platformu açmak DJ Famous'u da sessizce
oraya taşırdı — onay bir daha sorulmadan. Gerçek bir kişiyi konu alan içerikte
bu kabul edilemez, o yüzden iki sözlük.

**Üçü de dikey 45 saniyelik kesiti gönderiyor**, uzun seti değil. Zorunluluk:
Facebook Reels 90 saniye, Bluesky 3 dakika sınırlı; Telegram bot API'si 50 MB
sınırlı ve bir setin `youtube_16x9.mp4`'ü ~137 MB. Telegram bu yüzden
`kind="dikey"` ile çağrılıyor — varsayılanı ("uzun") kullansaydı her seferinde
boyut kontrolünde patlardı.

**Üçü de hatasız-geçer.** Biri düşerse set yine yayınlanır; bunlar boru hattının
asıl işi (YouTube/TikTok/Instagram) değil, ekidir.

**Zaten yayınlanmış setler geriye dönük gitmez.** `find_pending_sets()` dört ana
platformu da tamamlamış bir seti bir daha işlemiyor, dolayısıyla bu üçü yalnızca
YENİ setlerde çalışır. Eski bir seti elle göndermek için:

```bash
cd upload
python facebook_upload.py --project "../dj_sets/<set>" --kind reels
python telegram_upload.py --project "../dj_sets/<set>" --kind dikey
python bluesky_upload.py  --project "../dj_sets/<set>"
```

(Telegram ve Bluesky `--dry-run` destekliyor — göndermeden önce ne gideceğini
görmek için.)

## Telif (Content ID) — kural

**Olan:** City Pulse Set (4 Eylül 2026) yayınlandıktan sonra Content ID eşleşmesi
aldı. Eşleşen eser: **"Bring Me To Life" — Tiësto, FORS**. 4 ayrı yerde toplam
106 saniye; sonuç para kazanma kapalı + 2 ülkede engelli. Bölümler elle
çıkarılınca talep düştü.

**Suno seni KORUMUYOR.** Şartları açık: üçüncü tarafın haklarını ihlal
etmeyeceğine dair garanti vermiyor, üstelik tazminat yükümlülüğü tek yönlü —
Suno'yu sen tazmin ediyorsun. Yardım merkezinde Content ID'yle ilgili tek madde
yok. Verdiği şey ticari kullanım *izni*, telif *garantisi* değil.

### Yayın öncesi karantina — zorunlu

`config.DJ_ON_TARAMA` bunu otomatik yapıyor: set önce YouTube'a `private`
yükleniyor, `config.DJ_TARAMA_BEKLEME_SN` (2 saat) tarama bekleniyor, temizse
açılıyor ve ancak o zaman diğer platformlara gidiyor. Content ID taraması
gizlilikten bağımsız çalıştığı için bu, ücretsiz ve **aynı motoru kullanan**
tek güvenilir yöntem. Üçüncü taraf araçlar (ACRCloud, Pex) farklı veritabanı
kullanıyor; "temiz" demeleri YouTube'da talep gelmeyeceği anlamına GELMEZ.

**İkinci aşamayı `dj_tarama_kontrol.py` yürütüyor ve HAFTALIK koşuya değil,
`auto_process.py`'nin SAATLİK koşusuna bağlı.** Sebep: `dj_famous_process.py`
haftada bir çalışıyor, ikinci aşama ona bağlansa bir sonraki haftaya kalırdı.
Akış: set `dj_tarama_bekliyor` durumunda bekler → süre dolunca modül videoyu
kontrol eder → temizse `public` yapıp `dj_tarama_temiz` işaretini koyar ve
kalan platformlar (Shorts, TikTok, Instagram, Facebook, Telegram, Bluesky)
devam eder → engel varsa private kalır, log + telefon bildirimi gider.
Aynı kapı **`derlemeler/` için de çalışıyor**: derleme de YouTube için baştan
taranan YENİ bir yükleme; kaynak şarkıların daha önce temiz çıkmış olması yeni
dosyayı garanti etmiyor.

**Tespitin sınırı — dürüstçe:** YouTube Data API normal kanallara Content ID
itiraz listesini AÇMIYOR (20 videoda doğrulandı; itiraz varken de her şey
`processed` görünüyor). Modül `contentDetails.regionRestriction.blocked`
alanına bakıyor, çünkü City Pulse'un bildirimi "2 idari bölgede engellendi"
diyordu — ama bu bir VARSAYIM, elde engelli bir video olmadığı için
doğrulanamadı. Bu yüzden ikinci bir ağ var: süre dolduğunda sonuç ne olursa
olsun telefona bildirim gidiyor ve Studio'dan elle bakılması isteniyor.

### İtiraz gelirse — refleks kurala bağlı

**Varsayılan: KES.** Studio → bölümü kes / sesi sustur. Talep otomatik düşer,
ihtar riski sıfır. City Pulse'ta yapılan buydu ve doğruydu.

**Dispute'a yalnızca şu üçü BİRLİKTE varsa git:**
1. Talep videonun %20'sinden fazlasını kapsıyor **veya** video tamamen bloklu
2. Aynı referans kayıt **2+ kez** geldi (sistematik yanlış eşleşme göstergesi)
3. O parçanın üretim kaydı elinde (aşağıya bak)

Gerekçe **"yanlış tanımlama (misidentified)"** olacak. **"AI ile üretildi"
YouTube'un geçerli sebep listesinde YOK** — tek başına söylemek hak sahibine
"modele telifli eser verilmiş" okuması için alan açar.

**Appeal (escalate) aşamasına ASLA otomatik geçme.** Reddedilen appeal, hak
sahibinin kaldırma talebine ve oradan **kanal ihtarına** dönüşebilir. Orada dur.

### Üretim kaydı — tek dispute sigortası

Her set için `_segments/uretim_kaydi.json` tutulmalı: parça başına Suno üretim
ID'si, tam prompt metni, üretim tarihi, **indirme tarihi** ve o andaki abonelik
durumu.

İndirme tarihi kritik: Suno'ya göre ticari hak *"downloaded while subscribed"*
koşuluna bağlı — üretim anına değil, İNDİRME anına. Aboneliğin bir gün
kesilirse o gün indirilenlerin ticari hakkı yok.

### Üretim tarafında azaltma

- **Setin ilk dakikalarını ayrı üret.** City Pulse'ta eşleşmelerin %65'i ilk 6
  dakikadaydı. Bir setin girişi en jenerik yeridir: sabit 4/4, düz kick, yaygın
  doku. Parmak izi çakışması için en verimli zemin. Intro'yu tek uzun üretimden
  almak yerine ayrı kısa üretimlerden kurgula.
- **40 dakika, 80 değil.** Content ID tespiti segment bazlı ama yaptırım VİDEO
  bazlı: 106 saniyelik eşleşme 81 dakikanın tamamının parasını kapattı. Kısa
  set = aynı risk, çok daha küçük hasar.
- **Klip kaynağı temiz bölgeden.** `dj_clips.py` artık `state.json`'daki
  `telif_araliklari`'na değen pencereleri eliyor. Meta Rights Manager
  Facebook+Instagram'da aynı mantıkla ses eşleştirmesi yapıyor, o yüzden
  telifli bölge hiçbir platforma gitmemeli.

## Kullanım

```bash
python dj_famous_process.py                 # dj_sets/ altında bekleyen HER seti işler
python dj_famous_process.py --privacy unlisted
python dj_famous_process.py --no-schedule    # YouTube golden-hour zamanlamasını kapatır
```

Haftalık çalıştırma için Görev Zamanlayıcı'da AYRI bir haftalık tetikleyici gerekir
(ana kataloğun saatlik tetikleyicisinden farklı) — `setup_task_scheduler.ps1` bunu
da kuruyor (varsayılan: her Cuma 18:00, `-DjFamousDayOfWeek`/`-DjFamousTime` ile
değiştirilebilir).

## Render süresi/boyutu notu

Ana katalog şarkıları 2-4 dakika, DJ Famous setleri çok daha uzun (referans: ~1 saat)
olabilir — render süresi ve çıktı dosya boyutu buna orantılı artar. `dj_famous_process.py`
bu yüzden ana kataloktan (2 saat) çok daha yüksek bir kilit-bayatlama süresi (8 saat)
kullanıyor, render sırasında ikinci bir çalıştırma "önceki çökmüş" sanıp üstüne
binmesin diye.
