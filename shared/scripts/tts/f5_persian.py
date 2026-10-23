#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""f5_persian.py — F5-TTS فاین‌تیون فارسی (Apache-2.0)"""
import os
import sys


def main():
    from f5_tts.api import F5TTS
    out_dir = sys.argv[1] if len(sys.argv) > 1 else 'out/f5'
    os.makedirs(out_dir, exist_ok=True)
    ref = os.environ.get('F5_REF', '/tmp/f5fa/ref.wav')
    ref_text = os.environ.get('F5_REF_TEXT', '')
    fa = F5TTS(model='F5TTS_v1_Base', ckpt_file='/tmp/f5fa/model_last.pt',
               vocab_file='/tmp/f5fa/vocab.txt')
    lines = {
        'hook': 'اینستاگرام از تو پول نمی‌گیره، ولی از هر ثانیه‌ای که توی فیدت می‌گذرونی پول درمی‌آره.',
        'numbers': 'سال گذشته این شرکت نزدیک به دو میلیارد دلار از تبلیغات درآمد داشت.',
        'punch': 'پس چرا وقتی یوتیوب میلیون‌ها بازدید رو مستقیم پول می‌ده، اینستاگرام فقط لایک می‌ده؟',
    }
    import soundfile as sf
    for key, text in lines.items():
        wav, sr, _ = fa.infer(ref_file=ref, ref_text=ref_text, gen_text=text,
                              cross_fade_duration=0.15, nfe_step=32)
        path = os.path.join(out_dir, f'f5-{key}.wav')
        sf.write(path, wav, sr)
        print('  wrote', path, flush=True)


if __name__ == '__main__':
    main()
