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
2. **Google Chrome** installed on Windows
3. **Administrator Rights** on Windows (for portproxy setup)
4. **PowerShell 7+** on Windows

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