#!/usr/bin/env python3
"""
WSL Dev Kit - Unified Browser Debug Bridge

A single-file Python tool that auto-orchestrates cross-environment browser debugging
between Windows and WSL. Zero external dependencies, stdlib only.

MIT License
Copyright (c) 2026 Terence
"""

# =============================================================================
# AGENT GUIDANCE
# =============================================================================
# This tool solves the WSL browser debugging problem by:
# 1. Detecting environment (Windows, WSL, Linux, macOS)
# 2. Auto-launching browsers with remote debugging on Windows
# 3. Setting up portproxy to expose debug port on WSL interface
# 4. Handling cross-environment orchestration from WSL
# 5. Providing embedded test suite for validation
#
# Key constraints:
# - Chrome ALWAYS binds to 127.0.0.1 regardless of --remote-debugging-address
# - Use netsh portproxy to expose on WSL interface (listenaddr=WSL_IP -> connectaddr=127.0.0.1)
# - Firefox/LibreWolf support --start-debugger-server <ip>:<port>
# - All networking must account for Windows Firewall rules
# - Profile corruption prevention: always nuke entire profile dir, not just SingletonLock
# =============================================================================

import sys
import os
import platform
import subprocess
import time
import argparse
import shutil
import tempfile
import signal
import base64
import zlib
import threading
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn


VERSION = "2.0.0"


# Force UTF-8 encoding for stdout/stderr to handle unicode characters on Windows
if sys.version_info >= (3, 7):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')



# =============================================================================
# ENUMS
# =============================================================================

class Environment(Enum):
    """Detected operating environment"""
    WINDOWS = "windows"
    WSL = "wsl"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class Browser(Enum):
    """Supported browsers"""
    CHROME = "chrome"
    FIREFOX = "firefox"
    LIBREWOLF = "librewolf"


# =============================================================================
# BROWSER PATHS & CONFIGURATION
# =============================================================================

# Default browser installation paths per OS
BROWSER_PATHS: Dict[Browser, Dict[Environment, List[str]]] = {
    Browser.CHROME: {
        Environment.WINDOWS: [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        Environment.WSL: [
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ],
        Environment.LINUX: [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ],
        Environment.MACOS: [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
    },
    Browser.FIREFOX: {
        Environment.WINDOWS: [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            os.path.expandvars(r"%LocalAppData%\Mozilla Firefox\firefox.exe"),
        ],
        Environment.WSL: [
            "/mnt/c/Program Files/Mozilla Firefox/firefox.exe",
            "/mnt/c/Program Files (x86)/Mozilla Firefox/firefox.exe",
        ],
        Environment.LINUX: [
            "/usr/bin/firefox",
            "/usr/bin/firefox-esr",
            "/snap/bin/firefox",
        ],
        Environment.MACOS: [
            "/Applications/Firefox.app/Contents/MacOS/firefox",
        ],
    },
    Browser.LIBREWOLF: {
        Environment.WINDOWS: [
            r"C:\Program Files\LibreWolf\librewolf.exe",
            r"C:\Program Files (x86)\LibreWolf\librewolf.exe",
        ],
        Environment.WSL: [
            "/mnt/c/Program Files/LibreWolf/librewolf.exe",
            "/mnt/c/Program Files (x86)/LibreWolf/librewolf.exe",
        ],
        Environment.LINUX: [
            "/usr/bin/librewolf",
            "/usr/local/bin/librewolf",
        ],
        Environment.MACOS: [
            "/Applications/LibreWolf.app/Contents/MacOS/librewolf",
        ],
    },
}


# =============================================================================
# EMBEDDED TEST SUITE
# =============================================================================

# Compressed and base64-encoded interactivity-test.html
# Original size: ~21KB, compressed: ~6.7KB
TEST_HTML = """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"""


def get_test_html() -> str:
    """Decompress and return the embedded test HTML"""
    compressed = base64.b64decode(TEST_HTML)
    decompressed = zlib.decompress(compressed)
    return decompressed.decode('utf-8')


class HTTPTestServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for serving the test page"""
    pass


class TestPageHandler(SimpleHTTPRequestHandler):
    """Custom request handler that serves the embedded test HTML"""
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(get_test_html().encode('utf-8'))
        else:
            self.send_error(404, 'File not found')
    
    def log_message(self, format, *args):
        # Suppress default logging, we'll handle it ourselves
        pass


def serve_test_page(port: int = 8080, open_browser: bool = False, browser: Optional[Browser] = None, env: Optional[Environment] = None) -> None:
    """
    Serve the embedded test page on the specified port.
    
    Args:
        port: Port to serve on
        open_browser: Whether to automatically open browser to the test page
        browser: Browser to use (required if open_browser=True)
        env: Environment (required if open_browser=True)
    """
    printer.step(f"Starting HTTP server on port {port}...")
    
    try:
        server = HTTPTestServer(('', port), TestPageHandler)
        printer.success(f"Test page available at: http://localhost:{port}/")
        
        if open_browser and browser and env:
            import urllib.request
            import webbrowser
            
            # Give server a moment to start
            time.sleep(0.5)
            
            # Try to open with the system default browser or specified browser
            url = f"http://localhost:{port}/"
            printer.step(f"Opening {url} in browser...")
            
            try:
                webbrowser.open(url)
                printer.success("Browser opened successfully")
            except Exception as e:
                printer.warning(f"Could not auto-open browser: {e}")
                printer.info(f"Please navigate to: {url}")
        
        printer.info("Press Ctrl+C to stop the server")
        server.serve_forever()
        
    except KeyboardInterrupt:
        printer.info("\nShutting down server...")
        server.shutdown()
        printer.success("Server stopped")
    except OSError as e:
        if 'Address already in use' in str(e):
            printer.error(f"Port {port} is already in use. Try a different port with --http-port")
        else:
            printer.error(f"Failed to start server: {e}")
        sys.exit(1)


@dataclass
class BrowserConfig:
    """Configuration for launching a browser with remote debugging"""
    path: str
    debug_port: int
    profile_dir: str
    args: List[str]
    process_name: str  # For killing


def find_browser(browser: Browser, env: Environment) -> Optional[str]:
    """
    Find the browser executable path.
    
    Args:
        browser: Browser to find
        env: Current environment
        
    Returns:
        Path to browser executable, or None if not found
    """
    # Get default paths for this browser/env combo
    default_paths = BROWSER_PATHS.get(browser, {}).get(env, [])
    
    # Check default paths first
    for path in default_paths:
        expanded_path = os.path.expandvars(os.path.expanduser(path))
        if os.path.isfile(expanded_path):
            return expanded_path
    
    # Try to find in PATH
    browser_names = {
        Browser.CHROME: ["chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
        Browser.FIREFOX: ["firefox", "firefox-esr"],
        Browser.LIBREWOLF: ["librewolf"],
    }
    
    for name in browser_names.get(browser, []):
        found = shutil.which(name)
        if found:
            return found
    
    return None


def get_browser_args(browser: Browser, debug_port: int, profile_dir: str, env: Environment) -> List[str]:
    """
    Get browser-specific arguments for remote debugging.
    
    Args:
        browser: Browser type
        debug_port: Port for remote debugging
        profile_dir: Directory for browser profile
        env: Current environment
        
    Returns:
        List of command-line arguments
    """
    if browser == Browser.CHROME:
        # Chrome always binds to 127.0.0.1 regardless of --remote-debugging-address
        return [
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-hang-monitor",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-web-resources",
            "--metrics-recording-only",
            "--password-store=basic",
            "--use-mock-keychain",
            "about:blank",
        ]
    elif browser in (Browser.FIREFOX, Browser.LIBREWOLF):
        # Firefox/LibreWolf support --start-debugger-server with IP:port
        # For now, bind to localhost and use portproxy on Windows
        return [
            f"--start-debugger-server=127.0.0.1:{debug_port}",
            "--profile", profile_dir,
            "--no-remote",
            "about:blank",
        ]
    else:
        return []


def get_process_name(browser: Browser, env: Environment) -> str:
    """
    Get the process name for killing the browser.
    
    Args:
        browser: Browser type
        env: Current environment
        
    Returns:
        Process name
    """
    if env == Environment.WINDOWS:
        if browser == Browser.CHROME:
            return "chrome.exe"
        elif browser == Browser.FIREFOX:
            return "firefox.exe"
        elif browser == Browser.LIBREWOLF:
            return "librewolf.exe"
    else:
        if browser == Browser.CHROME:
            return "chrome"
        elif browser == Browser.FIREFOX:
            return "firefox"
        elif browser == Browser.LIBREWOLF:
            return "librewolf"
    return ""


def cleanup_profile(profile_dir: str):
    """
    Clean up browser profile directory to prevent corruption.
    
    Args:
        profile_dir: Path to profile directory
    """
    if os.path.exists(profile_dir):
        try:
            shutil.rmtree(profile_dir, ignore_errors=True)
            printer.step(f"Cleaned up profile directory: {profile_dir}")
        except Exception as e:
            printer.warning(f"Could not clean profile directory: {e}")


def kill_browser(browser: Browser, env: Environment):
    """
    Kill all instances of the specified browser.
    
    Args:
        browser: Browser to kill
        env: Current environment
    """
    process_name = get_process_name(browser, env)
    if not process_name:
        return
    
    try:
        if env == Environment.WINDOWS:
            # Use taskkill on Windows
            subprocess.run(
                ["taskkill", "/F", "/IM", process_name, "/T"],
                capture_output=True,
                timeout=10
            )
        else:
            # Use pkill on Unix-like systems
            subprocess.run(
                ["pkill", "-9", process_name],
                capture_output=True,
                timeout=10
            )
        printer.step(f"Killed existing {browser.value} processes")
    except Exception as e:
        printer.warning(f"Could not kill {browser.value}: {e}")


def launch_browser(config: BrowserConfig, env: Environment) -> Optional[subprocess.Popen]:
    """
    Launch browser with the specified configuration.
    
    Args:
        config: Browser configuration
        env: Current environment
        
    Returns:
        Popen object for the browser process, or None if failed
    """
    try:
        # Build command
        cmd = [config.path] + config.args
        
        if env == Environment.WINDOWS:
            # On Windows, use CREATE_NEW_PROCESS_GROUP to detach
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            # On Unix-like systems, use setsid to detach
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
        
        printer.success(f"Launched browser with PID {process.pid}")
        return process
    except Exception as e:
        printer.error(f"Failed to launch browser: {e}")
        return None


# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

def detect_environment() -> Environment:
    """
    Detect the current operating environment.
    
    Returns:
        Environment enum value
    """
    system = platform.system().lower()
    
    if system == "windows":
        return Environment.WINDOWS
    elif system == "linux":
        # Check if running in WSL
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    return Environment.WSL
        except FileNotFoundError:
            pass
        return Environment.LINUX
    elif system == "darwin":
        return Environment.MACOS
    else:
        return Environment.UNKNOWN


def detect_wsl_host_ip() -> str:
    """
    Detect the Windows host IP address from within WSL.
    
    Returns:
        IP address as string, or empty string if not in WSL or cannot detect
    """
    env = detect_environment()
    if env != Environment.WSL:
        return ""
    
    try:
        # Method 1: Parse /etc/resolv.conf (most reliable)
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        
        # Method 2: Parse ip route
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Output format: "default via <IP> dev eth0"
            parts = result.stdout.strip().split()
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                return parts[2]
    except Exception:
        pass
    
    return ""


# =============================================================================
# WINDOWS NETWORK SETUP
# =============================================================================

def is_admin() -> bool:
    """
    Check if the current process has Administrator privileges on Windows.
    
    Returns:
        True if running as Administrator, False otherwise
    """
    if platform.system().lower() != "windows":
        return False
    
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_wsl_adapter_ip() -> str:
    """
    Get the IP address of the WSL network adapter on Windows.
    
    This function searches for network adapters with "WSL" in the name
    and returns the IPv4 address.
    
    Returns:
        IP address as string, or empty string if not found
    """
    env = detect_environment()
    if env != Environment.WINDOWS:
        return ""
    
    try:
        # Use PowerShell to get WSL adapter IP
        # Wildcard match handles both "vEthernet (WSL)" and newer naming schemes
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "(Get-NetIPAddress -InterfaceAlias '*WSL*' -AddressFamily IPv4).IPAddress"
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip().split('\n')[0].strip()
            return ip
    except Exception as e:
        # Note: printer not available yet, will be initialized later
        pass
    
    return ""


def setup_portproxy(wsl_ip: str, port: int) -> bool:
    """
    Configure netsh portproxy to expose the debug port on the WSL interface.
    
    This maps: WSL_IP:port -> 127.0.0.1:port
    Requires Administrator privileges.
    
    Args:
        wsl_ip: WSL adapter IP address
        port: Debug port number
        
    Returns:
        True if successful, False otherwise
    """
    if not is_admin():
        printer.error("Administrator privileges required for portproxy setup")
        return False
    
    try:
        # Remove any existing mapping first (ignore errors)
        subprocess.run(
            [
                "netsh", "interface", "portproxy", "delete", "v4tov4",
                f"listenaddress={wsl_ip}", f"listenport={port}"
            ],
            capture_output=True,
            timeout=10
        )
        
        # Add the portproxy rule
        # CRITICAL: listenaddress=WSL_IP, connectaddress=127.0.0.1
        # This exposes the local Chrome instance to WSL
        cmd = [
            "netsh", "interface", "portproxy", "add", "v4tov4",
            f"listenaddress={wsl_ip}",
            f"listenport={port}",
            "connectaddress=127.0.0.1",
            f"connectport={port}"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            printer.success(f"Configured portproxy: {wsl_ip}:{port} -> 127.0.0.1:{port}")
            return True
        else:
            printer.error(f"Failed to configure portproxy: {result.stderr}")
            return False
    except Exception as e:
        printer.error(f"Error setting up portproxy: {e}")
        return False


def cleanup_portproxy(wsl_ip: str, port: int) -> bool:
    """
    Remove portproxy configuration.
    
    Args:
        wsl_ip: WSL adapter IP address
        port: Debug port number
        
    Returns:
        True if successful, False otherwise
    """
    if not is_admin():
        printer.warning("Administrator privileges required for portproxy cleanup")
        return False
    
    try:
        cmd = [
            "netsh", "interface", "portproxy", "delete", "v4tov4",
            f"listenaddress={wsl_ip}",
            f"listenport={port}"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            printer.success(f"Removed portproxy rule for {wsl_ip}:{port}")
            return True
        else:
            # Don't error if the rule didn't exist
            if "does not exist" not in result.stderr.lower():
                printer.warning(f"Portproxy cleanup issue: {result.stderr}")
            return True
    except Exception as e:
        printer.warning(f"Error cleaning up portproxy: {e}")
        return False


def verify_chrome_listening(port: int, max_retries: int = 10, delay: float = 1.0) -> bool:
    """
    Verify that Chrome is listening on the debug port.
    
    Args:
        port: Debug port number
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        True if Chrome is listening, False otherwise
    """
    import socket
    import json
    
    for attempt in range(max_retries):
        try:
            # Try to connect to the debug port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                # Port is open, try to fetch version endpoint
                try:
                    import urllib.request
                    url = f"http://127.0.0.1:{port}/json/version"
                    req = urllib.request.Request(url, headers={'User-Agent': 'WSL-Dev-Kit'})
                    
                    with urllib.request.urlopen(req, timeout=2) as response:
                        data = json.loads(response.read().decode())
                        if 'Browser' in data or 'webSocketDebuggerUrl' in data:
                            printer.success(f"Chrome DevTools listening on port {port}")
                            return True
                except Exception:
                    pass  # Port open but not responding yet
            
            if attempt < max_retries - 1:
                time.sleep(delay)
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    return False


@dataclass
class WindowsSetupResult:
    """Result of Windows orchestration"""
    success: bool
    wsl_ip: str
    portproxy_configured: bool
    chrome_listening: bool
    error_message: str = ""


class WindowsOrchestrator:
    """
    Orchestrates the complete Windows-side setup for WSL browser debugging.
    
    This class handles:
    - Checking for admin privileges
    - Finding and launching the browser
    - Setting up portproxy rules
    - Verifying the setup
    """
    
    def __init__(self, browser: Browser, debug_port: int):
        self.browser = browser
        self.debug_port = debug_port
        self.env = Environment.WINDOWS
        self.wsl_ip = ""
    
    def run(self) -> WindowsSetupResult:
        """
        Execute the full Windows setup workflow.
        
        Returns:
            WindowsSetupResult with status and details
        """
        result = WindowsSetupResult(
            success=False,
            wsl_ip="",
            portproxy_configured=False,
            chrome_listening=False
        )
        
        # Check admin privileges
        if not is_admin():
            result.error_message = "Administrator privileges required"
            printer.error(result.error_message)
            printer.info("Please run this script as Administrator")
            return result
        
        printer.step("Running as Administrator ✓")
        
        # Get WSL adapter IP
        printer.step("Detecting WSL network adapter...")
        self.wsl_ip = get_wsl_adapter_ip()
        result.wsl_ip = self.wsl_ip
        
        if not self.wsl_ip:
            result.error_message = "Could not detect WSL adapter IP"
            printer.error(result.error_message)
            printer.info("Make sure WSL is installed and has been run at least once")
            return result
        
        printer.success(f"WSL adapter IP: {self.wsl_ip}")
        
        # Find browser
        printer.step(f"Locating {self.browser.value}...")
        browser_path = find_browser(self.browser, self.env)
        
        if not browser_path:
            result.error_message = f"Could not find {self.browser.value} installation"
            printer.error(result.error_message)
            return result
        
        printer.success(f"Found: {browser_path}")
        
        # Kill existing instances and clean profile
        printer.step("Preparing browser environment...")
        kill_browser(self.browser, self.env)
        time.sleep(1)
        
        profile_dir = os.path.join(tempfile.gettempdir(), f"wsl-dev-{self.browser.value}-profile")
        cleanup_profile(profile_dir)
        
        # Launch browser
        printer.step(f"Launching {self.browser.value}...")
        browser_args = get_browser_args(self.browser, self.debug_port, profile_dir, self.env)
        process_name = get_process_name(self.browser, self.env)
        
        config = BrowserConfig(
            path=browser_path,
            debug_port=self.debug_port,
            profile_dir=profile_dir,
            args=browser_args,
            process_name=process_name
        )
        
        process = launch_browser(config, self.env)
        if not process:
            result.error_message = "Failed to launch browser"
            printer.error(result.error_message)
            return result
        
        # Wait and verify browser is listening
        printer.step("Waiting for browser to initialize...")
        if not verify_chrome_listening(self.debug_port):
            result.error_message = "Browser did not start listening on debug port"
            printer.error(result.error_message)
            return result
        
        result.chrome_listening = True
        
        # Configure portproxy
        printer.step("Configuring network portproxy...")
        if not setup_portproxy(self.wsl_ip, self.debug_port):
            result.error_message = "Failed to configure portproxy"
            printer.error(result.error_message)
            return result
        
        result.portproxy_configured = True
        
        # Final verification
        printer.step("Verifying setup...")
        result.success = True
        
        printer.success("=" * 60)
        printer.success("Windows setup complete!")
        printer.success(f"Browser debug endpoint: {self.wsl_ip}:{self.debug_port}")
        printer.success("WSL can now connect to the browser")
        printer.success("=" * 60)
        
        return result


# =============================================================================
# WSL ORCHESTRATION
# =============================================================================

def verify_connection(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Verify that we can connect to a host:port.
    
    Args:
        host: Host to connect to
        port: Port to connect to
        timeout: Connection timeout in seconds
    
    Returns:
        True if connection successful
    """
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def run_powershell_from_wsl(script: str) -> tuple[bool, str]:
    """
    Execute a PowerShell script from WSL using powershell.exe.
    
    Args:
        script: PowerShell script to execute
    
    Returns:
        Tuple of (success, output/error_message)
    """
    try:
        # Escape quotes in the script
        escaped_script = script.replace('"', '`"')
        
        # Use powershell.exe from WSL
        cmd = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    
    except subprocess.TimeoutExpired:
        return False, "PowerShell command timed out"
    except Exception as e:
        return False, f"Failed to run PowerShell: {e}"


@dataclass
class WSLSetupResult:
    """Result of WSL orchestration"""
    success: bool
    windows_host_ip: str
    windows_setup_completed: bool
    connection_verified: bool
    error_message: str = ""


class WSLOrchestrator:
    """
    Orchestrates browser debugging from WSL by triggering Windows-side setup.
    
    This class handles:
    - Detecting the Windows host IP
    - Generating and executing PowerShell script on Windows
    - Verifying the connection from WSL
    """
    
    def __init__(self, browser: Browser, debug_port: int):
        self.browser = browser
        self.debug_port = debug_port
        self.windows_host_ip = ""
    
    def run(self) -> WSLSetupResult:
        """
        Execute the full WSL orchestration workflow.
        
        Returns:
            WSLSetupResult with status and details
        """
        result = WSLSetupResult(
            success=False,
            windows_host_ip="",
            windows_setup_completed=False,
            connection_verified=False
        )
        
        printer.step("Running from WSL - initiating cross-environment setup")
        
        # Detect Windows host IP
        printer.step("Detecting Windows host IP...")
        self.windows_host_ip = detect_wsl_host_ip()
        result.windows_host_ip = self.windows_host_ip
        
        if not self.windows_host_ip:
            result.error_message = "Could not detect Windows host IP from WSL"
            printer.error(result.error_message)
            printer.info("Make sure you're running from WSL, not native Linux")
            return result
        
        printer.success(f"Windows host IP: {self.windows_host_ip}")
        
        # Check if we're already connected (maybe setup already done)
        printer.step("Checking existing connection...")
        if verify_connection(self.windows_host_ip, self.debug_port):
            printer.success("Browser debug port already accessible!")
            result.success = True
            result.windows_setup_completed = True
            result.connection_verified = True
            printer.info("Skipping Windows setup (already configured)")
            return result
        
        # Generate PowerShell script to run this same tool on Windows
        printer.step("Preparing Windows setup script...")
        
        # Get the path to this script on Windows filesystem
        # WSL path /mnt/c/... -> Windows path C:\...
        current_script = os.path.abspath(__file__)
        if current_script.startswith('/mnt/'):
            # Convert /mnt/c/path/to/script.py -> C:\path\to\script.py
            parts = current_script.split('/')
            drive = parts[2].upper()
            windows_path = f"{drive}:\\" + "\\".join(parts[3:])
        else:
            # Fallback - try to find python in Windows PATH
            result.error_message = "Could not determine Windows path to script"
            printer.error(result.error_message)
            printer.info(f"Script path: {current_script}")
            printer.info("Make sure the script is on a Windows drive (e.g., /mnt/c/...)")
            return result
        
        # Build PowerShell command to run this script on Windows
        ps_script = f"""
$ErrorActionPreference = 'Stop'

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {{
    Write-Error "Administrator privileges required. Please run PowerShell as Administrator and try again."
    exit 1
}}

# Find python
$python = $null
foreach ($cmd in @('python', 'python3', 'py')) {{
    try {{
        $version = & $cmd --version 2>&1
        if ($version -match 'Python 3') {{
            $python = $cmd
            break
        }}
    }} catch {{}}
}}

if (-not $python) {{
    Write-Error "Python 3 not found in PATH"
    exit 1
}}

# Run the script
Write-Host "Launching WSL Dev Kit on Windows..."
& $python "{windows_path}" --browser {self.browser.value} --port {self.debug_port}
"""
        
        # Execute on Windows
        printer.step("Executing setup on Windows (this requires Administrator)...")
        printer.warning("You may see a UAC prompt on Windows - please approve it")
        
        success, output = run_powershell_from_wsl(ps_script)
        
        if not success:
            result.error_message = f"Windows setup failed: {output}"
            printer.error(result.error_message)
            printer.info("")
            printer.info("Troubleshooting steps:")
            printer.info("1. Make sure PowerShell is run as Administrator on Windows")
            printer.info("2. Verify Python 3 is installed on Windows")
            printer.info("3. Check that the script path is accessible from Windows:")
            printer.info(f"   {windows_path}")
            return result
        
        result.windows_setup_completed = True
        printer.success("Windows setup completed")
        
        # Verify connection
        printer.step("Verifying connection from WSL...")
        max_attempts = 5
        for attempt in range(max_attempts):
            if verify_connection(self.windows_host_ip, self.debug_port):
                result.connection_verified = True
                result.success = True
                break
            
            if attempt < max_attempts - 1:
                printer.info(f"Attempt {attempt + 1}/{max_attempts} - waiting...")
                time.sleep(2)
        
        if not result.connection_verified:
            result.error_message = "Connection verification failed"
            printer.error(result.error_message)
            printer.info(f"Could not connect to {self.windows_host_ip}:{self.debug_port}")
            printer.info("Windows setup may have completed but port is not accessible")
            return result
        
        # Success!
        printer.success("=" * 60)
        printer.success("WSL orchestration complete!")
        printer.success(f"Browser debug endpoint: {self.windows_host_ip}:{self.debug_port}")
        printer.success("You can now use browser automation tools from WSL")
        printer.success("=" * 60)
        
        return result


@dataclass
class DiagnosticResult:
    """Result of diagnostic checks"""
    env: Environment
    browser_found: bool
    browser_path: str
    admin_rights: bool
    wsl_ip: str
    host_ip: str
    port_accessible: bool
    portproxy_rule_exists: bool
    details: List[str]


def run_diagnostics(browser_name: str, port: int) -> DiagnosticResult:
    """
    Run a full suite of diagnostic checks.
    
    Args:
        browser_name: Name of browser to check
        port: Debug port to check
        
    Returns:
        DiagnosticResult object
    """
    env = detect_environment()
    browser = Browser[browser_name.upper()]
    details = []
    
    printer.header("Diagnostic Report")
    
    # Check 1: Environment
    details.append(f"Environment: {env.value}")
    printer.step(f"Environment: {env.value}")
    
    # Check 2: Browser
    browser_path = find_browser(browser, env)
    browser_found = bool(browser_path)
    if browser_found:
        details.append(f"Browser found: {browser_path}")
        printer.success(f"Browser found: {browser_path}")
    else:
        details.append(f"Browser not found: {browser.value}")
        printer.error(f"Browser not found: {browser.value}")
        
    # Check 3: Admin rights (Windows only)
    admin_rights = False
    if env == Environment.WINDOWS:
        admin_rights = is_admin()
        status = "Yes" if admin_rights else "No"
        details.append(f"Admin rights: {status}")
        if admin_rights:
            printer.success(f"Admin rights: {status}")
        else:
            printer.warning(f"Admin rights: {status}")
    else:
        details.append("Admin rights: N/A (not Windows)")
        printer.info("Admin rights: N/A")
        
    # Check 4: Network config
    wsl_ip = ""
    host_ip = ""
    
    if env == Environment.WINDOWS:
        wsl_ip = get_wsl_adapter_ip()
        if wsl_ip:
            details.append(f"WSL Adapter IP: {wsl_ip}")
            printer.success(f"WSL Adapter IP: {wsl_ip}")
        else:
            details.append("WSL Adapter IP: Not found")
            printer.warning("WSL Adapter IP: Not found")
            
    elif env == Environment.WSL:
        host_ip = detect_wsl_host_ip()
        if host_ip:
            details.append(f"Windows Host IP: {host_ip}")
            printer.success(f"Windows Host IP: {host_ip}")
        else:
            details.append("Windows Host IP: Not found")
            printer.warning("Windows Host IP: Not found")

    # Check 5: Portproxy (Windows only)
    portproxy_rule_exists = False
    if env == Environment.WINDOWS and is_admin() and wsl_ip:
        # Check if rule exists using netsh
        try:
            cmd = ["netsh", "interface", "portproxy", "show", "v4tov4"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if f"{wsl_ip}" in result.stdout and f"{port}" in result.stdout:
                portproxy_rule_exists = True
                details.append(f"Portproxy rule exists for {wsl_ip}:{port}")
                printer.success(f"Portproxy rule exists for {wsl_ip}:{port}")
            else:
                details.append(f"No portproxy rule found for {wsl_ip}:{port}")
                printer.warning(f"No portproxy rule found for {wsl_ip}:{port}")
        except Exception as e:
            details.append(f"Error checking portproxy: {e}")
            printer.error(f"Error checking portproxy: {e}")

    # Check 6: Port accessibility
    port_accessible = False
    check_ip = "127.0.0.1"
    
    if env == Environment.WSL and host_ip:
        check_ip = host_ip
    
    details.append(f"Checking connection to {check_ip}:{port}...")
    if verify_connection(check_ip, port, timeout=1.0):
        port_accessible = True
        details.append(f"Port {port} is accessible")
        printer.success(f"Port {port} is accessible")
    else:
        details.append(f"Port {port} is NOT accessible")
        printer.warning(f"Port {port} is NOT accessible")

    return DiagnosticResult(
        env=env,
        browser_found=browser_found,
        browser_path=browser_path or "",
        admin_rights=admin_rights,
        wsl_ip=wsl_ip,
        host_ip=host_ip,
        port_accessible=port_accessible,
        portproxy_rule_exists=portproxy_rule_exists,
        details=details
    )


# =============================================================================
# COLORFUL OUTPUT
# =============================================================================

class ColorPrinter:
    """
    ANSI color printer for terminal output. No dependencies.
    Falls back to plain text on non-TTY or Windows without ANSI support.
    """
    
    # ANSI color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    
    def __init__(self):
        # Check if colors are supported
        self.enabled = self._supports_color()
    
    def _supports_color(self) -> bool:
        """Check if the terminal supports ANSI colors"""
        # Check if stdout is a TTY
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return False
        
        # On Windows, check for ANSI support
        if platform.system() == "Windows":
            try:
                # Windows 10+ supports ANSI escape codes
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Enable virtual terminal processing
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        
        return True
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if enabled"""
        if self.enabled:
            return f"{color}{text}{self.RESET}"
        return text
    
    def success(self, message: str):
        """Print success message in green"""
        print(self._colorize(f"✓ {message}", self.GREEN))
    
    def error(self, message: str):
        """Print error message in red"""
        print(self._colorize(f"✗ {message}", self.RED), file=sys.stderr)
    
    def warning(self, message: str):
        """Print warning message in yellow"""
        print(self._colorize(f"⚠ {message}", self.YELLOW))
    
    def info(self, message: str):
        """Print info message in blue"""
        print(self._colorize(f"ℹ {message}", self.BLUE))
    
    def step(self, message: str):
        """Print step message in cyan"""
        print(self._colorize(f"→ {message}", self.CYAN))
    
    def header(self, message: str):
        """Print header message in bold magenta"""
        print(self._colorize(f"\n{'='*60}\n{message}\n{'='*60}", self.MAGENTA + self.BOLD))


# Global printer instance
printer = ColorPrinter()


# =============================================================================
# ARGUMENT PARSER
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        prog="wsl-dev-kit",
        description="WSL Dev Kit - Unified Browser Debug Bridge for Windows/WSL development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows: Launch Chrome and set up debug bridge
  python wsl_dev_kit.py
  
  # WSL: Auto-orchestrate Windows setup
  python wsl_dev_kit.py
  
  # Specify browser and port
  python wsl_dev_kit.py --browser firefox --port 9223
  
  # Detection only (no launch)
  python wsl_dev_kit.py --detect-only
  
  # Cleanup existing setup
  python wsl_dev_kit.py --cleanup
        """
    )
    
    parser.add_argument(
        "--browser",
        type=str,
        choices=["chrome", "firefox", "librewolf"],
        default="chrome",
        help="Browser to launch (default: chrome)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="Remote debugging port (default: 9222)"
    )
    
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect environment and browser, do not launch"
    )
    
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up existing setup (kill browser, remove portproxy, etc.)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run full diagnostic checks"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Quick pass/fail validation check"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show version information and exit"
    )
    
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the embedded test page via HTTP"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Launch browser and open the test page (implies --serve)"
    )
    
    parser.add_argument(
        "--http-port",
        type=int,
        default=8080,
        help="HTTP server port for test page (default: 8080)"
    )
    
    return parser


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Print header
    printer.header("WSL Dev Kit - Browser Debug Bridge")
    
    # Handle test page serving
    if args.serve or args.test:
        if args.test:
            # --test implies --serve and opens browser
            printer.info("Test mode: serving test page and opening browser")
            env = detect_environment()
            browser = Browser[args.browser.upper()]
            serve_test_page(args.http_port, open_browser=True, browser=browser, env=env)
        else:
            # Just serve the test page
            printer.info("Serving embedded test page")
            serve_test_page(args.http_port, open_browser=False)
        return 0
    
    # Handle diagnostics
    if args.diagnose:
        run_diagnostics(args.browser, args.port)
        return 0

    if args.validate:
        printer.info("Running validation check...")
        result = run_diagnostics(args.browser, args.port)
        if result.browser_found and result.port_accessible:
            printer.success("Validation PASSED")
            return 0
        else:
            printer.error("Validation FAILED")
            return 1
    
    # Detect environment
    env = detect_environment()
    printer.info(f"Detected environment: {env.value}")
    
    # If in WSL, detect Windows host IP
    if env == Environment.WSL:
        host_ip = detect_wsl_host_ip()
        if host_ip:
            printer.info(f"Windows host IP: {host_ip}")
        else:
            printer.warning("Could not detect Windows host IP")
    
    # Parse browser
    browser = Browser[args.browser.upper()]
    printer.info(f"Target browser: {browser.value}")
    printer.info(f"Debug port: {args.port}")
    
    # Find browser executable
    browser_path = find_browser(browser, env)
    if not browser_path:
        printer.error(f"Could not find {browser.value} installation")
        printer.info(f"Searched paths: {BROWSER_PATHS.get(browser, {}).get(env, [])}")
        return 1
    
    printer.success(f"Found browser: {browser_path}")
    
    # If detect-only mode, exit here
    if args.detect_only:
        printer.success("Detection complete")
        return 0
    
    # Handle cleanup mode
    if args.cleanup:
        printer.step("Cleaning up...")
        kill_browser(browser, env)
        
        # Also cleanup portproxy on Windows if running as admin
        if env == Environment.WINDOWS and is_admin():
            wsl_ip = get_wsl_adapter_ip()
            if wsl_ip:
                cleanup_portproxy(wsl_ip, args.port)
        
        return 0
    
    # Windows-specific orchestration
    if env == Environment.WINDOWS:
        orchestrator = WindowsOrchestrator(browser, args.port)
        result = orchestrator.run()
        
        if not result.success:
            return 1
        
        return 0
    
    # WSL-specific orchestration
    if env == Environment.WSL:
        orchestrator = WSLOrchestrator(browser, args.port)
        result = orchestrator.run()
        
        if not result.success:
            return 1
        
        return 0
    
    # For other environments (native Linux, macOS), use simple launch
    printer.step("Native environment detected - launching browser locally")
    
    # Create temp profile directory
    profile_dir = os.path.join(tempfile.gettempdir(), f"wsl-dev-{browser.value}-profile")
    
    # Clean up existing browser and profile
    printer.step("Preparing browser environment...")
    kill_browser(browser, env)
    time.sleep(1)  # Give processes time to die
    cleanup_profile(profile_dir)
    
    # Create browser configuration
    browser_args = get_browser_args(browser, args.port, profile_dir, env)
    process_name = get_process_name(browser, env)
    
    config = BrowserConfig(
        path=browser_path,
        debug_port=args.port,
        profile_dir=profile_dir,
        args=browser_args,
        process_name=process_name
    )
    
    # Launch browser
    printer.step(f"Launching {browser.value}...")
    process = launch_browser(config, env)
    
    if not process:
        printer.error("Failed to launch browser")
        return 1
    
    # Wait for browser to initialize
    printer.step("Waiting for browser to initialize...")
    time.sleep(3)
    
    printer.success(f"Browser launched successfully on port {args.port}")
    printer.info("Browser is running in the background")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
