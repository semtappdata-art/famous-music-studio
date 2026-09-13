# -*- coding: utf-8 -*-
"""TikTok elle yayınını TEK bir şarkı adı/koduyla işaretler — Telegram onayı yolu.

    python upload/tiktok_yayin_onayi.py "Sabah Senin"
    python upload/tiktok_yayin_onayi.py "T3F2A"

NEDEN VAR (2026-09-13): `tiktok_published_at`in tek yazanı
`tiktok_publish_plan.py --yayinlandi "<proje yolu>"` idi ve UNUTULUYORDU —
katalogda işaret taşıyan kayıt neredeyse yok, `_tiktok_ikiz_kapisi` kör.
Hatırlatma (`tiktok_upload.notify_pending_publish`) artık "yayınladım <ad>"
yanıt kalıbını veriyor; yanıtı Hermes gateway'i okuyor ve
`.hermes/skills/tiktok-yayin-onayi` becerisiyle YALNIZ bu betiği çalıştırıyor.

BOT HERMES İLE PAYLAŞILIYOR: bu betik (ve depo) Telegram'dan HİÇBİR ŞEY
OKUMAZ — güncelleme okuyan bir Bot API çağrısı (polling ya da webhook) ikinci
bir tüketici olup Hermes'in mesajlarını çalardı (`notify.py`'deki karar). Betik tamamen yerel: ağ yok, kabuk yok,
silme yok. Argüman `sys.argv`'dan gelir ve yalnız KARŞILAŞTIRILIR; hiçbir
komuta, yola ya da dosya adına dönüşmez.

KURALLAR (bilerek sıkı — bir sohbet mesajı yanlış projeyi işaretleyemesin):
  * Eşleşme: proje kodu → birebir başlık/klasör adı → normalize eşitlik
    (büyük/küçük harf, Türkçe harfsiz yazım, boşluk/noktalama). ALT DİZE ile
    eşleşme YOK: "Sabah" "Sabah Senin"i de "Sabaha Kadar"ı da işaretlemez,
    adayları listeler. Birden çok eşleşme → BELİRSİZ, işaretleme yok.
  * Yalnız `tiktok_publish_id` taşıyan proje işaretlenir; zaten işaretliyse
    değişiklik yok (idempotent, çıkış 0).
  * `build_plan()` `hazir=False` diyorsa (ikiz/uyumluluk/yayin_beklet) İŞARETLEME
    YOK — sebep düz metin. Gerçekten yayınlandıysa bilinçli yol bilgisayarda:
    `tiktok_publish_plan.py --yayinlandi-hepsi` ("EVET" onayıyla).
  * Yazan tek fonksiyon `tiktok_publish_plan.isaretle_yayinlandi` (mantık
    kopyalanmadı); kaynak alanı aynı atomik yazımda.

Çıkış kodları: 0 işaretlendi/zaten işaretli, 2 işaretlenmedi (sebep çıktıda).
Çıktı kısa ve UTF-8 (Hermes terminal aracı UTF-8 çözüyor; cp1254 konsolda da
çökmez — `tiktok_publish_plan._cikti_utf8`).
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tiktok_publish_plan as TPP
import uyumluluk
from tiktok_upload import _load_meta, yayin_kodu

KAYNAK_ETIKETI = "Telegram onayı (kullanıcı)"
_EN_FAZLA_ADAY = 6
_TR_KATLA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
    "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
})
_ONEK = re.compile(r"^(yayinladim|yayinlandi|paylastim)\b[\s:,.-]*")


def normalize(metin: str) -> str:
    """Karşılaştırma anahtarı: Türkçe harfler katlanır, harf/rakam dışı boşluk olur."""
    s = str(metin or "").translate(_TR_KATLA).lower()
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return " ".join(s.split())


def _kayitlar() -> list:
    """[(proje_yolu, gorunen_ad, durum)] — kök listesi `uyumluluk`'tan (tek kanonik)."""
    kayitlar = []
    for proje in uyumluluk.proje_klasorleri():
        try:
            baslik = _load_meta(proje).get("title")
        except Exception:                                    # noqa: BLE001
            baslik = None
        ad = baslik or os.path.basename(os.path.abspath(proje))
        kayitlar.append((proje, ad, TPP._durum_oku(proje)))
    return kayitlar


def eslestir(sorgu: str) -> tuple:
    """(eslesenler, oneriler) döner; ikisi de [(proje, ad, durum)]."""
    kayitlar = _kayitlar()
    ham = " ".join(str(sorgu or "").split())
    anahtar = _ONEK.sub("", normalize(ham))
    if not anahtar:
        return [], []

    def _klasor(p):
        return os.path.basename(os.path.abspath(p))

    kod = anahtar.upper().replace(" ", "")
    if re.fullmatch(r"T[0-9A-F]{4}", kod):
        eslesen = [k for k in kayitlar if yayin_kodu(k[2].get("tiktok_publish_id")) == kod]
        if eslesen:
            return eslesen, []

    eslesen = [k for k in kayitlar if ham in (k[1], _klasor(k[0]))]
    if not eslesen:
        eslesen = [k for k in kayitlar
                   if anahtar in (normalize(k[1]), normalize(_klasor(k[0])))]
    if eslesen:
        return eslesen, []

    # Eşleşme yok: yalnız ÖNERİ (asla işaretlenmez). Bekleyen taslaklar arasından
    # kelime örtüşmesi olanlar; hiçbiri yoksa bekleyenlerin tamamı.
    bekleyen = [k for k in kayitlar
                if k[2].get("tiktok_publish_id") and not k[2].get("tiktok_published_at")]
    kelimeler = set(anahtar.split())
    oneriler = [k for k in bekleyen
                if anahtar in normalize(k[1]) or kelimeler & set(normalize(k[1]).split())]
    return [], (oneriler or bekleyen)


def _liste(kayitlar) -> str:
    adlar = ["%s (%s)" % (k[1], yayin_kodu(k[2].get("tiktok_publish_id")) or "kod yok")
             for k in kayitlar[:_EN_FAZLA_ADAY]]
    fazla = len(kayitlar) - _EN_FAZLA_ADAY
    return ", ".join(adlar) + (" ve %d tane daha" % fazla if fazla > 0 else "")


def onayla(sorgu: str, zaman: str = None) -> tuple:
    """(cikis_kodu, tek_satirlik_metin). Diske yalnız başarıda, tek atomik yazımla dokunur."""
    eslesen, oneriler = eslestir(sorgu)
    if len(eslesen) > 1:
        return 2, ("BELİRSİZ: '%s' birden çok projeyle eşleşti, işaretlenmedi. "
                   "Hangisi? %s — yanıtı kodla tekrarla." % (sorgu.strip(), _liste(eslesen)))
    if not eslesen:
        ek = (" Bekleyen taslaklar: %s" % _liste(oneriler)) if oneriler else ""
        return 2, "BULUNAMADI: '%s' adında proje yok, işaretlenmedi.%s" % (sorgu.strip(), ek)

    proje, ad, durum = eslesen[0]
    kod = yayin_kodu(durum.get("tiktok_publish_id"))
    if not durum.get("tiktok_publish_id"):
        return 2, ("İŞARETLENMEDİ: '%s' TikTok'a hiç taslak olarak yüklenmemiş "
                   "(tiktok_publish_id yok)." % ad)
    if durum.get("tiktok_published_at"):
        return 0, "ZATEN İŞARETLİ: '%s' (%s) — %s, değişiklik yok." % (
            ad, kod, durum["tiktok_published_at"])

    try:
        plan = TPP.build_plan(proje)
    except Exception as e:                                   # noqa: BLE001
        return 2, "İŞARETLENMEDİ: '%s' için yayın planı hesaplanamadı (%s)." % (
            ad, type(e).__name__)
    if not plan.get("hazir"):
        return 2, ("İŞARETLENMEDİ: '%s' (%s) plana göre yayınlanmamalıydı — %s. "
                   "Gerçekten yayınladıysan bilgisayardan: python "
                   "upload/tiktok_publish_plan.py --yayinlandi-hepsi" % (
                       ad, kod, plan.get("engel") or "sebep bilinmiyor"))

    damga = zaman or time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        yazildi, mesaj = TPP.isaretle_yayinlandi(
            proje, zaman=damga, kaynak="%s, %s" % (KAYNAK_ETIKETI, damga))
    except TPP.IsaretlemeHatasi as e:
        return 2, "İŞARETLENMEDİ: %s" % e
    if not yazildi:
        return 0, "ZATEN İŞARETLİ: %s" % mesaj
    _deftere_yaz(proje, ad, kod, damga)
    return 0, "TAMAM: '%s' (%s) TikTok'ta yayınlandı olarak işaretlendi — %s." % (
        ad, kod, damga)


def _deftere_yaz(proje: str, ad: str, kod, damga: str) -> None:
    """Başarılı işareti elle işlemler defterine de yazar (kaynak=telegram).

    State'i YUKARIDA `isaretle_yayinlandi` yazdı; defter yalnız kayıt tutar
    (`state_yansit=False`). Defter yazımı ne sebeple patlarsa patlasın onay
    DÜŞMEZ: işaret zaten diske indi, kullanıcıya TAMAM gider; sorun yalnız
    stderr'e bir UYARI satırı olarak düşer (stdout Hermes'e giden yanıttır).
    """
    try:
        import elle_islem
        elle_islem.ekle(
            "tiktok", "yayinladi",
            "Telegram onayı: '%s' (%s) TikTok'ta yayınlandı" % (ad, kod or "kod yok"),
            proje=os.path.basename(os.path.abspath(proje)), zaman=damga,
            kaynak="telegram", kanit=kod or None, state_yansit=False,
            state_etkisi="tiktok_published_at, tiktok_published_kaynak")
    except Exception as e:                                   # noqa: BLE001
        print("UYARI: elle işlemler defterine yazılamadı (%s: %s) — onay geçerli."
              % (type(e).__name__, str(e)[:150]), file=sys.stderr)


def main(argv=None) -> int:
    TPP._cikti_utf8()
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1 or not args[0].strip():
        print("KULLANIM: python upload/tiktok_yayin_onayi.py \"<şarkı adı ya da kod>\" "
              "(tam olarak bir argüman)")
        return 2
    kod, metin = onayla(args[0])
    print(metin)
    return kod


if __name__ == "__main__":
    sys.exit(main())
