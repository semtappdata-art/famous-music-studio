# -*- coding: utf-8 -*-
"""Yükleme isteklerinde ağ hatasını SINIFLANDIRAN tek yardımcı.

NEDEN VAR (2026-09-12): `upload/telegram_upload.py::_api_post`'un docstring'i
ve `seek(0)` mantığı yeniden denemeyi VARSAYIYORDU ama kod ilk ağ
istisnasında `raise` ediyordu; `bluesky_upload.py` ile `facebook_upload.py`'de
ise hiç yeniden deneme YOKTU. Canlı kanıt `auto_process.log` satır 3400:

    [2026-09-11 18:13:19]   Telegram geri doldurma HATA (Beni Bırakma):
    Telegram sendVideo: ağ hatası (ConnectionError)

O yükleme kayboldu ve süpürge bir sonraki koşuda aynı projeyi yeniden
denemeye hazırdı — yani "kayıp" ile "iki kez yayınlandı" arasındaki fark
TAMAMEN şansa bağlıydı.

NAİF DÜZELTME NEDEN YAPILMADI: `sendVideo` (ve `createRecord`, ve
`/{page_id}/videos`) İDEMPOTENT DEĞİL. Bağlantı gövde gönderildikten SONRA
koparsa körü körüne yeniden deneme kanala İKİNCİ bir video atar. Bu, bu
deponun en büyük tekil riskinin ("inauthentic / toplu üretilmiş AI içerik")
ta kendisi — `projects/Küllerimden Geç`in temizliği hâlâ elle yapılıyor.

────────────────────────────────────────────────────────────────────────────
SINIFLANDIRMA — KAYNAK: requests belgeleri (2026-09-12'de okundu)
────────────────────────────────────────────────────────────────────────────
requests'in kendi istisna hiyerarşisi bu ayrımı ZATEN taşıyor
(`requests/exceptions.py`, docstring'ler AYNEN):

  * `ConnectTimeout` — "The request timed out while trying to connect to the
    remote server. **Requests that produced this error are safe to retry.**"
    Yani bağlantı hiç kurulamadı, istek sunucuya ULAŞMADI. → GÜVENLİ.
    (Hiyerarşide hem `ConnectionError` hem `Timeout` altında.)

  * `ReadTimeout` — "The server did not send any data in the allotted amount
    of time." Belgelerin Timeouts bölümü read timeout'un ne zaman başladığını
    söylüyor: "**Once your client has connected to the server and sent the
    HTTP request**, the read timeout is the number of seconds the client will
    wait for the server to send a response." Yani GÖVDE ZATEN GİTTİ; sunucu
    videoyu işlemiş olabilir. → BELİRSİZ, yeniden denemek KOPYA üretir.

  * `ChunkedEncodingError` ("The server declared chunked encoding but sent an
    invalid chunk"), `ContentDecodingError` ("Failed to decode response
    content") — ikisi de YANIT aşamasında; istek işlenmiş. → BELİRSİZ.

  * ÇIPLAK `ConnectionError` ("A Connection error occurred") — İKİ ANLAMLI.
    DNS/bağlantı reddi de buradan gelir (güvenli), gövde gönderilirken gelen
    `ConnectionResetError`/"Connection aborted" da (güvensiz). Belgeler ayrımı
    yapmıyor, o yüzden VARSAYILAN GÜVENSİZ: temkinli taraf, kanalda ikinci bir
    video olmayan taraf. TEK istisna, altında yatan urllib3 istisnası bağlantının
    HİÇ KURULAMADIĞINI söylüyorsa (`NewConnectionError`/`NameResolutionError`/
    `socket.gaierror`) — o zaman istek tel üzerine hiç çıkmamıştır → GÜVENLİ.
    Bu, `auto_process.log`'daki gerçek vakanın (ConnectionError) sınıfı.

  * `SSLError`, `ProxyError` (ikisi de `ConnectionError` altında),
    `TooManyRedirects`, `RetryError` → temkinli: BELİRSİZ.

  * `HTTPError`, `JSONDecodeError`, `InvalidJSONError` → YANIT ALINDI, sonuç
    BİLİNİYOR; bu bir "ağ belirsizliği" değil. Yeniden deneme de çözmez.
    → KALICI (olduğu gibi yukarı).

  * `MissingSchema`/`InvalidSchema`/`InvalidURL`/`URLRequired`/`InvalidHeader`
    — istek HAZIRLANIRKEN, tek bayt gitmeden atılır. Teknik olarak "güvenli"
    ama yeniden denemek ASLA düzeltmez (kod hatası). → KALICI.

httpx (atproto istemcisinin altındaki kütüphane) aynı ayrımı farklı adlarla
taşıyor: `ConnectError`/`ConnectTimeout` = bağlantı kurulamadı (güvenli),
`ReadTimeout`/`ReadError`/`WriteTimeout`/`WriteError`/`RemoteProtocolError` =
istek yolda/işlenmiş olabilir (belirsiz). Sınıflandırma TİP ADINA bakıyor,
kütüphaneyi import ETMİYOR — `atproto` kurulu olmayan bir makinede bu modül
yine de çalışsın diye (bkz. bluesky_upload._import_atproto'nun aynı gerekçesi).

────────────────────────────────────────────────────────────────────────────
BELİRSİZ DURUMDA NE YAPILIYOR — üç seçenekten İKİSİNİN BİRLEŞİMİ
────────────────────────────────────────────────────────────────────────────
1. DOĞRULAYARAK yeniden deneme (`dogrula` geri çağrısı): platforma "bu içerik
   zaten var mı" diye sorulabiliyorsa, yeniden denemeden ÖNCE sorulur.
      * Bluesky: `com.atproto.repo.listRecords` — lexicon'ın kendi tarifi
        "List a range of records in a repository... **Does not require auth**"
        (atproto/lexicons/com/atproto/repo/listRecords.json). Son gönderiler
        okunup metin karşılaştırılabiliyor → doğrulanabilir.
      * Facebook: Reels akışı 3 fazlı ve `video_id` FAZ 1'de sabitleniyor;
        resmî doküman faz 2 için "offset ... unless resuming an interrupted
        upload" diyor ve `GET /{video-id}?fields=status` ile `bytes_transfered`
        sorulabiliyor. Yani faz 2/3'te yeniden deneme AYNI video_id'ye yazar,
        İKİNCİ bir gönderi OLUŞTURAMAZ. Uzun format (`/{page_id}/videos`,
        tek multipart POST) içinse doğrulama `GET /{page_id}/videos` listesi.
      * Telegram: DOĞRULAMA YOK. Bot API'nin yöntem listesinde bir sohbetin
        geçmişini okuyan yöntem (getMessages/getChatHistory) YOK; `getUpdates`
        "New incoming message"/"New incoming channel post" döndürüyor, yani
        botun KENDİ giden mesajını değil. Ayrıca `getUpdates` kuyruğu tüketen
        ve webhook'la çakışan bir çağrı — bir doğrulama aracı değil.
2. Doğrulanamıyorsa: YENİDEN DENEME YOK ama SESSİZ de kalma. state.json'a
   "belirsiz durum" işareti (`yukleme_belirsiz`), log'a satır,
   `notify.uyar_bir_kez` ile koşu başına bir uyarı. Operatör kanala elle bakar.
   Bugünün dersi: sessiz kayıp, gürültülü kayıptan KÖTÜDÜR.

SÜPÜRGE ETKİSİ (bu modülün ikinci yarısı — `kapi()`):
`upload/ek_platform_backfill.eksik_projeler()` ve
`upload/facebook_backfill.eksik_projeler()` bir projeyi "eksik" saymak için
SADECE durum anahtarının (`telegram_message_id` / `bluesky_post_uri` /
`facebook_reels_id`) yokluğuna bakıyor. Belirsiz kalan bir yükleme o anahtarı
YAZMADIĞI için süpürge onu "hiç gitmemiş" görür ve BİR SONRAKİ KOŞUDA YENİDEN
YÜKLER — yani kopyayı süpürge üretir. Kapı bu yüzden İKİ yerde kuruluyor:
  (a) YÜKLEYİCİNİN İÇİNDE (`kapi()`, bu modül): çağıran kim olursa olsun
      (süpürge, process_project, elle çalıştırma) işaret duruyorsa yükleme
      REDDEDİLİR. Bu, yazma iznimizin olduğu dosyalarda kurulabilen ve
      kopyayı GERÇEKTEN önleyen kapı.
  (b) SÜPÜRGENİN İÇİNDE (UYGULANDI, 2026-09-12): `eksik_projeler()` belirsiz
      işaretli projeyi ADAY LİSTESİNE HİÇ ALMIYOR. Hem
      `upload/ek_platform_backfill.py` hem `upload/facebook_backfill.py` bu
      modülden `belirsiz_mi`yi İÇE AKTARIYOR (kopyalamıyor) ve filtre
      zincirlerine `if belirsiz_mi(st, <durum_anahtari>): continue` satırını
      koydu. Olmasaydı (a) her koşuda istisna atar ve `limit=1` olduğu için
      kuyruğun tek slotunu kalıcı olarak yakardı (modülün kendi
      docstring'indeki "tıkaç" tuzağının aynısı).

İŞARET NASIL TEMİZLENİR: operatör kanalda/sayfada gönderiyi görüp karar
verdikten sonra `python upload/ag_yeniden_deneme.py --temizle "<proje>"
--anahtar telegram_message_id` (gönderi YOKSA: yeniden yüklenebilir hâle
gelir) ya da gönderi VARSA aynı komuta `--mesaj-id <id>` eklenir (anahtar
doldurulur, proje "yüklendi" sayılır). İkisi de ELLE — hangi kararın doğru
olduğunu ancak kanala bakan insan bilir.
"""

import argparse
import json
import os
import sys
import time

_UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_UPLOAD_DIR)
for _yol in (_UPLOAD_DIR, _REPO):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import notify
import state_io
from gizli_maskele import maskele_istisna

# ---------------------------------------------------------------------------
# sınıflandırma
# ---------------------------------------------------------------------------

GUVENLI = "guvenli"      # istek sunucuya HİÇ ulaşmadı -> yeniden denemek güvenli
BELIRSIZ = "belirsiz"    # gövde gitmiş olabilir -> yeniden deneme KOPYA üretir
KALICI = "kalici"        # ağ belirsizliği değil (yanıt alındı / kod hatası)

# Tip ADLARIYLA eşleşiyor, kütüphane import EDİLMİYOR: aynı tablo requests,
# httpx, urllib3 ve çıplak socket/OSError için birden çalışsın diye (bkz.
# modül docstring'i). Ad çakışması riski yok — bu adların hepsi ağ katmanına
# özgü.
_GUVENLI_ADLAR = frozenset({
    "ConnectTimeout",        # requests + httpx: "safe to retry" (belgede aynen)
    "ConnectTimeoutError",   # urllib3 karşılığı
    "ConnectError",          # httpx: bağlantı kurulamadı
    "NewConnectionError",    # urllib3: soket hiç açılamadı
    "NameResolutionError",   # urllib3: DNS çözülemedi
    "gaierror",              # socket: DNS çözülemedi
    "ConnectionRefusedError",
})

_BELIRSIZ_ADLAR = frozenset({
    "ReadTimeout",           # istek GÖNDERİLDİKTEN sonra yanıt beklenirken
    "ReadTimeoutError",      # urllib3 karşılığı
    "ReadError",             # httpx karşılığı
    "WriteTimeout",          # httpx: GÖVDE yazılırken -> kısmen gitmiş olabilir
    "WriteError",
    "ChunkedEncodingError",  # yanıt aşaması -> istek işlendi
    "ContentDecodingError",
    "RemoteProtocolError",   # httpx: sunucu bağlantıyı yarıda kesti
    "ConnectionResetError",  # gövde gönderilirken reset
    "ConnectionAbortedError",
    "BrokenPipeError",
    "ProtocolError",         # urllib3: "Connection aborted."
    "ConnectionError",       # ÇİFT ANLAMLI -> temkinli taraf (bkz. docstring)
    "SSLError",
    "ProxyError",
    "TooManyRedirects",
    "RetryError",
    "Timeout",               # çıplak Timeout: hangi faz olduğu belli değil
    "TimeoutError",
})

_KALICI_ADLAR = frozenset({
    "JSONDecodeError",
    "InvalidJSONError",
    "MissingSchema",         # istek hazırlanırken -> yeniden deneme çözmez
    "InvalidSchema",
    "InvalidURL",
    "InvalidProxyURL",
    "URLRequired",
    "InvalidHeader",
    "StreamConsumedError",
    "UnrewindableBodyError",
})

# AD ÇAKIŞMASI TUZAĞI (geliştirme sırasında CANLI yakalandı, 2026-09-12):
# `HTTPError` İKİ ayrı şey. `requests.exceptions.HTTPError` "yanıt alındı,
# 4xx/5xx" demek (KALICI). `urllib3.exceptions.HTTPError` ise urllib3'ün TÜM
# hatalarının TABAN sınıfı — `NewConnectionError` bile ondan türüyor, yani
# çıplak adla eşleştirildiğinde bir DNS hatası "kalıcı" sayılıp yeniden
# denenmiyordu (ilk yazımda tam olarak bu oldu). Bu yüzden `HTTPError`
# MODÜLÜYLE BİRLİKTE eşleşiyor.
_KALICI_TAM_ADLAR = frozenset({
    "requests.exceptions.HTTPError",
    "requests.HTTPError",
    "httpx.HTTPStatusError",
})

# Bu modüllerden gelen istisnaların METNİ log'a HAM olarak yazılmamalı:
# requests/httpx/urllib3 istisnaları mesajlarının içinde TAM istek URL'sini
# taşıyor ve Telegram bot token'ı URL'in YOLUNDA (bkz. gizli_maskele.py'nin
# var olma gerekçesi — 2026-09-04'te gerçekten oldu).
_AG_MODULLERI = ("requests", "urllib3", "httpx", "httpcore", "http.client",
                 "socket", "ssl", "atproto", "aiohttp")


def _zincir(e, derinlik=6):
    """İstisna ve onu SARAN/SARILAN istisnalar (neden zinciri + args).

    NEDEN GEREKLİ: requests, urllib3'ün istisnasını `ConnectionError`e sarıyor
    ve ayrımı taşıyan bilgi (bağlantı HİÇ kurulamadı mı) sadece SARILAN
    istisnada var. `__cause__`/`__context__` her zaman dolmuyor — requests
    sarılanı `args[0]` olarak da taşıyabiliyor, o yüzden üçü de geziliyor.

    `reason` DA GEZİLİYOR ve bu satır olmadan modül yanlış çalışıyordu (canlı
    yakalandı): gerçek bir DNS/bağlantı-reddi hatasının şekli
    `requests.ConnectionError(MaxRetryError(..., reason=NewConnectionError(...)))`
    ve `MaxRetryError` sebebini `args`ta DEĞİL, `reason` ÖZNİTELİĞİNDE tutuyor.
    O yüzden "bağlantı hiç kurulamadı" bilgisi zincirde hiç görünmüyor, ve
    `auto_process.log`'daki gerçek vakanın sınıfı yanlış çıkıyordu.
    """
    gorulen = []
    yigin = [e]
    while yigin and len(gorulen) < derinlik:
        x = yigin.pop(0)
        if x is None or any(x is g for g in gorulen):
            continue
        gorulen.append(x)
        yigin.append(getattr(x, "__cause__", None))
        yigin.append(getattr(x, "__context__", None))
        sebep = getattr(x, "reason", None)      # urllib3.MaxRetryError.reason
        if isinstance(sebep, BaseException):
            yigin.append(sebep)
        for arg in getattr(x, "args", ()) or ():
            if isinstance(arg, BaseException):
                yigin.append(arg)
    return gorulen


def _adlar(e):
    """İstisna zincirindeki tip adları: (çıplak adlar, modüllü tam adlar)."""
    ad_kumesi = set()
    tam_kume = set()
    for x in _zincir(e):
        for tip in type(x).__mro__:
            ad_kumesi.add(tip.__name__)
            tam_kume.add("%s.%s" % (getattr(tip, "__module__", ""), tip.__name__))
    return ad_kumesi, tam_kume


def ag_istisnasi_mi(e) -> bool:
    """Bu istisna bir AĞ katmanı istisnası mı — metni log'a HAM yazılmamalı mı?

    `OSError` de sayılıyor: soket hataları (ConnectionResetError vb.) çıplak
    hâlde OSError alt sınıfıdır ve bazıları yol/adres bilgisi taşır.
    """
    for x in _zincir(e):
        modul = getattr(type(x), "__module__", "") or ""
        if modul.split(".")[0] in _AG_MODULLERI or modul in _AG_MODULLERI:
            return True
        if isinstance(x, OSError):
            return True
    return False


def sinifla(e) -> str:
    """İstisnayı GUVENLI / BELIRSIZ / KALICI olarak sınıflandırır.

    SIRA ÖNEMLİ ve şu gerekçeye dayanıyor:
      1. Önce GÜVENLİ adlar aranır. `ConnectTimeout` hem `ConnectionError`
         hem `Timeout` alt sınıfı; miras zincirine bakıldığında ikisi de
         BELİRSİZ listesinde görünür. En DAR ve en KESİN bilgi (belgede
         "safe to retry" yazan tip) kazanmalı.
      2. Sonra KALICI adlar: yanıt alınmış ya da istek hiç hazırlanamamış.
      3. Sonra BELİRSİZ adlar.
      4. Hiçbiri değilse: ağ istisnasıysa TEMKİNLİ davranıp BELİRSİZ, değilse
         KALICI (bizim kodumuzun hatası — yeniden denemek gizler).
    """
    adlar, tam_adlar = _adlar(e)
    if adlar & _GUVENLI_ADLAR:
        return GUVENLI
    if (adlar & _KALICI_ADLAR) or (tam_adlar & _KALICI_TAM_ADLAR):
        return KALICI
    if adlar & _BELIRSIZ_ADLAR:
        return BELIRSIZ
    return BELIRSIZ if ag_istisnasi_mi(e) else KALICI


# ---------------------------------------------------------------------------
# istisnalar
# ---------------------------------------------------------------------------

class AgHatasi(RuntimeError):
    """Yeniden denendi ve olmadı — ya da kalıcı bir ağ hatası.

    METNİ KASITLI OLARAK FAKİR: sadece "ne yapılıyordu" + istisna TİPİ.
    Orijinal istisnanın metni URL'i (dolayısıyla Telegram bot token'ını)
    taşıyabiliyor; maskelenmiş hâli `ayrinti` alanında duruyor, yazdırmak
    isteyen açıkça ister.
    """

    def __init__(self, ne: str, tip: str, ayrinti: str = "", deneme: int = 1):
        self.ne = ne
        self.tip = tip
        self.ayrinti = ayrinti
        self.deneme = deneme
        super().__init__("%s: ağ hatası (%s), %d denemede gönderilemedi"
                         % (ne, tip, deneme))


class BelirsizSonuc(RuntimeError):
    """Gövde gönderildikten SONRA koptu — gitti mi gitmedi mi BİLİNMİYOR.

    Bu istisna bir "başarısızlık" değil, bir KARAR: yeniden denemiyoruz,
    çünkü denemek kanala ikinci bir kopya atabilir. state.json'a işaret
    bırakılıyor ve operatörün elle bakması isteniyor.
    """

    def __init__(self, ne: str, tip: str, anahtar: str = "", proje: str = ""):
        self.ne = ne
        self.tip = tip
        self.anahtar = anahtar
        self.proje = proje
        super().__init__(
            "%s: gövde gönderildikten SONRA bağlantı koptu (%s) — gidip "
            "gitmediği BİLİNMİYOR, yeniden DENENMEDİ (kopya riski). "
            "Kanalı/sayfayı ELLE kontrol et; ayrıntı: state.json > "
            "yukleme_belirsiz%s"
            % (ne, tip, (" > " + anahtar) if anahtar else ""))


# ---------------------------------------------------------------------------
# "belirsiz durum" işareti (state.json)
# ---------------------------------------------------------------------------

ISARET_ALANI = "yukleme_belirsiz"


def _durum_oku(proje: str) -> dict:
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def belirsiz_mi(durum_veya_proje, anahtar: str):
    """İşaret varsa işaret sözlüğünü, yoksa None döner.

    Hem açılmış bir state sözlüğü hem de proje YOLU kabul ediyor: süpürgeler
    state'i zaten okumuş oluyor (ikinci bir disk okuması gereksiz), yükleyici
    ise elinde yolla çağırıyor.
    """
    durum = (durum_veya_proje if isinstance(durum_veya_proje, dict)
             else _durum_oku(durum_veya_proje))
    isaretler = durum.get(ISARET_ALANI)
    if not isinstance(isaretler, dict):
        return None
    kayit = isaretler.get(anahtar)
    return kayit if isinstance(kayit, dict) and kayit else None


def belirsiz_isaretle(proje: str, anahtar: str, platform: str, ne: str,
                      tip: str, log=print) -> dict:
    """state.json'a "bu yükleme belirsiz kaldı" işaretini ATOMİK yazar.

    `state_io.durum_yaz` kullanılıyor (doğrudan `open(..., "w")` DEĞİL) —
    deponun tek atomik yazıcısı; gerekçe state_io.py'nin docstring'inde.
    """
    durum = _durum_oku(proje)
    isaretler = durum.get(ISARET_ALANI)
    if not isinstance(isaretler, dict):
        isaretler = {}
    kayit = {
        "platform": platform,
        "ne": ne,
        "istisna": tip,
        "zaman": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "not": ("Gövde gönderildikten sonra bağlantı koptu. Gönderi "
                "PLATFORMDA OLABİLİR. Yeniden yükleme BİLEREK engellendi "
                "(kopya riski). Elle kontrol et; sonra "
                "upload/ag_yeniden_deneme.py --temizle ile bu işareti kaldır."),
    }
    isaretler[anahtar] = kayit
    durum[ISARET_ALANI] = isaretler
    state_io.durum_yaz(proje, durum)

    mesaj = ("BELİRSİZ YÜKLEME (%s / %s): %s sırasında bağlantı gövde "
             "gönderildikten SONRA koptu (%s). Gönderi platformda OLABİLİR — "
             "yeniden denenmedi. %s kanalını/sayfasını ELLE kontrol et."
             % (platform, os.path.basename(os.path.normpath(proje)), ne, tip,
                platform))
    try:
        log("  " + mesaj)
    except Exception:
        pass
    # Koşu başına BİR uyarı: süpürge her saat aynı projeye bakıyor, her
    # seferinde telefonu titretmenin anlamı yok (notify.uyar_bir_kez sadece
    # log'a yazar, ağa ÇIKMAZ).
    notify.uyar_bir_kez("belirsiz-%s-%s" % (platform, anahtar), mesaj)
    return kayit


def belirsizi_temizle(proje: str, anahtar: str) -> bool:
    """İşareti kaldırır (operatör elle karar verdikten sonra). True = vardı."""
    durum = _durum_oku(proje)
    isaretler = durum.get(ISARET_ALANI)
    if not isinstance(isaretler, dict) or anahtar not in isaretler:
        return False
    isaretler.pop(anahtar)
    if isaretler:
        durum[ISARET_ALANI] = isaretler
    else:
        durum.pop(ISARET_ALANI, None)
    state_io.durum_yaz(proje, durum)
    return True


def kapi(proje: str, anahtar: str, platform: str) -> None:
    """Belirsiz işareti duruyorsa yüklemeyi REDDEDER (BelirsizSonuc fırlatır).

    NEDEN YÜKLEYİCİNİN İÇİNDE, ÇAĞIRANIN DEĞİL: bu yüklemeyi ÜÇ ayrı yol
    çağırıyor (`auto_process._ek_platformlari_isle`,
    `upload/*_backfill.py` süpürgeleri, elle `--project` çalıştırması) ve
    kapıyı çağıranlara dağıtmak bu deponun CLAUDE.md'sindeki "unutulacak
    liste" tuzağının ta kendisi olurdu. Kapı tek yerde: yüklemenin kendisinde.
    """
    kayit = belirsiz_mi(proje, anahtar)
    if not kayit:
        return
    raise BelirsizSonuc(
        "%s (önceki koşu: %s, %s)" % (platform, kayit.get("ne", "?"),
                                      kayit.get("zaman", "?")),
        kayit.get("istisna", "?"), anahtar, proje)


# ---------------------------------------------------------------------------
# asıl sarmalayıcı
# ---------------------------------------------------------------------------

# `dogrula` geri çağrısı "bilmiyorum" demek istediğinde bunu döner. AYRI bir
# nesne, çünkü `None` "kesinlikle YOK" anlamına geliyor ve ikisini karıştırmak
# tam da üretmemek istediğimiz kopyayı üretirdi.
BILINMIYOR = object()

MAX_DENEME = 3
TABAN_BEKLEME = 2.0


def guvenli_istek(cagri, ne: str, hazirla=None, dogrula=None,
                  belirsiz_guvenli: bool = False, proje: str = "",
                  anahtar: str = "", platform: str = "",
                  max_deneme: int = None, taban_bekleme: float = None,
                  uyu=None, log=print):
    """`cagri()` sonucunu döner; ağ hatasında SINIFA göre davranır.

    Parametreler:
      cagri            : argümansız çağrılabilir — asıl HTTP isteği.
      ne               : insan okunur iş adı ("Telegram sendVideo").
      hazirla          : her denemeden ÖNCE çağrılır (dosyayı seek(0) ile başa
                         sar, dosya nesnesini yeniden aç...). İlk denemede de
                         çağrılır — böylece "yalnızca yeniden denemede
                         hazırlanan" bir yol kalmıyor.
      dogrula          : BELİRSİZ durumda "bu içerik platformda zaten var mı"
                         sorusunu soran geri çağrı. Dönüşü:
                           * bir değer  -> VAR; o değer sonuç olarak döner
                                           (yeniden gönderim YAPILMAZ)
                           * None       -> KESİNLİKLE YOK; yeniden denemek
                                           güvenli hâle gelir
                           * BILINMIYOR -> doğrulanamadı; işaret + istisna
                         Doğrulama çağrısının KENDİSİ patlarsa BILINMIYOR
                         sayılır (temkinli taraf).
      belirsiz_guvenli : bu istek İŞ SEVİYESİNDE idempotent ise True. O zaman
                         BELİRSİZ de GÜVENLİ gibi yeniden denenir. Sadece
                         gerekçesi ÇAĞRI YERİNDE yazılı olan yerlerde kullan
                         (ör. Facebook Reels faz 2/3: video_id faz 1'de
                         sabitlendiği için yeniden deneme ikinci bir gönderi
                         OLUŞTURAMAZ).
      proje/anahtar/platform : verilirse BELİRSİZ durumda state.json'a işaret
                         bırakılır. Verilmezse sadece istisna atılır (işareti
                         çağıran kendi koyar).

    Bekleme: `taban_bekleme * 2**deneme` (2 sn, 4 sn). `uyu` enjekte
    edilebilir — testler gerçekten beklemesin diye.

    VARSAYILANLAR ÇAĞRI ANINDA çözülüyor (imzada `= MAX_DENEME` DEĞİL,
    `= None`): Python varsayılan argümanları TANIM anında bağlıyor, yani
    `MAX_DENEME`/`TABAN_BEKLEME` sabitlerini monkeypatch'lemek hiçbir şeyi
    değiştirmezdi ve testler GERÇEKTEN saniyelerce beklerdi.
    """
    if max_deneme is None:
        max_deneme = MAX_DENEME
    if taban_bekleme is None:
        taban_bekleme = TABAN_BEKLEME
    if uyu is None:
        uyu = time.sleep
    son_tip = "?"
    son_ayrinti = ""
    for deneme in range(max_deneme):
        if hazirla is not None:
            hazirla()
        try:
            return cagri()
        except BelirsizSonuc:
            raise
        except BaseException as e:
            sinif = sinifla(e)
            if sinif == KALICI:
                if ag_istisnasi_mi(e):
                    # HAM metin YASAK (token sızıntısı) — maskelenmiş özet.
                    # `from None`: zincir de yazdırılmasın.
                    raise AgHatasi(ne, type(e).__name__, maskele_istisna(e),
                                   deneme + 1) from None
                raise            # bizim kodumuzun hatası: olduğu gibi yukarı
            son_tip = type(e).__name__
            son_ayrinti = maskele_istisna(e) if ag_istisnasi_mi(e) else str(e)[:200]

            if sinif == BELIRSIZ and not belirsiz_guvenli:
                sonuc = BILINMIYOR
                if dogrula is not None:
                    log("  %s: bağlantı gövdeden SONRA koptu (%s) — yeniden "
                        "denemeden ÖNCE platforma soruluyor..." % (ne, son_tip))
                    try:
                        sonuc = dogrula()
                    except BaseException:
                        # Doğrulama da patladıysa hiçbir şey bilmiyoruz.
                        sonuc = BILINMIYOR
                if sonuc is BILINMIYOR:
                    if proje and anahtar:
                        belirsiz_isaretle(proje, anahtar, platform or ne, ne,
                                          son_tip, log=log)
                    raise BelirsizSonuc(ne, son_tip, anahtar, proje) from None
                if sonuc is not None:
                    log("  %s: doğrulandı — içerik platformda ZATEN VAR, "
                        "yeniden gönderilmedi." % ne)
                    return sonuc
                log("  %s: doğrulandı — içerik platformda YOK, yeniden "
                    "deneniyor." % ne)
                # None: kesinlikle gitmemiş -> aşağıdaki normal yeniden deneme

            if deneme + 1 >= max_deneme:
                raise AgHatasi(ne, son_tip, son_ayrinti, deneme + 1) from None
            bekleme = taban_bekleme * (2 ** deneme)
            log("  %s: ağ hatası (%s) — %.0f sn sonra yeniden deneniyor "
                "(%d/%d)." % (ne, son_tip, bekleme, deneme + 2, max_deneme))
            uyu(bekleme)

    raise AgHatasi(ne, son_tip, son_ayrinti, max_deneme)


# ---------------------------------------------------------------------------
# operatör aracı: işareti görüntüle / temizle
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Belirsiz kalan yükleme işaretlerini gösterir/temizler.")
    ap.add_argument("--proje", help="Proje klasörü (örn. \"projects/Son Kez\")")
    ap.add_argument("--temizle", action="store_true",
                    help="İşareti kaldır (kanalda gönderi YOKSA: yeniden yüklenebilir olur)")
    ap.add_argument("--anahtar", help="Durum anahtarı (örn. telegram_message_id)")
    ap.add_argument("--deger", help="Gönderi VARSA: anahtara yazılacak gerçek "
                                    "id/uri (proje 'yüklendi' sayılır)")
    args = ap.parse_args()

    if not args.proje:
        ap.error("--proje gerekli")
    durum = _durum_oku(args.proje)
    isaretler = durum.get(ISARET_ALANI) or {}
    if not args.temizle:
        print(json.dumps(isaretler, ensure_ascii=False, indent=2))
        return
    if not args.anahtar:
        ap.error("--temizle için --anahtar gerekli")
    if args.deger:
        durum = _durum_oku(args.proje)
        durum[args.anahtar] = args.deger
        state_io.durum_yaz(args.proje, durum)
    vardi = belirsizi_temizle(args.proje, args.anahtar)
    print("işaret %s" % ("kaldırıldı" if vardi else "zaten yoktu"))


if __name__ == "__main__":
    main()
