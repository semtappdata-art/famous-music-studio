# -*- coding: utf-8 -*-
"""Testlerin ÜRETİM dosyalarına yazmasını engelleyen global koruma.

NEDEN VAR (2026-09-11'de canlı olarak yakalandı): `auto_process.log`'a
18:03:20 damgasıyla şu satırlar düştü —

    Otomatik zamanlama: 7 proje bekliyor, sıradaki için ~1.0 saat daha var ...
    Otomatik zamanlama: 9 proje bekliyor, ... ~0.7 saat ...

Gerçek katalogda o sayılar YOK; bunlar `tests/test_auto_pace_count.py`'nin
fikstürleriydi. Sebep basit ve bu depoda tekrarlanabilir bir desen:
`_auto_pace_count()` `log()` çağırıyor, `log()` de modül düzeyindeki
`LOG_PATH`'e — yani GERÇEK `auto_process.log`'a — yazıyor. Test modülü
`import auto_process` dediği anda o sabit gerçek yolu gösteriyor.

İKİ AYRI ZARAR, ikincisi ciddi:

1. Üretim log'u test gürültüsüyle kirleniyor; bir arızayı log'dan okumak
   (bugün tam da bunu yapmak gerekti) zorlaşıyor.

2. **NABIZ GÖZCÜSÜ KÖRLENİYOR.** `watch_projects.py` makine arızasını haber
   verecek TEK mekanizma ve tespiti `auto_process.log`'un mtime'ına dayanıyor
   (`_heartbeat_check`): 4 saatten uzun süre tazelenmezse "makine kapandı /
   görev bozuldu" uyarısı gidiyor. Testler her koşuşta o dosyanın mtime'ını
   tazelediği için, makine gerçekten dursa bile watchdog ASLA ateşlenmezdi.
   Yani test paketini çalıştırmak, üretimin emniyet ağını kapatıyordu.

3. `log()` içine kilit NABZI da konmuş durumda (`os.utime(LOCK_PATH)`), yani
   testler prensipte gerçek `.auto_process.lock`'a da dokunabilirdi. Pratikte
   bugün dokunmuyorlardı — o satır `if _KILIT_BIZDE:` arkasında ve kilidi
   almayan bir test bayrağı False bırakıyor — ama koruma "bugünkü kod yolu"na
   değil, dosya adına bağlanmalı: `LOCK_PATH` de yönlendiriliyor.

YÖNTEM — neden autouse fixture, neden her testte tek tek DEĞİL:
`tests/test_auto_process_kilit.py` bunu zaten elle yapıyor (modülü `importlib`
ile bağımsız yükleyip `mod.LOG_PATH`/`mod.LOCK_PATH`'i `tmp_path`'e çekerek) ve
DOĞRU olan da oydu — ama o koruma yalnızca o dosyada var. Aynı disiplini 16 test
dosyasına elle dağıtmak, yarın yazılacak 17.'nin yine üretim log'una yazması
demek; bu deponun CLAUDE.md'sindeki "unutulacak bir liste" tuzağının ta kendisi.
Bu yüzden koruma tek noktada ve OTOMATİK: hiçbir test dosyasının bir şey
yapmasına gerek yok, yeni yazılanlar dahil.

`test_auto_process_kilit.py` DEĞİŞTİRİLMEDİ: o kendi bağımsız modül
kopyalarını `importlib` ile yüklüyor (bu fixture'ın gördüğü `sys.modules`
nesnelerinden farklı nesneler) ve yollarını yüklemenin hemen ardından kendisi
kuruyor. İki mekanizma çakışmıyor, aynı sonucu veriyor.

Yönlendirme yalnızca YAZILAN dosyalara (log / kilit / marker) uygulanıyor;
token ve gizli anahtar yolları KAPSAM DIŞI — onlar okunuyor, testler zaten
kendi taklitlerini kuruyor ve buradan boşa çıkarmak mevcut testlerin
davranışını sessizce değiştirirdi.
"""

import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sadece üretimde YAZILAN yol sabitleri. Yeni bir modül aynı adlardan birini
# tanımladığı anda korumaya kendiliğinden dahil olur — bakım gerektirmez.
KORUNAN_YOL_ADLARI = (
    "LOG_PATH",
    "LOCK_PATH",
    "AUTO_PROCESS_LOG_PATH",
    "DJ_FAMOUS_LOG_PATH",
    "HEARTBEAT_MARKER_PATH",
    # 2026-09-12'de EKLENDİ, aynı sınıftan dördüncü vaka — ve en sinsisi.
    # `upload/saglik_durum.json` (saglik_kontrol + weekly_report) sadece bir
    # bildirim damgası dosyası sanılıyordu, bu yüzden korumaya alınmamıştı;
    # testler ona yazsa bile en fazla bir günlük uyarı kaybolurdu. Ama
    # `saglik_kontrol.kacan_kosu()` ile o dosya ÖLÇÜM KAYNAĞI oldu:
    # `son_kosu_ts`, "saatlik hattın sonuna en son ne zaman ulaşıldı"yı tutuyor
    # ve kaçan koşu tespiti TAM OLARAK bu damgayla yapılıyor. `kontrol_et()`
    # çağıran (ve DURUM_DOSYASI'nı kendisi yönlendirmeyen) BİR test bile —
    # ör. test_ses_takip_denetimi.py — üretim dosyasına "son koşu: şimdi"
    # yazıyordu. Bedeli tam olarak nabız gözcüsündeki (madde 2) ile aynı:
    # gece ölen bir otomasyonun 9 saatlik boşluğu, sabah pytest çalıştırmak
    # yüzünden GÖRÜNMEZ olurdu. Kendi yolunu zaten tmp'ye çeken testler
    # (test_durum_atomik_yazim, test_kacan_kosu, ...) etkilenmiyor: onların
    # monkeypatch'i bu autouse fixture'dan SONRA çalışıyor.
    "DURUM_DOSYASI",
    # 2026-09-12'de EKLENDİ, beşinci vaka — ve tek "log dosyası olmayan"ı.
    # `derleme.HEDEF_KOK` (derleme.py) GERÇEK `derlemeler/` klasörü, ve
    # `derleme.uret()` oraya klasör AÇIP video YAZIYOR (önce `.tmp-<ad>`,
    # sonra `os.replace` ile `HEDEF_KOK/<ad>`). Yani `uret()` çağıran ve
    # yolu kendisi tmp'ye çekmeyen BİR test bile, yayınlanmış gerçek
    # içeriğin (`derlemeler/Gece Seansı Vol. 1`, 1,4 GB medya) yanına yeni
    # bir klasör bırakırdı. Öncekilerden farkı, zararın log kirlenmesi
    # değil KATALOĞA SAHTE BİR ÖĞE eklenmesi olması: `derlemeler/` altındaki
    # her klasör `dj_famous_process.py --base derlemeler` için "bekleyen
    # set" demek (`find_pending_sets`) ve o çağrı saatlik hattan otomatik
    # tetiklenebiliyor (`dj_tarama_kontrol._kalan_platformlari_isle`) — yani
    # bir test artığı YAYIN kuyruğuna girebilirdi.
    # `tests/test_derleme_telif_kapisi.py` yolu zaten kendisi yamalıyor
    # (doğru olan da oydu, ve bu fixture ona dokunmuyor); ama koruma tek bir
    # test dosyasının hatırlamasına bırakılamaz — CLAUDE.md'deki "unutulacak
    # liste" tuzağı burada da geçerli. Kanıt: `tests/test_conftest_hedef_kok.py`.
    "HEDEF_KOK",
)


def _repo_modulleri():
    """sys.modules içinde bu depodan gelen modüller.

    YENİ import YAPILMIYOR (bilerek): pytest tüm test modüllerini fixture'lar
    çalışmadan ÖNCE, toplama aşamasında import ediyor — yani bir testin
    kullandığı her repo modülü bu noktada zaten sys.modules'te. Burada
    `import_module` çağırmak ise kullanılmayan ağır modülleri (render,
    generate_cover zinciri) her testte yüklemek demekti.
    """
    for mod in list(sys.modules.values()):
        try:
            dosya = getattr(mod, "__file__", None)
        except Exception:      # yarı-yüklenmiş/egzotik modüller
            continue
        if not dosya:
            continue
        try:
            tam = os.path.abspath(dosya)
        except (OSError, ValueError):
            continue
        if tam.startswith(_REPO + os.sep):
            yield mod


@pytest.fixture(scope="session")
def _izolasyon_kumu(tmp_path_factory):
    """Tek bir geçici klasör — test başına bir tane açmak 250+ boş klasör
    demekti; yollar modül adıyla öneklendiği için çakışma olmuyor."""
    return tmp_path_factory.mktemp("uretim_izolasyonu")


@pytest.fixture(autouse=True)
def uretim_dosyalarini_koru(monkeypatch, _izolasyon_kumu):
    """Her testte repo modüllerinin log/kilit yollarını geçici klasöre çeker."""
    kum = _izolasyon_kumu
    for mod in _repo_modulleri():
        for ad in KORUNAN_YOL_ADLARI:
            mevcut = getattr(mod, ad, None)
            if not isinstance(mevcut, str):
                continue
            # SADECE depo içine bakan yollar yönlendiriliyor. Bir test kendi
            # yolunu zaten tmp'ye çekmişse (test_watch_scan, test_dj_yayin_kapisi)
            # ona dokunulmuyor — o testin niyeti daha spesifik.
            if not os.path.abspath(mevcut).startswith(_REPO + os.sep):
                continue
            hedef = kum / ("%s__%s" % (mod.__name__.replace(".", "_"),
                                       os.path.basename(mevcut)))
            monkeypatch.setattr(mod, ad, str(hedef), raising=False)
    yield
