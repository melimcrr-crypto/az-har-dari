#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemini_ep.py — روایت کامل یک قسمت با Gemini TTS

  GEMINI_API_KEY=... python3 shared/scripts/tts/gemini_ep.py episodes/ep02-crane-operator \
      --voice Charon --model gemini-2.5-pro-preview-tts

* متن از audio/script.json
* اصلاح تلفظ از audio/pron.json (واژه‌نامه) + عددها به حروف فارسی
* هر بخش به قطعه‌های ≤۱۲۰۰ کاراکتری شکسته می‌شود، بعد با ۰٫۲۵s مکث به هم چسبانده می‌شود
* هر بخش مستر می‌شود: EQ + کمپرس + loudnorm −۱۶ LUFS
خروجی: audio/s01.mp3 … + audio/gemini-report.json
"""
import argparse
import base64
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

STYLE = (
    "مثل یک آدم واقعی که برای یک دوست تعریف می‌کند حرف بزن: محاوره‌ای، گرم، بی‌تکلف و کمی سریع. "
    "نه لحن گویندهٔ خبر، نه لحن تبلیغاتی، نه لحن کتاب صوتی. نفس‌گیری طبیعی، مکث کوتاه انسانی "
    "پشت ویرگول و نقطه، و تأکید نامنظم روی کلمه‌های مهم. "
    "تلفظ: فارسی معیار تهرانی، بدون کشیدن واکه‌ها، بدون غلط تلفظی، حروف فارسی را درست و کامل "
    "ادا کن (پ، چ، ژ، گ را درست بخوان)، کسرهٔ اضافه را وصل بگو و کلمه‌ها را نشکن."
)

DIGITS = {'0': 'صفر', '1': 'یک', '2': 'دو', '3': 'سه', '4': 'چهار', '5': 'پنج',
          '6': 'شش', '7': 'هفت', '8': 'هشت', '9': 'نه'}
ONES = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه']
TEENS = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
TENS = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
HUNDS = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']


def n2fa(n):
    n = int(n)
    if n == 0:
        return 'صفر'
    parts = []
    if n >= 1_000_000_000:
        parts.append(n2fa(n // 1_000_000_000) + ' میلیارد')
        n %= 1_000_000_000
    if n >= 1_000_000:
        parts.append(n2fa(n // 1_000_000) + ' میلیون')
        n %= 1_000_000
    if n >= 1000:
        parts.append(n2fa(n // 1000) + ' هزار')
        n %= 1000
    if n >= 100:
        parts.append(HUNDS[n // 100])
        n %= 100
    if 10 <= n < 20:
        parts.append(TEENS[n - 10])
    elif n >= 20:
        t, o = divmod(n, 10)
        parts.append(TENS[t] + ((' و ' + ONES[o]) if o else ''))
    elif n > 0:
        parts.append(ONES[n])
    return ' و '.join(p for p in parts if p)


def spell_numbers(text):
    """۹۸٪ → نود و هشت درصد   |   ۴۵ → چهل و پنج   |   ۲٫۵ → دو و نیم"""
    def repl(m):
        raw = m.group(0).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
        if '٫' in raw or '.' in raw:
            a, b = re.split('[٫.]', raw)
            if b in ('۵', '5'):
                return n2fa(int(a)) + ' و نیم'
            return n2fa(int(a)) + ' ممیز ' + ' '.join(DIGITS[d] for d in b)
        return n2fa(int(raw))

    text = text.replace('٪', ' درصد ')
    return re.sub(r'[۰-۹0-9]+(?:[٫.][۰-۹0-9]+)?', repl, text)


def normalize(text, pron):
    text = spell_numbers(text)
    for wrong, right in pron.items():
        if wrong == right:
            continue
        text = re.sub(rf'(?<!\w){re.escape(wrong)}(?!\w)', right, text)
    text = text.replace('ي', 'ی').replace('ك', 'ک').replace('\u200c', '\u200c')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def chunks(text, limit=1200):
    out, buf = [], ''
    for sent in re.split(r'(?<=[.!؟:؛])\s+', text):
        if len(buf) + len(sent) + 1 > limit and buf:
            out.append(buf.strip())
            buf = sent
        else:
            buf = f'{buf} {sent}'.strip()
    if buf:
        out.append(buf.strip())
    return out or [text]


def synth(model, voice, text, key, retries=3):
    body = json.dumps({
        'contents': [{'parts': [{'text': f'{STYLE}\n\n{text}'}]}],
        'generationConfig': {
            'responseModalities': ['AUDIO'],
            'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}},
        },
    }).encode()
    req = urllib.request.Request(API.format(model=model), data=body,
                                 headers={'x-goog-api-key': key,
                                          'Content-Type': 'application/json'})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                data = json.loads(r.read())
            b64 = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
            mime = data['candidates'][0]['content']['parts'][0]['inlineData'].get('mimeType', '')
            rate = 24000 if '24000' in mime else 24000
            return base64.b64decode(b64), rate
        except urllib.error.HTTPError as exc:
            last = f'{exc.code} {exc.read().decode()[:200]}'
        except Exception as exc:                          # noqa: BLE001
            last = str(exc)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(last)


def ffmpeg():
    import shutil
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def master(src_wav, out_mp3):
    chain = ('highpass=f=75,'
             'equalizer=f=200:t=q:w=1.1:g=1.4,'
             'equalizer=f=2600:t=q:w=1.0:g=1.0,'
             'equalizer=f=7000:t=q:w=1.4:g=-1.4,'
             'acompressor=threshold=-19dB:ratio=2.4:attack=8:release=180:makeup=1.5,'
             'loudnorm=I=-16:TP=-1.5:LRA=10,aresample=48000')
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', src_wav, '-af', chain,
                    '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '192k', out_mp3], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--voice', default=os.environ.get('GEMINI_TTS_VOICE', 'Charon'))
    ap.add_argument('--model', default=os.environ.get('GEMINI_TTS_MODEL',
                                                      'gemini-2.5-pro-preview-tts'))
    args = ap.parse_args()
    key = os.environ.get('GEMINI_API_KEY') or ''
    if not key:
        raise SystemExit('GEMINI_API_KEY تنظیم نشده است')

    ep_dir = args.episode
    script = json.load(open(os.path.join(ep_dir, 'audio', 'script.json'), encoding='utf-8'))
    pron_path = os.path.join(ep_dir, 'audio', 'pron.json')
    pron = {}
    if os.path.exists(pron_path):
        pron = {k: v for k, v in json.load(open(pron_path, encoding='utf-8')).items()
                if not k.startswith('_')}

    os.makedirs(os.path.join(ep_dir, 'audio'), exist_ok=True)
    tmp_dir = os.path.join(ep_dir, 'audio', '_gemini')
    os.makedirs(tmp_dir, exist_ok=True)

    report = {'voice': args.voice, 'model': args.model, 'segments': []}
    t_all = time.time()
    total_chars = 0

    for seg in script['segments']:
        sid = seg['id']
        text = normalize(seg['text'], pron)
        total_chars += len(text)
        parts = chunks(text)
        pieces = []
        t0 = time.time()
        for i, part in enumerate(parts):
            pcm, rate = synth(args.model, args.voice, part, key)
            raw = os.path.join(tmp_dir, f'{sid}-{i}.pcm')
            wav = os.path.join(tmp_dir, f'{sid}-{i}.wav')
            open(raw, 'wb').write(pcm)
            subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(rate),
                            '-ac', '1', '-i', raw, wav], check=True)
            pieces.append(wav)
        # چسباندن قطعه‌ها با ۰٫۲۵ ثانیه سکوت
        lst = os.path.join(tmp_dir, f'{sid}.txt')
        silence = os.path.join(tmp_dir, 'gap.wav')
        if not os.path.exists(silence):
            subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'lavfi',
                            '-i', 'anullsrc=r=24000:cl=mono', '-t', '0.25', silence], check=True)
        with open(lst, 'w') as f:
            for k, p in enumerate(pieces):
                f.write(f"file '{os.path.abspath(p)}'\n")
                if k < len(pieces) - 1:
                    f.write(f"file '{os.path.abspath(silence)}'\n")
        joined = os.path.join(tmp_dir, f'{sid}-joined.wav')
        subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                        '-i', lst, '-ar', '24000', '-ac', '1', joined], check=True)
        out_mp3 = os.path.join(ep_dir, 'audio', f'{sid}.mp3')
        master(joined, out_mp3)
        d = None
        probe = subprocess.run([ffmpeg(), '-hide_banner', '-i', out_mp3],
                               capture_output=True, text=True).stderr
        for line in probe.splitlines():
            if 'Duration' in line:
                h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
                d = round(int(h) * 3600 + int(m) * 60 + float(s), 2)
        report['segments'].append({'id': sid, 'chars': len(text), 'chunks': len(parts),
                                   'seconds': d, 'build_seconds': round(time.time() - t0, 1)})
        print(f"{sid}  {d:>7}s  ({len(parts)} قطعه، {time.time() - t0:.1f}s)", flush=True)

    report['total_seconds'] = round(sum(s['seconds'] or 0 for s in report['segments']), 2)
    report['total_build_seconds'] = round(time.time() - t_all, 1)
    report['chars'] = total_chars
    json.dump(report, open(os.path.join(ep_dir, 'audio', 'gemini-report.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\nجمع: {report['total_seconds']}s ({report['total_seconds'] / 60:.2f} دقیقه) "
          f"در {report['total_build_seconds']}s · {total_chars} کاراکتر")


if __name__ == '__main__':
    main()
