#!/usr/bin/env python3
"""Simple startup script: test CLI then run main app."""

import os
import subprocess
import sys


def install_cursor_cli():
    """Install Cursor CLI if needed."""
    cursor_path = os.path.expanduser("~/.local/bin/agent")
    if os.path.exists(cursor_path):
        return True

    print("Installing Cursor CLI...")
    result = subprocess.run(
        ["bash", "-c", "curl -fsSL https://cursor.com/install | bash"],
        capture_output=True,
    )
    if result.returncode == 0:
        print("✅ Cursor CLI installed")
        return True
    print(f"❌ Cursor CLI install failed: {result.stderr.decode()}")
    return False


def run_cli_test():
    """Run CLI test."""
    print("🧪 Testing CLI...")
    result = subprocess.run([sys.executable, "scripts/test_cli.py"], cwd="/app")
    return result.returncode == 0


def main():
    provider = os.environ.get("CLI_PROVIDER", "claude")
    print(f"Starting agent-engine (provider: {provider})...")

    # Install Cursor if needed
    if provider == "cursor":
        if not install_cursor_cli():
            sys.exit(1)

    # Run CLI test
    if not run_cli_test():
        print("⚠️  CLI test had warnings (continuing anyway)")

    print("✅ Starting main application...")

    # Start heartbeat in background
    subprocess.Popen([sys.executable, "scripts/heartbeat.py"])

    # Run main app (replaces this process)
    os.execv(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    main()
