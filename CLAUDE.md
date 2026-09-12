# CLAUDE.md — Famous Music Studio

Bu dosya, Claude Code'un bu repoda her oturum başında otomatik okuduğu kalıcı bağlam
dosyasıdır. Amaç: yeni bir oturumun (ya da context sıkışması sonrası bu oturumun) sıfırdan
keşfetmeye çalışmadan, projenin mimarisini ve buraya nasıl gelindiğini hızlıca anlaması.

## Proje nedir

"Famous Music Studio" — Suno-AI ile üretilen Türkçe şarkılardan otomatik olarak YouTube
(uzun format + Shorts), TikTok, Instagram Reels ve — opt-in olarak, `config.EK_PLATFORMLAR`
(2026-09-10'da üçü de açıldı) — Facebook Reels / Telegram / Bluesky için video üreten ve
yükleyen, tek kişilik bir otomasyon kanalı. Kullanıcı Suno'da şarkı üretip
`projects/<isim>/audio.wav` olarak indiriyor, gerisi (kapak/kart görseli üretimi, video
render, platformlara yükleme) `auto_process.py` ile tam otomatik. Windows Görev
Zamanlayıcı ile periyodik çalışıyor. Ana katalogdan AYRI iki hat daha var: haftalık DJ
Famous setleri (`dj_sets/`) ve ayda en fazla bir derleme (`derlemeler/`) — ikisi de
`dj_famous_process.py` ile işleniyor.

Detaylı workflow için `.claude/skills/suno-video-render/SKILL.md`'yi (Skill tool ile)
yükle — render mimarisi, ffmpeg tuzakları, config.py ayarları orada.

## Mimari — kısa özet

```
audio.wav → generate_cover.py (eksikse cover/art üretir)
  → validate_project.py (sağlık kontrolü + uyumluluk.kontrol(..., "render") politika kapısı)
  → render.py (ffmpeg ile video)
  → auto_process.py: uyumluluk.kontrol(..., "yukleme") → YouTube (uzun+Shorts) + TikTok
    + Instagram + (opt-in) Facebook/Telegram/Bluesky
```

- `config.py` — tüm görünüm/kalite ayarları (temalar, kart boyutu, backdrop pan/hue hızı, vb.)
- `ffmpeg_utils.py` — kart+backdrop+marquee+progress-bar filtergraph inşası
- `generate_cover.py` — eksik cover/art'ı üretir: art için önce `stock_art.py` (Pexels
  fotoğrafı), o olmazsa tema rengi + bokeh dokusu; cover'ı İKİ oranda üretir
- `stock_art.py` — şarkının tarzına/sözlerine uygun gerçek fotoğrafı Pexels'ten indirir
- `validate_project.py` — render'dan ÖNCE otomatik çalışan sağlık kontrolü (bozuk ses,
  geçersiz meta.json/theme, art==cover metin sızması şüphesi) — `render.py` her projede
  render başlamadan önce bunu çağırır, HATA varsa render'a hiç girmez; `uyumluluk.kontrol()`
  politika kapısı da buradan tetikleniyor
- `auto_process.py` — asıl production giriş noktası, `--count` kadar bekleyen projeyi işler
- `caption_align.py` — YouTube'un otomatik (ASR) altyazısının zamanlamasını gerçek
  sözlerle (`<slug>_sozler.md`) hizalar; `upload/youtube_captions.py` bunu çağırır
- `upload/*.py` — platform bazlı yükleme + OAuth (youtube_auth, tiktok_auth, instagram_auth)
- `upload/social_text.py` — caption/hashtag/etkileşim sorusu üretimi (şarkı başlığından
  deterministik seçim — aynı şarkı hep aynı satırları alır)
- `dj_famous_process.py` — ana katalogdan (yukarıdaki akış) TAMAMEN AYRI, haftalık DJ
  Famous üretimi (`dj_sets/` klasörü) — detay: `dj_sets/README.md`. `--base derlemeler`
  ile derlemeleri de AYNI hattan yayınlıyor (ayrı bir işleyici gerekmedi).
- `uyumluluk.py` — render ve yükleme adımlarında otomatik çalışan politika kapısı (aşağıya bkz.)
- `state_io.py` — `state.json` için TEK atomik yazıcı (`.tmp` + `flush`/`fsync` +
  `os.replace`; Windows'ta da atomik). Üç ayrı yerde `open(..., "w")` ile HEDEFİN ÜSTÜNE
  yazılıyordu; `open` dosyayı önce sıfırladığı için yarıda kesilen bir yazım diskte yarım
  bir JSON bırakıyordu — `uyumluluk._durum()` sertleştikten sonra bunun bedeli "boru hattı
  tamamen durur"a çıktı. state.json'ı elle yazan YENİ kod ekleme, bu modülü kullan.
- `dj_tarama_kontrol.py` — DJ setleri + derlemeler için Content ID karantinası (aşağıya bkz.)
- `saglik_kontrol.py` — sessiz duruşları yakalar; 2026-09-12 itibarıyla YEDİ adım
  (aşağıda "Testler ve otomatik sağlık izleme"); saatlik koşudan, bildirimler günde bir
- `gorev_sarmalayici.py` — üç Görev Zamanlayıcı görevinin de GERÇEK giriş noktası
  (`pythonw.exe gorev_sarmalayici.py <betik>.py`). Bir görev çalışmadığında bakılacak İLK
  yer onun yazdığı `gorev_izleri/<betik>.log`'dur, `auto_process.log` DEĞİL.
- `upload/ai_beyani_onar.py` — geçmişte SİLİNMİŞ `containsSyntheticMedia` beyanını geri
  yazan ELLE kampanya; zamanlayıcıda BİLEREK yok, varsayılanı kuru koşu
- `upload/ek_platform_backfill.py` (Telegram/Bluesky) + `upload/facebook_backfill.py` —
  geri doldurma; ikisi de golden-hour VE günlük tavan olmak üzere İKİ kapıdan geçiyor
- `upload/youtube_analytics.py` — izlenme SÜRESİ ölçümü. AYRI bir `analytics_token.json`
  kullanıyor: `yt-analytics.readonly` iznini mevcut `upload/token.json`'a eklemek en kolay
  yol olurdu ama `Credentials.from_authorized_user_file` kayıtlı izinlerle istenenleri
  karşılaştırdığı için o token'ı GEÇERSİZ KILAR ve saatlik YÜKLEME HATTI DURUR.
- `derleme.py` — yayınlanmış şarkılardan uzun format derleme (Suno kotasına HİÇ dokunmadan).
  Zamanlayıcıda BİLEREK yok: ayda en fazla bir tane, her biri farklı konseptle, elle.
- `dj_clips.py` — bir setten birden çok dikey kesit ÜRETİR ama set başına EN FAZLA BİRİNİ
  yayınlar (üretim bedava, yayın kısıtlı — "inauthentic content" riski). ÜRETİM tarafı
  çalıştı (`dj_sets/Just Relax/output/clip_01..03.mp4`), YAYIN tarafı 2026-09-11 itibarıyla
  HİÇ çalışmadı: süpürge (`dj_clips.supur`, `dj_famous_process.py`'den) üç koşuda da
  "yayınlanacak kesit yok" dedi. Hattın ikinci yarısı üretimde HENÜZ DOĞRULANMADI.

## Bu deponun EN SIK hatası: BAĞLANTI seviyesindeki sessiz arıza

2026-09-11'de tek bir günde **en az on** ayrı "yazıldı, kendi içinde doğru, ama hiçbir
yerden çağrılmıyor / yanlış argümanla çağrılıyor / hiçbir zamanlayıcı görevine bağlı
değil" vakası bulundu. Hepsi gerçek:

- `notify_config.json` hiç oluşturulmamıştı → `notify.send()` her seferinde sessizce
  `False` döndü; TikTok hatırlatması, nabız uyarısı, token/Netlify uyarısı ve karantina
  bildirimi (beş emniyet ağı) aynı anda ölüydü ve kimse bilmiyordu.
- `netlify_kontrol.py` ile `weekly_report._check_instagram_token_expiry()` tam da "sessiz
  duruşu yakalamak" için yazılmıştı; ikisi de hiçbir yerden çağrılmıyordu. 2026-09-08'de
  Netlify token'ı doldu, Instagram yüklemeleri 401'le sessizce durdu, 25+ koşu fark edilmedi.
- `upload/youtube_analytics.py` doğruydu ama tek çağıranı, zamanlayıcıya bağlı OLMAYAN
  `weekly_report.py`'ydi — yani ölçüm pratikte hiç çalışmadı.
- `_ek_platformlari_isle()` yalnızca `process_project()` içinden çağrılıyordu; dört ana
  anahtarı dolan proje `pending`'den kalıcı düştüğü için 18 şarkının 14'ü Telegram/Bluesky'yı
  BİR DAHA hiç görmedi ve log'a tek satır bile düşmedi.
- `_refresh_stats(args.base)` yanlış argümanla çağrılıyordu; çok-kök düzeltmesi ölü dalda
  kaldı, `dj_sets`'in deltası hiç hesaplanmadı.
- `uyumluluk.KOKLER` göreli yoldaydı: yanlış cwd'de `os.path.isdir` False döner, `kontrol()`
  `hata=0 uyari=0` der ve **kapı kendiliğinden AÇILIR**. (Aynı düzeltme `dj_tarama_kontrol.py`
  ve `upload/youtube_analytics.py`'de de yapıldı.)
- `generate_cover.py`'daki `max(alt, min(tavan, sığan))` koruma gibi duruyordu; matematiksel
  olarak yaptığı TEK şey taşmayı garantilemekti.
- **Yeni bir alt sınıf: "çağrı doğru, ama YANLIŞ YERDE."** `sync_project` hem
  `auto_process.py` hem `dj_famous_process.py`'de Shorts yüklemesinden ÖNCE çağrılıyordu;
  o an `state.json`'da `youtube_shorts_video_id` HENÜZ YOK — yani 20 Shorts'un HİÇBİRİ
  playlist'e girmemişti, ve proje `_is_fully_done()`'dan geçip `pending`den düştüğü için
  bir daha hiç denenmedi. Düzeltme: Shorts yüklendikten SONRA İKİNCİ bir `sync_project`
  çağrısı (idempotent; üyeliği YouTube'dan doğruluyor). İlk çağrı da KALMALI — Content ID
  kapısı `return` ettiğinde ikinciye hiç gelinmiyor. Koruma testi bu yüzden çağrının
  VARLIĞINI değil SIRASINI doğruluyor (`ast` ile çağrı satır numaraları,
  `tests/test_entegrasyon_duman.py`; davranış tarafı `tests/test_playlist_shorts_sirasi.py`).
- **Yalan söyleyen yorum, hiç yorum olmamasından KÖTÜDÜR**: `dj_famous_process.py`'nin
  başında "Merkezi maskeleyici — log'a yazılan HER metin buradan geçiyor" yazıyordu;
  `gizli_maskele.maskele` import EDİLMİŞTİ ama `log()` içinde hiç ÇAĞRILMIYORDU — dosyadaki
  tek geçiş import satırının kendisiydi. Bedeli tam orada ödendi: 2026-09-04'te gerçek bir
  Instagram erişim token'ı `dj_famous_process.log`'a düştü. Yorum doğruyu söylediği için
  arıza grep'le bile görünmüyordu. Bir yorum bir GARANTİ ifade ediyorsa, o garantiyi
  doğrulayan bir test olmadan yazma (`tests/test_sizinti_kaynaklari.py`).

**Ortak nokta: hiçbiri fonksiyon seviyesinde bozuk değil.** grep ile "çağrılmayan fonksiyon"
aramak bunların hiçbirini yakalamaz — hepsinde bir çağrı VAR, ya da çağrı doğru ama hattın
dışında. Arıza BAĞLANTIDA.

Yeni bir modül/koruma yazarken ÜÇ soruyu cevaplamadan bitmiş sayma:

1. **Bunu kim çağıracak?** — dosya + fonksiyon adıyla.
2. **Hangi zamanlayıcı görevinden?** — `setup_task_scheduler.ps1` yalnızca ÜÇ görev kuruyor
   (saatlik `auto_process.py`, haftalık `dj_famous_process.py`, dakikalık
   `watch_projects.py`); başkası YOK. Yeni görev eklemek yerine bu üçünden birine bağla —
   `auto_process.main()`'in `finally` bloğu, "iş olsun olmasın her koşuda" çalışan arka
   plan kancalarının yeri.
3. **Çalışmadığını nasıl anlarız?** — Sessizce `False`/`{}`/boş liste dönen bir koruma,
   OLMAYAN korumadan KÖTÜDÜR: yokluğu görünmez. En az bir log satırı bırak
   (`notify.uyar_bir_kez(anahtar, mesaj)` koşu başına bir kez yazar) ya da bir test yaz.

**Yeni bir platform/adım eklerken `auto_process._is_fully_done()`'a EKLEME** — gerekçenin
tamamı o fonksiyonun docstring'inde ("YENİ BİR PLATFORM EKLERKEN — BURAYA EKLEME",
2026-09-11). Kural iki seçenekli, üçüncüsü YOK: **(A)** ucuz/idempotent/kotasız bir
TAMAMLAMA işi → `_drain_golden_hour_queue()` (o fonksiyon `pending` değil **`ready`** ile
geziyor — `_is_fully_done`'dan geçmiş projeleri de kapsayan TEK yer); **(B)** kendi hız
sınırı/API kotası/günlük tavanı olan bir iş → AYRI süpürge modülü + `main()`'in `finally`
bloğu. `pending`e (yani `process_project()`'e) bağlamak, o platformu kataloğun büyük kısmı
için KALICI OLARAK ÖLÜ yapar; 2026-09-11'de tam olarak bu üç kez oldu.

## Önemli tasarım kararları (nedenini bilmeden değiştirme)

- **`Küllerimden Geç` YouTube'da BİLEREK `unlisted` — public YAPMA**: `Yeniden Doğacağım`
  (`kZML9g4GdBs`, 1 Eylül, public) ile AYNI ses (`audio.wav` md5'leri eşit) ve aynı sözler;
  `Küllerimden Geç` (`-CQ7MmUygTQ` + Shorts `jN78mJrZd3c`) 7 Eylül'deki İKİNCİ yüklemedir ve
  2026-09-11'de liste dışına alındı — silinmedi. Kanıt: iki projenin `state.json`/`meta.json`
  dosyalarındaki `kopya_notu`. `derleme.py`, `latest_release.py` ve
  `upload/ek_platform_backfill.py` üçü de bu kaydı "unlisted = kopya" diye BİLEREK dışlıyor;
  `uyumluluk.py`'deki md5 tekrar kontrolü de bu olaydan doğdu — ve o kontrol 2026-09-11'de
  UYARI'dan **HATA**'ya çekildi: aynı md5 artık boru hattını DURDURUR. İki muafiyet var,
  ikisi de dar: (a) BU projenin kaydında `kopya_notu` VAR *ve* çiftin bir tarafı yayından
  çekilmiş (unlisted / zamanlanmamış private); (b) bu proje zaten yayında ve eşleşen klasör
  HENÜZ yayınlanmamış (hata o klasöre düşer). Yani "nota yaz, yayınla" diye bir kaçış yolu
  yok. Public yapmak aynı sesi kanalda
  iki kez yayına sokar — kanalın en büyük riski olan "inauthentic / toplu üretilmiş AI içerik"
  politikasına doğrudan yem, ve o üç kopya kapısını aynı anda açar
  (bkz. `buyume_kontrol_listesi.md`, E7).
- **Kapak İKİ ayrı oranda üretiliyor: `cover.png` (16:9) + `cover_vertical.png` (9:16)**:
  eskiden tek kare (1600x1600) kapak vardı, YouTube'un 16:9 oynatıcısında sağ/sol
  kenarlarda çirkin koyu şeritler (pillarbox) oluşuyordu (kullanıcı geri bildirimi).
  `youtube_upload.py` uzun formata 16:9'u, Shorts'a 9:16'yı gönderiyor
  (`_find_cover_vertical`); `instagram_upload.py`/`tiktok_upload.py` (ikisi de dikey
  video) önce dikey varyanta bakıp yoksa 16:9'a düşüyor. `_compose_cover_rich`'in metin
  bloğu bu yüzden ALTTAN yukarı istifleniyor (sabit üstten-oran yerine) — aynı
  kompozisyon iki oranda da taşmadan çalışsın diye.
- **Kapakta müzik TÜRÜ yazmıyor** (kullanıcı isteği): "ARABESK"/"ELEKTRONİK" gibi harf
  aralıklı tür etiketi kaldırıldı. Tarz bilgisi zaten caption/hashtag'lerde var.
- **TÜM gerçek fotoğraflar (stok + elle sağlanan + karakter portresi) DJ Famous'un
  (`dj_sets/`) sade/ortalanmış kapak düzenini kullanıyor** (`_add_title_text`,
  `is_photo` — kullanıcı isteği: "DJ set görsel dosya yapısı diğer parçalarda da
  kullan"). Önce (kısa süreliğine) "zengin" sol-alt blok (ayraç + alt marka şeridi +
  büyük logo, `_compose_cover_rich`) denendi ve kullanıcı tarafından REDDEDİLDİ
  ("yapılan değişiklikler hatalı oldu") — o kadar dekoratif öğe bir fotoğrafın üstüne
  binince fotoğrafı bastırıyordu. `_compose_cover_rich` artık SADECE gerçek bir fotoğraf
  hiç bulunamadığında (Pexels de başarısızsa) düşülen saf prosedürel bokeh dokusunda
  kullanılıyor. `is_photo = character_image veya existing_art veya fetched_stock_photo`
  — art.jpg bir kez yazıldıktan sonra "bizim indirdiğimiz stok fotoğraf" ile
  "kullanıcının koyduğu görsel" ayırt EDİLEMİYOR, bu yüzden ikisi de aynı düzene bağlı
  (yeniden çalıştırmada tasarımın sessizce değişmesini önlüyor, bu daha önce oldu).
- **Karakter roster'ındaki placeholder'lara dikkat**: `characters/asi.jpg` ("Beton
  Krallığı" için) gerçek bir AI-üretimi portre DEĞİL, jenerik bir monogram/silüet
  placeholder'mış (açık krem daire + "AS" harfleri) — fark edilmesi zor, çünkü
  `find_character_image()` var/yok kontrolü yapıyor, içeriğin gerçek bir portre olup
  olmadığını doğrulamıyor. Kullanıcı isteğiyle bu proje `meta.json`'dan `"character"`
  alanı kaldırılıp diğer kataloğa döndürüldü (artık `stock_art.py` fotoğrafı kullanıyor).
  Yeni bir karakter eklerken roster'daki dosyanın GERÇEKTEN bir portre olduğu (bu tür bir
  placeholder değil) elle doğrulanmalı.
- **Alt karartma katsayısı 0.72** (eskiden 0.55, %50'den başlıyor): prosedürel bokeh
  dokularında 0.55 yetiyordu ama gerçek fotoğraflara geçince parlak gündüz kareleri
  geldi ve altın amblem soluk kalıyordu.
- **Kapak başlık tipografisi (2026-09-11, `generate_cover.py`)**: punto kapağın kısa
  kenarının %7,5'inden **%14'üne** çıkarıldı (`basis*0.14`) — kapak YouTube feed'inde
  ~246 px genişlikte görünüyor, eski oran orada ~10 px'lik okunmaz yazıya düşüyordu
  (9/9 kapakta ölçüldü); ayrıca `shadowcolor=black@0.75` gölge eklendi, çünkü stok
  fotoğrafların bir kısmı açık tonlu (deniz, gökyüzü) ve beyaz yazı kayboluyordu.
  Sığdırma TAHMİNLE değil, ffmpeg'e tek bir kısa çağrı yapılıp metnin GERÇEK piksel
  genişliği ÖLÇÜLEREK yapılıyor (`_basligi_sigdir`) — karakter başına ortalama genişlik
  0,43-0,50 em arasında oynuyor, %15'lik tahmin hatası ya taşma ya gereksiz küçültme
  demek. Kural DÖRT adımlı: (1) tek satır, tavan puntoda; (2) sığmazsa ve en az iki
  kelime varsa iki satıra bölünür ve **punto tavanı KORUNUR** (bölme noktası ölçülerek
  en dengeli yerden); (3) tek kelimelik başlık bölünemez, SADECE orada küçültülür;
  (4) iki satır da sığmazsa küçültülür. `MAKS_BASLIK_SATIRI = 2` — üç satır kapağı blok
  metne çevirip fotoğrafın üstünü kapatıyor (kullanıcının reddettiği dekoratif yön).
  **Eski ALT SINIR (`basis*0.075`) KALDIRILDI**: `max(alt, min(tavan, sığan))` ifadesi
  ancak sığan punto alt sınırın ALTINDAYKEN devreye giriyordu, yani koruma gibi durup
  yaptığı tek şey taşmayı GARANTİLEMEKTİ — yukarıdaki "sessiz arıza" bölümünün ders
  niteliğinde örneği. `_compose_cover_rich` de artık aynı ölçümlü sığdırmayı kullanıyor
  (eskiden hiç ölçmüyordu, 20 başlığın 13'ü taşıyordu). Logo: `LOGO_GLOW_FILTER`
  (parlak hâle) kaldırıldı, yerine logonun KENDİ alfasından türetilen KOYU hâle geldi —
  parlak hâle koyu zeminde işe yarıyordu ama sıcak/parlak fotoğrafta altın-üstüne-altın
  kontrastı sıfırdı (ölçüldü: luma farkı 22.8/255); logo yüksekliği `basis*0.2 → 0.26`.
  **Başlığın ALTINDAKİ ayracın/markanın yeri artık font metriğinden DEĞİL, ÖLÇÜLMÜŞ
  sabitlerden türüyor**: `DRAWTEXT_SATIR_YUKSEKLIGI = 1.3333` (drawtext'in satır
  yüksekliği ÷ punto oranı — 144 puntoda 192 px olarak ÖLÇÜLDÜ, tahmin değil) +
  `BASLIK_AYRAC_BOSLUGU`. Eski formül kazara font metriğine bağımlıydı: `FONT_BOLD_PATH`
  değişse ayraç sessizce iki satırlı başlığın üstüne biner ya da metni keserdi
  (`tests/test_kapak_ayrac_geometri.py`).
- **ffmpeg tuzağı — drawtext'te `"\n"` satır sonu DEĞİLDİR**: filtre grafiği
  ayrıştırıcısı ters eğik çizgiyi kaçış sayıp yutuyor ve ekrana düz bir `n` harfi
  çiziliyor ("YenidennDoğacağım" — gerçek bir render'da görüldü). Çalışan tek yol HAM
  0x0A satır sonu (`generate_cover.DRAWTEXT_SATIR_SONU`), tırnak içinde sorunsuz geçiyor.
  SIRA da kritik: satırlar TEK TEK `_escape_drawtext()`'ten geçirilip SONRA birleştiriliyor
  — o fonksiyon ters eğik çizgiyi ikiye katladığı için önce birleştirip sonra kaçırmak
  satır sonunu her hâlükârda bozar. (Aynı sınıftan bir tuzak: `drawbox` şeffaf tuvalde
  alfa yazmıyor.)
- **Dosya YAZARKEN ters eğik çizgi yutuluyor — ffmpeg tuzağından FARKLI**: orada metni
  ffmpeg'in ayrıştırıcısı bozuyor, burada dosyayı yazan araç zinciri. 2026-09-11'de beş kez: JSON
  araç parametresi / bash heredoc kaçışı bir kez DAHA çözüp diske GERÇEK baytı yazdı
  (`generate_cover.py`→NUL 0x00, `youtube_upload.py`+`saglik_kontrol.py`→0x0A, `gizli_maskele.py`→0x08).
  ÇALIŞAN YÖNTEM: ters eğik çizgili metni `chr(92)` ile kur ya da `Write` aracıyla doğrudan yaz;
  her yazımdan sonra `ast.parse` + kontrol karakteri taraması (`tests/test_kaynak_bayt_muhafizi.py`).
- **Kapaktaki marka satırı düz metin DEĞİL, gerçek amblem**: "Famous Music Studio"
  yazısının yerini `config.LOGO_PATH`'teki altın sunburst logo aldı (kullanıcı isteği).
  Logo düz SİYAH zemin üzerine kaydedilmiş, alfa kanalı YOK — `colorkey` ile siyah
  şeffaflaştırılıp overlay ediliyor, ardından `LOGO_BRIGHTEN_FILTER` (eq+curves) ile
  altın canlandırılıyor (ham hâli koyu/mat duruyordu). Canva'daki kaynak tasarımı
  `transparent_background` ile dışa aktarmak DENENDİ — siyah zemin tasarımın içine
  çizili bir öğe olduğu için sonuç birebir aynı dosya, colorkey yaklaşımı doğru olan.
  Logo asset'i gitignored (`upload/assets/*.png`) — bulunamazsa kod sessizce eski düz
  metin satırına düşer, otomasyon bozulmaz.
- **`art.jpg` artık prosedürel gradyan DEĞİL, tarza uygun GERÇEK bir fotoğraf**
  (`stock_art.py`, Pexels): kullanıcı isteği — kapak, şarkının tarzını ve sözlerinin
  çağrıştırdığı mekânı/atmosferi anımsatsın (yağmurlu pencere, gece şehri, altın saat
  ormanı), soyut bokeh değil. Videodaki kartın ve blur backdrop'ın rengi zaten
  `art.jpg`'den türediği için (`ffmpeg_utils.ensure_art_backdrop`) tüm videonun renk
  atmosferi de otomatik olarak tarza uyuyor. Arama terimi önceliği: `meta.json`'daki
  `"art_query"` (şarkıya özel, elle, en güçlü kontrol) > **şarkının `*_sozler.md`
  dosyasından otomatik çıkarım** > `config.THEMES[tema]["art_query"]` (tarzın
  varsayılanı, sözler dosyası yoksa).
  Sözlerden çıkarım: `LYRIC_IMAGERY` sözlüğü Türkçe imgeleri İngilizce terimlere
  eşler, en sık geçen 2 tanesi alınır ve BAŞINA temanın `art_mood`'u eklenir
  (`config.THEMES[tema]["art_mood"]`, ör. "melancholy moody rainy"). **Atmosfer
  çapası ŞART** — sadece sözlerden gelen terimlerle arandığında gündüz çekilmiş,
  neşeli, şarkının duygusuyla alakasız kareler geliyordu. Sözlükte SADECE
  mekân/hava/ışık terimleri var, NESNE terimleri (zincir, masa, mektup, gitar)
  bilerek çıkarıldı: nesne aramaları katalog/ürün çekimi ve yanlış anlam getiriyor
  ("Kırık Zincir" -> "chain" -> BİSİKLET zinciri fotoğrafı geldi). Sözler dosyası
  başlıktan bulunuyor ("Yürek Yarası" -> `yurek_yarasi_sozler.md`); Türkçe ünsüz
  yumuşaması ön-ek eşleşmesini bozduğu için ("Beton Krallığı" -> `beton_kralligi`
  ama dosya `beton_krallik`) `difflib` ile benzerlik eşleşmesine düşülüyor.
  Terimler İNGİLİZCE — Pexels'in arama dizini ağırlıklı İngilizce, Türkçe
  terimler alakasız sonuç veriyor. Seçim DETERMİNİSTİK (başlık hash'i → sonuç indeksi),
  aynı şarkı yeniden işlenince kapağı değişmez. `original` yerine `large2x` indiriliyor:
  original'da 28MB/5000px dosyalar geliyordu, oysa kart videoda ~486px çiziliyor.
  Anahtar/ağ/sonuç yoksa sessizce eski prosedürel bokeh'e düşer — otomasyon durmaz.
  Lisans: Pexels License (ücretsiz, ticari kullanıma açık, atıf zorunlu değil).
  API anahtarı `stock_art_config.json` (gitignored).
- **YouTube linki caption'da DEĞİL**: Instagram/TikTok caption'larında dış link yok —
  bilinçli, off-platform link Explore/For You dağıtımını olumsuz etkileyebiliyor. Link
  bunun yerine paylaşım SONRASI bir yorum (`build_youtube_comment`).
  **Instagram/TikTok yorumlarında düz metin linkler TIKLANAMIYOR** (WebSearch ile
  doğrulandı, 2026-09-05) — `build_youtube_comment`'in ürettiği youtu.be linki
  yine de kopyalanabilir metin olarak duruyor, ama gerçekten tıklanabilir tek
  yer profildeki "bio link". Bu yüzden yorum metnine ikinci bir satır eklendi —
  düz "profildeki linkten..." yazısı YERİNE, hesabın kendisini `@handle` ile
  ETİKETLEYEN (mention) bir cümle: "@famous_music_studio hesabına dokun,
  bio'daki linkten de ulaşabilirsin 🔗" (TikTok: `@famousmusicstudio`,
  `config.SOCIAL_HANDLES`). Mention, düz URL'den FARKLI bir mekanizma —
  caption/yorumda GERÇEKTEN tıklanabilir, tıklanınca doğrudan profile açılıyor
  (WebSearch ile doğrulandı: "@mentions are tappable in captions" ama "links
  in captions are not"). `build_youtube_comment(url, lang, platform)` artık
  `platform` parametresi alıyor ("instagram"/"tiktok") — doğru handle'ı seçmek
  için (`instagram_upload.py`/`tiktok_upload.py` çağrılarında elle geçiliyor).
  Kullanıcının Instagram ve TikTok'ta bio linkini `famousmusicstudio.com/latest.html`'e
  (yayındaki TÜM şarkıları en yeni önce listeleyen sayfa — sadece "en son"a
  değil, eski bir paylaşımı görüp gelen biri de aradığı şarkıyı bulabiliyor;
  `auto_process.py` HER çalıştırmada `latest_release.regenerate()` ile yeniden
  üretip `git_sync.push_path()` ile SADECE bu dosyayı push ediyor — yeni yükleme
  anında değil her run'da, çünkü golden-hour zamanlı bir video private→public'e
  YouTube tarafından SONRADAN geçebiliyor, bir sonraki run bunu yakalıyor)
  bağlaması gerekiyor, bu ELLE ve TEK SEFERLİK yapılan bir profil ayarı, API'den
  değiştirilemiyor (bkz. `buyume_kontrol_listesi.md`, C3). Meta Verified (ücretli, Reels'e özel tıklanabilir link) araştırıldı
  ama hem $49.99/ay'dan başlıyor hem Content Publishing API ile uyumluluğu
  doğrulanamadı — kullanıcı bunun yerine ücretsiz bio-link + mention çözümünü
  seçti.
- **`art.jpg` METİNSİZ olmalı**: hem kartın içeriği hem blur backdrop'ın kaynağı. İçine
  metin gömülüyse blur'da okunaksız lekeye dönüşür. Bu hataya birkaç kez düşüldü (Kalbim
  Oynuyor, Yeniden Doğacağım) — `art.* == cover.*` (byte-birebir aynı) hızlı
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
- **`arabesk` teması SABİT olarak düet formatında üretiliyor** (tek taraflı vokal değil,
  karşılıklı etiketli bölümlerle): başlangıçta sadece **kadın-erkek** (bkz.
  `yurek_yarasi_sozler.md`, ilk örnek — aynı ayrılığı iki taraftan anlatan yapı, arabeskin
  klasik düet geleneği) idi; `Sofraya Gelmedin` (bkz. `sofraya_gelmedin_sozler.md`) ile
  **baba-oğul** düeti de eklendi — kural artık düet OLMASINI zorunlu kılıyor, tarafların
  cinsiyet/yaş kombinasyonunu değil. `[Verse - Kadın]`/`[Verse - Erkek]` ya da
  `[Verse - Baba]`/`[Verse - Oğul]` gibi karşılıklı etiketli bölümler kullanılabilir. Bu ana
  kataloğun `arabesk` şarkıları için geçerli — karakter sistemindeki tekli arabesk
  karakterleri (Kerem Ateşi, Azra Yıldız) bu kuraldan ETKİLENMEDİ, onlar kendi sabit tekli
  kimliklerini koruyor.
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
- **YENİ yayınlar için 52 saatlik bir TABAN aralık var (`auto_process.MIN_YAYIN_ARALIGI_SN`)**:
  yukarıdaki 24 saatlik bölüşüm TEK BAŞINA, bir günde `projects/` altına 7 dosya düşerse
  yedisini de AYNI GÜN yayınlıyordu (24/7 ≈ 3,4 saat ara). Haftalık sayı doğru çıkıyor ama
  günlük desen YouTube'un "inauthentic content" tarifinin ta kendisi — kanalın en büyük
  tekil riski telif değil, TAM OLARAK bu. Gerçek aralık artık
  `max(52 saat, 24 saat / bekleyen proje sayısı)`; 52 saat haftada 3 şarkı hedefinden
  geliyor (7×24/3 = 56 saat, eksi golden-hour kaymasının haftalık sürüklenme payı).
  **Geri doldurma bu tabandan MUAF**: `state.json`'ında zaten bir `youtube_video_id` olan
  proje (ör. YouTube'a çıkmış ama Instagram'ı yarım kalmış şarkı) yeni bir yayın değil,
  yarım kalmış bir işin tamamlanmasıdır — kanalın yükleme desenini etkilemez. Kontrol, bu
  koşuda işlenecek dilimin TAMAMINA bakıyor:
  `any("youtube_video_id" not in _load_state(p) for p in pending[:count])` — dilim
  `main()`'deki `batch = pending[:count]` ile aynı olmak ZORUNDA; `count > 1` olduğunda ilk
  sıradaki bir geri doldurma, arkasındaki yeni şarkıya muafiyet kazandırmasın diye
  (2026-09-11). Log'a hangi kuralın beklettiği ("yeni yayın tabanı" / "günlük pencere
  bölüşümü") yazılıyor.
- **Platform başına FARKLI golden-hour stratejisi (`config.GOLDEN_HOURS`,
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
    için güvenli marj var. **EXPIRED'ı `try_publish_pending()` YENİDEN OLUŞTURMAZ**
    (bu belgede öyle yazıyordu, YANLIŞTI): bayat kaydı siler, operatöre
    `instagram_upload.py --project ...` komutunu basıp çıkar — yeniden paylaşım
    hacim etkisi olan bir karar, kendiliğinden tetiklenmemeli. Kapı da artık
    "media_id var mı" değil "bekleyen konteyner SON yayından yeni mi"
    (`_konteyner_yayindan_yeni`); eski hâli iki konteyneri 6 gün bloklamıştı.
  - **TikTok** — Content Posting API'de de native zamanlanmış yayın YOK, ayrıca
    henüz audit'ten geçmediği için zaten sadece taslak/gelen kutusuna yükleyip
    kullanıcının uygulamadan ELLE yayınlamasını gerektiriyor (bkz. aşağıdaki
    madde). Bu elle adımı unutmamak için kullanıcı isteğiyle `notify.py` (ntfy.sh
    üzerinden ücretsiz telefon push bildirimi) eklendi — `tiktok_upload.py`nin
    `notify_pending_publish()`'i golden-hour'a girildiğinde bir kereliğine
    hatırlatma gönderiyor (`state.json`'da `tiktok_notified` ile tekrar
    göndermiyor, TikTok API'sinden kullanıcının gerçekten yayınlayıp
    yayınlamadığını öğrenmenin bir yolu yok). **`notify_config.json` (gitignored,
    `{"ntfy_topic": "..."}`) BUGÜNE KADAR HİÇ YOKTU** — yani `notify.py` yazıldığından
    beri TEK BİR push bildirimi gitmedi; 2026-09-11'de kuruldu. Dosya yoksa otomasyon
    hâlâ bozulmuyor ama artık SESSİZ de değil: `notify.send()` kanal yoksa
    `notify.uyar_bir_kez()` ile koşu başına BİR kez log'a "bu koşudaki TÜM bildirimler
    atlanıyor" satırı yazıyor, ve `notify.is_configured()` sayesinde çağıranlar (ör.
    `tiktok_upload.notify_pending_publish()`) "bildirim gitmedi"nin sebebini
    golden-hour beklemesinden ayırt edebiliyor.
  - **Facebook** — YouTube gibi NATIVE zamanlama desteği VAR (Reels'te
    `video_state=SCHEDULED` + `scheduled_publish_time`, uzun formatta
    `published=false` + `scheduled_publish_time`), bu yüzden orada da kendi
    kuyruğumuza gerek yok ve `--no-schedule` orada da geçerli. **Telegram/Bluesky**'da
    zamanlama yok — script o an çalıştığında gönderiliyorlar.
- **Instagram konteynerinde 23 SAATLİK YAŞ KAPISI, ve o kapı `_konteyner_yayindan_yeni()`
  ile Graph API çağrısının da ÖNÜNDE** (`instagram_upload.KONTEYNER_OMRU_SN`,
  `_konteyner_bayat()`, 2026-09-12): `Gece Sürüşü`/`Kalbim Oynuyor` state'lerinde 7 GÜNLÜK
  konteynerler duruyordu ve her golden-hour'da yayınlanmaya çalışılıyordu. Instagram bu
  ölü konteynerler için `status_code` olarak EXPIRED **DÖNDÜRMÜYOR** — `media_publish`
  adımında HTTP 500 `{"is_transient": true}` veriyor, yani "geçici" diyen KALICI bir hata
  (11 Eylül'de 8 boşa API çağrısı; kendiliğinden ASLA düzelmiyor). Bu yüzden ölçüt
  Instagram'ın cevabı değil BİZİM yazdığımız `instagram_container_created_at` damgası.
  **24 değil 23 saat, ve payın gerekçesi var**: damga YEREL saatle yazılıyor, Instagram'ın
  saati bizimkiyle birebir aynı olmak zorunda değil, ve sınıra dakikalar kala yayın
  denemesi yarış durumu demek. 23 saat, golden-hour pencereleri arasındaki en kötü aralığı
  (~14 saat) hâlâ rahatça kapsıyor — yani bu kapı GERÇEKTEN bekleyen hiçbir konteyneri
  erken düşürmez. **SIRA BİLİNÇLİ**: kapı en başta olduğu için, konteyner son yayından
  yeni OLMASA bile (yani "zaten yayınlanmış" dalından çıkılacak olsa bile) ölü kayıt
  temizleniyor. Aşağıda olsaydı o kayıtlar state'te SONSUZA KADAR kalırdı — canlıda tam
  olarak böyle **13 ölü kayıt** birikmişti ve `auto_process` her koşuda 13 sahte "bekleyen
  konteyner" satırı basıyordu (gerçekte bekleyen TEK proje vardı); 2026-09-12'de temizlendi.
  Damga YOKSA/BOZUKSA kapı KAPANMIYOR (False): "yaşını bilmiyorum"u "sil"e çevirmek,
  gerçekten bekleyen bir konteyneri sessizce düşürüp gönderiyi hiç yayınlamamak olurdu.
- **Instagram'da yeniden deneme YALNIZ 5xx + `is_transient: true`; taşıma hatası (timeout /
  bağlantı kopması) BİLEREK DENENMİYOR** (`instagram_upload._graph_istek`, `_gecici_5xx_mi`,
  2026-09-12). Ayrım tek cümlede: **tam bir HTTP yanıt geldiyse** Instagram isteği
  İŞLEMEDİĞİNİ kendi söylüyor → yayın oluşmadı, tekrar güvenli; **yanıt kaybolduysa** istek
  işlenmiş OLABİLİR ve `media_publish` **İDEMPOTENT DEĞİL** — aynı Reel kanalda iki kez
  çıkar, ki bu deponun en büyük tekil riskinin ("inauthentic / toplu üretilmiş AI içerik")
  ta kendisi. Bu yüzden `except RequestException` dalı HİÇ yeniden denemiyor ve öyle
  KALMALI (aynı gerekçe Telegram `sendVideo`, Bluesky `createRecord`, Facebook `/videos`,
  YouTube `videos.insert`/`comments.insert` için de geçerli). Çıplak 5xx TEK BAŞINA da
  yetmiyor: bayat konteynerler de 500 veriyordu ve orada tekrar denemek yalnızca boşa API
  çağrısıydı, çünkü hata KALICIYDI — bu yüzden Instagram'ın KENDİ `is_transient`
  işaretine bakılıyor. 4xx bu dala GİRMİYOR (400/401/403 = kimlik/izin/kota/politika;
  tekrar kotayı yakar ve hız sınırına takar). Tavan dar (8+32 sn, en kötü 40 sn; jitter,
  backoff büyütme, pencere kontrolü YOK): kapatılan risk tek ve dar — golden-hour
  penceresinin SON dakikalarına denk gelen gerçek bir geçici 500'ün doğal tekrar şansının
  kalmaması. **`upload/ag_yeniden_deneme.py`'ye EKLENMEDİ, bilerek**: o modül TAŞIMA
  KATMANI istisnalarını (`requests.exceptions.*`) sınıflandırıyor; HTTP 500 bir istisna
  DEĞİL, BAŞARIYLA ALINMIŞ bir yanıttır — `sinifla()` bu vakayı hiç görmez.
- **`notify.send()` ntfy'ye JSON GÖVDESİYLE gönderiyor, HTTP BAŞLIĞIYLA DEĞİL**
  (2026-09-11 arızası): eski sürüm başlığı `headers={"Title": ...}` ile yolluyordu, ama
  `requests`ın altındaki `http.client` HTTP başlıklarını **latin-1** ile kodluyor ve
  Türkçenin `ı İ ş ğ` harfleri latin-1'de YOK (`ç ö ü` VAR — bu yüzden arıza tüm
  başlıklarda değil sadece bir kısmında görünüyordu, yanıltıcıydı). `UnicodeEncodeError`
  `send()` içinde yakalanıp sessizce `False` dönüyordu: 12 bildirim başlığının **5'i
  ölüydü**. Başlığa değişken metin koyan HER yeni bildirim aynı tuzağa düşerdi; JSON
  gövdesi (topic/title/message hepsi gövdede, UTF-8) kısıtı KÖKÜNDEN kaldırdı. ntfy'nin
  JSON publish uç noktası **KÖK yola** POST istiyor — topic URL yoluna KONMAZ
  (`https://ntfy.sh/`, `https://ntfy.sh/<topic>` değil). Koruma:
  `tests/test_notify_turkce_baslik.py` (depodaki TÜM `notify.send()` çağrılarının
  başlıklarını `ast` ile tarıyor).
- **`notify.uyar_bir_kez()` TELEFONA GİTMEZ — yalnızca log'a yazar.** Telefona giden TEK
  yol `notify.send()`, ve otomasyonda onu çağıran TEK yer `saglik_kontrol._bildir()`
  (günde bir). Kapı noktalarındaki docstring'ler `uyar_bir_kez`'i bildirim gibi okutuyor;
  DEĞİL. Bu ayrım 2026-09-12'de gerçek bir boşluğa sebep oldu: `uyumluluk` kapıları
  fail-closed yapıldıktan sonra kapanan bir kapı projeyi atlıyor ve geriye YALNIZCA bir
  log satırı kalıyor — yani kanal günlerce sessizce durabilir ve kimse haberdar olmazdı
  (`saglik_kontrol.yayin_durgunlugu` tam bu boşluk için eklendi). Kural: bir korumanın
  operatöre ULAŞMASI gerekiyorsa `saglik_kontrol`'e adım ekle; `uyar_bir_kez` "koşu başına
  bir kez log'a" disiplinidir, alarm değil.
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
  **2026-09-05'te aynı kural `config.HOOK_LINES`/`HOOK_LINES_EN` ve
  `ENGAGEMENT_QUESTIONS`/`ENGAGEMENT_QUESTIONS_EN`'e de genişletildi** — bu
  satırlardaki "Bu şarkı tamamen yapay zeka ile yapıldı"/"Human or AI? You
  decide" gibi AI-vurgulu hook/soru metinleri (ana kataloğun HER caption'ının
  başında görünüyordu) kaldırılıp AI'dan bağımsız hook'larla değiştirildi
  (kullanıcı kararı: görünür "AI ile yapıldı" bilgilendirmesi mümkün olduğunca
  azaltılsın, sadece ZORUNLU/arka-plan mekanizmalarda kalsın). **DJ Famous
  (`dj_sets/`) BUNDAN MUAF** — orada AI-üretimi bilinçli olarak açık şekilde
  belirtiliyor (gerçek kişi içeriği, farklı tasarım kararı), kendi ayrı caption
  metni kullanılıyor, `HOOK_LINES`'a bağlı değil.
- **Instagram'da yayınlanmış bir medyayı API'den silmek MÜMKÜN DEĞİL** (bu
  projenin kullandığı "Instagram API with Instagram Login" — `instagram_auth.py`,
  `graph.instagram.com` — ile): medya silme (`DELETE /<media-id>`) endpoint'i
  SADECE eski "Facebook Login" akışını (bir Facebook Sayfası üzerinden
  bağlanan Graph API) destekliyor, WebSearch ile doğrulandı (2026-09-05).
  Denendiğinde `IGApiException code 100 / error_subcode 33` ("Unsupported
  delete request... does not support this operation") dönüyor. Eski bir
  gönderiyi kaldırmak gerekiyorsa (ör. kapak tasarımı değişip eski post yeni
  bir kopyayla değiştirildiğinde) bunu API'ye eklemeye ÇALIŞMA — kullanıcı
  Instagram uygulamasından elle silmeli (bkz. `buyume_kontrol_listesi.md`,
  A6 — 2026-09-05 kapak-tasarımı migrasyonunun canlı örneği).
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
- **TikTok'a ELLE yayın yaparken caption/ilk yorum `upload/tiktok_publish_plan.py`'den
  ALINIR, asistanın kafasından UYDURULMAZ**: modülü ÇALIŞTIRAN hiçbir kod yok (ne
  `auto_process.py`, ne `tiktok_upload.py`, ne Görev Zamanlayıcı) — var olma sebebi tam
  olarak bu elle adım. ("Hiçbir yerden referans almıyor" YANLIŞTI ve modülü ölü
  gösteriyordu: `.claude/skills/fms-tiktok-yayin/SKILL.md`, `buyume_kontrol_listesi.md` ve
  `haftalik_is_akisi.md` ona BELGE olarak referans veriyor; olmayan şey otomatik ÇAĞRI.)
  TikTok yayını higgsfield MCP bağlayıcısı
  üzerinden bir asistan oturumundan yapılıyor (kendi app'imizin `video.publish` izni
  yok); metin o sırada yeniden yazılırsa boru hattının ürettiğinden farklı olur.
  Doğru kullanım:
  `python upload/tiktok_publish_plan.py --project "projects/<isim>" --json`
  — caption `social_text.build_caption()`'dan TAZE hesaplanıyor (`state.json`'daki
  `tiktok_suggested_caption` eski projelerde yok), ilk yorum ve kapak ipucu da
  aynı çıktıda. Detay: modülün kendi docstring'i.
  **2026-09-12'de bu modülde İKİ arıza birden bulundu ve düzeltildi, ikisi de
  "elle yapılan adım kimsenin denetlemediği tek yol" sınıfından:**
  (a) **Politika kapısı bu yolu HİÇ kapsamıyordu.** `uyumluluk.kontrol()`
  render'dan ve yüklemeden önce otomatik çalışıyor, ama TikTok yayını tasarım
  gereği o hattın dışında — boru hattı yalnızca TASLAK yüklüyor. Kuru tarama,
  bekleyen 20 taslağın ikisinin `hazir: True` dediğini gösterdi:
  `dj_sets/City Pulse Set` (state.json'ında `telif_eser` + `telif_araliklari`
  kayıtlı, `uyumluluk` HATA veriyor) ve `projects/Küllerimden Geç`
  (`Yeniden Doğacağım` ile aynı md5; TikTok'ta İKİSİ de taslak, yani tekrar
  orada henüz ÖNLENMİŞ değil). `build_plan()` artık `uyumluluk.kontrol(...,
  "yukleme")` çağırıyor (HATA → `engel`) ve TikTok'a ÖZEL bir ikiz kapısı var
  (`_tiktok_ikiz_kapisi`) — çünkü `uyumluluk`'un muafiyeti *YouTube*'da bir
  tarafın çekilmiş olması, TikTok hakkında hiçbir şey söylemiyor. Kapı
  çökerse `hazir` **False** olur (sessizce açılmaz). `buyume_kontrol_listesi.md`
  A4'ün düz metindeki "ikisi aynı ses, körü körüne yayınlama" uyarısı artık
  kodda.
  (b) **Modül bu makinede caption'ı HİÇ basamıyordu.** Windows'ta
  `sys.stdout.encoding` ANSI kod sayfası (`cp1254`) ve üretilen HER caption
  `config.HOOK_LINES`'tan gelen bir emoji taşıyor — hem düz hem `--json`
  çıktısı tam caption satırında `UnicodeEncodeError` ile çöküyordu. Yani
  "caption'ı uydurma, buradan al" diyen modülün verdiği tek şey bir
  traceback'ti. `_cikti_utf8()` (konsol kod sayfası 65001 + akışlar UTF-8)
  `main()`'in ilk satırı. Koruma: `tests/test_tiktok_plan_politika_kapisi.py`
  (alt süreçte `PYTHONIOENCODING=cp1254` ile aynı koşulu kuruyor).
  (c) **`build_plan` iki alanı (`tiktok_published_at`, `tiktok_dogrulandi`) OKUYORDU,
  YAZAN hiçbir kod yoktu** — 22 klasörün hiçbirinde mevcut değildi; ikiz kapısının en
  ağır kuralı ("ikiz zaten yayınlanmış → ENGEL") ölü daldı. `--yayinlandi` /
  `--yayinlandi-hepsi` (etkileşimli, tek tek onay) / `--dogrulandi` eklendi.
  `tiktok_dogrulandi` proje değil **KANAL** seviyesinde okunuyor (proje bazlı hâli
  ispaten sabit `SELF_ONLY` üretiyordu). Üç soru: çağıran KULLANICININ KENDİSİ;
  zamanlayıcı görevi YOK (olgunun tek kaynağı insan); çalışmadığı `--yayinlandi-hepsi
  --dry-run` listesi 20'de takılı kaldığında görülür. Koruma: `tests/test_tiktok_yayin_isaretleme.py`.
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
  **Artık `dj_sets/` klasörünü de aynı şekilde izliyor** (`dj_famous_process.py`'yi
  tetikleyerek) — başlangıçta sadece `projects/` (ana katalog) kapsanıyordu, kullanıcı
  Suno'dan bir DJ Famous setini indirip `dj_sets/<isim>/` klasörüne elle kaydederken
  bu boşluk fark edildi (`_scan_once()` → parametrik `_scan_dir(base_dir,
  trigger_script)`'e genelleştirildi, `projects/` ve `dj_sets/` için ayrı ayrı çağrılıyor).
  **AÇIK ARIZA — 2026-09-12'de bulundu, düzeltmesi bu satır yazılırken AKIŞTA (paralel
  ajan). Çözülmüş sayma; kapandığını `git log -- watch_projects.py` ile DOĞRULA.**
  `watch_projects.COVER_NAMES` yalnızca `cover.jpg/jpeg/png` içeriyor — **`cover_vertical.png`
  YOK**, oysa `generate_cover.py` kapağı İKİ oranda üretiyor (yukarıdaki kapak maddesi).
  Sonuç zinciri: 28 dikey kapak her dakika "sahipsiz görsel" sanılıyor → her biri
  `_is_stable()` içinde `time.sleep(3)` yiyor → tarama **84 saniye** sürüyor (ÖLÇÜLDÜ:
  `gorev_izleri/watch_projects.log`, arka arkaya "BİTTİ ... süre=84.2sn"). Tek başına
  sadece israf; üç şeyle birleşince zarar gerçek: (1) watcher görevinin
  `ExecutionTimeLimit`'i **5 dakika**; (2) `_trigger_script` ENGELLEYİCİ (`subprocess.run`,
  tetiklenen `auto_process.py` bitene kadar bekliyor); (3) süre limiti dolunca Görev
  Zamanlayıcı süreç AĞACINI öldürüyor. Yani tetiklenen koşu ortasından kesiliyor, kilidi
  kalıyor ve saatlik hat `LOCK_STALE_SECONDS` (4 saat) boyunca duruyor. En pahalı sonucu
  ise render'ın yarıda kesilmesi: `auto_process._is_rendered()` YALNIZCA dosya VARLIĞINA
  bakıyor (`os.path.isfile`), yani **yarım bir mp4'e True der** ve bir sonraki koşu o bozuk
  videoyu render etmeden YÜKLER.
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
- **Üç görev de betikleri DOĞRUDAN değil `gorev_sarmalayici.py` üzerinden çalıştırıyor**
  (2026-09-12): `pythonw.exe`'de `sys.stdout`/`sys.stderr` **None**'dır ve Görev
  Zamanlayıcı'nın stderr'i yönlendireceği bir yer yoktur — bir betik KENDİ log dosyasını
  açmadan ÖNCE ölürse (import hatası, sözdizimi hatası, eksik bağımlılık, DLL) geriye TEK
  BAYT iz kalmıyordu; TaskScheduler Operational olay günlüğü de bu makinede KAPALI, yani
  ikinci bir kaynak da yok. Kanıt: 2026-09-11'de 12:12/13:12/14:12 saatlik koşuları log'da
  HİÇ görünmüyor (yerlerinde +20 dk kaymış telafi koşuları var), ve 02:12'deki "eski kilit
  dosyası (10732s)" satırı kilidini bırakmadan ÖLEN bir koşunun izi. Sarmalayıcı
  `gorev_izleri/<betik>.log`'a BAŞLADI / ÇÖKTÜ+traceback / BİTTİ rc+süre yazıyor; böylece
  üç arıza biçimi ayırt edilebiliyor: **çöktü** · **takıldı/öldü** (BAŞLADI var, eşleşen
  BİTTİ YOK) · **hiç tetiklenmedi** (o saate ait BAŞLADI bile yok). Dört ayrıntı gerekçeli:
  - **Kapanış ölümleri artık yakalanıyor**: `calistir()` dönerken hata akışı KAPATILMIYOR
    ve `sys.stderr` `None`'a geri ALINMIYOR. Bir betiğin ölümü `calistir()` döndükten
    SONRA da olabiliyor (`atexit` kancası, `__del__` sonlandırıcısı, arka plan thread'i);
    eski sürümde böyle bir koşu "BAŞLADI + BİTTİ rc=0" (tertemiz) görünüyordu ve Görev
    Zamanlayıcı da `LastTaskResult=0` diyordu — sahte bir betikle ÖLÇÜLDÜ.
  - **`_buda()` ATOMİK** (`.tmp` + `fsync` + `os.replace`): eski sürüm hedefi
    `open(yol, "w")` ile açıyordu, yani ÖNCE sıfırlayıp sonra dolduruyordu — ve budama HER
    koşunun İLK işi (dakikalık izleyicide günde 1440 kez). Bu makinede süreçler
    `TerminateProcess` ile ölüyor (pile geçiş, `ExecutionTimeLimit`), yani o pencerede
    öldürülmek tam da ölümün KANITI olacak dosyayı SIFIRLAMAK demekti. `state_io.py` aynı
    dersi `state.json` için zaten öğrenmişti.
  - **`os.chdir(KOK)`** — `-WorkingDirectory`'ye GÜVENİLMİYOR: boru hattı göreli yollarla
    çalışıyor ve yanlış cwd HATA VERMİYOR, sadece "bulunamadı" oluyor
    (`find_ready_projects()` boş liste döner, log'a "İşlenecek proje yok" yazılır ve
    otomasyon HER KOŞUDA başarıyla hiçbir şey yapmaz). `uyumluluk.KOKLER` vakasının
    birebir aynısı. Fark varsa hem düzeltiliyor hem İZ bırakılıyor.
  - **İz dosyasına giden TÜM yollar `gizli_maskele`'den geçiyor**: `_yaz()` (tek yazma
    noktası), `traceback.format_exc()` ve yönlendirilmiş `sys.stderr` (`_MaskeliAkis`).
    `writelines` AYRI tanımlı, `buffer`/`detach` KAPALI — `__getattr__` ile alt akışa
    devredilseydi maskeleyici ATLANIRDI (traceback modülü o yolları kullanabiliyor).
    Gerekçe: `try/except` ile sarılmamış, token taşıyan bir `requests` çağrısının
    `ConnectionError` mesajı TAM istek URL'ini taşır (2026-09-04'te `dj_famous_process.log`'a
    gerçek bir Instagram token'ı böyle düştü) ve `log_rotate.trim_log()` bu klasöre
    UĞRAMIYOR — buraya düşen sızıntı sonradan TEMİZLENMEZ, maskeleme YAZARKEN olmak
    zorunda. `gizli_maskele` yüklenemezse sarmalayıcı çalışmaya DEVAM eder (maskelenmemiş
    iz, izsizlikten iyidir) ama sessiz kalmaz: koşu başına bir "MASKELEYİCİ YÜKLENEMEDİ"
    satırı düşer.
- **Görev Zamanlayıcı 2026-09-12'de YENİDEN KURULDU — "makine pilde iken üç görev de
  durur" notu ARTIK GEÇERSİZ.** Doğrulandı: üç görevin de `Arguments` alanı artık
  sarmalayıcıyı MUTLAK yolla çağırıyor, ve `DisallowStartIfOnBatteries` /
  `StopIfGoingOnBatteries` üçünde de **False**. Eskiden ikisi de True'ydu: makine fişten
  çıkınca otomasyonun TAMAMI — dakikalık watcher, yani ikinci emniyet ağı dahil — sessizce
  duruyordu; 11 Eylül 21:12 → 12 Eylül 06:46 arasındaki 9,5 saatlik boşluk (9 kaçan tetik)
  tam olarak buydu. **Kurulum YÜKSELTİLMİŞ PowerShell gerektiriyor**: görevler yükseltilmiş
  bağlamda kurulu olduğu için normal kullanıcıda `Unregister-ScheduledTask`
  `HRESULT 0x80070005 Erişim engellendi` veriyor — silme başarısız olduğu için hiçbir görev
  KAYBOLMUYOR (zararsız), ama script yarıda kalır ve kurulum yapılmamış olur.
  Doğrulama: `gorev_izleri/` altında üç dosyanın da tazelenmesi.
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
- **`uyumluluk.py` politika kapısı İKİ ayrı aşamada OTOMATİK çalışıyor**: render'dan önce
  `render.py → validate_project.validate() → uyumluluk.kontrol(proje, "render")`, yayından
  önce `auto_process.py`/`dj_famous_process.py` içinden `kontrol(proje, "yukleme")`. Ağa
  ÇIKMAZ (güncel politika araştırması `icerik-uyumluluk-ajani`'nın işi; bu modül hızlı,
  yerel, bilinen kuralları üretilen dosyalara uyguluyor): telif eşleşmesi işareti, aynı
  sesin başka projede tekrarı (md5, önce boyut ön filtresi), derlemede bölüm damgası/
  küratörlük notu, `meta.json`'da AI beyanının kapatılmış olması, bugün kaç yükleme
  yapıldığı (`GUNLUK_YUKLEME_UYARI = 3`). **HATA bulursa o proje yayınlanmaz**, uyarı
  sadece log'a düşer.
  **Bozuk `state.json` HATA, bozuk `meta.json` UYARI — asimetri BİLİNÇLİ.** Eskiden ikisi
  de sessizce `{}` sayılıyordu; `state.json`'da bu, `telif_araliklari`yi boş gösterip
  "bu içerik yeniden yayınlanmamalı" KAPISINI sessizce açıyordu (City Pulse'ta bir kez
  yaşanan olayın tekrarı — geri dönüşü yok). `meta.json`'da açılan bir kapı YOK: AI
  beyanını gerçekten yapan mekanizma bu dosya değil, `youtube_upload`'ın koşulsuz
  `containsSyntheticMedia: True`'su; kaybı uyarı düzeyinde ve meta ELLE yazılan bir
  dosya, bir yazım hatasının tüm kanalı durdurması ağır kaçar. Gerekçenin tamamı
  `uyumluluk.kontrol()` içindeki yorumda — değiştirmeden önce ORADAN oku.
  **2026-09-12: kapı artık YEDİ çağrı noktasında ve HEPSİ FAIL-CLOSED.** Noktalar: ana hat
  (`auto_process.process_project`), `dj_famous_process.process_set`, `validate_project`
  (render), İKİ geri doldurma süpürgesi (`upload/ek_platform_backfill.py`,
  `upload/facebook_backfill.py`) ve `dj_clips.py`'de İKİ nokta — `yayina_uygun_mu`'nun SON
  adımı (bilerek en sonda: üstündeki kapılar saf state okuması, bu ise diskteki tüm
  kökleri gezip gerektiğinde md5 hesaplıyor) + `kesit_yayinla`'nın İLK adımı (ağa çıkılan
  son nokta; `kesit_yayinla` dışarıya açık bir giriş ve `yayina_uygun_mu`'dan geçmek
  ZORUNDA değil, orada `return` değil `raise` var ki süpürge "yayınlandı" sanmasın).
  `upload/tiktok_publish_plan.build_plan()` sekizinci kapı ama farklı sınıf: orası
  otomasyon değil, ELLE yapılan adımın kapısı (yukarıdaki TikTok maddesi).
  **Fail-closed gerekçesi:** eski kod `kontrol()`ün istisnasını "görmezden geliniyor" diye
  loglayıp DEVAM ediyordu — yani garanti yalnızca kapı düzgün DÖNDÜĞÜNDE geçerliydi.
  "Bilmiyorum" ile "temiz" aynı şey DEĞİL; bu kapıya bağlı iki gerçek koruma (City Pulse
  Set'in HÂLÂ açık telif itirazı, `Küllerimden Geç` md5 kopyası) yanlış tarafa düşerse
  sonuç GERİ ALINAMAZ bir yayındır (Instagram'da yayınlanmış medya API'den silinemiyor).
  Ters yönün maliyeti bu projenin BİR koşu gecikmesi. KAPSAM: `return` yalnızca O PROJEYİ
  atlıyor, koşuyu değil — `for project_dir in batch` devam eder, `finally`'deki süpürgeler
  yine çalışır.
  **Aynı gün GİZLİ bir İKİNCİ fail-open da kapandı**: `if _uh: return` kararı `try`
  bloğunun İÇİNDEydi ve `uyumluluk.rapor_yaz()` ile AYNI `except`i paylaşıyordu — yani
  raporlama adımı patlarsa HATA kararı sessizce kaybolup yayın devam ediyordu. Artık karar
  ile rapor AYRI sarmalanıyor: kararın girdisi (`_uh`) zaten elde; rapor yazılamazsa
  log'a ismiyle düşer ama kapı kararı BUNDAN ETKİLENMEZ. Ders genel: bir kapının kararını
  bir RAPORLAMA adımıyla aynı `try`a koymak, kapıyı o raporun sağlamlığına bağlar.
- **DJ setleri VE derlemeler Content ID karantinasından geçer (`dj_tarama_kontrol.py`)**:
  YouTube'a önce `private` yüklenir (`dj_tarama_bekliyor`), diğer platformlara HİÇ
  gitmez; `config.DJ_TARAMA_BEKLEME_SN` (2 saat) dolunca SAATLİK koşudan kontrol edilir
  (haftalık koşuya bağlansaydı ikinci aşama bir sonraki haftaya kalırdı), temizse `public`
  olup kalan platformlar devam eder.
  **"Araştırıldı, YOK" bilgisi — tekrar aramaya değmez**: YouTube Data API, partner
  olmayan normal kanallara Content ID itiraz listesini AÇMIYOR; öyle bir uç yok
  (2026-09-11'de 20 videoda doğrulandı — itiraz varken de her şey `processed` görünüyor).
  Bu yüzden `contentDetails.regionRestriction.blocked` alanına bakılıyor ve bu bir
  VARSAYIM; ikinci ağ olarak süre dolduğunda sonuç ne olursa olsun telefona bildirim
  gidip Studio'dan ELLE bakılması isteniyor.
  **`videos.update` KISMİ GÜNCELLEME YAPMAZ**: `part` içinde yer alıp gövdede verilmeyen
  mutable alanlar SİLİNİR. İlk sürüm yalnızca `privacyStatus` gönderiyordu ve her temiz
  taramada `containsSyntheticMedia`/`selfDeclaredMadeForKids`'i siliyordu — yani
  `dj_sets/README.md`'nin ilk taahhüdü her sette kayboluyordu. Üstelik oku-birleştir-yaz
  TEK BAŞINA yetmiyor: `videos.list(part="status")` `containsSyntheticMedia`'yı GERİ
  DÖNDÜRMÜYOR (yazılabilir ama OKUNAMAZ), yani round-trip onu sessizce kaybettirir —
  o alan her yazımda AÇIKÇA yeniden set ediliyor.
- **`upload/set_privacy.py` AYNI TUZAĞIN İKİNCİ KURBANIYDI: zorunlu AI beyanını
  SİLİYORDU** (2026-09-12'de düzeltildi, GEÇMİŞ hasar HENÜZ onarılmadı). Gövdede yalnızca
  `privacyStatus` gidiyordu, yani betiğin HER çalıştırması dokunduğu videonun
  `containsSyntheticMedia: True` (YouTube'a karşı ZORUNLU beyan) ve
  `selfDeclaredMadeForKids: False` alanlarını sessizce siliyordu — ve
  `videos.list(part="status")` `containsSyntheticMedia`'yı GERİ DÖNDÜRMEDİĞİ için "hangi
  videoda silinmiş" diye API'den bakmanın YOLU YOK, yalnızca Studio'dan görülür. Betik
  artık mevcut `status`u okuyup birleştiriyor (`guvenli_status_govdesi()`). Hasar üç
  yazım olayından geliyor — `444daac` + `2d6da01` (2026-09-07, tüm katalog Content ID
  taraması için unlisted'a çekilip geri public yapıldı) ve 2026-09-11 `Küllerimden Geç` —
  yani **~32-42 videoda beyan silinmiş KABUL EDİLMELİ**. Onarım için
  `upload/ai_beyani_onar.py` yazıldı: ELLE çalışır, hiçbir zamanlayıcı görevine BAĞLI
  DEĞİL (video başına 51 birim kota; saatlik hatta bağlamak asıl yüklemeleri düşürürdü —
  2026-09-06'da `_drain_golden_hour_queue` ile tam olarak bu oldu), **varsayılanı KURU
  KOŞU** (`--uygula` açıkça verilmeli), her video KENDİ mevcut gizliliğine yazılır
  (gizlilik YouTube'dan okunur, okunamazsa video ATLANIR) ve bir "güvenlik kemeri" hiçbir
  videoyu `unlisted`/`private`'tan `public`'e çeviremez. Hedef listesi SABİT DEĞİL,
  `uyumluluk.proje_klasorleri()`'nden türetiliyor (bu deponun "bayatlayan sabit liste"
  hata sınıfı). 2026-09-12 itibarıyla `upload/ai_beyani_onarim.json` YOK — yani kampanya
  HENÜZ HİÇ ÇALIŞMADI.
- **Kilit deseni: `O_CREAT|O_EXCL` ile ATOMİK alma + nabız `log()`'un İÇİNDE**
  (`auto_process.py`; `dj_famous_process.py` aynı desen): `os.path.exists` + `open`
  ikilisi yarış durumu yaratıyordu, iki süreç aynı anda "kilit yok" görüp ikisi de devam
  edebiliyordu. Bayat kilidin devralınması da (`LOCK_STALE_SECONDS = 4 saat`) aynı
  O_EXCL'le korunuyor, yoksa bayat kilidi iki süreç birden devralırdı. Nabzın (kilit
  dosyasının `os.utime` ile tazelenmesi) `log()` İÇİNDE olması bilinçli: "her uzun
  adımdan sonra tazele" listesine bağlamak, yeni bir adım eklendiğinde UNUTULACAK bir
  liste demektir — her adım zaten bir satır bastığı için nabız adım listesiyle
  kendiliğinden büyüyor.
- **Derleme başlık kuralı**: derlemeler `<ad> (Sözleri) | Türkçe Hip-Hop Şarkısı` diye
  çıkıyordu — derlemenin sözleri YOK, ve 13 parçalık karma bir derlemeye `meta.json`'daki
  tek `theme` alanından tür vermek düpedüz yanlıştı. Artık `build_snippet`'te ayrı bir
  derleme dalı var: tür, parçaların temalarının ÇOĞUNLUĞUNDAN türüyor ve çoğunluk yarıyı
  GEÇMİYORSA "Müzik" deniyor (`_derleme_tur_bilgisi`, `adet * 2 > len(temalar)`) — karma
  bir derlemeye "Hip-Hop Derlemesi" demek aynı yanlışın yumuşak hâli.
- **`derleme.py`'nin telif kapısı `telif_araliklari` YANINDA `telif_eser`'e de bakıyor**
  (`TELIF_ISARETLERI`, 2026-09-12): bu iki alanı da depoda **HİÇBİR KOD ÜRETMİYOR** —
  `dj_tarama_kontrol.py` karantinayı kurar ama `telif_*` YAZMAZ, alanlar ELLE yazılıyor.
  Yani kapı "operatör HER İKİ yarıyı da doldurur" KONVANSİYONUNA dayanıyordu: Content ID
  eşleşmesi eserin TAMAMINI kapsadığında ya da aralıklar henüz çıkarılmadığında
  `telif_eser` tek başına yazılır ve o şarkı derlemeye GİRERDİ. Maliyet asimetrik olduğu
  için karar kolay: yanlış pozitifin bedeli bir şarkının bir derlemede eksik kalması
  (üstelik log'a düşerek), yanlış negatifin bedeli City Pulse Set'in HÂLÂ açık olan telif
  itirazının üstüne İKİNCİ bir ihlal. `telif_notu` BİLEREK listede YOK: o serbest bir
  metin alanı ve "kontrol edildi, telif yok" gibi TERSİ bir cümle de taşıyabilir — kapıyı
  bir notun VARLIĞINA bağlamak "işaret" ile "yorum"u karıştırmak olurdu. Boş liste (`[]`)
  işaret SAYILMAZ (state göçünde temizlenmiş kayıt tam böyle görünüyor), bozuk tip ise
  SAYILIR: "bu alanı okuyamıyorum" ile "temiz" aynı şey değil.

- **`upload/youtube_playlists.py` DÖRT katmanlı, ve üyelik kapısı `state.json` DEĞİL
  YouTube'un KENDİSİ**: (1) tarz playlist'leri (`config.THEMES`) — keşif/kimlik;
  (2) `_tum_sarkilar` — SADECE ana kataloğun (`projects/`) uzun formatları tek zincirde,
  enerji eğrisine göre sıralı (`derleme._enerji` İÇE AKTARILIYOR, kopyalanmıyor —
  kopyalamak `state_io`ya yol açan hatanın ta kendisiydi); (3) `_shorts` AYRI, çünkü
  her Short aynı şarkının dikey kesiti: tek listede olsalardı dinleyici aynı şarkıyı
  arka arkaya iki kez duyardı. (4) `_derlemeler` — derlemelerin kendi rafı; 2026-09-11'de
  "Gece Seansı Vol. 1" canlı olarak YANLIŞ listeye girdikten sonra eklendi: başlıktaki tür
  `_derleme_tur_bilgisi` ile parçaların ÇOĞUNLUĞUNDAN türerken playlist seçimi hâlâ
  `meta["theme"]`e bakıyordu, yani aynı karar iki yerde iki ayrı kuralla veriliyordu.
  Karma bir derlemenin tarz playlist'i yok — dördüncü katman olmasa kanalın en uzun, en
  çok izlenme süresi üreten varlığı HİÇBİR listede kalmazdı.
  "Zaten ekli mi" kapısı `playlistItems.list` (1 birim,
  süreç ömrü önbellekli); eskiden `state.json`'daki `youtube_playlist_id`, yani YEREL bir
  İDDİA kapı olarak kullanılıyordu ve bir videoyu ("Beton Krallığı") kalıcı olarak
  listesiz bırakmıştı.
  **Kartlar ve son ekranlar YouTube Data API v3'te YOK** (kaynak listesinde `cards`/
  `endScreens` geçmiyor) — sadece Studio'dan; araştırmaya değmez. İzleyiciyi bir sonraki
  videoya taşıyan yüzeylerden API'den yönetilebilen TEK şey playlist'ler.
  (`PlaylistImages` kaynağı var, kullanılmıyor.)
- **YouTube OAuth scope'u (`youtube.upload` + `youtube.force-ssl`) DAHA FAZLA DARALTILAMAZ**:
  WebSearch ile Google'ın resmi YouTube Data API dokümantasyonu doğrulandı (2026-09) —
  `videos.update` (bkz. `set_privacy.py`/`update_metadata.py`) ve `playlistItems.insert`
  (bkz. `youtube_playlists.py`) çağrıları `youtubepartner`, `youtube`, `youtube.force-ssl`
  scope'larından EN AZ birini şart koşuyor; bu üçü arasında `youtube.force-ssl` zaten en
  dar seçenek. Yani mevcut kurulum zaten minimal — daha dar bir scope'a geçmek bu iki
  işlevi kırar. Kaynak: [Videos: update](https://developers.google.com/youtube/v3/docs/videos/update),
  [PlaylistItems: insert](https://developers.google.com/youtube/v3/docs/playlistItems/insert).
- **YouTube altyazısı OTOMATİK gerçek sözlerle hizalanıyor — ama SADECE bir
  `<slug>_sozler.md` dosyası olan projeler için** (`caption_align.py` +
  `upload/youtube_captions.py`, `auto_process.py`'den çağrılıyor): kullanıcı
  isteği (2026-09-06) — bu tarihte Gece Sürüşü/Sessiz Mektup/Kumdan Denize/
  Beni Bırakma'nın YouTube altyazılarında elle bulunup düzeltilen onlarca
  ASR hatası ("güllerimden" ↔ "küllerimden", "alar" ↔ "ağlar" gibi) bir daha
  ELLE yapılmasın diye. Yöntem: YouTube'un kendi "Otomatik altyazılar"ının
  (ASR) ZAMANLAMASI güvenilir (ses-analizine dayalı) ama METNİ kendi
  duyduğu gibi yazıyor — `caption_align.align()` `difflib.SequenceMatcher`
  ile ASR'nin kelime dizisini gerçek sözlerin (`## Temiz Sözler` bölümü)
  kelime dizisiyle eşleştirip, eşleşen kelimeler için ASR'nin GERÇEK
  zamanını, eşleşmeyenler için komşu eşleşmelerden doğrusal aradeğer
  kullanıyor (bkz. modülün docstring'i: bu yaklaşım "align_captions_v2"
  adıyla önce elle/scratchpad'de denendi, 4 şarkıda doğrulandı, SONRA koda
  entegre edildi). **Sözler dosyası yoksa sessizce atlanır** — ASR'nin
  kendi (potansiyel hatalı) metnini "düzeltilmiş" gibi otomatik yayınlamak
  güvenli değil, bu insan gözden geçirmesi gerektiriyor (bkz. Beni
  Bırakma'nın elle incelemesinde bulunan 2 belirsiz bölüm — sözler dosyası
  olsaydı otomasyon bile bunları gerçek sözlerle çözebilirdi, ama o şarkı
  için hâlâ bir `*_sozler.md` yok). **ASR yükleme sonrası hemen hazır
  olmuyor** (dakikalar-saatler) — `auto_process.py` bu yüzden
  `state.json`'da `youtube_captions_done` set olana kadar HER koşuda
  tekrar dener (Instagram'ın golden-hour konteyner kuyruğuyla AYNI desen,
  bkz. `_drain_golden_hour_queue`) — bilerek `_is_fully_done()`'a
  EKLENMEDİ, yoksa sözler dosyası olmayan (kataloğun çoğunluğu) projeler
  `_auto_pace_count()`'un kademeleme aritmetiğini kalıcı olarak bozardı
  (asla "tam" olamayacakları için sonsuza kadar `pending` kalırlardı).
  **Mevcut bir manuel altyazı parçası varsa `insert()` değil `update()`**
  kullanılıyor — 2026-09-06'da Studio üzerinden ELLE düzeltilmiş 4 şarkı
  üzerinde bu otomasyon tekrar çalıştığında duplicate bir "Manuel
  altyazılar (2)" parçası oluşturmasın diye (idempotent, zararsız üzerine
  yazma). Ana kataloğa (`auto_process.py`) özgü — `dj_famous_process.py`'ye
  BİLEREK eklenmedi (DJ Famous setleri için lyrics-dosyası kuralı yok, ayrı
  bir akış).
  **2026-09-06'da YouTube API KOTASINI TÜKETEN bir hataya yol açtı ve
  düzeltildi**: `_drain_golden_hour_queue`, `ready` listesindeki (kataloğun
  çoğunda bir `*_sozler.md` olduğu için genelde 10+ proje) HER projede
  `_check_youtube_captions`'ı çağırıyordu — her çağrı (video zaten
  altyazılıysa/sözler dosyası yoksa hariç) en az bir `captions.list` API
  isteği demek, bu da tek bir `auto_process.py` koşusunda günlük 10.000
  birimlik kotanın büyük kısmını tüketip ASIL video yüklemelerini (her biri
  ~1600 birim) engelleyebiliyordu (gerçekleşti — bir koşuda ~13 proje
  kontrol edilirken kota bitti, "quotaExceeded" hataları hem altyazı hem
  sonraki Instagram/video işlemlerinde art arda geldi). Düzeltme:
  `_drain_golden_hour_queue` artık TEK bir koşuda EN FAZLA BİR projede
  gerçek bir API isteğine izin veriyor (`_check_youtube_captions` artık
  bool dönüyor — video/sözler dosyası yok gibi tamamen yerel kontrollerle
  sessizce çıktıysa False, ASR kontrolü için GERÇEKTEN API'ye dokunduysa
  True) — ilk gerçek deneme sonrası döngü sonraki projeler için captions
  kontrolünü atlar. Aynı desen `process_project()` içindeki tekil çağrı
  için sorun değil (zaten aynı anda işlenen proje sayısı `--count`/otomatik
  kademelemeyle sınırlı, tipik olarak 1).
  **Hizalama artık ASR/sözler EŞLEŞME ORANINA bakıyor ve 0,25'in altında
  altyazıyı YAYINLAMIYOR** (`caption_align.LyricsMismatch`, 2026-09-11); eşik
  keyfî değil, ölçüldü: yanlış eşleşmelerin tavanı 0,146, doğruların tabanı
  0,303 (`tests/test_altyazi_sozler_eslesmesi.py` iki bulutun ayrık kalmasını
  bekçilik ediyor). **Sözler dosyası eşleşmesi altyazı hattında İKİNCİ kez
  doğrulanıyor** (`youtube_captions.SLUG_BENZERLIK_ESIGI`), çünkü
  `stock_art.find_lyrics_file`in ön-ek kuralının uzunluk koruması yoktu
  ("Neon" -> `neon_kalp_sozler.md`) — o boşluk aynı gün
  `stock_art.ONEK_UZUNLUK_ORANI` ile kapatıldı, ama İKİ kapı da KALIYOR.
- **Türkçe tuzağı — `"İ".lower()` Python'da `i` + U+0307 (BİRLEŞEN NOKTA)
  üretir**: ASR küçük harf yazdığı için "İ" ile başlayan kelimeler altyazı
  hizalamasında HİÇ eşleşmiyordu (katalogda 14 kelime / 9 şarkı, çoğu satır
  başı). Doğrusu: ÖNCE `İ→i, I→ı` eşlemesi, SONRA `lower()`
  (`caption_align._norm_word`). ffmpeg'in `drawtext` tuzakları gibi "bir daha
  düşülmesin" sınıfından — Türkçe metni küçük harfe çeviren HER yeni kod
  (eşleştirme, arama, slug) aynı tuzağa düşer.

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

Baseline (ilk kapsamlı) denetimler yapıldı, bulguların çoğu düzeltildi
(bkz. git geçmişi, PR #25/#26/#27). Periyodik olarak tekrar çalıştırılabilirler.

## Testler ve otomatik sağlık izleme

- **`tests/` (pytest) + `.github/workflows/tests.yml`**: projede daha önce hiç otomatik
  test yoktu (`otomasyon-denetcisi` denetiminin tekrar eden bulgularından biri). Kapsamı
  `ls tests/` ile gör — her dosya adı bir modülün ya da bir tuzağın adı (golden-hour
  pencere sınırları, kademeleme aritmetiği, ASR hizalaması, uyumluluk kapısı, atomik
  state yazımı, backfill günlük tavanı, nabız, DJ yayın kapısı...). Yeni bir modül
  yazdıysan test dosyasını da yaz: yukarıdaki "sessiz arıza" sorularından üçüncüsünün
  en ucuz cevabı bu.
  **Bu Windows makinesinde `pytest`'i düz çalıştırmak yanıltıcı:** pytest'in varsayılan
  geçici klasörü (`%LOCALAPPDATA%\Temp\pytest-of-ACER`) okunamıyor, `tmp_path` kullanan
  HER test "PermissionError" ile hata veriyor — kodla ilgisi yok. Doğru çalıştırma:
  `python -m pytest -q -p no:cacheprovider --basetemp="<scratchpad>/pytest_tmp"`
  **Buraya sabit bir TEST SAYISI yazma** — sayı sürekli artıyor (bu satırdaki rakam tek
  bir günde defalarca eskidi) ve dakikalar içinde yanlışa düşen bir sayı bu dosyanın
  amacına aykırı; gerektiğinde `python -m pytest --collect-only -q` ile öğren.
  `--basetemp` her ajan/oturum için AYRI olmalı: ortak klasörde paralel koşular
  `WinError 145` ile çakıştı.
  **`tests/conftest.py` — testler artık ÜRETİM log/kilit dosyalarına YAZAMIYOR**: autouse
  bir fixture, repo modüllerindeki `LOG_PATH`/`LOCK_PATH`/marker sabitlerini geçici
  klasöre çekiyor. Sebep "log kirleniyor"dan çok daha ağır: `watch_projects.py`'nin nabız
  gözcüsü `auto_process.log`'un mtime'ına bakıyor — testler her koşuda o dosyayı
  tazelediği için, makine gerçekten dursa bile watchdog ASLA ateşlenmezdi; yani test
  paketini çalıştırmak üretimin emniyet ağını kapatıyordu. Koruma dosya ADINA bağlı
  (yolun bugünkü kullanımına değil), yeni test dosyalarının hiçbir şey yapmasına gerek
  YOK — "unutulacak liste" tuzağı bilerek kapatıldı.
  **2026-09-12'de korumaya İKİ ad daha eklendi, ikisi de "log kirlenmesi"nden ağır.**
  `DURUM_DOSYASI` (`upload/saglik_durum.json`): bir bildirim damgası dosyası sanılıyordu,
  ama `saglik_kontrol.kacan_kosu()` ile ÖLÇÜM KAYNAĞI oldu — `son_kosu_ts` "saatlik hattın
  sonuna en son ne zaman ulaşıldı"yı tutuyor ve kaçan koşu tespiti TAM OLARAK o damgayla
  yapılıyor; `kontrol_et()` çağıran tek bir test bile üretime "son koşu: şimdi" yazıyordu,
  yani gece ölen bir otomasyonun 9 saatlik boşluğu sabah pytest çalıştırmak yüzünden
  GÖRÜNMEZ olurdu (nabız gözcüsüyle birebir aynı bedel). `HEDEF_KOK` (`derleme.py`): gerçek
  `derlemeler/` klasörü ve `derleme.uret()` oraya klasör AÇIP video YAZIYOR — oradaki her
  klasör `dj_famous_process --base derlemeler` için "bekleyen set" demek ve o çağrı saatlik
  hattan otomatik tetiklenebiliyor, yani bir test artığı YAYIN KUYRUĞUNA girebilirdi.
  CI'da (Linux) böyle bir sorun yok. CI her push/PR'da `pytest`'i
  çalıştırıyor — `ffprobe` gerektiren testler `ffprobe` yoksa (bu geliştirme ortamı gibi)
  otomatik atlanıyor, CI'da `ffmpeg` kurulduğu için hepsi çalışıyor. `requirements-dev.txt`
  sadece test için (`pytest`) — üretim makinesinde gerekmiyor.
- **`watch_projects.py` artık bir "nabız" (heartbeat) kontrolü de yapıyor**: tek nokta
  arızası riskini azaltmak için eklendi — makine kapanır/uyursa ya da bir Görev Zamanlayıcı
  görevi bozulursa bunu fark edecek hiçbir mekanizma yoktu. `auto_process.py`'nin HER
  çalıştırmasında (iş olsun olmasın) `log()` en az bir kez çağrıldığı için,
  `auto_process.log`'un mtime'ı saatlik görevin gerçekten tetiklendiğinin ucuz bir
  göstergesi — 4 saatten uzun süre güncellenmezse `notify.py` (ntfy.sh) ile telefona TEK
  seferlik bir uyarı gönderiliyor (`.watchdog_alerted` marker dosyasıyla spam önleniyor,
  log tazelenince marker temizlenip bir sonraki kesintide tekrar uyarabiliyor). SINIR:
  bu kontrol `watch_projects.py`'nin İÇİNDE çalıştığı için, sorun `watch_projects.py`'nin
  KENDİ görevindeyse tespit edilemez (`auto_process.py` yine de bağımsız kendi saatlik
  tetikleyicisiyle çalışmaya devam eder, sadece bu nabız kontrolü devre dışı kalır) —
  makine tamamen kapalıysa zaten hiçbir yerel script bir şey gönderemez, bu harici
  altyapısı olmayan bir kişisel otomasyonun doğal sınırı.

- **`saglik_kontrol.kontrol_et()` artık YEDİ adım** (2026-09-12). Hepsi
  `auto_process.main()`'in `finally` bloğundan; YENİ zamanlayıcı görevi EKLENMEDİ.
  Dördü eski (Instagram token süresi · Netlify kimlik bilgisi · Görev Zamanlayıcı görev
  TANIMI · ses/tarz takibi tutarlılığı), üçü bugün eklendi — üçü de "önceki adımların
  göremediği kör nokta" olduğu için var:
  - **`kacan_kosu()` — eşik 4 saat.** Diğer adımların hepsi "koşu gerçekleşti"
    VARSAYIMININ üstüne kurulu; koşu hiç tetiklenmezse hiçbiri çalışmaz ve log'a TEK SATIR
    bile düşmez (kaçan koşunun tanımı bu: geriye hiçbir iz BIRAKMAZ). Ölçüt log DEĞİL kendi
    damgamız (`saglik_durum.json`), ve damga hangi dala girilirse girilsin HER koşuda
    tazeleniyor — aksi hâlde bir kez oluşan boşluk sonsuza kadar raporlanırdı.
    **Makine kapalı/uykuda = NORMAL**: boşluk, makinenin KESİNTİSİZ ayakta olduğu süreden
    uzunsa log'a satır düşer ama TELEFON ÇALMAZ. Burada bir tuzak var: `LastBootUpTime`
    TEK BAŞINA YETMİYOR, çünkü **uyku açılış zamanını SIFIRLAMAZ** — gece uyuyan bir
    dizüstüde uptime koca bir sayı olur ve "makine ayaktaydı" YALANINI söyler; gerçek
    sinyal, uptime ile son UYANMA olayının (Power-Troubleshooter, Id 1) KÜÇÜĞÜ.
    **Güç durumu OKUNAMAZSA bildirim GİDER** (bilerek): "bilmiyorum" masumiyet karinesi
    değildir — sessiz kalmak tam da bu modülün yakalamak için var olduğu deseni geri
    getirirdi. 24 saatten sonra (`UZUN_SESSIZLIK_ESIGI_SN`) sebep artık önemsiz, her
    hâlükârda uyarılıyor.
  - **`git_senkron()` — eşik 6 saat, ve DAL değil SONUÇ ölçülüyor.**
    `latest_release.regenerate()` `docs/latest.html`'i her koşuda DİSKTE doğru üretiyordu,
    ama `git_sync.push_path()` ilk iş olarak dala bakıp `main` değilse sessizce `return`
    ediyor; üretim klasörü başka bir dalda durduğu için bio linkinin gösterdiği TEK
    tıklanabilir sayfa 7 GÜN boyunca CANLI'da bayat kaldı ve ne log'a ne bildirime tek
    satır düştü. Adım dalı DEĞİL, yereldeki sayfa ile `origin/main`'dekinin GİRİŞ
    SAYILARINI karşılaştırıyor (`git show`, ağa çıkmadan): sayfa güncelse dal `main`
    olmasa bile telefon ÇALMAZ. Dal kapısının kendisi doğru; kapatılan şey kapının
    SESSİZLİĞİ.
  - **`yayin_durgunlugu()` — eşik 78 saat, SABİT DEĞİL TÜRETİLMİŞ.** İlk altı adımın
    hiçbiri "en son ne zaman bir şey YAYINLANDI" diye SORMUYOR: `kacan_kosu` kendi
    damgasına bakıyor (her koşuda tazeleniyor), `git_senkron` yerel/canlı FARKINI ölçüyor
    (hiçbir şey yayınlanmazsa iki taraf eşit kalır), kalan dördü ön koşullara bakıyor —
    yani koşu yapılıyor, ortam sağlıklı görünüyor ve kanal GÜNLERCE sessizce durabiliyordu
    (özellikle uyumluluk kapıları fail-closed olduktan sonra: kapanan kapı projeyi atlar,
    geriye yalnızca bir log satırı kalır). Eşik `1.5 × YAYIN_TABANI_SN` — yani 52 saatlik
    `auto_process.MIN_YAYIN_ARALIGI_SN`'in 1,5 katı; taban değişirse eşik kendiliğinden
    kayar, elle güncellenecek ikinci bir sayı OLMAZ. **BEKLEYEN PROJE ŞARTI ZORUNLU**:
    katalog bittiyse sessizlik NORMALDİR (Suno kotası yüzünden kanal haftalarca meşru
    biçimde sessiz kalabilir) ve alarm YANLIŞ olurdu.
  ÇAĞRI SIRASI anlamlı: `yayin_durgunlugu` `kacan_kosu`'dan ÖNCE, `kacan_kosu` EN SONDA —
  çünkü o adım "saatlik hattın SONUNA ulaşıldı" damgasını atıyor; yukarıdaki adımlardan
  biri beklenmedik şekilde patlarsa damga da atılmaz ve bir SONRAKİ koşu bunu boşluk
  olarak görür (istenen davranış).
- **Haftalık gözden geçirme — `weekly_report.haftalik_gozden_gecirme()`** (2026-09-12):
  "bu hafta ne oldu / ne bekliyor / senin işin ne" özeti, telefona TEK bildirim.
  **YENİ bir zamanlayıcı görevi YOK** (bu belgenin kendi kuralı): `auto_process.main()`'in
  `finally` bloğundan çağrılıyor ve pencere kontrolü fonksiyonun İÇİNDE — haftanın geri
  kalanında diske de ağa da hiç dokunmuyor. Pencere **pazartesi 09:00 sonrası, golden-hour
  DIŞI**: haftanın sorusu hafta BAŞINDA sorulur (cuma akşamı gelen özet pazartesiye kadar
  bayatlar), ISO hafta damgası da pazartesi değişiyor, ve cuma 18:00'deki haftalık DJ
  koşusunun damgası pazartesi sabahı çoktan diskte — yani hafta rapora TAM giriyor.
  **SIFIR YouTube API isteği**: bütün sayılar `state.json`'lardan ve `izlenme_raporu()`nun
  bıraktığı anlık görüntüden okunuyor. Makine pazartesi kapalıysa rapor KAYBOLMAZ (haftanın
  ilk uygun koşusunda çıkar — pilde duran görevler bu depoda gerçek bir vakaydı);
  gönderilemezse hafta damgası ATILMAZ, yoksa temel çizgi kayar ve bir sonraki haftanın
  "değişim" sayısı sessizce yanlış olurdu.

## TARİHLİ RANDEVU — 2026-10-09: ölçüm penceresi

2026-09-11'de kanalın **40 kapağı birden** ve **video açılışları** değişti. Bunun işe
yarayıp yaramadığının TEK kanıtı, o günkü temel çizgiyle bir ay sonraki ölçümün
karşılaştırılması. **2026-10-09'da (ya da ilk sonraki oturumda) çalıştır:**

```
python olcum_temel_cizgi.py --dry-run      # önce bu: hiç API çağırmaz, hiç yazmaz
python olcum_temel_cizgi.py --cek          # -> olcum_2026-10-09.json (yeni dosya)
python olcum_temel_cizgi.py --karsilastir  # temel çizgi <-> yeni ölçüm
```

- **Neyle karşılaştırılıyor:** `olcum_temel_cizgi.json` (2026-09-11, değişiklikten ÖNCESİ).
  Bu dosya TEMEL ÇİZGİ — script onun üstüne yazmayı bir muhafızla reddediyor.
- **Birincil metrik:** `audienceWatchRatio` **%2 ve %3** noktaları (temel: 0,837 / 0,715;
  `Küllerimden Geç` kopya olduğu için ortalamaya katılmıyor).
- **Gürültü tabanı 21,2 puan** (aynı md5'li iki video arasında ölçüldü) — tek video
  farkları anlamsız, sadece 7 videonun ortalamasındaki YÖN okunur. Güvenilir karar için
  ikinci ölçüm: 2026-10-23 … 2026-11-06.
- **Elle tek ek adım:** tıklanma oranı API'de YOK; Studio > Analizler > Erişim'den
  2026-08-14..2026-09-10 ve 2026-09-12..2026-10-09 aralıklarını CSV dışa aktar.
  (Detay ve gerekçenin tamamı `olcum_temel_cizgi.py` docstring'inde.)

### İKİNCİ TARİH — 2026-10-11: YouTube Reporting API'yi AÇ

Google Cloud Console'da tek tık, ~5 dk. **Ertelenemez**: Reporting job yalnızca
KURULMADAN ÖNCEKİ 30 GÜNÜ geriye dolduruyor, 40 kapak 2026-09-11'de değişti ve temel çizgi
tam o pencerede — her gecikme günü temel çizgiden BİR GÜN siliyor. 2026-09-12'de
doğrulandı: `olcum_temel_cizgi.json` → `cekilebildi_mi = false` (403 SERVICE_DISABLED).
Alternatif yol YOK — Analytics API `impressions`/`impressionClickThroughRate` metriklerini
TANIMIYOR (dört ayrı denemeyle kayıtlı); yedek yalnızca Studio → Analizler → Erişim CSV'si,
yani yukarıdaki "elle tek ek adım"ın ta kendisi.

### 2026-09-12'de YANLIŞ ÇIKAN İKİ SAYI — tekrar kullanma

- **"DJ seti Suno kotası başına ~12 kat verimli" YANLIŞ BÖLMEYDİ.** Gerçek Analytics
  verisiyle ölçülen: 2 set 28 günde 1.377 dk, 18 şarkı 1.521 dk → **video başına 8,2 kat**
  (688 vs 84 dk). KOTA başına bölünce avantaj KAYBOLUYOR: bir set 12-16 Suno indirmesi
  yiyor (`dj_sets/Night Drive/SUNO.md`), yani indirme başına 43-57 dk; tekil şarkı 84,5 dk
  (1.521/18). **Kota başına ŞARKI daha verimli, set değil.** Karar yine set lehine ayakta
  ama gerekçesi kota değil **VİDEO SAYISI**: az sayıda uzun video, kanalın en büyük riski
  olan "toplu üretilmiş AI içerik" sinyalini düşürüyor. Sonuç kural: set yapılacaksa
  **12 parça, 16 değil** (45-60 dk).
- **"Yıllık ~2.620 saat izlenme" projeksiyonu ŞİŞİK.** 28 günlük izlenme süresinin
  **%83'ü son 7 günde** oluşmuş, yani rakam tek seferlik bir hızlanmayı sabit hız sanıyor.
  Gerçekçi taban **~784 saat/yıl**. Büyüme kararlarını şişik rakama dayandırma.

### Ortaklığın (YPP) asıl darboğazı ABONE, izlenme saati DEĞİL

Bu, 2026-09-12'ye kadar hiçbir belgede yazmıyordu ve strateji tarafında en pahalı
boşluktu: 28 günde net **+28 abone**; bu hızda 1.000 abone ≈ **2,7 yıl**, ve 4.000 saat
eşiği ondan ÖNCE dolacak. Yani "izlenme süresini artıran" her fikir (uzun format, derleme,
DJ seti) doğru ama YETERSİZ — eşiği belirleyen değişken abone kazanımı, ve onu artıran
işler çoğunlukla kodun DIŞINDA (bkz. `buyume_kontrol_listesi.md`). ⚠ Buna dayanan bir
karar vermeden önce: YPP'nin 4.000 saat eşiğinin Shorts izlenmesini sayıp saymadığı bu
ortamdan DOĞRULANAMADI, Studio'dan elle teyit gerekiyor.

## Açık/bilinen boşluklar (henüz yapılmadı)

- TikTok/Instagram'ın AI-içerik açıklama API alan adları HÂLÂ tam doğrulanmadı (2026-09-04
  WebSearch ile tekrar denendi): TikTok Content Posting API'de `post_info.is_aigc`,
  Instagram Graph API'de `media_publish` çağrısında `is_ai_generated` adlı alanlar üçüncü
  taraf entegrasyon dokümantasyonlarında (Ayrshare vb.) tutarlı şekilde geçiyor, ama resmi
  `developers.tiktok.com`/`developers.facebook.com` sayfalarının ham metniyle bu ortamdan
  DOĞRULANAMADI — Meta'nın en güncel resmi changelog'unda (3 Aralık 2025) bu alandan hiç
  bahsedilmiyor, bu olumsuz bir sinyal. Koda eklemeden önce kullanıcının gerçek bir API
  test isteğiyle (ör. sandbox/test hesabı) bu alanların kabul edildiğini bizzat doğrulaması
  gerekiyor — yanlış alan adı riskli olduğu için hâlâ koda eklenmedi.
- İlk 3 şarkının (Beni Bırakma, Yeniden Doğacağım, Shudhniy L) Suno stil etiketleri
  arşivlenmemiş.

## Diğer takip dosyaları

`buyume_kontrol_listesi.md` (elle yapılan büyüme adımları), `trend_hashtag_notlari.md`
(hashtag/saat araştırması, periyodik güncellenmeli), `ses_ve_tarz_takibi.md` (vokal
çeşitliliği), `suno_prompt_hazirlik.md` (yeni şarkı ekleme adımları + lisans notu).
`denetim_bulgulari_2026-09-12.md` — 2026-09-12'deki 14 salt-okunur denetimin HÂLÂ AÇIK
bulguları (arşiv değil, EYLEM listesi: kararlar, elle yapılacaklar, kod işleri, ölçüm
takvimi, ve "araştırıldı, YOK" diye kapatılmış yollar). Yeni bir işe başlamadan önce oraya
bak — aynı şeyi ikinci kez araştırmayı önlemek için yazıldı.

## Git/PR alışkanlığı

Bu proje iki farklı ortamda geliştiriliyor, her birinin kendi dal alışkanlığı var:

- **Yerel makine (Windows, üretim + yerel Claude Code oturumları)**:
  `claude/analiz-yap-sk8gpf` dalında geliştirilip PR ile `main`'e birleştiriliyor. Bir PR
  merge olduktan sonra bu dal restart edilir (`git fetch origin main && git reset --hard
  origin/main` veya içerik aynıysa force-with-lease push) — merge edilmiş commit'lerin
  üzerine yeni commit yığmak yerine.

  **UYARI — `git reset --hard`/`git clean -f` üretim makinesinin checkout'unda ASLA
  elle çalıştırılmamalı:** yukarıdaki restart deseni sadece bu geliştirme dalı için
  güvenli (disposable, gerçek veri tutmuyor). `projects/*/state.json` gibi dosyalar
  git'e commit'li VE üretim makinesinde otomasyon tarafından sürekli commit'siz
  güncelleniyor (bkz. `git_sync.py` notu yukarıda) — bu checkout'ta bir
  `reset --hard`/`clean -f` bu commit'siz güncellemeleri KALICI OLARAK SİLER. Bu
  gerçekten oldu: `83cd3a2` commit'i ("Kaybolan Instagram upload kayıtlarını geri
  yükle") tam olarak böyle bir kazanın sonucuydu. Üretim checkout'unda temizlik
  gerekiyorsa önce `git status`/`git diff` ile neyin commit'siz olduğuna bak, gerekeni
  commit'le, sadece SONRA (gerekiyorsa) sert bir komut düşün.

- **Claude Code on the web**: her görev için `claude/<özet>-<rastgele>` biçiminde yeni
  bir dal otomatik oluşturuyor (sabit tek bir dal adı YOK — farklı görevler farklı dal
  isimleri alır, geçmiş PR'larda görülen `claude/analiz-yap-sk8gpf` yerelin sabit dalıdır,
  bu ortamınki değil). Değişiklikler o dalda geliştirilip PR ile `main`'e birleştiriliyor.
  Bir görev başında dal `main`'in gerisindeyse önce `git fetch origin main` ile güncel
  `main` referansı çekilmeli.

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
