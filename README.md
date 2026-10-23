# از هر دری — ریپوی تولید

کانال یوتیوب فارسی «از هر دری»: هر قسمت یک سؤال، یک جواب روشن، ۸ تا ۱۲ دقیقه.

این ریپو کل تولید را نگه می‌دارد: پرامپت و عکس هر نما، متن و صدای روایت، موزیک، و رندر خودکار روی سرورهای گیت‌هاب.

## وضعیت قسمت‌ها

| # | قسمت | نما | عکس | صدا | ویدیو |
|---|---|---|---|---|---|
| ۱ | اینستاگرام چطور پول درمی‌آورد؟ | ۴۸ | ✅ ۴۸/۴۸ | ✅ | آماده (Release) |
| ۲ | رانندهٔ جرثقیل — پنج سطح | ۴۸ | ⬜ ۰/۴۸ | متن آماده | — |

## ساختار

```
episodes/
  ep01-instagram-money/
    episode.json          فهرست نماها + بخش‌های صوتی + تنظیمات رندر
    shots/NN-slug/
      prompt.txt          پرامپت تصویر (شامل متن فارسی داخل عکس و حالت کاراکتر)
      meta.json           شماره، مدت، کاراکتر دارد یا نه
      image/NN-slug.jpg   عکس نهایی
    audio/
      s01.mp3 … s11.mp3   بخش‌های روایت (منبع)
      script.json         متن کامل روایت
      pron.json           واژه‌نامهٔ تلفظ
shared/
  brand/character_sheet.jpg   شیت کاراکتر — مرجع همهٔ نماهای کاراکتری
  music/curiosity.mp3         موزیک (Mixkit، تجاری آزاد، بدون اعتباردهی)
  fonts/Vazirmatn-*.ttf       فونت فارسی برای متن‌های روی ویدیو
  scripts/                    build_timings · prepare_audio · merge_audio · render · check_missing · lint_images
.github/workflows/
  render.yml            رندر دستی با تعیین قسمت → آرتیفکت + Release
  validate.yml          با هر push: وضعیت نماها و بررسی قواعد تصویر
```

## ساخت ویدیو (روی سرور گیت‌هاب)

Actions → **Render episode** → Run workflow:

| ورودی | مقدار |
|---|---|
| `episode` | `ep01-instagram-money` |
| `crf` | `20` (۱۸ تا ۲۳) |
| `release` | `true` |

خروجی: آرتیفکت ۱۴ روزه + فایل MP4 روی Releases با تگ `ep01-…-v<شماره>`.

معادل محلی:
```bash
python shared/scripts/build_timings.py episodes/ep01-instagram-money
python shared/scripts/prepare_audio.py episodes/ep01-instagram-money
python shared/scripts/render.py        episodes/ep01-instagram-money --crf 20
```

## افزودن قسمت تازه

```bash
cp -r template-episode episodes/ep02-<slug>
# episode.json را پر کن: shots[]، segments[]، audio، عنوان
python shared/scripts/check_missing.py episodes/ep02-<slug> --next   # دستهٔ ۱۰ تایی پرامپت
```

## تولید عکس با چند اکانت

`WORKER_PROMPT.md` را به اکانت‌های دیگر Arena بده. هر اکانت:
1. `python shared/scripts/check_missing.py episodes/<ep>` → می‌فهمد چه مانده
2. `--next` → ۱۰ نمای بعدی
3. می‌سازد، در `shots/<id>/image/` می‌گذارد، push می‌کند، **متوقف می‌شود**
4. کاربر «ادامه» می‌گوید → ۱۰ تای بعدی

## قاعده‌های ثابت

- کاراکتر در ۴۵ نما از ۴۸ نما حاضر است (فقط سه اینفوگرافیک خالی‌اند).
- متن داخل عکس: ۱ تا ۴ کلمهٔ فارسی + یک عدد. جمله‌های بلند و منبع را رندر روی ویدیو می‌گذارد.
- پالت: کرم `#F6EEDC` · سبز-آبی `#12545A` · مرجانی `#E9705B` · ذغالی `#2B2F33`
- هیچ کلمهٔ انگلیسی روی تصویر، بدون لوگو و واترمارک.
- ویدیوها در گیت ذخیره نمی‌شوند؛ فقط در Releases/Artifacts.
