# 🎬 Famous Music Studio — Upload SOP (Standard Operating Procedure)

Bu doküman, Instagram Reels ve TikTok upload işlemlerinin standart yolunu tanımlar.
Aynı işlem tekrarlandığında bu sırayla izlenir.

---

## 0. Ön Kontroller

```bash
cd C:/Users/ACER/Desktop/ilk-projem
```

1. `upload/instagram_token.json` — token var mı?
2. `upload/tiktok_token.json` — token var mı?
3. `upload/instagram_client_secrets.json` — app_id + app_secret var mı?
4. `upload/tiktok_client_secrets.json` — client_key + client_secret var mı?
5. `upload/netlify_client_secrets.json` — Netlify token + site_id var mı?

---

## 1. İNSTAGRAM REELS YÜKLEME

### 1.1 Token Kontrolü

```bash
python3 -c "
import json
with open('upload/instagram_token.json') as f: t=json.load(f)
print('Token:', t.get('access_token','YOK')[:20]+'...')
print('User ID:', t.get('ig_user_id'))
"
```

### 1.2 Token Yenileme (gerekirse)

```bash
python3 upload/instagram_auth.py --print-url
# → Auth URL'si açılır, Instagram'da izin verilir
# → Callback sayfasından kod kopyalanır
python3 upload/instagram_auth.py --code KOPYALANAN_KOD
```

### 1.3 Video Upload (her parça için)

```bash
python3 upload/instagram_upload.py --project "projects/{PARÇA_ADI}"
```

**Örnekler:**
```bash
python3 upload/instagram_upload.py --project "projects/Küllerimden Geç"
python3 upload/instagram_upload.py --project "projects/Sokaklar Beni Tanır"
python3 upload/instagram_upload.py --project "projects/Son Kez"
python3 upload/instagram_upload.py --project "projects/Yürek Yarası"
```

### 1.4 Upload Sonrası Kontrol

```bash
python3 -c "
import json
with open('upload/instagram_token.json') as f: t=json.load(f)
import urllib.request
url = f\"https://graph.instagram.com/v21.0/{t['ig_user_id']}?fields=id,username,media_count&access_token={t['access_token']}\"
with urllib.request.urlopen(url) as r: print(json.loads(r.read()))
"
```

Beklenen sonuç: `{'id': '28754750310777836', 'username': 'famous_music_studio', 'media_count': 32}`

---

## 2. TIKTOK YÜKLEME

### 2.1 Token Kontrolü

```bash
python3 -c "
import json
with open('upload/tiktok_token.json') as f: t=json.load(f)
print('Token:', t.get('access_token','YOK')[:20]+'...')
print('Open ID:', t.get('open_id'))
"
```

### 2.2 Token Yenileme (gerekirse)

```bash
python3 << 'EOF'
import json, requests
with open('upload/tiktok_client_secrets.json') as f: s=json.load(f)
with open('upload/tiktok_token.json') as f: t=json.load(f)
resp = requests.post('https://open.tiktokapis.com/v2/oauth/token/',
    headers={'Content-Type':'application/x-www-form-urlencoded'},
    data={'client_key':s['client_key'],'client_secret':s['client_secret'],
          'grant_type':'refresh_token','refresh_token':t['refresh_token']})
if resp.ok:
    with open('upload/tiktok_token.json','w') as f: json.dump(resp.json(),f,indent=2)
    print('Token yenilendi')
else:
    print('HATA:', resp.text[:200])
EOF
```

### 2.3 OAuth2 Auth Akışı (ilk kez veya token süresi dolduysa)

```bash
python3 upload/tiktok_auth.py --print-url
# → Auth URL'si tarayıcıda açılır
# → TikTok'ta giriş yapılıp izin verilir
# → Callback sayfasından kod kopyalanır
python3 upload/tiktok_auth.py --code KOPYALANAN_KOD
```

### 2.4 TikTok Publish Plan (zamanlı yükleme)

```bash
python3 upload/tiktok_publish_plan.py --project "projects/{PARÇA_ADI}"
```

**Örnekler:**
```bash
python3 upload/tiktok_publish_plan.py --project "projects/Küllerimden Geç"
python3 upload/tiktok_publish_plan.py --project "projects/Sokaklar Beni Tanır"
python3 upload/tiktok_publish_plan.py --project "projects/Son Kez"
python3 upload/tiktok_publish_plan.py --project "projects/Yürek Yarası"
```

### 2.5 Zamanlı Yükleme Schedule

Her proje için state.json'a `tiktok_scheduled_at` ve `tiktok_scheduled` alanları eklenir:

```python
import json, datetime

projeler = ['Küllerimden Geç', 'Sokaklar Beni Tanır', 'Son Kez', 'Yürek Yarası']
base = datetime.datetime(2026, 10, 9, 18, 0, 0)

for i, proj in enumerate(projeler):
    sp = f'projects/{proj}/state.json'
    with open(sp, encoding='utf-8') as f: st = json.load(f)
    st['tiktok_scheduled_at'] = (base + datetime.timedelta(days=i)).isoformat()
    st['tiktok_scheduled'] = True
    with open(sp, 'w', encoding='utf-8') as f: json.dump(st, f, ensure_ascii=False, indent=2)
```

---

## 3. STATE.JSON GÜNCELLEME

Her upload sonrası state.json güncellenir:

### Instagram için:
- `instagram_upload_at` — yükleme zamanı
- `instagram_media_id` — media ID
- `instagram_creation_id` — creation ID

### TikTok için:
- `tiktok_published_at` — yayın zamanı
- `tiktok_dogrulandi` — doğrulanma durumu
- `tiktok_scheduled_at` — zamanlı yükleme tarihi
- `tiktok_scheduled` — schedule durumu

---

## 4. CAPTION TEMPLATE'LERİ

### Instagram Reels:
```
{Parça Adı} #FamousMusicStudio #TurkishMusic #AIassisted #NewMusic
```

### TikTok:
```
{Parça Adı} #FamousMusicStudio #TurkishMusic #AIassisted #NewMusic
```

### YouTube Shorts:
```
{Parça Adı} #FamousMusicStudio #TurkishMusic #AIassisted
```

---

## 5. HATA OLASILIKLARI VE ÇÖZÜMLERİ

| Hata | Sebep | Çözüm |
|------|-------|-------|
| 401 Unauthorized | Token süresi doldu | refresh_token ile yenile |
| 400 Bad Request | Token geçersiz | OAuth2 auth akışını tekrarla |
| reCAPTCHA | Bot tespiti | Manuel giriş yap |
| 404 Not Found | API endpoint değişti | Güncel endpoint kontrolü |
| Scope not authorized | Yetki eksik | OAuth2 ile scope ekle |

---

## 6. TEK KOMUTLU YÜKLEME (Tüm Parçalar)

```bash
# Instagram hepsini yükle
for proj in "Küllerimden Geç" "Sokaklar Beni Tanır" "Son Kez" "Yürek Yarası"; do
    python3 upload/instagram_upload.py --project "projects/$proj"
done

# TikTok schedule güncelle
python3 << 'EOF'
import json, datetime
projeler = ['Küllerimden Geç', 'Sokaklar Beni Tanır', 'Son Kez', 'Yürek Yarası']
base = datetime.datetime(2026, 10, 9, 18, 0, 0)
for i, proj in enumerate(projeler):
    sp = f'projects/{proj}/state.json'
    with open(sp, encoding='utf-8') as f: st = json.load(f)
    st['tiktok_scheduled_at'] = (base + datetime.timedelta(days=i)).isoformat()
    st['tiktok_scheduled'] = True
    with open(sp, 'w', encoding='utf-8') as f: json.dump(st, f, ensure_ascii=False, indent=2)
EOF
```

---

## 7. DOĞRULAMA

### Instagram:
```bash
python3 -c "
import json, urllib.request
with open('upload/instagram_token.json') as f: t=json.load(f)
url = f\"https://graph.instagram.com/v21.0/{t['ig_user_id']}?fields=id,username,media_count&access_token={t['access_token']}\"
with urllib.request.urlopen(url) as r: print(json.loads(r.read()))
"
```

### TikTok:
```bash
python3 upload/tiktok_publish_plan.py --project "projects/{PARÇA_ADI}"
```

---

## 8. CONTENT ID ALLOWLIST PROSEDÜRÜ (KRİTİK — DistroKid sonrası)

YouTube Content ID, dağıtıcının (DistroKid) kaydettiği her ses dosyasını **platform genelinde** tarar. Kendi kanalınızdaki kendi videonuz bile claim yiyebilir — allowlist yoksa video engellenir/monetize olur.

### 8.1 İlk DistroKid Yayını Sonrası (Tek Seferlik)

1. **Kanal ID'sini al** (API'den — kesin):
   ```bash
   cd upload && python -c "
   from youtube_auth import get_authenticated_service
   yt = get_authenticated_service()
   print(yt.channels().list(part='id', mine=True).execute()['items'][0]['id'])
   "
   ```
   → **Bu kanalın ID'si: `UCbbcH8rtQTtz8R66jfKoSZg`**
   (ayrıca `config.YOUTUBE_KANAL_ID` altında sabit tanımlı)

2. **DistroKid'e bildir:**
   - DistroKid Dashboard → "Content ID" sekmesi → "Whitelist Channel" / "Allowlist"
   - Kanal ID'sini yapıştır → "Save"
   - **Onay e-postası/confirmation** gelene kadar bekle

3. **Mevcut videolardaki claim'leri temizlet:**
   - YouTube Studio → "Copyright" → "Content ID claims"
   - Kendi videolarınızdaki DistroKid claim'lerini seç → "Release claim" / "Dispute" → "My distributor authorized this"
   - Veya DistroKid support'a: "Please release all claims on channel UCxxxxx, we've allowlisted it"

### 8.2 Yeni Proje Yayınlanmadan Önce (Kontrol Listesi)

```bash
# 1. Kanal allowlist aktif mi?
python3 -c "
import urllib.request, json
# YouTube Data API v3 gerekli - alternatif: manuel Studio kontrolü
print('Manuel kontrol: YouTube Studio > Copyright > Filtre: Content ID > Claim yapan: DistroKid > Kanallarım')
"

# 2. Yeni video yüklemeden önce: önce 10 sn unlisted test yükle
#    - Eğer claim yersen → allowlist hâlâ işlenmemiş
#    - Claim yoksa → güvenli, public/golden-hour'da yayınla
```

### 8.3 Canlı Yayın (Live Stream) İçin Ekstra

- Canlı yayın **ayrı kural** tabi: match anında yayın kesilebilir/placeholder bastırılabilir.
- DistroKid'e **live stream allowlist** ayrı talep et (bazı dağıtıcılar bunu ayrı tutar).
- Alternatif: Canlı yayında **sadece AI üretimli kendi sesleriniz** (DistroKid'e gönderilmemiş stemler) kullanın.

---

## 9. DOĞRULAMA (Genel)

### Instagram:
```bash
python3 -c "
import json, urllib.request
with open('upload/instagram_token.json') as f: t=json.load(f)
url = f\"https://graph.instagram.com/v21.0/{t['ig_user_id']}?fields=id,username,media_count&access_token={t['access_token']}\"
with urllib.request.urlopen(url) as r: print(json.loads(r.read()))
"
```

### TikTok:
```bash
python3 upload/tiktok_publish_plan.py --project \"projects/{PARÇA_ADI}\"
```

---

**Son güncelleme:** 2026-10-19
**Test edildi:** Instagram 4/4 klip yüklendi, TikTok 4 proje schedule edildi
**Yeni:** Content ID allowlist prosedürü eklendi (DistroKid entegrasyonu için kritik)
