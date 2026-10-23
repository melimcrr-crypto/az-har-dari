#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strong.py — موتورهای سنگین‌تر/طبیعی‌تر برای صدای فارسی

  python3 shared/scripts/tts/strong.py --engine audio8  --out out/audio8
  python3 shared/scripts/tts/strong.py --engine gemini  --out out/gemini    (کلید: GEMINI_API_KEY)
  python3 shared/scripts/tts/strong.py --engine eleven  --out out/eleven    (کلید: ELEVENLABS_API_KEY)
  python3 shared/scripts/tts/strong.py --engine edge    --out out/edge      (خط پایه)

هر موتور همان سه جملهٔ آزمون را می‌سازد.
"""
import argparse
import json
import os
import subprocess
import sys
import time

LINES = {
    'hook': 'اینستاگرام از تو پول نمی‌گیره، ولی از هر ثانیه‌ای که توی فیدت می‌گذرونی پول درمی‌آره.',
    'numbers': 'سال گذشته این شرکت نزدیک به دو میلیارد دلار از تبلیغات درآمد داشت؛ یعنی نود و هشت درصد کل درآمدش.',
    'punch': 'پس چرا وقتی یوتیوب میلیون‌ها بازدید رو مستقیم پول می‌ده، اینستاگرام فقط لایک می‌ده؟',
}


def mp3(src, dst, sr=None):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', src]
    if sr:
        cmd += ['-ar', str(sr)]
    cmd += ['-ac', '1', '-c:a', 'libmp3lame', '-b:a', '128k', dst]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- audio8
def engine_audio8(texts, out):
    import torch
    import soundfile as sf
    from transformers import AutoModel, AutoProcessor
    sys.path.insert(0, 'Audio8-Persian-TTS/src')
    from fa_tools import normalize_fa

    model_id = 'ArminRahimi/Audio8-TTS-Persian'
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_id, trust_remote_code=True,
                                      dtype=torch.float32).eval()
    res = {}
    for key, text in texts.items():
        t0 = time.time()
        inputs = processor(text=[normalize_fa(text)], return_tensors='pt')
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=1024, temperature=0.8,
                                 top_p=0.95, top_k=50, do_sample=True,
                                 return_dict_in_generate=True)
            wav, lengths = model.decode_audio(gen.codes)
        wav_path = os.path.join(out, f'audio8-{key}.wav')
        sf.write(wav_path, wav[0, : int(lengths[0])].float().cpu().numpy(),
                 model.config.codec_sample_rate)
        res[key] = wav_path
        print(f'  audio8 {key}: {time.time() - t0:.1f}s', flush=True)
    return res


# ---------------------------------------------------------------- gemini
def engine_gemini(texts, out):
    import urllib.request
    key = os.environ['GEMINI_API_KEY']
    model = os.environ.get('GEMINI_TTS_MODEL', 'gemini-2.5-pro-preview-tts')
    voice = os.environ.get('GEMINI_TTS_VOICE', 'Charon')
    style = ('مثل یک آدم واقعی که دارد برای یک دوست تعریف می‌کند صحبت کن؛ محاوره‌ای، '
             'گرم و بی‌تکلف. نه لحن گویندهٔ خبر، نه لحن تبلیغاتی. نفس‌گیری طبیعی و '
             'تأکید نامنظم روی کلمه‌های مهم.')
    res = {}
    for name, text in texts.items():
        body = json.dumps({
            'contents': [{'parts': [{'text': f'{style}\n\n{text}'}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}},
            },
        }).encode()
        url = (f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent')
        req = urllib.request.Request(url, data=body, headers={
            'x-goog-api-key': key, 'Content-Type': 'application/json'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        pcm = data['candidates'][0]['content']['parts'][0]['inlineData']['data']
        import base64
        raw = base64.b64decode(pcm)
        wav_path = os.path.join(out, f'gemini-{name}.wav')
        with open(wav_path, 'wb') as f:
            f.write(raw)
        # گوگل ۲۴ کیلوهرتز تک‌کانال خام می‌دهد؛ با ffmpeg بسته‌بندی می‌شود
        pcm_path = os.path.join(out, f'gemini-{name}.pcm')
        os.replace(wav_path, pcm_path)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 's16le', '-ar', '24000',
                        '-ac', '1', '-i', pcm_path, wav_path], check=True)
        os.remove(pcm_path)
        res[name] = wav_path
        print(f'  gemini {name}: {time.time() - t0:.1f}s', flush=True)
    return res


# ---------------------------------------------------------------- elevenlabs
def engine_eleven(texts, out):
    import urllib.request
    key = os.environ['ELEVENLABS_API_KEY']
    voice = os.environ.get('ELEVEN_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')  # Adam
    model = os.environ.get('ELEVEN_MODEL', 'eleven_v3')
    res = {}
    for name, text in texts.items():
        body = json.dumps({'text': text, 'model_id': model,
                           'voice_settings': {'stability': 0.45, 'similarity_boost': 0.8,
                                              'style': 0.25, 'use_speaker_boost': True}}).encode()
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128'
        req = urllib.request.Request(url, data=body, headers={
            'xi-api-key': key, 'Content-Type': 'application/json'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            audio = r.read()
        path = os.path.join(out, f'eleven-{name}.mp3')
        open(path, 'wb').write(audio)
        res[name] = path
        print(f'  eleven {name}: {time.time() - t0:.1f}s', flush=True)
    return res


# ---------------------------------------------------------------- edge (خط پایه)
def engine_edge(texts, out):
    res = {}
    for name, text in texts.items():
        path = os.path.join(out, f'edge-{name}.mp3')
        subprocess.run(['edge-tts', '--voice', 'fa-IR-FaridNeural', '--rate=-4%',
                        '--text', text, '--write-media', path], check=True)
        res[name] = path
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', required=True,
                    choices=['audio8', 'gemini', 'eleven', 'edge'])
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t0 = time.time()
    fn = {'audio8': engine_audio8, 'gemini': engine_gemini,
          'eleven': engine_eleven, 'edge': engine_edge}[args.engine]
    files = fn(LINES, args.out)
    files = {k: v for k, v in files.items() if v}

    total = 0.0
    for key, path in files.items():
        subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', path], capture_output=True)  # warm
    report = {'engine': args.engine, 'build_seconds': round(time.time() - t0, 1), 'files': files}
    json.dump(report, open(os.path.join(args.out, 'report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"{args.engine}: {len(files)}/3 در {report['build_seconds']}s")


if __name__ == '__main__':
    main()
