# Prince of Persia — لعبة بكسل (Pixel Edition)

<div dir="rtl">

لعبة بكسل صغيرة مستوحاة من **أمير بلاد فارس** (Prince of Persia)،
كل الرسوم (الأمير، الحارس، البلاط الفارسي، القمر، البوابة، الجرعات،
الخلفية…) مرسومة برمجياً باستخدام مكتبة **Pillow (PIL)** ثم يتم تحريكها
داخل **pygame**.

## التشغيل

```bash
pip install -r requirements.txt
python3 game.py
```

عند تشغيل اللعبة لأول مرة، يقوم `sprites.py` بإنشاء كل الأطر دفعة واحدة
ويحوّلها إلى أسطح `pygame`. يمكنك أيضاً توليد ملفات الصور (PNG) إلى
المجلد `assets/` بشكل منفصل عبر:

```bash
python3 sprites.py
```

## التحكم

| المفتاح       | الوظيفة                |
|---------------|------------------------|
| `→` / `←`     | الجري يميناً / يساراً  |
| `Space`       | القفز                  |
| `F`           | ضربة السيف             |
| `R`           | إعادة المحاولة بعد النصر أو الهزيمة |
| `Esc`         | الخروج                 |

## الهدف

- اهزم حُرّاس القصر (ضربتان لكل حارس) أو تجاوزهم بالقفز.
- اقفز بين المنصات والتقط جرعات الصحة الحمراء.
- اوصل إلى **البوابة الذهبية** على يمين القاعة لتحقيق النصر.

## بنية المشروع

```
sprites.py        — مولّد كل البكسلات باستخدام Pillow (شخصيات، بلاط، خلفية)
game.py           — حلقة اللعبة، الفيزياء، القتال، الذكاء الاصطناعي للحراس
assets/           — صور PNG يتم توليدها تلقائياً (اختياري)
requirements.txt  — Pillow + pygame + (arabic_reshaper, python-bidi اختياري)
```

كل إطار لكل حالة (سكون، ركض، قفز، هجوم، إصابة) يُرسم على لوحة منطقية
صغيرة الحجم (24×32 بكسل) ثم يُكبَّر 4× مع `Image.NEAREST` للحفاظ على
المظهر البكسيلي الكلاسيكي، ثم يُقلب أفقياً لإنشاء النسخة المعاكسة.

</div>

---

## English Summary

A small **Prince of Persia–style pixel platformer** where every visual asset
(prince, palace guards, sandstone tiles, spikes, potions, the moonlit
Persian palace background, the wooden gate…) is **drawn procedurally with
Pillow** and then animated in **pygame**.

### Run

```bash
pip install -r requirements.txt
python3 game.py
```

To regenerate all sprite PNGs into `assets/` independently:

```bash
python3 sprites.py
```

### Controls

| Key           | Action                |
|---------------|-----------------------|
| `←` / `→`     | Run left / right      |
| `Space`       | Jump                  |
| `F`           | Sword attack          |
| `R`           | Restart after a win or loss |
| `Esc`         | Quit                  |

### How the Pillow animation works

`sprites.py` defines each frame as a tiny composition of geometric
primitives drawn with `PIL.ImageDraw` on a 24×32 RGBA canvas:

- legs offset per frame for a 6-frame run cycle,
- arms re-positioned and the sword line rotated for a 4-frame attack,
- a 1-pixel outline is added by max-filtering the alpha channel,
- frames are upscaled 4× with `Image.NEAREST` so pixels stay crisp,
- finally each frame is converted to a `pygame.Surface` via
  `pygame.image.fromstring` so the game loop can blit them at 60 FPS.

The same approach builds the tiles, the parallax palace background
(gradient sky → stars → moon with shading → silhouetted onion-domed
towers → foreground dunes), and the props (potions, door, spikes).

### Project layout

```
sprites.py        Pillow-based pixel-art generator
game.py           pygame loop: physics, animation, combat, AI
assets/           Generated PNGs (created on demand)
requirements.txt  Pillow + pygame + (optional Arabic shaping libs)
```
