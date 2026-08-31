---
name: suno-video-render
description: Suno'da üretilen ses dosyalarından YouTube/YouTube Shorts/TikTok/Instagram Reels/Facebook için otomatik çoklu-platform "müzik kartı" videosu üreten bu projenin (render.py) workflow'u. Yeni şarkı eklerken, render çalıştırırken, config.py'deki kart/marquee/ilerleme çubuğu ayarlarını değiştirirken, render sonrası görsel doğrulama yaparken veya ffmpeg filtergraph hatalarıyla karşılaşınca kullan.
---

# Suno Video Render Pipeline

Bu proje, Suno'dan indirilen ses dosyalarını (audio.wav/.mp3/.m4a) + bir kart görselini alıp,
ffmpeg ile 3 platform için "müzik player kartı" tarzında video üretir: YouTube (16:9), YouTube
Shorts/TikTok/Instagram Reels (9:16), Instagram post/Facebook kare (1:1).

**Görsel stil (v2 — referans videoya göre tasarlandı, tam ekran/Ken-Burns tasarımının yerine
geçti):** siyah zemin üzerinde, ekranın büyük kısmını kaplayan ("orta alan") yuvarlak köşeli bir
albüm kartı + etrafında zamanla renk değiştiren (hue rotation) neon parlama çerçevesi + kartın
altında küçük, ince, künye tarzı sürekli kayan (marquee) yazı ("Şarkı Adı — Famous Studio
Yapımı") + en altta gerçek zamanlı dolan bir ilerleme çubuğu. **Kart statik durur (zoom yok),
waveform yok** — sadece kart alanı işlenir, geri kalan çerçeve düz siyahtır, bu yüzden eski tam
ekran tasarımına göre çok daha az render maliyeti vardır.

Kartın 4 düz kenarı boyunca **gerçek sese tepki veren eşitleyici çubukları** var (`showfreqs`,
tema rengiyle). Köşeler bilinçli olarak sarılmıyor — sadece arkadaki glow ile dolduruluyor
(kullanıcı onayıyla basitleştirildi, "tam çevreleyen" bir efekt DEĞİL).

"Famous Music Studio" logosu artık karttan kaldırıldı — kart şu an düz koyu renk
(`config.CARD_ART_COLOR`) dolgu, `cover.jpg` sadece platform thumbnail'i için kullanılacak
(bu script tarafından üretilmiyor, ayrıca yüklenecek).

**AÇIK KONU:** Kart içine şarkıya özel atmosferik/sanatsal bir görsel (referans videodaki neon
sokak fotoğrafı gibi) eklenecek ama kaynağı henüz kararlaştırılmadı (Suno mu sağlayacak, AI ile
mi üretilecek). Yeni oturumda önce bunu netleştir.

**Referans örnek tamamlandı (2026-08-30):** `projects/ilk-sarkim` — gerçek şarkı ("AY-AH
Nights", Turkish Trap Arabesk, gece/yalnızlık teması), gerçek kart görseli (`art.png`, Canva ile
üretildi, tema rengiyle uyumlu), tema=`pop`, tam 3 platform render'ı başarılı. Bu, pipeline'ın
"kusursuz başlangıç" referans noktası — yeni özellik denerken bunu bozmadığından emin ol.
Kart içeriği artık `art.jpg/.jpeg/.png` (opsiyonel, yoksa düz renk) — `cover.jpg` SADECE
platform thumbnail'i, videoya hiç girmiyor.

**Gerçek şarkıda test edildi ve düzeltildi (bu oturumda):**
- Render süresi: yeni hafif kart tasarımı eski tam ekran tasarımından ~2.2x hızlı (4 dk'lık
  şarkı için ~22 dk → ~9-10 dk).
- `CARD_SIZE_RATIO` gerçek ekranda çok büyük duruyordu → 0.74'ten 0.55'e düşürüldü.
- Kayan yazı/kart boyutu birkaç yanlış denemeden sonra referans video (sunıo/video_1.mp4)
  TEKRAR dikkatle ölçülerek düzeltildi: (1) `CARD_SIZE_RATIO` referansta ölçüldüğünde ~0.31-0.35
  çıktı (0.55 bile hâlâ çok büyüktü) → 0.35'e düşürüldü. (2) Künye yazısı kartın İÇİNDE DEĞİL,
  kartın ALTINDA (küçük bir `MARQUEE_GAP_RATIO` boşluğuyla), `card_size` genişliğinde duruyor —
  "kart içine bindirme" denemesi YANLIŞTI, referans videoda yazı açıkça kartın altında.
  **Ders:** Görsel konumlandırma belirsizliğinde tahmin etmek yerine referans kareyi
  `Read` ile tekrar aç ve piksel oranlarını ölç — birkaç deneme-yanılma turu yerine tek
  seferde doğru sonucu verir.
- `showfreqs` gerçek müzikte `ascale=log` ile sürekli maksimuma vurup "beyaz duvar" gibi amatör
  görünüyordu; `ascale=lin` ise neredeyse görünmez oldu. `ascale=sqrt` + `EQ_INPUT_GAIN=0.7`
  (showfreqs'e girmeden önce sesi zayıflatan bir `volume` filtresi) orta yol oldu — ince,
  dokulu bir çizgi. Bu ayarları değiştirirken MUTLAKA gerçek bir şarkıyla test et, sinüs test
  tonu bu sorunları YANSITMIYOR (çok farklı görünüyor).

## Proje Yapısı

- `render.py` — CLI giriş noktası (`--project <klasör>` veya `--all`), 3 platformu paralel render eder
- `ffmpeg_utils.py` — ffprobe süre okuma + kart/glow/marquee/progress-bar filtergraph inşası + render_video()
- `config.py` — TÜM görünüm/kalite ayarları burada (aşağıda liste)
- `assets/card_mask.png` — yuvarlak köşe maskesi (luma tabanlı, `alphamerge` ile kullanılır, tüm temalarda ortak)
- `assets/card_glow_<tema>.png` — her tema (pop/rock/elektronik/akustik/hiphop) için ayrı, o temanın rengiyle üretilmiş yumuşak kenarlı kare parlama (alfa tabanlı; `hue` filtresiyle o renk etrafında HAFİFÇE salınır, tüm renkleri gezmez)
- `projects/<şarkı-adı>/` — her şarkı kendi klasöründe:
  - `audio.wav` (veya `.mp3`/`.m4a`)
  - `cover.jpg` (veya `.jpeg`/`.png`) — şu an hem thumbnail hem kart için kullanılıyor (yukarıdaki açık konuya bakın)
  - `meta.json` (opsiyonel) — `{"title": "..."}` — kayan yazıda görünür
  - `output/` — render sonrası 3 mp4 buraya yazılır

## Yeni Şarkı Ekleme ve Render

1. `projects/<şarkı-adı>/audio.wav` ve kart görselini koy.
2. (Opsiyonel) `meta.json` ile `title` ekle (künye yazısında görünür).
3. Çalıştır: `python render.py --project projects/<şarkı-adı>` veya `python render.py --all`.

## config.py Ayarları

- `PLATFORMS` — platform_key → (genişlik, yükseklik).
- `CARD_SIZE_RATIO` — kartın min(genişlik,yükseklik)'e oranı (0.74 — büyük/baskın, küçük thumbnail değil).
- `CARD_CORNER_RATIO`, `CARD_GLOW_MARGIN_RATIO`, `CARD_HUE_PERIOD_SEC` — köşe yuvarlaklığı, çerçeve payı, renk dönüş hızı.
- `CARD_ASSET_REF_SIZE` / `CARD_MASK_ASSET_PATH` / `CARD_GLOW_ASSET_PATH` — önbelleğe alınmış asset'ler (dosya silinirse otomatik yeniden üretilir).
- `THEMES[key]["accent"]`/`["accent2"]` — çerçeve artık İKİ renk arasında AÇISAL (angular,
  `atan2` ile) gradyan, `rotate` filtresiyle sürekli döndürülüyor — referans videodaki
  "aynı anda çok renkli" görünüm buradan geliyor (eski tek-renk `hue` salınımı yerine geçti).
- `MARQUEE_SUFFIX`, `MARQUEE_SEPARATOR`, `MARQUEE_REPEAT`, `MARQUEE_SPEED_PX_S`, `FONT_SIZE_RATIO`, `FONT_COLOR` — künye tarzı kayan yazı (küçük, ince, `—` ayraçlı, yavaş kayar — büyük/kalın başlık DEĞİL, bilinçli tercih).
- `PROGRESS_BAR_*` — alttaki ilerleme çubuğu boyut/renk/konum ayarları.
- `MAX_PARALLEL_RENDERS` — kaç platformun aynı anda render edileceği.
- `THEMES` / `DEFAULT_THEME` — meta.json'daki `"theme"` alanına göre kart çerçevesinin rengini
  belirler (`pop`, `rock`, `elektronik`, `akustik`, `hiphop`). `CARD_HUE_WOBBLE_DEG` kadar o
  renk etrafında hafifçe salınır — tüm renkleri gezen rastgele bir efekt DEĞİL, tür kimliğini
  yansıtan sabit bir renk + hafif canlılık. Not: `akustik` ve `hiphop` ikisi de sıcak
  turuncu/sarı aile, gözle ayırt etmek zor olabilir — kullanıcı geri bildirimi bekleniyor.

## Render Sonrası Doğrulama (bu projede standart yöntem)

```bash
# Çözünürlük/süre kontrolü
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -show_entries format=duration -of default=noprint_wrappers=1 output/youtube_16x9.mp4

# Görsel kontrol için örnek kare çıkar (scratchpad'e yaz, sonra Read tool ile görüntüle)
ffmpeg -y -i output/youtube_16x9.mp4 -vf "select=eq(n\,150)" -vframes 1 -update 1 "<scratchpad>/frame.png"
```

Marquee/hue-rotation/progress-bar gibi ZAMANLA DEĞİŞEN bir şeyi doğrularken tek kare yetmez —
en az 2-3 farklı frame numarasından kare çıkarıp gerçekten hareket ettiğini/değiştiğini
karşılaştırarak doğrula. Yeni bir ffmpeg filtre fikri denerken önce KISA (birkaç saniyelik test
tonu + basit bir görsel) izole bir klip üzerinde dene, ana pipeline'a onaylanmadan entegre etme.

## Bilinen ffmpeg Tuzakları (bu oturumda çözüldü, tekrar düşmeyin)

1. **drawtext + Windows dosya yolu**: mutlak yol (`C:\Windows\Fonts\...`) filtergraph'ta `:`
   yüzünden parse hatası verir. Çözüm: `os.path.relpath(...).replace("\\","/")` ile cwd'ye göre
   göreli, `/` ayraçlı bir yol kullan.
2. **fontconfig kurulu değilse `font=Arial` kullanma** — "Fontconfig error" verir. Her zaman
   `fontfile=<göreli-yol>` kullan.
3. **`geq`/`format=rgba` sırası önemli**: `color=c=...@0.0` + `geq` ile `a=...` versen bile,
   `format=rgba` filtre zincirine EKLENMEDEN önce eklenmezse çıktı `rgb24` (alfasız) olabilir.
   Her zaman `format=rgba,geq=...` sırasıyla uygula, `ffprobe -show_entries stream=pix_fmt` ile doğrula.
4. **`hue` filtresiyle renk döndürürken kaynak RENKLİ (doygun) olmalı** — beyaz/gri (doygunluk=0)
   üzerinde hue rotasyonu GÖRÜNMEZ etki yapar (matematik doğru çalışır ama sonuç hep gri kalır).
   Neon/dönen renk efekti için glow asset'i baştan doygun bir renkle (örn. saf cyan) üret.
5. **`alphamerge` ikinci girdinin LUMINANCE'ini (parlaklık) alfa olarak kullanır, kendi alfa
   kanalını DEĞİL.** Yuvarlak köşe maskesi gibi bir şekli `alphamerge` ile uygulayacaksan, şekli
   maskenin R/G/B (gri ton) değerine göm, alfa kanalına değil.
6. **`drawbox`'ın `w`/`h` parametreleri `t` (zaman) değişkenini güvenilir şekilde desteklemiyor**
   (denendi, tüm kare doldu, animasyon çalışmadı). Zamanla büyüyen bir çubuk/şekil için `geq` +
   `T` (mutlak zaman, per-pixel per-frame güvenilir çalışıyor) kullan: `r='thresh+delta*lt(X\,W*T/dur)'`.
7. **Tek kare PNG yazarken** `-frames:v 1 -update 1` kullan.
8. **Filtre ifadelerinde virgül** (`mod(a,b)`, `hypot(a,b)`, `max(a,b)`, `clip(a,b,c)` gibi iç
   içe fonksiyonlarda) `\,` olarak escape edilmeli, yoksa filtergraph parser virgülü zincir
   ayracı sanıp hata verir. Bu proje boyunca en çok tekrar eden hata kaynağı budur.
9. **Windows'ta `/tmp` yazılamaz** — scratchpad dizinini kullan.
10. **`color=...`, `nullsrc` gibi kaynak filtreler** ekstra bir `-i` girdisi gerektirmeden
    doğrudan `filter_complex` içine (girdi etiketi olmadan) yazılabilir — canvas/progress-bar
    arka planı için bu şekilde kullanıldı.
11.5. **Statik bir PNG'yi (`-loop 1 -i x.png`) filtergraph'ın ANA/TEMEL katmanı (canvas) olarak
    kullanırken mutlaka `fps={FPS}` ekle.** Aksi halde PNG'nin varsayılan (genelde 25) kare
    hızı tüm zincirin zamanlamasını bozabiliyor — belirti: `showfreqs` gibi zamana bağlı
    filtreler DONMUŞ gibi davranıyor (iki farklı zaman noktasında piksel değerleri aynı
    kalıyor), ama marquee/progress-bar gibi `t`/`T` kullanan diğer şeyler normal görünebiliyor
    (bu yüzden fark etmesi zor). Vinyet arka planını canvas yaparken bu bulundu/düzeltildi.
11. **KRİTİK — bir filtre çıktısını (`[label]`) `vflip`/`transpose` gibi filtrelere VE aynı
    zamanda başka bir yerde (örn. `overlay`) doğrudan besliyorsan, önce `split` ile açıkça
    çoğalt.** Bunu atlamak (örn. `[eqh]vflip[x]` ve `[eqh]transpose=1[y]` gibi aynı etiketi
    birden fazla filtreye vermek) sessizce bozuk/kayıp içerik üretiyor (bu oturumda kartın
    tamamen kaybolmasına neden oldu, saatlerce debug gerektirdi). `[label]split=N[a][b][c]...`
    yaz, her dala AYRI kopya ver. Ham girdi etiketlerini (`[0:v]` gibi) birden fazla yerde
    kullanmak bu sorunu YAŞAMADI — sorun özellikle bir FİLTRE çıktısının çoklu tüketiminde çıktı.

## Performans Notları

- 3 platform **paralel** render ediliyor (`ThreadPoolExecutor`).
- Kart tasarımı (v2), eski tam ekran + Ken-Burns + waveform tasarımına göre doğası gereği çok
  daha hafif: kartın kendisi statik (zoom yok), çerçevenin dışındaki büyük alan düz siyah
  (neredeyse bedava encode), waveform kaldırıldı.
- Aynı şarkıyı sadece başlık değiştirerek tekrar tekrar render etmenin önbellekleme ile
  hızlandırılması **bilinçli olarak yapılmadı** — iki kademeli bir önbellek ikinci nesil
  sıkıştırma kaybı getirir ve gerçek kullanım akışında (şarkı başına tek render) faydası yoktur.
  Her render her zaman orijinal kaynak dosyalardan yapılır — kalite kaybı birikmez.
