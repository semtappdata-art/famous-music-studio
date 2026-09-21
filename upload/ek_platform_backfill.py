# -*- coding: utf-8 -*-
"""Telegram ve Bluesky'ya hiç gitmemiş katalog şarkılarını geri doldurur.

NEDEN VAR — sessiz arıza, 2026-09-11'de bulundu:

`auto_process._is_fully_done()` yalnızca dört anahtarı sayıyor:
`youtube_video_id`, `youtube_shorts_video_id`, `tiktok_publish_id`,
`instagram_media_id`. Bu dördü dolan proje `pending` listesinden KALICI olarak
düşüyor. `_ek_platformlari_isle()` ise yalnızca `process_project()` içinden
çağrılıyor — yani listeden düşen proje Telegram/Bluesky'yı BİR DAHA hiç
görmüyor.

Sonuç (disk kanıtı, 18 katalog şarkısı): YouTube 18, Shorts 18, TikTok 17,
Instagram 14 — ama **Telegram 1, Bluesky 1**. 14 şarkı kalıcı olarak dışlanmış
ve log'a tek satır bile düşmemiş.

Facebook'un bu boşluk için ayrı bir geri doldurma modülü vardı
(`facebook_backfill.py`); Telegram ve Bluesky'da yoktu. Bu modül onun
karşılığı.

`_is_fully_done()`'a bu platformları EKLEMEK yanlış çözüm olurdu: bayrak
kapalıyken tüm katalog sonsuza kadar "bekliyor" görünürdü — facebook_backfill
de aynı gerekçeyle ayrı bir adım.

KAPSAM — ÜÇ İÇERİK KÖKÜ (2026-09-11'de düzeltildi):
`BASE` yalnızca `projects/` idi; bir DJ setinin ya da derlemenin Telegram/
Bluesky yüklemesi yarım kalırsa HİÇBİR süpürge onu tamamlamıyordu. Artık
`uyumluluk.KOKLER`. Genişletme iki AYRI tuzak ortaya çıkardı, ikisi de diskte
doğrulandı ve ikisi de burada kapatıldı:

  1. **Telegram'da DJ/derleme kökleri FARKLI bir dosya ve FARKLI bir state
     anahtarı kullanıyor.** `dj_famous_process._EK_PLATFORMLAR` Telegram'ı
     `kind="dikey"` ile çağırıyor (`telegram_shorts_message_id`), çünkü bir set
     41-81 dakika: `output/youtube_16x9.mp4` City Pulse Set'te 540 MB, Gece
     Seansı Vol. 1'de 254 MB — Telegram bot API'sinin 50 MB sınırının KAT KAT
     üstünde. Varsayılan ("uzun") tanımla genişletilseydi bu üç set/derleme
     "Telegram'a hiç gitmemiş" görünür (oysa dikey sürüm GİTMİŞ), her koşuda
     `_ensure_size_ok` hatası alır ve GÜNLÜK TEK SLOTU kalıcı olarak işgal edip
     asıl eksik şarkıları da bloke ederdi. Çözüm: kök başına SAPMA
     (`TELEGRAM_DJ_SAPMASI`), dj_famous_process'teki tablonun birebir karşılığı.
  2. **Boyut ön koşulu.** Yukarıdaki sapma bugünkü vakayı çözüyor ama koruma
     dosya boyutunun KENDİSİNE de bağlandı (`MAKS_BAYT`): hiçbir zaman
     yüklenemeyecek bir aday, kuyruğun başında sonsuza kadar oturan ve her gün
     tek slotu yakan bir tıkaç demektir.

Kapsam genişlemesi GÜNLÜK TAVANLARI GEVŞETMİYOR, tersine sıkıyor:
`bugun_yuklenen()` de artık üç kökü sayıyor, yani o gün normal hattan çıkmış
bir setin Telegram/Bluesky paylaşımı da tavanı dolduruyor (eskiden sayaç
`projects/` dışını görmüyordu — `bluesky_upload._todays_upload_count`'un
düzeltilen hatasının birebir aynısı). Bu yüzden GUNLUK_TAVAN = 1'de KALDI.

TEMPO — İKİ KAPI (facebook_backfill ile birebir aynı desen):
  1. Golden-hour kapısı: pencere dışında hiçbir şey yapılmaz.
  2. GÜNLÜK tavan: `bugun_yuklenen()` state'teki `*_uploaded_at` damgalarından
     BUGÜN atılan gönderileri sayar.
Bu modülün ilk sürümünde SADECE (1) vardı ve tek kapı olarak kullanılmıştı.
Golden-hour günde 6 saat (`config.GOLDEN_HOURS`), auto_process saatlik
tetikleniyor — yani koşu başına 1 gönderi sınırı GÜNDE 6 Telegram + 6 Bluesky
gönderisi demekti ve 14 eksik şarkı ~1,2 günde boşalıyordu. Tam olarak bu
modülün engellemek için yazıldığı şey ("spam'e döner, toplu üretim sinyali
verir"). facebook_backfill bu tuzağı docstring'inde anlatıp `bugun_yuklenen()`
ile çözmüştü; burada yorum kopyalanmış ama koruma UYGULANMAMIŞTI.

TEK YOL + YENİ ŞARKI ÖNCE (2026-09-13): ana hat (`auto_process._ek_platformlari_isle`)
Telegram/Bluesky'ı artık GÖNDERMİYOR — orada golden-hour, gizlilik ve tavan
kapısı yoktu, pencere dışında işlenen yeni şarkı YouTube private + `publishAt`
iken linkiyle düşüyordu. Bedeli: yeni şarkı bu kuyruğa girdi ve eskiden yeniye
sıralansaydı 16+ günlük eksik kuyruğunun ARKASINDA kalırdı. Bu yüzden `adaylar()`
public anı son `YENI_PUBLIC_PENCERESI_SN` içinde olanları ÖNE alıyor ve
`_public_ani()` public olmamış (zamanlanmış / gerçekte gizli) projeyi aday
listesinden çıkarıyor.
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

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import config
import uyumluluk
from ag_yeniden_deneme import belirsiz_mi

# ÜÇ içerik kökü. Adı `BASE` (tekil) kaldı ama artık bir kök DEMETİ:
# `uyumluluk.proje_klasorleri()` hem tek yol (str) hem demet kabul ediyor ve
# mevcut testler bu adı tek bir klasöre monkeypatch'liyor — ikisi de çalışsın.
# Kök listesi burada ELLE SAYILMIYOR: tek kanonik kaynak uyumluluk.KOKLER
# (muhafız: tests/test_kok_listesi_muhafizi.py).
BASE = uyumluluk.KOKLER

# Koşu başına kaç gönderi (tek bir auto_process çalıştırmasında).
KOSU_TAVANI = 1

# GÜN başına kaç gönderi (platform başına). ASIL koruma bu — KOSU_TAVANI tek
# başına hiçbir şeyi sınırlamıyor, çünkü saatlik koşu golden-hour boyunca 6 kez
# tetikleniyor. facebook_backfill'de GUNLUK_TAVAN=2; burada iki platform var ve
# ikisi de aynı takipçi kitlesine gidiyor, bu yüzden platform başına 1 seçildi
# (günde toplam 2 gönderi = Facebook'un hacmiyle aynı).
GUNLUK_TAVAN = 1

# Telegram Bot API dosya sınırı (telegram_upload.MAX_FILE_BYTES'in aynası —
# oraya import etmek `requests`i bu süpürgeye zorunlu bağımlılık yapardı).
# NEDEN ÖN KOŞUL: yüklenemeyecek bir aday listenin başında kalır ve günlük TEK
# slotu her gün yeniden yakar; hata log'a düşer ama kuyruk hiç ilerlemez.
TELEGRAM_MAKS_BAYT = 50 * 1024 * 1024

# Kök başına SAPMA: bu köklerde platformun kullandığı dosya/anahtar farklı.
# `dj_famous_process._EK_PLATFORMLAR`'ın karşılığı — orada da Telegram
# `kind="dikey"` ile çağrılıyor (gerekçe: modül docstring'i, madde 1).
TELEGRAM_DJ_SAPMASI = {
    "kokler": ("dj_sets", "derlemeler"),
    "anahtar": "telegram_shorts_message_id",
    "damga": "telegram_shorts_uploaded_at",
    "gerekli_video": os.path.join("output", "shorts_9x16.mp4"),
    "ek": {"kind": "dikey"},
}

# (bayrak, ad, state anahtarı, damga anahtarı, gerekli video, kimlik dosyası,
#  modül, fonksiyon, ek kwargs, maks bayt, kök sapmaları)
# İlk dokuz alan VARSAYILAN (ana katalog) varyantı; sapmalar en sonda —
# alanların SIRASI test_ek_platform_backfill.py tarafından indeksle
# okunuyor, yeni alanlar bu yüzden SONA ekleniyor.
# Facebook BİLEREK yok — kendi modülü var (facebook_backfill.py).
#
# "gerekli video" ALANI NEDEN VAR: ön koşul ile gerçekten yüklenen dosya
# birbirinden ayrılmıştı. Eskiden her iki platform için de
# `output/shorts_9x16.mp4` varlığına bakılıyordu, ama Telegram boş kwargs ile
# çağrılıyor -> `telegram_upload.upload_video` varsayılanı `kind="uzun"` ->
# aslında `output/youtube_16x9.mp4` yükleniyor. Sadece shorts'u olan bir
# projede FileNotFoundError. ANA KATALOĞUN boyut tarafı temiz (en büyük 16x9
# 21,1 MB, Telegram bot sınırı 50 MB), yani `projects/` için "uzun" seçimi
# doğru. DJ setleri/derlemeler için DEĞİL (o dosyalar 130-540 MB) — onlar
# TELEGRAM_DJ_SAPMASI ile dikey sürüme yönlendiriliyor, üstelik boyut da
# ön koşulun parçası (TELEGRAM_MAKS_BAYT).
PLATFORMLAR = [
    ("telegram", "Telegram", "telegram_message_id", "telegram_uploaded_at",
     os.path.join("output", "youtube_16x9.mp4"),
     "telegram_client_secrets.json", "telegram_upload", "upload_video", {},
     TELEGRAM_MAKS_BAYT, (TELEGRAM_DJ_SAPMASI,)),
    # Bluesky'da sapma YOK: üç kökte de `shorts_9x16.mp4` + `bluesky_post_uri`
    # kullanılıyor (dj_famous_process de ek argümansız çağırıyor). Boyut sınırı
    # da yok: dikey kesitler 2-5 MB ve asıl sınır SÜRE (bkz.
    # bluesky_upload.MAX_VIDEO_SECONDS), o da yükleyicinin kendi kontrolü.
    ("bluesky", "Bluesky", "bluesky_post_uri", "bluesky_uploaded_at",
     os.path.join("output", "shorts_9x16.mp4"),
     "bluesky_client_secrets.json", "bluesky_upload", "upload_video", {},
     None, ()),
]


def _varyantlar(platform: tuple) -> list:
    """Platform tanımını KÖK BAŞINA varyantlara açar.

    Her kök için ya varsayılan alanlar ya da o kökü kapsayan sapma geçerli.
    Kök EŞLEŞMESİ klasör ADIYLA yapılıyor (tam yolla değil): `BASE` testlerde
    geçici bir klasöre monkeypatch'leniyor, orada da "projects" adı korunuyor.
    """
    (_bayrak, _ad, anahtar, damga, gerekli_video, _kimlik, _modul, _fonksiyon,
     ek, maks_bayt, sapmalar) = platform
    kokler = (BASE,) if isinstance(BASE, str) else tuple(BASE)
    gruplar = []
    for kok in kokler:
        kok_adi = os.path.basename(os.path.normpath(kok))
        secilen = None
        for sapma in sapmalar:
            if kok_adi in sapma["kokler"]:
                secilen = sapma
                break
        v = {
            "anahtar": (secilen or {}).get("anahtar", anahtar),
            "damga": (secilen or {}).get("damga", damga),
            "gerekli_video": (secilen or {}).get("gerekli_video", gerekli_video),
            "ek": (secilen or {}).get("ek", ek),
            "maks_bayt": (secilen or {}).get("maks_bayt", maks_bayt),
        }
        for g in gruplar:
            if all(g[k] == v[k] for k in ("anahtar", "damga", "gerekli_video")):
                g["kokler"].append(kok)
                break
        else:
            v["kokler"] = [kok]
            gruplar.append(v)
    return gruplar


def _damga_anahtarlari(platform: tuple) -> tuple:
    """Bu platformun BÜTÜN damga anahtarları — günlük tavan hepsini saymalı.

    Telegram'da ana katalog `telegram_uploaded_at`, DJ/derleme kökleri
    `telegram_shorts_uploaded_at` yazıyor. Tek anahtar sayılsaydı tavan yine
    eksik sayardı — düzeltilmek istenen hatanın ta kendisi.
    """
    return tuple(dict.fromkeys(v["damga"] for v in _varyantlar(platform)))


def _durum(klasor: str) -> dict:
    try:
        with open(os.path.join(klasor, "state.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


# Geri doldurmada "YENİ şarkı" sayılan pencere: public anı bu kadar yakınsa
# aday listesinin ÖNÜNE geçer (2026-09-13). 7 gün = haftada 3 şarkılık tempoda
# en fazla ~3 şarkı; günlük tavan 1 olduğu için hepsi birkaç günde erir ve eski
# eksik kuyruğu tamamen durmaz.
YENI_PUBLIC_PENCERESI_SN = 7 * 24 * 3600

# `auto_process.TEMPO_DISI_PUBLIC_ANI_ALANI`'nın aynası (auto_process'i import
# etmek süpürgeye ağır bir bağımlılık olurdu); eşitlik testle kilitli.
TEMPO_DISI_PUBLIC_ANI_ALANI = "youtube_public_ani_tempo_disi"


def _utc_ts(deger):
    """`"2026-09-05T06:30:00Z"` (youtube_upload._compute_publish_at) -> epoch."""
    if not isinstance(deger, str) or not deger:
        return None
    from datetime import datetime
    try:
        an = datetime.fromisoformat(deger.replace("Z", "+00:00"))
    except ValueError:
        return None
    return an.timestamp() if an.tzinfo is not None else None


def _yerel_ts(deger):
    """`"2026-09-12T06:48:56"` (yerel saat damgası) -> epoch; bozuksa None."""
    if not isinstance(deger, str):
        return None
    try:
        return time.mktime(time.strptime(deger, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _public_ani(st: dict, simdi: float = None):
    """Uzun formatın GERÇEK public anı (epoch) — ya da bugün public DEĞİLSE None.

    TÜRETME: max(`youtube_uploaded_at`, `youtube_publish_at`,
    `youtube_public_ani_tempo_disi`). Gerekçe: zamanlamasız yüklenen video
    yüklendiği an public olur (`youtube_publish_at` None); zamanlanmış video
    `publishAt` anında; önceden yayınlanmış bir videoyu sonradan public'e alan
    görünürlük planı o anı `youtube_publish_at`'e (ya da `tempo_sayilir: False`
    ise tempo dışı alana) yazar. Hepsi "public'e geçiş" anı olduğu için EN GEÇ
    olanı gerçek andır. Damga yoksa/okunamazsa 0.0 (= eski; aday kalır, önü
    almaz) — `auto_process._son_yeni_yayin_ani` ile aynı hoşgörü.

    None (aday DEĞİL) dönen durumlar:
      * publish anı GELECEKTE -> YouTube'da private + `publishAt` bekliyor;
        linki paylaşmak izleyiciyi "video yok" sayfasına götürür;
      * `youtube_privacy_gercek` (youtube_stats'ın API ölçümü) public DEĞİL —
        state "public" dese de YouTube'da gizli (Bu Gece Kazandık vakası).
        TEK İSTİSNA bayat zamanlama ölçümü: ölçüm `private` ve publishAt
        ÖLÇÜMDEN SONRA ve şimdiden önce -> ölçüm yayından önce alınmış, video
        o arada public oldu (saglik_kontrol'ün gizlilik kayması adımıyla aynı
        kural). Ölçüm damgası yoksa istisna UYGULANMAZ: "bilmiyorum" gönderme
        gerekçesi değil.
    `youtube_privacy in (unlisted, private)` kapısı `eksik_projeler`de AYRICA
    duruyor (elle ayarın aynası; iki bağımsız kapı bilinçli).
    """
    simdi = time.time() if simdi is None else simdi
    anlar = []
    yukleme = _yerel_ts(st.get("youtube_uploaded_at"))
    if yukleme is not None:
        anlar.append(yukleme)
    for anahtar in ("youtube_publish_at", TEMPO_DISI_PUBLIC_ANI_ALANI):
        t = _utc_ts(st.get(anahtar))
        if t is None:
            continue
        if t > simdi:
            return None                   # publishAt bekliyor
        anlar.append(t)
    gercek = st.get("youtube_privacy_gercek")
    if gercek and gercek != "public":
        olcum = _yerel_ts(st.get("youtube_privacy_gercek_at"))
        yayin = _utc_ts(st.get("youtube_publish_at"))
        bayat_zamanlama_olcumu = (gercek == "private" and yayin is not None
                                  and olcum is not None and olcum < yayin <= simdi)
        if not bayat_zamanlama_olcumu:
            return None
    return max(anlar) if anlar else 0.0


def eksik_projeler(durum_anahtari: str, gerekli_video: str,
                   maks_bayt: int = None, kokler=None) -> list:
    """YouTube'da yayında ama bu platforma hiç gitmemiş projeler, ESKİDEN YENİYE.

    Yayın sırasını korumak için yükleme tarihine göre sıralı — facebook_backfill
    ile aynı gerekçe: sayfaya kataloğun kronolojisi yansısın.

    `gerekli_video` platforma göre değişiyor: ön koşul, o platformun GERÇEKTEN
    yükleyeceği dosya olmalı (bkz. PLATFORMLAR'daki not). `maks_bayt` verilirse
    o dosyanın boyutu da ön koşulun parçası (bkz. modül docstring'i, madde 2);
    `kokler` verilmezse üç içerik kökünün hepsi (BASE) taranır.
    """
    liste = []
    for klasor in uyumluluk.proje_klasorleri(BASE if kokler is None else kokler):
        st = _durum(klasor)
        if not st.get("youtube_video_id"):
            continue                      # henüz yayınlanmamış
        if st.get(durum_anahtari):
            continue                      # zaten gitmiş
        # BELIRSIZ kalan yukleme ADAY DEGIL. Ag hatasi govde gonderildikten
        # SONRA olustuysa yukleyici durum anahtarini yazmaz ve state'e bir
        # belirsizlik isareti birakir (upload/ag_yeniden_deneme.py). Bu satir
        # olmasaydi supurge projeyi 'hic gitmemis' gorup bir sonraki kosuda
        # YENIDEN yuklerdi — kopyayi supurge uretirdi. Yukleyicinin icindeki
        # kapi zaten istegi engelliyor, ama o zaman supurge her kosuda istisna
        # alip limit=1'lik tek gunluk slotu KALICI olarak tikardi. Operator
        # elle bakip isareti temizleyene kadar bu proje kuyrukta yok.
        if belirsiz_mi(st, durum_anahtari):
            continue
        if st.get("youtube_privacy") in ("unlisted", "private"):
            continue                      # liste dışı/kopya
        if _public_ani(st) is None:
            continue                      # publishAt bekliyor / gerçekte gizli
        if st.get("telif_araliklari"):
            continue                      # telif eşleşmesi — yeniden yayınlama
        video = os.path.join(klasor, gerekli_video)
        if not os.path.isfile(video):
            continue
        if maks_bayt and os.path.getsize(video) > maks_bayt:
            continue                      # platformun sınırını aşıyor
        liste.append((st.get("youtube_uploaded_at") or "", klasor))
    liste.sort()
    return [k for _, k in liste]


def boyutu_asanlar(durum_anahtari: str, gerekli_video: str, maks_bayt: int,
                   kokler=None) -> list:
    """SADECE boyut yüzünden elenen adaylar — proje adları.

    NEDEN AYRI BİR FONKSİYON: `eksik_projeler` bu adayları sessizce atlıyor ve
    "sessizce atlayan koruma, olmayan korumadan kötüdür". Ama her koşuda log'a
    yazmak da doğru değil (DJ setlerinin 16:9 dosyası HER ZAMAN sınırın
    üstünde olacak, yani kalıcı gürültü). Bu yüzden çağıran yalnızca boyutun
    GERÇEKTEN tıkaç olduğu durumda — kota varken gönderilecek başka aday
    kalmadığında — log'a bir satır yazıyor.
    """
    if not maks_bayt:
        return []
    adlar = []
    for klasor in uyumluluk.proje_klasorleri(BASE if kokler is None else kokler):
        st = _durum(klasor)
        if not st.get("youtube_video_id") or st.get(durum_anahtari):
            continue
        video = os.path.join(klasor, gerekli_video)
        if os.path.isfile(video) and os.path.getsize(video) > maks_bayt:
            adlar.append(os.path.basename(klasor))
    return adlar


def adaylar(platform: tuple) -> list:
    """Platformun TÜM varyantlarındaki adaylar — (proje, varyant).

    SIRA (2026-09-13): önce public anı son `YENI_PUBLIC_PENCERESI_SN` içinde
    olan YENİ şarkılar — kendi içinde EN YENİ public anı ÖNCE — sonra geri
    kalanlar eskisi gibi `youtube_uploaded_at` ile eskiden yeniye.
    NEDEN EN YENİ ÖNCE: kuru simülasyonda (13 Eyl) kronolojik sırayla bugün
    public olan `Sabah Senin`, geçen hafta çıkmış üç şarkının arkasında kaldı;
    günlük tavan 1 ile TG/BS'ye ancak 3 gün sonra gidecekti.
    NEDEN: Telegram/Bluesky'ın ana hat yolu kapandı; bu süpürge artık yeni
    şarkının da TEK yolu. Eskiden yeniye tek kronolojide yeni şarkı, günlük
    tavan 1'le haftalar süren eksik kuyruğunun arkasında kalırdı.

    Varyantlar kök başına farklı dosya/anahtar kullanabildiği için (Telegram'da
    dikey sürüm) listeler ayrı ayrı üretilip BURADA tek sırada birleşiyor:
    sıra kökten değil, yayın tarihinden gelmeli.
    """
    simdi = time.time()
    birlesik = []
    for v in _varyantlar(platform):
        for proje in eksik_projeler(v["anahtar"], v["gerekli_video"],
                                    v["maks_bayt"], v["kokler"]):
            st = _durum(proje)
            an = _public_ani(st, simdi) or 0.0
            if an and simdi - an <= YENI_PUBLIC_PENCERESI_SN:
                anahtar = (0, -an, "", proje)        # en yeni public anı önce
            else:
                anahtar = (1, 0.0, st.get("youtube_uploaded_at") or "", proje)
            birlesik.append((anahtar, proje, v))
    birlesik.sort(key=lambda x: x[0])
    return [(proje, v) for _, proje, v in birlesik]


def bugun_yuklenen(damga_anahtari) -> int:
    """Bu platforma BUGÜN kaç gönderi gitti — günlük tavanı uygulamak için.

    facebook_backfill.bugun_yuklenen()'in birebir karşılığı. Damga anahtarları
    gerçekten yazılıyor: telegram_upload.py `f"{state_prefix}_uploaded_at"`
    (uzun sürüm -> `telegram_uploaded_at`, dikey sürüm ->
    `telegram_shorts_uploaded_at`), bluesky_upload.py `bluesky_uploaded_at`.
    Diskte de doğrulandı.

    `damga_anahtari` TEK bir ad ya da bir ad dizisi olabilir: Telegram'da ana
    katalog ile DJ/derleme kökleri farklı anahtar yazıyor ve günlük tavan
    İKİSİNİ BİRDEN saymalı (yoksa tavan eksik sayar — bu modülün var olma
    sebebi olan hata sınıfı). Üç kökü de gezer: o gün normal hattan çıkmış bir
    setin paylaşımı da tavanı doldurmalı.

    GUNLUK_TAVAN = 1'İN GERÇEK ANLAMI (belgelenmemiş gerçek, 2026-09-11):
    bu sayaç ANA HATTIN paylaşımlarını da sayıyor — bilerek, çünkü tavan
    "kanal bugün bu platforma kaç kez gönderdi" sorusunun cevabı olmalı, "geri
    doldurma kaç kez gönderdi"nin değil. Sonucu şu: ana hat haftada ~3 şarkı +
    1 set yayınlıyor ve YAYIN YAPILAN HER GÜNDE geri doldurmaya 0 slot kalıyor.
    Yani geri doldurma pratikte YALNIZCA YAYINSIZ günlerde ilerler. Bugünkü
    kuyruk (Telegram 16, Bluesky 15 eksik proje) bu tempoda en iyi ihtimalle
    16+ günde boşalır. Tasarım bilinçli (hacim koruması, "inauthentic content"
    riski) ve log'a "tavan dolu" satırı düşüyor — ama kuyruğun neden bu kadar
    yavaş eridiğini arayan bir sonraki okur bunu koddan çıkaramıyordu.
    Kuyruğu hızlandırmanın TEK yolu GUNLUK_TAVAN'ı yükseltmektir ve bu bir
    HACİM kararıdır — elle `--ignore-golden` ile koşturmak yetmez, o bayrak
    yalnızca golden-hour kapısını atlar, günlük tavan yine uygulanır.
    """
    anahtarlar = ((damga_anahtari,) if isinstance(damga_anahtari, str)
                  else tuple(damga_anahtari))
    bugun = time.strftime("%Y-%m-%d")
    sayi = 0
    for klasor in uyumluluk.proje_klasorleri(BASE):
        st = _durum(klasor)
        if any(str(st.get(a) or "")[:10] == bugun for a in anahtarlar):
            sayi += 1                     # proje başına en fazla bir kez
    return sayi


# --- POLİTİKA KAPISI (2026-09-12'de eklendi) ------------------------------
# Bu modül `uyumluluk`u BUGÜNE KADAR yalnızca KÖK LİSTESİ için kullanıyordu
# (`KOKLER` + `proje_klasorleri()`); deponun politika kapısı olan
# `uyumluluk.kontrol()` burada HİÇ çağrılmıyordu. Yani kapı render'dan önce
# (validate_project) ve ana hattın yüklemesinden önce (auto_process /
# dj_famous_process) çalışıyor ama BU SÜPÜRGE onun DIŞINDAN yayın yapıyordu —
# üstelik süpürge tam da `_is_fully_done()`'dan geçmiş, yani ana hattın bir
# daha DOKUNMADIĞI projeleri gönderiyor.
#
# Tek koruma `eksik_projeler()`teki `youtube_privacy in ("unlisted","private")`
# satırıydı ve o bir KOD KAPISI DEĞİL, ELLE yapılmış bir YouTube ayarının
# yerel AYNASI: 'Küllerimden Geç' ('Yeniden Doğacağım' ile aynı audio.wav
# md5'i) bugün SADECE o ayna sayesinde Telegram/Bluesky'a gitmiyor. Ayar bir
# gün public'e çekilirse — ya da alan bayatlar/kaybolursa — kopya üç platforma
# birden çıkardı. Üstelik aynı kopya Instagram'da hâlâ canlı ve TikTok'ta
# taslak bekliyor, yani "tekrar önlendi" durumu sanıldığından zayıf.
#
# `youtube_privacy` kontrolü KALDIRILMADI: iki BAĞIMSIZ kapı bilinçli (aynı
# desen caption_align/youtube_captions slug eşleşmesinde de var). Biri elle
# yapılan ayarın aynası, diğeri kodun kendi kararı; ikisi farklı şeyler
# bildiği için birbirinin yerine geçmiyor.

# Koşu başına BİR kez uyarılan anahtarlar (notify.uyar_bir_kez deseni).
# Süpürge saatlik koşuyor ve engelli proje HER koşuda atlanacak; anahtar proje
# YOLUNA bağlı olduğu için log'a koşu başına tek satır düşer, kalıcı gürültü
# olmaz. BİLEREK temizlenmiyor: kapsam bir PROCESS, yani bir zamanlayıcı koşusu.
_UYARILANLAR: set = set()

# Koşu İÇİ kapı önbelleği: aynı proje hem Telegram hem Bluesky için sınanıyor,
# md5 iki kez hesaplanmasın. `backfill()` başında TEMİZLENİYOR — her koşu diskin
# O ANKİ hâline bakmalı (bayat bir "temiz" kararı taşımak kapıyı açardı).
_KAPI_ONBELLEGI: dict = {}


def _kapi_uyar(anahtar: str, mesaj: str, log) -> None:
    """Aynı anahtar için koşu başına TEK satır yazar.

    `notify` TEMBEL import ediliyor: o modül `requests`e bağlı ve bu süpürgenin
    bilinçli olarak `requests` bağımlılığı yok (aynı gerekçe TELEGRAM_MAKS_BAYT
    notunda). notify import edilemezse satır KAYBOLMUYOR, `log`a düşüyor —
    sessizce atlayan bir koruma, olmayan korumadan kötüdür.
    """
    if anahtar in _UYARILANLAR:
        return
    _UYARILANLAR.add(anahtar)
    try:
        import notify
        notify.uyar_bir_kez(anahtar, mesaj)
    except Exception:                     # noqa: BLE001
        log(mesaj)


def politika_kapisi(klasor: str, log=print) -> str:
    """Bu proje gönderilebilir mi — ENGEL varsa sebep metni, temizse "".

    FAIL-CLOSED: `uyumluluk.kontrol()` istisna fırlatırsa proje ATLANIR.
    Gerekçe bu depoda ödenmiş bir bedel: `uyumluluk.KOKLER` göreli yolken
    `os.path.isdir` False dönüyor, `kontrol()` hata=0 uyarı=0 diyor ve kapı
    KENDİLİĞİNDEN AÇILIYORDU. "Bilmiyorum" ile "temiz" aynı şey değil; bu
    kapının yanlış tarafa düşmesinin bedeli bir gönderinin BİR KOŞU gecikmesi
    değil, kopya/telifli içeriğin üç platforma yayılmasıdır. Gecikme geri
    alınabilir, yayın alınamaz (Instagram'da API'den silmek MÜMKÜN DEĞİL).

    HATA yalnızca O PROJEYİ düşürür, süpürgeyi DURDURMAZ — bir projenin engeli
    diğerlerini bloklamamalı. UYARI'lar yalnızca log'a yazılır (kapı açık kalır),
    çünkü uyarı tanımı gereği "devam edilebilir".
    """
    yol = os.path.abspath(klasor)
    if yol in _KAPI_ONBELLEGI:
        return _KAPI_ONBELLEGI[yol]
    ad = os.path.basename(os.path.normpath(klasor))
    try:
        hatalar, uyarilar = uyumluluk.kontrol(klasor, "yukleme")
    except Exception as e:                # noqa: BLE001
        hatalar = ["uyumluluk kapısı ÇALIŞTIRILAMADI (%s: %s) — fail-closed, "
                   "proje atlandı" % (type(e).__name__, e)]
        uyarilar = []
    for u in uyarilar:
        _kapi_uyar("ek_backfill_uyumluluk_uyari:%s:%s" % (yol, str(u)[:40]),
                   "  uyumluluk uyarısı (%s): %s" % (ad, u), log)
    engel = hatalar[0] if hatalar else ""
    if engel:
        _kapi_uyar("ek_backfill_uyumluluk_hata:%s" % yol,
                   "  %s: UYUMLULUK HATASI — geri doldurma ATLANDI: %s"
                   % (ad, engel), log)
    _KAPI_ONBELLEGI[yol] = engel
    return engel


def backfill(limit: int = KOSU_TAVANI, dry_run: bool = False, log=print) -> dict:
    sonuc = {"durum": "tamam", "islenen": [], "kalan": {}, "tavan": {}}
    _KAPI_ONBELLEGI.clear()               # bu koşunun kendi kararları (yukarı bkz.)
    telafi = config.backfill_telafi_aktif()
    if config.next_golden_publish_time() is not None and not telafi:
        # Golden-hour DIŞINDA hiçbir şey yapma — telafi penceresi kapalıysa.
        sonuc["durum"] = "golden-hour disinda"
        return sonuc

    for platform in PLATFORMLAR:
        (bayrak, ad, _anahtar, _damga, _gerekli_video, kimlik,
         modul_adi, fonksiyon, _ek, _maks, _sapmalar) = platform
        # İKİ SESSİZ DAL KAPATILDI (2026-09-11). İkisi de `continue` ediyor,
        # log'a hiçbir şey yazmıyor ve sonuç sözlüğünde iz bırakmıyordu: bayrak
        # kapanırsa ya da kimlik dosyası kaybolursa bu süpürge SONSUZA KADAR
        # sessizce hiçbir şey yapar — oysa modülün TAMAMI "sessizce duran hattı
        # yakalamak" için yazıldı ve `tavan`/`kalan`/`atlanan` dallarının hepsi
        # özenle loglanıyor. Desen `dj_tarama_kontrol.kontrol_et()`ten alındı
        # ("config.DJ_ON_TARAMA kapalı, karantina kapısı atlandı"): "config'te
        # kapattık" ile "kod bozuk" ayırt edilebilsin.
        if not config.EK_PLATFORMLAR.get(bayrak, False):
            sonuc.setdefault("kapali", {})[ad] = bayrak
            log("  %s geri doldurma: config.EK_PLATFORMLAR['%s'] kapalı, "
                "atlandı" % (ad, bayrak))
            continue
        if not os.path.isfile(os.path.join(UPLOAD_DIR, kimlik)):
            sonuc.setdefault("kimlik_yok", {})[ad] = kimlik
            log("  %s geri doldurma: upload/%s yok, atlandı (kimlik dosyası "
                "olmadan yükleme denenemez)" % (ad, kimlik))
            continue

        # GÜNLÜK tavan: golden-hour içinde saatlik 6 koşu olduğu için koşu
        # başına sınır tek başına yetmiyor (bkz. modül docstring'i). Sayaç
        # platformun BÜTÜN damga anahtarlarını ve ÜÇ KÖKÜ birden kapsıyor.
        yapildi = bugun_yuklenen(_damga_anahtarlari(platform))
        tavan = (config.BACKFILL_TELAFI_TAVANLARI.get(bayrak, GUNLUK_TAVAN)
                 if telafi else GUNLUK_TAVAN)
        kalan_kota = tavan - yapildi
        if kalan_kota <= 0:
            sonuc["tavan"][ad] = "bugün %d gönderi yapıldı (tavan %d%s)" % (
                yapildi, tavan, ", telafi" if telafi else "")
            sonuc["kalan"][ad] = len(adaylar(platform))
            continue

        eksikler = adaylar(platform)
        if not eksikler:
            # Kota VARDI ama gidecek aday yok. Sebep boyut sınırıysa BURADA
            # söylenmeli: "tıkandı" ile "iş bitti" aynı şey değil (bu modül tam
            # da sessiz duruşları yakalamak için var).
            asanlar = []
            for v in _varyantlar(platform):
                asanlar += boyutu_asanlar(v["anahtar"], v["gerekli_video"],
                                          v["maks_bayt"], v["kokler"])
            if asanlar:
                sonuc.setdefault("atlanan", {})[ad] = asanlar
                log("  %s geri doldurma: %d aday dosya boyutu sınırını aştığı "
                    "için atlandı (%s)" % (ad, len(asanlar), ", ".join(asanlar)))

        # POLİTİKA KAPISI yalnızca GERÇEKTEN gönderilecek adaylara uygulanıyor,
        # tüm kataloğa değil. KOTA/MALİYET: `uyumluluk.kontrol()` md5 hesaplıyor
        # ve süpürge saatlik koşuyor. Ölçüldü (22 proje, 2026-09-12): tüm katalog
        # 0,45 sn, proje başına ~6 ms; tek istisna aynı BOYUTTA ses taşıyan
        # kopya çifti (~0,17 sn, çünkü modülün BOYUT ÖN FİLTRESİ ancak orada
        # md5'e düşüyor). Yani tüm katalog için çağırmak da kabul edilebilirdi,
        # ama kuyruğun başındaki 1-2 adayla sınırlamak hem daha ucuz hem de
        # doğru soru: kapı YAYIN kararının kapısı, tarama raporunun değil.
        # Engellenen aday kotayı TÜKETMEZ — sıradaki temiz projeye bakılır
        # (bir projenin engeli diğerlerini bloklamamalı) — ve gönderi
        # yapılmadığı için günlük tavana da girmez (tavan `*_uploaded_at`
        # damgalarını, yani GERÇEKLEŞEN gönderileri sayıyor).
        hedefler = []
        for proje, varyant in eksikler:
            if len(hedefler) >= min(limit, kalan_kota):
                break
            # RİTİM R3b (2026-09-13, karar 4): şarkı aynı gün en fazla N platformda —
            # geri doldurma DAHİL (11 Eyl: 2 dk'da 6 olay). Tavandaki proje kotayı
            # tüketmez; hesaplanamazsa bu koşuda atlanır.
            try:
                import yayin_ritmi
                _r_izin, _r_sebep = yayin_ritmi.platform_gun_izni(_durum(proje), bayrak)
            except Exception as e:                # noqa: BLE001
                _r_izin, _r_sebep = False, "ritim kapısı hesaplanamadı (%s)" % type(e).__name__
            if not _r_izin:
                sonuc.setdefault("ritim", {}).setdefault(ad, []).append(
                    {"proje": os.path.basename(proje), "sebep": _r_sebep[:160]})
                _kapi_uyar("ek_backfill_ritim:%s:%s" % (ad, os.path.abspath(proje)),
                           "  %s geri doldurma bekliyor (%s): %s"
                           % (ad, os.path.basename(proje), _r_sebep), log)
                continue
            engel = politika_kapisi(proje, log)
            if engel:
                sonuc.setdefault("engellenen", {}).setdefault(ad, []).append(
                    {"proje": os.path.basename(proje), "sebep": engel[:160]})
                continue
            hedefler.append((proje, varyant))

        for proje, varyant in hedefler:
            proje_adi = os.path.basename(proje)
            if dry_run:
                sonuc["islenen"].append({"platform": ad, "proje": proje_adi,
                                         "kuru": True})
                continue
            try:
                modul = __import__(modul_adi)
                islev = getattr(modul, fonksiyon)
                r = islev(proje, **varyant["ek"])
                sonuc["islenen"].append({"platform": ad, "proje": proje_adi,
                                         "sonuc": str(r)[:60]})
            except Exception as e:
                sonuc["islenen"].append({"platform": ad, "proje": proje_adi,
                                         "hata": str(e)[:160]})
        # Kalan SONRADAN yeniden sayılıyor: başarılı yükleme state'i güncelliyor,
        # baştaki listeden düşmek yanıltıcı olurdu (facebook_backfill'deki
        # aynı hata için düşülen not).
        sonuc["kalan"][ad] = len(adaylar(platform))
    return sonuc


def main():
    ap = argparse.ArgumentParser(
        description="Telegram/Bluesky'ya hiç gitmemiş şarkıları geri doldurur.")
    ap.add_argument("--limit", type=int, default=KOSU_TAVANI,
                    help="Platform başına bu koşuda en fazla kaç gönderi")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ignore-golden", action="store_true",
                    help="Golden-hour kontrolünü atla (elle çalıştırma için)")
    args = ap.parse_args()

    if args.ignore_golden:
        config.next_golden_publish_time = lambda *a, **k: None

    s = backfill(limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
