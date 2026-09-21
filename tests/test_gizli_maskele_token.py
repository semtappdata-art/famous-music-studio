# -*- coding: utf-8 -*-
r"""gizli_maskele — ÇIPLAK `token` anahtarı ve Netlify token'ı (B5, 2026-09-11).

NEDEN AYRI DOSYA: `tests/test_gizli_maskele.py` maskeleyicinin doğduğu olayı
(Instagram `access_token` sızıntısı) çiviliyor; burası o denetimde bulunan
BOŞLUĞU çiviliyor — `upload/netlify_client_secrets.json`'ın anahtarı düpedüz
`"token"` ve `_ANAHTARLAR` listesinde çıplak `token` YOKTU, yani

    {"token": "nfp_..."}

maskelenmeden geçiyordu. Gerçek sızıntı şekillerinin diğerleri
(`access_token=`, `/bot<token>/`, `refresh_token`, `app_password`, `Bearer`)
zaten kapalıydı. Boşluk teorik de değil: Netlify hattı aynı gün
`saglik_kontrol.netlify_araci()` ile SAATLİK koşuya bağlandı — o kimlik bilgisi
artık üretim hattında her saat dolaşıyor ve Instagram yüklemelerinin tamamı
ona bağlı.

DÜZELTMENİN ASIL RİSKİ YANLIŞ POZİTİFTİ: çıplak `token` kelimesi normal log
satırlarında sık geçiyor ("upload/token.json yok",
"youtube_captions_token_yok", "Instagram token'ının süresi..."). Bu yüzden
kural DEĞER değil ANAHTAR+AYIRICI arıyor (`token=` ya da `"token":`) ve
başında `\b` var; aşağıdaki ikinci bölüm bunu depodaki GERÇEK log satırı
biçimleriyle doğruluyor.

Bu dosyadaki TÜM token değerleri SAHTEDİR.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gizli_maskele import MASKE, maskele

# Netlify kişisel erişim token'ının BİÇİMİNE benziyor (nfp_ + uzun gövde),
# ama uydurma.
SAHTE_NETLIFY = "nfp_SAHTEabcdefghijklmnopqrstuvwxyz0123456789"


def _sizmadi(cikti, gizli):
    assert gizli not in cikti, "SIZINTI: %r -> %r" % (gizli, cikti)
    assert MASKE in cikti, "maskelenmedi: %r" % (cikti,)


# --- 1) Sızıntı şekilleri KAPALI -----------------------------------------


def test_netlify_json_govdesi():
    """Dosyanın kendi biçimi: `netlify_kontrol.py` bunu `json.load` ile
    okuyor, bir hata mesajı/debug satırı sözlüğü olduğu gibi basabilir."""
    metin = '{"token": "%s", "site_id": "famousmusicstudio"}' % SAHTE_NETLIFY
    cikti = maskele(metin)
    _sizmadi(cikti, SAHTE_NETLIFY)
    assert "site_id" in cikti          # gizli olmayan alan korunuyor


def test_netlify_dict_repr():
    """Python bir dict'i repr ederken tek tırnak kullanır."""
    metin = "creds: {'token': '%s', 'site_id': 'abc'}" % SAHTE_NETLIFY
    cikti = maskele(metin)
    _sizmadi(cikti, SAHTE_NETLIFY)
    assert "site_id" in cikti


def test_ciplak_token_sorgu_dizesinde():
    metin = "ConnectionError: https://api.netlify.com/api/v1/sites?token=%s&x=1" \
        % SAHTE_NETLIFY
    _sizmadi(maskele(metin), SAHTE_NETLIFY)


def test_netlify_token_anahtarsiz_ham_halde():
    """ANAHTAR YOKKEN de yakalanmalı: `nfp_` değer-deseni."""
    _sizmadi(maskele("beklenmeyen yanit: %s" % SAHTE_NETLIFY), SAHTE_NETLIFY)


def test_netlify_token_bearer_basliginda():
    """`netlify_kontrol` token'ı Authorization başlığında yolluyor."""
    metin = "istek basliklari: {'Authorization': 'Bearer %s'}" % SAHTE_NETLIFY
    _sizmadi(maskele(metin), SAHTE_NETLIFY)


def test_idempotent():
    """`log_rotate.trim_log()` aynı dosyayı her koşuda yeniden maskeliyor —
    ikinci geçiş metni DEĞİŞTİRMEMELİ (daha önce bir karakter uzama hatası
    yaşandı)."""
    for metin in ('{"token": "%s"}' % SAHTE_NETLIFY,
                  "token=%s" % SAHTE_NETLIFY,
                  "ham: %s" % SAHTE_NETLIFY):
        bir = maskele(metin)
        assert maskele(bir) == bir


# --- 2) YANLIS POZITIF YOK -----------------------------------------------

# Hepsi depodaki GERÇEK log/çıktı satırı biçimleri (auto_process.py,
# dj_famous_process.py, weekly_report.py, netlify_kontrol.py, youtube_captions).
NORMAL_SATIRLAR = [
    "  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)",
    "  TikTok atlandı: upload/tiktok_token.json yok (önce tiktok_auth.py çalıştır)",
    "  Instagram atlandı: upload/instagram_token.json yok",
    "  altyazı atlandı: youtube_captions_token_yok",
    "  Instagram token'ının süresi ~12 gün içinde doluyor — yeniden yetkilendir",
    "Kimlik doğrulama başarılı, token.json yazıldı.",
    "token   : 44 karakter",
    "site_id : GEÇERLİ (ad: famousmusicstudio)",
    "  analytics_token.json ayrı tutuluyor: aynı token'a scope eklemek yükleme "
    "hattını durdurur",
    "  YouTube: sayfalama nextPageToken=CAUQAA ile devam ediyor",
]


def test_normal_log_satirlari_aynen_korunur():
    for satir in NORMAL_SATIRLAR:
        assert maskele(satir) == satir, \
            "YANLIS POZITIF: %r -> %r" % (satir, maskele(satir))


def test_mevcut_maskeleme_testleri_hala_gecerli():
    """Yeni kuralın ESKİ yanlış-pozitif setini bozmadığı da doğrulansın —
    `test_gizli_maskele.py` bu listeyi kendi başına zaten koşuyor, burada
    ikinci bir kapı olarak duruyor (iki dosya birbirinden bağımsız
    değiştirilebiliyor)."""
    import test_gizli_maskele as eski
    for satir in eski.NORMAL_SATIRLAR:
        assert maskele(satir) == satir
