#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""summary_1min.py — خلاصهٔ گزارش دقیقه‌ای برای صفحهٔ Actions"""
import glob
import json

print('# یک دقیقه با Pocket-TTS-Farsi v2')
for p in sorted(glob.glob('out/*/*-report.json')):
    r = json.load(open(p, encoding='utf-8'))
    name = p.split('/')[1]
    print(f"\n**{name}** — صدا {r['audio_seconds']}s ({r['audio_minutes']} دقیقه) · "
          f"ساخت {r['build_seconds']}s · سرعت {r['realtime_factor']}×")
    print('| # | ثانیهٔ صدا | ثانیهٔ ساخت |')
    print('|---|---|---|')
    for s in r['sentences']:
        print(f"| {s['i']} | {s['seconds']} | {s['build_seconds']} |")
