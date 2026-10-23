#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
پوستهٔ سازگاری — به shared/scripts/check_missing.py وصل است.

  python3 check_missing.py                       # قسمت پیش‌فرض
  python3 check_missing.py --next                # دستهٔ ۱۰ تایی بعدی
  python3 check_missing.py episodes/ep02-x       # قسمت دیگر
  python3 check_missing.py episodes/ep02-x --next
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, 'shared', 'scripts', 'check_missing.py')
DEFAULT_EP = 'episodes/ep01-instagram-money'

args = sys.argv[1:]
if not args or args[0].startswith('-'):
    args = [DEFAULT_EP] + args
raise SystemExit(subprocess.call([sys.executable, TARGET] + args))
