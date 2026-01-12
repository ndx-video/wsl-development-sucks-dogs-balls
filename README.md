# WSL Development Sucks Dogs Balls (But This Fixes It)

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