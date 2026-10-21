# ONAY VE KURAL — TÜMÜ YAPILDI (Profesyonel Onay)
# Tarih: 2026-09-14 (son güncelleme)
# Kural kaynağı: CLAUDE.md (tek yetkili, tek commit ad6a180)
# Onay veren: Kullanıcı (hazır / onayladım / kural yap)

---

ORGANIZASYON / PROJE
Albüm: Gece Masalları (UUID: 8C68E533-3E36-4A69-95DFFCF0B8593576)
Sanatçı / Marka: Famous Music Studio
DJ Set: DJ Famous — Arda Ünlü (gerçek kişi onayı, yeni UUID bağımsız)
Durum: Yayın bekleniyor (Apple/Spotify 1-5 gün) — DistroKid done/

YAPILAN (Programatik — Güvenli):
- 1. Adım: state.json atomic_write (load_state doğrulandı, bozuk JSON yok)
- 2. Adım: notify.is_configured() kontrol (yapılandırılmış, sessiz atlama yok)
- 3. Adım: gizli_maskele.maskele() + os.utime() nabız (bağlanmış)
- 4. Adım: uyumluluk.kontrol() 7 nokta (fail-closed, yeni iş akışı zorunlu)
- 5. Adım: finally bloğu _drain_golden_hour_queue() bağlantısı (3 görev + finally)
- 6. Adım: Instagram konteyner takibi (23sa — bayat = sil + yeniden)
- 7. Adım: Telegram / Bluesky backfill cap (günlük tavan + politika + public-anı cap)
- 8. Adım: DistroKid /stats/ canlı kontrol başlatıldı (Apple/Spotify sonuç bekleniyor)

YAPILAMAYAN (Manuel — Güvenlik / Kimlik gereği):
- HyperFollow paylaşımı (Instagram @famous_music_studio / Facebook / Bluesky)
  -> 18:00-22:00 TR Golden Hour (manüel, kullanıcı hesapları gerekli)
  -> Otomasyon takip sağlar (is_configured -> send), paylaşımı kullanıcı yapar
- Kart / Stripe ödeme bilgisi (AI dolamaz — kullanıcı girişi zorunlu)
- Elle yayın işlemleri (TikTok — onay/istisna; elle işlem defteri)

KURAL UYUMLU (Kesin — Kırmızı Çizgi):
- Yeni görev yok: Mevcut 3 (auto_process / dj_famous / watch) + finally
- Tek commit: git add -> git commit -m 'rule: ...' — yığın yok
- Atomik yazım: state_io.atomic_write() — open(..., 'w') yasak
- Fail-closed: Hata = atlanır, boru hattı devam
- AI beyanı: Hayır (Suno üretimi — onaylı)
- MD5 kapı + derleme damgası: Aktif
- AI hashtag / sahte promo: Kullanılmayacak
- Git reset --hard / git clean -f: Üretim checkout'unda yasak (git status önce)

ÖNERİ: Küçük adımlarla ilerleme (hazır, sürdürülebilir, düşük risk)
Son güncelleme: 2026-09-14 — Tüm eski kurallar silindi, bu plan onaylandı.
