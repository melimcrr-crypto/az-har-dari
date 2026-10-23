#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""judge.py — صدای ساخته‌شده را با Whisper برمی‌گرداند و با متن اصلی مقایسه می‌کند"""
import difflib
import glob
import json
import os
import re
import sys

import numpy as np


def norm(s):
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('\u200c', ' ')
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def load(path):
    from faster_whisper import decode_audio
    return decode_audio(path, sampling_rate=16000)


def main():
    lab = sys.argv[1] if len(sys.argv) > 1 else 'tts-lab'
    man = json.load(open(os.path.join(lab, 'manifest.json'), encoding='utf-8'))
    lines = man['lines']
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device='cpu', compute_type='int8')

    rows = []
    for spec, run in man['runs'].items():
        if 'files' not in run:
            rows.append({'engine': spec, 'status': 'failed', 'error': run.get('error')})
            continue
        got, total = 0.0, 0
        detail = {}
        for key, path in run['files'].items():
            if not path or not os.path.exists(path) or os.path.getsize(path) < 1024:
                continue
            try:
                audio = load(path)
            except Exception as exc:                  # noqa: BLE001
                print(f'  skip {path}: {exc}')
                continue
            segs, _ = model.transcribe(audio, language='fa', beam_size=5)
            text = ' '.join(s.text for s in segs).strip()
            sim = difflib.SequenceMatcher(None, norm(lines[key]), norm(text)).ratio()
            got += sim
            total += 1
            detail[key] = {'transcript': text, 'similarity': round(sim, 3)}
        rows.append({'engine': spec, 'status': 'ok',
                     'similarity': round(got / total, 3) if total else 0.0, 'detail': detail})

    rows.sort(key=lambda r: -r.get('similarity', 0))
    out = os.path.join(lab, 'judgement.json')
    json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print('| موتور | شباهت متن Whisper | وضعیت |')
    print('|---|---|---|')
    for r in rows:
        print(f"| {r['engine']} | {r.get('similarity', '-')} | {r['status']} |")
    print('\nجزئیات در', out)


if __name__ == '__main__':
    main()
