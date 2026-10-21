<# 
.SYNOPSIS
    Famous Music Studio - Chrome Remote Debugging Shortcut Creator
    Masaüstüne ve Başlangıç klasörüne kısayol oluşturur.
#>

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$debugPort = 9222
$userDataDir = "$env:LOCALAPPDATA\ChromeDebugProfile"
$scriptPath = "C:\Users\ACER\Desktop\ilk-projem\launch_chrome_debug_silent.vbs"

# Kullanici veri dizini olustur
if (-not (Test-Path $userDataDir)) {
    New-Item -ItemType Directory -Path $userDataDir -Force | Out-Null
}

# Kısayol oluşturma fonksiyonu
function Create-Shortcut {
    param(
        [string]$TargetPath,
        [string]$Arguments,
        [string]$ShortcutPath,
        [string]$Description,
        [string]$IconLocation,
        [bool]$RunMinimized = $true
    )
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    $shortcut.Description = $Description
    $shortcut.IconLocation = $IconLocation
    if ($RunMinimized) { $shortcut.WindowStyle = 7 } # 7 = Minimized
    $shortcut.Save()
    Write-Host "Kısayol oluşturuldu: $ShortcutPath"
}

# 1. Masaüstü kısayolu (Chrome'u debug modunda başlatan)
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Chrome Debug (Famous Music Studio).lnk"
Create-Shortcut `
    -TargetPath "wscript.exe" `
    -Arguments "`"$scriptPath`"" `
    -ShortcutPath $shortcutPath `
    -Description "Chrome'u MCP (chrome-devtools-mcp) için remote debugging port 9222 ile başlatır" `
    -IconLocation "$chromePath,0"

# 2. Başlangıç klasörüne kısayol (Windows açılışında otomatik başlasın)
$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupShortcut = Join-Path $startup "Chrome Debug (Famous Music Studio).lnk"
Create-Shortcut `
    -TargetPath "wscript.exe" `
    -Arguments "`"$scriptPath`"" `
    -ShortcutPath $startupShortcut `
    -Description "Windows açılışında Chrome'u MCP için debug modunda başlatır" `
    -IconLocation "$chromePath,0"

# 3. Görev Zamanlayıcısı ile de ekle (daha güvenilir) - Delay parametresi olmadan
$taskName = "FamousMusicStudio_ChromeDebug"
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force -Description "Chrome'u MCP (chrome-devtools-mcp) için remote debugging port 9222 ile başlatır"

Write-Host "`nTüm kısayollar ve görev oluşturuldu!" -ForegroundColor Green
Write-Host "Artık Windows açıldığında Chrome otomatik debug modunda başlayacak." -ForegroundColor Cyan
Write-Host "MCP (chrome-devtools-mcp) her zaman port 9222'ye bağlanabilecek." -ForegroundColor Cyan