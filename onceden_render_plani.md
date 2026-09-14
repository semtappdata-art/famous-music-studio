# Önceden render planı: haftanın şarkılarını toptan hazırlayıp plana göre yayınlamak

> Yazıldığı an: **2026-09-12**. Bu çalışma **salt okunur**: render, yükleme, Suno, ffmpeg ya da ağ
> yazması yapılmadı, kod değişmedi. Kanıtlar `dosya:satır` olarak verildi. Ölçümler
> `uretim_hazirlik_suresi.md` ve `auto_process.log` kayıtlarından alındı. İnternetten doğrulananların
> kaynağı §7'de.
> **"doğrulanmadı"** yazan her madde ne ölçüldü ne de resmî kaynaktan teyit edildi.

## 0. Kısa sonuç

- **Yapılabilir, ama bugünkü kod bunu yapmıyor.** Render yayın temposu kapısının **arkasında**
  duruyor. Ses dosyası gelse bile render, 52 saatlik taban açılana kadar bekliyor.
- **Asıl kazanç zaman değil, önizleme.** Render şarkı başına 4-8 dk sürüyor, darboğaz o değil.
  Son 7 günde 14 golden-hour penceresinin **hiçbiri** makine kapalı olduğu için kaçmadı. Önceden
  render etmenin gerçek değeri başka: kapak/video, YouTube'a gitmeden **günler önce** görülür.
  `Bu Gece Kazandık` vakası tam olarak bu fırsatın kaçmasıydı.
- **"YouTube/Facebook'a günler önceden zamanlı yükleme" (B) teknik olarak mümkün**, ama pahalı ve
  riskli. Kazancı ölçülen verilere göre ~0 pencere. Instagram, Telegram, Bluesky ve TikTok yine
  makineye ya da insana bağlı kalıyor. Yüklenmiş bir videonun dosyası da değiştirilemiyor.
- **Öneri: A+ (önce render + Telegram önizlemesi + onay bekletmesi).** Yayın zamanlaması bugünkü
  gibi kalıyor. B, ancak haftalık hacim 3 şarkıya çıkarsa yeniden değerlendirilmeli.
- **Belgelerdeki kota hesabı eskimiş.** `videos.insert` artık **1 birim**, kendi kovasında ve
  günde 100 çağrı sınırıyla çalışıyor (resmî revizyon geçmişi: 4 Ara 2025 ~1600→~100, 1 Haz 2026
  ayrı kova). `haftalik_is_akisi.md:63-65`, `denetim_bulgulari_2026-09-12.md:1030` ve
  `dj_tarama_kontrol.py:74`'teki "tek yayın ~4.150 birim, `videos.insert` ×2 = 3.200" hesabı artık
  geçerli değil. Bu belge onları değiştirmedi; ayrı bir düzeltme işi.

---

## 1. Bugünkü mimari destekliyor mu?

| Soru | Cevap | Kanıt |
|---|---|---|
| `process_project` render ile yüklemeyi aynı adımda mı yapıyor? | **Evet.** Kapak → `_is_rendered` değilse render → uyumluluk "yukleme" kapısı → YouTube → Shorts → TikTok → IG → FB/TG/BS, hepsi tek fonksiyonda | `auto_process.py:969-1174` (render 978-989, kapı 1024-1044, yüklemeler 1062-1174) |
| `_auto_pace_count` render'ı da bekletiyor mu? | **Evet.** `process_project` yalnızca `count>0` olunca ve yalnızca `batch = pending[:count]` için çağrılıyor. `count==0` iken koşu drain yapıp dönüyor; render hiç denenmiyor | `auto_process.py:1618-1641` |
| Bekletilen (`yayin_beklet`) proje render ediliyor mu? | **Hayır**, `_bekletilenleri_ayir` onu `pending`'den çıkarıyor. Uyumluluk kapısı ise render aşamasında bekletmeyi yalnız UYARI sayıyor, yani önceden render ile çelişmiyor | `auto_process.py:1601-1606`, `uyumluluk.py:296-305` |
| `watch_projects` ses gelince ne tetikliyor? | Başka adla inen sesi `audio.*` yapıyor ve `auto_process.py`'yi kopuk süreçle başlatıyor. Başlayan koşu **aynı tempo kapısından** geçiyor, yani kapı kapalıysa izleyici tetiklemesi de render üretmiyor. Dosya doğrudan `audio.wav` adıyla konursa izleyici tetiklemiyor | `watch_projects.py:380-427`, `:268-372` |
| Kuyruk başı tıkanması (`pending[:1]`) render'ı da tıkıyor mu? | **Evet**, bugün render de yayın da aynı dilimde | `auto_process.py:491`, `:1636` |
| `_is_rendered` / `video_butun_mu` hazır videoyu doğru tanıyor mu? | **Bütünlüğü doğru tanıyor**: 0 bayt, ffprobe süresi, yarım mp4. **Tazeliği tanımıyor**: kapak/art sonradan değişirse eski mp4 "hazır" sayılıyor ve render tekrarlanmıyor. Reddedilen önizlemede `output/*.mp4` silinmeli | `auto_process.py:252-275`, `render.py:38-112` (mtime karşılaştırması yok) |
| Render uzun sürerse kilit ya da görev limiti sorun olur mu? | Hayır. Render en kötü 6,6 dk; `LOCK_STALE_SECONDS` 4 sa, saatlik görevin limiti 2 sa | `auto_process.py:93`, ölçüm R-6 |

**"Render şimdi, yayın sonra" için gereken değişiklik:** `main()`'e tempo kapısından **bağımsız**
bir hazırlama adımı. Adım `pending` ile bekletilenlerin birleşiminde, **henüz `youtube_video_id`'si
olmayan** ve `_is_rendered` False dönen projeleri `generate_cover.generate` +
`render_module.render_project` ile hazırlar. Yayın bugünkü gibi `_auto_pace_count` ve golden-hour
kapısında kalır. Adımın yeri önemli:

- Bugün `count==0` dalı (`:1618-1628`) ve `batch` döngüsü (`:1636-1642`) iki ayrı çıkış.
- Adım **ikisinde de** drain'den SONRA çağrılmalı. Böylece golden-hour içindeki bir IG yayını,
  render yüzünden 5-8 dk gecikmez.
- Koşu başına 1 render ile sınırlanmalı. Haftanın 3-4 şarkısı arka arkaya gelen izleyici
  tetiklemeleriyle zaten bir saat içinde biter.
- `if not pending:` erken dönüşü (`:1607-1610`) etkilenmez, çünkü orada render edilecek proje yok.

---

## 2. Platform platform önceden zamanlama

| Platform | Önceden zamanlama | Bugünkü kod | Önceden hazırlığa etkisi |
|---|---|---|---|
| **YouTube** | `private` + `publishAt` ile günler öncesinden yüklenebilir. Resmî belgede ileri tarih sınırı **yok** (azami süre **doğrulanmadı**). Yalnız hiç yayınlanmamış videoda geçerli | `_compute_publish_at` yalnız **bir sonraki** pencereyi hesaplıyor (`upload/youtube_upload.py:484-494`, `config.py:600-618`). İleri tarih için bir "en erken an" parametresi gerekir. `_golden_publish_at(gun_ertele)` benzer bir desen olarak zaten var (`:552-570`) | B seçeneğinde kullanılabilir. Riskleri aşağıda |
| **Facebook** | Reels: **10 dk ile 29 gün** arası (resmî doküman). Kodun yorumu da "10 dk - 29 gün" diyor | `_compute_scheduled_time` yalnız bir sonraki pencereyi hesaplıyor (`upload/facebook_upload.py:248-282`), alt pay 15 dk (`:72-79`) | B'de haftalık zamanlama sınırın çok içinde kalıyor |
| **Instagram** | Native zamanlama yok. Konteyner 23 saatte bayatlıyor | `KONTEYNER_OMRU_SN = 23*3600` (`upload/instagram_upload.py:46`). Konteyner yüklemede açılıyor, pencere dışındaysa kuyruğa giriyor (`:596-605`) | **Önceden hazırlanamaz.** Konteyner en fazla ~23 sa önce açılabilir ve yayın anında makine açık olmalı. B'de IG yüklemesi tempo kapısında kalmak **zorunda** |
| **Telegram / Bluesky** | Zamanlama yok | `_ek_platformlari_isle` TG/BS'yi **anında** gönderiyor (`auto_process.py:1161-1209`, `zamanlama_destegi=False`). Geri doldurma golden-hour'u bekliyor (`upload/ek_platform_backfill.py:422`) | **A'da sızıntı yok**: yükleme yine tempo kapısında, bugünkü R-4 davranışı değişmiyor. **B'de sızıntı var**: `eksik_projeler` yalnız `youtube_privacy`'ye bakıyor (`ek_platform_backfill.py:235`, `facebook_backfill.py:108`). Zamanlı yüklemede bu alan yine `"public"` yazılıyor (`youtube_upload.py:517-522`), yani geri doldurma şarkıyı YouTube public olmadan **günler önce** TG/BS/FB'ye çıkarır. `latest_release._yayinda_mi` / `_already_live` (`latest_release.py:77-117`) bu kontrolü yapıyor; geri doldurmalarda yok |
| **TikTok** | API'de zamanlama yok; taslak elle yayınlanıyor | Taslak yükleme sırasında gidiyor (`upload/tiktok_upload.py:94-168`), hatırlatma golden-hour'da (`auto_process.py:941-942`) | Etkisiz. Önceden hazırlık taslağı öne çekmez; Perşembe dağıtım vardiyası aynı kalır |

### YouTube'u önceden yüklemenin riskleri (B için)

- **Dosya değiştirilemez.** Kapak `thumbnails.set` ile değişebilir, ama video karesindeki kart
  ya da açılış kapağı yanlışsa (Bu Gece Kazandık vakası) tek yol silip yeniden yüklemek. İnsan gözü
  **yüklemeden önce** olmalı.
- **Otomatik altyazı:** ASR'nin private videoda da üretildiği **doğrulanmadı**.
  `_drain_golden_hour_queue` koşu başına tek proje deniyor (R-2); bekleyen zamanlı videolar bu
  slotu tüketir.
- **Playlist:** `sync_project` private videoyu listeye ekler. Public olana kadar görünmeyeceği
  varsayılıyor (**doğrulanmadı**).
- **md5 kapısı:** yükleme öncesi HATA. Önceden render ile bu hata yayın günü yerine indirme günü
  görülür. Bu bir artı. Aynı klasöre iki varyant koymak yine HATA
  (`haftalik_is_akisi.md` §2 adım 11).
- **`youtube_privacy` sözleşmesi:** alan istenen gizliliği tutuyor. B'de "istenen public, gerçek
  private" durumu günlerce sürer. Kayma dedektörü bunu **zaten istisna sayıyor**: `private` +
  gelecekteki `*_publish_at` kayma değil (`saglik_kontrol.py:1727-1732`). Bio sayfası da gelecekteki
  `publish_at`'i yayında saymıyor (`latest_release.py:77-96`). Açık kalan tek delik geri doldurmalar
  (yukarıdaki tablo).
- **Tempo sayacı zincire uyuyor:** `_son_yeni_yayin_ani` gelecekteki public anını da alıyor ve
  "o andan itibaren 52 sa" bekletiyor (`auto_process.py:427-454`, `:506-511`). Zincirleme zamanlama
  bu yüzden sayacı bozmaz. Bugünkü kod ise yüklemenin **kendisini** bekletiyor, zinciri kuramıyor.
- **İç "toplu üretim" uyarısı:** aynı gün `youtube_uploaded_at`'i dolu 3 proje
  `GUNLUK_YUKLEME_UYARI = 3` eşiğini tetikler (`uyumluluk.py:119`, `:501-528`). Yalnız UYARI verir,
  ama tam olarak B'nin ürettiği desen.
- **Kota:** `videos.insert` 1 birim, ayrı kovada, günde 100 çağrı (resmî). Haftanın 4 şarkısı
  × (uzun + Shorts) = 8 çağrı, sınırın çok altında. Ortak 10.000'lik havuzdan `thumbnails.set` 50,
  `playlistItems.insert` 50, `captions.list` 50 harcanıyor. Denetimdeki ölçümden türetilen değer
  yayın başına ~950 birim (4.150 − eski 2×1.600), 4 şarkı tek günde ~3,8 bin birim. **Tavan
  aşılmaz.** Yeni maliyetle şarkı başı gerçek toplam ayrıca ölçülmedi (**doğrulanmadı**).

---

## 3. Kazanç gerçekte nerede?

| Kalem | Ölçüm | Önceden render etkisi |
|---|---|---|
| Render süresi | medyan 257 sn, en kötü 310 sn; yeni biçim ölçülmedi (`uretim_hazirlik_suresi.md` §1-5a/5c) | Darboğaz değil. Yayın anını değiştirmez |
| Tempo beklemesi | 52 sa taban + ~1 sa kayma; kuyruk başında ~26 sa medyan | **Hiç değişmez** (kural) |
| Makine kapalı saatler | Saatlerin %25'i; `WakeToRun=False` | Pencere kaybına pek dönüşmüyor, aşağıya bakın |
| **Golden-hour pencere kapsaması (7 gün, bu çalışmada log'dan sayıldı)** | Öğle (12-14) **7/7** gün en az bir koşu (12 Eyl'de yalnız 13:xx). Akşam (18-22) **7/7** gün (08 ve 09 Eyl'de 18:xx yok, 19-21 var) | **Kaçan pencere: 0/14.** B'nin "makine kapalıyken pencereyi kurtarır" kazancı bu haftada **0** |
| Kapının gece açılması | Kapı 02:05'te açılırsa iş sabahki ilk koşuya kalıyor; YouTube yine `publishAt` ile pencereyi tutuyor | B yalnız YouTube/FB için bu gecikmeyi kaldırır; ölçülen etkisi yok |
| Hata ve görsel sorunların görülme anı | Bugün: yükleme anı (render ile aynı koşu). Bu Gece Kazandık YouTube'a eski görselle çıktı, 4 gün sonra fark edildi | **A: indirme günü.** Asıl kazanç bu |
| Kuyruk başı tıkanması (R-1) | 1-52 sa | A render'ı tıkanmadan kurtarır. Yayın tıkanması aynı kalır (ayrı düzeltme) |

**B'de bile makineye bağlı kalanlar:** Instagram (konteyner ≤23 sa, yayın anında makine açık),
Telegram/Bluesky (gönderim anında makine açık) ve altyazı hizalama. TikTok ise elle.

**Hacim notu:** `haftalik_is_akisi.md` §1 varsayılanı **haftada 1 şarkı**. Tek şarkıda "haftayı
toptan render et" ile "indirildiği gün render et" aynı şey. Toptan hazırlığın anlamı ancak 2-3
şarkılık haftalarda doğar.

---

## 4. Riskler

| Risk | Değerlendirme |
|---|---|
| **"Toplu üretilmiş AI içerik"** | Resmî politika içeriğin "mass-produced, generic, repetitive" olmamasını istiyor. **Yükleme sıklığından ya da zamanlamadan söz etmiyor** (support.google.com/youtube/answer/1311392). Tek günde çok sayıda **private** yüklemenin bir sinyal olup olmadığı resmî kaynakta yok: **doğrulanmadı.** İzleyicinin gördüğü desen public anı olduğu için A bunu hiç değiştirmez. B'de yükleme deseni değişir ama public deseni aynı kalır. Kanal çapında yaptırım var (Ocak 2026 YPP süpürmesi, ikincil kaynak), bu yüzden temkin B'ye karşı |
| **md5 kapısı** | Aynı klasöre iki varyant = HATA. Önceden render bunu öne çeker, zararı yok. Haftalık toplu indirmede aynı varyantın iki klasöre konma olasılığı artar; hata yayından önce görünür |
| **Bekletme ve görünürlük planı** | A'nın önizleme adımı `yayin_beklet`'i kullanır; kapı fail-closed ve yedi yayın yolunu tek yerden kapatıyor (`uyumluluk.py:282-305`). **Tuzak:** bekletme kalkınca proje klasör `getctime` sırasıyla kuyruğa döner (`auto_process.py:286-310`), onay sırası yayın sırasını değiştirmez. Görünürlük planı yalnız yayınlanmış projelere dokunuyor (`:773-900`), etkileşim yok |
| **Kuyruk başı tıkanması** | A'nın hazırlama adımı `pending[:1]` yerine bütün listeyi gezmeli, yoksa R-1 önizlemeyi de geciktirir. Yayındaki R-1 olduğu gibi kalır |
| **Tazelik** | Önizleme reddedilince `video_butun_mu` eski mp4'ü "bütün" sayar. Ret komutu `output/youtube_16x9.mp4` + `shorts_9x16.mp4`'ü silmeli; kapak da değişecekse `cover*.png` da silinmeli |
| **Onaysız bekleyen şarkı** | Önizleme bekletmesi unutulursa şarkı sessizce bekler. `yayin_durgunlugu`'nun bekletilen projeyi "bekleyen" sayıp saymadığı **doğrulanmadı**. 24 sa sonra bir kez hatırlatma bildirimi gerekir |
| **Yayın kanalına sızma** | Önizleme görselleri **operatör** sohbetine gitmeli. `notify._telegram_ayari` yayın kanalı ile bildirim sohbeti aynıysa Telegram'ı kapatıyor (`notify.py:145-175`); önizleme bu kapıyı yeniden kullanmalı |
| **B'ye özgü** | Geri doldurma sızıntısı (§2), yüklenmiş videoyu geri alamamak, iç günlük uyarı eşiği, deponun "bağlantı seviyesinde sessiz arıza" geçmişi (CLAUDE.md) |

---

## 5. Seçenekler

| | **A+ — Önce render + önizleme** (önerilen) | **B — Önce render + YouTube/FB native zamanlı yükleme** | **C — Kod yok, işleyiş düzeni** |
|---|---|---|---|
| **Ne değişir** | `auto_process.main()`: yeni `_onceden_hazirla(projeler, limit=1)`, `count==0` dalında ve batch döngüsünden sonra, drain'den SONRA. Yeni `onizleme.py`: görselleri gönderir, `yayin_beklet={"sebep":"önizleme onayı bekliyor","tur":"onizleme",...}` yazar (`state_io`), `onayla` / `reddet` komutları. `notify.py`: `sendPhoto`/`sendMediaGroup` desteği (depoda hiç yok) | A+'ya ek: `youtube_upload._compute_publish_at(en_erken=...)`; `auto_process._auto_pace_count` ve `main`'de "yükleme kapısı" ile "yayın anı" ayrımı (slot = `son_yeni_yayin_ani + 52 sa`'ten sonraki ilk pencere); `facebook_upload._compute_scheduled_time` ileri tarih; `_ek_platformlari_isle`, `ek_platform_backfill.eksik_projeler`, `facebook_backfill.eksik_projeler` için ortak "YouTube public anı geçti mi" kapısı (`latest_release._already_live` ortak modüle); IG konteyneri slot −23 sa'ten önce açılmamalı | Hiçbir dosya. `haftalik_is_akisi.md`: yayın günlerinde makine 12:00-13:15 ve 18:00-19:15 açık; ses hedef pencereden ≥1 gün önce; §2 adım 13'teki mp4 izleme kontrolü korunur |
| **Kazanç** | Görsel/render hatası indirme günü görülür; YouTube'a yanlış görsel gitmez; md5/validate hataları öne çekilir; R-1 render'ı tıkamaz | A+'nın hepsi + YouTube/FB public anı makineden bağımsız. Ölçülen kurtarılan pencere: **0/14** | Kod riski yok. Pencere kapsaması zaten 14/14 |
| **Maliyet** | Orta-küçük: ~3 dosya, ~150-200 satır; 5-7 test (hazırlamanın tempo kapısını beklemediği, drain'den sonra geldiği için `ast` sırası, önizleme bekletmesinin yüklemeyi durdurduğu, reddin mp4'leri sildiği, yayın kanalı kapısı) | Büyük: ~7 dosya, ~350+ satır, 10+ test. Deponun en sık arıza sınıfına (bağlantı) en açık seçenek | ~0 |
| **Yine elle / makineye bağlı** | IG, TG/BS, altyazı, YouTube yüklemesi (bugünkü gibi); TikTok elle; onay elle | IG, TG/BS, altyazı; TikTok elle; onay elle | Hepsi bugünkü gibi; görsel kontrolü yükleme sonrası |

### Seçim: **A+**

1. Kullanıcının bugün yaşadığı gerçek bedel (Bu Gece Kazandık) **zaman değil, geri alınamaz
   yükleme**. A+ tam onu kapatıyor, B ise yüklemeyi daha da öne çekip riski büyütüyor.
2. B'nin tek ek kazancı olan pencere kurtarma ölçülen haftada **0**. Maliyeti ise en az iki kat ve
   yeni bir sızıntı yolu açıyor (geri doldurmalar).
3. Varsayılan hacim haftada 1 şarkı. Toptan zamanlamanın getirisi bu hacimde çok düşük.
4. A+ yayın desenini hiç değiştirmiyor, yani "inauthentic content" riskine dokunmuyor.

**B'yi yeniden aç, eğer:** haftalık hacim 3 şarkıya çıkarsa **ve** makine kapalılığı 4 hafta
içinde en az bir golden-hour penceresini gerçekten kaçırırsa (log sayımı: §3'teki yöntem). O zaman
bile yalnız YouTube kısmıyla, geri doldurma kapısı ÖNCE eklenerek.

---

## 6. Önizleme adımı: nasıl eklenir

```
ses indi → watch_projects tetikler → auto_process
  → (drain, yayın kapısı: değişmedi)
  → _onceden_hazirla: youtube_video_id YOK + _is_rendered False olan ilk proje
       generate_cover → render_project → onizleme.gonder(proje)
         · yayin_beklet = {"sebep": "önizleme onayı bekliyor", "tur": "onizleme", "istendi_at": ...}
         · Telegram operatör sohbetine: cover.png, cover_vertical.png,
           youtube_16x9.mp4'ün 0. saniye (açılış kapağı) + ~%40 karesi, shorts'un bir karesi
           (ffmpeg -ss ... -frames:v 1 → geçici jpg → sendMediaGroup → geçici dosya silinir)
         · Telegram yoksa/kapalıysa: ntfy'ye metin + klasör yolu (görsel yok)
kullanıcı → python onizleme.py onayla "<Proje>"   → bekletme silinir, kuyruğa normal girer
          → python onizleme.py reddet "<Proje>" [--kapak]
                → output/*.mp4 (+ istenirse cover*.png) silinir, bekletme KALIR,
                  bir sonraki koşu yeniden render edip yeniden gönderir
```

- Onay komutu yalnız `tur == "onizleme"` olan bekletmeyi silmeli. Bu Gece Kazandık'taki gibi elle
  konmuş bekletmelere dokunmamalı.
- Telegram'da düğmeli onay (`getUpdates` yoklaması) ikinci aşama olabilir. İlk sürümde komut
  satırı yeterli ve test edilebilir.
- Hatırlatma: bekletme 24 sa'ten eskiyse günde bir bildirim (`notify.uyar_bir_kez` deseni).

---

## 7. Sonraki oturum: ajan iş listesi (A+)

Dosya sahipliği tek ajanda kalmalı: `auto_process.py` + `onizleme.py` + `notify.py` + testler.

1. **Keşif (salt okunur):** `yayin_durgunlugu` ve `haftalik_gozden_gecirme` bekletilen projeyi
   nasıl sayıyor, `uyumluluk.kontrol(..., "render")` md5'te HATA mı UYARI mı veriyor
   (`uyumluluk.py:316-480`), `validate_project` Pexels'e ağ çağrısı yapıyor mu. Üçü de bu çalışmada
   **doğrulanmadı.**
2. `notify.py`: `gorsel_gonder(baslik, dosyalar)` fonksiyonu. `_telegram_ayari` kapısını kullanır,
   `sendMediaGroup`, gövde UTF-8. Test: yayın kanalı id'sinde istek atılmıyor.
3. `onizleme.py`: `gonder` / `onayla` / `reddet` / `durum`, state yazımı `state_io` ile. Kareler
   `%TEMP%` altında üretilip siliniyor.
4. `auto_process.py`: `_onceden_hazirla` fonksiyonu, iki çağrı noktası (drain'den sonra), koşu başına
   1 render, `youtube_video_id` olan projeye asla dokunmuyor, bekletilenler dahil (render aşaması
   bekletmeyi yalnız uyarı sayıyor).
5. Testler: hazırlığın `_auto_pace_count` 0 dönerken de çalıştığı; çağrının drain'den sonra
   geldiği (`ast` satır sırası, `tests/test_entegrasyon_duman.py` deseni); önizleme bekletmesinin
   `process_project`'e girmediği; reddin mp4'leri sildiği; onayın elle konmuş bekletmeye
   dokunmadığı.
6. `haftalik_is_akisi.md` §2 D-13 adımını "Telegram'daki önizlemeyi onayla/reddet" olarak
   güncelle; CLAUDE.md'ye tasarım kararı maddesi.
7. İlk canlı doğrulama: bir sonraki Salı indirmesinde render → önizleme → onay → yayın zinciri,
   log satırlarıyla.
8. **Ayrı iş (bu planın dışında):** belgelerdeki kota rakamlarını yeni `videos.insert` maliyetiyle
   düzelt (2026-09-12'de yapıldı); R-1 kuyruk başı tıkanması; R-4 TG/BS'nin golden-hour'u beklememesi.

---

## 8. Doğrulanmayanlar

- YouTube `publishAt` için azami ileri tarih (resmî belgede sınır yok).
- Private videoda ASR altyazısının üretilmesi; private videonun playlist'te görünmemesi.
- Tek günde çok sayıda private yüklemenin YouTube tarafında bir sinyal olup olmadığı.
- Şarkı başına gerçek toplam YouTube kota harcaması (yeni `videos.insert` maliyetiyle).
- Yeni biçim render süresi (11 Eyl sonrası 0 örnek).
- §3'teki pencere kapsaması tek bir 7 günlük log penceresinden; hafta sonu/iş günü farkı ayrılmadı.
  Sayım "o saatte en az bir log satırı var" ölçütüyle yapıldı.
- §7 madde 1'deki üç kod davranışı.

## Kaynaklar (internet, 2026-09-12)

- YouTube Data API revizyon geçmişi (4 Ara 2025 ve 1 Haz 2026 kota değişiklikleri): https://developers.google.com/youtube/v3/revision_history
- Kota maliyetleri (`videos.insert` 1, günde 100): https://developers.google.com/youtube/v3/determine_quota_cost
- `status.publishAt` koşulları: https://developers.google.com/youtube/v3/docs/videos
- Facebook Reels yayınlama, zamanlama 10 dk - 29 gün: https://developers.facebook.com/docs/video-api/guides/reels-publishing/
- YouTube kanal para kazanma politikası, inauthentic content: https://support.google.com/youtube/answer/1311392
- İkincil: https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/
