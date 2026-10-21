@echo off
:: Famous Music Studio - Chrome Remote Debugging Launcher
:: Bu script Chrome'u remote debugging port 9222 ile başlatır
:: MCP (chrome-devtools-mcp) bu port üzerinden bağlanır

set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
set DEBUG_PORT=9222
set USER_DATA_DIR=%LOCALAPPDATA%\ChromeDebugProfile

:: Kullanıcı verisi dizini yoksa oluştur
if not exist "%USER_DATA_DIR%" mkdir "%USER_DATA_DIR%"

:: Chrome zaten açık mı kontrol et (debug portunda)
netstat -an | findstr :%DEBUG_PORT% >nul
if %errorlevel% equ 0 (
    echo Chrome zaten debug portunda calisiyor (port %DEBUG_PORT%).
    echo MCP baglanabilir.
    exit /b 0
)

echo Chrome debug modunda baslatiliyor...
start "" %CHROME_PATH% ^
    --remote-debugging-port=%DEBUG_PORT% ^
    --user-data-dir="%USER_DATA_DIR%" ^
    --no-first-run ^
    --no-default-browser-check ^
    --disable-background-timer-throttling ^
    --disable-backgrounding-occluded-windows ^
    --disable-renderer-backgrounding

echo.
echo Chrome baslatildi. MCP artik port %DEBUG_PORT% uzerinden baglanabilir.
echo Bu pencereyi kapatabilirsiniz.
timeout /t 3 /nobreak >nul