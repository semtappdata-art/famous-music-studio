# --- ÖZGÜN METİN (§2c/§2e, kararlar 2-3) — okuyan: ozgun_metin.py
# Hikâye paragrafı (`meta.hikaye`, 2-4 cümle) + "neden bu şarkı" (`meta.neden_bu_sarki`, 1
# cümle): bu tarihten önce eksikse UYARI, bu tarihten itibaren yeni şarkıda HATA (yayın durur).
HIKAYE_KAPISI_TARIHI = "2026-09-21"
# YouTube başlık kalıbı rotasyonu: yalnız YENİ yüklemede seçilir (state `youtube_baslik_kalibi`),
# ardışık iki yeni yayında aynı kalıp yok, "Sözleri" hepsinde; eski videolar K1'de kalır.
YOUTUBE_BASLIK_ROTASYONU_AKTIF = True
YOUTUBE_BASLIK_KALIPLARI = (
    {"id": "K1", "sablon": "{title} (Sözleri) | Türkçe {tur} Şarkısı"},
    {"id": "K2", "sablon": "{title} — Sözleri | Famous Music Studio"},
    # K3 yalnız meta.json'da `baslik_eki` (şarkıya özgü 2-4 kelime) varsa aday.
    {"id": "K3", "sablon": "{title} (Sözleri) · {baslik_eki}", "gerekli": "baslik_eki"},
)
