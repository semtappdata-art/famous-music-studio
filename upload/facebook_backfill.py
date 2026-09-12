"""Katalogda Facebook'a hiç gitmemiş parçaları GÜNLERE YAYARAK yükler.

Neden ayrı bir modül — `auto_process._is_fully_done()` dört alana bakıyor
(YouTube, Shorts, TikTok, Instagram) ve Facebook orada YOK. Bu bilinçli:
o listeye Facebook eklemek, bayrak kapalıyken ya da token yokken TÜM katalogu
sonsuza kadar "bekleyen" gösterirdi (aynı tuzağa `youtube_captions_done` için
de düşülmüş, bkz. o fonksiyonun docstring'i). Sonuç olarak zaten tamamlanmış
projeler bir daha hiç işlenmiyor, yani geri doldurma kendiliğinden olmuyor.

KAPSAM — ÜÇ İÇERİK KÖKÜ (2026-09-11'de düzeltildi): `BASE` yalnızca
`projects/` idi, yani bir DJ setinin ya da derlemenin Facebook yüklemesi yarım
kalırsa HİÇBİR süpürge onu tamamlamıyordu (dj_famous_process tek denemeden
sonra projeyi bırakıyor). Artık `uyumluluk.KOKLER`. Bunun İKİNCİ ve daha az
görünen faydası: `bugun_yuklenen()` de üç kökü sayıyor — eskiden bir DJ setinin
BUGÜN yapılan Facebook paylaşımı sayaca HİÇ girmiyordu, yani günlük tavan
EKSİK sayıyordu (`bluesky_upload._todays_upload_count` ile birebir aynı hata:
eksik sayan tavan, olmayan tavandan farksız). Bu yüzden kapsam genişlemesi
tavanı GEVŞETMİYOR, tersine sıkıyor — GUNLUK_TAVAN 2'de KALDI.

Neden günlere yayılıyor — sayfa yeni (0 takipçi) ve 17 Reels'i arka arkaya
atmak yeni bir sayfada spam sinyali üretir.

Tempo, iki kapıyla sınırlanıyor:
  1. YALNIZCA golden-hour içinde çalışır (config.GOLDEN_HOURS). Dışındaysa
     hiçbir şey yapmaz — zamanlama yerine hemen yayın tercih edildi, çünkü
     aynı golden-hour'a birden fazla gönderi zamanlamak hepsinin aynı anda
     çıkmasına yol açardı.
  2. Günlük tavan (GUNLUK_TAVAN). Saatlik koşuda golden-hour 6 saat sürüyor,
     yani tavan olmadan günde 6 gönderi olurdu.

Kullanım:
    python upload/facebook_backfill.py --dry-run
    python upload/facebook_backfill.py --limit 1
"""

import argparse
import json
import os
import sys
import time

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(UPLOAD_DIR)
sys.path.insert(0, UPLOAD_DIR)
sys.path.insert(0, REPO)

import config
import uyumluluk
from ag_yeniden_deneme import belirsiz_mi

# Günde en fazla kaç Facebook gönderisi (geri doldurma + o gün yapılan normal
# paylaşımlar BİRLİKTE — sayaç artık üç kökü de geziyor, bkz. docstring).
GUNLUK_TAVAN = 2

# ÜÇ içerik kökü. Adı `BASE` (tekil) kaldı ama artık bir kök DEMETİ:
# `uyumluluk.proje_klasorleri()` hem tek yol (str) hem demet kabul ediyor, ve
# mevcut testler bu adı tek bir klasöre monkeypatch'liyor — ikisi de çalışsın.
# Kök listesi burada ELLE SAYILMIYOR: tek kanonik kaynak uyumluluk.KOKLER
# (muhafız: tests/test_kok_listesi_muhafizi.py).
BASE = uyumluluk.KOKLER


def _durum(klasor):
    sp = os.path.join(klasor, "state.json")
    try:
        with open(sp, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def eksik_projeler():
    """YouTube'da yayında ama Facebook'a hiç gitmemiş projeler, ESKİDEN YENİYE.

    Yayın sırasını korumak için yükleme tarihine göre sıralı: sayfaya
    kataloğun kronolojisi yansısın, rastgele bir sıra değil.
    """
    liste = []
    for klasor in uyumluluk.proje_klasorleri(BASE):
        st = _durum(klasor)
        if not st.get("youtube_video_id"):
            continue                      # henüz yayınlanmamış, sırası değil
        if st.get("facebook_reels_id"):
            continue                      # zaten var
        # BELIRSIZ kalan yukleme ADAY DEGIL. Ag hatasi govde gonderildikten
        # SONRA olustuysa yukleyici durum anahtarini yazmaz ve state'e bir
        # belirsizlik isareti birakir (upload/ag_yeniden_deneme.py). Bu satir
        # olmasaydi supurge projeyi 'hic gitmemis' gorup bir sonraki kosuda
        # YENIDEN yuklerdi — kopyayi supurge uretirdi. Yukleyicinin icindeki
        # kapi zaten istegi engelliyor, ama o zaman supurge her kosuda istisna
        # alip limit=1'lik tek gunluk slotu KALICI olarak tikardi. Operator
        # elle bakip isareti temizleyene kadar bu proje kuyrukta yok.
        if belirsiz_mi(st, "facebook_reels_id"):
            continue
        # AŞAĞIDAKİ İKİ FİLTRE, kapsam üç köke çıkarılırken EKLENDİ (2026-09-11).
        # Kapsam `projects/` iken ikisi de teorikti; dj_sets/derlemeler girince
        # ikisinin de diskte GERÇEK bir karşılığı var:
        #   * City Pulse Set `telif_araliklari` taşıyor (Content ID eşleşmesi) —
        #     telif eşleşmiş bir içeriği başka bir platforma yeniden yaymak tam
        #     olarak uyumluluk.kontrol()'ün engellediği şey.
        #   * "Küllerimden Geç" `youtube_privacy="unlisted"` (kopya/liste dışı) —
        #     YouTube'da bilerek gizlenmiş bir videoyu Facebook'a çıkarmak
        #     niyetin tersi olurdu.
        # ek_platform_backfill.eksik_projeler() bu iki kapıyı zaten taşıyordu;
        # burada eksikti.
        if st.get("telif_araliklari"):
            continue                      # telif eşleşmesi — yeniden yayınlama
        if st.get("youtube_privacy") in ("unlisted", "private"):
            continue                      # liste dışı/kopya
        video = os.path.join(klasor, "output", "shorts_9x16.mp4")
        if not os.path.isfile(video):
            continue
        liste.append((st.get("youtube_uploaded_at") or "", klasor))
    liste.sort()
    return [k for _, k in liste]


def bugun_yuklenen():
    """Bugün Facebook'a kaç gönderi gitti — günlük tavanı uygulamak için.

    ÜÇ kökü birden sayıyor: geri doldurmanın yanında, o gün normal hattan
    (dj_famous_process) çıkmış bir setin/derlemenin Facebook paylaşımı da bu
    tavanı doldurmalı. Tek kök sayıldığında tavan sessizce eksik sayıyordu.
    """
    bugun = time.strftime("%Y-%m-%d")
    sayi = 0
    for klasor in uyumluluk.proje_klasorleri(BASE):
        st = _durum(klasor)
        damga = st.get("facebook_uploaded_at") or ""
        if str(damga)[:10] == bugun:
            sayi += 1
    return sayi


# --- POLİTİKA KAPISI (2026-09-12'de eklendi) ------------------------------
# Bu modül `uyumluluk`u BUGÜNE KADAR yalnızca KÖK LİSTESİ için kullanıyordu
# (`KOKLER` + `proje_klasorleri()`); deponun politika kapısı olan
# `uyumluluk.kontrol()` burada HİÇ çağrılmıyordu. Kapı render'dan önce
# (validate_project) ve ana hattın yüklemesinden önce (auto_process /
# dj_famous_process) otomatik çalışıyor, ama BU SÜPÜRGE onun DIŞINDAN Facebook
# Reels yayınlıyordu — üstelik tam da `_is_fully_done()`'dan geçmiş, ana hattın
# bir daha DOKUNMADIĞI projeleri.
#
# Yukarıdaki `eksik_projeler()` iki state alanını (telif_araliklari,
# youtube_privacy) zaten eliyor ama o alanlar KOD KAPISI DEĞİL: `youtube_privacy`
# ELLE yapılmış bir YouTube ayarının yerel AYNASI. 'Küllerimden Geç' ('Yeniden
# Doğacağım' ile aynı audio.wav md5'i) bugün SADECE o ayna sayesinde Facebook'a
# gitmiyor; ayar public'e çekilirse ya da alan bayatlarsa kopya yayına çıkardı.
# İki filtre de KALDIRILMADI — iki bağımsız kapı bilinçli (aynı desen
# caption_align/youtube_captions slug eşleşmesinde de var).

# Koşu başına BİR kez uyarılan anahtarlar (notify.uyar_bir_kez deseni). Süpürge
# saatlik koşuyor ve engelli proje HER koşuda atlanacak; anahtar proje YOLUNA
# bağlı olduğu için log'a koşu başına tek satır düşer. BİLEREK temizlenmiyor:
# kapsam bir PROCESS, yani bir zamanlayıcı koşusu.
_UYARILANLAR = set()


def _stderr(mesaj):
    """Yedek kanal: notify yoksa satır yine de görünür bir yere düşsün."""
    print(mesaj, file=sys.stderr)


def _kapi_uyar(anahtar, mesaj, log):
    """Aynı anahtar için koşu başına TEK satır yazar.

    `notify` TEMBEL import ediliyor — import zamanında zorunlu bir bağımlılık
    olmasın diye. Import edilemezse satır KAYBOLMUYOR, `log`a düşüyor: sessizce
    atlayan bir koruma, olmayan korumadan kötüdür.
    """
    if anahtar in _UYARILANLAR:
        return
    _UYARILANLAR.add(anahtar)
    try:
        import notify
        notify.uyar_bir_kez(anahtar, mesaj)
    except Exception:                     # noqa: BLE001
        log(mesaj)


def politika_kapisi(klasor, log=_stderr):
    """Bu proje gönderilebilir mi — ENGEL varsa sebep metni, temizse "".

    FAIL-CLOSED: `uyumluluk.kontrol()` istisna fırlatırsa proje ATLANIR.
    Gerekçe bu depoda ödenmiş bir bedel: `uyumluluk.KOKLER` göreli yolken
    `os.path.isdir` False dönüyor, `kontrol()` hata=0 uyarı=0 diyor ve kapı
    KENDİLİĞİNDEN AÇILIYORDU. "Bilmiyorum" ile "temiz" aynı şey değil; bu
    kapının yanlış tarafa düşmesinin bedeli bir gönderinin BİR KOŞU gecikmesi
    değil, kopya/telifli içeriğin yayına çıkmasıdır — gecikme geri alınabilir,
    yayın alınamaz.

    HATA yalnızca O PROJEYİ düşürür, süpürgeyi DURDURMAZ (bir projenin engeli
    diğerlerini bloklamamalı); UYARI'lar yalnızca log'a yazılır.
    """
    yol = os.path.abspath(klasor)
    ad = os.path.basename(os.path.normpath(klasor))
    try:
        hatalar, uyarilar = uyumluluk.kontrol(klasor, "yukleme")
    except Exception as e:                # noqa: BLE001
        hatalar = ["uyumluluk kapısı ÇALIŞTIRILAMADI (%s: %s) — fail-closed, "
                   "proje atlandı" % (type(e).__name__, e)]
        uyarilar = []
    for u in uyarilar:
        _kapi_uyar("fb_backfill_uyumluluk_uyari:%s:%s" % (yol, str(u)[:40]),
                   "  uyumluluk uyarısı (%s): %s" % (ad, u), log)
    engel = hatalar[0] if hatalar else ""
    if engel:
        _kapi_uyar("fb_backfill_uyumluluk_hata:%s" % yol,
                   "  %s: UYUMLULUK HATASI — Facebook geri doldurma ATLANDI: %s"
                   % (ad, engel), log)
    return engel


def backfill(limit=1, dry_run=False, ignore_golden=False, log=_stderr):
    """En fazla `limit` projeyi Facebook'a yükler. Sonuç sözlüğü döner."""
    if not config.EK_PLATFORMLAR.get("facebook"):
        return {"durum": "kapalı", "sebep": "config.EK_PLATFORMLAR['facebook'] False"}

    golden_disi = config.next_golden_publish_time() is not None
    if golden_disi and not ignore_golden:
        return {"durum": "beklemede", "sebep": "golden-hour dışındayız"}

    yapildi = bugun_yuklenen()
    kalan_kota = GUNLUK_TAVAN - yapildi
    if kalan_kota <= 0:
        return {"durum": "tavan", "sebep": "bugün %d gönderi yapıldı" % yapildi}

    eksik = eksik_projeler()
    if not eksik:
        return {"durum": "bitti", "sebep": "Facebook'a gitmemiş proje kalmadı"}

    # POLİTİKA KAPISI yalnızca GERÇEKTEN gönderilecek adaylara uygulanıyor, tüm
    # kataloğa değil. KOTA/MALİYET: `uyumluluk.kontrol()` md5 hesaplıyor ve bu
    # süpürge saatlik koşuyor. Ölçüldü (22 proje, 2026-09-12): tüm katalog
    # 0,45 sn, proje başına ~6 ms; tek istisna aynı BOYUTTA ses taşıyan kopya
    # çifti (~0,17 sn — modülün BOYUT ÖN FİLTRESİ ancak orada md5'e düşüyor).
    # Yani tüm katalog da taşınabilirdi; kuyruğun başındaki 1-2 adayla
    # sınırlamak hem daha ucuz hem de doğru soru: kapı YAYIN kararının kapısı.
    # Engellenen aday kotayı TÜKETMEZ (sıradaki temiz projeye bakılır) ve
    # gönderi yapılmadığı için günlük tavana da girmez — tavan
    # `facebook_uploaded_at` damgalarını, yani GERÇEKLEŞEN gönderileri sayıyor.
    hedefler = []
    engellenen = []
    for klasor in eksik:
        if len(hedefler) >= min(limit, kalan_kota):
            break
        engel = politika_kapisi(klasor, log)
        if engel:
            engellenen.append({"proje": os.path.basename(klasor),
                               "sebep": engel[:160]})
            continue
        hedefler.append(klasor)

    sonuc = {"durum": "tamam", "kalan": len(eksik), "islenen": []}
    if engellenen:
        sonuc["engellenen"] = engellenen

    if dry_run:
        sonuc["durum"] = "kuru"
        sonuc["islenen"] = [os.path.basename(k) for k in hedefler]
        return sonuc

    from facebook_upload import upload_reels
    for klasor in hedefler:
        ad = os.path.basename(klasor)
        try:
            # schedule=False: zaten golden-hour içindeyiz, hemen yayınla.
            vid = upload_reels(klasor, schedule=False)
            sonuc["islenen"].append({"proje": ad, "video_id": vid})
        except Exception as e:
            sonuc["islenen"].append({"proje": ad, "hata": str(e)[:200]})

    # "kalan" YÜKLEMEDEN SONRA yeniden sayılıyor. Önce hesaplanan sayı log'a
    # bir eksik gidiyordu: "Beni Bırakma yüklendi (kalan 17)" yazıyordu ama
    # gerçek kalan 16'ydı — yükleme sayacın anlık görüntüsünden sonra oluyor.
    sonuc["kalan"] = len(eksik_projeler())
    return sonuc


def main():
    ap = argparse.ArgumentParser(description="Facebook'a gitmemiş parçaları günlere yayarak yükler.")
    ap.add_argument("--limit", type=int, default=1, help="Bu koşuda en fazla kaç proje (varsayılan 1)")
    ap.add_argument("--dry-run", action="store_true", help="Hiçbir şey gönderme, ne yapacağını yaz")
    ap.add_argument("--ignore-golden", action="store_true",
                    help="Golden-hour kontrolünü atla (elle test için)")
    args = ap.parse_args()

    s = backfill(limit=args.limit, dry_run=args.dry_run, ignore_golden=args.ignore_golden)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    if s.get("durum") in ("tamam", "kuru"):
        print()
        print("Facebook'a gitmemiş kalan proje: %d" % len(eksik_projeler()))


if __name__ == "__main__":
    main()
