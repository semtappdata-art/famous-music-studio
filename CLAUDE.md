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
audio.wav → generate_cover.py (eksikse cover/art üretir) → render.py (ffmpeg ile video)
    → auto_process.py: YouTube (uzun+Shorts) + TikTok + Instagram yükleme
```

- `config.py` — tüm görünüm/kalite ayarları (temalar, kart boyutu, backdrop pan/hue hızı, vb.)
- `ffmpeg_utils.py` — kart+backdrop+marquee+progress-bar filtergraph inşası
- `generate_cover.py` — eksik cover/art'ı tema rengi + bokeh dokusuyla otomatik üretir
- `auto_process.py` — asıl production giriş noktası, `--count` kadar bekleyen projeyi işler
- `upload/*.py` — platform bazlı yükleme + OAuth (youtube_auth, tiktok_auth, instagram_auth)
- `upload/social_text.py` — caption/hashtag/etkileşim sorusu üretimi (şarkı başlığından
  deterministik seçim — aynı şarkı hep aynı satırları alır)

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
- **Koşu başına proje sayısı (`--count`, varsayılan 2)**: bir ara bilinçli olarak 1'e
  düşürülüp günde 2 AYRI Görev Zamanlayıcı tetikleyicisine geçilmişti ("aynı anda birden
  fazla şarkı aynı takipçi kitlesinde birbiriyle yarışır" riski) — kullanıcı bu riski
  bilerek tekrar yükseltilmesini istedi.
- **AI-içerik açıklaması**: kanal %100 AI üretimi olduğu için YouTube upload'ında
  `containsSyntheticMedia: True` set ediliyor (resmi kaynakla doğrulandı). TikTok/Instagram
  tarafında resmi API alan adı bu ortamdan doğrulanamadı — koda hiçbir şey eklenmedi (yanlış
  alan adı riskli), sadece kullanıcıya elle etiketleme hatırlatması var.

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
