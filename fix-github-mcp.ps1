# GitHub MCP Server Fix - Windows PowerShell (Admin olarak calistir)

Write-Host "=== GitHub Copilot CLI MCP Fix ===" -ForegroundColor Cyan

# 1. Docker varsa yerel MCP server baslat
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Docker bulundu. Yerel github-mcp-server baslatiliyor..." -ForegroundColor Green

    # GITHUB_TOKEN: once .env'den oku, yoksa gh cli'dan al, yoksa sor
    $token = $env:GITHUB_TOKEN
    if (-not $token) {
        $envPath = "C:\Users\ACER\Desktop\ilk-projem\.env"
        if (Test-Path $envPath) {
            $envContent = Get-Content $envPath -Raw
            if ($envContent -match 'GITHUB_TOKEN=([^\r\n]+)') {
                $token = $matches[1].Trim()
                Write-Host "OK Token .env'den alindi" -ForegroundColor Green
            }
        }
    }
    if (-not $token) {
        $ghToken = gh auth token 2>$null
        if ($ghToken) {
            $token = $ghToken.Trim()
            Write-Host "OK Token 'gh auth token' ile alindi" -ForegroundColor Green
        }
    }
    if (-not $token) {
        $token = Read-Host "GitHub Personal Access Token (classic, repo scope) girin"
    }

    # Token'i ortam degiskenine de yaz (docker args icin)
    $env:GITHUB_TOKEN = $token

    # Once test et (interactive) - calisirsa arka plana al
    Write-Host "Test ediliyor (interactive)..." -ForegroundColor Cyan
    $testResult = docker run --rm -e GITHUB_TOKEN=$token ghcr.io/github/github-mcp-server --help 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Image calisiyor. Arka planda baslatiliyor..." -ForegroundColor Green
        $container = docker run -d --rm `
            -e GITHUB_TOKEN=$token `
            --name github-mcp-local `
            ghcr.io/github/github-mcp-server 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK Container baslatildi: $container" -ForegroundColor Green
            Write-Host "OK MCP endpoint: stdio (docker container)" -ForegroundColor Cyan
        } else {
            Write-Host "HATA Arka plan baslatilamadi. Manuel calistirin:" -ForegroundColor Red
            Write-Host "  docker run -i --rm -e GITHUB_TOKEN=$token ghcr.io/github/github-mcp-server" -ForegroundColor Yellow
        }
    } else {
        Write-Host "HATA Image calismadi. Cikti:" -ForegroundColor Red
        Write-Host $testResult -ForegroundColor Red
        Write-Host "Manuel deneyin:" -ForegroundColor Yellow
        Write-Host "  docker run -i --rm -e GITHUB_TOKEN=$token ghcr.io/github/github-mcp-server" -ForegroundColor Yellow
    }
} else {
    Write-Host "Docker yok. Copilot CLI downgrade onerisi:" -ForegroundColor Yellow
    Write-Host "  winget install --id GitHub.CopilotCLI --version 1.0.50 --force" -ForegroundColor Cyan
    Write-Host "  VEYA https://github.com/github/copilot-cli/releases/tag/v1.0.50 indirin" -ForegroundColor Cyan
}

# 2. Copilot CLI MCP ayarini guncelle (settings.json) - klasor yoksa olustur
$settingsDir = "$env:APPDATA\github-copilot-cli"
$settingsPath = "$settingsDir\settings.json"

if (-not (Test-Path $settingsDir)) {
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    Write-Host "OK Klasor olusturuldu: $settingsDir" -ForegroundColor Green
}

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath | ConvertFrom-Json
} else {
    $settings = @{} | ConvertTo-Json | ConvertFrom-Json
    Write-Host "OK Yeni settings.json olusturuluyor" -ForegroundColor Cyan
}

$settings.mcpServers = @{
    "github-mcp-server" = @{
        type = "stdio"
        command = "docker"
        args = @("run", "-i", "--rm", "-e", "GITHUB_TOKEN=$token", "ghcr.io/github/github-mcp-server")
    }
}

$settings | ConvertTo-Json -Depth 5 | Set-Content $settingsPath -Encoding UTF8
Write-Host "OK settings.json guncellendi: $settingsPath" -ForegroundColor Green

Write-Host "`nYapilacaklar:" -ForegroundColor Cyan
Write-Host "1. Copilot CLI'yi yeniden baslatin" -ForegroundColor White
Write-Host "2. /mcp show github-mcp-server -> 'Status: OK Connected' olmali" -ForegroundColor White
Write-Host "3. Sorun devam ederse: copilot login tekrar yapin" -ForegroundColor White

Read-Host "Kapatmak icin Enter"