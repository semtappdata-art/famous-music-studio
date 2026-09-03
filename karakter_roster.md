# Karakter Roster'ı — Günlük Ekstra (+1) Şarkı İçin

**Amaç:** Mevcut günlük üretim akışına DOKUNMADAN, buna ek olarak günde 1 şarkı, aşağıdaki
10 karakterden birine atanarak üretiliyor. Karakterin sabit vokal kimliği (cinsiyet + doku +
tarz) o karaktere ait HER şarkıda korunur — böylece tek seferlik rastgele vokal yerine,
zamanla tanınabilir bir "sanal sanatçı" kimliği oluşur (bkz. "Neden bu işe yarıyor" bölümü).

**Bu, koddan (auto_process.py) bağımsız, elle takip edilen bir içerik/prodüksiyon sürecidir**
— otomasyon hâlâ sadece `audio.wav` geldikten sonra devreye giriyor, hangi karakterle
üretileceğini otomasyon bilmiyor/seçmiyor. Suno'da şarkı üretirken bu dosyadan karakteri
seç, stil etiketine karakterin vokal tanımını ekle.

## Neden bu işe yarıyor (araştırma kanıtı)

**IngaRose** — Suno ile üretilmiş, kadın R&B/soul karakteri olarak sunulan bir "sanal
sanatçı". "Celebrate Me" şarkısı TikTok'ta viral olup ABD/İngiltere/Fransa/Kanada/Yeni
Zelanda iTunes listelerinde 1 numaraya çıktı, 300.000+ TikTok video kullanımı, ~1 milyon
aylık Spotify dinleyicisi topladı. Instagram bio'sunda AÇIKÇA "İnsan yazımı sözler, Suno ile
işlendi" yazıyor — yani gizleme yok, şeffaf AI-karakter markalaması, ve bu ŞEFFAFLIĞA rağmen
(belki de sayesinde) viral oldu. Aynı yaratıcının "Eddie Dalton" adlı başka bir erkek AI
karakteri de listelere girdi. **Sonuç: tutarlı, isimli bir "sanal sanatçı" kimliği, anonim
tek-seferlik şarkılardan daha güçlü bir büyüme motoru olabilir — ve bunu gizlemeden yapmak
(AI olduğunu açıkça belirtmek) başarıyı engellemiyor.**

Türkiye tarafında (`turkiye_muzik_trend_arastirmasi.md` ile tutarlı, daha ayrıntılı):
rap/trap'te sert/agresif erkek vokal tarzları güçlü dinlenme alıyor; melodik, duygusal
koroları olan pop-rap/arabesk-pop melezi erkek sesler hem rap hem pop dinleyicisinde karşılık
buluyor; kadın tarafta R&B/pop/Türkçe rap arasında geçiş yapabilen çok yönlü vokaller öne
çıkıyor.

## 10 Karakter

Her karakter: **[İsim] — [cinsiyet] — [ana tema] — [Suno vokal tanımı, doğrudan style
etiketine eklenebilir] — [ilham kaynağı, taklit değil trend referansı]**

Her karakterin ayrıca sabit bir portresi var (bkz. "Portre görselleri" bölümü) —
parantez içindeki dosya adı `characters/` klasöründe aranan dosya.

1. **ASI** (`characters/asi.jpg`) — erkek — `hiphop` — *"aggressive gritty male rap
   vocals, deep bass-heavy delivery, raw street energy"* — Türkçe trap'te öne çıkan
   sert/agresif erkek vokal trendinden ilhamla (bkz. araştırma notu, isim/kimlik
   taklidi yok).
2. **Nova Deniz** (`characters/nova-deniz.jpg`) — kadın — `hiphop`/`pop` geçişli —
   *"versatile female vocals, confident rap-pop crossover delivery, melodic hooks
   with edge"* — rap/pop/R&B arası geçiş yapabilen çok yönlü kadın vokal trendinden
   ilhamla.
3. **Kerem Ateşi** (`characters/kerem-atesi.jpg`) — erkek — `arabesk` — *"warm raspy
   male vocals, melodic emotional delivery, memorable chorus hooks, pop-rap-arabesk
   fusion energy"* — melodik/duygusal, hem rap hem pop dinleyicisine hitap eden
   arabesk-pop melezi trendinden ilhamla (Son Kez'in "warm raspy male vocals"
   yönüyle de tutarlı).
4. **Azra Yıldız** (`characters/azra-yildiz.jpg`) — kadın — `arabesk` — *"powerful
   emotional female vocals, belting arabesk-pop delivery, dramatic dynamic range"*
   — güçlü, duygusal arabesk-pop kadın vokal trendinden ilhamla.
5. **Ege Barış** (`characters/ege-baris.jpg`) — erkek — `pop` — *"warm smooth male
   vocals, radio-friendly pop delivery, easy melodic hooks"* — geniş tabanlı Türkçe
   pop dinleyicisine hitap eden, erişilebilir erkek vokal.
6. **Lina Su** (`characters/lina-su.jpg`) — kadın — `pop` — *"bright breathy female
   vocals, catchy pop delivery, youthful energetic tone"* — geniş tabanlı pop
   dinleyicisine hitap eden kadın vokal.
7. **Mira Rüzgar** (`characters/mira-ruzgar.jpg`) — kadın — `pop`/`hiphop` geçişli —
   *"smoky soulful female vocals, R&B-inflected pop delivery, intimate emotional
   tone"* — IngaRose'un uluslararası doğrulanmış R&B/soul karakter formülünden
   ilhamla (taklit değil, kanıtlanmış bir kalıbın Türkçe'ye uyarlanması).
8. **Efe Sinyal** (`characters/efe-sinyal.jpg`) — erkek — `elektronik` — *"processed
   energetic male vocals, synth-driven delivery, modern electronic pop energy"*
9. **Elif Yağmur** (`characters/elif-yagmur.jpg`) — kadın — `akustik` — *"soft
   intimate female vocals, breathy acoustic delivery, gentle fingerstyle-friendly
   tone"* — Son Kez'in akustik yönünün kadın karşılığı.
10. **Kaya Demir** (`characters/kaya-demir.jpg`) — erkek — `rock` — *"powerful gritty
    male rock vocals, raw energetic delivery"* — kataloğun hâlâ hiç kullanılmamış
    `rock` slotunu dolduran karakter (bkz. `ses_ve_tarz_takibi.md`, müzik
    prodüksiyon ajanı denetimi) — düşük veri desteğine rağmen
    (`turkiye_muzik_trend_arastirmasi.md`) katalog çeşitliliği için tutuldu.

## Portre görselleri

Her karakterin `characters/` klasöründe sabit, tekrar kullanılan bir portresi VAR
(dosya adları yukarıda, `generate_character_portraits.py` ile üretildi — büst siluet +
2 harfli monogram, kural detayı `characters/README.md`'de). Bu portreler otomasyona
bağlı — `generate_cover.py`, `meta.json`'da `"character"` alanı eşleşen bir portre
bulursa onu `cover.jpg`/`art.jpg` için otomatik kullanır (yoksa sessizce procedural
gradyana döner, hiçbir şey bozulmaz). Portreler:

- **Metinsiz** olmalı (art.jpg kuralı — blur backdrop kaynağı da bu görsel).
- **Fotogerçekçi "gerçek insan" olmamalı** — stilize/illüstratif, aşağıdaki "Sınır ve
  dürüstlük notu"yla tutarlı olmalı.
- Bir kere üretilip o karakterin HER şarkısında AYNI kalmalı.

**Cinsiyet dağılımı:** 5 erkek (ASI, Kerem Ateşi, Ege Barış, Efe Sinyal, Kaya Demir), 5 kadın
(Nova Deniz, Azra Yıldız, Lina Su, Mira Rüzgar, Elif Yağmur) — dengeli.

**Tema ağırlığı:** rap/trap ve arabesk-pop'a (araştırmada en güçlü sinyal) 2'şer karakter,
pop'a 2 + 1 geçişli, elektronik/akustik/rock'a 1'er — `turkiye_muzik_trend_arastirmasi.md`'nin
önceliklendirmesiyle tutarlı.

## Kullanım

1. Günlük ekstra (+1) şarkı için bu listeden bir karakter seç (rotasyon önerilir — aynı
   karakter art arda günlerde kullanılmasın, `ses_ve_tarz_takibi.md`'deki "tekrar etmesin"
   mantığıyla aynı).
2. Karakterin vokal tanımını doğrudan Suno stil etiketine ekle (tema/tempo/enstrümantasyon
   ile birlikte, `suno_prompt_hazirlik.md`'deki şablona göre).
3. `meta.json`'da `theme` alanını karakterin ana temasına göre ayarla.
4. `meta.json`'a `"character": "Kerem Ateşi"` gibi bir alan ekle — bu artık SADECE kayıt
   amaçlı değil: `generate_cover.py` bu alanı okuyup `characters/` klasöründe eşleşen bir
   portre varsa (bkz. "Portre görselleri") onu `cover.jpg`/`art.jpg` için otomatik
   kullanıyor. Portre henüz hazırlanmadıysa alan yine de zararsız — otomasyon sessizce
   procedural gradyana düşer, hiçbir şey bozulmaz. `cover.jpg`/`art.jpg`'yi zaten elle
   koyduysan (karakter portresinden bağımsız, tek seferlik özel bir görsel istiyorsan)
   o da her zaman önceliklidir, karakter portresi sadece boşluğu doldurur.

## Sınır ve dürüstlük notu

IngaRose örneği şeffaflığın (AI olduğunu gizlememenin) başarıyı engellemediğini gösteriyor
— bu kanalın zaten `containsSyntheticMedia`/AI-içerik açıklaması politikası (bkz. CLAUDE.md)
ile uyumlu. Karakterler "gerçek insan sanatçı" gibi SUNULMAMALI — IngaRose'un yaptığı gibi
AI kaynaklı olduğu açık kalmalı, sadece isimli/tutarlı bir kimlik taşımalı.

## Kaynaklar

- https://en.wikipedia.org/wiki/IngaRose
- https://www.forbes.com/sites/conormurray/2026/04/17/the-no-1-song-on-us-itunes-and-several-other-countries-is-ai-generated/
- https://www.techloy.com/10-ai-music-acts-that-have-officially-topped-the-global-charts/
- https://gazetemerhaba.com/kultur-ve-sanat/2025in-en-cok-dinlenen-sarkicilari-aciklandi-turkiye-rape-teslim-oldu-ilk-7-listesi-106088
- https://aiunfiltered.beehiiv.com/p/complete-list-of-prompts-styles-for-suno-ai-music-2026
