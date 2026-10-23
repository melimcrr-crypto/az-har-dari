#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_samples.py — نمونهٔ صدای فارسی از چند موتور مختلف

  python3 shared/scripts/tts/make_samples.py --out tts-lab --engines piper:amir,piper:gyro,edge:fa-IR-FaridNeural

هر موتور همان دو جملهٔ آزمون را می‌خواند تا مقایسه منصفانه باشد.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

PIPER_BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fa/fa_IR'
HF = 'https://huggingface.co'

LINES = {
    'hook': 'اینستاگرام از تو پول نمی‌گیره، ولی از هر ثانیه‌ای که توی فیدت می‌گذرونی پول درمی‌آره.',
    'numbers': 'سال گذشته این شرکت نزدیک به دو میلیارد دلار از تبلیغات درآمد داشت؛ یعنی نود و هشت درصد کل درآمدش.',
    'punch': 'پس چرا وقتی یوتیوب میلیون‌ها بازدید رو مستقیم پول می‌ده، اینستاگرام فقط لایک می‌ده؟',
}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def piper_voice(voice, workdir):
    d = os.path.join(workdir, f'piper-{voice}')
    os.makedirs(d, exist_ok=True)
    onnx = os.path.join(d, f'fa_IR-{voice}-medium.onnx')
    cfg = onnx + '.json'
    for url, dst in ((f'{PIPER_BASE}/{voice}/medium/fa_IR-{voice}-medium.onnx', onnx),
                     (f'{PIPER_BASE}/{voice}/medium/fa_IR-{voice}-medium.onnx.json', cfg)):
        if not os.path.exists(dst):
            urllib.request.urlretrieve(url, dst)
    return onnx, cfg


def synth_piper(voice, out_dir):
    onnx, cfg = piper_voice(voice, out_dir)
    results = {}
    for key, text in LINES.items():
        wav = os.path.join(out_dir, f'piper-{voice}-{key}.wav')
        p = run(['piper', '--model', onnx, '--config', cfg, '--output_file', wav,
                 '--length_scale', '1.05'], input=text)
        if p.returncode or not os.path.exists(wav):
            p = run([sys.executable, '-m', 'piper', '--model', onnx, '--config', cfg,
                     '--output_file', wav], input=text)
        results[key] = wav if os.path.exists(wav) else None
        if results[key] is None:
            print('  piper error:', p.stderr[-400:])
    return results


def synth_edge(voice, out_dir):
    results = {}
    for key, text in LINES.items():
        mp3 = os.path.join(out_dir, f'edge-{voice.split("-")[-1]}-{key}.mp3')
        p = run(['edge-tts', '--voice', voice, '--rate=-4%', '--text', text,
                 '--write-media', mp3])
        results[key] = mp3 if os.path.exists(mp3) else None
        if results[key] is None:
            print('  edge error:', (p.stderr or p.stdout)[-400:])
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='tts-lab')
    ap.add_argument('--engines', default='edge:fa-IR-FaridNeural,piper:amir,piper:gyro')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    manifest = {'lines': LINES, 'runs': {}}
    for spec in args.engines.split(','):
        spec = spec.strip()
        if not spec:
            continue
        kind, name = spec.split(':', 1)
        t0 = time.time()
        print(f'== {spec}', flush=True)
        try:
            if kind == 'piper':
                res = synth_piper(name, args.out)
                label = f'piper-{name}'
            elif kind == 'edge':
                res = synth_edge(name, args.out)
                label = f'edge-{name}'
            else:
                print('  skipped (unknown kind)')
                continue
        except Exception as exc:                      # noqa: BLE001
            print('  FAILED:', exc)
            manifest['runs'][spec] = {'error': str(exc)}
            continue
        ok = [v for v in res.values() if v]
        manifest['runs'][spec] = {'files': res, 'ok': len(ok), 'seconds': round(time.time() - t0, 1)}
        print(f'  {len(ok)}/{len(LINES)} ok, {time.time() - t0:.1f}s')

    with open(os.path.join(args.out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    # یک فایل مقایسه‌ای: هر موتور پشت سر هم، جملهٔ اول
    pieces = [r['files'].get('hook') for r in manifest['runs'].values()
              if isinstance(r, dict) and r.get('files', {}).get('hook')]
    if pieces and shutil.which('ffmpeg'):
        lst = os.path.join(args.out, 'list.txt')
        with open(lst, 'w') as f:
            for p in pieces:
                f.write(f"file '{os.path.abspath(p)}'\n")
        run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
             '-ar', '44100', '-ac', '1', os.path.join(args.out, 'compare.mp3')])
        print('compare.mp3 built')


if __name__ == '__main__':
    main()
