#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""summary.py — خلاصهٔ گزارش‌های report.json برای صفحهٔ Actions"""
import glob
import sys

print('# روایت کامل با موتورهای مختلف')
for path in sorted(glob.glob('out/*/report.json')):
    import json
    r = json.load(open(path, encoding='utf-8'))
    print(f"\n**{r['engine']}** — صدا {r['total_audio_seconds']}s · ساخت "
          f"{r['total_build_seconds']}s · {r['total_chars']} کاراکتر")
    print('| بخش | ثانیه | ساخت |')
    print('|---|---|---|')
    for s in r['segments']:
        print(f"| {s['id']} | {s['seconds']} | {s['build_seconds']}s |")
sys.stdout.flush()
