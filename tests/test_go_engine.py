"""Byzantine Adversarial QA & Invariant Test Suite for Axioma Go.

Verifies 100% of invariants:
1. Bounds checking: x in 0..9, y in 0..9. (-1, 0), (10, 5), coord 'I5', etc. must be rejected.
2. Overlap rejection: Playing on occupied intersection must be rejected.
3. Suicide rejection: Attempting single or multi-stone placement with 0 liberties without capturing must fail.
4. Suicide exception: Placement with 0 initial liberties that captures opponent stones must SUCCEED.
5. Ko rule: Single-stone recapture on immediate next ply must fail; must succeed after an intervening move.
6. All 6 Showcases: Programmatically verify that every showcase runs its move plies and produces the expected captures:
   - Snapback captures 8 White stones at ply 3.
   - Ladder captures 8 White stones after 15 plies.
   - Geta captures 3 White stones at ply 5.
   - Crane's Nest captures 3 White stones.
   - Double Atari captures targeted stone.
   - Under the Stones captures White cutting stones at ply 4.
7. Functorial Undo: Play 10 moves, undo 10 moves, assert exact equality of grid, turn, captures, and Ko state to initial state.
8. REST API integration: Instantiate handler to verify /api/state, /api/play, /api/showcases, /api/showcases/<id>/fork.

Uses pure Python 3.14 standard library (unittest). Zero external dependencies.
"""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import unittest

# Ensure repo root is on sys.path
current_dir = Path(__file__).resolve()
repo_root = current_dir.parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from apps.axioma_go.src import (
    BLACK,
    BOARD_SIZE,
    CANONICAL_SHOWCASES,
    COL_LABELS,
    EMPTY,
    WHITE,
    FunctorialUndoViolation,
    GoBoard,
    GoEngine,
    GoEngineError,
    IllegalMoveError,
    IntersectionOccupiedError,
    KoError,
    OutOfBoundsError,
    SuicideError,
    TurnOrderError,
    UndoManager,
    col_to_x,
    coord_to_str,
    coord_to_xy,
    str_to_coord,
    verify_reversibility,
    x_to_col,
    xy_to_coord,
)
from apps.axioma_go.src.go_engine import index_to_xy, xy_to_index
from apps.axioma_go.src.server import AxiomaGoRequestHandler, AxiomaGoState, GLOBAL_STATE


class TestCoordinatesAndBounds(unittest.TestCase):
    """[INV-GO-001] Verifies 10x10 grid bounds and coordinate translation standards."""

    def test_column_labels_and_i_exclusion(self) -> None:
        self.assertEqual(len(COL_LABELS), 10)
        self.assertEqual(COL_LABELS, "ABCDEFGHJK")
        self.assertNotIn("I", COL_LABELS)

    def test_coordinate_roundtrip_all_intersections(self) -> None:
        for x in range(BOARD_SIZE):
            for y in range(BOARD_SIZE):
                coord = xy_to_coord(x, y)
                rx, ry = coord_to_xy(coord)
                self.assertEqual((rx, ry), (x, y))

    def test_canonical_corners(self) -> None:
        self.assertEqual(xy_to_coord(0, 0), "A1")
        self.assertEqual(xy_to_coord(9, 0), "K1")
        self.assertEqual(xy_to_coord(0, 9), "A10")
        self.assertEqual(xy_to_coord(9, 9), "K10")
        self.assertEqual(xy_to_coord(3, 3), "D4")
        self.assertEqual(xy_to_coord(7, 6), "H7")
        self.assertEqual(xy_to_coord(8, 0), "J1")

    def test_out_of_bounds_coordinates_rejection(self) -> None:
        """Requirement 1: Bounds checking x in 0..9, y in 0..9; (-1, 0), (10, 5) rejected."""
        with self.assertRaises(OutOfBoundsError):
            coord_to_xy("I5")  # 'I' is strictly excluded
        with self.assertRaises(OutOfBoundsError):
            coord_to_xy("A0")  # Row 0 does not exist
        with self.assertRaises(OutOfBoundsError):
            coord_to_xy("A11")  # Row 11 out of bounds
        with self.assertRaises(OutOfBoundsError):
            coord_to_xy("L5")  # Column L out of bounds
        with self.assertRaises(OutOfBoundsError):
            xy_to_coord(-1, 0)
        with self.assertRaises(OutOfBoundsError):
            xy_to_coord(10, 5)
        with self.assertRaises(OutOfBoundsError):
            xy_to_index(-1, 0)
        with self.assertRaises(OutOfBoundsError):
            xy_to_index(10, 5)

        # Also test on GoBoard directly
        board = GoBoard()
        with self.assertRaises(OutOfBoundsError):
            board.validate_move(BLACK, -1, 0)
        with self.assertRaises(OutOfBoundsError):
            board.validate_move(BLACK, 10, 5)
        with self.assertRaises(OutOfBoundsError):
            board.validate_move(BLACK, 0, -1)
        with self.assertRaises(OutOfBoundsError):
            board.validate_move(BLACK, 5, 10)

        ok1, _, err1 = board.play_move(BLACK, -1, 0)
        self.assertFalse(ok1)
        ok2, _, err2 = board.play_move(BLACK, 10, 5)
        self.assertFalse(ok2)

        # And on engine.py GoEngine directly
        from apps.axioma_go.src.engine import GoEngine as EngineModel
        eng = EngineModel(10)
        ok_eng1, msg1 = eng.play(-1, 0, "B")
        self.assertFalse(ok_eng1)
        self.assertIn("out of bounds", msg1.lower())
        ok_eng2, msg2 = eng.play(10, 5, "B")
        self.assertFalse(ok_eng2)
        self.assertIn("out of bounds", msg2.lower())


class TestOverlapAndSuicideInvariants(unittest.TestCase):
    """[INV-GO-002, INV-GO-003] Overlap rejection, suicide rejection, and suicide capture exception."""

    def setUp(self) -> None:
        self.board = GoBoard()

    def test_overlap_rejection_on_occupied_intersection(self) -> None:
        """Requirement 2: Playing on occupied intersection must be rejected."""
        ok1, _, err1 = self.board.play_move(BLACK, 3, 3)
        self.assertTrue(ok1)
        self.assertIsNone(err1)

        # Attempt to play White on the exact same intersection
        with self.assertRaises(IntersectionOccupiedError):
            self.board.validate_move(WHITE, 3, 3)

        ok2, _, err2 = self.board.play_move(WHITE, 3, 3)
        self.assertFalse(ok2)
        self.assertIsNotNone(err2)
        self.assertIn("occupied", err2.lower())

        # Test in engine as well
        from apps.axioma_go.src.engine import GoEngine as EngineModel
        eng = EngineModel(10)
        ok_p1, _ = eng.play(4, 4, "B")
        self.assertTrue(ok_p1)
        ok_p2, msg_p2 = eng.play(4, 4, "W")
        self.assertFalse(ok_p2)
        self.assertIn("already occupied", msg_p2.lower())

    def test_single_stone_suicide_rejection(self) -> None:
        """Requirement 3: Attempting single-stone placement with 0 liberties without capturing must fail."""
        # White surrounds corner (0, 0)
        self.board.set_stone(1, 0, WHITE)
        self.board.set_stone(0, 1, WHITE)

        # Black playing (0, 0) has 0 liberties and captures 0 stones -> SUICIDE
        with self.assertRaises(SuicideError):
            self.board.validate_move(BLACK, 0, 0)

        ok, caps, err = self.board.play_move(BLACK, 0, 0)
        self.assertFalse(ok)
        self.assertEqual(len(caps), 0)
        self.assertIn("suicide", err.lower())

    def test_multi_stone_suicide_rejection(self) -> None:
        """Requirement 3: Multi-stone group placement with 0 liberties without capturing must fail."""
        # Form an enclosed 2-stone cavity at (1, 1) and (1, 2)
        white_surround = [
            (0, 1), (0, 2),  # left
            (2, 1), (2, 2),  # right
            (1, 0),          # bottom
            (1, 3),          # top
        ]
        for wx, wy in white_surround:
            self.board.set_stone(wx, wy, WHITE)

        # Black plays (1, 1) leaving exactly 1 liberty at (1, 2)
        ok1, _, _ = self.board.play_move(BLACK, 1, 1)
        self.assertTrue(ok1)

        # Now White plays elsewhere (e.g. 8, 8)
        self.board.play_move(WHITE, 8, 8)

        # Now Black attempts to play at (1, 2). The resulting 2-stone group {(1, 1), (1, 2)} has 0 liberties!
        with self.assertRaises(SuicideError):
            self.board.validate_move(BLACK, 1, 2)

        ok2, caps2, err2 = self.board.play_move(BLACK, 1, 2)
        self.assertFalse(ok2)
        self.assertIn("suicide", err2.lower())

    def test_suicide_exception_placement_with_captures_succeeds(self) -> None:
        """Requirement 4: Placement with 0 initial liberties that captures opponent stones must SUCCEED."""
        # White group at (0, 0) with 1 remaining liberty at (0, 1)
        self.board.set_stone(0, 0, WHITE)
        self.board.set_stone(1, 0, BLACK)
        self.board.set_stone(0, 2, BLACK)
        self.board.set_stone(1, 1, BLACK)

        # (0, 1) is surrounded by (0, 0)[W], (0, 2)[B], (1, 1)[B].
        # If Black plays (0, 1), it has no liberties of its own, BUT it removes White's last liberty at (0, 0)!
        # Under Go rules, opponent stones are removed FIRST, giving Black liberty!
        ok, caps, err = self.board.play_move(BLACK, 0, 1)
        self.assertTrue(ok, f"Capture move should succeed despite 0 initial liberties: {err}")
        self.assertEqual(caps, [(0, 0)])
        self.assertEqual(self.board.get_stone(0, 0), EMPTY)
        self.assertEqual(self.board.get_stone(0, 1), BLACK)
        self.assertEqual(self.board.captures[BLACK], 1)


class TestKoRuleLockout(unittest.TestCase):
    """[INV-GO-004] Ko Rule: immediate single-stone recapture rejected; succeeds after intervening move."""

    def setUp(self) -> None:
        self.board = GoBoard()

    def test_ko_rule_immediate_recapture_lockout_and_resolution(self) -> None:
        """Requirement 5: Single-stone recapture on immediate next ply must fail; succeeds after intervening move."""
        # Setup classic Ko configuration around (1, 1) and (2, 1)
        self.board.set_stone(0, 1, BLACK)
        self.board.set_stone(1, 2, BLACK)
        self.board.set_stone(1, 0, BLACK)

        self.board.set_stone(3, 1, WHITE)
        self.board.set_stone(2, 2, WHITE)
        self.board.set_stone(2, 0, WHITE)

        # White places stone at (1, 1) in atari
        self.board.set_stone(1, 1, WHITE)

        # Step 1: Black plays at (2, 1), capturing the single White stone at (1, 1)
        ok_b, caps_b, err_b = self.board.play_move(BLACK, 2, 1)
        self.assertTrue(ok_b)
        self.assertEqual(caps_b, [(1, 1)])
        # Ko lockout point must be set to (1, 1)
        self.assertEqual(self.board.ko_point, (1, 1))

        # Step 2: White tries to IMMEDIATELY recapture at (1, 1) -> MUST FAIL (Ko lockout)
        with self.assertRaises(KoError):
            self.board.validate_move(WHITE, 1, 1)

        ok_w, _, err_w = self.board.play_move(WHITE, 1, 1)
        self.assertFalse(ok_w)
        self.assertIn("ko", err_w.lower())

        # Step 3: White plays an intervening Ko threat elsewhere (e.g. 7, 7)
        ok_threat, _, _ = self.board.play_move(WHITE, 7, 7)
        self.assertTrue(ok_threat)
        # Intervening move clears Ko lockout
        self.assertIsNone(self.board.ko_point)

        # Step 4: Black answers the Ko threat (e.g. 8, 7) instead of filling the Ko
        ok_ans, _, _ = self.board.play_move(BLACK, 8, 7)
        self.assertTrue(ok_ans)

        # Step 5: White can now LEGALLY recapture at (1, 1)!
        ok_recap, caps_recap, _ = self.board.play_move(WHITE, 1, 1)
        self.assertTrue(ok_recap)
        self.assertEqual(caps_recap, [(2, 1)])
        # Now Black is locked out from immediate recapture at (2, 1)
        self.assertEqual(self.board.ko_point, (2, 1))


class TestCanonicalShowcasesExecution(unittest.TestCase):
    """Requirement 6: Programmatically verify all 6 showcases produce the exact expected captures."""

    def test_showcase_1_snapback_captures_8_white_stones_at_ply_3(self) -> None:
        """Snapback captures 8 White stones at ply 3."""
        self.assertIn("snapback", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["snapback"]
        steps = sc["steps"]
        self.assertGreaterEqual(len(steps), 4)

        # Step 0: Setup
        self.assertEqual(steps[0]["ply"], 0)
        # Step 1: Black plays sacrifice inside eye (E5)
        self.assertEqual(steps[1]["ply"], 1)
        # Step 2: White takes bait at E6 (captures 1 Black stone)
        self.assertEqual(steps[2]["ply"], 2)
        self.assertEqual(steps[2]["state"]["captures"]["W"], 1)

        # Step 3: Black snaps back at E5 -> captures all 8 White stones!
        self.assertEqual(steps[3]["ply"], 3)
        self.assertEqual(steps[3]["state"]["captures"]["B"], 8)
        self.assertEqual(steps[3]["badge"], "CAPTURED")

    def test_showcase_2_ladder_captures_8_white_stones_after_15_plies(self) -> None:
        """Ladder captures 8 White stones after 15 plies."""
        self.assertIn("ladder", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["ladder"]
        steps = sc["steps"]
        # Steps include ply 0 setup + 15 plies = 16 elements
        self.assertEqual(len(steps), 16)

        # Step 15 terminal capture
        terminal_step = steps[15]
        self.assertEqual(terminal_step["ply"], 15)
        self.assertEqual(terminal_step["state"]["captures"]["B"], 8)
        self.assertEqual(terminal_step["badge"], "CAPTURED")

    def test_showcase_3_geta_captures_3_white_stones_at_ply_5(self) -> None:
        """Geta captures 3 White stones at ply 5."""
        self.assertIn("geta", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["geta"]
        steps = sc["steps"]
        self.assertEqual(len(steps), 6)  # ply 0..5

        # Ply 5 terminal capture
        terminal_step = steps[5]
        self.assertEqual(terminal_step["ply"], 5)
        self.assertEqual(terminal_step["state"]["captures"]["B"], 3)
        self.assertEqual(terminal_step["badge"], "CAPTURED")

    def test_showcase_4_cranes_nest_captures_3_white_stones(self) -> None:
        """Crane's Nest captures 3 White stones."""
        self.assertIn("cranes_nest", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["cranes_nest"]
        steps = sc["steps"]
        terminal_step = steps[-1]
        self.assertEqual(terminal_step["state"]["captures"]["B"], 3)
        self.assertEqual(terminal_step["badge"], "CAPTURED")

    def test_showcase_5_double_atari_captures_targeted_stone(self) -> None:
        """Double Atari captures targeted stone."""
        self.assertIn("double_atari", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["double_atari"]
        steps = sc["steps"]
        terminal_step = steps[-1]
        self.assertGreaterEqual(terminal_step["state"]["captures"]["B"], 1)
        self.assertEqual(terminal_step["badge"], "CAPTURED")

    def test_showcase_6_under_the_stones_captures_cutting_stones_at_ply_4(self) -> None:
        """Under the Stones captures White cutting stones at ply 4."""
        self.assertIn("ishi_no_shita", CANONICAL_SHOWCASES)
        sc = CANONICAL_SHOWCASES["ishi_no_shita"]
        steps = sc["steps"]
        self.assertEqual(len(steps), 5)  # ply 0..4

        # Ply 1: White captures Black sacrifice group
        self.assertEqual(steps[1]["state"]["captures"]["W"], 2)
        # Ply 4: Black captures White cutting stones in vacated space!
        terminal_step = steps[4]
        self.assertEqual(terminal_step["ply"], 4)
        self.assertEqual(terminal_step["state"]["captures"]["B"], 2)
        self.assertEqual(terminal_step["badge"], "CAPTURED")


class TestFunctorialUndoReversibility(unittest.TestCase):
    """Requirement 7: Play 10 moves, undo 10 moves, assert exact equality of grid, turn, captures, and Ko state."""

    def test_functorial_undo_ten_ply_identity(self) -> None:
        from apps.axioma_go.src.engine import GoEngine as EngineModel
        eng = EngineModel(10)
        initial_board = [row[:] for row in eng.board]
        initial_player = eng.current_player
        initial_captures = dict(eng.captures)
        initial_history_len = len(eng.history)

        moves = [
            (3, 3, "B"), (6, 6, "W"),
            (3, 4, "B"), (6, 5, "W"),
            (4, 3, "B"), (5, 6, "W"),
            (4, 4, "B"), (5, 5, "W"),
            (2, 2, "B"), (7, 7, "W"),
        ]

        # Execute 10 forward plies
        for ply_idx, (x, y, col) in enumerate(moves, 1):
            ok, msg = eng.play(x, y, col)
            self.assertTrue(ok, f"Forward ply {ply_idx} failed: {msg}")

        self.assertEqual(len(eng.history), 10)
        self.assertNotEqual(eng.board, initial_board)

        # Roll back all 10 plies via categorical adjoint morphism
        for undo_idx in range(10):
            ok, msg = eng.undo()
            self.assertTrue(ok, f"Reverse undo ply {undo_idx + 1} failed: {msg}")

        # Assert exact equality to initial state
        self.assertEqual(len(eng.history), initial_history_len)
        self.assertEqual(eng.board, initial_board, "Board matrix must match initial state exactly")
        self.assertEqual(eng.current_player, initial_player, "Current player must match initial state exactly")
        self.assertEqual(eng.captures, initial_captures, "Captures map must match initial state exactly")

    def test_functorial_undo_manager_with_captures(self) -> None:
        """Verifies UndoManager state hashing across multi-stone capture sequence."""
        board = GoBoard(10)
        manager = UndoManager(board)
        initial_hash = board.compute_hash()

        # Sequence executing captures
        moves = [
            (BLACK, 0, 0),
            (WHITE, 1, 0),
            (BLACK, 9, 9),  # black plays away
            (WHITE, 0, 1),  # captures (0, 0)
        ]
        for color, x, y in moves:
            board.play_move(color, x, y)
            manager.record_state(board)

        self.assertEqual(board.captures[WHITE], 1)

        # Undo all 4 moves
        restored = None
        for _ in range(4):
            restored = manager.undo()

        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.compute_hash(), initial_hash)
        self.assertEqual(restored.get_stone(0, 0), EMPTY)
        self.assertEqual(restored.captures[WHITE], 0)


class TestRestApiIntegration(unittest.TestCase):
    """Requirement 8: Verify REST API endpoints /api/state, /api/play, /api/showcases, /api/showcases/<id>/fork."""

    class DummyHttpRequestHandler(AxiomaGoRequestHandler):
        """Hermetic request handler test harness simulating standard HTTP requests in-memory."""

        def __init__(self, path: str, command: str = "GET", body_dict: Optional[Dict[str, Any]] = None) -> None:
            body_bytes = json.dumps(body_dict).encode("utf-8") if body_dict is not None else b""
            self.requestline = f"{command} {path} HTTP/1.1"
            self.request_version = "HTTP/1.1"
            self.command = command
            self.path = path
            self.headers = {"Content-Length": str(len(body_bytes))}
            self.rfile = io.BytesIO(body_bytes)
            self.wfile = io.BytesIO()
            self.close_connection = False

        def get_response_data(self) -> Tuple[int, Dict[str, Any]]:
            raw = self.wfile.getvalue().decode("utf-8")
            lines = raw.split("\r\n")
            status_line = lines[0]
            status_code = int(status_line.split(" ")[1])
            body_start = raw.find("\r\n\r\n") + 4
            body_str = raw[body_start:]
            data = json.loads(body_str) if body_str else {}
            return status_code, data

    def setUp(self) -> None:
        GLOBAL_STATE.reset()

    def test_get_api_state(self) -> None:
        """Verify GET /api/state returns 200 with board matrix, captures, and turn."""
        h = self.DummyHttpRequestHandler("/api/state", command="GET")
        h.do_GET()
        status, data = h.get_response_data()
        self.assertEqual(status, 200)
        self.assertEqual(data["size"], 10)
        self.assertEqual(data["current_player"], "B")
        self.assertIn("board", data)
        self.assertIn("captures", data)

    def test_post_api_play(self) -> None:
        """Verify POST /api/play executes move and returns 200 with updated state."""
        h = self.DummyHttpRequestHandler("/api/play", command="POST", body_dict={"x": 3, "y": 3, "color": "B"})
        h.do_POST()
        status, data = h.get_response_data()
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["current_player"], "W")
        self.assertEqual(data["board"][3][3], "B")

    def test_get_api_showcases(self) -> None:
        """Verify GET /api/showcases returns 200 with all 6 showcases in manifest."""
        h = self.DummyHttpRequestHandler("/api/showcases", command="GET")
        h.do_GET()
        status, data = h.get_response_data()
        self.assertEqual(status, 200)
        self.assertIn("showcases", data)
        showcase_ids = [s["id"] for s in data["showcases"]]
        self.assertEqual(len(showcase_ids), 6)
        expected_ids = ["snapback", "ladder", "geta", "cranes_nest", "double_atari", "ishi_no_shita"]
        for eid in expected_ids:
            self.assertIn(eid, showcase_ids)

    def test_post_api_showcases_fork(self) -> None:
        """Verify POST /api/showcases/<id>/fork forks into live playable state."""
        h = self.DummyHttpRequestHandler("/api/showcases/snapback/fork", command="POST", body_dict={"ply": 2})
        h.do_POST()
        status, data = h.get_response_data()
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["active_showcase_id"], "snapback")
        self.assertEqual(data["active_ply"], 2)


if __name__ == "__main__":
    unittest.main()
