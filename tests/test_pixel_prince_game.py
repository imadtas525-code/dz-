import unittest

from PIL import Image

from pixel_prince_game import GameWorld, PixelRenderer, SCREEN_SIZE, SpriteBank


class PixelPrinceGameTest(unittest.TestCase):
    def test_world_starts_in_playing_state(self):
        world = GameWorld()

        self.assertEqual(world.state, "playing")
        self.assertFalse(world.gem_collected)
        self.assertTrue(world.guard.active)
        self.assertGreater(world.player.x, 0)

    def test_player_moves_right(self):
        world = GameWorld()
        start_x = world.player.x

        for _ in range(5):
            world.update({"right"})

        self.assertGreater(world.player.x, start_x)
        self.assertEqual(world.player.facing, 1)

    def test_renderer_returns_pillow_image(self):
        world = GameWorld()
        renderer = PixelRenderer(SpriteBank())

        frame = renderer.render(world)

        self.assertIsInstance(frame, Image.Image)
        self.assertEqual(frame.size, SCREEN_SIZE)


if __name__ == "__main__":
    unittest.main()
