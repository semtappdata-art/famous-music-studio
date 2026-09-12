# Ses ve Tarz Çeşitliliği Takibi

**SON DURUM (2026-09-11) — son 3 üretimin üçü de ERKEK vokal** (Sokaklar Beni Tanır:
tekli erkek → Kader Ortakları: E+E düet → Bu Gece Kazandık: E+E düet). Son kadın vokal
5 Eylül'deki **Kumdan Denize**. **Sıradaki şarkı: KADIN vokal, düet DEĞİL.** Tempo da
kümelendi: son dört ölçülebilir üretim 90/92/118/122 BPM; 76-80 BPM (yavaş) aralığı
Sessiz Mektup'tan (76) beri hiç kullanılmadı.

Yeni bir şarkı prompt'u (Suno Style etiketi) yazmadan önce bu listeye bak —
aynı vokal cinsiyetini/dokusunu art arda tekrarlamamak için. (Kalbim Oynuyor,
Sabaha Kadar ve Son Kez'in ilk hâli hep "female vocals" kullanmıştı, fark
edilmeden — bu dosya o hatayı tekrarlamamak için tutuluyor.)

**Kapsam ve kaynaklar (tahmin YOK, hepsi diskten doğrulandı — 2026-09-11):** tablo ana
katalog (`projects/`) içindir; DJ setleri (`dj_sets/`) ve derlemeler (`derlemeler/`)
kendi hatlarında izleniyor. Tema `projects/<isim>/meta.json`'daki `"theme"` alanından;
**vokal ve BPM `<slug>_sozler.md`'nin `## Stil Etiketi` bloğundaki Suno etiketinden**
(`meta.json`'da vokal ya da BPM alanı YOKTUR — tek gerçek kaynak stil etiketidir);
düetin tarafları aynı dosyanın `[Verse - Kadın]`/`[Verse - Baba]` gibi bölüm
etiketlerinden. Sıralama üretim (Suno kaydının oluşma) sırasıdır, yayın sırası değil —
`projects/*/audio.*` dosyalarının tarihinden ve sözler dosyalarındaki Suno şarkı
sayfası tarihlerinden çıkarıldı; 5 Eylül'deki toplu YouTube yüklemesi üretim sırasını
YANSITMIYOR.

| Şarkı | Tema | BPM | Vokal |
|---|---|---|---|
| Beni Bırakma | hiphop | (kayıt yok) | (kayıt yok — stil etiketi arşivlenmedi) |
| Gece Sürüşü *(eski adı: Shudhniy L)* | pop | (kayıt yok) | (kayıt yok — stil etiketi arşivlenmedi) |
| Yeniden Doğacağım | arabesk | (kayıt yok) | (kayıt yok — stil etiketi arşivlenmedi; düet tarafları da kayıtlı değil) |
| Kalbim Oynuyor | pop | 124 | female vocals |
| Sabaha Kadar | elektronik | 122 | female vocals |
| Son Kez | akustik | 92 | warm raspy male vocals |
| Beton Krallığı | hiphop | 138 | aggressive gritty male rap vocals (ASI karakterinin SABİT kimliği — dönüşüm kuralından muaf) |
| Yürek Yarası | arabesk | 78 | **düet: kadın-erkek** — powerful belting female + warm raspy male |
| Bir Bahar Daha | pop | 104 | warm smooth male vocals |
| Neon Kalp **(üretilmedi)** | elektronik | 124 | bright breathy female vocals |
| Kırık Zincir | rock | 132 | powerful gritty male vocals |
| Sessiz Mektup | akustik | 76 | soft breathy female vocals |
| Yeraltı | hiphop | 92 | husky nasal male vocals (melodik + agresif hibrit) |
| Sofraya Gelmedin | arabesk | (yok) | **düet: baba-oğul** — gravelly weary older-male + husky vulnerable younger-male |
| Kumdan Denize | elektronik (Afro-House/Arabic EDM) | 122 | polished female lead vocal (confident, intimate) |
| Sokaklar Beni Tanır | hiphop | (yok) | deep world-weary male vocals |
| Küllerimden Geç *(yeni kayıt değil)* | arabesk | (kayıt yok) | (kayıt yok — "Yeniden Doğacağım"ın sesi yeniden markalandı) |
| Kader Ortakları | hiphop (Pop-Hip-Hop, arabesk-vokal etkili) | 90 | **düet: erkek-erkek** — Male 1: warm smooth melancholic tenor, Male 2: raspy gritty passionate baritone |
| Bu Gece Kazandık | pop (dance-arabesk-pop) | 118 | **düet: erkek-erkek** — Male 1: tender warm melismatic tenor (vibrato), Male 2: bright energetic nasal-edged voice |

**Sütun işaretleri:** `(yok)` = stil etiketi VAR ama içinde BPM yazmıyor.
`(kayıt yok)` = şarkının hiç arşivlenmiş stil etiketi yok (ilk üç şarkı +
Küllerimden Geç; bkz. CLAUDE.md "Açık/bilinen boşluklar").
`(üretilmedi)` = satır bir FİKİR olarak duruyor, diskte karşılığı yok.

## Satır notları (2026-09-11 doğrulaması)

- **Gece Sürüşü = eski "Shudhniy L"** — bu satır hayalet DEĞİL, yeniden adlandırma.
  Kanıt: eski `projects/ilk-sarkim` kaydının (`meta.json` başlığı "Shudhniy L")
  `state.json`'ındaki `youtube_video_id` `7gyLv84KxTk` ve `tiktok_publish_id`
  `v_inbox_file~v2.7680640761771296784`, bugünkü `projects/Gece Sürüşü/state.json`
  ile BİREBİR aynı; tema ikisinde de `pop`. (Eski kayıt `.claude/worktrees/*`
  altındaki dallarda duruyor.) Aynı dönemde `projects/beni bırakma` →
  `Beni Bırakma` ve `projects/ilk otomasyon` → `Yeniden Doğacağım` yeniden
  adlandırmaları da yapıldı. Tabloda "Gece Sürüşü" satırının eksik görünmesinin
  sebebi buydu.
- **Neon Kalp üretilmedi** — `neon_kalp_sozler.md` (sözler + stil etiketi) yazılmış
  ama diskte proje klasörü yok, `state.json` yok, hiçbir platforma çıkmamış. Eski
  dallarda sadece `meta.json`'ı olan boş bir klasör var (ses dosyası bile yok).
  Satır SİLİNMEDİ: fikrin düşünülüp bırakıldığı bilgisi kayıtta kalsın diye — ama
  vokal dönüşüm zincirini sayarken **sayılmamalı** (Bir Bahar Daha → Kırık Zincir
  aslında erkek→erkek'tir; `kirik_zincir_sozler.md`'deki "Neon Kalp'in (kadın)
  ardından erkeğe dönüldü" notu bu yüzden gerçeği yansıtmıyor).
- **Yürek Yarası düzeltildi** — tabloda "female vocals" yazıyordu; stil etiketi
  aslında `powerful belting female vocals alternating with warm raspy male vocals`
  ve sözler dosyasında `[Intro - Female]`/`[Intro - Male]` bölümleri var, yani
  kadın-erkek DÜET. Arabesk düet kuralının İLK örneği bu şarkı.
- **Sofraya Gelmedin** tabloda hiç yoktu — arabesk düet kuralının İKİNCİ örneği
  (baba-oğul) ve CLAUDE.md ona atıf yapıyor. Suno kaydı 5 Eylül 2026 00:58,
  Kumdan Denize'den hemen önce üretilmiş.
- **Beton Krallığı** tabloda hiç yoktu. Vokali `karakter_roster.md`'deki ASI
  karakterinin sabit kimliği olduğu için dönüşüm kuralına girdi sayılmaz, ama
  tempo/tema kümelenmesinde sayılır (kataloğun en hızlısı: 138 BPM).
- **Küllerimden Geç** yeni bir kayıt değil (`Yeniden Doğacağım` ile aynı ses),
  YouTube'da bilerek `unlisted`. Vokal çeşitliliği sayımına DAHİL EDİLMEMELİ.

## Yeni şarkı eklerken

1. Yukarıdaki "SON DURUM" satırını oku — tabloyu taramadan yönü gösterir.
2. Tabloya bir satır ekle: Şarkı | Tema | BPM | Vokal. BPM'i stil etiketine
   YAZ (son iki şarkıda unutuldu, tempo kümelenmesi ölçülemez oldu).
3. Son 2-3 şarkıdan farklı bir vokal cinsiyeti/dokusu seç (mümkünse erkek/kadın
   dönüşümlü, ayrıca "warm", "raspy", "breathy", "powerful", "soft" gibi doku
   sıfatlarını da değiştir — sadece cinsiyet değil, karakter de tekrar etmesin).
4. `arabesk` şarkılarda düet ZORUNLU ama kombinasyon serbest (CLAUDE.md) —
   tarafları (kadın-erkek / baba-oğul / erkek-erkek ...) Vokal sütununa YAZ ki
   hangi kombinasyonların tüketildiği görülsün.
5. **"SON DURUM" satırını da güncelle.** Tablo güncellenip bu satır unutulursa
   kural yine yanlış geçmişe bakar.

> **Bu dosya ELLE tutuluyor ve 2026-09-11'de üç şarkıda (Beton Krallığı, Gece
> Sürüşü/Shudhniy L, Sofraya Gelmedin) güncellenmediği tespit edildi.** Otomatik
> bir tutarlılık uyarısı HENÜZ YOK — öneri rapor edildi, koda eklenmedi. Bunu
> okuyan kişi/ajan: tabloyu `ls projects/` çıktısıyla karşılaştırmadan tam
> güvenme.
