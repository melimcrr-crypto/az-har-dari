#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
synth_episode.py — کل روایتِ یک قسمت را با یک موتور می‌سازد

  python3 shared/scripts/tts/synth_episode.py episodes/ep01-instagram-money \
      --engine edge:fa-IR-FaridNeural --out /tmp/ep01-farid
  python3 shared/scripts/tts/synth_episode.py episodes/ep01-instagram-money \
      --engine piper:ganji --out /tmp/ep01-ganji

خروجی: s01.mp3 … sNN.mp3 + report.json (مدت هر بخش، زمان ساخت، کاراکتر)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PIPER_BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fa/fa_IR'


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def duration(path):
    p = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', path])
    try:
        return round(float(p.stdout.strip()), 2)
    except ValueError:
        p = run(['ffmpeg', '-i', path])
        m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', p.stderr)
        if not m:
            return None
        h, mi, s = m.groups()
        return round(int(h) * 3600 + int(mi) * 60 + float(s), 2)


def load_segments(ep_dir):
    script = json.load(open(os.path.join(ep_dir, 'audio', 'script.json'), encoding='utf-8'))
    pron_path = os.path.join(ep_dir, 'audio', 'pron.json')
    pron = {}
    if os.path.exists(pron_path):
        pron = {k: v for k, v in json.load(open(pron_path, encoding='utf-8')).items()
                if not k.startswith('_')}

    def fix(text):
        for wrong, right in pron.items():
            if wrong != right:
                text = re.sub(rf'(?<!\w){re.escape(wrong)}(?!\w)', right, text)
        return text

    return [{'id': s['id'], 'title': s.get('title', ''), 'text': fix(s['text'])}
            for s in script['segments']]


def chunks(text, limit=1200):
    parts, buf = [], ''
    for sent in re.split(r'(?<=[.!؟:؛])\s+', text):
        if len(buf) + len(sent) + 1 > limit and buf:
            parts.append(buf.strip())
            buf = sent
        else:
            buf = f'{buf} {sent}'.strip()
    if buf:
        parts.append(buf.strip())
    return parts or [text]


def synth_edge(voice, text, out_mp3, rate='-3%'):
    tmp = []
    for i, part in enumerate(chunks(text)):
        piece = f'{out_mp3}.part{i}.mp3'
        p = run(['edge-tts', '--voice', voice, f'--rate={rate}', '--text', part,
                 '--write-media', piece])
        if not os.path.exists(piece) or os.path.getsize(piece) < 1024:
            raise RuntimeError((p.stderr or p.stdout).strip()[-300:])
        tmp.append(piece)
    if len(tmp) == 1:
        os.replace(tmp[0], out_mp3)
    else:
        lst = out_mp3 + '.txt'
        with open(lst, 'w') as f:
            for t in tmp:
                f.write(f"file '{os.path.abspath(t)}'\n")
        run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
             '-i', lst, '-c:a', 'libmp3lame', '-b:a', '96k', '-ar', '24000', '-ac', '1', out_mp3])
        for t in tmp + [lst]:
            os.remove(t)


def piper_files(voice, workdir):
    os.makedirs(workdir, exist_ok=True)
    onnx = os.path.join(workdir, f'fa_IR-{voice}-medium.onnx')
    cfg = onnx + '.json'
    for url, dst in ((f'{PIPER_BASE}/{voice}/medium/fa_IR-{voice}-medium.onnx', onnx),
                     (f'{PIPER_BASE}/{voice}/medium/fa_IR-{voice}-medium.onnx.json', cfg)):
        if not os.path.exists(dst):
            urllib.request.urlretrieve(url, dst)
    return onnx, cfg


def synth_piper(voice, text, out_mp3, workdir):
    onnx, cfg = piper_files(voice, workdir)
    wav = out_mp3 + '.wav'
    p = run(['piper', '--model', onnx, '--config', cfg, '--output_file', wav,
             '--length_scale', '1.02'], input=text)
    if not os.path.exists(wav):
        raise RuntimeError((p.stderr or '')[-300:])
    run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libmp3lame',
         '-b:a', '96k', '-ac', '1', out_mp3])
    os.remove(wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--engine', required=True, help='edge:fa-IR-FaridNeural یا piper:ganji')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    kind, name = args.engine.split(':', 1)
    os.makedirs(args.out, exist_ok=True)
    segs = load_segments(args.episode)

    report = {'engine': args.engine, 'segments': []}
    t_all = time.time()
    total_chars = 0
    for seg in segs:
        out = os.path.join(args.out, f"{seg['id']}.mp3")
        t0 = time.time()
        if kind == 'edge':
            synth_edge(name, seg['text'], out)
        elif kind == 'piper':
            synth_piper(name, seg['text'], out, os.path.join(args.out, '_models'))
        else:
            raise SystemExit('engine ناشناخته')
        dur = duration(out)
        total_chars += len(seg['text'])
        report['segments'].append({'id': seg['id'], 'chars': len(seg['text']),
                                   'seconds': dur, 'build_seconds': round(time.time() - t0, 1)})
        print(f"{seg['id']}  {dur:>6}s  ({len(seg['text'])} char, {time.time() - t0:.1f}s build)",
              flush=True)

    report['total_audio_seconds'] = round(sum(s['seconds'] or 0 for s in report['segments']), 2)
    report['total_build_seconds'] = round(time.time() - t_all, 1)
    report['total_chars'] = total_chars
    json.dump(report, open(os.path.join(args.out, 'report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\nجمع صدا: {report['total_audio_seconds']}s   زمان ساخت: {report['total_build_seconds']}s"
          f"   کاراکتر: {total_chars}")


if __name__ == '__main__':
    main()
