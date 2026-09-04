# CLAUDE.md — Famous Music Studio

Bu dosya, Claude Code'un bu repoda her oturum başında otomatik okuduğu kalıcı bağlam
dosyasıdır. Amaç: yeni bir oturumun (ya da context sıkışması sonrası bu oturumun) sıfırdan
keşfetmeye çalışmadan, projenin mimarisini ve buraya nasıl gelindiğini hızlıca anlaması.

## Proje nedir

"Famous Music Studio" — Suno-AI ile üretilen Türkçe şarkılardan otomatik olarak YouTube
(uzun format + Shorts), TikTok ve Instagram Reels için video üreten ve yükleyen, tek
kişilik bir otomasyon kanalı. Kullanıcı Suno'da şarkı üretip `projects/<isim>/audio.wav`
olarak indiriyor, gerisi (kapak/kart görseli üretimi, video render, üç platforma yükleme)
`auto_process.py` ile tam otomatik. Windows Görev Zamanlayıcı ile periyodik çalışıyor.

Detaylı workflow için `.claude/skills/suno-video-render/SKILL.md`'yi (Skill tool ile)
yükle — render mimarisi, ffmpeg tuzakları, config.py ayarları orada.

## Mimari — kısa özet

```
audio.wav → generate_cover.py (eksikse cover/art üretir) → validate_project.py (sağlık kontrolü)
    → render.py (ffmpeg ile video) → auto_process.py: YouTube (uzun+Shorts) + TikTok + Instagram
```

- `config.py` — tüm görünüm/kalite ayarları (temalar, kart boyutu, backdrop pan/hue hızı, vb.)
- `ffmpeg_utils.py` — kart+backdrop+marquee+progress-bar filtergraph inşası
- `generate_cover.py` — eksik cover/art'ı tema rengi + bokeh dokusuyla otomatik üretir
- `validate_project.py` — render'dan ÖNCE otomatik çalışan sağlık kontrolü (bozuk ses,
  geçersiz meta.json/theme, art==cover metin sızması şüphesi) — `render.py` her projede
  render başlamadan önce bunu çağırır, HATA varsa render'a hiç girmez
- `auto_process.py` — asıl production giriş noktası, `--count` kadar bekleyen projeyi işler
- `upload/*.py` — platform bazlı yükleme + OAuth (youtube_auth, tiktok_auth, instagram_auth)
- `upload/social_text.py` — caption/hashtag/etkileşim sorusu üretimi (şarkı başlığından
  deterministik seçim — aynı şarkı hep aynı satırları alır)
- `dj_famous_process.py` — ana katalogdan (yukarıdaki akış) TAMAMEN AYRI, haftalık DJ
  Famous üretimi (`dj_sets/` klasörü) — detay: `dj_sets/README.md`.

## Önemli tasarım kararları (nedenini bilmeden değiştirme)

- **YouTube linki caption'da DEĞİL**: Instagram/TikTok caption'larında dış link yok —
  bilinçli, off-platform link Explore/For You dağıtımını olumsuz etkileyebiliyor. Link
  bunun yerine paylaşım SONRASI bir yorum (`build_youtube_comment`).
- **`art.jpg` METİNSİZ olmalı**: hem kartın içeriği hem blur backdrop'ın kaynağı. İçine
  metin gömülüyse blur'da okunaksız lekeye dönüşür. Bu hataya birkaç kez düşüldü (Kalbim
  Oynuyor, ilk otomasyon/Küllerimden Geç) — `art.* == cover.*` (byte-birebir aynı) hızlı
  bir sağlık kontrolü.
- **Backdrop artık statik değil**: `art.jpg`'den türetilen blur arka plan, hedef
  çözünürlükten %14 büyük üretilip render sırasında yavaşça kayıyor (pan) + dar bir açı
  aralığında ton değiştiriyor (hue akışı). İkisi de ucuz filtre, performans maliyeti yok.
- **Otomatik kapak/kart bokeh dokusu**: `generate_cover.py`'ın eskiden ürettiği düz gradyan,
  kart ile backdrop'u ayırt edilemez kılıyordu — şarkı başlığından türetilen deterministik
  bokeh dokusu eklendi.
- **Vokal/tema çeşitliliği takibi**: yeni bir şarkı stil etiketi yazmadan önce
  `ses_ve_tarz_takibi.md`'ye bak — art arda aynı vokal cinsiyeti/dokusu kullanılmasın.
  `config.THEMES`'in 6 slotu (pop/rock/elektronik/akustik/hiphop/arabesk) artık hepsi
  en az bir şarkıda kullanıldı (`rock` en son, Kırık Zincir ile dolduruldu).
- **`arabesk` teması SABİT olarak kadın-erkek düet formatında üretiliyor**: tek taraflı
  vokal değil, `[Verse - Kadın]`/`[Verse - Erkek]` gibi etiketli karşılıklı bölümlerle
  (bkz. `yurek_yarasi_sozler.md`, ilk örnek — aynı ayrılığı iki taraftan anlatan yapı,
  arabeskin klasik düet geleneği). Bu ana kataloğun `arabesk` şarkıları için geçerli —
  karakter sistemindeki tekli arabesk karakterleri (Kerem Ateşi, Azra Yıldız) bu kuraldan
  ETKİLENMEDİ, onlar kendi sabit tekli kimliklerini koruyor.
- **Her şarkının kapanışı (Outro) SABİT bir kurala göre yazılıyor**: şarkı sonlarının
  anlamsız/ani kesilmesi tekrarlayan bir sorundu (`...` ile yarım bırakılmış Outro
  cümleleri + stil etiketinde kapanışın tanımlanmamış olması). Artık HER stil etiketinin
  sonuna bir kapanış tanımı ekleniyor (`gentle fade-out ending` sakin temalar için,
  `strong final hit ending, no abrupt cutoff` enerjik temalar için) ve Outro iki TAM,
  bitmiş cümle oluyor — `...` YOK. Detay ve örnekler: `suno_prompt_hazirlik.md`,
  "Kapanış (Outro) kuralı".
- **Her `*_sozler.md`'de "Temiz Sözler" bölümü SABİT**: Suno'ya yapıştırılan sözlerdeki
  `[Verse 1]`/`[Chorus]` gibi köşeli parantez etiketleri YouTube açıklamasına aynen
  kopyalanınca amatör görünüyordu (kullanıcı geri bildirimi). Artık her sözler
  dosyasında, etiketli Suno versiyonunun altında etiketsiz, doğrudan açıklamaya
  yapıştırılabilir bir "Temiz Sözler" bölümü de bulunuyor.
- **Şarkı Intro'sunun ilk satırı temayı DOĞRUDAN adlandırmaz**: "Kırdım zincirleri,
  artık özgürüm" gibi açılışlar (şarkının konusunu hemen özetleyen "tez cümlesi")
  yapay/şablon hissi veriyordu (kullanıcı geri bildirimi). Artık Intro somut bir
  an/detay/duyu imgesiyle açılıyor, temayı dolaylı hissettiriyor. Detay:
  `suno_prompt_hazirlik.md`, "Intro kuralı".
- **`--count` artık OTOMATİK kademeleniyor (elle verilmezse)**: sabit bir sayı yerine
  script, kaç proje bekliyorsa 24 saati o sayıya eşit aralıklara bölüp (ör. 9 proje →
  ~2.7 saatte bir, 2 proje → 12 saatte bir) son yüklemeden bu aralık kadar süre
  geçmediyse o koşuda hiçbir şey yapmıyor (`_auto_pace_count()`, `auto_process.py`).
  Amaç aynı: aynı anda birden fazla şarkı paylaşmanın aynı takipçi kitlesinde
  birbiriyle yarışmasını önlemek — ama artık kaç dosya biriktiği önemli değil,
  otomatik dengeleniyor. Bunun işlemesi için Görev Zamanlayıcı'nın SIK (ör. saatte
  bir) TEK bir tetikleyiciyle çalışması yeterli — script her çağrıldığında "sırası
  geldi mi" diye kendi karar veriyor. `--count N` elle verilirse bu mantık devre
  dışı kalır (eski sabit davranış).
- **Üç platform, üç FARKLI golden-hour stratejisi (`config.GOLDEN_HOURS`,
  `config.next_golden_publish_time`, TR yerel 12:00-14:00/18:00-22:00)** — otomatik
  kademeleme render/upload anını günün her saatine denk getirebildiği için (eskiden
  sabit 13:00/19:00, artık saatte bir kontrol), kullanıcıyla netleştirilip her
  platform kendi API kısıtına göre çözüldü:
  - **YouTube** — native destek var: `status.privacyStatus="private"` +
    `status.publishAt` ile yükleniyor, YouTube videoyu bir sonraki golden-hour
    penceresinde kendisi otomatik public yapıyor. `--no-schedule` ile kapatılabilir.
  - **Instagram** — Graph API'de native zamanlanmış yayın YOK (WebSearch ile
    doğrulandı, Eylül 2026), bu yüzden KENDİ kuyruğumuz var: `instagram_upload.py`
    konteyneri (`creation_id`) hemen oluşturup `state.json`'a kaydediyor ama
    `media_publish` çağrısını (gerçek canlıya çıkış) golden-hour'a kadar
    erteliyor (`try_publish_pending()`, `auto_process.py`'nin her çalıştırmasında
    — batch'e girmeyen projeler için bile `_drain_golden_hour_queue()` ile kontrol
    ediliyor). Instagram konteynerleri 24 saat sonra EXPIRED oluyor (WebSearch ile
    doğrulandı) — golden-hour pencereleri arası en kötü senaryoda ~14 saat olduğu
    için güvenli marj var, yine de `try_publish_pending()` EXPIRED durumunu
    algılayıp konteyneri sıfırdan yeniden oluşturuyor.
  - **TikTok** — Content Posting API'de de native zamanlanmış yayın YOK, ayrıca
    henüz audit'ten geçmediği için zaten sadece taslak/gelen kutusuna yükleyip
    kullanıcının uygulamadan ELLE yayınlamasını gerektiriyor (bkz. aşağıdaki
    madde). Bu elle adımı unutmamak için kullanıcı isteğiyle `notify.py` (ntfy.sh
    üzerinden ücretsiz telefon push bildirimi) eklendi — `tiktok_upload.py`nin
    `notify_pending_publish()`'i golden-hour'a girildiğinde bir kereliğine
    hatırlatma gönderiyor (`state.json`'da `tiktok_notified` ile tekrar
    göndermiyor, TikTok API'sinden kullanıcının gerçekten yayınlayıp
    yayınlamadığını öğrenmenin bir yolu yok). `notify_config.json` (gitignored,
    `{"ntfy_topic": "..."}`) yoksa sessizce atlanır, otomasyon bozulmaz.
- **Paylaşım metinlerinin dili (caption/hashtag/YouTube yorumu) artık STİLE göre
  otomatik (`config.THEMES[...]["language"]`, `social_text.resolve_language()`)**:
  kullanıcı isteği — Suno'da üretilen müziğin STİLİNE göre dil hazırlığı otomatik
  olsun, her projede elle `"language"` yazmaya gerek kalmasın. Ana kataloğun 6
  tarzının hepsi `"tr"` (Türkiye pazarına göre kurulu, değişmedi); `"dj"` (DJ
  Famous) `"en"` — markanın global açılımının ilk somut denemesi (kullanıcı
  kararı, 2026-09-03: "ama sonra yabancı da olacak"). `meta.json`'da açık bir
  `"language"` varsa (istisna/override için) o öncelikli, yoksa temanın
  varsayılanına düşülür. `build_caption()`/`build_ai_disclosure_line()`/
  `build_youtube_comment()` hepsi bu mekanizmayı kullanıyor; TikTok'un
  `notify_pending_publish()` bildirimi İSTİSNA — o kanal OPERATÖRÜNE (kullanıcı)
  gidiyor, izleyiciye değil, bu yüzden bilerek Türkçe kalıyor (dil seçimi
  içerik/izleyici odaklı, operatör arayüzü değil).
- **DJ Famous (`dj_sets/`, `dj_famous_process.py`) ana katalogla ASLA karıştırılmamalı**:
  ana katalog kurgusal, DJ Famous GERÇEK bir kişiyi (kendi açık onayıyla) konu alıyor —
  bu yüzden bilerek ayrı bir klasör, ayrı bir script, ayrı bir kilit/log dosyası. AI-üretimi
  olduğu gizlenmiyor (kullanıcıyla netleştirilen tasarım kararı): YouTube'un
  `containsSyntheticMedia` bayrağı zaten otomatik, TikTok'ta yüklerken uygulamadan native
  "AI-generated content" etiketinin açılması gerektiği hatırlatılıyor, Instagram
  caption'ının sonuna `social_text.build_ai_disclosure_line()` ile tek satır ekleniyor
  (Meta'nın `is_ai_generated` API alanı ikincil kaynaklarda geçiyor ama resmi
  dokümantasyonda doğrulanamadı, bkz. `upload/instagram_upload.py`'deki not — bu yüzden
  API'ye güvenmek yerine caption satırı kullanıldı). Gerçek bir kişinin fotoğrafını
  girdi olarak kullanmak KENDİ açık rızasını gerektirir — aile içi bir karar olsa bile.
  `generate_cover.py`'daki `_add_title_text()` bu özellik eklenirken bir hata da ortaya
  çıkardı ve düzeltildi: elle sağlanan (character-roster'da olmayan) bir `art.jpg`
  CANVAS_SIZE (1600x1600) dışında bir çözünürlükte/en-boy oranındaysa başlık metni
  canvas dışına taşıp kesiliyordu — artık her zaman önce scale+crop ile normalize
  ediliyor (video render tarafı zaten `ffmpeg_utils.py`'de bunu yapıyordu, sadece
  kapak üretimi eksikti).
- **AI-içerik açıklaması**: kanal %100 AI üretimi olduğu için YouTube upload'ında
  `containsSyntheticMedia: True` set ediliyor (resmi kaynakla doğrulandı). TikTok/Instagram
  tarafında resmi API alan adı bu ortamdan doğrulanamadı — koda hiçbir şey eklenmedi (yanlış
  alan adı riskli), sadece kullanıcıya elle etiketleme hatırlatması var.
- **"#AIMusic"/"#YapayZekaMüzik"/"#AIMusicChallenge"/"#SunoAI" gibi AI-vurgulu
  ibareler KULLANILMIYOR** (kullanıcı kararı): ne caption'da (`config.BRAND_HASHTAGS`,
  `config.DISCOVERY_HASHTAGS`), ne YouTube etiketlerinde
  (`upload/youtube_upload.py::build_snippet/build_shorts_snippet`), ne video içi kayan
  yazıda (`marquee_text`). Bu, yukarıdaki ZORUNLU AI-üretimi bildirimini DEĞİŞTİRMEZ —
  o ayrı, dokunulmayan bir mekanizma (containsSyntheticMedia, TikTok etiket hatırlatması,
  Instagram disclosure satırı). Kaldırılan sadece marka/keşfet amaçlı hashtag'ler.
- **TikTok kapak (cover) görseli API'den ayarlanamıyor**: `video_cover_image_url` sadece
  audit'ten geçmiş Direct Post akışında var, bu projenin kullandığı Taslak/Gelen Kutusu
  akışında yok (WebSearch ile doğrulandı, Eylül 2026) — API üzerinden koda eklenebilecek
  bir şey değil. Bunun yerine `tiktok_upload.py` YouTube/Instagram'daki caption/AI-etiket
  hatırlatmalarıyla AYNI desende (bkz. `upload_video()` içindeki not) her yüklemede hangi
  `cover.jpg`'yi kullanacağını basıp `state.json`'a (`tiktok_cover_hint`) kaydediyor;
  `--pending-covers` ile TikTok'a zaten yüklü TÜM projeler için bu listeyi tek seferde
  alabilirsin (eski videolar dahil, `tiktok_cover_hint` yoksa `_find_cover` ile yeniden
  bulunuyor). Kullanıcı bunu TikTok uygulamasında (taslağı yayınlarken YA DA yayınlandıktan
  sonra 7 gün içinde "Gönderiyi düzenle" → "Kapağı düzenle") "Yükle" ile galeriden elle
  seçiyor — video karesi seçmek zorunda değil. Detay: README.md, "Kimlik doğrulama" →
  TikTok adımı.
- **`watch_projects.py` (opsiyonel klasör izleyici) saatlik tetikleyiciyi DEĞİŞTİRMEZ,
  tamamlar**: kullanıcı isteğiyle eklendi — Suno'dan yeni indirilen (herhangi bir adla)
  ses dosyasını yakalayıp `audio.wav`'a çevirir ve `auto_process.py`'yi hemen tetikler,
  ama kademeleme kararına karışmaz (`auto_process.py` "sırası geldi mi" kontrolünü
  hâlâ kendisi yapar) — sadece "dosya geldi → fark edilme" gecikmesini saatlerden
  dakikalara indiriyor. TEK SEFERLİK bir tarama scripti — sürekli çalışan bir
  arkaplan süreci DEĞİL, `setup_task_scheduler.ps1` bunu 1 dakikada bir tekrar eden
  bir görev olarak kurar (`auto_process.py`'nin saatlik görevindeki AYNI tetikleyici
  deseni). İlk tasarım ("oturum açılışında başlayan sürekli süreç", `-AtLogOn`
  tetikleyicisi) bu ortamda (Claude Code'un arka planda/interaktif olmayan çalıştırma
  bağlamı) `Register-ScheduledTask` "Erişim engellendi" hatası verdiği için terk
  edildi — Windows'un logon-tabanlı tetikleyicileri böyle bir bağlamdan kaydedilirken
  izin isteyebiliyor, zaman-tabanlı tekrarlı tetikleyiciler bu kısıtlamaya takılmıyor.
- **`.ps1` dosyaları UTF-8 BOM'suz kaydedilirse Windows PowerShell 5.1'de BOZULUR**:
  `setup_task_scheduler.ps1` ilk yazıldığında BOM'suzdu — Türkçe karakterler (ı, ğ, ş,
  İ, —) ANSI kod sayfasıyla yanlış okunup parse hatalarına yol açıyordu (script hiç
  çalışmayacaktı). Düzeltildi (BOM eklendi) ama YENİ bir `.ps1` dosyası yazılırsa aynı
  hataya düşülebilir — UTF-8 BOM'LU kaydedilmeli (Python'da `encoding="utf-8-sig"`).
  `.py` dosyaları etkilenmiyor (Python 3 kaynak kodu için BOM gerektirmiyor).
- **Log dosyaları (`auto_process.log`, `watch_projects.log`) 7 günden eskiyi tutmuyor**:
  her çalıştırmada `log_rotate.trim_log()` ile eski satırlar silinip dosya üzerine
  yeniden yazılıyor (ayrı döndürülmüş `.1`/`.2` dosyaları YOK — kullanıcı isteği).
- **Görev Zamanlayıcı görevleri `pythonw.exe` ile çalıştırılıyor, `python.exe` DEĞİL**:
  `python.exe` her tetiklenişte kısa süreliğine görünür bir konsol penceresi açıp
  kapatıyordu — `watch_projects.py` dakikada bir çalıştığı için bu, ekranda sürekli
  terminal penceresi açılıp kapanıyormuş gibi rahatsız edici bir görüntüye yol açıyordu
  (kullanıcı geri bildirimi). `auto_process.py`/`dj_famous_process.py`/
  `watch_projects.py` üçü de zaten kendi `.log` dosyalarına yazdığı için `pythonw.exe`'ye
  geçmek (pencere açmayan yorumlayıcı) hiçbir tanılama bilgisini kaybettirmiyor —
  `setup_task_scheduler.ps1` artık python.exe'nin yanındaki pythonw.exe'yi otomatik
  bulup üç görevde de onu kullanıyor (bulamazsa python.exe'ye düşüp uyarı basıyor).
- **`auto_process.py`/`dj_famous_process.py` her çalıştırmada başında sessizce
  `git pull` deniyor (`git_sync.auto_pull()`)**: kullanıcı her kod düzeltmesi PR ile
  `main`'e birleştikten sonra üretim makinesine elle `git pull` yapmak zorunda
  kalmasın diye eklendi. SADECE `git pull --ff-only` — `projects/*/state.json` gibi
  bazı runtime dosyaları git'e commit'li (`.gitignore`'da YOK) ve otomasyon her
  yüklemede bunları yerel olarak (commit'siz) değiştiriyor; sert bir reset/merge bu
  değişikliklerin üzerine yazabilirdi, fast-forward ise uzak taraf o dosyalara
  dokunmadığı sürece yereldeki commit'siz değişiklikleri OLDUĞU GİBİ bırakıyor.
  Sadece `main` daldayken çalışıyor (elle farklı bir dal checkout edilmişse
  dokunmuyor) ve fast-forward mümkün değilse (ör. gerçekten çakışan bir durum,
  ağ yok, `.git` yok) ASLA otomatik merge/reset denemiyor — sessizce log'a bir
  satır düşüp eski koduyla devam ediyor, otomasyonu hiçbir zaman durdurmuyor.
  `watch_projects.py`'ye BİLEREK eklenmedi — dakikada bir GitHub'a istek atmak
  gereksiz; watcher zaten yeni dosya geldiğinde `auto_process.py`'yi tetikliyor,
  pull orada zaten oluyor. Görev Zamanlayıcı görev TANIMINI (tetikleyici, hangi
  script/python.exe) etkileyen değişiklikler bu mekanizmayla YAYILMAZ — o zaman
  hâlâ `setup_task_scheduler.ps1`'in elle yeniden çalıştırılması gerekiyor.

## Beş özel subagent (`.claude/agents/`)

Salt-okunur denetçiler — kod yazmazlar, sadece bulgu raporlarlar:

- **sosyal-medya-danismani** — caption/hashtag/görsel/zamanlama değişirken proaktif kullan.
- **muzik-produksiyon-ajani** — yeni şarkı sözü/stil etiketi yazarken (tema dengesi, tempo,
  vokal çeşitliliği, lirik zanaat).
- **otomasyon-denetcisi** — tüm pipeline'ın genel sağlık denetimi (bug, performans, test
  eksikliği, belge tutarsızlığı).
- **siper-guvenlik-ajani** — derinlemesine güvenlik (secrets, komut enjeksiyonu, OAuth kapsamı).
- **icerik-uyumluluk-ajani** — AI-içerik açıklama/platform politika uyumluluğu (WebSearch
  ile güncel politika kontrolü şart, hafızaya güvenme).

Dördü de baseline (ilk kapsamlı) denetimini bir kere yaptı, bulguların çoğu düzeltildi
(bkz. git geçmişi, PR #25/#26/#27). Periyodik olarak tekrar çalıştırılabilirler.

## Açık/bilinen boşluklar (henüz yapılmadı)

- TikTok/Instagram'ın AI-içerik açıklama API alan adları doğrulanmadı (resmi dokümantasyona
  bu ortamdan erişilemedi) — kullanıcı doğrularsa koda eklenebilir.
- YouTube OAuth scope'u (`youtube.force-ssl`) daraltılabilir mi test edilmedi — yanlış
  daraltma `set_privacy.py`/`update_metadata.py`'yi bozabilir, canlı ortamda test gerekir.
- İlk 3 şarkının (Beni Bırakma, Küllerimden Geç, Shudhniy L) Suno stil etiketleri
  arşivlenmemiş.
- `rock` teması hiç kullanılmadı (6 slottan tek boş kalan).

## Diğer takip dosyaları

`buyume_kontrol_listesi.md` (elle yapılan büyüme adımları), `trend_hashtag_notlari.md`
(hashtag/saat araştırması, periyodik güncellenmeli), `ses_ve_tarz_takibi.md` (vokal
çeşitliliği), `suno_prompt_hazirlik.md` (yeni şarkı ekleme adımları + lisans notu).

## Git/PR alışkanlığı

`claude/analiz-yap-sk8gpf` dalında geliştirilip PR ile `main`'e birleştiriliyor. Bir PR
merge olduktan sonra bu dal restart edilir (`git fetch origin main && git reset --hard
origin/main` veya içerik aynıysa force-with-lease push) — merge edilmiş commit'lerin
üzerine yeni commit yığmak yerine.

## Claude Code Remote Control (opsiyonel, yerel geliştirme için)

Bu repo Windows'ta yerel olarak (Görev Zamanlayıcı + elle debug için terminal) geliştirilip
kullanılıyor. Uzun süren bir işlem başlatılıp (ör. büyük bir render batch'i, `auto_process.py`
çalıştırması, bir subagent denetimi) masadan uzaklaşılacaksa, oturum
[Remote Control](https://code.claude.com/docs/en/remote-control) ile telefon/tarayıcıdan takip
edilebilir:

```
claude remote-control
```

Bu, verilen QR kodu/URL üzerinden claude.ai/code veya Claude mobil uygulamasından bağlanmaya
izin verir; kod çalıştırma ve dosya erişimi yine bu makinede (yerel) kalır, sadece
görüntüleme/yönlendirme uzaktan yapılabilir. `auto_process.log`/`watch_projects.log` gibi log
dosyalarını veya render çıktısını uzaktan kontrol etmek, ya da bir izin isteğine (permission
prompt) telefonan yanıt vermek için kullanışlı. Zorunlu bir kurulum adımı değil — proje
otomasyonu (`auto_process.py`, `watch_projects.py`) Görev Zamanlayıcı ile bağımsız çalışır,
Remote Control sadece Claude Code ile yerel geliştirme/debug oturumlarını uzaktan izlemek
içindir.
