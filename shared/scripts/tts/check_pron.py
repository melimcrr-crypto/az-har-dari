#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_pron.py — بررسی تلفظ و درستی متن با گوش دادن به صدای ساخته‌شده

  python3 shared/scripts/tts/check_pron.py episodes/ep02-crane-operator

روش: هر بخش صوتی به Gemini داده می‌شود، برگرداندهٔ متن با متن اصلی مقایسه می‌شود
(شباهت واژه‌به‌واژه). پایین‌تر از آستانه = جای تلفظ یا برش خوردن جمله.
اگر کلید Gemini نبود، Whisper محلی (اگر نصب باشد) و در نهایت فقط گزارش «بررسی نشد».
خروجی: audio/pron-report.json
"""
import base64
import difflib
import json
import os
import re
import sys
import urllib.request

MODEL = os.environ.get('GEMINI_CHECK_MODEL', 'gemini-2.5-flash')
PROMPT = ("این فایل صوتی فارسی محاوره‌ای است. فقط متن را دقیقاً همان‌طور که شنیده می‌شود بنویس، "
          "بدون توضیح و بدون مقدمه.")


def norm_words(s):
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('\u200c', ' ').replace('ٔ', '')
    s = re.sub(r'[^\w\s]', ' ', s)
    return [w for w in re.split(r'\s+', s) if w]


def keys():
    raw = os.environ.get('GEMINI_API_KEYS') or os.environ.get('GEMINI_API_KEY') or ''
    return [k.strip() for k in raw.replace('\n', ',').split(',') if k.strip()]


def transcribe_gemini(path, ks):
    b64 = base64.b64encode(open(path, 'rb').read()).decode()
    body = json.dumps({'contents': [{'parts': [
        {'text': PROMPT},
        {'inline_data': {'mime_type': 'audio/mp3', 'data': b64}}]}],
        'generationConfig': {'temperature': 0}}).encode()
    last = None
    for k in ks:
        req = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
            data=body, headers={'x-goog-api-key': k, 'Content-Type': 'application/json'})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=300))
            return d['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as exc:                            # noqa: BLE001
            last = str(exc)
    raise RuntimeError(last)


def transcribe_whisper(path):
    from faster_whisper import WhisperModel
    m = WhisperModel('small', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(path, language='fa', beam_size=5)
    return ' '.join(s.text for s in segs)


def main():
    ep_dir = sys.argv[1] if len(sys.argv) > 1 else 'episodes/ep02-crane-operator'
    thr = float(os.environ.get('PRON_THRESHOLD', '0.80'))
    script = json.load(open(os.path.join(ep_dir, 'audio', 'script.json'), encoding='utf-8'))
    ks = keys()
    rows = []
    for seg in script['segments']:
        sid = seg['id']
        path = os.path.join(ep_dir, 'audio', f'{sid}.mp3')
        if not os.path.exists(path):
            rows.append({'id': sid, 'missing': True})
            continue
        try:
            got = transcribe_gemini(path, ks) if ks else transcribe_whisper(path)
        except Exception as exc:                            # noqa: BLE001
            rows.append({'id': sid, 'error': str(exc)[:120]})
            print(f'{sid}  ✗ {str(exc)[:80]}')
            continue
        a, b = norm_words(seg['text']), norm_words(got)
        sim = round(difflib.SequenceMatcher(None, a, b).ratio(), 3)
        diff = [w for w in a if w not in b][:12]
        rows.append({'id': sid, 'similarity': sim, 'ok': sim >= thr,
                     'missing_words': diff, 'transcript': got[:400]})
        print(f"{sid}  {sim:.3f}  {'✅' if sim >= thr else '⚠'}  {' '.join(diff)}")

    report = os.path.join(ep_dir, 'audio', 'pron-report.json')
    json.dump(rows, open(report, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    bad = [r['id'] for r in rows if r.get('similarity', 1) < thr]
    print('\nپایین‌تر از آستانه:', ', '.join(bad) if bad else 'هیچ')
    print('|', ' | '.join(f"{r['id']} {r.get('similarity', '—')}" for r in rows), '|')
    print(f'گزارش: {report}')


if __name__ == '__main__':
    main()
