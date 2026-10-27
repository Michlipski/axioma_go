# Axioma Go: 10x10 Tactical Capture Dojo

**Generation:** Generation 4b (Service-Oriented Sovereign Mesh)  
**Port:** `8082`  
**Governing Protocols:** `[L1-G4B-001]` Decoupled Research Sovereignty, `[L1-G4B-002]` Bounded Fractal Recursion, `[L1-G4B-003]` Merkle-DAG Telemetry, `[L1-G4B-004]` Dynamic Persona Specialization, `[L1-G4B-008]` Witness Reconciliation Gate, `[NEG-G1B-001]` Anti-Phantom Emission, `[L1-G3B-018]` Zero-CDN Telemetry Dashboard.

---

## 1. Overview & Elevator Pitch
Axioma Go is an online Go game product designed for tactical depth over opening breadth. Rather than sprawling across a 19x19 board where micro-tactics are drowned in opening theory, Axioma Go scopes the topological manifold strictly to a **10x10 grid** (100 intersections, A1–K10 excluding I).

The centerpiece of the application is its **Automated Capturing Showcases**: a curated collection of 6 canonical Go capture techniques (Tesuji) executed with step-by-step automated playback, tactical annotations, dynamic liberty indicators, and an instantaneous **"Fork & Play"** feature enabling users to branch off from any point in a showcase into live interactive play.

---

## 2. Standout Features

### 2.1 The 6 Canonical Capturing Showcases
1. **The Snapback (Uttegaeshi / 打って返し):** Sacrificing a stone into the opponent's throat (*damezumari*), tempting them to capture 1 stone only to collapse their entire 8-stone cluster down to 1 liberty, followed by a crushing multi-stone recapture.
2. **The Zigzag Ladder (Shicho / 征子):** Continuous 15-ply staircase pursuit driving the defender diagonally across the 10x10 grid directly into a pre-positioned ladder catcher (*Shicho-atari*).
3. **The Loose Net (Geta / 下駄):** Knight's move encirclement capturing cutting stones without direct contact.
4. **The Crane's Nest (Tsuru no Sugomori / 鶴の巣ごもり):** Central wedge throw-in suffocating an escaping string inside a hollow bamboo-joint enclosure.
5. **The Double-Atari Fork (Ryō-Atari / 両アタリ):** Geometric fork simultaneously placing two separate enemy groups in atari.
6. **Under the Stones (Ishi-no-Shita / 石の下):** Sacrificing a 4-stone block on the edge, waiting for the opponent to clear the board, and striking inside the vacated cavity to harvest the opponent's cutting stones.

### 2.2 Tactile Board Ergonomics
- **Kaya Wood Aesthetics:** High-contrast responsive wooden board with crisp grid lines, coordinate headers, and star points (*Hoshi* at D4, G4, D7, G7, and Tengen).
- **SVG Clamshell & Slate Stones:** Subtle 3D lighting, radial gradients, drop shadows, and stone landing animations.
- **Dynamic Liberty Heatmap:** Live toggleable green badge overlay displaying exact remaining liberties on every stone group.
- **Pulsing Atari Threat Halos:** Soft amber/red glowing rings around any group reduced to 1 liberty.
- **Dual Graveyard Counters:** Real-time counters and captured stone trays for Black and White.
- **1-Tap Functorial Undo (`[L1-002]`):** Reversible algebraic state transitions allowing instant undo/redo with zero state divergence.
- **"Fork & Play" Branching:** Click "Fork & Play" at any ply during an automated showcase to instantly convert the position into an interactive game.

---

## 3. Running the Application

### 3.1 Quick Start
```bash
python3 apps/axioma_go/run.py
```
Then open your browser to:
```
http://localhost:8082
```

### 3.2 Running the Verification Suite
```bash
python3 -m unittest discover -v -s apps/axioma_go/tests
```
All 54 unit, property-based, showcase execution, and hermetic dashboard tests run in under 0.1s with exit code 0.

---

## 4. Architecture & Service Mesh Compliance
- **Zero External Dependencies:** Built 100% on Python 3.14 standard library (`http.server`, `json`, `hashlib`, `unittest`).
- **Zero External CDNs (`HERM-005`):** Pure inline HTML5, CSS3, and vanilla ES6+ JavaScript. No Google Fonts, unpkg, or CDN scripts.
- **Development Process Telemetry Dashboard:** Standalone deliverable at `dashboard.html` / `telemetry_dashboard.html` documenting the entire G4b compilation lifecycle, 60/40 thermodynamic token ledger, Landauer dissipation, subagent execution witnesses, and Merkle-DAG root attestation.
