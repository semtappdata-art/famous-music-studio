---
name: suno-video-render
description: Suno'da üretilen ses dosyalarından YouTube (uzun format + Shorts), TikTok, Instagram Reels için otomatik çoklu-platform "Now Playing" tarzı müzik kartı videosu üreten bu projenin (render.py, generate_cover.py, auto_process.py) workflow'u. Yeni şarkı eklerken, render çalıştırırken, config.py'deki kart/backdrop/marquee/ilerleme çubuğu ayarlarını değiştirirken, render sonrası görsel doğrulama yaparken veya ffmpeg filtergraph hatalarıyla karşılaşınca kullan.
---

# Suno Video Render Pipeline

Bu proje, Suno'dan indirilen ses dosyalarını (audio.wav/.mp3/.m4a) + (opsiyonel) bir kart
görselini alıp, ffmpeg ile 2 platform çıktısı üretir: YouTube uzun format (16:9,
`youtube_16x9.mp4`) ve YouTube Shorts/TikTok/Instagram Reels (9:16, `shorts_9x16.mp4` — bu
tek dosya üç yere de yükleniyor). `auto_process.py` bunun üstüne YouTube Shorts'u AYRI bir
YouTube video'su olarak da yüklüyor — aynı şarkı için iki ayrı YouTube uploadı oluyor.

**Güncel görsel stil — Spotify "Now Playing" tarzı:** ortada yuvarlak köşeli, ekranın büyük
kısmını kaplayan bir albüm kartı (içeriği şarkının kendi `art.jpg`'si — kare kırpılıp
yerleştirilir) + arka plan, o AYNI `art.jpg`'nin ekranı kaplayacak şekilde büyütülüp güçlü
bulanıklaştırılmış (`gblur`) ve hafif karartılmış hâli (`ffmpeg_utils.ensure_art_backdrop`) —
yani arka planın rengi/atmosferi sabit bir tema paletinden DEĞİL, doğrudan o şarkının kart
görselinden geliyor. Bu backdrop artık STATİK bir kare değil: hedef çözünürlükten biraz büyük
üretilip render sırasında içinde yavaşça kayan bir `crop` penceresi (pan) + dar bir açı
aralığında salınan `hue` (renk akışı) uygulanıyor — ikisi de ucuz filtreler, performans
maliyeti yok. Kartın altında küçük, kayan (marquee) künye yazısı + sabit "Famous Music Studio"
marka satırı + en altta gerçek zamanlı dolan bir ilerleme çubuğu var. Kart statik durur (zoom
yok, sadece backdrop hareketli), waveform/eşitleyici çubuğu YOK (eski bir tasarımda vardı,
kullanıcı beğenmeyip kaldırdı) — sadece kart alanı + backdrop işlenir, bu yüzden eski tam
ekran/waveform tasarımına göre çok daha az render maliyeti vardır.

`art.jpg` yoksa `ffmpeg_utils.ensure_vignette()` fallback'i (sabit, tema rengine göre statik
bir vinyet — o da aynı pan+hue muamelesini alır) kullanılır. `art.jpg`/`cover.jpg` da yoksa
(hiç elle görsel hazırlanmamışsa) `generate_cover.py`, `meta.json`'daki title/theme'e göre
ikisini de otomatik üretir — tema rengi + şarkı başlığından türetilen deterministik bir bokeh
dokusu (düz gradyan DEĞİL — kart ile backdrop arasında görsel kontrast olması için).

**KRİTİK — art.jpg METİNSİZ olmalı:** `art.jpg`, hem kartın içeriği hem de blur backdrop'ın
kaynağı olarak kullanılıyor. İçine başlık/logo gibi bir metin gömülüyse, blur bunu okunaksız
bir lekeye çevirir. `cover.jpg` (platform thumbnail'i) başlıklı olabilir/olmalı — ama `art.jpg`
her zaman metinsiz bir görsel/doku olmalı. Bu proje boyunca birkaç kez (elle hazırlanan
art.jpg'lerin cover.jpg ile aynı, metinli dosya olarak bırakılması yüzünden) bu hataya
düşüldü — yeni bir proje incelerken `art.* == cover.*` (byte-birebir aynı) olup olmadığını
kontrol etmek hızlı bir sağlık kontrolü.

## Proje Yapısı

- `render.py` — CLI giriş noktası (`--project <klasör>` veya `--all`), platformları paralel render eder (`config.PLATFORMS`)
- `generate_cover.py` — eksik `cover.png`/`art.png`'yi tema rengi + bokeh dokusuyla otomatik üretir (`auto_process.py` render'dan önce çağırır)
- `ffmpeg_utils.py` — ffprobe süre okuma + kart/backdrop(pan+hue)/marquee/progress-bar filtergraph inşası + `render_video()`
- `audio_highlight.py` — Shorts/Reels için sesin en yoğun/enerjik bölümünü bulur (`config.HIGHLIGHT_DURATION`, 45sn)
- `auto_process.py` — asıl production giriş noktası: cover/art üretimi + render + YouTube (uzun+Shorts) + TikTok + Instagram, hepsi tek komutta
- `config.py` — TÜM görünüm/kalite ayarları burada (aşağıda liste)
- `assets/card_mask.png` — yuvarlak köşe maskesi (luma tabanlı, `alphamerge` ile kullanılır, tüm temalarda ortak)
- `projects/<şarkı-adı>/` — her şarkı kendi klasöründe:
  - `audio.wav` (veya `.mp3`/`.m4a`) — TEK zorunlu dosya, gerisi otomatik üretilebilir
  - `cover.jpg`/`.png` (opsiyonel, yoksa otomatik üretilir) — başlıklı platform thumbnail'i
  - `art.jpg`/`.png` (opsiyonel, yoksa otomatik üretilir) — METİNSİZ, kart içeriği + backdrop kaynağı
  - `meta.json` (opsiyonel) — `{"title": "...", "theme": "..."}`
  - `output/` — render sonrası mp4'ler buraya yazılır

## Yeni Şarkı Ekleme ve Render

1. `projects/<şarkı-adı>/audio.wav` koy (görsel opsiyonel — yoksa otomatik üretilir).
2. (Opsiyonel) `meta.json` ile `title`/`theme` ekle.
3. Tam otomasyon için: `python auto_process.py` (cover/art + render + tüm platform upload'ları).
   Sadece render için: `python render.py --project projects/<şarkı-adı>` veya `--all`.

## config.py Ayarları

- `PLATFORMS` — platform_key → (genişlik, yükseklik). Şu an `youtube_16x9` ve `shorts_9x16`
  (üçüncü bir `square_1x1` vardı, hiçbir upload script'i kullanmadığı için kaldırıldı).
- `CARD_SIZE_RATIO` — kartın min(genişlik,yükseklik)'e oranı (0.45).
- `CARD_CORNER_RATIO` — köşe yuvarlaklığı.
- `CARD_ASSET_REF_SIZE` / `CARD_MASK_ASSET_PATH` — önbelleğe alınmış maske asset'i.
- `BACKDROP_PAN_MARGIN_RATIO`, `BACKDROP_PAN_SPEED_X`/`_Y` — backdrop'un ne kadar büyük
  üretileceği ve pan (kayma) hızı.
- `BACKDROP_HUE_AMPLITUDE_DEG`, `BACKDROP_HUE_SPEED` — renk akışının genliği/hızı (tam 360°
  dönmez, tema renginden çok uzaklaşmasın diye dar bir açıda salınır).
- `MARQUEE_SEPARATOR`, `MARQUEE_REPEAT`, `MARQUEE_SPEED_PX_S`, `FONT_SIZE_RATIO`, `FONT_COLOR` — künye tarzı kayan yazı.
- `PROGRESS_BAR_*` — alttaki ilerleme çubuğu boyut/renk/konum ayarları.
- `MAX_PARALLEL_RENDERS` — kaç platformun aynı anda render edileceği.
- `THEMES` / `DEFAULT_THEME` — meta.json'daki `"theme"` alanına göre (`pop`, `rock`,
  `elektronik`, `akustik`, `hiphop`, `arabesk`) kayan yazının rengini ve caption'daki tür
  hashtag'lerini belirler — backdrop'un rengini DEĞİL (o artık `art.jpg`'den geliyor).
- `HIGHLIGHT_DURATION`, `HIGHLIGHT_PLATFORMS` — Shorts/Reels için hangi platformların ses
  highlight'ıyla kırpılacağı ve ne kadar süreyle.

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
11. **Statik bir PNG'yi (`-loop 1 -i x.png`) filtergraph'ın ANA/TEMEL katmanı (canvas) olarak
    kullanırken mutlaka `fps={FPS}` ekle.** Aksi halde PNG'nin varsayılan (genelde 25) kare
    hızı tüm zincirin zamanlamasını bozabiliyor — belirti: zamana bağlı filtreler (`t`/`T`
    kullananlar) DONMUŞ gibi davranabiliyor (iki farklı zaman noktasında piksel değerleri aynı
    kalıyor). Vinyet arka planını canvas yaparken bu bulundu/düzeltildi.
12. **KRİTİK — bir filtre çıktısını (`[label]`) `vflip`/`transpose` gibi filtrelere VE aynı
    zamanda başka bir yerde (örn. `overlay`) doğrudan besliyorsan, önce `split` ile açıkça
    çoğalt.** Bunu atlamak (örn. `[eqh]vflip[x]` ve `[eqh]transpose=1[y]` gibi aynı etiketi
    birden fazla filtreye vermek) sessizce bozuk/kayıp içerik üretiyor (bu oturumda kartın
    tamamen kaybolmasına neden oldu, saatlerce debug gerektirdi). `[label]split=N[a][b][c]...`
    yaz, her dala AYRI kopya ver. Ham girdi etiketlerini (`[0:v]` gibi) birden fazla yerde
    kullanmak bu sorunu YAŞAMADI — sorun özellikle bir FİLTRE çıktısının çoklu tüketiminde çıktı.

## Performans Notları

- Tüm platformlar (`config.PLATFORMS`, şu an 2 tane) **paralel** render ediliyor (`ThreadPoolExecutor`).
- Kart tasarımı, eski tam ekran + Ken-Burns + waveform tasarımına göre doğası gereği çok
  daha hafif: kartın kendisi statik (zoom yok, sadece backdrop hareketli), çerçevenin dışındaki
  büyük alan backdrop ile dolduruluyor ama waveform/eşitleyici çubuğu yok — kaldırıldı.
  Backdrop'taki pan/hue de ucuz (crop + hue filtreleri, geq gibi her karede yeniden
  hesaplama gerektirmiyor), performansa ölçülebilir bir maliyeti yok.
- Aynı şarkıyı sadece başlık değiştirerek tekrar tekrar render etmenin önbellekleme ile
  hızlandırılması **bilinçli olarak yapılmadı** — iki kademeli bir önbellek ikinci nesil
  sıkıştırma kaybı getirir ve gerçek kullanım akışında (şarkı başına tek render) faydası yoktur.
  Her render her zaman orijinal kaynak dosyalardan yapılır — kalite kaybı birikmez.
