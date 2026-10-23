#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""summary_final.py — خلاصهٔ رندر برای صفحهٔ Actions"""
import glob
import json
import os

print('# رندر تمیز')
for rep in glob.glob('episodes/*/audio/gemini-report.json'):
    r = json.load(open(rep, encoding='utf-8'))
    print(f"\n**صدا** — {r['voice']} / {r['model']} · "
          f"{r['total_seconds']}s ({r['total_seconds'] / 60:.2f} دقیقه) · "
          f"ساخت {r['total_build_seconds']}s · {r['chars']} کاراکتر")
    print('| بخش | ثانیه | قطعه | ساخت |')
    print('|---|---|---|---|')
    for s in r['segments']:
        print(f"| {s['id']} | {s['seconds']} | {s['chunks']} | {s['build_seconds']}s |")
for p in glob.glob('episodes/*/output/*.mp4'):
    print(f"\nخروجی: `{p}` — **{os.path.getsize(p) / 1048576:.1f} MB**")
