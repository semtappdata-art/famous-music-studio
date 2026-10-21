# PROFESYONEL MÜZİK ŞİRKETİ + YOUTUBE PAZAR LİDERİ — DERİN ANALİZ

**Tarih:** 2026-10-19 | **Kaynaklar:** YouTube Help (Release Strategy, Test & Compare),
YouTube for Artists (Listener→Fan), promolink 2026 elektronik takvimi, Music Ally Sandbox
(Anjunadeep/Defected/Ninja Tune A&R röportajları), Proton Soundsystem A&R kılavuzu,
The Source rollout, Tunepact/Gyre/GetMoreStreams 2026 rehberleri, Indie Artist Stack
**Kural:** Sektörün yaptığını biz otomasyona dökeriz — her maddenin sonunda dosya + aksiyon.

---

## BÖLÜM 1 — PROFESYONEL LABEL NEYİ FARKLI YAPAR (7 davranış)

### 1.1 T-minus takvimi: yayın günü değil, 5 hafta önce başlar
Profesyonel elektronik yayın akışı (promolink 2026, The Source rollout):
- **T-5 hafta:** Dar listeye DJ promo (10–20 tanınmış isim) — Carl Cox/Charlotte de Witte tipi isimlere alan bırakılır
- **T-4/5:** Distribütör upload + **Spotify for Artists pitch AYNI hafta** (editörler 4 hafta ister; Spotify'ın resmi son günü 7 gün ama o editöre zaman bırakmaz)
- **T-3/4:** Geniş DJ listesi — gövdede "Supported by [X]" (ikinci dalga = onay damgası, duyuru değil)
- **T-2:** İçerik yığını — dikey klipler; uzun işler (visualiser/klip) sonraki hafta
- **T-1:** SmartLink + pre-save + son hatırlatma (Beatport butonları hazır)
- **Yayın günü:** İcraat | **T+1/3:** Büyüme (klip + DJ cascade + akıllı reklam, Discover Weekly/Release Radar sinyalleri izlenir)
- **Bizde:** `yayin_ritmi.py` gün/saat tutar ama T-minus fazları YOK. **Aksiyon:** Her projeye `takvim.json` (T-5→T+3 kontrol listesi) + `auto_process` faz kapısı. Tek şarkı = tek upload değil, 8 haftalık operasyondur.

### 1.2 DJ promo cascade: promo pool = keşif radarı
Label'lar promo havuzunu iki yönlü kullanır: (a) destek toplar, (b) **hangi artistin hangi parçayı sevdiğini izleyip remixçi seçer** (Proton A&R: "promo pool'un en güçlü kullanımı"). İkinci dalga mailde "Supported by Adam Beyer" yazar — açılma oranını konu başlığından çok bu cümle artırır.
- **Bizde:** DJ listesi + destek takibi yok. **Aksiyon:** `promo_havuzu.json` (gönderilen/kim açtı/kim çaldı) + Bluesky/IG DM şablonu. Küçük başla: her setten önce 15 DJ hesabına stem/özel link.

### 1.3 Beatport ↔ Spotify cross-feed (elektroniğe özel kaldıraç)
Spotify editörleri karar öncesi **Beatport chart'a bakar**. Doğru sıra: DJ promo → Beatport hareketi → Spotify pitch. Ters sıra cross-feed'i çöpe atar. Pitch'e gerçekten destekleyen 2–3 DJ ismi yazılır (uydurma isim = label kara listesi).
- **Bizde:** DistroKid planı var (§11) ama pitch prosedürü yok. **Aksiyon:** DistroKid çıkışlarında Spotify for Artists pitch şablonu (tür + hikaye + şehir + pazarlama planı) + Beatport penceresiyle aynı haftaya kilitleme.

### 1.4 Derivative sürümler: single → remix paketi → ikinci hayat
Orijinal tek başına salınır; remix'ler 1–3 ay sonra, momentuma göre (Defected: "remix, kaydın hikayesini güçlendirir" — club'da tutan parçaya club-remix, radyoda tutana radyo-remix). Hit'e 6–12 ay sonra ikinci paket = ikinci basın + ikinci editoryal kapı. 2026 notu: Spotify algoritması remix'i kayırmıyor; remix'in yerini **collab** aldı (en hızlı büyüme kaldıracı).
- **Bizde:** Her parça tek sürümde ölüyor. **Aksiyon:** Tutmuş parçaya T+2 ay "blue hour remix / sunrise edit" + her sette 1 collab adayı (ör. Rikodisco/Bytemounts tarzı yerel isimle split).

### 1.5 Teslimat paketi disiplini (editör filtresi)
24-bit WAV, 3000×3000 RGB kapak (telefonda okunan tipografi), temiz metadata (artist adı Spotify/Beatport ile BİREBİR), ISRC/UPC, yazar/miks/mastering kredileri. Kötü master veya düşük kapak = editörün ilk filtresi.
- **Bizde:** Kapak otomasyonu var ama 3000×3000 + kredi bloğu standardı yok. **Aksiyon:** `validate_project`'e kapak çözünürlük + kredi alanı kontrolü.

### 1.6 Kendi playlist'ini kendin büyüt (Anjunadeep doktrini)
"Editoryal desteğe bağımlı kalmamak için önce kendi başına ayakta dur" — Anjuna kendi playlist'lerini inşa edip sonra Spotify'a "bak, pazar burada" diye götürür. Boşluk görülen türde playlist'i önce bağımsız küratör doldurur.
- **Bizde:** Playlist oluşumu `youtube_playlists.py`'de var ama Spotify tarafı yok. **Aksiyon:** "City Pulse Sessions" + "Night Drive" Spotify playlist'leri (bizim katalog + referans parçalar), her açıklamada link.

### 1.7 Tekrar etkileşim ritmi: 2 ay sessizlik = ölüm
Dans müziği avantajı hızlı üretimdir: orijinal → remix → sıradaki kayıt; hayranla SÜREKLİ konuşulur. 2 yıl susan rock grubu modeli elektroniğe uymaz.
- **Bizde:** 6 şarkı + 3 set/hafta hedefi doğru; ritim takvimi (§12) korunmalı, backlog eritme backfill ile.

---

## BÖLÜM 2 — YOUTUBE PAZAR LİDERİ DAVRANIŞLARI (9 davranış)

### 2.1 Release hub: 1 yayın = 1 ana video + uydu içerikler
Lider formül (Indie Artist Stack 2026): ana video (hedef) + Shorts (keşif) + post (tekrar temas) + playlist (oturum derinliği) + yorum (ilişki). Aynı şeyi tekrar yüklemek YOK — şarkıyı farklı açılardan göstermek VAR. Veri: klibi gören hayran ertesi ay %94 daha fazla katalog tüketir.
- **Bizde:** Uzun + Shorts var; post/playlist/yorum halkası kopuk. **Aksiyon:** Her yayın = 1 uzun + 3 Shorts + 2 topluluk postu + playlist ekleme (kontrol listesi).

### 2.2 Premiere: etkinlikse evet, rutinse hayır
Premiere = hatırlatıcı + canlı sohbet + aynı-an izleme. Kural: katılacaksan ve önceden duyurduysan yap; yoksa temiz zamanlı yayın daha iyi. (Bizim golden-hour zamanlaması zaten Premiere'in "temiz" karşılığı.)
- **Aksiyon:** Sadece seri prömiyerlerinde (Ep01, şehir değişimi) Premiere + canlı sohbet katılımı; rutinde `publishAt`.

### 2.3 Test & Compare: 3 kapak, kazanan izlenme süresiyle belli olur
YouTube Studio: 3 başlık/kapak, ~2 hafta, kazanan = en yüksek izlenme süresi (istatistiksel anlamlılık; net kazanan yoksa ilk yüklenen kalır). Shorts/Premiere'da YOK. İpucu: eskilerde dene, birbirinden FARKLI varyantlar dene, 720p+ yükle (düşük çözünürlük hepsini 480p'ye çeker).
- **Bizde:** Tek kapak, kör uçuş. **Aksiyon:** Ayda 1 eski videoda A/B (örn. landmark'lı vs. silüetli kapak) + sonucu `BUYUME_ONERILERI.md`'ye işle. Otomasyon 2. ve 3. varyantı üretebilir (`cover_generator` varyant bayrağı).

### 2.4 Topluluk sekmesi: haftada 2–3, anket kraldır (500 abone eşiği)
En yüksek kaldıraçlı post: "Sıradaki video hangisi olsun?" iki şıklı anket (betimleyici şıklar). Ritim: haftada 2–3, video öncesi 24–48 saat ısınma postu, video günü post. Günlük = spam, haftalık = momentum kaybı.
- **Bizde:** Topluluk postu otomasyonu yok. **Aksiyon:** 500 abone sonrası: yayın öncesi anket ("Sıradaki şehir: Tokyo mu Berlin mi?") + kapak A/B anketi. Şimdiden şablonları hazırla.

### 2.5 Playlist = niyet yolu, depo değil
"Rahatlama", "gece sürüşü", "yeni çıkanlar" gibi dinleyici niyetiyle grupla; yeni yayını anında ilgili listeye ekle. Tek şarkı → doğal olarak sıradaki.
- **Aksiyon:** Niyet playlist'leri: `Gece Sürüşü`, `Gün Doğumu Setleri`, `Şehir Nabzı` + bitiş ekranı "sonraki bölüm".

### 2.6 Shorts kuralları (kritik tuzaklar)
- Dikey/kare **3 dakikaya kadar** Shorts sayılır; ilk kare = kapak.
- **1 dakikadan uzun + aktif Content ID claim = dünya geneli engel.** Kendi distribütör claim'ini temizlemeden uzun klip YOK.
- Uzun videodan 3–5 Shorts: en iyi nakarat anı + yapım hikayesi + canlı vurgu.
- **Bizde:** 45sn highlight = güvenli bölgede. **Aksiyon:** 45sn sınırını KORU (bilerek); 60sn+ denenecekse önce claim taraması.

### 2.7 Content ID + allowlist (en pahalı hata)
Kayıtların Content ID'de olmalı (eşik yok, distribütör üzerinden) — eserin BAŞKALARININ videolarında bile para kazanır. Ama kritik tersi: distribütör kaydettikten sonra **kendi kanalındaki kendi videon bile claim yer** → çözümü: kanal ID'sini (UC…) distribütöre verip **allowlist** + eski claim'leri kaldırtmak. Canlı yayın ayrı kuralla kesilebilir.
- **Bizde:** DistroKid planı var ama allowlist prosedürü YOK — ilk DistroKid çıkışında kanal claim yeme riski. **Aksiyon:** DistroKid günü: (1) Content ID opt-in, (2) kanal allowlist talebi, (3) mevcut videolarda claim taraması. Bunu `SOP_yukleme.md`'ye prosedür olarak ekle.

### 2.8 YPP eşikleri + erken erişim
Tam para kazanma: 1.000 abone + (4.000 saat / 12 ay VEYA 10M Shorts / 90 gün). Erken katman: ~500 abone + 3 video + (3.000 saat / 90 gün VEYA 3M Shorts) → hayran fonlaması açılır.
- **Aksiyon:** Hedef panosu: önce 500 (topluluk + fonlama), sonra 1.000. Shorts hacmi 90 günlük pencerede izlenir.

### 2.9 Listener → Fan hunisi + Inspiration sekmesi
YouTube'un resmi hunisi: Çek (trend/collab) → Bağla (düzenli içerik) → Dönüştür (otantik etkileşim) → Tut (strateji). Trend'lere katıl + Analytics'teki Inspiration sekmesinden aranan konuları çek.
- **Aksiyon:** Ayda 1 trend Shorts (aynı ses, bizim görsel dil) + Inspiration taramasını haftalık rapora ekle.

---

## BÖLÜM 3 — FARK YARATACAK ÖZEL DETAYLAR (bizim hatta, öncelikli)

| # | Detay | Neden fark | Dosya/aksiyon |
|---|-------|-----------|---------------|
| 1 | T-minus takvimi (`takvim.json` + faz kapısı) | Label disiplini; yayın günü paniği biter | `auto_process` + yeni `takvim.json` |
| 2 | Test & Compare rutini (ayda 1 eski video) | Kapak kör uçuşu biter, CTR veriye bağlanır | `cover_generator` varyant bayrağı + manuel Studio testi |
| 3 | DistroKid allowlist prosedürü | Kendi videona claim yeme felaketini önler | `SOP_yukleme.md` + DistroKid günü kontrol listesi |
| 4 | Kendi Spotify playlist'leri (2 liste) | Editoryale "pazar burada" argümanı | Açıklamalara link, haftalık güncelleme |
| 5 | Yayın başına uydu paketi (1+3+2+playlist) | Tek upload kaderciliği biter | Yayın kontrol listesi |
| 6 | Derivative/remix penceresi (T+2 ay) | Katalog ikinci kez para/basın üretir | Takvime remix slotu |
| 7 | 45sn Shorts sınırını koru | Content ID dünya-engeli tuzağından kaçış | Kural olarak kilitli (değişiklikte test) |
| 8 | Topluluk şablonları (anket ×2) | 500 abone günü hazır olunur | Şablon + zamanlayıcı |
| 9 | Promo havuzu (15 DJ/set) | Destek cümlesi = açılma oranı | `promo_havuzu.json` + DM şablonu |
| 10 | Teslimat paketi kontrolü | Editör filtresinden geçme | `validate_project`: 3000×3000 + kredi alanı |

**30 günlük sıra:** Hafta 1 → #3 + #7 kilitle (risk kapatma). Hafta 2 → #1 + #5 (operasyon). Hafta 3 → #2 + #4 (büyüme). Hafta 4 → #6 + #9 (kaldıraç). #8 şablonları aralarda, #10 validate'e.

---

*Bu belge `SUNO_ONCESI_HAZIRLIK_DJSET.md` + `BUYUME_ONERILERI.md`'nin kardeşidir: biri NE üreteceğini, biri NASIL büyüteceğini, bu ise KİMİN standartlarında oynandığını söyler.*
