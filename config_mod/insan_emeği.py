# --- İNSAN EMEĞİ GÖNDERİLERİ (turev_takvimi.py kanal kayıtları; TikTok LIVE planı,
# kullanıcı kararı 2026-09-13) ---
# "Söz Defteri" / "Kulis": projeye bağlı olmayan, elle çekilen TikTok gönderileri.
# Şarkı kesiti tavanlarına (TIKTOK_KIT_*, TUREV_GUNLUK_TAVAN) SAYILMAZ; kendi tavanı bu.
TUREV_INSAN_EMEGI_HAFTALIK_TAVAN = 2      # TR takvim haftası (Pzt-Paz) başına
TUREV_INSAN_EMEGI_KAYMA_GUN = 2           # çakışmada hedef günden en fazla N gün ileri (aynı hafta)
TUREV_KANAL_TAKVIMI = "kanal_takvimi.json"  # repo kökü; kanal geneli kayıt yeri
# YouTube Topluluk sürümü (soz_defteri_topluluk / kulis_topluluk): bağlı TikTok kaydının
# ÇÖZÜLMÜŞ anından en az bu kadar saat sonra; tavan dışı, elle (Topluluk API'si yok).
TUREV_TOPLULUK_TIKTOK_SONRASI_SAAT = 24
