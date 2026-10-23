#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_audio.py — ساخت bed و میکس (روایت + موزیک با ducking)

  python3 shared/scripts/prepare_audio.py episodes/ep01-instagram-money

ورودی : <episode>/audio/narration.mp3  +  موزیک تعریف‌شده در episode.json
خروجی : <episode>/audio/bed.mp3 , <episode>/audio/mix.mp3
نیاز  : ffmpeg (روی رانر گیت‌هاب نصب است)
"""
import json
import os
import subprocess
import sys

FF = os.environ.get('FFMPEG', 'ffmpeg')
XF = 2.0


def dur(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if 'Duration' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise SystemExit(f'مدت {path} خوانده نشد')


def make_bed(track, target, out):
    trk = dur(track)
    n = max(2, int(target / max(trk - XF, 1)) + 2)
    inputs = []
    for _ in range(n):
        inputs += ['-i', track]
    fmt = 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo'
    graph = f'[0:a]{fmt}[z0];'
    cur = '[z0]'
    for i in range(1, n):
        graph += f'[{i}:a]{fmt}[z{i}];{cur}[z{i}]acrossfade=d={XF}:c1=tri:c2=tri[a{i}];'
        cur = f'[a{i}]'
    graph += f'{cur}atrim=0:{target},afade=t=in:st=0:d=2.5,afade=t=out:st={max(0,target-8)}:d=8[out]'
    subprocess.run([FF, '-y', '-loglevel', 'error'] + inputs +
                   ['-filter_complex', graph, '-map', '[out]',
                    '-codec:a', 'libmp3lame', '-b:a', '192k', out], check=True)
    print(f'✅ bed.mp3  ({dur(out):.1f}s · لوپ {n}× با کراس‌فید {XF}s)')


def make_mix(narration, bed, out):
    graph = (
        '[0:a]aresample=48000,volume=1.0,asplit=2[v1][v2];'
        '[1:a]aresample=48000,volume=0.30[m];'
        '[m][v1]sidechaincompress=threshold=0.035:ratio=12:attack=15:release=450:makeup=1[duck];'
        '[duck]volume=0.62[bed];'
        '[v2][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,'
        'loudnorm=I=-16:TP=-1.5:LRA=11[out]'
    )
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', narration, '-i', bed,
                    '-filter_complex', graph, '-map', '[out]',
                    '-codec:a', 'libmp3lame', '-b:a', '192k', out], check=True)
    print(f'✅ mix.mp3  ({dur(out):.1f}s · موزیک با ducking، −۱۶ LUFS)')


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep01-instagram-money'
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    a = ep['audio']
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    narration = os.path.join(ep_dir, a['narration'])
    music = a['music']
    music = music if os.path.isabs(music) else os.path.normpath(os.path.join(ep_dir, music))
    bed = os.path.join(ep_dir, a['bed'])
    mix = os.path.join(ep_dir, a['mix'])
    if not os.path.exists(music):
        music = os.path.join(here, 'shared/music/curiosity.mp3')
    os.makedirs(os.path.dirname(bed), exist_ok=True)
    if not os.path.exists(narration):
        print('… narration.mp3 نیست، از بخش‌ها ساخته می‌شود')
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'merge_audio.py'),
                        ep_dir], check=True)
    target = dur(narration)
    make_bed(music, target, bed)
    make_mix(narration, bed, mix)


if __name__ == '__main__':
    main()
