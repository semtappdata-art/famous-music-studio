"""Bir YouTube videosunun privacyStatus'unu günceller — DİĞER `status`
alanlarını, özellikle ZORUNLU AI beyanını, KORUYARAK.

Kullanım:
    python upload/set_privacy.py VIDEO_ID public

NEDEN GÖVDEDE SADECE `privacyStatus` YOK — `videos.update` KISMİ GÜNCELLEME
YAPMAZ: `part` içinde yer alıp gövdede verilmeyen her mutable alan SİLİNİR.
Bu betiğin ilk sürümü gövdeye yalnızca `{"privacyStatus": privacy}` koyuyordu,
yani HER çalıştırmasında sessizce şunları siliyordu:

  * `containsSyntheticMedia: True`  — YouTube'un zorunlu AI-üretimi beyanı.
    Bu kanalın TÜM içeriği (vokal + beste + kapak + video) AI üretimi; beyanı
    yapan tek mekanizma `upload/youtube_upload.py`'nin yükleme sırasındaki
    koşulsuz `containsSyntheticMedia: True`'su. Yükleme SONRASI çalışan bu
    betik onu siliyorsa, o "koşulsuz" garanti (ve `tests/test_uyumluluk_meta.py`
    kararının dayandığı varsayım) geçersizleşiyor.
  * `selfDeclaredMadeForKids: False`

VE BU TESPİT EDİLEMİYOR: `videos.list(part="status")` `containsSyntheticMedia`
alanını GERİ DÖNDÜRMÜYOR (yazılabilir ama OKUNAMAZ; 2026-09-11'de gerçek bir
videoda doğrulandı — dönen alanlar: uploadStatus, privacyStatus, license,
embeddable, publicStatsViewable, madeForKids, selfDeclaredMadeForKids). Yani
"silindi mi" diye bakmanın API yolu yok; sadece Studio'dan elle görülebiliyor.

ÇÖZÜM İKİ PARÇALI, ikisi de şart:
  1. Mevcut `status` OKUNUR, üzerine yazılır, TAMAMI geri gönderilir — böylece
     `license`/`embeddable`/`publicStatsViewable` gibi alanlar korunur.
  2. Round-trip TEK BAŞINA YETMEZ: okumada hiç gelmeyen `containsSyntheticMedia`
     yazmaya da girmezdi. Bu yüzden AI beyanı her yazımda AÇIKÇA yeniden set
     ediliyor — tahmine/round-trip'e bırakılmıyor.

Aynı tuzak `dj_tarama_kontrol.yayina_ac()`'ta zaten çözülmüştü; buradaki
`guvenli_status_govdesi()` o desenin ortak/test edilebilir hâli. Mantığı
KOPYALAMAK yerine bu fonksiyon paylaşılmalı: `dj_tarama_kontrol.py` bir
sonraki dokunuşunda `from set_privacy import guvenli_status_govdesi` ile
buraya bağlanabilir (bu değişiklikte o dosyaya dokunulmadı).

Koruma testi: `tests/test_set_privacy_ai_beyani.py`.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_auth import get_authenticated_service

# Kota defteri: modül düzeyinde (conftest yönlendirmesi yüklü modülde çalışır).
try:
    import youtube_kota
except Exception:  # noqa: BLE001
    youtube_kota = None

GIZLILIKLER = ("public", "unlisted", "private")
# videos.list (1) + videos.update (50) — resmî tablo, bkz. youtube_kota.MALIYETLER.
VIDEO_BASINA_BIRIM = 51

# Geri gönderilmemesi gereken alanlar: `uploadStatus`/`failureReason`/
# `rejectionReason` salt-okunur, `privacyStatus` zaten aşağıda yeniden
# yazılıyor. (`madeForKids` BİLEREK listede değil — `dj_tarama_kontrol`
# yıllardır aynı gövdeyi gönderiyor ve API kabul ediyor; 2026-09-11 18:13'te
# "Gece Seansı Vol. 1" üzerinde canlı doğrulandı.)
SALT_OKUNUR_STATUS_ALANLARI = (
    "uploadStatus",
    "failureReason",
    "rejectionReason",
    "privacyStatus",
)


def guvenli_status_govdesi(mevcut_status, privacy: str) -> dict:
    """`videos.update(part="status")` için KAYIPSIZ gövde üretir.

    `mevcut_status`: `videos.list(part="status")`'tan dönen sözlük.
    """
    durum = dict(mevcut_status or {})
    for alan in SALT_OKUNUR_STATUS_ALANLARI:
        durum.pop(alan, None)
    durum["privacyStatus"] = privacy
    # `publishAt` (golden-hour zamanlaması, bkz. config.next_golden_publish_time)
    # YouTube tarafından SADECE privacyStatus="private" ile kabul ediliyor. Hâlâ
    # zamanlanmış bir videoyu public/unlisted'a çekerken okunan publishAt'i geri
    # göndermek isteği reddettirir — zamanlama zaten anlamını yitirdiği için
    # düşürülüyor.
    if privacy != "private":
        durum.pop("publishAt", None)
    # AÇIKÇA yeniden yazılıyor, round-trip'e GÜVENİLMİYOR (gerekçe: modül
    # docstring'i). Kanalın %100'ü AI üretimi ve hiçbir içerik çocuklara
    # yönelik değil; ikisi de `youtube_upload.py`'nin yükleme sırasında
    # gönderdiği KOŞULSUZ değerlerle birebir aynı — bu betik yüklemenin
    # kararını yeniden üretiyor, ondan sapmıyor.
    durum["containsSyntheticMedia"] = True
    durum["selfDeclaredMadeForKids"] = False
    return durum


def set_privacy(video_id: str, privacy: str) -> None:
    youtube = get_authenticated_service()
    # Okuma başarısızsa YAZMIYORUZ: elde mevcut status olmadan gönderilecek
    # her gövde, korumaya çalıştığımız alanları silen gövdenin ta kendisi
    # olurdu. Sessizce "yalnızca privacyStatus"a düşmek yerine gürültülü
    # şekilde durmak doğru davranış (kapı kendiliğinden AÇILMASIN).
    yanit = youtube.videos().list(part="status", id=video_id).execute()
    ogeler = yanit.get("items") or []
    if not ogeler:
        raise RuntimeError(
            "video bulunamadı ya da status okunamadı: %s — gizlilik "
            "DEĞİŞTİRİLMEDİ (eksik gövde AI beyanını silerdi)" % video_id
        )
    durum = guvenli_status_govdesi(ogeler[0].get("status") or {}, privacy)
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": durum},
    ).execute()
    print(f"  {video_id} -> {privacy} (AI beyanı korundu)")


def main(argv=None) -> int:
    """`set_privacy.py VIDEO_ID [VIDEO_ID ...] GIZLILIK [--gunluk-sinir N] [--zorla]`

    Eski tek videolu kullanım (`VIDEO_ID public`) aynen çalışır.
    argparse BİLEREK yok: video kimliği '-' ile başlayabiliyor (`-CQ7MmUygTQ`)
    ve argparse onu bayrak sanıp reddederdi.

    KOTA KORUMASI (2026-09-13, `upload/youtube_kota.py`): bugünkü harcama + bu iş
    günlük havuzun %60'ını aşacaksa HİÇBİR çağrı yapılmadan durur (çıkış 3).
    `--gunluk-sinir N` sığan kadarını (en fazla N) yapar; `--zorla` %60'ı aşar
    ama saatlik hattın yayın rezervini yine yiyemez.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    zorla, gunluk_sinir, girdiler = False, None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--zorla":
            zorla = True
        elif a == "--gunluk-sinir" and i + 1 < len(argv):
            gunluk_sinir = int(argv[i + 1])
            i += 1
        elif a.startswith("--gunluk-sinir="):
            gunluk_sinir = int(a.split("=", 1)[1])
        else:
            girdiler.append(a)
        i += 1
    if len(girdiler) < 2 or girdiler[-1] not in GIZLILIKLER:
        print("Kullanım: python upload/set_privacy.py VIDEO_ID [VIDEO_ID ...] "
              "public|unlisted|private [--gunluk-sinir N] [--zorla]")
        return 2
    idler, gizlilik = girdiler[:-1], girdiler[-1]
    izin = len(idler)
    if youtube_kota is None:
        print("UYARI: youtube_kota yüklenemedi — kota koruması DEVRE DIŞI")
    else:
        try:
            karar = youtube_kota.toplu_izin(VIDEO_BASINA_BIRIM, len(idler),
                                            gunluk_sinir=gunluk_sinir, zorla=zorla)
        except Exception as e:  # noqa: BLE001
            print("UYARI: kota kontrolü yapılamadı (%s) — koruma DEVRE DIŞI" % e)
        else:
            print(karar["mesaj"])
            if karar["durdu"]:
                return 3
            izin = karar["izin"]
    for video_id in idler[:izin]:
        set_privacy(video_id, gizlilik)
    if izin < len(idler):
        print("Yapılmayan (yarın): %s" % " ".join(idler[izin:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
