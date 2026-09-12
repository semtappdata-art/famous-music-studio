# -*- coding: utf-8 -*-
"""YouTube Analytics — izlenme SÜRESİ (watch-time) ölçümü.

NEDEN AYRI BİR MODÜL VE AYRI BİR TOKEN:

`youtube_stats.py` izlenme/beğeni/yorum sayılarını Data API'den çekiyor ve
bunlar için mevcut token yetiyor. Ama izlenme SÜRESİ Data API'de YOK — ayrı
bir servis (youtubeAnalytics v2) ve ayrı bir izin gerekiyor
(`yt-analytics.readonly`). Mevcut token'da o izin yok; kontrol edildi, sadece
`youtube.upload` ve `youtube.force-ssl` var.

İzni `youtube_auth.SCOPES`'a eklemek EN KOLAY yol olurdu ama YANLIŞ olurdu:
`Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)` istenen izinlerle
kayıtlı izinleri karşılaştırıyor. Listeyi büyütmek mevcut token'ı geçersiz
kılar ve kullanıcı yeniden yetkilendirene kadar SAATLİK YÜKLEME HATTI DURUR.
Çalışan bir hattı, ölçüm eklemek için riske atmak kabul edilemez.

Bu yüzden analytics KENDİ token dosyasını kullanıyor (`analytics_token.json`).
Yükleme hattı hiç etkilenmiyor; bu token yoksa modül sessizce boş sonuç
dönüyor ve otomasyon normal çalışmaya devam ediyor.

NEDEN GEREKLİ: DJ setlerinin asıl değeri izlenme SAYISI değil, izlenme
SÜRESİ. 41 dakikalık bir set, 3 dakikalık bir şarkıyla aynı izlenmeyi alsa
bile kat kat fazla watch-time üretiyor ve YouTube dağıtımı bunu ödüllendiriyor.
"Haftada bir set değer mi" sorusu bu sayı olmadan tahminle cevaplanıyordu.

Kullanım:
    python upload/youtube_analytics.py --auth     # bir kereye mahsus izin
    python upload/youtube_analytics.py            # raporu yazdır
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(UPLOAD_DIR)
CLIENT_SECRETS_PATH = os.path.join(UPLOAD_DIR, "client_secrets.json")
TOKEN_PATH = os.path.join(UPLOAD_DIR, "analytics_token.json")

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

# Icerik kokleri: TEK kanonik kaynak uyumluluk.KOKLER (mutlak yollar; goreli
# birakilirsa yanlis cwd'de os.path.isdir False doner ve fonksiyon SESSIZCE bos
# sonuc uretir). Burada kendi KOPYASI vardi: icerigi dogruydu ama kopya olmak,
# dorduncu bir kok acildiginda elle dokunulmasi gereken yerlerden biri olmak
# demek — `derlemeler/` eklendiginde bu sinif hata tam da boyle olusmustu.
# Muhafiz: tests/test_kok_listesi_muhafizi.py
from uyumluluk import KOKLER  # noqa: E402

# Kanalın ilk yüklemesinden bugüne bakmak yeterli; API başlangıç tarihi
# istiyor ve geçmişe fazladan gitmek sonucu değiştirmiyor.
BASLANGIC = "2026-08-01"


def _token_yaz(creds) -> None:
    """analytics_token.json'u ATOMIK yazar.

    NEDEN: duz `open(TOKEN_PATH, "w")` dosyayi ONCE SIFIRLIYOR. Yazim
    sirasinda surec olurse (Gorev Zamanlayici timeout'u, guc kesintisi) token
    dosyasi YARIM kalir ve bir sonraki kosuda
    `Credentials.from_authorized_user_file` patlar. Ayri bir token oldugu icin
    yukleme hattini durdurmaz (tasarim geregi, bkz. modul docstring'i) — ama
    izlenme olcumu SESSIZCE olur, ki bu olcum bugune kadar zaten hic
    calismamisti; ayni sessiz duruse ikinci bir yol acmanin anlami yok.

    NEDEN `state_io._atomik_metin_yaz` (sozluk yazan `_atomik_yaz` degil):
    `creds.to_json()` bir STRING donduruyor. Onu `json.loads` ile sozluge
    cevirip yeniden serilestirmek google-auth'un urettigi gosterimi bizim
    bicimlendirmemizle degistirirdi; token dosyasinda gereksiz bir risk.
    `state_io`'ya bu yuzden string yazan kardes fonksiyon eklendi — burada
    yerel bir tmp+replace kopyasi yazmak atomik yazimin DORDUNCU kopyasi
    olurdu, oysa `state_io.py` tam da o kopyalari tek yerde toplamak icin var.
    """
    import state_io
    state_io._atomik_metin_yaz(TOKEN_PATH, creds.to_json())


def get_service():
    """Analytics servisini döner; token yoksa None (sessiz geçiş)."""
    if not os.path.isfile(TOKEN_PATH):
        return None
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _token_yaz(creds)          # atomik — yarim token dosyasi birakma
        else:
            return None
    return build("youtubeAnalytics", "v2", credentials=creds)


def yetkilendir():
    """Tarayıcıda izin akışını açar, analytics_token.json yazar."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.isfile(CLIENT_SECRETS_PATH):
        raise FileNotFoundError(
            "client_secrets.json bulunamadı: %s" % CLIENT_SECRETS_PATH)
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
    # open_browser=False: URL'yi kendimiz acmak icin stdout'a yazdiriyoruz.
    # Varsayilan (True) Chrome'un varsayilan penceresini aciyor ve o pencere
    # tarayici otomasyonunun gorebildigi sekme grubunda OLMUYOR - onay
    # ekranina erisilemiyordu.
    creds = flow.run_local_server(port=0, open_browser=False,
                                  authorization_prompt_message="AUTH_URL: {url}")
    _token_yaz(creds)                  # ilk yazim da ayni yoldan gecsin
    print("Analytics izni alındı: %s" % TOKEN_PATH)


def _video_idler() -> dict:
    """{video_id: (kok_adi, proje_adi)} — state.json'lardan toplanır.

    `kok_adi` TAM YOL DEĞİL, sadece klasör adı ("projects" / "dj_sets" /
    "derlemeler"). rapor() özeti bu değerle gruplanıyor ve tablo `%-9s` ile
    basılıyor — tam yol konunca satırda
    `C:\\Users\\ACER\\Desktop\\ilk-projem\\projects` yazıyordu.
    """
    harita = {}
    for kok in KOKLER:
        d = kok
        if not os.path.isdir(d):
            continue
        for ad in sorted(os.listdir(d)):
            sp = os.path.join(d, ad, "state.json")
            if not os.path.isfile(sp):
                continue
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    st = json.load(f)
            except (OSError, ValueError):
                continue
            # Uzun format: asıl watch-time buradan geliyor. Shorts ayrı
            # sayılıyor ve kısa olduğu için karşılaştırmayı bozardı.
            vid = st.get("youtube_video_id")
            if vid:
                # basename: özet/tablo kök ADIYLA gruplansın (bkz. docstring).
                harita[vid] = (os.path.basename(kok), ad)
    return harita


def izlenme_suresi(video_idler=None) -> dict:
    """Video başına izlenme süresi. Token yoksa {} döner (sessiz geçiş).

    API tek çağrıda en fazla 500 video filtreliyor; bizde 20 civarı var,
    sayfalama gerekmiyor - ama filtre uzunluğu büyürse burada bölmek gerekir.
    """
    servis = get_service()
    if servis is None:
        return {}
    harita = video_idler or _video_idler()
    if not harita:
        return {}

    bugun = date.today().isoformat()
    sonuc = {}
    idler = list(harita)
    for i in range(0, len(idler), 200):
        obek = idler[i:i + 200]
        try:
            r = servis.reports().query(
                ids="channel==MINE",
                startDate=BASLANGIC,
                endDate=bugun,
                metrics="estimatedMinutesWatched,averageViewDuration,averageViewPercentage,views",
                dimensions="video",
                filters="video==%s" % ",".join(obek),
                maxResults=200,
            ).execute()
        except Exception as e:
            print("  Analytics sorgusu başarısız: %s" % str(e)[:200])
            continue
        for satir in r.get("rows", []) or []:
            vid, dk, ort_sn, ort_yuzde, izlenme = satir[0], satir[1], satir[2], satir[3], satir[4]
            kok, ad = harita.get(vid, ("?", vid))
            sonuc[vid] = {
                "kok": kok, "ad": ad,
                "toplam_dakika": dk,
                "ort_izlenme_sn": ort_sn,
                "ort_izlenme_yuzde": ort_yuzde,
                "izlenme": izlenme,
            }
    return sonuc


def rapor() -> dict:
    """Kök bazında (projects / dj_sets) toplamları döner."""
    veri = izlenme_suresi()
    ozet = {}
    for bilgi in veri.values():
        o = ozet.setdefault(bilgi["kok"], {"video": 0, "dakika": 0, "izlenme": 0,
                                           "ort_sn_toplam": 0})
        o["video"] += 1
        o["dakika"] += bilgi["toplam_dakika"]
        o["izlenme"] += bilgi["izlenme"]
        o["ort_sn_toplam"] += bilgi["ort_izlenme_sn"]
    for o in ozet.values():
        o["ort_izlenme_sn"] = round(o["ort_sn_toplam"] / o["video"]) if o["video"] else 0
        del o["ort_sn_toplam"]
    return {"video_bazinda": veri, "ozet": ozet}


def main():
    ap = argparse.ArgumentParser(description="YouTube izlenme süresi raporu.")
    ap.add_argument("--auth", action="store_true", help="Bir kereye mahsus izin akışı")
    ap.add_argument("--json", action="store_true", help="Ham JSON yazdır")
    args = ap.parse_args()

    if args.auth:
        yetkilendir()
        return

    if not os.path.isfile(TOKEN_PATH):
        print("analytics_token.json yok. Önce: python upload/youtube_analytics.py --auth")
        return

    r = rapor()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if not r["video_bazinda"]:
        print("Veri gelmedi (video yok ya da Analytics henüz işlememiş olabilir).")
        return

    print("%-9s %5s %10s %12s %10s" % ("kök", "video", "izlenme", "toplam dk", "ort sn"))
    for kok, o in sorted(r["ozet"].items()):
        print("%-9s %5d %10d %12d %10d"
              % (kok, o["video"], o["izlenme"], o["dakika"], o["ort_izlenme_sn"]))

    print("\nvideo bazında (en çok izlenme süresi önce):")
    for b in sorted(r["video_bazinda"].values(), key=lambda x: -x["toplam_dakika"])[:12]:
        print("  %-9s %-28s %6d dk | ort %4d sn (%%%.0f) | %4d izlenme"
              % (b["kok"], b["ad"][:28], b["toplam_dakika"], b["ort_izlenme_sn"],
                 b["ort_izlenme_yuzde"], b["izlenme"]))


if __name__ == "__main__":
    main()
