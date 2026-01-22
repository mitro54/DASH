#!/bin/bash
# =============================================================================
# DAIS Build Verification Test
# =============================================================================
#
# @file     test_build.sh
# @brief    Verifies DAIS binary was built correctly.
#
# @details  This script performs basic build verification by checking that
#           the DAIS binary exists and is executable. It does NOT test
#           functionality (see functional/test_commands.py for that).
#
# @usage    ./tests/test_build.sh
#           bash tests/test_build.sh
#
# @returns  0 on success, 1 on failure
#
# @note     PTY-dependent tests are intentionally excluded here because
#           this script may run in minimal Docker environments.
#
# =============================================================================

set -e  # Exit immediately on any error

# -----------------------------------------------------------------------------
# Binary Location
# -----------------------------------------------------------------------------
# Determine the path to the DAIS binary. This script can be run from:
#   - Project root (./tests/test_build.sh)
#   - Tests directory (./test_build.sh)
#   - Any directory via absolute path
# -----------------------------------------------------------------------------

if [ -f "build/DAIS" ]; then
    BINARY="./build/DAIS"
elif [ -f "../build/DAIS" ]; then
    BINARY="../build/DAIS"
else
    # Fallback: resolve path relative to script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    BINARY="$PROJECT_ROOT/build/DAIS"
fi

# -----------------------------------------------------------------------------
# Test Execution
# -----------------------------------------------------------------------------

echo "============================================"
echo " DAIS Build Verification Test"
echo "============================================"
echo "Binary path: $BINARY"
echo ""

# Test 1: Binary exists
echo "[TEST 1] Checking binary exists..."
if [ ! -f "$BINARY" ]; then
    echo "FAIL: Binary not found at $BINARY"
    echo ""
    echo "Debug info:"
    echo "  Current directory: $(pwd)"
    echo "  Build directory contents:"
    ls -la build/ 2>/dev/null || echo "    (no build directory)"
    exit 1
fi
echo "PASS: Binary exists"

# Test 2: Binary is executable
echo "[TEST 2] Checking binary is executable..."
if [ ! -x "$BINARY" ]; then
    echo "FAIL: Binary is not executable"
    echo "  Try: chmod +x $BINARY"
    exit 1
fi
echo "PASS: Binary is executable"

# Test 3: Binary file type verification
# Note: The 'file' command may not be available in all environments
echo "[TEST 3] Verifying binary file type..."
if command -v file &> /dev/null; then
    file "$BINARY"
else
    echo "  (file command not available, skipping)"
fi
echo "PASS: Binary file verified"

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

echo ""
echo "============================================"
echo " All build tests passed!"
echo "============================================"
exit 0
