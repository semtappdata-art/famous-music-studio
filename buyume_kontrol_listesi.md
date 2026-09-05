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

## 4. (ACİL, tek seferlik) Yeni kapak tasarımına geçiş — eski Instagram/TikTok
paylaşımlarını elle temizle
2026-09-05'te 7 eski şarkı yeni kapak tasarımıyla (Pexels fotoğraf + altın amblem)
yeniden render edilip YouTube/TikTok/Instagram'a YENİDEN yüklendi (eskinin
YERİNE değil, yanına). YouTube tarafını kod (YouTube API) hallediyor — yeni
videoyu public yapıp eskisini siliyor (bkz. proje hafızası,
`youtube_quota_migration_pending`). **Ama Instagram ve TikTok'ta eski
gönderiyi silmek API'den mümkün değil** (Instagram: bu projenin kullandığı
"Instagram Login" — graph.instagram.com — media delete endpoint'ini
desteklemiyor, sadece eski "Facebook Login" akışı destekliyor, WebSearch ile
doğrulandı 2026-09-05; TikTok: Content Posting API'de yayınlanmış/taslak bir
gönderiyi silme/iptal etme endpoint'i yok). Bu yüzden aşağıdakiler SENİN
uygulamalardan elle yapman gereken adımlar:

- **Instagram** (uygulamadan sil): "Bir Bahar Daha" (eski media_id
  17989399238849006), "Sabaha Kadar" (18016641764731825), "beni bırakma"
  (18416877271155090), "ilk otomasyon" (18134444965723339). "Kalbim Oynuyo"
  (eski: 18112520588001058) ve "ilk-sarkim" (eski: 17957449007998018) için
  yeni post henüz yayınlanmadı (golden-hour bekliyor) — yeni post canlıya
  çıktıktan SONRA eskisini sil. "Kumdan Denize"de silinecek eski bir post yok
  (eski konteyner hiç yayınlanmamıştı, kendiliğinden 24 saatte düşer).
- **TikTok** (uygulamadan): her şarkı için gelen kutusunda YENİ bir taslak var
  (yeni kapakla) — bunu yayınla, SONRA eğer eski gönderi zaten canlıysa onu
  sil/gizle. Etkilenen: "Bir Bahar Daha", "Sabaha Kadar", "beni bırakma",
  "ilk otomasyon", "Kumdan Denize" (bu sonuncusu TikTok'a ilk kez yükleniyor,
  silinecek eski bir gönderi yok). "ilk-sarkim" ve "Kalbim Oynuyo"nun TikTok'u
  bu migrasyonda hiç dokunulmadı (değişiklik yok).

## 5. (TEK SEFERLİK) Instagram ve TikTok'ta bio linkini famousmusicstudio.com'a bağla
Instagram/TikTok yorumlarında düz metin linkler tıklanamıyor (platform kısıtı,
WebSearch ile doğrulandı) — tek gerçekten tıklanabilir yer profildeki "bio
link". Her paylaşım sonrası eklenen yoruma artık "Profildeki linkten de
kanalımıza ulaşabilirsin 🔗" satırı eklendi (`social_text.build_youtube_comment`,
2026-09-05) — ama bu satırın işe yaraması için SEN Instagram ve TikTok
uygulamalarından profil düzenle → bio link alanına `https://famousmusicstudio.com`
yazmalısın (site zaten hazır, GitHub Pages'te yayında, YouTube/Instagram/TikTok
linklerini içeriyor). API'den değiştirilemiyor (bio, content-publishing
kapsamının dışında), bu yüzden elle. Meta Verified (ücretli, Reels'e özel
tıklanabilir link, $49.99/ay'dan başlıyor) araştırıldı ama hem pahalı hem
otomasyonla (Content Publishing API) uyumluluğu doğrulanamadığı için ücretsiz
bio-link çözümü tercih edildi.

## Zaten otomatik olan (bu listede DEĞİL)
- Trend hashtag'ler → `config.DISCOVERY_HASHTAGS`, her caption'a otomatik ekleniyor
- Yorum artırma sorusu → her caption'ın sonunda otomatik
- Paylaşım saatleri (12:00-14:00 / 18:00-22:00 aralığı) → Görev Zamanlayıcı zaten 13:00/19:00
