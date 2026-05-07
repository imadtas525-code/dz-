"""
Pixel-art sprite & background generator for the Prince of Persia–style game.

Every sprite is hand-drawn here with Pillow (PIL):
  * a tiny "logical" frame is composed from primitives (rectangles, ellipses,
    polygons, lines) on an RGBA canvas,
  * the result is upscaled with NEAREST resampling so the pixels stay crunchy,
  * frames are exported as PNG files and also returned as pygame Surfaces so
    the game can use them directly.

Run this module on its own to (re)generate the assets/ folder:

    python3 sprites.py
"""

from __future__ import annotations

import io
import math
import os
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------------------
# Palette – Persian-inspired colors
# ---------------------------------------------------------------------------

PAL = {
    "transparent": (0, 0, 0, 0),
    "outline":     (24, 16, 32, 255),

    # Prince
    "skin":        (232, 190, 148, 255),
    "skin_dark":   (170, 120, 90, 255),
    "hair":        (40, 25, 20, 255),
    "turban":      (240, 235, 220, 255),
    "turban_sh":   (190, 180, 160, 255),
    "shirt":       (235, 200, 70, 255),   # saffron yellow
    "shirt_sh":    (170, 130, 30, 255),
    "sash":        (190, 40, 50, 255),    # red sash
    "pants":       (245, 240, 225, 255),  # white pants
    "pants_sh":    (180, 170, 150, 255),
    "boots":       (90, 55, 35, 255),
    "boots_sh":    (55, 30, 18, 255),

    # Sword
    "blade":       (220, 225, 235, 255),
    "blade_sh":    (140, 145, 160, 255),
    "hilt":        (210, 170, 60, 255),

    # Guard
    "g_skin":      (200, 160, 130, 255),
    "g_armor":     (90, 95, 110, 255),
    "g_armor_sh":  (55, 60, 75, 255),
    "g_armor_hi":  (140, 145, 160, 255),
    "g_cloth":     (60, 50, 80, 255),
    "g_cloth_sh":  (35, 28, 50, 255),
    "g_helm":      (170, 130, 40, 255),

    # Tiles / world
    "stone_a":     (210, 175, 120, 255),
    "stone_b":     (180, 140, 90, 255),
    "stone_dk":    (120, 85, 50, 255),
    "stone_hi":    (240, 210, 160, 255),
    "wall_a":      (95, 70, 55, 255),
    "wall_b":      (70, 50, 40, 255),
    "wall_hi":     (130, 100, 75, 255),
    "spike":       (210, 215, 225, 255),
    "spike_sh":    (110, 115, 130, 255),
    "potion":      (220, 60, 70, 255),
    "potion_sh":   (140, 30, 40, 255),
    "glass":       (210, 230, 255, 255),
    "door":        (90, 55, 30, 255),
    "door_hi":     (160, 110, 60, 255),
    "door_dk":     (45, 25, 15, 255),
    "gold":        (240, 200, 70, 255),

    # Sky / background
    "sky_top":     (20, 14, 45, 255),
    "sky_mid":     (60, 30, 70, 255),
    "sky_low":     (160, 80, 75, 255),
    "moon":        (250, 240, 210, 255),
    "moon_sh":     (210, 195, 160, 255),
    "palace":      (35, 22, 50, 255),
    "palace_hi":   (60, 40, 80, 255),
    "star":        (250, 240, 200, 255),
    "ground_far":  (50, 30, 40, 255),
}


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

LOGICAL_W, LOGICAL_H = 24, 32      # base resolution for characters
SCALE = 4                          # final pixel size multiplier
TILE_LOGICAL = 16                  # base resolution for tiles
TILE_SCALE = 4
TILE = TILE_LOGICAL * TILE_SCALE   # = 64 px on screen


def new_canvas(w: int = LOGICAL_W, h: int = LOGICAL_H) -> Image.Image:
    return Image.new("RGBA", (w, h), PAL["transparent"])


def upscale(img: Image.Image, scale: int = SCALE) -> Image.Image:
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def outline(img: Image.Image, color=PAL["outline"]) -> Image.Image:
    """Add a 1px outline around every opaque cluster."""
    alpha = img.split()[-1]
    edge = alpha.filter(ImageFilter.MaxFilter(3))
    out = Image.new("RGBA", img.size, color)
    out.putalpha(edge)
    out.paste(img, (0, 0), img)
    return out


def flip_h(img: Image.Image) -> Image.Image:
    return img.transpose(Image.FLIP_LEFT_RIGHT)


# ---------------------------------------------------------------------------
# Prince frames
# ---------------------------------------------------------------------------

def _draw_prince_base(d: ImageDraw.ImageDraw, leg_offset_l: int, leg_offset_r: int,
                      arm_l: Tuple[int, int], arm_r: Tuple[int, int],
                      body_dy: int = 0, head_dy: int = 0,
                      sword: bool = True, sword_angle: float = -25.0,
                      sword_extra: float = 0.0):
    """Compose the prince out of simple shapes. All coords are in logical pixels."""
    cx = 12

    # ----- Legs -----
    ly = 26 + body_dy
    # left leg
    d.rectangle([cx - 4, ly, cx - 1, 30 + leg_offset_l], fill=PAL["pants"])
    d.rectangle([cx - 4, 30 + leg_offset_l, cx - 1, 31 + leg_offset_l],
                fill=PAL["boots"])
    # right leg
    d.rectangle([cx, ly, cx + 3, 30 + leg_offset_r], fill=PAL["pants"])
    d.rectangle([cx, 30 + leg_offset_r, cx + 3, 31 + leg_offset_r],
                fill=PAL["boots"])

    # ----- Torso (yellow shirt) -----
    ty = 18 + body_dy
    d.rectangle([cx - 5, ty, cx + 4, ty + 7], fill=PAL["shirt"])
    # vest shading
    d.rectangle([cx - 5, ty + 5, cx + 4, ty + 7], fill=PAL["shirt_sh"])
    # red sash
    d.rectangle([cx - 5, ty + 7, cx + 4, ty + 8], fill=PAL["sash"])
    d.rectangle([cx - 1, ty + 8, cx, ty + 11], fill=PAL["sash"])  # hanging end

    # ----- Arms -----
    ax1, ay1 = arm_l
    ax2, ay2 = arm_r
    # left (back) arm
    d.line([(cx - 4, ty + 1), (ax1, ay1)], fill=PAL["shirt"], width=2)
    d.rectangle([ax1 - 1, ay1, ax1 + 1, ay1 + 2], fill=PAL["skin"])
    # right (front) arm – holds sword
    d.line([(cx + 3, ty + 1), (ax2, ay2)], fill=PAL["shirt"], width=2)
    d.rectangle([ax2 - 1, ay2, ax2 + 1, ay2 + 2], fill=PAL["skin"])

    # ----- Head -----
    hy = 8 + head_dy
    # neck
    d.rectangle([cx - 1, ty - 2, cx, ty], fill=PAL["skin_dark"])
    # face (rounded square)
    d.rectangle([cx - 3, hy, cx + 3, hy + 6], fill=PAL["skin"])
    d.rectangle([cx - 4, hy + 1, cx + 4, hy + 5], fill=PAL["skin"])
    # hair sideburn / back
    d.rectangle([cx - 4, hy + 4, cx - 3, hy + 6], fill=PAL["hair"])
    d.rectangle([cx + 3, hy + 4, cx + 4, hy + 6], fill=PAL["hair"])
    # eyes
    d.point((cx - 1, hy + 3), fill=PAL["outline"])
    d.point((cx + 2, hy + 3), fill=PAL["outline"])
    # mouth
    d.point((cx + 1, hy + 5), fill=PAL["skin_dark"])

    # ----- Turban -----
    d.rectangle([cx - 4, hy - 3, cx + 4, hy], fill=PAL["turban"])
    d.rectangle([cx - 5, hy - 2, cx + 5, hy], fill=PAL["turban"])
    d.rectangle([cx - 5, hy, cx + 5, hy + 1], fill=PAL["turban_sh"])
    # turban gem / fold
    d.point((cx, hy - 2), fill=PAL["sash"])
    # turban tail
    d.rectangle([cx + 4, hy - 1, cx + 6, hy + 2], fill=PAL["turban"])

    # ----- Sword -----
    if sword:
        sx, sy = ax2, ay2 + 1  # hand position
        ang = math.radians(sword_angle)
        length = 10 + sword_extra
        ex = sx + math.cos(ang) * length
        ey = sy + math.sin(ang) * length
        # blade
        d.line([(sx, sy), (ex, ey)], fill=PAL["blade"], width=2)
        # blade highlight
        ox = math.cos(ang + math.pi / 2) * 0.6
        oy = math.sin(ang + math.pi / 2) * 0.6
        d.line([(sx + ox, sy + oy), (ex + ox, ey + oy)],
               fill=PAL["blade_sh"], width=1)
        # hilt
        d.rectangle([sx - 1, sy - 1, sx + 1, sy + 1], fill=PAL["hilt"])


def make_prince_frames() -> Dict[str, List[Image.Image]]:
    frames: Dict[str, List[Image.Image]] = {
        "idle": [], "run": [], "jump": [], "attack": [], "hit": [],
    }

    # ---- IDLE (4 frames – gentle breathing) ----
    for i in range(4):
        breathe = (0, -1, 0, -1)[i]
        sword_a = -25 + (1 if i % 2 else 0)
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_prince_base(
            d, leg_offset_l=0, leg_offset_r=0,
            arm_l=(7, 22 + breathe), arm_r=(17, 22 + breathe),
            body_dy=breathe, head_dy=breathe, sword_angle=sword_a,
        )
        frames["idle"].append(outline(img))

    # ---- RUN (6 frames) ----
    run_legs = [(-1,  1), ( 0,  0), ( 1, -1), ( 1, -1), ( 0,  0), (-1,  1)]
    run_arms_l = [(6, 21), (7, 22), (8, 23), (8, 23), (7, 22), (6, 21)]
    run_arms_r = [(18, 23), (17, 22), (16, 21), (16, 21), (17, 22), (18, 23)]
    for i in range(6):
        img = new_canvas()
        d = ImageDraw.Draw(img)
        bdy = -1 if i in (1, 4) else 0
        _draw_prince_base(
            d,
            leg_offset_l=run_legs[i][0], leg_offset_r=run_legs[i][1],
            arm_l=run_arms_l[i], arm_r=run_arms_r[i],
            body_dy=bdy, head_dy=bdy,
            sword_angle=-30 + i * 2,
        )
        frames["run"].append(outline(img))

    # ---- JUMP (2 frames: rising / falling) ----
    for i, (la, ra, ang) in enumerate([
        ((6, 19), (18, 19), -55),   # rising, arms up
        ((7, 24), (17, 24),  10),   # falling, arms down
    ]):
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_prince_base(
            d, leg_offset_l=-2 if i == 0 else 1,
            leg_offset_r=-1 if i == 0 else 0,
            arm_l=la, arm_r=ra, body_dy=-1 if i == 0 else 0,
            head_dy=-1 if i == 0 else 0, sword_angle=ang,
        )
        frames["jump"].append(outline(img))

    # ---- ATTACK (4 frames: wind-up, slash mid, slash extend, recover) ----
    attack_specs = [
        ((6, 22), (16, 19), -75, 0),    # wind up – sword raised
        ((6, 22), (19, 19), -35, 2),    # slashing forward
        ((6, 22), (22, 22),  10, 4),    # full extension
        ((6, 22), (18, 22), -10, 1),    # recover
    ]
    for la, ra, ang, extra in attack_specs:
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_prince_base(
            d, leg_offset_l=0, leg_offset_r=-1,
            arm_l=la, arm_r=ra, sword_angle=ang, sword_extra=extra,
        )
        frames["attack"].append(outline(img))

    # ---- HIT (2 frames – knockback) ----
    for i in range(2):
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_prince_base(
            d, leg_offset_l=1, leg_offset_r=0,
            arm_l=(5, 24), arm_r=(19, 20),
            body_dy=1 if i == 0 else 0, head_dy=2 if i == 0 else 1,
            sword_angle=-50 + i * 10,
        )
        # red flash overlay
        flash = Image.new("RGBA", img.size, (255, 60, 60, 90 if i == 0 else 50))
        img.alpha_composite(flash, (0, 0))
        frames["hit"].append(outline(img))

    return frames


# ---------------------------------------------------------------------------
# Guard frames
# ---------------------------------------------------------------------------

def _draw_guard_base(d: ImageDraw.ImageDraw,
                     leg_offset_l: int, leg_offset_r: int,
                     arm_l: Tuple[int, int], arm_r: Tuple[int, int],
                     body_dy: int = 0, sword_angle: float = -10.0,
                     sword_extra: float = 0.0):
    cx = 12
    # legs (dark cloth)
    ly = 26 + body_dy
    d.rectangle([cx - 4, ly, cx - 1, 30 + leg_offset_l], fill=PAL["g_cloth"])
    d.rectangle([cx - 4, 30 + leg_offset_l, cx - 1, 31 + leg_offset_l],
                fill=PAL["boots_sh"])
    d.rectangle([cx, ly, cx + 3, 30 + leg_offset_r], fill=PAL["g_cloth"])
    d.rectangle([cx, 30 + leg_offset_r, cx + 3, 31 + leg_offset_r],
                fill=PAL["boots_sh"])

    # torso – armor
    ty = 17 + body_dy
    d.rectangle([cx - 6, ty, cx + 5, ty + 9], fill=PAL["g_armor"])
    # armor segmenting lines
    d.line([(cx - 6, ty + 3), (cx + 5, ty + 3)], fill=PAL["g_armor_sh"])
    d.line([(cx - 6, ty + 6), (cx + 5, ty + 6)], fill=PAL["g_armor_sh"])
    # shoulder highlights
    d.rectangle([cx - 6, ty, cx - 4, ty + 2], fill=PAL["g_armor_hi"])
    d.rectangle([cx + 3, ty, cx + 5, ty + 2], fill=PAL["g_armor_hi"])
    # belt
    d.rectangle([cx - 6, ty + 9, cx + 5, ty + 10], fill=PAL["g_helm"])

    # arms
    ax1, ay1 = arm_l
    ax2, ay2 = arm_r
    d.line([(cx - 5, ty + 2), (ax1, ay1)], fill=PAL["g_armor"], width=2)
    d.rectangle([ax1 - 1, ay1, ax1 + 1, ay1 + 2], fill=PAL["g_skin"])
    d.line([(cx + 4, ty + 2), (ax2, ay2)], fill=PAL["g_armor"], width=2)
    d.rectangle([ax2 - 1, ay2, ax2 + 1, ay2 + 2], fill=PAL["g_skin"])

    # head
    hy = 8 + body_dy
    d.rectangle([cx - 3, hy, cx + 3, hy + 6], fill=PAL["g_skin"])
    d.rectangle([cx - 4, hy + 1, cx + 4, hy + 5], fill=PAL["g_skin"])
    # beard
    d.rectangle([cx - 3, hy + 4, cx + 3, hy + 6], fill=PAL["hair"])
    d.rectangle([cx - 4, hy + 4, cx + 4, hy + 5], fill=PAL["hair"])
    # eyes
    d.point((cx - 1, hy + 3), fill=PAL["outline"])
    d.point((cx + 2, hy + 3), fill=PAL["outline"])

    # helmet (golden)
    d.rectangle([cx - 4, hy - 2, cx + 4, hy + 1], fill=PAL["g_helm"])
    d.rectangle([cx - 5, hy, cx - 4, hy + 4], fill=PAL["g_helm"])  # cheek guard
    d.rectangle([cx + 4, hy, cx + 5, hy + 4], fill=PAL["g_helm"])
    # spike on top
    d.rectangle([cx - 1, hy - 4, cx, hy - 2], fill=PAL["g_helm"])
    d.point((cx, hy - 5), fill=PAL["gold"])

    # scimitar
    sx, sy = ax2, ay2 + 1
    ang = math.radians(sword_angle)
    length = 11 + sword_extra
    # curved blade approximated by two line segments
    mx = sx + math.cos(ang) * (length * 0.55)
    my = sy + math.sin(ang) * (length * 0.55)
    ex = sx + math.cos(ang - 0.3) * length
    ey = sy + math.sin(ang - 0.3) * length
    d.line([(sx, sy), (mx, my)], fill=PAL["blade"], width=2)
    d.line([(mx, my), (ex, ey)], fill=PAL["blade"], width=2)
    d.rectangle([sx - 1, sy - 1, sx + 1, sy + 1], fill=PAL["g_helm"])


def make_guard_frames() -> Dict[str, List[Image.Image]]:
    frames: Dict[str, List[Image.Image]] = {
        "idle": [], "walk": [], "attack": [], "hit": [],
    }

    for i in range(2):
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_guard_base(d, 0, 0, (6, 23), (18, 23),
                         body_dy=-1 if i else 0)
        frames["idle"].append(outline(img))

    walk_legs = [(-1, 1), (0, 0), (1, -1), (0, 0)]
    for i in range(4):
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_guard_base(
            d, walk_legs[i][0], walk_legs[i][1],
            (6 - (i % 2), 23), (18 + (i % 2), 23),
            body_dy=-1 if i % 2 else 0,
        )
        frames["walk"].append(outline(img))

    for la, ra, ang, extra in [
        ((7, 23), (16, 19), -60, 0),
        ((7, 23), (20, 21), -10, 2),
        ((7, 23), (22, 23),  20, 4),
    ]:
        img = new_canvas()
        d = ImageDraw.Draw(img)
        _draw_guard_base(d, 0, -1, la, ra, sword_angle=ang, sword_extra=extra)
        frames["attack"].append(outline(img))

    img = new_canvas()
    d = ImageDraw.Draw(img)
    _draw_guard_base(d, 1, 0, (5, 24), (20, 21),
                     body_dy=1, sword_angle=30)
    flash = Image.new("RGBA", img.size, (255, 80, 80, 100))
    img.alpha_composite(flash, (0, 0))
    frames["hit"].append(outline(img))

    return frames


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

def make_tile_floor() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL), PAL["stone_b"])
    d = ImageDraw.Draw(img)
    # top "lit" edge
    d.rectangle([0, 0, TILE_LOGICAL - 1, 1], fill=PAL["stone_hi"])
    d.rectangle([0, 2, TILE_LOGICAL - 1, 3], fill=PAL["stone_a"])
    # mortar lines (brick pattern)
    d.line([(0, 7), (TILE_LOGICAL - 1, 7)], fill=PAL["stone_dk"])
    d.line([(0, 12), (TILE_LOGICAL - 1, 12)], fill=PAL["stone_dk"])
    d.line([(5, 4), (5, 7)], fill=PAL["stone_dk"])
    d.line([(11, 8), (11, 12)], fill=PAL["stone_dk"])
    d.line([(3, 13), (3, 15)], fill=PAL["stone_dk"])
    d.line([(9, 13), (9, 15)], fill=PAL["stone_dk"])
    # tiny speckle
    d.point((2, 5), fill=PAL["stone_dk"])
    d.point((13, 10), fill=PAL["stone_dk"])
    d.point((7, 14), fill=PAL["stone_dk"])
    return img


def make_tile_wall() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL), PAL["wall_b"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, TILE_LOGICAL - 1, 1], fill=PAL["wall_hi"])
    d.rectangle([0, 2, TILE_LOGICAL - 1, 4], fill=PAL["wall_a"])
    # bricks
    d.line([(0, 6), (TILE_LOGICAL - 1, 6)], fill=PAL["outline"])
    d.line([(0, 11), (TILE_LOGICAL - 1, 11)], fill=PAL["outline"])
    d.line([(7, 0), (7, 6)], fill=PAL["outline"])
    d.line([(3, 7), (3, 11)], fill=PAL["outline"])
    d.line([(11, 7), (11, 11)], fill=PAL["outline"])
    d.line([(8, 12), (8, 15)], fill=PAL["outline"])
    return img


def make_tile_spikes() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL), PAL["transparent"])
    d = ImageDraw.Draw(img)
    # base
    d.rectangle([0, 12, TILE_LOGICAL - 1, 15], fill=PAL["stone_dk"])
    d.rectangle([0, 12, TILE_LOGICAL - 1, 12], fill=PAL["stone_b"])
    # 4 spikes
    for x in (1, 5, 9, 13):
        d.polygon([(x, 12), (x + 2, 12), (x + 1, 4)], fill=PAL["spike"])
        d.line([(x + 1, 12), (x + 1, 5)], fill=PAL["spike_sh"])
    return img


def make_tile_pillar() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL), PAL["transparent"])
    d = ImageDraw.Draw(img)
    d.rectangle([3, 0, 12, 15], fill=PAL["stone_b"])
    d.rectangle([3, 0, 4, 15], fill=PAL["stone_a"])
    d.rectangle([12, 0, 12, 15], fill=PAL["stone_dk"])
    d.line([(3, 4), (12, 4)], fill=PAL["stone_dk"])
    d.line([(3, 11), (12, 11)], fill=PAL["stone_dk"])
    return img


def make_potion() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL), PAL["transparent"])
    d = ImageDraw.Draw(img)
    # neck
    d.rectangle([7, 3, 9, 5], fill=PAL["glass"])
    d.rectangle([6, 5, 10, 6], fill=PAL["glass"])
    # body
    d.ellipse([4, 6, 12, 14], fill=PAL["potion"])
    # liquid shine
    d.line([(6, 8), (6, 11)], fill=PAL["glass"])
    d.point((7, 7), fill=PAL["glass"])
    # cork
    d.rectangle([7, 1, 9, 3], fill=PAL["boots"])
    return outline(img)


def make_door() -> Image.Image:
    img = Image.new("RGBA", (TILE_LOGICAL, TILE_LOGICAL * 2), PAL["transparent"])
    d = ImageDraw.Draw(img)
    # arched frame
    d.rectangle([1, 6, TILE_LOGICAL - 2, TILE_LOGICAL * 2 - 1], fill=PAL["door"])
    d.ellipse([1, 0, TILE_LOGICAL - 2, 12], fill=PAL["door"])
    # inner darker
    d.rectangle([3, 7, TILE_LOGICAL - 4, TILE_LOGICAL * 2 - 2], fill=PAL["door_dk"])
    d.ellipse([3, 1, TILE_LOGICAL - 4, 11], fill=PAL["door_dk"])
    # planks / handle
    d.line([(8, 8), (8, TILE_LOGICAL * 2 - 3)], fill=PAL["door_hi"])
    d.point((11, 18), fill=PAL["gold"])
    return outline(img)


# ---------------------------------------------------------------------------
# Background (parallax)
# ---------------------------------------------------------------------------

def make_background(width: int, height: int) -> Image.Image:
    img = Image.new("RGBA", (width, height), PAL["sky_top"])
    d = ImageDraw.Draw(img)

    # vertical gradient sky
    for y in range(height):
        t = y / height
        if t < 0.55:
            k = t / 0.55
            c = (
                int(PAL["sky_top"][0] * (1 - k) + PAL["sky_mid"][0] * k),
                int(PAL["sky_top"][1] * (1 - k) + PAL["sky_mid"][1] * k),
                int(PAL["sky_top"][2] * (1 - k) + PAL["sky_mid"][2] * k),
                255,
            )
        else:
            k = (t - 0.55) / 0.45
            c = (
                int(PAL["sky_mid"][0] * (1 - k) + PAL["sky_low"][0] * k),
                int(PAL["sky_mid"][1] * (1 - k) + PAL["sky_low"][1] * k),
                int(PAL["sky_mid"][2] * (1 - k) + PAL["sky_low"][2] * k),
                255,
            )
        d.line([(0, y), (width, y)], fill=c)

    # stars
    import random
    rng = random.Random(7)
    for _ in range(120):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, int(height * 0.55))
        b = rng.randint(180, 255)
        d.point((x, y), fill=(b, b, 200, 255))

    # moon
    mx, my, mr = int(width * 0.78), int(height * 0.18), 38
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=PAL["moon"])
    d.ellipse([mx - mr + 8, my - mr + 4, mx + mr - 16, my + mr - 12],
              fill=PAL["moon_sh"])
    # crater dots
    d.ellipse([mx - 8, my - 4, mx - 2, my + 2], fill=PAL["moon_sh"])
    d.ellipse([mx + 6, my + 8, mx + 12, my + 14], fill=PAL["moon_sh"])

    # palace silhouette
    base_y = int(height * 0.72)
    d.rectangle([0, base_y, width, height], fill=PAL["palace"])
    # walls
    wall_y = base_y - 60
    d.rectangle([60, wall_y, width - 60, base_y], fill=PAL["palace"])
    # towers with onion domes
    tower_xs = [80, 240, 460, 720, 900]
    for tx in tower_xs:
        if tx > width - 40:
            continue
        # tower body
        d.rectangle([tx - 18, wall_y - 80, tx + 18, base_y], fill=PAL["palace"])
        d.rectangle([tx - 18, wall_y - 80, tx - 16, base_y],
                    fill=PAL["palace_hi"])
        # dome
        d.ellipse([tx - 22, wall_y - 120, tx + 22, wall_y - 60],
                  fill=PAL["palace"])
        d.polygon([(tx - 22, wall_y - 90), (tx + 22, wall_y - 90),
                   (tx, wall_y - 130)], fill=PAL["palace"])
        # spire
        d.line([(tx, wall_y - 130), (tx, wall_y - 145)],
               fill=PAL["palace_hi"])
        d.ellipse([tx - 2, wall_y - 148, tx + 2, wall_y - 144],
                  fill=PAL["gold"])
        # windows (lit)
        for wy in (wall_y - 50, wall_y - 25):
            d.rectangle([tx - 3, wy, tx + 3, wy + 6], fill=PAL["gold"])

    # crenellations on the long wall
    for x in range(60, width - 60, 20):
        d.rectangle([x, wall_y - 6, x + 10, wall_y], fill=PAL["palace"])

    # foreground dunes
    d.polygon([(0, height), (0, height - 30),
               (width // 3, height - 60),
               (2 * width // 3, height - 40),
               (width, height - 70), (width, height)],
              fill=PAL["ground_far"])

    return img


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _save(img: Image.Image, path: str, scale: int = SCALE) -> None:
    out = upscale(img, scale)
    out.save(path)


def generate_all(assets_dir: str = "assets") -> Dict[str, object]:
    """Render and save every sprite. Returns a dict describing what was made."""
    os.makedirs(assets_dir, exist_ok=True)
    info: Dict[str, object] = {}

    # ----- Prince -----
    prince = make_prince_frames()
    pdir = os.path.join(assets_dir, "prince")
    os.makedirs(pdir, exist_ok=True)
    for state, frames in prince.items():
        for i, f in enumerate(frames):
            _save(f, os.path.join(pdir, f"{state}_{i}.png"))
            _save(flip_h(f), os.path.join(pdir, f"{state}_{i}_left.png"))
    info["prince_states"] = {k: len(v) for k, v in prince.items()}

    # ----- Guard -----
    guard = make_guard_frames()
    gdir = os.path.join(assets_dir, "guard")
    os.makedirs(gdir, exist_ok=True)
    for state, frames in guard.items():
        for i, f in enumerate(frames):
            _save(f, os.path.join(gdir, f"{state}_{i}.png"))
            _save(flip_h(f), os.path.join(gdir, f"{state}_{i}_left.png"))
    info["guard_states"] = {k: len(v) for k, v in guard.items()}

    # ----- Tiles & props -----
    tdir = os.path.join(assets_dir, "tiles")
    os.makedirs(tdir, exist_ok=True)
    _save(make_tile_floor(),  os.path.join(tdir, "floor.png"),  TILE_SCALE)
    _save(make_tile_wall(),   os.path.join(tdir, "wall.png"),   TILE_SCALE)
    _save(make_tile_spikes(), os.path.join(tdir, "spikes.png"), TILE_SCALE)
    _save(make_tile_pillar(), os.path.join(tdir, "pillar.png"), TILE_SCALE)
    _save(make_potion(),      os.path.join(tdir, "potion.png"), TILE_SCALE)
    _save(make_door(),        os.path.join(tdir, "door.png"),   TILE_SCALE)

    bg = make_background(960, 540)
    bg.save(os.path.join(assets_dir, "background.png"))

    info["tiles"] = ["floor", "wall", "spikes", "pillar", "potion", "door"]
    info["background"] = "background.png"
    return info


# ---------------------------------------------------------------------------
# pygame integration
# ---------------------------------------------------------------------------

def pil_to_surface(img: Image.Image):
    """Convert a PIL RGBA image to a pygame Surface (no file I/O)."""
    import pygame
    data = img.tobytes()
    return pygame.image.fromstring(data, img.size, "RGBA").convert_alpha()


def build_runtime_assets() -> Dict[str, object]:
    """Generate everything as pygame Surfaces ready for the game loop."""
    assets: Dict[str, object] = {"prince": {}, "guard": {}, "tiles": {}}

    prince = make_prince_frames()
    for state, frames in prince.items():
        right = [pil_to_surface(upscale(f)) for f in frames]
        left  = [pil_to_surface(upscale(flip_h(f))) for f in frames]
        assets["prince"][state] = {"right": right, "left": left}

    guard = make_guard_frames()
    for state, frames in guard.items():
        right = [pil_to_surface(upscale(f)) for f in frames]
        left  = [pil_to_surface(upscale(flip_h(f))) for f in frames]
        assets["guard"][state] = {"right": right, "left": left}

    tiles = {
        "floor":  make_tile_floor(),
        "wall":   make_tile_wall(),
        "spikes": make_tile_spikes(),
        "pillar": make_tile_pillar(),
        "potion": make_potion(),
        "door":   make_door(),
    }
    for k, img in tiles.items():
        assets["tiles"][k] = pil_to_surface(upscale(img, TILE_SCALE))

    assets["background"] = pil_to_surface(make_background(960, 540))
    return assets


if __name__ == "__main__":
    info = generate_all()
    print("Generated assets:")
    for k, v in info.items():
        print(f"  {k}: {v}")
