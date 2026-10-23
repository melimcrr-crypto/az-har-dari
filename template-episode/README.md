# قالب قسمت تازه

1. `cp -r template-episode episodes/ep02-<slug>`
2. `episode.example.json` را به `episode.json` تغییر نام بده و پر کن.
3. برای هر نما پوشه بساز:
   `shots/NN-slug/{prompt.txt, meta.json, image/}`
4. عکس‌ها را بساز (`check_missing.py --next`) و صدا را در `audio/s01.mp3…` بگذار.
5. `actions → Render episode` با نام پوشهٔ تازه.
