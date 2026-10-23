#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_audio_sfx.py — میکس تمیز: روایت + افکت صدا، بدون موزیک

  python3 shared/scripts/prepare_audio_sfx.py episodes/ep02-crane-operator

ورودی : <episode>/audio/narration.mp3 + timings.json
خروجی : <episode>/audio/sfx.wav , <episode>/audio/mix.mp3
افکت‌ها: ووش نرم روی هر برش نما، کلیک ملایم در شروع هر بخش، ایمپکت کوتاه در تیتر/پایان
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

SR = 48000
FF = os.environ.get('FFMPEG', 'ffmpeg')


def dur(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise SystemExit(f'مدت {path} خوانده نشد')


def whoosh(n=0.55):
    """صدای عبور هوا: نویز با پاکت نرم و فیلتر ساده"""
    t = np.linspace(0, n, int(SR * n), endpoint=False)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(t.size)
    # فیلتر میان‌گذر ساده با تفاضل و میانگین متحرک
    k = 64
    noise = noise - np.convolve(noise, np.ones(k) / k, mode='same')
    env = np.sin(np.pi * t / n) ** 2
    swell = 0.35 + 0.65 * np.clip(t / n * 1.6, 0, 1)
    w = noise * env * swell
    return 0.30 * w / (np.max(np.abs(w)) + 1e-9)


def click(n=0.09):
    t = np.linspace(0, n, int(SR * n), endpoint=False)
    env = np.exp(-t * 45)
    return 0.20 * np.sin(2 * np.pi * 950 * t) * env


def impact(n=0.9):
    t = np.linspace(0, n, int(SR * n), endpoint=False)
    env = np.exp(-t * 5.5)
    low = np.sin(2 * np.pi * 62 * t) * env
    return 0.26 * low


def place(track, sound, at):
    i = int(at * SR)
    j = min(track.size, i + sound.size)
    if i < track.size:
        track[i:j] += sound[: j - i]


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep02-crane-operator'
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    tim = json.load(open(os.path.join(ep_dir, 'timings.json'), encoding='utf-8'))
    narration = os.path.join(ep_dir, ep['audio']['narration'])
    out_sfx = os.path.join(ep_dir, 'audio', 'sfx.wav')
    out_mix = os.path.join(ep_dir, 'audio', 'mix.mp3')

    if not os.path.exists(narration):
        print('… narration.mp3 نیست، از بخش‌ها ساخته می‌شود')
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'merge_audio.py'),
                        ep_dir], check=True)

    total = tim['total']
    track = np.zeros(int(total * SR), dtype=np.float32)

    shots = sorted(tim['shots'].items(), key=lambda kv: kv[1]['start'])
    w = whoosh()
    for k, (_, s) in enumerate(shots):
        if k == 0:
            continue
        place(track, w, max(0.0, s['start'] - 0.18))

    # شروع هر بخش: کلیک ملایم
    if ep.get('segments'):
        seg_ids = [sg['id'] for sg in ep['segments']]
        starts = []
        for sg in ep['segments']:
            first = min(sg['shots'])
            st = tim['shots'].get(str(first), {}).get('start')
            if st is not None:
                starts.append(st)
        for st in starts[1:]:
            place(track, click(), st)

    # تیتر و پایان: ایمپکت
    place(track, impact(), 0.15)
    place(track, impact(), max(0.5, total - 3.0))

    # کمی فضای استریو
    left = track
    right = np.concatenate([np.zeros(int(0.006 * SR), dtype=np.float32), track])[: track.size]
    sf.write(out_sfx, np.stack([left, right], axis=1), SR)
    print(f'✅ sfx.wav  ({total:.1f}s · {len(shots) - 1} ووش · {max(0, len(starts) - 1)} کلیک)')

    graph = ('[0:a]aresample=48000,aformat=channel_layouts=stereo[v];'
             '[1:a]aresample=48000,volume=0.85[s];'
             '[v][s]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,'
             'loudnorm=I=-16:TP=-1.5:LRA=11[out]')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', narration, '-i', out_sfx,
                    '-filter_complex', graph, '-map', '[out]',
                    '-codec:a', 'libmp3lame', '-b:a', '192k', out_mix], check=True)
    print(f'✅ mix.mp3  ({dur(out_mix):.1f}s · روایت + افکت، بدون موزیک، −۱۶ LUFS)')


if __name__ == '__main__':
    main()
