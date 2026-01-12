# WSL Dev Kit

**The nuclear option for WSL2 browser automation.**

WSL2 is a Virtual Machine. `localhost` in WSL is **not** `localhost` in Windows. Chrome ignores `--remote-debugging-address` on Windows and always binds to `127.0.0.1`.

**WSL Dev Kit** (`wsl-dev`) bridges this chasm. It is a single-file, zero-dependency Python tool that orchestrates the connection between your WSL environment and Windows browsers.

## Features

- **Unified Tool**: One command works on both Windows and WSL.
- **Auto-Orchestration**:
    - **From WSL**: Detects Windows host, invokes PowerShell via interop to set up the bridge, and validates connectivity.
    - **On Windows**: Admin check, `netsh portproxy` setup, firewall handling, and browser launching.
- **Browser Support**: Chrome (default), Firefox, and LibreWolf.
- **Embedded Test Suite**: Includes a full interactivity test page to verify automation.
- **Zero Dependencies**: Uses standard library only.
- **Diagnostics**: Built-in self-test and validation.

## Installation

Requires **Python 3.8+** on Windows and WSL.

```bash
git clone https://github.com/yourusername/wsl-development-sucks-dogs-balls.git
cd wsl-development-sucks-dogs-balls
pip install -e .
```

*Note: You must install this on **both** Windows and WSL if you want to run it natively in each environment, though the WSL version can trigger the Windows side automatically.*

## Usage

### 🚀 Standard Usage (From WSL)

Just run the tool. It will detect it's in WSL, find the Windows host, and set everything up.

```bash
wsl-dev
```

**What happens:**
1. Detects Windows Host IP.
2. Invokes itself on Windows (via `powershell.exe`) to kill old browser instances and set up `portproxy`.
3. Launches Chrome on Windows with remote debugging enabled.
4. Verifies the connection from WSL.

### 🪟 Windows Usage

Run as **Administrator** (required for `netsh` commands).

```powershell
wsl-dev
```

### 🌐 Options

| Flag | Description |
|------|-------------|
| `--browser <name>` | Select browser: `chrome` (default), `firefox`, `librewolf`. |
| `--diagnose` | Run a comprehensive self-test and report issues. |
| `--validate` | Quick pass/fail check for connectivity. |
| `--serve` | Serve the embedded test page on port 8000. |
| `--test` | Open the test page in the browser automatically. |
| `--port <N>` | Specify custom debug port (default: 9222). |

### Examples

**Launch Firefox instead of Chrome:**
```bash
wsl-dev --browser firefox
```

**Run diagnostics:**
```bash
wsl-dev --diagnose
```

**Serve the test suite and open it:**
```bash
wsl-dev --serve --test
```

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

## Troubleshooting

### "Connection Refused"
- **Cause**: Chrome isn't running or `portproxy` failed.
- **Fix**: Run `wsl-dev --diagnose` to see which step failed. Ensure you have Admin rights on Windows.

### "Portproxy creation failed"
- **Cause**: Missing Admin rights on Windows.
- **Fix**: Run PowerShell as Administrator. If running from WSL, the tool attempts to elevate, but UAC might block it.

### Browser Profile Issues
- **Cause**: Corrupted profile from previous sessions.
- **Fix**: The tool attempts to clear `C:\ChromeDevProfile` (or similar) on launch. Manually delete this folder if issues persist.

### "Command not found"
- **Cause**: `pip` install location not in PATH.
- **Fix**: Add your Python scripts directory to PATH, or run via `python -m wsl_dev_kit`.

## License

MIT
