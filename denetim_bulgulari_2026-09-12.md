# Denetim bulguları — 2026-09-12

2026-09-12'de bu depoda 14 salt-okunur denetim yapıldı; raporlar geçici bir oturum
klasöründeydi ve artık erişilemez. Bu belge onların **hâlâ açık olan** bulguları — arşiv
değil, eylem listesi. Aynı gün kapatılan 13 arıza bilerek dışarıda (son bölüm). Her madde
yazılırken **kodda yeniden doğrulandı** (2026-09-12 ~12:00); parantezdeki rapor adı
yalnızca iz sürmek için, maddenin kendisi tek başına anlaşılır.

---

## 1. KARAR BEKLEYENLER

### K-1. YouTube Shorts yüklemesi kapatılsın mı?

**Ölçüm (28 gün, 20 Shorts):** 1.363 izlenme (kanalın %31,8'i) ama 70 dk izlenme süresi
(%1,94) — izlenme başına ~2,1 sn. Ve **0 abone, 0 paylaşım, 0 yorum.** Shorts'un tek
savunulabilir gerekçesi keşif; keşfin üç göstergesi de sıfır (uzun formla r = 0,135).
Maliyet: yayın başına 1.701 kota birimi (%17) ve YouTube'a giden video sayısının iki
katına çıkması — kanalın en büyük riskinin ("toplu üretilmiş AI içerik") tam merkezi.

- **A — açık kalsın:** örneklem küçük ve genç, Shorts dağıtımı gecikmelidir; en iyi Short
  %72,6 izlenme yüzdesi tutturmuş — içerik izlendiğinde tutuyor, sorun hiç gösterilmemesi.
- **B — tamamen kapat:** video sayısı yarıya, 1.701 birim serbest; izlenmenin üçte biri gider.
- **C — kısmi (rapor önerisi):** otomatik şarkı Shorts'unu kapat, `dj_clips` hattı
  (haftada ≤1 kürate kesit) açık kalsın. Keşif bileti elde kalır, hacim 1/7'ye iner.

⚠ Kapatma **tek satırlık config işi değil**: önce `auto_process._is_fully_done()` ve
`dj_famous_process.find_pending_sets()`'teki anahtar demeti koşullu yapılmalı, **sonra**
bayrak. Ters sırada `youtube_shorts_video_id` asla dolmaz, katalog kalıcı `pending`
görünür ve günlük yayın freni sessizce devre dışı kalır (bu arıza burada üç kez yaşandı).
**`config.PLATFORMS`'a ASLA dokunma** — dikey render dosyasına beş platform + iki süpürge
bağlı. Böyle bir bayrak şu an yok (doğrulandı). Mevcut 21 Shorts'a dokunulmamalı (B-13).
*(shorts_maliyet.md, performans_raporu.md)*

### K-2. `dj_sets/_arda/README.md`'nin kişisel olmayan kısmı taşınsın mı?

Klasörün tamamı bugün `.gitignore`'a alındı — doğru karar (gerçek bir kişinin 14 yüz
fotoğrafı; onay "AI servisine yükleyip sahne üretmek" içindi, public depoda yayımlamak
için değil). **Ama README de depodan çıktı** ve içinde kişisel olmayan değerli bilgi vardı:
onay kaydı + tarihi, "ilk sahne yayınlanmadan gösterilmeli" kuralı, higgsfield kredi
maliyetleri (~14 kredi/set), karakter eğitim planı.
**a)** Olduğu gibi bırak → bilgi diskte kalır, makine kaybında gider. **b)** `!` ile geri al
→ kişinin adı ve fotoğraf tarifi public depoya girer, **önerilmez**. **c)** Kişisel olmayan
kısmı `dj_sets/README.md`'ye taşı, klasör bütünüyle ignore kalsın — **rapor önerisi.**

### K-3. `derlemeler/_iptal/En Çok Dinlenenler/` silinsin mi? (661 MB, bugün ölçüldü)

39 dk 51 sn'lik, tam render edilmiş ama **hiçbir platforma gitmemiş** bir derleme
(`state.json`/`meta.json`/kapak yok → yayın adımına hiç girilmemiş). Çıkarım: `--en-iyi`
modunun ilk denemesiydi, beğenilmeyip yerine küratörlü `Gece Seansı Vol. 1` üretildi; ikisi
aynı havuzdan kurulduğu için ikisini birden yayınlamak "her biri farklı konseptle" kuralını
ihlal eder. **Sil** → 661 MB açılır, geri alınamaz. **Sakla** → disk dışında zararı yok;
`_` öneki hattan dışlamayı zaten sağlıyor ve bu gerçek klasör adıyla test ediliyor,
**kazara yayınlanma riski yok.**

### K-4. Telegram / Bluesky günlük tavanı yükseltilsin mi?

`ek_platform_backfill.GUNLUK_TAVAN = 1` (platform başına/gün), `KOSU_TAVANI = 1`;
`facebook_backfill.GUNLUK_TAVAN = 2`. Kuyruğu hızlandırmanın **tek yolu** bu sabit.
**1'de kalsın** → 18 şarkılık geri doldurma haftalar sürer, ama günlük yükleme deseni düşük
kalır ("inauthentic content" tarifinde bakılan şey haftalık toplam değil, günlük desen).
**2-3'e çıkar** → kuyruk hızlanır, günde 4-6 ek gönderi, risk aynı yönde. Not: bir derleme
yayınlandığı gün bu tek slotu işgal ediyor, o gün bekleyen şarkı bir gün geriye kayıyor.

### K-5. DJ kesit yayın hattı (`dj_clips`) devreye alınsın mı?

Kod olgun, iyi test edilmiş, eksik politika kapısı bugün eklendi. Tıkayan tek şey bir veri
alanı: `dj_sets/Just Relax/state.json`'da `dj_tarama_temiz` yok (doğrulandı — o set
karantina kapısı kurulmadan önce yayınlandı). **Ama önce onay sorusu var:** README'nin kendi
kuralı *"yeni bir kullanım/platform eklenecekse tekrar teyit edilmeli"*. Kesit setin
tanıtımı değil, **kendi başlığı ve açıklamasıyla duran ayrı bir gönderi** (bir test bunu
zorunlu kılıyor); kartında yine kişinin AI ile işlenmiş fotoğrafı var, set başına onun
görüntüsünü taşıyan gönderi 2'den 3'e çıkıyor. Emsal net: Facebook/Telegram/Bluesky
eklenirken *aynı dosya, aynı görsel, aynı caption* gidiyordu ve yine de ayrı teyit alınıp
yazılı kaydedildi.

Sorulacak özet: *"Setinden alınan 45 sn'lik bir bölümün, setin kendisinden bağımsız ayrı
bir gönderi olarak yayınlanmasını onaylıyor musun? Sınırlar: set başına 1, küresel olarak
haftada 1, yalnızca YouTube Shorts. Onay yalnızca YouTube için mi? Kesidin hangi bölümden
alındığını önceden görmek ister misin?"*

**Hiç alma** → haftada +1 yayın, "15→10 yayın/hafta" hedefinin tersi, elde edilen 45 sn'lik
türev içerik; kesit küratörlük EKLEMİYOR, yalnızca hacim ekliyor — derlemenin tam tersi.
**Sınırlı al** → onay sonrası, yalnızca YouTube, tavanlar gevşetilmeden, ilk yayın elle
izlenerek. ⚠ **Onay gelmeden `dj_tarama_temiz: true` YAZILMAMALI** — o işaret konduğu an
bir sonraki haftalık koşu kesidi otomatik yükler. Cevap sonrası README'ye tarihli onay
satırı eklenmeli. *(icerik_kaldıraci.md §4)*

### K-6. `Küllerimden Geç` için yeni ses üretilsin mi? — öneri: ERTELE

Sözler/kapak/meta kullanılabilir, eksik olan özgün ses. Ama mevcut videonun sesi
değiştirilemez — yeni bir yükleme gerekir, unlisted eski kayıt artık olarak kalır ve Suno
kotasından harcanır. Kota projenin gerçek tavanı olduğuna göre aynı kotayı **hiç
yayınlanmamış yeni bir şarkıya** harcamak daha verimli.

### K-7. `reply.txt` silinsin mi? (439 bayt)

Projeyle ilgisi olmayan bir oturum testi transkripti; hiçbir modül okumuyor, git'te
izlenmiyor (doğrulandı). **Öneri: sil.**

---

## 2. ELLE YAPILACAKLAR

Etki sırasına göre. "Canlı doğrulama" denen yerde diskten karar verilemiyor.

> **GÜNCELLEME — 2026-09-12 akşam (E-1…E-17 tek tek DİSKTEN yeniden doğrulandı).**
> Kapanan: **E-1** (kalan notu ölçüldü) ve **E-8** (işaret zaten yazılmış — kuru
> koşuyla doğrulandı). Ölçüsü DEĞİŞEN üç madde: **E-7** (üç telif satırının **ikisi**
> kapandı), **E-16** (3 proje → **2**), **E-10** (belgedeki yedekleme komutu
> PowerShell'de ÇALIŞMIYORDU — ölçüldü ve düzeltildi, maddenin altında).
> Kalan 14 maddenin hepsi AÇIK ve gerekçeleri **tek bir sınıftan**: platforma yazan
> bir fiil, bir tarayıcı/telefon oturumu, ya da bir kullanıcı kararı. §2'de diskten
> kapatılabilecek başka kalem çıkmadı.
> **“Yapılmaya değmez” sayılan madde YOK** — §3'teki C-12'nin aksine burada
> maliyeti gerçek/riski sıfır bir kalem bulunamadı; açık kalanların hepsinin
> karşılığı gerçek bir risk ya da gerçek bir gelir/erişim kaybı.
> Maddelerin başındaki **[KAPANDI]/[AÇIK]** işareti bu turdan.

**E-1 · [KAPANDI 2026-09-12] Görev Zamanlayıcı'yı yeniden kur · ~2 dk · diğer her
şeyin ön koşulu.**
**YAPILDI — 2026-09-12 ~12:00.** Bu belge yazılırken hâlâ açıktı, aynı gün kapandı.
Script yükseltilmiş PowerShell ile çalıştırıldı (ilk deneme yükseltmesiz yapıldı ve
`Unregister-ScheduledTask` `HRESULT 0x80070005 Erişim engellendi` verdi — görevler
yükseltilmiş bağlamda kurulmuş; silme başarısız olduğu için hiçbir görev kaybolmadı).
Doğrulama: üç görevin de `Arguments` alanı artık
`"<repo>\gorev_sarmalayici.py" <betik>.py`, ve `DisallowStartIfOnBatteries` /
`StopIfGoingOnBatteries` üçünde de **False**. `gorev_izleri/watch_projects.log` 12:06'da
kendiliğinden oluştu, ilk `BAŞLADI` satırı düştü.

**Kalan not da kapandı — akşam ÖLÇÜLDÜ.** `auto_process.log`'da
`sarmalayıcı devrede DEĞİL` satırının SON geçtiği an **11:56:48** (satır 3220-3226,
üç görev için üç satır). Ondan sonraki **sekiz koşunun** (13:05, 14:05, 15:05, 16:05,
17:05, 18:05, 19:05, 20:05) hiçbirinde o satır YOK — yani uyarı **kesildi**.
Karşı kanıt (uyarının susması tek başına “görev hiç çalışmadı” da olabilirdi):
`gorev_izleri/auto_process.log` aynı sekiz koşuyu `BAŞLADI … BİTTİ … rc=0` çiftleriyle
yazmış, yani görevler GERÇEKTEN sarmalayıcıdan geçiyor; `gorev_izleri/watch_projects.log`
da dakikalık koşuları yazmaya devam ediyor (20:29'a kadar, 47 KB).
Uyarının kendisi hâlâ canlı bir koruma: üç görevden biri eski tanıma dönerse bir
sonraki koşuda yeniden yazılır.

**E-2 · [AÇIK — tarayıcı/konsol oturumu, kullanıcı] YouTube Reporting API'yi aç ·
~5 dk · SON TARİH 2026-10-11 (29 gün).** Google Cloud
Console'da tek tık. Bugün doğrulandı: `olcum_temel_cizgi.json` → `cekilebildi_mi = false`
(403 SERVICE_DISABLED). **Ertelenemez:** job yalnızca kurulmadan önceki **30 günü**
doldurur; 40 kapak 2026-09-11'de değişti ve temel çizgi tam o pencerede — her gecikme günü
temel çizgiden bir gün siliyor. Analytics API'nin `impressions`/CTR metriklerini tanımadığı
dört denemeyle kayıtlı, alternatif yol yok. Yedek: Studio → Analizler → Erişim, CSV.
> **Bırakıldı (2026-09-12):** Google Cloud Console'da oturum açıp bir servisi ETKİN
> etmek bu ajanın yapabileceği bir fiil değil (tarayıcı + kullanıcı hesabı).
> Bu turda diskten yeniden doğrulandı, değişmedi: `olcum_temel_cizgi.json` →
> `gosterim_ctr_durumu.cekilebildi_mi = false`, sebep alanı
> `“KAPALI — Google Cloud projesinde (1026223060773) YouTube Reporting API etkin
> değil (HTTP 403 SERVICE_DISABLED).”`
> **KULLANICININ ATACAĞI TAM ADIM:** console.cloud.google.com → proje
> **1026223060773** → “APIs & Services” → “Library” → “YouTube Reporting API” →
> **ENABLE**. Sonra depoda `python olcum_temel_cizgi.py` yeniden çalıştırılıp aynı
> alanın `true` olduğu görülmeli — kapandığının ÖLÇÜSÜ bu, konsoldaki yeşil tik değil.

**E-3 · [AÇIK — başka ajanın sahipliğinde + bu oturumda commit/push YASAK] Üretim
checkout'unu `main`'e al, push'un aktığını doğrula · ~2 dk.**
`git_sync.push_path()` dal `main` değilse **sessizce `return`** ediyor (bilinçli tasarım).
HEAD hâlâ `claude/analiz-yap-sk8gpf` ve log'da `otomatik push edildi` satırı sayısı **0**
(ikisi de bugün doğrulandı). Sonuç: `docs/latest.html` her saat diskte doğru üretiliyor ama
canlıya hiç gitmiyor — **bio linkinin gösterdiği sayfa 7 gündür bayat**, yayındaki 20
içerikten 6'sı (4 şarkı + bir DJ seti + ilk derleme) sayfada yok. Yol: commit → push → PR →
merge, sonra üretim checkout'u `main`'e. ⚠ **`git reset --hard`/`git clean -f` üretim
checkout'unda ASLA elle çalıştırılmamalı** — `projects/*/state.json` git'te izleniyor ama
otomasyon sürekli commit'siz güncelliyor. Doğrulama: sonraki koşuda log'da
`docs/latest.html otomatik push edildi`.
> **Bırakıldı (2026-09-12):** iki ayrı sebep. (1) `docs/`, `netlify_kontrol.py` ve git
> dal/PR durumu bu turda BAŞKA bir ajanın sahipliğinde. (2) Maddenin gövdesi zaten
> `commit → push → PR → merge` diyor; bu oturumda commit/push açıkça yasak.
> **Bu turda yeniden ölçüldü, DEĞİŞMEDİ ve gecikme BÜYÜYOR:** HEAD hâlâ
> `claude/analiz-yap-sk8gpf`; `auto_process.log`'da `otomatik push edildi` satırı
> **0** (grep -c ile sayıldı); ve her saat başı düşen uyarı satırı büyüyor —
> 13:05'te `4 sa 53 dk geride`, 17:05'te `8 sa 52 dk geride`, her koşuda
> `6 içerik canlıda YOK (canlı 14, olması gereken 20)`.
> **KULLANICININ ATACAĞI TAM ADIM:** dal commit'lenip PR açılıp `main`'e merge
> edildikten sonra üretim checkout'unda `git checkout main` + `git pull`. Doğrulama
> bir sonraki saatlik koşuda: `auto_process.log`'da `otomatik push edildi` satırı
> görünmeli VE `UYARI: git senkron` satırı kesilmeli — birincisi tek başına yetmez.

**E-4 · [AÇIK — tarayıcı OAuth, kullanıcı] Instagram token'ını yeniden yetkilendir ·
~5 dk.** `upload/instagram_token.json`
mtime **2026-09-01** (doğrulandı): ne daha önce log'a sızmış değer geçersiz kılındı, ne
60 günlük sayaç sıfırlandı.
> **Bırakıldı (2026-09-12):** OAuth akışı tarayıcıda kullanıcı hesabıyla yürüyor;
> ajan bir token dosyasını tazeleyemez (ve bu oturumda token dosyaları açılmadı).
> Bu turda yeniden ölçüldü: `upload/instagram_token.json` mtime **2026-09-01 10:00**,
> 276 bayt — 11 gündür dokunulmamış, yani madde yazıldığından beri hiç değişmedi.
> **E-16 ve E-11 bu maddeye BAĞLI** (token tazelenmeden ikisi de 401 alır).

**E-5 · [AÇIK — 42 YouTube videosuna YAZAN fiil + ağ çağrısı] AI beyanı onarım
kampanyasını çalıştır · ~10 dk · kota planı gerektirir.**
`upload/ai_beyani_onar.py` var ama `upload/ai_beyani_onarim.json` **YOK** → **42 videonun
hiçbiri onarılmamış.** Maliyet 42 × 51 = **2.142 birim (%21,4)**. Önce dört maddeyi
`auto_process.log`'un son 30 satırından doğrula: (1) bugün **Cuma değil** (Cuma DJ koşusu
+3.454…5.104 birim); (2) sıradaki yayına **≥3 saat** var; (3) log'da `DJ tarama: karantinada
bekleyen içerik yok`; (4) elle `--count N` planı yok. **Tavsiye:** Cuma olmayan gün
**10:15 TR**, önce `--dry-run --limit 100` (42 birim), sonra `--uygula --limit 42`; günün
kalanına ~6.600 birim kalır. Kampanya kesintiye dayanıklı (`quotaExceeded`'da temiz durur,
ilerleme her videodan sonra diske yazılır).
> **Bırakıldı (2026-09-12):** `--uygula` 42 canlı YouTube videosunun `status`
> bloğunu GÜNCELLER — platforma yazan bir fiil, bu oturumda yasak. `--dry-run` bile
> ağ çağrısıdır (42 birim okuma) ve ağ çağrısı da izne bağlı.
> Bu turda diskten doğrulandı, değişmedi: `upload/ai_beyani_onarim.json` **YOK**
> (dosya hiç oluşmamış) → 42 videonun hiçbiri onarılmamış.
> **KULLANICININ ATACAĞI TAM ADIM (sırayla):** (1) Cuma OLMAYAN bir günde, TR **10:15**
> (kota Pasifik gece yarısında sıfırlanıyor); (2) `auto_process.log`'un son 30
> satırında dört şart teyit edilir — Cuma değil · sıradaki yayına ≥3 saat var ·
> `DJ tarama: karantinada bekleyen içerik yok` satırı düşmüş · elle `--count N` planı
> yok; (3) `python upload/ai_beyani_onar.py --dry-run --limit 100`; (4) çıktı beklendiği
> gibiyse `python upload/ai_beyani_onar.py --uygula --limit 42`.
> Kapandığının ÖLÇÜSÜ: `upload/ai_beyani_onarim.json` oluşmuş ve içinde 42 kayıt olmalı.

**E-6 · [AÇIK — platforma yayın fiili] TikTok taslaklarını elle yayınla · ~40 dk.**
**21 taslak** `DRAFT_INBOX`
(18 `projects/` + 2 `dj_sets/` + 1 `derlemeler/`); `tiktok_published_at` olan: **0**. İkisi
yayınlanmayacak — `City Pulse Set` (telif eşleşmesi) ve `Küllerimden Geç` (kopya, unlisted)
→ **19 yayınlanabilir.** Yayınladıklarını mutlaka işaretle
(`python upload/tiktok_publish_plan.py --yayinlandi-hepsi`): API "yayınlandı mı" sorusunu
cevaplamıyor, işaretleme tek doğruluk kaynağı. ⚠ Modülün docstring'i "20 taslak" diyordu; **bu akşam düzeltildi** (C-14 turu) ve
artık **21** yazıyor, sayının nereden geldiği de kayıtlı — 20'de "bitti" sanılırsa
bir taslak sonsuza kadar beklerdi.
**Bu turda BAĞIMSIZ olarak yeniden sayıldı** (üç kökün tüm `state.json`'ları tarandı):
`tiktok_publish_id` taşıyan **21** kayıt — 18 `projects/` + 2 `dj_sets/`
(`City Pulse Set`, `Just Relax`) + 1 `derlemeler/` (`Gece Seansı Vol. 1`);
`tiktok_published_at` taşıyan **0**. Yani sayı doğru ve iş hiç başlamamış.
⚠ "Trend ses/format ile ek TikTok paylaşımı" fikri geçerli ama **bu 19 bitene kadar askıda
kalmalı.**
> **Bırakıldı (2026-09-12):** taslağı canlıya çıkarmak TikTok uygulamasından yapılan,
> geri alınamaz bir yayın fiili (`video.publish` scope'u reddedildi — B-5, kalıcı).
> **KULLANICININ ATACAĞI TAM ADIM:** TikTok uygulaması → gelen kutusu/taslaklar →
> **19** taslağı tek tek yayınla (`City Pulse Set` ve `Küllerimden Geç` ATLANACAK) ve
> her birinde native **“AI-generated content”** etiketini AÇ. Bitince depoda
> `python upload/tiktok_publish_plan.py --yayinlandi-hepsi` — API “yayınlandı mı”
> sorusunu cevaplamadığı için bu işaretleme TEK doğruluk kaynağı; atlanırsa madde
> kapandığı hâlde kapalı görünmez.

**E-7 · [AÇIK — üçün BİRİ kaldı; Studio canlı ekran] Studio'da üç telif satırını
kontrol et · ~5 dk · tek ekran.** YouTube Data API
Content ID itirazlarını göstermiyor; bilgi yalnızca Studio → Kısıtlamalar'da.
(1) **City Pulse Set** — telif eşleşmesi kayıtlı (4 aralık, 106 sn), itirazın durumu
bilinmiyor; risk artık üç kapıyla çevrelenmiş, yani "yanlışlıkla yayınlanır" değil "durumu
bilmiyoruz" boşluğu. (2) **Gece Seansı Vol. 1** — **BU SATIR KAPANDI:**
`derlemeler/Gece Seansı Vol. 1/state.json`'da `dj_tarama_temiz: true` +
`dj_tarama_kontrol_at: 2026-09-11T18:13:21` (bu turda diskten doğrulandı). Kaçan şey
yalnızca tek atışlık BİLDİRİMDİ; sonucun KAYDI yerinde, yani Studio'ya bu satır için
tekrar bakmaya gerek yok.
(3) **Just Relax** — **BU SATIR DA KAPANDI:** state.json'da `dj_tarama_temiz: true`
ve yanında provenansı: `dj_tarama_temiz_kaynak = "YouTube Studio hak talepleri
sayfasi, 2026-09-12: 'Bu videoda hak talebi bulunamadi'"` — yani Studio'ya GERÇEKTEN
bakılmış ve kanıt state'e yazılmış (bkz. E-8).

**Kalan TEK satır (1) City Pulse Set.** `dj_sets/City Pulse Set/state.json`'da
`telif_eser = "Bring Me To Life - Tiesto, FORS"` ve dört `telif_araliklari` duruyor,
ama **İTİRAZIN DURUMUNU tutan hiçbir alan yok** (bu turda state'in tüm `telif_*`
anahtarları tarandı: yalnızca `telif_araliklari`, `telif_eser`, `telif_notu`).
O bilgi yalnızca canlı Studio ekranında; API göstermiyor (B-2, kalıcı).
> **KULLANICININ ATACAĞI TAM ADIM:** YouTube Studio → İçerik → `City Pulse Set` →
> **Kısıtlamalar** sütunundaki telif satırına tıkla → itirazın durumunu oku
> (beklemede / kabul / red). Sonucu `dj_sets/City Pulse Set/state.json`'a
> `Just Relax`'teki desenle yaz: bir durum alanı + yanında tarihli `*_kaynak` cümlesi.
> Provenansı yazmak kozmetik değil — `Just Relax`'te tam olarak o cümle, E-8'in
> “bakmadan true yazılmış mı” sorusunu bu turda cevaplayan şeydi.

**E-8 · [KAPANDI 2026-09-12] `Just Relax` state.json'a `dj_tarama_temiz: true` ·
~1 dk · KOŞULLU.** Yalnızca
E-7'de temiz görüldüyse **ve** K-5 onayı geldiyse. Bu alan kozmetik değil, bir **politika
kapısı**; bakmadan `true` yazmak karantinayı elle açmaktır. Kuru doğrulama:
`python dj_clips.py --yayin-kuru`.
> **Kapandı — ajan YAZMADI, YAZILMIŞ olduğunu DOĞRULADI.** İki koşulun ikisi de
> sağlanmış: K-5 onayı bugün geldi (commit `6f6fd5b`, bkz. C-8) ve E-7'nin (3).
> satırı Studio'da bakılarak kapanmış. Diskteki hâli:
> `dj_sets/Just Relax/state.json` → `dj_tarama_temiz: true` **ve**
> `dj_tarama_temiz_kaynak: "YouTube Studio hak talepleri sayfasi, 2026-09-12:
> 'Bu videoda hak talebi bulunamadi'"`. İkinci alan maddenin kendi endişesinin
> (“bakmadan `true` yazmak karantinayı elle açmaktır”) cevabı: bakılmış.
> **Kuru doğrulama ÇALIŞTIRILDI** (`python dj_clips.py --yayin-kuru`; saf disk işi —
> `yayina_uygun_mu()` yalnızca state okur, `uyumluluk.kontrol()` de diski gezer,
> `kesit_yayinla` çağrılmadan `dry_run` dalından dönülüyor, ağ çağrısı YOK):
> `bakilan: 2, yayinlanan: 1`, seçilen `Just Relax → clip_01.mp4`
> (332,53-377,53 sn, 2.505.728 bayt); `City Pulse Set` “üretilmiş kesit yok” ile
> atlandı. Yani kapı GERÇEKTEN açıldı: madde yazıldığında süpürge
> “Content ID taraması henüz temiz değil” diyordu, şimdi yayınlanabilir bir kesit
> gösteriyor. ⚠ **Bunun doğal sonucu:** bir sonraki haftalık DJ koşusu (`dj_clips.supur`,
> `dj_famous_process.py`'nin `finally`'sinden) bu kesidi OTOMATİK yükleyecek —
> K-5'in “ilk yayın elle izlenerek” şartı burada geçerli.

**E-9 · [AÇIK — platform fiili; API'den YAPILAMAZ (B-1)] Instagram'daki kopya Reels'i
ARŞİVLE (silme) · ~5 dk.** Aynı ses (md5 birebir)
Instagram'da iki kez canlı: `18087131705485174` (07 Eylül, kopya) ve `18112778338817977`
(05 Eylül, asıl). YouTube tarafı 11 Eylül'de temizlendi, Instagram temizlenmedi — **bugün
kanalın "tekrarlayan içerik" tarifine giren tek somut canlı yüzeyi bu.** Kaldırılacak:
`18087131705485174`. Arşivleme silmeye üstün (profilden kaldırır, veriyi tutar, geri
alınabilir). **API'den yapılamaz** (B-1).
> **Bırakıldı (2026-09-12):** iki bağımsız sebep. (1) Instagram'a yazan/kaldıran bir
> fiil, bu oturumda yasak. (2) Teknik olarak da imkânsız: Graph API medya silmiyor
> (`IGApiException 100 / subcode 33`) ve arşivleme uç noktası hiç yok — `upload/`
> altında DELETE yolu YOK ve B-1 “eklenmemeli” diyor.
> **KULLANICININ ATACAĞI TAM ADIM:** Instagram uygulaması → profil → **07 Eylül**
> tarihli Reel (medya kimliği `18087131705485174`) → sağ üst … → **Arşivle**.
> ⚠ **05 Eylül'deki `18112778338817977` KALACAK** — asıl kayıt odur, arşivlenmeyecek.
> ⚠ **Silme değil arşivleme**: veri durur, geri alınabilir, ve bu deponun
> “hiçbir şeyi silme” kuralına uyar.

**E-10 · [AÇIK — hedef klasör kullanıcı kararı · ama belgedeki KOMUT bu turda
DÜZELTİLDİ] Yedekleme kur · ~5 dk (P1) + haftalık (P2).** Diskte **5,9 GB** ignore edilmiş,
yani version control dışında içerik var; bu bir dizüstü, disk kaybında GitHub'dan gelmez.
**~11 MB hiçbir koşulda geri gelmez:** `dj_sets/_arda/` (kaybı onay konuşmasını yeniden
açmak demek), iki `dj_sets/*/art.jpg` (AI ile işlenmiş sahne; yeniden üretim FARKLI kare
verir, yayındaki videonun kartıyla arşiv uyuşmaz), `_telif_bolumleri/` (açık bir telif
itirazının kanıtı). **~5 KB'ı** (token + client_secrets + `notify_config.json` +
`stock_art_config.json`) kaybedilirse saatlerce OAuth; en zahmetlisi Facebook (sayfa
token'ı non-expiring, bir kez kurulup bir daha dokunulmayan dosya).

```powershell
# P1 — bulut klasörü, günlük. Riskin %95'ini kapatıyor.
# ÖLÇÜLDÜ 2026-09-12, TAM BU KOMUTLA (/L ile): 435 dosya, 110,96 MB —
# belgedeki "111 MB" doğru; çıkış kodu 1 (= dosya kopyalandı, hata yok).
$kaynak = "C:\Users\ACER\Desktop\ilk-projem"
$hedef  = "$env:OneDrive\fms-yedek-kritik"
$disla = @(
  "/XD", ".git", ".claude", "__pycache__", ".pytest_cache", "gorev_izleri",
         ".stock_video_cache", "output", "_segments", "_iptal",
  "/XF", "audio.wav", "audio.mp3", "audio.m4a", "audio_telifsiz.wav",
         "backdrop.mp4", "*.log", "*.bak.*"
)
# ÖNCE /L ile listele, çıktıyı gör; doğruysa /L'yi SİL ve tekrar çalıştır.
robocopy $kaynak $hedef /MIR @disla /R:1 /W:1 /NFL /NDL /NP /L
# P2 — 3,8 GB, harici disk, haftalık: aynı komut, $disla'dan "/XF" ve sonrasını çıkar.
```

⚠ P1 çıktısı **SIR İÇERİR** (token dosyaları kopyaya giriyor — amaç bu): hedef klasör
paylaşıma kapalı olmalı. ⚠ `/MIR` hedefi aynalar, hedef SADECE bu yedeğe ait olmalı.
⚠ Zamanlayıcıya bağlanacaksa **mevcut üç göreve EKLEME** — ayrı görev, sakin bir saat.

> **Komut bu turda DÜZELTİLDİ — eski hâli PowerShell'de HİÇBİR ŞEY YEDEKLEMİYORDU.**
> Blok `powershell` etiketliydi ama `^` (cmd.exe satır devamı) kullanıyordu;
> PowerShell'in devam karakteri backtick, `^` değil. Ölçüldü (2026-09-12, hepsi `/L`
> ile, hiçbir dosyaya dokunulmadan):
>   1. PowerShell `^`'i robocopy'ye **dosya filtresi** olarak geçiriyor — çıktının
>      başlığı `Files : ^` (normalde `Files : *.*`), ve hiçbir dosya eşleşmiyor:
>      `Files : 0 kopyalandı`.
>   2. Sonraki satırlar AYRI birer deyim oluyor:
>      `/XF : The term '/XF' is not recognized as the name of a cmdlet…` — yani
>      `/XD`/`/XF` dışlamaları ve `/R:1 /W:1` **hiç uygulanmıyor**; robocopy
>      varsayılan `/R:1000000 /W:30` ile koşuyor (tek kilitli dosya yedeği saatlerce
>      asar — bu turda gerçekten yaşandı, koşu 2 dakikada bitmeyip iptal edildi).
>   3. **En sinsi kısmı:** robocopy bu hâlde **çıkış kodu 0** veriyor (“dosya
>      kopyalanmadı, hata da yok”), doğru komut ise 3. Yani ekranda başarı gibi
>      görünüyor ve kullanıcı yedeği olduğunu sanıyor.
> **Ölçülüp ÇÜRÜTÜLEN korku:** “`/MIR` + boş filtre hedefi siler” sanılabilir;
> ölçüldü, SİLMİYOR — sahte bir kaynak/hedef çiftinde `Extras: 0` çıktı (doğru komut
> aynı çiftte `Extras: 1` diyor). Yani arıza **sessiz bir hiçbir-şey-yapmama**,
> veri kaybı değil. Yine de bir yedekleme talimatı için en kötü arıza sınıfı bu:
> yokluğu görünmüyor (bkz. CLAUDE.md, “sessizce False dönen koruma”).
> **Düzeltme:** devam karakteri hiç kullanılmıyor — dışlamalar bir diziye (`@disla`)
> konup splat ediliyor, `$kaynak`/`$hedef` ayrı değişken. `/L` de komutun İÇİNE
> konuldu: ilk çalıştırma zorunlu olarak kuru, kullanıcı çıktıyı görüp `/L`'yi siliyor.
> **Madde yine de AÇIK:** hedef klasörün nerede olacağı ve SIR İÇEREN bir kopyanın
> buluta konup konmayacağı kullanıcı kararı; ajan `$env:OneDrive`'a yazmadı.
> **KULLANICININ ATACAĞI TAM ADIM:** yukarıdaki bloğu `/L` ile çalıştır → çıktıda
> `Files : *.*` ve ~433 dosya / ~111 MB gördüğünü doğrula → `/L`'yi sil → tekrar
> çalıştır → `$env:OneDrive\fms-yedek-kritik` klasörünün paylaşıma KAPALI olduğunu
> teyit et (içinde token dosyaları var).

**E-11 · [AÇIK — platform fiili] Instagram'da 4 eski kapaklı gönderiyi kaldır/arşivle ·
~5 dk · canlı doğrulama.**
`state.json`'lardaki yeni `instagram_media_id` değerleri "canlı yeni" ile birebir uyuşuyor;
eskiler ancak uygulamadan görülür, silen kod yok ve olamaz. E-9 ile aynı oturumda +0 dk.
> **Bırakıldı (2026-09-12):** E-9 ile birebir aynı gerekçe — Instagram'dan kaldırma
> yalnızca uygulamadan yapılır (B-1) ve platforma dokunmak bu oturumda yasak.
> **KULLANICININ ATACAĞI TAM ADIM:** E-9'un arşivleme oturumunda, profilde yukarı
> kaydırıp **eski (2026-09-11 öncesi) kapak tasarımını taşıyan** 4 gönderiyi de
> arşivle. Hangilerinin kalacağını ayırt etme ölçütü diskte var: `state.json`'lardaki
> GÜNCEL `instagram_media_id` değerleri “canlı yeni” ile birebir uyuşuyor — yani
> **state'te kimliği geçmeyen** gönderi eskidir.

**E-12 · [AÇIK — YouTube'a YAZAN fiil] Bekleyen 1 yorum yanıtını gönder · ~2 dk.**
`yorum_taslaklari.json`: 11 taslağın
10'u yanıtlanmış, 1'i `onay_bekliyor` (`Kader Ortakları` altında, 2 gündür), taslak hazır:
`python upload/yorum_gonder.py --gonder --limit 1`. `atlanan` listesindeki tek kayıt
bilinçli atlama (aynı kişinin aynı videoya birebir aynı ikinci yorumu). Otomatikleştirilmeme
gerekçesi (kota + "inauthentic" riski + geri dönüşsüzlük) geçerli.
> **Bırakıldı (2026-09-12):** `--gonder` `comments.insert` çağırır — YouTube'a yazan,
> geri alınamaz bir fiil (yayınlanan yorum düzenlenemez, ancak silinir).
> Bu turda diskten yeniden ölçüldü ve madde **birebir doğru**: 11 taslak,
> 10 `zaten_yanitlandi` + **1 `onay_bekliyor`** (`Kader Ortakları`,
> id `UgwTQ2104QUJBakLO_l4AaABAg`), `atlanan` 1 kayıt.
> ⚠ **Log'daki sayıyla karıştırma — bu tuzağa düşmek kolay:** `auto_process.log` her
> saat `Yorumlar: **2** yanıt bekliyor` yazıyor ve bu satır taslak dosyasından DEĞİL,
> canlı API'den (`comments_cache.json`) geliyor. İkisi çelişmiyor: canlıda yanıtsız
> iki yorum var, ikisinin de taslağı VAR, ama ikincisi (`Küllerimden Geç`,
> `UgwtcZ0es5VVchJirHl4AaABAg`) `atlanan` listesindeki **bilinçli atlama** — aynı
> kişinin aynı videoya birebir aynı ikinci yorumu. Yani log sonsuza kadar “2”
> diyecek; E-12 bitince bile “1” olacak, “0” olmayacak.
> **KULLANICININ ATACAĞI TAM ADIM:** depoda
> `python upload/yorum_gonder.py --gonder --limit 1`. `--limit 1` şart: limitsiz
> çalıştırmak atlama kararını da ezebilir.

**E-13 · [AÇIK — telefon; diskten doğrulanamıyor] ntfy aboneliğini doğrula · ~3 dk.**
`notify_config.json`
var ama telefondaki abonelik iz bırakmıyor. Yapılmadıysa şu emniyet ağlarının **hepsi
sağır**: Instagram token, Netlify, görev tanımı, kaçan koşu, git senkron, ses takip,
karantina, DJ kesit işareti, yayın durgunluğu. ⚠ Ayrıca: **`notify.uyar_bir_kez()` telefona
hiçbir şey göndermiyor** — yalnızca log satırı yazıyor. Telefona giden tek yol
`notify.send()` ve otomasyonda onu çağıran tek yer `saglik_kontrol._bildir()`. Kapı
noktalarındaki docstring'ler bunu bildirim gibi okutuyor; değil.
> **Bırakıldı (2026-09-12):** doğrulanacak şey bir TELEFONDAKİ abonelik; diskte izi
> yok ve ajan telefona bakamaz. Diskten yapılabilen yarısı bu turda ölçüldü:
> `notify_config.json` var (87 bayt, mtime bugün 17:16) ve İKİ anahtar taşıyor —
> `ntfy_topic` **ve** `telegram_chat_id`. Yani kanal yapılandırması tam; eksik olan
> yalnızca telefonun o konuya ABONE olup olmadığı.
> **KULLANICININ ATACAĞI TAM ADIM:** telefonda ntfy uygulaması → abonelikler
> listesinde `notify_config.json`'daki `ntfy_topic` değeri görünüyor mu? Yoksa
> ekle. Uçtan uca ÖLÇÜM: depoda `python saglik_kontrol.py` çalıştırılıp telefona
> bildirim düşüyor mu bakılmalı — `notify.send()`'i otomasyonda çağıran TEK yer
> `saglik_kontrol._bildir()`, yani gerçek hattı sınayan tek komut bu.

**E-14 · [AÇIK — platform profili; E-3'e BAĞLI] Bio linkini kontrol et · ~3 dk.** Instagram/TikTok profillerinde
site alanı `https://famousmusicstudio.com/latest.html` mı? E-3 olmadan yarım kalır.
> **Bırakıldı (2026-09-12):** profil ayarı yalnızca uygulamadan değişir, API'den
> değiştirilemiyor (CLAUDE.md, C3) — ve E-3 kapanmadan anlamsız: bugün o adresin
> gösterdiği sayfa **7+ gün bayat** (canlıda 14 içerik, olması gereken 20).
> **KULLANICININ ATACAĞI TAM ADIM (E-3'ten SONRA):** Instagram profili → Profili
> düzenle → Bağlantılar, ve TikTok profili → Profili düzenle → Web sitesi; ikisinde
> de değer `https://famousmusicstudio.com/latest.html` olmalı. Sonra o adres
> tarayıcıda açılıp **20** içerik listelediği görülmeli.

**E-15 · [AÇIK — platforma yükleme] Facebook sayfa varlıkları + Bluesky banner ·
~10 dk · canlı doğrulama.**
`marka/facebook_kapak.png` (1640×856) ve `marka/bluesky_banner.png` diskte; yüklenip
yüklenmedikleri görülmüyor. `marka/facebook_metinleri.txt` bugün düzeltildi, hazır.
> **Bırakıldı (2026-09-12):** kapak/banner yüklemek Facebook ve Bluesky'a yazan bir
> fiil. Diskten yapılabilen yarısı bu turda ölçüldü — **üç dosya da yerinde ve
> boyutları doğru**: `marka/facebook_kapak.png` **1640×856** (Facebook sayfa kapağı
> oranı), `marka/bluesky_banner.png` **1500×500** (Bluesky banner oranı),
> `marka/facebook_metinleri.txt` 652 bayt (bugün 07:36'da düzeltilmiş).
> Yani hazırlık tarafında eksik YOK; kalan tek şey yükleme fiili.
> **KULLANICININ ATACAĞI TAM ADIM:** Facebook Sayfası → Düzenle → Kapak fotoğrafı →
> `marka/facebook_kapak.png`; sayfa açıklaması/bilgi alanlarına
> `marka/facebook_metinleri.txt` içeriği. Bluesky → Edit Profile → Banner →
> `marka/bluesky_banner.png`.

**E-16 · [AÇIK — Instagram'a YÜKLEME gerektiriyor · sayı 3 → 2] İki projenin
Instagram dağıtımı yarım kalmış.** Bu turda üç kökün TÜM `state.json`'ları yeniden
tarandı — `youtube_video_id` dolu ama `instagram_media_id` YOK olan **iki** proje
kaldı: `Bu Gece Kazandık`, `Kader Ortakları`.
**`Sofraya Gelmedin` listeden DÜŞTÜ:** bugün 13:05 koşusunda kendiliğinden tamamlandı
(`auto_process.log`: `Instagram: tamam, media_id=18619032325043423`) ve aynı değer
`projects/Sofraya Gelmedin/state.json`'da duruyor — iki kaynak birbirini doğruluyor.
Kalan ikisi 09-10 sonrası, token kesintisiyle örtüşüyor. Veri bozuk değil, **iş yarım**;
ikisinde `instagram_creation_id` de YOK (bu turda tek tek bakıldı), yani golden-hour
kuyruğuna hiç girmemişler — kendiliğinden toparlanmaları beklenemez.
> **Bırakıldı (2026-09-12):** tamamlama adımı Instagram'a video yükleyip yayınlıyor —
> platforma yazan fiil, bu oturumda yasak. Ayrıca **E-4'e bağlı**: token 09-01'den
> beri tazelenmedi, şimdi çalıştırmak 401 verir ve iş yine yarım kalır.
> **KULLANICININ ATACAĞI TAM ADIM (önce E-4, sonra bunlar):**
> `python upload/instagram_upload.py --project "projects/Bu Gece Kazandık"` ve
> `python upload/instagram_upload.py --project "projects/Kader Ortakları"`
> (`--project` doğrulandı, modülün zorunlu argümanı). Kapandığının ÖLÇÜSÜ: iki
> `state.json`'da da `instagram_media_id` alanının oluşması.
> ⚠ Yükleme golden-hour kuyruğuna girer — `media_publish` hemen değil, bir sonraki
> 12:00-14:00 / 18:00-22:00 penceresinde çalışır. “Çalışmadı” sanıp tekrar
> tetikleme: konteyner iki kez oluşur.

**E-17 · [AÇIK — insan işi, devredilemez] İlk 20-30 gerçek takipçiyi elle bul ·
birkaç saat.** Depodan doğrulanamaz ama
kanal istatistikleri (izlenme 12-119 bandı) hâlâ "algoritma henüz hesaba güvenmiyor"
aralığında; madde anlamını koruyor.
> **Bırakıldı (2026-09-12):** maddenin tamamı platformlarda gerçek insanlarla
> etkileşim (takip, yorum, mesaj) — hem platforma yazan fiil hem de devredilmesi
> maddenin AMACINI bozan bir iş: “gerçek takipçi” aranırken otomatik/ajan eliyle
> etkileşim üretmek, kanalın en büyük riski olan “inauthentic” tarifinin ta kendisi.
> **YAPILMAYA DEĞMEZ DEĞİL:** kanal istatistikleri (izlenme 12-119 bandı) hâlâ
> “algoritma hesaba güvenmiyor” aralığında, yani maddenin karşılığı gerçek.

---

## 3. KOD İŞLERİ

> **GÜNCELLEME — 2026-09-12 akşam (C-1…C-14 tek tek koddan doğrulandı).**
> Kapanan: **C-1, C-2, C-5, C-11, C-13** + **C-14'ün sahiplik içindeki 13 satırı**.
> Açık kalan: **C-3, C-4, C-6, C-7, C-8, C-9, C-10** (gerekçeler maddelerin altında).
> **C-12 yapılmaya değmez** sayıldı (altta).
> Test sayısı 1226 → 1291. Maddelerin başındaki **[KAPANDI]/[AÇIK]** işareti bu turdan.

**C-1 · [KAPANDI 2026-09-12] `facebook_backfill.politika_kapisi`'ye `_KAPI_ONBELLEGI` ekle (~5 satır).**
Doğrulandı: `ek_platform_backfill.py`'de var (koşu başına proje başına tek kapı çağrısı,
koşu sonunda `.clear()`), `facebook_backfill.py`'de **yok**. Bugünkü katalogda etkisi yok;
maliyet sorunu değil, iki kardeş modül arasında asimetri. `.clear()` de kopyalanmalı.
> **Kapatıldı:** `_KAPI_ONBELLEGI` + `politika_kapisi` içinde okuma/yazma +
> `backfill()` başında `.clear()` eklendi; iki kardeş modül artık birebir aynı
> desende. Koruma: `tests/test_backfill_uyumluluk_kapisi.py`'ye iki PARAMETRİK
> test (`[ek_platform]` / `[facebook]`) — hangi modülde eksilirse orada kırılır.
> Kırmızı/yeşil: HEAD'in dosyasıyla `facebook` varyantları FAILED, düzeltmeyle
> 14/14 passed. Ölçülen kazanç bugün **sıfır** (kapı zaten proje başına bir kez
> soruluyordu); değeri asimetrinin kapanması ve ikinci çağrının artık ücretsiz
> olması.

**C-2 · [KAPANDI 2026-09-12] Test: bozuk `state.json` md5 ikizini de düşürüyor (~40 satır).** Bugün ölçülen,
testle kaplı olmayan davranış: tek bir bozuk `state.json` **iki** projeyi durduruyor —
kendisi ve aynı ses md5'ini taşıyan ikizi. Karşı tarafın durumu okunamayınca
`cekilmis_taraf = None` ve `oteki_yayinda = True` olur, md5 muafiyetinin iki şartı da
sağlanmaz, kalan tek dal HATA'dır. Davranış **bilinçli ve doğru** ("bilmiyorum" ≠
"çözülmüş"), ama ölçülmemiş yan etkisi şu: depodaki tek belgelenmiş kopya çifti, birinin
dosyası bozulunca meşru tarafı da yayından düşürüyor — ve o çift bugün uyarı seviyesinde,
yani mesafe tek bir yarım yazımdan ibaret. **Tarif:** `tmp_path`'te iki sahte proje,
`audio.wav` birebir aynı; A unlisted + `kopya_notu`, B public; `uyumluluk.KOKLER`'i
monkeypatch'le bu köke çevir. (1) Temel çizgi `kontrol(B,"yukleme")` → `hatalar == []`.
(2) A'nın state'ine yarım JSON yaz (`'{"a":'`). (3) İddia: `hatalar` boş değil, mesaj
`"BİREBİR AYNI (md5)"` içeriyor. (4) Yan kazanç: üçüncü ilgisiz projenin `hatalar`ı BOŞ
kalıyor → "kanal durmuyor" garantisi de çivilenir. **Doğrulandı: böyle bir test bugün yok**;
hiçbir test iki projenin state'leri arasındaki bu bağı görmüyor.
> **Kapatıldı:** `tests/test_uyumluluk_kopya_kapisi.py::test_bozuk_state_json_md5_IKIZINI_de_dusuruyor`
> — tarifin dördü de (temel çizgi / yarım JSON / ikizin düşmesi / ilgisiz projenin
> temiz kalması) aynı testte. `uyumluluk.py` DEĞİŞMEDİ (davranış zaten doğruydu).
> Kırmızı/yeşil: `except DurumBozuk` dalı `b_durum = {}`'e mutasyona uğratılınca
> test FAILED, geri alınınca 22/22 passed.

**C-3 · [AÇIK — karar bekliyor] AI beyan satırını Instagram/Facebook/Telegram/Bluesky
caption'larına ekle.** Doğrulandı: `social_text.build_ai_disclosure_line()` var ama onu çağıran tek
yer `dj_famous_process.py`. Ana kataloğun **17 IG + 5 FB + 2 TG + 5 Bluesky** gönderisinin
hiçbirinde AI bildirimi yok (YouTube'da koşulsuz ve otomatik, 40/40). Mevcut karar
`config.py`'de yazılı ("sadece DJ Famous'ta", gerekçe: gerçek bir kişiyi konu alıyor) — ama
**Meta'nın "AI info" etiketi gerçek kişi şartına bağlı değil**; tamamen sentetik ses +
görsel de kapsamda, ve beyan edilmemiş olması "gizlemeye çalıştı" okumasına açık. Bu, ceza
tarafında "erişim düşüşü"nden "politika ihlali"ne geçiren fark. İş: `build_caption()`
çıktısının sonuna `build_ai_disclosure_line(resolve_language(meta))`.
> **Bırakıldı (2026-09-12):** maddenin kendi başlığı "karar gerektirir" diyor ve
> mevcut karar `config.py`'de YAZILI ("sadece DJ Famous'ta"). Yazılı bir kararı
> ajan tek başına tersine çeviremez — üstelik yön geri alınamaz: satır bir kez
> caption'a girip yayınlandıktan sonra eski gönderilerden kaldırılamaz.
> Kod tarafı gerçekten tek satır; eksik olan onay. Doğrulandı:
> `build_ai_disclosure_line()`'ın tek çağıranı hâlâ `dj_famous_process.py:711`.

**C-4 · [AÇIK — K-1'e bağlı] Uzun format ile Shorts'u aynı saniyede yayınlamayı bırak.** Ölçüm: 15/20 projede
fark **medyan 9 saniye**; `publishAt` değerleri de makine imzası taşıyor (04:30Z, 05:00Z,
05:30Z… tam 30 dk aralıklar). Bu, bir insan incelemecinin veya sınıflandırıcının göreceği
**en kolay okunan** sinyal — "aynı kanala 9 sn arayla iki video" tartışmaya açık değil. İş:
`upload_short()`'un `publish_at`'ine sabit kayma (ör. +6-12 saat, bir sonraki golden-hour).
Doğrulandı: bugün `upload_short` uzun formatla **aynı** `_compute_publish_at(privacy,
schedule)` sonucunu kullanıyor. Yan kazanç: ikinci bir keşfet penceresi. **K-1'de Shorts
kapatılırsa bu madde düşer.**
> **Bırakıldı (2026-09-12):** iki sebep birlikte. (1) Maddenin kendi son cümlesi
> K-1'e bağlıyor ve K-1 hâlâ açık bir KARAR — Shorts kapanırsa bu iş çöpe gider.
> (2) "Sabit kayma (ör. +6-12 saat)" bir YAYIN STRATEJİSİ seçimi, kod seçimi
> değil: Shorts'u bir sonraki golden-hour'a atmak kanalın günlük desenini
> değiştirir. Kod tarafı hazır: `_golden_publish_at(gun_ertele)` (DJ kesidi için
> yazılmıştı) tam bu işi yapıyor; `upload_short()`'un
> `_compute_publish_at(privacy, schedule)` çağrısını onunla değiştirmek yeterli.
> Yeniden doğrulandı: bugün ikisi AYNI çağrıyı kullanıyor
> (`upload/youtube_upload.py:502` ve `:530`).

**C-5 · [KAPANDI — bugün, commit `a625b00`] Uzun format açıklamasındaki tekrarı kır.** Ölçüm: 18 şarkının YouTube açıklamasının
**%61'i birebir aynı kelimeler**, satırların **%50'si (4/8) byte-birebir aynı**; keşfet
hashtag bloğu 18/18'de tamamen ve aynı sırayla. Kısa format caption'da 18/18'de ortak satır
**sıfır**, çünkü orada `pick_subset` ile seçim yapılıyor — sorun kasıtlı karar değil, iki
kod yolunun ayrışması. İş (`youtube_upload.build_snippet()`): `config.DISCOVERY_HASHTAGS`
yerine `social_text.pick_subset(title, config.DISCOVERY_HASHTAGS,
config.DISCOVERY_HASHTAG_COUNT, salt=13)`; ve `follow_line` hardcoded (doğrulandı,
`upload/youtube_upload.py:161`) → `pick_deterministic(title, config.FOLLOW_LINES, salt=11)`.
Beklenen: ortak kelime %61 → ~%35-40, ortak satır 4 → 3.
> **Kapandı** (bu belge yazıldıktan SONRA, aynı gün): `build_snippet()` artık
> `pick_subset(... DISCOVERY_HASHTAGS ...)` ve
> `follow_line = pick_deterministic(title, config.FOLLOW_LINES, salt=11)`
> kullanıyor (TR ve EN dalları ayrı ayrı). Commit mesajının ölçtüğü sonuç:
> benzerlik 0,79 → 0,46.

**C-6 · [AÇIK — geniş] Golden-hour penceresi başına "tek yayın" kilidi yok.** Üç hat da aynı pencereleri
(`GOLDEN_HOURS = [(12,14),(18,22)]`) kullanıyor ve birbirinden habersiz aynı dilime
yazabiliyor: ana katalog, derleme (aynı hattan), DJ kesit (+3 gün kaydırılmış aynı
pencereler). Çakışma olasılığı düşük tutulmuş ama **garanti değil**; bir günde 2-3 şey aynı
18:00-22:00 penceresine düşebilir. Hiçbir test kontrol etmiyor.
> **Bırakıldı (2026-09-12):** kilidin doğru yeri ÜÇ ayrı giriş noktasının
> (`auto_process`, `dj_famous_process`, `dj_clips.supur`) ORTAK üstü ve böyle bir
> yer bugün YOK — yeni bir paylaşılan durum dosyası + üç çağrı noktası + kilidin
> fail-open/fail-closed kararı demek. En dar tarif: `state_io` ile yazılan tek
> bir `golden_pencere_kaydi.json`
> (`{"pencere": "2026-09-12T18", "sahip": "auto_process"}`) ve üç hattın da
> yayına girmeden ÖNCE sorduğu bir `pencere_bos_mu()`.
> ⚠ Bu kapının YANLIŞ tarafa düşmesi = yayının sessizce ATLANMASI, yani
> fail-OPEN olmak zorunda — deponun diğer bütün kapılarının TERSİ bir karar, ve
> tam da bu yüzden sahibinin onayı olmadan kurulmamalı.

**C-7 · [AÇIK — yer seçimi karar gerektiriyor] "Ayda en fazla bir derleme" kuralı kodda/testte yok.** Doğrulandı: `derleme.py`'de
sabit/kapı yok, kural yalnızca iki README'de. Derleme 52 saatlik yayın tabanından **muaf**,
yani ayda bir gün 7 yayınlık bir sıçrama yapıyor (günlük desen 2-3'ten 9-10'a çıkıyor) ve
bunu engelleyen mekanizma yok.
> **Bırakıldı (2026-09-12):** kapının yeri belirsiz ve yanlış yer işe yaramıyor.
> `derleme.uret()` yalnızca KLASÖRÜ üretiyor; YAYINLAYAN
> `dj_famous_process.py --base derlemeler`. Üretim tarafına kapı koymak sıçramayı
> engellemez (önceden üretilmiş bir klasör yine yayınlanır) ve
> `derlemeler/_iptal/En Çok Dinlenenler` örneğinin gösterdiği gibi "üret,
> beğenme, at" meşru bir akış — orada kapı yalnızca engel olur. Yayın tarafına
> koymak ise DJ hattıyla PAYLAŞILAN bir modüle dokunmak: oradaki bir hata
> haftalık DJ setini durdurur. Bugün kuralı fiilen uygulayan şey,
> `derleme.py`'nin zamanlayıcıda BİLEREK olmaması (elle çalıştırılıyor).
> Doğrulandı: `derleme.py`'de aylık sabit/kapı yok.

**C-8 · [AÇIK — düşük, ürün kararı] `latest_release.py` DJ kesidini görmüyor.** `youtube_clip_video_id` bio-link
sayfasına girmiyor (doğrulandı). K-5 onaylanırsa farkında olunmalı.
> **Bırakıldı (2026-09-12):** yeniden doğrulandı — `latest_release._collect()`
> yalnızca `youtube_video_id` topluyor, `youtube_clip_video_id` dosyada hiç
> geçmiyor. Ama bu bir ARIZA değil bir SORU: 45 sn'lik türev bir kesit,
> bio-linkteki "yayındaki TÜM şarkılar" listesinde görünmeli mi? Maddenin kendi
> ifadesi de "farkında olunmalı" diyor, "eklenmeli" demiyor. K-5 bugün onaylandı
> (commit `6f6fd5b`), yani soru artık gerçek — ama cevabı sahibinin.

**C-9 · [AÇIK — kota planı gerektiriyor] `_is_fully_done()` kapağı ve playlist üyeliğini saymıyor.** Kota tükendiğinde ilk
kırılan `captions.list`, ama **kalıcı** kırılan `thumbnails.set` ve `playlistItems.insert`;
ikisi de sayılmadığı için dört ana anahtar dolduğu anda proje `pending`den kalıcı düşer ve
**kapaksız/listesiz** kalır (2026-09-06'da gerçekten oldu). Telafi yolu hiçbir göreve bağlı
değil: `upload/youtube_upload.py --thumbnail-only --all` yalnızca CLI'den.
> **Bırakıldı (2026-09-12) — ama tarif net.** Doğrulandı: `_is_fully_done()` hâlâ
> DÖRT anahtara bakıyor ve `fix_all_thumbnails()`'ın tek çağıranı argparse.
> CLAUDE.md'nin kuralı çözümü zaten söylüyor: `_is_fully_done()`'a EKLEME,
> **(A) `_drain_golden_hour_queue()`'ya bağla** (o fonksiyon `ready` ile geziyor).
> ÜÇ parça gerekiyor ve üçüncüsü ajan sahipliğinin dışında:
>   1. `upload_thumbnail()` başarıdan sonra state'e bir damga yazmalı
>      (`youtube_thumbnail_set_at`) — bugün BÖYLE BİR ALAN YOK, yani süpürgenin
>      "kimde eksik" diye soracağı ölçüt de yok.
>   2. Süpürge, damgası olmayan projede `fix_thumbnail()` çağırır ve `captions`
>      deseniyle **koşu başına EN FAZLA BİR** projeye dokunur.
>   3. **KOTA KARARI:** `thumbnails.set` 50 birim; saatlik hatta yeni bir API
>      çağrısı eklemek, E-5'in (2.142 birim) planlandığı bir günde tavanı
>      değiştirir. Bu bütçe kararı verilmeden bağlamak, kapatılan arızanın
>      yerine "kota bitti" arızası koymak olur.
> Playlist yarısı ZATEN kapalı: `sync_project` Shorts'tan SONRA ikinci kez
> çağrılıyor (idempotent, üyeliği YouTube'dan doğruluyor).

**C-10 · [AÇIK — düşük] md5 kapısı yalnızca `audio.*`'a bakıyor.** `art.jpg` ikizi kapıya
takılmıyor; bugün tek örneği bilinen çift olduğu için zarar yok, ama iki FARKLI şarkı aynı
`art.jpg`'yi alsa iki videonun kartı **ve backdrop'ı** birebir aynı olur ve hiçbir kapı
uyarmaz. Kısmen kapalı: `stock_art.py` indirme anında kopya koruması kazandı, ama bu
yalnızca Pexels yolunu koruyor; elle kopyalanmış veya eski bir `art.jpg` kapsam dışı.
Tarif: aynı md5 bloğu `art.*` için, **UYARI seviyesinde**, ~12-15 satır.
> **Bırakıldı (2026-09-12) — ölçü gereği.** Doğrulandı: `uyumluluk.py` yalnızca
> `("audio.wav", "audio.mp3", "audio.m4a")` tarıyor. Ama B-11 aynı gün ölçtü:
> 198 medya dosyasında kopya `art.jpg` **tek çift** ve o çift zaten bilinen ses
> kopyasının kendisi — yani bugün sıfır vaka. Kapının maliyeti de sıfır değil
> (`uyumluluk.kontrol()` her render VE her yükleme öncesi çalışıyor; `art.*`
> dosyaları katalogda ses dosyalarından FAZLA). Vakası olmayan bir kapı eklemek
> bu deponun belgelenmiş hata sınıfı; asıl açık yol (elle kopyalanan `art.jpg`)
> ilk gerçek vakada kapatılmalı.

**C-11 · [KAPANDI 2026-09-12] `derleme.py` için ucuz testler.** `uret()` uçtan uca hiç test edilmemiş; ffmpeg
concat'ın testi pahalı ama `zaman_damgalari()` ve `_mmss()` saf fonksiyonlar.
> **Kapatıldı:** `tests/test_derleme_zaman_damgalari.py` (19 test). Asıl korunan
> sözleşme ÇAPRAZ: `ses_birlestir()` her komşu çiftte `acrossfade=d=GECIS_SN`
> uyguluyor, `zaman_damgalari()` aynı düşümü yapmak ZORUNDA — iki fonksiyon ayrı
> ve aralarında hiçbir bağ yok, biri değişirse YouTube bölüm işaretleri sessizce
> kayar ve bunu ancak izleyici fark eder. `derleme.py` DEĞİŞMEDİ (belge
> düzeltmesi hariç, bkz. C-14). Kırmızı/yeşil: geçiş düşümü kaldırılınca 3 test
> FAILED, geri alınınca 19/19 passed.

**C-12 · [YAPILMAYA DEĞMEZ — 2026-09-12] `gorev_sarmalayici.calistir()` betik yolunu
kök altına zorlamıyor.**
`betik = argv[1]`; mutlak yol da `..\..\x.py` de kabul edilip `runpy.run_path` ile
çalıştırılır. **İstismar edilebilir değil** — argv'nin iki kaynağı da sabit ve proje klasörü
adı komut satırına hiç girmiyor. `os.path.abspath(betik).startswith(KOK + os.sep)` iki
satır; sadece hijyen.
> **Yapılmadı, bilerek.** Kod tarafı gerçekten iki satır — ama test tarafı değil:
> `tests/test_gorev_sarmalayici.py`, `tests/test_sarmalayici_maskeleme.py` ve
> `tests/test_uretim_log_izolasyonu.py` sarmalayıcıyı **tmp_path'te üretilen
> sahte betiklerle**, yani KÖK DIŞINDAN çağırıyor — bu bilinçli bir test
> tasarımı (üretim log'larına ve gerçek betiklere dokunmamak için). Kapı
> eklenirse ~10 çağrı noktası ve üç dosya `KOK` monkeypatch'iyle yeniden
> yazılmak zorunda. Maddenin kendi ifadesi "istismar edilebilir değil — argv'nin
> iki kaynağı da sabit"; yani gerçek risk sıfır, maliyet gerçek. Bu, deponun
> belgelenmiş "fazla mühendislik" hatasının tam tarifi.

**C-13 · [KAPANDI 2026-09-12] `netlify_kontrol.py` tek ağ hıçkırığında sahte telefon
uyarısı üretiyor.** İki
GET'te de tekrar yok; tek geçici hata → sahte *"Netlify/Instagram hattı arızalı"* bildirimi.
1 satırlık tekrar susturur. Gürültü sorunu, arıza değil.
> **Kapatıldı:** `main()` içine `_get(url)` — TEK yeniden deneme (2 sn), yalnızca
> taşıma istisnası ve 5xx için; **4xx tekrarlanmıyor** (401 = süresi dolmuş
> token, tekrar sadece hız sınırını yakar). İki GET de bu yoldan geçiyor.
> SADECE BURADA güvenli, çünkü ikisi de OKUMA: aynı desen bir YAYIN çağrısına
> kopyalanmamalı (B-22).
> Kırmızı/yeşil, ölçülmüş: tek `ConnectionError` + sonra başarı senaryosunda
> HEAD'in dosyası **kod 2** (sahte alarm) veriyordu, yeni dosya **kod 0** veriyor.
> Koruma: `tests/test_netlify_tekrar.py` (6 test) — kalıcı arızanın HÂLÂ alarm
> ürettiğini de doğruluyor, yani tekrar bir maskeye dönüşmüyor.

**C-14 · [KISMEN KAPANDI 2026-09-12] Yalan söyleyen / bayatlamış yorumlar ve belgeler.** En tehlikeli dördü bugün
kapatıldı; kalanlar (bugün doğrulandı — hiçbiri fonksiyon seviyesinde bozuk değil, hepsi
BAĞLANTI/GARANTİ seviyesinde, yani grep'le görünmez):

| Nerede | İddia → Gerçek |
|---|---|
| `CLAUDE.md:637` | playlist modülü "ÜÇ katmanlı" → kendi docstring'i **DÖRT**; 4. katmanın sebebi canlı bir arıza |
| `README.md:299` | `ek_platform_backfill.KOK_SAPMALARI` → böyle bir sembol yok, gerçek ad `TELEGRAM_DJ_SAPMASI` |
| `tiktok_publish_plan.py:27` | "bekleyen 20 taslak" → **21**; bu sayı "çalışmadığını nasıl anlarız" cevabının kendisi (E-6) |
| `derlemeler/README.md:43` | "Kapak mozaik olmalı" → mozaik kodu yok; `derleme.py:487` kapağı Pexels stok fotoğrafından çektiriyor. Belge, en büyük risk dediği şeyin kodda yapıldığını gizliyor |
| `derlemeler/README.md` | "Sıralama izlenmeye göre" → SEÇİM izlenmeye, **SIRALAMA enerji eğrisine** göre; yayınlanmış videonun açıklaması da böyle diyor |
| `dj_sets/README.md:234` | "`_segments/uretim_kaydi.json` — tek dispute sigortası" → depoda **hiç yok**; eksik olarak değil, işleyen bir kural gibi sunuluyor |
| `dj_sets/README.md:104` | "**Her** sette `SUNO.md` var" → tek sonuç `Night Drive`, onda `audio.wav` bile yok; iki yayınlanmış setin tarifi kayıtsız |
| `dj_sets/README.md:259` | "bekleyen HER seti işler" → `--limit` varsayılanı **1**, belgede hiç geçmiyor |
| `dj_sets/README.md:273` | ana katalog kilidi "2 saat" → `LOCK_STALE_SECONDS` **4 saat** |
| `dj_sets/README.md:3`, `derlemeler/README.md:15` | "günlük 6 üretim" → `MIN_YAYIN_ARALIGI_SN = 52 saat`; iki belge kodun 11 Eylül'de KAPATTIĞI deseni yürürlükteymiş gibi anlatıyor |
| `suno-video-render/SKILL.md`, `README.md:16` | `generate_cover.py` "tema rengi + bokeh" → ÖNCE Pexels'ten gerçek fotoğraf; dış API bağımlılığı ve 3. taraf lisansı belgede görünmüyor |
| `suno-video-render/SKILL.md:79` | `THEMES` altı tema → **7**; listede olmayan `dj` teması DJ hattının İngilizce metin akışını tetikliyor, silen biri dili Türkçeye düşürür |
| `notify.py:18-21` | "TÜM emniyet ağları (beş kalem)" → en az beş ağ daha bağlandı (görev tanımı, kaçan koşu, git senkron, ses takip, yayın durgunluğu) |
| `youtube_stats.py:114` | "HER İKİ kök taranır" → **ÜÇ**; aynı dosya `:87` doğru yazıyor. Bu dosyanın sebebi "yanlış kümeye bakan doğru kod" arızası |
| `youtube_comments.py:17` | Yanıt "panodan onaylanarak gönderilmeli" → o panoda gönderen uç yok; gerçek yol `upload/yorum_gonder.py`. Yorum, **spam riskini yöneten insan onayı adımını** var olmayan bir panoya havale ediyor |
| `youtube_playlists.py:706` | `youtube_analytics._video_haritasi` → o modülde yok (kastedilen `_video_idler`); bu ad **başka bir modülde** gerçekten var, emsali arayan yanlış yere gider |
| `bluesky_upload.py:224` | grapheme sayacı "asla AZ saymaz" → ZWJ dalı sonraki karakteri koşulsuz atıyor; `"a"+ZWJ+"b"` gerçekte 2, fonksiyon 1 sayıyor, testi yok |
| `stock_art.py:18`, `:226` | "aynı şarkı her zaman aynı fotoğrafı alır" → indeks artık yalnızca başlangıç noktası; alaka filtresi + kopya kontrolü seçimi kaydırıyor (`:698` doğru anlatıyor) |
| `dj_hud.py:11-14` | "ekolayzer render'da gerçek sesten üretiliyor" → `ffmpeg_utils`'te `showwaves`/`showfreqs` yok |
| `saglik_kontrol.py` | "üç/dört adım" → bugün **yedi**; yeni adım ekleyen kişi bağlantıyı doğru saydığını sanır |
| `youtube_upload.py:798` | argparse "projects/ (+ dj_sets/)" → `--thumbnail-only --all` gerçekte **üç** kök |
| `CLAUDE.md:494` | `tiktok_publish_plan.py` "hiçbir yerden referans almıyor" → SKILL.md ve büyüme listesi referanslı; modül "ölü" izlenimi veriyor |
| `CLAUDE.md` Zamanlayıcı bölümü | görevler betikleri doğrudan çalıştırıyor gibi → üçü de `gorev_sarmalayici.py` üzerinden; bir görev çalışmadığında bakılacak **İLK dosya** odur ve adı kalıcı bağlam dosyasında hiç geçmiyor |
| `log_rotate.py:1` | "auto_process.log ve watch_projects.log için" → `dj_famous_process.log` de kapsamda |

**2026-09-12 akşam — tablodaki 13 satır KAPATILDI** (hepsi koddan yeniden
doğrulandı, sonra düzeltildi):

`README.md:299` + **bonus** `ek_platform_backfill.py:40` (aynı uydurma sembol adı
modülün KENDİ docstring'inde de vardı) · `tiktok_publish_plan.py:27` (20 → **21**,
sayının nereden geldiği de yazıldı) · `suno-video-render/SKILL.md:79` (`THEMES`
**7**, ve `dj` slotunun DİL akışını tetiklediği not edildi) ·
`suno-video-render/SKILL.md` + `README.md:16` (`generate_cover` → önce Pexels;
dış API bağımlılığı ve lisans artık görünür) · `notify.py` ("beş kalem" → sayma
bırakıldı, kanonik liste `saglik_kontrol.kontrol_et()`) · `youtube_stats.py:114`
("HER İKİ kök" → **ÜÇ**) · `youtube_comments.py:17` (var olmayan pano →
`upload/yorum_gonder.py`) · `youtube_playlists.py:766` (`_video_haritasi` →
`_video_idler`, yanlış emsalin nerede GERÇEKTEN olduğu da yazıldı) ·
`stock_art.py:18` + `:226` ("her zaman aynı fotoğraf" → indeks yalnızca
başlangıç noktası) · `dj_hud.py:11-14` (ekolayzer iddiası — `ffmpeg_utils`'te
`showwaves`/`showfreqs` YOK, doğrulandı) · `saglik_kontrol.py` (dört ayrı yerde
donmuş adım sayısı; artık "kanonik liste `kontrol_et()`" deniyor) ·
`youtube_upload.py` argparse (`projects/ (+ dj_sets/)` → **üç** kök) ·
`log_rotate.py:1` (`dj_famous_process.log` de kapsamda, üç çağıran yazıldı).

**`bluesky_upload.py:224` — bu satır bir BELGE değil, bir KOD hatasıydı ve öyle
kapatıldı.** ZWJ dalı bir sonraki karakteri KOŞULSUZ yutuyordu: `"a"+ZWJ+"b"`
gerçekte 2 grapheme iken **1** sayılıyordu, yani docstring'in "asla AZ saymaz"
GARANTİSİ tam ters yönde çiğneniyordu. Bedeli soyut değil: AZ sayan bir sayaç
`trim_to_graphemes()`'i "daha yer var" diye yanıltır ve Bluesky'ın **300
grapheme** sınırını AŞAN bir gönderi üretir — istek REDDEDİLİR, gönderi hiç
yayınlanmaz. Düzeltme: `_piktografik_mi()` ile lookahead (UAX#29 GB11'in
yaklaşık hâli) — ZWJ artık yalnızca bir EMOJİ yutuyor, harf/rakam yutmuyor.
Yanılma yönü bilinçli: emin olunamayan yerde FAZLA sayılıyor (fazla sayma metni
erken kırpar, az sayma gönderiyi öldürür). Koruma:
`tests/test_bluesky_grapheme.py` (35 test — aile/bayrak/gökkuşağı/ten rengi
dizileri hâlâ TEK grapheme, NFD birleşik işaretler doğru, ve garantinin kendisi
ölçülüyor). Kırmızı/yeşil: HEAD'in dosyasıyla iki ZWJ testi FAILED, düzeltmeyle
35/35 passed.

**Kapatılmayan 10 satır — hepsi DOSYA SAHİPLİĞİ dışında** (bu turda o dosyalara
yazma yetkisi yoktu; paralel ajan / kalıcı bağlam dosyaları):
`CLAUDE.md:637`, `CLAUDE.md:494`, `CLAUDE.md` Zamanlayıcı bölümü,
`derlemeler/README.md:43`, `derlemeler/README.md` ("sıralama izlenmeye göre"),
`derlemeler/README.md:15`, `dj_sets/README.md:234`, `:104`, `:259`, `:273`, `:3`.
⚠ İkisi **kodda da** vardı ve kod tarafı DÜZELTİLDİ: `derleme.py`'nin kendi
modül docstring'i de "sıralama izlenmeye göre" diyordu (gerçek: SEÇİM izlenmeye,
**SIRALAMA enerji eğrisine** — `sec()` doğru anlatıyor).

---

## 4. ÖLÇÜM VE TAKVİM

| Tarih | Ne | Not |
|---|---|---|
| **2026-10-11** | **Reporting API son tarihi** | Job kurulmadan önceki yalnızca 30 günü doldurur. 29 gün kaldı (E-2). |
| **2026-10-09** | **Kapak ölçüm randevusu** | 40 kapak 2026-09-11'de değişti; temel çizgi öncesini temiz kapsıyor. `olcum_temel_cizgi.py` aynı sorgularla yeniden çalıştırılacak. Bugün kapak etkisi hakkında **veri yok.** |
| **09-12 → 09-26** | **A/B: zamanlanmış vs anlık yayın** | Zamanlanmış 6 video medyan 28,7 izlenme/gün, anlık 12 video 8,0 (3,6 kat) — **ama 6'sı da aynı günün tek partisi ve zirve trafiğe denk geldi, ayrıştırılamıyor.** Tek yol: 2 hafta dönüşümlü yayın; 9 Ekim ölçümüne bu değişkeni sokmak bedava. |
| **10-23 … 11-06** | **İkinci ölçüm penceresi** | K-1'de Shorts kapatılırsa "4 hafta önce / 4 hafta sonra": uzun form izlenmesi + abone değişimi. |
| **~2026-12-10** | 21 Shorts'un 90 günlük eğrisi | Gecikmeli keşif var mı? K-1'deki en güçlü karşı argümanın tek testi. |
| **~2026-10-31** | Instagram token 60 günü dolar | Son yetkilendirme 09-01; E-4 yapılırsa sayaç sıfırlanır. |
| **~2026-12-09** | Facebook veri erişimi yenilemesi | Bugün tazelendi (`kalan_gun: 89`), **otomatik izleniyor** — şimdi yapılacak bir şey yok. |

**Saat seçimi:** YouTube Data API kotası Pasifik gece yarısında sıfırlanıyor = TR **10:00**
(yaz) / **11:00** (kış); log çıkarımı, panelden doğrulanmadı. Kota yoğun işler (E-5) bu
saatin hemen sonrasına.

---

## 5. BİLGİ — tekrar araştırılmasın

### Kapalı yollar

- **B-1.** Instagram API'den **medya SİLİNEMİYOR** (`IGApiException 100 / subcode 33`);
  kaldırma yalnızca uygulamadan elle. `upload/` altında DELETE yolu yok, **eklenmemeli.**
- **B-2.** YouTube Data API **Content ID itirazlarını göstermiyor** (partner olmayan kanal).
  Tek yol Studio → Kısıtlamalar; `telif_*` alanları elle tutuluyor.
- **B-3.** **Kartlar ve son ekranlar Data API v3'te YOK** — sadece Studio, araştırmaya değmez.
- **B-4.** **YouTube OAuth kapsamı daha fazla daraltılamaz:** `youtube.upload` +
  `youtube.force-ssl` (ikincisi altyazı/yorum için zorunlu). ⚠ **`yt-analytics.readonly`'yi
  `upload/token.json`'a EKLEME** — o token'ı geçersiz kılar ve **saatlik yükleme hattı
  durur**; Analytics AYRI `analytics_token.json` kullanıyor.
- **B-5.** TikTok `video.publish` scope'u **reddedildi** → elle yayın kalıcı. **Gönderi
  silme endpoint'i yok. Kapak API'den ayarlanamıyor** (telafi: `tiktok_cover_hint`).
- **B-6.** **Meta Verified reddedildi**, karar kalıcı.
- **B-7.** Analytics API `impressions`/`impressionClickThroughRate` metriklerini
  **tanımıyor** (dört denemeyle kayıtlı); CTR yalnızca Studio CSV'sinden.
- **B-8.** Facebook `pages_manage_metadata` izninin depoda **karşılığı yok** — isteyen kod
  yok, ifade yalnızca büyüme listesinin kendi maddesinde geçiyor. Kapatılabilir.
- **B-9.** `search.list` bu depoda **hiç kullanılmıyor**. **B-10.** `youtubeAnalytics v2`
  **ayrı kota havuzu** — Data API v3'ten 0 birim yiyor.

### Kota — ölçülmüş sayılar

Tek yayın **~4.150 birim** (%42); `videos.insert` ×2 = 3.200, maliyetin %91'i. Yayınsız
günlük taban **49** (%0,5), bir şarkı ASR beklerken **1.249** (%12,5). Günde en fazla **6**
`videos.insert` (pratikte 4-5). **İlk aşılan senaryo: 2 yayın + onarım kampanyası =
11.697/10.000**; DJ seti + kesit + 1 yayın kampanya olmadan bile aşar (10.506). **Kotayı
öldüren tek düğme `--count`** — `MIN_YAYIN_ARALIGI_SN = 52 saat` sayesinde elle verilmedikçe
günde en fazla 1 yeni yayın. Görev tablosunda olmayan maliyetler: `captions.download`
**200**, `thumbnails.set` **50**, `channels.list` **1**. ⚠ "Kota bitse de yüklemeler
geçiyor" diye **davranma**: 09-06'da okumalar 403 alırken iki `videos.insert` başarılı oldu,
sebebi doğrulanamadı — tek gözlem, garanti değil.

### Ölçülüp temiz çıkanlar

- **B-11.** Katalog kopya taraması bitti: 198 medya dosyası (5.269 MB) md5'lendi. Kopya ses
  **1 çift** (bilinen `Küllerimden Geç`/`Yeniden Doğacağım`), kopya `art.jpg` aynı çift.
  Kapaklar, videolar, backdrop'lar, DJ kesitleri — **hiçbirinde tekrar yok**; 0 bayt dosya
  yok, 198/198 ffprobe'dan geçti.
- **B-12.** **Kopya çiftin altyazıları YANLIŞ DEĞİL** — iki söz dosyasının farkı yalnızca
  başlıktaki açıklama notu, "Temiz Sözler" bloklarının md5'i birebir aynı;
  `find_lyrics_file()` 18/18 doğru dosyayı buluyor. Kök neden kesin: indirme hatası değil,
  bilinçli bir "yeniden markalama" (asıl = `Yeniden Doğacağım`).
- **B-13.** **Kopya video SİLİNMEMELİ:** 182 izlenme kanal ortalamasının (106,8) üzerinde,
  17 beğeni ortalamanın (2,50) **6,8 katı** — silmek iki ortalamayı da DÜŞÜRÜR; unlisted
  video zaten keşfet/öneri yüzeyinde değil; ayrıca `kopya_notu`nun dayandığı kanıt ortadan
  kalkar ve `uyumluluk.py` muafiyet mantığı ona bakıyor. **Asıl kayıt da
  gizlenmemeli/silinmemeli** (dört ayrı yer onu referans alıyor). Aynı gerekçeyle **21
  Shorts da silinmemeli/gizlenmemeli**: 1.363 izlenme + 70 dk + 22 beğeni kalıcı gider,
  ölçüm temel çizgisi karşılaştırılamaz olur, ve 21 videoyu tek seferde silmek "toplu işlem"
  deseninin kendisi.
- **B-14.** **Metinler özgün:** kısa format caption'da 18/18'de ortak satır **0**, benzerlik
  ortalaması 0,112, 21/21 benzersiz hook; şarkı sözlerinde benzerlik ortalaması 0,105;
  80 görselin hepsi benzersiz. Hashtag yasağı, dış link yasağı ve `[Verse]` sızıntısı —
  **üçü de uyuyor.**
- **B-15.** **Sızıntı temiz:** `docs/` 9 desen ailesiyle tarandı, sıfır eşleşme. Takip edilen
  dosyalarda e-posta, iç Windows yolu, IP, analytics/pixel yok. **Token dosyaları hiç commit
  edilmemiş** (geçmişte bir kez bile). Üç üretim log'unda token deseni: 0.
- **B-16.** **Komut enjeksiyonu / yol geçişi temiz:** depoda `shell=True`, `os.system(`,
  `os.popen(` **hiç yok**; dışarıdan gelen hiçbir değer komut satırına ya da `os.path.join`'e
  girmiyor; PowerShell sorguları sabit metin, tek bir yazma fiili yok.
- **B-17.** **Canlı sitede ölü/yanlış video kimliği yok:** 14/14 eşleşti, hepsi public; geri
  çekilen "Paris Street Session" hiçbir yerde yok; unlisted ve `_` önekli içerik sızmamış.
- **B-18.** **Netlify'da dosya birikmesi yok** (digest deploy eskisini otomatik düşürüyor).
  ⚠ Ama her deploy'un kalıcı permalink'i var ve kod eskileri hiç silmiyor — videolar
  markasız bir `netlify.app` adresinde de durabiliyor. Gizlilik sızıntısı değil.
- **B-19.** **CRLF hipotezi çürüdü:** 115 değişmiş dosyanın hiçbiri "sadece satır sonu
  gürültüsü" değil; `core.autocrlf=true` commit'te normalize ediyor. **Ayrı satır sonu
  commit'ine gerek yok.**
- **B-20.** **Tek bir bozuk `state.json` KANALI DURDURMAZ** — tam olarak 2 projeyi durdurur
  (kendisi + md5 ikizi), kalan 20'ye yalnızca uyarı yazar. Kanalın tamamını durduran tek şey
  `uyumluluk.py`'nin kendisinin bozulmasıdır ve her giriş noktası onu ayrı ayrı yakalıyor.
- **B-21.** **Kapı maliyeti ihmal edilebilir:** 22 proje tam tarama **0,492 sn**; md5
  yalnızca tek çift için hesaplanıyor.
- **B-22.** **`ag_yeniden_deneme` doğru bağlanmış; toptan yayılması GEREKMİYOR.** YouTube
  altyazı/playlist/ölçüm/yorum modülleri süpürge tarafından bir sonraki saatte zaten
  tekrarlanıyor ve korumasız olmalarının ölçülebilir bedeli hiç olmadı; jitter da gereksiz.
  **Çift yayın riski taşıyan çağrılara "sadece tekrar dene" EKLENMEMELİ:** Telegram
  `sendVideo`, Bluesky `createRecord`, Facebook `/videos` ve `/comments`, Instagram
  `media_publish`, YouTube `videos.insert` ve `comments.insert`.
- **B-23.** `dj_clips` **YAYIN tarafı üretimde hâlâ hiç çalışmadı** (doğrulandı) — kesit
  kota tahmini (~1.650 birim) teorik.
- **B-24.** **Shorts uzun forma trafik TAŞIMIYOR** (r = 0,135). **Başlık uzunluğunu optimize
  etmeye çalışma:** 18 şarkıda r = −0,507 görünüyor ama 5 Eylül toplu yüklemesi çıkarılınca
  işaret **ters dönüyor** (+0,261) — örüntü değil, gürültü.
- **B-25.** **Gürültü tabanı:** içerik farkı SIFIR olan kopya çiftte izlenme farkı %25,
  beğeni farkı 6,3 kat. **Tek bir videonun %25 daha çok izlenmesi hiçbir şey anlatmıyor.**
- **B-26.** **DJ setleri tezi DOĞRULANDI** (gerçek Analytics verisiyle): 2 set 28 günde
  **1.377 dk** izlenme süresi üretti, 18 şarkı 1.521 dk. Video başına 688 vs 84 dk =
  **8,2 kat**; izlenme başına 9,63 vs 0,84 dk = **11,5 kat**. Yan kanıt: TV izlenmenin
  %17'si ama izlenme süresinin **%62,6'sı**.

  **DÜZELTME (2026-09-12, aynı gün):** bu maddenin ilk hâli "Suno kotası başına set
  üretmek ~12 kat verimli" diyordu — **YANLIŞ BÖLME.** 8,2 kat *video* başına. Kota
  başına bölünce avantaj KAYBOLUYOR: bir set `dj_sets/Night Drive/SUNO.md`'ye göre
  **12-16 indirme** tüketiyor, yani indirme başına 43-57 dk; tekil şarkı 84,5 dk
  (1.521 / 18). Yani **kota başına şarkı DAHA verimli**, set değil.

  Karar yine de set lehine ayakta kalıyor ama gerekçesi farklı: belirleyici değişken
  kota değil **video sayısı** — az sayıda uzun video, "toplu üretilmiş AI içerik"
  sinyalini düşürüyor (bkz. ozgunluk_riski bulguları). Sonuç kural: set yapılacaksa
  **12 parça, 16 değil** (45-60 dk).
- **B-27.** `watch_projects.py`'ye md5 kontrolü **eklemeye gerek yok** — kopya, diske
  düştüğü anda değil render/yükleme anında durdurulmalı; render kapısı zaten yayına giden
  tek boğaz ve HATA seviyesinde.
- **B-28.** **Sarmalayıcıyı kurmadan önce düzeltilmesi gereken güvenlik açığı YOK.** Güvenlik
  denetimi: Yüksek 0 · Orta 0 · Düşük 2 · Bilgi 2 — düşüklerin ikisi de ya bugün kapatıldı
  ya hijyen sınıfında (C-12).
- **B-29.** `marka/facebook_metinleri.txt` bozukluğunun kaynağı bulundu (bir `.join()`
  çağrısının argümanları ters çevrilmişti) ve **dosya bugün düzeltildi**; o desen hiçbir
  çalışan kodda yok ve başka hiçbir üretilmiş metni bozmamış (49 dosya tarandı).

- **B-30.** **`query_from_lyrics()` sözler dosyasının TAMAMINI okuyor**, "## Temiz Sözler"
  bölümünü değil — yani başlıktaki açıklama notları, `## Stil Etiketi` bloğundaki İNGİLİZCE
  etiket ve analiz tabloları da anahtar kelime sayımına giriyor. Bugün ölçüldü: 19 şarkının
  **2'sinde** sonuç değişiyor (`Kader Ortakları` night → city skyline, `Kırık Zincir`
  railway terimini kaybediyor), 17'sinde fark yok. Zarar sessiz: yanlış terim hiçbir istisna
  atmaz, hiçbir log satırı bırakmaz — sadece kapak şarkının konusundan kopar.
  **Bugün DÜZELTİLMEDİ, çünkü ölçüm kapatmayı haklı çıkarmıyor:** iki şarkı da yayında ve
  kapakları yerinde; düzeltme ancak yeniden render edilirlerse etkir. Ama oran ZAMANLA
  KÖTÜLEŞİR: sözler dosyaları belgelendikçe şiirin payı düşüyor — `Son Kez` %24, `Kader
  Ortakları` %24, bugün yazılan `Sabah Senin` **%8**. Düzeltme tek satır ve hazır bir
  fonksiyonu var (`caption_align.extract_clean_lyrics()`); karar: yeni bir şarkıda fark
  üretirse o an kapatılsın.
- **B-31.** **Sıklık kuralı başlığın çapasını ezebiliyor.** `keywords_from_lyrics()` en sık
  geçen 2 imgeyi alır (`MAX_LYRIC_TERMS`); gerekçe "şarkının merkezindeki imge en çok
  tekrar eder" ve genelde doğru. `Sabah Senin`de tersine döndü: temiz sözlerde gece 4,
  karanlık 4, ışık 3 → sorgu **"dark dramatic moody night darkness"**, yani adı "Sabah
  Senin" olan ve nakaratı sabahı devreden bir şarkıya GECE kapağı. Sözlükte `sunrise`
  var ama anahtarları `şafak/safak/gün doğ/seher` — sözlerde 9 kez geçen **"sabah" hiç
  eşleşmiyor**. Ölçüldü: `sunrise`a "sabah"+"ağar" eklenirse katalogda **3 şarkı** değişir
  (`Sabah Senin`, `Kader Ortakları`, `Son Kez` — son ikisi yayında), ve tuzak gerçek:
  "sabaha kadar" bir GECE deyimidir, `Sabaha Kadar` adlı elektronik şarkıda 16 kez geçiyor.
  **Sözlük DEĞİŞTİRİLMEDİ.** Bu şarkı için tasarımın kendi çıkış kapısı kullanıldı:
  `meta.json`'a `art_query` yazıldı (öncelik 1, 19 şarkının zaten 4'ünde var).

### Ölçülemeyenler (varsayım olarak kayıtlı)

Google Cloud kota **paneli** görülemedi (tavan 10.000 varsayıldı; yükseltme verilmişse tablo
iyi yönde yanılıyor). Kota sıfırlanma saati log'dan çıkarıldı. `videos.insert`'in başarısız
chunk tekrarlarının kotayı çarpıp çarpmadığı **tespit edilemez**. 09-06'da kotayı bitiren
gerçek harcama log rotasyonu yüzünden **doğrulanamaz**. TikTok'ta AI etiketinin açılıp
açılmadığı **kayıtta yoktu** (bugün `tiktok_published_at`/`tiktok_dogrulandi` alanları
eklendi, bundan sonra ölçülebilir). **Diğer platformların performansı ölçülemiyor** —
`state.json` onlar için yalnızca kimlik ve zaman damgası tutuyor; performans raporunun
tamamı YouTube'a dayanıyor. **YPP 4.000 saat eşiğinin Shorts'u sayıp saymadığı
doğrulanamadı** — K-1 kararı buna dayandırılacaksa Studio'dan elle teyit edilmeli. GitHub
Pages kaynak dalı, HTTPS ayarı, DNS ve Netlify'da birikmiş deploy sayısı yalnızca canlı
panelden görülür.

---

## Bugün ne yapıldı (2026-09-12) — bağlam

Yukarıdaki liste, **zaten yapılmış olanların üstüne** kalandır.
**13 arıza kapatıldı · test sayısı 743 → 961 · 29 commit.** Hepsi bu belge yazılırken kodda
yeniden doğrulandı:

1. **Ana yayın hattındaki fail-open politika kapısı** — `uyumluluk.kontrol()`'ün KENDİSİ
   istisna fırlatırsa akış devam ediyor ve yükleme yapılıyordu; kapı sessizce AÇILIYORDU.
   Artık fail-closed (`auto_process`, `dj_famous_process`, `validate_project`).
2. **`upload/set_privacy.py` AI beyanını siliyordu** — `part="status"` + gövdede sadece
   `privacyStatus` → `containsSyntheticMedia: True` her çalıştırmada sessizce siliniyordu ve
   `videos.list` bu alanı döndürmediği için tespit edilemiyordu. Artık mevcut `status`
   okunup üzerine yazılıyor, beyan her yazımda açıkça yeniden set ediliyor.
3. **Geri doldurma süpürgelerine politika kapısı bağlandı** (Telegram/Bluesky + Facebook),
   ikisi de fail-closed; engellenen proje kotayı tüketmiyor.
4. **DJ kesit yayın yoluna politika kapısı eklendi** — bu yol `process_set()`'in dışından
   koştuğu için oradaki kapıya hiç uğramıyordu.
5. **`gorev_izleri/*.log` maskeleyiciye bağlandı** — sarmalayıcı, token maskeleme hattının
   DIŞINDA üçüncü bir log ailesi yazıyordu.
6. **Instagram `_graph_istek`'e geçici 5xx yeniden denemesi** (`is_transient` şartıyla,
   4xx'e dokunmadan) — golden-hour pencere kenarında kaçan yayınları kurtarıyor.
7. **`saglik_kontrol`'e yedinci adım: `yayin_durgunlugu`** — altı adımın hiçbiri "en son ne
   zaman bir şey yayınlandı" diye sormuyordu; kapı kapalı KALSA bile kimse görmüyordu.
8. **TikTok yayın planı araçları çalışır hâle geldi** — politika kapısı, ikiz kapısı,
   `--yayinlandi`/`--dogrulandi`/`--yayinlandi-hepsi`, cp1254 emoji düzeltmesi.
9. **`.gitignore` kapatıldı** — kişi fotoğrafları, telif işaretli 3. taraf ses kesitleri,
   913 MB'lık telifsiz ham set, `derlemeler/` kökü (1,4 GB), DJ backdrop videosu, marka
   MP4'leri, izleyici verisi taşıyan yorum kuyruğu. Bunlar olmadan `git add -A` hem gizlilik
   ihlali olurdu hem GitHub'ın 100 MB sınırında reddedilirdi.
10. **`derleme.adaylar()`'ın telif kapısına test yazıldı.**
11. **DJ kesidi playlist zincirine bağlandı** — "20 Shorts'un hiçbiri playlist'e girmemişti"
    arızasının aynı deseni, bu kez bedeli ödenmeden kapatıldı.
12. **`marka/facebook_metinleri.txt` düzeltildi** (içerik uydurulmadı, tekrar temizlendi).
13. **`ag_yeniden_deneme.py`'nin yanlış docstring'i düzeltildi** ve `.example` kimlik
    dosyaları artık git'te izleniyor.

**Bilerek yapılmayanlar:** hiçbir platforma dokunulmadı, hiçbir video silinmedi/gizlenmedi,
ağ çağrısı yapılmadı, token dosyası açılmadı, Görev Zamanlayıcı'ya fiil uygulanmadı.
