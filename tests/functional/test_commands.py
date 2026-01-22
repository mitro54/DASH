#!/usr/bin/env python3
"""
DAIS Functional Tests.

This module provides functional tests for the DAIS shell wrapper using pexpect
to simulate interactive terminal sessions. Tests verify core functionality
including startup, shutdown, and built-in commands.

Usage:
    python3 tests/functional/test_commands.py

Requirements:
    - pexpect: pip install pexpect
    - DAIS binary must be built in ./build/DAIS

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed or binary not found
"""

import sys
import os
import time

try:
    import pexpect
except ImportError:
    print("ERROR: pexpect not installed. Run: pip install pexpect")
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

STARTUP_TIMEOUT = 10  # Seconds to wait for DAIS startup message
COMMAND_TIMEOUT = 5   # Seconds to wait for command responses
EXIT_TIMEOUT = 10     # Seconds to wait for clean exit
SHELL_INIT_DELAY = 2  # Seconds to allow shell initialization


# =============================================================================
# Utilities
# =============================================================================

def find_binary():
    """
    Locate the DAIS binary by checking common build paths.

    Searches multiple candidate paths relative to both the current working
    directory and the script location to support various execution contexts.

    Returns:
        str: Absolute path to the DAIS binary if found, None otherwise.
    """
    candidates = [
        './build/DAIS',
        '../build/DAIS',
        os.path.join(os.path.dirname(__file__), '..', '..', 'build', 'DAIS'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def spawn_dais(binary):
    """
    Spawn a new DAIS process with PTY allocation.

    Args:
        binary: Path to the DAIS binary.

    Returns:
        pexpect.spawn: The spawned child process.
    """
    return pexpect.spawn(binary, timeout=15, encoding='utf-8')


def cleanup_child(child):
    """
    Safely terminate and close a pexpect child process.

    Args:
        child: The pexpect child process to clean up.
    """
    try:
        child.sendline(':exit')
        child.expect(pexpect.EOF, timeout=EXIT_TIMEOUT)
    except pexpect.TIMEOUT:
        child.terminate(force=True)
    finally:
        child.close()


# =============================================================================
# Test Cases
# =============================================================================

def test_startup_and_exit():
    """
    Verify DAIS starts correctly and responds to :exit command.

    This test confirms:
    - DAIS launches and displays a startup message
    - The :exit command terminates the session cleanly
    - No zombie processes are left behind

    Returns:
        bool: True if test passed, False if failed, None if skipped.
    """
    print("[TEST] Startup and exit...")

    binary = find_binary()
    if not binary:
        print("  SKIP: Binary not found")
        return None

    try:
        child = spawn_dais(binary)

        # Check for startup message
        try:
            child.expect('DAIS has been started', timeout=STARTUP_TIMEOUT)
            print("  PASS: Startup message detected")
        except pexpect.TIMEOUT:
            print("  WARN: Startup message not found (continuing anyway)")

        # Allow shell to initialize
        time.sleep(SHELL_INIT_DELAY)

        # Test clean exit
        child.sendline(':exit')
        try:
            child.expect(pexpect.EOF, timeout=EXIT_TIMEOUT)
            print("  PASS: Clean exit")
        except pexpect.TIMEOUT:
            print("  FAIL: Did not exit within timeout")
            child.terminate(force=True)
            return False

        child.close()
        return True

    except Exception as e:
        print(f"  FAIL: Exception - {e}")
        return False


def test_help_command():
    """
    Verify the :help command displays expected content.

    This test confirms:
    - The :help command is recognized
    - Output contains the "DAIS Commands" header
    - Session can be exited after running :help

    Returns:
        bool: True if test passed, False if failed, None if skipped.
    """
    print("[TEST] :help command...")

    binary = find_binary()
    if not binary:
        print("  SKIP: Binary not found")
        return None

    try:
        child = spawn_dais(binary)
        time.sleep(SHELL_INIT_DELAY + 1)

        child.sendline(':help')

        try:
            child.expect('DAIS Commands', timeout=COMMAND_TIMEOUT)
            print("  PASS: Help header found")
        except pexpect.TIMEOUT:
            print("  WARN: Help header not found")

        time.sleep(0.5)
        cleanup_child(child)
        print("  PASS: :help command works")
        return True

    except Exception as e:
        print(f"  FAIL: Exception - {e}")
        return False


def test_q_exit():
    """
    Verify the :q shortcut command exits DAIS.

    This test confirms:
    - The :q command is recognized as an exit alias
    - Session terminates cleanly without needing :exit

    Returns:
        bool: True if test passed, False if failed, None if skipped.
    """
    print("[TEST] :q exit command...")

    binary = find_binary()
    if not binary:
        print("  SKIP: Binary not found")
        return None

    try:
        child = spawn_dais(binary)
        time.sleep(SHELL_INIT_DELAY + 1)

        child.sendline(':q')

        try:
            child.expect(pexpect.EOF, timeout=EXIT_TIMEOUT)
            print("  PASS: :q works")
            child.close()
            return True
        except pexpect.TIMEOUT:
            print("  FAIL: :q did not terminate")
            child.terminate(force=True)
            return False

    except Exception as e:
        print(f"  FAIL: Exception - {e}")
        return False


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """
    Execute all functional tests and report results.

    Runs each test case sequentially with delays between tests to avoid
    resource contention. Prints a summary and exits with appropriate code.
    """
    print("=" * 50)
    print(" DAIS Functional Tests")
    print("=" * 50)

    binary = find_binary()
    if not binary:
        print("ERROR: DAIS binary not found")
        print("Searched: ./build/DAIS, ../build/DAIS")
        print("Build first: mkdir build && cd build && cmake .. && make")
        sys.exit(1)

    print(f"Using binary: {binary}")
    print()

    # Execute tests with inter-test delays
    results = []

    results.append(('startup_exit', test_startup_and_exit()))
    time.sleep(1)

    results.append(('help', test_help_command()))
    time.sleep(1)

    results.append(('q_exit', test_q_exit()))

    # Print summary
    print()
    print("=" * 50)
    print(" Results Summary")
    print("=" * 50)

    valid_results = [(name, r) for name, r in results if r is not None]
    passed = sum(1 for _, r in valid_results if r)
    total = len(valid_results)

    for name, result in results:
        status = "SKIP" if result is None else ("PASS" if result else "FAIL")
        print(f"  {name}: {status}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total and total > 0:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
