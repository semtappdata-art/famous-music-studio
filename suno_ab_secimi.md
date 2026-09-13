# Suno A/B seçimi — indirmeden

**Kural: iki alternatiften SADECE kazanan indirilir.** Karşılaştırma tarayıcıda,
çalma akışı üzerinden yapılır ve indirme kotasından hiçbir şey düşmez.

## Neden bu dosya var

2026-09-12'de `Sabah Senin` üretilirken iki varyantı karşılaştırmak için **ikisi de
indirildi** ve kota 27'den 25'e düştü. İkinci indirme tamamen gereksizdi: kaybeden
varyant hiçbir işe yaramadı. Kullanıcı bunu fark edip yöntemi sordu; ölçüldü ve
indirmeden karşılaştırmanın mümkün olduğu doğrulandı.

**Kotanın gerçekte ne zaman düştüğü ölçüldü:** sayaç yalnızca "Unlock & Download"
tıklandığında değişiyor (27 -> 26 tam o anda). Parçayı çalmak, dinlemek, sayfada
gezmek, aynı parçayı ikinci kez indirmek (kilit bir kez açılıyor, "You've unlocked
this song, you can return and download at any time") — hiçbiri düşürmüyor.

Bu, DJ setlerinde katlanarak önemli: bir set 12-16 indirme demek
(`dj_sets/Night Drive/SUNO.md`). Orada her varyantı indirmek kotayı tek başına bitirir.

## Neden Web Audio, neden baytlar değil

Denenen ve ELENEN yollar (hepsi gerçekten denendi, tahmin değil):

| Yol | Sonuç |
|---|---|
| `curl https://cdn1.suno.ai/<id>.mp3` | **403** |
| Sayfa içinden `fetch(cdn1/cdn2/cdn-o/cdn.suno.ai)` | **CORS — "Failed to fetch"** |
| `audiopipe.suno.ai/?item_id=<id>` | **403** |
| `/api/feed/v2?ids=...` | **404** (uç nokta değişmiş) |
| `fetch(<audio>.currentSrc)` (blob: URL) | **"Failed to fetch"** — blob: URL'nin arkasında Blob değil **MediaSource** var |

Geriye tek yol kalıyor: sesi **çalarken** `AudioContext` grafiğine bağlayıp gerçek
örnekleri ölçmek. Betik `suno_ab_olcum.js` dosyasında.

Ölçüm sessiz çalışır: veri `gain` düğümünden ÖNCE alınır, gain 0'dır, yani
hoparlörden ses çıkmaz ama analizör gerçek dalga formunu görür.

## Doğrulama (bu yöntem neden güvenilir)

Aynı iki parça **iki bağımsız yolla** ölçüldü: (a) bu tarayıcı yöntemiyle,
(b) indirilmiş WAV'lardan ffmpeg + numpy ile. Sonuç:

| Ölçüt | A (tarayıcı) | A (WAV) | B (tarayıcı) | B (WAV) |
|---|---|---|---|---|
| Merkez/yan oranı | 4,79 ortanca / 10,56 tepe | 4-11 aralığı | 2,00 / 4,23 | 1,5-3,6 aralığı |
| Kapanışta düşüşün başladığı an | **269,75 sn** | **269,75 sn** | 276,0 sn | — |
| Son değer / kuyruk tepesi | 0,064 | 0,06 | 0,065 | 0,07 |
| **Kazanan** | **A** | **A** | | |

Düşüşün başladığı an **birebir aynı saniyede** çıktı ve kazanan değişmedi.

**Ama mutlak değerler ~%20 farklı** (akış kod çözümü ile WAV farkı + analizörün
pencerelemesi). Bu yüzden eşikler mutlak sayıya değil, **iki varyant arasındaki
orana** bakmalı. Bir varyantı tek başına "geçti/kaldı" diye yargılamak için bu
yöntem uygun DEĞİL.

## Ne ölçer, ne ölçmez

Ölçer — stil etiketinin **yapısal** vaatleri:

- `ilk_ses_sn` — "opens cold on the vocal, no instrumental intro" tuttu mu
- `MY_ortanca` / `MY_max` — vokal enstrümanların önünde mi (merkez/yan enerji)
- `sustain_sn` — son akor tam seviyede ne kadar durdu ("strong final hit ending")
- `son_tepe_orani` — 0,35 üstü ani kesme demek ("no abrupt cutoff" düşüyor)

**Ölçmez:** vokal tonu, sözlerin doğru söylenip söylenmediği, akort/entonasyon
hatası, ve parçanın güzel olup olmadığı. Bunlar için insan kulağı şart. Ölçüm
yalnızca yapısal vaatlerin tutup tutmadığını söyler — 2026-09-12'de sözlerin
reddedildiği turda öğrenilen ders aynen geçerli: **kural uyumu kalite değildir.**

## Akış

1. Suno'da iki varyant üret.
2. Chrome'da `suno.com/create` açıkken bir varyanta tıkla (çalmaya başlasın).
3. `suno_ab_olcum.js`'i konsola yapıştır, `kur()` çağır.
4. `await olc('A')` — ~21 sn sürer (ilk 14 sn + son 6,5 sn; tüm parçayı dinlemeye gerek yok).
5. Diğer varyanta tıkla, `await olc('B')`.
6. `karsilastir()` — özet tablo.
7. Operatöre iki varyantı da Telegram'dan gönder (MP3'e çevirmek için indirmek
   GEREKMEZ — ama gerekirse yalnızca kazanan indirilip çevrilir).
8. **Sadece kazananı indir.**

## Sınır

Bu yöntem kilitli (henüz indirilmemiş) parçalarda da çalışır, çünkü Suno kilitli
parçaları da çaldırıyor — dinlemeden satın aldırmıyor. 2026-09-12 doğrulaması
kilidi açılmış iki parça üzerinde yapıldı; çalma yolu kilit durumundan bağımsız
olduğu için sonuç taşınır, ama kilitli bir çift üzerinde henüz sınanmadı.

## 2026-09-13 — Sabah Senin yeniden üretimi (yeni sözler)

- Model v6 (Weirdness 40, Style Influence 75, Variety Normal), 1 üretim, kredisiz kampanya; indirme 25 -> 24.
- **Setinterval yöntemi gizli sekmede GEÇERSİZ çıktı** (B'de 14 sn'de 15 örnek). Ölçüm, sesin
  iş parçacığında çalışan `ScriptProcessor` toplayıcısıyla (blok ≈43 ms, gain 0) iki varyanta da
  aynı yöntemle yeniden yapıldı. Ölçmeden önce oynatma çubuğundaki clip id ve süre doğrulandı —
  bir denemede yanlış satıra tıklanıp eski clip çaldı; o çalma ölçüme girmedi.

| Ölçüt | A `49e09f77-09f6-4008-a68d-98f048b67c87` | B `7a77e7b9-410b-4c90-ac2a-d6d0fc7d9d78` |
|---|---|---|
| Süre | 166,6 sn | 193,6 sn |
| İlk ses | 0 sn | 0,17 sn |
| Merkez/yan ortanca / tepe | **4,18 / 11,74** | 3,46 / 6,37 |
| Örnek tepe / kırpılan blok | −1,9 dBFS / 0 | −1,2 dBFS / 0 |
| Sönme başı / kuyruk / son sessizlik | 164,25 / 2,39 / 0,39 sn | 191,5 / 2,10 / 0,85 sn |
| Son tepe oranı | 0,004 | 0 |

**Seçilen: A.** Vokal belirgin biçimde daha önde (ortanca +%21, tepe +%84), daha geniş tepe payı.
İkisi de kırpılmasız, doğal kapanış, hedef süre içinde. **Kulakla kontrol yapılamadı** (nakarat
okunuşu, telaffuz, son nakaratta gitar/vokal dengesi, son 5 sn) — elle dinlenmeli.
İndirilen WAV: 166,64 sn, 48 kHz, stereo, 16 bit; −15,3 LUFS, TP −4,3 dBTP, LRA 7,2 LU.
