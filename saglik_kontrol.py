# -*- coding: utf-8 -*-
"""Sessizce duran hatları yakalayan sağlık kontrolleri — saatlik koşudan çalışır.

NEDEN VAR: Depoda bu arızaları yakalamak için yazılmış İKİ koruma vardı ve
2026-09-11 taramasına göre **ikisi de hiç çalışmıyordu**:

1. `netlify_kontrol.py` — kendi docstring'i: *"Token süresi dolduğunda bu adım
   401 veriyor ve tüm Instagram yüklemeleri sessizce duruyor — 2026-09-08'de
   tam olarak bu oldu ve 25+ koşu boyunca fark edilmedi."* Depoda tek referansı
   kendi kullanım örneğiydi; hiçbir yerden çağrılmıyordu.
2. `weekly_report._check_instagram_token_expiry()` — deponun TEK Instagram
   token süre kontrolü. `weekly_report.py` hiçbir zamanlayıcıya bağlı değil,
   yani bu kontrol de hiç çalışmıyordu. Token ~60 günde sessizce doluyor.

3. **Zamanlanmış görev TANIMININ kendisi** (2026-09-11 23:15, bugün eklendi) —
   `gorev_tanimlari()`. Yukarıdaki iki maddeden farklı olarak bu, Python
   kodunda DEĞİL, Windows'un görev kaydında duran bir arıza sınıfı: görev
   tanımı `git pull` ile YAYILMIYOR, yani `setup_task_scheduler.ps1`
   düzeltilse bile üretim makinesinde HİÇBİR ŞEY değişmiyor — script elle
   yeniden çalıştırılana kadar. Bu adım o farkı GÖRÜNÜR kılıyor.

4. **Koşunun KENDİSİ hiç olmadıysa** (2026-09-12, `kacan_kosu()`) — yukarıdaki
   üç adım da "koşu gerçekleşti" varsayımının ÜSTÜNE kurulu; saatlik görev hiç
   tetiklenmediğinde hiçbiri çalışmaz ve log'a TEK SATIR bile düşmez.
   11 Eylül 21:12 → 12 Eylül 06:46 arasındaki 9,5 saatlik boşluk (9 kaçan
   tetik) tam olarak böyle görünmezdi. Bu adım o boşluğu KENDİ damgasıyla
   ölçüyor.

5. **Yayına giden yol sessizce kapalıysa** (2026-09-12, `git_senkron()`) —
   `latest_release.regenerate()` saatlik hatta DOĞRU bağlı ve `docs/latest.html`'i
   her koşuda DİSKTE güncelliyor; `git_sync.push_path()` ise ilk iş olarak dala
   bakıp `main` değilse sessizce `return` ediyor. Üretim klasörü başka bir dalda
   durduğu için sayfa 2026-09-05'ten beri CANLI'da bayat kaldı (14 giriş, oysa
   20 olmalı) ve bu yedi gün boyunca ne log'a ne bildirime tek satır düştü.
   Instagram/TikTok bio linkinden çıkan TEK tıklanabilir yol o sayfa olduğu
   için bedeli doğrudan trafik. Dal kapısının KENDİSİ doğru (bkz. git_sync.py
   docstring'i); bu adım kapıyı değil, kapının SESSİZLİĞİNİ kapatıyor.

Yani "sessiz duruşu yakalamak için yazılmış ama kendisi çalışmayan koruma" —
bugün bulunan desenin en saf hali. Bu modül hepsini saatlik hatta bağlıyor.

Bildirimler GÜNDE BİR: saatlik koşuda her seferinde telefon çalması uyarıyı
değersizleştirir (aynı gerekçe facebook veri erişimi uyarısında da var).
"""

import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

INSTAGRAM_TOKEN = os.path.join(REPO, "upload", "instagram_token.json")
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")

# Kaç gün kala uyarılsın. Instagram token'ı ~60 günlük; 10 gün, yeniden
# yetkilendirme için rahat bir pencere.
INSTAGRAM_UYARI_GUN = 10

# --- Kaçan koşu (log boşluğu) sabitleri ------------------------------------
#
# KAYNAK SEÇİMİ — `auto_process.log`'un son satırı DEĞİL, KENDİ damgamız.
# İki aday vardı, log ÜÇ ayrı sebeple elendi:
#   1. Log, bu kontrol çalışmadan ÖNCE bu koşu tarafından yazılıyor:
#      `main()` boyunca onlarca `log()` çağrısı var, `trim_log(LOG_PATH)` de
#      `_saglik_kontrol()`ten önce koşuyor. Yani biz baktığımızda son satırın
#      damgası HER ZAMAN "az önce" — ölçmek istediğimiz boşluk kendi
#      yazdığımız satırlarla kapanmış oluyor. Kaynak olarak kullanılamaz.
#   2. `log_rotate.trim_log()` dosyayı 7 günde bir YENİDEN YAZIYOR (ve
#      maskeleme yaptığında satır sayısı değişmese bile yeniden yazıyor) —
#      mtime'a da, "dosyanın ilk satırı" gibi bir çapaya da güvenilemez.
#   3. Kaçan koşu log'a TEK SATIR bırakmaz; yani log'da aradığımız şey zaten
#      YOK. Yokluktan ölçüm yapmak için ayrı bir referansa ihtiyaç var.
# Kendi damgamızın tek tuzağı "ilk kurulumda boş" — o da tek bir dalla
# çözülüyor (aşağıda: ilk koşu damgayı atar, hiçbir şey iddia etmez).
# Damga `_durum()` dosyasında (upload/saglik_durum.json) epoch saniye olarak
# duruyor ve `main()`in `finally` bloğundan yazıldığı için anlamı net:
# "saatlik hattın SONUNA en son ne zaman ulaşıldı".
SON_KOSU_ANAHTARI = "son_kosu_ts"

# Saatlik tetikleyicinin beklenen aralığı (setup_task_scheduler.ps1).
BEKLENEN_KOSU_ARALIGI_SN = 60 * 60

# EŞİK — 4 saat. NEDEN 1 ya da 2 değil:
#   - TEK kaçan koşu gürültüdür: kısa bir uyku, `-StartWhenAvailable`
#     telafisinin dakikalık kayması (13:32/14:34 damgaları gerçekten görüldü)
#     ya da makinenin o an meşgul olması tek bir tetiği kaydırabiliyor.
#   - Görevde `MultipleInstances=IgnoreNew` + `ExecutionTimeLimit` var: 2 saat
#     süren TEK bir koşu, arkasındaki tetikleri YUTAR. Damga koşunun SONUNDA
#     atıldığı için bu durumda boşluk meşru olarak ~3 saate çıkabiliyor.
#     3 saatlik bir eşik bu normal durumu arıza diye raporlardı.
#   - `watch_projects.HEARTBEAT_STALE_SECONDS` de aynı gerekçeyle 4 saat.
#     İki emniyet ağının AYNI eşiği kullanması bilinçli: biri (dakikalık
#     Watcher) öldüğünde diğeri (bu kontrol) aynı olayı aynı anda görsün.
#   - Maliyet tarafı ucuz: yayın tabanı zaten 52 saat, 4 saatlik gecikme tek
#     bir yayını bile kaçırtmaz.
KACAN_KOSU_ESIGI_SN = 4 * 60 * 60

# Makine kapalı/uykudaysa bildirim GİTMEZ (gece kapalı duran bir dizüstü için
# her sabah alarm çalmamalı — kullanıcı kuralı). Ama bunun da bir tavanı var:
# 24 saattir hiç koşu yoksa sebebi ne olursa olsun kanal DURMUŞ demektir ve
# operatörün bilmesi gereken tek bir eylem kalır ("makineyi aç"). Normal bir
# gece ~9-10 saat olduğu için bu tavan her sabah çalmaz.
UZUN_SESSIZLIK_ESIGI_SN = 24 * 60 * 60

# "Makine bu boşluk boyunca ayaktaydı" kıyasında tanınan pay: açılış/uyanma
# damgası ile ilk görev tetiği arasında her hâlükârda birkaç dakika var.
GUC_TOLERANS_SN = 15 * 60

# --- Git senkronizasyonu / bio linki sayfası -------------------------------
#
# ÖLÇÜLEN OLGU: "dal `main` değil" DEĞİL — "CANLI sayfa GERİDE".
#
# ARIZA (2026-09-05 -> 2026-09-12, yedi gün kimse fark etmedi): Instagram ve
# TikTok bio linki `famousmusicstudio.com/latest.html`'e gidiyor ve o iki
# platformdan çıkan TEK tıklanabilir yol bu sayfa (caption'larda dış link
# BİLEREK yok, bkz. CLAUDE.md). `latest_release.regenerate()` sayfayı her
# saatlik koşuda DİSKTE doğru üretiyordu; `git_sync.push_path()` ise ilk iş
# olarak dala bakıp `main` değilse sessizce `return` ediyor. Üretim klasörü
# başka bir dalda durduğu için push HİÇ olmadı: canlı sayfada 14 giriş,
# diskte 20 — altı yayındaki içerik (bir de "Derlemeler" bölümünün tamamı)
# bio linkinden görünmüyordu. `git log --grep` sıfır commit, log'da sıfır
# satır: arızanın kendisi de, yokluğu da GÖRÜNMEZDİ.
#
# NEDEN DAL DEĞİL DE GİRİŞ SAYISI — "dal main değil" en dolaysız ölçüt ama
# hem YETERSİZ hem GÜRÜLTÜLÜ:
#   - Yetersiz: sayfayı geride bırakan tek sebep dal değil. Push reddi, ağ
#     yokluğu, uzak tarafın ileride olması aynı sonucu verir ve üçü de aynı
#     şekilde sessizdir (`push_path` hepsinde vazgeçiyor). Sonucu ölçmek
#     sebeplerin hepsini birden yakalar.
#   - Gürültülü: kullanıcı BİLEREK başka bir dalda çalışıyor olabilir (şu an
#     öyle). Her saat "dal main değil" diye bağıran bir uyarı, yanındaki
#     gerçek uyarıları da değersizleştirir. Dal tek başına ZARARSIZ; zarar,
#     o sürede yeni yayın çıkıp sayfaya girmemesi. Eksik giriş sayısı zaten
#     tam olarak "bu sürede kaç yayın kayboldu" demek.
# Dal yine de OKUNUYOR — alarm ölçütü olarak değil, mesajın içindeki SEBEP
# ve DÜZELTME cümlesini doğru seçmek için (dal farklıysa kapı kapalıdır;
# dal main ise kapı açık, arıza push'un kendisinde).
#
# AĞA ÇIKMIYOR: `git show origin/main:docs/latest.html` YEREL uzak-izleme
# ref'ini okur, `fetch` gerektirmez. O ref `git fetch`/`git pull` yapılmadıkça
# bayatlayabilir — üstelik tam bu arızada `auto_pull()` de aynı dal kapısından
# dönüyor, yani ref haftalardır tazelenmemiş olabilir. YÖN önemli: bayat ref
# canlı sayfayı olduğundan GERİ gösterir, yani yanlış alarm üretme riski
# buradadır. Panzehir olarak `git fetch` eklemek BİLEREK reddedildi (saatlik
# hatta ağ çağrısı + uzak-izleme ref'ini bir tanı adımının yan etkisiyle
# oynatmak). Yerine iki şey var: (1) aşağıdaki ZAMAN eşiği, (2) bu dosyanın
# origin/main'deki tek yazarı zaten bu otomasyonun kendisi — `push_path`
# başarılı olduğunda git uzak-izleme ref'ini KENDİSİ günceller, yani ref'in
# bayatlaması pratikte "bizim push'umuz olmadı" ile aynı şey.
#
# Diskteki sayfa `regenerate()` ÇAĞRILMADAN okunuyor: o fonksiyon
# `docs/latest.html`'e YAZAR ve bir TANI adımının yan etkisi olamaz (aynı
# ilke: `gorev_tanimlari` yalnız `Get-*` kullanıyor). Tazelik zaten garanti —
# `auto_process.main()`in `finally` bloğunda `_refresh_latest_listing()`
# (regenerate + push) `_saglik_kontrol()`ten ÖNCE koşuyor. O sıra bozulsa
# bile en kötü hâl "bir koşu bayat" (1 saat), eşiğin çok altında.
CANLI_SAYFA_RELPATH = "docs/latest.html"
CANLI_SAYFA_REF = "origin/main"

# Giriş sayısı MARKUP'TAN BAĞIMSIZ ölçülüyor: benzersiz YouTube video kimliği
# kümesi. `<li>` saymak kırılgan olurdu — canlı sürüm (2026-09-05) ile
# diskteki sürüm (2026-09-11 tasarım yenilemesi) AYNI şablon değil: yenisinde
# satırda küçük resim `<img>` + `<span>` var, eskisinde düz metin. İki farklı
# şablonu karşılaştıran bir ölçüt, şablon her değiştiğinde sessizce yanlış
# cevap verirdi — tam da bu modülün yakalamak için var olduğu sınıf.
_VIDEO_LINK_RE = re.compile('href="https://youtu[.]be/([A-Za-z0-9_-]{5,20})"')

# "Sayfanın geride olduğu İLK görülen an" damgası. Sayfa yetişince SİLİNİYOR,
# böylece eşik "kaç saattir GERİDE"yi ölçüyor — "kaç saattir başka dalda"yı
# değil.
GIT_SENKRON_DAMGASI = "git_senkron_geride_ts"

# EŞİK — 6 saat geride kalmış olmak. Neden tek bir koşu yetmiyor:
#   - `push_path()` ağ yokken / uzak taraf ileriyken sessizce vazgeçip BİR
#     SONRAKİ koşuda yeniden deniyor. Tek koşuluk gecikme normal çalışmanın
#     parçası, arıza değil.
#   - Saatlik hatta 6 saat = en az 6 ardışık başarısız deneme; bu kadar süren
#     bir ağ kesintisi artık "geçici" değildir.
#   - Bayat `origin/main` ref'i ihtimaline karşı da tampon: gerçekten push
#     edilmiş bir değişiklik ref'i de güncellemiş olur, aradaki fark ancak
#     push OLMADIYSA kalıcıdır.
#   - Maliyet ucuz: yayın tabanı 52 saat (auto_process.MIN_YAYIN_ARALIGI_SN),
#     6 saatlik gecikme tek bir yayının görünürlüğünü bile ölçülebilir şekilde
#     etkilemez — ama yedi gün etkiliyordu.
GERI_KALMA_ESIGI_SN = 6 * 60 * 60

# Win32_Battery.BatteryStatus: 1=deşarj (pilde), 4=düşük, 5=kritik — üçü de
# "fişte DEĞİL" demek. 2=AC, 3=dolu, 6-9=şarj oluyor, 10/11=belirsiz/kısmi.
_PILDE_DURUMLAR = (1, 4, 5)

# `setup_task_scheduler.ps1`'in kurduğu ÜÇ görev ve her birinin sarmaladığı
# betik. Buradaki adlar o script'tekiyle AYNI olmak zorunda — biri değişirse
# bu kontrol sessizce "görev yok" deyip atlar (kasıtlı, bkz. gorev_tanimlari).
GOREV_BETIKLERI = {
    "FamousMusicStudio-AutoProcess": "auto_process.py",
    "FamousMusicStudio-DjFamousProcess": "dj_famous_process.py",
    "FamousMusicStudio-Watcher": "watch_projects.py",
}
SARMALAYICI_ADI = "gorev_sarmalayici.py"

# SADECE OKUYAN PowerShell sorgusu — `Get-*` dışında hiçbir fiil YOK.
# Register-/Set-/Unregister-/Start-ScheduledTask BURAYA ASLA GİRMEZ: bu bir
# TANI adımı. Görev tanımını değiştirmek kullanıcının elle attığı bir adımdır
# (setup script'i mevcut görevleri silip yeniden kuruyor ve yükseltilmiş izin
# isteyebiliyor) — bir sağlık kontrolünün yan etkisi olamaz.
_PS_SORGU = """
$adlar = @(%s)
$c = New-Object System.Collections.ArrayList
foreach ($a in $adlar) {
  $t = Get-ScheduledTask -TaskName $a -ErrorAction SilentlyContinue
  if ($t) {
    $act = $t.Actions | Select-Object -First 1
    $null = $c.Add([pscustomobject]@{
      ad = $a
      arg = [string]$act.Arguments
      pilde_baslamasin = [bool]$t.Settings.DisallowStartIfOnBatteries
      pilde_dursun = [bool]$t.Settings.StopIfGoingOnBatteries
    })
  }
}
ConvertTo-Json -InputObject @($c) -Compress
"""

# Güç durumu sorgusu — yine SADECE OKUYAN fiiller (Get-*). Üç bilgi:
#   acik_sn   : son AÇILIŞTAN (LastBootUpTime) beri geçen saniye
#   uyanma_sn : son UYANMADAN beri geçen saniye (Power-Troubleshooter, Id 1);
#               olay yoksa/okunamıyorsa -1
#   pil_*     : Win32_Battery — pil yoksa 0 / -1
# Üçü TEK çağrıda alınıyor: saatlik hatta her arıza için ayrı bir PowerShell
# süreci başlatmak (~1 sn) gereksiz. `acik_sn` tek başına YETMİYOR — uyku
# açılış zamanını SIFIRLAMAZ, yani gece uyuyan bir dizüstüde uptime koca bir
# sayı olur ve "makine ayaktaydı" yalanını söyler; boşluğu açıklayan gerçek
# sinyal ikisinin KÜÇÜĞÜ ("kesintisiz ne kadardır ayakta").
_PS_GUC = """
$b = [ordered]@{ acik_sn = -1; uyanma_sn = -1; pil_durumu = 0; pil_yuzde = -1 }
try {
  $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
  $b.acik_sn = [int]((Get-Date) - $os.LastBootUpTime).TotalSeconds
} catch {}
try {
  $ev = Get-WinEvent -MaxEvents 1 -ErrorAction Stop -FilterHashtable @{
    LogName = 'System'
    ProviderName = 'Microsoft-Windows-Power-Troubleshooter'
    Id = 1
  }
  if ($ev) { $b.uyanma_sn = [int]((Get-Date) - $ev.TimeCreated).TotalSeconds }
} catch {}
try {
  $p = Get-CimInstance Win32_Battery -ErrorAction Stop | Select-Object -First 1
  if ($p) {
    $b.pil_durumu = [int]$p.BatteryStatus
    $b.pil_yuzde = [int]$p.EstimatedChargeRemaining
  }
} catch {}
ConvertTo-Json -InputObject ([pscustomobject]$b) -Compress
"""


def _durum() -> dict:
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _kaydet(g: dict) -> None:
    """Damgalari birlestirip ATOMIK yazar (bkz. state_io).

    NEDEN state_io: duz `open(..., "w")` dosyayi ONCE SIFIRLIYOR; `json.dump`
    bitmeden surec olurse (Gorev Zamanlayici timeout'u, guc kesintisi) diskte
    YARIM bir JSON kaliyor. Bu dosya `state.json` kadar kritik degil (bozulursa
    `_durum()` `{}` dondurup en fazla bir gunluk damgayi kaybeder) ama desen
    AYNI ve kaynagi tek yerde duzeltildi — yeni bir kopya yazma.
    """
    d = _durum()
    d.update(g)
    try:
        import state_io
        state_io._atomik_yaz(DURUM_DOSYASI, d)
    except OSError:
        pass


def _bildir(baslik: str, mesaj: str, anahtar: str) -> bool:
    """Günde bir bildirim gönderir (aynı anahtar için). Gönderildiyse True.

    DAMGA SADECE BAŞARIDA ATILIYOR. Eskiden `notify.send` patlasa bile
    `_kaydet({anahtar: bugun})` çalışıyordu — yani telefon bildirim hattı
    bozuksa "Instagram token'ı doldu" uyarısı hiç ulaşmıyor AMA 24 saat
    boyunca tekrar da denenmiyordu. Bu modülün TÜM var oluş gerekçesi
    "sessizce duran korumaları yakalamak"; korumanın kendisi tam o tuzağa
    düşüyordu. Başarısızlıkta damga atılmadığı için bir sonraki saatlik koşu
    yeniden dener.

    İSTİSNA YETMİYORDU (2026-09-11, ikinci düzeltme): `notify.send` ağ yokken,
    ntfy.sh 5xx dönerken ya da kanal hiç kurulu değilken PATLAMIYOR, sessizce
    `False` dönüyor (bkz. notify.py — üç yolun üçü de `return False`). Yani
    damga hâlâ atılıyordu ve "Instagram token'ın doldu" uyarısı, gönderimin
    başarısız olduğu gün kaybolup 24 saat tekrar denenmiyordu. Artık damga
    SADECE `send()` True dönerse atılıyor.

    TEKRAR DENEME / GÜRÜLTÜ DENGESİ — bilerek fazladan bir susturma YOK:
    kanal hiç kurulu değilken bu fonksiyon her saatlik koşuda tekrar deniyor,
    ama bu log'u KİRLETMİYOR çünkü gürültü kontrolü zaten `notify.py`'nin
    içinde: `send()` başarısız olduğu her yolda `uyar_bir_kez()` çağırıyor ve
    o da SÜREÇ başına anahtar başına TEK satır yazıyor. Saatlik koşu ayrı bir
    süreç olduğu için tavan "saatte bir satır" — ve log zaten 7 günde bir
    kırpılıyor (`log_rotate.trim_log`). Buraya ikinci bir "kanal kurulu
    değilse günde bir dene" damgası koymak (`notify.is_configured()` ile)
    tam da bugün temizlenen deseni geri getirirdi: kurulu olmayan kanal,
    GÖRÜNÜR kalması gereken tek durumdur — onu susturmak korumayı yine
    sessiz duruşa çevirir. Uyarı metninin kendisi zaten her koşuda çağıranın
    `log()`'una düşüyor, yani bildirim gitmese de bilgi kaybolmuyor.
    """
    bugun = time.strftime("%Y-%m-%d")
    if _durum().get(anahtar) == bugun:
        return False
    try:
        import notify
        gonderildi = notify.send(baslik, mesaj)
    except Exception as e:
        print("  bildirim gönderilemedi (%s): %s" % (baslik, str(e)[:150]))
        return False
    if not gonderildi:
        # Damga YOK -> bir sonraki saatlik koşu yeniden dener. Sebebi
        # notify.uyar_bir_kez() koşu başına bir kez zaten yazdı.
        return False
    _kaydet({anahtar: bugun})
    return True


def instagram_token_suresi(log=print) -> dict:
    """Instagram token'ının kalan ömrü. weekly_report'tan taşındı."""
    s = {"durum": "yok"}
    if not os.path.isfile(INSTAGRAM_TOKEN):
        return s
    try:
        with open(INSTAGRAM_TOKEN, "r", encoding="utf-8") as f:
            token = json.load(f)
        sure = token.get("expires_in")
        if not sure:
            return {"durum": "sure bilgisi yok"}
        # expires_in dosyanın YAZILDIĞI ana göre göreli; mtime'ı o an kabul
        # ediyoruz (kesin değil ama makul).
        bitis = os.path.getmtime(INSTAGRAM_TOKEN) + sure
        kalan = (bitis - time.time()) / 86400
        s = {"durum": "tamam", "kalan_gun": round(kalan, 1)}
        if kalan < 0:
            mesaj = ("Instagram token'ının süresi ~%d gün önce DOLMUŞ — yüklemeler "
                     "401 veriyor olabilir. Yeniden yetkilendir: "
                     "python upload/instagram_auth.py --print-url" % -kalan)
            log("  UYARI: " + mesaj)
            _bildir("Instagram yetkisi doldu", mesaj, "instagram_bildirim_gun")
            s["uyari"] = True
        elif kalan < INSTAGRAM_UYARI_GUN:
            mesaj = ("Instagram token'ı ~%d gün içinde doluyor — yakında yeniden "
                     "yetkilendirmen gerekecek." % kalan)
            log("  UYARI: " + mesaj)
            _bildir("Instagram yetkisi yenilenmeli", mesaj, "instagram_bildirim_gun")
            s["uyari"] = True
    except (ValueError, OSError, KeyError) as e:
        s = {"durum": "okunamadi", "hata": str(e)[:120]}
    return s


def netlify_araci(log=print) -> dict:
    """netlify_kontrol.main() — Instagram'ın video barındırma adımı.

    Bu adım 401 verdiğinde tüm Instagram yüklemeleri sessizce duruyor.
    Fonksiyon 0 dönerse sağlıklı.
    """
    try:
        import netlify_kontrol
        kod = netlify_kontrol.main()
        if kod != 0:
            mesaj = ("Netlify barındırma kontrolü başarısız (kod %s) — Instagram "
                     "yüklemeleri sessizce durmuş olabilir." % kod)
            log("  UYARI: " + mesaj)
            _bildir("Netlify/Instagram hattı arızalı", mesaj, "netlify_bildirim_gun")
            return {"durum": "arizali", "kod": kod}
        return {"durum": "tamam"}
    except SystemExit as e:            # main() sys.exit kullanıyorsa
        return {"durum": "tamam" if e.code in (0, None) else "arizali"}
    except Exception as e:
        log("  Netlify kontrolü çalıştırılamadı: %s" % str(e)[:150])
        return {"durum": "calistirilamadi", "hata": str(e)[:120]}


def _powershell_yolu():
    """powershell.exe'nin tam yolu. Yoksa None (Windows dışı ya da bulunamadı).

    PATH'e TEK BAŞINA güvenilmiyor: bu modül `pythonw.exe` altında, Görev
    Zamanlayıcı'nın kendi (kısıtlı) ortamından çağrılıyor. `shutil.which`
    önce deneniyor, olmazsa sabit sistem yoluna düşülüyor.
    """
    if os.name != "nt":
        return None
    import shutil
    y = shutil.which("powershell")
    if y:
        return y
    kok = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not kok:
        return None
    y = os.path.join(kok, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    return y if os.path.isfile(y) else None


def _gorev_tanimlarini_oku():
    """Kayıtlı üç görevin tanımını JSON olarak OKUR. Hiçbir şey DEĞİŞTİRMEZ.

    Dönüş: kayıt listesi; okunamadıysa None (çağıran sessizce atlar).

    `CREATE_NO_WINDOW` ŞART: üç görev de `pythonw.exe` ile koşuyor, çünkü bu
    makinede her tetiklenişte açılıp kapanan konsol penceresi kullanıcı
    tarafından REDDEDİLDİ (bkz. CLAUDE.md). Bu bayrak olmadan saatlik koşuda
    bir PowerShell penceresi çakardı — tam da kaçınılan şey, bu kez bir TANI
    adımı yüzünden geri gelirdi.
    """
    exe = _powershell_yolu()
    if not exe:
        return None
    adlar = ",".join("'%s'" % a for a in GOREV_BETIKLERI)
    try:
        p = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", _PS_SORGU % adlar],
            capture_output=True,
            timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    cikti = (p.stdout or b"").decode("utf-8", "replace").strip()
    if not cikti:
        return None
    try:
        veri = json.loads(cikti)
    except ValueError:
        return None
    if isinstance(veri, dict):      # tek kayıtta PowerShell diziyi düzleştirebilir
        veri = [veri]
    return veri if isinstance(veri, list) else None


def gorev_tanimlari(log=print) -> dict:
    """Kayıtlı görevler GERÇEKTEN doğru kurulmuş mu? (bu makineye özel)

    NEDEN VAR — 2026-09-11 23:15 canlı ölçümü, İKİ ayrı arıza aynı anda:

    **A) Pil ayarı.** `New-ScheduledTaskSettingsSet`'in VARSAYILANI "pilde
    başlatma" + "pile geçince durdur". `setup_task_scheduler.ps1` bu iki
    bayrağı yazmadığı için üç görev de öyle kurulmuştu ve fiş çekilince
    otomasyonun TAMAMI sessizce durdu: AutoProcess'in 22:12 tetiği HİÇ
    koşmadı, Watcher `0x8007042B` (ERROR_PROCESS_ABORTED) ile öldürüldü. Aynı
    ayar günün iki çözülmemiş gizemini de açıklıyor — kaybolan
    12:12/13:12/14:12 koşuları (yerlerinde `-StartWhenAvailable` telafisinin
    imzası olan 13:32/14:34 damgaları) ve 02:12'deki 10732 saniyelik bayat
    kilit (`TerminateProcess` `finally`'yi çalıştırmaz, `_release_lock()` hiç
    koşmaz). ps1 düzeltildi — ama:

    **B) Görev tanımı `git pull` ile YAYILMAZ.** Ölçüm anında kayıtlı görevler
    hâlâ ESKİ tanımı taşıyordu (`pythonw.exe auto_process.py`,
    `gorev_sarmalayici.py` YOK; Watcher'ın süre limiti hâlâ `PT2H`, oysa ps1
    onu 5 dakikaya çekmişti) — yani ps1 yazıldığından beri bir kez bile
    yeniden çalıştırılmamış. Kod düzeltmesi ile ÜRETİMDEKİ gerçeklik
    arasındaki bu boşluk, bu deponun en sık arıza sınıfı olan "yazıldı ama
    bağlanmadı"nın Windows tarafındaki karşılığı ve grep'le GÖRÜNMÜYOR.

    Bu adım iki arızayı da yakalıyor — yani (A) bir daha kendi kendini sessizce
    kuramaz: ps1 düzeltmesi geri alınsa bile ilk saatlik koşu bunu söyler.

    SESSİZCE ATLAMA (bilerek): Windows değilse, PowerShell bulunamazsa ya da
    hiçbir görev kayıtlı değilse hiçbir şey demeden geçer — bu makineye özel
    bir denetim; CI'da (Linux) ve kurulum yapılmamış bir checkout'ta gürültü
    üretmemeli.
    """
    if os.name != "nt":
        return {"durum": "atlandi", "sebep": "windows degil"}

    veri = _gorev_tanimlarini_oku()
    if veri is None:
        return {"durum": "atlandi", "sebep": "gorev tanimlari okunamadi"}
    if not veri:
        # Hiçbir görev kayıtlı değil: kurulum henüz yapılmamış bir checkout.
        return {"durum": "atlandi", "sebep": "kayitli gorev yok"}

    sorunlar = []
    gorevler = {}
    for kayit in veri:
        ad = str(kayit.get("ad") or "?")
        arg = str(kayit.get("arg") or "")
        pilde_baslamasin = bool(kayit.get("pilde_baslamasin"))
        pilde_dursun = bool(kayit.get("pilde_dursun"))
        sarmalayici_var = SARMALAYICI_ADI in arg

        if not sarmalayici_var:
            sorunlar.append(
                "%s: sarmalayıcı devrede DEĞİL (Arguments: %s) — betik kendi "
                "log'unu açmadan ölürse (import hatası) geriye TEK BAYT iz kalmaz"
                % (ad, arg or "(bos)"))
        if pilde_baslamasin:
            sorunlar.append(
                "%s: pilde BAŞLAMIYOR (DisallowStartIfOnBatteries=True) — fiş "
                "çekildiği anda bu görev sessizce durur" % ad)
        if pilde_dursun:
            sorunlar.append(
                "%s: pile geçince ÖLDÜRÜLÜYOR (StopIfGoingOnBatteries=True) — "
                "TerminateProcess finally'yi çalıştırmaz, kilit ortada kalır" % ad)

        gorevler[ad] = {
            "arg": arg,
            "sarmalayici": sarmalayici_var,
            "pil_tamam": not (pilde_baslamasin or pilde_dursun),
        }

    eksik = [a for a in GOREV_BETIKLERI if a not in gorevler]

    if not sorunlar:
        return {"durum": "tamam", "gorevler": gorevler, "eksik": eksik}

    for s in sorunlar:
        log("  UYARI: gorev tanimi — " + s)
    mesaj = ("Zamanlanmış görev TANIMLARI bozuk — otomasyon sessizce durabilir:\n"
             + "\n".join("- " + s for s in sorunlar)
             + "\nDüzeltme (ELLE; git pull ile YAYILMAZ): repo klasöründe "
               "powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1")
    _bildir("Gorev tanimlari bozuk", mesaj, "gorev_tanim_bildirim_gun")
    return {"durum": "bozuk", "sorunlar": sorunlar, "gorevler": gorevler,
            "eksik": eksik}


def ses_takip_tutarliligi(log=print) -> dict:
    """`ses_ve_tarz_takibi.md` diskle uyumlu mu? — UYARI, hata DEĞİL.

    NEDEN BURAYA BAĞLI (2026-09-12) — üç aday vardı, ikisi elendi:

    - `uyumluluk.kontrol()`: render'dan VE yüklemeden önce, HER proje için
      ayrı ayrı çalışıyor. Oysa denetlenen şey tek bir proje değil,
      KATALOĞUN TAMAMI ile tek bir markdown dosyasının tutarlılığı — proje
      başına tekrarlanan, hep aynı metni basan bir uyarı olurdu (18 proje →
      aynı satır 18 kez; `--count` ile sınırlı bir koşuda bile birden çok
      kez). Ayrıca o modül bir POLİTİKA KAPISI; oraya "üretim planlama
      aracı eskimiş" bilgisini koymak iki farklı şiddet rejimini aynı
      kapıda karıştırırdı.
    - `validate_project.validate()`: aynı sorun — proje başına, render
      öncesi. Üstelik orası HATA döndürdüğünde render hiç başlamıyor;
      katalog-seviyesi bir bakım uyarısının o hattın yanında durması, ileride
      birinin onu yanlışlıkla hataya çevirmesini kolaylaştırırdı.
    - **`saglik_kontrol` (SEÇİLEN)**: bu modülün tanımı zaten "sessizce duran
      / eskiyen şeyleri GÖRÜNÜR kılmak" ve deseni birebir uyuyor — koşu
      başına TEK kez (auto_process'in `finally` bloğu), bildirimi GÜNDE BİR
      (`_bildir`), hiçbir hatası otomasyonu durdurmuyor. Takip dosyası da
      tam olarak bu sınıftan: kimse kırıldığını fark etmiyor, çünkü kırıkken
      de "çalışıyor" gibi görünüyor.

    Bildirim metni kırpılıyor (`ses_takip_denetimi.ozet`): tablo tamamen
    bozulursa telefona 18 maddelik bir duvar göndermek uyarıyı değersizleştirir.
    """
    try:
        import ses_takip_denetimi
        s = ses_takip_denetimi.denetle()
    except Exception as e:
        # Denetimin KENDİSİ patlarsa sessiz kalma — bu modülün tüm gerekçesi bu.
        log("  Ses/tarz takip denetimi çalıştırılamadı: %s" % str(e)[:150])
        return {"durum": "calistirilamadi", "hata": str(e)[:120]}

    if s.get("durum") == "tamam":
        return s

    gosterilecek = ses_takip_denetimi.ozet(s)
    for u in gosterilecek:
        log("  UYARI: ses/tarz takibi — " + u)
    mesaj = ("`ses_ve_tarz_takibi.md` diskle uyumsuz — vokal çeşitliliği kuralı "
             "YANLIŞ bir geçmişe bakıyor olabilir:\n"
             + "\n".join("- " + u for u in gosterilecek)
             + "\nDüzeltme ELLE: tabloyu güncelle ve dosyanın başındaki "
               "'SON DURUM' satırını da düzelt.")
    _bildir("Ses/tarz takibi eskimiş", mesaj, "ses_takip_bildirim_gun")
    return s


def _sure_metni(sn: float) -> str:
    """Saniyeyi telefonda okunabilir bir süreye çevirir ("9 sa 34 dk")."""
    sn = max(0, int(sn))
    saat, dk = sn // 3600, (sn % 3600) // 60
    return "%d sa %02d dk" % (saat, dk) if saat else "%d dk" % dk


def _guc_durumu():
    """Makine ne kadardır KESİNTİSİZ ayakta + pil durumu. Okunamazsa None.

    "Kesintisiz ayakta" = min(açılıştan beri, son uyanmadan beri). İkisi de
    gerekli: kapanma/açılma `acik_sn`'i sıfırlar ama UYKU sıfırlamaz — sadece
    uptime'a bakan bir kontrol, gece uyuyan bir dizüstüyü "sürekli açıktı"
    sanıp her sabah alarm çalardı (kullanıcının açıkça istemediği şey).

    None dönüşü "sorun yok" DEĞİL, "bilmiyorum" demektir; çağıran onu ayrı bir
    dal olarak ele alıyor (bkz. kacan_kosu).
    """
    exe = _powershell_yolu()
    if not exe:
        return None
    try:
        p = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", _PS_GUC],
            capture_output=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    cikti = (p.stdout or b"").decode("utf-8", "replace").strip()
    if not cikti:
        return None
    try:
        veri = json.loads(cikti)
    except ValueError:
        return None
    if not isinstance(veri, dict):
        return None

    def _say(ad, varsayilan=-1):
        try:
            return int(veri.get(ad))
        except (TypeError, ValueError):
            return varsayilan

    acik = _say("acik_sn")
    uyanma = _say("uyanma_sn")
    adaylar = [x for x in (acik, uyanma) if x >= 0]
    pil_durumu = _say("pil_durumu", 0)
    return {
        "acik_sn": acik,
        "uyanma_sn": uyanma,
        # Her ikisi de okunamadıysa "bilmiyorum" (None) — 0 demek "makine daha
        # yeni açıldı" anlamına gelirdi ve boşluğu YANLIŞLIKLA açıklardı.
        "uyanik_sn": min(adaylar) if adaylar else None,
        "pil_durumu": pil_durumu,
        "pil_yuzde": _say("pil_yuzde"),
        "pilde": pil_durumu in _PILDE_DURUMLAR,
    }


def kacan_kosu(log=print) -> dict:
    """Saatlik koşu KAÇTI mı? — bu deponun en pahalı arıza sınıfının imzası.

    NEDEN VAR (2026-09-11/12 canlı vakası): `auto_process.log`'da 11 Eylül
    21:12 ile 12 Eylül 06:46 arasında 9,5 saatlik bir boşluk var. Dokuz saatlik
    tetik (22:12, 23:12, 00:12 ... 06:12) kaçtı ve log'a TEK BİR SATIR bile
    düşmedi — kaçan koşunun tanımı bu: geriye hiçbir iz BIRAKMAZ. Bu modüldeki
    diğer dört adımın hiçbiri onu göremez, çünkü hepsi "koşu gerçekleşti"
    varsayımının ÜSTÜNE kurulu; koşunun kendisi olmadığında hiçbiri çalışmaz.
    Sebep de biliniyor: üç görev de `DisallowStartIfOnBatteries` /
    `StopIfGoingOnBatteries` ile kurulu (bkz. gorev_tanimlari), makine fişten
    çıkınca otomasyonun TAMAMI sessizce duruyor ve dakikalık Watcher (ikinci
    emniyet ağı) da aynı sebeple ölü olduğu için nabız uyarısı da gelmiyor.

    ÖLÇÜM: kendi damgamız (SON_KOSU_ANAHTARI) — log DEĞİL, gerekçesi sabitin
    yanında.

    MAKİNE KAPALI/UYKUDA = NORMAL: boşluk, makinenin KESİNTİSİZ ayakta olduğu
    süreden uzunsa (`_guc_durumu`), koşular "kaçmadı" — makine o sırada zaten
    yoktu. O durumda log'a bir satır düşer ama TELEFON ÇALMAZ. Tek istisna
    UZUN_SESSIZLIK_ESIGI_SN: 24 saat sonra sebep artık önemli değil.

    GÜÇ DURUMU OKUNAMAZSA BİLDİRİM GİDER (bilerek): "bilmiyorum" masumiyet
    karinesi değildir. Sessiz kalmak, tam da bu modülün yakalamak için var
    olduğu deseni ("koruma var, çalışmıyor, kimse bilmiyor") geri getirirdi.
    Bunun yerine mesajın içinde güç durumunun okunamadığı açıkça yazıyor.

    BİLDİRİM YORGUNLUĞU: `_bildir(..., "kacan_kosu_bildirim_gun")` — mevcut
    günde-bir mekanizmasının aynısı. Saatlik koşuda aynı arıza için ikinci bir
    bildirim gitmez; damga da yalnızca gönderim BAŞARILIYSA atılıyor.

    Damga HER koşuda (hangi dala girilirse girilsin) tazeleniyor: aksi hâlde
    bir kez oluşan boşluk sonsuza kadar "kaçan koşu" diye raporlanırdı.
    """
    simdi = time.time()
    ham = _durum().get(SON_KOSU_ANAHTARI)
    try:
        onceki = float(ham)
    except (TypeError, ValueError):
        onceki = None

    # İLK KURULUM / bozuk damga: iddia edecek hiçbir şey yok. Sessizce damgayı
    # at ve çık — burada uyarmak, yeni bir checkout'un ilk koşusunda her
    # seferinde yanlış alarm demek olurdu.
    if onceki is None:
        _kaydet({SON_KOSU_ANAHTARI: simdi})
        return {"durum": "ilk_kosu"}

    bosluk = simdi - onceki
    if bosluk < 0:
        # Damga GELECEKTE: sistem saati geri alınmış (NTP düzeltmesi, elle
        # değiştirme). Ölçüm anlamsız; damgayı düzelt, alarm verme.
        log("  Kaçan koşu kontrolü: damga gelecekte (sistem saati değişmiş), sıfırlandı.")
        _kaydet({SON_KOSU_ANAHTARI: simdi})
        return {"durum": "atlandi", "sebep": "damga gelecekte"}

    s = {"durum": "tamam", "bosluk_sn": int(bosluk)}
    if bosluk < KACAN_KOSU_ESIGI_SN:
        _kaydet({SON_KOSU_ANAHTARI: simdi})
        return s

    # ~Kaç tetik kaçtı: boşluktan, bu koşuyu doğuran tetiği düşüyoruz.
    kacan = max(1, int(round(bosluk / BEKLENEN_KOSU_ARALIGI_SN)) - 1)
    # Ok işareti olarak "->" — U+2192 DEĞİL (bilerek): bu modül
    # `python saglik_kontrol.py` ile elle de çalıştırılıyor ve bu makinede
    # `sys.stdout.encoding` ANSI kod sayfası (cp1254). Türkçenin ı/ş/ğ harfleri
    # cp1254'te VAR ama "→" YOK — tek bir süs karakteri, tanı çıktısını
    # `UnicodeEncodeError` ile çökertirdi. Aynı tuzağa 2026-09-12'de
    # `upload/tiktok_publish_plan.py` düşmüştü (caption'daki emoji).
    aralik = "%s -> %s" % (time.strftime("%d.%m %H:%M", time.localtime(onceki)),
                           time.strftime("%d.%m %H:%M", time.localtime(simdi)))
    guc = _guc_durumu()
    uyanik = (guc or {}).get("uyanik_sn")

    if uyanik is not None and uyanik + GUC_TOLERANS_SN < bosluk:
        makine_vardi = False
        guc_cumlesi = ("Makine bu sürenin bir kısmında KAPALI/UYKUDAYDI "
                       "(kesintisiz ayakta: %s)." % _sure_metni(uyanik))
    elif uyanik is None:
        makine_vardi = True
        guc_cumlesi = ("Makinenin güç durumu OKUNAMADI — kapalı mıydı yoksa görev mi "
                       "hiç tetiklenmedi, ayırt edilemedi.")
    else:
        makine_vardi = True
        guc_cumlesi = ("Makine bu sürenin TAMAMINDA açıktı — yani görev tetiklenmedi, "
                       "makine kapalı olduğu için değil.")
    if guc and guc.get("pilde"):
        guc_cumlesi += " Şu an PİLDE (%%%s)." % guc.get("pil_yuzde")

    s.update({"durum": "bosluk", "kacan": kacan, "aralik": aralik,
              "makine_vardi": makine_vardi, "guc": guc})

    log("  UYARI: kaçan koşu — saatlik otomasyon %s sessiz kaldı (~%d koşu, %s). %s"
        % (_sure_metni(bosluk), kacan, aralik, guc_cumlesi))

    # Makine yoktuysa telefon çalmaz — 24 saati aşmadıkça.
    if not makine_vardi and bosluk < UZUN_SESSIZLIK_ESIGI_SN:
        s["durum"] = "bosluk_aciklandi"
        _kaydet({SON_KOSU_ANAHTARI: simdi})
        return s

    mesaj = ("Saatlik otomasyon %s sessiz kaldı — ~%d koşu kaçtı (%s).\n%s\n"
             "İlk bak: Görev Zamanlayıcı > FamousMusicStudio-AutoProcess > "
             "Koşullar sekmesi (pilde başlatma/durdurma). Düzeltme ELLE, "
             "git pull ile YAYILMAZ: repo klasöründe "
             "powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1"
             % (_sure_metni(bosluk), kacan, aralik, guc_cumlesi))
    s["bildirildi"] = _bildir("Otomasyon sessiz kaldı", mesaj, "kacan_kosu_bildirim_gun")
    _kaydet({SON_KOSU_ANAHTARI: simdi})
    return s


def _git_oku(argv, timeout: int = 20):
    """SALT OKUMA bir git komutu çalıştırır. (returncode, metin) ya da None.

    Bu modülden git'e giden HER çağrı buradan geçiyor. YAZMA fiili
    (add/commit/push/checkout/branch/reset/stash/merge/rebase) ve AĞA ÇIKAN
    fiil (fetch/pull/push) buraya ASLA girmez: bu bir TANI adımı, tıpkı
    `_gorev_tanimlarini_oku`'nun yalnız `Get-*` kullanması gibi. Bir sağlık
    kontrolünün yan etkisi olarak depo durumunu değiştirmek, yakalamaya
    çalıştığımız sınıfın daha kötü bir versiyonunu üretirdi. Koruma:
    `tests/test_git_senkron_uyarisi.py` bu dosyadaki tüm `_git_oku`
    çağrılarını `ast` ile tarayıp fiili beyaz listeyle karşılaştırıyor.

    `CREATE_NO_WINDOW` ŞART: üç zamanlanmış görev de `pythonw.exe` ile
    koşuyor; konsolsuz bir süreçten `git.exe` çağırmak her saat bir pencere
    çaktırırdı — kullanıcı tarafından REDDEDİLEN davranış (bkz.
    `_gorev_tanimlarini_oku`).

    Çıktı BAYT olarak alınıp `utf-8/replace` ile çözülüyor: `git show` bir
    HTML dosyası döndürüyor ve `text=True` yerel ANSI kod sayfasını
    (bu makinede cp1254) kullanarak Türkçe başlıkları bozardı.
    """
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return None
    try:
        p = subprocess.run(
            ["git"] + list(argv),
            cwd=REPO,
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace")


def _sayfa_girisleri(metin: str) -> set:
    """Sayfadaki benzersiz YouTube video kimlikleri (bkz. _VIDEO_LINK_RE)."""
    return set(_VIDEO_LINK_RE.findall(metin or ""))


def _yerel_sayfa_metni():
    """Diskteki `docs/latest.html`. Okunamazsa None. HİÇBİR ŞEY YAZMAZ."""
    try:
        with open(os.path.join(REPO, CANLI_SAYFA_RELPATH), "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _geri_kalma_metni(sn: float) -> str:
    """Geride kalma süresi. 48 saatten uzun süreler GÜN olarak yazılıyor.

    `_sure_metni` saatlik boşluklar için tasarlandı; bu arıza GÜNLERCE
    sürebiliyor (gerçek vaka: 7 gün) ve telefonda "168 sa 00 dk" okunmuyor.
    """
    if sn >= 48 * 3600:
        gun = int(sn // 86400)
        return "%d gün %d sa" % (gun, int((sn - gun * 86400) // 3600))
    return _sure_metni(sn)


def git_senkron(log=print) -> dict:
    """Bio linki sayfası CANLI'da geride mi kaldı? (sessiz push arızası)

    Gerekçenin tamamı yukarıdaki sabitlerin yanında (CANLI_SAYFA_RELPATH ...
    GERI_KALMA_ESIGI_SN): ne ölçüldüğü, neden dal değil de giriş sayısı,
    neden ağa çıkılmadığı, eşiğin neden 6 saat olduğu.

    ÜÇ SORU (CLAUDE.md):
      1. Kim çağıracak? — `saglik_kontrol.kontrol_et()`.
      2. Hangi görevden? — saatlik `FamousMusicStudio-AutoProcess`;
         `auto_process.main()`in `finally` bloğu zaten `_saglik_kontrol()`
         çağırıyor, yeni bir görev/çağrı noktası EKLENMEDİ.
      3. Çalışmadığını nasıl anlarız? — her dalda log'a en az bir satır
         düşüyor ("tamam" hariç) ve beş senaryonun beşi de testle kilitli.

    YANLIŞ ALARM: sayfa güncelse, dal `main` olmasa bile TELEFON ÇALMAZ —
    en fazla tek bir log satırı. Sayfa geride ama bu ilk gözlemse yine sessiz
    (ne kadardır geride olduğunu bilmiyoruz, damga atılır). Bildirim yalnızca
    "geride VE en az GERI_KALMA_ESIGI_SN kadar süredir geride" olduğunda.

    BİLDİRİM YORGUNLUĞU: `_bildir(..., "git_senkron_bildirim_gun")` — mevcut
    günde-bir mekanizmasının AYNISI; damga yalnızca gönderim BAŞARILIYSA
    atılıyor.
    """
    dal = None
    ham_dal = _git_oku(["rev-parse", "--abbrev-ref", "HEAD"])
    if ham_dal is None:
        # Git yok / `.git` yok / çağrı patladı: git deposu olmayan bir
        # checkout'ta (ya da CI'da) gürültü üretme.
        return {"durum": "atlandi", "sebep": "git okunamadi"}
    if ham_dal[0] == 0:
        dal = ham_dal[1].strip() or None

    yerel = _yerel_sayfa_metni()
    if yerel is None:
        return {"durum": "atlandi", "sebep": "yerel sayfa yok", "dal": dal}

    ham_canli = _git_oku(["show", "%s:%s" % (CANLI_SAYFA_REF, CANLI_SAYFA_RELPATH)])
    if ham_canli is None or ham_canli[0] != 0 or not ham_canli[1].strip():
        # `origin/main` ref'i yok (taze klon, uzak taraf hiç fetch edilmemiş)
        # ya da dosya o ağaçta yok (sayfa henüz hiç yayınlanmamış).
        #
        # BURADA SESSİZ KALMAK, `kacan_kosu`daki "bilmiyorum masumiyet
        # karinesi değildir" kuralıyla ÇELİŞMİYOR: orada ölçülecek OLGU
        # (boşluk) elimizdeydi, eksik olan yalnızca açıklamasıydı. Burada
        # karşılaştırmanın bir tarafı hiç YOK — "geride" diyebilmek için
        # gereken veri mevcut değil. Uyarmak, sayfayı hiç yayınlamamış bir
        # checkout'ta saat başı yanlış alarm demek olurdu.
        if _durum().get(GIT_SENKRON_DAMGASI):
            _kaydet({GIT_SENKRON_DAMGASI: None})
        return {"durum": "atlandi", "sebep": "origin/main okunamadi", "dal": dal}

    yerel_ids = _sayfa_girisleri(yerel)
    canli_ids = _sayfa_girisleri(ham_canli[1])
    # Yön BİLEREK tek taraflı: "diskte var, canlıda yok". Tersi (canlıda var,
    # diskte yok) bir yayının geri çekilmesidir ve bir sonraki başarılı push
    # onu zaten düzeltir — bio linkinden içerik KAYBI değil.
    eksik = yerel_ids - canli_ids

    s = {"durum": "tamam", "dal": dal, "canli": len(canli_ids),
         "yerel": len(yerel_ids), "eksik": len(eksik)}

    if not eksik:
        if _durum().get(GIT_SENKRON_DAMGASI):
            _kaydet({GIT_SENKRON_DAMGASI: None})
        if dal and dal != "main":
            s["durum"] = "dal_farkli"
            log("  git senkron: dal '%s' (main değil) — push kapısı kapalı, ama "
                "canlı sayfa güncel (%d giriş). Bildirim gönderilmedi."
                % (dal, len(canli_ids)))
        return s

    simdi = time.time()
    try:
        ilk = float(_durum().get(GIT_SENKRON_DAMGASI))
    except (TypeError, ValueError):
        ilk = None

    if ilk is None or ilk > simdi:
        # İlk gözlem (ya da sistem saati geri alınmış): ne kadardır geride
        # olduğunu bilmiyoruz. Damgayı at, bu koşuda hiçbir şey iddia etme.
        _kaydet({GIT_SENKRON_DAMGASI: simdi})
        s.update({"durum": "geride_yeni", "geride_sn": 0})
        log("  git senkron: canlı sayfa %d giriş geride (ilk gözlem, damga "
            "atıldı; %d saat sonra hâlâ geridiyse bildirim gider)."
            % (len(eksik), GERI_KALMA_ESIGI_SN // 3600))
        return s

    geride_sn = simdi - ilk
    s.update({"durum": "geride", "geride_sn": int(geride_sn)})
    log("  UYARI: git senkron — canlı bio sayfası %s geride: %d içerik canlıda "
        "YOK (canlı %d, olması gereken %d), dal '%s'."
        % (_geri_kalma_metni(geride_sn), len(eksik), len(canli_ids),
           len(yerel_ids), dal or "?"))

    if geride_sn < GERI_KALMA_ESIGI_SN:
        # Eşik altı: log'da görünür, telefon çalmaz. `push_path()` bir sonraki
        # koşuda zaten yeniden deniyor.
        s["durum"] = "geride_esik_alti"
        return s

    if dal and dal != "main":
        sebep = ("Sebep: üretim klasörü '%s' dalında. git_sync.push_path() "
                 "SADECE 'main' dalında çalışır, başka dalda sessizce vazgeçer "
                 "(kapı doğru, sessizliği değil)." % dal)
        duzeltme = ("Düzeltme ELLE (yayına çıkarma kararı senin): repo "
                    "klasöründe önce 'git status' ile commit'siz "
                    "değişiklikleri gör, sonra üretim checkout'unu 'main' "
                    "dalına al — bir sonraki saatlik koşu sayfayı kendisi "
                    "push eder.")
    else:
        sebep = ("Sebep: dal 'main', yani kapı AÇIK — push'un kendisi "
                 "başarısız oluyor (ağ yok / uzak taraf ileride / reddedildi).")
        duzeltme = ("İlk bak: auto_process.log içinde 'docs/latest.html commit "
                    "edildi ama push edilemedi' satırı.")

    mesaj = ("Bio linki sayfası (famousmusicstudio.com/latest.html) %s GERİDE: "
             "%d yayındaki içerik canlı sayfada HİÇ görünmüyor "
             "(canlıda %d giriş, olması gereken %d).\n"
             "Instagram ve TikTok'tan çıkan TEK tıklanabilir yol bu sayfa.\n"
             "%s\n%s"
             % (_geri_kalma_metni(geride_sn), len(eksik), len(canli_ids),
                len(yerel_ids), sebep, duzeltme))
    s["bildirildi"] = _bildir("Bio linki sayfası bayat", mesaj,
                              "git_senkron_bildirim_gun")
    return s


# --- Yayın durgunluğu (yedinci adım, 2026-09-12) ---------------------------
#
# ÖLÇÜLEN OLGU: "en son NE ZAMAN bir şey YAYINLANDI" — "koşu oldu mu" DEĞİL.
#
# BOŞLUK (bugün doğrulandı): bu modüldeki ALTI adımın hiçbiri yayının
# durduğunu göremiyor.
#   - `kacan_kosu()` KENDİ damgasına bakıyor ve o damga `kontrol_et()` her
#     çağrıldığında (yani HER koşuda) tazeleniyor. Koşu yapılıyor ama hiçbir
#     şey yayınlanmıyorsa "tamam" der — ölçtüğü şey zaten yayın değil, koşu.
#   - `git_senkron()` yerel `docs/latest.html` ile canlı sürüm arasındaki
#     FARKI ölçüyor, BÜYÜMEYİ değil. Hiçbir şey yayınlanmazsa iki taraf eşit
#     kalır ve o da "tamam" der.
#   - Geri kalan dördü (token / Netlify / görev tanımı / ses takibi) tek tek
#     ÖN KOŞULLARA bakıyor; hepsi sağlıklıyken de yayın durabilir.
# Somut senaryo: `uyumluluk.kontrol()` 2026-09-12'de yedi çağrı noktasında
# FAIL-CLOSED yapıldı. Bir kapı kapanırsa proje ATLANIYOR ve geriye yalnızca
# bir log satırı kalıyor — `notify.uyar_bir_kez()` telefona GİTMİYOR (sadece
# log'a yazıyor; telefona giden tek hat `notify.send()` ve otomasyonda onu
# çağıran TEK yer `_bildir()`). Yani katalogdaki her proje sırayla bir kapıya
# takılırsa kanal GÜNLERCE sessizce durur ve kullanıcı ancak "neden video
# çıkmıyor?" diye şüphelenirse fark eder. Bu adım tam olarak o soruyu soran
# tek kontrol.
#
# ÜÇ SORU (CLAUDE.md):
#   1. Kim çağıracak? — `saglik_kontrol.kontrol_et()` (aşağıda, `kacan_kosu`
#      ÖNÜNDE: o adım damgayı tazeleyen adım, sıra bozulursa değil ama
#      okunurluk bozulur; asıl gerekçe `kontrol_et` içindeki notta).
#   2. Hangi görevden? — saatlik `FamousMusicStudio-AutoProcess`;
#      `auto_process.main()`in `finally` bloğu zaten `_saglik_kontrol()`
#      çağırıyor. YENİ görev/çağrı noktası EKLENMEDİ, `auto_process.py`ye
#      DOKUNULMADI.
#   3. Çalışmadığını nasıl anlarız? — "tamam" dışındaki her dal log'a en az
#      bir satır yazıyor ve yedi senaryonun yedisi de testle kilitli
#      (`tests/test_yayin_durgunlugu.py`), `kontrol_et`e bağlı olduğu da
#      `ast` muhafızıyla doğrulanıyor.

# DAMGA SEÇİMİ — SABİT LİSTE DEĞİL, SONEK EŞLEŞMESİ (`*_uploaded_at`).
# Elle sayılan bir liste bu depoda defalarca eskidi (bkz. uyumluluk.KOK_ADLARI
# notu). Diskte BUGÜN yedi farklı ad var — `youtube_uploaded_at`,
# `youtube_shorts_uploaded_at`, `tiktok_uploaded_at`, `instagram_uploaded_at`,
# `telegram_uploaded_at`, `bluesky_uploaded_at`, `facebook_uploaded_at` — ve
# DJ setleri/derlemeler bir SEKİZİNCİSİNİ daha yazıyor
# (`telegram_shorts_uploaded_at`), ki elle yazılmış bir listeye eklenmesi
# kesinlikle unutulurdu. Sonek kuralı yarın eklenecek platformu da kendiliğinden
# kapsıyor. Yön de doğru: burada EKSİK bir anahtar yanlış ALARM üretir (sessizlik
# olduğundan uzun görünür), yani listeyi geniş tutmak güvenli taraf.
YAYIN_DAMGA_SONEKI = "_uploaded_at"

# "Bekleyen proje var mı" ÖLÇÜTÜ — `auto_process._is_fully_done()` KOPYALANMADI
# ve `auto_process` IMPORT DA EDİLMEDİ. İki gerekçe:
#   - `import auto_process` modül düzeyinde `sys.stdout.reconfigure(...)`
#     yapıyor ve `config` + `upload/*` zincirinin tamamını çekiyor. Bir TANI
#     adımının böyle bir yan etkisi olamaz (aynı ilke: `gorev_tanimlari`
#     yalnız `Get-*`, `_git_oku` yalnız salt-okuma fiilleri kullanıyor).
#     Üstelik `auto_process._saglik_kontrol()` bu modülü import ediyor, yani
#     ters yönde bir import döngüsü riski de var.
#   - Sessizce SÜRÜKLENEN bir kopya da istemiyoruz: aşağıdaki dörtlü,
#     `_is_fully_done()`in dörtlüsüyle AYNI kalmak zorunda ve bunu
#     `tests/test_yayin_durgunlugu.py` `ast` ile (auto_process'i çalıştırmadan)
#     doğruluyor. CLAUDE.md bu listeye yeni platform EKLENMESİNİ zaten
#     yasaklıyor, yani küme tasarım gereği sabit.
ANA_PLATFORM_ANAHTARLARI = (
    "youtube_video_id",
    "youtube_shorts_video_id",
    "tiktok_publish_id",
    "instagram_media_id",
)

# SES DOSYASI ŞARTI — bu kontrolün en önemli yanlış-alarm koruması.
# `uyumluluk.proje_klasorleri()` TEK SEVİYE tarıyor ve gördüğü her klasörü
# döndürüyor; bunların hepsi proje DEĞİL. Diskte bugün somut örnek var:
# `dj_sets/Night Drive` — ne `audio.*`, ne `state.json`. Ses şartı olmasaydı o
# klasör SONSUZA KADAR "bekleyen proje" sayılırdı; yani katalog gerçekten
# bitse bile bu nöbetçi ilelebet kurulu kalır ve 78 saat sonra her gün alarm
# çalardı. Ses yoksa boru hattı o klasöre zaten HİÇ girmiyor
# (`auto_process.find_ready_projects` aynı şartı kullanıyor), dolayısıyla
# "yayınlanmayı bekleyen iş" de değildir.
SES_DOSYALARI = ("audio.wav", "audio.mp3", "audio.m4a")

# EŞİK — 78 saat = 1,5 x yayın tabanı. NEDEN 24 ya da 48 DEĞİL:
#   - `auto_process.MIN_YAYIN_ARALIGI_SN` 52 SAAT. Yani "iki gün boyunca
#     hiçbir şey yayınlanmaması" bu kanalda TAMAMEN NORMAL — tasarımın
#     kendisi. 24 ya da 48 saatlik bir eşik HER HAFTA yanlış alarm demek
#     olurdu; üç yanlış alarmdan sonra kimse bildirime bakmaz ve bu nöbetçi
#     de "sessizce ölmüş koruma" sınıfına katılırdı.
#   - Gerçek aralık `max(52 sa, 24 sa / bekleyen sayısı)` (`_auto_pace_count`);
#     ikinci terim 24 saati ASLA aşamayacağı için pratik taban her zaman 52
#     saat. Yani ölçülecek "meşru en uzun sessizlik" 52 saatten başlıyor.
#   - 52'nin ÜSTÜNE eklenen 26 saat, meşru gecikmelerin toplamı: saatlik
#     tetik granülasyonu (~1 sa), golden-hour penceresine kadar bekleme
#     (~en kötü 14 sa) ve makinenin bir gece/bir gün kapalı kalması. Makine
#     kapalılığı zaten `kacan_kosu`nun işi; burada onu ikinci kez alarma
#     çevirmiyoruz, payın içine katıyoruz.
#   - TAVAN tarafı: 78 < 104 (= 2 x 52). Yani alarm, BİRİNCİ yayın penceresi
#     kaçtıktan sonra ama İKİNCİSİ kaçmadan önce çalıyor — gerçek bir duruşta
#     kaybedilen yayın sayısı bir tanede kalıyor.
YAYIN_TABANI_SN = 52 * 60 * 60          # auto_process.MIN_YAYIN_ARALIGI_SN
YAYIN_DURGUNLUK_ESIGI_SN = int(1.5 * YAYIN_TABANI_SN)   # 78 saat


def _proje_state(proje: str) -> dict:
    """Bir projenin `state.json`'ı. Yoksa/bozuksa BOŞ sözlük — ÇÖKMEZ.

    Bozuk JSON'u yutmak burada DOĞRU: bu bir tanı adımı ve bozuk bir state
    zaten "bu projede hiçbir anahtar yok" demek, yani proje "bekleyen"
    sayılır. Yön güvenli tarafta: eksik veri alarmı GECİKTİRMEZ, en fazla
    bir projeyi fazladan bekleyen sayar.
    """
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _damga_ts(deger):
    """`"2026-09-12T06:48:56"` -> epoch saniye. Bozuksa None (auto_process ile
    AYNI biçim; `_last_upload_time` de `%Y-%m-%dT%H:%M:%S` kullanıyor)."""
    if not isinstance(deger, str):
        return None
    try:
        return time.mktime(time.strptime(deger, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _yayin_taramasi() -> dict:
    """Kataloğu TEK geçişte tarar: en yeni yayın damgası + bekleyen projeler.

    Kök listesi ELLE SAYILMIYOR — `uyumluluk.proje_klasorleri()` deponun TEK
    kanonik içerik kökü kaynağı (`projects`, `dj_sets`, `derlemeler`). Elle
    sayan her yer 2026-09-11'de `derlemeler/`i atlamıştı; aynı hatayı yedinci
    kez yapmıyoruz (muhafız: tests/test_kok_listesi_muhafizi.py).

    Dönüş: {"son_ts", "son_kaynak", "bekleyen", "proje"}.
    """
    import uyumluluk

    son_ts = None
    son_kaynak = None
    bekleyen = []
    proje = 0

    for yol in uyumluluk.proje_klasorleri():
        if not any(os.path.isfile(os.path.join(yol, a)) for a in SES_DOSYALARI):
            continue                       # proje değil (bkz. SES_DOSYALARI)
        proje += 1
        state = _proje_state(yol)
        ad = os.path.basename(yol)

        if any(k not in state for k in ANA_PLATFORM_ANAHTARLARI):
            bekleyen.append(ad)

        for anahtar, deger in state.items():
            if not anahtar.endswith(YAYIN_DAMGA_SONEKI):
                continue
            ts = _damga_ts(deger)
            if ts is None:
                continue
            if son_ts is None or ts > son_ts:
                son_ts, son_kaynak = ts, "%s/%s" % (ad, anahtar)

    return {"son_ts": son_ts, "son_kaynak": son_kaynak,
            "bekleyen": bekleyen, "proje": proje}


def yayin_durgunlugu(log=print) -> dict:
    """Bekleyen proje VARKEN yayın durdu mu? (kanalın sessizce durması)

    Gerekçenin tamamı yukarıdaki sabitlerin yanında: ne ölçüldüğü, damgaların
    neden sonekle bulunduğu, "bekleyen proje" ölçütünün neden ses dosyası
    şartı taşıdığı ve eşiğin neden 52 saatlik yayın tabanının 1,5 katı olduğu.

    BEKLEYEN PROJE ŞARTI ZORUNLU — bu kontrolün doğruluğu buna bağlı: katalog
    tamamen bitmişse (yayınlanacak hiçbir şey kalmamışsa) sessizlik NORMALDİR
    ve alarm YANLIŞTIR. Kullanıcı Suno kotası yüzünden yeni şarkı üretmediği
    sürece kanal haftalarca meşru biçimde sessiz kalabilir.

    YANLIŞ ALARM KAPILARI (dördü de sessiz):
      - bekleyen proje yok -> hiçbir şey iddia etme,
      - hiç yayın damgası yok (taze checkout) -> karşılaştırmanın bir tarafı
        eksik, `git_senkron`'daki "origin/main okunamadı" dalıyla aynı gerekçe,
      - damga GELECEKTE (sistem saati geri alınmış) -> ölçüm anlamsız,
      - sessizlik eşiğin altında -> normal bekleme.

    BİLDİRİM YORGUNLUĞU: `_bildir(..., "yayin_durgunlugu_bildirim_gun")` —
    mevcut günde-bir mekanizmasının AYNISI; damga yalnızca gönderim
    BAŞARILIYSA atılıyor.
    """
    try:
        t = _yayin_taramasi()
    except Exception as e:
        # Taramanın KENDİSİ patlarsa sessiz kalma — bu modülün tüm gerekçesi bu.
        log("  Yayın durgunluğu taraması çalıştırılamadı: %s" % str(e)[:150])
        return {"durum": "calistirilamadi", "hata": str(e)[:120]}

    bekleyen = t["bekleyen"]
    s = {"durum": "tamam", "bekleyen": len(bekleyen), "proje": t["proje"]}

    if not bekleyen:
        # Katalog bitti: sessizlik normaldir. En pahalı yanlış alarm burada
        # önleniyor, bu yüzden log'a bile satır yok.
        s["durum"] = "bekleyen_yok"
        return s

    son = t["son_ts"]
    if son is None:
        s.update({"durum": "atlandi", "sebep": "yayin damgasi yok"})
        return s

    simdi = time.time()
    sessizlik = simdi - son
    s["sessizlik_sn"] = int(sessizlik)
    s["son_yayin"] = t["son_kaynak"]

    if sessizlik < 0:
        s.update({"durum": "atlandi", "sebep": "damga gelecekte"})
        log("  Yayın durgunluğu: en yeni damga gelecekte (sistem saati "
            "değişmiş), ölçüm atlandı.")
        return s

    if sessizlik < YAYIN_DURGUNLUK_ESIGI_SN:
        return s

    s["durum"] = "durgun"
    # Tarih biçiminde ok/süs karakteri YOK: bu modül `python saglik_kontrol.py`
    # ile elle de çalıştırılıyor ve bu makinede `sys.stdout.encoding` cp1254
    # (bkz. kacan_kosu'daki aynı not). Türkçenin ı/ş/ğ harfleri cp1254'te VAR,
    # ok işareti (U+2192) YOK. Test: bu fonksiyondaki TÜM metin sabitlerinin
    # cp1254'e kodlanabildiği `ast` ile kilitli.
    son_metni = time.strftime("%d.%m %H:%M", time.localtime(son))
    sure = _geri_kalma_metni(sessizlik)

    log("  UYARI: yayın durgunluğu — %s hiçbir platforma yayın çıkmadı (son "
        "damga %s, %s), ama %d proje bekliyor. Teşhis: python uyumluluk.py"
        % (sure, son_metni, t["son_kaynak"], len(bekleyen)))

    mesaj = ("Kanal %s boyunca HİÇBİR platforma yayın yapmadı (son damga: %s, %s), "
             "ama %d proje hâlâ bekliyor.\n"
             "Yayın tabanı 52 saat, bu uyarının eşiği %d saat — yani en az bir "
             "yayın penceresi tamamen kaçtı, bu normal bekleme DEĞİL.\n"
             "İlk bak: repo klasöründe  python uyumluluk.py  — tek komutluk "
             "teşhis, kapıda takılan projeyi ADIYLA HATA olarak basar "
             "(uyumluluk kapıları fail-closed: kapanan kapı projeyi atlar ve "
             "geriye yalnızca bir log satırı kalır).\n"
             "Sonra: auto_process.log içinde 'Otomatik zamanlama' ve "
             "'uyumluluk' satırları."
             % (sure, son_metni, t["son_kaynak"], len(bekleyen),
                YAYIN_DURGUNLUK_ESIGI_SN // 3600))
    s["bildirildi"] = _bildir("Yayın durdu", mesaj, "yayin_durgunlugu_bildirim_gun")
    return s


def kontrol_et(log=print) -> dict:
    return {
        "instagram_token": instagram_token_suresi(log),
        "netlify": netlify_araci(log),
        # Üçü arasında "Python'ın dışına" bakan TEK adım: düzeltilmiş kodun
        # üretimde gerçekten DEVREDE olduğunu doğrulayan tek yer
        # (bkz. gorev_tanimlari docstring'i, madde B).
        "gorev_tanimlari": gorev_tanimlari(log),
        # Diger uc adimdan farkli olarak bu, bir BORU HATTI arizasini degil
        # bir BELGE eskimesini yakaliyor — ama ayni sinifta: kirikken de
        # "calisiyor" gorunuyor ve bedeli 2026-09-12'de odendi (bkz.
        # ses_takip_denetimi.py). Siddet UYARI; yayini durdurmaz.
        "ses_takibi": ses_takip_tutarliligi(log),
        # Yukaridaki adimlar "yukleme oldu mu" diye sorar; bu adim yuklenenin
        # IZLEYICIYE ULASAN yolunu olcuyor. docs/latest.html diskte dogru
        # uretiliyordu ama origin/main'e HIC push edilmedi (dal kapisi),
        # yani Instagram/TikTok bio linkinden cikan TEK yol yedi gun boyunca
        # bayat kaldi. Olcut dal degil, canli sayfadaki giris sayisi.
        "git_senkron": git_senkron(log),
        # YEDINCI ADIM (2026-09-12). Yukaridaki alti adimin hicbiri "en son ne
        # zaman bir sey YAYINLANDI" diye SORMUYOR: kacan_kosu kendi damgasina
        # bakiyor (o damga her kosuda tazeleniyor), git_senkron yerel/canli
        # FARKINI olcuyor (hicbir sey yayinlanmazsa iki taraf esit kalir),
        # kalan dorduyse on kosullara bakiyor. Yani kosu yapiliyor, ortam
        # saglikli gorunuyor ve kanal GUNLERCE sessizce durabiliyordu — ozellikle
        # uyumluluk kapilari fail-closed yapildiktan sonra (kapanan kapi projeyi
        # atlar, geriye yalnizca bir log satiri kalir; notify.uyar_bir_kez
        # telefona GITMEZ).
        # SIRA: kacan_kosu'dan ONCE, cunku o adim damgayi tazeliyor ve
        # (beklenmedik bir sekilde patlarsa) bu adimin da atlanmasi istenen
        # davranis — "kosunun sonuna ulasildi" iddiasi en sonda dogsun.
        "yayin_durgunlugu": yayin_durgunlugu(log),
        # EN SONDA, bilerek: bu adim damgayi TAZELIYOR ("saatlik hattin sonuna
        # en son ne zaman ulasildi"). Yukaridaki adimlardan biri beklenmedik
        # bir sekilde patlarsa damga da atilmaz ve bir SONRAKI kosu bunu
        # bosluk olarak gorur — istenen davranis bu.
        # Digerlerinden farki: onlar "kosu oldu" varsayiminin USTUNE kurulu
        # kontroller; bu ise kosunun KENDISININ olup olmadigini olcen tek adim.
        "kacan_kosu": kacan_kosu(log),
    }


if __name__ == "__main__":
    print(json.dumps(kontrol_et(), ensure_ascii=False, indent=2))
