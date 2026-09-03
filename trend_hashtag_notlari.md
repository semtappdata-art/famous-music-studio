# Trend Hashtag Notları

**Son güncelleme: Eylül 2026** (WebSearch ile araştırıldı — bu liste zamanla
eskir, birkaç ayda bir tekrar kontrol edilmeli).

`config.py`'deki `DISCOVERY_HASHTAGS` bu araştırmaya dayanıyor, `build_caption()`
her paylaşımda otomatik ekliyor. Buradaki liste referans/güncelleme kaynağı.

## Genel keşfet etiketleri (platform bağımsız)
`#keşfet` `#fyp` `#viral` `#keşfetteyiz` `#trend`

## Suno/AI müzik nişi
`#SunoAI` `#ŞarkıYap` `#AIGeneratedMusic`

NOT: `#AIMusic`/`#YapayZekaMüzik` bilerek listede/kullanımda YOK — kullanıcı kararı:
hiçbir üretimde (caption, YouTube tag, video içi kayan yazı) bu ibareler
kullanılmasın. ZORUNLU AI-üretimi bildirimi bundan ayrı bir mekanizma, hâlâ yerinde
(bkz. `config.py`'deki `BRAND_HASHTAGS` notu).

## En iyi paylaşım saatleri (Türkiye)
Araştırmaya göre 12:00-14:00 ve 18:00-22:00 arası — bizim mevcut
Görev Zamanlayıcı ayarımız (13:00 ve 19:00) bu pencerelerle zaten örtüşüyor,
değiştirmeye gerek yok.

## Güncelleme nasıl yapılır
Birkaç ayda bir (örn. her yeni şarkı döneminde) şunu sorup güncel listeyi
kontrol et: *"TikTok Türkiye trend hashtag [ay] [yıl] keşfet müzik"* ve
*"Suno AI müzik TikTok Instagram hashtag yapay zeka şarkı viral [yıl]"* —
sonuçlara göre `config.DISCOVERY_HASHTAGS`'i güncelle.

## Kaynaklar (Eylül 2026 araştırması)
- https://clipchamp.com/tr/blog/tiktok-trends-challenges/
- https://www.tiktok.com/discover/ke%C5%9Ffete-d%C3%BC%C5%9Fme-etiketleri
- https://www.tiktok.com/discover/suno-ai-t%C3%BCrk%C3%A7e-yapay-zeka-%C5%9Fark%C4%B1
