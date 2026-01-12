# WSL-Dev-Kit Build Plan

## Overview
Create a unified, single-file Python tool (`wsl_dev_kit.py`) that:
- Detects Windows vs WSL environment
- Auto-orchestrates cross-environment setup
- Supports Chrome, Firefox, LibreWolf
- Embeds the test suite
- Zero external dependencies (stdlib only)
- Publishable to PyPI

---

## Stage 1: Core Infrastructure
**File:** `wsl_dev_kit.py` (skeleton + core detection)

Create the file with:
- [ ] Shebang, docstring, license header
- [ ] Agent guidance comments at top
- [ ] Imports (all stdlib)
- [ ] `Environment` enum (WINDOWS, WSL, LINUX, MACOS, UNKNOWN)
- [ ] `Browser` enum (CHROME, FIREFOX, LIBREWOLF)
- [ ] `detect_environment()` function
- [ ] `detect_wsl_host_ip()` function  
- [ ] `ColorPrinter` class for pretty output (no deps)
- [ ] Argument parser setup (argparse)
- [ ] `main()` entry point skeleton

**Deliverable:** Runnable script that detects environment and parses args.

**Test command:** `python wsl_dev_kit.py --help`

---

## Stage 2: Browser Detection & Launch ✅
**File:** `wsl_dev_kit.py` (add browser logic)

Add:
- [x] `BROWSER_PATHS` dict with default paths per OS/browser
- [x] `find_browser(browser: Browser)` function
- [x] `BrowserConfig` dataclass (path, debug_port, profile_dir, args)
- [x] `get_browser_args(browser: Browser)` - returns debug args per browser
- [x] `launch_browser(config: BrowserConfig)` function
- [x] `kill_browser(browser: Browser)` function
- [x] `cleanup_profile(profile_dir: str)` function

**Deliverable:** Can find and launch browsers with remote debugging.

**Test command:** `python wsl_dev_kit.py --browser chrome --detect-only`

**Status:** ✅ COMPLETE - All browsers (Chrome, Firefox) detect, launch, and cleanup successfully

---

## Stage 3: Windows Network Setup ✅
**File:** `wsl_dev_kit.py` (add Windows networking)

Add:
- [x] `is_admin()` function
- [x] `get_wsl_adapter_ip()` function
- [x] `setup_portproxy(wsl_ip: str, port: int)` function
- [x] `cleanup_portproxy(wsl_ip: str, port: int)` function
- [x] `verify_chrome_listening(port: int)` function
- [x] `WindowsOrchestrator` class tying it together

**Deliverable:** Full Windows-side setup working.

**Test command:** `python wsl_dev_kit.py` (run as admin on Windows)

**Status:** ✅ COMPLETE - Windows orchestration with admin check, WSL adapter detection, portproxy setup, and browser verification all working

---

## Stage 4: WSL Cross-Environment Orchestration ✅
**File:** `wsl_dev_kit.py` (add WSL orchestration)

Add:
- [x] `run_powershell_from_wsl(script: str)` function
- [x] `WSLOrchestrator` class that:
  - Detects Windows host IP
  - Invokes PowerShell to run Windows setup
  - Sets up local forwarding if needed
- [x] `verify_connection(host: str, port: int)` function

**Deliverable:** Running from WSL auto-triggers Windows setup.

**Test command:** `python wsl_dev_kit.py` (from WSL)

**Status:** ✅ COMPLETE - WSL orchestration with PowerShell invocation, connection verification, and automatic Windows setup

---

## Stage 5: Embedded Test Suite ✅
**File:** `wsl_dev_kit.py` (add test HTML)

Add:
- [x] `TEST_HTML` constant (compressed/base64 encoded)
- [x] `get_test_html()` function (decompresses)
- [x] `HTTPTestServer` class (stdlib http.server)
- [x] `serve_test_page(port: int)` function
- [x] `--serve` flag to serve test page
- [x] `--test` flag to open browser to test page

**Deliverable:** Can serve embedded test page.

**Test command:** `python wsl_dev_kit.py --serve --port 8080`

**Status:** ✅ COMPLETE - Embedded test suite implemented and verified

---

## Stage 6: Validation & Diagnostics ✅
**File:** `wsl_dev_kit.py` (add validation)

Add:
- [x] `DiagnosticResult` dataclass
- [x] `run_diagnostics()` function that checks:
  - Environment detection
  - Browser found
  - Browser launches
  - Debug port responding
  - Portproxy configured (Windows)
  - WSL can reach Windows (WSL)
- [x] `--diagnose` flag for full diagnostic report
- [x] `--validate` flag for quick pass/fail check

**Deliverable:** Comprehensive self-test capability.

**Test command:** `python wsl_dev_kit.py --diagnose`

**Status:** ✅ COMPLETE - Diagnostics and validation implemented and verified.

---

## Stage 7: PyPI Packaging ✅
**Files:** `pyproject.toml`, update `wsl_dev_kit.py`

Add:
- [x] `pyproject.toml` with:
  - Package metadata
  - Entry point: `wsl-dev = wsl_dev_kit:main`
  - Python >=3.8 requirement
  - No dependencies
- [x] Version string in `wsl_dev_kit.py`
- [x] `--version` flag

**Deliverable:** Installable via `pip install .`

**Test command:** `pip install -e . && wsl-dev --help`

**Status:** ✅ COMPLETE - pyproject.toml created, version added, installed and verified locally.

---

## Stage 8: Documentation & Cleanup ✅
**Files:** Update `README.md`, delete old files

- [x] Update README.md for new tool
- [x] Add usage examples
- [x] Add troubleshooting section
- [x] Delete `start-dev-host.ps1` (functionality merged)
- [x] Delete `debug-bridge.sh` (functionality merged)
- [x] Delete `agents.md` (guidance now in source)
- [x] Keep `interactivity-test.html` as reference (embedded copy in .py)

**Deliverable:** Clean repo with single-tool focus.

**Status:** ✅ COMPLETE - Documentation updated and obsolete files removed.

---

## Stage 9: Final Testing & Commit ✅
**Actions:**

- [x] Test on Windows (PowerShell)
- [x] Test on WSL (bash)
- [x] Test all three browsers
- [x] Test `--diagnose` output
- [x] Test PyPI local install
- [x] Commit all changes
- [x] Push branch
- [x] Tag as v2.0.0

**Test commands:**
```powershell
# Windows
python wsl_dev_kit.py --diagnose
python wsl_dev_kit.py --browser firefox
python wsl_dev_kit.py --serve --test
```

```bash
# WSL
python3 wsl_dev_kit.py --diagnose
python3 wsl_dev_kit.py --browser chrome
```

**Status:** ✅ COMPLETE - All tests passed, ready for release.

---

## File Size Estimates

| Component | Lines |
|-----------|-------|
| Header/imports/constants | ~50 |
| Environment detection | ~80 |
| Browser detection/launch | ~150 |
| Windows networking | ~120 |
| WSL orchestration | ~100 |
| Embedded HTML (compressed) | ~30 |
| HTTP server | ~60 |
| Diagnostics | ~100 |
| Arg parsing/main | ~80 |
| **Total** | **~770** |

This is manageable in chunks.

---

## How to Use This Plan

1. Start each stage by saying: **"Continue with Stage N of plan.md"**
2. I will implement that stage only
3. We test the deliverable
4. Move to next stage in fresh context

Current status: **Ready to start Stage 9**

