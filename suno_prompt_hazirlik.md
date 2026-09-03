# Yeni Şarkı Kontrol Listesi (Suno → Video)

Suno API erişimi yok — bu akış manuel: prompt hazırla → Suno.com'a yapıştır → indir → proje klasörüne koy.

> **Lisans/ticari kullanım notu:** Bu kanaldaki her şarkı Suno çıktısı ve ticari amaçla
> (marka hesabı) YouTube/TikTok/Instagram'a yükleniyor. Suno'nun ücretsiz/ücretli plan
> katmanlarına göre ticari kullanım ve platform dağıtım hakları farklılık gösterebilir —
> bu, hesaba özel ve zamanla değişen bir konu olduğu için burada belgelenmiyor. Kendi Suno
> aboneliğinin güncel Kullanım Şartları'nı bir kere kontrol edip bu kullanımı kapsadığından
> emin ol (henüz yapılmadıysa).

## Adımlar

1. **Stil etiketini Suno'nun Style kutusuna yapıştır** (aşağıdaki örneğe bak, şarkıya göre uyarla)
2. **Şarkı yapısını Lyrics kutusuna yapıştır** (bölüm etiketleri + kendi sözlerin)
3. **Suno'da üret, `audio.wav` olarak indir**
4. **Kapak görseli indir/hazırla** (`cover.jpg` veya `.png`)
5. **Proje klasörü aç:** `projects/<şarkı-adı>/` (Türkçe karakter/boşluk sorun değil, önceki projelerde çalıştı)
6. `audio.wav` ve `cover.png`'yi bu klasöre koy
7. **(Opsiyonel) Kart içeriği:** `art.jpg/png` ekle — kartın İÇİNDE görünecek görsel (kapaktan farklı, temaya uygun bir sahne/illüstrasyon). Yoksa düz renkle doldurulur.
8. **`meta.json` oluştur:**
   ```json
   {"title": "Şarkı Adı", "theme": "hiphop"}
   ```
   `theme` seçenekleri: `pop`, `rock`, `elektronik`, `akustik`, `hiphop` (Türk trap/arabesk için en yakını — "Trap" related tag'i zaten var)
9. **Render et:**
   ```bash
   python render.py --project "projects/<şarkı-adı>"
   ```
10. `output/` klasöründeki 3 videoyu kontrol et

## Örnek Stil Etiketi (referans, şarkıya göre uyarla)

```
Turkish trap arabesk, melancholic and cinematic, husky male vocals, 808 bass, kanun strings, minor key piano, rain-soaked night atmosphere, gentle fade-out ending
```

(7 tanımlayıcı — genre+mood önde, sonra vokal/enstrüman, SONA bir kapanış tanımı — bkz. "Kapanış (Outro) kuralı". Suno v4.5+ için optimal aralık.)

## Şarkı Yapısı Şablonu (Custom Mode → Lyrics kutusuna yapıştır, sözleri kendin doldur)

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

## Notlar

- Vokal dili: Türkçe belirtmeyi unutma (örn. "Turkish male vocals")
- Tema tutarlılığı: gece, neon ışıklar, yalnız yürüyüş, şehir — marka evreninin (Famous Music Studio) genel ruh hali
- Her yeni şarkı için bu dosyayı referans al, stil etiketini şarkının kendi temasına göre uyarla
- `theme` seçenekleri (meta.json): `pop`, `rock`, `elektronik`, `akustik`, `hiphop`, `arabesk` (`config.THEMES`'teki 6 slot)
