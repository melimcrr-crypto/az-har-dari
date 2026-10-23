#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_audio.py — چسباندن بخش‌های صوتی به narration.mp3 (همان پارامترهای narrate.py)"""
import json
import os
import subprocess
import sys
import wave

FF = os.environ.get('FFMPEG', 'ffmpeg')
GAP, LEAD, TAIL = 0.30, 0.35, 0.80


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep01-instagram-money'
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    adir = os.path.join(ep_dir, 'audio')
    out = os.path.join(adir, 'narration.mp3')
    parts, sr = [], None
    for s in ep['segments']:
        p = os.path.join(adir, s['id'] + '.wav')
        if not os.path.exists(p):
            mp3 = os.path.join(adir, s['id'] + '.mp3')
            subprocess.run([FF, '-y', '-loglevel', 'error', '-i', mp3, '-ac', '1', '-ar', '24000',
                            '-c:a', 'pcm_s16le', p], check=True)
        with wave.open(p) as w:
            sr = sr or w.getframerate()
            parts.append(w.readframes(w.getnframes()))
    gap = b'\x00\x00' * int(GAP * sr)
    data = b'\x00\x00' * int(LEAD * sr) + gap.join(parts) + b'\x00\x00' * int(TAIL * sr)
    wav = os.path.join(adir, '_narration.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', wav, '-codec:a', 'libmp3lame',
                    '-b:a', '192k', out], check=True)
    os.remove(wav)
    print(f'✅ narration.mp3 ({len(data)/2/sr:.1f}s)')


if __name__ == '__main__':
    main()
