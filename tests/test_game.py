import unittest

from PIL import Image

from pixel_prince import Game, InputState, Level, PixelRenderer
from pixel_prince.game import VIEW_HEIGHT, VIEW_WIDTH


class GameTests(unittest.TestCase):
    def test_default_level_loads_entities(self) -> None:
        level = Level.default()

        self.assertEqual(len(level.gems), 3)
        self.assertEqual(len(level.guards), 2)
        self.assertGreater(level.width, 40)

    def test_player_collects_gem(self) -> None:
        game = Game()
        gem = game.gems[0]
        game.player.x = gem.x
        game.player.y = gem.y

        game.update(1 / 60, InputState())

        self.assertTrue(gem.collected)
        self.assertEqual(game.player.gems, 1)

    def test_renderer_returns_pixel_frame(self) -> None:
        game = Game()
        renderer = PixelRenderer()

        frame = renderer.render(game)

        self.assertIsInstance(frame, Image.Image)
        self.assertEqual(frame.size, (VIEW_WIDTH, VIEW_HEIGHT))

    def test_attack_damages_guard(self) -> None:
        game = Game()
        guard = game.guards[0]
        game.player.x = guard.x - 7
        game.player.y = guard.y
        game.player.facing = 1

        game.update(1 / 60, InputState(attack=True))

        self.assertEqual(guard.health, 1)


if __name__ == "__main__":
    unittest.main()
