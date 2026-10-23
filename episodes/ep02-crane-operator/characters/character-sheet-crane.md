# شیت کاراکتر — نسخهٔ رانندهٔ جرثقیل

همان کاراکتر همیشگی «از هر دری»، فقط با لباس کار. برای اینکه ۴۸ نما یک آدم باشند، این شیت را
به هر تولیدکنندهٔ عکس ضمیمه کن.

## مشخصات ثابت (در همهٔ پرامپت‌ها تکرار شده)

| مورد | مقدار |
|---|---|
| سن | ۲۷ |
| هیکل | لاغر و ورزشی، شانه‌های صاف |
| صورت | فک تیز، ته‌ریش طراحی‌شدهٔ کوتاه |
| مو | قهوه‌ای تیرهٔ پرپشت، کویف نرم |
| زیرپوش | تیشرت کرم |
| رویی | پیراهن کار سبز-آبی تیره (`#12545A`) باز |
| جلیقه | نارنجی شب‌نما (`#E9705B`) |
| کلاه | سفید ایمنی — روی سر در کارگاه، در دست در فضای بسته |
| جانبی | زنجیر نقره‌ای نازک، ساعت مچی |
| حالت چهره | گرم، کمی خسته، مطمئن |

## پرامپت شیت کاراکتر (برای تولید عکس)

```text
CHARACTER SHEET — a single reference sheet, 16:9, on a warm cream #F6EEDC paper background.

The same man in five views, full body, standing, evenly lit, no dramatic shadows:
1) front view, arms at his sides
2) three-quarter view, holding a white hard hat under one arm
3) side view, in profile
4) closer chest-up portrait, warm half-smile
5) back view, orange hi-vis vest with a reflective stripe

He is an Iranian man, 27, slim athletic build, sharp jawline, light designer stubble, thick
dark-brown hair in a soft quiff, cream t-shirt under an open dark-teal work shirt, a thin
silver chain, a wristwatch, an orange high-visibility vest and dark work trousers, steel-toe
boots. Do not change his age, hair or face between views — it must read as one person.

Small Persian caption under each view in a bold Persian sans-serif with correct letter
joining: «روبرو» «سه‌رخ» «نیم‌رخ» «پرتره» «پشت». A thin teal rule separates the views.

VISUAL STYLE: detailed editorial illustration for a documentary explainer, soft paper grain,
restrained cel shading, confident linework. Palette: warm cream #F6EEDC, deep teal #12545A,
industrial coral #E9705B, charcoal #2B2F33. No watermark, no logo, no English words,
no gibberish letters.
```

## چطور استفاده کنم

1. این پرامپت را تولید کن → `character_sheet_crane.jpg`
2. آن فایل را در **همهٔ ۴۸ تولید** به‌عنوان تصویر مرجع ضمیمه کن (نماهای ۲۳ و ۲۹ کاراکتر ندارند، ضمیمه لازم نیست)
3. متن `prompt.txt` هر نما را از پوشهٔ `shots/` بردار و عکس را با نام همان پوشه ذخیره کن:
   `shots/05-license-card/image/05-license-card.jpg`
4. بعد: `python3 check_missing.py episodes/ep02-crane-operator`
