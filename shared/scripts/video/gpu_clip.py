#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gpu_clip.py — کلیپ کوتاه با Wan روی رانر GPU"""
import os

import torch
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline, WanPipeline
from diffusers.utils import export_to_video, load_image

MODELS = {
    'wan21-1.3b': 'Wan-AI/Wan2.1-T2V-1.3B-Diffusers',
    'wan22-5b': 'Wan-AI/Wan2.2-TI2V-5B-Diffusers',
}

model_key = os.environ.get('MODEL', 'wan21-1.3b')
prompt = os.environ.get('PROMPT', 'slow cinematic push-in, warm light')
image_path = os.environ.get('IMAGE', '').strip()
seconds = int(os.environ.get('SECONDS_IN', '5'))
fps = 16
num_frames = ((seconds * fps) // 4) * 4 + 1
model_id = MODELS[model_key]

os.makedirs('out', exist_ok=True)
dtype = torch.bfloat16

if image_path and os.path.exists(image_path):
    vae = AutoencoderKLWan.from_pretrained(model_id, subfolder='vae',
                                           torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(model_id, vae=vae, torch_dtype=dtype)
    pipe.to('cuda')
    img = load_image(image_path).resize((832, 480))
    frames = pipe(image=img, prompt=prompt, num_frames=num_frames,
                  guidance_scale=5.0, num_inference_steps=30).frames[0]
else:
    pipe = WanPipeline.from_pretrained(model_id, torch_dtype=dtype).to('cuda')
    frames = pipe(prompt=prompt, num_frames=num_frames, height=480, width=832,
                  guidance_scale=5.0, num_inference_steps=30).frames[0]

out = f'out/{model_key}-{seconds}s.mp4'
export_to_video(frames, out, fps=fps)
print('✅', out, os.path.getsize(out) // 1024, 'KB')
