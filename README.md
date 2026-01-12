# WSL Development Sucks Dogs Balls

## But you still do it because REASONS

**The Chasm:** WSL2 is a Virtual Machine. 
* `localhost` in WSL is **not** `localhost` in Windows.
* Chrome ignores `--remote-debugging-address` on Windows and always binds to `127.0.0.1`.
* Your Agentic tools fail to connect, timeout, or get `Connection Refused`.

This repo provides the **nuclear option**: a bulletproof bridge using `netsh portproxy` to expose Chrome's debug port to WSL.

---

## Prerequisites

1. **WSL2** (obviously)
2. **Google Chrome** installed on Windows at `C:\Program Files\Google\Chrome\Application\chrome.exe`
3. **Administrator Rights** on Windows (for portproxy setup)
4. **PowerShell 7+** on Windows
5. **Python 3.x** on Windows (for the HTTP test server)
6. **VS Code** with the following extensions:
   - **Playwright MCP** (for browser automation)
   - **GitHub Copilot** or similar AI assistant

---

## Quick Start

### Windows (Run as Administrator)
```powershell
.\start-dev-host.ps1
```

Output:
```
--- [1/4] Detecting WSL Network ---
OK WSL Host IP: 172.21.208.1

--- [2/4] Nuking Chrome & Clearing Profile ---
OK Chrome killed, profile cleared

--- [3/4] Setting up PortProxy ---
OK PortProxy: 172.21.208.1:9222 -> 127.0.0.1:9222

--- [4/4] Launching Chrome ---
OK Chrome DevTools listening!

---------------------------------------------------
Windows: http://127.0.0.1:9222/json/version
WSL:     http://172.21.208.1:9222/json/version
---------------------------------------------------
```

### WSL
From WSL, connect to Chrome using the Windows host IP:
```bash
curl http://$(ip route show | grep default | awk '{print $3}'):9222/json/version
```

Or use `debug-bridge.sh` if you need localhost forwarding within WSL.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                        WINDOWS                               │
│                                                              │
│  Chrome ──► 127.0.0.1:9222 (always, can't change)           │
│                    │                                         │
│                    │ netsh portproxy                         │
│                    ▼                                         │
│           172.21.x.x:9222 (WSL-facing interface)            │
└────────────────────┼────────────────────────────────────────┘
                     │ vEthernet (WSL)
┌────────────────────┼────────────────────────────────────────┐
│                    ▼                            WSL          │
│  Your Agent ──► Windows Host IP:9222                        │
└─────────────────────────────────────────────────────────────┘
```

1. Chrome binds to `127.0.0.1:9222` (this is hardcoded behavior on Windows)
2. `netsh interface portproxy` exposes that on the WSL vEthernet interface
3. WSL tools connect to the Windows host IP (usually `172.21.x.x`)

---

## For AI Agents

See [agents.md](agents.md) for critical pitfalls and debugging guidance when modifying this project.

---

## Running the Interactivity Test Suite

The included `interactivity-test.html` provides a comprehensive battery of tests to verify browser automation is working correctly.

### For Humans: Manual Testing

1. **Start the debug bridge:**
   ```powershell
   # Run as Administrator
   .\start-dev-host.ps1
   ```

2. **Start the HTTP server** (in a separate terminal):
   ```powershell
   python -m http.server 8080
   ```

3. **Open in Chrome:**
   Navigate to `http://127.0.0.1:8080/interactivity-test.html`

4. **Click through tests manually** - the status panel in the top-right shows pass/fail counts.

### For Humans: Automated Testing via AI Agent

Ask your AI assistant (Copilot, Claude, etc.):

> "Navigate to http://127.0.0.1:8080/interactivity-test.html and run all the interactivity tests"

The agent will use Playwright MCP to:
- Click buttons (single, double, counter)
- Type in text fields
- Select dropdowns
- Check checkboxes and radio buttons
- Test keyboard events
- Hover over elements
- Drag and drop items
- Test async operations
- Verify localStorage
- Manipulate the DOM

### Test Coverage

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| Click Events | 3 | Single click, double click, counter state |
| Text Input | 1 | Input events, character counting |
| Form Elements | 4 | Select, checkboxes, radio buttons |
| Keyboard | 1 | Key events, key history tracking |
| Mouse | 1 | Hover, enter/leave events |
| Canvas | 1 | Drawing, mouse tracking |
| Drag & Drop | 1 | HTML5 drag and drop API |
| Async | 2 | Promises, fetch API |
| Storage | 3 | localStorage save/load/clear |
| DOM | 3 | Add/remove/toggle elements |

---

## Tips for Getting the Most Out of This Test Kit

### 🎯 For Debugging Connection Issues

1. **Always verify Chrome is listening first:**
   ```powershell
   curl.exe http://127.0.0.1:9222/json/version
   ```
   
2. **Check the portproxy is set up:**
   ```powershell
   netsh interface portproxy show all
   ```

3. **If things are broken, nuclear reset:**
   ```powershell
   netsh interface portproxy reset
   Stop-Process -Name chrome -Force
   Start-Sleep -Seconds 60  # Wait for TIME_WAIT to clear
   .\start-dev-host.ps1
   ```

### 🤖 For AI Agent Development

1. **Use the test suite as a smoke test** - If all 17+ tests pass, your browser automation setup is solid.

2. **Check console logs** - The test page logs every action with `[TEST]` prefix.

3. **Screenshot on failure** - Use `browser_take_screenshot` to capture visual state.

4. **The status panel never lies** - Top-right corner shows real-time pass/fail counts.

### ⚠️ Common Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Connection refused" | Chrome not running | Run `start-dev-host.ps1` |
| "file:// blocked" | No HTTP server | Run `python -m http.server 8080` |
| Tests hang | Chrome profile corrupted | Delete `C:\ChromeDevProfile` |
| Hundreds of TIME_WAIT | Portproxy loop | `netsh interface portproxy reset`, wait 60s |
| WSL can't connect | Firewall blocking | Run script as Administrator |

### 📊 Interpreting Results

- **17/17 passed** = Everything works, you're ready to automate
- **Some failures** = Check console logs for which test failed
- **All failures** = Usually a connection issue, not a test issue

---

## Files in This Repo

| File | Purpose |
|------|---------|
| `start-dev-host.ps1` | Windows script to launch Chrome with debug bridge |
| `debug-bridge.sh` | WSL script for localhost forwarding (optional) |
| `interactivity-test.html` | Comprehensive browser automation test suite |
| `agents.md` | Guidelines for AI agents working on this project |
| `README.md` | This file |