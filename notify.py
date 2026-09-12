"""Telefona operatör bildirimi gönderen küçük yardımcı (Telegram ya da ntfy.sh).

İKİ ARKA UÇ, BELİRLİ BİR ÖNCELİK (2026-09-12):
  1. TELEGRAM (varsa TERCİH EDİLEN) — `notify_config.json` içinde
     `"telegram_chat_id"` varsa bildirim Telegram Bot API'nin `sendMessage`
     yöntemiyle gider. NEDEN ÖNCELİKLİ: bu deponun Telegram hattı ÜRETİMDE
     KANITLI (auto_process.log, 2026-09-12 06:48: "Telegram: tamam — 8"),
     ntfy hattı ise bugüne kadar tek bir teslim kaydı bırakmadı —
     `notify_config.json` uzun süre HİÇ yoktu, yani `notify.py` yazıldığından
     beri doğrulanmış TEK bir push yok. Sekiz sağlık kontrolünün tamamı
     (`saglik_kontrol.kontrol_et` -> `_bildir` -> `send`) bu tek hatta bağlı;
     emniyet ağını kanıtlanmamış değil KANITLI kanaldan geçirmek gerekiyordu.
  2. ntfy.sh — Telegram yapılandırılmamışsa (ya da bot token'ı bulunamazsa)
     YEDEK olarak aynen duruyor, SİLİNMEDİ.
  3. İkisi de yoksa davranış eskisi gibi: `uyar_bir_kez()` ile koşu başına BİR
     log satırı ve `False` dönüş.

BOT TOKEN'I İKİNCİ BİR YERE KOPYALANMIYOR (tek kaynak ilkesi): token
`upload/telegram_client_secrets.json`'dan OKUNUYOR — o dosya zaten yükleme
hattının kimlik kaynağı. `notify_config.json`'a SADECE hedef chat id yazılıyor.

YAYIN KANALINA YAZMA KAPISI — bkz. _telegram_ayari(). Bildirim chat id'si
yükleme hattının kullandığı yayın chat id'sine EŞİTSE hiçbir şey gönderilmez.

Kurulum (kullanıcı tarafında, elle, bir kere):
  1. Telefona "ntfy" uygulamasını kur (App Store / Play Store).
  2. Rastgele, tahmin edilmesi zor bir konu (topic) adı seç (ör.
     "fms-bildirim-x7q2") ve uygulamada o konuya abone ol — ntfy.sh'de hesap
     gerekmiyor, konu adı tek başına "gizlilik" sağlıyor (herkese açık ama
     bilinmeyen bir kanal). KISA ad seçme: adı tahmin eden herkes bildirimleri
     okuyabilir/sahte bildirim gönderebilir.
  3. Repo kökünde notify_config.json oluştur (gitignored — bkz. .gitignore):
         {"ntfy_topic": "senin-sectigin-konu-adi"}

TELEGRAM kurulumu (TERCİH EDİLEN yol, kullanıcı tarafında, elle, bir kere):
  1. Bot ZATEN VAR (`upload/telegram_client_secrets.json` — yükleme hattı onu
     kullanıyor). Yeni bot oluşturma, token kopyalama YOK.
  2. Telegram'da o bota ÖZELDEN (DM) bir mesaj yaz ("/start" yeter).
  3. Kendi kişisel chat id'ni öğren:
         https://api.telegram.org/bot<TOKEN>/getUpdates
     çıktısındaki `message.chat.id` (kendi DM'inde POZİTİF bir sayıdır; kanal
     id'leri -100... ile başlar).
  4. notify_config.json'a o sayıyı ekle:
         {"ntfy_topic": "...", "telegram_chat_id": "123456789"}
     `ntfy_topic` kalabilir — Telegram varsa ntfy'ye hiç gidilmez, sadece
     Telegram yapılandırması kaldırılırsa yedek olarak devreye girer.

notify_config.json yoksa send() False döner — otomasyon bildirim olmadan da
normal çalışmaya devam eder, sadece hatırlatma gönderilmez. AMA artık SESSİZ
değil: koşu başına BİR KEZ (her çağrıda değil, gürültü olmasın diye) çalışan
scriptin kendi log dosyasına "bildirim kanalı kurulu değil" satırı düşer —
bkz. uyar_bir_kez(). NEDEN: bu dosya 2026-09-11'e kadar hiç oluşturulmamıştı,
send() her seferinde sessizce False döndüğü için telefona BUGÜNE KADAR TEK BİR
bildirim gitmedi ve buna bağlı TÜM emniyet ağları (TikTok taslak hatırlatması,
watch_projects nabız uyarısı, Instagram token uyarısı, Content ID karantina
bildirimi, haftalık rapor hatırlatması) ölü durumdaydı — kimse fark etmedi.

GÖNDERİM BİÇİMİ: ntfy'nin JSON publish uç noktası (POST https://ntfy.sh/,
topic/title/message GÖVDEDE) — HTTP başlığı DEĞİL. NEDEN: bkz. send().
"""

import json
import os
import sys
import time

import requests

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notify_config.json")

# ntfy'nin JSON publish uç noktası. Konu adı URL'de DEĞİL, gövdede gidiyor —
# ntfy belgelerinin açık şartı: "Do not include the topic in the URL path".
_NTFY_URL = "https://ntfy.sh/"

# Bot token'ının TEK kaynağı — yükleme hattının zaten kullandığı dosya
# (upload/telegram_upload.SECRETS_PATH ile AYNI yol). Token BURAYA ya da
# notify_config.json'a KOPYALANMIYOR: ikinci bir kopya, biri yenilendiğinde
# sessizce eskiyen bir sır yüzeyi demektir.
_TELEGRAM_SECRETS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "upload", "telegram_client_secrets.json")

_TELEGRAM_API = "https://api.telegram.org"

# sendMessage metin sınırı: "1-4096 characters after entities parsing"
# (core.telegram.org/bots/api). Bildirimlerimiz birkaç yüz karakter, ama
# sınır aşılırsa Telegram TÜM mesajı reddeder — sessiz kayıp yerine kırp.
_TELEGRAM_MAX_CHARS = 4096

# Başlık ile gövdeyi ayıran boş satır. chr(10) BİLEREK: bu depoda ters eğik
# çizgili kaçış dizileri kaynağa YAZILIRKEN birkaç kez ham bayta çözüldü
# (bkz. CLAUDE.md, "Dosya YAZARKEN ters eğik çizgi yutuluyor").
_TG_AYRAC = chr(10) + chr(10)

# Koşu (process) başına bir kez uyarılan durumlar. Her notify.send() çağrısında
# uyarmak 17 projelik bir koşuda log'u 17 aynı satırla dolduruyordu.
_uyarilanlar: set = set()


def _yapilandirma() -> dict:
    """notify_config.json (yoksa/bozuksa boş sözlük)."""
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _topic() -> str | None:
    return _yapilandirma().get("ntfy_topic") or None


def _telegram_sirlari() -> dict:
    """upload/telegram_client_secrets.json — SALT OKUNUR.

    Buradan SADECE iki alan kullanılıyor: `bot_token` (gönderim için) ve
    `chat_id` (YAYIN hedefi — aşağıdaki kapının karşılaştırdığı değer)."""
    if not os.path.isfile(_TELEGRAM_SECRETS_PATH):
        return {}
    try:
        with open(_TELEGRAM_SECRETS_PATH, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _chat_id_esit(a, b) -> bool:
    """İki chat id aynı hedefi mi gösteriyor?

    Sayısal id'ler zaten birebir. Kullanıcı adları ("@kanaladi") Telegram'da
    BÜYÜK/küçük harf duyarsız, ve yapılandırmaya boşlukla yapıştırılmış bir
    değer gözle aynı görünüp string olarak farklı olurdu — kapının tek bir
    boşluk yüzünden açılması, kapının hiç olmamasıyla aynı şey."""
    return str(a).strip().casefold() == str(b).strip().casefold()


def _telegram_ayari() -> tuple[str | None, str | None, str | None]:
    """(bot_token, bildirim_chat_id, engel) döner.

    Üçü de None ise: Telegram hiç yapılandırılmamış (ntfy'ye düşülür).
    `engel` doluysa Telegram KULLANILMAZ; sebebi çağıran loglar.

    YAYIN KANALINA YAZMA KAPISI (`engel == "yayin-kanali"`):
    `upload/telegram_client_secrets.json`'daki `chat_id`, videoların çıktığı
    YAYIN hedefidir (state.json'lardaki `telegram_chat_id` ile aynı). Operatör
    uyarıları ("uyumluluk kapısı çöktü", "Instagram token'ı doluyor", "kanal 3
    gündür yayın yapmadı") oraya GİTMEMELİ: iki farklı amaç (yayın akışı ve
    alarm akışı) tek kanalda birikirse uyarılar gönderilerin arasında kaybolur
    ve geri alınamaz. Tek bir yapılandırma hatası (kopyala-yapıştırla aynı id)
    bunu sessizce yapardı; bu yüzden kapı KODDA ve testle kilitli
    (tests/test_notify_telegram.py). Kapı kapandığında Telegram'a HİÇBİR istek
    ATILMAZ — ntfy yedeği varsa bildirim oradan gider, yoksa False döner."""
    ham = _yapilandirma().get("telegram_chat_id")
    if ham is None or not str(ham).strip():
        return None, None, None
    bildirim_chat = str(ham).strip()
    sirlar = _telegram_sirlari()
    token = sirlar.get("bot_token")
    if not token or not str(token).strip():
        return None, None, "token-yok"
    yayin_chat = sirlar.get("chat_id")
    if yayin_chat and _chat_id_esit(yayin_chat, bildirim_chat):
        return None, None, "yayin-kanali"
    return str(token).strip(), bildirim_chat, None


def is_configured() -> bool:
    """Bildirim kanalı (Telegram ya da ntfy) kurulu mu?

    Çağıranlar "bildirim gönderilmedi"nin sebebini ayırt edebilsin diye public:
    ör. tiktok_upload.notify_pending_publish() "golden-hour bekleniyor" demeden
    önce buna bakıyor — gerçek sebep pencere değil, kanalın hiç kurulmamış
    olması olabiliyor (2026-09-11'e kadar tam olarak öyleydi).

    Telegram kapıya takılmışsa (yayın kanalı / token yok) o hat YOK sayılır;
    True dönmesi için ntfy yedeğinin kurulu olması gerekir — aksi hâlde
    "kurulu" diyen ama hiçbir şey gönderemeyen bir kanal bildirilmiş olurdu."""
    token, chat, _engel = _telegram_ayari()
    return bool(token and chat) or bool(_topic())


def uyar_bir_kez(anahtar: str, mesaj: str) -> None:
    """Aynı 'anahtar' için koşu başına tek bir uyarı satırı yazar.

    Satır, ÇALIŞAN scriptin kendi log dosyasına gider (auto_process.log /
    watch_projects.log / dj_famous_process.log) — üç giriş noktasının da
    modül düzeyinde LOG_PATH tanımlaması bu deponun ortak kuralı.
    NEDEN sabit auto_process.log DEĞİL: watch_projects.py'nin nabız (heartbeat)
    kontrolü auto_process.log'un mtime'ına bakıyor; oraya başka bir scriptten
    yazmak nabzı SAHTE tazeler ve tam da haber vermesi gereken arızayı gizler.
    LOG_PATH yoksa (ör. saglik_kontrol.py gibi düz stdout'a yazan scriptler)
    stderr'e düşer.

    Public: çağıran modüller (ör. tiktok_upload) de aynı "koşu başına bir kez"
    disiplinini kullanabilsin diye."""
    if anahtar in _uyarilanlar:
        return
    _uyarilanlar.add(anahtar)
    satir = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {mesaj}"
    yol = getattr(sys.modules.get("__main__"), "LOG_PATH", None)
    if isinstance(yol, str) and yol:
        try:
            with open(yol, "a", encoding="utf-8") as f:
                f.write(satir + "\n")
        except OSError:
            pass
    print(satir, file=sys.stderr)


def _gonderilemeyen_karakterler(metin: str) -> str:
    """metin içindeki latin-1'e SIĞMAYAN karakterler (tekrarsız, sırayla).

    Sadece TANI amaçlı: bir kodlama hatası log'a düştüğünde "hangi harf"
    sorusunu cevaplıyor. Türkçede bunlar tam olarak ı İ ş Ş ğ Ğ — ç ö ü Ç Ö Ü
    latin-1'de VAR, o yüzden hata tüm Türkçe başlıklarda değil sadece bir
    kısmında görünüyordu (yanıltıcıydı)."""
    gorulen = []
    for ch in metin:
        try:
            ch.encode("latin-1")
        except UnicodeEncodeError:
            if ch not in gorulen:
                gorulen.append(ch)
    return "".join(gorulen)


def _token_maskele(metin: str, bot_token: str) -> str:
    """Log'a yazılacak metinden bot token'ını siler.

    NEDEN: token URL'in YOLUNDA (`/bot<token>/sendMessage`) ve requests'in ağ
    istisnaları mesajlarının içinde tam isteği URL'ini taşıyor — maskelemeden
    loglanırsa token düz metin olarak log'a düşer ve o token tek başına kanala
    mesaj göndermeye yeter. Aynı gerekçe telegram_upload._api_post'ta da var
    (ve 2026-09-04'te bir Instagram token'ıyla GERÇEKTEN yaşandı)."""
    if bot_token:
        metin = metin.replace(bot_token, "<gizli-token>")
    return metin


def _telegram_gonder(bot_token: str, chat_id: str, title: str, message: str) -> bool:
    """Telegram Bot API sendMessage ile operatör bildirimi gönderir.

    TÜRKÇE KARAKTER: gövde UTF-8 JSON — ntfy'deki latin-1 HTTP başlığı tuzağı
    burada YOK (hiçbir değişken metin başlığa konmuyor, tek başlık sabit ASCII
    Content-Type). `ensure_ascii=False` + açık `.encode("utf-8")` ntfy yolundaki
    kararın aynısı: gövdenin telde GERÇEKTEN UTF-8 Türkçe olduğu test
    edilebilsin diye (requests'in `json=` parametresi \\uXXXX kaçışı üretirdi).

    `parse_mode` GÖNDERİLMİYOR — BİLEREK. Aynı karar upload/telegram_upload.py'de
    de alındı: bildirim metinlerinde tırnak, alt çizgi, köşeli parantez, emoji ve
    dosya yolu geçiyor; Markdown/HTML modunda bunların KAÇIRILMASI (escape)
    gerekir ve kaçırılmamış TEK bir karakter "can't parse entities" ile TÜM
    gönderimi düşürür. Bir alarm kanalında bu, "uyarı metninde alt çizgi olduğu
    için uyarı hiç ulaşmadı" demek olurdu — tam da bu modülün önlemek için var
    olduğu arıza. Düz metinde Telegram URL'leri zaten kendisi tıklanabilir yapar.

    HATA YOLU — AĞA ÇIKILDIYSA ntfy'YE DÜŞÜLMEZ (bilinçli karar):
    Telegram yapılandırılmış ve istek GERÇEKTEN denenmişse, başarısızlıkta
    sessizce ntfy'ye kaçmak iki şeyi birden bozardı: (a) ntfy 200 dönerse
    `send()` True döner, `saglik_kontrol._bildir()` günlük damgayı atar ve
    uyarı 24 saat boyunca bir daha DENENMEZ — oysa kanıtlanmış hat bozuk ve
    operatör bunu bilmiyor; (b) Telegram'ın bozuk olduğu, "bildirim gitti"
    görüntüsünün altında gizlenir. Bu yüzden burada `False` dönülüyor —
    ama SESSİZ DEĞİL: her başarısızlık yolu `uyar_bir_kez()` ile log'a bir
    satır bırakıyor ve damga atılmadığı için bir sonraki saatlik koşu YENİDEN
    DENER. 4xx (kalıcı: token/izin/chat id) ile 5xx-ağ (geçici) AYRI anahtar,
    AYRI metin — ntfy yolundaki aynı ayrımın eşi (kalıcı bir kod/yapılandırma
    hatasını geçici bir aksaklık gibi göstermek bu deponun belgelenmiş hatası).
    ntfy YEDEĞİ yalnızca Telegram hiç YAPILANDIRILMAMIŞSA (ya da kapıya
    takıldıysa, yani hiç istek atılmadıysa) devreye girer."""
    metin = (title + _TG_AYRAC + message).strip()
    if len(metin) > _TELEGRAM_MAX_CHARS:
        metin = metin[:_TELEGRAM_MAX_CHARS - 1] + "…"
    govde = json.dumps(
        {"chat_id": chat_id, "text": metin},
        ensure_ascii=False,
    ).encode("utf-8")
    url = "%s/bot%s/sendMessage" % (_TELEGRAM_API, bot_token)
    try:
        resp = requests.post(
            url,
            data=govde,
            # Sabit ASCII — burada da değişken metin taşıyan HTTP başlığı YOK.
            headers={"Content-Type": "application/json"},
            timeout=(5, 10),
        )
    except Exception as e:
        uyar_bir_kez(
            "telegram-gonderim-hatasi",
            "UYARI: Telegram bildirimi gonderilemedi (%s) — operatore ULASMADI. "
            "(Gecici olabilir: ag/Telegram; damga atilmadi, bir sonraki kosu "
            "yeniden dener.)" % _token_maskele(str(e)[:200], bot_token),
        )
        return False

    kod = getattr(resp, "status_code", 0)
    try:
        payload = resp.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    if kod == 200 and payload.get("ok", True):
        return True

    aciklama = _token_maskele(str(payload.get("description", ""))[:200], bot_token)
    if 400 <= kod < 500:
        # KALICI: 400 chat not found / 401 gecersiz token / 403 bot engellendi.
        # Tekrar denemek duzeltmez; yapilandirma ya da bot yetkisi duzelmeli.
        uyar_bir_kez(
            "telegram-kalici-hata",
            "HATA (KALICI, yapilandirma/yetki duzeltmesi gerek): Telegram "
            "bildirimi REDDEDILDI (HTTP %s) %r. Bu bir ag arizasi DEGIL — her "
            "kosuda ayni sekilde patlar. Bakilacaklar: notify_config.json'daki "
            "telegram_chat_id dogru mu, bota ozelden (DM) en az bir kez yazildi "
            "mi, bot token'i (upload/telegram_client_secrets.json) gecerli mi." % (
                kod, aciklama),
        )
    else:
        uyar_bir_kez(
            "telegram-gonderim-hatasi",
            "UYARI: Telegram bildirimi gonderilemedi (HTTP %s) %r — operatore "
            "ULASMADI. (Gecici olabilir; damga atilmadi, bir sonraki kosu "
            "yeniden dener.)" % (kod, aciklama),
        )
    return False


def send(title: str, message: str) -> bool:
    """Telefona bir bildirim gönderir. Başlık da mesaj da TÜRKÇE olabilir.

    ARKA UÇ SEÇİMİ (sözleşme DEĞİŞMEDİ — imza da dönüş de aynı):
    Telegram yapılandırılmışsa oraya gider (kanıtlanmış hat), yoksa ntfy'ye
    düşülür, ikisi de yoksa `uyar_bir_kez()` + `False`. Ayrıntı ve gerekçe:
    modül docstring'i, _telegram_ayari(), _telegram_gonder().

    NEDEN JSON GÖVDESİ, NEDEN ARTIK 'Title' BAŞLIĞI DEĞİL (2026-09-11 arızası):
    eski sürüm başlığı `headers={"Title": title}` ile gönderiyordu. `requests`
    altında `http.client` HTTP başlıklarını LATIN-1 ile kodluyor; Türkçenin
    ı(U+0131) İ(U+0130) ş(U+015F) ğ(U+011F) harfleri latin-1'de YOK, dolayısıyla
    `UnicodeEncodeError` atıyordu. Bu, send() içinde yakalanıp sessizce False
    dönüyordu — yani başlığında bu harflerden biri geçen HER bildirim ölüydü.
    Gerçekten oldu: 2026-09-11 15:13'te "Haftalık izlenme süresi", 18:13'te
    "DJ set yayında" bildirimleri bu yüzden telefona HİÇ ulaşmadı.

    ntfy'nin belgelediği İKİ çözüm var:
      (a) başlığı RFC 2047 ile kodlamak (`=?UTF-8?B?...?=`) — ntfy sunucusu
          bunu çözüyor ("you may also encode any header (including the title)
          as RFC 2047", docs.ntfy.sh/publish/);
      (b) JSON publish: konu/başlık/mesaj GÖVDEDE gider, HTTP başlığı hiç
          kullanılmaz ("Publish as JSON", aynı sayfa).

    (b) SEÇİLDİ. NEDEN: (a) semptomu sarıyor — başlık hâlâ latin-1 kısıtlı bir
    kanaldan geçiyor, sadece kaçırılmış hâlde; yeni bir alan (ör. ileride
    `Tags`/`Click`) eklendiğinde aynı tuzağa yeniden düşülür ve bu deponun
    CLAUDE.md'sindeki "unutulacak bir liste" tuzağının ta kendisi olur.
    (b) kısıtı KÖKÜNDEN kaldırıyor: gövde zaten UTF-8 gidiyordu (eski kodda da
    `message.encode("utf-8")` vardı ve mesajlar sorunsuzdu), artık başlık da
    aynı gövdenin içinde. ASCII'ye katlama (ı->i) ise üçüncü seçenekti ve
    REDDEDİLDİ: operatöre giden metni kalıcı olarak bozuyor ("DJ set yayinda"),
    üstelik gövde Türkçe kalacağı için tutarsız bir görüntü veriyor.

    `ensure_ascii=False` + açık `.encode("utf-8")` BİLEREK: requests'in `json=`
    parametresi \\uXXXX kaçışlarıyla ASCII üretirdi (geçerli JSON, çalışır) ama
    o zaman "gövde gerçekten UTF-8 Türkçe mi" sorusu tel üzerinde test
    EDİLEMEZ hâle gelirdi. Bkz. tests/test_notify_turkce_baslik.py.

    Dönüş: gönderim başarılıysa True, değilse False (otomasyon hiçbir zaman
    bildirim yüzünden durmaz)."""
    tg_token, tg_chat, tg_engel = _telegram_ayari()
    if tg_engel == "yayin-kanali":
        uyar_bir_kez(
            "telegram-yayin-kanali",
            "HATA (KALICI, yapilandirma duzeltmesi gerek): notify_config.json'daki "
            "telegram_chat_id, YUKLEME hattinin yayin chat id'siyle AYNI — operator "
            "uyarilari yayin akisina KARISMASIN diye gonderim DURDURULDU. Telegram'a "
            "hicbir istek atilmadi. Duzeltme: telegram_chat_id'ye kendi KISISEL "
            "(DM) chat id'ni yaz; kurulum adimlari notify.py docstring'inde.",
        )
    elif tg_engel == "token-yok":
        uyar_bir_kez(
            "telegram-token-yok",
            "UYARI: notify_config.json'da telegram_chat_id VAR ama bot token'i "
            "okunamadi (upload/telegram_client_secrets.json yok / bot_token bos) — "
            "Telegram bildirimi atlandi, varsa ntfy yedegine dusuluyor.",
        )
    if tg_token and tg_chat:
        return _telegram_gonder(tg_token, tg_chat, title, message)

    topic = _topic()
    if not topic:
        # Sessizce False dönmek "koruma var, çalışmıyor, kimse bilmiyor"
        # deseninin ta kendisiydi — koşu başına bir kez açıkça söyle.
        uyar_bir_kez(
            "kanal-yok",
            "UYARI: bildirim kanali kurulu DEGIL (notify_config.json yok ya da "
            "icinde ne telegram_chat_id ne ntfy_topic var) — bu kosudaki TUM "
            "telefon bildirimleri atlaniyor "
            "(TikTok taslak hatirlatmasi, nabiz uyarisi, token/karantina "
            "uyarilari). Kurulum: notify.py docstring.",
        )
        return False
    govde = json.dumps(
        {
            "topic": topic,
            "title": title,
            "message": message,
            # 3 = ntfy'nin "default" onceligi; eski kodun Priority: "default"
            # basliginin JSON karsiligi (deger degismedi, sadece yeri degisti).
            "priority": 3,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    try:
        resp = requests.post(
            _NTFY_URL,
            data=govde,
            # Sabit ASCII — bu sozlukte ARTIK degisken metin YOK, latin-1
            # tuzagina yeniden dusecek bir yuzey birakilmadi.
            headers={"Content-Type": "application/json"},
            timeout=(5, 10),
        )
        resp.raise_for_status()
        return True
    except UnicodeEncodeError as e:
        # AYRI DAL, AYRI MESAJ — NEDEN: kodlama hatasi AG hatasi DEGIL.
        # Ag/5xx hatasi geciciydir, bir sonraki kosu duzelir; kodlama hatasi
        # KALICI bir KOD hatasidir, her seferinde ayni sekilde tekrarlanir ve
        # beklemekle ASLA duzelmez. Ikisini ayni "bildirim gonderilemedi"
        # satirina yazmak, 2026-09-11'de tam olarak oldugu gibi, kalici bir
        # bug'i gecici bir aksaklik gibi gostermisti.
        # JSON govdesine gectikten sonra bu dalin calismasi BEKLENMIYOR;
        # duserse depoda yeni bir latin-1 yuzeyi acilmis demektir.
        uyar_bir_kez(
            "kodlama-hatasi",
            "HATA (KALICI, kod duzeltmesi gerek): bildirim KODLANAMADI (%s). "
            "Sorunlu karakter(ler): %r. Bu bir ag arizasi DEGIL — tekrar "
            "denemek duzeltmez, her kosuda ayni sekilde patlar. notify.send() "
            "govdeyi UTF-8 JSON olarak gonderiyor; demek ki HTTP basligina "
            "yeniden degisken metin konmus." % (
                str(e)[:200], _gonderilemeyen_karakterler(title + message)),
        )
        return False
    except Exception as e:
        # Kanal KURULU ama gönderim patlıyorsa (ağ yok, ntfy.sh 5xx) bu da
        # sessiz kalmamalı — yine koşu başına bir kez. Bu dal GEÇİCİ hatalar
        # içindir; kalıcı kodlama hatası yukarıdaki ayrı dalda.
        uyar_bir_kez(
            "gonderim-hatasi",
            "UYARI: bildirim gonderilemedi (%s) — telefon bildirimleri bu kosuda "
            "ulasmadi. (Gecici olabilir: ag/ntfy.sh; bir sonraki kosu yeniden "
            "dener.)" % str(e)[:200],
        )
        return False
