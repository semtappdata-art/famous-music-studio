# -*- coding: utf-8 -*-
"""Log'a/diske yazilacak metinlerden kimlik bilgisi (token/secret) maskeleyen
TEK yardimci.

NEDEN VAR (gercek olay, 2026-09-04): `dj_famous_process.log` satir 17'de
GERCEK bir Instagram erisim token'i bulundu. Saldirgan yok, exploit yok —
sadece bir ag kesintisi vardi. Zincir su:

    requests.get(GRAPH_API + "/<id>", params={"access_token": TOKEN, ...})
      -> requests.exceptions.ConnectionError
      -> str(e) ICINDE TAM ISTEK URL'i var (sorgu dizesiyle birlikte)
      -> log(f"  Instagram HATA: {e}")  -> token duz metin olarak diske

Yani "ag hatasi = token log'da". Instagram/Facebook token'i sorgu dizesinde
gittigi icin bu, istisna metnini loglayan HER cagri noktasi icin gecerli.
Ayni sinifin bir sonraki kurbani hazirdi: `upload/telegram_upload.py`
`_api_post` URL'i `{API_BASE}/bot{bot_token}/{method}` kuruyor — bot token
YOLUN ICINDE, yani bir ConnectionError/ReadTimeout onu da log'a dusururdu.
Bot token tek basina kanala mesaj gondermeye/silmeye yeter.

YENI (2026-10-03): Dağıtız izleme (distributed tracing) desteği eklendi.
Her auto_process.py çalıştırması için trace ID oluşturulur ve önemli işlemler
için span ID'leri eklenir. Bu, sistemin davranışını analiz etmeyi ve 
performans bottleneck'lerini tanımlamayı mümkün kılar.

NEDEN AYRI MODUL:
  - `notify.py` telefona push gondermenin yeri, metin temizligi oraya ait
    degil.
  - `log_rotate.py` zamana gore log budamanin yeri; maskeleme zamandan
    bagimsiz bir sorumluluk (ve `log_rotate` bunu KULLANIYOR, tersi degil).
  - `config.py` gorunum/kalite ayarlarinin yeri.
  - `upload/` altindaki moduller de (telegram/facebook/instagram) ayni
    fonksiyonu cekmek zorunda; depo kokunde kucuk, bagimsiz bir modul
    `state_io.py` ile AYNI desende (bugun ayni gerekceyle oyle eklendi) her
    iki taraftan da import edilebiliyor.

KULLANIM:
    from gizli_maskele import maskele, maskele_istisna
    log(f"  Instagram HATA: {maskele_istisna(e)}")

TASARIM NOTU — neden "beyaz liste" degil de desen listesi: log satirlarinin
cogu normal Turkce metin; her seyi maskelemek log'u okunamaz yapar. Bu yuzden
sadece BILINEN kimlik bilgisi sekilleri hedefleniyor ve `tests/
test_gizli_maskele.py` yanlis pozitif uretmedigini de dogruluyor.
"""

import json
import os
import json
import os
import re

MASKE = "…[MASKELİ]"
# LOG_PATH tanımlaması - auto_process.py ile aynı dosyayı kullan
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_process.log")
# Zaten maskelenmiş bir değeri tanımak için (bkz. _anahtar_esittir).
_MASKE_BASI = MASKE[0]

# Bu anahtarlardan sonra gelen deger her zaman gizlidir. `authorization` ve
# `code_verifier` de burada: OAuth akislarinda ikisi de tek basina yeterli.
_ANAHTARLAR = (
    "access_token",
    "input_token",
    "page_access_token",
    "user_access_token",
    "client_secret",
    "app_secret",
    "refresh_token",
    "bot_token",
    "app_password",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "session_token",
    "code_verifier",
    "id_token",
    # CIPLAK `token` (2026-09-11): `upload/netlify_client_secrets.json`'in
    # anahtari duz `"token"` ve bu liste onu KAPSAMIYORDU, yani
    # `{"token": "nfp_..."}` maskelenmeden gecebiliyordu. Netlify hatti bugun
    # `saglik_kontrol.netlify_araci()` ile SAATLIK kosuya baglandi — o kimlik
    # bilgisi artik uretim hattinda her saat dolasiyor.
    # YANLIS POZITIF NEDEN YOK: desenlerin hepsi anahtari ya `=` (sorgu
    # dizesi) ya da tirnak + `:` (JSON/dict) ile ARIYOR ve basinda `\b` var.
    # Depodaki gercek log satirlari bu bicimlerin HICBIRINE uymuyor:
    # "upload/token.json yok", "tiktok_token.json yok",
    # "youtube_captions_token_yok", "Instagram token'inin suresi ~12 gun" —
    # `token`dan hemen sonra `.`/` `/`_`/`'` geliyor. `instagram_token=` gibi
    # ON EKLI adlar da `\b` yuzunden bu kurala TAKILMAZ (onlar zaten kendi
    # adlariyla listede). Kanit: tests/test_gizli_maskele_token.py.
    "token",
)

_ANAHTAR_ALT = "|".join(_ANAHTARLAR)

# LOG_PATH tanımlaması - auto_process.py ile aynı dosyayı kullan
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_process.log")

# Dağıtız izleme (distributed tracing) için thread-local depolama
import threading
import uuid
import time

_trace_context = threading.local()

def _generate_trace_id():
    """Benzersiz trace ID oluşturur."""
    return str(uuid.uuid4())

def _generate_span_id():
    """Benzersiz span ID oluşturur."""
    return str(uuid.uuid4())[:8]  # Kısa span ID için ilk 8 karakter

def get_trace_context():
    """Mevcut trace context'i döndürür, yoksa yeni oluşturur."""
    if not hasattr(_trace_context, 'trace_id'):
        _trace_context.trace_id = _generate_trace_id()
        _trace_context.span_id = _generate_span_id()
        _trace_context.start_time = time.time()
        _trace_context.spans = []  # (span_id, parent_span_id, operation_name, start_time, end_time)
    return _trace_context

def start_span(operation_name, parent_span_id=None):
    """Yeni bir span başlatır ve span ID'ini döndürür."""
    ctx = get_trace_context()
    span_id = _generate_span_id()
    span_info = {
        'span_id': span_id,
        'parent_span_id': parent_span_id or ctx.span_id,
        'operation_name': operation_name,
        'start_time': time.time(),
        'end_time': None
    }
    ctx.spans.append(span_info)
    return span_id

def end_span(span_id):
    """Belirtilen span'i sonlandırır."""
    ctx = get_trace_context()
    for span in ctx.spans:
        if span['span_id'] == span_id:
            span['end_time'] = time.time()
            break

def get_current_span_id():
    """Mevcut span ID'ini döndürür."""
    ctx = get_trace_context()
    return ctx.span_id if hasattr(ctx, 'span_id') else None

def get_trace_id():
    """Mevcut trace ID'ini döndürür."""
    ctx = get_trace_context()
    return ctx.trace_id if hasattr(ctx, 'trace_id') else None

def get_traces():
    """Tüm trace bilgilerini döndürür."""
    ctx = get_trace_context()
    return {
        'trace_id': getattr(ctx, 'trace_id', None),
        'spans': getattr(ctx, 'spans', [])
    }

def reset_trace_context():
    """Trace context'ini sıfırlar (yeni bir trace için)."""
    if hasattr(_trace_context, 'trace_id'):
        delattr(_trace_context, 'trace_id')
    if hasattr(_trace_context, 'span_id'):
        delattr(_trace_context, 'span_id')
    if hasattr(_trace_context, 'start_time'):
        delattr(_trace_context, 'start_time')
    if hasattr(_trace_context, 'spans'):
        delattr(_trace_context, 'spans')

def _anahtar_esittir(m: "re.Match") -> str:
    # ZATEN MASKELI ISE DOKUNMA. Neden sart: deger sinifi `]` karakterini
    # AYIRICI sayiyor (sorgu dizesi degerleri orada biter), yani bir kez
    # yazilmis `access_token=…[MASKELİ]` metni ikinci gecişte `…[MASKELİ`
    # olarak eslesip sonuna BIR `]` DAHA ekliyordu. `log_rotate.trim_log()`
    # her kosuda ayni dosyayi yeniden maskeledigi icin bu, satirin her gun
    # bir karakter uzamasi demekti (gercek bir log satirinda yakalandi).
    if m.group(2).startswith(_MASKE_BASI):
        return m.group(0)
    return m.group(1) + "=" + MASKE


def _anahtar_json(m: "re.Match") -> str:
    return '"' + m.group(1) + '": "' + MASKE + '"'


def _sabit(metin: str):
    return lambda m: metin


# Sira ONEMLI: once "anahtar + deger" ciftleri (en dar, en guvenli), sonra
# anahtarsiz ama bicimi kendini ele veren ham token'lar.
_DESENLER = (
    # 1) Sorgu dizesi / form govdesi: ...?access_token=EAAG...&fields=...
    #    Deger, ayirici bir karakter gorene kadar suruyor (& bosluk tirnak vb.).
    (re.compile(r"\b(" + _ANAHTAR_ALT + r")=([^&\s\"'<>)\],;]+)", re.I),
     _anahtar_esittir),

    # 2) JSON/dict govdesi: {"access_token": "EAAG..."} ya da repr'deki
    #    {'client_secret': '...'} — cift ve tek tirnak ayri ayri.
    (re.compile(r"\"(" + _ANAHTAR_ALT + r")\"\s*:\s*\"[^\"]*\"", re.I),
     _anahtar_json),
    (re.compile(r"'(" + _ANAHTAR_ALT + r")'\s*:\s*'[^']*'", re.I),
     _anahtar_json),

    # 3) Telegram Bot API: token YOLUN icinde
    #    https://api.telegram.org/bot123456789:AAF.../sendVideo
    (re.compile(r"/bot\d+:[A-Za-z0-9_\-]+"),
     _sabit("/bot" + MASKE)),

    # 4) Anahtarsiz ham Telegram token'i (<rakam>:<gizli>). Zaman damgasi
    #    (12:00:00) buna TAKILMAZ: en az 6 rakam + en az 30 karakterlik gizli
    #    kisim sart.
    (re.compile(r"\b\d{6,12}:[A-Za-z0-9_\-]{30,}"),
     _sabit(MASKE)),

    # 5) Authorization basligi: "Bearer eyJ..."
    (re.compile(r"\bBearer\s+[A-Za-z0-9._\-~+/]+=*", re.I),
     _sabit("Bearer " + MASKE)),

    # 6) Meta (Facebook/Instagram) token on ekleri — anahtar adi olmadan,
    #    ciplak gectikleri yerlerde de yakalansin diye.
    (re.compile(r"\bEAA[A-Za-z0-9]{15,}"), _sabit(MASKE)),
    (re.compile(r"\bIGQ[A-Za-z0-9_\-]{15,}"), _sabit(MASKE)),

    # 7) Google OAuth refresh token'i ("1//0g..." ile baslar)
    (re.compile(r"\b1//[A-Za-z0-9_\-]{20,}"), _sabit(MASKE)),

    # 8) Netlify kisisel erisim token'i (`nfp_` on eki) — ANAHTARSIZ gectigi
    #    yerler icin. Yukaridaki `token` anahtar kurali JSON govdesini
    #    kapsiyor, bu deger-deseni ise token'in tek basina (ornegin bir istisna
    #    metninde ya da elle yapistirilmis bir satirda) gectigi hali yakaliyor.
    #    `nfp_` + en az 20 karakter: normal Turkce log metninde boyle bir dizi
    #    yok. NOT: Netlify'in ESKI (on eksiz, 64 haneli hex) token'lari bu
    #    desene UYMAZ — onlar icin koruma yalnizca `token` anahtar kuralidir;
    #    64-hane hex icin ayri bir deger-deseni BILEREK eklenmedi, sha256
    #    ozetleri gibi zararsiz dizileri de maskelerdi.
    (re.compile(r"\bnfp_[A-Za-z0-9_\-]{20,}"), _sabit(MASKE)),

    # 9) Bluesky app password'u: xxxx-xxxx-xxxx-xxxx (dort dortlu blok).
    #    Tarih (2026-09-11) ve UUID bu bicime UYMUYOR, bkz. testler.
    (re.compile(r"\b[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}\b"),
     _sabit(MASKE)),
)


def maskele(metin) -> str:
    """`metin` icindeki bilinen kimlik bilgisi desenlerini maskeler.

    Her zaman bir `str` doner (None/istisna/sayi da guvenle gecebilsin diye);
    hicbir desen eslesmezse metin AYNEN korunur — normal log satirlari
    bozulmaz."""
    if metin is None:
        return ""
    if not isinstance(metin, str):
        metin = str(metin)
    for desen, degistir in _DESENLER:
        metin = desen.sub(degistir, metin)
    return metin


def maskele_istisna(e: BaseException) -> str:
    """Bir istisnayi log'a yazilabilir, maskelenmis bir metne cevirir.

    `str(e)` bos olabilir (ornegin `KeyError()` ya da bazi `OSError`lari) —
    o zaman en azindan istisnanin TIPI yazilir, yoksa log'da anlamsiz bir
    "HATA: " satiri kalir."""
    metin = maskele(str(e))
    if not metin.strip():
        return type(e).__name__
    return metin


def json_log(mesaj: str, **kwargs) -> None:
    """Güvenli JSON log üretir - auto_process.log'a yazar, analiz edilebilir.
    
    KULLANIM:
        json_log("YouTube altyazı atlandı", 
                project=ad, 
                baslik=baslik, 
                missing_file=expected_filename)
    """
    import time
    from gizli_maskele import maskele, get_trace_id, get_current_span_id
    
    # Maskeleme uygulanacak tüm string değerleri işle
    masked_kwargs = {
        k: maskele(str(v)) if isinstance(v, str) else v 
        for k, v in kwargs.items()
    }
    
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": "INFO",
        "message": mesaj,
        **masked_kwargs
    }
    
    # Trace context bilgilerini ekle (varsa)
    trace_id = get_trace_id()
    span_id = get_current_span_id()
    if trace_id:
        log_entry["trace_id"] = trace_id
    if span_id:
        log_entry["span_id"] = span_id
    
    # Mevcut auto_process.log formatına uyum sağlayacak şekilde yaz
    # (JSON tek satır, mevcut log parsers'ı bozmadan)
    log_json = "{"
    log_json += ", ".join(f'"{k}": {json.dumps(v) if not isinstance(v, str) else f'"{v}"'}'
                         for k, v in log_entry.items())
    log_json += "}"
    
    print(log_json)  # stdout'a da yaz (mevcut _log davranışı)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_json + "\n")
    except OSError:
        pass  # Log yazılamazsa otomasyonu durdurma (mevcut davranış)


