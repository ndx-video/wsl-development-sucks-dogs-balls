# WSL Development Sucks Dogs Balls (But This Fixes It)

## The Problem
You are a modern developer. You run your heavy tools (Claude Code, Antigravity, MCP Servers) in **WSL2** because it's superior. You run your browser (Chrome) in **Windows** because Linux GUI apps are janky.

**The Chasm:** WSL2 is a Virtual Machine. 
* `localhost` in WSL is **not** `localhost` in Windows.
* Chrome, by default, is paranoid and blocks all "external" connections (including WSL).
* Your Agentic tools fail to connect, timeout, or get `Connection Refused`.

This repo provides the **nuclear option**: a bulletproof, hard-coded TCP bridge that forces Chrome to listen and forces WSL to talk to it.

---

## Prerequisites

1.  **WSL2** (obviously).
2.  **Google Chrome** installed on Windows.
3.  **socat** installed in WSL (`sudo apt install socat -y`).
4.  **Administrator Rights** on Windows (only needed once for the Firewall rule).

---

## The Solution

We use a "Pincer Movement":
1.  **Windows Side (`start-dev-host.ps1`):** Nukes all "zombie" Chrome processes, opens the Firewall, and launches a fresh Chrome instance listening on `0.0.0.0` (Public Mode).
2.  **WSL Side (`debug-bridge.sh`):** Hunts down the Windows IP, kills any stale tunnels, and creates a `socat` pipe from `WSL:localhost:9222` -> `Windows:9222`.

---

## File 1: Windows Host Script
Save this as `start-dev-host.ps1` in your repo.

```powershell
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