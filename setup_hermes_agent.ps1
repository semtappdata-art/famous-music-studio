<#
Hermes Agent (Nous Research) kurulum scripti — Famous Music Studio için.

Ne yapar:
  1. Resmi Windows installer'ını (install.ps1, GitHub main) çalıştırır:
     %LOCALAPPDATA%\hermes altına uv + Python 3.11 + Node + PortableGit + Hermes.
     Admin gerekmez. Sonunda `hermes setup` sihirbazı açılır (model/sağlayıcı seçimi).
  2. Bu repoyu Hermes'e "güvenilir proje" olarak tanıtır (`hermes skills trust`) —
     böylece .hermes/skills/famous-music-studio proje skill'i ve CLAUDE.md bağlamı
     bu klasörde açılan her Hermes oturumunda otomatik yüklenir.
  3. `hermes doctor` ile kurulumu doğrular.

Kullanım (PowerShell, repo kökünde):
  .\setup_hermes_agent.ps1                # tam kurulum + sihirbaz
  .\setup_hermes_agent.ps1 -SkipSetup     # sihirbazı atla (sonra: hermes setup)
  .\setup_hermes_agent.ps1 -TrustOnly     # Hermes zaten kurulu, sadece repoyu tanıt

Not: Bu dosya UTF-8 BOM'LU kaydedilmeli (Windows PowerShell 5.1, Türkçe karakter).
Detay: hermes_agent_kurulum.md
#>
param(
    [switch]$SkipSetup,
    [switch]$TrustOnly,
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallerUrl = "https://raw.githubusercontent.com/NousResearch/hermes-agent/$Branch/scripts/install.ps1"
$HermesBin = Join-Path $env:LOCALAPPDATA "hermes\bin"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

if (-not $TrustOnly) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "UYARI: git PATH'te yok. Installer kendi PortableGit'ini indirecek." -ForegroundColor Yellow
    }

    Write-Step "Resmi Hermes installer'ı indiriliyor: $InstallerUrl"
    $script = Invoke-RestMethod -Uri $InstallerUrl
    $block = [scriptblock]::Create($script)

    Write-Step "Hermes Agent kuruluyor (%LOCALAPPDATA%\hermes) — birkaç dakika sürebilir"
    if ($SkipSetup) {
        & $block -SkipSetup -Branch $Branch
    } else {
        & $block -Branch $Branch
    }
}

# Installer PATH'i sadece User env'e yazar; bu oturumda da görünsün.
if (Test-Path $HermesBin) {
    if (-not ($env:PATH -split ";" | Where-Object { $_ -eq $HermesBin })) {
        $env:PATH = "$HermesBin;$env:PATH"
    }
}
if (-not $env:HERMES_HOME) { $env:HERMES_HOME = Join-Path $env:LOCALAPPDATA "hermes" }

if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    Write-Host "HATA: 'hermes' komutu bulunamadı. Yeni bir terminal açıp tekrar deneyin:" -ForegroundColor Red
    Write-Host "      .\setup_hermes_agent.ps1 -TrustOnly"
    exit 1
}

Write-Step "Repo Hermes'e güvenilir proje olarak tanıtılıyor: $RepoRoot"
Push-Location $RepoRoot
try {
    hermes skills trust $RepoRoot
} finally {
    Pop-Location
}

Write-Step "Kurulum doğrulanıyor (hermes doctor)"
hermes doctor

Write-Host ""
Write-Host "Tamam. Sonraki adımlar:" -ForegroundColor Green
Write-Host "  - Yeni bir terminal aç (PATH güncellemesi için)."
Write-Host "  - Model/sağlayıcı seçilmediyse:  hermes model"
Write-Host "  - Repo kökünde sohbet:           cd `"$RepoRoot`"; hermes"
Write-Host "  - Proje skill'i:                 /famous-music-studio"
Write-Host "  - Detay: hermes_agent_kurulum.md"
