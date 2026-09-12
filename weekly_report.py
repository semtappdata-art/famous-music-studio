# -*- coding: utf-8 -*-
"""Katalogun YouTube istatistiklerini (uzun format + Shorts) tazeleyip özet bir
tablo basar — haftalık takip için. Ayrıca izlenme SÜRESİ (watch-time) özetini
ekler ve Instagram token'ının süresi yaklaşıyorsa uyarır.

Kullanım:
    python weekly_report.py                 # projects + dj_sets + derlemeler
    python weekly_report.py --base projects # tek kök
    python weekly_report.py --izlenme       # sadece izlenme süresi raporu (elle)

İki ayrı giriş noktası var:

1. `main()` — ELLE çalıştırılan tam rapor (tablo + izlenme süresi).
2. `izlenme_raporu()` — saatlik `auto_process` koşusundan çağrılmak üzere
   yazılmış, HAFTADA BİR gerçekten çalışan izlenme süresi kontrolü. Neden:
   bu dosya hiçbir Görev Zamanlayıcı görevine bağlı değil (bkz.
   `saglik_kontrol.py` docstring'i, madde 2) — yani içine yazılan her ölçüm
   pratikte hiç çalışmıyor. `saglik_kontrol` bu sorunu "korumaları saatlik
   hatta bağla, bildirimi günde bire indir" deseniyle çözdü; burada aynı desen
   GÜNLÜK damgadan HAFTALIK damgaya genelleştiriliyor (izlenme raporu haftalık
   bir şey, saatlik değil).
3. `haftalik_gozden_gecirme()` — aynı saatlik koşudan, HAFTADA BİR (pazartesi
   sabahı) telefona giden "bu hafta ne yayınlandı / ne bekliyor / ölçüm /
   sağlık / senin işin" özeti. Detay ve gerekçeler aşağıdaki
   "HAFTALIK GÖZDEN GEÇİRME" bölümünün başında. Elle:
   `python weekly_report.py --haftalik` (bildirim GÖNDERMEZ, sadece basar).
"""

import argparse
import contextlib
import datetime
import io
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

from youtube_stats import get_stats_batch, KOKLER

INSTAGRAM_TOKEN_PATH = os.path.join(REPO, "upload", "instagram_token.json")
INSTAGRAM_WARN_DAYS = 10  # bu kadar gün kala uyar (60 günlük token için makul bir tampon)

# saglik_kontrol.py ile AYNI durum dosyası — damgalar tek yerde toplansın,
# iki ayrı "en son ne zaman bildirdim" defteri tutulmasın.
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")

HAFTA_ANAHTARI = "izlenme_rapor_hafta"        # rapor bu hafta çalıştı mı
BOS_ANAHTARI = "izlenme_rapor_bos_gun"        # veri gelmedi -> bugün tekrar deneme
TOKEN_ANAHTARI = "izlenme_token_bildirim_hafta"
RAPOR_BILDIRIM = "izlenme_rapor_bildirim_hafta"

AUTH_KOMUTU = "python upload/youtube_analytics.py --auth"


# --------------------------------------------------------------------------
# Damga/bildirim yardımcıları — saglik_kontrol._durum/_kaydet/_bildir deseni,
# tek farkla: damga "gün" olmak zorunda değil, dışarıdan veriliyor (hafta).
# Kopya (import yerine) bilerek: saglik_kontrol'ün özel isimlerine bağlanmak
# o dosya değiştiğinde bu hattı sessizce kırardı.
# --------------------------------------------------------------------------
def _durum(yol: str | None = None) -> dict:
    try:
        with open(yol or DURUM_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _kaydet(g: dict, yol: str | None = None) -> None:
    """Damgalari birlestirip ATOMIK yazar (bkz. state_io).

    NEDEN state_io: duz `open(..., "w")` hedefi ONCE SIFIRLIYOR; `json.dump`
    bitmeden surec olurse diskte YARIM bir JSON kaliyor. Burada ek bir sebep
    var: bu dosya (`upload/saglik_durum.json`) `saglik_kontrol.py` ile
    PAYLASILIYOR — biri gunluk saglik damgalarini, digeri haftalik izlenme
    damgalarini yaziyor. Yarim bir yazim iki modulun damgalarini BIRLIKTE
    sifirlardi.
    """
    yol = yol or DURUM_DOSYASI
    d = _durum(yol)
    d.update(g)
    try:
        import state_io
        state_io._atomik_yaz(yol, d)
    except OSError:
        pass


def _bildir(baslik: str, mesaj: str, anahtar: str, damga: str,
            yol: str | None = None) -> bool:
    """Aynı anahtar için DÖNEM BAŞINA bir bildirim gönderir. Gönderildiyse True.

    saglik_kontrol._bildir'in genelleştirilmişi: orada damga sabit olarak gün
    ("%Y-%m-%d"), burada çağıran belirliyor — izlenme raporunda ISO hafta.
    Saatlik koşuda her seferinde telefon çalması uyarıyı değersizleştirir.

    DAMGA SADECE BAŞARIDA ATILIYOR (2026-09-11, `saglik_kontrol._bildir` ile
    AYNI düzeltme — bilerek birebir aynı desen). Eskiden `notify.send`in dönüş
    değeri YOK SAYILIYOR, istisnası da `except Exception: pass` ile yutuluyor,
    damga yine atılıyordu. Pratik etkisi `TOKEN_ANAHTARI`nda gerçek: "Analytics
    izni hiç alınmamış" hatırlatması gönderilemese bile hafta damgalanıp uyarı
    bir HAFTA susuyordu. İzlenme ölçümü bugüne kadar zaten hiç çalışmamıştı;
    bozulduğunu haber verecek TEK mekanizma bu bildirim.

    İSTİSNA YAKALAMAK YETMİYOR: `notify.send` üç başarısızlık yolunun da
    (kanal kurulu değil / HTTP hatası / ağ hatası) hiçbirinde PATLAMIYOR,
    sessizce `False` dönüyor (bkz. notify.py). Yani bu arızayı yakalamanın tek
    yolu DÖNÜŞ DEĞERİNE bakmak.

    Fazladan susturma YOK: başarısızlıkta damga atılmadığı için bir sonraki
    saatlik koşu yeniden dener, ama log kirlenmiyor — gürültü kontrolü zaten
    `notify.py`nin içinde (`uyar_bir_kez`, süreç başına anahtar başına tek
    satır).
    """
    if _durum(yol).get(anahtar) == damga:
        return False
    try:
        import notify
        gonderildi = notify.send(baslik, mesaj)
    except Exception as e:
        print("  bildirim gönderilemedi (%s): %s" % (baslik, str(e)[:150]))
        return False
    if not gonderildi:
        # Damga YOK -> bir sonraki saatlik koşu yeniden dener. Sebebi
        # notify.uyar_bir_kez() koşu başına bir kez zaten yazdı.
        return False
    _kaydet({anahtar: damga}, yol)
    return True


def _hafta(t: float | None = None) -> str:
    """ISO yıl-hafta damgası ("2026-W37").

    time.strftime("%G-W%V") Windows'ta güvenilir değil (platform C
    kütüphanesine bağlı) — isocalendar() her yerde aynı sonucu veriyor.
    """
    y, w, _ = datetime.date.fromtimestamp(t if t is not None else time.time()).isocalendar()
    return "%d-W%02d" % (y, w)


def _kok_adi(kok: str) -> str:
    """Kök için kısa ad ("projects"), TAM YOL değil.

    youtube_analytics.KOKLER mutlak yollardan oluşuyor (bilerek — göreli
    bırakılınca yanlış cwd'de sessizce boş sonuç veriyordu). O yüzden özetin
    anahtarı `C:\\Users\\...\\projects` gelebiliyor ve tabloyu taşırıyor.
    basename her iki durumda da doğru: kısa ad verilirse kendisini döner.
    """
    return os.path.basename(str(kok).rstrip("\\/")) or str(kok)


# --------------------------------------------------------------------------
def _check_instagram_token_expiry() -> None:
    """Instagram token'ının kalan ömrü (elle koşuda bilgi amaçlı).

    NOT: bu kontrolün OTOMATİK hattı artık `saglik_kontrol.instagram_token_suresi()`
    (saatlik auto_process koşusundan çalışıyor). Burada duruyor çünkü elle
    `python weekly_report.py` çalıştıran kullanıcı da bu bilgiyi görmeli.
    """
    if not os.path.isfile(INSTAGRAM_TOKEN_PATH):
        return  # Instagram hiç bağlanmamış, kontrol edecek bir şey yok
    try:
        with open(INSTAGRAM_TOKEN_PATH, "r", encoding="utf-8") as f:
            token = json.load(f)
        expires_in = token.get("expires_in")
        if not expires_in:
            return
        # expires_in, dosyanın en son YAZILDIĞI ana göre (exchange_code veya
        # refresh_access_token) göreli saniye — dosyanın mtime'ını o an olarak kabul
        # ediyoruz (kesin değil ama makul bir yaklaşım).
        issued_at = os.path.getmtime(INSTAGRAM_TOKEN_PATH)
        expires_at = issued_at + expires_in
        days_left = (expires_at - time.time()) / 86400
        if days_left < 0:
            print(f"⚠️  Instagram token'ının süresi DOLMUŞ görünüyor (~{-days_left:.0f} gün önce) — "
                  f"upload/instagram_upload.py 401 vermeye başlamış olabilir. "
                  f"Yeniden yetkilendir: python upload/instagram_auth.py --print-url")
        elif days_left < INSTAGRAM_WARN_DAYS:
            print(f"⚠️  Instagram token'ının süresi ~{days_left:.0f} gün içinde doluyor — "
                  f"yakında yeniden yetkilendirmen gerekecek: python upload/instagram_auth.py --print-url")
    except (json.JSONDecodeError, OSError, KeyError):
        pass  # sağlık kontrolü, ana raporu bozmasın


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def _sayi(state: dict, *alanlar) -> int:
    """Birden fazla alanın toplamı; None/eksik değerler 0 sayılır."""
    t = 0
    for a in alanlar:
        try:
            t += int(state.get(a) or 0)
        except (TypeError, ValueError):
            pass
    return t


# --------------------------------------------------------------------------
# İzlenme süresi (watch-time)
# --------------------------------------------------------------------------
def _ozet_satirlari(ozet: dict) -> list:
    """youtube_analytics.rapor()["ozet"] -> basılacak satırlar.

    Tek yerde: hem elle koşu (`main`) hem saatlik hat (`izlenme_raporu`)
    aynı biçimi kullansın. Kök adı burada kısaltılıyor (bkz. _kok_adi).
    """
    satirlar = ["İZLENME SÜRESİ (uzun format)",
                "%-12s %6s %9s %11s %9s" % ("kök", "video", "izlenme", "toplam dk", "ort sn")]
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        satirlar.append("%-12s %6d %9d %11d %9d"
                        % (_kok_adi(kok), o["video"], o["izlenme"], o["dakika"],
                           o["ort_izlenme_sn"]))
    satirlar.append("")
    # Asıl karşılaştırma: BİR videonun ürettiği ortalama izlenme dakikası.
    # Toplamı karşılaştırmak katalog lehine yanıltıcı olurdu — orada 18,
    # setlerde 2 video var.
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        if o["video"]:
            satirlar.append("  %s: video başına %.0f dakika izlenme"
                            % (_kok_adi(kok), o["dakika"] / o["video"]))
    return satirlar


def _bildirim_metni(ozet: dict) -> str:
    parcalar = []
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        if o["video"]:
            parcalar.append("%s: video başına %.0f dk (%d video)"
                            % (_kok_adi(kok), o["dakika"] / o["video"], o["video"]))
    return " | ".join(parcalar) or "veri yok"


def izlenme_raporu(log=print, zorla: bool = False, durum_dosyasi: str | None = None,
                   rapor_fn=None, token_yolu: str | None = None) -> dict:
    """HAFTADA BİR izlenme süresi raporu — saatlik auto_process koşusundan.

    NEDEN BURADA: `upload/youtube_analytics.py` doğru yazıldı ama tek çağıranı
    bu dosyaydı ve bu dosya hiçbir zamanlayıcı görevine bağlı değil — yani
    ölçüm pratikte HİÇ çalışmıyordu. `saglik_kontrol.py` bugün tam bu sebeple
    yazıldı: zamanlayıcıya bağlı olmayan korumaları saatlik hatta bağlamak
    için. Aynı deseni izliyoruz, tek farkla: damga günlük değil HAFTALIK.

    Üç ayrı damga var ve üçü de aynı amaca hizmet ediyor — saatlik koşuda
    gürültü yapmamak:
      * HAFTA_ANAHTARI — rapor bu hafta çalıştıysa bir daha çalışma.
      * BOS_ANAHTARI   — Analytics veri döndürmediyse (yeni video, henüz
                         işlenmemiş) bugün tekrar deneme, yarın dene. Haftayı
                         damgalamıyoruz, yoksa tek boş sonuç yüzünden rapor
                         bir hafta kaybolurdu.
      * TOKEN_ANAHTARI — izin hiç alınmamışsa haftada bir hatırlat.

    Hiçbir hata otomasyonu durdurmaz.
    """
    yol = durum_dosyasi or DURUM_DOSYASI
    hafta = _hafta()
    bugun = time.strftime("%Y-%m-%d")
    d = _durum(yol)
    if not zorla:
        if d.get(HAFTA_ANAHTARI) == hafta:
            return {"durum": "atlandi", "neden": "bu hafta çalıştı", "hafta": hafta}
        if d.get(BOS_ANAHTARI) == bugun:
            return {"durum": "atlandi", "neden": "bugün veri gelmedi", "gun": bugun}

    token = token_yolu
    if rapor_fn is None:
        try:
            from youtube_analytics import rapor as _rapor, TOKEN_PATH
        except Exception as e:
            log("  İzlenme raporu: youtube_analytics yüklenemedi (%s)" % str(e)[:120])
            _kaydet({BOS_ANAHTARI: bugun}, yol)
            return {"durum": "modul_yok", "hata": str(e)[:120]}
        rapor_fn = _rapor
        if token is None:
            token = TOKEN_PATH

    # ÖN KOŞUL: analytics ayrı bir token kullanıyor (yükleme token'ını
    # geçersiz kılmamak için, bkz. youtube_analytics modül notu). Kullanıcı
    # OAuth akışını hiç çalıştırmadıysa ölçüm sessizce boş döner ve KİMSE
    # FARK ETMEZ — bugün altı kez görülen desenin ta kendisi. Haftada bir,
    # gürültüsüz bir hatırlatma bırakıyoruz.
    if token and not os.path.isfile(token):
        mesaj = ("İzlenme süresi ölçümü çalışmıyor: YouTube Analytics izni hiç "
                 "alınmamış. Bir kereye mahsus: " + AUTH_KOMUTU)
        log("  UYARI: " + mesaj)
        gonderildi = _bildir("İzlenme ölçümü kapalı", mesaj, TOKEN_ANAHTARI, hafta, yol)
        return {"durum": "token_yok", "bildirim": gonderildi, "komut": AUTH_KOMUTU}

    try:
        r = rapor_fn() or {}
    except Exception as e:
        log("  İzlenme raporu HATA: %s" % str(e)[:150])
        _kaydet({BOS_ANAHTARI: bugun}, yol)
        return {"durum": "hata", "hata": str(e)[:150]}

    ozet = r.get("ozet") or {}
    if not ozet:
        log("  İzlenme raporu: Analytics'ten veri gelmedi — bugün tekrar denenmeyecek.")
        _kaydet({BOS_ANAHTARI: bugun}, yol)
        return {"durum": "veri_yok"}

    for satir in _ozet_satirlari(ozet):
        log(satir)
    # Hafta damgalanıyor: bir sonraki koşularda tekrar API'ye gitmesin.
    # BOS_ANAHTARI temizleniyor ki yeni haftada eski gün damgası engel olmasın.
    # ÖZET DE KAYDEDİLİYOR (2026-09-12): haftalık gözden geçirme raporu
    # izlenme SÜRESİNİ buradan okuyor. Alternatifi Analytics'e İKİNCİ bir
    # istek atmaktı — aynı sayı, ayrı kota havuzu, sıfır kazanç. Sadece
    # özet (kök başına dört sayı) yazılıyor, kök adları KISA hâlleriyle
    # (mutlak yol damga dosyasını gereksiz şişiriyordu, bkz. _kok_adi).
    _kaydet({HAFTA_ANAHTARI: hafta, BOS_ANAHTARI: "",
             IZLENME_OZET_ANAHTARI: {_kok_adi(k): {
                 "video": o.get("video"), "izlenme": o.get("izlenme"),
                 "dakika": o.get("dakika"), "ort_izlenme_sn": o.get("ort_izlenme_sn"),
             } for k, o in ozet.items() if isinstance(o, dict)}}, yol)
    _bildir("Haftalık izlenme süresi", _bildirim_metni(ozet), RAPOR_BILDIRIM, hafta, yol)
    return {"durum": "tamam", "hafta": hafta, "ozet": ozet}


def _watch_time_ozeti() -> None:
    """Elle koşuda izlenme süresi bölümü — damgaya bakmadan, her zaman basar."""
    try:
        from youtube_analytics import rapor, TOKEN_PATH
        if not os.path.isfile(TOKEN_PATH):
            print()
            print("İzlenme süresi ölçümü kapalı (analytics izni yok). Bir kereye mahsus: "
                  + AUTH_KOMUTU)
            return
        ozet = (rapor() or {}).get("ozet") or {}
        if not ozet:
            return
        print()
        for satir in _ozet_satirlari(ozet):
            print(satir)
    except Exception as e:
        print("  İzlenme süresi alınamadı: %s" % str(e)[:120])


# --------------------------------------------------------------------------
# HAFTALIK GÖZDEN GEÇİRME (2026-09-12)
#
# NE İÇİN: kullanıcı tek kişilik bir operasyon yürütüyor ve "bu hafta ne oldu,
# ne bekliyor, ne yapmalıyım" sorusunu her hafta ELLE cevaplıyordu. Bu bölüm
# o üç soruyu telefona giden TEK bir kısa metne indiriyor.
#
# NEDEN AYRI BİR MODÜL DEĞİL: bu dosya zaten "haftalık takip" dosyası ve
# `izlenme_raporu()` ile HAFTALIK-damga deseni burada kurulu. İkinci bir
# modül, `saglik_durum.json`'da ikinci bir damga defteri ve `_bildir`/`_hafta`
# yardımcılarının üçüncü bir kopyası demekti — bu deponun belgelenmiş hata
# sınıfı (`derleme._enerji` kopyalama vakası, `state_io` öncesi üç ayrı
# yazıcı). Hiçbir şey yeniden hesaplanmıyor: sayılar `state.json`'lardan,
# sağlık `saglik_kontrol.kontrol_et()`ten, izlenme süresi `izlenme_raporu()`nun
# aynı koşuda yazdığı özetten, tarihler markdown dosyalarından okunuyor.
#
# ÜÇ SORU (CLAUDE.md):
#   1. Kim çağıracak? — `auto_process._haftalik_gozden_gecirme()`.
#   2. Hangi zamanlayıcı görevinden? — saatlik `FamousMusicStudio-AutoProcess`;
#      `auto_process.main()`in `finally` bloğu ("iş olsun olmasın her koşuda").
#      YENİ görev EKLENMEDİ — CLAUDE.md bunu açıkça yasaklıyor.
#   3. Çalışmadığını nasıl anlarız? — üretilemezse SESSİZ KALMIYOR: ayrı bir
#      "Haftalık özet üretilemedi" bildirimi gidiyor (günde bir), rapor her
#      koşuda log'a da düşüyor ve gönderim başarısızsa hafta damgası
#      ATILMIYOR (bir sonraki gün yeniden denenir).
#
# KOTA: bu bölüm YouTube API'ye SIFIR istek atıyor. İzlenme sayıları
# `state.json`'lardan (onları günde bir `youtube_stats` tazeliyor), izlenme
# SÜRESİ `izlenme_raporu()`nun yazdığı özetten geliyor. Tek ağ maliyeti
# `saglik_kontrol.kontrol_et()`in içindeki Netlify kontrolü (2 GET) ve o zaten
# saatlik hattan 168 kez/hafta çalışıyor — haftada bir tekrarı %0,6 ek yük.
# --------------------------------------------------------------------------

# Damga anahtarları — hepsi `saglik_durum.json`'da (DURUM_DOSYASI).
HAFTALIK_ANAHTARI = "haftalik_ozet_hafta"          # bu hafta gönderildi mi
HAFTALIK_DENEME_ANAHTARI = "haftalik_ozet_deneme_gun"  # bugün denendi ve gitmedi
HAFTALIK_HATA_ANAHTARI = "haftalik_ozet_hata_gun"  # üretilemedi bildirimi
HAFTALIK_OLCUM_ANAHTARI = "haftalik_ozet_olcum"    # geçen haftanın ölçüm anlık görüntüsü
IZLENME_OZET_ANAHTARI = "izlenme_rapor_ozet"       # izlenme_raporu()'nun bıraktığı özet

# HANGİ GÜN/SAAT — Pazartesi 09:00'dan sonraki ilk saatlik koşu.
#   * Haftanın SORUSU ("bu hafta ne yapmalıyım") hafta başında sorulur; cuma
#     akşamı gelen bir özet bir sonraki pazartesiye kadar bayatlar.
#   * ISO hafta damgası (`_hafta()`) pazartesi değişiyor — rapor penceresi ile
#     damga aynı gün başlasın, "hafta ortasında damga atlama" durumu olmasın.
#   * Golden-hour DIŞINDA (12-14, 18-22): o saatlerde aynı saatlik koşu render
#     + yükleme yapıyor; raporun oraya binmesi hem koşuyu uzatır hem de
#     telefona yayın bildirimleriyle aynı anda ikinci bir bildirim düşürür.
#   * Haftalık DJ görevi cuma 18:00 (`setup_task_scheduler.ps1` varsayılanı) —
#     pazartesi sabahı o setin damgası çoktan diskte, yani haftanın yayınları
#     rapora TAM giriyor.
RAPOR_GUNU = 0          # 0 = Pazartesi (time.localtime().tm_wday)
RAPOR_SAATI = 9         # yerel saat; ilk uygun saatlik koşuda çalışır
PENCERE_SN = 7 * 24 * 60 * 60     # "bu hafta" = son 7 gün (kayan pencere)

# Golden-hour YEDEĞİ — `config.GOLDEN_HOURS` okunamazsa. Tek yerde ve
# gerekçesi burada: golden-hour kaçınması bir TERCİH, bir kapı değil.
GOLDEN_YEDEK = ((12, 14), (18, 22))

# TARİHLİ İŞLER — tarihler KODA GÖMÜLMÜYOR, bu iki dosyanın BAŞLIKLARINDAN
# okunuyor. Sadece başlık satırları taranıyor (gövde değil): gövdedeki
# tarihlerin çoğu kanıt/geçmiş tarihi ("2026-09-11'de doğrulandı") ve hepsini
# listelemek raporu kullanılmaz hâle getirirdi.
TARIH_KAYNAKLARI = ("buyume_kontrol_listesi.md", "CLAUDE.md")

# YEDEK LİSTE — yalnızca yukarıdaki dosyalar okunamazsa/başlıkları değişirse
# kullanılır VE rapora "(yedek liste)" diye YAZILIR (sessizce doğru görünmesin).
# Buradaki tarihler o dosyalardan kopyalandı, kaynakları:
#   2026-10-09  CLAUDE.md, "TARİHLİ RANDEVU": 40 kapak değişikliğinin ölçüm
#               penceresi — bir ay sonraki karşılaştırma yapılmazsa değişikliğin
#               işe yarayıp yaramadığı hiçbir zaman bilinemez.
#   2026-10-11  buyume_kontrol_listesi.md B1: YouTube Reporting API. Bir
#               reporting job yalnızca oluşturulmadan ÖNCEKİ 30 günü geriye
#               dönük üretiyor — bu tarihten sonra "değişiklik öncesi" dönem
#               GERİ GELMEZ.
#   2026-12-09  buyume_kontrol_listesi.md B3: Facebook veri erişimi yenilemesi.
TARIHLI_YEDEK = (
    ("2026-10-09", "Ölçüm penceresi (olcum_temel_cizgi.py --cek)"),
    ("2026-10-11", "YouTube Reporting API son tarihi (B1)"),
    ("2026-12-09", "Facebook veri erişimi yenilemesi (B3)"),
)
TARIHLI_TAVAN = 4       # rapora en fazla bu kadar satır (telefonda okunacak)

# SAĞLIK — `kontrol_et()`in yedi adımının "durum" değerleri ÜÇ kovaya ayrılıyor.
# BEYAZ LİSTE (kara liste değil) BİLEREK: yarın eklenecek yeni bir arıza durumu
# kendiliğinden UYARI sayılır. Ters yön (yeni bir iyi durumun uyarı görünmesi)
# gürültü yapar ama hiçbir şeyi GİZLEMEZ — güvenli taraf bu.
#
# "atlandi" NEDEN TEMİZ SAYILMIYOR: bir adımın ATLANMASI (PowerShell yok, git
# okunamadı, yerel sayfa yok) "sorun yok" DEĞİL, "bakılamadı" demektir. Temiz
# saymak, bu deponun tam da düzeltmeye çalıştığı şeyi yapardı: sessizce hiçbir
# şey yapmayan bir korumayı sağlıklı göstermek. Ama UYARI da değil — yanlış
# alarm üretir. Bu yüzden ayrı bir "not" kovası var, uyarılardan sonra ve
# daha sessiz.
SAGLIK_TEMIZ = frozenset(("tamam", "yok", "bekleyen_yok", "ilk_kosu"))
SAGLIK_NOTLAR = frozenset((
    "atlandi",              # adım bakamadı (ör. Windows değil, git yok)
    "geride_esik_alti",     # sayfa geride ama alarm eşiğinin altında
    "geride_yeni",          # ilk gözlem, ne kadardır geride bilinmiyor
    "bosluk_aciklandi",     # koşu boşluğunun sebebi biliniyor (makine kapalı)
))

# cp1254'te KARŞILIĞI OLMAYAN ama metinlere kolayca sızan karakterler.
# NEDEN: bu modül elle de çalıştırılıyor ve bu makinede `sys.stdout.encoding`
# ANSI kod sayfası (cp1254). Bu tuzak bu depoda İKİ kez arıza üretti
# (`tiktok_publish_plan.py` caption'ı hiç basamıyordu; `≈` işareti
# `buyume_kontrol_listesi.md` başlığında DURUYOR ve doğrudan basılırsa
# UnicodeEncodeError veriyor). Türkçe harfler (ı İ ş ğ ç ö ü) ve em-dash
# cp1254'te VAR — onlar serbest.
CP1254_ESLEME = {
    "→": "->",     # →
    "←": "<-",     # ←
    "≈": "~",      # ≈
    "≤": "<=",     # ≤
    "≥": ">=",     # ≥
    "•": "-",      # •
    " ": " ",      # kırılmaz boşluk
}


def _cp1254_guvenli(metin: str) -> str:
    """Metni cp1254'e KESİN kodlanabilir hâle getirir.

    Sadece sabit metinleri elle temiz yazmak YETMEZ: rapora proje adları,
    markdown başlıkları ve istisna mesajları da giriyor — yani içerik bugün
    temiz olsa bile yarın bir emoji/ok işareti sızabilir. Bu yüzden dönüşüm
    çıktının SON adımında, tek yerde yapılıyor (unutulacak liste tuzağı).
    Eşlemede olmayan her kodlanamaz karakter "?" olur — bilgi kaybı, ama
    raporun HİÇ basılamaması/gönderilememesinden iyidir.
    """
    for kaynak, hedef in CP1254_ESLEME.items():
        metin = metin.replace(kaynak, hedef)
    return metin.encode("cp1254", "replace").decode("cp1254")


def _damga_ts(deger):
    """`"2026-09-12T06:48:56"` -> epoch saniye; bozuksa None.

    `saglik_kontrol._damga_ts` ile aynı iş — KOPYA BİLEREK: o özel bir isim
    (alt çizgiyle başlıyor), ona bağlanmak o dosya değiştiğinde bu hattı
    sessizce kırardı. Aynı gerekçe `_durum`/`_kaydet`/`_bildir` için yukarıda
    zaten yazılı. PUBLIC sabitler (ANA_PLATFORM_ANAHTARLARI vb.) ise
    kopyalanmıyor, import ediliyor — onlarda sürüklenme riski tersine.
    """
    if not isinstance(deger, str):
        return None
    try:
        return time.mktime(time.strptime(deger, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _golden_saat(saat: int) -> bool:
    try:
        import config
        araliklar = config.GOLDEN_HOURS
    except Exception:
        araliklar = GOLDEN_YEDEK
    return any(bas <= saat < bit for bas, bit in araliklar)


def _zamani_mi(d: dict, hafta: str, t: float) -> tuple:
    """(çalışsın mı, sebep) — haftada BİR kez, pazartesi sabahı.

    GECİKME TOLERANSI: makine pazartesi kapalıysa (pilde duran görevler bu
    depoda gerçek bir vaka) rapor KAYBOLMAZ — haftanın ilerleyen bir gününde
    ilk koşuda çıkar. Golden-hour kaçınması SADECE pazartesi geçerli: sonraki
    günlerde bir "tercih" uğruna raporu ertelemek, yalnızca golden-hour'da
    açık olan bir makinede raporu HİÇ göndermemek demek olurdu.
    """
    yerel = time.localtime(t)
    if d.get(HAFTALIK_ANAHTARI) == hafta:
        return False, "bu hafta gönderildi"
    if d.get(HAFTALIK_DENEME_ANAHTARI) == time.strftime("%Y-%m-%d", yerel):
        # Bildirim kanalı bugün çalışmadı. Saatlik koşuda 24 kez yeniden
        # denemek `saglik_kontrol.kontrol_et()`i de 24 kez çalıştırırdı.
        return False, "bugün denendi, gönderilemedi"
    if yerel.tm_wday == RAPOR_GUNU:
        if yerel.tm_hour < RAPOR_SAATI:
            return False, "hafta başı penceresi henüz açılmadı"
        if _golden_saat(yerel.tm_hour):
            return False, "golden-hour — sonraki koşuya bırakıldı"
    return True, ""


def _katalog_taramasi(t: float) -> dict:
    """Kataloğu TEK geçişte tarar: son 7 günün yayınları + bekleyenler + izlenme.

    Kök listesi ELLE SAYILMIYOR (`uyumluluk.proje_klasorleri()`), platform
    listesi ELLE YAZILMIYOR (`_uploaded_at` soneki) — ikisi de bu depoda
    tekrarlanmış hatalar (bkz. tests/test_kok_listesi_muhafizi.py ve
    `saglik_kontrol.YAYIN_DAMGA_SONEKI` notu). Sabitler saglik_kontrol'den
    IMPORT ediliyor: `ANA_PLATFORM_ANAHTARLARI` ile
    `auto_process._is_fully_done()`in dörtlüsünün aynı kalması zaten bir
    testle kilitli, üçüncü bir kopya o kilidin dışında kalırdı.
    """
    import uyumluluk
    from saglik_kontrol import (ANA_PLATFORM_ANAHTARLARI, SES_DOSYALARI,
                                YAYIN_DAMGA_SONEKI)

    yayin = {}          # platform -> son 7 gündeki gönderi sayısı
    yayin_gun = {}      # platform -> gönderi yapılan günler (tavan tahmini)
    bekleyen = {}       # ana platform anahtarı -> eksik proje sayısı
    proje = 0
    izlenme = 0

    for yol in uyumluluk.proje_klasorleri():
        if not any(os.path.isfile(os.path.join(yol, a)) for a in SES_DOSYALARI):
            continue                      # proje değil (bkz. SES_DOSYALARI)
        proje += 1
        state = _load_state(yol)
        izlenme += _sayi(state, "youtube_views", "youtube_shorts_views")
        for anahtar in ANA_PLATFORM_ANAHTARLARI:
            if not state.get(anahtar):
                bekleyen[anahtar] = bekleyen.get(anahtar, 0) + 1
        for anahtar, deger in state.items():
            if not anahtar.endswith(YAYIN_DAMGA_SONEKI):
                continue
            ts = _damga_ts(deger)
            if ts is None or not (t - PENCERE_SN) <= ts <= (t + 3600):
                continue
            ad = anahtar[:-len(YAYIN_DAMGA_SONEKI)]
            yayin[ad] = yayin.get(ad, 0) + 1
            yayin_gun.setdefault(ad, set()).add(str(deger)[:10])

    return {"yayin": yayin, "yayin_gun": yayin_gun, "bekleyen": bekleyen,
            "proje": proje, "izlenme": izlenme}


def _dolu_gunler(yayin_gun: dict, bayrak: str) -> set:
    """Bu platforma son 7 günde gönderi yapılan günler (tüm varyantlar).

    Telegram'da ana katalog `telegram_uploaded_at`, DJ/derleme kökleri
    `telegram_shorts_uploaded_at` yazıyor — günlük tavan İKİSİNİ BİRDEN
    sayıyor (`ek_platform_backfill._damga_anahtarlari`), yani tahmin de
    saymalı. Ön-ek kuralı yarın eklenecek varyantı da kapsıyor.
    """
    gunler = set()
    for ad, kume in yayin_gun.items():
        if ad == bayrak or ad.startswith(bayrak + "_"):
            gunler |= kume
    return gunler


def _kuyruk_satiri(ad: str, kalan: int, tavan: int, dolu_gun: set) -> str:
    """Bir geri doldurma kuyruğunun kalan süresi — ÖLÇÜLMÜŞ tempoya göre.

    TAVANLAR ANA HATTIN GÖNDERİLERİNİ DE SAYIYOR (`bugun_yuklenen` docstring'i:
    "geri doldurma pratikte YALNIZCA YAYINSIZ günlerde ilerler"). Bu yüzden
    kapasite "tavan x 7" DEĞİL, "tavan x (o platforma gönderi YAPILMAYAN gün
    sayısı)". Son 7 gün ölçülüyor, çünkü tempoyu belirleyen şey kataloğun o
    haftaki yayın yoğunluğu — sabit bir varsayım her hafta yanlış olurdu.
    """
    if kalan <= 0:
        return "%s: kuyruk boş" % ad
    kapasite = max(0, 7 - len(dolu_gun)) * max(0, tavan)
    if kapasite <= 0:
        return "%s: %d bekliyor - tavan her gün dolu, kuyruk ilerlemiyor" % (ad, kalan)
    hafta = kalan / float(kapasite)
    return "%s: %d bekliyor (~%.0f hafta)" % (ad, kalan, hafta) if hafta >= 1 \
        else "%s: %d bekliyor (bu hafta biter)" % (ad, kalan)


def _geri_doldurma_satirlari(yayin_gun: dict) -> list:
    satirlar = []
    try:
        import ek_platform_backfill as ek
        for platform in ek.PLATFORMLAR:
            bayrak, ad = platform[0], platform[1]
            satirlar.append(_kuyruk_satiri(ad, len(ek.adaylar(platform)),
                                           ek.GUNLUK_TAVAN,
                                           _dolu_gunler(yayin_gun, bayrak)))
    except Exception as e:
        satirlar.append("Telegram/Bluesky kuyruğu OKUNAMADI (%s)" % str(e)[:60])
    try:
        import facebook_backfill as fb
        satirlar.append(_kuyruk_satiri("Facebook", len(fb.eksik_projeler()),
                                       fb.GUNLUK_TAVAN,
                                       _dolu_gunler(yayin_gun, "facebook")))
    except Exception as e:
        satirlar.append("Facebook kuyruğu OKUNAMADI (%s)" % str(e)[:60])
    return satirlar


def _saglik_satiri(saglik_fn=None) -> str:
    """Yedi adımın o haftaki durumu — kaç uyarı, hangileri.

    `saglik_kontrol.kontrol_et()` YENİDEN çağrılıyor (sonucu saklayan bir yer
    yok ve `auto_process._saglik_kontrol()` dönüş değerini atıyor). Maliyeti
    haftada bir: 2 Netlify GET + iki kısa yerel alt süreç. YouTube kotasına
    DOKUNMUYOR. Log'u susturuluyor — aynı satırlar saniyeler önce saatlik
    kancadan zaten düştü.
    """
    try:
        if saglik_fn is None:
            import saglik_kontrol
            saglik_fn = saglik_kontrol.kontrol_et
        # STDOUT DA SUSTURULUYOR: adımların log'u `log` parametresinden
        # geçiyor ama `netlify_kontrol.main()` doğrudan `print` ediyor —
        # elle koşuda (`--haftalik`) o çıktı raporun önüne geçiyordu.
        yutucu = io.StringIO()
        with contextlib.redirect_stdout(yutucu):
            sonuc = saglik_fn(lambda *a, **k: None) or {}
    except Exception as e:
        return "SAĞLIK: kontrol çalıştırılamadı (%s)" % str(e)[:80]
    if not sonuc:
        return "SAĞLIK: kontrol boş döndü — adımlar çalışmamış olabilir"
    uyarilar, notlar = [], []
    for ad, s in sorted(sonuc.items()):
        durum = str((s or {}).get("durum", "?"))
        if durum in SAGLIK_TEMIZ:
            continue
        (notlar if durum in SAGLIK_NOTLAR else uyarilar).append("%s(%s)" % (ad, durum))
    if not uyarilar and not notlar:
        return "SAĞLIK: %d adımın hepsi temiz" % len(sonuc)
    parca = ["SAĞLIK: %d adım" % len(sonuc)]
    if uyarilar:
        parca.append("%d uyarı: %s" % (len(uyarilar), ", ".join(uyarilar)))
    if notlar:
        parca.append("%d not: %s" % (len(notlar), ", ".join(notlar)))
    return " - ".join(parca)


def _olcum_satiri(d: dict, izlenme: int) -> tuple:
    """(satır, yeni anlık görüntü) — izlenme ve izlenme süresi DEĞİŞİMİ.

    İki kaynak da HAZIR veriden okunuyor, hiçbiri yeniden hesaplanmıyor:
      * izlenme -> `state.json` (günde bir `youtube_stats` tazeliyor),
      * izlenme süresi -> `izlenme_raporu()`nun AYNI koşuda bıraktığı özet.
    Değişim için geçen haftanın anlık görüntüsü `saglik_durum.json`'da duruyor;
    ilk haftada temel çizgi yok, bu açıkça yazılıyor (sessizce "0 değişim"
    demek yanlış bilgi olurdu).
    """
    ozet = d.get(IZLENME_OZET_ANAHTARI) or {}
    dakika = 0
    video = 0
    if isinstance(ozet, dict):
        for o in ozet.values():
            if isinstance(o, dict):
                try:
                    dakika += int(o.get("dakika") or 0)
                    video += int(o.get("video") or 0)
                except (TypeError, ValueError):
                    pass
    yeni = {"izlenme": izlenme, "dakika": dakika, "video": video}

    ek = ""
    if not ozet:
        # İzlenme SÜRESİ hiç yazılmamış: ya Analytics izni yok ya da haftalık
        # izlenme raporu henüz hiç çalışmadı. Sessizce "0 dk" göstermek tam da
        # bu deponun düzeltmeye çalıştığı sessiz arıza olurdu.
        ek = " [izlenme süresi kaydı YOK - izlenme raporu çalışmamış olabilir]"

    onceki = d.get(HAFTALIK_OLCUM_ANAHTARI)
    if not isinstance(onceki, dict):
        return ("ÖLÇÜM: izlenme %d, izlenme süresi %d dk (ilk hafta - temel "
                "çizgi kaydedildi)%s" % (izlenme, dakika, ek)), yeni

    def _fark(simdi, ad):
        try:
            eski = int(onceki.get(ad) or 0)
        except (TypeError, ValueError):
            return "?"
        return "%+d" % (simdi - eski)

    return ("ÖLÇÜM: izlenme %d (%s), izlenme süresi %d dk (%s)%s"
            % (izlenme, _fark(izlenme, "izlenme"), dakika,
               _fark(dakika, "dakika"), ek)), yeni


_TARIH_RE = re.compile(r"(20\d\d-\d\d-\d\d)")


def _basligi_temizle(satir: str, tarih: str) -> str:
    s = satir.lstrip("#").strip()
    s = s.replace("**", "").replace("`", "")
    s = s.replace(tarih, " ")
    s = re.sub(r"[≈~]\s*", "", s)          # "son tarih ≈2026-12-09"
    s = re.sub(r"\s*[—-]\s*([:,])\s*", r"\1 ", s)
    s = re.sub(r"\s+([,:;])", r"\1", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" —-:,;.")
    return s if len(s) <= 58 else s[:55].rstrip() + "..."


def _tarihli_isler(t: float) -> list:
    """Tarihli işler — `buyume_kontrol_listesi.md` + `CLAUDE.md` BAŞLIKLARINDAN.

    Tarihler KODA GÖMÜLMÜYOR: o dosyalar zaten bu işlerin tek kaynağı ve
    kullanıcı tarih değiştirdiğinde kodu güncellemesi gerekmemeli. Dosyalar
    okunamazsa TARIHLI_YEDEK devreye giriyor ve rapor bunu AÇIKÇA yazıyor.
    """
    bulunan = []
    for ad in TARIH_KAYNAKLARI:
        yol = os.path.join(REPO, ad)
        try:
            with open(yol, "r", encoding="utf-8") as f:
                for satir in f:
                    s = satir.strip()
                    if not s.startswith("#"):
                        continue
                    m = _TARIH_RE.search(s)
                    if m:
                        bulunan.append((m.group(1), _basligi_temizle(s, m.group(1))))
        except OSError:
            continue
    yedek = not bulunan
    if yedek:
        bulunan = list(TARIHLI_YEDEK)

    bugun = datetime.date.fromtimestamp(t)
    satirlar = []
    for tarih, etiket in sorted(set(bulunan)):
        try:
            g = datetime.date(*[int(p) for p in tarih.split("-")])
        except ValueError:
            continue
        kalan = (g - bugun).days
        if kalan < -30:
            continue            # çoktan geçmiş ve kapanmış işler raporu şişirir
        durum = ("GEÇTİ, %d gün" % -kalan) if kalan < 0 else ("%d gün" % kalan)
        satirlar.append("  %s (%s) %s" % (tarih, durum, etiket))
    satirlar = satirlar[:TARIHLI_TAVAN]
    if yedek:
        satirlar.append("  (YEDEK LİSTE - markdown dosyaları okunamadı)")
    return satirlar or ["  (tarihli iş bulunamadı)"]


def _haftalik_satirlar(t: float, d: dict, saglik_fn=None) -> tuple:
    """(rapor satırları, yeni ölçüm anlık görüntüsü).

    HER BÖLÜM KENDİ İÇİNDE KORUNUYOR: bir bölüm patlarsa raporun TAMAMI
    kaybolmasın, o satırın yerinde GÖRÜNÜR bir hata dursun. Sessizce eksik
    bir rapor, bu deponun tam da düzeltmeye çalıştığı arıza sınıfı.
    """
    hafta = _hafta(t)
    satirlar = ["HAFTALIK ÖZET %s (%s)" % (hafta, time.strftime("%d.%m", time.localtime(t)))]
    olcum = {}

    try:
        tarama = _katalog_taramasi(t)
    except Exception as e:
        satirlar.append("YAYIN/BEKLEYEN: katalog taranamadı (%s)" % str(e)[:80])
        tarama = None

    if tarama is not None:
        yayin = tarama["yayin"]
        toplam = sum(yayin.values())
        satirlar.append("YAYIN (son 7 gün): %d gönderi" % toplam)
        if yayin:
            satirlar.append("  " + ", ".join(
                "%s %d" % (ad, sayi) for ad, sayi in sorted(yayin.items())))
        bekleyen = tarama["bekleyen"]
        satirlar.append("BEKLEYEN (%d proje): %s" % (
            tarama["proje"],
            ", ".join("%s %d" % (a.replace("_video_id", "").replace("_publish_id", "")
                                 .replace("_media_id", ""), s)
                      for a, s in sorted(bekleyen.items())) or "ana hat temiz"))
        for satir in _geri_doldurma_satirlari(tarama["yayin_gun"]):
            satirlar.append("  " + satir)
        try:
            olcum_satiri, olcum = _olcum_satiri(d, tarama["izlenme"])
            satirlar.append(olcum_satiri)
        except Exception as e:
            satirlar.append("ÖLÇÜM: hesaplanamadı (%s)" % str(e)[:80])

    satirlar.append(_saglik_satiri(saglik_fn))

    satirlar.append("SENİN İŞİN:")
    try:
        satirlar.extend(_tarihli_isler(t))
    except Exception as e:
        satirlar.append("  (tarihli işler okunamadı: %s)" % str(e)[:60])
    return satirlar, olcum


def haftalik_gozden_gecirme(log=print, zorla: bool = False,
                            durum_dosyasi: str | None = None,
                            gonder: bool = True, simdi: float | None = None,
                            saglik_fn=None) -> dict:
    """HAFTADA BİR "ne oldu / ne bekliyor / ne yapmalıyım" özeti.

    Saatlik `auto_process` koşusundan çağrılır; haftanın geri kalanında
    HİÇBİR ŞEY yapmaz (ilk satırdaki damga kontrolü). Hiçbir hata otomasyonu
    durdurmaz.
    """
    yol = durum_dosyasi or DURUM_DOSYASI
    t = simdi if simdi is not None else time.time()
    hafta = _hafta(t)
    bugun = time.strftime("%Y-%m-%d", time.localtime(t))
    d = _durum(yol)

    if not zorla:
        calis, sebep = _zamani_mi(d, hafta, t)
        if not calis:
            return {"durum": "atlandi", "neden": sebep, "hafta": hafta}

    try:
        satirlar, olcum = _haftalik_satirlar(t, d, saglik_fn)
        metin = _cp1254_guvenli("\n".join(satirlar))
    except Exception as e:
        # SESSİZ ARIZA KORUMASI (CLAUDE.md, üçüncü soru): rapor üretilemezse
        # bu GÖRÜNÜR olmalı. Damga GÜNLÜK — hata sürerse her gün bir kez
        # hatırlatır, saatte bir değil.
        mesaj = "Haftalık özet üretilemedi: %s" % str(e)[:150]
        log("  " + _cp1254_guvenli(mesaj))
        gonderildi = _bildir("Haftalık özet üretilemedi", _cp1254_guvenli(mesaj),
                             HAFTALIK_HATA_ANAHTARI, bugun, yol)
        return {"durum": "hata", "hata": str(e)[:150], "bildirim": gonderildi}

    for satir in metin.split("\n"):
        log(satir)
    if not gonder:
        return {"durum": "uretildi", "hafta": hafta, "metin": metin}

    if _bildir("Haftalık özet %s" % hafta, metin, HAFTALIK_ANAHTARI, hafta, yol):
        # Anlık görüntü SADECE gönderim başarılıysa yenileniyor: yoksa
        # gönderilemeyen bir hafta temel çizgiyi kaydırır ve bir sonraki
        # haftanın "değişim" sayısı sessizce yanlış olurdu.
        _kaydet({HAFTALIK_OLCUM_ANAHTARI: olcum, HAFTALIK_DENEME_ANAHTARI: ""}, yol)
        return {"durum": "tamam", "hafta": hafta, "metin": metin}

    log("  Haftalık özet gönderilemedi (bildirim kanalı) — yarın tekrar denenecek.")
    _kaydet({HAFTALIK_DENEME_ANAHTARI: bugun}, yol)
    return {"durum": "gonderilemedi", "hafta": hafta, "metin": metin}


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Katalogun YouTube istatistiklerini tazeleyip özet tablo basar."
    )
    parser.add_argument(
        "--base", default=None,
        help=("Tek bir kök dizin (örn. projects). Verilmezse youtube_stats.KOKLER "
              "— projects + dj_sets + derlemeler — birlikte taranır."),
    )
    parser.add_argument("--izlenme", action="store_true",
                        help="Sadece izlenme süresi raporunu bas (damgayı yok sayar).")
    parser.add_argument("--haftalik", action="store_true",
                        help=("Haftalık gözden geçirme özetini bas (damgayı yok "
                              "sayar, BİLDİRİM GÖNDERMEZ)."))
    args = parser.parse_args()

    if args.haftalik:
        # gonder=False: elle koşu telefonu çaldırmasın ve hafta damgasını
        # yakmasın — otomatik rapor bu yüzden atlanırdı.
        sonuc = haftalik_gozden_gecirme(zorla=True, gonder=False)
        if sonuc.get("durum") == "hata":
            print("Haftalık özet üretilemedi: %s" % sonuc.get("hata"))
        return

    if args.izlenme:
        sonuc = izlenme_raporu(zorla=True)
        if sonuc.get("durum") == "token_yok":
            print("Analytics izni yok. Çalıştır: " + AUTH_KOMUTU)
        return

    _check_instagram_token_expiry()

    kokler = [os.path.abspath(args.base)] if args.base else list(KOKLER)

    # TEK istek: eskiden her proje için ayrı get_stats() çağrılıyordu
    # (18 proje = 18 istek) ve Shorts hiç ölçülmüyordu. get_stats_batch
    # videos.list'in 50 id sınırını kullanıyor: 18 uzun + 18 Shorts = 1 istek.
    # force=True — haftalık rapor ELLE isteniyor, günlük tazeleme aralığını bekleme.
    try:
        sonuc = get_stats_batch(kokler[0] if args.base else None, force=True)
        if sonuc.get("istek"):
            print("Tazelendi: %d video, %d proje (%d istek)"
                  % (sonuc.get("video", 0), sonuc.get("proje", 0), sonuc["istek"]))
    except Exception as e:
        print("İstatistik tazelenemedi (%s) — kayıtlı son değerlerle devam ediliyor."
              % str(e)[:150])

    rows = []
    for kok in kokler:
        if not os.path.isdir(kok):
            continue
        for name in sorted(os.listdir(kok)):
            project_dir = os.path.join(kok, name)
            if not os.path.isdir(project_dir):
                continue
            state = _load_state(project_dir)
            # Shorts'u da kabul et: bir proje uzun formata hiç yüklenmemiş ama
            # Shorts'a yüklenmiş olabilir — eski sürüm bunları tabloda hiç
            # göstermiyordu.
            if not (state.get("youtube_video_id") or state.get("youtube_shorts_video_id")):
                continue
            rows.append((
                name,
                _kok_adi(kok),
                _sayi(state, "youtube_views"),
                _sayi(state, "youtube_shorts_views"),
                _sayi(state, "youtube_likes", "youtube_shorts_likes"),
                _sayi(state, "youtube_comments", "youtube_shorts_comments"),
                state.get("youtube_privacy", "?"),
            ))

    if not rows:
        print("Henüz YouTube'a yüklenmiş proje yok.")
        return

    rows.sort(key=lambda r: r[2] + r[3], reverse=True)
    name_w = max(max(len(r[0]) for r in rows), 5) + 2
    kok_w = max(max(len(r[1]) for r in rows), 3) + 2
    cizgi = "-" * (name_w + kok_w + 46)
    print(f"{'Şarkı'.ljust(name_w)}{'Kök'.ljust(kok_w)}"
          f"{'İzlenme':>10}{'Shorts':>9}{'Beğeni':>9}{'Yorum':>8}  Görünürlük")
    print("(Beğeni/Yorum = uzun format + Shorts toplamı)")
    print(cizgi)
    t_uzun = t_short = t_like = t_yorum = 0
    for name, kok, views, shorts, likes, comments, privacy in rows:
        print(f"{name.ljust(name_w)}{kok.ljust(kok_w)}"
              f"{views:>10}{shorts:>9}{likes:>9}{comments:>8}  {privacy}")
        t_uzun += views
        t_short += shorts
        t_like += likes
        t_yorum += comments
    print(cizgi)
    print(f"{'Toplam'.ljust(name_w)}{''.ljust(kok_w)}"
          f"{t_uzun:>10}{t_short:>9}{t_like:>9}{t_yorum:>8}")
    print(f"Genel izlenme (uzun + Shorts): {t_uzun + t_short}")

    _watch_time_ozeti()


if __name__ == "__main__":
    main()
