# Pixel Prince

لعبة بكسل صغيرة مستوحاة من أجواء القصور الصحراوية الكلاسيكية. التحريك والرسم يتمان
بواسطة Pillow، بينما يستخدم وضع اللعب نافذة Tkinter القياسية لعرض الإطارات والتقاط
لوحة المفاتيح.

## التشغيل

```bash
python3 -m pip install -r requirements.txt
python3 run_game.py
```

## نسخة تعمل في المتصفح

توجد نسخة Canvas خفيفة للتجربة المباشرة من المتصفح:

https://htmlpreview.github.io/?https://github.com/imadtas525-code/dz-/blob/cursor/pillow-pixel-prince-game-f915/docs/index.html

## التحكم

- الأسهم أو `A/D`: الحركة يميناً ويساراً
- `Space` أو السهم للأعلى: قفز
- `Shift` أو `Z/X`: ضربة سيف
- `R`: إعادة اللعب
- `Esc`: خروج

الهدف هو جمع الجواهر الثلاثة ثم الوصول إلى باب القصر، مع تجنب الأشواك والحراس.

## تصدير أنيميشن GIF باستخدام Pillow

```bash
python3 run_game.py --gif artifacts/pixel_prince.gif --frames 180 --scale 4
```

هذا ينشئ عرضاً متحركاً قصيراً بدون فتح نافذة، مناسباً للبيئات التي لا تحتوي على
واجهة رسومية.

## الاختبارات

```bash
python3 -m unittest discover -s tests
```
