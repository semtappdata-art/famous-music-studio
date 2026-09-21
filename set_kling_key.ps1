$key = Read-Host 'Kling API Key girin'
if ([string]::IsNullOrWhiteSpace($key)) {
    Write-Host 'Bos anahtar; kaydedilmedi' -ForegroundColor Red
    exit 1
}
[Environment]::SetEnvironmentVariable('KLING_API_KEY', $key.Trim(), 'User')
[Environment]::SetEnvironmentVariable('KLING_ACCESS_KEY', $null, 'User')
[Environment]::SetEnvironmentVariable('KLING_SECRET_KEY', $null, 'User')
if ([Environment]::GetEnvironmentVariable('KLING_API_KEY','User')) {
    Write-Host 'KAYDEDILDI' -ForegroundColor Green
} else {
    Write-Host 'KAYDEDILEMEDI' -ForegroundColor Red
}
