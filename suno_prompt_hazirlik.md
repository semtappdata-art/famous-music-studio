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
Turkish trap arabesk, melancholic and cinematic, husky male vocals, 808 bass, kanun strings, minor key piano, rain-soaked night atmosphere
```

(7 tanımlayıcı — genre+mood önde, sonra vokal/enstrüman. Suno v4.5+ için optimal aralık.)

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
```

## Notlar

- Vokal dili: Türkçe belirtmeyi unutma (örn. "Turkish male vocals")
- Tema tutarlılığı: gece, neon ışıklar, yalnız yürüyüş, şehir — marka evreninin (Famous Music Studio) genel ruh hali
- Her yeni şarkı için bu dosyayı referans al, stil etiketini şarkının kendi temasına göre uyarla
