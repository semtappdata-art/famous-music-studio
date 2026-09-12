"""ELLE ONAYLANMIŞ yorum yanıtlarını YouTube'a gönderir. Varsayılan: --dry-run.

NEDEN VAR
---------
`upload/youtube_comments.py` yanıt bekleyen yorumları çekiyor ama YAZMA tarafı
bilerek orada yok. Yanıt metinleri `yorum_taslaklari.json`'da elle hazırlanıyor
ve bugüne kadar onları GÖNDEREN tek satır kod yoktu — taslaklar dosyada durup
kaldı. Bu modül tam olarak o boşluğu kapatıyor: hazırlanmış bir taslağı, tek
tek onaylanarak, gönderilebilir hale getirmek.

BU BİLEREK OTOMATİK DEĞİLDİR — ZAMANLAYICIYA BAĞLAMA
----------------------------------------------------
Bir sonraki oturum bunu Görev Zamanlayıcı'ya ya da `auto_process.main()`'in
`finally` bloğuna bağlamaya kalkabilir. YAPMA. Üç ayrı sebep:

1. **Politika riski.** Kanalın en büyük tekil riski telif değil, YouTube'un
   "inauthentic content" / "high-volume, repetitive" tanımı. Şablon üretilmiş
   yanıtları toplu göndermek bu tanımın tam ortası. Gerçek izleyiciye yazılan
   bir cümlenin insan tarafından okunmuş olması bu riske karşı ASIL sinyal.
2. **Kota.** `comments.insert` adet başına **50 birim** (okuma 1 birim).
   Günlük kota 10.000 ve tek bir video yüklemesi ~1600 birim harcıyor;
   kontrolsüz bir yanıt döngüsü ASIL yükleme hattını durdurur (2026-09-06'da
   `captions.list` döngüsüyle bu bir kez yaşandı).
3. **Geri dönüşü yok.** Yanlış/tekrar eden bir yanıt gerçek bir insana,
   kanalın adına yazılmış olur.

Bu yüzden: `--gonder` bayrağı OLMADAN hiçbir şey gönderilmez, her koşuda
`--limit` tavanı vardır ve gönderimden önce thread'in gerçek durumu API'den
tekrar okunur.

ÇİFT GÖNDERİM KORUMASI (iki katman)
-----------------------------------
* Taslaktaki `durum` alanı: sadece `onay_bekliyor` olanlar gönderilir;
  gönderilen taslak anında `gonderildi` olarak işaretlenip dosyaya yazılır.
* Gönderimden ÖNCE `commentThreads.list` ile thread tazeden okunur (tüm
  taslaklar için TEK istek, 1 birim): yorum silinmişse ya da thread'de
  kanalın zaten bir yanıtı varsa o taslak atlanır. Bu katman şart —
  2026-09-11'de dosyadaki 10 taslağın 10'unun da aslında 10 Eylül'de ELLE
  gönderilmiş olduğu bu kontrolle ortaya çıktı; dosyaya güvenilseydi
  10 gerçek insana aynı cümle ikinci kez giderdi.

KULLANIM
--------
    python upload/yorum_gonder.py                 # dry-run: ne gönderilecek?
    python upload/yorum_gonder.py --id <yorumID>  # tek bir taslağa odaklan
    python upload/yorum_gonder.py --gonder --id <yorumID>   # GERÇEK gönderim
    python upload/yorum_gonder.py --gonder --hepsi          # onaylı hepsi

`--gonder` ile `--id` ya da `--hepsi`'den biri ZORUNLU: bayrağı yanlışlıkla
yazıp bütün dosyayı göndermek mümkün olmasın diye.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASLAK_YOLU = os.path.join(REPO, "yorum_taslaklari.json")

BIRIM_YANIT = 50          # comments.insert kota maliyeti (adet basina)
BIRIM_OKUMA = 1           # commentThreads.list (sayfa basina)
KOSU_TAVANI = 5           # tek kosuda gonderilebilecek en fazla yanit


def taslaklari_oku(yol: str = None) -> dict:
    # Varsayilan DEGERI imzaya yazma: `yol=TASLAK_YOLU` modul yuklenirken
    # bir kez baglanir, sonradan TASLAK_YOLU'nu degistirmek (test, farkli
    # dosya) hicbir sey yapmaz. Gec baglama sart.
    with open(yol or TASLAK_YOLU, "r", encoding="utf-8") as f:
        return json.load(f)


def taslaklari_yaz(veri: dict, yol: str = None) -> None:
    """Atomik yazim: yarida kesilen bir yazim dosyayi bozmasin (state_io deseni)."""
    yol = yol or TASLAK_YOLU
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(gecici, yol)


def adaylar(veri: dict, sadece_id: str = None) -> list:
    """Gonderilebilir taslaklar: durum == onay_bekliyor (ya da hic yok) ve
    bos olmayan bir yanit metni var."""
    out = []
    for t in veri.get("taslaklar", []):
        if sadece_id and t.get("id") != sadece_id:
            continue
        if t.get("durum", "onay_bekliyor") != "onay_bekliyor":
            continue
        if not (t.get("yanit") or "").strip():
            continue
        out.append(t)
    return out


def thread_durumu(yt, kanal_id: str, idler: list) -> dict:
    """TEK istekte (1 birim) thread'lerin guncel halini okur.

    Doner: {yorum_id: {"var": bool, "kanal_yanitladi": bool, "metin": str}}
    Listede DONMEYEN bir id silinmis/erisilemez demektir."""
    sonuc = {i: {"var": False, "kanal_yanitladi": False, "metin": ""} for i in idler}
    if not idler:
        return sonuc
    # comments/commentThreads id listesi 50'lik parcalara boluinuyor
    for bas in range(0, len(idler), 50):
        parca = idler[bas:bas + 50]
        r = yt.commentThreads().list(
            part="snippet,replies", id=",".join(parca),
            textFormat="plainText", maxResults=100).execute()
        for it in r.get("items", []):
            ust = it["snippet"]["topLevelComment"]["snippet"]
            yanitlar = (it.get("replies", {}) or {}).get("comments", [])
            kanal_yaniti = any(
                ((y["snippet"].get("authorChannelId") or {}).get("value") == kanal_id)
                for y in yanitlar)
            sonuc[it["id"]] = {
                "var": True,
                # totalReplyCount > 0 ama replies listesi kanal yaniti icermiyorsa
                # (baskasi cevaplamis) yine de biz yanitlayabiliriz.
                "kanal_yanitladi": kanal_yaniti,
                "metin": (ust.get("textDisplay") or "").strip(),
            }
    return sonuc


def _isaretle(veri: dict, yorum_id: str, durum: str, **ek) -> None:
    for t in veri.get("taslaklar", []):
        if t.get("id") == yorum_id:
            t["durum"] = durum
            t.update(ek)
            return


def calistir(gonder: bool, sadece_id: str = None, limit: int = KOSU_TAVANI) -> int:
    veri = taslaklari_oku()
    liste = adaylar(veri, sadece_id)

    if not liste:
        print("Gönderilecek onaylı taslak yok "
              "(durum='onay_bekliyor' olan ve metni dolu bir taslak bulunamadı).")
        return 0

    yt = get_authenticated_service()
    kanal = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
    durumlar = thread_durumu(yt, kanal, [t["id"] for t in liste])
    print("Ön kontrol: %d thread okundu (~%d birim).\n" % (len(liste), BIRIM_OKUMA))

    gonderilen = 0
    for t in liste:
        d = durumlar.get(t["id"], {})
        bilgi = "%s — %s (%s)" % (t.get("parca", "?"), t.get("yazan", "?"), t["id"])

        if not d.get("var"):
            print("[ATLANDI] %s\n  yorum artık YOK (silinmiş/gizlenmiş).\n" % bilgi)
            _isaretle(veri, t["id"], "yorum_silinmis")
            continue
        if d.get("kanal_yanitladi"):
            print("[ATLANDI] %s\n  kanalın bu thread'de ZATEN bir yanıtı var — "
                  "ikinci kez yanıtlamak kötü görünür.\n" % bilgi)
            _isaretle(veri, t["id"], "zaten_yanitlandi")
            continue
        if d.get("metin") and d["metin"] != (t.get("yorum") or "").strip():
            print("[DİKKAT] %s\n  yorum DEĞİŞMİŞ. taslaktaki: %r\n  şu anki:    %r\n"
                  "  Yanıt hâlâ uyuyor mu, elle bak; bu taslak atlandı.\n"
                  "  GERİ ALMA: bu taslak artık 'yorum_degismis' durumunda ve bir\n"
                  "  daha KENDİLİĞİNDEN aday olmaz — uygun bulursan yorum_taslaklari\n"
                  "  .json'da 'durum'u elle 'onay_bekliyor' yap.\n"
                  % (bilgi, t.get("yorum"), d["metin"]))
            _isaretle(veri, t["id"], "yorum_degismis", guncel_yorum=d["metin"])
            continue

        if gonderilen >= limit:
            print("[BEKLİYOR] %s\n  koşu tavanı (%d) doldu, sonraki koşuda.\n"
                  % (bilgi, limit))
            continue

        if not gonder:
            print("[DRY-RUN] %s\n  yorum: %s\n  yanıt: %s\n  (gerçek gönderim: --gonder)\n"
                  % (bilgi, t.get("yorum"), t.get("yanit")))
            gonderilen += 1
            continue

        try:
            yt.comments().insert(
                part="snippet",
                body={"snippet": {"parentId": t["id"], "textOriginal": t["yanit"]}},
            ).execute()
        except Exception as e:                      # noqa: BLE001 - tek tek raporla
            print("[HATA] %s\n  gönderilemedi: %s\n" % (bilgi, e))
            continue

        gonderilen += 1
        print("[GÖNDERİLDİ] %s\n  %s\n" % (bilgi, t["yanit"]))
        _isaretle(veri, t["id"], "gonderildi",
                  gonderildi_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  gonderilen_metin=t["yanit"])
        # HER gonderimden sonra diske yaz: yarida kesilse bile gonderilmis
        # olanlar bir daha gitmesin.
        taslaklari_yaz(veri)

    # Atlama/degisim isaretleri HER IKI modda da kalicilasmali. Eskiden bu
    # yazim yalnizca dry-run dalindaydi: `--gonder --hepsi` ile TAMAMI atlanan
    # bir kosu (ornegin 10 taslagin 10'u da "zaten_yanitlandi") diske hicbir
    # sey yazmiyordu, cunku gonderim dalindaki tek yazim basarili bir
    # insert'ten SONRA geliyor. Sonuc: isaretleme kalici olmuyor, her kosu
    # ayni thread'leri bastan okuyup yine atliyordu.
    taslaklari_yaz(veri)

    if not gonder:
        print("DRY-RUN: hiçbir şey gönderilmedi. %d taslak gönderilmeye hazır "
              "(~%d birim kota)." % (gonderilen, gonderilen * BIRIM_YANIT))
    else:
        print("Gönderilen: %d  (~%d birim kota harcandı)."
              % (gonderilen, gonderilen * BIRIM_YANIT))
    return gonderilen


def main():
    ap = argparse.ArgumentParser(
        description="Onaylanmış yorum yanıtlarını gönderir (varsayılan: dry-run).")
    ap.add_argument("--gonder", action="store_true",
                    help="GERÇEKTEN gönder. Bu bayrak yoksa hiçbir şey gönderilmez.")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Açıkça dry-run (varsayılan davranış, okunabilirlik için).")
    ap.add_argument("--id", help="Sadece bu yorum ID'sinin taslağı.")
    ap.add_argument("--hepsi", action="store_true",
                    help="--gonder ile birlikte: onaylı TÜM taslaklar (tavan: --limit).")
    ap.add_argument("--limit", type=int, default=KOSU_TAVANI,
                    help="Tek koşuda en fazla kaç yanıt (varsayılan: %d)." % KOSU_TAVANI)
    args = ap.parse_args()

    if args.gonder and args.dry_run:
        ap.error("--gonder ile --dry-run birlikte kullanılamaz.")
    if args.gonder and not (args.id or args.hepsi):
        ap.error("--gonder için --id <yorumID> ya da --hepsi gerekli "
                 "(yanlışlıkla toplu gönderimi önlemek için).")

    calistir(gonder=args.gonder, sadece_id=args.id, limit=max(1, args.limit))


if __name__ == "__main__":
    main()
