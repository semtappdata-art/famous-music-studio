"""ntfy.sh üzerinden telefona push bildirimi gönderen küçük yardımcı.

Kurulum (kullanıcı tarafında, elle, bir kere):
  1. Telefona "ntfy" uygulamasını kur (App Store / Play Store).
  2. Rastgele, tahmin edilmesi zor bir konu (topic) adı seç (ör.
     "fms-bildirim-x7q2") ve uygulamada o konuya abone ol — ntfy.sh'de hesap
     gerekmiyor, konu adı tek başına "gizlilik" sağlıyor (herkese açık ama
     bilinmeyen bir kanal). KISA ad seçme: adı tahmin eden herkes bildirimleri
     okuyabilir/sahte bildirim gönderebilir.
  3. Repo kökünde notify_config.json oluştur (gitignored — bkz. .gitignore):
         {"ntfy_topic": "senin-sectigin-konu-adi"}

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

# Koşu (process) başına bir kez uyarılan durumlar. Her notify.send() çağrısında
# uyarmak 17 projelik bir koşuda log'u 17 aynı satırla dolduruyordu.
_uyarilanlar: set = set()


def _topic() -> str | None:
    if not os.path.isfile(_CONFIG_PATH):
        return None
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("ntfy_topic")
    except (OSError, json.JSONDecodeError):
        return None


def is_configured() -> bool:
    """Bildirim kanalı (notify_config.json + ntfy_topic) kurulu mu?

    Çağıranlar "bildirim gönderilmedi"nin sebebini ayırt edebilsin diye public:
    ör. tiktok_upload.notify_pending_publish() "golden-hour bekleniyor" demeden
    önce buna bakıyor — gerçek sebep pencere değil, kanalın hiç kurulmamış
    olması olabiliyor (2026-09-11'e kadar tam olarak öyleydi)."""
    return bool(_topic())


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


def send(title: str, message: str) -> bool:
    """Telefona bir bildirim gönderir. Başlık da mesaj da TÜRKÇE olabilir.

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
    topic = _topic()
    if not topic:
        # Sessizce False dönmek "koruma var, çalışmıyor, kimse bilmiyor"
        # deseninin ta kendisiydi — koşu başına bir kez açıkça söyle.
        uyar_bir_kez(
            "kanal-yok",
            "UYARI: bildirim kanali kurulu DEGIL (notify_config.json yok ya da "
            "ntfy_topic bos) — bu kosudaki TUM telefon bildirimleri atlaniyor "
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
