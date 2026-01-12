#!/bin/bash

# Configuration
PORT=9222
LOG_FILE="debug-bridge.log"
# Get Windows IP (Route default -> awk print 3rd column)
WSL_IP=$(ip route show | grep -i default | awk '{ print $3}')

# Helper function for logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Clear previous log
echo "--- Starting New Session ---" > "$LOG_FILE"

# 1. Sanity Check IP
if [ -z "$WSL_IP" ]; then
    log "❌ CRITICAL ERROR: Could not detect Windows IP."
    exit 1
fi
log "Windows Host IP detected as: $WSL_IP"

# 2. Cleanup
log "--- Cleaning up Port $PORT ---"
if sudo lsof -t -i:$PORT >/dev/null; then
    PID=$(sudo lsof -t -i:$PORT)
    log "Killing process $PID..."
    sudo kill -9 $PID
else
    log "Port $PORT is clear."
fi

# 3. Start Bridge
log "--- Starting Bridge (Socat) ---"
# Start socat with IPv4 force
nohup socat TCP4-LISTEN:$PORT,fork,reuseaddr TCP:$WSL_IP:$PORT >> "$LOG_FILE" 2>&1 &
SOCAT_PID=$!
log "Bridge started with PID $SOCAT_PID"

# Wait for bind
sleep 1

# 4. Hard Verification (The Fix)
log "--- Verification Test (Hard 5s Limit) ---"

# We use the 'timeout' utility to kill curl if it takes > 5 seconds
# timeout 5s: The OS kills the command after 5s
# curl -v: Verbose output (captured to log) to see WHERE it hangs
if timeout 5s curl -v http://127.0.0.1:$PORT/json/version >> "$LOG_FILE" 2>&1; then
    log "✅ SUCCESS! Connection established."
    echo ""
    # Print the JSON to console for confirmation
    curl -s --max-time 2 http://127.0.0.1:$PORT/json/version | head -n 5
    exit 0
else
    EXIT_CODE=$?
    log "❌ FAILURE. Test failed."
    
    if [ $EXIT_CODE -eq 124 ]; then
        log "Reason: TIMEOUT (The connection hung and was killed)."
        log "Diagnosis: The Windows Firewall is likely silently dropping packets."
        log "Fix: Open PowerShell as Admin and run: New-NetFirewallRule -DisplayName 'WSL Bridge' -Direction Inbound -InterfaceAlias 'vEthernet (WSL)' -Action Allow"
    else
        log "Reason: Connection Refused or Error (Code $EXIT_CODE)."
        log "Diagnosis: Chrome is not listening or rejecting the connection."
    fi
    exit 1
fi
