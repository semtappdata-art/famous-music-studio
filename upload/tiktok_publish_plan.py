"""Bir projenin TikTok yayın planını hesaplar — HİÇBİR ŞEY GÖNDERMEZ.

Neden ayrı bir modül: TikTok'a yayın artık higgsfield MCP bağlayıcısı üzerinden
yapılıyor (kendi app'imizin `video.publish` izni yok, app review "kişisel
kullanım" gerekçesiyle reddediyor). MCP yalnızca bir asistan oturumundan
çağrılabiliyor; Görev Zamanlayıcı'dan koşan `auto_process.py` ona erişemez.

Bu yüzden iş ikiye bölündü:
  1. Boru hattı videoyu render eder ve BURADAKİ planı üretir.
  2. Asistan "yayınla" dendiğinde planı okur ve MCP'den gönderir.

Kritik nokta: caption/yorum/kapak asistanın KAFASINDAN UYDURULMAZ, deponun
kendi `social_text.build_caption()` fonksiyonundan gelir. Böylece MCP'den
yayınlanan metin, boru hattının ürettiğiyle birebir aynı olur.

Caption state.json'dan OKUNMUYOR, taze hesaplanıyor: `tiktok_suggested_caption`
alanı sonradan eklendi, daha eski projelerde yok (ör. Yeraltı). Ayrıca
build_caption başlığa göre değişken hook/soru seçiyor — plan her zaman güncel
koddan üretilmeli.

POLİTİKA KAPISI BURADA DA ÇALIŞIR (2026-09-12'de eklendi) — NEDEN:
`uyumluluk.kontrol()` render'dan ve YÜKLEMEDEN önce otomatik çalışıyor
(`render.py` ve `auto_process.py`/`dj_famous_process.py` üzerinden). TikTok
yayını ise TASARIM GEREĞİ o hattın DIŞINDA: video boru hattından taslak olarak
gelen kutusuna yükleniyor, canlıya çıkaran adım ELLE (asistan + higgsfield MCP,
ya da telefon). Yani kapı, yayına çıkmadan önce kontrol edilmeyen TEK yolu
kapsamıyordu — ve bekleyen 20 taslak tam orada duruyor. 2026-09-12 kuru
taramasında bunun bedeli ölçüldü, iki kayıt `hazir: True` diyordu:
  * `dj_sets/City Pulse Set` — state.json'ında `telif_eser`
    ("Bring Me To Life - Tiesto, FORS") + 4 `telif_araliklari` kayıtlı;
    `uyumluluk.kontrol(..., "yukleme")` bu proje için HATA veriyor
    ("bu içerik yeniden yayınlanmamalı") ama plan bunu hiç sormuyordu.
  * `projects/Küllerimden Geç` — `Yeniden Doğacağım` ile aynı `audio.wav`
    (md5 eşit); YouTube'da bilerek liste dışı, ama TikTok'ta İKİSİ de hâlâ
    taslak. `buyume_kontrol_listesi.md` A4 "20 taslağı yayınla" diyor ve
    "ikisi aynı ses" uyarısı sadece düz metin olarak orada duruyordu.
Artık iki kapı da koddan geçiyor: `uyumluluk` HATA'ları `engel` oluyor,
uyarılar plana yazılıyor, ve TikTok'a ÖZEL bir ikiz kapısı var
(`_tiktok_ikiz_kapisi` — gerekçesi kendi docstring'inde).

ELLE YAYIN SONRASI İŞARETLEME (2026-09-12'de eklendi) — NEDEN BURADA:
`build_plan()` iki state alanını OKUYOR (`tiktok_published_at`,
`tiktok_dogrulandi`) ama depoda bu alanları YAZAN hiçbir kod yoktu — 22 proje
klasörünün hiçbirinde ikisi de mevcut değil. Yani "okuyan var, yazan yok":
CLAUDE.md'deki BAĞLANTI seviyesindeki sessiz arıza sınıfının bir örneği daha.
Bedeli somut: `_tiktok_ikiz_kapisi`'nın EN AĞIR kuralı ("ikiz TikTok'ta ZATEN
yayınlanmış → ENGEL") pratikte HİÇ ateşlenemiyordu, çünkü hiçbir kayıt
"yayınlandı" demiyordu.

Yazanın burada olmasının sebebi: yayın adımının kendisi ELLE. TikTok'un
`video.publish` izni alınamadı (app review "kişisel kullanım" gerekçesiyle
reddetti — KAPALI bir yol), boru hattı yalnızca TASLAK yüklüyor, kullanıcı
taslağı TikTok uygulamasından yayınlıyor. API "yayınlandı mı" sorusunu da
cevaplamıyor (`video.list` scope'u yok). Yani bu olguyu depoya bildirebilecek
TEK kaynak kullanıcının kendisi; onu okuyan modül de burası.

    python upload/tiktok_publish_plan.py --yayinlandi "projects/Yeraltı"
    python upload/tiktok_publish_plan.py --yayinlandi-hepsi      # etkileşimli
    python upload/tiktok_publish_plan.py --dogrulandi "projects/Yeraltı"

İKİ ALAN AYRI TUTULUYOR, çünkü İKİ AYRI OLGU (birleştirmek tehlikeli):
  * `tiktok_published_at` — "bu taslak TikTok'ta yayına çıktı". Kapıyı besler.
  * `tiktok_dogrulandi`   — "SELF_ONLY gönderisinde başlık/açıklama/AIGC
    etiketi GÖZLE doğrulandı, artık PUBLIC_TO_EVERYONE önerilebilir"
    (bkz. `.claude/skills/fms-tiktok-yayin/SKILL.md`, "Kırmızı çizgiler").
`--yayinlandi` İKİNCİSİNİ YAZMAZ: yayınlamak doğrulamak değildir. Toplu
işaretleme ikisini birden yazsaydı, tek bir "hepsini işaretle" hareketi
kanalın tamamını denetlenmemiş bir PUBLIC_TO_EVERYONE önerisine geçirirdi.

Kullanım:
    python upload/tiktok_publish_plan.py --project "projects/Yeraltı"
    python upload/tiktok_publish_plan.py --project "projects/Yeraltı" --json
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from social_text import build_caption, build_youtube_comment, resolve_language
from tiktok_upload import _find_cover, _load_meta

# NEDEN modülü İÇE AKTARIYORUZ, kuralları KOPYALAMIYORUZ: telif/kopya
# kurallarının ikinci bir kopyası, birinci kopya güncellendiğinde sessizce
# eskiyen bir kapı demek (bkz. CLAUDE.md — `derleme._enerji`'nin
# `youtube_playlists.py`'ye kopyalanmasından doğan hata). md5/ses yolu
# yardımcıları da aynı sebeple buradan alınıyor.
import uyumluluk
# state.json'a YAZAN tek yol: atomik yazici (CLAUDE.md'nin acik kurali —
# state.json'i elle `open(..., "w")` ile yazan YENI kod eklenmiyor).
import state_io

VIDEO_ADI = "shorts_9x16.mp4"


class IsaretlemeHatasi(Exception):
    """İşaretleme reddedildi — sebebi mesajda. SESSİZCE geçilmez."""


def _kisa_baslik(caption: str, sinir: int = 150) -> str:
    """caption'ın ilk satırını, en fazla `sinir` karakter olacak şekilde döner."""
    ilk = (caption or "").strip().splitlines()[0].strip() if caption else ""
    if len(ilk) <= sinir:
        return ilk
    kesik = ilk[:sinir]
    bosluk = kesik.rfind(" ")
    return (kesik[:bosluk] if bosluk > 40 else kesik).rstrip()


def _durum_oku(project_dir: str) -> dict:
    yol = os.path.join(project_dir, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _durum_oku_kesin(project_dir: str) -> dict:
    """YAZMADAN ÖNCE okuyan sürüm — hata YUTMAZ, `IsaretlemeHatasi` atar.

    NEDEN `_durum_oku`'yu kullanmıyoruz: o fonksiyon PLAN için doğru — dosya
    yoksa/bozuksa `{}` döner ve plan yine basılır (operatör caption'ı
    görebilsin). Aynı davranış YAZMA yolunda felaket olurdu: bozuk bir
    state.json'da `{}` okuyup üstüne yazmak, o projenin TÜM kaydını siler
    (`youtube_video_id`, `tiktok_publish_id`, `kopya_notu`...) — ve
    `kopya_notu` `uyumluluk`'un md5 muafiyetini besleyen alan, yani kayıp
    sessizce bir KAPIYI da açardı. Okuyamıyorsak yazmıyoruz.
    """
    yol = os.path.join(project_dir, "state.json")
    if not os.path.isdir(project_dir):
        raise IsaretlemeHatasi("proje klasörü yok: %s" % project_dir)
    if not os.path.isfile(yol):
        raise IsaretlemeHatasi(
            "state.json yok: %s — bu proje TikTok'a hiç yüklenmemiş" % yol)
    try:
        with open(yol, "r", encoding="utf-8") as f:
            durum = json.load(f)
    except (OSError, ValueError) as e:
        raise IsaretlemeHatasi(
            "state.json OKUNAMADI (%s: %s) — üstüne yazmak kaydın tamamını "
            "silerdi, işaretleme durduruldu: %s" % (type(e).__name__, e, yol))
    if not isinstance(durum, dict):
        raise IsaretlemeHatasi("state.json bir sözlük değil: %s" % yol)
    return durum


def _kanal_dogrulandi() -> bool:
    """Kanalda HERHANGİ bir gönderi gözle doğrulanmış mı?

    NEDEN PROJE BAZLI DEĞİL, KANAL BAZLI (2026-09-12 kararı): `tiktok_dogrulandi`
    bir PROJE olgusu gibi yazılmıştı ama ifade ettiği şey kanal seviyesinde —
    "boru hattının ürettiği başlık/açıklama/AIGC etiketi TikTok'ta DOĞRU
    görünüyor". Proje bazlı okunduğunda alan İSPATEN ölüydü:
    `onerilen_gizlilik` yalnızca HENÜZ YAYINLANMAMIŞ bir proje için anlamlı,
    ama bir projenin `tiktok_dogrulandi`si ancak o proje yayınlandıktan
    (`tiktok_published_at`) sonra doğru olabilir — ve o anda `build_plan`
    zaten `engel = "zaten yayınlanmış"` diyor. Yani ifade her zaman SELF_ONLY'ye
    düşüyordu: yeni hiçbir şarkı asla PUBLIC_TO_EVERYONE önerisi alamazdı,
    kanal sonsuza kadar kendi kendine yayın yapardı. Doğrulama BİR KEZ yapılan
    bir şey (bkz. `.claude/skills/fms-tiktok-yayin/SKILL.md` sırası), o yüzden
    kayıt hangi projede duruyorsa dursun kanalın tamamı için okunuyor.

    Kökler `uyumluluk`'tan (TEK kanonik liste) ve MUTLAK — göreli olsaydı
    yanlış cwd'de tarama boş döner ve öneri SELF_ONLY'de takılırdı. Bu yön
    zaten GÜVENLİ taraf: şüphede kalırsak herkese açık yayın ÖNERMİYORUZ.
    """
    for proje in uyumluluk.proje_klasorleri():
        if _durum_oku(proje).get("tiktok_dogrulandi"):
            return True
    return False


def _ayni_sesi_tasiyanlar(project_dir: str) -> list:
    """Bu projeyle AYNI sesi (audio md5) taşıyan DİĞER klasörler: [(yol, durum)].

    `uyumluluk`'un md5 taramasıyla aynı yöntem — önce dosya BOYUTU ön filtresi,
    sonra md5 — ve aynı üç içerik kökü (`uyumluluk.KOKLER`, MUTLAK yollar; göreli
    olsaydı yanlış cwd'de `os.path.isdir` False döner ve kapı kendiliğinden
    AÇILIRDI, bkz. CLAUDE.md). Ses dosyası okunamıyorsa o aday atlanır ama
    tarama DEVAM eder: tek bir kilitli dosya tüm kopya kontrolünü sessizce
    devre dışı bırakmamalı.
    """
    ses = uyumluluk._ses_yolu(project_dir)
    if not ses:
        return []
    try:
        benim_boyut = os.path.getsize(ses)
    except OSError:
        return []
    benim_md5 = None
    bulunan = []
    for kok in uyumluluk.KOKLER:
        if not os.path.isdir(kok):
            continue
        for baska in os.listdir(kok):
            bp = os.path.join(kok, baska)
            if os.path.abspath(bp) == os.path.abspath(project_dir):
                continue
            bs = uyumluluk._ses_yolu(bp)
            if not bs:
                continue
            try:
                if os.path.getsize(bs) != benim_boyut:
                    continue
                if benim_md5 is None:
                    benim_md5 = uyumluluk._md5(ses)
                if uyumluluk._md5(bs) != benim_md5:
                    continue
            except OSError:
                continue
            bulunan.append((bp, _durum_oku(bp)))
    return bulunan


def _tiktok_ikiz_kapisi(project_dir: str, durum: dict) -> tuple:
    """TikTok'a ÖZEL kopya kapısı. (engel, uyarilar) döner.

    NEDEN `uyumluluk`'un md5 kapısı BURADA YETMİYOR: o kapının muafiyeti
    "çiftin bir tarafı YouTube'da yayından çekilmiş" — yani YouTube hakkında
    bir olgu. TikTok hakkında hiçbir şey söylemiyor. Gerçek durum (2026-09-12):
    `Küllerimden Geç` YouTube'da liste dışı (muafiyet geçerli, `uyumluluk`
    sadece UYARI veriyor) ama TikTok'ta İKİSİ de hâlâ taslakta — yani orada
    tekrar HENÜZ ÖNLENMİŞ DEĞİL, sadece ertelenmiş durumda. Elle yayın adımı
    bu kararın alındığı TEK yer olduğu için kapı da burada olmalı.

    KURAL (sadece aynı md5'i taşıyan bir İKİZ varsa işler):
      1. İkiz TikTok'ta ZATEN yayınlanmışsa (`tiktok_published_at`) → ENGEL:
         aynı ses ikinci kez yayına girer.
      2. İkiz de yayınlanmamış bir taslaksa: meşru taraf, YouTube'da `public`
         olan taraftır (kanalın kendi kaydıyla tutarlı olan). Ben o değilsem
         ENGEL; ben oysam UYARI (ikizin taslakta KALMASI gerektiğini söyler).
      3. İkisi de public değilse ya da İKİSİ de public'se hangisinin meşru
         olduğu koddan bilinemez → ENGEL. `uyumluluk`'un aynı durumdaki
         davranışı: "operatör ayırt edene kadar ikisini de durdur".
    """
    engeller, uyarilar = [], []
    ben_public = durum.get("youtube_privacy") == "public"
    for yol, d in _ayni_sesi_tasiyanlar(project_dir):
        ad = os.path.basename(os.path.abspath(yol))
        if d.get("tiktok_published_at"):
            engeller.append(
                "aynı ses (md5) '%s' adıyla TikTok'ta ZATEN yayınlanmış (%s) — "
                "bunu yayınlamak kanalda aynı kaydı ikinci kez yayına sokar"
                % (ad, d["tiktok_published_at"]))
            continue
        if not d.get("tiktok_publish_id"):
            continue  # ikiz TikTok'a hiç yüklenmemiş: burada çözülecek çakışma yok
        ikiz_public = d.get("youtube_privacy") == "public"
        if ben_public and not ikiz_public:
            uyarilar.append(
                "aynı ses (md5) '%s' adıyla da TikTok gelen kutusunda duruyor — "
                "YAYINLANACAK OLAN BU proje (YouTube'da public olan taraf), '%s' "
                "TASLAKTA KALMALI ya da silinmeli" % (ad, ad))
        elif ikiz_public and not ben_public:
            engeller.append(
                "aynı ses (md5) '%s' adıyla da taslakta ve YouTube'da public olan "
                "taraf O — meşru kayıt '%s', bu proje taslakta kalmalı" % (ad, ad))
        else:
            engeller.append(
                "aynı ses (md5) '%s' adıyla da TikTok taslağında; hangisinin meşru "
                "olduğu kayıtlardan anlaşılamıyor (ikisi de %s) — operatör ayırt "
                "edene kadar ikisi de yayınlanmamalı"
                % (ad, "YouTube'da public" if ben_public else "public değil"))
    return (engeller[0] if engeller else None), uyarilar


def build_plan(project_dir: str) -> dict:
    """Yayın için gereken her şeyi tek sözlükte döner.

    `hazir` False ise yayınlanmamalı; `engel` nedeni söyler.
    """
    meta = _load_meta(project_dir)
    durum = _durum_oku(project_dir)
    video = os.path.join(project_dir, "output", VIDEO_ADI)

    youtube_url = None
    if durum.get("youtube_video_id"):
        youtube_url = "https://youtu.be/" + durum["youtube_video_id"]

    dil = resolve_language(meta)
    caption = build_caption(meta)
    ilk_yorum = (build_youtube_comment(youtube_url, dil, platform="tiktok")
                 if youtube_url else None)

    # SIRA: ucuz/kesin kontroller önce, politika kapısı sonra. `uyumluluk`
    # md5 taraması yaptığı için (yerel, ağsız ama diskten okur) video bile
    # olmayan bir projede boşuna çalıştırmanın anlamı yok.
    engel = None
    if not os.path.isfile(video):
        engel = "video yok: " + video
    elif durum.get("tiktok_published_at"):
        engel = "zaten yayınlanmış: " + durum["tiktok_published_at"]

    # POLİTİKA KAPISI — modül docstring'indeki gerekçe. Kapı ağa ÇIKMAZ.
    # Hiçbir istisna planı üretilemez hâle getirmemeli: kapı çökerse plan yine
    # basılır ama "hazir" kesinlikle False olur ve sebebi yazılır — sessizce
    # AÇILAN bir kapı, olmayan kapıdan kötüdür (CLAUDE.md).
    try:
        uy_hatalar, uy_uyarilar = uyumluluk.kontrol(project_dir, "yukleme")
    except Exception as e:                                   # noqa: BLE001
        uy_hatalar = ["uyumluluk kapısı ÇALIŞTIRILAMADI (%s: %s)"
                      % (type(e).__name__, e)]
        uy_uyarilar = []
    try:
        ikiz_engel, ikiz_uyarilar = _tiktok_ikiz_kapisi(project_dir, durum)
    except Exception as e:                                   # noqa: BLE001
        ikiz_engel = "TikTok ikiz kapısı ÇALIŞTIRILAMADI (%s: %s)" % (type(e).__name__, e)
        ikiz_uyarilar = []
    if ikiz_engel:
        uy_hatalar = list(uy_hatalar) + [ikiz_engel]
    uy_uyarilar = list(uy_uyarilar) + list(ikiz_uyarilar)
    if engel is None and uy_hatalar:
        engel = uy_hatalar[0]

    # Doğrulama kanal seviyesinde okunuyor (gerekçe: `_kanal_dogrulandi`).
    # Kendi kaydındaki bayrak ÖNCE bakılıyor — eski/elle yazılmış kayıtlar
    # geçerliliğini korusun ve tarama hiç gerekmesin diye. Tarama çökerse
    # GÜVENLİ tarafa düşülüyor (False → SELF_ONLY): bu kapı "yayınlama" demiyor,
    # "önce kendine göster" diyor; sessizce PUBLIC'e açılması kabul edilemez.
    try:
        dogrulandi = bool(durum.get("tiktok_dogrulandi")) or _kanal_dogrulandi()
    except Exception:                                        # noqa: BLE001
        dogrulandi = False

    return {
        "proje": os.path.basename(os.path.abspath(project_dir)),
        # TikTok'un `title` alanı 150 karakterle sınırlı; üretilen caption'ların
        # HEPSİ (18/18, 200-252 karakter) bunu aşıyor — ölçüldü. Bu yüzden tam
        # caption `description` alanına (4000 sınır) gider, `title`a caption'ın
        # ilk satırı (hook) konur. İlk satır da uzunsa kelime sınırından kırpılır.
        "baslik_150": _kisa_baslik(caption),
        "baslik": meta.get("title", "Untitled"),
        "video": video if os.path.isfile(video) else None,
        "video_bayt": os.path.getsize(video) if os.path.isfile(video) else 0,
        "caption": caption,
        "ilk_yorum": ilk_yorum,
        "kapak": _find_cover(project_dir),
        "dil": dil,
        # TikTok gerçekçi AI içerikte AIGC etiketini zorunlu kılıyor; şarkı
        # Suno ile üretildiği için bu HER ZAMAN açık gitmeli.
        "aigc": True,
        # Doğru sıra: önce SELF_ONLY ile doğrula, sonra herkese aç.
        # DIRECT_POST geri alınamaz.
        "onerilen_gizlilik": "PUBLIC_TO_EVERYONE" if dogrulandi else "SELF_ONLY",
        "dogrulandi": dogrulandi,
        "taslak_id": durum.get("tiktok_publish_id"),
        # Kapının TAMAMI plana yazılıyor, sadece ilk engel değil: `--json`
        # çıktısını okuyan asistan oturumu "neden yayınlamıyorum"u tek tek
        # görebilmeli, yoksa ikinci bir engel bir sonraki denemede sürpriz olur.
        "uyumluluk_hatalari": list(uy_hatalar),
        "uyumluluk_uyarilari": list(uy_uyarilar),
        "hazir": engel is None,
        "engel": engel,
    }


# --------------------------------------------------------------------------
# ELLE YAYIN SONRASI İŞARETLEME — hiçbir ağ çağrısı yok, tamamen yerel.
# --------------------------------------------------------------------------

def isaretle_yayinlandi(project_dir: str, zaman: str = None,
                        dry_run: bool = False) -> tuple:
    """`tiktok_published_at` yazar. `(yazildi, mesaj)` döner.

    `tiktok_dogrulandi`'yı BİLEREK YAZMAZ — modül docstring'indeki gerekçe:
    yayınlamak, gönderiyi gözle doğrulamak değildir.

    İDEMPOTENT: zaten işaretli bir proje hata DEĞİL (yeniden çalıştırmak
    zararsız olmalı) ama sessiz de değil — damgası basılıp `yazildi=False`
    dönülüyor, çünkü "ikinci kez işaretledim" ile "işaretlendi" aynı şey gibi
    görünürse toplu modda hangi satırın gerçekten değiştiği kaybolur.
    """
    durum = _durum_oku_kesin(project_dir)
    ad = os.path.basename(os.path.abspath(project_dir))
    if not durum.get("tiktok_publish_id"):
        raise IsaretlemeHatasi(
            "'%s' TikTok'a hiç yüklenmemiş (state.json'da `tiktok_publish_id` "
            "yok) — yayınlanmış olamaz. Önce: "
            "python upload/tiktok_upload.py --project \"%s\"" % (ad, project_dir))
    eski = durum.get("tiktok_published_at")
    if eski:
        return False, "'%s' ZATEN işaretli (%s) — değişiklik yok." % (ad, eski)
    # `tiktok_uploaded_at` ile AYNI biçim (`tiktok_upload.py`): iki damga aynı
    # kayıtta yan yana duruyor, farklı biçimde olsalardı kıyaslanamazlardı.
    damga = zaman or time.strftime("%Y-%m-%dT%H:%M:%S")
    if dry_run:
        return False, "[kuru] '%s' -> tiktok_published_at = %s (YAZILMADI)" % (ad, damga)
    durum["tiktok_published_at"] = damga
    state_io.durum_yaz(project_dir, durum)
    return True, "'%s' yayınlandı olarak işaretlendi: %s" % (ad, damga)


def isaretle_dogrulandi(project_dir: str, dry_run: bool = False) -> tuple:
    """`tiktok_dogrulandi = True` yazar. `(yazildi, mesaj)` döner.

    ÖNKOŞUL yayınlanmış olmak: doğrulama "TikTok'ta gözümle gördüm" demek,
    var olmayan bir gönderi doğrulanamaz. Bu önkoşul aynı zamanda bayrağın tek
    gerçek riskini de sınırlıyor — bir kez True olduğunda plan kanalın TAMAMI
    için PUBLIC_TO_EVERYONE önermeye başlıyor (bkz. `_kanal_dogrulandi`).
    """
    durum = _durum_oku_kesin(project_dir)
    ad = os.path.basename(os.path.abspath(project_dir))
    if not durum.get("tiktok_published_at"):
        raise IsaretlemeHatasi(
            "'%s' henüz yayınlanmış olarak işaretlenmemiş — doğrulanacak bir "
            "gönderi yok. Önce: --yayinlandi \"%s\"" % (ad, project_dir))
    if durum.get("tiktok_dogrulandi"):
        return False, "'%s' ZATEN doğrulanmış — değişiklik yok." % ad
    if dry_run:
        return False, "[kuru] '%s' -> tiktok_dogrulandi = True (YAZILMADI)" % ad
    durum["tiktok_dogrulandi"] = True
    state_io.durum_yaz(project_dir, durum)
    return True, ("'%s' doğrulandı olarak işaretlendi — plan artık kanal için "
                  "PUBLIC_TO_EVERYONE öneriyor." % ad)


def bekleyen_taslaklar() -> list:
    """TikTok'a yüklenmiş ama henüz "yayınlandı" işareti almamış projeler.

    Kökler `uyumluluk.proje_klasorleri()`'nden: depodaki TEK kanonik kök
    listesi (`projects` + `dj_sets` + `derlemeler`). Elle sayılsaydı
    `derlemeler/` yine atlanırdı — bu depoda defalarca olan hata.
    """
    bulunan = []
    for proje in uyumluluk.proje_klasorleri():
        durum = _durum_oku(proje)
        if durum.get("tiktok_publish_id") and not durum.get("tiktok_published_at"):
            bulunan.append(proje)
    return bulunan


def _toplu_isaretle(dry_run: bool = False, girdi=None) -> int:
    """Bekleyen taslakları TEK TEK sorarak işaretler. Yazılan sayıyı döner.

    NEDEN "--yayinlandi-hepsi" diye körü körüne bir toplu bayrak YOK:
    işaretleme bir GÖZLEM kaydı, bir istek değil. Kullanıcının 20 bekleyen
    taslağı var ama hepsini yayınlamış olması gerekmiyor; tek hareketle
    hepsini işaretlemenin bedeli iki yönlü ve ikisi de sessiz:
      * YAYINLANMAMIŞ bir taslak "yayınlandı" sayılır → panodaki bekleyen
        listesinden düşer, hatırlatma bir daha gelmez, taslak TikTok'ta
        sonsuza kadar öylece kalır (bu deponun imza arızası: kaybolan iş).
      * İşaret `_tiktok_ikiz_kapisi`'nı besliyor. Bir ikizin YANLIŞ tarafı
        "yayınlandı" işaretlenirse kapı meşru tarafı ENGELLER ve gerçekte
        yayınlanmamış olan kopya kanalın "canlı" kaydı sayılır — aynı sesin
        TikTok'a çıkma riskini azaltmak için kurulan kapı ters çalışır.
    Bu yüzden mod ETKİLEŞİMLİ ve sürtünme RİSKLE ORANTILI: planı `hazir=False`
    diyen (yani yayınlanmamalıydı) bir proje için düz "e" yetmiyor, açıkça
    "EVET" yazmak gerekiyor. Varsayılan cevap her zaman HAYIR.
    """
    adaylar = _bekleyenleri_listele()
    if not adaylar:
        return 0

    # `girdi` verilmişse çağıran zaten cevapları sağlıyor (testler) — o durumda
    # terminal şartı aranmıyor.
    #
    # WINDOWS NOTU: `isatty()` burada TEK emniyet değil, olmamalı da —
    # `< /dev/null` (MSYS'de NUL) Windows'ta KARAKTER AYGITI olduğu için
    # `isatty()` True dönüyor, yani "etkileşimsiz" tespiti bu platformda
    # güvenilir değil. Asıl emniyet aşağıdaki döngüde: `input()` EOF verirse
    # iş İPTAL ediliyor (varsayılan cevap her zaman HAYIR), yani cevapsız bir
    # koşu hiçbir şey işaretlemiyor.
    etkilesimli = girdi is not None or (sys.stdin is not None and sys.stdin.isatty())
    if not etkilesimli:
        if dry_run:
            return 0      # kuru mod: yukarıdaki liste zaten basıldı, yazım yok
        # Etkileşimsiz bir kabuktan çalıştırmak, tam da kaçınmak istediğimiz
        # "körü körüne hepsini işaretle" hareketinin ta kendisi olurdu.
        raise IsaretlemeHatasi(
            "toplu işaretleme ONAY istiyor ama terminal etkileşimli değil. "
            "Listeyi görmek için --yayinlandi-hepsi --dry-run, tek tek "
            "işaretlemek için --yayinlandi \"<proje>\" kullan.")

    print("\n(Cevap: e = evet yayınladım, başka her şey = hayır; q = çık)\n")
    yazilan = 0
    for i, (proje, plan) in enumerate(adaylar, 1):
        ad = os.path.basename(os.path.abspath(proje))
        durum = _durum_oku(proje)
        print("[%d/%d] %s" % (i, len(adaylar), ad))
        print("       yüklenme : %s" % (durum.get("tiktok_uploaded_at") or "bilinmiyor"))
        print("       taslak id: %s" % (durum.get("tiktok_publish_id") or "-"))
        if plan["hazir"]:
            soru = "       TikTok'ta yayınladın mı? [e/H/q] "
            gecerli = ("e", "evet")
        else:
            # Kapının "bunu yayınlama" dediği bir projeyi işaretlemek, gerçekten
            # yayınlandıysa DOĞRU kayıt — ama yanlışlıkla basılmış bir "e" ile
            # olmamalı. Sürtünme burada bilerek artıyor.
            print("       !! Plan bu projeyi YAYINLANMAMALI diyor: %s" % plan["engel"])
            soru = ("       Buna rağmen yayınladıysan onaylamak için EVET yaz "
                    "[EVET/h/q] ")
            gecerli = ("EVET",)
        try:
            cevap = (girdi() if girdi else input(soru)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n       -> iptal edildi.")
            break
        if cevap.lower() in ("q", "cik", "çık"):
            print("       -> çıkılıyor.")
            break
        if cevap not in gecerli:
            print("       -> atlandı (işaretlenmedi).\n")
            continue
        try:
            oldu, mesaj = isaretle_yayinlandi(proje, dry_run=dry_run)
        except IsaretlemeHatasi as e:
            print("       -> HATA: %s\n" % e)
            continue
        yazilan += 1 if oldu else 0
        print("       -> %s\n" % mesaj)

    print("Toplam yazılan: %d / %d" % (yazilan, len(adaylar)))
    if dry_run:
        print("(--dry-run: diske HİÇBİR ŞEY yazılmadı.)")
    return yazilan


def _bekleyenleri_listele() -> list:
    """Bekleyenleri TOPLU bir özet olarak basar, `[(proje, plan)]` döner.

    NEDEN ÖNCE TOPLU ÖZET, sonra tek tek soru: operatör 20 soruya cevap
    vermeye başlamadan ÖNCE listenin tamamını görmeli — hangi taslakların
    plana göre yayınlanmaması gerektiği (kopya/telif) ancak bütünü görünce
    fark ediliyor. Planlar burada BİR KEZ hesaplanıp döndürülüyor: `build_plan`
    md5 taraması yapıyor, döngüde ikinci kez çağırmanın anlamı yok.
    """
    adaylar = bekleyen_taslaklar()
    if not adaylar:
        print("Bekleyen TikTok taslağı yok (hepsi işaretli ya da hiç yükleme yok).")
        return []
    print("TikTok'a yüklü ama 'yayınlandı' işareti olmayan %d taslak:"
          % len(adaylar))
    cift = []
    for proje in adaylar:
        plan = build_plan(proje)
        cift.append((proje, plan))
        print("  %-34s hazir=%-5s%s" % (
            os.path.basename(os.path.abspath(proje))[:34], plan["hazir"],
            "" if plan["hazir"] else "  <- " + (plan["engel"] or "")))
    return cift


def _cikti_utf8() -> None:
    """Konsol çıktısını UTF-8'e çeker — BU MODÜLÜN ÇALIŞMASININ ŞARTI.

    ARIZA (2026-09-12'de üretim makinesinde ölçüldü, modül yazıldığından beri
    vardı): Windows'ta Python'ın `sys.stdout.encoding`i ANSI kod sayfası
    (`cp1254`) oluyor. Üretilen HER caption `config.HOOK_LINES`'tan gelen bir
    emoji taşıyor (🌙, 🔥 ...) ve emoji cp1254'te YOK — yani

        python upload/tiktok_publish_plan.py --project "projects/<isim>"
        python upload/tiktok_publish_plan.py --project "projects/<isim>" --json

    komutlarının İKİSİ de `UnicodeEncodeError` ile çöküyordu, tam da caption
    basılacağı satırda. Başlık/engel satırları basıldığı için çıktı "çalışıyor"
    gibi başlıyor, sonra traceback'e dönüyordu.

    Bedeli tam olarak bu modülün var olma sebebini yok ediyordu: modül,
    TikTok'a ELLE yayın yapan kişinin caption'ı KAFASINDAN UYDURMAMASI için
    var (bkz. üstteki docstring ve CLAUDE.md). Caption hiç basılamayınca geriye
    kalan tek seçenek uydurmak oluyordu. 20 bekleyen taslak bu komuta bağlı.

    İKİ ADIM birden gerekiyor: (1) konsolun KOD SAYFASI 65001'e çekilmeli —
    tek başına `reconfigure` çökmeyi durdurur ama cp1254 konsolunda Türkçe
    harfler bozuk görünürdü; (2) akışlar UTF-8'e çevrilmeli. Çıktı bir dosyaya
    ya da boruya yönlendirilmişse (1) sessizce başarısız olur, (2) yeterlidir.
    Hiçbir hata yukarı çıkmıyor: bu yardımcı planın basılmasını ASLA
    engellememeli — düzeltmek istediği arızanın aynısını üretmiş olurdu.
    """
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:                                    # noqa: BLE001
            pass
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


def main() -> None:
    # İLK SATIR: argümanlar ayrıştırılmadan önce, çünkü argparse'ın kendi hata
    # ve yardım metinleri de Türkçe (ve aynı kod sayfasına çarpar).
    _cikti_utf8()
    ap = argparse.ArgumentParser(
        description="TikTok yayın planını yazdırır / elle yayını işaretler "
                    "(HİÇBİR ŞEY GÖNDERMEZ, ağa çıkmaz).")
    # Tam olarak BİR mod seçilmeli: argparse'ın kendi hatası, elle yazılmış bir
    # "ikisi birden verilemez" kontrolünden hem daha kısa hem daha net.
    mod = ap.add_mutually_exclusive_group(required=True)
    mod.add_argument("--project", help="Proje klasörü (örn. projects/Yeraltı)")
    mod.add_argument("--yayinlandi", metavar="PROJE",
                     help="Bu projeyi TikTok'ta YAYINLANDI olarak işaretle "
                          "(tiktok_published_at)")
    mod.add_argument("--yayinlandi-hepsi", action="store_true",
                     dest="yayinlandi_hepsi",
                     help="Bekleyen taslakları TEK TEK sorarak işaretle")
    mod.add_argument("--dogrulandi", metavar="PROJE",
                     help="SELF_ONLY gönderisi gözle doğrulandı — plan bundan "
                          "sonra PUBLIC_TO_EVERYONE önerir (tiktok_dogrulandi)")
    ap.add_argument("--json", action="store_true", help="Ham JSON bas")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Ne yazılacağını göster, diske DOKUNMA")
    args = ap.parse_args()

    # İşaretleme modları. Hata SESSİZCE geçilmiyor: mesaj + sıfırdan farklı
    # çıkış kodu, çünkü bu komut bir betikten de çağrılabilir.
    if args.yayinlandi or args.dogrulandi or args.yayinlandi_hepsi:
        try:
            if args.yayinlandi_hepsi:
                _toplu_isaretle(dry_run=args.dry_run)
            elif args.yayinlandi:
                print(isaretle_yayinlandi(args.yayinlandi, dry_run=args.dry_run)[1])
            else:
                print(isaretle_dogrulandi(args.dogrulandi, dry_run=args.dry_run)[1])
        except IsaretlemeHatasi as e:
            print("HATA: %s" % e)
            sys.exit(2)
        return

    plan = build_plan(args.project)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    print("Proje    : %s (%s)" % (plan["proje"], plan["baslik"]))
    print("Video    : %s" % (plan["video"] or "YOK"))
    if plan["video"]:
        print("Boyut    : %.2f MB" % (plan["video_bayt"] / 1048576))
    print("Kapak    : %s" % (plan["kapak"] or "yok"))
    print("Dil      : %s | AIGC: %s" % (plan["dil"], plan["aigc"]))
    # Öneri SEBEBİYLE birlikte basılıyor: "neden hâlâ SELF_ONLY" sorusunun
    # cevabı bir state alanında saklı kalmasın (bkz. `_kanal_dogrulandi`).
    print("Gizlilik : %s  (%s)" % (
        plan["onerilen_gizlilik"],
        "kanal doğrulandı" if plan["dogrulandi"] else
        "kanal HENÜZ doğrulanmadı — ilk gönderiyi gözle doğrulayıp "
        "`--dogrulandi \"<proje>\"` çalıştır"))
    print("Hazır    : %s%s" % (plan["hazir"], "" if plan["hazir"] else "  <- " + plan["engel"]))
    # Kapı çıktısı caption'dan ÖNCE basılıyor: operatör terminalde önce
    # caption'ı görüp kopyalamaya başlarsa, altta duran "bunu yayınlama"
    # satırını okumadan işi bitirmiş olabiliyor.
    for h in plan["uyumluluk_hatalari"]:
        print("!! ENGEL  : %s" % h)
    for u in plan["uyumluluk_uyarilari"]:
        print("*  UYARI  : %s" % u)
    print("--- caption ---")
    print(plan["caption"])
    if plan["ilk_yorum"]:
        print("--- yayından sonra ilk yorum ---")
        print(plan["ilk_yorum"])


if __name__ == "__main__":
    main()
