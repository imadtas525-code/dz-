#!/usr/bin/env python3
"""A tiny Prince-inspired pixel platformer animated with Pillow.

All sprites are generated at runtime with Pillow, then displayed in a Tkinter
window through ImageTk. No external artwork is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk


TILE = 16
LEVEL_WIDTH = 20
LEVEL_HEIGHT = 12
SCREEN_SIZE = (LEVEL_WIDTH * TILE, LEVEL_HEIGHT * TILE)
SCALE = 3

try:
    RESAMPLE_NEAREST = Image.Resampling.NEAREST
except AttributeError:  # pragma: no cover - Pillow < 9 compatibility
    RESAMPLE_NEAREST = Image.NEAREST


LEVEL = [
    "....................",
    "....................",
    ".............J......",
    "............###.....",
    "....................",
    "..P.................",
    "#####....####.......",
    "....................",
    "......####.......D..",
    "................###.",
    "..G............^....",
    "####################",
]


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h


@dataclass
class Entity:
    x: float
    y: float
    w: float
    h: float
    vx: float = 0.0
    vy: float = 0.0
    facing: int = 1
    on_ground: bool = False
    active: bool = True

    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.w, self.h)


def intersects(a: Rect, b: Rect) -> bool:
    return a.left < b.right and a.right > b.left and a.top < b.bottom and a.bottom > b.top


class GameWorld:
    """Holds deterministic game state and collision logic."""

    def __init__(self, level: Optional[List[str]] = None) -> None:
        self.level = level or LEVEL
        self.solid_tiles: Set[Tuple[int, int]] = set()
        self.spikes: List[Rect] = []
        self.player_start = (TILE * 2 + 3, TILE * 5 + 2)
        self.guard_start = (TILE * 2 + 3, TILE * 10 + 2)
        self.door = Rect(TILE * 17 + 2, TILE * 8, 12, 16)
        self.gem = Rect(TILE * 13 + 4, TILE * 2 + 4, 8, 8)
        self._parse_level()
        self.reset()

    def _parse_level(self) -> None:
        if any(len(row) != LEVEL_WIDTH for row in self.level):
            raise ValueError("Every level row must be exactly 20 tiles wide.")
        if len(self.level) != LEVEL_HEIGHT:
            raise ValueError("The level must be exactly 12 tiles tall.")

        for ty, row in enumerate(self.level):
            for tx, marker in enumerate(row):
                px = tx * TILE
                py = ty * TILE
                if marker == "#":
                    self.solid_tiles.add((tx, ty))
                elif marker == "^":
                    self.spikes.append(Rect(px + 2, py + 6, TILE - 4, TILE - 6))
                elif marker == "P":
                    self.player_start = (px + 3, py + 2)
                elif marker == "G":
                    self.guard_start = (px + 3, py + 2)
                elif marker == "D":
                    self.door = Rect(px + 2, py, 12, 16)
                elif marker == "J":
                    self.gem = Rect(px + 4, py + 4, 8, 8)

    def reset(self) -> None:
        self.player = Entity(*self.player_start, w=10, h=14)
        self.guard = Entity(*self.guard_start, w=10, h=14, vx=0.7, facing=1)
        self.tick = 0
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.gem_collected = False
        self.state = "playing"
        self.message = "Find the jewel, defeat the guard, and reach the door."

    def update(self, keys: Set[str]) -> None:
        if "r" in keys:
            self.reset()
            return

        self.tick += 1
        if self.state != "playing":
            return

        self._update_player(keys)
        self._update_guard()
        self._handle_objectives()

    def _update_player(self, keys: Set[str]) -> None:
        player = self.player
        move_left = "left" in keys or "a" in keys
        move_right = "right" in keys or "d" in keys
        wants_jump = "up" in keys or "w" in keys

        player.vx = 0.0
        if move_left:
            player.vx = -2.0
            player.facing = -1
        if move_right:
            player.vx = 2.0
            player.facing = 1

        if wants_jump and player.on_ground:
            player.vy = -5.4
            player.on_ground = False

        if "space" in keys and self.attack_cooldown <= 0:
            self.attack_timer = 12
            self.attack_cooldown = 22

        self.attack_timer = max(0, self.attack_timer - 1)
        self.attack_cooldown = max(0, self.attack_cooldown - 1)

        player.vy = min(player.vy + 0.28, 5.2)
        self._move_with_collision(player, player.vx, 0)
        self._move_with_collision(player, 0, player.vy)

        if player.y > SCREEN_SIZE[1]:
            self._lose("The prince fell into the dungeon.")

        for spike in self.spikes:
            if intersects(player.rect(), spike):
                self._lose("Spikes caught the prince. Press R to retry.")

    def _update_guard(self) -> None:
        guard = self.guard
        if not guard.active:
            return

        guard.vx = 0.7 * guard.facing
        guard.vy = min(guard.vy + 0.28, 4.0)
        old_x = guard.x
        self._move_with_collision(guard, guard.vx, 0)
        self._move_with_collision(guard, 0, guard.vy)

        hit_wall = abs(guard.x - old_x) < 0.01
        ahead_x = guard.x + (guard.w + 2 if guard.facing > 0 else -2)
        foot_y = guard.y + guard.h + 2
        no_floor_ahead = not self._solid_at_pixel(ahead_x, foot_y)
        if hit_wall or no_floor_ahead:
            guard.facing *= -1

        if intersects(self.player.rect(), guard.rect()):
            if self.attack_timer > 0 and intersects(self._attack_rect(), guard.rect()):
                guard.active = False
                self.message = "Guard disarmed! Now reach the exit."
            else:
                self._lose("The palace guard stopped you. Press R to retry.")

    def _handle_objectives(self) -> None:
        if not self.gem_collected and intersects(self.player.rect(), self.gem):
            self.gem_collected = True
            self.message = "Jewel collected. Find the moonlit door."

        if self.gem_collected and intersects(self.player.rect(), self.door):
            self.state = "won"
            self.message = "You escaped the palace! Press R to play again."

    def _move_with_collision(self, entity: Entity, dx: float, dy: float) -> None:
        if dx:
            entity.x += dx
            for tile in self._solid_rects_near(entity.rect()):
                if not intersects(entity.rect(), tile):
                    continue
                if dx > 0:
                    entity.x = tile.x - entity.w
                else:
                    entity.x = tile.x + tile.w
                entity.vx = 0

        if dy:
            entity.y += dy
            entity.on_ground = False
            for tile in self._solid_rects_near(entity.rect()):
                if not intersects(entity.rect(), tile):
                    continue
                if dy > 0:
                    entity.y = tile.y - entity.h
                    entity.on_ground = True
                else:
                    entity.y = tile.y + tile.h
                entity.vy = 0

    def _solid_rects_near(self, rect: Rect) -> Iterable[Rect]:
        left = max(0, int(rect.left // TILE) - 1)
        right = min(LEVEL_WIDTH - 1, int(rect.right // TILE) + 1)
        top = max(0, int(rect.top // TILE) - 1)
        bottom = min(LEVEL_HEIGHT - 1, int(rect.bottom // TILE) + 1)

        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                if (tx, ty) in self.solid_tiles:
                    yield Rect(tx * TILE, ty * TILE, TILE, TILE)

    def _solid_at_pixel(self, x: float, y: float) -> bool:
        if x < 0 or y < 0 or x >= SCREEN_SIZE[0] or y >= SCREEN_SIZE[1]:
            return True
        return (int(x // TILE), int(y // TILE)) in self.solid_tiles

    def _attack_rect(self) -> Rect:
        player = self.player
        if player.facing > 0:
            return Rect(player.x + player.w - 1, player.y + 3, 13, 5)
        return Rect(player.x - 12, player.y + 3, 13, 5)

    def player_action(self) -> str:
        if self.attack_timer > 0:
            return "attack"
        if not self.player.on_ground:
            return "jump"
        if abs(self.player.vx) > 0.1:
            return "run"
        return "idle"

    def _lose(self, message: str) -> None:
        self.state = "lost"
        self.message = message


class SpriteBank:
    """Builds tiny pixel-art animation frames with Pillow drawing tools."""

    def __init__(self) -> None:
        self.prince: Dict[Tuple[str, int, int], Image.Image] = {}
        self.guard: Dict[Tuple[int, int], Image.Image] = {}
        self.gem: List[Image.Image] = []
        self._build_prince_frames()
        self._build_guard_frames()
        self._build_gem_frames()

    def _build_prince_frames(self) -> None:
        frame_counts = {"idle": 2, "run": 4, "jump": 1, "attack": 3}
        for action, count in frame_counts.items():
            for frame in range(count):
                right = self._draw_prince(action, frame)
                self.prince[(action, frame, 1)] = right
                self.prince[(action, frame, -1)] = right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    def _draw_prince(self, action: str, frame: int) -> Image.Image:
        image = Image.new("RGBA", (18, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        step = frame % 2
        leg_a = 1 if action == "run" and step == 0 else 0
        leg_b = 1 if action == "run" and step == 1 else 0
        body_y = 5 if action == "jump" else 6

        # Turban, face, vest, sash, and loose pants in a tiny readable silhouette.
        draw.rectangle((6, 1, 12, 3), fill="#f3e8d2")
        draw.rectangle((5, 3, 13, 4), fill="#ffffff")
        draw.rectangle((7, 4, 12, 8), fill="#d99a67")
        draw.point((11, 5), fill="#251b13")
        draw.rectangle((6, body_y + 3, 12, body_y + 8), fill="#b83232")
        draw.rectangle((6, body_y + 7, 12, body_y + 8), fill="#f6d365")
        draw.rectangle((5, body_y + 9, 8, body_y + 13 - leg_a), fill="#2c6fbb")
        draw.rectangle((10, body_y + 9, 13, body_y + 13 - leg_b), fill="#2c6fbb")
        draw.rectangle((4, body_y + 14 - leg_a, 8, body_y + 15 - leg_a), fill="#3a2416")
        draw.rectangle((10, body_y + 14 - leg_b, 14, body_y + 15 - leg_b), fill="#3a2416")

        if action == "attack":
            reach = 15 if frame < 2 else 13
            draw.rectangle((12, body_y + 5, 15, body_y + 6), fill="#d99a67")
            draw.rectangle((15, body_y + 4, reach + 2, body_y + 4), fill="#d8dde6")
            draw.point((reach + 3, body_y + 4), fill="#ffffff")
        else:
            draw.rectangle((4, body_y + 5, 6, body_y + 6), fill="#d99a67")
            draw.rectangle((12, body_y + 5, 14, body_y + 6), fill="#d99a67")

        return image

    def _build_guard_frames(self) -> None:
        for facing in (-1, 1):
            for frame in range(2):
                right = self._draw_guard(frame)
                self.guard[(frame, 1)] = right
                self.guard[(frame, -1)] = right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    def _draw_guard(self, frame: int) -> Image.Image:
        image = Image.new("RGBA", (18, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        offset = frame % 2
        draw.rectangle((6, 2, 12, 4), fill="#414756")
        draw.rectangle((7, 4, 12, 8), fill="#c28354")
        draw.point((11, 5), fill="#141414")
        draw.rectangle((5, 8, 13, 13), fill="#374151")
        draw.rectangle((6, 13, 8, 16 - offset), fill="#5b6475")
        draw.rectangle((10, 13, 12, 16 - (1 - offset)), fill="#5b6475")
        draw.rectangle((13, 9, 16, 10), fill="#a3a3a3")
        draw.rectangle((15, 6, 16, 13), fill="#d6d3d1")
        return image

    def _build_gem_frames(self) -> None:
        colors = ["#69e6ff", "#a7f3ff", "#38bdf8", "#a7f3ff"]
        for color in colors:
            image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.polygon([(3, 0), (7, 3), (4, 7), (0, 3)], fill=color)
            draw.line((3, 0, 4, 7), fill="#ffffff")
            self.gem.append(image)


class PixelRenderer:
    def __init__(self, sprites: Optional[SpriteBank] = None) -> None:
        self.sprites = sprites or SpriteBank()

    def render(self, world: GameWorld) -> Image.Image:
        image = Image.new("RGB", SCREEN_SIZE, "#17172f")
        draw = ImageDraw.Draw(image)
        self._draw_backdrop(draw)
        self._draw_tiles(draw, world)
        self._draw_door(draw, world)
        self._draw_gem(image, world)
        self._draw_entities(image, world)
        self._draw_hud(draw, world)
        return image

    def _draw_backdrop(self, draw: ImageDraw.ImageDraw) -> None:
        for y in range(SCREEN_SIZE[1]):
            shade = 30 + int(y * 0.18)
            draw.line((0, y, SCREEN_SIZE[0], y), fill=(18, 18, shade))
        draw.ellipse((244, 18, 272, 46), fill="#f4e8c1")
        draw.ellipse((236, 14, 264, 42), fill="#17172f")

        for x in range(10, SCREEN_SIZE[0], 48):
            draw.rectangle((x, 46, x + 14, 158), fill="#242445")
            draw.rectangle((x - 4, 42, x + 18, 48), fill="#353565")
            draw.arc((x - 10, 54, x + 28, 96), 180, 360, fill="#353565", width=2)

    def _draw_tiles(self, draw: ImageDraw.ImageDraw, world: GameWorld) -> None:
        for tx, ty in world.solid_tiles:
            x = tx * TILE
            y = ty * TILE
            draw.rectangle((x, y, x + TILE - 1, y + TILE - 1), fill="#9d6b3b")
            draw.line((x, y, x + TILE - 1, y), fill="#e0a75d")
            draw.line((x, y + TILE - 1, x + TILE - 1, y + TILE - 1), fill="#5f3b25")
            draw.rectangle((x + 2, y + 4, x + 13, y + 5), fill="#b9834c")

        for spike in world.spikes:
            draw.polygon(
                [
                    (spike.x, spike.bottom),
                    (spike.x + spike.w / 2, spike.top),
                    (spike.right, spike.bottom),
                ],
                fill="#d7dce8",
            )

    def _draw_door(self, draw: ImageDraw.ImageDraw, world: GameWorld) -> None:
        door = world.door
        color = "#6d3f25" if world.gem_collected else "#3d2c21"
        glow = "#f5c96a" if world.gem_collected else "#7c5f3b"
        draw.rectangle((door.x, door.y + 5, door.right, door.bottom), fill=color)
        draw.arc((door.x, door.y, door.right, door.y + 12), 180, 360, fill=glow, width=2)
        draw.rectangle((door.x + 2, door.y + 7, door.right - 2, door.bottom), outline=glow)

    def _draw_gem(self, image: Image.Image, world: GameWorld) -> None:
        if world.gem_collected:
            return
        bob = -1 if (world.tick // 12) % 2 else 0
        frame = self.sprites.gem[(world.tick // 8) % len(self.sprites.gem)]
        image.paste(frame, (int(world.gem.x), int(world.gem.y + bob)), frame)

    def _draw_entities(self, image: Image.Image, world: GameWorld) -> None:
        player_frame = (world.tick // 5) % {"idle": 2, "run": 4, "jump": 1, "attack": 3}[world.player_action()]
        player_sprite = self.sprites.prince[(world.player_action(), player_frame, world.player.facing)]
        image.paste(player_sprite, (int(world.player.x) - 4, int(world.player.y) - 5), player_sprite)

        if world.guard.active:
            guard_frame = (world.tick // 10) % 2
            guard_sprite = self.sprites.guard[(guard_frame, world.guard.facing)]
            image.paste(guard_sprite, (int(world.guard.x) - 4, int(world.guard.y) - 5), guard_sprite)

    def _draw_hud(self, draw: ImageDraw.ImageDraw, world: GameWorld) -> None:
        draw.rectangle((4, 4, SCREEN_SIZE[0] - 4, 18), fill="#111122")
        draw.text((8, 7), world.message, fill="#f8f5d7")
        if world.state == "won":
            draw.text((102, 84), "VICTORY", fill="#fff3a3")
        elif world.state == "lost":
            draw.text((108, 84), "RETRY?", fill="#ffb4a8")


class PixelPrinceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pixel Palace Prince - Pillow Animation")
        self.keys: Set[str] = set()
        self.world = GameWorld()
        self.renderer = PixelRenderer()
        self.canvas = tk.Canvas(
            root,
            width=SCREEN_SIZE[0] * SCALE,
            height=SCREEN_SIZE[1] * SCALE,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.photo: Optional[ImageTk.PhotoImage] = None

        root.bind("<KeyPress>", self._on_key_press)
        root.bind("<KeyRelease>", self._on_key_release)
        self._loop()

    def _on_key_press(self, event: tk.Event) -> None:
        self.keys.add(self._normalize_key(event.keysym))

    def _on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(self._normalize_key(event.keysym))

    @staticmethod
    def _normalize_key(keysym: str) -> str:
        key = keysym.lower()
        if key in {"left", "right", "up", "down", "space", "a", "d", "w", "r"}:
            return key
        return keysym

    def _loop(self) -> None:
        self.world.update(self.keys)
        frame = self.renderer.render(self.world)
        scaled = frame.resize((SCREEN_SIZE[0] * SCALE, SCREEN_SIZE[1] * SCALE), RESAMPLE_NEAREST)
        self.photo = ImageTk.PhotoImage(scaled)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.root.after(16, self._loop)


def main() -> None:
    root = tk.Tk()
    PixelPrinceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
