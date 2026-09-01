#!/usr/bin/env python3.11
"""
gen_qf_pdfs.py — RENAMED to gen_match_pdf.py (v5.11)

This wrapper forwards all arguments to gen_match_pdf.py.
"""
import sys, os, subprocess
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen_match_pdf.py')
print("⚠️  gen_qf_pdfs.py is deprecated — redirecting to gen_match_pdf.py", file=sys.stderr)
os.execv(sys.executable, [sys.executable, script] + sys.argv[1:])
