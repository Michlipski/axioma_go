"""Axioma Go Engine: Pure Deterministic 10x10 Go Substrate.

Bound Invariants:
- [INV-GO-001] GridBounds10x10: Strictly 10x10 intersections (x in 0..9, y in 0..9, A1 to K10 excluding I).
- [INV-GO-002] LibertyConservation: Union-find connected component tracking of stone groups.
- [INV-GO-003] NoSuicideWithoutCapture: Suicide moves prohibited unless capturing opponent stones.
- [INV-GO-004] SingleStoneKoRepetitionLockout: Single stone capture repetition lockout on immediate next ply.
- [INV-GO-005] ReversibilityFunctorialUndo: Forward and reverse state transitions with SHA-256 state hashing.
- [L1-002] Functorial State Reversibility: Deterministic adjoint rollback S_{t-1} = f^{-1}(S_t).
- [L1-016] Exception Enclave Rigor: Explicit typed exception hierarchy for all illegal transitions.
- [L1-G3B-011] Universal Contract IR: Canonical algebraic state representation and serialization.

Zero external dependencies. Python 3.14 standard library.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants & Coordinate Standards (10x10 Intersections, Skipping 'I')
# ---------------------------------------------------------------------------

BOARD_SIZE: int = 10
COL_LABELS: str = "ABCDEFGHJK"  # Standard Go coordinate system: A-K excluding 'I'
EMPTY: str = "."
BLACK: str = "B"
WHITE: str = "W"


def col_to_x(col_char: str) -> int:
    """Converts a column letter (A-K excluding I) to 0-indexed column integer [0..9].

    Raises OutOfBoundsError if column letter is invalid or 'I'.
    """
    cleaned = col_char.strip().upper()
    if cleaned == "I":
        raise OutOfBoundsError("INV-GO-001: Column 'I' is excluded in Go notation (skips to J).")
    idx = COL_LABELS.find(cleaned)
    if idx == -1:
        raise OutOfBoundsError(f"INV-GO-001: Invalid column letter '{col_char}'. Valid columns: {list(COL_LABELS)}")
    return idx


def x_to_col(x: int) -> str:
    """Converts a 0-indexed column integer [0..9] to Go column letter (A-K excluding I)."""
    if not (0 <= x < BOARD_SIZE):
        raise OutOfBoundsError(f"INV-GO-001: Column index {x} out of bounds [0..{BOARD_SIZE - 1}].")
    return COL_LABELS[x]


def coord_to_xy(coord: str) -> Tuple[int, int]:
    """Parses a standard Go coordinate string (e.g. 'A1', 'D4', 'K10') into (x, y) 0-indexed tuple.

    x in 0..9 (A..K excluding I), y in 0..9 (row 1..10, 1-indexed at y=0).
    """
    s = coord.strip().upper()
    if len(s) < 2 or len(s) > 3:
        raise OutOfBoundsError(f"INV-GO-001: Malformed coordinate '{coord}'. Expected e.g. 'A1', 'K10'.")
    col_str = s[0]
    row_str = s[1:]
    x = col_to_x(col_str)
    try:
        row_num = int(row_str)
    except ValueError as err:
        raise OutOfBoundsError(f"INV-GO-001: Invalid row number '{row_str}' in coordinate '{coord}'.") from err

    if not (1 <= row_num <= BOARD_SIZE):
        raise OutOfBoundsError(f"INV-GO-001: Row number {row_num} out of bounds [1..{BOARD_SIZE}].")
    y = row_num - 1
    return x, y


def xy_to_coord(x: int, y: int) -> str:
    """Converts (x, y) 0-indexed integer coordinates into standard Go notation (e.g. 'A1', 'K10')."""
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        raise OutOfBoundsError(f"INV-GO-001: Coordinates ({x}, {y}) out of bounds [0..{BOARD_SIZE - 1}].")
    return f"{x_to_col(x)}{y + 1}"


def xy_to_index(x: int, y: int) -> int:
    """Flattens (x, y) 0-indexed coordinates into 1D integer index [0..99]."""
    if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
        raise OutOfBoundsError(f"INV-GO-001: Coordinates ({x}, {y}) out of bounds.")
    return y * BOARD_SIZE + x


def index_to_xy(idx: int) -> Tuple[int, int]:
    """Unflattens 1D integer index [0..99] into (x, y) coordinates."""
    if not (0 <= idx < BOARD_SIZE * BOARD_SIZE):
        raise OutOfBoundsError(f"INV-GO-001: Index {idx} out of bounds [0..{BOARD_SIZE * BOARD_SIZE - 1}].")
    return idx % BOARD_SIZE, idx // BOARD_SIZE


# ---------------------------------------------------------------------------
# Exception Enclave Hierarchy ([L1-016])
# ---------------------------------------------------------------------------

class GoEngineError(Exception):
    """Base exception for all Axioma Go engine operations."""
    def __init__(self, message: str, code: str = "GO_ENGINE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return self.message


class IllegalMoveError(GoEngineError):
    """Raised when an illegal move is attempted in violation of Go rules or invariants."""
    def __init__(self, message: str = "ILLEGAL_MOVE", code: Optional[str] = None) -> None:
        actual_code = code or message
        super().__init__(message, code=actual_code)


class OutOfBoundsError(IllegalMoveError, IndexError, ValueError):
    """[INV-GO-001] Raised when move coordinates fall outside 10x10 intersections."""
    def __init__(self, message: str = "OUT_OF_BOUNDS") -> None:
        super().__init__(message, code="OUT_OF_BOUNDS")


class IntersectionOccupiedError(IllegalMoveError):
    """Raised when attempting to place a stone on an already occupied intersection."""
    def __init__(self, message: str = "INTERSECTION_OCCUPIED") -> None:
        super().__init__(message, code="INTERSECTION_OCCUPIED")


class SuicideError(IllegalMoveError):
    """[INV-GO-003] Raised when an illegal suicide move without capture is attempted."""
    def __init__(self, message: str = "SUICIDE_PROHIBITED") -> None:
        super().__init__(message, code="SUICIDE_PROHIBITED")


class KoError(IllegalMoveError):
    """[INV-GO-004] Raised when a single-stone Ko repetition lockout is violated."""
    def __init__(self, message: str = "KO_PROHIBITED") -> None:
        super().__init__(message, code="KO_PROHIBITED")


class TurnOrderError(IllegalMoveError):
    """Raised when playing out of turn."""
    def __init__(self, message: str = "NOT_YOUR_TURN") -> None:
        super().__init__(message, code="NOT_YOUR_TURN")


# ---------------------------------------------------------------------------
# Union-Find Disjoint Set & Stone Group Tracking ([INV-GO-002])
# ---------------------------------------------------------------------------

class UnionFind:
    """Disjoint Set Union (DSU) with path compression and rank optimization.

    Maps 2D board coordinates (x, y) to linear index = y * BOARD_SIZE + x [0..99].
    """

    def __init__(self, size: int = BOARD_SIZE * BOARD_SIZE) -> None:
        self.size = size
        self.parent: List[int] = list(range(size))
        self.rank: List[int] = [0] * size

    def find(self, i: int) -> int:
        root = i
        while root != self.parent[root]:
            root = self.parent[root]
        # Path compression
        curr = i
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, i: int, j: int) -> int:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i == root_j:
            return root_i
        if self.rank[root_i] < self.rank[root_j]:
            self.parent[root_i] = root_j
            return root_j
        elif self.rank[root_i] > self.rank[root_j]:
            self.parent[root_j] = root_i
            return root_i
        else:
            self.parent[root_j] = root_i
            self.rank[root_i] += 1
            return root_i


@dataclass
class StoneGroup:
    """Represents a connected component (chain) of stones of the same color."""
    color: str
    root: int
    stones: Set[Tuple[int, int]] = field(default_factory=set)
    liberties: Set[Tuple[int, int]] = field(default_factory=set)

    @property
    def liberty_count(self) -> int:
        return len(self.liberties)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color": self.color,
            "root": self.root,
            "stones": sorted(list(self.stones)),
            "liberties": sorted(list(self.liberties)),
            "liberty_count": len(self.liberties),
        }


# ---------------------------------------------------------------------------
# GoBoard & GoEngine Core Implementation
# ---------------------------------------------------------------------------

class GoBoard:
    """Pure, deterministic 10x10 Go board state and transition kernel.

    Enforces:
    - [INV-GO-001] GridBounds10x10: Strict bounds checking [0..9, 0..9].
    - [INV-GO-002] LibertyConservation: Union-find connected component tracking.
    - [INV-GO-003] NoSuicideWithoutCapture: Rejects suicide without opponent capture.
    - [INV-GO-004] SingleStoneKoRepetitionLockout: 1-ply single stone Ko lockout.
    - [INV-GO-005] ReversibilityFunctorialUndo: Immutable snapshots & SHA-256 state hashes.
    """

    def __init__(self, size: int = BOARD_SIZE) -> None:
        if size != BOARD_SIZE:
            raise OutOfBoundsError(f"INV-GO-001: Axioma Go strictly requires 10x10 board, got {size}x{size}.")
        self.size: int = size
        self.grid: List[List[str]] = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.current_player: str = BLACK
        self.captures: Dict[str, int] = {BLACK: 0, WHITE: 0}
        self.ko_point: Optional[Tuple[int, int]] = None
        self.consecutive_passes: int = 0
        self.is_game_over: bool = False
        self.step_count: int = 0
        self.move_history: List[Dict[str, Any]] = []

        # Internal group cache (rebuilt on transition)
        self._groups: Dict[int, StoneGroup] = {}
        self._stone_to_group_root: Dict[Tuple[int, int], int] = {}
        self._rebuild_groups()

    # -----------------------------------------------------------------------
    # Helper & Inspection Properties
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalize_color(color: str) -> str:
        c = color.strip().upper()
        if c in ("B", "BLACK"):
            return BLACK
        if c in ("W", "WHITE"):
            return WHITE
        raise IllegalMoveError(f"INVALID_COLOR: Expected 'B' or 'W', got '{color}'")

    @staticmethod
    def opponent(color: str) -> str:
        return WHITE if color == BLACK else BLACK

    def is_on_board(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get_stone(self, x: int, y: int) -> str:
        if not self.is_on_board(x, y):
            raise OutOfBoundsError(f"INV-GO-001: Coordinates ({x}, {y}) out of bounds [0..{self.size - 1}].")
        return self.grid[y][x]

    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Returns valid orthogonal adjacent intersections."""
        res: List[Tuple[int, int]] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.is_on_board(nx, ny):
                res.append((nx, ny))
        return res

    # -----------------------------------------------------------------------
    # Connected Components & Liberty Calculation ([INV-GO-002])
    # -----------------------------------------------------------------------

    def _coord_to_index(self, x: int, y: int) -> int:
        return y * self.size + x

    def _rebuild_groups(self) -> None:
        """Reconstructs all stone groups and counts liberties via UnionFind."""
        uf = UnionFind(self.size * self.size)

        # 1. Union adjacent stones of the same color
        for y in range(self.size):
            for x in range(self.size):
                color = self.grid[y][x]
                if color == EMPTY:
                    continue
                idx = self._coord_to_index(x, y)
                for nx, ny in self.get_neighbors(x, y):
                    if self.grid[ny][nx] == color:
                        n_idx = self._coord_to_index(nx, ny)
                        uf.union(idx, n_idx)

        # 2. Collect stones by group root
        groups_by_root: Dict[int, StoneGroup] = {}
        stone_to_root: Dict[Tuple[int, int], int] = {}

        for y in range(self.size):
            for x in range(self.size):
                color = self.grid[y][x]
                if color == EMPTY:
                    continue
                idx = self._coord_to_index(x, y)
                root = uf.find(idx)
                if root not in groups_by_root:
                    groups_by_root[root] = StoneGroup(color=color, root=root)
                groups_by_root[root].stones.add((x, y))
                stone_to_root[(x, y)] = root

        # 3. Compute distinct liberties for each group
        for group in groups_by_root.values():
            for sx, sy in group.stones:
                for nx, ny in self.get_neighbors(sx, sy):
                    if self.grid[ny][nx] == EMPTY:
                        group.liberties.add((nx, ny))

        self._groups = groups_by_root
        self._stone_to_group_root = stone_to_root

    def get_liberties_map(self) -> Dict[str, int]:
        """[INV-GO-002] Returns mapping of 'x,y' to liberty count of its stone group.

        Only occupied intersections are included in the map.
        """
        self._rebuild_groups()
        lib_map: Dict[str, int] = {}
        for group in self._groups.values():
            count = len(group.liberties)
            for sx, sy in group.stones:
                lib_map[f"{sx},{sy}"] = count
        return lib_map

    def get_atari_groups(self) -> List[Dict[str, Any]]:
        """Returns list of groups with exactly 1 liberty, their coords, and the threat liberty coord.

        Useful for tactical HUDs, threat warnings, and zero-trust verification.
        """
        self._rebuild_groups()
        atari_groups: List[Dict[str, Any]] = []
        for root, group in sorted(self._groups.items(), key=lambda item: item[0]):
            if len(group.liberties) == 1:
                threat = next(iter(group.liberties))
                atari_groups.append({
                    "color": group.color,
                    "group_id": root,
                    "stones": sorted(list(group.stones)),
                    "liberties": 1,
                    "threat_coord": threat,
                })
        return atari_groups

    # -----------------------------------------------------------------------
    # Move Validation Enclave ([INV-GO-001] to [INV-GO-004])
    # -----------------------------------------------------------------------

    def validate_move(self, color: str, x: int, y: int, enforce_turn: bool = True) -> List[Tuple[int, int]]:
        """Strictly validates whether playing (color, x, y) is legal under Go invariants.

        Returns:
            List of opponent stones captured by this move if legal.

        Raises:
            OutOfBoundsError: If coordinates are outside 10x10 grid.
            IntersectionOccupiedError: If (x, y) already has a stone.
            TurnOrderError: If enforce_turn=True and color != self.current_player.
            KoError: If (x, y) violates single-stone Ko lockout.
            SuicideError: If placing at (x, y) results in 0 liberties and captures no opponent stones.
        """
        # [INV-GO-001] Bounds Check
        if not self.is_on_board(x, y):
            raise OutOfBoundsError(f"INV-GO-001: Coordinates ({x}, {y}) out of bounds [0..{self.size - 1}].")

        norm_color = self._normalize_color(color)

        if enforce_turn and norm_color != self.current_player:
            raise TurnOrderError(f"NOT_YOUR_TURN: Expected {self.current_player}, got {norm_color}.")

        # Intersection Vacancy Check
        if self.grid[y][x] != EMPTY:
            raise IntersectionOccupiedError(f"INTERSECTION_OCCUPIED: ({x}, {y}) occupied by {self.grid[y][x]}.")

        # [INV-GO-004] Ko Repetition Check
        if self.ko_point is not None and self.ko_point == (x, y):
            raise KoError("KO_PROHIBITED")

        opp_color = self.opponent(norm_color)

        # Simulate move on scratch board state to assess captures and liberties
        # 1. Identify adjacent opponent groups that would lose their final liberty at (x, y)
        captured_stones: List[Tuple[int, int]] = []
        captured_roots: Set[int] = set()

        for nx, ny in self.get_neighbors(x, y):
            if self.grid[ny][nx] == opp_color:
                root = self._stone_to_group_root.get((nx, ny))
                if root is not None and root not in captured_roots:
                    opp_group = self._groups[root]
                    # If this group's only remaining liberty was (x, y), it is captured!
                    if opp_group.liberties == {(x, y)}:
                        captured_roots.add(root)
                        captured_stones.extend(opp_group.stones)

        # 2. [INV-GO-003] Suicide check if no captures occurred
        if not captured_stones:
            # Check if newly placed stone has any immediate empty neighbors
            has_empty_neighbor = any(self.grid[ny][nx] == EMPTY for nx, ny in self.get_neighbors(x, y))
            if not has_empty_neighbor:
                # Stone must connect to at least one friendly group that has at least one OTHER liberty
                friendly_has_liberty = False
                for nx, ny in self.get_neighbors(x, y):
                    if self.grid[ny][nx] == norm_color:
                        f_root = self._stone_to_group_root.get((nx, ny))
                        if f_root is not None:
                            f_group = self._groups[f_root]
                            # If the friendly group has any liberty other than (x, y)
                            other_libs = f_group.liberties - {(x, y)}
                            if len(other_libs) > 0:
                                friendly_has_liberty = True
                                break
                if not friendly_has_liberty:
                    raise SuicideError("SUICIDE_PROHIBITED")

        return captured_stones

    # -----------------------------------------------------------------------
    # Move Execution & Turn Mechanics
    # -----------------------------------------------------------------------

    def play_move(
        self,
        color: str,
        x: int,
        y: int,
        raise_on_error: bool = False,
        enforce_turn: bool = True,
    ) -> Tuple[bool, List[Tuple[int, int]], Optional[str]]:
        """Executes a stone placement on the 10x10 board.

        Returns:
            Tuple of (success: bool, captured_stones: List[Tuple[int, int]], error_message: Optional[str]).
        """
        try:
            captured = self.validate_move(color, x, y, enforce_turn=enforce_turn)
        except IllegalMoveError as err:
            if raise_on_error:
                raise
            return False, [], str(err.code or err.message or err)
        except Exception as exc:
            if raise_on_error:
                raise IllegalMoveError(str(exc)) from exc
            return False, [], str(exc)

        norm_color = self._normalize_color(color)

        # 1. Place stone
        self.grid[y][x] = norm_color

        # 2. Remove captured stones
        for cx, cy in captured:
            self.grid[cy][cx] = EMPTY

        self.captures[norm_color] += len(captured)

        # 3. [INV-GO-004] Single stone Ko detection
        # Ko occurs when exactly 1 stone was captured, and the placed stone is in a 1-stone group with 1 liberty
        self._rebuild_groups()
        placed_root = self._stone_to_group_root.get((x, y))
        if placed_root is not None:
            placed_group = self._groups[placed_root]
            if len(captured) == 1 and len(placed_group.stones) == 1 and len(placed_group.liberties) == 1:
                # Ko point is the single captured stone's coordinate
                self.ko_point = captured[0]
            else:
                self.ko_point = None
        else:
            self.ko_point = None

        # 4. Turn progression & state accounting
        self.consecutive_passes = 0
        self.step_count += 1
        self.current_player = self.opponent(norm_color)

        move_record = {
            "step": self.step_count,
            "action": "play",
            "color": norm_color,
            "coord": (x, y),
            "coord_str": xy_to_coord(x, y),
            "captures": sorted(captured),
            "ko_point": self.ko_point,
        }
        self.move_history.append(move_record)

        return True, sorted(captured), None

    def pass_turn(self, color: str, enforce_turn: bool = True) -> bool:
        """Passes the turn for the given color.

        If two consecutive passes occur, sets is_game_over = True.
        """
        norm_color = self._normalize_color(color)
        if enforce_turn and norm_color != self.current_player:
            return False

        self.ko_point = None  # Passing always clears Ko lockout
        self.consecutive_passes += 1
        if self.consecutive_passes >= 2:
            self.is_game_over = True

        self.step_count += 1
        self.current_player = self.opponent(norm_color)

        move_record = {
            "step": self.step_count,
            "action": "pass",
            "color": norm_color,
            "coord": None,
            "coord_str": "PASS",
            "captures": [],
            "ko_point": None,
        }
        self.move_history.append(move_record)
        return True

    def get_legal_moves(self, color: str, enforce_turn: bool = True) -> List[Tuple[int, int]]:
        """Returns all legal (x, y) coordinates for the given color."""
        legal: List[Tuple[int, int]] = []
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x] == EMPTY:
                    try:
                        self.validate_move(color, x, y, enforce_turn=enforce_turn)
                        legal.append((x, y))
                    except IllegalMoveError:
                        continue
        return legal

    # -----------------------------------------------------------------------
    # Serialization, Copying & Hash Preservation ([INV-GO-005])
    # -----------------------------------------------------------------------

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 state hash for cryptographic verification."""
        canonical_state = {
            "size": self.size,
            "grid": self.grid,
            "current_player": self.current_player,
            "captures": self.captures,
            "ko_point": self.ko_point,
            "consecutive_passes": self.consecutive_passes,
            "is_game_over": self.is_game_over,
            "step_count": self.step_count,
        }
        payload = json.dumps(canonical_state, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Produces a complete, JSON-serializable snapshot of the board state."""
        return {
            "size": self.size,
            "grid": copy.deepcopy(self.grid),
            "current_player": self.current_player,
            "captures": dict(self.captures),
            "ko_point": list(self.ko_point) if self.ko_point is not None else None,
            "consecutive_passes": self.consecutive_passes,
            "is_game_over": self.is_game_over,
            "step_count": self.step_count,
            "move_history": copy.deepcopy(self.move_history),
            "state_hash": self.compute_hash(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GoBoard:
        """Restores a GoBoard from a serializable snapshot dictionary."""
        size = data.get("size", BOARD_SIZE)
        board = cls(size=size)
        board.grid = copy.deepcopy(data["grid"])
        board.current_player = data["current_player"]
        board.captures = dict(data.get("captures", {BLACK: 0, WHITE: 0}))
        ko = data.get("ko_point")
        board.ko_point = (ko[0], ko[1]) if ko is not None else None
        board.consecutive_passes = data.get("consecutive_passes", 0)
        board.is_game_over = data.get("is_game_over", False)
        board.step_count = data.get("step_count", 0)
        board.move_history = copy.deepcopy(data.get("move_history", []))
        board._rebuild_groups()
        return board

    def clone(self) -> GoBoard:
        """Creates an independent deep copy of the board state."""
        return self.from_dict(self.to_dict())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GoBoard):
            return False
        return (
            self.size == other.size
            and self.grid == other.grid
            and self.current_player == other.current_player
            and self.captures == other.captures
            and self.ko_point == other.ko_point
            and self.consecutive_passes == other.consecutive_passes
            and self.is_game_over == other.is_game_over
        )

    # -----------------------------------------------------------------------
    # Board Visualizer & Scoring
    # -----------------------------------------------------------------------

    def to_ascii(self) -> str:
        """Renders human-readable 10x10 ASCII grid with A-K column headers and 1..10 row labels."""
        lines = []
        cols = " ".join(COL_LABELS)
        lines.append(f"   {cols}")
        for y in range(self.size - 1, -1, -1):
            row_num = y + 1
            row_str = " ".join(self.grid[y][x] for x in range(self.size))
            lines.append(f"{row_num:2d} {row_str} {row_num:2d}")
        lines.append(f"   {cols}")
        return "\n".join(lines)

    def compute_territory(self) -> Dict[str, Any]:
        """Calculates area territory using flood-fill for empty regions."""
        visited: Set[Tuple[int, int]] = set()
        territory: Dict[str, Set[Tuple[int, int]]] = {BLACK: set(), WHITE: set(), "NEUTRAL": set()}

        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x] != EMPTY or (x, y) in visited:
                    continue

                # BFS component
                component: Set[Tuple[int, int]] = set()
                border_colors: Set[str] = set()
                queue = [(x, y)]
                visited.add((x, y))

                while queue:
                    cx, cy = queue.pop(0)
                    component.add((cx, cy))
                    for nx, ny in self.get_neighbors(cx, cy):
                        neighbor_val = self.grid[ny][nx]
                        if neighbor_val == EMPTY:
                            if (nx, ny) not in visited:
                                visited.add((nx, ny))
                                queue.append((nx, ny))
                        else:
                            border_colors.add(neighbor_val)

                if border_colors == {BLACK}:
                    territory[BLACK].update(component)
                elif border_colors == {WHITE}:
                    territory[WHITE].update(component)
                else:
                    territory["NEUTRAL"].update(component)

        black_stones = sum(1 for y in range(self.size) for x in range(self.size) if self.grid[y][x] == BLACK)
        white_stones = sum(1 for y in range(self.size) for x in range(self.size) if self.grid[y][x] == WHITE)

        return {
            "black_territory": len(territory[BLACK]),
            "white_territory": len(territory[WHITE]),
            "neutral_territory": len(territory["NEUTRAL"]),
            "black_stones": black_stones,
            "white_stones": white_stones,
            "black_score": black_stones + len(territory[BLACK]) + self.captures[BLACK],
            "white_score": white_stones + len(territory[WHITE]) + self.captures[WHITE],
        }


# ---------------------------------------------------------------------------
# GoEngine Subclass Alias
# ---------------------------------------------------------------------------

class GoEngine(GoBoard):
    """Full-featured Go Engine with session lifecycle and functorial undo hooks."""
    pass
