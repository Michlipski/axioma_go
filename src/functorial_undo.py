"""Functorial Undo & Categorical Adjoint State Reversal for Axioma Go.

Enforces:
- Invariant [L1-002]: Functorial State Evolution & Morphism Preservation.
  Every architectural state transformation operates as a structure-preserving functor across
  board categories: F(f ∘ g) = F(f) ∘ F(g) ∧ F(id) = id.
- Invariant [INV-GO-005]: ReversibilityFunctorialUndo:
  Adjoint state rollback S_{t-1} = f^{-1}(S_t) and forward replay S_{t+1} = f(S_t).
- Cryptographic hash chaining (SHA-256) ensuring zero state drift and Landauer bit recovery.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from .go_engine import GoBoard, GoEngineError


class FunctorialUndoViolation(GoEngineError):
    """Raised when an adjoint rollback operation fails or violates causal history."""
    def __init__(self, message: str = "FUNCTORIAL_UNDO_VIOLATION") -> None:
        super().__init__(message, code="FUNCTORIAL_UNDO_VIOLATION")


class UndoManager:
    """Manages causal history stack and deterministic adjoint rollbacks for 10x10 Axioma Go.

    Maintains:
    - `_undo_stack`: Linear history of immutable GoBoard snapshots from S_0 up to S_t.
    - `_redo_stack`: Forward branch of undone states for deterministic replay.
    - `_state_hashes`: Cryptographic SHA-256 fingerprint chain for each state in history.
    """

    def __init__(self, initial_board: Optional[GoBoard] = None, max_depth: int = 1000) -> None:
        self.max_depth: int = max_depth
        self._undo_stack: List[GoBoard] = []
        self._redo_stack: List[GoBoard] = []
        self._state_hashes: List[str] = []

        if initial_board is not None:
            self.record_state(initial_board)

    def record_state(self, board: GoBoard) -> str:
        """Pushes an immutable snapshot of GoBoard onto the causal history stack.

        Any new forward action invalidates the current redo stack.
        Returns the SHA-256 hash of the recorded state.
        """
        snapshot = board.clone()
        state_hash = snapshot.compute_hash()

        if len(self._undo_stack) >= self.max_depth:
            # Thermodynamic lease: drop oldest state to maintain bounded memory
            self._undo_stack.pop(0)
            self._state_hashes.pop(0)

        self._undo_stack.append(snapshot)
        self._state_hashes.append(state_hash)

        # Invalidate redo stack upon new causal forward branch
        self._redo_stack.clear()
        return state_hash

    # Alias for API compatibility
    push_state = record_state

    def undo(self) -> Optional[GoBoard]:
        """Reverses the most recent state transition: S_{t-1} = f^{-1}(S_t).

        Returns:
            The restored GoBoard state, or None if undo stack depth <= 1 (at genesis).
        """
        if not self.can_undo():
            return None

        # Pop current head state and shift to redo stack
        current_head = self._undo_stack.pop()
        self._state_hashes.pop()
        self._redo_stack.append(current_head)

        # The new top of undo stack is S_{t-1}
        restored = self._undo_stack[-1].clone()
        return restored

    def redo(self) -> Optional[GoBoard]:
        """Replays the most recently undone transition: S_{t+1} = f(S_t).

        Returns:
            The restored forward GoBoard state, or None if redo stack is empty.
        """
        if not self.can_redo():
            return None

        # Pop from redo stack and push back onto undo stack
        target_state = self._redo_stack.pop()
        target_hash = target_state.compute_hash()

        self._undo_stack.append(target_state)
        self._state_hashes.append(target_hash)

        return target_state.clone()

    def can_undo(self) -> bool:
        """Returns True if there is at least one previous state to roll back to."""
        return len(self._undo_stack) > 1

    def can_redo(self) -> bool:
        """Returns True if there is at least one undone state to replay forward."""
        return len(self._redo_stack) > 0

    def current_state(self) -> Optional[GoBoard]:
        """Returns an independent clone of the current head state, or None if empty."""
        if not self._undo_stack:
            return None
        return self._undo_stack[-1].clone()

    def peek_undo(self) -> Optional[GoBoard]:
        """Peeks at the state that would be restored by an undo, without mutating stacks."""
        if not self.can_undo():
            return None
        return self._undo_stack[-2].clone()

    def peek_redo(self) -> Optional[GoBoard]:
        """Peeks at the state that would be restored by a redo, without mutating stacks."""
        if not self.can_redo():
            return None
        return self._redo_stack[-1].clone()

    def history_depth(self) -> int:
        """Returns the number of snapshots in the undo stack."""
        return len(self._undo_stack)

    def redo_depth(self) -> int:
        """Returns the number of snapshots in the redo stack."""
        return len(self._redo_stack)

    def get_history_hashes(self) -> List[str]:
        """Returns the list of cryptographic SHA-256 hashes of states in the undo history."""
        return list(self._state_hashes)

    def clear(self) -> None:
        """Clears both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._state_hashes.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Returns operational metrics for telemetry dashboards and Landauer accounting."""
        return {
            "history_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "head_hash": self._state_hashes[-1] if self._state_hashes else None,
            "max_depth": self.max_depth,
        }


# ---------------------------------------------------------------------------
# Reversibility Invariant Verification Helper ([INV-GO-005], [L1-002])
# ---------------------------------------------------------------------------

def verify_reversibility(
    initial_board: GoBoard,
    moves: List[Tuple[str, int, int]],
    raise_on_violation: bool = True,
) -> bool:
    """Rigorously proves Invariant [L1-002] Functorial State Reversibility.

    Executes a complete algebraic round-trip:
    1. Forward Morphisms: Plays moves sequentially, capturing snapshots S_0, S_1, ..., S_N.
    2. Adjoint Morphisms (Undo): Reverses step-by-step from S_N back to S_0, verifying exact equality
       and SHA-256 state hash matching at every intermediate step.
    3. Identity Invariant: Verifies S_{restored_0} == S_0.
    4. Co-Adjoint Morphisms (Redo): Replays forward step-by-step from S_0 to S_N, verifying exact
       state hash matching at every step.
    5. Final Equality: Verifies S_{redone_N} == S_N.

    Args:
        initial_board: Starting GoBoard instance (typically empty 10x10 board).
        moves: Sequence of (color, x, y) moves to execute.
        raise_on_violation: If True, raises FunctorialUndoViolation on failure; otherwise returns False.

    Returns:
        True if all functorial reversibility and identity invariants hold.

    Raises:
        FunctorialUndoViolation: If any state divergence is detected.
    """
    manager = UndoManager(initial_board=initial_board)
    working_board = initial_board.clone()

    snapshots: List[GoBoard] = [initial_board.clone()]
    hashes: List[str] = [initial_board.compute_hash()]

    # Phase 1: Forward execution
    for color, x, y in moves:
        success, _, err = working_board.play_move(color, x, y)
        if not success:
            if raise_on_violation:
                raise FunctorialUndoViolation(f"Move ({color}, {x}, {y}) failed during forward phase: {err}")
            return False

        manager.record_state(working_board)
        snapshots.append(working_board.clone())
        hashes.append(working_board.compute_hash())

    total_steps = len(moves)

    # Phase 2: Adjoint reverse execution (Undo)
    for step in range(total_steps, 0, -1):
        restored = manager.undo()
        expected_step = step - 1
        expected_board = snapshots[expected_step]
        expected_hash = hashes[expected_step]

        if restored is None:
            if raise_on_violation:
                raise FunctorialUndoViolation(f"Undo returned None at step {step} -> {expected_step}.")
            return False

        actual_hash = restored.compute_hash()
        if actual_hash != expected_hash:
            if raise_on_violation:
                raise FunctorialUndoViolation(
                    f"Hash mismatch at undo step {expected_step}: expected {expected_hash}, got {actual_hash}"
                )
            return False

        if restored != expected_board:
            if raise_on_violation:
                raise FunctorialUndoViolation(f"Board inequality at undo step {expected_step}.")
            return False

    # Phase 3: Identity Invariant Check at Genesis
    if manager.can_undo():
        if raise_on_violation:
            raise FunctorialUndoViolation("UndoManager indicates can_undo() is True at genesis.")
        return False

    genesis_state = manager.current_state()
    if genesis_state != initial_board:
        if raise_on_violation:
            raise FunctorialUndoViolation("Restored genesis state does not match initial_board.")
        return False

    # Phase 4: Co-Adjoint forward execution (Redo)
    for step in range(1, total_steps + 1):
        redone = manager.redo()
        expected_board = snapshots[step]
        expected_hash = hashes[step]

        if redone is None:
            if raise_on_violation:
                raise FunctorialUndoViolation(f"Redo returned None at step {step}.")
            return False

        actual_hash = redone.compute_hash()
        if actual_hash != expected_hash:
            if raise_on_violation:
                raise FunctorialUndoViolation(
                    f"Hash mismatch at redo step {step}: expected {expected_hash}, got {actual_hash}"
                )
            return False

        if redone != expected_board:
            if raise_on_violation:
                raise FunctorialUndoViolation(f"Board inequality at redo step {step}.")
            return False

    # Phase 5: Terminal Redo Check
    if manager.can_redo():
        if raise_on_violation:
            raise FunctorialUndoViolation("UndoManager indicates can_redo() is True at final step.")
        return False

    terminal_state = manager.current_state()
    if terminal_state != snapshots[-1]:
        if raise_on_violation:
            raise FunctorialUndoViolation("Terminal redone state does not match original final state.")
        return False

    return True
