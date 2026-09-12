"""Render edilmiş bir projeyi Instagram'a Reels olarak yükler (Instagram Graph API).

Kullanım:
    python upload/instagram_upload.py --project "projects/beni bırakma"

ÖNEMLİ — Instagram Graph API dosya upload'ı değil, HERKESE AÇIK bir video_url
bekliyor. İki seçenek var:
  1. --video-url ile zaten barındırılan (örn. bir CDN/hosting'deki) bir URL ver.
  2. upload/netlify_client_secrets.json dosyasını doldur ({"token": "...",
     "site_id": "..."}) — bu durumda script, projedeki shorts_9x16.mp4 dosyasını
     otomatik olarak ayrı bir Netlify sitesine deploy edip URL'i kendisi üretir.
     Bu Netlify sitesi SADECE geçici video barındırma için kullanılmalı (her
     yüklemede içeriğinin tamamen değişmesi beklenir) — famousmusicstudio.com
     ana sitesiyle KARIŞTIRILMAMALI, ayrı bir site olmalı.
"""

import argparse
import hashlib
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io
from gizli_maskele import maskele
from instagram_auth import get_access_token
from social_text import build_caption, build_youtube_comment, resolve_language

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
NETLIFY_SECRETS_PATH = os.path.join(UPLOAD_DIR, "netlify_client_secrets.json")

GRAPH_API = "https://graph.instagram.com/v21.0"

# Instagram konteynerinin ömrü 24 saat; biz 23 saatte bayat sayıyoruz.
# Pay bilerek var: damga YEREL saatle yazılıyor, Instagram'ın saati bizimkiyle
# birebir aynı olmak zorunda değil ve konteyner "24 saat" sınırına dakikalar
# kala yayınlanmaya kalkışılırsa yarış durumu oluşur. 23 saat, golden-hour
# pencereleri arası en kötü aralığı (~14 saat) hâlâ rahatça kapsıyor — yani
# bu kapı GERÇEKTEN bekleyen hiçbir konteyneri erken düşürmez.
KONTEYNER_OMRU_SN = 23 * 3600

# `try_publish_pending()`'in None dönme SEBEPLERİ (bkz. o fonksiyonun
# `sebep_out` parametresi). Çağıran "yayın olmadı"yı tek başına okuyunca
# yanlış yorumluyordu — `auto_process` bunların HEPSİNİ "golden-hour
# bekleniyor" diye logluyordu (2026-09-11: her koşuda 13 satır, gerçekte
# bekleyen tek proje vardı).
SEBEP_YAYINLANDI = "yayinlandi"
SEBEP_BEKLEYEN_YOK = "bekleyen_yok"
SEBEP_ZATEN_YAYINLANMIS = "zaten_yayinlanmis"
SEBEP_BAYAT_TEMIZLENDI = "bayat_temizlendi"
SEBEP_SURESI_DOLDU = "suresi_doldu"
SEBEP_ISLENIYOR = "isleniyor"
SEBEP_GOLDEN_HOUR = "golden_hour_bekleniyor"

# HTTP 5xx + gövdede `is_transient: true` için DAR yeniden deneme penceresi.
# Bekleme listesi TEK kaynak: deneme sayısı ondan türüyor, ikisi birbirinden
# kayamasın diye (`GECICI_5XX_DENEME` elle yazılsaydı bir gün IndexError olurdu).
# En kötü toplam bekleme 8+32 = 40 sn. Tavan bilerek dar: bu dalın tek amacı
# golden-hour penceresinin SON dakikalarına denk gelen geçici bir arızayı
# kurtarmak, pencerenin kalanını beklemeyle yemek değil (bkz. `_graph_istek`).
GECICI_5XX_BEKLEME_SN = (8, 32)
GECICI_5XX_DENEME = len(GECICI_5XX_BEKLEME_SN) + 1   # 1 ilk istek + 2 tekrar

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]


def _en_yeni_kapak(project_dir: str, names: list) -> str | None:
    """Verilen adaylar arasından EN YENİ (mtime) olanı döndürür, birden fazla
    aday varsa UYARI basar.

    NEDEN: eskiden liste sırasıyla İLK eşleşen dönüyordu — yani `cover.jpg`
    her zaman `cover.png`'yi yeniyordu, oysa kapak üreticisi
    (`generate_cover.py`) `cover.png` yazıyor. Bir projede eski bir
    `cover.jpg` kalmışsa yenilenen PNG SESSİZCE yok sayılıyordu; hiçbir hata
    mesajı yoktu. Uyarı satırı bilerek var: asıl arıza yanlış dosyanın
    seçilmesi değil, seçimin sessiz olmasıydı."""
    adaylar = [
        os.path.join(project_dir, ad)
        for ad in names
        if os.path.isfile(os.path.join(project_dir, ad))
    ]
    if not adaylar:
        return None
    # Eşit mtime'da liste sırası korunsun diye sıralama kararlı (stable) kullanılıyor.
    adaylar.sort(key=os.path.getmtime, reverse=True)
    if len(adaylar) > 1:
        digerleri = ", ".join(os.path.basename(p) for p in adaylar[1:])
        print(
            f"  UYARI: birden fazla kapak adayı var ({os.path.basename(project_dir)}), "
            f"en yenisi kullanılıyor: {os.path.basename(adaylar[0])} "
            f"(yok sayılan: {digerleri})"
        )
    return adaylar[0]


def _find_cover(project_dir: str) -> str | None:
    """Reels videosu dikey (9:16) olduğu için önce cover_vertical.*'a bakar —
    onunla üretilmiş kapak Instagram'da tam kadraj kaplar, aksi halde 16:9
    cover.png'ye düşülür (üstte/altta ince bir şerit görünebilir, hiç kapaksız
    kalmaktan iyidir).

    Dikey/yatay TERCİHİ mtime'dan ÖNCE gelir (dikey varsa yatay hiç bakılmaz);
    mtime yalnızca AYNI grup içindeki uzantı çakışmasını (jpg/jpeg/png) çözer."""
    dikey = _en_yeni_kapak(project_dir, COVER_VERTICAL_NAMES)
    if dikey:
        return dikey
    return _en_yeni_kapak(project_dir, COVER_NAMES)


def _gecici_5xx_mi(resp) -> bool:
    """Yanit "Instagram bu istegi ISLEMEDI, tekrar dene" diyor mu.

    IKI kosul BIRDEN aranir: HTTP 5xx **ve** govdede `is_transient: true`.
    Ciplak 5xx TEK BASINA YETMEZ — bunu varsaymak gercek bir arizaya geri
    goturur: bayat (olu) konteynerler de `media_publish` adiminda HTTP 500
    veriyordu (bkz. `_konteyner_bayat()` docstring'i) ve orada tekrar
    denemek sadece bosa API cagrisiydi, cunku hata KALICIYDI. Bu yuzden
    Instagram'in KENDI isaretine guveniliyor; alan yoksa ya da False ise
    yeniden DENEMIYORUZ (eski davranis: aninda hata).

    Meta hata govdesini bazen `{"error": {...}}` icinde sariyor, bazen
    duz veriyor. Uretimde GORULEN gercek govde duz olandi
    (`{"message":"Service temporarily unavailable","is_transient":true,
    "code":2}`, `auto_process.log:3167+`), ama ikisi de kabul ediliyor —
    iki bicimden birini secmek, digeri geldiginde dalin SESSIZCE hic
    calismamasi demekti.

    Govde JSON degilse / sozluk degilse / alan bool True degilse: HAYIR.
    Temkinli taraf = eski davranis."""
    if not 500 <= resp.status_code < 600:
        return False
    try:
        govde = resp.json()
    except (ValueError, TypeError):
        # `requests`in JSONDecodeError'u ValueError'dan tureyor; JSON
        # olmayan bir 5xx govdesi (HTML hata sayfasi, bos yanit) burada.
        return False
    if not isinstance(govde, dict):
        return False
    hata = govde.get("error")
    if isinstance(hata, dict) and hata.get("is_transient") is True:
        return True
    return govde.get("is_transient") is True


def _graph_istek(metot: str, url: str, ne_yapiliyordu: str, **kw) -> requests.Response:
    """Graph API istegi — hata mesajlarinda TOKEN OLMADAN.

    NEDEN VAR (gercek olay, 2026-09-04): bu modulun GET istekleri token'i
    SORGU DIZESINDE tasiyor (`params={"access_token": ...}`). Iki ayri yoldan
    token'i log'a dusuruyordu:
      1. `requests.exceptions.ConnectionError` mesaji TAM istek URL'sini
         iceriyor — `dj_famous_process.log:17`'ye gercek bir Instagram
         token'i tam olarak boyle dustu (ag kesintisi yetti, saldirgan
         gerekmedi).
      2. `resp.raise_for_status()`'in urettigi HTTPError mesaji da
         "... for url: <tam url>" formatinda, yani ayni sizinti.
    Ikisi de burada token'siz bir RuntimeError'a cevriliyor. `from None`:
    orijinal istisna zincire EKLENMIYOR, yoksa traceback'in "During handling
    of the above exception" bolumunde token'li mesaj yine basilirdi.
    Yanit GOVDESI yine de (kirpilmis ve maskelenmis olarak) veriliyor —
    Meta'nin hata kodlari teshis icin gerekli.

    ────────────────────────────────────────────────────────────────────
    DAR YENIDEN DENEME DALI (2026-09-12) — SADECE 5xx + `is_transient`
    ────────────────────────────────────────────────────────────────────
    NEDEN BURADA, `upload/ag_yeniden_deneme.py` MODULUNDE DEGIL: o modul
    TASIMA KATMANI istisnalarini (`requests.exceptions.*`) siniflandiriyor,
    yani "govde tele cikti mi, cikmadi mi" sorusunu cevapliyor. **HTTP 500
    bir istisna DEGIL, BASARIYLA ALINMIS bir yanittir** — `requests` hicbir
    sey firlatmaz, `ag_yeniden_deneme.sinifla()` bu vakayi hic gormez.
    Baska bir soru, baska bir dal; oraya zorla uydurmak iki farkli kavrami
    tek kutuya tikmak olurdu.

    **CIFT YAYIN GUVENLIGI — bu dalin en onemli kisiti.** `media_publish`
    IDEMPOTENT DEGIL: ayni konteyner iki kez yayinlanirsa kanalda ayni Reel
    iki kez cikar (bu deponun en buyuk tekil riski, "inauthentic / toplu
    uretilmis AI icerik"). Ayrim TEK cumlede:
      * Sunucudan TAM bir HTTP yanit geldi, kodu 5xx, govdesi
        `is_transient: true` -> Instagram istegi ISLEMEDIGINI KENDISI
        soyluyor. Yayin olusmadi, tekrar guvenli. -> BU DAL.
      * Baglanti koptu / zaman asimi (yanit KAYBOLDU) -> istek islenmis
        OLABILIR, bilmiyoruz. -> asagidaki `except RequestException`
        dali; orasi HIC yeniden denemiyor ve BILEREK oyle kaliyor.
    Yani tasima katmani tekrari EKLENMEDI; retry'a girmenin on sarti tam
    bir yanit almis olmak. (Kanit: `tests/test_instagram_gecici_hata.py`,
    `test_media_publish_baglanti_hatasinda_TEK_cagri`.)

    4xx'e DOKUNULMUYOR: 400/401/403 kimlik, izin, kota ve politika
    hatalaridir; tekrar denemek kotayi yakar ve hiz sinirina takar. Govdede
    `is_transient` yazsa bile 4xx bu dala GIRMEZ.

    NEDEN BU KADAR DAR (olcum, 2026-09-12): tum log gecmisinde TOPLAM 8
    adet 5xx var, hepsi 2026-09-11'de, golden-hour saatlerinde tam ikiser —
    iki BAYAT konteynerin imzasi. O ariza kaynagindan kesildi (23 saatlik
    yas kapisi, `_konteyner_bayat()`); TAZE bir konteyner bugune kadar HIC
    500 yemedi. Yani aci bir yangin yok. Kapatilan risk tek: golden-hour
    penceresinin sonuna dakikalar kala (or. 21:12, pencere 22:00'de
    kapaniyor) gelen GERCEK bir gecici 500'un dogal tekrar sansi kalmiyor
    ve o yayin GUNU kaciriyor. Bu yuzden bekleme tavani dar tutuldu
    (en kotu 40 sn) ve jitter/backoff buyutme/pencere kontrolu
    EKLENMEDI — pencere kenari disinda kazanci yok."""
    for deneme in range(GECICI_5XX_DENEME):
        try:
            resp = requests.request(metot, url, **kw)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Instagram {ne_yapiliyordu}: ağ hatası ({type(e).__name__})"
            ) from None
        if resp.status_code < 400:
            return resp
        if _gecici_5xx_mi(resp) and deneme < GECICI_5XX_DENEME - 1:
            bekleme = GECICI_5XX_BEKLEME_SN[deneme]
            # Log satiri bilerek var: sessizce yeniden deneyen bir koruma,
            # calismadigini kimseye soylemez (CLAUDE.md, "sessiz ariza").
            print(f"  UYARI: Instagram {ne_yapiliyordu}: HTTP {resp.status_code} "
                  f"geçici hata (is_transient), {bekleme} sn sonra yeniden "
                  f"deneniyor ({deneme + 2}/{GECICI_5XX_DENEME})")
            time.sleep(bekleme)
            continue
        raise RuntimeError(
            f"Instagram {ne_yapiliyordu}: HTTP {resp.status_code} — "
            f"{maskele(resp.text[:300])}"
        )
    # Ulasilamaz: dongunun son turu ya `return` eder ya `raise`. Yine de
    # sessiz bir `None` donmesin diye acik birakilmiyor.
    raise RuntimeError(f"Instagram {ne_yapiliyordu}: beklenmeyen döngü çıkışı")


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _upload_to_netlify(file_paths: list[str]) -> dict[str, str]:
    """Verilen dosyaları (ör. video + kapak) AYNI 'sadece medya' Netlify
    deploy'unda birlikte yükler, dosya adı -> public URL sözlüğü döner.
    netlify_client_secrets.json gerektirir.

    ÖNEMLİ: Dosyalar TEK bir deploy'da birlikte gönderilmeli — Netlify'ın
    digest deploy'u her deploy'u sitenin İÇERİĞİNİN TAMAMI olarak ele alıyor,
    yani video ayrı bir deploy'da, kapak ayrı bir deploy'da gönderilirse
    İKİNCİ deploy videoyu siteden KALDIRIR (sadece kendi dosyasını içerir).
    Instagram video_url'i asenkron işlerken (bkz. status_code polling) video
    o sırada Netlify'da artık bulunamaz. Bu yüzden bu fonksiyon çoklu dosya
    kabul ediyor, çağıran video+kapağı TEK çağrıda birlikte göndermeli.

    NOT: Önceden burada ham bir zip'i `Content-Type: application/zip` ile tek
    POST'ta göndermeyi deniyorduk (Netlify'ın "one-off deploy" yöntemi) — ama
    gerçek kullanımda Netlify bunu zip olarak AÇMADI, tüm içeriği tek, yanlış
    mime type'lı ("text/plain") bir kök (`/`) dosyası olarak kaydetti, video
    hiçbir zaman gerçek dosya adıyla erişilebilir olmadı. Onun yerine Netlify'ın
    "digest deploy" API'si kullanılıyor (dosya yolu + SHA1 hash'i JSON ile
    bildirilip, Netlify içeriği zaten önbelleğinde tutmuyorsa dosya ayrıca PUT
    edilir) — bu, Netlify'ın kendi web arayüzündeki (sürükle-bırak) yöntemle
    aynı ve bu projede elle doğrulanmış şekilde çalışıyor."""
    if not os.path.isfile(NETLIFY_SECRETS_PATH):
        raise FileNotFoundError(
            f"{NETLIFY_SECRETS_PATH} bulunamadı ve --video-url verilmedi.\n"
            "Ya --video-url ile herkese açık bir video linki ver, ya da Netlify'da "
            "ayrı bir 'medya' sitesi oluşturup token/site_id'sini şu formatta kaydet:\n"
            '{"token": "...", "site_id": "..."}'
        )
    with open(NETLIFY_SECRETS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)

    contents: dict[str, bytes] = {}
    sha1s: dict[str, str] = {}
    for path in file_paths:
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            content = f.read()
        contents[filename] = content
        sha1s[filename] = hashlib.sha1(content).hexdigest()

    auth_headers = {"Authorization": f"Bearer {creds['token']}"}

    create_resp = requests.post(
        f"https://api.netlify.com/api/v1/sites/{creds['site_id']}/deploys",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"files": {f"/{name}": sha for name, sha in sha1s.items()}},
        timeout=(10, 30),
    )
    create_resp.raise_for_status()
    deploy = create_resp.json()
    deploy_id = deploy["id"]

    # Netlify aynı içeriği (aynı SHA1) daha önce görmediyse dosyayı ayrıca yükle.
    required_shas = set(deploy.get("required") or [])
    for name, content in contents.items():
        if sha1s[name] in required_shas:
            upload_resp = requests.put(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{name}",
                headers={**auth_headers, "Content-Type": "application/octet-stream"},
                data=content,
                timeout=(10, 300),
            )
            upload_resp.raise_for_status()

    # Deploy 'ready' olana kadar bekle
    status_resp = None
    for _ in range(30):
        status_resp = requests.get(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}",
            headers=auth_headers,
            timeout=(10, 30),
        )
        status_resp.raise_for_status()
        if status_resp.json().get("state") == "ready":
            break
        time.sleep(2)
    else:
        raise RuntimeError("Netlify deploy zaman aşımına uğradı.")

    base_url = status_resp.json()["ssl_url"]
    return {name: f"{base_url}/{name}" for name in contents}


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(project_dir: str, updates: dict) -> None:
    """state.json'a alan ekler/gunceller — ATOMIK (state_io.durum_yaz).

    NEDEN: eskiden hedefin USTUNE dogrudan yaziliyordu; `open(..., "w")`
    dosyayi once SIFIRLIYOR, `json.dump` bitmeden surec olurse diskte YARIM
    bir JSON kaliyor ve `uyumluluk._durum()` sertlestirildikten sonra bozuk
    bir state.json boru hattini DURDURUYOR. Ayrica `auto_process` (saatlik)
    ile `dj_famous_process` (haftalik) AYRI kilitler kullanip ayni dosyaya
    yazabiliyor; kaybolan bir `instagram_media_id` bu platformda IKINCI bir
    gonderi demek."""
    state = _load_state(project_dir)
    state.update(updates)
    state_io.durum_yaz(project_dir, state)


def _konteyner_yayindan_yeni(state: dict) -> bool:
    """Bekleyen konteyner, kayitli SON yayindan SONRA mi olusturuldu.

    NEDEN VAR (gercek ariza): "kapak tasarimi degisti, yeniden paylas"
    senaryosunda yeni bir konteyner olusturuluyor ama state'te ESKI gonderinin
    `instagram_media_id`'si duruyor. `try_publish_pending()` eskiden sadece
    "media_id var mi" diye bakiyordu, yani eski gonderinin VARLIGI yeni
    konteyneri KALICI OLARAK bloke ediyordu — `projects/Gece Surusu` ve
    `projects/Kalbim Oynuyor`da 05 Eylul'de olusturulan konteynerler hic
    yayinlanmadi, log'da 6 gun boyunca yanlislikla "golden-hour bekleniyor"
    yazdi.

    Cift yayin korumasini KIRMIYORUZ, sadece dogru soruyu soruyoruz:
    "bu konteyner, en son yayinladigimiz seyden DAHA YENI mi?". Damgalar
    `%Y-%m-%dT%H:%M:%S` sabit genisliginde oldugu icin metin karsilastirmasi
    tarih karsilastirmasiyla ayni sonucu verir (sifir dolgulu, buyukten
    kucuge siralı alanlar).

    DAMGA YOKSA TEMKINLI DAVRANILIR (False): eski state.json'larda
    `instagram_container_created_at` alani hic yoktu; "bilmiyorum"u
    "yayinla"ya cevirmek sessizce yinelenen gonderi uretirdi."""
    olusturuldu = state.get("instagram_container_created_at")
    yayinlandi = state.get("instagram_uploaded_at")
    if not olusturuldu or not yayinlandi:
        return False
    return str(olusturuldu) > str(yayinlandi)


def _konteyner_yasi_sn(state: dict, simdi: float | None = None) -> float | None:
    """Bekleyen konteynerin saniye cinsinden yasi; damga yoksa/bozuksa None.

    Damgalar `time.strftime("%Y-%m-%dT%H:%M:%S")` ile YEREL saatte yaziliyor,
    bu yuzden geri okurken de yerel saat kullaniliyor (`time.mktime`).
    `strptime` bos/bozuk metinde ValueError firlatir — o durumda "bilmiyorum"
    demek icin None donuyoruz, tahmin YURUTMUYORUZ."""
    olusturuldu = state.get("instagram_container_created_at")
    if not olusturuldu:
        return None
    try:
        epoch = time.mktime(time.strptime(str(olusturuldu), "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError, OverflowError):
        return None
    return (simdi if simdi is not None else time.time()) - epoch


def _konteyner_bayat(state: dict, simdi: float | None = None) -> bool:
    """Bekleyen konteyner Instagram'in 24 saatlik omrunu asmis mi (YAS KAPISI).

    NEDEN VAR (gercek ariza, 2026-09-11): `projects/Gece Surusu` ve
    `projects/Kalbim Oynuyor` state'lerinde 05 Eylul damgali konteynerler
    vardi, yayin damgalari 01 Eylul'du — yani `_konteyner_yayindan_yeni()`
    True donuyor ve her golden-hour'da yayin deneniyordu. Konteynerler
    7 GUNLUKTU, coktan olmuslerdi; ama Instagram `status_code` olarak
    **EXPIRED DONDURMUYOR** (donduruyor olsaydi asagidaki EXPIRED dali
    temizlerdi). Bunun yerine `media_publish` adiminda HTTP 500
    `{"message":"Service temporarily unavailable","is_transient":true,
    "code":2}` veriyor — "gecici" diyen, aslinda KALICI bir hata. Sonuc:
    her golden-hour saatinde 2 bosa API cagrisi, 11 Eylul'de 8 hata
    (`auto_process.log:3167+`), ve kendiliginden ASLA duzelmiyor.

    Yani `status_code`'a guvenilemez; tek saglam olcut bizim kendi
    yazdigimiz `instagram_container_created_at` damgasi. Kapi Graph API
    cagrisindan ONCE calisir: olu bir konteyner icin token alip aga gitmenin
    hicbir faydasi yok.

    DAMGA YOKSA/BOZUKSA TEMKINLI DAVRANILIR (False): yas bilinmiyorsa bayat
    SAYMIYORUZ — "bilmiyorum"u "sil"e cevirmek, gercekten bekleyen bir
    konteyneri sessizce dusurup gonderiyi hic yayinlamamak demekti."""
    yas = _konteyner_yasi_sn(state, simdi)
    if yas is None:
        return False
    return yas > KONTEYNER_OMRU_SN


def _bekleyen_konteyneri_temizle(project_dir: str, state: dict, creation_id: str, gerekce: str) -> None:
    """Olu bir konteynerin kaydini state'ten siler — TEK temizleme yolu.

    Hem yas kapisi hem EXPIRED dali buradan geciyor: iki yerde ayni uc satiri
    tekrarlamak, birinin ilerde `instagram_container_created_at`'i silmeyi
    unutmasi demekti (damga kalirsa `_konteyner_yayindan_yeni()` yanlis cevap
    verir). Yazim ATOMIK (`state_io.durum_yaz`, bkz. `_save_state`)."""
    print(f"  Instagram: bekleyen konteyner (creation_id={creation_id}) {gerekce}, "
          "kaydı temizleniyor")
    state.pop("instagram_creation_id", None)
    state.pop("instagram_container_created_at", None)
    state_io.durum_yaz(project_dir, state)
    # DIKKAT: yeni konteyneri BU fonksiyon olusturmuyor, `upload_video()`
    # olusturuyor. Zaten yayinlanmis (instagram_media_id dolu) bir proje
    # `auto_process._is_fully_done()` acisindan "bitmis" sayildigi icin
    # batch'e HIC girmez, yani otomatik yeniden denenmez — bu bilincli:
    # yeniden paylasim hacim etkisi olan bir karar, kendiliginden
    # tetiklenmemeli. Operatore ne yapacagini soyluyoruz.
    if state.get("instagram_media_id"):
        print(f"     Yeniden paylaşmak istiyorsan: "
              f'python upload/instagram_upload.py --project "{project_dir}"')


def _sebep_yaz(sebep_out: dict | None, kod: str) -> None:
    """`try_publish_pending()`'in sebep kodunu (varsa) cagirana bildirir."""
    if sebep_out is not None:
        sebep_out["kod"] = kod


def _publish_container(ig_user_id: str, access_token: str, creation_id: str, project_dir: str) -> str:
    """Hazır (status_code=FINISHED) bir konteyneri yayınlar, YouTube linki
    yorumunu ekler, state'i günceller. media_id döner."""
    publish_resp = _graph_istek(
        "POST",
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        "yayınlama (media_publish)",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=(10, 30),
    )
    media_id = publish_resp.json()["id"]
    print(f"  tamam: media_id={media_id}")

    # YouTube linki caption'a DEĞİL, paylaşımdan SONRA bir yoruma ekleniyor — bkz.
    # social_text.build_caption()'daki not. Yorum başarısız olsa bile ana yükleme
    # zaten tamamlandığı için hata fırlatmıyoruz, sadece logluyoruz.
    video_id = _load_state(project_dir).get("youtube_video_id")
    if video_id:
        lang = resolve_language(_load_meta(project_dir))
        try:
            comment_resp = _graph_istek(
                "POST",
                f"{GRAPH_API}/{media_id}/comments",
                "YouTube linki yorumu",
                data={"message": build_youtube_comment(f"https://youtu.be/{video_id}", lang, platform="instagram"), "access_token": access_token},
                timeout=(10, 30),
            )
            print(f"  YouTube linki yorum olarak eklendi: {comment_resp.json().get('id')}")
        except (RuntimeError, requests.exceptions.RequestException) as e:
            # RuntimeError da yakalaniyor: _graph_istek ag/HTTP hatalarini
            # token'siz bir RuntimeError'a ceviriyor (bkz. o fonksiyon).
            # Yorum basarisiz olsa bile ana yukleme tamamlandi, patlatmiyoruz.
            print(f"  UYARI: YouTube linki yorumu eklenemedi: {maskele(str(e))}")

    # Yayinlanan konteynerin kaydi SILINIYOR (sadece uzerine yazilmiyor).
    # NEDEN: bir konteyner tek kullanimlik — yayinlandiktan sonra state'te
    # durmasi "bekleyen is var" gibi gorunuyor ve `auto_process`'in
    # golden-hour kuyrugu her kosuda bosuna Graph API'ye gidiyordu. Temiz
    # state ayrica `_konteyner_yayindan_yeni()`yi tek anlamli kiliyor:
    # state'te bir creation_id varsa GERCEKTEN bekleyen bir yayin vardir.
    state = _load_state(project_dir)
    state.pop("instagram_creation_id", None)
    state.pop("instagram_container_created_at", None)
    state["instagram_media_id"] = media_id
    state["instagram_uploaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state_io.durum_yaz(project_dir, state)
    return media_id


def try_publish_pending(project_dir: str, sebep_out: dict | None = None) -> str | None:
    """state.json'da bekleyen (henüz yayınlanmamış) bir instagram_creation_id
    varsa kontrol eder: konteyner hâlâ işleniyorsa ya da golden-hour dışındaysak
    None döner (bir sonraki çalıştırmada tekrar denenir). Konteynerin süresi
    dolmuşsa (Instagram: 24 saat) bekleyen kaydı temizler — upload_video() bir
    sonraki çağrıda sıfırdan yeni bir konteyner oluşturur. Golden-hour
    penceresindeyse ve konteyner hazırsa yayınlar, media_id döner.

    Zaten yayınlanmış bir gönderi (instagram_media_id) varken de çalışır —
    AMA sadece bekleyen konteyner o yayından SONRA oluşturulmuşsa
    (bkz. _konteyner_yayindan_yeni). Bu, "kapak değişti, yeniden paylaş"
    senaryosunun kalıcı olarak tıkanmasını düzeltiyor; damgalar eksikse
    temkinli davranıp yayınlamıyor.

    `sebep_out` (opsiyonel, sozluk): verilirse `sebep_out["kod"]`e None'in
    SEBEBI yazilir (SEBEP_* sabitleri). GERIYE UYUMLU bir cikis kapisi olarak
    eklendi — donus turunu degistirmek `auto_process.py`, `dj_famous_process.py`,
    bu modulun kendi CLI'i ve testlerdeki tum cagri noktalarini bozardi.
    NEDEN GEREKTI: "None" bu fonksiyonda ALTI farkli sey demek ve cagiran
    hepsini "golden-hour bekleniyor" diye logluyordu; ayni satir bir kez
    (2026-09-05..11) 6 gun yanlis okundu, sonra ters yonden geri geldi —
    yayinlanmis projelerdeki bayat kayit yuzunden her kosuda 13 kez basiliyor
    ama gercekte bekleyen TEK proje vardi."""
    state = _load_state(project_dir)
    creation_id = state.get("instagram_creation_id")
    if not creation_id:
        _sebep_yaz(sebep_out, SEBEP_BEKLEYEN_YOK)
        return None

    # YAS KAPISI — `_konteyner_yayindan_yeni()` ve Graph API'den ONCE.
    # SIRA BILINCLI: bu kapi en basta oldugu icin, konteyner son yayindan
    # yeni OLMASA bile (yani asagidaki cift-yayin korumasindan cikilacak
    # olsa bile) olu kayit temizleniyor. Kapi asagida olsaydi o kayitlar
    # state'te SONSUZA KADAR kalir ve `auto_process` onlari her kosuda
    # "bekleyen konteyner" sanmaya devam ederdi (Ariza B'nin ta kendisi).
    # Neden `status_code`'a guvenmiyoruz: bkz. `_konteyner_bayat()`.
    if _konteyner_bayat(state):
        _bekleyen_konteyneri_temizle(
            project_dir, state, creation_id,
            f"24 saatlik ömrünü aşmış (bayat, {KONTEYNER_OMRU_SN // 3600} saat kapısı)")
        _sebep_yaz(sebep_out, SEBEP_BAYAT_TEMIZLENDI)
        return None

    # ESKIDEN: `if not creation_id or state.get("instagram_media_id")`.
    # O kapi "ayni seyi iki kez yayinlama" icin dogruydu ama YANLIS soruyu
    # soruyordu: eski bir gonderinin VARLIGI, sonradan olusturulmus YENI bir
    # konteyneri kalici olarak blokluyordu (bkz. _konteyner_yayindan_yeni()
    # docstring'i — Gece Surusu / Kalbim Oynuyor, 6 gun yayinlanamadi).
    # Cift yayin korumasi duruyor: konteyner son yayindan YENI degilse
    # (ya da damgalar eksikse) hala cikiyoruz.
    if state.get("instagram_media_id") and not _konteyner_yayindan_yeni(state):
        _sebep_yaz(sebep_out, SEBEP_ZATEN_YAYINLANMIS)
        return None

    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    status_resp = _graph_istek(
        "GET",
        f"{GRAPH_API}/{creation_id}",
        "konteyner durumu",
        params={"fields": "status_code", "access_token": access_token},
        timeout=(10, 30),
    )
    status_code = status_resp.json().get("status_code")

    if status_code == "EXPIRED":
        # Instagram'in KENDI soyledigi sureli dolma. Yukaridaki yas kapisiyla
        # AYNI temizleme yolunu kullaniyor; bu dal, damgasi olmayan (eski)
        # state'ler icin hala tek emniyet agi.
        _bekleyen_konteyneri_temizle(
            project_dir, state, creation_id, "süresi dolmuş (EXPIRED, 24 saat)")
        _sebep_yaz(sebep_out, SEBEP_SURESI_DOLDU)
        return None
    if status_code == "ERROR":
        raise RuntimeError(f"Instagram video işleme hatası: {status_resp.json()}")
    if status_code != "FINISHED":
        print(f"  Instagram: konteyner hâlâ işleniyor ({status_code}), bir sonraki kontrolde tekrar denenecek")
        _sebep_yaz(sebep_out, SEBEP_ISLENIYOR)
        return None

    if config.next_golden_publish_time() is not None:
        print(f"  Instagram: konteyner hazır (creation_id={creation_id}), golden-hour penceresi bekleniyor")
        _sebep_yaz(sebep_out, SEBEP_GOLDEN_HOUR)
        return None

    print(f"  Instagram: golden-hour penceresi, yayınlanıyor (creation_id={creation_id})")
    media_id = _publish_container(ig_user_id, access_token, creation_id, project_dir)
    _sebep_yaz(sebep_out, SEBEP_YAYINLANDI)
    return media_id


def upload_video(project_dir: str, video_url: str | None = None, caption: str | None = None) -> str | None:
    """Konteyneri oluşturur ve FINISHED olana kadar bekler, sonra:
    - şu an bir golden-hour penceresindeysek HEMEN yayınlar, media_id döner;
    - değilse konteyneri (instagram_creation_id) state.json'a kaydedip None
      döner — bir sonraki çalıştırma (auto_process.py, saatlik) golden-hour'a
      girdiğimizde try_publish_pending() ile bunu bulup yayınlar. Amaç: render/
      upload anı ile Instagram'da CANLIYA ÇIKTIĞI an ayrılsın (YouTube'un
      publishAt'iyle aynı fikir — ama Instagram Graph API'de native zamanlanmış
      yayın YOK, bu yüzden kendi golden-hour kuyruğumuzu tutuyoruz)."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    # cover_url: verilmezse Instagram video_url'in ilk karesini (thumb_offset=0)
    # kullanıyor — YouTube'da tespit edilen aynı sorun (başlıksız/rastgele kare)
    # burada da geçerliydi. video + kapak TEK Netlify deploy'unda birlikte
    # yükleniyor (bkz. _upload_to_netlify'daki not — ayrı deploy'lar birbirini siler).
    cover_url = None
    cover_path = _find_cover(project_dir)

    if video_url is None:
        to_deploy = [video_path] + ([cover_path] if cover_path else [])
        print("  Netlify'a yükleniyor...")
        urls = _upload_to_netlify(to_deploy)
        video_url = urls[os.path.basename(video_path)]
        print(f"  video yüklendi: {video_url}")
        if cover_path:
            cover_url = urls.get(os.path.basename(cover_path))
            print(f"  kapak yüklendi: {cover_url}")
    elif cover_path:
        # video_url dışarıdan verildi (--video-url) ama kapak yine de Netlify'a
        # gidebilir — burada tek dosya olduğu için "başka bir dosyayı silme"
        # riski yok.
        try:
            urls = _upload_to_netlify([cover_path])
            cover_url = urls[os.path.basename(cover_path)]
            print(f"  kapak yüklendi: {cover_url}")
        except Exception as e:
            print(f"  UYARI: kapak yüklenemedi, Instagram varsayılan kareyi kullanacak: {e}")

    if caption is None:
        meta = _load_meta(project_dir)
        caption = build_caption(meta)

    # AÇIK MADDE: Meta, gerçekçi AI-üretimi içerik için "AI Info" etiketlemesini
    # zorunlu kılıyor (about.fb.com/news/2024/02 ve 2024/04 duyuruları). Graph API
    # media endpoint'inde buna karşılık gelen resmi alan adı bu depoda DOĞRULANAMADI
    # (developers.facebook.com'a bu ortamdan erişilemedi) — ikincil kaynaklarda
    # `is_ai_generated` benzeri bir alan geçiyor ama teyitsiz. Yanlış alan adını
    # buraya eklemek her yüklemede API hatasına yol açabileceği için BİLEREK
    # eklenmedi — resmi dokümantasyondan doğrulanınca buraya eklenmeli.

    # 1) Media container olustur
    media_data = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    }
    if cover_url:
        media_data["cover_url"] = cover_url
    create_resp = _graph_istek(
        "POST",
        f"{GRAPH_API}/{ig_user_id}/media",
        "konteyner oluşturma",
        data=media_data,
        timeout=(10, 30),
    )
    creation_id = create_resp.json()["id"]

    # 2) Container video islenene kadar bekle (status_code: FINISHED)
    print(f"  işleniyor: creation_id={creation_id}")
    for _ in range(60):
        time.sleep(5)
        status_resp = _graph_istek(
            "GET",
            f"{GRAPH_API}/{creation_id}",
            "konteyner durumu",
            params={"fields": "status_code", "access_token": access_token},
            timeout=(10, 30),
        )
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"Instagram video işleme hatası: {status_resp.json()}")
    else:
        raise RuntimeError("Instagram video işleme zaman aşımına uğradı.")

    # Konteyner hazır — creation_id'yi HEMEN state'e kaydet (golden-hour
    # bekleniyorsa bile kaybolmasın; try_publish_pending() bunu bulup bir
    # sonraki pencerede yayınlayacak, konteyner tekrar oluşturulmayacak).
    _save_state(project_dir, {
        "instagram_creation_id": creation_id,
        "instagram_container_created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })

    if config.next_golden_publish_time() is not None:
        print(f"  Instagram: konteyner hazır (creation_id={creation_id}), golden-hour penceresi bekleniyor")
        return None

    return _publish_container(ig_user_id, access_token, creation_id, project_dir)


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi Instagram'a Reels olarak yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument("--video-url", default=None, help="Herkese açık video URL'si (verilmezse Netlify'a otomatik yüklenir)")
    parser.add_argument("--caption", default=None, help="Gönderi açıklaması (verilmezse meta.json'daki title kullanılır)")
    args = parser.parse_args()

    upload_video(args.project, args.video_url, args.caption)


if __name__ == "__main__":
    main()
