#!/usr/bin/env python3
"""
DAIS Functional Tests
=====================
Uses pexpect to test DAIS interactive commands.
Requires: pip install pexpect

Run: python3 tests/functional/test_commands.py
"""

import sys
import os
import time

try:
    import pexpect
except ImportError:
    print("ERROR: pexpect not installed. Run: pip install pexpect")
    sys.exit(1)


# Path to DAIS binary (relative to project root)
DAIS_BINARY = os.path.join(os.path.dirname(__file__), '..', '..', 'build', 'DAIS')


def test_help_command():
    """Test that :help displays expected content."""
    print("[TEST] :help command...")
    
    child = pexpect.spawn(DAIS_BINARY, timeout=10, encoding='utf-8')
    
    # Wait for startup
    time.sleep(1)
    
    # Send :help command
    child.sendline(':help')
    
    # Look for expected content
    try:
        child.expect('DAIS Commands', timeout=5)
        print("  PASS: Help header found")
    except pexpect.TIMEOUT:
        print("  FAIL: Help header not found")
        child.sendline(':exit')
        child.close()
        return False
    
    # Clean exit
    child.sendline(':exit')
    child.expect(pexpect.EOF, timeout=5)
    child.close()
    
    print("  PASS: :help command works")
    return True


def test_history_command():
    """Test that :history displays without error."""
    print("[TEST] :history command...")
    
    child = pexpect.spawn(DAIS_BINARY, timeout=10, encoding='utf-8')
    
    # Wait for startup
    time.sleep(1)
    
    # Send :history command
    child.sendline(':history')
    
    # Give it time to respond
    time.sleep(0.5)
    
    # Clean exit
    child.sendline(':exit')
    
    try:
        child.expect(pexpect.EOF, timeout=5)
    except pexpect.TIMEOUT:
        print("  FAIL: Did not exit cleanly")
        child.close()
        return False
    
    child.close()
    print("  PASS: :history command works")
    return True


def test_exit_commands():
    """Test that :exit and :q both work."""
    print("[TEST] Exit commands...")
    
    # Test :exit
    child = pexpect.spawn(DAIS_BINARY, timeout=10, encoding='utf-8')
    time.sleep(1)
    child.sendline(':exit')
    
    try:
        child.expect(pexpect.EOF, timeout=5)
        print("  PASS: :exit works")
    except pexpect.TIMEOUT:
        print("  FAIL: :exit did not terminate")
        child.close()
        return False
    child.close()
    
    # Test :q
    child = pexpect.spawn(DAIS_BINARY, timeout=10, encoding='utf-8')
    time.sleep(1)
    child.sendline(':q')
    
    try:
        child.expect(pexpect.EOF, timeout=5)
        print("  PASS: :q works")
    except pexpect.TIMEOUT:
        print("  FAIL: :q did not terminate")
        child.close()
        return False
    child.close()
    
    print("  PASS: Both exit commands work")
    return True


def test_ls_settings():
    """Test that :ls (settings display) works."""
    print("[TEST] :ls settings command...")
    
    child = pexpect.spawn(DAIS_BINARY, timeout=10, encoding='utf-8')
    time.sleep(1)
    
    # Send :ls to show current settings
    child.sendline(':ls')
    time.sleep(0.5)
    
    # Clean exit
    child.sendline(':exit')
    
    try:
        child.expect(pexpect.EOF, timeout=5)
    except pexpect.TIMEOUT:
        print("  FAIL: Did not exit cleanly")
        child.close()
        return False
    
    child.close()
    print("  PASS: :ls settings works")
    return True


def main():
    """Run all functional tests."""
    print("=" * 50)
    print(" DAIS Functional Tests")
    print("=" * 50)
    
    # Check binary exists
    if not os.path.exists(DAIS_BINARY):
        print(f"ERROR: DAIS binary not found at {DAIS_BINARY}")
        print("Make sure to build DAIS first: mkdir build && cd build && cmake .. && make")
        sys.exit(1)
    
    results = []
    
    # Run tests
    results.append(('help', test_help_command()))
    results.append(('history', test_history_command()))
    results.append(('exit', test_exit_commands()))
    results.append(('ls_settings', test_ls_settings()))
    
    # Summary
    print("=" * 50)
    print(" Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
