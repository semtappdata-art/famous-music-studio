<#
Tek seferlik kurulum scripti — ÜÇ görev kurar:
  1. auto_process.py (ana katalog, günlük 6 üretim) — ESKİ tetikleyicileri (ör.
     günde iki kez 13:00/19:00) otomatik bulup silip, otomatik kademeleme
     mantığının (bkz. README.md, CLAUDE.md) gerektirdiği TEK, SIK (saatte bir)
     bir tetikleyici kurar.
  2. dj_famous_process.py (haftalık DJ Famous seti, bkz. dj_sets/README.md) —
     haftada BİR (varsayılan: Cuma 18:00) çalışan ayrı bir tetikleyici.
  3. watch_projects.py (klasör izleyici) — 1 DAKİKADA bir tekrar eden, projects/
     altına Suno'dan yeni bir ses dosyası düşürüldüğünde onu audio.wav'a çevirip
     auto_process.py'yi hemen tetikleyen bir görev. Saatlik tetikleyiciyle
     ÇAKIŞMAZ — kademeleme kararını hâlâ auto_process.py kendisi verir, bu
     sadece tepki süresini (saatlerden dakikalara) kısaltır.
Görev Zamanlayıcı arayüzünde elle tıklama gerektirmez.

Kullanım (PowerShell'de, repo klasöründeyken):
    powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1
    powershell -ExecutionPolicy Bypass -File setup_task_scheduler.ps1 -DjFamousDayOfWeek Sunday -DjFamousTime 20:00

Yeniden çalıştırmak güvenlidir (idempotent) — var olan aynı isimli görevleri
günceller, eski/farklı isimli auto_process.py görevlerini temizler.
#>

param(
    # Dizi kabul ediyor: haftada birden fazla gun icin
    #   -DjFamousDayOfWeek Tuesday,Friday,Sunday
    # dj_famous_process kosu basina 1 YENI set isliyor (--limit), yani 3 gun
    # = haftada 3 set, hepsi ayni gune yigilmadan.
    [string[]]$DjFamousDayOfWeek = @("Friday"),
    [string]$DjFamousTime = "18:00"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "FamousMusicStudio-AutoProcess"

# python.exe'yi bul: önce repo içinde bir venv, yoksa PATH'teki python
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $found = Get-Command python -ErrorAction SilentlyContinue
    if (-not $found) {
        throw "python.exe bulunamadı — Python PATH'e ekli olmalı ya da $venvPython içinde bir venv olmalı."
    }
    $pythonExe = $found.Source
}

# Görevler python.exe ile çalıştırılırsa her tetiklenişte (watch_projects.py için
# dakikada bir) görünür bir konsol penceresi açılıp hemen kapanıyor. Üç script de
# (auto_process.py/dj_famous_process.py/watch_projects.py) zaten kendi .log
# dosyalarına da yazdığı için konsol çıktısı kaybolmaz — görevlerde pencere açmayan
# pythonw.exe kullanılıyor (aynı klasörde python.exe'nin yanında bulunur).
$pythonwExe = $pythonExe -replace 'python\.exe$', 'pythonw.exe'
if (-not (Test-Path $pythonwExe)) {
    Write-Warning "pythonw.exe bulunamadı ($pythonwExe) — görevler python.exe ile kurulacak, her tetiklenişte kısa bir konsol penceresi görünebilir."
    $pythonwExe = $pythonExe
}

# Üç görev de betiği DOĞRUDAN değil, `gorev_sarmalayici.py` üzerinden çağırıyor.
# NEDEN (2026-09-11 üretim sağlık denetimi): pythonw.exe'de stdout/stderr None'dır
# ve Görev Zamanlayıcı'da stderr'i bir dosyaya yönlendirmenin yolu yoktur — bir
# betik KENDİ .log dosyasını açmadan ÖNCE ölürse (import hatası, sözdizimi hatası,
# eksik bağımlılık) geriye tek bir bayt bile kalmıyordu. Aynı gün auto_process.log'da
# 12:12/13:12/14:12 koşuları HİÇ görünmedi ve nedeni kanıtlanamadı; TaskScheduler
# Operational olay günlüğü de bu makinede KAPALI, yani ikinci bir kaynak da yok.
# Sarmalayıcı, herhangi bir proje modülü import EDİLMEDEN önce bir "BAŞLADI"
# damgası atıyor, çöküşte tam traceback'i ve çıkışta "BİTTİ" damgasını
# gorev_izleri/<betik>.log dosyasına yazıyor. Saf stdlib, pencere AÇMIYOR
# (aynı pythonw.exe, aynı bayrak) — `cmd /c ... 2>>` sarmalayıcısı ise konsol
# uygulaması olduğu için terk ettiğimiz pencere sorununu geri getirirdi.
$wrapper = Join-Path $repoRoot "gorev_sarmalayici.py"
if (-not (Test-Path $wrapper)) {
    throw "gorev_sarmalayici.py bulunamadı ($wrapper) — depo güncel değil. Önce 'git pull' yapıp bu scripti tekrar çalıştır."
}

# auto_process.py'yi çağıran ESKİ görevleri bul ve sil (isim ne olursa olsun —
# ör. daha önce elle kurulmuş, günde 2 kez çalışan 13:00/19:00 görevi)
$existing = Get-ScheduledTask | Where-Object {
    $action = $_.Actions | Select-Object -First 1
    $action -and $action.Arguments -and ($action.Arguments -match "auto_process\.py")
}
foreach ($t in $existing) {
    Write-Host "Eski görev siliniyor: $($t.TaskName)"
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
}

# Yeni görev: saatte bir, süresiz tekrar eden TEK tetikleyici
$action = New-ScheduledTaskAction -Execute $pythonwExe -Argument "`"$wrapper`" auto_process.py" -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
# PİL AYARLARI — `-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries` ÜÇ görevde
# de ŞART. NEDEN (2026-09-11 canlı ölçümü, bu bir DİZÜSTÜ bilgisayar):
# `New-ScheduledTaskSettingsSet`'in VARSAYILANI "pilde başlatma" + "pile geçince
# durdur"dur — yani bu iki bayrak YAZILMAZSA fiş çekildiği anda otomasyonun
# TAMAMI sessizce ölür. Ölçülen sonuç: AutoProcess'in 22:12 tetiği HİÇ koşmadı,
# Watcher `0x8007042B` (ERROR_PROCESS_ABORTED) ile öldürüldü.
# Aynı ayar günün iki çözülmemiş gizemini de açıklıyor:
#   * 12:12/13:12/14:12 koşularının kaybolup yerlerine 13:32/14:34 damgalı
#     (`-StartWhenAvailable` telafisi) koşuların gelmesi — görev pilde hiç
#     BAŞLAMADI, güç gelince telafi koştu;
#   * 02:12'deki "Eski kilit dosyası bulundu (10732s)" — pile geçiş görevi
#     `TerminateProcess` ile öldürüyor, `finally: _release_lock()` HİÇ çalışmıyor,
#     kilit ortada kalıyor.
# Bu satırları silme: silmek "otomasyon fişe bağlıyken çalışır" demektir.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$taskName' görevi saatte bir çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\auto_process.py"
Write-Host "  python : $pythonwExe (sarmalayıcı: gorev_sarmalayici.py)"
Write-Host "  iz     : $repoRoot\gorev_izleri\auto_process.log (BAŞLADI/ÇÖKTÜ/BİTTİ damgaları)"
Write-Host ""
Write-Host "Kontrol için:  Get-ScheduledTask -TaskName '$taskName' | Get-ScheduledTaskInfo"

# --- DJ Famous (haftalık, ayrı görev) ---
$djFamousTaskName = "FamousMusicStudio-DjFamousProcess"

$djFamousOld = Get-ScheduledTask | Where-Object {
    $action = $_.Actions | Select-Object -First 1
    $action -and $action.Arguments -and ($action.Arguments -match "dj_famous_process\.py")
}
foreach ($t in $djFamousOld) {
    Write-Host "Eski DJ Famous görevi siliniyor: $($t.TaskName)"
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
}

$djFamousAt = [DateTime]::ParseExact($DjFamousTime, "HH:mm", $null)
$djFamousAction = New-ScheduledTaskAction -Execute $pythonwExe -Argument "`"$wrapper`" dj_famous_process.py" -WorkingDirectory $repoRoot
$djFamousTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DjFamousDayOfWeek -At $djFamousAt -WeeksInterval 1
# 1 saate kadar sürebilecek set videoları render+3 platform yükleme için ana
# katalogdan (2 saat) çok daha uzun bir süre limiti (bkz. dj_sets/README.md).
# Pil bayrakları: gerekçe yukarıdaki AutoProcess ayarlarının başında — dizüstünde
# varsayılan ayar bu görevi de pilde hiç başlatmaz / başlamışsa öldürür.
$djFamousSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $djFamousTaskName -Action $djFamousAction -Trigger $djFamousTrigger `
    -Settings $djFamousSettings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$djFamousTaskName' görevi her $($DjFamousDayOfWeek -join ', ') günü $DjFamousTime çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\dj_famous_process.py"
Write-Host "  iz     : $repoRoot\gorev_izleri\dj_famous_process.log"
Write-Host "  farklı gün/saat istersen: -DjFamousDayOfWeek <gün> -DjFamousTime <SS:dd> ile yeniden çalıştır"
Write-Host ""
Write-Host "Kontrol için:  Get-ScheduledTask -TaskName '$djFamousTaskName' | Get-ScheduledTaskInfo"

# --- Klasör izleyici (watch_projects.py, 1 dakikada bir tekrar eden TEK
# seferlik tarama — auto_process.py'nin saatlik görevindeki AYNI tetikleyici
# deseni. NOT: ilk tasarım "oturum açılışında başlayan sürekli süreç"
# (-AtLogOn tetikleyicisi) idi ama bu ortamda Register-ScheduledTask "Erişim
# engellendi" hatası verdi — Windows'un logon-tabanlı tetikleyicileri,
# arka planda/interaktif olmayan bir bağlamdan kaydedilirken bu izni
# isteyebiliyor; zaman-tabanlı tekrarlı tetikleyiciler (aşağıdaki gibi) bu
# kısıtlamaya takılmıyor. Detay: CLAUDE.md, watch_projects.py'nin başlığı.) ---
$watcherTaskName = "FamousMusicStudio-Watcher"

$watcherOld = Get-ScheduledTask | Where-Object {
    $action = $_.Actions | Select-Object -First 1
    $action -and $action.Arguments -and ($action.Arguments -match "watch_projects\.py")
}
foreach ($t in $watcherOld) {
    Write-Host "Eski izleyici görevi siliniyor: $($t.TaskName)"
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
}

$watcherAction = New-ScheduledTaskAction -Execute $pythonwExe -Argument "`"$wrapper`" watch_projects.py" -WorkingDirectory $repoRoot
$watcherTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
# Süre limiti 5 DAKİKA (eskiden 2 saat): watch_projects.py tek seferlik bir
# klasör TARAMASI, normalde saniyeler sürüyor. `MultipleInstances IgnoreNew` ile
# birlikte 2 saatlik limit şu anlama geliyordu: takılan TEK bir tarama, sonraki
# ~120 taramanın hiç başlamamasına yol açar — ve bu görev aynı zamanda kanalın
# TEK nabız gözcüsünü (auto_process.log 4 saattir güncellenmiyorsa telefona uyarı)
# barındırdığı için emniyet ağı da o süre boyunca sessizce kapanır. 5 dakika,
# takılan bir taramayı en fazla 5 tarama gecikmesine indiriyor.
# Pil bayrakları: gerekçe yukarıdaki AutoProcess ayarlarının başında — dizüstünde
# varsayılan ayar bu görevi de pilde hiç başlatmaz / başlamışsa öldürür.
$watcherSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $watcherTaskName -Action $watcherAction -Trigger $watcherTrigger `
    -Settings $watcherSettings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$watcherTaskName' görevi 1 dakikada bir çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\watch_projects.py"
Write-Host "  log    : $repoRoot\watch_projects.log"
Write-Host "  iz     : $repoRoot\gorev_izleri\watch_projects.log"
Write-Host ""
Write-Host "Kontrol için:  Get-ScheduledTask -TaskName '$watcherTaskName' | Get-ScheduledTaskInfo"
