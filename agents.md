# Agent Guidelines for WSL-Dev-Bridge

## Critical Pitfalls

### 1. Chrome `--remote-debugging-address` Does Nothing on Windows

**Problem:** Chrome on Windows ignores `--remote-debugging-address=<ip>` and always binds to `127.0.0.1` regardless of what you specify.

**Wrong approach:**
```powershell
# This does NOT work - Chrome still binds to 127.0.0.1
"--remote-debugging-address=172.21.208.1"
"--remote-debugging-address=0.0.0.0"
```

**Correct approach:** Accept that Chrome binds to localhost and use `netsh interface portproxy` to expose it on the WSL interface.

---

### 2. PortProxy Direction Matters

**Problem:** Setting up portproxy backwards creates a connection storm that exhausts ephemeral ports.

**Wrong (creates infinite loop):**
```powershell
# Chrome on 127.0.0.1, proxy points 127.0.0.1 -> WSL IP (WRONG!)
netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=9222 connectaddress=172.21.208.1 connectport=9222
```

**Correct:**
```powershell
# Chrome on 127.0.0.1, proxy exposes WSL IP -> 127.0.0.1
netsh interface portproxy add v4tov4 listenaddress=$WslHostIP listenport=9222 connectaddress=127.0.0.1 connectport=9222
```

**Symptom of wrong direction:** `netstat -an | Select-String ":9222"` shows hundreds/thousands of TIME_WAIT connections.

**Recovery:** `netsh interface portproxy reset` then wait 60+ seconds for TIME_WAIT to clear.

---

### 3. WSL Adapter Name Varies by Windows Build

**Problem:** The adapter isn't always `vEthernet (WSL)`. Newer builds with Hyper-V firewall rename it.

**Wrong:**
```powershell
Get-NetIPAddress -InterfaceAlias "vEthernet (WSL)"  # May not exist
```

**Correct:**
```powershell
Get-NetIPAddress -InterfaceAlias "*WSL*" -AddressFamily IPv4  # Wildcard match
```

---

### 4. Chrome Profile Corruption

**Problem:** Repeatedly killing Chrome mid-startup corrupts the profile, causing hangs on next launch.

**Solution:** Always nuke the entire profile directory, not just `SingletonLock`:
```powershell
Remove-Item $UserDataDir -Recurse -Force -ErrorAction SilentlyContinue
```

---

### 5. Don't Open the Debug Endpoint as a Webpage

**Problem:** Launching Chrome with `http://127.0.0.1:9222/json/version` as the URL is pointless—that's the debug API endpoint, not a browseable page.

**Wrong:**
```powershell
Start-Process chrome.exe -ArgumentList "--remote-debugging-port=9222","http://127.0.0.1:9222/json/version"
```

**Correct:**
```powershell
Start-Process chrome.exe -ArgumentList "--remote-debugging-port=9222","about:blank"
```

---

### 6. Firewall Rules Need Admin

**Problem:** `New-NetFirewallRule` and `Set-NetFirewallRule` fail silently or with "Access Denied" if not elevated.

**Solution:** Script must be run as Administrator for first-time setup. Check with:
```powershell
([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

---

### 7. CORS is Not the Issue

**Problem:** When debugging localhost-to-localhost connection failures, CORS is a red herring. CORS only applies to browser-initiated cross-origin requests, not direct HTTP calls.

**Actual causes:**
- Chrome not listening (wrong address binding)
- Firewall blocking
- PortProxy misconfigured
- Chrome not fully initialized yet

---

## Debugging Checklist

1. **Is Chrome actually listening?**
   ```powershell
   netstat -an | Select-String ":9222"
   ```
   Should show `LISTENING` on `127.0.0.1:9222`

2. **Is the portproxy configured?**
   ```powershell
   netsh interface portproxy show all
   ```
   Should show WSL IP -> 127.0.0.1 mapping

3. **Can you hit Chrome directly?**
   ```powershell
   curl.exe -s http://127.0.0.1:9222/json/version
   ```
   Should return JSON with `Browser` field

4. **Can you hit via WSL IP?**
   ```powershell
   curl.exe -s http://<WSL-IP>:9222/json/version
   ```
   Should return same JSON

5. **Are there connection storms?**
   ```powershell
   (netstat -an | Select-String ":9222" | Measure-Object).Count
   ```
   More than ~10 connections = something is looping

---

## Running the Interactivity Test Suite

The test suite (`interactivity-test.html`) validates browser automation capabilities. Here's how agents should invoke it:

### Step 1: Launch Chrome with Debug Bridge

```powershell
# Run from the project directory (requires Administrator)
.\start-dev-host.ps1
```

Wait for `OK Chrome DevTools listening!` before proceeding.

### Step 2: Start the HTTP Server

The test file must be served via HTTP (file:// URLs are blocked by Playwright):

```powershell
python -m http.server 8080
```

Run this as a **background process** so it doesn't block subsequent commands.

### Step 3: Navigate to the Test Page

Use Playwright MCP to navigate:
```
mcp_playwright_browser_navigate → http://127.0.0.1:8080/interactivity-test.html
```

### Step 4: Run Test Battery

Execute tests in this order for comprehensive coverage:

| Test | Tool | Target Ref | Notes |
|------|------|------------|-------|
| Single Click | `browser_click` | `btn-single` | Basic click event |
| Double Click | `browser_click` (doubleClick=true) | `btn-double` | Double-click event |
| Counter | `browser_click` | `btn-counter` | State mutation |
| Text Input | `browser_type` | `text-input` | Fill with any text |
| Select | `browser_select_option` | `select-input` | Choose "Option 2" |
| Checkbox | `browser_click` | `check1`, `check2` | Toggle checkboxes |
| Radio | `browser_click` | Radio A/B/C | Radio button selection |
| Keyboard | `browser_type` (slowly=true) | `keyboard-input` | Key-by-key typing |
| Mouse | `browser_hover` | `mouse-area` | Hover events |
| Async | `browser_click` | `btn-async` | 1-second async operation |
| Storage | `browser_type` + `browser_click` | Key/Value inputs + Save/Load | localStorage test |
| DOM Add | `browser_click` | `btn-add` | Dynamic element creation |
| DOM Toggle | `browser_click` | `btn-toggle` | Visibility toggle |
| DOM Remove | `browser_click` | `btn-remove` | Element removal |
| Drag & Drop | `browser_drag` | `draggable1` → `drop-zone` | Drag and drop |

### Step 5: Verify Results

Check the status panel (top-right) or console logs:
```
mcp_playwright_browser_console_messages → level: "info"
```

All tests should show `[TEST] <name>: PASS` in console output.

### Common Agent Mistakes

1. **Forgetting the HTTP server** - `file://` URLs are blocked
2. **Not waiting for Chrome** - Run `curl http://127.0.0.1:9222/json/version` to verify
3. **Using wrong refs** - Always get fresh snapshot after navigation
4. **Running tests in parallel** - Run sequentially to avoid race conditions
5. **Skipping the screenshot** - Use `browser_take_screenshot` for visual verification

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                        WINDOWS                               │
│                                                              │
│  Chrome ──► 127.0.0.1:9222 (always, can't change)           │
│                    │                                         │
│                    │ netsh portproxy                         │
│                    ▼                                         │
│           172.21.208.1:9222 (WSL-facing interface)          │
│                    │                                         │
└────────────────────┼────────────────────────────────────────┘
                     │ vEthernet (WSL)
┌────────────────────┼────────────────────────────────────────┐
│                    ▼                            WSL          │
│                                                              │
│  Agent/Tool ──► 172.21.208.1:9222 (Windows host IP)         │
│       or                                                     │
│  socat ──► localhost:9222 ──► 172.21.208.1:9222             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
