"""Bir DJ setinden BİRDEN FAZLA dikey kısa video (Shorts/Reels/TikTok) üretir
ve bunlardan EN FAZLA BİRİNİ, sete göre günler sonraya zamanlanmış ikinci bir
dalga olarak yayınlar.

Neden: DJ setleri 41-81 dakika. Mevcut hat her setten TEK bir 45 saniyelik
dikey video çıkarıyor (`render.py`, en yoğun tek pencere). Oysa setin içinde
birbirine benzemeyen onlarca an var ve Suno indirme kotası (ayda 20-60) yeni
şarkı üretmenin önündeki asıl duvar. Elde olandan daha fazla içerik çıkarmak,
yeni üretimden çok daha ucuz.

Bu modül ana hattı DEĞİŞTİRMİYOR: `output/shorts_9x16.mp4` olduğu gibi kalıyor
(mevcut yüklemeler ona bağlı). Ek kesitler `output/clip_01.mp4`, `clip_02.mp4`
diye ayrı dosyalara yazılıyor ve `state.json`'da `dj_clips` altında
kaydediliyor — hangi kesitin hangi aralıktan geldiği izlenebilsin.

YAYIN HACMİ — BU MODÜLÜN EN ÖNEMLİ KISITI (2026-09-11):
Kanalın en büyük riski telif değil, YouTube'un "inauthentic content"
politikası (15 Temmuz 2025'te "repetitious content"ten yeniden adlandırıldı):
toplu üretilmiş, jenerik, TEKRARLAYICI içerik; yaptırım kanal kapatmaya kadar
gidiyor. Kanal haftada ~15 yükleme yapıyor ve bunu 10'a DÜŞÜRME planı var.
Bu yüzden ÜRETİM ile YAYIN bilerek ayrıldı:
  * ÜRETİM serbest — her sette 3 kesit üretiliyor, diskte durmaları bedava.
  * YAYIN kısıtlı — set başına EN FAZLA 1 kesit (kural YAPISAL, ayarlanabilir
    bir sabit YOK: `kesit_sec()` tek bir kesit döndürüyor ve `yayina_uygun_mu`
    `youtube_clip_video_id` yazılmış bir seti bir daha hiç yayına almıyor),
    setin KENDİ Shorts'uyla aynı gün DEĞİL (`KESIT_MIN_ARA_SN`), ve küresel
    olarak en fazla haftada bir (`KESIT_ARA_SN`). Aynı setten çıkan üç kesit
    birbirine benzer; üçünü birden yayınlamak "tekrarlayıcı içerik"
    tarifinin ta kendisidir. Net etki: haftada +1 yükleme.

POLİTİKA KAPISI (2026-09-12): kesit yayını `dj_famous_process.process_set`'ten
GEÇMİYOR (süpürge `main()`'in `finally` bloğundan koşuyor), yani oradaki
`uyumluluk.kontrol(..., "yukleme")` çağrısı bu yolu HİÇ kapsamıyordu. Kapı artık
`uyumluluk_kapisi()` ile bu modülde, İKİ noktada: `yayina_uygun_mu`'nun son
adımı ve `kesit_yayinla`'nın ilk adımı. HATA -> o kesit yayınlanmaz; kapı
çökerse de yayınlanmaz (FAIL-CLOSED).

Zamanlama YENİDEN İCAT EDİLMİYOR: kesit YouTube'a `publishAt` ile private
yükleniyor ve `config.next_golden_publish_time()`'a ileri bir `now` verilerek
(`KESIT_ERTELEME_GUN` gün sonrası) hesaplanan golden-hour'da YouTube'un kendisi
public'e çeviriyor — `youtube_upload._compute_publish_at`'in kullandığı AYNI
mekanizma, sadece başlangıç anı kaydırılmış hâli.

Kullanım:
    python dj_clips.py --set "dj_sets/Just Relax" --count 3
    python dj_clips.py --set "dj_sets/Just Relax" --count 3 --dry-run
    python dj_clips.py --all --count 3
    python dj_clips.py --yayin-kuru      # kim yayına uygun, yükleme YAPMADAN
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import config
import ffmpeg_utils
import state_io
import uyumluluk
from audio_highlight import find_highlights
from render import find_audio, find_art, load_meta

# Kesitler arasındaki en az boşluk. 60 sn bilinçli: daha küçük değerlerde
# seçilen pencereler aynı bölümün birkaç saniye kaymış hâlleri oluyor ve
# üç ayrı Shorts birbirinin aynı çıkıyor.
MIN_ARA_SN = 60.0
DIKEY = config.PLATFORMS["shorts_9x16"]

# Göreli `--base`/`supur(base=...)` değerlerinin çözüleceği kök
# (`uyumluluk._KOK` ile aynı desen) — gerekçe `_set_klasorleri` docstring'inde.
_KOK = os.path.dirname(os.path.abspath(__file__))

# --- Yayın kısıtları (yukarıdaki modül notundaki gerekçeler) ---------------

# SET BAŞINA YAYIN SAYISI BİR SABİT DEĞİL, YAPISAL BİR KURAL. Burada eskiden
# `SET_BASINA_YAYIN = 1` duruyordu ve "ileride '2 yapalım' denirse kararın
# maliyeti tek yerden görülsün" diye açıklanıyordu; gerçekte HİÇBİR YERDEN
# OKUNMUYORDU (AST taramasıyla doğrulandı, 2026-09-11). Sınırı uygulayan iki
# şey var ve ikisi de sabitten bağımsız: `kesit_sec()` TEK bir kesit
# döndürüyor, `yayina_uygun_mu` da `youtube_clip_video_id` yazılmış seti bir
# daha hiç seçmiyor. Yani sabiti 2 yapan biri HİÇBİR ŞEYİN değişmediğini
# görürdü — "yapmayacağını vaat eden sabit", bu deponun en pahalı hata
# sınıflarından biri (ölü koruma; bkz. CLAUDE.md).
# GERÇEKTEN 2'ye çıkarılmak istenirse tek satırlık bir iş DEĞİL: state
# anahtarı (tekil `youtube_clip_video_id` + `youtube_clip_dosya`) LİSTEYE
# çevrilmeli. Ve bu bir hacim kararıdır — kanal haftalık yüklemeyi 15'ten
# 10'a DÜŞÜRMEYE çalışıyor, "inauthentic content" politikası kanalın en büyük
# tekil riski. Kuralın yapısal olduğunu sabitleyen test:
# tests/test_dj_kesit_yapisal_sinir.py

# Setin KENDİ Shorts'u yüklendikten sonra kesidin yayına UYGUN sayılması için
# geçmesi gereken en az süre. 2 gün: istenen kural "aynı gün değil" ama
# `youtube_shorts_uploaded_at` yerel saat damgası, `publishAt` UTC — 24 saatlik
# bir eşik saat dilimi/zamanlama kaymasıyla aynı güne düşebilirdi. 2 gün bu
# belirsizliği tamamen kapatıyor.
KESIT_MIN_ARA_SN = 2 * 24 * 3600

# İki kesit yayını arasındaki en az süre (TÜM setler için, küresel). 7 gün:
# DJ hattı haftada bir çalışıyor, ama `dj_tarama_kontrol` temiz tarama sonrası
# dj_famous_process'i ekstra tetikliyor — bu koruma olmadan aynı hafta içinde
# iki kesit çıkabilirdi. Üst sınır net kalsın: haftada +1 yükleme.
KESIT_ARA_SN = 7 * 24 * 3600

# Kesit yüklendikten kaç gün SONRAKİ golden-hour'da yayına çıksın.
# 3 gün: DJ koşusu Cuma; kesit bir sonraki Cuma koşusunda yüklenip Pazartesi
# yayınlanıyor. Yani kesit yeni setin yayın gününe DE binmiyor — hafta içine
# yayılıyor. Yükleme anı ile yayın anı YouTube'un `publishAt`'i sayesinde
# birbirinden bağımsız, bu yüzden script'in ne zaman koştuğu önemli değil.
KESIT_ERTELEME_GUN = 3


def _durum_oku(klasor):
    y = os.path.join(klasor, "state.json")
    try:
        with open(y, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _durum_yaz(klasor, guncelleme):
    """state.json'a ATOMİK yazar (`state_io.durum_yaz`).

    NEDEN state_io (CLAUDE.md'nin açık kuralı: "state.json'ı elle yazan YENİ
    kod ekleme"): burası düz `open(y, "w")` ile yazıyordu ve `open` dosyayı
    ÖNCE sıfırlıyor. Bu modülün en kötü senaryosu hem de en sık koşacağı yer:
    `kesit_yayinla` UZUN bir YouTube yüklemesinden HEMEN SONRA, YENİDEN
    ÜRETİLEMEYEN `youtube_clip_video_id`'yi yazıyor. Yazım yarıda kesilirse
    (Görev Zamanlayıcı timeout'u -> TerminateProcess, güç kesintisi) diskte
    yarım bir JSON kalır; `uyumluluk._durum()` artık bunu sessizce `{}`
    saymıyor, `DurumBozuk` fırlatıp O SETİN TÜM BORU HATTINI durduruyor — ve
    video YouTube'da zamanlanmış kalırken kaydı diskte hiç olmuyor.
    `state_io` .tmp + fsync + os.replace ile yazıyor: ya tam eski hâli ya tam
    yeni hâli kalır.
    """
    st = _durum_oku(klasor)
    st.update(guncelleme)
    state_io.durum_yaz(klasor, st)


def _zaman(damga):
    """'%Y-%m-%dT%H:%M:%S' damgasını epoch'a çevirir, bozuksa None.
    auto_process._last_upload_time ile AYNI desen."""
    if not damga:
        return None
    try:
        return time.mktime(time.strptime(damga, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def telife_degiyor_mu(bas, son, araliklar):
    """[bas, son) penceresi `araliklar`daki telifli bölümlerden birine değiyor mu?

    ORTAK YARDIMCI, BİLEREK: aynı örtüşme testi hem ÜRETİM (`clip_uret`, pencere
    elemesi) hem YAYIN (`_uygun_kesitler`) tarafında lazım. Testi kopyalamak bu
    depoda defalarca iki kopyanın sessizce ayrışmasıyla sonuçlandı
    (bkz. CLAUDE.md, `state_io`ya yol açan hata) — kural TEK yerde.

    Sınır bitişikliği çakışma DEĞİL: 100-200 telifliyken 200-245 penceresi
    telifli tek bir örnek bile içermiyor (bkz. tests/test_dj_clips.py).

    BOZUK ARALIK = DEĞİYOR SAYILIR (fail-closed). Sayıya çevrilemeyen bir kayıt
    "telif yok" diye okunursa kapı SESSİZCE AÇILIR ve yeniden yayınlanan telifli
    bir bölümün geri dönüşü yok; tersi durumda en fazla kesit üretilmez/
    yayınlanmaz ve bu log'a düşer (görülebilir, geri alınabilir). Aynı asimetri
    `uyumluluk.py`'de bozuk `state.json` için de bilerek seçildi.
    """
    for t in araliklar or []:
        try:
            tbas, tson = float(t[0]), float(t[1])
        except (TypeError, ValueError, IndexError, KeyError):
            return True
        if bas < tson and son > tbas:
            return True
    return False


def clip_uret(set_dir, count=3, dry_run=False):
    """Sette `count` adet ek dikey kesit üretir. Sonuç sözlüğü döner."""
    ad = os.path.basename(os.path.normpath(set_dir))
    ses = find_audio(set_dir)
    if not ses:
        return {"set": ad, "hata": "audio bulunamadı"}

    # count+1 isteniyor ve EN YÜKSEK enerjili pencere ATILIYOR: o pencereyi
    # ana hat zaten `output/shorts_9x16.mp4` için kullanıyor (render.py ->
    # find_highlight aynı tepeyi seçiyor). Atılmazsa kesitlerden biri mevcut
    # Shorts'un kopyası oluyordu — ilk denemede clip_03 ile shorts_9x16
    # BİREBİR aynı boyutta çıktı, o yüzden fark edildi.
    hepsi = find_highlights(ses, config.HIGHLIGHT_DURATION,
                            count=count + 1, min_gap=MIN_ARA_SN)
    adaylar = list(hepsi[1:]) if len(hepsi) > 1 else list(hepsi)

    # ENERJİ SIRASI BURADA YAKALANIYOR (find_highlights enerji sırasında
    # dönüyor, aşağıdaki sorted() onu zaman sırasına çeviriyor ve bilgi
    # kayboluyordu). Yayın adımı "en enerjili kesit" kuralını uygulayabilsin
    # diye sıra state.json'a yazılıyor: 1 = adaylar arasında en enerjilisi.
    enerji_sirasi = {(a, b): i for i, (a, b) in enumerate(adaylar, 1)}
    pencereler = sorted(adaylar)

    # TELİF KORUMASI: state.json'da `telif_araliklari` varsa o aralıklara
    # değen pencereler ELENİYOR. City Pulse Set'te (4 Eylül 2026) Suno çıktısı
    # "Bring Me To Life (Tiësto, FORS)" ile eşleşti; o bölümler YouTube'daki
    # sürümden elle çıkarıldı ama yerel audio.wav hâlâ içeriyor. Koruma
    # olmasaydı klip üreticisi tam o bölümden kesip yeniden yayınlayabilirdi.
    telifli = _durum_oku(set_dir).get("telif_araliklari") or []
    if telifli:
        onceki = len(pencereler)
        pencereler = [(a, b) for a, b in pencereler
                      if not telife_degiyor_mu(a, b, telifli)]
        if len(pencereler) < onceki:
            print("  %d pencere telifli aralığa değdiği için elendi" % (onceki - len(pencereler)))

    if not pencereler:
        return {"set": ad, "hata": "uygun pencere bulunamadı"}

    if dry_run:
        return {"set": ad, "kuru": True,
                "pencereler": [{"bas": a, "son": b, "enerji": enerji_sirasi[(a, b)]}
                               for a, b in pencereler]}

    meta = load_meta(set_dir)
    art = find_art(set_dir)
    cikti_dir = os.path.join(set_dir, "output")
    os.makedirs(cikti_dir, exist_ok=True)

    ffmpeg_utils.ensure_card_mask()
    uretilen = []
    for i, (bas, son) in enumerate(pencereler, 1):
        yol = os.path.join(cikti_dir, "clip_%02d.mp4" % i)
        try:
            ffmpeg_utils.render_video(
                art, ses, yol, DIKEY[0], DIKEY[1],
                meta.get("title"), meta.get("theme"),
                start_time=bas, end_time=son,
                marquee_override=meta.get("marquee_text"),
            )
            uretilen.append({"dosya": os.path.basename(yol), "bas": bas, "son": son,
                             "enerji": enerji_sirasi[(bas, son)],
                             "bayt": os.path.getsize(yol)})
        except Exception as e:
            uretilen.append({"dosya": os.path.basename(yol), "bas": bas, "son": son,
                             "enerji": enerji_sirasi[(bas, son)],
                             "hata": str(e)[:160]})

    basarili = [k for k in uretilen if not k.get("hata")]

    # `dj_clips` YALNIZCA en az BİR başarılı kesit varsa yazılıyor.
    # NEDEN: bu anahtar aynı zamanda bir KALICI KİLİT —
    # `dj_famous_process._kesitleri_uret` "zaten üretilmiş" diye erken dönüyor
    # ve `yayina_uygun_mu` da varlığına bakıyor. Eskiden hata alan pencereler de
    # listeye giriyor ve liste HER HÂLÜKÂRDA yazılıyordu: üç render'ın üçü de
    # patlasa bile state'e üç `{"hata": ...}` kaydı düşüyor, log "3 kesit
    # üretildi" diyor (yalan), sonraki koşu "zaten üretilmiş" deyip bir daha
    # ASLA denemiyor ve süpürge sonsuza kadar "diskte yayınlanabilir kesit
    # dosyası yok" diyordu. Hiç yazmamak, bir sonraki koşunun yeniden
    # denemesini sağlıyor (render pahalı ama sonsuz kilitten ucuz).
    if basarili:
        _durum_yaz(set_dir, {
            "dj_clips": uretilen,
            "dj_clips_uretildi": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    return {"set": ad, "uretilen": uretilen,
            "basarili": len(basarili), "hatali": len(uretilen) - len(basarili),
            "kaydedildi": bool(basarili)}


# --- İkinci dalga: yayın ---------------------------------------------------


def _uygun_kesitler(set_dir, st=None):
    """(yayınlanabilir kesitler, telif nedeniyle elenen sayısı) döner.

    Liste YAYIN SIRASINDA: en yüksek enerjili (`enerji` en küçük) önce.

    TELİF YENİDEN KONTROL EDİLİYOR — bu fonksiyonun var olma sebebi.
    `telif_araliklari` gerçek hayatta kesitler üretildikten GÜNLER SONRA
    state'e giriyor: Content ID itirazı gelir, insan Studio'da bakar, aralıkları
    elle yazar. `clip_uret` o sette bir daha hiç çalışmıyor (`dj_clips` varsa
    erken dönülüyor), yani ÜRETİM anındaki eleme o yeni bilgiyi hiç görmüyordu.
    Sonuç: telif işareti alıp sonra temizlenen ve `dj_tarama_temiz: true`
    verilen bir set, TELİFLİ bölümden kesilmiş eski bir kesidi yayınlayabilirdi.
    Test tamamen YEREL ve bedava (`telife_degiyor_mu` — üretim tarafıyla AYNI
    yardımcı, kopya DEĞİL), yani her yayın denemesinde çalıştırmanın maliyeti yok.

    `bas`/`son` bilgisi OLMAYAN eski kayıtlar, sette telifli aralık varken
    ELENİYOR (fail-closed): nereden kesildiği bilinmeyen bir kesidin telifli
    bölüme değmediğini iddia edemeyiz. Telifli aralık yoksa o kayıtlar normal
    şekilde yayına uygun kalıyor.
    """
    st = _durum_oku(set_dir) if st is None else st
    kesitler = st.get("dj_clips") or []
    telifli = st.get("telif_araliklari") or []
    uygun, telif_elenen = [], 0
    for k in kesitler:
        if k.get("hata") or not k.get("dosya"):
            continue
        if not os.path.isfile(os.path.join(set_dir, "output", k["dosya"])):
            continue
        if telifli:
            try:
                bas, son = float(k["bas"]), float(k["son"])
            except (KeyError, TypeError, ValueError):
                telif_elenen += 1
                continue
            if telife_degiyor_mu(bas, son, telifli):
                telif_elenen += 1
                continue
        uygun.append(k)
    # enerji yoksa büyük bir sayı ver: enerji bilgisi OLAN kayıtlar her zaman
    # önce gelsin, olmayanlar aralarında dosya adına göre sıralansın.
    uygun.sort(key=lambda k: (k.get("enerji") or 9999, k["dosya"]))
    return uygun, telif_elenen


def kesit_sec(set_dir, st=None):
    """Yayınlanacak TEK kesidi seçer, yoksa None döner.

    KURAL: EN YÜKSEK ENERJİLİ kesit (`enerji` alanı en küçük olan; 1 = en
    enerjili). Gerekçe iki katlı:
      1. Elde tek bir yayın hakkı var (set başına EN FAZLA bir kesit; kural
         yapısal, bkz. modül notu) — o hak setin en güçlü anına harcanmalı. Ana Shorts zaten setin 1 numaralı tepesini
         kullanıyor, bu ondan sonraki en iyi an.
      2. Seçim DETERMİNİSTİK olmalı: rastgele/tarihe bağlı bir seçim, aynı
         set yeniden işlendiğinde başka bir kesit seçip iki kez yayın
         yapılmasına yol açabilirdi. Eşitlik hâlinde dosya adına göre
         sıralanıyor — aynı girdi hep aynı çıktı.

    `enerji` alanı olmayan ESKİ kayıtlar (2026-09-11 öncesi üretilmiş
    clip_*.mp4'ler) için dosya adı sırası kullanılıyor; o kayıtlarda enerji
    bilgisi hiç tutulmamıştı ve setleri yeniden render etmek pahalı.
    """
    uygun, _ = _uygun_kesitler(set_dir, st)
    return uygun[0] if uygun else None


def _kapi_uyar(anahtar, mesaj):
    """Kapı kararını log'a TEK KEZ yazar (koşu başına, anahtar başına).

    NEDEN `notify.uyar_bir_kez` (CLAUDE.md'nin üçüncü sorusu: "çalışmadığını
    nasıl anlarız?"): sessizce `None` dönen bir kapı, OLMAYAN kapıdan kötüdür —
    yokluğu görünmez. Ama süpürge `dj_famous_process`'in HER koşusundan (ve
    `dj_tarama_kontrol`'ün ekstra tetiklemelerinden) çalışıyor; düz `print`
    aynı satırı haftalarca tekrarlayıp log'u boğardı. `uyar_bir_kez` satırı
    çalışan scriptin kendi log dosyasına (dj_famous_process.log) düşürüyor.

    notify hiç yüklenemezse bile SESSİZ kalınmıyor: satır stdout'a basılıyor.
    """
    try:
        import notify
        notify.uyar_bir_kez(anahtar, mesaj)
    except Exception:
        print(mesaj)


def uyumluluk_kapisi(set_dir):
    """(gecti, sebep) — kesit yayını için `uyumluluk.kontrol(..., "yukleme")`.

    NEDEN VAR (2026-09-12): politika kapısı `dj_famous_process.process_set`
    içinde çağrılıyordu ve kesit yayını O YOLDAN HİÇ GEÇMİYORDU — süpürge
    `main()`'in `finally` bloğundan koşuyor (`_kesit_yayini` -> `supur` ->
    `kesit_yayinla` -> `youtube_upload.upload_clip`). Yani telif eşleşmesi
    işaretli, aynı md5'i taşıyan ya da `ai_beyani=False` yazılmış bir setin
    KESİTİ hiçbir kontrolden geçmeden yayınlanabiliyordu. Bu, aynı gün
    `upload/tiktok_publish_plan.py`'de düzeltilen arızanın birebir aynısı:
    kapı doğru, çağrı doğru, ama HAT DIŞINDA (bkz. CLAUDE.md, "BAĞLANTI
    seviyesindeki sessiz arıza").

    FAIL-CLOSED, tartışmasız: `kontrol()` herhangi bir sebeple çökerse kesit
    YAYINLANMAZ. Bu depoda fail-open'ın bedeli zaten ödendi — `uyumluluk.KOKLER`
    göreli yolken `os.path.isdir` False dönüyor, `kontrol()` `hata=0` diyor ve
    kapı KENDİLİĞİNDEN açılıyordu. Ters yönün maliyeti en fazla "bir hafta
    kesit çıkmaz" ve o log'a düşer; bu yönün maliyeti geri alınamaz bir yayın.
    (Aynı asimetri `telife_degiyor_mu`'nun bozuk aralık kuralında da var.)

    UYARILAR yayını DURDURMUYOR (`uyumluluk`'un genel kuralı: HATA = devam
    edilmez, uyarı = loglanır) ama sessizce yutulmuyor da.
    """
    ad = os.path.basename(os.path.normpath(set_dir))
    try:
        hatalar, uyarilar = uyumluluk.kontrol(set_dir, "yukleme")
    except Exception as e:
        _kapi_uyar(
            "dj_kesit_uyumluluk_coktu_%s" % ad,
            "DJ kesit: '%s' için uyumluluk kapısı ÇÖKTÜ (%s) — kesit "
            "YAYINLANMADI (fail-closed). state.json/meta.json okunabilir mi "
            "diye bak." % (ad, str(e)[:160]))
        return False, "uyumluluk kapısı çöktü, fail-closed (%s)" % str(e)[:120]

    if uyarilar:
        _kapi_uyar(
            "dj_kesit_uyumluluk_uyari_%s" % ad,
            "DJ kesit uyumluluk uyarısı (%s): %s"
            % (ad, "; ".join(uyarilar)[:400]))

    if hatalar:
        _kapi_uyar(
            "dj_kesit_uyumluluk_%s" % ad,
            "DJ kesit: '%s' UYUMLULUK HATASI nedeniyle yayınlanmıyor — %s"
            % (ad, "; ".join(hatalar)[:400]))
        return False, "uyumluluk HATASI: %s" % ("; ".join(hatalar))[:200]

    return True, "uyumluluk temiz"


def yayina_uygun_mu(set_dir, simdi=None, st=None):
    """(kesit, sebep) döner. kesit None ise `sebep` neden atlandığını söyler."""
    simdi = time.time() if simdi is None else simdi
    st = _durum_oku(set_dir) if st is None else st

    if st.get("youtube_clip_video_id"):
        return None, "kesit zaten yayınlanmış"
    if not st.get("dj_clips"):
        return None, "üretilmiş kesit yok"

    # Content ID kapısı kesitler için de geçerli: engelli bir setin hiçbir
    # türevi yayınlanmamalı (dj_famous_process.process_set ile AYNI kural).
    if st.get("dj_tarama_engelli"):
        return None, "Content ID engeli var"
    if config.DJ_ON_TARAMA and not st.get("dj_tarama_temiz"):
        return None, ("Content ID taraması henüz temiz değil "
                      "(kapıdan ÖNCE yayınlanmış eski setlerde bu işaret hiç yok — "
                      "Studio'da telif bölümüne bakıp state.json'a elle "
                      "dj_tarama_temiz: true eklenmeli)")

    shorts_at = _zaman(st.get("youtube_shorts_uploaded_at"))
    if not st.get("youtube_shorts_video_id") or shorts_at is None:
        return None, "setin kendi Shorts'u henüz yayınlanmadı"
    gecen = simdi - shorts_at
    if gecen < KESIT_MIN_ARA_SN:
        return None, ("setin Shorts'undan bu yana %.1f gün geçti, en az %.0f gün gerekli"
                      % (gecen / 86400.0, KESIT_MIN_ARA_SN / 86400.0))

    kesit = kesit_sec(set_dir, st)
    if not kesit:
        return None, "diskte yayınlanabilir kesit dosyası yok"

    # POLİTİKA KAPISI — BİLEREK EN SONDA. Yukarıdaki kapıların hepsi saf
    # state okuması (bedava); `uyumluluk.kontrol` ise diskteki TÜM kökleri
    # geziyor ve gerektiğinde md5 hesaplıyor. Süpürge her koşuda her sete
    # bakıyor, yani kapıyı başa koymak onu 5 set × her koşu çalıştırırdı.
    # Burada yalnızca GERÇEKTEN yayınlanacak tek set için koşuyor.
    # (Sıranın ikinci faydası: "üretilmiş kesit yok" gibi somut sebepler
    # uyumluluk mesajının altında kaybolmuyor.)
    gecti, kapi_sebep = uyumluluk_kapisi(set_dir)
    if not gecti:
        return None, kapi_sebep
    return kesit, "uygun"


def _son_kesit_yayini(setler):
    """TÜM setlerdeki en son kesit yüklemesinin epoch'u (yoksa None).
    auto_process._last_upload_time ile aynı desen — küresel tempo kontrolü."""
    son = None
    for s in setler:
        t = _zaman(_durum_oku(s).get("youtube_clip_uploaded_at"))
        if t is not None and (son is None or t > son):
            son = t
    return son


def _set_klasorleri(base):
    """`base` altındaki set klasörleri — MUTLAK yola çevrilmiş hâliyle.

    NEDEN MUTLAK (2026-09-11): `supur(base="dj_sets")` ve
    `dj_famous_process.main()`'in `--base` varsayılanı GÖRELİ. Yanlış cwd'de
    (Görev Zamanlayıcı repo kökünü veriyor ama script elle mutlak yoluyla
    çalıştırılınca cwd başka oluyor) `os.path.isdir` False döner, liste boş
    çıkar ve ikinci dalga hiç çalışmaz. `uyumluluk.KOKLER`,
    `dj_tarama_kontrol.BASELER` ve `upload/youtube_analytics`'te aynı gün
    düzeltilen hatanın aynısı.

    Listeleme de kanonik `uyumluluk.proje_klasorleri()`'ne devredildi: `.`/`_`
    ön ekli klasörlerin elenmesi ve sıralama TEK yerde kalsın — elle kopyalanan
    filtre bu depoda defalarca sessizce ayrıştı (bkz. state_io'ya yol açan
    hata). `.` ön eki de artık eleniyor; eskiden sadece `_` eleniyordu, yani
    yarım bir `.tmp-<ad>` klasörü set sanılabilirdi.
    """
    if not os.path.isabs(base):
        base = os.path.join(_KOK, base)
    return list(uyumluluk.proje_klasorleri(base))


def _playlist_senkronu(set_dir, log=print):
    """Yayınlanan kesidi ait olduğu playlist'e ekler — `_durum_yaz`'DAN SONRA.

    ÇAĞRININ VARLIĞI DEĞİL, SIRASI KRİTİK. Bu deponun en pahalı arızası tam
    burada yaşandı: `sync_project` hem `auto_process.py` hem
    `dj_famous_process.py`'de Shorts yüklemesinden ÖNCE çağrılıyordu, o an
    `state.json`'da `youtube_shorts_video_id` HENÜZ YOKTU ve 20 Shorts'un
    HİÇBİRİ playlist'e girmedi — üstelik proje `_is_fully_done()`'dan geçip
    `pending`den düştüğü için bir daha hiç denenmedi (bkz. CLAUDE.md).
    `sync_project` kararını `beklenen_anahtarlar()` ile state'ten türetiyor:
    `youtube_clip_video_id` diskte yoksa fonksiyon SESSİZCE hiçbir şey yapmaz.
    Bu yüzden burası `kesit_yayinla`'nın state yazımının ARDINDAN çağrılıyor;
    sıra `tests/test_dj_kesit_uyumluluk_kapisi.py`'de hem `ast` ile hem
    davranışsal olarak çivili.

    KESİDİN GİRDİĞİ LİSTE `_shorts` — gerekçe `youtube_playlists.
    beklenen_anahtarlar()` içindeki yorumda (kesit, setin KENDİ Shorts'undan
    FARKLI bir aralıktan geliyor).

    HATASIZ-GEÇER: video bu noktada ZATEN YouTube'da ve `state.json`'a
    yazılmış; playlist'e ekleyememek (kota, ağ, token) yüklemeyi geri almaz ve
    bir sonraki `--sync-all`/`--durum` koşusunda kapanabilir. Sessiz DEĞİL:
    hata log'a düşüyor ve `youtube_playlists --durum` raporu artık kesitleri de
    sayıyor.
    """
    try:
        from youtube_playlists import (get_authenticated_service as _yt,
                                       sync_project as _sync)
        _sync(_yt(), set_dir)
    except Exception as e:
        log("  DJ kesit playlist HATA (görmezden geliniyor): %s" % str(e)[:200])


def kesit_yayinla(set_dir, kesit, log=print, privacy="public"):
    """Seçilen kesidi YouTube'a Short olarak, KESIT_ERTELEME_GUN gün sonraki
    golden-hour'a zamanlanmış şekilde yükler ve state.json'a yazar."""
    st = _durum_oku(set_dir)

    # İKİNCİ KEMER. `yayina_uygun_mu` kapıyı zaten uyguluyor; bu çağrı, ağa
    # çıkılan SON noktada duruyor. NEDEN İKİSİ BİRDEN: `kesit_yayinla` dışarıya
    # açık bir giriş noktası (elle onarım koşuları, ileride eklenecek bir
    # çağıran) ve o yol `yayina_uygun_mu`'dan geçmek ZORUNDA değil. Bu depoda
    # "kapı var ama o yolda değil" arızası bir günde on kez bulundu; maliyeti
    # haftada bir fazladan yerel tarama, bedeli ise geri alınamaz bir yayın.
    # Burada `return` DEĞİL `raise`: sessiz bir atlama, süpürgenin
    # "yayınlandı" sanmasına yol açardı.
    _gecti, _sebep = uyumluluk_kapisi(set_dir)
    if not _gecti:
        raise RuntimeError("uyumluluk kapısı kesidi durdurdu: %s" % _sebep)

    from youtube_upload import upload_clip

    video_id, publish_at = upload_clip(
        set_dir, kesit["dosya"],
        full_video_id=st.get("youtube_video_id"),
        bas_sn=float(kesit.get("bas") or 0.0),
        gun_ertele=KESIT_ERTELEME_GUN,
        privacy=privacy,
    )
    # Anahtar isimlendirmesi youtube_upload'ın mevcut ailesine uyuyor
    # (youtube_shorts_video_id / _uploaded_at / _privacy / _publish_at).
    # `youtube_clip_dosya` TEKRAR GÖNDERMEYİ engelleyen alan: hem hangi
    # kesidin gittiğini hem de "bu set için iş bitti"yi tek yerde tutuyor.
    _durum_yaz(set_dir, {
        "youtube_clip_video_id": video_id,
        "youtube_clip_dosya": kesit["dosya"],
        "youtube_clip_bas": kesit.get("bas"),
        "youtube_clip_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "youtube_clip_privacy": privacy,
        "youtube_clip_publish_at": publish_at,
    })
    log("  DJ kesit: %s -> https://youtube.com/shorts/%s (yayın: %s)"
        % (kesit["dosya"], video_id, publish_at))
    # PLAYLIST SENKRONU — state yazımının ARDINDAN (gerekçe: _playlist_senkronu).
    _playlist_senkronu(set_dir, log)
    return video_id


def supur(base="dj_sets", log=print, dry_run=False):
    """İkinci dalga süpürgesi: TÜM setlere bakar, EN FAZLA BİR kesit yayınlar.

    `dj_famous_process.main()`'den çağrılıyor — `find_pending_sets()` tamamlanmış
    setleri listeden düşürdüğü için (4 ana platform bitince set artık 'pending'
    değil) kesit yayını process_set'e konulamazdı: set daha bir kez bile
    ziyaret edilmeden 'bitmiş' sayılıyor. Bu süpürge o yüzden pending'den
    BAĞIMSIZ, bütün klasörlere bakıyor — auto_process._drain_golden_hour_queue'
    nun ('batch'e girmeyen projeler de kontrol edilsin') aynı gerekçesi.
    """
    sonuc = {"bakilan": 0, "yayinlanan": 0, "atlanan": []}
    setler = _set_klasorleri(base)
    if not setler:
        return sonuc

    # KÜRESEL TEMPO: son kesit yayınından bu yana KESIT_ARA_SN geçmediyse
    # bu koşuda hiçbir şey yapma. _auto_pace_count'un "son yüklemeden bu yana
    # yeterli süre geçti mi" aritmetiğiyle aynı fikir, sabit aralıklı hâli.
    son = _son_kesit_yayini(setler)
    if son is not None:
        kalan = KESIT_ARA_SN - (time.time() - son)
        if kalan > 0:
            log("  DJ kesit: son kesit yayınından bu yana yeterli süre geçmedi "
                "(~%.1f gün daha), bu koşuda atlanıyor" % (kalan / 86400.0))
            return sonuc

    for set_dir in setler:
        sonuc["bakilan"] += 1
        ad = os.path.basename(set_dir)
        kesit, sebep = yayina_uygun_mu(set_dir)
        if not kesit:
            sonuc["atlanan"].append({"set": ad, "sebep": sebep})
            continue
        if dry_run:
            sonuc["yayinlanan"] += 1
            sonuc["kuru"] = {"set": ad, "kesit": kesit}
            log("  DJ kesit (kuru): %s -> %s yayınlanabilirdi" % (ad, kesit["dosya"]))
            return sonuc
        try:
            kesit_yayinla(set_dir, kesit, log=log)
            sonuc["yayinlanan"] += 1
        except Exception as e:
            log("  DJ kesit HATA (%s): %s" % (ad, str(e)[:200]))
        # Set bazındaki sınır YAPISAL: `youtube_clip_video_id` yazıldıktan
        # sonra `yayina_uygun_mu` o seti bir daha hiç seçmiyor. Buradaki
        # `return` KOŞU bazında sınırlıyor — hata alsak bile döngüye devam edip ikinci
        # bir sete geçmiyoruz, yoksa tek koşuda birden fazla kesit çıkabilirdi.
        return sonuc

    return sonuc


def main():
    ap = argparse.ArgumentParser(description="DJ setinden çoklu dikey kesit üretir.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--set", help="Set klasörü (örn. 'dj_sets/Just Relax')")
    g.add_argument("--all", action="store_true", help="dj_sets/ altındaki tüm setler")
    g.add_argument("--yayin-kuru", action="store_true",
                   help="Hangi set/kesit yayına uygun, YÜKLEME YAPMADAN göster")
    ap.add_argument("--count", type=int, default=3, help="Set başına kesit sayısı")
    ap.add_argument("--dry-run", action="store_true", help="Render etme, pencereleri yaz")
    ap.add_argument("--base", default="dj_sets", help="Set klasörlerinin kök dizini")
    args = ap.parse_args()

    if args.yayin_kuru:
        print(json.dumps(supur(args.base, dry_run=True), ensure_ascii=False, indent=2))
        return

    if args.all:
        hedefler = _set_klasorleri(args.base)
    else:
        hedefler = [args.set]

    for h in hedefler:
        s = clip_uret(h, count=args.count, dry_run=args.dry_run)
        print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
