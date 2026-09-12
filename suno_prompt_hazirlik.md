# Yeni Şarkı Kontrol Listesi (Suno → Video)

Suno API erişimi yok — bu akış Suno.com'un kendi arayüzünden yürütülüyor:
prompt hazırla → Suno.com'a yapıştır → indir → proje klasörüne koy.

> **2026-09-06'dan itibaren bu artık kullanıcının değil Claude'un iş planı**
> (kullanıcı kararı: "bu akışı kaydet artık bu iş planımız", ilk uçtan uca
> örnek: "Sokaklar Beni Tanır"). Yani Claude, tarayıcı otomasyonuyla
> Suno.com'a bizzat gidip aşağıdaki adımların TAMAMINI (üretim dahil)
> yürütür — kullanıcının kendisinin Suno'da üretim yapıp indirmesini
> BEKLEMESİ gerekmiyor. Pratik notlar:
> - Sözleri Suno'nun Lyrics kutusuna TEK dev bir blok olarak yapıştırmak
>   editörü DONDURABİLİYOR — bölüm bölüm (Intro, Verse 1, ...) küçük
>   parçalar halinde yapıştır.
> - Stiller kutusu bazen alakasız bir otomatik öneriyle geliyor — mutlaka
>   temizleyip kendi stil etiketini yaz.
> - Üretim bitince oynatma ikonu (▶) görünene kadar bekle (süre görünmesi
>   tek başına yeterli değil, birkaç saniye daha işleniyor olabilir).
> - İndirilen dosyayı `Downloads` klasöründen proje klasörüne
>   `audio.mp3`/`audio.wav` olarak taşı, sonra `auto_process.process_project(
>   project_dir, privacy, schedule=True)`'ı DOĞRUDAN çağır (`--count 1`
>   otomatik kademeleme YENİ eklenen şarkıyı değil en eski bekleyeni seçer).

> **Klasör açma sırası ÖNEMLİ:** `watch_projects.py` (Suno'dan indirilen ses dosyasını
> otomatik `audio.wav`'a çevirip pipeline'ı tetikleyen izleyici) sadece ZATEN VAR OLAN
> proje klasörlerini tarıyor — kendisi klasör açmıyor. Yani proje klasörü indirmeden
> ÖNCE hazır olmazsa, otomasyon indirilen dosyayı hiç fark etmez. Bu yüzden aşağıdaki
> adım sırası, klasör açmayı en başa (Suno'ya gitmeden önce) koyuyor — Claude bir
> prompt hazırladığında bunu otomatik yapar, elle açman gerekmez.

> **Lisans/ticari kullanım notu:** Bu kanaldaki her şarkı Suno çıktısı ve ticari amaçla
> (marka hesabı) YouTube/TikTok/Instagram'a yükleniyor. Suno'nun ücretsiz/ücretli plan
> katmanlarına göre ticari kullanım ve platform dağıtım hakları farklılık gösterebilir —
> bu, hesaba özel ve zamanla değişen bir konu olduğu için burada belgelenmiyor. Kendi Suno
> aboneliğinin güncel Kullanım Şartları'nı bir kere kontrol edip bu kullanımı kapsadığından
> emin ol (henüz yapılmadıysa).

## Adımlar

1. **Proje klasörü aç ve `meta.json` oluştur — Suno'ya gitmeden ÖNCE:**
   `projects/<şarkı-adı>/` (Türkçe karakter/boşluk sorun değil, önceki projelerde
   çalıştı — DJ Famous seti içinse `dj_sets/<isim>/`).
   ```json
   {"title": "Şarkı Adı", "theme": "hiphop"}
   ```
   `theme` seçenekleri: `pop`, `rock`, `elektronik`, `akustik`, `hiphop` (Türk trap/arabesk için en yakını — "Trap" related tag'i zaten var), `arabesk`. Claude prompt'u hazırlarken bu klasörü/dosyayı otomatik oluşturur.
2. **Stil etiketini Suno'nun Style kutusuna yapıştır** (aşağıdaki örneğe bak, şarkıya göre uyarla)
3. **Şarkı yapısını Lyrics kutusuna yapıştır** (bölüm etiketleri + kendi sözlerin)
4. **Suno'da üret.** İndirirken (resmi "Download" düğmesiyle, herhangi bir dosya
   adıyla/formatla — mp3/wav fark etmez) doğrudan 1. adımda açılan proje klasörüne
   kaydet. `watch_projects.py` klasörü zaten izlediği için dosyayı otomatik
   `audio.wav`'a çevirip pipeline'ı (`auto_process.py`/`dj_famous_process.py`)
   kendiliğinden tetikler — elle `audio.wav` adına çevirmen gerekmez.
5. **Kapak görseli indir/hazırla** (`cover.jpg` veya `.png`), proje klasörüne koy —
   opsiyonel: eksikse `generate_cover.py` render sırasında otomatik üretir.
6. **(Opsiyonel) Kart içeriği:** `art.jpg/png` ekle — kartın İÇİNDE görünecek görsel (kapaktan farklı, temaya uygun bir sahne/illüstrasyon). Yoksa düz renkle doldurulur.
7. **Render'ı elle tetiklemene gerek yok** — Görev Zamanlayıcı zaten periyodik
   çalışıyor (`auto_process.py` saatte bir, `dj_famous_process.py` haftada bir), audio
   hazır olan projeyi kendiliğinden işler. Hemen görmek istersen elle de çalıştırabilirsin:
   ```bash
   python render.py --project "projects/<şarkı-adı>"
   ```
8. `output/` klasöründeki videoları kontrol et

## Örnek Stil Etiketi (referans, şarkıya göre uyarla)

```
Turkish trap arabesk, melancholic and cinematic, husky male vocals, 808 bass, kanun strings, minor key piano, rain-soaked night atmosphere, gentle fade-out ending
```

(7 tanımlayıcı — genre+mood önde, sonra vokal/enstrüman, SONA bir kapanış tanımı — bkz. "Kapanış (Outro) kuralı". Suno v4.5+ için optimal aralık.)

> **Bu örnek ARTIK TEK BAŞINA YETMİYOR** — 2026-09-12'den itibaren her etikette bir
> AÇILIŞ tanımı da zorunlu ve `Turkish <tür>, <mood>` sıra kalıbı kırılıyor; bkz.
> aşağıdaki "Stil etiketinde AÇILIŞ tanımı" bölümü.

## Şarkı Yapısı Şablonu (Custom Mode → Lyrics kutusuna yapıştır, sözleri kendin doldur)

> **BU ŞABLON ARTIK DÖRTTEN BİRİ** (ve katalogda doymuş olanı — 18 dosyanın 15'i bunu
> kullanıyor). Hangi şarkının hangi iskeleti alacağı başlıktan deterministik olarak
> türüyor; bkz. aşağıdaki "Bölüm iskeleti kuralı" bölümü. Aşağıdaki blok, o kuralın
> 3 numaralı iskeletidir.

```
[Intro]

[Verse 1]

[Pre-Chorus]

[Chorus]

[Verse 2]

[Chorus]

[Bridge]

[Outro]
(iki tam, bitmiş cümle — bkz. "Kapanış (Outro) kuralı", "..." ile yarım bırakma)
```

## Kapanış (Outro) kuralı — SABİT, atlama

Şarkı sonlarının anlamsız/yarım kesilmiş hissettirmesi tekrarlayan bir sorundu — kaynağı muhtemelen iki şey:

1. **Style etiketinde kapanışın nasıl olacağı belirtilmiyordu** — Suno'ya "nasıl bitsin" söylenmezse rastgele/ani kesebiliyor. Artık HER stil etiketinin SONUNA bir kapanış tanımı ekleniyor:
   - Yumuşak/duygusal şarkılar (pop, akustik, arabesk): `gentle fade-out ending`
   - Enerjik/sert şarkılar (rock, hiphop, elektronik): `strong final hit ending, no abrupt cutoff`
2. **Outro sözleri "..." ile yarım bırakılmış cümlelerdi** (ör. "Kalbim hâlâ..."), gerçek bir kapanış cümlesi değil — hem müzikal olarak "bitmemiş" hissi veriyor hem de (Yürek Yarası'ndaki köşeli-parantez-dışı-metin hatasına benzer şekilde) Suno'nun düz metni garip yorumlama riski taşıyor. Artık Outro **iki TAM, bitmiş cümle** oluyor — üç nokta (`...`) YOK, yarım bırakılan düşünce YOK, nakaratı tekrar eden ama net bir noktada biten bir kapanış.

Bu kural `karakter_roster.md`'deki arabesk-düet kuralı gibi kalıcı — yeni her şarkı prompt'unda uygulanmalı.

## Temiz Sözler (YouTube açıklaması) kuralı — SABİT, atlama

Suno'ya yapıştırılan sözler `[Verse 1]`, `[Chorus]` gibi köşeli parantez etiketleri
içerir — bunlar Suno'ya yönelik yapı talimatları, izleyiciye değil. Bu etiketlerle
birlikte YouTube açıklamasına kopyalanırsa amatör görünüyor (kullanıcı geri bildirimi).

Artık her `*_sozler.md` dosyasında, Suno'ya yapıştırılan (etiketli) versiyonun HEMEN
ALTINDA ayrı bir **"Temiz Sözler (YouTube açıklaması için kopyala-yapıştır)"** bölümü
oluyor — aynı sözler, köşeli parantez etiketleri TAMAMEN çıkarılmış, sadece bölümler
arası boş satırla ayrılmış hâlde. Bu, doğrudan YouTube açıklamasına yapıştırılabilir.

Bu kural da kalıcı — yeni her şarkı prompt'unda uygulanmalı.

## Intro kuralı — SABİT, atlama

Şarkı başlarının "yapay/şablon" hissettirmesi tekrarlayan bir sorundu. Kök neden:
Intro'nun ilk satırı genelde şarkının konusunu/başlığını doğrudan özetleyen bir "tez
cümlesi" oluyordu — ör. "Kırdım zincirleri, artık özgürüm" (Kırık Zincir), "Bir mektup
yazdım sana, göndermedim" gibi temayı hemen adlandıran açılışlar. Gerçek/insan yazımı
şarkı sözleri genelde böyle başlamaz — somut bir AN, DETAY veya duyu imgesiyle açılır,
temayı dolaylı olarak hissettirir, doğrudan söylemez.

**Kural:** Intro'nun ilk satırı şarkının temasını/başlığını DOĞRUDAN adlandırmamalı.
Bunun yerine küçük, somut, sahneleyici bir detayla açılmalı (saat, mekan, ses, fiziksel
bir hareket, bir nesne) — dinleyici temayı satır satır keşfetmeli, ilk cümlede
özetlenmiş bulmamalı.

- **Zayıf (kaçınılacak):** "Kırdım zincirleri, artık özgürüm" — doğrudan tema özeti.
- **Güçlü (hedeflenen):** "Saat üçte uyandım, terden ıslanmış çarşaf" — somut an,
  temayı (mücadele/özgürleşme) dolaylı hissettiriyor, sonraki satırlarda açılıyor.

Bu kural da kalıcı — yeni her şarkı prompt'unda uygulanmalı. (Bugüne kadar üretilmiş
7 şarkı geriye dönük DEĞİŞTİRİLMEDİ — audio zaten üretildi, sadece bundan sonrakiler
için geçerli.)

## Bölüm iskeleti kuralı — DÖNÜŞÜMLÜ, tek şablon YOK

Kullanıcı geri bildirimi (2026-09-12): *"Suno parçaları hep aynı başlangıç oluyor."*
Ölçüm suçluyu buldu ve suçlu **stil etiketi değil** — 16 etiket arasındaki ortalama
Jaccard benzerliği 0,143, yani etiketler birbirinden gerçekten farklı. Suçlu bu
dosyadaki **tek sabit bölüm şablonu**.

**Katalogdaki bugünkü doygunluk** (bir sonraki okur neyin tükendiğini görsün diye):

| İskelet | Şarkı |
|---|---|
| `[Intro] > [Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Chorus] > [Bridge] > [Outro]` | 10 |
| Aynı iskelet, düet taraf etiketleriyle (`[Intro - Male 1]`, `[Intro - Baba]`, `[Intro - Female]`) | 4 |
| Sapma (`gece_surusu` hook/chant, `kumdan_denize`, `kirik_zincir` çift Pre-Chorus) | 3 |
| Etiketsiz ASR dökümü (`beni_birakma`, `kullerimden_gec`) | 2 |

- **Etiketli 18 dosyanın 15'i (%83) birebir aynı sırada.**
- **Fiilen üretilmiş 17 şarkının 17'si `[Intro...]` ile başlıyor.**
- Suno `[Intro]` etiketini **enstrümantal açılış işareti** sayıyor: altına söz koysak
  bile önce kendi tür-varsayılanı girişini üretip sonra o iki satırı söylüyor. Aynı
  girdi → aynı çıktı. Bu bir Suno kusuru değil, bu şablonun kusuru.

**Kural:** artık tek şablon yok, DÖRT iskelet var; ve şarkı hangisini kullanacağını
kendi SEÇMİYOR, başlıktan deterministik olarak türetiyor.

| # | İskelet | Açılış tipi |
|---|---|---|
| 0 | `[Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Chorus] > [Bridge] > [Chorus] > [Outro]` | Intro YOK, doğrudan söz |
| 1 | `[Chorus] > [Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Bridge] > [Chorus] > [Outro]` | nakaratla soğuk açılış |
| 2 | `[Instrumental Intro (enstrüman + bar sayısı)] > [Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Chorus] > [Bridge] > [Outro]` | açılışı SEN tarif ediyorsun |
| 3 | `[Intro] > [Verse 1] > [Pre-Chorus] > [Chorus] > [Verse 2] > [Chorus] > [Bridge] > [Outro]` | mevcut (doymuş) şablon |

**Seçim — DETERMİNİSTİK, rastgele DEĞİL:**

```
index = int(hashlib.sha256(başlık.encode("utf-8")).hexdigest()[:8], 16) % 4
```

Aynı desen depoda zaten var (`stock_art._secim_indeksi`, `social_text`'in caption
seçimi): aynı şarkı yeniden ele alındığında aynı iskeleti alır, yani sözler dosyası ile
üretilmiş ses birbirini tutar. **Rastgele seçim YASAK** — bir sonraki oturum aynı şarkı
için başka bir iskelet üretir ve arşiv sessizce tutarsızlaşır.

Hesaplanmış örnekler: `Kırık Zincir` → 0 · `Sabah Senin` → 1 · `Yeraltı` → 1 ·
`Son Kez` → 2 · `Yürek Yarası` → 3 · `Gece Sürüşü` → 3.

**Düet (arabesk) şarkılar MUAF DEĞİL:** seçilen iskelet taraf etiketleriyle yazılır
(`[Chorus - Kadın]`, `[Verse 1 - Baba]`). Düet kuralı bölüm SIRASINI değil bölüm
ETİKETİNİ belirliyor; ikisi çakışmıyor.

**Intro kuralıyla çakışma — çözümü yazılı olsun:** yukarıdaki "Intro kuralı" (ilk satır
temayı doğrudan adlandırmaz) şarkının ilk **anlatı** bölümü için geçerlidir. 1 numaralı
iskelette açılış nakarattır ve nakaratın işi zaten çapayı vermektir — orada Intro kuralı
açılıştan sonraki **ilk kıtaya** kayar. 0 ve 2 numaralı iskeletlerde kural olduğu gibi
`[Verse 1]`e uygulanır. 3 numarada hiçbir şey değişmez.

## Stil etiketinde AÇILIŞ tanımı — SABİT, atlama

"Kapanış (Outro) kuralı" işe yaradı: bugün 16 stil etiketinin **10'unda** bir kapanış
tanımı var. Ama **açılış tanımı yalnızca 1'inde** var (`kumdan_denize` — ve o etiket
kataloğun en özgün duyan açılışına sahip). Asimetri ortada: Suno'ya nasıl BİTECEĞİNİ
söylüyoruz, nasıl BAŞLAYACAĞINI söylemiyoruz; o da tür varsayılanını koyuyor.

**Kural 1 — her stil etiketinde bir AÇILIŞ tanımı olacak**, kapanış tanımının simetriği:
- `opens cold on the vocal, band enters at the chorus`
- `opens with a lone baglama figure over room tone`
- `opens with a single distorted guitar hit, no build-up`
- `opens with solo piano, drums enter only in verse 2`

**Kural 2 — tek cümlelik TIRMANIŞ MAKROSU yasak.** `clean electric guitar arpeggio
building into a wall of distorted guitars` tek cümlede hem açılışı hem gelişimi veriyor;
Suno bunu hazır bir "tırmanış makrosu" gibi çalıştırıyor. Açılış ve doruk AYRI söylenir:
`opens with ... , wall of distorted guitars only in the final chorus`.

**Kural 3 — sıra kalıbı kırılacak.** 16 etiketin **15'i** `Turkish <tür>, <iki sıfatlı
ruh hâli>, ...` ile başlıyor. Her seferinde aynı sırayla aynı tür bilgi verilirse Suno
aynı şablonu okuduğunu anlıyor. Etiketlerin bir kısmı açılış tanımıyla, bir kısmı
enstrümanla, bir kısmı aranjman hareketiyle başlasın. Dil bilgisi (`Turkish ... vocals`)
etikette KALIR — sadece en başta olmak zorunda değil.

## İki kovalı sözlük kuralı — SABİT, atlama

Kullanıcı geri bildirimi (2026-09-12): *"şarkılarda normalde kullanılmayan detay
kelimeler var, itici duruyor."* Ölçüm kullanıcıyı doğruladı: teknik/endüstriyel/
bürokratik sözlük (makine, termos, servis, fabrika, düdük, sayaç, bip, battaniye, kart)
**yayındaki 19 şarkının 0'ında** geçiyor. Sıfır. Reddedilen `vardiya` metninde 20 tane,
ilk `sabah_senin` metninde 12 tane vardı.

**Somutluk ≠ yadırgatıcılık.** İkisini ayıran ÜÇ ölçülebilir özellik var:

| # | Ölçüt | Nasıl ölçülür |
|---|---|---|
| 1 | **Marka sıklığı (`df`)** | Kelime, yayındaki 19 şarkının kaçında geçiyor? (gövde eşleşmesiyle) |
| 2 | **Duygu yükü** | Kelime KENDİ BAŞINA bir duygu taşıyor mu? *yağmur, ayna, mektup, yol, kül* taşır; *sayaç, termos, servis* taşımaz — onlar duyguyu ancak cümleden ödünç alır |
| 3 | **Register** | Kelime günlük konuşmada mı yaşıyor, yoksa iş/belge/teknik dilinde mi? |

**Kova A — söylenebilir nesneler:** üç testi de geçenler. Kanalda yaşıyor (`df ≥ 2`),
kendi duygusu var, günlük dil. (cam, perde, anahtar, kapı, ışık, yol, sokak, gece,
sabah, şehir, el, göz, nefes, deniz, kül, mektup, yağmur, duvar, pencere, köşe, saat...)

**Kova B — sahne mobilyası:** üç testten **en az İKİSİNİ** düşürenler. (makine, termos,
servis, fabrika, düdük, sayaç, bip, battaniye, kart, vardiya, mesai, fatura, prim,
bordro, peron, şalter...) `battaniye` tam da bu yüzden Kova B: register'ı sıcak ev
eşyası (3. testi geçer) ama `df = 0` ve kendi başına duygu taşımaz — iki testi düşürüyor.

**Sayılabilir kısıtlar:**

1. **Kova B'den şarkı başına EN FAZLA 2 kelime.**
2. **Nakaratta Kova B = 0.** İstisna yok.
3. **Nakaratta geçen her İSMİN `df ≥ 2` olması ŞART.** İlk `sabah_senin` nakaratı tam
   buradan düşüyordu: "süt kokun" ve "yastığında", ikisi de `df = 0` ve ikisi de
   nakaratın merkezinde.
4. **"Somut isim / kıta ≥ 2" kotası YALNIZ Kova A'dan sayılır.** Eski hâliyle kota Kova
   B ile de doluyordu; doldukça metin belgeselleşiyordu.
5. **"Sadece bu bankanın kelimeleriyle yaz" kaydı KALDIRILDI** (`soz_yazma_yontemi.md`
   adım 2). Duyu envanteri bir ZEMİN, kapalı bir küme değil. Kök neden buydu: sahne
   fabrika olunca envanter fabrika envanteri oldu ve kural o envanterin dışına çıkmayı
   yasakladı — **kelimeler seçilmedi, dayatıldı.**
6. **Emek / meslek / mekân hissi kelimeyle değil DURUMLA kurulur:** yorgunluk, saat,
   karanlık, dönüş, ışık, eve varış. Mesleği adlandıran kelime bir kısayoldur ve
   bedeli register'dır.

| Sınıf | Karar | Örnek |
|---|---|---|
| İş / üretim / bürokrasi | Nakaratta YASAK, metinde ≤2 | makine yağı, sayaç, vardiya, mesai, fatura, bordro |
| Ulaşım / servis aracı | ≤1 | servis, peron, taksi |
| Ses taklidi | YASAK | bip, tık, çat |
| Ev eşyası, `df ≥ 2` | Serbest | perde, anahtar, kapı, cam |
| Ev eşyası, `df = 0` | Nakarat DIŞINDA, Kova B bütçesinden düşer | battaniye, termos, yastık |
| Klasik lirik nesneler | Serbest / teşvik | yol, gece, ayna, mektup, sokak, yağmur, cam, ışık, deniz, kül |

## Açık muhatap testi — SABİT, atlama

Kullanıcı geri bildirimi (2026-09-12): *"diyalog kısıtlı, dinleyici kitlesine."*
Ölçüm şaşırtıcı çıktı: ilk `sabah_senin` metni muhatapsız DEĞİLDİ — 19 "sen" ile
**kataloğun en yükseği** (medyan 4, yani 4,75 katı). Yani mevcut sayısal kural (≥4
"sen") fazlasıyla geçilmişti ve şikâyet yine de geldi. Kural **sayıyı** ölçüyor,
**açıklığı** ölçmüyor.

Kataloğun **%53'ü** "herkesin doldurabileceği bir sen" kullanıyor (sevgili / ayrılınan
kişi). İlk `sabah_senin`'in "sen"ini ancak **küçük çocuğu olan bir ebeveyn**
doldurabiliyordu — dinleyici şarkının içine değil izleyici koltuğuna oturuyordu.

> **İlke: spesifik DETAY dinleyiciyi dışarıda bırakmaz, spesifik MUHATAP bırakır.**
> Detay ne kadar özel olursa olsun evrensel kalabilir; muhatap özelleşince kitle daralır.

**Kural — iki şart BİRDEN:**

1. **Sayı:** metinde en az 4 "sen" / 2. tekil ek. *(Eski kural, KALIYOR.)*
2. **Açıklık:** *"Bu 'sen', dinleyicinin hayatındaki en az ÜÇ FARKLI insanla
   doldurulabiliyor mu?"* Doldurulamıyorsa **muhatap değişir** — satırlar değil, muhatap.

| Muhatap | Üç kişi testi |
|---|---|
| Sevgili / ayrılınan kişi / uzaklaşan arkadaş | ✅ herkes doldurur |
| Evde bekleyen / eve dönülen kişi (ilişki adı KONMAMIŞ) | ✅ |
| Geçmişteki kendisi | ✅ |
| Şehir / gece | ✅ |
| Baba, anne, çocuk, eş — **adı konmuş rol** | ⚠️ sadece o roldekiler doldurur: şarkı başına en fazla 1, ve art arda iki şarkıda olmaz |

**Nakarat kapısı (yazımdan sonra, Suno'dan önce):** nakaratın 4 satırını al ve sor —
*"bu 4 satırı sevgilisine söyleyen biri kulağa saçma gelir mi?"* Evet ise nakarat
yeniden yazılır. Kapalı bir muhatap zorunluysa ilişkinin özelliği KITADA kalır ve
nakarat genel bir "sen"e döner.

## Raporlar çelişince hangisi geçerli — 2026-09-12 kaydı

Aynı gün üretilen iki rapor **makine yağı** hakkında birbirinin tersini söyledi ve
kullanıcı taraf tuttu. Bu kayıt, bir sonraki okur o iki cümleyi yan yana bulduğunda
hangisinin hangi koşulda geçerli olduğunu bilsin diye duruyor:

| Nerede | Ne denmişti | Bugünkü karar |
|---|---|---|
| `soz_yazma_yontemi.md` N5 | ✅ *"Avucumda makine yağı, tırnağımda is"* — iyi kıta satırı örneği | **Yarısı doğru.** Satırın YAPISI (somut nesneyle açmak, devrik, yüklemsiz) doğru ve kural olarak KALIYOR. Satırın KELİMELERİ yanlış: `makine`, `is` → Kova B, `df = 0`. Aynı yapı Kova A ile kurulur |
| `sozler_teshis.md` §1.7 | *"Vardiya somut imge bakımından kataloğun en zenginlerinden biri"* | **Doğru ama övgü değil.** Somutluk TEK BAŞINA erdem değil; erdem olan **kanalda yaşayan** somutluk |
| `sozler_teshis.md` Kusur 5 | *"makine yağı / termos / sayaç düşük register'lı sözcükler"* | **Geçerli olan bu.** Kullanıcının itirazı bu tarafı doğruladı, N5 tarafını çürüttü |
| `sozler_teshis.md` P2 | *"metinde en az 4 'sen' olmalı"* | **Yetersiz.** Sayı kalıyor, yanına yukarıdaki açıklık testi ekleniyor |

**Tek cümlelik kural:** somutluk ile yadırgatıcılığı ayıran şey imgenin GÜCÜ değil,
kelimenin KANALDA YAŞAYIP YAŞAMADIĞIDIR. Aynı sahne, aynı somutluk düzeyi, farklı
register: `Termosta kalan son yudum da senin` (`df = 0`, yüksüz nesne) →
`Avucumun sıcağı hâlâ sende` (aynı somutluk, kelimeler katalogda yaşıyor).

## Notlar

- Vokal dili: Türkçe belirtmeyi unutma (örn. "Turkish male vocals")
- Tema tutarlılığı: gece, neon ışıklar, yalnız yürüyüş, şehir — marka evreninin (Famous Music Studio) genel ruh hali
- Her yeni şarkı için bu dosyayı referans al, stil etiketini şarkının kendi temasına göre uyarla
- `theme` seçenekleri (meta.json): `pop`, `rock`, `elektronik`, `akustik`, `hiphop`, `arabesk` (`config.THEMES`'teki 6 slot)
