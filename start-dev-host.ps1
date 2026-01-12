# ==========================================
# WSL-DEV-BRIDGE: Secure Host Initiator
# ==========================================

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$UserDataDir = "C:\ChromeDevProfile"
$Port = 9222

Write-Host "--- [1/4] Detecting WSL Network ---" -ForegroundColor Cyan
$WslAdapter = Get-NetIPAddress -InterfaceAlias "*WSL*" -AddressFamily IPv4 -ErrorAction SilentlyContinue
if (-not $WslAdapter) {
    Write-Host "X CRITICAL: No WSL adapter found. Is WSL running?" -ForegroundColor Red
    exit 1
}
$WslHostIP = $WslAdapter.IPAddress
Write-Host "OK WSL Host IP: $WslHostIP" -ForegroundColor Green

Write-Host "`n--- [2/4] Nuking Chrome & Clearing Profile ---" -ForegroundColor Cyan
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Remove-Item $UserDataDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "OK Chrome killed, profile cleared" -ForegroundColor Green

Write-Host "`n--- [3/4] Setting up PortProxy ---" -ForegroundColor Cyan
netsh interface portproxy delete v4tov4 listenaddress=$WslHostIP listenport=$Port 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenaddress=$WslHostIP listenport=$Port connectaddress=127.0.0.1 connectport=$Port | Out-Null
Write-Host "OK PortProxy: ${WslHostIP}:${Port} -> 127.0.0.1:${Port}" -ForegroundColor Green

Write-Host "`n--- [4/4] Launching Chrome ---" -ForegroundColor Cyan
Start-Process $ChromePath -ArgumentList "--remote-debugging-port=$Port","--user-data-dir=$UserDataDir","--no-first-run","about:blank"
Start-Sleep -Seconds 3

$test = curl.exe -s "http://127.0.0.1:$Port/json/version" 2>$null
if ($test -match "Browser") {
    Write-Host "OK Chrome DevTools listening!" -ForegroundColor Green
} else {
    Write-Host "X Chrome not responding" -ForegroundColor Red
}

Write-Host "`n---------------------------------------------------"
Write-Host "Windows: http://127.0.0.1:${Port}/json/version" -ForegroundColor Yellow
Write-Host "WSL:     http://${WslHostIP}:${Port}/json/version" -ForegroundColor Yellow
Write-Host "---------------------------------------------------"
