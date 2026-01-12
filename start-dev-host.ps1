# ==========================================
# WSL-DEV-BRIDGE: Windows Host Initiator
# ==========================================
# 1. Enforces Firewall Rules
# 2. Kills all existing Chrome instances (Hard)
# 3. Launches Chrome in "Open Listening" Mode
# ==========================================

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$UserDataDir = "C:\ChromeDevProfile"
$Port = 9222
$DebugUrl = "http://localhost:$Port/json/version"

Write-Host "--- [1/3] Checking Firewall Rules ---" -ForegroundColor Cyan
$RuleName = "Chrome DevTools Bridge"

# Check if rule exists
$Rule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue

if ($null -eq $Rule) {
    Write-Host "Rule not found. Creating Firewall Rule for Port $Port..." -ForegroundColor Yellow
    # Requires Admin privileges to run this part
    try {
        New-NetFirewallRule -DisplayName $RuleName `
                            -Direction Inbound `
                            -LocalPort $Port `
                            -Protocol TCP `
                            -Action Allow `
                            -Profile Any
        Write-Host "✅ Firewall Rule Created." -ForegroundColor Green
    }
    catch {
        Write-Host "❌ FAILED to create Firewall Rule. Run this script as Administrator!" -ForegroundColor Red
        exit
    }
} else {
    Write-Host "✅ Firewall Rule exists." -ForegroundColor Green
}

Write-Host "`n--- [2/3] Nuking Chrome Zombies ---" -ForegroundColor Cyan
# Kill Chrome completely to ensure the new flags take effect
$ChromeProcs = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($ChromeProcs) {
    Write-Host "Killing $($ChromeProcs.Count) Chrome processes..." -ForegroundColor Yellow
    Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
    
    # Wait a beat for file handles to release
    Start-Sleep -Seconds 1
} else {
    Write-Host "No existing Chrome processes found." -ForegroundColor Gray
}

# Remove the SingletonLock to prevent "Profile in use" errors
if (Test-Path "$UserDataDir\SingletonLock") {
    Write-Host "Removing stale SingletonLock..." -ForegroundColor Gray
    Remove-Item "$UserDataDir\SingletonLock" -Force -ErrorAction SilentlyContinue
}

Write-Host "`n--- [3/3] Launching Chrome (Public Mode) ---" -ForegroundColor Cyan
$Args = @(
    "--remote-debugging-port=$Port",
    "--remote-debugging-address=0.0.0.0",   # The Key: Listen to WSL
    "--remote-allow-origins=*",             # The Key: Trust WSL
    "--user-data-dir=$UserDataDir",
    "--no-first-run",
    $DebugUrl                               # Open verification page immediately
)

try {
    # We use Start-Process to detach it from this terminal
    Start-Process -FilePath $ChromePath -ArgumentList $Args
    Write-Host "✅ Chrome Launched on 0.0.0.0:$Port" -ForegroundColor Green
    Write-Host "    You should see the JSON version info in the new window."
}
catch {
    Write-Host "❌ Failed to launch Chrome. Check path: $ChromePath" -ForegroundColor Red
}

Write-Host "`n---------------------------------------------------"
Write-Host "READY. Now run ./debug-bridge.sh inside WSL." -ForegroundColor Cyan
Write-Host "---------------------------------------------------"