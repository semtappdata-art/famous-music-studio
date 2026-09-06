# Sokaklar Beni Tanır — Orijinal Sözler (Hip-Hop/Trap)

Suno'nun Lyrics kutusuna aynen yapıştırılabilir.

> Yeni bir şarkı prompt'u yazmadan önce `ses_ve_tarz_takibi.md`'ye bak —
> vokal cinsiyeti/dokusu art arda tekrarlanmasın.

**Neden bu tema:** Tema gece, yalnızlık, şehir, terk edilmişlik — marka evrenine
uygun (Beni Bırakma ile aynı ruh hali). Sözler tekli anlatıcı (düet formatında
DEĞİL), bu yüzden `arabesk` yerine `hiphop` seçildi — `arabesk` teması bu
katalogda SABİT olarak düet formatında üretiliyor (bkz. CLAUDE.md), tekli bir
anlatı bu kurala uymaz. `hiphop`, Türk trap/dark-pop için en yakın slot
(Beni Bırakma da bu kovada izleniyor, bkz. `ses_ve_tarz_takibi.md`). Son
loglanan vokal Kumdan Denize'de kadındı, bu yüzden erkeğe dönülüyor; "husky/
raspy/warm-smooth/gritty" dokuları son şarkılarda kullanıldığı için "deep,
world-weary" (henüz kullanılmamış) seçildi.

## Stil Etiketi (Suno Style kutusuna yapıştır)

```
Turkish trap hip-hop, melancholic and cinematic, deep world-weary male vocals, moody synth pads, muted 808 bass, rain-soaked city night atmosphere, gentle fade-out ending
```

## Sözler (Suno Lyrics kutusuna yapıştır)

```
[Intro]
Gece yine sessiz, ben yine yalnız
Şehir ışıkları söner, ben hâlâ ayaktayım

[Verse 1]
Islak asfaltta yankılanır adımlarım
Kimse duymaz, kimse sormaz halimi
Neon tabelalar yazar adımı
Ama sen yoksun, sensiz bu şehir yabancı

[Pre-Chorus]
Bir sigara, bir yağmur, bir sen eksik
Kalbim hâlâ o sokakta unutulmuş
Ne kadar yürüsem de geri dönemem
Zaman durmuyor, ben duruyorum

[Chorus]
Sokaklar beni tanır, sen tanımadın
Her köşede bir anı, sen unutmadın mı
Gece bana sarılır, sen sarılmadın
Sokaklar beni tanır, ben hâlâ oradayım

[Verse 2]
Vitrinler parlar, kalbim kararır
Herkes geçer yanımdan, kimse durmaz
Bu şehrin her sokağı bir hikaye anlatır
Benimkinde hep sen varsın, hep aynı yerde kalırsın

[Chorus]
Sokaklar beni tanır, sen tanımadın
Her köşede bir anı, sen unutmadın mı
Gece bana sarılır, sen sarılmadın
Sokaklar beni tanır, ben hâlâ oradayım

[Bridge]
Belki bir gün bu sokaklar unutur beni
Belki bir gün ben de unuturum seni
Ama bu gece, bu yağmur, bu yalnızlık
Hepsi senin, hepsi bu şehrin

[Outro]
Sokaklar beni tanır, ben hâlâ oradayım.
Gece bana sarılır, ben hâlâ buradayım.
```

## Temiz Sözler (YouTube açıklaması için kopyala-yapıştır)

```
Gece yine sessiz, ben yine yalnız
Şehir ışıkları söner, ben hâlâ ayaktayım

Islak asfaltta yankılanır adımlarım
Kimse duymaz, kimse sormaz halimi
Neon tabelalar yazar adımı
Ama sen yoksun, sensiz bu şehir yabancı

Bir sigara, bir yağmur, bir sen eksik
Kalbim hâlâ o sokakta unutulmuş
Ne kadar yürüsem de geri dönemem
Zaman durmuyor, ben duruyorum

Sokaklar beni tanır, sen tanımadın
Her köşede bir anı, sen unutmadın mı
Gece bana sarılır, sen sarılmadın
Sokaklar beni tanır, ben hâlâ oradayım

Vitrinler parlar, kalbim kararır
Herkes geçer yanımdan, kimse durmaz
Bu şehrin her sokağı bir hikaye anlatır
Benimkinde hep sen varsın, hep aynı yerde kalırsın

Sokaklar beni tanır, sen tanımadın
Her köşede bir anı, sen unutmadın mı
Gece bana sarılır, sen sarılmadın
Sokaklar beni tanır, ben hâlâ oradayım

Belki bir gün bu sokaklar unutur beni
Belki bir gün ben de unuturum seni
Ama bu gece, bu yağmur, bu yalnızlık
Hepsi senin, hepsi bu şehrin

Sokaklar beni tanır, ben hâlâ oradayım
Gece bana sarılır, ben hâlâ buradayım
```

## Notlar

- Vokal dili: Türkçe ("deep world-weary male vocals" + Türkçe sözler).
- Vokal cinsiyeti: Kumdan Denize'nin (kadın) ardından erkeğe dönüldü, doku
  "deep, world-weary" — daha önce kullanılmamış bir kombinasyon.
- Tema: gece, yalnızlık, terk edilmişlik, şehir — Beni Bırakma ile aynı ruh
  hali, ama tekli anlatıcı olduğu için `arabesk` (düet-zorunlu) yerine
  `hiphop` seçildi.
- `config.py`'deki `theme` alanı için: `"hiphop"` (accent turuncu/sarı).
- Kapanış: stil etiketine `gentle fade-out ending` eklendi (şarkının
  melankolik/duygusal tonuna göre — `hiphop` teması genelde "strong final
  hit" alsa da, bu şarkının sözleri sakin/hüzünlü, müzikal tona uyan kapanış
  tercih edildi), Outro iki tam cümleye çevrildi (eskiden "Sokaklar beni
  tanır..." ile yarım bırakılmıştı — bkz. `suno_prompt_hazirlik.md`,
  "Kapanış (Outro) kuralı").
- Intro kuralına uygun: ilk satır temayı doğrudan adlandırmıyor ("Gece yine
  sessiz, ben yine yalnız" — somut an/duyu imgesi, "sokaklar beni tanır"
  temasını dolaylı hissettiriyor, ilk kez Chorus'ta açıklanıyor).
