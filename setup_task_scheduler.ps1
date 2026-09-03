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
    [string]$DjFamousDayOfWeek = "Friday",
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
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "auto_process.py" -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$taskName' görevi saatte bir çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\auto_process.py"
Write-Host "  python : $pythonExe"
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
$djFamousAction = New-ScheduledTaskAction -Execute $pythonExe -Argument "dj_famous_process.py" -WorkingDirectory $repoRoot
$djFamousTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DjFamousDayOfWeek -At $djFamousAt -WeeksInterval 1
# 1 saate kadar sürebilecek set videoları render+3 platform yükleme için ana
# katalogdan (2 saat) çok daha uzun bir süre limiti (bkz. dj_sets/README.md).
$djFamousSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $djFamousTaskName -Action $djFamousAction -Trigger $djFamousTrigger `
    -Settings $djFamousSettings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$djFamousTaskName' görevi her $DjFamousDayOfWeek $DjFamousTime çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\dj_famous_process.py"
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

$watcherAction = New-ScheduledTaskAction -Execute $pythonExe -Argument "watch_projects.py" -WorkingDirectory $repoRoot
$watcherTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$watcherSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $watcherTaskName -Action $watcherAction -Trigger $watcherTrigger `
    -Settings $watcherSettings -Principal $principal -Force | Out-Null

Write-Host ""
Write-Host "Tamam: '$watcherTaskName' görevi 1 dakikada bir çalışacak şekilde kuruldu."
Write-Host "  script : $repoRoot\watch_projects.py"
Write-Host "  log    : $repoRoot\watch_projects.log"
Write-Host ""
Write-Host "Kontrol için:  Get-ScheduledTask -TaskName '$watcherTaskName' | Get-ScheduledTaskInfo"
