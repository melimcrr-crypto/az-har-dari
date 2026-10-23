#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint_images.py — بررسی قواعد تصویر: نسبت ۱۶:۹، وزن، نام فایل، حداقل ابعاد"""
import glob
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAX_KB = 900
MIN_W = 1280
bad = []

for p in sorted(glob.glob(os.path.join(ROOT, 'episodes/*/shots/*/image/*'))):
    if os.path.splitext(p)[1].lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        continue
    rel = os.path.relpath(p, ROOT)
    size_kb = os.path.getsize(p) / 1024
    with Image.open(p) as im:
        w, h = im.size
    ratio = w / h
    if abs(ratio - 16 / 9) > 0.06:
        bad.append(f'{rel}: نسبت {ratio:.2f} (باید ۱٫۷۸)')
    if size_kb > MAX_KB:
        bad.append(f'{rel}: {size_kb:.0f}KB (حداکثر {MAX_KB})')
    if w < MIN_W:
        bad.append(f'{rel}: عرض {w}px (حداقل {MIN_W})')
    expected = os.path.basename(os.path.dirname(os.path.dirname(p)))
    if os.path.splitext(os.path.basename(p))[0] != expected:
        bad.append(f'{rel}: نام فایل باید {expected} باشد')

if bad:
    print('⚠️  ' + str(len(bad)) + ' مورد:')
    for b in bad:
        print('  -', b)
    sys.exit(0)
print('✅ همهٔ تصویرها سالم‌اند')
