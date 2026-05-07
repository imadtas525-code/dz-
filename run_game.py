"""Run or export the Pillow-powered Pixel Prince game."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from pixel_prince import Game, InputState, PixelRenderer, scripted_preview_gif


class PixelPrinceApp:
    def __init__(self, scale: int = 4) -> None:
        import tkinter as tk
        from PIL import ImageTk

        self.ImageTk = ImageTk
        self.root = tk.Tk()
        self.root.title("Pixel Prince - Pillow Animation")
        self.root.resizable(False, False)

        self.scale = scale
        self.game = Game()
        self.renderer = PixelRenderer()
        self.controls = InputState()
        self.last_tick = time.perf_counter()

        frame = self.renderer.render_scaled(self.game, self.scale)
        self.photo = ImageTk.PhotoImage(frame)
        self.label = tk.Label(self.root, image=self.photo, bd=0)
        self.label.pack()

        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.root.after(16, self._tick)

    def run(self) -> None:
        self.root.mainloop()

    def _key_down(self, event: Any) -> None:
        self._set_key(event.keysym, True)

    def _key_up(self, event: Any) -> None:
        self._set_key(event.keysym, False)

    def _set_key(self, key: str, pressed: bool) -> None:
        if key in {"Left", "a", "A"}:
            self.controls.left = pressed
        elif key in {"Right", "d", "D"}:
            self.controls.right = pressed
        elif key in {"Up", "space", "w", "W"}:
            self.controls.jump = pressed
        elif key in {"Shift_L", "Shift_R", "z", "Z", "x", "X"}:
            self.controls.attack = pressed
        elif key in {"r", "R"} and pressed:
            self.game = Game()
            self.controls = InputState()
        elif key == "Escape" and pressed:
            self.root.destroy()

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_tick
        self.last_tick = now

        self.game.update(dt, self.controls)
        frame = self.renderer.render_scaled(self.game, self.scale)
        self.photo = self.ImageTk.PhotoImage(frame)
        self.label.configure(image=self.photo)
        self.root.after(16, self._tick)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pixel Prince, a Pillow-rendered pixel platformer.")
    parser.add_argument("--scale", type=int, default=4, help="Nearest-neighbor display/export scale.")
    parser.add_argument("--gif", type=Path, help="Export a scripted animated GIF instead of opening a window.")
    parser.add_argument("--frames", type=int, default=180, help="Number of frames for GIF export.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.gif:
        output = scripted_preview_gif(args.gif, frames=args.frames, scale=args.scale)
        print(f"Saved animated GIF to {output}")
        return

    PixelPrinceApp(scale=args.scale).run()


if __name__ == "__main__":
    main()
