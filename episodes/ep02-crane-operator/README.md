# قسمت ۲ — رانندهٔ جرثقیل برجی: پنج سطح تا بالای برج

۴۸ نما · ۱۱ بخش روایی · **۸:۰۰ دقیقه** · بدون موزیک، بدون متن روی تصویر

## آخرین رندر (سری ۳)
| مورد | مقدار |
|---|---|
| فایل | `ep02-crane-operator.mp4` — ۱۰۰٫۸ مگابایت · ۱۲۸۰×۷۲۰ · ۲۴fps |
| صدا | Gemini `gemini-2.5-flash-preview-tts` · صدای `Charon` · tempo ۱٫۰۳ · −۱۶ LUFS |
| روایت | ۴۷۹٫۶ ثانیه صدا داخل ۴۸۰٫۰ ثانیه ویدیو (اختلاف ۰٫۴s) |
| مکث‌ها | lead ۰٫۳۵s · gap ۱٫۳۱s بین بخش‌ها · tail ۰٫۸s |
| تلفظ | بررسی خودکار با Gemini روی هر ۱۱ بخش: هیچ کلمه‌ای پایین‌تر از آستانه نبود |
| متن | ۵۷۳۸ کاراکتر محاوره‌ای |

## فایل‌ها
| فایل | چیست |
|---|---|
| `episode.json` | مشخصات قسمت، فهرست ۴۸ نما، وزن زمانی هر نما، نگاشت بخش‌های صوتی به نماها |
| `shots/<id>/prompt.txt` | پرامپت تصویر هر نما |
| `shots/<id>/image/<id>.jpg` | تصویر نهایی هر نما (۴۸/۴۸) |
| `audio/script.json` | متن روایت، ۱۱ بخش، لحن محاوره‌ای |
| `audio/pron.json` | واژه‌نامهٔ تلفظ برای TTS |
| `audio/durations.json` | مدت دقیق هر بخش؛ خودکار توسط TTS نوشته می‌شود |
| `timings.json` | شروع و مدت هر نما؛ خودکار ساخته می‌شود |
| `output/ep02-crane-operator.mp4` | خروجی نهایی |

## ساخت (GitHub Actions)
`Actions → Render final → Run workflow`

* پوشه: `episodes/ep02-crane-operator`
* صدا: `Charon` (جایگزین‌ها: Puck، Kore، Fenrir، Aoede)
* مدل: `gemini-2.5-pro-preview-tts`
* کیفیت: `21`

مراحل: بررسی تصاویر → روایت Gemini → بررسی تلفظ با Whisper → زمان‌بندی از صدای واقعی → افکت صدا و میکس → رندر تمیز → انتشار در Releases.

## ساخت (محلی)
```bash
export GEMINI_API_KEY=...
python3 shared/scripts/tts/gemini_ep.py episodes/ep02-crane-operator --voice Charon
python3 shared/scripts/build_timings.py episodes/ep02-crane-operator --target 480
python3 shared/scripts/merge_audio.py episodes/ep02-crane-operator
python3 shared/scripts/prepare_audio_sfx.py episodes/ep02-crane-operator
python3 shared/scripts/render_clean.py episodes/ep02-crane-operator --fps 24
```

## قواعد ثابت این قسمت
* هیچ متنی روی تصویر سوزانده نمی‌شود؛ تیتر، چیپ و کارت پایانی حذف شده‌اند.
* هیچ موزیکی زیر روایت نیست؛ فقط ووش برش نما، کلیک شروع بخش، و ایمپکت ابتدا/انتها.
* زوم آرام متناوب (۱٫۰۴۵) و کراس‌فید ۰٫۴۵ ثانیه؛ هر نما به اندازهٔ جمله‌اش می‌ماند.
* سکوت lead/gap/tail در `timings.json` ذخیره می‌شود و `merge_audio.py` همان را می‌خواند،
  تا صدا و تصویر مو‌به‌مو یکی باشند.
