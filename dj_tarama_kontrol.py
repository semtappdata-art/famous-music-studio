# -*- coding: utf-8 -*-
"""DJ setlerinin Content ID taramasını kontrol edip yayını açar.

NEDEN VAR: City Pulse Set (4 Eylül 2026) yayınlandıktan SONRA telif itirazı
aldı — Suno çıktısı "Bring Me To Life (Tiësto, FORS)" ile eşleşti, 4 ayrı
yerde toplam 106 saniye. Sonuç: para kazanma kapalı + 2 ülkede engelli. O
anda içerik zaten altı platformdaydı ve geri almak elle kesme demekti.

AKIŞ:
  1. `dj_famous_process.py` seti YouTube'a `private` yükler ve durur
     (state: `dj_tarama_bekliyor`). Diğer platformlara HİÇ gitmez.
  2. Bu modül, `auto_process.py`'nin saatlik koşusundan çağrılır. Süre
     dolduysa videoyu kontrol eder.
  3. Temizse videoyu `public` yapar ve `dj_tarama_temiz` işaretini koyar;
     bir sonraki DJ koşusu kaldığı yerden devam eder (Shorts, TikTok,
     Instagram, Facebook, Telegram, Bluesky).
  4. Engel varsa private bırakır, log + telefona bildirim gönderir.

Haftalık koşuyu beklemek yerine saatlik hatta bağlanmasının sebebi:
`dj_famous_process.py` haftada bir çalışıyor, ikinci aşama bir sonraki
haftaya kalırdı.

TESPİTİN SINIRI — DÜRÜSTÇE: YouTube Data API, normal kanallara Content ID
itiraz listesini AÇMIYOR; öyle bir uç yok (2026-09-11'de 20 videoda
doğrulandı, itiraz varken de her şey `processed` görünür). Burada
`contentDetails.regionRestriction.blocked` alanına bakılıyor çünkü City
Pulse'un bildirim e-postası "2 idari bölgede engellendi" diyordu — yani
engelleme bu alana yansımalı. Ama bu VARSAYIM, elimizde şu an engelli bir
video olmadığı için doğrulanamadı. Bu yüzden ikinci bir ağ var: süre
dolduğunda sonuç ne olursa olsun telefona bildirim gidiyor ve kullanıcıdan
Studio'ya bakması isteniyor. Otomatik kontrol tutmazsa insan gözü yakalar.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import config
import state_io

# Göreli yol: Görev Zamanlayıcı -WorkingDirectory repo kökü veriyor
# (setup_task_scheduler.ps1). Yine de mutlak yola çeviriyoruz - yanlış cwd'de
# os.path.isdir False döner ve fonksiyon SESSİZCE boş liste döndürürdü,
# yani kapı hiç açılmazdı ve hiçbir hata görünmezdi.
# Content ID kapisi HEM DJ setleri HEM derlemeler icin. Derleme de 40 dakikalik
# YENI bir yukleme: YouTube onu bastan tariyor, kaynak sarkilarin daha once
# temiz cikmis olmasi yeni dosyayi garanti etmiyor. 2 saatlik beklemenin
# maliyeti sifir, kacirilan bir itirazin maliyeti City Pulse'ta goruldu.
_KOK = os.path.dirname(os.path.abspath(__file__))
BASELER = (os.path.join(_KOK, "dj_sets"), os.path.join(_KOK, "derlemeler"))

# Kaç başarısız sorgudan sonra "kontrol edilemiyor" bildirimi gitsin.
# Saatlik koşuda 6 = 6 saat.
BELIRSIZ_BILDIRIM_ESIGI = 6

# Kalan platformları getiren dj_famous_process alt sürecinin süre sınırı.
# 3600 (1 saat) idi ve İKİ katmanlı bir soruna yol açıyordu:
#   (a) timeout dolunca çocuk süreç Windows'ta TerminateProcess ile ölüyor ve
#       dj_famous_process.main()'in `finally: _release_lock()` bloğu HİÇ
#       çalışmıyor -> kilit 8 saat diskte kalıyor (bkz. _dj_kilidini_temizle);
#   (b) bu çağrı auto_process KENDİ kilidini tutarken yapılıyor; iki kök
#       sırayla çağrıldığında engelleme 2x3600 = 2 saate çıkıyordu ve
#       auto_process.LOCK_STALE_SECONDS de tam 2 saat — yani kilit bayat
#       sayılıp İKİNCİ bir auto_process aynı anda başlayabiliyordu.
# 1800 + koşu başına TEK kök (KOSU_BASINA_KOK) ile en kötü hâl 30 dakika.
DJ_SUREC_TIMEOUT = 1800

# Koşu başına kaç kök (dj_sets / derlemeler) işlensin — KOTA KAPISI.
# Her kök AYRI bir dj_famous_process koşusu demek ve her koşu uzun format +
# Shorts = 2 x ~1600 = ~3200 YouTube birimi harcıyor. Aynı saatte hem bir DJ
# seti hem bir derleme kapıdan temiz geçerse 6400, üstüne aynı finally
# bloğundaki normal auto_process yüklemeleri (3200) = 9600/10000 ve günün geri
# kalanı kotasız kalıyordu. Kalan kök bir sonraki SAATLİK koşuya bırakılıyor
# (`dj_kalan_bekliyor` bayrağıyla kalıcı, yoksa hiç tetiklenmezdi).
KOSU_BASINA_KOK = 1

# Kalan platformlar kaç başarısız denemeden sonra bırakılsın (sonsuz döngü
# olmasın diye). Tavanı bulunca bayrak temizlenip telefona haber gidiyor.
DJ_KALAN_DENEME_TAVANI = 3


def _durum(proje: str) -> dict:
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _kaydet(proje: str, guncelleme: dict) -> None:
    # ATOMIK yazim (state_io): eskiden hedefin ustune dogrudan yaziliyordu ve
    # yarida kesilen bir yazim yarim JSON birakiyordu. uyumluluk._durum() artik
    # bozuk state.json'da HATA uretip yayini durduruyor — yani yarim bir dosya
    # tum boru hattini durdurur. Bu fonksiyon her saatlik kosuda cagriliyor.
    st = _durum(proje)
    st.update(guncelleme)
    state_io.durum_yaz(proje, st)


def _tara(simdi: float) -> dict:
    """Karantinadaki HER projeyi üç kovaya ayırır.

    NEDEN AYRI KOVALAR (2026-09-11 arızası): eskiden bu tarama tek bir "süresi
    dolmuş" listesi döndürüyordu ve dolmamış/damgası bozuk projeler sessizce
    `continue` ile düşüyordu. 15:15'te yüklenen `derlemeler/Gece Seansı Vol. 1`
    için saatlik koşu 17:12'de çalıştı — eşiğe 194 saniye kalmıştı, proje
    listeden düştü, `kontrol_et()` `bakilan=0` döndü ve `auto_process._dj_tarama`
    hiçbir satır basmadı. Log'da "tarama" kelimesi geçen TEK satır yoktu, yani
    "kapı çalıştı ama daha erkendi" ile "kapı hiç çağrılmıyor" DIŞARIDAN ayırt
    edilemiyordu. Artık kovalar ayrı taşınıyor ve `kontrol_et()` her koşuda en
    az bir satır basıyor (CLAUDE.md: sessizce boş liste dönen koruma, olmayan
    korumadan kötüdür).
    """
    kova = {"dolmus": [], "erken": [], "damgasiz": []}
    for base in BASELER:
        if not os.path.isdir(base):
            continue
        for ad in sorted(os.listdir(base)):
            proje = os.path.join(base, ad)
            st = _durum(proje)
            if not st.get("dj_tarama_bekliyor") or st.get("dj_tarama_temiz"):
                continue
            damga = st.get("dj_tarama_yuklendi_at")
            t = None
            if damga:
                try:
                    t = time.mktime(time.strptime(damga, "%Y-%m-%dT%H:%M:%S"))
                except ValueError:
                    t = None
            if t is None:
                # Bayrak açık ama damga yok/bozuk: bu proje ESKİDEN sonsuza
                # kadar görünmezdi (hiçbir listeye girmez, hiçbir log satırı
                # bırakmazdı). Artık rapor ediliyor.
                kova["damgasiz"].append(proje)
                continue
            kalan = config.DJ_TARAMA_BEKLEME_SN - (simdi - t)
            if kalan <= 0:
                kova["dolmus"].append(proje)
            else:
                kova["erken"].append((proje, kalan))
    return kova


def bekleyen_setler() -> list:
    """Taraması beklenen ve süresi DOLMUŞ setler."""
    return _tara(time.time())["dolmus"]


def bekleyen_ozeti() -> dict:
    """Süresi DOLMAMIŞ + damgası bozuk karantina kayıtları (log için)."""
    kova = _tara(time.time())
    return {"erken": kova["erken"], "damgasiz": kova["damgasiz"]}


def video_engelli_mi(video_id: str):
    """(engelli_mi, bolgeler) döner; sorgulanamazsa (None, []).

    None dönmesi "bilmiyorum" demek — o durumda yayın AÇILMIYOR, bir sonraki
    koşuda tekrar denenecek. Emin olmadan herkese açmak, tam kaçınmak
    istediğimiz şeyi yapardı.
    """
    try:
        from youtube_auth import get_authenticated_service
        yt = get_authenticated_service()
        r = yt.videos().list(part="contentDetails,status", id=video_id).execute()
        ogeler = r.get("items") or []
        if not ogeler:
            return None, []
        cd = ogeler[0].get("contentDetails") or {}
        kis = (cd.get("regionRestriction") or {}).get("blocked") or []
        return bool(kis), list(kis)
    except Exception as e:
        print("  tarama sorgusu başarısız: %s" % str(e)[:150])
        return None, []


def yayina_ac(video_id: str) -> bool:
    """Videoyu herkese açar — DİĞER status alanlarını KORUYARAK.

    TUZAK: `videos.update` kısmi güncelleme YAPMAZ. Gövdede verilmeyen ama
    `part` içinde yer alan mutable alanlar SİLİNİR. İlk sürüm yalnızca
    `privacyStatus` gönderiyordu ve her temiz taramada şunları siliyordu:
      * `containsSyntheticMedia: True`  — AI üretimi beyanı
      * `selfDeclaredMadeForKids: False`
    Birincisi dj_sets/README.md'nin ilk taahhüdü ("AI üretimi olduğu hiçbir
    şekilde gizlenmiyor"); kapı yüzünden her sette kaybolacaktı. O yüzden
    mevcut status önce OKUNUYOR, üzerine yazılıyor, tamamı geri gönderiliyor.
    """
    try:
        from youtube_auth import get_authenticated_service
        yt = get_authenticated_service()
        r = yt.videos().list(part="status", id=video_id).execute()
        ogeler = r.get("items") or []
        if not ogeler:
            print("  yayına açma: video bulunamadı (%s)" % video_id)
            return False
        durum = dict(ogeler[0].get("status") or {})
        # Salt-okunur alanlar geri gönderilirse API reddediyor.
        for k in ("uploadStatus", "failureReason", "rejectionReason", "privacyStatus"):
            durum.pop(k, None)
        durum["privacyStatus"] = "public"
        # AÇIKÇA yeniden yazılıyor, round-trip'e GÜVENİLMİYOR:
        # `videos.list(part="status")` bu iki alanı GERİ DÖNDÜRMÜYOR (2026-09-11'de
        # gerçek bir videoda doğrulandı - dönen alanlar: uploadStatus,
        # privacyStatus, license, embeddable, publicStatsViewable, madeForKids,
        # selfDeclaredMadeForKids). Yani "oku-birleştir-yaz" tek başına
        # containsSyntheticMedia'yı KORUYAMAZ; okumada yok, yazmaya da girmez.
        # AI beyanı dj_sets/README.md'nin ilk taahhüdü, tahmine bırakılamaz.
        durum["containsSyntheticMedia"] = True
        durum["selfDeclaredMadeForKids"] = False
        yt.videos().update(part="status",
                           body={"id": video_id, "status": durum}).execute()
        return True
    except Exception as e:
        print("  yayına açma başarısız: %s" % str(e)[:150])
        return False


def _dj_kilidini_temizle(log=print) -> None:
    """dj_famous_process'in artik kilidini DISARIDAN siler (timeout sonrasi).

    NEDEN GEREKLI: `subprocess.run(..., timeout=N)` sure dolunca cocuk sureci
    OLDURUYOR; Windows'ta bu TerminateProcess demek ve oldurulen surecte
    `finally` blogu HIC calismiyor. Yani dj_famous_process.main()'in
    `finally: _release_lock()` satiri atlaniyor, `.dj_famous_process.lock`
    diskte kaliyor ve LOCK_STALE_SECONDS (8 SAAT) dolana kadar HER DJ kosusu —
    haftalik Cuma tetikleyicisi dahil — sessizce atlaniyor. Sessiz, 8 saatlik,
    hicbir log satiri birakmayan bir duruş.

    Kilit yolu dj_famous_process.LOCK_PATH'ten okunuyor (sabit kopyalanirsa
    ileride kayabilir); import basarisiz olursa ayni yola elle dusuluyor.
    Import SADECE bu nadir yolda yapiliyor — modul config/render/generate_cover
    cekiyor, her kosuda odemeye degmez.
    """
    try:
        import dj_famous_process
        yol = dj_famous_process.LOCK_PATH
    except Exception:
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           ".dj_famous_process.lock")
    try:
        if os.path.isfile(yol):
            os.remove(yol)
            log("  DJ tarama: timeout sonrasi artik kilit silindi (%s)"
                % os.path.basename(yol))
    except OSError as e:
        log("  DJ tarama: artik kilit silinemedi: %s" % str(e)[:120])


def _kalan_bekleyen_kokler() -> dict:
    """{kok: [proje, ...]} — taramasi temiz cikmis ama kalan platformlari
    henuz tetiklenmemis projeler.

    NEDEN KALICI BIR BAYRAK: kosu basina TEK kok isliyoruz (KOSU_BASINA_KOK,
    kota kapisi). Ertelenen kok bir sonraki kosuda yeniden bulunabilmeli, ama
    `dj_tarama_temiz` isaretlenen proje `bekleyen_setler()`ten kalici olarak
    dusuyor — yani sadece o listeye guvenseydik ertelenen kok BIR DAHA hic
    tetiklenmezdi (auto_process._is_fully_done ile ayni tuzak).
    """
    harita = {}
    for base in BASELER:
        if not os.path.isdir(base):
            continue
        for ad in sorted(os.listdir(base)):
            proje = os.path.join(base, ad)
            if _durum(proje).get("dj_kalan_bekliyor"):
                harita.setdefault(base, []).append(proje)
    return harita


def _kalan_platformlari_isle(base: str, projeler: list, log=print) -> bool:
    """Tarama temiz cikinca dj_famous_process'i TEK bir kok icin tetikler.

    NEDEN GEREKLI: kontrol_et yalnizca YouTube videosunu public yapiyor.
    Shorts/TikTok/Instagram/Facebook/Telegram/Bluesky'i getiren sey
    dj_famous_process ve o HAFTADA BIR calisiyor - yani kisa formatlar
    bir sonraki Cumaya kalirdi. Kapinin var olma gerekcesi "haftalik kosuyu
    beklemek seti 7 gun geciktirir" idi; tetiklemeden o gecikme aynen geri
    geliyordu.

    AYRI SUREC olarak calistiriliyor: dj_famous_process'in kendi kilidi var
    (8 saatlik bayatlama), ayni anda iki kosu ust uste binmiyor. Ic ice
    import edip cagirmak ise auto_process'in kilidiyle karisirdi.

    NEDEN `Popen` ile atesle-unut DEGIL: (1) donen kod/stderr bu hattaki TEK
    gorunurluk — basarisiz bir kosu sessizce kaybolursa set yine haftalarca
    eksik platformda kalir ve `dj_kalan_bekliyor` bayragini ne zaman
    temizleyecegimizi bilemeyiz; (2) auto_process kendi kilidini birakip
    cikinca arkada kalan cocuk surec BIR SONRAKI saatlik kosuyla ust uste
    binerdi ve kimse fark etmezdi. Bu yuzden bekleme KORUNDU, sadece suresi
    yariya indirildi (DJ_SUREC_TIMEOUT) ve timeout dalinda kilit ELLE
    temizleniyor — asil ariza zaten bekleme degil, sizan kilitti.
    """
    import subprocess
    kok = os.path.dirname(os.path.abspath(__file__))
    ad = os.path.basename(base)
    basarili = False
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(kok, "dj_famous_process.py"),
             "--base", ad],
            cwd=kok, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=DJ_SUREC_TIMEOUT)
        if r.returncode == 0:
            basarili = True
            log("  DJ tarama: %s icin kalan platformlar tetiklendi" % ad)
        else:
            log("  DJ tarama: %s islenirken hata (%s)"
                % (ad, (r.stderr or "")[-200:]))
    except subprocess.TimeoutExpired:
        log("  DJ tarama: %s icin dj_famous_process %d sn icinde bitmedi, "
            "sure doldu" % (ad, DJ_SUREC_TIMEOUT))
        # Cocuk surec oldurulduğu icin kendi kilidini birakamadi.
        _dj_kilidini_temizle(log)
    except Exception as e:
        log("  DJ tarama: %s tetiklenemedi: %s" % (ad, str(e)[:150]))

    # Bayragi ancak GERCEKTEN islendikten sonra dusur; basarisizlikta sayaci
    # arttirip tavanda pes et (yoksa her saat yeniden denenip sonsuz doner).
    for proje in projeler:
        if basarili:
            _kaydet(proje, {"dj_kalan_bekliyor": False, "dj_kalan_deneme": 0})
            continue
        deneme = int(_durum(proje).get("dj_kalan_deneme") or 0) + 1
        guncelleme = {"dj_kalan_deneme": deneme}
        if deneme >= DJ_KALAN_DENEME_TAVANI:
            guncelleme["dj_kalan_bekliyor"] = False
            pad = os.path.basename(proje)
            log("  DJ tarama: %s icin kalan platformlar %d denemede getirilemedi, "
                "birakildi" % (pad, deneme))
            _bildir("DJ set kalan platformlar getirilemedi",
                    "%s YouTube'da yayinda ama Shorts/TikTok/Instagram/Facebook/"
                    "Telegram/Bluesky %d denemede gonderilemedi. Elle "
                    "dj_famous_process.py calistirman gerekebilir." % (pad, deneme))
        _kaydet(proje, guncelleme)
    return basarili


def kontrol_et(log=print) -> dict:
    """Bekleyen setleri kontrol eder. auto_process'in saatlik koşusundan çağrılır."""
    sonuc = {"bakilan": 0, "acilan": 0, "engelli": 0, "belirsiz": 0,
             "acilan_kokler": [], "erken": 0, "damgasiz": 0, "kalan_kok": 0}
    if not getattr(config, "DJ_ON_TARAMA", False):
        # Eskiden sessizce dönüyordu: kapı KAPALI olduğu hâlde log'da hiçbir iz
        # kalmıyordu, yani "config'te kapattık" ile "kod bozuk" ayırt edilemezdi.
        log("  DJ tarama: config.DJ_ON_TARAMA kapalı, karantina kapısı atlandı")
        return sonuc

    for proje in bekleyen_setler():
        sonuc["bakilan"] += 1
        ad = os.path.basename(proje)
        st = _durum(proje)
        vid = st.get("youtube_video_id")
        if not vid:
            # Sessiz `continue` idi: bayrağı açık ama video id'si olmayan bir
            # proje her koşuda listeye girip hiçbir iz bırakmadan düşüyordu.
            log("  DJ tarama (%s): youtube_video_id yok, kontrol edilemiyor "
                "(elle bak)" % ad)
            continue

        engelli, bolgeler = video_engelli_mi(vid)
        if engelli is None:
            sonuc["belirsiz"] += 1
            # Modül notundaki "her durumda bildirim gider" iddiası bu dal için
            # geçerli DEĞİLDİ: token bozulursa set haftalarca private'ta bekler
            # ve telefona hiçbir şey gitmezdi. Sayaç + tek seferlik bildirim.
            deneme = int(st.get("dj_tarama_deneme") or 0) + 1
            _kaydet(proje, {"dj_tarama_deneme": deneme})
            log(f"  DJ tarama ({ad}): sorgulanamadı ({deneme}. deneme), "
                "bir sonraki koşuda tekrar denenecek")
            if deneme == BELIRSIZ_BILDIRIM_ESIGI:
                _bildir("DJ set kontrol edilemiyor",
                        "%s taranamıyor (%d denemedir). Token bozulmuş olabilir — "
                        "Studio'da telif bölümüne elle bak." % (ad, deneme))
            continue

        if engelli:
            sonuc["engelli"] += 1
            mesaj = ("%s: Content ID ENGELİ var (%s). Video private bırakıldı, "
                     "diğer platformlara gönderilmedi." % (ad, ", ".join(bolgeler)))
            log("  DJ tarama: " + mesaj)
            # `dj_tarama_bekliyor` KAPATILIYOR: açık kalırsa set her saat
            # yeniden listeye giriyor ve telefon günde 24 kez çalıyordu.
            # Ayrı bir `dj_tarama_engelli` işareti konuyor; dj_famous_process
            # bunu görüp seti hiçbir platforma göndermiyor.
            _kaydet(proje, {"dj_tarama_engel": bolgeler,
                            "dj_tarama_engelli": True,
                            "dj_tarama_bekliyor": False,
                            "dj_tarama_kontrol_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            _bildir("DJ set ENGELLENDİ", mesaj)
            continue

        if yayina_ac(vid):
            sonuc["acilan"] += 1
            sonuc["acilan_kokler"].append(os.path.dirname(proje))
            # `dj_kalan_bekliyor`: kalan platformlar (Shorts/TikTok/...) henuz
            # gonderilmedi. Bayrak KALICI, cunku kosu basina tek kok isleniyor
            # (kota) ve ertelenen kok bir sonraki saatlik kosuda bu bayraktan
            # bulunuyor — `dj_tarama_temiz` olan proje bekleyen_setler()ten
            # kalici olarak dusuyor.
            _kaydet(proje, {"dj_tarama_temiz": True,
                            "dj_tarama_bekliyor": False,
                            "dj_tarama_deneme": 0,
                            "dj_kalan_bekliyor": True,
                            "dj_kalan_deneme": 0,
                            "youtube_privacy": "public",
                            "dj_tarama_kontrol_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            log(f"  DJ tarama ({ad}): temiz, yayına açıldı — diğer platformlar "
                "bir sonraki DJ koşusunda gönderilecek")
            # Otomatik kontrol bir VARSAYIMA dayanıyor (modül notu), o yüzden
            # temiz sonuçta da haber veriliyor: insan gözü ikinci ağ.
            _bildir("DJ set yayında",
                    "%s yayına açıldı. Otomatik kontrol temiz dedi — yine de "
                    "Studio'da telif bölümüne bir bak." % ad)

    # Kalan platformlari getir (haftalik kosuyu bekleme). HER KOK AYRI bir
    # dj_famous_process cagrisi gerektiriyor: o tek bir --base aliyor ve
    # derlemeler ile setler ayri koklerde. Eski yorum "tek cagri yetiyor"
    # diyordu ama kod zaten kok basina donuyordu — yorum koda uyduruldu.
    # KOSU BASINA TEK KOK (kota, bkz. KOSU_BASINA_KOK): kalani bir sonraki
    # saatlik kosu alir, `dj_kalan_bekliyor` bayragi sayesinde kaybolmaz.
    bekleyen = _kalan_bekleyen_kokler()
    sirali = sorted(bekleyen)
    for base in sirali[:KOSU_BASINA_KOK]:
        _kalan_platformlari_isle(base, bekleyen[base], log)
    sonuc["kalan_kok"] = max(0, len(sirali) - KOSU_BASINA_KOK)
    if sonuc["kalan_kok"]:
        log("  DJ tarama: %d kok bir sonraki saatlik kosuya birakildi "
            "(YouTube kotasi)" % sonuc["kalan_kok"])

    # HER KOŞUDA EN AZ BİR SATIR — arızanın asıl sebebi buydu (bkz. _tara()).
    # Eşiğe 194 saniye kala çalışan bir koşu ile hiç çağrılmayan bir kapı,
    # log'dan ayırt edilebilmeli. Bu satır tarama işi OLSA DA OLMASA DA basılır.
    ozet = bekleyen_ozeti()
    sonuc["erken"] = len(ozet["erken"])
    sonuc["damgasiz"] = len(ozet["damgasiz"])
    if ozet["erken"]:
        detay = ", ".join(
            "%s ~%d dk" % (os.path.basename(p), max(1, int(k // 60)))
            for p, k in sorted(ozet["erken"], key=lambda x: x[1])[:3])
        log("  DJ tarama: %d içerik karantinada, süresi dolmadı (%s)"
            % (len(ozet["erken"]), detay))
    for proje in ozet["damgasiz"]:
        log("  DJ tarama (%s): dj_tarama_bekliyor açık ama dj_tarama_yuklendi_at "
            "yok/bozuk — bu kayıt kendiliğinden AÇILMAZ, elle bak"
            % os.path.basename(proje))
    if not (sonuc["bakilan"] or sonuc["erken"] or sonuc["damgasiz"]
            or sirali):
        log("  DJ tarama: karantinada bekleyen içerik yok (kapı çalıştı)")
    else:
        log("  DJ tarama özeti: bakilan=%d acilan=%d engelli=%d belirsiz=%d "
            "erken=%d damgasiz=%d kalan_kok=%d"
            % (sonuc["bakilan"], sonuc["acilan"], sonuc["engelli"],
               sonuc["belirsiz"], sonuc["erken"], sonuc["damgasiz"],
               sonuc["kalan_kok"]))
    return sonuc


def _bildir(baslik: str, mesaj: str) -> bool:
    """Telefona bildirim gonderir; BASARILI mi doner.

    Eskiden `except Exception: pass` idi — bildirim hatti bozuksa
    "DJ set ENGELLENDI" gibi uyarilar sessizce kayboluyordu ve hicbir yerde iz
    kalmiyordu. Hata artik en azindan loga dusuyor (saglik_kontrol._bildir ile
    ayni sinif hata).
    """
    try:
        import notify
        notify.send(baslik, mesaj)
        return True
    except Exception as e:
        print("  bildirim gonderilemedi (%s): %s" % (baslik, str(e)[:150]))
        return False


if __name__ == "__main__":
    print(json.dumps(kontrol_et(), ensure_ascii=False, indent=2))
