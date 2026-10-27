"""Unit Test Suite for Axioma Go Capturing Showcases.

Mathematically validates:
1. showcase_01_snapback: The Snapback (Uttegaeshi / 打って返し)
2. showcase_02_ladder: The Zigzag Ladder (Shicho / 征子)
3. showcase_03_geta: The Loose Net (Geta / 下駄)
4. showcase_04_cranes_nest: The Crane's Nest (Tsuru no Sugomori / 鶴の巣ごもり)
5. showcase_05_double_atari: The Double-Atari Fork (Ryō-Atari / 両アタリ)
6. showcase_06_ishi_no_shita: Under the Stones (Ishi-no-Shita / 石の下)

Pure Python 3.14 standard library. Zero external dependencies.
"""

from __future__ import annotations

import json
import unittest
from typing import Set, Tuple

from apps.axioma_go.src import (
    BLACK,
    BOARD_SIZE,
    WHITE,
    GoBoard,
    build_showcase_board_at_step,
    get_showcase,
    list_showcases,
    showcase_01_snapback,
    showcase_02_ladder,
    showcase_03_geta,
    showcase_04_cranes_nest,
    showcase_05_double_atari,
    showcase_06_ishi_no_shita,
    ALL_SHOWCASES,
)


class TestShowcaseCatalogAndAPI(unittest.TestCase):
    """Verifies showcase catalog, metadata exposure, and helper functions."""

    def test_catalog_has_all_six_showcases(self) -> None:
        showcases = list_showcases()
        self.assertEqual(len(showcases), 6)
        expected_ids = [
            "showcase_01_snapback",
            "showcase_02_ladder",
            "showcase_03_geta",
            "showcase_04_cranes_nest",
            "showcase_05_double_atari",
            "showcase_06_ishi_no_shita",
        ]
        actual_ids = [sc["showcase_id"] for sc in showcases]
        self.assertEqual(actual_ids, expected_ids)

    def test_get_showcase_by_id_and_aliases(self) -> None:
        # Exact ID
        sc1 = get_showcase("showcase_01_snapback")
        self.assertEqual(sc1.showcase_id, "showcase_01_snapback")

        # Short aliases
        self.assertIs(get_showcase("snapback"), sc1)
        self.assertIs(get_showcase("1"), sc1)

        sc2 = get_showcase("ladder")
        self.assertEqual(sc2.showcase_id, "showcase_02_ladder")

        sc3 = get_showcase("geta")
        self.assertEqual(sc3.showcase_id, "showcase_03_geta")

        sc4 = get_showcase("cranes_nest")
        self.assertEqual(sc4.showcase_id, "showcase_04_cranes_nest")

        sc5 = get_showcase("double_atari")
        self.assertEqual(sc5.showcase_id, "showcase_05_double_atari")

        sc6 = get_showcase("ishi_no_shita")
        self.assertEqual(sc6.showcase_id, "showcase_06_ishi_no_shita")

    def test_get_showcase_unknown_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            get_showcase("non_existent_showcase_xyz")

    def test_showcase_json_serializability(self) -> None:
        for sc in ALL_SHOWCASES:
            data = sc.to_dict()
            # Ensure valid JSON serialization
            serialized = json.dumps(data)
            self.assertIsInstance(serialized, str)
            self.assertGreater(len(serialized), 100)
            self.assertIn("showcase_id", data)
            self.assertIn("name", data)
            self.assertIn("japanese_name", data)
            self.assertIn("summary", data)
            self.assertIn("initial_stones", data)
            self.assertIn("steps", data)

    def test_dict_and_attribute_access(self) -> None:
        sc = showcase_01_snapback
        self.assertEqual(sc["id"], "showcase_01_snapback")
        self.assertEqual(sc["name"], "The Snapback")
        self.assertIn("B", sc["setup"])
        self.assertIn("W", sc["setup"])
        step0 = sc.steps[0]
        self.assertEqual(step0["ply"], 1)
        self.assertEqual(step0["x"], 4)
        self.assertEqual(step0["y"], 3)
        self.assertIn("title", step0["commentary"])


class TestShowcase01Snapback(unittest.TestCase):
    """Mathematical validation for Showcase 1: Snapback (Uttegaeshi)."""

    def setUp(self) -> None:
        self.sc = showcase_01_snapback

    def test_initial_configuration(self) -> None:
        board = self.sc.fork_into_board(ply_index=0)
        self.assertEqual(board.size, BOARD_SIZE)

        # White 7-stone inverted U-trap
        expected_white: Set[Tuple[int, int]] = {
            (3, 2), (4, 2), (5, 2),
            (3, 3),         (5, 3),
            (3, 4),         (5, 4),
        }
        for pt in expected_white:
            self.assertEqual(board.get_stone(pt[0], pt[1]), WHITE)

        # Verify White liberties before Ply 1: exactly 2 liberties at (4,3) and (4,4)
        w_root = board._stone_to_group_root[(3, 2)]
        w_libs = board._groups[w_root].liberties
        self.assertEqual(w_libs, {(4, 3), (4, 4)})

    def test_ply_by_ply_execution(self) -> None:
        # Ply 1: Black plays (4,3) [E4] -> Mutual atari
        board1 = self.sc.fork_into_board(ply_index=1)
        self.assertEqual(board1.get_stone(4, 3), BLACK)
        w_root = board1._stone_to_group_root[(3, 2)]
        self.assertEqual(board1._groups[w_root].liberties, {(4, 4)})
        b_root = board1._stone_to_group_root[(4, 3)]
        self.assertEqual(board1._groups[b_root].liberties, {(4, 4)})

        # Ply 2: White takes bait at (4,4) [E5] -> Captures Black (4,3)
        board2 = self.sc.fork_into_board(ply_index=2)
        self.assertEqual(board2.get_stone(4, 4), WHITE)
        self.assertEqual(board2.get_stone(4, 3), ".")  # Black stone was captured!
        self.assertEqual(board2.captures[WHITE], 1)
        w_root2 = board2._stone_to_group_root[(4, 4)]
        self.assertEqual(len(board2._groups[w_root2].stones), 8)
        self.assertEqual(board2._groups[w_root2].liberties, {(4, 3)})  # White in ATARI!

        # Ply 3: Black strikes back at (4,3) [E4] -> Captures all 8 White stones!
        board3 = self.sc.fork_into_board(ply_index=3)
        self.assertEqual(board3.get_stone(4, 3), BLACK)
        self.assertEqual(board3.captures[BLACK], 8)
        # All 8 White intersections must now be empty
        for x, y in [(3, 2), (4, 2), (5, 2), (3, 3), (5, 3), (3, 4), (5, 4), (4, 4)]:
            self.assertEqual(board3.get_stone(x, y), ".")


class TestShowcase02Ladder(unittest.TestCase):
    """Mathematical validation for Showcase 2: Zigzag Ladder (Shicho)."""

    def setUp(self) -> None:
        self.sc = showcase_02_ladder

    def test_initial_configuration(self) -> None:
        board = self.sc.fork_into_board(ply_index=0)
        self.assertEqual(board.get_stone(2, 1), BLACK)
        self.assertEqual(board.get_stone(3, 1), BLACK)
        self.assertEqual(board.get_stone(1, 2), BLACK)
        self.assertEqual(board.get_stone(7, 5), BLACK)  # Ladder Catcher
        self.assertEqual(board.get_stone(2, 2), WHITE)  # Target

        # White target has 2 liberties initially
        w_root = board._stone_to_group_root[(2, 2)]
        self.assertEqual(board._groups[w_root].liberties, {(2, 3), (3, 2)})

    def test_ladder_ply_14_collision_and_ply_15_capture(self) -> None:
        self.assertEqual(len(self.sc.steps), 15)

        # Board at Ply 14: White crashes into catcher at (7,5)
        board14 = self.sc.fork_into_board(ply_index=14)
        self.assertEqual(board14.get_stone(6, 5), WHITE)
        self.assertEqual(board14.get_stone(7, 5), BLACK)  # The pre-positioned catcher!
        w_root14 = board14._stone_to_group_root[(6, 5)]
        self.assertEqual(len(board14._groups[w_root14].stones), 8)
        self.assertEqual(board14._groups[w_root14].liberties, {(6, 6)})  # Only (6,6) remains!

        # Board at Ply 15: Black captures all 8 White stones at (6,6)
        board15 = self.sc.fork_into_board(ply_index=15)
        self.assertEqual(board15.get_stone(6, 6), BLACK)
        self.assertEqual(board15.captures[BLACK], 8)
        # Verify White ladder stones are wiped off
        white_ladder_points = [
            (2, 2), (3, 2), (3, 3), (4, 3),
            (4, 4), (5, 4), (5, 5), (6, 5),
        ]
        for pt in white_ladder_points:
            self.assertEqual(board15.get_stone(pt[0], pt[1]), ".")


class TestShowcase03Geta(unittest.TestCase):
    """Mathematical validation for Showcase 3: The Loose Net (Geta)."""

    def setUp(self) -> None:
        self.sc = showcase_03_geta

    def test_net_containment_and_capture(self) -> None:
        self.assertEqual(len(self.sc.steps), 5)

        # Ply 1: Black plays Geta net at (5,5)
        board1 = self.sc.fork_into_board(ply_index=1)
        self.assertEqual(board1.get_stone(5, 5), BLACK)

        # Ply 3: Black blocks at (4,6) -> White in atari with 1 liberty at (5,4)
        board3 = self.sc.fork_into_board(ply_index=3)
        w_root3 = board3._stone_to_group_root[(4, 4)]
        self.assertEqual(board3._groups[w_root3].liberties, {(5, 4)})

        # Ply 5: Black slams door at (6,4) -> Captures all 3 White stones
        board5 = self.sc.fork_into_board(ply_index=5)
        self.assertEqual(board5.get_stone(6, 4), BLACK)
        self.assertEqual(board5.captures[BLACK], 3)
        for pt in [(4, 4), (4, 5), (5, 4)]:
            self.assertEqual(board5.get_stone(pt[0], pt[1]), ".")


class TestShowcase04CranesNest(unittest.TestCase):
    """Mathematical validation for Showcase 4: Crane's Nest (Tsuru no Sugomori)."""

    def setUp(self) -> None:
        self.sc = showcase_04_cranes_nest

    def test_wedge_and_bilateral_squeeze(self) -> None:
        self.assertEqual(len(self.sc.steps), 3)

        # Initial board
        board0 = self.sc.fork_into_board(ply_index=0)
        w_root0 = board0._stone_to_group_root[(4, 3)]
        self.assertEqual(board0._groups[w_root0].liberties, {(4, 4), (5, 4), (6, 4)})

        # Ply 1: Black wedge at (5,4)
        board1 = self.sc.fork_into_board(ply_index=1)
        self.assertEqual(board1.get_stone(5, 4), BLACK)
        w_root1 = board1._stone_to_group_root[(4, 3)]
        self.assertEqual(board1._groups[w_root1].liberties, {(4, 4), (6, 4)})

        # Ply 2: White push at (4,4) -> Compresses White to 1 liberty at (6,4)
        board2 = self.sc.fork_into_board(ply_index=2)
        w_root2 = board2._stone_to_group_root[(4, 3)]
        self.assertEqual(board2._groups[w_root2].liberties, {(6, 4)})

        # Ply 3: Black squeeze at (6,4) -> Captures cutting stones
        board3 = self.sc.fork_into_board(ply_index=3)
        self.assertEqual(board3.get_stone(6, 4), BLACK)
        self.assertEqual(board3.captures[BLACK], 4)
        for pt in [(4, 3), (5, 3), (6, 3), (4, 4)]:
            self.assertEqual(board3.get_stone(pt[0], pt[1]), ".")


class TestShowcase05DoubleAtari(unittest.TestCase):
    """Mathematical validation for Showcase 5: Double-Atari Fork (Ryō-Atari)."""

    def setUp(self) -> None:
        self.sc = showcase_05_double_atari

    def test_fork_and_split_defense(self) -> None:
        self.assertEqual(len(self.sc.steps), 3)

        # Ply 1: Black fork at (4,4) [E5] -> Both Group A and B in atari
        board1 = self.sc.fork_into_board(ply_index=1)
        self.assertEqual(board1.get_stone(4, 4), BLACK)
        grp_a = board1._groups[board1._stone_to_group_root[(3, 4)]]
        grp_b = board1._groups[board1._stone_to_group_root[(5, 4)]]
        self.assertEqual(grp_a.liberties, {(3, 5)})
        self.assertEqual(grp_b.liberties, {(5, 5)})

        # Ply 2: White defends A at (3,5)
        board2 = self.sc.fork_into_board(ply_index=2)
        grp_a2 = board2._groups[board2._stone_to_group_root[(3, 4)]]
        grp_b2 = board2._groups[board2._stone_to_group_root[(5, 4)]]
        self.assertGreater(len(grp_a2.liberties), 1)  # Group A escaped
        self.assertEqual(grp_b2.liberties, {(5, 5)})  # Group B remains in atari!

        # Ply 3: Black captures B at (5,5)
        board3 = self.sc.fork_into_board(ply_index=3)
        self.assertEqual(board3.get_stone(5, 5), BLACK)
        self.assertEqual(board3.captures[BLACK], 1)
        self.assertEqual(board3.get_stone(5, 4), ".")  # Group B captured


class TestShowcase06IshiNoShita(unittest.TestCase):
    """Mathematical validation for Showcase 6: Under the Stones (Ishi-no-Shita)."""

    def setUp(self) -> None:
        self.sc = showcase_06_ishi_no_shita

    def test_sacrifice_and_cavity_resurgence(self) -> None:
        self.assertEqual(len(self.sc.steps), 4)

        # Ply 1: White captures Black 4 stones at (5,8)
        board1 = self.sc.fork_into_board(ply_index=1)
        self.assertEqual(board1.get_stone(5, 8), WHITE)
        self.assertEqual(board1.captures[WHITE], 4)
        for pt in [(3, 8), (4, 8), (3, 9), (4, 9)]:
            self.assertEqual(board1.get_stone(pt[0], pt[1]), ".")  # Cavity cleared!

        # White cutting pair now has 2 liberties at (3,8) and (3,9)
        w_cut1 = board1._groups[board1._stone_to_group_root[(2, 8)]]
        self.assertEqual(w_cut1.liberties, {(3, 8), (3, 9)})

        # Ply 2: Black strikes into vacated cavity at (3,8) [D9] -> Atari on cutting pair!
        board2 = self.sc.fork_into_board(ply_index=2)
        self.assertEqual(board2.get_stone(3, 8), BLACK)
        w_cut2 = board2._groups[board2._stone_to_group_root[(2, 8)]]
        self.assertEqual(w_cut2.liberties, {(3, 9)})  # Only 1 liberty left!

        # Ply 3: White defends outside at (5,7)
        board3 = self.sc.fork_into_board(ply_index=3)
        self.assertEqual(board3.get_stone(5, 7), WHITE)

        # Ply 4: Black captures White cutting stones at (3,9) [D10]!
        board4 = self.sc.fork_into_board(ply_index=4)
        self.assertEqual(board4.get_stone(3, 9), BLACK)
        self.assertEqual(board4.captures[BLACK], 2)
        self.assertEqual(board4.get_stone(2, 8), ".")
        self.assertEqual(board4.get_stone(2, 9), ".")


class TestBuildShowcaseBoardAtStep(unittest.TestCase):
    """Verifies build_showcase_board_at_step function across multiple steps."""

    def test_build_at_step_matches_fork_into_board(self) -> None:
        for sc in ALL_SHOWCASES:
            for step_idx in range(len(sc.steps) + 1):
                b1 = build_showcase_board_at_step(sc.showcase_id, step_idx)
                b2 = sc.fork_into_board(step_idx)
                self.assertEqual(b1.grid, b2.grid)
                self.assertEqual(b1.captures, b2.captures)
                self.assertEqual(b1.current_player, b2.current_player)


if __name__ == "__main__":
    unittest.main()
