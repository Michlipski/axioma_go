"""Axioma Go Engine: 10x10 Go Substrate & Capture Showcase Engine.

Provides complete Go rule validation:
- 10x10 intersection grid (A1-K10 skipping 'I')
- Connected group & liberties calculation
- Capture detection & removal
- Suicide prevention rule
- Positional Ko rule
- Functorial Undo (immutable history stack)
- Automated Capture Showcase library (6 canonical techniques)
"""

from typing import List, Tuple, Set, Dict, Optional, Any
import copy

COLUMNS = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K"]

def coord_to_str(x: int, y: int) -> str:
    """Converts 0-indexed (x, y) to Go coordinate string, e.g. (4, 4) -> 'E5'."""
    if 0 <= x < len(COLUMNS) and 0 <= y < 10:
        return f"{COLUMNS[x]}{y + 1}"
    return f"({x},{y})"

def str_to_coord(s: str) -> Optional[Tuple[int, int]]:
    """Converts Go coordinate string like 'E5' to 0-indexed (x, y)."""
    s = s.strip().upper()
    if len(s) < 2:
        return None
    col_char = s[0]
    row_str = s[1:]
    if col_char not in COLUMNS:
        return None
    try:
        row = int(row_str)
        if not (1 <= row <= 10):
            return None
        return COLUMNS.index(col_char), row - 1
    except ValueError:
        return None


class GoEngine:
    """Deterministic, pure Python 10x10 Go engine."""

    def __init__(self, size: int = 10):
        self.size = size
        self.board: List[List[Optional[str]]] = [[None for _ in range(size)] for _ in range(size)]
        self.current_player: str = "B"
        self.captures: Dict[str, int] = {"B": 0, "W": 0}
        self.history: List[Dict[str, Any]] = []
        self.last_move: Optional[Dict[str, Any]] = None
        self.consecutive_passes: int = 0
        self.game_over: bool = False

    def clone(self) -> 'GoEngine':
        """Deep copy of the engine state."""
        eng = GoEngine(self.size)
        eng.board = [row[:] for row in self.board]
        eng.current_player = self.current_player
        eng.captures = dict(self.captures)
        eng.history = copy.deepcopy(self.history)
        eng.last_move = dict(self.last_move) if self.last_move else None
        eng.consecutive_passes = self.consecutive_passes
        eng.game_over = self.game_over
        return eng

    def set_stone(self, x: int, y: int, color: Optional[str]):
        """Sets a stone at (x, y) without move checks (for board setup)."""
        if 0 <= x < self.size and 0 <= y < self.size:
            self.board[y][x] = color

    def get_stone(self, x: int, y: int) -> Optional[str]:
        """Gets stone color at (x, y)."""
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.board[y][x]
        return None

    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Orthogonal neighbors of (x, y)."""
        res = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                res.append((nx, ny))
        return res

    def get_group(self, x: int, y: int) -> Tuple[Set[Tuple[int, int]], Set[Tuple[int, int]]]:
        """Returns (stones_in_group, liberties)."""
        color = self.board[y][x]
        if color is None:
            return set(), set()
        visited = set()
        stones = set()
        liberties = set()
        queue = [(x, y)]
        visited.add((x, y))

        while queue:
            cx, cy = queue.pop(0)
            stones.add((cx, cy))
            for nx, ny in self.get_neighbors(cx, cy):
                n_color = self.board[ny][nx]
                if n_color is None:
                    liberties.add((nx, ny))
                elif n_color == color and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return stones, liberties

    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Finds all connected stone groups on the board."""
        visited = set()
        groups = []
        for y in range(self.size):
            for x in range(self.size):
                if self.board[y][x] is not None and (x, y) not in visited:
                    stones, liberties = self.get_group(x, y)
                    visited.update(stones)
                    color = self.board[y][x]
                    groups.append({
                        "color": color,
                        "stones": sorted(list(stones)),
                        "liberties": sorted(list(liberties)),
                        "liberty_count": len(liberties)
                    })
        return groups

    def play(self, x: int, y: int, color: Optional[str] = None) -> Tuple[bool, str]:
        """Executes a move at (x, y).

        Validates:
        - Board bounds
        - Intersection vacancy
        - Opponent captures
        - Suicide prohibition
        - Positional Ko rule
        """
        if self.game_over:
            return False, "Game is already over"
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False, f"Coordinates ({x}, {y}) out of bounds"
        if self.board[y][x] is not None:
            return False, f"Intersection {coord_to_str(x, y)} is already occupied"

        move_color = color if color in ("B", "W") else self.current_player
        opponent = "W" if move_color == "B" else "B"

        # Snapshot before placing stone
        board_snapshot = [row[:] for row in self.board]

        # Tentatively place stone
        self.board[y][x] = move_color

        # Find adjacent opponent groups and capture if liberties == 0
        captured_stones: List[Tuple[int, int]] = []
        for nx, ny in self.get_neighbors(x, y):
            if self.board[ny][nx] == opponent:
                opp_stones, opp_libs = self.get_group(nx, ny)
                if len(opp_libs) == 0:
                    for sx, sy in opp_stones:
                        if (sx, sy) not in captured_stones:
                            captured_stones.append((sx, sy))

        # Remove captured stones
        for cx, cy in captured_stones:
            self.board[cy][cx] = None

        # Check suicide rule
        own_stones, own_libs = self.get_group(x, y)
        if len(own_libs) == 0:
            self.board = board_snapshot
            return False, "Suicide move is prohibited by Go rules"

        # Check positional Ko rule
        if len(self.history) >= 1:
            prev_board = self.history[-1]["board"]
            if self.board == prev_board:
                self.board = board_snapshot
                return False, "Move violates the Ko rule (position repetition)"

        # Save history snapshot for Functorial Undo
        self.history.append({
            "board": board_snapshot,
            "captures": dict(self.captures),
            "current_player": self.current_player,
            "last_move": dict(self.last_move) if self.last_move else None,
            "consecutive_passes": self.consecutive_passes
        })

        # Commit move updates
        self.captures[move_color] += len(captured_stones)
        self.last_move = {
            "x": x,
            "y": y,
            "coord": coord_to_str(x, y),
            "color": move_color,
            "captured": len(captured_stones)
        }
        self.consecutive_passes = 0
        self.current_player = opponent
        return True, "Success"

    def pass_turn(self, color: Optional[str] = None) -> Tuple[bool, str]:
        """Passes turn to the opponent."""
        if self.game_over:
            return False, "Game is already over"
        p_color = color if color in ("B", "W") else self.current_player
        opponent = "W" if p_color == "B" else "B"

        self.history.append({
            "board": [row[:] for row in self.board],
            "captures": dict(self.captures),
            "current_player": self.current_player,
            "last_move": dict(self.last_move) if self.last_move else None,
            "consecutive_passes": self.consecutive_passes
        })

        self.last_move = {
            "x": -1,
            "y": -1,
            "coord": "PASS",
            "color": p_color,
            "action": "pass",
            "captured": 0
        }
        self.current_player = opponent
        self.consecutive_passes += 1
        if self.consecutive_passes >= 2:
            self.game_over = True
            return True, "Both players passed consecutively. Game completed."
        return True, f"{p_color} passed"

    def undo(self) -> Tuple[bool, str]:
        """Reverts the last move via Functorial Undo."""
        if not self.history:
            return False, "No previous moves to undo"
        prev = self.history.pop()
        self.board = prev["board"]
        self.captures = prev["captures"]
        self.current_player = prev["current_player"]
        self.last_move = prev["last_move"]
        self.consecutive_passes = prev["consecutive_passes"]
        self.game_over = False
        return True, "Move reverted successfully"

    def reset(self):
        """Clears the board back to empty state."""
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.current_player = "B"
        self.captures = {"B": 0, "W": 0}
        self.history = []
        self.last_move = None
        self.consecutive_passes = 0
        self.game_over = False

    def get_state(self) -> Dict[str, Any]:
        """Serializes current engine state into a rich JSON-compatible dict."""
        groups = self.get_all_groups()
        liberties_map = {}
        atari_groups = []
        for g in groups:
            l_count = g["liberty_count"]
            for sx, sy in g["stones"]:
                liberties_map[f"{sx},{sy}"] = l_count
            if l_count == 1:
                atari_groups.append({
                    "color": g["color"],
                    "stones": g["stones"],
                    "liberty": g["liberties"][0],
                    "liberty_coord": coord_to_str(g["liberties"][0][0], g["liberties"][0][1])
                })

        return {
            "size": self.size,
            "board": [[cell if cell else "." for cell in row] for row in self.board],
            "current_player": self.current_player,
            "captures": dict(self.captures),
            "last_move": self.last_move,
            "liberties_map": liberties_map,
            "atari_groups": atari_groups,
            "move_count": len(self.history),
            "game_over": self.game_over,
            "columns": COLUMNS[:self.size]
        }


def build_canonical_showcases() -> Dict[str, Any]:
    """Generates all 6 canonical capture showcases with full tactical commentary."""
    showcases = {}

    # 1. Snapback (Uttegaeshi)
    eng1 = GoEngine(10)
    W1 = [(3, 4), (3, 3), (4, 3), (5, 3), (5, 4), (5, 5), (6, 4)]
    B1 = [
        (2, 4), (3, 5), (2, 3), (3, 2), (4, 2),
        (5, 2), (6, 3), (7, 4), (6, 5), (5, 6),
        (4, 6), (3, 6)
    ]
    for x, y in W1: eng1.set_stone(x, y, "W")
    for x, y in B1: eng1.set_stone(x, y, "B")

    s1_steps = []
    s1_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "布石 (Setup)",
        "explanation": "White has a 7-stone group surrounded by Black with only two inner liberties at E5 and E6. Black prepares the snapback sacrifice.",
        "state": eng1.get_state()
    })
    eng1.play(4, 4, "B")
    s1_steps.append({
        "ply": 1, "x": 4, "y": 4, "color": "B", "coord": "E5",
        "badge": "ATARI",
        "japanese_term": "捨て石 (Suteishi - Sacrifice)",
        "explanation": "Black plays inside the eye at E5! This stone is deliberately sacrificed into atari, leaving White with only 1 liberty at E6.",
        "state": eng1.get_state()
    })
    eng1.play(4, 5, "W")
    s1_steps.append({
        "ply": 2, "x": 4, "y": 5, "color": "W", "coord": "E6",
        "badge": "WARNING",
        "japanese_term": "ポン抜き (Pon-nuki Bait)",
        "explanation": "White captures Black's single stone by playing E6. But in doing so, White's entire 8-stone group is now reduced to a SINGLE liberty back at E5!",
        "state": eng1.get_state()
    })
    eng1.play(4, 4, "B")
    s1_steps.append({
        "ply": 3, "x": 4, "y": 4, "color": "B", "coord": "E5",
        "badge": "CAPTURED",
        "japanese_term": "打って返し (Uttegaeshi - Snapback)",
        "explanation": "Black immediately snaps back at E5! All 8 White stones are wiped off the board in one devastating strike.",
        "state": eng1.get_state()
    })
    showcases["snapback"] = {
        "id": "snapback",
        "name": "Snapback (Uttegaeshi)",
        "japanese_term": "打って返し (Uttegaeshi)",
        "description": "A classic sacrifice tesuji: Black feeds a stone into the opponent's mouth, and when White captures, Black immediately snaps back to capture the entire 8-stone group.",
        "setup": {"W": W1, "B": B1},
        "steps": s1_steps
    }

    # 2. Ladder (Shicho)
    eng2 = GoEngine(10)
    B2 = [(3, 4), (4, 3), (5, 3), (9, 7)]
    W2 = [(4, 4)]
    for x, y in W2: eng2.set_stone(x, y, "W")
    for x, y in B2: eng2.set_stone(x, y, "B")

    s2_steps = []
    s2_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "シチョウの起点 (Origin)",
        "explanation": "White's cutting stone at E5 is caught between Black stones at D5, E4, and F4.",
        "state": eng2.get_state()
    })
    ladder_moves = [
        (4, 5, "B", "ATARI", "当たり (Atari)", "Black ataris at E6, forcing White into diagonal flight."),
        (5, 4, "W", "WARNING", "逃げ (Escape)", "White flees to F5, attempting to break towards the open side."),
        (6, 4, "B", "ATARI", "追い込み (Chase)", "Black caps at G5! White is forced into another atari."),
        (5, 5, "W", "WARNING", "足掻き (Struggle)", "White turns down to F6."),
        (5, 6, "B", "ATARI", "階段 (Staircase)", "Black blocks at F7! The zig-zag ladder pattern is locked."),
        (6, 5, "W", "WARNING", "逃避 (Flee)", "White runs to G6."),
        (7, 5, "B", "ATARI", "当たり (Atari)", "Black strikes at H6, maintaining continuous atari."),
        (6, 6, "W", "WARNING", "疾走 (Dash)", "White extends to G7."),
        (6, 7, "B", "ATARI", "封鎖 (Seal)", "Black caps at G8."),
        (7, 6, "W", "WARNING", "追走 (Run)", "White pushes to H7."),
        (8, 6, "B", "ATARI", "当たり (Atari)", "Black strikes at J7, driving White directly towards the edge."),
        (7, 7, "W", "WARNING", "終点接近 (Near Edge)", "White reaches H8 with nowhere left to expand."),
        (7, 8, "B", "ATARI", "最終包囲 (Corner Trap)", "Black plays H9! White's liberties are completely choked."),
        (8, 7, "W", "WARNING", "絶望 (Last Stand)", "White makes a final dash to J8."),
        (8, 8, "B", "CAPTURED", "征子捕獲 (Ladder Captured!)", "Black drops the guillotine at J9 after 15 plies, capturing all 8 White stones!")
    ]
    for ply, (x, y, col, badge, term, expl) in enumerate(ladder_moves, start=1):
        eng2.play(x, y, col)
        s2_steps.append({
            "ply": ply, "x": x, "y": y, "color": col, "coord": coord_to_str(x, y),
            "badge": badge,
            "japanese_term": term,
            "explanation": expl,
            "state": eng2.get_state()
        })
    showcases["ladder"] = {
        "id": "ladder",
        "name": "The Ladder (Shichō)",
        "japanese_term": "征子 (シチョウ)",
        "description": "The fundamental geometric trap in Go: Black drives the opponent in a continuous diagonal zigzag staircase to the board edge where escape is impossible.",
        "setup": {"W": W2, "B": B2},
        "steps": s2_steps
    }

    # 3. The Net (Geta)
    eng3 = GoEngine(10)
    B3 = [(3, 4), (4, 3), (5, 3), (3, 5)]
    W3 = [(4, 4)]
    for x, y in W3: eng3.set_stone(x, y, "W")
    for x, y in B3: eng3.set_stone(x, y, "B")

    s3_steps = []
    s3_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "切断石 (Cutting Stone)",
        "explanation": "White has cut Black's groups with E5. Instead of a long ladder chase, Black can capture immediately with a loose net.",
        "state": eng3.get_state()
    })
    geta_moves = [
        (5, 5, "B", "WARNING", "下駄 (Geta - The Net)", "Black plays the classic Geta at F6! A knight's jump that loosely envelops White without direct contact."),
        (5, 4, "W", "WARNING", "突破試行 (Push)", "White pushes right to F5, attempting to pierce the net."),
        (6, 4, "B", "ATARI", "押さえ (Block & Atari)", "Black blocks at G5! White's 2 stones are now in atari with only 1 liberty at E6."),
        (4, 5, "W", "WARNING", "下がり (Turn)", "White tries escaping down to E6."),
        (4, 6, "B", "CAPTURED", "完封 (Net Sealed)", "Black drops the gate at E7! All 3 White stones are captured at ply 5.")
    ]
    for ply, (x, y, col, badge, term, expl) in enumerate(geta_moves, start=1):
        eng3.play(x, y, col)
        s3_steps.append({
            "ply": ply, "x": x, "y": y, "color": col, "coord": coord_to_str(x, y),
            "badge": badge,
            "japanese_term": term,
            "explanation": expl,
            "state": eng3.get_state()
        })
    showcases["geta"] = {
        "id": "geta",
        "name": "The Net (Geta)",
        "japanese_term": "下駄 (ゲタ)",
        "description": "An elegant tesuji that catches cutting stones in a loose net without needing a ladder, capturing 3 White stones at ply 5.",
        "setup": {"W": W3, "B": B3},
        "steps": s3_steps
    }

    # 4. Crane's Nest (Tsuru no Sugomori)
    eng4 = GoEngine(10)
    W4 = [(3, 3), (4, 3), (3, 4)]
    B4 = [
        (2, 2), (3, 2), (4, 2), (5, 2),
        (2, 3), (5, 3),
        (2, 4), (5, 4),
        (2, 5), (4, 5), (5, 5)
    ]
    for x, y in W4: eng4.set_stone(x, y, "W")
    for x, y in B4: eng4.set_stone(x, y, "B")

    s4_steps = []
    s4_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "巣ごもり局面 (Nest Pocket)",
        "explanation": "Three White stones at D4, E4, and D5 are enclosed in a deep pocket. Black executes the famous Crane's Nest tesuji.",
        "state": eng4.get_state()
    })
    crane_moves = [
        (4, 4, "B", "ATARI", "ハサミ付け (Clamp & Atari)", "Black clamps at E5! Placing the 3 White crane stones into atari."),
        (None, None, "W", "WARNING", "脱出不能 (Trapped)", "White has no viable escape route."),
        (3, 5, "B", "CAPTURED", "鶴の巣ごもり (Crane Captured)", "Black snaps shut the nest at D6, capturing all 3 White crane stones!")
    ]
    for ply, (x, y, col, badge, term, expl) in enumerate(crane_moves, start=1):
        if col == "W":
            eng4.pass_turn("W")
        else:
            eng4.play(x, y, col)
        s4_steps.append({
            "ply": ply, "x": x, "y": y, "color": col, "coord": coord_to_str(x, y) if x is not None and y is not None else "PASS",
            "badge": badge,
            "japanese_term": term,
            "explanation": expl,
            "state": eng4.get_state()
        })
    showcases["cranes_nest"] = {
        "id": "cranes_nest",
        "name": "Crane's Nest (Tsuru no Sugomori)",
        "japanese_term": "鶴の巣ごもり (Tsuru no Sugomori)",
        "description": "One of the most poetic classical Go tesujis: trapping a cluster of 3 stones in a pocket and capturing them cleanly.",
        "setup": {"W": W4, "B": B4},
        "steps": s4_steps
    }

    # 5. Double Atari (Ryō-atari)
    eng5 = GoEngine(10)
    W5 = [(3, 4), (5, 4)]
    B5 = [
        (3, 3), (3, 5),
        (5, 3), (5, 5)
    ]
    for x, y in W5: eng5.set_stone(x, y, "W")
    for x, y in B5: eng5.set_stone(x, y, "B")

    s5_steps = []
    s5_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "急所 (Vital Point)",
        "explanation": "Two separate White stones at D5 and F5 share a single mutual weakness at E5.",
        "state": eng5.get_state()
    })
    double_moves = [
        (4, 4, "B", "ATARI", "両アタリ (Ryō-Atari - Double Atari)", "Black strikes at E5! Both White stones are simultaneously placed into ATARI. White can only save one!"),
        (2, 4, "W", "WARNING", "一方防御 (Defend One)", "White extends to C5 to save the left group, leaving the right stone vulnerable."),
        (6, 4, "B", "CAPTURED", "確実捕獲 (Decisive Capture)", "Black captures the targeted White stone at G5!")
    ]
    for ply, (x, y, col, badge, term, expl) in enumerate(double_moves, start=1):
        eng5.play(x, y, col)
        s5_steps.append({
            "ply": ply, "x": x, "y": y, "color": col, "coord": coord_to_str(x, y),
            "badge": badge,
            "japanese_term": term,
            "explanation": expl,
            "state": eng5.get_state()
        })
    showcases["double_atari"] = {
        "id": "double_atari",
        "name": "Double Atari (Ryō-atari)",
        "japanese_term": "両アタリ (Ryō-atari)",
        "description": "A devastating fork maneuver in Go: a single stone attacks two independent enemy groups simultaneously, capturing the targeted stone.",
        "setup": {"W": W5, "B": B5},
        "steps": s5_steps
    }

    # 6. Under the Stones (Ishi-no-shita)
    eng6 = GoEngine(10)
    B6 = [(2, 0), (3, 0)]
    W_cut = [(2, 1), (3, 1)]
    W_other = [(1, 0)]
    B_other = [(1, 1), (2, 2), (3, 2), (4, 1)]
    W6 = W_cut + W_other
    for x, y in B6 + B_other: eng6.set_stone(x, y, "B")
    for x, y in W6: eng6.set_stone(x, y, "W")

    s6_steps = []
    s6_steps.append({
        "ply": 0, "x": None, "y": None, "color": None, "coord": None,
        "badge": "CALM",
        "japanese_term": "大石の犠牲 (Sacrifice Prep)",
        "explanation": "Black allows a 2-stone row at C1-D1 to be surrounded by White. Only 1 liberty remains at E1.",
        "state": eng6.get_state()
    })
    ishi_moves = [
        (4, 0, "W", "CAPTURED", "ポン抜き (Capture Sacrifice)", "White plays E1 and captures the Black sacrifice stones, opening up vacated territory underneath."),
        (2, 0, "B", "ATARI", "石の下 (Ishi-no-shita - Under the Stones)", "Black immediately strikes back at C1 into the vacated space ('under the stones')! White's cutting stones are placed into atari."),
        (None, None, "W", "WARNING", "防戦 (Helpless Defense)", "White cannot connect the cutting stones safely."),
        (3, 0, "B", "CAPTURED", "反撃完了 (Cutting Stones Captured)", "Black cuts at D1 and captures White's cutting stones at ply 4!")
    ]
    for ply, (x, y, col, badge, term, expl) in enumerate(ishi_moves, start=1):
        if col == "W" and x is None:
            eng6.pass_turn("W")
        else:
            eng6.play(x, y, col)
        s6_steps.append({
            "ply": ply, "x": x, "y": y, "color": col, "coord": coord_to_str(x, y) if x is not None and y is not None else "PASS",
            "badge": badge,
            "japanese_term": term,
            "explanation": expl,
            "state": eng6.get_state()
        })
    showcases["ishi_no_shita"] = {
        "id": "ishi_no_shita",
        "name": "Under the Stones (Ishi-no-shita)",
        "japanese_term": "石の下 (Ishi-no-shita)",
        "description": "A profound Go tesuji where a player deliberately sacrifices a stone group, only to play immediately into the freshly vacated intersections to capture White cutting stones at ply 4.",
        "setup": {"W": W6, "B": B6 + B_other},
        "steps": s6_steps
    }

    return showcases

CANONICAL_SHOWCASES = build_canonical_showcases()
