"""A tiny pixel platformer rendered with Pillow.

The game logic is intentionally independent from Tkinter so frames can be
rendered, exported as GIFs, and tested in headless environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw

TILE = 8
VIEW_WIDTH = 160
VIEW_HEIGHT = 104
GRAVITY = 560.0
PLAYER_SPEED = 62.0
JUMP_SPEED = 178.0
PLAYER_W = 6
PLAYER_H = 13


def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


@dataclass(slots=True)
class InputState:
    left: bool = False
    right: bool = False
    jump: bool = False
    attack: bool = False


@dataclass(slots=True)
class Player:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    facing: int = 1
    on_ground: bool = False
    health: int = 3
    gems: int = 0
    attack_timer: float = 0.0
    invulnerable_timer: float = 0.0
    dead: bool = False

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + PLAYER_W, self.y + PLAYER_H


@dataclass(slots=True)
class Guard:
    x: float
    y: float
    left_bound: float
    right_bound: float
    direction: int = -1
    health: int = 2
    stun_timer: float = 0.0
    attack_cooldown: float = 0.0

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + 7, self.y + 13

    @property
    def alive(self) -> bool:
        return self.health > 0


@dataclass(slots=True)
class Gem:
    x: float
    y: float
    collected: bool = False

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + 5, self.y + 5


@dataclass(slots=True)
class Door:
    x: float
    y: float

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + TILE, self.y + TILE * 2


@dataclass(slots=True)
class Level:
    """Tile map plus entity spawn points."""

    rows: list[str]
    player_spawn: tuple[float, float]
    door: Door
    gems: list[Gem] = field(default_factory=list)
    guards: list[Guard] = field(default_factory=list)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    @classmethod
    def from_rows(cls, rows: Sequence[str]) -> "Level":
        if not rows:
            raise ValueError("Level must contain at least one row")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("All level rows must have the same width")

        clean_rows: list[str] = []
        spawn: tuple[float, float] | None = None
        door: Door | None = None
        gems: list[Gem] = []
        guards: list[Guard] = []

        for row_index, row in enumerate(rows):
            clean = list(row)
            for col_index, tile in enumerate(row):
                tile_x = col_index * TILE
                tile_y = row_index * TILE
                if tile == "P":
                    spawn = (tile_x + 1, (row_index + 1) * TILE - PLAYER_H)
                    clean[col_index] = "."
                elif tile == "D":
                    door = Door(tile_x, (row_index + 1) * TILE - TILE * 2)
                    clean[col_index] = "."
                elif tile == "*":
                    gems.append(Gem(tile_x + 2, tile_y + 2))
                    clean[col_index] = "."
                elif tile == "G":
                    guards.append(
                        Guard(
                            tile_x + 1,
                            (row_index + 1) * TILE - 13,
                            max(0, tile_x - 32),
                            min(width * TILE - 8, tile_x + 40),
                        )
                    )
                    clean[col_index] = "."
            clean_rows.append("".join(clean))

        if spawn is None:
            raise ValueError("Level needs a P player spawn")
        if door is None:
            raise ValueError("Level needs a D exit door")
        return cls(clean_rows, spawn, door, gems, guards)

    @classmethod
    def default(cls) -> "Level":
        return cls.from_rows(
            [
                ".............................................................",
                ".............................................................",
                ".............................................................",
                ".............................*...............................",
                ".......................######................................",
                "...........*...............................D.................",
                ".......########.........................########.............",
                "....................^........................................",
                "...P............#######............G.........................",
                "#########........................#########..........*........",
                "..........................####...................#######.....",
                "..............G..............................................",
                "#############################################################",
            ]
        )


class Game:
    def __init__(self, level: Level | None = None) -> None:
        self.level = level or Level.default()
        self.player = Player(*self.level.player_spawn)
        self.guards = [
            Guard(g.x, g.y, g.left_bound, g.right_bound, g.direction, g.health)
            for g in self.level.guards
        ]
        self.gems = [Gem(g.x, g.y) for g in self.level.gems]
        self.elapsed = 0.0
        self.camera_x = 0.0
        self.message = "Collect the three moon gems and reach the palace door."
        self.won = False

    @property
    def world_width(self) -> int:
        return self.level.width * TILE

    @property
    def world_height(self) -> int:
        return self.level.height * TILE

    @property
    def remaining_gems(self) -> int:
        return sum(1 for gem in self.gems if not gem.collected)

    def reset(self) -> None:
        health = self.player.health
        gems = self.player.gems
        self.player = Player(*self.level.player_spawn, health=health, gems=gems)
        self.camera_x = 0.0

    def update(self, dt: float, controls: InputState) -> None:
        dt = max(0.0, min(dt, 1 / 20))
        if self.player.dead:
            return

        self.elapsed += dt
        self.player.attack_timer = max(0.0, self.player.attack_timer - dt)
        self.player.invulnerable_timer = max(0.0, self.player.invulnerable_timer - dt)
        self._update_player(dt, controls)
        self._update_guards(dt)
        self._collect_gems()
        self._check_spikes()
        self._check_exit()
        self._update_camera()

    def _update_player(self, dt: float, controls: InputState) -> None:
        player = self.player
        move = int(controls.right) - int(controls.left)
        player.vx = move * PLAYER_SPEED
        if move:
            player.facing = move

        if controls.jump and player.on_ground:
            player.vy = -JUMP_SPEED
            player.on_ground = False

        if controls.attack and player.attack_timer <= 0:
            player.attack_timer = 0.24
            self._strike_guards()

        player.vy += GRAVITY * dt
        self._move_axis(player, player.vx * dt, axis="x")
        self._move_axis(player, player.vy * dt, axis="y")

        if player.y > self.world_height:
            self._hurt_player()

    def _update_guards(self, dt: float) -> None:
        for guard in self.guards:
            if not guard.alive:
                continue
            guard.stun_timer = max(0.0, guard.stun_timer - dt)
            guard.attack_cooldown = max(0.0, guard.attack_cooldown - dt)
            if guard.stun_timer <= 0:
                guard.x += guard.direction * 26.0 * dt
                if guard.x < guard.left_bound:
                    guard.x = guard.left_bound
                    guard.direction = 1
                elif guard.x > guard.right_bound:
                    guard.x = guard.right_bound
                    guard.direction = -1

            if rects_overlap(guard.rect, self.player.rect):
                if self.player.attack_timer > 0.09:
                    self._damage_guard(guard)
                elif guard.attack_cooldown <= 0:
                    self._hurt_player()
                    guard.attack_cooldown = 0.9

    def _move_axis(self, player: Player, amount: float, axis: str) -> None:
        if axis == "x":
            player.x += amount
        else:
            player.y += amount
            player.on_ground = False

        if not self._rect_hits_solid(player.rect):
            return

        step = -1 if amount > 0 else 1
        while self._rect_hits_solid(player.rect):
            if axis == "x":
                player.x += step
            else:
                player.y += step

        if axis == "x":
            player.vx = 0.0
        else:
            if amount > 0:
                player.on_ground = True
            player.vy = 0.0

    def _strike_guards(self) -> None:
        player = self.player
        hitbox = (
            player.x + (PLAYER_W if player.facing > 0 else -9),
            player.y + 3,
            player.x + (PLAYER_W + 9 if player.facing > 0 else 0),
            player.y + 11,
        )
        for guard in self.guards:
            if guard.alive and rects_overlap(hitbox, guard.rect):
                self._damage_guard(guard)

    def _damage_guard(self, guard: Guard) -> None:
        if guard.stun_timer > 0:
            return
        guard.health -= 1
        guard.stun_timer = 0.35
        guard.direction *= -1
        self.message = "A palace guard is staggered!"
        if guard.health <= 0:
            self.message = "The path is clear."

    def _hurt_player(self) -> None:
        player = self.player
        if player.invulnerable_timer > 0 or player.dead:
            return
        player.health -= 1
        player.invulnerable_timer = 1.0
        self.message = "The prince is hurt! Find your rhythm."
        if player.health <= 0:
            player.dead = True
            self.message = "Game over. Press R to try again."
        else:
            saved_gems = player.gems
            self.player = Player(*self.level.player_spawn, health=player.health, gems=saved_gems)
            self.player.invulnerable_timer = 1.0

    def _collect_gems(self) -> None:
        for gem in self.gems:
            if not gem.collected and rects_overlap(self.player.rect, gem.rect):
                gem.collected = True
                self.player.gems += 1
                self.message = f"Moon gem collected: {self.player.gems}/{len(self.gems)}"

    def _check_spikes(self) -> None:
        left = int(self.player.x // TILE)
        right = int((self.player.x + PLAYER_W - 1) // TILE)
        top = int(self.player.y // TILE)
        bottom = int((self.player.y + PLAYER_H - 1) // TILE)
        for tile_y in range(top, bottom + 1):
            for tile_x in range(left, right + 1):
                if self._tile_at(tile_x, tile_y) == "^":
                    self._hurt_player()
                    return

    def _check_exit(self) -> None:
        if self.remaining_gems == 0 and rects_overlap(self.player.rect, self.level.door.rect):
            self.won = True
            self.message = "You escaped the moon palace!"
        elif rects_overlap(self.player.rect, self.level.door.rect):
            self.message = "The door needs every moon gem."

    def _update_camera(self) -> None:
        target = self.player.x - VIEW_WIDTH * 0.45
        max_camera = max(0, self.world_width - VIEW_WIDTH)
        self.camera_x = max(0.0, min(max_camera, target))

    def _rect_hits_solid(self, rect: tuple[float, float, float, float]) -> bool:
        left = int(rect[0] // TILE)
        right = int((rect[2] - 1) // TILE)
        top = int(rect[1] // TILE)
        bottom = int((rect[3] - 1) // TILE)
        for tile_y in range(top, bottom + 1):
            for tile_x in range(left, right + 1):
                if self._is_solid(tile_x, tile_y):
                    return True
        return False

    def _is_solid(self, tile_x: int, tile_y: int) -> bool:
        if tile_x < 0 or tile_x >= self.level.width:
            return True
        if tile_y >= self.level.height:
            return True
        if tile_y < 0:
            return False
        return self.level.rows[tile_y][tile_x] == "#"

    def _tile_at(self, tile_x: int, tile_y: int) -> str:
        if 0 <= tile_y < self.level.height and 0 <= tile_x < self.level.width:
            return self.level.rows[tile_y][tile_x]
        return "."


class PixelRenderer:
    """Draw the game world into low-resolution Pillow images."""

    sky = (16, 12, 33)
    sky_low = (42, 26, 56)
    sand = (179, 117, 62)
    sand_dark = (116, 71, 45)
    gold = (246, 199, 94)
    white = (241, 224, 180)
    red = (159, 47, 50)
    blue = (57, 105, 151)
    shadow = (18, 14, 23)

    def render(self, game: Game) -> Image.Image:
        image = Image.new("RGB", (VIEW_WIDTH, VIEW_HEIGHT), self.sky)
        draw = ImageDraw.Draw(image)
        self._draw_background(draw, game)
        self._draw_tiles(draw, game)
        self._draw_door(draw, game)
        self._draw_gems(draw, game)
        self._draw_guards(draw, game)
        self._draw_player(draw, game)
        self._draw_hud(draw, game)
        return image

    def render_scaled(self, game: Game, scale: int = 4) -> Image.Image:
        frame = self.render(game)
        return frame.resize((VIEW_WIDTH * scale, VIEW_HEIGHT * scale), Image.Resampling.NEAREST)

    def _screen_x(self, game: Game, world_x: float) -> int:
        return int(round(world_x - game.camera_x))

    def _draw_background(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        horizon = VIEW_HEIGHT - 31
        for y in range(VIEW_HEIGHT):
            color = self.sky if y < horizon else self.sky_low
            draw.line((0, y, VIEW_WIDTH, y), fill=color)
        moon_x = 132 - int(game.camera_x * 0.08)
        draw.ellipse((moon_x, 8, moon_x + 14, 22), fill=(224, 205, 146))
        for offset, height in [(0, 24), (38, 33), (84, 27), (132, 36), (188, 29)]:
            x = offset - int(game.camera_x * 0.2) % 220
            draw.rectangle((x, horizon - height, x + 20, horizon), fill=(54, 34, 57))
            draw.rectangle((x + 7, horizon - height - 9, x + 13, horizon - height), fill=(54, 34, 57))

    def _draw_tiles(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        first_col = max(0, int(game.camera_x // TILE) - 1)
        last_col = min(game.level.width, int((game.camera_x + VIEW_WIDTH) // TILE) + 2)
        for row_index, row in enumerate(game.level.rows):
            y = row_index * TILE
            for col_index in range(first_col, last_col):
                tile = row[col_index]
                x = self._screen_x(game, col_index * TILE)
                if tile == "#":
                    draw.rectangle((x, y, x + TILE - 1, y + TILE - 1), fill=self.sand)
                    draw.line((x, y + 7, x + 7, y + 7), fill=self.sand_dark)
                    draw.line((x + ((row_index + col_index) % 2) * 4, y, x + ((row_index + col_index) % 2) * 4, y + 7), fill=self.sand_dark)
                    draw.point((x + 2, y + 3), fill=self.white)
                elif tile == "^":
                    draw.polygon((x, y + 7, x + 3, y + 1, x + 7, y + 7), fill=(160, 166, 170))
                    draw.line((x + 3, y + 1, x + 3, y + 7), fill=(83, 88, 92))

    def _draw_door(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        x = self._screen_x(game, game.level.door.x)
        y = int(game.level.door.y)
        unlocked = game.remaining_gems == 0
        draw.rectangle((x - 1, y - 1, x + 8, y + 16), fill=self.sand_dark)
        draw.rectangle((x + 1, y + 2, x + 6, y + 15), fill=(38, 22, 40) if unlocked else (73, 49, 54))
        if unlocked:
            draw.rectangle((x + 3, y + 5, x + 4, y + 11), fill=self.gold)
        else:
            draw.rectangle((x + 2, y + 7, x + 5, y + 10), fill=(107, 101, 97))

    def _draw_gems(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        pulse = int(game.elapsed * 8) % 4
        for gem in game.gems:
            if gem.collected:
                continue
            x = self._screen_x(game, gem.x)
            y = int(gem.y) - (1 if pulse in (1, 2) else 0)
            draw.polygon((x + 2, y, x + 5, y + 2, x + 2, y + 5, x - 1, y + 2), fill=self.gold)
            draw.point((x + 2, y + 1), fill=self.white)

    def _draw_guards(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        for guard in game.guards:
            if not guard.alive:
                continue
            x = self._screen_x(game, guard.x)
            y = int(guard.y)
            wobble = int(game.elapsed * 10) % 2
            if guard.stun_timer > 0:
                x += int(game.elapsed * 30) % 2
            draw.rectangle((x + 1, y + 3, x + 6, y + 10), fill=self.red)
            draw.rectangle((x + 2, y, x + 5, y + 3), fill=(199, 136, 88))
            draw.rectangle((x + 1, y - 1, x + 6, y), fill=self.sand_dark)
            draw.line((x + (0 if guard.direction < 0 else 7), y + 4, x + (4 if guard.direction < 0 else 3), y + 7), fill=(199, 136, 88))
            draw.line((x + 2, y + 10, x + 1, y + 13 + wobble), fill=(47, 37, 42))
            draw.line((x + 5, y + 10, x + 6, y + 13 - wobble), fill=(47, 37, 42))
            blade_x = x - 4 if guard.direction < 0 else x + 8
            draw.line((x + 3, y + 6, blade_x, y + 5), fill=(194, 198, 201))

    def _draw_player(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        p = game.player
        x = self._screen_x(game, p.x)
        y = int(p.y)
        run_frame = int(game.elapsed * 12) % 2 if abs(p.vx) > 1 and p.on_ground else 0
        flicker = p.invulnerable_timer > 0 and int(game.elapsed * 18) % 2 == 0
        if flicker:
            return

        pants = self.blue
        skin = (212, 149, 92)
        sash = self.red
        draw.rectangle((x + 2, y, x + 4, y + 3), fill=skin)
        draw.rectangle((x + 1, y + 3, x + 5, y + 9), fill=self.white)
        draw.line((x + 1, y + 6, x + 5, y + 6), fill=sash)
        draw.line((x + 2, y + 9, x + 1, y + 12 + run_frame), fill=pants)
        draw.line((x + 5, y + 9, x + 6, y + 12 - run_frame), fill=pants)
        arm_end = x + (9 if p.facing > 0 else -3)
        draw.line((x + (5 if p.facing > 0 else 1), y + 5, arm_end, y + 4), fill=skin)

        if p.attack_timer > 0:
            sword_y = y + 4 + (1 if p.attack_timer < 0.12 else 0)
            sword_start = x + (5 if p.facing > 0 else 1)
            sword_end = x + (15 if p.facing > 0 else -9)
            draw.line((sword_start, sword_y, sword_end, sword_y - 1), fill=(220, 225, 226))
            draw.point((sword_end, sword_y - 1), fill=self.white)
        else:
            draw.line((x + 1, y + 1, x + 5, y + 1), fill=(35, 27, 36))

    def _draw_hud(self, draw: ImageDraw.ImageDraw, game: Game) -> None:
        for index in range(3):
            color = self.red if index < game.player.health else (67, 49, 55)
            x = 4 + index * 7
            draw.rectangle((x, 4, x + 4, 8), fill=color)
            draw.point((x + 1, 5), fill=(238, 105, 91))
        draw.text((28, 2), f"gems {game.player.gems}/{len(game.gems)}", fill=self.gold)
        if game.won or game.player.dead:
            draw.rectangle((20, 39, 140, 61), fill=(18, 14, 23), outline=self.gold)
            draw.text((30, 46), game.message, fill=self.white)
        else:
            draw.text((4, VIEW_HEIGHT - 10), game.message[:36], fill=(218, 185, 127))


def scripted_controls(frame: int) -> InputState:
    """Controls for GIF export: run, jump, and swing in a repeatable loop."""
    phase = frame % 150
    return InputState(
        right=phase < 118,
        jump=phase in range(34, 42) or phase in range(90, 98),
        attack=phase in range(65, 70),
    )


def scripted_preview_gif(path: str | Path, frames: int = 180, scale: int = 4) -> Path:
    game = Game()
    renderer = PixelRenderer()
    images: list[Image.Image] = []
    for frame_index in range(frames):
        game.update(1 / 18, scripted_controls(frame_index))
        images.append(renderer.render_scaled(game, scale))

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    first, rest = images[0], images[1:]
    first.save(
        output,
        save_all=True,
        append_images=rest,
        duration=55,
        loop=0,
        optimize=False,
    )
    return output


def simulate(game: Game, controls: Iterable[InputState], dt: float = 1 / 60) -> None:
    for control_state in controls:
        game.update(dt, control_state)
