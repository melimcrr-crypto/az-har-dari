#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_clean.py — رندر تمیز: بدون متن روی تصویر، بدون تیتر و چیپ و کارت پایانی

  python3 shared/scripts/render.py episodes/ep01-instagram-money [--crf 20] [--fps 25]

* زوم آرام متناوب (in/out)، کراس‌فید نرم، صفر نوشته روی تصویر
* صدا از <episode>/audio/mix.mp3
* فونت از shared/fonts
* خروجی: <episode>/output/<slug>.mp4
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FF = os.environ.get('FFMPEG', 'ffmpeg')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(ROOT, 'shared', 'fonts')

W, H = 1280, 720
XFADE = 0.45
ZOOM = 1.045
TITLE_SEC = 5.0
CHIP_SEC = 3.6
OUTRO_SEC = 9.0

TEAL = (18, 74, 78)
CREAM = (246, 238, 220)
CORAL = (233, 112, 91)
MINT = (178, 214, 208)


def font(kind, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f'Vazirmatn-{kind}.ttf'), size,
                              layout_engine=ImageFont.Layout.RAQM)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--crf', default='21')
    ap.add_argument('--fps', type=int, default=25)
    ap.add_argument('--preset', default='medium')
    args = ap.parse_args()

    ep_dir = args.episode
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    tim = json.load(open(os.path.join(ep_dir, 'timings.json'), encoding='utf-8'))
    out_dir = os.path.join(ep_dir, 'output')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, ep.get('slug', 'episode') + '.mp4')
    audio = os.path.join(ep_dir, ep['audio']['mix'])

    f_title = font('Black', 44)
    f_kick = font('Regular', 22)
    f_handle = font('Bold', 24)
    f_chip = font('Bold', 21)
    f_out1 = font('Bold', 30)
    f_out2 = font('Regular', 24)

    shots = {}
    for i, s in enumerate(ep['shots'], 1):
        d = os.path.join(ep_dir, 'shots', s['id'], 'image')
        cand = [f for f in sorted(os.listdir(d)) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if not cand:
            raise SystemExit(f'نمای {s["id"]} عکس ندارد')
        im = Image.open(os.path.join(d, cand[0])).convert('RGB')
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        shots[i] = im

    total = tim['total']
    seq = [(i, tim['shots'][str(i)]['start'], tim['shots'][str(i)]['dur'],
            tim['shots'][str(i)]['title']) for i in sorted(int(k) for k in tim['shots'])]
    starts = [s for (_, s, _, _) in seq]

    def zoomed(i, p):
        q = max(0.0, min(1.0, p))
        if i % 2 == 0:
            q = 1.0 - q
        z = 1.0 + (ZOOM - 1.0) * q
        nw, nh = int(W / z), int(H / z)
        x0, y0 = (W - nw) // 2, (H - nh) // 2
        return shots[i].crop((x0, y0, x0 + nw, y0 + nh)).resize((W, H), Image.BICUBIC)

    def overlay_title(frame):
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rectangle([0, H - 148, W, H], fill=TEAL + (218,))
        d.rectangle([0, H - 148, W, H - 142], fill=CORAL + (255,))
        d.text((W - 44, H - 116), ep.get('short_title', ''), font=f_title, fill=CREAM,
               direction='rtl', anchor='ra')
        d.text((W - 44, H - 58), f"قسمت {ep.get('number', 1)}  ·  {ep.get('channel', 'از هر دری')}",
               font=f_kick, fill=MINT, direction='rtl', anchor='ra')
        d.text((44, H - 61), ep.get('handle', '@AzHarDari'), font=f_handle, fill=CREAM,
               direction='ltr', anchor='lm')
        return Image.alpha_composite(frame.convert('RGBA'), lay).convert('RGB')

    def overlay_chip(frame, text, alpha):
        if alpha <= 0.02 or not text:
            return frame
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        bb = d.textbbox((0, 0), text, font=f_chip, direction='rtl')
        tw = bb[2] - bb[0]
        x1 = W - 36
        x0 = x1 - tw - 34
        d.rounded_rectangle([x0, 28, x1, 74], 11, fill=TEAL + (int(205 * alpha),))
        d.rectangle([x0 + 10, 71, x1 - 10, 74], fill=CORAL + (int(230 * alpha),))
        d.text((x1 - 17, 51), text, font=f_chip, fill=CREAM + (int(255 * alpha),),
               direction='rtl', anchor='rm')
        return Image.alpha_composite(frame.convert('RGBA'), lay).convert('RGB')

    def overlay_outro(frame, alpha):
        if alpha <= 0.02:
            return frame
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rectangle([0, 0, W, H], fill=TEAL + (int(190 * alpha),))
        d.rectangle([W // 2 - 60, H // 2 - 92, W // 2 + 60, H // 2 - 88],
                    fill=CORAL + (int(255 * alpha),))
        d.text((W // 2, H // 2 - 40), ep.get('outro_line', ''), font=f_out1,
               fill=CREAM + (int(255 * alpha),), direction='rtl', anchor='ma')
        d.text((W // 2, H // 2 + 24), 'هر هفته یک سؤال  ·  سابسکرایب کن', font=f_out2,
               fill=MINT + (int(255 * alpha),), direction='rtl', anchor='ma')
        d.text((W // 2, H // 2 + 92), ep.get('handle', '@AzHarDari'), font=f_handle,
               fill=CREAM + (int(255 * alpha),), direction='ltr', anchor='ma')
        return Image.alpha_composite(frame.convert('RGBA'), lay).convert('RGB')

    n_frames = int(round(total * args.fps))
    cmd = [FF, '-y', '-loglevel', 'error',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(args.fps), '-i', '-',
           '-i', audio,
           '-c:v', 'libx264', '-preset', args.preset, '-crf', str(args.crf), '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-tune', 'stillimage', '-g', '250', '-x264-params', 'ref=3:bframes=3',
           '-c:a', 'aac', '-b:a', '160k', '-shortest',
           '-movflags', '+faststart', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def shot_at(tt):
        lo, hi = 0, len(seq) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= tt:
                lo = mid
            else:
                hi = mid - 1
        return lo

    for k in range(n_frames):
        tt = k / args.fps
        idx = shot_at(tt)
        i, st, du, title = seq[idx]
        img = zoomed(i, (tt - st) / max(du, 0.01))
        if idx + 1 < len(seq) and tt > st + du - XFADE:
            ni, nst, ndu, _ = seq[idx + 1]
            a = min(1.0, (tt - (st + du - XFADE)) / XFADE)
            img = Image.blend(img, zoomed(ni, max(0.0, (tt - nst) / max(ndu, 0.01))), a)
        # بدون هیچ لایهٔ متنی — تنها تصویر، زوم و کراس‌فید
        try:
            proc.stdin.write(img.tobytes())
        except BrokenPipeError:
            break
        if k % 1000 == 0:
            print(f'{k}/{n_frames} ({tt:6.1f}s)', flush=True)

    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise SystemExit('ffmpeg خطا داد')
    print(f'✅ {out}  ({os.path.getsize(out)/1048576:.1f} MB)')


if __name__ == '__main__':
    main()
