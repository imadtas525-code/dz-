"""
Prince of Persia – لعبة بكسل (a small Prince of Persia–style pixel game).

All visual assets are generated procedurally with Pillow in `sprites.py`.
This file is just the game loop: input, physics, animation playback,
combat, enemy AI, and the win/lose screens.

Controls
--------
    ←  →   : run
    Space  : jump
    F      : sword attack
    R      : restart after a victory or defeat
    Esc    : quit

Goal
----
    Defeat the palace guards (or sneak past them) and reach the wooden
    door on the far right of the chamber.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import pygame

import sprites


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 960, 540
FPS = 60
TILE = sprites.TILE          # 64 px

GRAVITY = 0.55
MOVE_SPEED = 3.4
JUMP_SPEED = -10.5
MAX_FALL = 14.0

PRINCE_HITBOX = pygame.Rect(0, 0, 36, 96)   # tight collision box
GUARD_HITBOX = pygame.Rect(0, 0, 40, 96)
ATTACK_REACH = 70                            # px in front of player
ATTACK_VERT = 90
PLAYER_MAX_HP = 5
GUARD_HP = 2

# Animation timing (ticks per frame)
ANIM_TICKS = {
    "idle":   10,
    "run":    5,
    "jump":   8,
    "attack": 5,
    "hit":    6,
    "walk":   8,
}

# ---------------------------------------------------------------------------
# Level layout
# ---------------------------------------------------------------------------
#  '#' = stone floor / platform
#  '='  = wall block
#  '|'  = pillar (decorative, solid)
#  '^'  = spike hazard (sits on top of a floor row)
#  'P'  = potion pickup
#  'G'  = guard spawn
#  'D'  = exit door (right edge)
#  'S'  = player spawn
#  '.'  = empty
#
# The level is 15 columns x 8 rows  =  960 x 512  with a 28 px ceiling band.

LEVEL = [
    "...............",
    "...............",
    ".......P.......",
    "....###........",
    "...............",
    ".........###...",
    "S.....G.....G.D",
    "###############",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ----- font handling (Latin + Arabic shaping) -----

_LATIN_FONT_CACHE: Dict[int, pygame.font.Font] = {}
_ARABIC_FONT_CACHE: Dict[int, pygame.font.Font] = {}

_ARABIC_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
]

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_ARABIC_SHAPING = True
except Exception:
    _HAS_ARABIC_SHAPING = False


def _has_arabic(s: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in s)


def _latin_font(size: int) -> pygame.font.Font:
    if size not in _LATIN_FONT_CACHE:
        _LATIN_FONT_CACHE[size] = pygame.font.SysFont("dejavusans", size, bold=True)
    return _LATIN_FONT_CACHE[size]


def _arabic_font(size: int) -> pygame.font.Font:
    if size in _ARABIC_FONT_CACHE:
        return _ARABIC_FONT_CACHE[size]
    for p in _ARABIC_PATHS:
        if os.path.exists(p):
            f = pygame.font.Font(p, size)
            _ARABIC_FONT_CACHE[size] = f
            return f
    f = _latin_font(size)
    _ARABIC_FONT_CACHE[size] = f
    return f


def _shape_arabic(s: str) -> str:
    if _HAS_ARABIC_SHAPING:
        return get_display(arabic_reshaper.reshape(s))
    return s


def draw_text(surf, txt, pos, color=(255, 240, 200), size=22, center=False):
    if _has_arabic(txt):
        font = _arabic_font(size)
        txt = _shape_arabic(txt)
    else:
        font = _latin_font(size)
    img = font.render(txt, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Animator:
    sheets: Dict[str, Dict[str, List[pygame.Surface]]]
    state: str = "idle"
    facing: str = "right"
    frame: int = 0
    tick: int = 0

    def set_state(self, s: str, reset: bool = False):
        if s != self.state or reset:
            self.state = s
            self.frame = 0
            self.tick = 0

    def update(self, loop: bool = True) -> bool:
        """Advance the animation. Returns True if a non-looping anim finished."""
        self.tick += 1
        per = ANIM_TICKS.get(self.state, 6)
        finished = False
        if self.tick >= per:
            self.tick = 0
            frames = self.sheets[self.state][self.facing]
            if self.frame + 1 >= len(frames):
                if loop:
                    self.frame = 0
                else:
                    finished = True
            else:
                self.frame += 1
        return finished

    def image(self) -> pygame.Surface:
        frames = self.sheets[self.state][self.facing]
        return frames[min(self.frame, len(frames) - 1)]


class Player:
    def __init__(self, sheets, x: int, y: int):
        self.anim = Animator(sheets)
        self.rect = PRINCE_HITBOX.copy()
        self.rect.midbottom = (x, y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.hp = PLAYER_MAX_HP
        self.attacking = False
        self.attack_done_hit = False
        self.invuln = 0       # ticks
        self.hit_timer = 0
        self.alive = True

    # ---- physics + animation ----
    def update(self, keys, level: "Level"):
        if not self.alive:
            return

        if self.invuln > 0:
            self.invuln -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1

        # ---- horizontal input ----
        if self.hit_timer <= 0 and not self.attacking:
            ax = 0
            if keys[pygame.K_LEFT]:
                ax -= 1
                self.anim.facing = "left"
            if keys[pygame.K_RIGHT]:
                ax += 1
                self.anim.facing = "right"
            self.vx = ax * MOVE_SPEED
        elif self.attacking:
            self.vx *= 0.6  # slight slowdown while swinging

        # ---- gravity ----
        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        # ---- horizontal collision ----
        self.rect.x += int(self.vx)
        for solid in level.solids:
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                elif self.vx < 0:
                    self.rect.left = solid.right
                self.vx = 0

        # ---- vertical collision ----
        self.rect.y += int(self.vy)
        self.on_ground = False
        for solid in level.solids:
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = solid.bottom
                self.vy = 0

        # ---- hazards ----
        for hz in level.hazards:
            if self.rect.colliderect(hz):
                self.take_damage(2, push=-1 if self.anim.facing == "right" else 1)

        # ---- pickups ----
        for p in list(level.potions):
            if self.rect.colliderect(p):
                level.potions.remove(p)
                self.hp = min(PLAYER_MAX_HP, self.hp + 2)

        # keep on screen
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_W:
            self.rect.right = SCREEN_W
        if self.rect.top > SCREEN_H + 200:
            self.alive = False

        # ---- pick animation state ----
        if self.hit_timer > 0:
            self.anim.set_state("hit")
        elif self.attacking:
            self.anim.set_state("attack")
        elif not self.on_ground:
            self.anim.set_state("jump")
            # rising vs falling frame
            self.anim.frame = 0 if self.vy < 0 else 1
            self.anim.tick = 0
        elif abs(self.vx) > 0.1:
            self.anim.set_state("run")
        else:
            self.anim.set_state("idle")

        # ---- advance animation ----
        if self.anim.state == "attack":
            done = self.anim.update(loop=False)
            # at the contact frame (index 2) deal damage once
            if self.anim.frame == 2 and not self.attack_done_hit:
                self._do_attack_hit(level)
                self.attack_done_hit = True
            if done:
                self.attacking = False
                self.attack_done_hit = False
        elif self.anim.state in ("hit",):
            self.anim.update(loop=False)
        elif self.anim.state == "jump":
            pass  # frame chosen manually
        else:
            self.anim.update(loop=True)

    # ---- actions ----
    def jump(self):
        if self.alive and self.on_ground and self.hit_timer <= 0:
            self.vy = JUMP_SPEED
            self.on_ground = False

    def attack(self):
        if self.alive and not self.attacking and self.hit_timer <= 0:
            self.attacking = True
            self.attack_done_hit = False
            self.anim.set_state("attack", reset=True)

    def take_damage(self, dmg: int, push: int = 0):
        if not self.alive or self.invuln > 0:
            return
        self.hp -= dmg
        self.invuln = 50
        self.hit_timer = 18
        self.vx = push * 4
        self.vy = -4
        if self.hp <= 0:
            self.alive = False

    def _do_attack_hit(self, level: "Level"):
        if self.anim.facing == "right":
            zone = pygame.Rect(self.rect.right - 4, self.rect.top + 5,
                               ATTACK_REACH, ATTACK_VERT)
        else:
            zone = pygame.Rect(self.rect.left - ATTACK_REACH + 4,
                               self.rect.top + 5, ATTACK_REACH, ATTACK_VERT)
        for g in level.guards:
            if g.alive and zone.colliderect(g.rect):
                g.take_damage(1, push=1 if self.anim.facing == "right" else -1)

    # ---- draw ----
    def draw(self, surf):
        img = self.anim.image()
        # center sprite on hitbox horizontally; align bottom
        x = self.rect.centerx - img.get_width() // 2
        y = self.rect.bottom - img.get_height()
        # blink while invulnerable
        if self.invuln > 0 and self.invuln // 4 % 2 == 0:
            ghost = img.copy()
            ghost.set_alpha(140)
            surf.blit(ghost, (x, y))
        else:
            surf.blit(img, (x, y))


class Guard:
    def __init__(self, sheets, x: int, y: int, patrol: Tuple[int, int]):
        self.anim = Animator(sheets, state="idle")
        self.rect = GUARD_HITBOX.copy()
        self.rect.midbottom = (x, y)
        self.hp = GUARD_HP
        self.alive = True
        self.vx = 0.0
        self.vy = 0.0
        self.patrol_min, self.patrol_max = patrol
        self.dir = 1
        self.state_timer = 0
        self.attacking = False
        self.attack_done_hit = False
        self.invuln = 0
        self.hit_timer = 0
        self.death_timer = 0

    def take_damage(self, dmg: int, push: int = 0):
        if not self.alive or self.invuln > 0:
            return
        self.hp -= dmg
        self.invuln = 25
        self.hit_timer = 14
        self.vx = push * 3
        self.vy = -3
        if self.hp <= 0:
            self.alive = False
            self.death_timer = 35

    def update(self, level: "Level", player: Player):
        if self.invuln > 0:
            self.invuln -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1

        if not self.alive:
            self.death_timer -= 1
            # falling fade
            self.vy = min(self.vy + GRAVITY, MAX_FALL)
            self.rect.y += int(self.vy)
            for solid in level.solids:
                if self.rect.colliderect(solid) and self.vy > 0:
                    self.rect.bottom = solid.top
                    self.vy = 0
            return

        # ---- AI ----
        dist = player.rect.centerx - self.rect.centerx
        adist = abs(dist)

        if self.hit_timer > 0:
            self.vx *= 0.85
            self.anim.set_state("hit")
        elif self.attacking:
            self.vx = 0
            self.anim.set_state("attack")
        elif adist < 90 and abs(player.rect.centery - self.rect.centery) < 80 and player.alive:
            # face player and attack
            self.anim.facing = "right" if dist >= 0 else "left"
            self.vx = 0
            if self.state_timer <= 0:
                self.attacking = True
                self.attack_done_hit = False
                self.anim.set_state("attack", reset=True)
                self.state_timer = 60
        elif adist < 320 and player.alive:
            # chase
            self.dir = 1 if dist > 0 else -1
            self.vx = self.dir * 1.6
            self.anim.facing = "right" if self.dir > 0 else "left"
            self.anim.set_state("walk")
        else:
            # patrol
            self.vx = self.dir * 1.0
            self.anim.facing = "right" if self.dir > 0 else "left"
            self.anim.set_state("walk")
            if self.rect.right >= self.patrol_max:
                self.dir = -1
            elif self.rect.left <= self.patrol_min:
                self.dir = 1

        if self.state_timer > 0:
            self.state_timer -= 1

        # ---- physics ----
        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        self.rect.x += int(self.vx)
        for solid in level.solids:
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                elif self.vx < 0:
                    self.rect.left = solid.right
                self.dir = -self.dir
                self.vx = 0

        self.rect.y += int(self.vy)
        on_ground = False
        for solid in level.solids:
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    on_ground = True
                elif self.vy < 0:
                    self.rect.top = solid.bottom
                self.vy = 0

        # ---- animation advance & damage frame ----
        if self.anim.state == "attack":
            done = self.anim.update(loop=False)
            if self.anim.frame == 2 and not self.attack_done_hit:
                self._try_hit(player)
                self.attack_done_hit = True
            if done:
                self.attacking = False
        elif self.anim.state == "hit":
            self.anim.update(loop=False)
        else:
            self.anim.update(loop=True)

    def _try_hit(self, player: Player):
        if self.anim.facing == "right":
            zone = pygame.Rect(self.rect.right - 4, self.rect.top + 5,
                               60, ATTACK_VERT)
        else:
            zone = pygame.Rect(self.rect.left - 56, self.rect.top + 5,
                               60, ATTACK_VERT)
        if zone.colliderect(player.rect):
            player.take_damage(1, push=1 if self.anim.facing == "right" else -1)

    def draw(self, surf):
        img = self.anim.image()
        if not self.alive:
            # fade out
            alpha = max(0, int(255 * (self.death_timer / 35)))
            img = img.copy()
            img.set_alpha(alpha)
        elif self.invuln > 0 and self.invuln // 3 % 2 == 0:
            img = img.copy()
            img.set_alpha(160)
        x = self.rect.centerx - img.get_width() // 2
        y = self.rect.bottom - img.get_height()
        surf.blit(img, (x, y))


# ---------------------------------------------------------------------------
# Level
# ---------------------------------------------------------------------------

class Level:
    def __init__(self, layout: List[str], assets):
        self.layout = layout
        self.assets = assets
        self.solids: List[pygame.Rect] = []
        self.hazards: List[pygame.Rect] = []
        self.decor: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        self.potions: List[pygame.Rect] = []
        self.door_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.player_spawn: Tuple[int, int] = (80, SCREEN_H - 80)
        self.guard_spawns: List[Tuple[int, int]] = []
        self._parse(layout)

    def _parse(self, layout: List[str]):
        rows = len(layout)
        cols = len(layout[0])
        # vertical offset so the bottom row sits at the screen bottom
        oy = SCREEN_H - rows * TILE
        floor_tile = self.assets["tiles"]["floor"]
        spike_tile = self.assets["tiles"]["spikes"]
        pillar_tile = self.assets["tiles"]["pillar"]
        potion_tile = self.assets["tiles"]["potion"]
        door_tile = self.assets["tiles"]["door"]

        # cache potion size
        self._potion_img = potion_tile
        self._door_img = door_tile

        for j, row in enumerate(layout):
            for i, ch in enumerate(row):
                x = i * TILE
                y = j * TILE + oy
                if ch == "#":
                    self.solids.append(pygame.Rect(x, y, TILE, TILE))
                    self.decor.append((floor_tile, (x, y)))
                elif ch == "|":
                    self.solids.append(pygame.Rect(x, y, TILE, TILE))
                    self.decor.append((pillar_tile, (x, y)))
                elif ch == "^":
                    self.hazards.append(pygame.Rect(x + 8, y + 24,
                                                    TILE - 16, TILE - 24))
                    self.decor.append((spike_tile, (x, y)))
                elif ch == "P":
                    self.potions.append(pygame.Rect(x + 16, y + 16,
                                                    TILE - 32, TILE - 32))
                elif ch == "S":
                    self.player_spawn = (x + TILE // 2, y + TILE)
                elif ch == "G":
                    self.guard_spawns.append((x + TILE // 2, y + TILE))
                elif ch == "D":
                    dw, dh = door_tile.get_width(), door_tile.get_height()
                    self.door_rect = pygame.Rect(x + (TILE - dw) // 2,
                                                 y + TILE - dh, dw, dh)

    def draw(self, surf):
        for img, pos in self.decor:
            surf.blit(img, pos)
        # door
        surf.blit(self._door_img, self.door_rect.topleft)
        # potions (with gentle bob)
        t = pygame.time.get_ticks() / 250
        for p in self.potions:
            bob = int(3 * (0.5 + 0.5 * pygame.math.Vector2(1, 0).rotate(t * 60).y))
            surf.blit(self._potion_img, (p.x - 16, p.y - 16 + bob))


# ---------------------------------------------------------------------------
# HUD & screens
# ---------------------------------------------------------------------------

def draw_hud(surf, player: Player):
    # health hearts (red squares)
    pad = 18
    for i in range(PLAYER_MAX_HP):
        r = pygame.Rect(pad + i * 26, pad, 22, 22)
        pygame.draw.rect(surf, (40, 0, 0), r.inflate(4, 4), border_radius=4)
        if i < player.hp:
            pygame.draw.rect(surf, (220, 60, 70), r, border_radius=4)
            pygame.draw.rect(surf, (255, 200, 200), r.inflate(-12, -12), border_radius=2)
        else:
            pygame.draw.rect(surf, (60, 25, 25), r, border_radius=4)

    draw_text(surf, "Prince of Persia – DZ Edition",
              (SCREEN_W // 2, 26), color=(250, 220, 130), size=20, center=True)


def screen_message(surf, ar_title: str, en_title: str,
                   ar_sub: str, en_sub: str, color):
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surf.blit(overlay, (0, 0))
    draw_text(surf, ar_title, (SCREEN_W // 2, SCREEN_H // 2 - 70),
              color=color, size=64, center=True)
    draw_text(surf, en_title, (SCREEN_W // 2, SCREEN_H // 2 - 10),
              color=color, size=42, center=True)
    draw_text(surf, ar_sub, (SCREEN_W // 2, SCREEN_H // 2 + 50),
              color=(240, 230, 200), size=26, center=True)
    draw_text(surf, en_sub, (SCREEN_W // 2, SCREEN_H // 2 + 90),
              color=(220, 210, 180), size=22, center=True)
    draw_text(surf, "R = Restart    Esc = Quit",
              (SCREEN_W // 2, SCREEN_H - 40),
              color=(220, 200, 160), size=20, center=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_game():
    pygame.init()
    pygame.display.set_caption("Prince of Persia – Pixel (Pillow)")
    flags = pygame.SCALED
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    clock = pygame.time.Clock()

    assets = sprites.build_runtime_assets()
    bg = assets["background"]

    def new_game():
        lvl = Level(LEVEL, assets)
        player = Player(assets["prince"], *lvl.player_spawn)
        guards = [Guard(assets["guard"], gx, gy,
                        patrol=(max(0, gx - 180), min(SCREEN_W - 20, gx + 180)))
                  for gx, gy in lvl.guard_spawns]
        lvl.guards = guards
        return lvl, player, guards

    level, player, guards = new_game()
    state = "play"   # "play" | "win" | "lose"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_r and state in ("win", "lose"):
                    level, player, guards = new_game()
                    state = "play"
                if state == "play":
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        player.jump()
                    if event.key in (pygame.K_f, pygame.K_x, pygame.K_j):
                        player.attack()

        keys = pygame.key.get_pressed()

        if state == "play":
            player.update(keys, level)
            for g in guards:
                g.update(level, player)

            # win?
            if player.alive and player.rect.colliderect(level.door_rect):
                state = "win"
            # lose?
            if not player.alive:
                state = "lose"

        # ---- draw ----
        screen.blit(bg, (0, 0))
        level.draw(screen)
        for g in guards:
            g.draw(screen)
        player.draw(screen)
        draw_hud(screen, player)

        if state == "win":
            screen_message(screen,
                           "النصر!", "VICTORY",
                           "وصلت إلى بوابة القصر الذهبية",
                           "You reached the palace gate",
                           color=(255, 220, 90))
        elif state == "lose":
            screen_message(screen,
                           "هزيمة!", "DEFEAT",
                           "سقط الأمير... حاول مجدداً",
                           "The prince has fallen - try again",
                           color=(230, 80, 90))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    # Allow running headless (e.g. on a server) for a smoke-test
    if "--headless" in sys.argv:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    run_game()
