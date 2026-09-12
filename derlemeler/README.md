# Derlemeler — yayınlanmış şarkılardan uzun format

`derleme.py` üretiyor. Suno kotasına **hiç dokunmuyor**: malzeme zaten üretilmiş
ve yayınlanmış şarkılar.

## Neden var

1. **Kota.** Suno indirme sınırı projenin gerçek tavanı; katalog ve DJ setleri
   aynı kotadan besleniyor. Derleme, kota harcamadan uzun format üreten tek yol.
2. **İzlenme süresi.** Kanalın kendi ölçümü: video başına 85 dk (şarkı) /
   689 dk (DJ seti). Derleme şarkı hattını uzun format tarafına taşıyor.
3. **Asıl sebep — "inauthentic content".** YouTube 15 Temmuz 2025'te politikayı
   yeniden adlandırdı: toplu üretilmiş, jenerik, küratörlük eklenmemiş AI
   içeriği para kazanmaya uygun değil, yaptırım kanal kapatmaya kadar gidiyor.
   Günde 2 şarkı × 6 tarz bu tanıma en çok benzeyen desen. Derleme seçim,
   sıralama ve bölüm damgalarıyla küratörlük katmanı ekliyor.

## Kullanım

```bash
python derleme.py --ad "Arabesk Gece" --tema arabesk --dry-run
python derleme.py --ad "En Çok Dinlenenler" --en-iyi --hedef-dk 40
python dj_famous_process.py --base derlemeler      # render + yayın (ilk yayın elle; bkz. Zamanlama)
```

`dj_famous_process` `--base` aldığı için ayrı bir işleyici gerekmedi. Derleme
DJ setiyle aynı hattan geçiyor: **Content ID karantinası** → YouTube → Shorts →
TikTok → Instagram → Facebook/Telegram/Bluesky.

## Kurallar

- **Sadece yayında olan şarkılar.** Liste dışı/gizli olanlar atlanıyor.
- **Telif işareti olan şarkılar hiç girmiyor.** Kapı `telif_araliklari`'na
  DA `telif_eser`'e DE bakıyor (`derleme.TELIF_ISARETLERI`) — ikisi de elle
  yazılıyor, biri tek başına da yazılabilir. Derleme yeniden yayın
  demek; telifli malzemeyi ikinci kez yayınlamak City Pulse'ta yaşananı
  tekrarlamak olur.
  **Bu garantiyi doğrulayan test: `tests/test_derleme_telif_kapisi.py`**
  (alanın hangi biçiminin kapıyı kapattığı da orada çivili: boş liste ve
  `null` işaret sayılmaz, bozuk tip sayılır).
- **Sıralama izlenmeye göre, en çok izlenen başta.** İlk 30 saniye izleyiciyi
  tutar ya da kaybeder.
- **Kapak mozaik olmalı**, stok fotoğraf değil — parçaların kendi kapaklarından.
  Stok görsel hem içerikle ilgisiz hem de kanalın en büyük riskiyle (jenerik
  görünmek) aynı yönde.
- **Bölüm damgaları** YouTube açıklamasına chapter olarak basılıyor
  (`meta.json` → `derleme_liste`). Hem gezinme hem küratörlük sinyali.

## Zamanlama — ÜRETİM elle, YAYIN tarafı otomatik de tetikleniyor

Derleme hattının Görev Zamanlayıcı'da **kendi görevi YOK** ve olmayacak. Ama bu
"hiçbir şey kendiliğinden çalışmıyor" demek DEĞİL — iki yarı ayrı davranıyor:

- **Üretim (`derleme.py`) gerçekten ELLE.** Depoda hiçbir yerden çağrılmıyor;
  `derlemeler/` altında bir derleme klasörü ancak operatör komut verince oluşur.
- **Yayın (`dj_famous_process.py --base derlemeler`) OTOMATİK de tetikleniyor.**
  Zincir (2026-09-12'de kod okunarak doğrulandı): `auto_process.py` (SAATLİK
  Görev Zamanlayıcı görevi) → `main()`'in `finally` bloğundaki `_dj_tarama()` →
  `dj_tarama_kontrol.kontrol_et()` → `_kalan_platformlari_isle()` →
  `subprocess.run([..., "dj_famous_process.py", "--base", "derlemeler"])`.
  Kapı `dj_tarama_kontrol.BASELER`'in `derlemeler/`i de içermesinden geliyor
  (Content ID karantinası bilerek her iki kök için de çalışıyor) ve
  `config.DJ_ON_TARAMA` ile açılıp kapanıyor. Log satırı:
  *"DJ tarama: derlemeler icin kalan platformlar tetiklendi"*.

**Tetikleyicinin koşulu ve GERÇEK kapsamı** — ikisi aynı şey değil:

- **Koşul:** `derlemeler/` altında `state.json`'ında `dj_kalan_bekliyor: true`
  olan bir proje bulunması. Yani karantinası temiz çıkmış, YouTube'da public
  yapılmış ama Shorts/TikTok/Instagram/... henüz gönderilmemiş bir derleme.
  Tek başına duran yeni bir klasör bu bayrağa sahip olmadığı için alt süreci
  KENDİ BAŞINA başlatmaz.
- **Kapsam:** ama alt süreç başladığında yalnızca o projeyi işlemiyor.
  `find_pending_sets()` `derlemeler/` altındaki TÜM klasörleri tarıyor (`.` ile
  başlayanlar ve `meta.json`'ı olmayanlar hariç) ve
  `islenecek = bekleyenler + yeniler[:limit]` diyor — tetikleyici `--limit`
  geçmediği için varsayılan **1**, yani sıradaki YENİ klasör de render edilip
  yayınlanıyor.

**Sonuç: `derlemeler/` altına bırakılmış yeni bir klasör, operatör hiçbir yayın
komutu vermeden yayınlanabilir** — kuyrukta kalan platformlarını bekleyen başka
bir derleme varsa, bir sonraki saatlik koşuda. "Henüz yayınlanmasın" denen bir
derleme bu yüzden `derlemeler/` altında BEKLETİLMEZ: tarama iç içe klasörlere
inmediği için `derlemeler/_iptal/<ad>` hattın dışında kalır (`.` ile başlayan
adlar da atlanıyor — `derleme.py`'nin ürettiği `.tmp-<ad>` bu yüzden görünmez).
Aynı sebeple testler de gerçek `derlemeler/`e yazmamalı: `tests/conftest.py`
`derleme.HEDEF_KOK`'ü geçici klasöre çekiyor, kanıtı
`tests/test_conftest_hedef_kok.py`.

## Frekans — bilerek SEYREK

Sebep yukarıdaki 3. maddenin doğrudan devamı: derleme "inauthentic content"e
karşı bir **küratörlük** hamlesi, bir üretim hattı değil. Kendi haftalık
tetikleyicisine bağlanırsa kendisi o maddenin tarifine girer — "toplu
üretilmiş, tekrarlayıcı içerikle doldurma". Frekans kuralı:

- **Ayda en fazla bir derleme.**
- **Her biri farklı bir konseptle** (tema, dönem, "en çok dinlenenler" gibi) —
  aynı havuzdan aynı mantıkla üretilen ikinci bir derleme, birincinin
  tekrarıdır.
