import math
import unittest

from titans import ASSETS, assemble_mask, morph_mask, render, rotate_mask, sample_mask, text_mask


class RotationTests(unittest.TestCase):
    def test_front_and_full_turn_preserve_symbol(self):
        rows = sample_mask((ASSETS / "symbol-mask.bin").read_bytes(), 48)
        self.assertEqual(rotate_mask(rows, 0), rows)
        self.assertEqual(rotate_mask(rows, math.tau), rows)

    def test_back_mirrors_asymmetric_shape(self):
        rows = [[1.0, 0.0, 0.5, 0.0]]
        self.assertEqual(rotate_mask(rows, math.pi), [rows[0][::-1]])

    def test_side_is_narrow_and_centered(self):
        rows = [[1.0] * 48]
        edge = rotate_mask(rows, math.pi / 2)[0]
        self.assertEqual([x for x, value in enumerate(edge) if value], [23, 24])
        self.assertAlmostEqual(sum(edge), 1)

    def test_animation_overwrites_previous_frame_and_loops(self):
        rows = sample_mask((ASSETS / "symbol-mask.bin").read_bytes(), 48)
        for elapsed in (0, 0.75, 1.5, 3, 4.5, 6):
            frame = render(rows, elapsed, "spin")
            self.assertTrue(all(len(line) == 48 for line in frame.splitlines()))
        self.assertEqual(render(rows, 0, "spin"), render(rows, 6, "spin"))
        self.assertEqual(render(rows, 1.5, "spin"), render(rows, 0.75, "spin", period=3))


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.rows = sample_mask((ASSETS / "symbol-mask.bin").read_bytes(), 48)

    def test_hold_matches_original_and_does_not_mutate_it(self):
        original = [row[:] for row in self.rows]
        for phase in (0, 0.05, 0.95):
            self.assertEqual(assemble_mask(self.rows, phase), original)
        assemble_mask(self.rows, 0.2)
        self.assertEqual(self.rows, original)

    def test_particles_form_text_and_return_without_jumping(self):
        wordmark = text_mask(48, len(self.rows))
        for phase in (0.4, 0.5, 0.6):
            self.assertEqual(assemble_mask(self.rows, phase), wordmark)
        self.assertNotEqual(wordmark, self.rows)
        self.assertNotEqual(assemble_mask(self.rows, 0.25), self.rows)
        self.assertNotEqual(assemble_mask(self.rows, 0.25), wordmark)
        self.assertEqual(assemble_mask(self.rows, 0), assemble_mask(self.rows, 1))
        self.assertEqual(assemble_mask(self.rows, 0), assemble_mask(self.rows, 1 - 1e-8))
        forward = assemble_mask(self.rows, 0.25)
        backward = assemble_mask(self.rows, 0.75)
        for a, b in zip(sum(forward, []), sum(backward, [])):
            self.assertAlmostEqual(a, b)

    def test_morph_endpoints_and_legible_wordmark(self):
        self.assertEqual(morph_mask(self.rows, 0), self.rows)
        self.assertEqual(morph_mask(self.rows, 1), text_mask(48, len(self.rows)))
        wordmark = text_mask(48, 5)
        actual = ["".join("#" if value else " " for value in row).rstrip() for row in wordmark]
        self.assertEqual(actual, [
            "### #####     ##### ### #####  ###  #   #  ####",
            " #    #         #    #    #   #   # ##  # #",
            " #    #   ###   #    #    #   ##### # # #  ###",
            " #    #         #    #    #   #   # #  ##     #",
            "###   #         #   ###   #   #   # #   # ####",
        ])

    def test_bounds_at_small_and_normal_sizes(self):
        for width in (1, 12, 39, 45, 48, 96):
            rows = sample_mask((ASSETS / "symbol-mask.bin").read_bytes(), width)
            for phase in (0, 0.1, 0.3, 0.5, 0.7, 0.9):
                frame = assemble_mask(rows, phase)
                self.assertEqual(len(frame), len(rows))
                self.assertTrue(all(len(row) == width for row in frame))
                self.assertTrue(all(0 <= value <= 1 for row in frame for value in row))

    def test_period_padding_and_static_output(self):
        self.assertEqual(render(self.rows, 1.5, "assemble"),
                         render(self.rows, 3, "assemble", period=12))
        for elapsed in (0, 1, 3, 5, 6):
            frame = render(self.rows, elapsed, "assemble")
            self.assertTrue(all(len(line) == 48 for line in frame.splitlines()))
        self.assertEqual(render(self.rows, 0, "assemble", static=True),
                         render(self.rows, static=True))

    def test_combined_cycle_stages_and_repeat(self):
        period = 12
        for phase, effect, local_phase in (
            (0.1875, "assemble", 0.25),
            (0.375, "assemble", 0.5),
            (0.5625, "assemble", 0.75),
            (0.875, "spin", 0.5),
        ):
            self.assertEqual(
                render(self.rows, phase * period, "cycle", period=period),
                render(self.rows, local_phase * period, effect, period=period),
            )
        self.assertEqual(render(self.rows, 0, "cycle", period=period),
                         render(self.rows, period, "cycle", period=period))
        self.assertEqual(render(self.rows, 0, "cycle", period=period),
                         render(self.rows, period - 1e-8, "cycle", period=period))

    def test_only_held_text_has_flow(self):
        for color in (False, True):
            start = render(self.rows, 4, "assemble", color=color, period=10)
            middle = render(self.rows, 5, "assemble", color=color, period=10)
            end = render(self.rows, 6, "assemble", color=color, period=10)
            self.assertNotEqual(start, middle)
            self.assertEqual(start, end)
            if not color:
                # A flow has different brightness across letters, unlike a
                # uniform pulse. Whitespace remains the same text silhouette.
                self.assertGreater(len(set(middle) - {" ", "\n"}), 1)
                self.assertEqual([char.isspace() for char in start],
                                 [char.isspace() for char in middle])
            self.assertEqual(
                render(self.rows, 0, "assemble", color=color, period=10),
                render(self.rows, 9.5, "assemble", color=color, period=10),
            )
        for phase in (0.2, 0.7):
            expected = render(assemble_mask(self.rows, phase), static=True)
            actual = render(self.rows, phase * 10, "assemble", period=10)
            self.assertEqual([line.rstrip() for line in actual.split("\n")],
                             expected.split("\n"))

    def test_standalone_flow_uses_text_and_logo_hold_is_steady(self):
        wordmark = render(text_mask(48, len(self.rows)), static=True)
        frame = render(self.rows, 0, "flow")
        self.assertEqual([line.rstrip() for line in frame.split("\n")],
                         wordmark.split("\n"))
        self.assertEqual(render(self.rows, 0, "cycle", period=12),
                         render(self.rows, 0.5, "cycle", period=12))


if __name__ == "__main__":
    unittest.main()
