import pygame
import sys
import random
from PIL import Image

pygame.init()

# ----------------------------------
# حجم النافذة
# ----------------------------------

WIDTH = 1000
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("My Pixel Game")

clock = pygame.time.Clock()

# ----------------------------------
# الألوان
# ----------------------------------

YELLOW = (255, 220, 0)

# ----------------------------------
# اللاعب
# ----------------------------------

player_screen_x = 5

world_x = 100

player_width = 300
player_height = 200

facing_right = True

# ----------------------------------
# تحميل الخلفية
# ----------------------------------

background_image = pygame.image.load(
    "c:/Users/عماد الدين/Desktop/assets/background.png"
).convert()

# ----------------------------------
# فريمات المشي
# ----------------------------------

run_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_5.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_6.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/run_7.png"
    ).convert_alpha()
]

# ----------------------------------
# فريمات الهجوم
# ----------------------------------

attack_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_5.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_6.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_7.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/attack_8.png"
    ).convert_alpha()
]

# ----------------------------------
# فريمات القفز
# ----------------------------------

jump_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/jump_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/jump_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/jump_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/jump_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/jump_5.png"
    ).convert_alpha()
]

# ----------------------------------
# فريمات الضربة
# ----------------------------------

hurt_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_5.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/hurt_6.png"
    ).convert_alpha()
]

# ----------------------------------
# فريمات الموت
# ----------------------------------

death_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/death_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/death_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/death_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/death_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/death_5.png"
    ).convert_alpha()
]

# ----------------------------------
# فريمات مشي العدو
# ----------------------------------
# 6 صور للأنيميشن. لو غيّرت أسماء الملفات، عدّلها هنا فقط.

enemy_width = 80
enemy_height = 80

enemy_walk_frames = [

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_1.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_2.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_3.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_4.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_5.png"
    ).convert_alpha(),

    pygame.image.load(
        "c:/Users/عماد الدين/Desktop/assets/enemy_walk_6.png"
    ).convert_alpha()
]

# هل الصور الأصلية ينظر العدو فيها لليمين؟
# - True  : لو الرسمة الأصلية وجهها لليمين  (سنعكسها لما يمشي يساراً)
# - False : لو الرسمة الأصلية وجهها لليسار (سنعكسها لما يمشي يميناً)
# غيّر القيمة هذه فقط لو لقيت العدو يمشي بالعكس.

enemy_image_faces_right = False

# تكبير فريمات العدو لحجم enemy_width × enemy_height
for i in range(len(enemy_walk_frames)):

    enemy_walk_frames[i] = pygame.transform.scale(
        enemy_walk_frames[i],
        (enemy_width, enemy_height)
    )

# ----------------------------------
# تكبير الصور
# ----------------------------------

for i in range(len(run_frames)):

    run_frames[i] = pygame.transform.scale(
        run_frames[i],
        (player_width, player_height)
    )

for i in range(len(attack_frames)):

    attack_frames[i] = pygame.transform.scale(
        attack_frames[i],
        (player_width, player_height)
    )

for i in range(len(jump_frames)):

    jump_frames[i] = pygame.transform.scale(
        jump_frames[i],
        (player_width, player_height)
    )

for i in range(len(hurt_frames)):

    hurt_frames[i] = pygame.transform.scale(
        hurt_frames[i],
        (player_width, player_height)
    )

for i in range(len(death_frames)):

    death_frames[i] = pygame.transform.scale(
        death_frames[i],
        (player_width, player_height)
    )

# ----------------------------------
# Idle Animation
# ----------------------------------

idle_frames = []

idle_image = Image.open(
    "c:/Users/عماد الدين/Desktop/assets/idle.png"
).convert("RGBA")

for i in range(8):

    scale = 1 + (0.03 * (-1) ** i)

    new_width = int(idle_image.width * scale)

    new_height = int(idle_image.height * scale)

    resized = idle_image.resize(
        (new_width, new_height)
    )

    temp_path = f"temp_idle_{i}.png"

    resized.save(temp_path)

    frame = pygame.image.load(
        temp_path
    ).convert_alpha()

    frame = pygame.transform.scale(
        frame,
        (player_width, player_height)
    )

    idle_frames.append(frame)

# ----------------------------------
# الأنيميشن
# ----------------------------------

current_frame = 0
animation_speed = 0.15

attacking = False
attack_frame = 0
attack_speed = 0.25

hurt = False
hurt_frame = 0
hurt_speed = 0.20

dead = False
death_frame = 0
death_speed = 0.15

player_health = 3

# ----------------------------------
# الأرضية
# ----------------------------------

ground_height = 50

player_y = HEIGHT - ground_height - player_height

# ----------------------------------
# الحركة
# ----------------------------------

player_speed = 5

gravity = 0.5
velocity_y = 0

jump_power = -12

# ----------------------------------
# الأعداء
# ----------------------------------
# بدل ما نخزن مستطيل فقط، صرنا نخزن قاموس (dict) لكل عدو
# يحتوي على:
#   - rect       : المستطيل اللي نرسمه و نتصادم معه
#   - direction  : اتجاه الحركة (-1 يعني يمشي لليسار، +1 يعني يمشي لليمين)
#   - speed      : سرعة العدو
#   - start_x    : نقطة البداية، نستخدمها لحساب حدود الدورية (patrol)
#   - patrol_range : كم بكسل يبتعد العدو عن نقطة بدايته قبل ما يرجع

enemies = []

last_enemy_x = 800

enemy_speed = 2          # سرعة المربع الأصفر
enemy_patrol_range = 200 # المسافة اللي يقطعها العدو قبل ما يستدير و يرجع

# ----------------------------------
# الكاميرا
# ----------------------------------

camera_x = 0

# ----------------------------------
# هل اللاعب على الأرض؟
# ----------------------------------

on_ground = True

running = True

# ==================================
# LOOP
# ==================================

while running:

    # ----------------------------------
    # إغلاق اللعبة
    # ----------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

    # ----------------------------------
    # لوحة المفاتيح
    # ----------------------------------

    keys = pygame.key.get_pressed()

    moving = False

    # ----------------------------------
    # الحركة يمين ويسار
    # ----------------------------------

    if not hurt and not dead:

        if keys[pygame.K_RIGHT]:

            world_x += player_speed

            current_frame += animation_speed

            moving = True

            facing_right = True

        if keys[pygame.K_LEFT]:

            world_x -= player_speed

            current_frame += animation_speed

            moving = True

            facing_right = False

    # ----------------------------------
    # الوقوف
    # ----------------------------------

    if not moving:

        current_frame += 0.05

    # ----------------------------------
    # إعادة الفريمات
    # ----------------------------------

    if moving:

        if current_frame >= len(run_frames):

            current_frame = 0

    else:

        if current_frame >= len(idle_frames):

            current_frame = 0

    # ----------------------------------
    # الهجوم
    # ----------------------------------

    if keys[pygame.K_f] and not attacking and not hurt and not dead:

        attacking = True

        attack_frame = 0

    if attacking:

        attack_frame += attack_speed

        if attack_frame >= len(attack_frames):

            attack_frame = 0

            attacking = False

    # ----------------------------------
    # أنيميشن الضربة
    # ----------------------------------

    if hurt:

        hurt_frame += hurt_speed

        if hurt_frame >= len(hurt_frames):

            hurt_frame = 0

            hurt = False

    # ----------------------------------
    # أنيميشن الموت
    # ----------------------------------

    if dead:

        death_frame += death_speed

        if death_frame >= len(death_frames):

            death_frame = len(death_frames) - 1

    # ----------------------------------
    # منع الخروج
    # ----------------------------------

    if world_x < 0:

        world_x = 0

    # ----------------------------------
    # الكاميرا
    # ----------------------------------

    camera_x = world_x - player_screen_x

    # ----------------------------------
    # القفز
    # ----------------------------------

    if keys[pygame.K_SPACE] and on_ground and not hurt and not dead:

        velocity_y = jump_power

        on_ground = False

    # ----------------------------------
    # الجاذبية
    # ----------------------------------

    velocity_y += gravity

    player_y += velocity_y

    # ----------------------------------
    # اللاعب الحقيقي
    # ----------------------------------

    player = pygame.Rect(
        world_x,
        player_y,
        player_width,
        player_height
    )

    # ----------------------------------
    # الأرض
    # ----------------------------------

    ground_y = HEIGHT - ground_height

    if player_y + player_height >= ground_y:

        player_y = ground_y - player_height

        velocity_y = 0

        on_ground = True

    # ----------------------------------
    # إنشاء أعداء
    # ----------------------------------
    # كل عدو الآن قاموس فيه كل المعلومات اللي يحتاجها للحركة الدورية

    if world_x > last_enemy_x - 1000:

        random_distance = random.randint(800, 1400)

        new_enemy_x = last_enemy_x + random_distance

        enemy = {
            "rect": pygame.Rect(
                new_enemy_x,
                HEIGHT - ground_height - enemy_height,
                enemy_width,
                enemy_height
            ),
            "direction": -1,                    # يبدأ بالمشي لليسار (باتجاه اللاعب)
            "speed": enemy_speed,
            "start_x": new_enemy_x,             # نقطة البداية (مرجع للدورية)
            "patrol_range": enemy_patrol_range, # نصف المسافة اللي يتحرك فيها يميناً ويساراً
            "frame": 0,                         # رقم الفريم الحالي للأنيميشن
            "frame_speed": 0.15                 # سرعة تقدّم الفريمات (كلما زادت = أسرع)
        }

        enemies.append(enemy)

        last_enemy_x = new_enemy_x

    # ----------------------------------
    # تحريك الأعداء (المشي ذهاباً وإياباً)
    # ----------------------------------
    # هنا الجزء الجديد المهم:
    # نزيد قيمة x بمقدار direction * speed، فإذا كان direction = -1 يتحرك لليسار،
    # وإذا كان +1 يتحرك لليمين.
    # ثم نتحقق هل وصل إلى الحد الأيسر أو الحد الأيمن للدورية،
    # وإذا وصل، نقلب الاتجاه ليرجع في الاتجاه الآخر.

    for enemy in enemies:

        # تحريك العدو حسب اتجاهه الحالي
        enemy["rect"].x += enemy["direction"] * enemy["speed"]

        # تقدّم فريم الأنيميشن، ثم لفّه إلى البداية إذا انتهت الفريمات
        enemy["frame"] += enemy["frame_speed"]
        if enemy["frame"] >= len(enemy_walk_frames):
            enemy["frame"] = 0

        # حساب الحدود اليمنى واليسرى للدورية حول نقطة البداية
        left_limit = enemy["start_x"] - enemy["patrol_range"]
        right_limit = enemy["start_x"] + enemy["patrol_range"]

        # إذا وصل لأقصى اليسار -> يصبح اتجاهه يميناً (يرجع)
        if enemy["rect"].x <= left_limit:

            enemy["rect"].x = left_limit
            enemy["direction"] = 1

        # إذا وصل لأقصى اليمين -> يصبح اتجاهه يساراً (يرجع باتجاه اللاعب من جديد)
        elif enemy["rect"].x >= right_limit:

            enemy["rect"].x = right_limit
            enemy["direction"] = -1

    # ----------------------------------
    # حذف الأعداء القدامى
    # ----------------------------------
    # لاحظ أنه الآن نفحص enemy["rect"].x بدل enemy.x لأن العدو صار قاموس

    enemies = [

        enemy for enemy in enemies

        if enemy["rect"].x > camera_x - 500
    ]

    # ----------------------------------
    # التصادم مع الأعداء
    # ----------------------------------

    for enemy in enemies[:]:

        # نسحب المستطيل من القاموس عشان نسهّل الكود
        enemy_rect = enemy["rect"]

        attack_rect = pygame.Rect(
            player.x,
            player.y,
            player.width,
            player.height
        )

        # ----------------------------------
        # الهجوم
        # ----------------------------------

        if attacking:

            if facing_right:

                attack_rect.width += 80

            else:

                attack_rect.x -= 80

                attack_rect.width += 80

            if attack_rect.colliderect(enemy_rect):

                enemies.remove(enemy)

                print("Enemy Killed")

        # ----------------------------------
        # ضربة العدو
        # ----------------------------------

        elif player.colliderect(enemy_rect) and not hurt and not dead:

            hurt = True

            hurt_frame = 0

            player_health -= 1

            # دفع للخلف

            if facing_right:

                world_x -= 80

            else:

                world_x += 80

            # دفع للأعلى

            velocity_y = -5

            print("Health:", player_health)

            # الموت

            if player_health <= 0:

                dead = True

                death_frame = 0

    # ----------------------------------
    # رسم الخلفية
    # ----------------------------------

    background_width = background_image.get_width()

    for x in range(
        -background_width,
        100000,
        background_width
    ):

        screen.blit(
            background_image,
            (
                x - camera_x * 0.3,
                0
            )
        )

    # ----------------------------------
    # الأرضية
    # ----------------------------------

    ground_surface = pygame.Surface(
        (100000, ground_height),
        pygame.SRCALPHA
    )

    ground_surface.fill(
        (120, 70, 20, 120)
    )

    screen.blit(
        ground_surface,
        (
            -camera_x,
            ground_y
        )
    )

    # ----------------------------------
    # رسم الأعداء (بالأنيميشن)
    # ----------------------------------
    # 1) نختار الفريم الحالي حسب enemy["frame"].
    # 2) نقرر هل نعكسه أفقياً اعتماداً على اتجاه العدو واتجاه الصورة الأصلية.
    #    - direction = -1 يعني يمشي يساراً.
    #    - direction = +1 يعني يمشي يميناً.
    # 3) نرسمه عند موقع enemy["rect"] مع طرح camera_x.

    for enemy in enemies:

        enemy_rect = enemy["rect"]

        enemy_image = enemy_walk_frames[int(enemy["frame"])]

        # هل يجب عكس الصورة؟
        # لو الصورة الأصلية وجهها لليمين  وكان يمشي يساراً  -> اعكس.
        # لو الصورة الأصلية وجهها لليسار وكان يمشي يميناً  -> اعكس.
        if enemy_image_faces_right and enemy["direction"] == -1:
            enemy_image = pygame.transform.flip(enemy_image, True, False)
        elif (not enemy_image_faces_right) and enemy["direction"] == 1:
            enemy_image = pygame.transform.flip(enemy_image, True, False)

        screen.blit(
            enemy_image,
            (
                enemy_rect.x - camera_x,
                enemy_rect.y
            )
        )

    # ----------------------------------
    # اختيار الفريم الحالي
    # ----------------------------------

    if dead:

        current_image = death_frames[int(death_frame)]

    elif hurt:

        current_image = hurt_frames[int(hurt_frame)]

    elif not on_ground:

        if velocity_y < -6:

            current_image = jump_frames[0]

        elif velocity_y < 0:

            current_image = jump_frames[1]

        elif velocity_y < 4:

            current_image = jump_frames[2]

        elif velocity_y < 8:

            current_image = jump_frames[3]

        else:

            current_image = jump_frames[4]

    elif attacking:

        current_image = attack_frames[int(attack_frame)]

    elif moving:

        current_image = run_frames[int(current_frame)]

    else:

        current_image = idle_frames[int(current_frame)]

    # ----------------------------------
    # اتجاه الصور الأصلية
    # ----------------------------------

    if attacking or hurt or dead or not on_ground:

        image_faces_right = False

    else:

        image_faces_right = True

    # ----------------------------------
    # عكس الصورة
    # ----------------------------------

    if image_faces_right:

        if not facing_right:

            current_image = pygame.transform.flip(
                current_image,
                True,
                False
            )

    else:

        if facing_right:

            current_image = pygame.transform.flip(
                current_image,
                True,
                False
            )

    # ----------------------------------
    # رسم الشخصية
    # ----------------------------------

    screen.blit(

        current_image,

        (
            player_screen_x,
            player_y
        )
    )

    # ----------------------------------
    # تحديث الشاشة
    # ----------------------------------

    pygame.display.update()

    clock.tick(60)

pygame.quit()

sys.exit()
