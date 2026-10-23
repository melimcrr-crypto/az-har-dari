#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pocket_v2_long.py — Pocket-TTS-Farsi v2، متن محاوره‌ای، جمله‌به‌جمله + مسترینگ

  python3 shared/scripts/tts/pocket_v2_long.py out/long --voice prompt_hello.wav --tag take1

خروجی: <tag>-raw.wav (خام ۲۴k) · <tag>.wav (مستر ۴۸k) · <tag>.mp3 · <tag>-report.json
"""
import argparse
import json
import os
import re
import subprocess
import time

import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer, T5ForConditionalGeneration

from normalize_fa import normalize_for_model

SENTENCES = [
    'ببین، یه چیزی رو باید بدونی.',
    'اینستاگرام از تو یه ریال هم نمی‌گیره، ولی از هر ثانیه‌ای که توی فیدت می‌گذرونی داره پول درمی‌آره.',
    'حالا این پول از کجا می‌آد؟ از جیب آدمی که تو هیچ‌وقت نمی‌بینیش.',
    'یعنی همون تبلیغی که با یه اسکرول از روش رد می‌شی.',
    'میدونی چی باحاله؟ تو فکر می‌کنی تماشاچی هستی، ولی در واقع خودِ تو محصولی.',
    'هر لایکی که می‌دی، هر ثانیه‌ای که مکث می‌کنی، همه‌ش تبدیل می‌شه به یه عدد روی صفحهٔ یه نفر دیگه.',
    'و اون عدد، دقیقاً همون چیزیه که برندها براش پول می‌ده.',
    'حالا فکر نکن این ماجرا مال آدمای معروفه؛ نه، هر کسی که گوشی دستشه توی این بازی هست.',
    'حتی اون مغازه‌ای که توی محل شماست، داره برای دیده شدن پول می‌ده.',
    'یعنی یه چرخهٔ عجیبی که همه توش هستن و هیچ‌کس تابلوش نیست.',
    'پس دفعهٔ بعد که گوشی رو باز کردی، یه لحظه فکر کن: کی داره از این یک دقیقه پول درمی‌آره؟',
    'جوابش شاید بیشتر از چیزی باشه که فکرشو می‌کنی.',
]

G2P = 'mehdi-hf/Homo-GE2PE-Persian-HF'
TO_PHONEMES = str.maketrans({'/': 'a', 'a': 'A', '@': '?', '$': 'S', 'c': 'C'})


def ffmpeg():
    import shutil
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def dur_of(path):
    p = subprocess.run([ffmpeg(), '-i', path], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', p.stderr)
    if not m:
        return None
    h, mi, s = m.groups()
    return round(int(h) * 3600 + int(mi) * 60 + float(s), 2)


def trim(x, sr, thresh=0.012, pad=0.06):
    if x.size == 0:
        return x
    env = np.abs(x)
    win = max(1, int(sr * 0.01))
    env = np.convolve(env, np.ones(win) / win, mode='same')
    idx = np.where(env > thresh * env.max())[0]
    if idx.size == 0:
        return x
    a = max(0, idx[0] - int(sr * pad))
    b = min(len(x), idx[-1] + int(sr * pad))
    return x[a:b]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_dir')
    ap.add_argument('--voice', default=os.environ.get('VOICE', 'prompt_hello.wav'))
    ap.add_argument('--tag', default='take')
    ap.add_argument('--temp', type=float, default=0.3)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    tag = args.tag

    t_all = time.time()
    tok = AutoTokenizer.from_pretrained(G2P)
    g2p = T5ForConditionalGeneration.from_pretrained(G2P).eval()

    from pocket_tts import TTSModel
    t_load = time.time()
    model = TTSModel.load_model(config='hf://mehdi-hf/pocket-tts-farsi-v2/model.yaml',
                                temp=args.temp)
    state = model.get_state_for_audio_prompt(args.voice)
    load_s = round(time.time() - t_load, 1)
    sr = int(getattr(model, 'sample_rate', 24000))

    def phonemise(text):
        text = normalize_for_model(text).replace('؟', '').replace('?', '')
        enc = tok([text], add_special_tokens=False, return_tensors='pt')
        with torch.no_grad():
            out = g2p.generate(**enc, num_beams=5, max_length=512, early_stopping=True)
        return tok.batch_decode(out, skip_special_tokens=True)[0].strip() \
            .translate(TO_PHONEMES).replace('1', '')

    pieces, report = [], {'voice': args.voice, 'temp': args.temp, 'sentences': []}
    for i, s in enumerate(SENTENCES, 1):
        t0 = time.time()
        ph = phonemise(s)
        audio = model.generate_audio(state, ph, frames_after_eos=0)
        arr = np.asarray(audio, dtype=np.float32).squeeze()
        t_syn = time.time() - t0
        arr = trim(arr, sr)
        rms = float(np.sqrt(np.mean(arr ** 2)) + 1e-9)
        arr = np.clip(arr * (0.06 / rms), -1.0, 1.0)
        pieces.append(arr)
        pieces.append(np.zeros(int(sr * 0.22), dtype=np.float32))
        report['sentences'].append({'i': i, 'text': s, 'seconds': round(len(arr) / sr, 2),
                                    'build_seconds': round(t_syn, 1)})
        print(f'{i:>2}/{len(SENTENCES)}  {len(arr) / sr:5.2f}s audio  {t_syn:5.1f}s build',
              flush=True)

    raw = np.concatenate(pieces)
    raw_path = os.path.join(args.out_dir, f'{tag}-raw.wav')
    sf.write(raw_path, raw, sr)
    audio_seconds = round(len(raw) / sr, 2)

    out_wav = os.path.join(args.out_dir, f'{tag}.wav')
    out_mp3 = os.path.join(args.out_dir, f'{tag}.mp3')
    chain = ('highpass=f=75,'
             'equalizer=f=210:t=q:w=1.1:g=1.6,'
             'equalizer=f=2400:t=q:w=1.0:g=1.2,'
             'equalizer=f=6800:t=q:w=1.4:g=-1.6,'
             'acompressor=threshold=-19dB:ratio=2.6:attack=8:release=170:makeup=1.6,'
             'loudnorm=I=-16:TP=-1.5:LRA=9,'
             'aresample=48000')
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', raw_path,
                    '-af', chain, '-ac', '1', out_wav], check=True)
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-i', out_wav,
                    '-c:a', 'libmp3lame', '-b:a', '192k', '-ac', '1', out_mp3], check=True)

    total = round(time.time() - t_all, 1)
    report.update({
        'load_seconds': load_s,
        'audio_seconds': audio_seconds,
        'audio_minutes': round(audio_seconds / 60, 2),
        'build_seconds': total,
        'realtime_factor': round(audio_seconds / max(total, 0.1), 2),
        'audio_minutes_per_build_minute': round((audio_seconds / 60) / (max(total, 0.1) / 60), 2),
        'files': {'raw': raw_path, 'wav': out_wav, 'mp3': out_mp3},
        'mastered_seconds': dur_of(out_mp3),
    })
    json.dump(report, open(os.path.join(args.out_dir, f'{tag}-report.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\nصدا: {audio_seconds}s ({audio_seconds / 60:.2f} دقیقه)  "
          f"ساخت: {total}s  نسبت سرعت: {report['realtime_factor']}×")


if __name__ == '__main__':
    main()
