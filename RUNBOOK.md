# Famous Music Studio - Runbook

## Acil Durum Prosedürleri

### 1. Kanal Durduruldu
- Kontrol et: auto_process.log son 1 saat
- Kontrol et: Görev Zamanlayıcı görevleri aktif mi
- Kontrol et: API anahtarları geçerli mi
- Eylem: restart veya manuel müdahale

### 2. YouTube Kota Tükendi
- Kontrol et: youtube_kota.py ozet
- Bekle: kota sıfırlanana kadar (geçen gün)
- Eylem: kritik yüklemeleri manuel yap

### 3. Instagram Token Doldu
- Kontrol et: netlify_kontrol.py
- Eylem: Instagram Auth'dan yenile
- Bildir: operatöre

### 4. TikTok Taslak Bulunamadı
- Kontrol et: tiktok_upload.py log
- Eylem: manual upload
- Bildir: operatöre

### 5. Suno API Hatası
- Kontrol et: suno_api.py durum
- Eylem: fallback state dosyası kullan
- Bildir: operatöre

### 6. Disk Doldu
- Kontrol et: df -h
- Eylem: eski logları sil, backup al
- Bildir: operatöre

### 7. Ağ Kesintisi
- Kontrol et: failover.py durum
- Eylem: 4G modem'e geç
- Bildir: operatöre

### 8. Backup Başarısız
- Kontrol et: backup.py kontrol
- Eylem: manuel backup al
- Bildir: operatöre

## Günlük Kontroller
- [ ] auto_process.log son durum
- [ ] YouTube kota durumu
- [ ] Instagram token süresi
- [ ] TikTok taslak durumu
- [ ] Backup durumu
- [ ] Sentry hata logu

## Haftalık Kontroller
- [ ] Tüm API anahtarları geçerli
- [ ] Test suite çalışır
- [ ] Docker container sağlıklı
- [ ] Monitoring dashboard çalışır
- [ ] Backup restore testi

## Aylık Kontüller
- [ ] Security audit taraması
- [ ] API key rotation
- [ ] License yenileme
- [ ] Performance review
- [ ] Disaster recovery testi
