"""Axioma Go Canonical Capturing Showcases (10x10 Board).

Implements the 6 canonical capturing showcases from the Research Deliverable Bundle:
1. showcase_01_snapback: The Snapback (Uttegaeshi / 打って返し)
2. showcase_02_ladder: The Zigzag Ladder (Shicho / 征子)
3. showcase_03_geta: The Loose Net (Geta / 下駄)
4. showcase_04_cranes_nest: The Crane's Nest (Tsuru no Sugomori / 鶴の巣ごもり)
5. showcase_05_double_atari: The Double-Atari Fork (Ryō-Atari / 両アタリ)
6. showcase_06_ishi_no_shita: Under the Stones (Ishi-no-Shita / 石の下)

Pure Python 3.14 standard library. Zero external dependencies.
Grid is 10x10 intersections (x in 0..9, y in 0..9, columns A-K excluding 'I', rows 1..10).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from apps.axioma_go.src.go_engine import (
        BLACK,
        BOARD_SIZE,
        COL_LABELS,
        EMPTY,
        WHITE,
        GoBoard,
        coord_to_xy,
        xy_to_coord,
    )
except ImportError:
    try:
        from .go_engine import (
            BLACK,
            BOARD_SIZE,
            COL_LABELS,
            EMPTY,
            WHITE,
            GoBoard,
            coord_to_xy,
            xy_to_coord,
        )
    except ImportError:
        try:
            from go_engine import (
                BLACK,
                BOARD_SIZE,
                COL_LABELS,
                EMPTY,
                WHITE,
                GoBoard,
                coord_to_xy,
                xy_to_coord,
            )
        except ImportError:
            # Fallback definitions if go_engine is relocated
            BOARD_SIZE = 10
            COL_LABELS = "ABCDEFGHJK"
            EMPTY = "."
            BLACK = "B"
            WHITE = "W"

            def coord_to_xy(coord: str) -> Tuple[int, int]:
                s = coord.strip().upper()
                col = COL_LABELS.index(s[0])
                row = int(s[1:]) - 1
                return col, row

            def xy_to_coord(x: int, y: int) -> str:
                return f"{COL_LABELS[x]}{y + 1}"

            class GoBoard:  # type: ignore[no-redef]
                def __init__(self, size: int = 10):
                    self.size = size
                    self.grid = [[EMPTY for _ in range(size)] for _ in range(size)]
                    self.current_player = BLACK
                    self.captures = {BLACK: 0, WHITE: 0}
                    self.move_history: List[Dict[str, Any]] = []

                def _rebuild_groups(self) -> None:
                    pass

                def play_move(self, color: str, x: int, y: int, **kwargs: Any) -> Tuple[bool, List[Tuple[int, int]], Optional[str]]:
                    self.grid[y][x] = color
                    return True, [], None


# Ensure GoBoard has convenient helper aliases
if hasattr(GoBoard, "set_stone") is False:
    def _board_set_stone(self: Any, x: int, y: int, color: Optional[str]) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.grid[y][x] = color if color is not None else EMPTY
            if hasattr(self, "_rebuild_groups"):
                self._rebuild_groups()
    setattr(GoBoard, "set_stone", _board_set_stone)

if hasattr(GoBoard, "play") is False:
    def _board_play(self: Any, x: int, y: int, color: str) -> Tuple[bool, List[Tuple[int, int]], Optional[str]]:
        if hasattr(self, "play_move"):
            return self.play_move(color, x, y, enforce_turn=False)
        self.grid[y][x] = color
        return True, [], None
    setattr(GoBoard, "play", _board_play)


# ---------------------------------------------------------------------------
# Data Models for Capturing Showcases
# ---------------------------------------------------------------------------

@dataclass
class TacticalCommentary:
    """Rich pedagogical commentary for a tactical move ply."""
    title: str
    text: str
    tactical_principle: str
    threat_level: str  # CALM, ATARI, WARNING, CRITICAL, CAPTURED, RESOLVED
    badge: str = ""
    japanese_term: str = ""

    def __post_init__(self) -> None:
        if not self.badge:
            self.badge = self.threat_level
        if not self.japanese_term:
            self.japanese_term = self.tactical_principle

    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "text": self.text,
            "tactical_principle": self.tactical_principle,
            "threat_level": self.threat_level,
            "badge": self.badge,
            "japanese_term": self.japanese_term,
        }

    def __getitem__(self, item: str) -> str:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


@dataclass
class ShowcaseStep:
    """Single move ply within a tactical capturing showcase."""
    ply_number: int
    color: str
    coord: Tuple[int, int]
    coord_str: str
    commentary: TacticalCommentary
    captures_expected: int = 0
    resulting_liberties: Optional[int] = None
    state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ply_number": self.ply_number,
            "ply": self.ply_number,
            "color": self.color,
            "coord": list(self.coord),
            "x": self.coord[0],
            "y": self.coord[1],
            "coord_str": self.coord_str,
            "commentary": self.commentary.to_dict(),
            "badge": self.commentary.badge,
            "japanese_term": self.commentary.japanese_term,
            "explanation": self.commentary.text,
            "captures_expected": self.captures_expected,
            "resulting_liberties": self.resulting_liberties,
            "state": self.state or {},
        }

    def __getitem__(self, item: str) -> Any:
        if item in ("ply", "ply_number"):
            return self.ply_number
        if item == "x":
            return self.coord[0]
        if item == "y":
            return self.coord[1]
        if item == "badge":
            return self.commentary.badge
        if item == "japanese_term":
            return self.commentary.japanese_term
        if item == "explanation":
            return self.commentary.text
        if item == "commentary":
            return self.commentary.to_dict()
        if item == "state":
            return self.state if self.state is not None else {}
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except (AttributeError, KeyError):
            return default


@dataclass
class Showcase:
    """Canonical Go Capturing Showcase definition."""
    showcase_id: str
    name: str
    japanese_name: str
    summary: str
    initial_stones: List[Tuple[str, int, int]]  # List of (color, x, y)
    steps: List[ShowcaseStep]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Precomputes exact board state at each ply for UI rendering and server forks."""
        for i, step in enumerate(self.steps, start=1):
            if step.state is None:
                board = self.fork_into_board(ply_index=i)
                step.state = {
                    "board": [
                        [board.grid[y][x] if board.grid[y][x] != EMPTY else None for x in range(BOARD_SIZE)]
                        for y in range(BOARD_SIZE)
                    ],
                    "grid": copy.deepcopy(board.grid),
                    "current_player": board.current_player,
                    "captures": dict(board.captures),
                    "last_move": {
                        "x": step.coord[0],
                        "y": step.coord[1],
                        "color": step.color,
                        "coord": step.coord_str,
                    },
                    "step_count": step.ply_number,
                }

    @property
    def initial_stones_dict(self) -> Dict[str, List[Tuple[int, int]]]:
        """Returns stones partitioned by color: {'B': [...], 'W': [...]}."""
        res: Dict[str, List[Tuple[int, int]]] = {BLACK: [], WHITE: []}
        for color, x, y in self.initial_stones:
            norm = BLACK if color.upper() in ("B", "BLACK") else WHITE
            res[norm].append((x, y))
        return res

    def fork_into_board(self, ply_index: int = 0) -> GoBoard:
        """Creates a fully playable GoBoard instantiated to the state at `ply_index`.

        If ply_index == 0: board contains initial puzzle stones.
        If ply_index > 0: board plays up to ply_index steps sequentially.
        """
        board = GoBoard(size=BOARD_SIZE)

        # 1. Setup initial stones without triggering move validation
        for color, x, y in self.initial_stones:
            norm = BLACK if color.upper() in ("B", "BLACK") else WHITE
            board.grid[y][x] = norm

        if hasattr(board, "_rebuild_groups"):
            board._rebuild_groups()

        # Determine which player moves first
        if self.steps:
            board.current_player = self.steps[0].color
        else:
            board.current_player = BLACK

        # 2. Play forward up to ply_index steps
        clamped_ply = max(0, min(ply_index, len(self.steps)))
        for i in range(clamped_ply):
            step = self.steps[i]
            x, y = step.coord
            # Execute move with strict Go capture mechanics enabled
            board.play_move(step.color, x, y, enforce_turn=False, raise_on_error=False)

        # Set next expected player
        if clamped_ply < len(self.steps):
            board.current_player = self.steps[clamped_ply].color
        else:
            last_color = self.steps[-1].color if self.steps else BLACK
            board.current_player = WHITE if last_color == BLACK else BLACK

        return board

    def to_dict(self) -> Dict[str, Any]:
        """Produces a JSON-serializable representation compatible with UI dashboards and REST endpoints."""
        return {
            "id": self.showcase_id,
            "showcase_id": self.showcase_id,
            "name": self.name,
            "japanese_name": self.japanese_name,
            "japanese_term": self.japanese_name,
            "summary": self.summary,
            "description": self.summary,
            "initial_stones": [
                {"color": color, "x": x, "y": y, "coord": xy_to_coord(x, y)}
                for color, x, y in self.initial_stones
            ],
            "setup": {
                "B": [list(pt) for pt in self.initial_stones_dict[BLACK]],
                "W": [list(pt) for pt in self.initial_stones_dict[WHITE]],
            },
            "steps": [step.to_dict() for step in self.steps],
            "total_plies": len(self.steps),
            "metadata": self.metadata,
        }

    def __getitem__(self, item: str) -> Any:
        if item in ("id", "showcase_id"):
            return self.showcase_id
        if item in ("description", "summary"):
            return self.summary
        if item == "japanese_term":
            return self.japanese_name
        if item == "setup":
            return {
                "B": self.initial_stones_dict[BLACK],
                "W": self.initial_stones_dict[WHITE],
            }
        if item == "steps":
            return [s.to_dict() for s in self.steps]
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except (AttributeError, KeyError):
            return default


# ---------------------------------------------------------------------------
# Canonical Showcase 1: The Snapback (Uttegaeshi / 打って返し)
# ---------------------------------------------------------------------------

def _build_showcase_01_snapback() -> Showcase:
    """Showcase 1: The Snapback (Uttegaeshi / 打って返し).

    White 7-stone inverted U-trap: (3,2),(4,2),(5,2),(3,3),(5,3),(3,4),(5,4).
    Black surrounding wall: (2,2),(2,3),(2,4),(6,2),(6,3),(6,4),(3,1),(4,1),(5,1),(3,5),(4,5),(5,5).
    Ply 1: Black plays (4,3) [E4] (Sacrifice throw-in, mutual atari).
    Ply 2: White takes bait at (4,4) [E5], capturing Black E4. White group reduced to 1 liberty at E4!
    Ply 3: Black strikes back at (4,3) [E4], capturing all 8 White stones!
    """
    initial_stones: List[Tuple[str, int, int]] = []
    # White 7-stone inverted U-trap
    white_u = [(3, 2), (4, 2), (5, 2), (3, 3), (5, 3), (3, 4), (5, 4)]
    for pt in white_u:
        initial_stones.append((WHITE, pt[0], pt[1]))

    # Black surrounding wall
    black_wall = [
        (2, 2), (2, 3), (2, 4),
        (6, 2), (6, 3), (6, 4),
        (3, 1), (4, 1), (5, 1),
        (3, 5), (4, 5), (5, 5),
    ]
    for pt in black_wall:
        initial_stones.append((BLACK, pt[0], pt[1]))

    steps = [
        ShowcaseStep(
            ply_number=1,
            color=BLACK,
            coord=(4, 3),
            coord_str=xy_to_coord(4, 3),  # E4
            commentary=TacticalCommentary(
                title="Sacrifice Throw-In (Suteishi)",
                text=(
                    "Black plunges a single sacrifice stone directly into the eye cavity at E4 (4,3). "
                    "This intentional sacrifice creates an immediate mutual atari: Black has 1 liberty at E5, "
                    "while White's entire 7-stone inverted U-trap is compressed down to 1 single liberty at E5."
                ),
                tactical_principle="捨て石 (Suteishi - Sacrifice Throw-In)",
                threat_level="CRITICAL",
                badge="ATARI",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=2,
            color=WHITE,
            coord=(4, 4),
            coord_str=xy_to_coord(4, 4),  # E5
            commentary=TacticalCommentary(
                title="Taking the Bait (Pon-nuki Trap)",
                text=(
                    "White captures Black's bait stone at E4 by playing at E5 (4,4). "
                    "White gains 1 captured prisoner, but filling this intersection is fatal: "
                    "the newly merged 8-stone White clump is suffocated and now possesses exactly ONE liberty "
                    "remaining on the entire board—back at E4!"
                ),
                tactical_principle="ダメヅマリ (Damezumari - Shortage of Liberties)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=1,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=3,
            color=BLACK,
            coord=(4, 3),
            coord_str=xy_to_coord(4, 3),  # E4
            commentary=TacticalCommentary(
                title="The Snapback Strike (Uttegaeshi)",
                text=(
                    "Snapback! Black immediately strikes back into the vacated E4 (4,3) intersection. "
                    "Because Black captures an entire 8-stone group rather than a single stone, "
                    "the Ko rule does NOT apply. All 8 White stones are wiped off the board in one stroke!"
                ),
                tactical_principle="打って返し (Uttegaeshi - Snapback)",
                threat_level="RESOLVED",
                badge="CAPTURED",
            ),
            captures_expected=8,
            resulting_liberties=4,
        ),
    ]

    return Showcase(
        showcase_id="showcase_01_snapback",
        name="The Snapback",
        japanese_name="打って返し (Uttegaeshi)",
        summary=(
            "Sacrifice a stone into the opponent's eye cavity to create mutual atari, "
            "then immediately recapture all 8 stones after the opponent takes the bait."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Intermediate",
            "category": "Sacrifice Tesuji",
            "stones_captured": 8,
            "target_coordinates": "E4-E5",
        },
    )


# ---------------------------------------------------------------------------
# Canonical Showcase 2: The Zigzag Ladder (Shicho / 征子)
# ---------------------------------------------------------------------------

def _build_showcase_02_ladder() -> Showcase:
    """Showcase 2: The Zigzag Ladder (Shicho / 征子).

    Black anchors at (2,1),(3,1),(1,2), Ladder Catcher at (7,5).
    White target at (2,2).
    15-ply zigzag sequence terminating with White crashing into ladder catcher at (7,5)
    and Black capturing 8 White stones at (6,6).
    """
    initial_stones: List[Tuple[str, int, int]] = [
        (BLACK, 2, 1),  # C2 anchor
        (BLACK, 3, 1),  # D2 anchor
        (BLACK, 1, 2),  # B3 anchor
        (BLACK, 7, 5),  # H6 Ladder Catcher!
        (WHITE, 2, 2),  # C3 Target stone
    ]

    raw_moves = [
        (1, BLACK, (2, 3), "C4", "Initial Atari", "Black strikes at C4, forcing White into diagonal flight.", "当たり (Atari)", "ATARI"),
        (2, WHITE, (3, 2), "D3", "Escape Attempt", "White runs rightward to D3.", "逃げ (Flight)", "WARNING"),
        (3, BLACK, (4, 2), "E3", "Corner Turn Atari", "Black turns the corner at E3, maintaining atari.", "追い込み (Turn)", "ATARI"),
        (4, WHITE, (3, 3), "D4", "Flight Downward", "White flees downward to D4.", "逃走 (Run Down)", "WARNING"),
        (5, BLACK, (3, 4), "D5", "Staircase Block", "Black blocks at D5, holding White in continuous atari.", "封鎖 (Block)", "ATARI"),
        (6, WHITE, (4, 3), "E4", "Flight Rightward", "White flees rightward to E4.", "足掻き (Run Right)", "WARNING"),
        (7, BLACK, (5, 3), "F4", "Corner Turn Atari", "Black turns at F4, keeping White tightly caged.", "追い込み (Turn)", "ATARI"),
        (8, WHITE, (4, 4), "E5", "Flight Downward", "White extends downward to E5.", "逃走 (Run Down)", "WARNING"),
        (9, BLACK, (4, 5), "E6", "Staircase Block", "Black blocks at E6, maintaining the diagonal staircase.", "封鎖 (Block)", "ATARI"),
        (10, WHITE, (5, 4), "F5", "Flight Rightward", "White runs rightward to F5.", "足掻き (Run Right)", "WARNING"),
        (11, BLACK, (6, 4), "G5", "Corner Turn Atari", "Black turns at G5, herding White toward the waiting catcher.", "追い込み (Turn)", "ATARI"),
        (12, WHITE, (5, 5), "F6", "Flight Downward", "White flees down to F6.", "逃走 (Run Down)", "WARNING"),
        (13, BLACK, (5, 6), "F7", "Pre-Catcher Block", "Black blocks at F7, forcing White into the catcher intersection.", "包囲網 (Pre-Catcher)", "ATARI"),
        (14, WHITE, (6, 5), "G6", "Crash into Ladder Catcher", "White runs to G6, crashing directly into Black's waiting ladder catcher at H6 (7,5)! White has only 1 liberty at G7.", "シチョウ当たり激突 (Collision)", "CRITICAL"),
        (15, BLACK, (6, 6), "G7", "The Guillotine Capture", "Black strikes at G7 (6,6), capturing all 8 White ladder stones in a clean sweep!", "征子捕獲 (Ladder Captured!)", "CAPTURED"),
    ]

    steps: List[ShowcaseStep] = []
    for ply_num, col, coord, c_str, title, text, jp_term, badge in raw_moves:
        threat = "RESOLVED" if badge == "CAPTURED" else ("CRITICAL" if badge == "CRITICAL" else ("ATARI" if badge == "ATARI" else "WARNING"))
        caps_exp = 8 if ply_num == 15 else 0
        steps.append(
            ShowcaseStep(
                ply_number=ply_num,
                color=col,
                coord=coord,
                coord_str=c_str,
                commentary=TacticalCommentary(
                    title=title,
                    text=text,
                    tactical_principle=jp_term,
                    threat_level=threat,
                    badge=badge,
                ),
                captures_expected=caps_exp,
            )
        )

    return Showcase(
        showcase_id="showcase_02_ladder",
        name="The Zigzag Ladder",
        japanese_name="征子 (Shicho)",
        summary=(
            "A 15-ply diagonal pursuit driving a fleeing White group across the board into a "
            "pre-positioned ladder catcher at (7,5), culminating in an 8-stone capture at (6,6)."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Advanced",
            "category": "Geometric Pursuit",
            "stones_captured": 8,
            "catcher_coordinate": "H6",
            "capture_coordinate": "G7",
        },
    )


# ---------------------------------------------------------------------------
# Canonical Showcase 3: The Loose Net (Geta / 下駄)
# ---------------------------------------------------------------------------

def _build_showcase_03_geta() -> Showcase:
    """Showcase 3: The Loose Net (Geta / 下駄).

    Black framing stones at (3,3),(3,4),(3,5),(4,3),(5,3).
    White cutting stone at (4,4).
    Ply 1: Black plays Geta net at (5,5).
    Ply 2: White pushes at (4,5).
    Ply 3: Black blocks at (4,6) (Atari).
    Ply 4: White turns at (5,4).
    Ply 5: Black slams door at (6,4), capturing all 3 White stones!
    """
    initial_stones: List[Tuple[str, int, int]] = [
        (BLACK, 3, 3),  # D4
        (BLACK, 3, 4),  # D5
        (BLACK, 3, 5),  # D6
        (BLACK, 4, 3),  # E4
        (BLACK, 5, 3),  # F4
        (WHITE, 4, 4),  # E5 cutting stone
    ]

    steps = [
        ShowcaseStep(
            ply_number=1,
            color=BLACK,
            coord=(5, 5),
            coord_str=xy_to_coord(5, 5),  # F6
            commentary=TacticalCommentary(
                title="The Loose Net (Geta)",
                text=(
                    "Black places the Geta net at F6 (5,5), positioned at a diagonal knight's move distance. "
                    "Black does not touch the White stone directly, but envelops both of White's potential escape paths."
                ),
                tactical_principle="下駄 (Geta - Loose Net)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=2,
        ),
        ShowcaseStep(
            ply_number=2,
            color=WHITE,
            coord=(4, 5),
            coord_str=xy_to_coord(4, 5),  # E6
            commentary=TacticalCommentary(
                title="Pushing Downward",
                text="White attempts to break free by pushing downward to E6 (4,5).",
                tactical_principle="押し出し (Push)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=2,
        ),
        ShowcaseStep(
            ply_number=3,
            color=BLACK,
            coord=(4, 6),
            coord_str=xy_to_coord(4, 6),  # E7
            commentary=TacticalCommentary(
                title="Firm Block (Atari)",
                text=(
                    "Black blocks firmly at E7 (4,6), cutting off downward escape and putting "
                    "White's 2 stones into atari with only 1 liberty at F5 (5,4)."
                ),
                tactical_principle="ブロック当たり (Block Atari)",
                threat_level="CRITICAL",
                badge="ATARI",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=4,
            color=WHITE,
            coord=(5, 4),
            coord_str=xy_to_coord(5, 4),  # F5
            commentary=TacticalCommentary(
                title="Turning to the Flank",
                text="White turns rightward to F5 (5,4) in a desperate attempt to break through the side.",
                tactical_principle="転進 (Flank Pivot)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=5,
            color=BLACK,
            coord=(6, 4),
            coord_str=xy_to_coord(6, 4),  # G5
            commentary=TacticalCommentary(
                title="Slamming the Door",
                text=(
                    "Black slams the door shut at G5 (6,4)! White's liberties are completely exhausted, "
                    "and all 3 White stones are scooped up in capture."
                ),
                tactical_principle="下駄捕獲 (Net Capture Complete)",
                threat_level="RESOLVED",
                badge="CAPTURED",
            ),
            captures_expected=3,
            resulting_liberties=3,
        ),
    ]

    return Showcase(
        showcase_id="showcase_03_geta",
        name="The Loose Net",
        japanese_name="下駄 (Geta)",
        summary=(
            "A loose net played at a diagonal knight's move distance that traps an escaping "
            "cutting stone without direct contact, preventing escape and capturing 3 stones."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Beginner-Intermediate",
            "category": "Net Tesuji",
            "stones_captured": 3,
            "net_coordinate": "F6",
        },
    )


# ---------------------------------------------------------------------------
# Canonical Showcase 4: The Crane's Nest (Tsuru no Sugomori / 鶴の巣ごもり)
# ---------------------------------------------------------------------------

def _build_showcase_04_cranes_nest() -> Showcase:
    """Showcase 4: The Crane's Nest (Tsuru no Sugomori / 鶴の巣ごもり).

    White escaping string: (4,3),(5,3),(6,3).
    Black wings: (3,3),(7,3),(4,2),(5,2),(6,2),(3,4),(7,4),(4,5),(6,5).
    Central wedge at (5,4), squeeze at (6,4), final capture of cutting stones!
    """
    initial_stones: List[Tuple[str, int, int]] = [
        # White escaping string
        (WHITE, 4, 3),  # E4
        (WHITE, 5, 3),  # F4
        (WHITE, 6, 3),  # G4
        # Black wings and perimeter
        (BLACK, 3, 3),  # D4
        (BLACK, 7, 3),  # H4
        (BLACK, 4, 2),  # E3
        (BLACK, 5, 2),  # F3
        (BLACK, 6, 2),  # G3
        (BLACK, 3, 4),  # D5
        (BLACK, 7, 4),  # H5
        (BLACK, 4, 5),  # E6
        (BLACK, 6, 5),  # G6
    ]

    steps = [
        ShowcaseStep(
            ply_number=1,
            color=BLACK,
            coord=(5, 4),
            coord_str=xy_to_coord(5, 4),  # F5
            commentary=TacticalCommentary(
                title="The Central Wedge (Warikomi)",
                text=(
                    "Black plunges a wedge stone directly into F5 (5,4) at the throat of White's 3 cutting stones. "
                    "This splits White's escape channels, reducing White's liberties to E5 (4,4) and G5 (6,4)."
                ),
                tactical_principle="割り込み (Warikomi - Wedge)",
                threat_level="CRITICAL",
                badge="ATARI",
            ),
            captures_expected=0,
            resulting_liberties=2,
        ),
        ShowcaseStep(
            ply_number=2,
            color=WHITE,
            coord=(4, 4),
            coord_str=xy_to_coord(4, 4),  # E5
            commentary=TacticalCommentary(
                title="Desperate Breakout Attempt",
                text=(
                    "White pushes at E5 (4,4) attempting to break through Black's wedge. "
                    "However, connecting to E5 traps White: the expanded 4-stone White string "
                    "is compressed into atari with only 1 liberty remaining at G5 (6,4)!"
                ),
                tactical_principle="自滅の押し (Self-Choking Push)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=3,
            color=BLACK,
            coord=(6, 4),
            coord_str=xy_to_coord(6, 4),  # G5
            commentary=TacticalCommentary(
                title="Crane's Nest Squeeze & Capture",
                text=(
                    "The Crane's Nest clamp snaps shut! Black plays G5 (6,4), completely enclosing "
                    "the escaping string. White has 0 liberties left, and the cutting stones "
                    "are captured inside the nest."
                ),
                tactical_principle="鶴の巣ごもり (Tsuru no Sugomori - Crane's Nest)",
                threat_level="RESOLVED",
                badge="CAPTURED",
            ),
            captures_expected=4,
            resulting_liberties=4,
        ),
    ]

    return Showcase(
        showcase_id="showcase_04_cranes_nest",
        name="The Crane's Nest",
        japanese_name="鶴の巣ごもり (Tsuru no Sugomori)",
        summary=(
            "A classical tesuji capturing an escaping cutting string trapped between Black wings "
            "via an inside central wedge at (5,4) and bilateral squeeze at (6,4)."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Intermediate-Advanced",
            "category": "Squeeze Tesuji",
            "stones_captured": 4,
            "wedge_coordinate": "F5",
            "squeeze_coordinate": "G5",
        },
    )


# ---------------------------------------------------------------------------
# Canonical Showcase 5: The Double-Atari Fork (Ryō-Atari / 両アタリ)
# ---------------------------------------------------------------------------

def _build_showcase_05_double_atari() -> Showcase:
    """Showcase 5: The Double-Atari Fork (Ryō-Atari / 両アタリ).

    White Group A at (3,4), Group B at (5,4).
    Black net: (3,3),(2,4),(5,3),(6,4),(4,3).
    Ply 1: Black fork at (4,4) [E5].
    Ply 2: White defends A at (3,5).
    Ply 3: Black captures B at (5,5), taking stone at (5,4).
    """
    initial_stones: List[Tuple[str, int, int]] = [
        (WHITE, 3, 4),  # D5 (Group A)
        (WHITE, 5, 4),  # F5 (Group B)
        (BLACK, 3, 3),  # D4
        (BLACK, 2, 4),  # C5
        (BLACK, 5, 3),  # F4
        (BLACK, 6, 4),  # G5
        (BLACK, 4, 3),  # E4
    ]

    steps = [
        ShowcaseStep(
            ply_number=1,
            color=BLACK,
            coord=(4, 4),
            coord_str=xy_to_coord(4, 4),  # E5
            commentary=TacticalCommentary(
                title="The Double-Atari Fork (Ryō-Atari)",
                text=(
                    "Black strikes at the central junction at E5 (4,4), simultaneously placing "
                    "both White Group A at D5 (3,4) and White Group B at F5 (5,4) into atari. "
                    "White cannot defend both threats in a single move."
                ),
                tactical_principle="両アタリ (Ryō-Atari - Double Atari)",
                threat_level="CRITICAL",
                badge="ATARI",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=2,
            color=WHITE,
            coord=(3, 5),
            coord_str=xy_to_coord(3, 5),  # D6
            commentary=TacticalCommentary(
                title="Defending Group A",
                text=(
                    "White chooses to defend Group A by extending downward to D6 (3,5), "
                    "expanding its liberties from 1 to 3, but leaving Group B at F5 (5,4) undefended in atari."
                ),
                tactical_principle="選択防御 (Selective Defense)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=3,
            color=BLACK,
            coord=(5, 5),
            coord_str=xy_to_coord(5, 5),  # F6
            commentary=TacticalCommentary(
                title="Capturing Group B",
                text=(
                    "Black executes the inevitable capture, playing F6 (5,5) to wipe out "
                    "White Group B at F5 (5,4). Black converts the tactical fork into material gain!"
                ),
                tactical_principle="フォーク捕獲 (Fork Capture Realized)",
                threat_level="RESOLVED",
                badge="CAPTURED",
            ),
            captures_expected=1,
            resulting_liberties=3,
        ),
    ]

    return Showcase(
        showcase_id="showcase_05_double_atari",
        name="The Double-Atari Fork",
        japanese_name="両アタリ (Ryō-Atari)",
        summary=(
            "A tactical fork simultaneously threatening two distinct opponent groups, "
            "guaranteeing the capture of at least one group regardless of defensive response."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Beginner",
            "category": "Fork Tesuji",
            "stones_captured": 1,
            "fork_coordinate": "E5",
        },
    )


# ---------------------------------------------------------------------------
# Canonical Showcase 6: Under the Stones (Ishi-no-Shita / 石の下)
# ---------------------------------------------------------------------------

def _build_showcase_06_ishi_no_shita() -> Showcase:
    """Showcase 6: Under the Stones (Ishi-no-Shita / 石の下).

    Black 4-stone clump at (3,8),(4,8),(3,9),(4,9).
    White cutting pair at (2,8),(2,9), surrounding at (5,9),(3,7),(4,7).
    Black enclosure at (1,8),(1,9),(2,7).
    Ply 1: White captures Black 4 stones at (5,8).
    Ply 2: Black strikes into vacated cavity at (3,8) [D9] (Atari on White cutting stones).
    Ply 3: White defends outside at (5,7).
    Ply 4: Black captures White cutting stones at (3,9) [D10]!
    """
    initial_stones: List[Tuple[str, int, int]] = [
        # Black 4-stone clump
        (BLACK, 3, 8),  # D9
        (BLACK, 4, 8),  # E9
        (BLACK, 3, 9),  # D10
        (BLACK, 4, 9),  # E10
        # White cutting pair
        (WHITE, 2, 8),  # C9
        (WHITE, 2, 9),  # C10
        # White surrounding stones
        (WHITE, 5, 9),  # F10
        (WHITE, 3, 7),  # D8
        (WHITE, 4, 7),  # E8
        # Black outside enclosure
        (BLACK, 1, 8),  # B9
        (BLACK, 1, 9),  # B10
        (BLACK, 2, 7),  # C8
    ]

    steps = [
        ShowcaseStep(
            ply_number=1,
            color=WHITE,
            coord=(5, 8),
            coord_str=xy_to_coord(5, 8),  # F9
            commentary=TacticalCommentary(
                title="White Captures Black Clump",
                text=(
                    "White plays F9 (5,8), capturing Black's entire 4-stone clump at D9-E10. "
                    "However, this was an intentional sacrifice by Black: clearing these 4 stones "
                    "opens a 4-intersection hollow right behind White's cutting pair."
                ),
                tactical_principle="石の下布石 (Sacrifice Cavity Setup)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=4,
            resulting_liberties=2,
        ),
        ShowcaseStep(
            ply_number=2,
            color=BLACK,
            coord=(3, 8),
            coord_str=xy_to_coord(3, 8),  # D9
            commentary=TacticalCommentary(
                title="Strike into Vacated Cavity",
                text=(
                    "Black strikes immediately back into the freshly vacated cavity at D9 (3,8)! "
                    "This counter-strike puts White's cutting pair at C9-C10 (2,8)-(2,9) into atari, "
                    "leaving them with only 1 liberty at D10 (3,9)."
                ),
                tactical_principle="石の下急所 (Under the Stones Vital Point)",
                threat_level="CRITICAL",
                badge="ATARI",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=3,
            color=WHITE,
            coord=(5, 7),
            coord_str=xy_to_coord(5, 7),  # F8
            commentary=TacticalCommentary(
                title="White Outside Defense",
                text=(
                    "White realizes the cutting pair cannot be salvaged and plays an outside "
                    "defensive extension at F8 (5,7) to protect exterior territory."
                ),
                tactical_principle="外壁補強 (Exterior Reinforcement)",
                threat_level="WARNING",
                badge="WARNING",
            ),
            captures_expected=0,
            resulting_liberties=1,
        ),
        ShowcaseStep(
            ply_number=4,
            color=BLACK,
            coord=(3, 9),
            coord_str=xy_to_coord(3, 9),  # D10
            commentary=TacticalCommentary(
                title="Capture Under the Stones!",
                text=(
                    "Black strikes at D10 (3,9), capturing White's cutting pair! "
                    "By resurrecting stones from inside the opponent's captured territory, "
                    "Black achieves total victory in the corner through Ishi-no-Shita."
                ),
                tactical_principle="石の下捕獲 (Under the Stones Complete)",
                threat_level="RESOLVED",
                badge="CAPTURED",
            ),
            captures_expected=2,
            resulting_liberties=3,
        ),
    ]

    return Showcase(
        showcase_id="showcase_06_ishi_no_shita",
        name="Under the Stones",
        japanese_name="石の下 (Ishi-no-Shita)",
        summary=(
            "A profound sacrifice technique where Black allows a 4-stone clump to be captured, "
            "then immediately strikes into the freshly vacated cavity to capture White's cutting stones."
        ),
        initial_stones=initial_stones,
        steps=steps,
        metadata={
            "difficulty": "Master",
            "category": "Cavity Resurgence Tesuji",
            "stones_captured": 2,
            "cavity_coordinate": "D9",
            "capture_coordinate": "D10",
        },
    )


# ---------------------------------------------------------------------------
# Module Level Singletons & Registries
# ---------------------------------------------------------------------------

showcase_01_snapback: Showcase = _build_showcase_01_snapback()
showcase_02_ladder: Showcase = _build_showcase_02_ladder()
showcase_03_geta: Showcase = _build_showcase_03_geta()
showcase_04_cranes_nest: Showcase = _build_showcase_04_cranes_nest()
showcase_05_double_atari: Showcase = _build_showcase_05_double_atari()
showcase_06_ishi_no_shita: Showcase = _build_showcase_06_ishi_no_shita()

ALL_SHOWCASES: List[Showcase] = [
    showcase_01_snapback,
    showcase_02_ladder,
    showcase_03_geta,
    showcase_04_cranes_nest,
    showcase_05_double_atari,
    showcase_06_ishi_no_shita,
]

# Canonical lookup mapping canonical IDs and convenient short aliases
CANONICAL_SHOWCASES: Dict[str, Showcase] = {
    # Full IDs
    "showcase_01_snapback": showcase_01_snapback,
    "showcase_02_ladder": showcase_02_ladder,
    "showcase_03_geta": showcase_03_geta,
    "showcase_04_cranes_nest": showcase_04_cranes_nest,
    "showcase_05_double_atari": showcase_05_double_atari,
    "showcase_06_ishi_no_shita": showcase_06_ishi_no_shita,
    # Short aliases
    "snapback": showcase_01_snapback,
    "ladder": showcase_02_ladder,
    "geta": showcase_03_geta,
    "cranes_nest": showcase_04_cranes_nest,
    "crane_nest": showcase_04_cranes_nest,
    "double_atari": showcase_05_double_atari,
    "ishi_no_shita": showcase_06_ishi_no_shita,
    # Number aliases
    "1": showcase_01_snapback,
    "2": showcase_02_ladder,
    "3": showcase_03_geta,
    "4": showcase_04_cranes_nest,
    "5": showcase_05_double_atari,
    "6": showcase_06_ishi_no_shita,
}


# ---------------------------------------------------------------------------
# Public Helper Functions
# ---------------------------------------------------------------------------

def list_showcases() -> List[Dict[str, Any]]:
    """Returns metadata summary list of all 6 canonical capturing showcases."""
    return [
        {
            "id": sc.showcase_id,
            "showcase_id": sc.showcase_id,
            "name": sc.name,
            "japanese_name": sc.japanese_name,
            "summary": sc.summary,
            "total_plies": len(sc.steps),
            "difficulty": sc.metadata.get("difficulty", "Standard"),
            "category": sc.metadata.get("category", "Capturing Tesuji"),
        }
        for sc in ALL_SHOWCASES
    ]


def get_showcase(showcase_id: str) -> Showcase:
    """Retrieves a Showcase by canonical id or alias.

    Raises KeyError if showcase_id is unknown.
    """
    cleaned = str(showcase_id).strip().lower()
    if cleaned in CANONICAL_SHOWCASES:
        return CANONICAL_SHOWCASES[cleaned]
    raise KeyError(
        f"Showcase '{showcase_id}' not found. Available showcases: {list(CANONICAL_SHOWCASES.keys())}"
    )


def build_showcase_board_at_step(showcase_id: str, step_index: int) -> GoBoard:
    """Instantiates a playable GoBoard matching the exact position of `showcase_id` at `step_index`."""
    sc = get_showcase(showcase_id)
    return sc.fork_into_board(ply_index=step_index)
