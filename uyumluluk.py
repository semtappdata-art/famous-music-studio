# -*- coding: utf-8 -*-
"""Platform politikası uyumluluk kontrolleri — BORU HATTININ İÇİNDE çalışır.

`.claude/agents/icerik-uyumluluk-ajani.md` ile karıştırılmasın: o ajan ELLE
çağrılıyor ve güncel politikaları web'den araştırıyor. Bu modül ise her
render/yükleme adımında OTOMATİK çalışan, ağa çıkmayan, hızlı kontroller yapıyor.

NEDEN VAR: 2026-09-11'de iki politika riski de OLAY OLDUKTAN SONRA keşfedildi.

1. **Content ID** — City Pulse Set yayınlandıktan sonra "Bring Me To Life
   (Tiësto, FORS)" ile eşleşti; para kazanma kapandı, 2 ülkede engellendi.
   İçerik o anda zaten altı platformdaydı.
2. **"Inauthentic content"** — YouTube 15 Temmuz 2025'te politikayı yeniden
   adlandırdı: toplu üretilmiş, jenerik, küratörlük eklenmemiş AI içeriği para
   kazanmaya uygun değil; yaptırım kanal kapatmaya kadar gidiyor. Aynı
   politikanın "yeniden kullanılan içerik" bölümü, **"önemli bir değişiklik
   yapılmadan bir araya getirilmiş şarkı koleksiyonlarını"** ayrıca yasaklıyor.

Bu kontroller ağa ÇIKMIYOR (politika metni değişmez varsayılmıyor; güncel
politika araştırması ajanın işi). Burada yapılan şey: bilinen kuralları
üretilen dosyalara uygulamak.
"""

import hashlib
import json
import os

# Mutlak yol: goreli birakilirsa yanlis cwd'de os.path.isdir False doner ve
# HEM md5 tekrar kontrolu HEM gunluk yigilma sayaci SESSIZCE atlanir; kontrol()
# hata=0 uyari=0 dondugu icin boru hatti "temiz" der, yani kapi kendiliginden
# acilir. Gorev Zamanlayici -WorkingDirectory repo kokunu veriyor ama script
# elle mutlak yoluyla calistirildiginda cwd baska oluyor. Ayni duzeltme bugun
# dj_tarama_kontrol.py ve upload/youtube_analytics.py'de de yapildi (2026-09-11).
_KOK = os.path.dirname(os.path.abspath(__file__))

# BU LISTE DEPONUN TEK KANONIK ICERIK KOKU LISTESIDIR. Yeni bir yayin koku
# acilirsa DEGISTIRILECEK TEK YER burasi olmali.
#
# NEDEN MERKEZI (2026-09-11): `derlemeler/` bugun eklendi ve kok listesini ELLE
# sayan her yer onu atladi. Bu, CLAUDE.md'deki "baglanti seviyesinde sessiz
# ariza" sinifinin alt turu — kod dogru, cagriliyor, ama YANLIS KUMEYE bakiyor.
# Gercek ornekler: `youtube_stats.get_stats_batch(base)` hep "projects" ile
# cagriliyordu (katalogun yarisi hic olculmedi); `facebook_upload.
# bekleyen_yorumlari_tamamla()` varsayilani ("projects", "dj_sets") idi, yani
# bir derlemenin bekleyen Facebook yorumu HICBIR ZAMAN tamamlanamazdi.
# Muhafiz testi: tests/test_kok_listesi_muhafizi.py
KOK_ADLARI = ("projects", "dj_sets", "derlemeler")

# Mutlak yol ZORUNLU: goreli birakilirsa yanlis cwd'de os.path.isdir False
# doner ve tarayan fonksiyon SESSIZCE bos sonuc uretir (bkz. yukaridaki not).
KOKLER = tuple(os.path.join(_KOK, k) for k in KOK_ADLARI)


def proje_klasorleri(kokler=None):
    """Verilen koklerin (varsayilan: KOKLER) altindaki proje klasorlerini dondurur.

    Tek bir yerde: "kok var mi", "alt oge klasor mu", "sirali mi", "`.`/`_` on
    ekli mi" — kok listesini elle sayan her cagiran bunlari ayri ayri yaziyordu
    ve biri unutuluyordu. `kokler` tek bir yol (str) olarak da verilebilir
    (tek kok isleyen cagrilar). `.`/`_` filtresinin gerekcesi govdede.
    """
    if kokler is None:
        kokler = KOKLER
    elif isinstance(kokler, str):
        kokler = (kokler,)
    for kok in kokler:
        if not os.path.isdir(kok):
            continue
        for ad in sorted(os.listdir(kok)):
            # `.` ve `_` on ekli klasorler ATLANIYOR. IKI AYRI gerekce, ikisi de
            # bu depoda kanitlanmis:
            #
            # `.` — `derleme.py` uretimi once `derlemeler/.tmp-<ad>` altinda
            #   yapip sonda `os.replace` ile hedefe TASIYOR (derleme.py:289);
            #   o gecici klasor uretim boyunca diskte audio.wav'li ama YARIM
            #   duruyor. AYNI filtre `dj_famous_process.find_pending_sets()`te
            #   de var (:213) ve oradaki gerekce "yarim bir derlemeyi yayina
            #   sokmak" — bu fonksiyonun cagiranlarinin COGU da yayin hatti
            #   (facebook_backfill, ek_platform_backfill, bluesky_upload,
            #   tiktok_upload, youtube_comments), yani gerekce birebir gecerli.
            #   Bugun pratik zarar yok, cunku `.tmp-` klasorunde state.json
            #   OLMUYOR ve o hatlar state'e bakip atliyor — ama bu bir yazma
            #   SIRASI tesadufu, garanti degil. Bugun GORUNEN tek etki:
            #   `validate_project --all` yarim klasor icin sahte hata basiyor.
            #
            # `_` — bu depoda `_` on eki "YOK SAY" demek ve kural uc yerde
            #   zaten uygulaniyor: `dj_clips._set_klasorleri()` (:279),
            #   `watch_projects._stray_images()` (:141) ve `latest_release`
            #   (:131 — bugun eklendi; eksikligi, `_` ile arsivlenen bir
            #   projenin HERKESE ACIK sayfada listelenmeye devam etmesi
            #   demekti, yani arsivleme jesti YARIM calisiyordu). Burasi ayni
            #   jestin dorduncu yarisi.
            #   Diskteki iki ornek de bunu dogruluyor, ikisi de PROJE DEGIL:
            #   `dj_sets/_arda` (ham portre fotograflari; audio/meta/state YOK)
            #   ve `derlemeler/_iptal` (yalnizca KAPSAYICI; kendisinde audio/
            #   meta/state YOK). Ikincisi somut zarar da veriyordu: `_kok()`
            #   ona "derlemeler" dedigi icin kontrol() derleme dalina giriyor,
            #   meta.json hic olmadigindan HER taramada IKI SAHTE uyari
            #   basiyordu ("bolum damgasi yok" + "derleme_notu yok").
            #   `_iptal/` ALTINDA park edilmis GERCEK derleme
            #   ("En Cok Dinlenenler") bu filtreden ETKILENMIYOR: bu fonksiyon
            #   TEK seviye tariyor, yani o klasor zaten hicbir zaman
            #   taranmiyordu. Taranmasi isteniyorsa dogru hamle onu
            #   `derlemeler/` altina GERI TASIMAK — kapsayicisini proje gibi
            #   gostermek degil.
            if ad.startswith(".") or ad.startswith("_"):
                continue
            yol = os.path.join(kok, ad)
            if os.path.isdir(yol):
                yield yol

# Aynı gün bu sayıdan fazla yükleme "toplu üretim" desenine benziyor.
# Piyasa verisi (Metricool 2026): uzun format için tatlı nokta haftada 2-4 video.
# 2026-09-11'de 4 → 3: yeni yayın deseninde (ayda ~18 yükleme = 14 şarkı +
# 3 DJ seti + 1 derleme) bir günde AMAÇLANAN en fazla 2 uzun format var
# (1 şarkı + aynı güne denk gelen 1 set/derleme; Shorts ayrı anahtar, burada
# sayılmıyor). Eşik 4'te kalsaydı bu kontrol hiçbir zaman tetiklenmez, yani
# ölü kod olurdu. 3 = "desen kaçtı" anlamına gelen ilk sayı.
GUNLUK_YUKLEME_UYARI = 3


class DurumBozuk(Exception):
    """Bir JSON dosyasi (state.json / meta.json) VAR ama okunamiyor/parse edilemiyor.

    Ikisi icin de ayni desen kullaniliyor — "dosya yok" ile "dosya var ama
    bilinmiyor" ayri seyler — ama SIDDET farkli: bkz. _meta() ve kontrol().
    """


def _durum(proje: str) -> dict:
    """state.json'u dondurur; dosya YOKSA {} (henuz yayinlanmamis proje).

    Dosya VAR ama okunamiyorsa DurumBozuk firlatiyor. Eskiden burada da {}
    donuluyordu ve bu, yutulan bir hatadan daha kotusuydu: `telif_araliklari`
    bos cikiyor, yani asagidaki "bu icerik yeniden yayinlanmamali" kapisi
    SESSIZCE aciliyordu. Yarim yazilmis bir state.json (yazma tarafi henuz
    atomik degil) Content ID eslesmesi almis bir seti yeniden yayina ya da bir
    derlemeye sokabilirdi - City Pulse Set'te bir kez yasanan olayin tekrari.
    Bilinmeyen bir durum "temiz" sayilamaz.
    """
    yol = os.path.join(proje, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        raise DurumBozuk("state.json var ama JSON olarak okunamiyor (%s)" % e)
    except OSError as e:
        raise DurumBozuk("state.json var ama acilamiyor (%s)" % e)


def _meta(proje: str) -> dict:
    """meta.json'u dondurur; dosya YOKSA {}. VAR ama okunamiyorsa DurumBozuk.

    Eskiden bozuk bir meta.json da sessizce {} sayiliyordu ve bu, _durum()'un
    duzeltilen hatasiyla ayni sinifta bir "sessizce uyari uretmeme" idi:
    `ai_beyani=False` isareti ve derleme kontrolleri (bolum damgasi,
    derleme_notu) hic bakilmamis gibi gorunuyordu.
    """
    yol = os.path.join(proje, "meta.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except ValueError as e:
        raise DurumBozuk("meta.json var ama JSON olarak okunamiyor (%s)" % e)
    except OSError as e:
        raise DurumBozuk("meta.json var ama acilamiyor (%s)" % e)


def _ses_yolu(proje: str):
    for n in ("audio.wav", "audio.mp3", "audio.m4a"):
        y = os.path.join(proje, n)
        if os.path.isfile(y):
            return y
    return None


def _md5(yol: str) -> str:
    h = hashlib.md5()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _kok(proje: str) -> str:
    return os.path.basename(os.path.dirname(os.path.abspath(proje)))


def _kopya_notu_var(durum: dict, meta: dict) -> bool:
    """Bu projenin kaydinda `kopya_notu` var mi — operator tekrari BELGELEMIS mi?

    Alan depoda zaten kullaniliyor: 'Kullerimden Gec'in state.json'inda ve
    'Yeniden Dogacagim'in meta.json'inda (ikisi ayni olayin iki tarafi), bu
    yuzden IKI dosyaya da bakiliyor — hangisine yazildigi tarihsel bir kaza.
    """
    return bool((durum or {}).get("kopya_notu") or (meta or {}).get("kopya_notu"))


def _yayindan_cekilmis(durum: dict) -> bool:
    """Bu kayit YouTube'da yayindan CEKILMIS mi (canli bir kopya URETMIYOR mu)?

    'private' TEK BASINA yetmez, iki yanlis pozitif dogururdu:
      * golden-hour zamanlanmis bir video da private duruyor
        (`youtube_publish_at` dolu) ve YouTube onu kendisi public yapacak;
      * DJ setleri Content ID karantinasinda private bekliyor
        (`dj_tarama_bekliyor`) ve temiz cikarsa public oluyor.
    Ikisini de "cekilmis" saymak, canliya GIDECEK bir kopyayi "cozulmus" ilan
    etmek olurdu — kapinin acilmasinin tam da klasik bicimi.
    """
    durum = durum or {}
    gizlilik = durum.get("youtube_privacy")
    if gizlilik == "unlisted":
        return True
    if gizlilik == "private":
        return not (durum.get("youtube_publish_at")
                    or durum.get("dj_tarama_bekliyor"))
    return False


def _yayin_durumu_sozu(durum) -> str:
    """Operatore okunacak kisa durum ifadesi (hata mesajinda gecer)."""
    if durum is None:
        return "durumu okunamadı"
    if not durum.get("youtube_video_id"):
        return "henüz yayınlanmamış"
    return "YouTube'da %s" % (durum.get("youtube_privacy") or "gizliliği bilinmiyor")


def kontrol(proje: str, asama: str = "render") -> tuple:
    """(hatalar, uyarilar) doner. Hata = devam edilmemeli, uyari = loglanir.

    asama: "render" (uretimden once) veya "yukleme" (yayindan once).
    """
    hatalar, uyarilar = [], []
    try:
        meta = _meta(proje)
    except DurumBozuk as e:
        # KARAR: bu UYARI, state.json'daki gibi HATA DEGIL. Gerekce, bozuk bir
        # meta.json'in NEYI kaybettirdigi:
        #   * `ai_beyani=False` isareti gorunmez olur — ama beyani gercekten
        #     yapan mekanizma bu dosya DEGIL: youtube_upload._upload()
        #     `containsSyntheticMedia: True`yi KOSULSUZ gonderiyor. Yani bozuk
        #     meta bir kapiyi acmiyor, sadece "operator bilerek kapatmis"
        #     sinyalini gizliyor.
        #   * Derleme kontrolleri (bolum damgasi, derleme_notu) — ikisi de
        #     zaten UYARI; ustelik `_kok(proje) == "derlemeler"` yedegi meta'dan
        #     BAGIMSIZ tetikleniyor, yani meta={} ile bu dal yine calisir ve
        #     (liste bos oldugu icin) DAHA temkinli davranir.
        # state.json'da durum tersiydi: orada bozuk dosya `telif_araliklari`yi
        # bos gosterip "bu icerik yeniden yayinlanmamali" KAPISINI aciyordu —
        # geri donusu olmayan bir zarar (City Pulse). Burada acilan bir kapi yok.
        # Ayrica meta.json ELLE yazilan bir dosya; bir yazim hatasinin tum
        # kanali durdurmasi, kaybi uyari duzeyinde olan bir eksige gore agir
        # kacar. Sessizlik zaten kirildi: eksik yapilan kontroller artik loga
        # ISIMLERIYLE dusuyor.
        uyarilar.append(
            "%s — ai_beyani ve derleme kontrolleri YAPILAMADI, dosya "
            "düzeltilmeli" % e)
        meta = {}
    try:
        durum = _durum(proje)
    except DurumBozuk as e:
        # Telif kapisi DOGRULANAMIYOR. Uyari degil HATA: "bilmiyorum" ile
        # "temiz" ayni sey degil, boru hatti burada durmali.
        hatalar.append(
            "%s — telif/yayın geçmişi doğrulanamıyor, dosya düzeltilmeden "
            "yayına devam edilmemeli" % e)
        durum = {}

    # --- 1. Telif eşleşmesi işaretli mi -------------------------------------
    # Bu proje daha önce Content ID eşleşmesi aldıysa YENİDEN yayınlanmamalı.
    if durum.get("telif_araliklari"):
        hatalar.append(
            "telif eşleşmesi kayıtlı (%s) — bu içerik yeniden yayınlanmamalı, "
            "önce temizlenmiş ses kullanılmalı"
            % (durum.get("telif_eser") or "eser adı yok"))

    # --- 2. Aynı ses başka projede var mı ----------------------------------
    # 'Küllerimden Geç' / 'Yeniden Doğacağım' aynı sesle iki kez yayınlanmıştı
    # (md5'leri eşitti) ve aylarca fark edilmedi.
    ses = _ses_yolu(proje)
    if ses:
        # Kendi md5'imiz TEMBEL hesaplanıyor: eskiden koşulsuzdu ve tek başına
        # City Pulse Set'te (935 MB) 11 sn sürüyordu; üstelik proje başına İKİ
        # kez (render + yükleme aşaması). Boyut ön filtresi zaten md5'i eleyen
        # asıl adım — 22 ses dosyasının 18'inin boyutu tekil, yani çağrıların
        # çoğunda bu hesap tamamen boşa gidiyordu. Artık ancak boyutu eşleşen
        # bir aday çıkınca hesaplanıyor.
        benim = None
        try:
            benim_boyut = os.path.getsize(ses)
        except OSError as e:
            benim_boyut = None
            uyarilar.append(
                "kendi ses dosyası okunamadı (%s) — tekrar içerik (md5) "
                "kontrolü YAPILAMADI" % e)
        # NEDEN `proje_klasorleri()` DEGIL, ham `os.listdir`: bu dongu bir
        # YAYIN ADAYI listesi degil, bir KANIT taramasi. `_` ile kenara cekilmis
        # ya da `.tmp-` halindeki bir klasorde duran ses de "bu sarki kanalda
        # zaten var" kanitidir; onu elemek tekrar-icerik kontrolunu SESSIZCE
        # zayiflatir. Filtre "neyi yayina sokmayalim" sorusunun cevabi,
        # "neye bakmayalim"in degil.
        for kok in KOKLER:
            if benim_boyut is None:
                break
            if not os.path.isdir(kok):
                continue
            for baska in os.listdir(kok):
                bp = os.path.join(kok, baska)
                if os.path.abspath(bp) == os.path.abspath(proje):
                    continue
                bs = _ses_yolu(bp)
                if not bs:
                    continue
                # OSError SADECE bu adayı düşürür. Eskiden blogun TAMAMI tek bir
                # `except OSError: pass` ile sarılıydı: ses dosyası kilitliyse
                # tekrar-içerik kontrolü sessizce devre dışı kalıyor ve kimse
                # bunu bilmiyordu.
                try:
                    if os.path.getsize(bs) != benim_boyut:
                        continue          # boyut farklıysa md5 hesaplama
                    if benim is None:
                        benim = _md5(ses)
                    if _md5(bs) == benim:
                        # SIDDET KARARI: bu eslesme ZATEN COZULMUS bir vaka mi,
                        # yoksa YENI bir kopya mi? Ikisi ayni sey degil ve
                        # eskiden ikisi de sadece UYARI idi — yani ayni ses
                        # UCUNCU kez kopyalansa yine yayinlanirdi.
                        #
                        # KURAL: sadece IKI sart birlikte saglanirsa UYARI:
                        #   (1) BU projenin kaydinda `kopya_notu` var — operator
                        #       tekrari BELGELEMIS; ve
                        #   (2) ciftin en az bir tarafi yayindan cekilmis
                        #       (unlisted / zamanlanmamis private) — yani
                        #       KANITI da var, canlida tek kayit kaliyor.
                        # Aksi HER durumda HATA.
                        #
                        # Neden (1) "bu proje", "karsi taraf" degil: karsi
                        # tarafin isaretli olmasi yetseydi, ayni sesi tasiyan
                        # YENI (isaretsiz) bir ucuncu klasor "zaten belgelenmis"
                        # sayilip yayina girerdi — engellemek istedigimiz sey
                        # tam olarak bu. Gercek katalog bu sarti zaten
                        # sagliyor: `kopya_notu` CIFTIN IKI TARAFINDA da var
                        # (Kullerimden Gec -> state.json, Yeniden Dogacagim ->
                        # meta.json), bu yuzden mesru olan ikisi de UYARI'da
                        # kaliyor; biri public orijinal, digeri liste disi.
                        #
                        # Neden (2) gerekli: `kopya_notu`nun tek basina kapiyi
                        # acmasi, "nota yaz, yayinla" diye bir kacis yolu
                        # birakirdi. Henuz hic yayinlanmamis IKI klasor ayni
                        # md5'i tasiyorsa hicbiri "cekilmis" sayilmaz ve ikisi
                        # de HATA alir — 7 Eylul'de olan tam buydu (Suno'dan
                        # yanlis dosya kopyalandi) ve dogru davranis, ikisini
                        # de operator ayirt edene kadar durdurmaktir.
                        try:
                            b_durum = _durum(bp)
                        except DurumBozuk:
                            # "Bilmiyorum" != "cozulmus": okunamayan bir
                            # state.json kopyayi mesrulastiramaz.
                            b_durum = None
                        cekilmis_taraf = None
                        if _yayindan_cekilmis(durum):
                            cekilmis_taraf = "bu proje"
                        elif b_durum is not None and _yayindan_cekilmis(b_durum):
                            cekilmis_taraf = "'%s'" % baska
                        # Bozuk/okunamayan state.json "yayinda DEGIL" sayilmaz:
                        # bilinmeyen bir durum muafiyet kazandiramaz.
                        oteki_yayinda = (b_durum is None
                                         or bool(b_durum.get("youtube_video_id")))
                        if _kopya_notu_var(durum, meta) and cekilmis_taraf:
                            uyarilar.append(
                                "sesi '%s' ile BİREBİR AYNI (md5) — BİLİNEN kopya "
                                "(kopya_notu kayıtlı, %s yayından çekilmiş), yayın "
                                "durdurulmadı" % (baska, cekilmis_taraf))
                        elif durum.get("youtube_video_id") and not oteki_yayinda:
                            # BU proje zaten yayinda, eslesen klasor HENUZ DEGIL:
                            # tekrari YARATACAK olan bu isleme degil, o klasorun
                            # yayinlanmasi. Kapi ZATEN orada HATA veriyor (ayni
                            # md5, isaretsiz, yayinlanmamis). Burada da HATA
                            # vermek, birinin diske attigi yanlis bir kopya
                            # yuzunden MESRU orijinalin geri doldurma/altyazi
                            # islerini de durdururdu — engellenmek istenen sey bu
                            # degil.
                            uyarilar.append(
                                "sesi '%s' ile BİREBİR AYNI (md5) — bu proje zaten "
                                "yayında, '%s' ise HENÜZ YAYINLANMAMIŞ. Tekrar riski "
                                "o klasörde ve yayın kapısı ORADA HATA veriyor; "
                                "'%s' yanlışlıkla kopyalandıysa klasörü kaldır ya da "
                                "audio.wav'ını düzelt" % (baska, baska, baska))
                        else:
                            hatalar.append(
                                "sesi '%s' ile BİREBİR AYNI (md5) ve bu tekrar "
                                "KAYITLI DEĞİL ('%s' şu an: %s). Aynı kaydın kanalda "
                                "iki kez yayınlanması 'tekrar içerik / toplu "
                                "üretilmiş AI içerik' tarifinin merkezinde — bir kez "
                                "yaşandı ('Küllerimden Geç' / 'Yeniden Doğacağım'), "
                                "temizliği hâlâ elle yapılıyor. YAPILACAK, ikisinden "
                                "biri: (1) gerçekten aynı kayıtsa yayında KALACAK "
                                "olanı seç, diğerini YouTube'da liste dışına al "
                                "(unlisted) ve BU projenin state.json'ına bir "
                                "`kopya_notu` yaz (çiftin iki tarafına da yazmak en "
                                "temizi); (2) farklı bir şarkı olması gerekiyorsa "
                                "audio.wav yanlış dosyayla kopyalanmıştır — doğru "
                                "sesi koyup yeniden render et."
                                % (baska, baska, _yayin_durumu_sozu(b_durum)))
                except OSError as e:
                    uyarilar.append(
                        "'%s' ile md5 karşılaştırması yapılamadı (%s) — tekrar "
                        "içerik kontrolü bu aday için atlandı" % (baska, e))

    # --- 3. Derleme: "önemli değişiklik" var mı ----------------------------
    # YouTube'un yeniden kullanılan içerik kuralı, önemli değişiklik yapılmadan
    # bir araya getirilmiş şarkı koleksiyonlarını yasaklıyor. Bölüm damgaları ve
    # geçişler bunun en azından bir kısmını karşılıyor; hiçbiri yoksa uyar.
    if meta.get("derleme") or _kok(proje) == "derlemeler":
        liste = meta.get("derleme_liste") or []
        if len(liste) < 3:
            uyarilar.append(
                "derlemede bölüm damgası yok/az — YouTube 'önemli değişiklik "
                "yapılmadan bir araya getirilmiş şarkı koleksiyonu'nu yasaklıyor")
        if not meta.get("derleme_notu"):
            uyarilar.append(
                "derlemede özgün katkı notu (derleme_notu) yok — küratörlük "
                "gerekçesi açıklamaya yansımıyor")

    # --- 4. AI beyanı ------------------------------------------------------
    # Kanalın tamamı AI üretimi; YouTube'un sentetik içerik açıklama kuralında
    # 'AI ile üretilmiş müzik' örnek olarak geçiyor. Bu alan youtube_upload'da
    # sabit True gönderiliyor — burada yalnızca meta'da aksi bir işaret var mı
    # diye bakıyoruz.
    if meta.get("ai_beyani") is False:
        hatalar.append("meta.json'da ai_beyani=False — kanalın tamamı AI üretimi, "
                       "beyan kapatılamaz")

    # --- 5. Yükleme öncesi: günlük yığılma ---------------------------------
    if asama == "yukleme":
        import time
        bugun = time.strftime("%Y-%m-%d")
        sayac = 0
        # Burada da BILEREK ham `os.listdir`: sayac "bugun kanala kac yukleme
        # yapildi" diyor. Yukleme GERCEKLESTIKTEN sonra klasoru `_` ile
        # arsivlemek o yuklemeyi geri almiyor — filtrelemek sayaci EKSIK
        # gosterir, esik tetiklenmez ve "toplu uretim" uyarisi sessizce kaybolur.
        # Guvenlik sayaclari daima GENIS taranir.
        for kok in KOKLER:
            if not os.path.isdir(kok):
                continue
            for baska in os.listdir(kok):
                try:
                    st = _durum(os.path.join(kok, baska))
                except DurumBozuk as e:
                    # Okunamayan her proje sayacı EKSİK bırakır, yani eşik
                    # tetiklenmeyebilir. Sessiz kalmasın.
                    uyarilar.append(
                        "'%s' durumu okunamadı (%s) — günlük yükleme sayacı "
                        "eksik olabilir" % (baska, e))
                    continue
                if (st.get("youtube_uploaded_at") or "")[:10] == bugun:
                    sayac += 1
        if sayac >= GUNLUK_YUKLEME_UYARI:
            uyarilar.append(
                "bugün zaten %d yükleme yapıldı — toplu üretim deseni "
                "'inauthentic content' tarifine yaklaşıyor" % sayac)

    return hatalar, uyarilar


def rapor_yaz(proje: str, hatalar: list, uyarilar: list, log=print) -> None:
    ad = os.path.basename(os.path.normpath(proje))
    for h in hatalar:
        log("  UYUMLULUK HATASI (%s): %s" % (ad, h))
    for u in uyarilar:
        log("  uyumluluk uyarısı (%s): %s" % (ad, u))


if __name__ == "__main__":
    # Elle tarama, kok listesini/filtreyi KENDI ICINDE tekrar yazmiyor:
    # proje_klasorleri() ile ayni kumeyi goruyor. Ayni kural iki yerde iki kopya
    # olsaydi, biri (ornegin `.tmp-` filtresi) digerinde unutulurdu — bu deponun
    # en sik arizasi tam olarak bu.
    for p in proje_klasorleri():
        h, u = kontrol(p, "yukleme")
        if h or u:
            rapor_yaz(p, h, u)
    print("tarama bitti")
