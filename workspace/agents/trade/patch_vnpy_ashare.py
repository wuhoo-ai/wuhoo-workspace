#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch vnpy_futu gateway to support A-share and US exchanges

This patch adds the missing exchange mappings for:
- A-share (SSE/SZSE)
- US stocks (NASDAQ/NYSE)
"""

import sys
from pathlib import Path

# Find the gateway file
venv_path = Path(__file__).parent / 'venv-futu'
if not venv_path.exists():
    print("❌ Virtual environment not found")
    sys.exit(1)

gateway_file = venv_path / 'lib64' / 'python3.11' / 'site-packages' / 'vnpy_futu' / 'futu_gateway.py'

# Try alternative path (some systems use lib instead of lib64)
if not gateway_file.exists():
    gateway_file = venv_path / 'lib' / 'python3.11' / 'site-packages' / 'vnpy_futu' / 'futu_gateway.py'

if not gateway_file.exists():
    print(f"❌ Gateway file not found: {gateway_file}")
    sys.exit(1)

print(f"Patching: {gateway_file}")

# Read the file
with open(gateway_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already patched
if 'Exchange.SSE: "SH"' in content and 'Exchange.NASDAQ: "US"' in content:
    print("✅ Already patched")
    sys.exit(0)

# Patch the EXCHANGE_VT2FUTU mapping
old_mapping = """EXCHANGE_VT2FUTU: Dict[Exchange, str] = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
}"""

new_mapping = """EXCHANGE_VT2FUTU: Dict[Exchange, str] = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
    Exchange.SSE: "SH",          # A-share Shanghai
    Exchange.SZSE: "SZ",         # A-share Shenzhen
    Exchange.NASDAQ: "US",       # US NASDAQ
    Exchange.NYSE: "US",         # US NYSE
}"""

if old_mapping in content:
    content = content.replace(old_mapping, new_mapping)

    # Write back
    with open(gateway_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Patch applied successfully")
    print("\nAdded mappings:")
    print("  Exchange.SSE → SH")
    print("  Exchange.SZSE → SZ")
    print("  Exchange.NASDAQ → US")
    print("  Exchange.NYSE → US")
else:
    print("⚠️  Could not find the expected mapping pattern")
    print("Manual patching may be required")
    sys.exit(1)
