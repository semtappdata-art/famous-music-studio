# Karakter Portreleri

`karakter_roster.md`'deki 10 karakterin sabit, tanınabilir portresi buraya konur.
Bir proje `meta.json`'da `"character": "<İsim>"` alanına sahipse ve burada eşleşen
dosya varsa, `generate_cover.py` bu portreyi `cover.jpg` (üstüne başlık metni eklenmiş
hâli) ve `art.jpg` (metinsiz, kart içeriği + backdrop blur kaynağı) için otomatik
kullanır — dosya yoksa sessizce procedural gradyan/bokeh üretimine döner, hiçbir şey
bozulmaz.

**10 karakterin portresi zaten burada** — `generate_character_portraits.py` ile
üretildi: tema rengine göre radial gradyan + bokeh arka plan (generate_cover.py'nin
aynısı) üstüne düz renkli bir büst siluet + karakterin 2 harfli monogramı (ör. Kerem
Ateşi → "KA"). Bilinçli olarak bu şekilde — fotogerçekçi bir yüz üretecek bir araç bu
projede yok, ve olsa bile aşağıdaki "Görsel gereksinimleri" bölümündeki gerekçeyle
kullanılmazdı. İstersen (daha özgün/detaylı bir görsel istiyorsan) herhangi bir
karakterin dosyasını kendi hazırladığın bir görselle DOĞRUDAN değiştirebilirsin — aynı
dosya adını kullandığın sürece otomasyon fark etmez. Script'i tekrar çalıştırmak
(`python generate_character_portraits.py`) sadece EKSİK dosyaları üretir, mevcut
(senin değiştirdiğin dahil) hiçbirinin üstüne yazmaz — `--force` verirsen hepsini
yeniden üretir.

**Dosya adı kuralı:** karakter adı küçük harfe çevrilir, Türkçe karakterler ASCII'ye
çevrilir (ç→c, ğ→g, ı/İ→i, ö→o, ş→s, ü→u), boşluklar `-` olur. Uzantı `.jpg`, `.jpeg`
veya `.png` olabilir.

| Karakter | Beklenen dosya adı |
|---|---|
| ASI | `asi.jpg` |
| Nova Deniz | `nova-deniz.jpg` |
| Kerem Ateşi | `kerem-atesi.jpg` |
| Azra Yıldız | `azra-yildiz.jpg` |
| Ege Barış | `ege-baris.jpg` |
| Lina Su | `lina-su.jpg` |
| Mira Rüzgar | `mira-ruzgar.jpg` |
| Efe Sinyal | `efe-sinyal.jpg` |
| Elif Yağmur | `elif-yagmur.jpg` |
| Kaya Demir | `kaya-demir.jpg` |

## Görsel gereksinimleri (önemli — atlama)

- **Metinsiz** — `art.jpg` için kullanılıyor, üstüne isim/başlık gömülü olursa blur
  backdrop'ta okunaksız bir lekeye dönüşür (bkz. CLAUDE.md, bu hataya daha önce
  birkaç kez düşüldü).
- **Fotogerçekçi "gerçek insan" DEĞİL** — stilize/illüstratif bir portre olmalı.
  Karakterler `karakter_roster.md`'nin "Sınır ve dürüstlük notu"na göre gerçek insan
  sanatçı gibi sunulmamalı; fotogerçekçi bir yüz hem bu ilkeyle çelişir hem de
  (üretici modelin var olan gerçek bir kişiye benzeyen bir sonuç üretmesi riski
  dahil) yanıltıcı algılanma riski taşır.
- **Aynı karakter, aynı portre** — bir kere üretilip buraya konduktan sonra o
  karakterin HER şarkısında değişmeden kullanılmalı (kimlik tutarlılığı bu işin
  temeli — bkz. IngaRose vaka analizi, `karakter_roster.md`).
- **Kare/dikey oranlı, yüksek çözünürlüklü** — video kartı ve backdrop kaynağı
  olarak kullanılıyor, `config.CANVAS_SIZE` (1600x1600) civarında bir kaynak iyi
  sonuç verir.

Bu klasördeki dosyalar `.gitignore`'da DEĞİL — hazır portreler diğer görsel
varlıklar (`config.py`'deki font, vb.) gibi repoya commit edilir.
