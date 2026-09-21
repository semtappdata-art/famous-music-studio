# Yorum yanıt rehberi (TikTok, elle)

Bu kalıplar **otomatik gönderilmez**. Hermes, bot ya da zamanlanmış yanıt yok (TikTok Hizmet
Şartları md. 5; `reference_olcum_yorum_api.md`). Her yanıtı **sen**, telefondan yazarsın.

## İlk 2 saat kuralı

1. Gönderi yayınlandıktan sonraki **ilk 2 saat** içinde her yoruma yanıt ver. TikTok dağıtımı en
   çok bu pencerede ölçülüyor ve bugünkü yorum oranı ≈ %0,03. Tek bir sohbet bile fark yaratır.
2. İlk 30 dakikada uygulamayı açık tut. Sonra 30 dakikada bir bak.
3. **Aynı cümleyi iki kişiye yazma.** Kalıbı başlangıç noktası olarak al, yorumdaki bir kelimeyi
   yanıtına mutlaka geri koy (kişinin adı, sorduğu şey, sevdiği satır).
4. Yanıt kısa olsun (1–2 cümle) ve mümkünse **soruyla bitsin**. Sohbet uzarsa dağıtım artar.
5. İyi bir soru gelirse "videoyla yanıtla" düğmesiyle cevap ver. Bu, bir sonraki Söz Defteri
   gönderisi olabilir.
6. **Yapma:** "takip et, geri takip ederim", "hediye at", link, telefon numarası, üretim aracının adı.
   "Nasıl yapıyorsunuz?" sorusuna dürüst ve kısa yanıt ver (kalıp 7).
7. Küfür, taciz ya da spam varsa yanıt verme; gizle ya da bildir. Tartışmaya girme.
8. Günün sonunda: `python elle_islem.py ekle --platform tiktok --islem yorum_yaniti --ayrinti "<gönderi>: N yanıt"`.

## 10 kalıp (kişiselleştir, olduğu gibi yapıştırma)

| # | Durum | Kalıp | Nereyi değiştir |
|---|---|---|---|
| 1 | "Çok güzel" gibi kısa övgü | "Sağ ol **[ad]**! Hangi satırda durdun, merak ettim." | adı ve "satır" yerine videodaki öğeyi (nakarat, kapak) yaz |
| 2 | Belirli bir dizeyi alıntılamış | "**'[alıntı]'** benim de en sevdiğim yer. O satır üç kez değişti aslında 🙂" | kaç kez değiştiğini gerçek sayıyla yaz |
| 3 | "Eski daha iyiydi" | "Haklı olabilirsin, eski hâlinin bir sıcaklığı vardı. Sence hangi kelimesi kalmalıydı?" | yorumun gerekçesine değin |
| 4 | "Yeni daha iyi" | "Bunu duymak iyi geldi. Kısaltınca nefes aldı gibi oldu, değil mi?" | hangi değişikliği sevdiğini sorabilirsin |
| 5 | "Şarkı ne zaman çıkıyor?" | "Üzerinde çalışıyoruz, çıkınca profilde ilk o olacak. Beklediğin için teşekkürler **[ad]**!" | tarih kesinse söyle, kesin değilse söz verme |
| 6 | Kendi söz önerisini yazmış | "Bu fena değil! **'[öneri]'** ritme oturur mu diye bir deneyeyim, sonra söylerim." | gerçekten deneyeceksen yaz |
| 7 | "Yapay zeka mı? / Nasıl yapıyorsunuz?" | "Sözleri biz yazıp seçiyoruz, müzik ve vokal AI destekli. Hangi kısmını merak ettin?" | araç adı YOK; soruya göre kısalt |
| 8 | Duygusal bir hikâye paylaşmış | "Bunu paylaştığın için sağ ol. Şarkı tam da böyle bir sabah için yazıldı." | kişinin anlattığı ana dokun; soru sorma, sadece dinle |
| 9 | Başka bir şarkımızı sormuş | "**[şarkı]** profilde duruyor 🎧 Hangisini daha çok dinliyorsun?" | link verme, "profilde" de |
| 10 | Emoji ya da tek kelime | "🙌 Bu akşam neyle dinliyorsun, kulaklık mı hoparlör mü?" | saate göre değiştir (sabah/gece) |

**Ton kontrolü:** yanıtı göndermeden önce sesli oku. Bir arkadaşına yazar gibi değilse kısalt.
