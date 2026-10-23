#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pocket_v2.py — Pocket-TTS-Farsi v2 (غیرتجاری) + فونم‌سازی با Homo-GE2PE"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
import torch
from transformers import AutoTokenizer, T5ForConditionalGeneration

from normalize_fa import normalize_for_model

LINES = {
    'hook': 'اینستاگرام از تو پول نمی‌گیره، ولی از هر ثانیه‌ای که توی فیدت می‌گذرونی پول درمی‌آره.',
    'numbers': 'سال گذشته این شرکت نزدیک به دو میلیارد دلار از تبلیغات درآمد داشت؛ یعنی نود و هشت درصد کل درآمدش.',
    'punch': 'پس چرا وقتی یوتیوب میلیون‌ها بازدید رو مستقیم پول می‌ده، اینستاگرام فقط لایک می‌ده؟',
}

G2P = 'mehdi-hf/Homo-GE2PE-Persian-HF'
TO_PHONEMES = str.maketrans({'/': 'a', 'a': 'A', '@': '?', '$': 'S', 'c': 'C'})

tok = AutoTokenizer.from_pretrained(G2P)
g2p = T5ForConditionalGeneration.from_pretrained(G2P).eval()


def phonemise(text: str) -> str:
    text = normalize_for_model(text)
    text = text.replace('؟', '').replace('?', '')
    enc = tok([text], add_special_tokens=False, return_tensors='pt')
    with torch.no_grad():
        out = g2p.generate(**enc, num_beams=5, max_length=512, early_stopping=True)
    raw = tok.batch_decode(out, skip_special_tokens=True)[0].strip()
    return raw.translate(TO_PHONEMES).replace('1', '')


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else 'out/pocketv2'
    os.makedirs(out_dir, exist_ok=True)
    from pocket_tts import TTSModel
    model = TTSModel.load_model(config='hf://mehdi-hf/pocket-tts-farsi-v2/model.yaml', temp=0.3)
    state = model.get_state_for_audio_prompt(os.environ.get('VOICE', 'prompt_hello.wav'))
    info = {}
    for key, text in LINES.items():
        ph = phonemise(text)
        audio = model.generate_audio(state, ph, frames_after_eos=0)
        arr = np.asarray(audio, dtype=np.float32).squeeze()
        path = os.path.join(out_dir, f'pocketv2-{key}.wav')
        sf.write(path, arr, getattr(model, 'sample_rate', 24000))
        info[key] = path
        print(f'  {key}: {len(arr) / 24000:.1f}s', flush=True)
    json.dump(info, open(os.path.join(out_dir, 'files.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
