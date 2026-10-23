#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_missing.py — وضعیت عکس‌های یک قسمت

  python3 shared/scripts/check_missing.py episodes/ep01-instagram-money
  python3 shared/scripts/check_missing.py episodes/ep01-instagram-money --next      # دستهٔ ۱۰ تایی
  python3 shared/scripts/check_missing.py episodes/ep01-instagram-money --json
"""
import glob
import json
import os
import sys

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp')


def load(ep_dir):
    ep = json.load(open(os.path.join(ep_dir, 'episode.json'), encoding='utf-8'))
    out = []
    for s in ep['shots']:
        d = os.path.join(ep_dir, 'shots', s['id'])
        files = [f for f in glob.glob(os.path.join(d, 'image', '*'))
                 if os.path.splitext(f)[1].lower() in IMG_EXT]
        s['has_image'] = bool(files)
        p = os.path.join(d, 'prompt.txt')
        s['prompt'] = open(p, encoding='utf-8').read().strip() if os.path.exists(p) else ''
        out.append(s)
    return ep, out


def main():
    args = sys.argv[1:]
    if not args:
        print('استفاده: check_missing.py episodes/<slug> [--next [n]] [--json]')
        raise SystemExit(2)
    ep_dir = args[0]
    shots_all = load(ep_dir)[1]
    missing = [s for s in shots_all if not s['has_image']]

    if '--json' in args:
        print(json.dumps({'episode': ep_dir, 'total': len(shots_all),
                          'done': len(shots_all) - len(missing), 'missing': len(missing),
                          'shots': [{'id': s['id'], 'has_image': s['has_image'],
                                     'character': s.get('character', False)} for s in shots_all]},
                         ensure_ascii=False, indent=1))
        return

    if '--next' in args:
        i = args.index('--next')
        n = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 10
        batch = missing[:n]
        done = len(shots_all) - len(missing)
        out = os.path.join(ep_dir, 'work-batch.md')
        with open(out, 'w', encoding='utf-8') as f:
            f.write(f"# دستهٔ {done // 10 + 1} — {len(batch)} نما\n\n")
            f.write(f"وضعیت: {done}/{len(shots_all)} · باقی‌مانده: {len(missing)}\n\n")
            f.write(f"> در این دور پیام فقط همین {len(batch)} نما را بساز، بعد push کن و متوقف شو.\n\n")
            for s in batch:
                f.write(f"## {s['id']}\n\n- مسیر: `shots/{s['id']}/image/`\n")
                f.write(f"- کاراکتر: {'بله — character_sheet.png را ضمیمه کن' if s.get('character') else 'نه'}\n\n")
                f.write("```text\n" + s['prompt'] + "\n```\n\n")
        print(f'✅ {len(batch)} پرامپت → {out}  (باقی‌مانده: {len(missing) - len(batch)})')
        return

    print(f"ساخته‌شده: {len(shots_all) - len(missing)}/{len(shots_all)}   باقی: {len(missing)}")
    for s in shots_all:
        print(('✅' if s['has_image'] else '⬜'), f"{s['id']:<34}",
              '👤' if s.get('character') else '  ', f"{s.get('seconds', 0):>3}s", s.get('note', ''))
    if missing:
        raise SystemExit(0)


if __name__ == '__main__':
    main()
