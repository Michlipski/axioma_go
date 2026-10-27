# Domain Specification: Axioma Go (10x10 Tactical Capture Dojo)
**Namespace:** `trace.domains.axioma_go`  
**Standard Compliance:** TRACE Declarative Modeling (`[L1-G3B-011]`)  
**Generation:** Generation 4b  

---

## 1. Domain Entities (Nouns)

### 1.1 `IntersectionCoord`
- **Fields:**
  - `x`: Integer $\in [0..9]$ (Columns A, B, C, D, E, F, G, H, J, K)
  - `y`: Integer $\in [0..9]$ (Rows 1..10)
- **Invariants:**
  - `x` strictly between 0 and 9 inclusive.
  - `y` strictly between 0 and 9 inclusive.
  - Column label excludes the letter 'I' in standard GTP notation.

### 1.2 `StoneGroup`
- **Fields:**
  - `group_id`: Unique identifier (string)
  - `color`: `BLACK` or `WHITE`
  - `stones`: Set of connected `IntersectionCoord`
  - `liberties`: Set of orthogonally adjacent empty `IntersectionCoord`
- **Invariants:**
  - `liberties` is the set union of orthogonal empty neighbors of all stones in the group.
  - When `|liberties| == 1`, group enters `ATARI` state.
  - When `|liberties| == 0`, group is removed from board and captured.

### 1.3 `BoardState`
- **Fields:**
  - `grid`: $10 \times 10$ matrix mapping coordinates to `EMPTY`, `BLACK`, or `WHITE`.
  - `turn`: Active player color (`BLACK` or `WHITE`).
  - `move_number`: Current ply count.
  - `captured_black`: Total Black stones captured by White.
  - `captured_white`: Total White stones captured by Black.
  - `ko_point`: Optional coordinate prohibited under the single-stone Ko rule.
  - `state_hash`: SHA-256 fingerprint of the board configuration.

---

## 2. Invariants & Rules

1. **`[INV-GO-001]` GridBounds10x10:** Moves must strictly target intersections within $[0..9] \times [0..9]$.
2. **`[INV-GO-002]` LibertyConservation:** Disjoint connected groups maintain exact liberties.
3. **`[INV-GO-003]` NoSuicideWithoutCapture:** Move leaving newly formed group with 0 liberties is illegal unless it simultaneously captures adjacent opponent stones.
4. **`[INV-GO-004]` SingleStoneKoRepetitionLockout:** Single stone capture that leaves the capturing stone in 1-liberty atari cannot be immediately recaptured on the next ply.
5. **`[INV-GO-005]` FunctorialReversibility:** Move history can be undone with zero loss of state or hash divergence.
