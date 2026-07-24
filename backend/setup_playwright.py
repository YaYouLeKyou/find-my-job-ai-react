#!/usr/bin/env python3
"""
Setup script for Playwright browser automation.
Run this script to install Playwright and its browser binaries.

Usage:
    python backend/setup_playwright.py
    # or
    python -m backend.setup_playwright
"""

import subprocess
import sys


def run(cmd):
    """Run a command and print output."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("Playwright Setup for FindMyJobAI")
    print("=" * 60)

    # Step 1: Install playwright package
    print("\n[1/3] Installing playwright package...")
    if not run(f"{sys.executable} -m pip install playwright"):
        print("ERROR: Failed to install playwright package")
        return False

    # Step 2: Install browser binaries
    print("\n[2/3] Installing Chromium browser binaries...")
    if not run(f"{sys.executable} -m playwright install chromium"):
        print("ERROR: Failed to install Chromium browser binaries")
        return False

    # Step 3: Install system dependencies (Linux only)
    print("\n[3/3] Checking system dependencies...")
    try:
        if sys.platform.startswith("linux"):
            run(f"{sys.executable} -m playwright install-deps chromium")
        else:
            print("  System dependencies not needed on this platform.")
    except Exception as e:
        print(f"  Warning: Could not install system dependencies: {e}")

    print("\n" + "=" * 60)
    print("✅ Playwright setup complete!")
    print("=" * 60)
    print("\nPlaywright scrapers are now available for:")
    print("  - Indeed (fallback when requests-based scraper fails)")
    print("  - Monster (fallback)")
    print("  - Careerbuilder (fallback)")
    print("  - Simplyhired (fallback)")
    print("  - LinkedIn (fallback)")
    print("  - Welcome to the Jungle")
    print("  - HelloWork")
    print("  - APEC")
    print("  - JobTeaser")
    print("\nRestart your backend server to activate Playwright scrapers.")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
