# Büyüme Kontrol Listesi (elle yapılan adımlar)

Bunlar kodla otomatikleştirilemeyen, senin elle yapman gereken adımlar —
"gerçekçi analiz" sohbetinde konuşulan planın kod-dışı kısmı.

## 1. Trend ses/format kullan (TikTok)
Kendi orijinal müziğini paylaşmaya devam et (otomasyon zaten bunu yapıyor) —
ayrıca ara sıra o anki **trend olan bir sesi** kullanarak kısa, davetkâr bir
video da paylaş (örn. "bu sesi AI ile ben besteledim" tarzı bir duet/stitch).
Trend sesler TikTok'un "Keşfet" akışına çok daha hızlı taşıyor.

## 2. İlk 20-30 gerçek takipçiyi manuel bul
Soğuk başlangıç sorununu aşmanın en pratik yolu — ilgili topluluklarda
(Reddit r/SunoAI, Türkçe AI müzik Discord sunucuları/grupları) hesabı
paylaşmak. İlk birkaç düzine gerçek etkileşim, algoritmanın hesaba
güvenmeye başlaması için kritik — bunu otomasyon yapamaz, sosyal bir adım.

## 3. Haftalık takip
Her hafta şunu çalıştır (veya Remote Control oturumuna yaptır):
```
python weekly_report.py
```
Tüm şarkıların YouTube izlenme/beğeni/yorum sayılarını tazeleyip özet bir
tablo basar. Düz bir çizgi 2-3 hafta devam ederse, reklam/boost bütçesi
konuşmaya değer — o zaman bu sohbete dönüp konuşalım.

## Zaten otomatik olan (bu listede DEĞİL)
- Trend hashtag'ler → `config.DISCOVERY_HASHTAGS`, her caption'a otomatik ekleniyor
- Yorum artırma sorusu → her caption'ın sonunda otomatik
- Paylaşım saatleri (12:00-14:00 / 18:00-22:00 aralığı) → Görev Zamanlayıcı zaten 13:00/19:00
