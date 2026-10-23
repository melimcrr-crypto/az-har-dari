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
    "محاوره‌ای، گرم و بی‌تکلف، با سرعت طبیعی پادکست؛ مثل کسی که برای یک دوست تعریف می‌کند. "
    "نه لحن خبر، نه لحن تبلیغاتی، نه لحن کتاب صوتی. کلمه‌ها را نکش و مکث طولانی نگذار، "
    "اما پشت ویرگول و نقطه نفس طبیعی بگیر. تلفظ فارسی معیار تهرانی، بدون غلط تلفظی."
)
STYLE_SHORT = "محاوره‌ای و گرم، با سرعت طبیعی پادکست. فارسی معیار تهرانی، بدون غلط تلفظی."

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


KEYS = []
_ki = {'i': 0}


def keys_from_env():
    raw = os.environ.get('GEMINI_API_KEYS') or os.environ.get('GEMINI_API_KEY') or ''
    return [k.strip() for k in raw.replace('\n', ',').split(',') if k.strip()]


def next_key():
    if not KEYS:
        return ''
    k = KEYS[_ki['i'] % len(KEYS)]
    _ki['i'] += 1
    return k


def synth(model, voice, text, key, retries=4):
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
        style = STYLE if attempt == 0 else STYLE_SHORT
        body = json.dumps({
            'contents': [{'parts': [{'text': f'{style}\n\n{text}'}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}},
            },
        }).encode()
        req = urllib.request.Request(API.format(model=model), data=body,
                                     headers={'x-goog-api-key': key or next_key(),
                                              'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                data = json.loads(r.read())
            parts_ = data['candidates'][0]['content']['parts']
            inline = next((p['inlineData'] for p in parts_ if 'inlineData' in p), None)
            if inline is None:
                last = 'پاسخ بدون صدا: ' + str(data)[:160]
                key = next_key()
                time.sleep(1 + attempt)
                continue
            data['candidates'][0]['content']['parts'][0]['inlineData'] = inline
            b64 = inline['data']
            mime = inline.get('mimeType', '')
            rate = 24000
            m2 = __import__('re').search(r'rate=(\d+)', mime)
            if m2:
                rate = int(m2.group(1))
            return base64.b64decode(b64), rate
        except urllib.error.HTTPError as exc:
            last = f'{exc.code} {exc.read().decode()[:200]}'
            if exc.code in (429, 403, 400):
                key = next_key()
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


def master(src_wav, out_mp3, tempo=1.0):
    chain = ('highpass=f=75,'
             'equalizer=f=200:t=q:w=1.1:g=1.4,'
             'equalizer=f=2600:t=q:w=1.0:g=1.0,'
             'equalizer=f=7000:t=q:w=1.4:g=-1.4,'
             'acompressor=threshold=-19dB:ratio=2.4:attack=8:release=180:makeup=1.5,'
             'loudnorm=I=-16:TP=-1.5:LRA=10,'
             + (f'atempo={tempo:.3f},' if abs(tempo - 1.0) > 0.001 else '')
             + 'aresample=48000')
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', src_wav, '-af', chain,
                    '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '192k', out_mp3], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--voice', default=os.environ.get('GEMINI_TTS_VOICE', 'Charon'))
    ap.add_argument('--model', default=os.environ.get('GEMINI_TTS_MODEL',
                                                      'gemini-2.5-flash-preview-tts'))
    ap.add_argument('--tempo', type=float, default=float(os.environ.get('GEMINI_TTS_TEMPO', '1.0')),
                    help='سرعت نهایی گفتار بدون تغییر گام صدا')
    args = ap.parse_args()
    global KEYS
    KEYS = keys_from_env()
    key = KEYS[0] if KEYS else ''
    if not key:
        raise SystemExit('GEMINI_API_KEYS (یا GEMINI_API_KEY) تنظیم نشده است')
    print(f'🔑 {len(KEYS)} کلید · مدل {args.model} · صدا {args.voice} · tempo {args.tempo}', flush=True)

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

    report = {'voice': args.voice, 'model': args.model, 'tempo': args.tempo, 'segments': []}
    durations = {}
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
        master(joined, out_mp3, tempo=args.tempo)
        d = None
        probe = subprocess.run([ffmpeg(), '-hide_banner', '-i', out_mp3],
                               capture_output=True, text=True).stderr
        for line in probe.splitlines():
            if 'Duration' in line:
                h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
                d = round(int(h) * 3600 + int(m) * 60 + float(s), 2)
        wsdur = None
        try:
            import wave as _w
            with _w.open(joined) as _f:
                wsdur = round(_f.getnframes() / _f.getframerate(), 3)
        except Exception:                                  # noqa: BLE001
            pass
        # مدت باید از خودِ mp3 خوانده شود (بعد از tempo و مسترینگ)، نه از wav قبل از tempo
        durations[sid] = d if d else (round(wsdur / max(args.tempo, 0.01), 3) if wsdur else None)
        report['segments'].append({'id': sid, 'chars': len(text), 'chunks': len(parts),
                                   'seconds': d, 'build_seconds': round(time.time() - t0, 1)})
        print(f"{sid}  {d:>7}s  ({len(parts)} قطعه، {time.time() - t0:.1f}s)", flush=True)

    report['total_seconds'] = round(sum(s['seconds'] or 0 for s in report['segments']), 2)
    report['total_build_seconds'] = round(time.time() - t_all, 1)
    report['chars'] = total_chars
    json.dump(durations, open(os.path.join(ep_dir, 'audio', 'durations.json'), 'w',
                              encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(report, open(os.path.join(ep_dir, 'audio', 'gemini-report.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\nجمع: {report['total_seconds']}s ({report['total_seconds'] / 60:.2f} دقیقه) "
          f"در {report['total_build_seconds']}s · {total_chars} کاراکتر")


if __name__ == '__main__':
    main()
