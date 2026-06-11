#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TriTier-M3U-Scanner
نقطه ورود اصلی برنامه
"""
import sys
import os
import threading # ✅ اضافه کردن ماژول Thread

# اطمینان از اینکه ماژول‌های پروژه قابل شناسایی هستند
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.app import IPTVScannerGUI

def main():
    try:

        print("  > 🖥️ LAUNCHING GUI...")
        app = IPTVScannerGUI()
        app.run() # حالا پنجره برنامه بدون مشکل باز می‌شود
        
    except KeyboardInterrupt:
        print("\n[!] Program terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()