#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_timings.py — زمان‌بندی نماها از مدت واقعی فایل‌های صوتی

  python3 shared/scripts/build_timings.py episodes/ep01-instagram-money

خروجی: <episode>/timings.json  (شروع و مدت هر نما + جمع کل)
نقشهٔ «کدام بخش صوتی روی کدام نماها می‌نشیند» داخل episode.json است: segments[].shots
"""
import json
import os
import subprocess
import sys
import wave


def wav_durations(ep_dir, segments):
    """مدت هر بخش صوتی.

    اولویت: مقدار ذخیره‌شده در episode.json (segments[].dur) → ffprobe → فایل wav اگر موجود باشد.
    """
    out = {}
    adir = os.path.join(ep_dir, 'audio')
    for s in segments:
        if s.get('dur'):
            out[s['id']] = float(s['dur'])
            continue
        wav = os.path.join(adir, s['id'] + '.wav')
        if os.path.exists(wav):
            with wave.open(wav) as w:
                out[s['id']] = w.getnframes() / w.getframerate()
            continue
        mp3 = os.path.join(adir, s['id'] + '.mp3')
        if os.path.exists(mp3):
            out[s['id']] = probe_duration(mp3)
            continue
        raise SystemExit(f'صوت بخش {s["id"]} نیست و مقدار dur هم در episode.json ندارد')
    return out


def probe_duration(path):
    """مدت با ffprobe؛ اگر نبود، پیمایش هدر mp3."""
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'default=nw=1:nk=1', path],
                           capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return mp3_duration(path)


def mp3_duration(path):
    """مدت mp3 بدون ffmpeg: پیمایش هدر فریم‌ها."""
    import struct
    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    rates = [44100, 48000, 32000]
    with open(path, 'rb') as f:
        data = f.read()
    i, total = 0, 0.0
    if data[:3] == b'ID3':
        size = ((data[6] & 0x7f) << 21) | ((data[7] & 0x7f) << 14) | ((data[8] & 0x7f) << 7) | (data[9] & 0x7f)
        i = 10 + size
    frames = 0
    while i < len(data) - 4:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            br_idx = (b2 >> 4) & 0x0F
            sr_idx = (b2 >> 2) & 0x03
            pad = (b2 >> 1) & 0x01
            if br_idx in (0, 15) or sr_idx == 3:
                i += 1
                continue
            br = bitrates[br_idx] * 1000
            sr = rates[sr_idx]
            if br == 0:
                i += 1
                continue
            if b1 & 0x18 == 0x18:      # MPEG1
                samples = 1152
                flen = int(144 * br / sr) + pad
            else:                       # MPEG2 / 2.5
                samples = 576
                flen = int(72 * br / sr) + pad
            total += samples / sr
            frames += 1
            i += max(flen, 1)
        else:
            i += 1
    if frames == 0:
        raise SystemExit(f'مدت {path} خوانده نشد')
    return total


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep01-instagram-money'
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    segs = ep['segments']
    shots = ep['shots']
    durs = wav_durations(ep_dir, segs)

    timed = {}
    t = 0.0
    for s in segs:
        ids = s['shots']
        weights = [shots[i - 1]['seconds'] for i in ids]
        tot = sum(weights)
        for i, w in zip(ids, weights):
            d = durs[s['id']] * w / tot
            timed[i] = {'start': round(t, 2), 'dur': round(d, 2),
                        'seg': s['id'], 'title': s.get('title', '')}
            t += d

    out = {'episode': ep.get('title', ''), 'segments': {k: round(v, 2) for k, v in durs.items()},
           'shots': timed, 'total': round(t, 2)}
    path = os.path.join(ep_dir, 'timings.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✅ {path} — {len(timed)} نما · {t/60:.2f} دقیقه')
    return out


if __name__ == '__main__':
    main()
