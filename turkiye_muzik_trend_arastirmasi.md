# Türkiye Geneli Müzik Tarz Trendleri

**Son güncelleme: Eylül 2026** (WebSearch ile araştırıldı — bu liste zamanla eskir, birkaç ayda
bir tekrar kontrol edilmeli, bkz. `trend_hashtag_notlari.md`'deki aynı disiplinle).

Amaç: kanalın hangi müzik tarzlarına öncelik vermesi gerektiğine, kendi kanalımızın (henüz
çok düşük) izlenme verisiyle DEĞİL, Türkiye genelindeki gerçek dinleme trendleriyle karar
vermek.

## Bulgular (Spotify/YouTube Music/Apple Music Türkiye, 2025-2026 yıl sonu raporları)

1. **Rap/Trap** — Türkiye'nin tartışmasız baskın türü. Spotify'da tür bazında lider, YouTube
   Music'te en yüksek büyüme oranı, Apple Music Türkiye'de yılın en çok dinlenen türü.
2. **Arabesk-Pop / melodik trap-arabesk melezi** — yılın en hızlı yükselen türü, rap'in hemen
   arkasında. Semicenk, Muti, Heijan gibi sanatçılar rap/trap'i arabesk duygusal vokalle
   harmanlıyor — hem ritmik hem duygusal bir deneyim sunuyor. **Bu saf "arabesk" değil,
   spesifik bir melez alt tür.**
3. **Türkçe Pop** — hâlâ geniş bir taban, arabeskin erişimine yakın, rap'in çok üzerinde
   (özellikle daha geniş/farklı demografilerde).
4. **İndie/Alternatif** — öne çıkan bir diğer tür.
5. **Elektronik/Lo-fi** — öne çıkan, büyüyen bir tür.

## Kataloğun mevcut 6 temasıyla (config.THEMES) karşılaştırma

- `hiphop` → rap/trap'e karşılık geliyor, **1 numaralı öncelik** olmalı.
- `arabesk` → saf arabesk yerine **arabesk-pop/melodik trap-arabesk melezi** olarak
  düşünülmeli — bu, saf geleneksel arabeskten daha güncel/trend bir yorum.
- `pop` → doğrudan karşılığı var, geniş taban.
- `akustik` → indie/alternatif ile kısmen örtüşüyor ama birebir aynı değil (akustik daha
  sakin/organik, indie daha "prodüksiyonlu alternatif" bir tını olabilir) — tam eşleşme değil.
- `elektronik` → doğrudan karşılığı var.
- **`rock` → bu araştırmada Türkiye'nin öne çıkan trend türleri arasında HİÇ geçmedi.**
  Kataloğun 6 temasından tek kullanılmamış slot rock'tu (bkz. `ses_ve_tarz_takibi.md`) —
  "boş slotu doldur" mantığıyla sıradaki şarkı için rock önerilmişti (bkz. git geçmişi,
  müzik prodüksiyon ajanı denetimi). Bu araştırma o öneriyle ÇELİŞİYOR: rock, Türkiye
  genelinde şu an öne çıkan bir büyüme alanı değil. Katalog çeşitliliği açısından rock hâlâ
  makul bir seçim ama büyüme/erişim önceliği açısından hiphop, arabesk-pop melezi veya pop
  daha güçlü bir bahis.

## Öneri (öncelik sırası, hacim gerçeği göz önünde — bkz. auto_process.py `--count`)

1. **hiphop (rap/trap)** — en güçlü sinyal, öncelik.
2. **arabesk (melodik trap-arabesk melez tonda, saf ağıt değil)** — ikinci güçlü sinyal.
3. **pop** — geniş taban, güvenli seçim.
4. `elektronik`/`akustik` — daha düşük ama gerçek talep.
5. `rock` — veri bunu desteklemiyor, katalog çeşitliliği için hâlâ makul ama büyüme
   önceliği DEĞİL.

**Not:** Bu, kendi kanalımızın performansı değil, Türkiye genel piyasası — kanalın kendi
gerçek verisi (`weekly_report.py`) birkaç hafta/ay biriktikçe bu genel piyasa tahminini
kendi gerçek sonuçlarımızla çapraz kontrol etmek gerekir; ikisi çelişirse kendi verimiz
kazanır.

## Kaynaklar

- https://www.nethaberler.com/haber-turkiyede-en-cok-dinlenen-muzik-turu-2025-rap-zirvede-gunde-kac-saat-muzik-dinliyoruz-111076.html
- https://www.firsat.me/Blog/youtube-music-turkiye-2025-dijital-dalgalarda-en-cok-dinlenenler-ve-toplumsal-ruhun-yankisi
- https://muzikanaliz.com/karsilastirmali-platform-analizi-turkiyede-2025-dijital-muzik-tuketimi/
- https://susambulten.com/dis-ticaretin-haritasi-genclerin-kulaginda-pop-rap-ve-klasik-muzik-var/
- https://artistryofgood.com/spotify-wrapped-2025-ve-kulturel-donusum/
