# YouTube A/B Test (Test & Compare) Rehberi

## Genel Bakış
YouTube'un **Test & Compare** özelliği, videonuz için en fazla 3 farklı kapak (thumbnail) ve/veya başlık test etmenizi sağlar. Kazanan, **izlenme süresi (watch time)** alapján belirlenir.

## Gereksinimler
- YouTube Studio **Gelişmiş Özellikler** etkin olmalı
- Video: **Shorts, Scheduled Live, Premiere** OLMAYAN normal uzun format videolar
- İçerik: **Made for Kids** veya **18+** OLMAYAN videolar
- Kapak çözünürlüğü: **720p+** (1280x720 minimum), aksi takdirde 480p'ye düşürülür

## Nasıl Kullanılır

### 1. Yeni Video İçin
1. YouTube Studio → **İçerik** → **Video Yükle**
2. Video yüklendikten sonra **Detaylar** sekmesine git
3. **Kapak** bölümünde **A/B Testi** butonuna tıkla
2. **Thumbnail only**, **Title only** veya **Title and thumbnail** seç
3. En fazla 3 varyant yükle (A, B, C)
4. **Bitti** → Test başlar

### 2. Mevcut Video İçin
1. YouTube Studio → **İçerik** → Video seç
2. **Detayları Düzenle** → **Kapak** → **A/B Testi**
3. Varyantları yükle → **Bitti**

## Test Süreci
- **Süre:** ~2 hafta (en fazla)
- **Kazanan:** En yüksek **izlenme süresi (watch time share)** olan
- **İstatistiksel Anlamlılık:** YouTube otomatik hesaplar
- **Kazanan Yoksa:** İlk yüklenen (A) varsayılan kalır
- **Test Sırasında Değişiklik:** Test otomatik durur, yeniden başlatılmalı

## Varyant Oluşturma Stratejileri

### Kapak Varyantları (En Etkili)
| Varyant | Fark | Ne Zaman İşe Yarar |
|---------|------|-------------------|
| **A (Kontrol)** | Mevcut tasarım | Baz çizgi |
| **B (Varyant)** | Farklı renk paleti (accent2) | Renk psikolojisi testi |
| **C (Varyant)** | Farklı yerleşim (sol üst logo, sağ alt başlık) | Görsel hiyerarşi testi |

### Otomatik Varyant Üretimi (Bizim Sistemimiz)
Sistemimiz **cover_generator.py** ile otomatik üretir:
- **Variant A (Ana):** Standart tasarım (ortada başlık, sağ alt logo)
- **Variant B (Test):** `cover_variant_B.png` + `cover_vertical_variant_B.png`
  - Farklı renk: Tema `accent2` rengi
  - Farklı yerleşim: Sol üst logo, sağ alt başlık
  - Farklı arka plan: Vignette + hafif blur

### Otomatik Üretim Kodu
```python
# cover_generator.py içinde
_generate_variant_b_covers(bg_path, cover_b_path, cover_v_b_path, title, theme, is_photo)
# Üretir: cover_variant_B.png + cover_vertical_variant_B.png
```

## En İyi Uygulamalar (Best Practices)

### 1. Varyantlar Arasında Anlamlı Fark Olmalı
- ❌ Kötü: Sadece yazı rengi değiştirmek
- ✅ İyi: Tamamen farklı renk paleti + yerleşim
- ✅ İyi: Farklı odak noktası (yüz vs mekan vs metin)

### 2. Test Öncesi Kontrol Listesi
- [ ] 3 varyant da 720p+ çözünürlükte mi?
- [ ] Mobilde %10 boyutta okunuyor mu? (thumbnail küçültme testi)
- [ ] Marka logosu görünür mü?
- [ ] Başlık 4 kelimeyi geçmiyor mu? (mobilde kesilmez)

### 3. Test Süresi ve Sonuç
- **Minimum:** 3-4 gün (istatistiksel anlamlılık için)
- **İdeal:** 7-14 gün (haftalık döngü tamamlanması için)
- **Sonuç:** YouTube Studio → Analytics → Reach → **Test & Compare** sekmesi

### 4. Sonuç Değerlendirme
| Sonuç | Anlamı | Aksiyon |
|-------|--------|---------|
| **Winner** | Belli bir varyant net kazandı | O varyantı ana yap |
| **Performed Same** | Fark anlamlı değil | Tercih ettiğiniz kalsın |
| **Inconclusive** | Veri yetersiz | Test uzat veya yeni varyant dene |

## Bizim Sistemimizde Entegrasyon

### Otomatik Üretim
`cover_generator.py` → `_generate_variant_b_covers()` fonksiyonu:
```python
_generate_variant_b_covers(bg_path, cover_b_path, cover_v_b_path, title, theme, is_photo)
# Üretir: cover_variant_B.png + cover_vertical_variant_B.png
```

### Çalışma Akışı
1. `render.py` → `cover_generator.py` çağırır
2. Ana kapak (A) + Variant B (B) otomatik üretilir
3. YouTube yükleme sırasında manuel A/B testi başlatılır
2 hafta sonra sonuç analiz edilir → bir sonraki hafta için iyileştirme

## İpuçları ve Püf Noktalar

### 1. Eski Videolarda Test Et
- Yeni videolarda değil, **hali hazırda izlenme alan videolarda** test et
- Etki daha hızlı ölçülür

### 2. Farklı Varyant Sayısı
- 2 varyant (A/B) → Hızlı sonuç
- 3 varyant (A/B/C) → Daha kapsamlı ama daha uzun süre

### 3. Mobil Öncelikli
- Thumbnail'in %10 boyutunda (mobilde) okunuyor mu?
- Test et: `ffmpeg -i cover.png -vf "scale=128:72" thumb_small.png`

### 4. Renk Psikolojisi
| Renk | Etki | Kullanım Alanı |
|------|------|----------------|
| Kırmızı/Turuncu | Aciliyet, enerji | Club, peak-time |
| Mavi/Mor | Güven, derinlik | Melodic, ambient |
| Yeşil | Doğa, huzur | Organic, nature |
| Altın/Sarı | Prestij, ısınma | Sunset, golden hour |

### 5. Sıralama ve Zamanlama
- Test başlat → En az 7 gün bekle
- Sonuç net değilse → 14 güne uzat
- Hala belirsizse → Yeni varyant üret, tekrar test et

## Otomasyon Entegrasyonu (Gelecek)

### Planlanan Özellikler
1. **Otomatik A/B Test Başlatma:** YouTube Data API v3 ile otomatik başlatma
2. **Sonuç Takibi:** Günlük izlenme süresi takibi + otomatik rapor
3. **Otomatik Kazanan Seçimi:** İstatistiksel anlamlılık kontrolü + otomatik uygulama
4. **Geçmiş Veri Analizi:** Hangi varyant tipleri hangi içerik türünde kazanıyor?

## Sorun Giderme

### Test Başlamıyorsa
- Gelişmiş özellikler etkin mi? (YouTube Studio → Ayarlar → Kanal → Gelişmiş)
- Video Shorts/Premiere/Scheduled Live mi? (Bunlar test edilemez)
- 18+ veya Made for Kids mi? (Bunlar test edilemez)
- Kapak 720p+ mi? (Daha düşükse 480p'ye çekilir)

### Sonuç Anlamsızsa
- Varyantlar çok benzer mi? → Daha radikal fark yarat
- Test süresi yeterli mi? → En az 7-14 gün bekle
- Trafik yetersiz mi? → Daha fazla görüntüleme bekle veya reklam destekli test

---

## Kaynakça
- [YouTube Help: A/B test titles & thumbnails](https://support.google.com/youtube/answer/16391400)
- [YouTube for Artists: Growing your audience](https://artists.youtube/resources/growing-your-audience/)
- [Indie Artist Stack: YouTube Promotion 2026](https://indieartiststack.com/guides/how-to-promote-music-on-youtube-2026)

---

*Son güncelleme: 2026-10-19 | Versiyon 1.0*