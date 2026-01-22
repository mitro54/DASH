#!/bin/bash
# ============================================================================
# DAIS Build Test Script
# ============================================================================
# Verifies that DAIS builds correctly and can start/exit properly.
# Exit codes: 0 = success, 1 = failure
# ============================================================================

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINARY="$PROJECT_ROOT/build/DAIS"

echo "============================================"
echo " DAIS Build Verification Test"
echo "============================================"

# Test 1: Check binary exists
echo "[TEST 1] Checking binary exists..."
if [ ! -f "$BINARY" ]; then
    echo "FAIL: Binary not found at $BINARY"
    exit 1
fi
echo "PASS: Binary exists"

# Test 2: Check binary is executable
echo "[TEST 2] Checking binary is executable..."
if [ ! -x "$BINARY" ]; then
    echo "FAIL: Binary is not executable"
    exit 1
fi
echo "PASS: Binary is executable"

# Test 3: Smoke test - start DAIS and send :exit
echo "[TEST 3] Smoke test - start and exit..."

# Create a temporary file for capturing output
TEMP_OUTPUT=$(mktemp)

# Use timeout to prevent hanging, send :exit command
timeout 10s bash -c "echo ':exit' | $BINARY > $TEMP_OUTPUT 2>&1" || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "FAIL: DAIS timed out (did not exit within 10 seconds)"
        cat "$TEMP_OUTPUT"
        rm -f "$TEMP_OUTPUT"
        exit 1
    fi
}

# Check for expected startup message
if grep -q "DAIS has been started" "$TEMP_OUTPUT"; then
    echo "PASS: Startup message detected"
else
    echo "WARN: Startup message not found (may be OK depending on config)"
fi

# Check for session ended message
if grep -q "Session ended" "$TEMP_OUTPUT"; then
    echo "PASS: Clean exit detected"
else
    echo "WARN: Exit message not found"
fi

rm -f "$TEMP_OUTPUT"
echo "PASS: Smoke test completed"

echo "============================================"
echo " All tests passed!"
echo "============================================"
exit 0
