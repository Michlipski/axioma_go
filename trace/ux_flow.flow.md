# User Flow Specification: Axioma Go Tactical Dojo
**Namespace:** `trace.flows.axioma_go`  
**Target Persona:** Elena Vance (Tactical Apprentice) / Master Kenji (Sensei)  
**Primary Goal:** Master capturing mechanics through automated showcases and interactive branch forking.  

---

## Flow 1: Automated Showcase Observation & Step Inspection
1. **Discovery:** User lands on `http://localhost:8082`.
2. **Selection:** Clicks on "Showcases" tab or selects a canonical technique (e.g. "The Snapback").
3. **Observation:**
   - Initial board loads showing the 7-stone White trap and Black enclosure.
   - User hits "Auto-Play" or clicks "Next >>" to advance plies.
   - Visual annotations highlight the sacrifice throw-in, mutual atari, and the crushing multi-stone capture.
4. **Pedagogical Takeaway:** User reads tactical annotations and observes group liberty counts before and after the strike.

---

## Flow 2: Forking Showcase into Free Play
1. **Branch Point:** At move 1 of the Snapback (after Black plays E4), user wonders: "What if White does not capture and defends outside instead?"
2. **Fork Execution:** User clicks "Fork & Play" button.
3. **State Transition:**
   - Active showcase detaches into an independent interactive `BoardState`.
   - UI switches seamlessly to Free Play mode with the exact board position preserved.
4. **Exploration:** User places White stones at alternative coordinates to test refutations.
5. **Functorial Reversal:** User clicks "Undo" to step backward, testing multiple variations without state corruption.
