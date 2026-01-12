# ==========================================
# WSL-DEV-BRIDGE: Secure Host Initiator
# ==========================================
# 1. Detects the specific vEthernet (WSL) IP
# 2. Creates a scoped Firewall Rule (WSL Subnet Only)
# 3. Launches Chrome bound ONLY to the WSL Interface
# ==========================================

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$UserDataDir = "C:\ChromeDevProfile"
$Port = 9222
$AdapterName = "vEthernet (WSL)"

Write-Host "--- [1/4] Detecting WSL Network ---" -ForegroundColor Cyan

# Find the WSL Adapter IP on the Host
try {
    $WslAdapter = Get-NetIPAddress -InterfaceAlias $AdapterName -AddressFamily IPv4 -ErrorAction Stop
    $HostIP = $WslAdapter.IPAddress
    # Calculate the subnet (simple approximation based on prefix, usually /20)
    # For firewall safety, we allows the whole class B or the specific prefix. 
    # To be safe and simple, we allow the /16 range which covers WSL's dynamic allocation.
    $FirewallScope = "$($HostIP.Split('.')[0]).$($HostIP.Split('.')[1]).0.0/16"
    
    Write-Host "✅ Detected WSL Host IP: $HostIP" -ForegroundColor Green
    Write-Host "🔒 Firewall Scope: $FirewallScope (WSL Traffic Only)" -ForegroundColor Gray
}
catch {
    Write-Host "❌ CRITICAL: Could not find network adapter '$AdapterName'." -ForegroundColor Red
    Write-Host "   Is WSL2 running? Run 'wsl' in another window to wake it up."
    exit
}

Write-Host "`n--- [2/4] Enforcing Scoped Firewall Rules ---" -ForegroundColor Cyan
$RuleName = "Chrome DevTools Bridge (WSL Secure)"

# Remove old "Lazy" rules if they exist
Remove-NetFirewallRule -DisplayName "Chrome DevTools Bridge" -ErrorAction SilentlyContinue

# Check/Update Secure Rule
$Rule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue

if ($null -eq $Rule) {
    Write-Host "Creating Secure Firewall Rule..." -ForegroundColor Yellow
    try {
        # This rule allows traffic on Port 9222 ONLY from the WSL Subnet
        New-NetFirewallRule -DisplayName $RuleName `
                            -Direction Inbound `
                            -LocalPort $Port `
                            -Protocol TCP `
                            -Action Allow `
                            -Profile Any `
                            -RemoteAddress $FirewallScope
        Write-Host "✅ Secure Firewall Rule Created." -ForegroundColor Green
    }
    catch {
        Write-Host "❌ FAILED. Run as Administrator!" -ForegroundColor Red
        exit
    }
} else {
    # Optional: Update the scope if the WSL IP changed (it changes on reboot!)
    Set-NetFirewallRule -DisplayName $RuleName -RemoteAddress $FirewallScope
    Write-Host "✅ Firewall Rule Updated for new IP." -ForegroundColor Green
}

Write-Host "`n--- [3/4] Nuking Chrome Zombies ---" -ForegroundColor Cyan
$ChromeProcs = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($ChromeProcs) {
    Write-Host "Killing $($ChromeProcs.Count) Chrome processes..." -ForegroundColor Yellow
    Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

if (Test-Path "$UserDataDir\SingletonLock") {
    Remove-Item "$UserDataDir\SingletonLock" -Force -ErrorAction SilentlyContinue
}

Write-Host "`n--- [4/4] Launching Chrome (Secure Mode) ---" -ForegroundColor Cyan
$Args = @(
    "--remote-debugging-port=$Port",
    "--remote-debugging-address=$HostIP",   # Binds ONLY to the WSL Interface
    "--remote-allow-origins=*",             # Still needed for tool headers, but network is locked
    "--user-data-dir=$UserDataDir",
    "--no-first-run",
    "http://$($HostIP):$Port/json/version"
)

try {
    Start-Process -FilePath $ChromePath -ArgumentList $Args
    Write-Host "✅ Chrome Launched on $HostIP:$Port" -ForegroundColor Green
    Write-Host "    (Invisible to Public LAN, Visible to WSL)"
}
catch {
    Write-Host "❌ Failed to launch Chrome." -ForegroundColor Red
}

Write-Host "`n---------------------------------------------------"
Write-Host "READY. Run ./debug-bridge.sh in WSL." -ForegroundColor Cyan
Write-Host "NOTE: Your bridge script must target: $HostIP" -ForegroundColor Yellow
Write-Host "---------------------------------------------------"