"""Axioma Go Sovereign Package (`apps.axioma_go.src`).

Exports Go board, engine, exceptions, coordinates, functorial undo, and canonical showcases.
"""

from .go_engine import (
    BOARD_SIZE,
    COL_LABELS,
    EMPTY,
    BLACK,
    WHITE,
    GoBoard,
    GoEngine,
    GoEngineError,
    IllegalMoveError,
    IntersectionOccupiedError,
    KoError,
    OutOfBoundsError,
    SuicideError,
    TurnOrderError,
    coord_to_xy,
    xy_to_coord,
    x_to_col,
    col_to_x,
)

from .functorial_undo import (
    UndoManager,
    FunctorialUndoViolation,
    verify_reversibility,
)

from .showcases import (
    Showcase,
    ShowcaseStep,
    TacticalCommentary,
    list_showcases,
    get_showcase,
    build_showcase_board_at_step,
    showcase_01_snapback,
    showcase_02_ladder,
    showcase_03_geta,
    showcase_04_cranes_nest,
    showcase_05_double_atari,
    showcase_06_ishi_no_shita,
    ALL_SHOWCASES,
)

from .engine import (
    CANONICAL_SHOWCASES,
    coord_to_str,
    str_to_coord,
)

__all__ = [
    "BOARD_SIZE",
    "COL_LABELS",
    "EMPTY",
    "BLACK",
    "WHITE",
    "GoBoard",
    "GoEngine",
    "GoEngineError",
    "IllegalMoveError",
    "IntersectionOccupiedError",
    "KoError",
    "OutOfBoundsError",
    "SuicideError",
    "TurnOrderError",
    "coord_to_xy",
    "xy_to_coord",
    "x_to_col",
    "col_to_x",
    "UndoManager",
    "FunctorialUndoViolation",
    "verify_reversibility",
    "CANONICAL_SHOWCASES",
    "coord_to_str",
    "str_to_coord",
    "Showcase",
    "ShowcaseStep",
    "TacticalCommentary",
    "list_showcases",
    "get_showcase",
    "build_showcase_board_at_step",
    "showcase_01_snapback",
    "showcase_02_ladder",
    "showcase_03_geta",
    "showcase_04_cranes_nest",
    "showcase_05_double_atari",
    "showcase_06_ishi_no_shita",
    "ALL_SHOWCASES",
]
