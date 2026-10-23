#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_pron.py — بررسی تلفظ: صدا را با Whisper برمی‌گرداند و با متن مقایسه می‌کند

  python3 shared/scripts/tts/check_pron.py episodes/ep02-crane-operator

اگر شباهت یک بخش از ۰٫۷۵ کمتر بود، آن بخش با «⚠» علامت می‌خورد تا دوباره ساخته شود.
خروجی: audio/pron-report.json
"""
import difflib
import json
import os
import re
import sys


def norm(s):
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('\u200c', ' ')
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep02-crane-operator'
    script = json.load(open(os.path.join(ep_dir, 'audio', 'script.json'), encoding='utf-8'))
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device='cpu', compute_type='int8')

    rows = []
    for seg in script['segments']:
        path = os.path.join(ep_dir, 'audio', f"{seg['id']}.mp3")
        if not os.path.exists(path):
            rows.append({'id': seg['id'], 'missing': True})
            continue
        segments, _ = model.transcribe(path, language='fa', beam_size=5)
        got = ' '.join(s.text for s in segments)
        sim = round(difflib.SequenceMatcher(None, norm(seg['text']), norm(got)).ratio(), 3)
        rows.append({'id': seg['id'], 'similarity': sim,
                     'ok': sim >= 0.75, 'transcript': got[:300]})
        print(f"{seg['id']}  {sim:.3f}  {'✅' if sim >= 0.75 else '⚠'}")

    json.dump(rows, open(os.path.join(ep_dir, 'audio', 'pron-report.json'), 'w',
                         encoding='utf-8'), ensure_ascii=False, indent=1)
    bad = [r['id'] for r in rows if r.get('similarity', 1) < 0.75]
    print('\nپایین‌تر از آستانه:', ', '.join(bad) if bad else 'هیچ')
    print('|', ' | '.join(f"{r['id']} {r.get('similarity', '—')}" for r in rows), '|')


if __name__ == '__main__':
    main()
