# Eternity II research notes — volume 4

Continuation of `RESEARCH_NOTES_3.md`. Read that file's **SESSION
CLOSE** section first (around line 900) — it carries the three
next-step options (A spectral, B Régin-coupled, C SAT) and the
graph-theoretic reframing that motivates them.

Auto-memory state in `project_e2_state.md` is the authoritative
summary of where we stand: **449/480 = 93.5% on official E2**, plateau
confirmed structural via the Hamming-moat argument on (Graph 1 ∩
Graph 2). Don't repeat propagator-strength work — every alldiff
variant tested plateaus in the same band.

---

## 2026-05-11 — Session open (vol. 4 first session)

### Plan from vol. 3 SESSION CLOSE

Recommended path: **Option A — spectral / structural diagnostic of
plateau Graph 2** (cheap, half-day). Shapes whether Option B
(Régin-coupled, 3-5 days) or Option C (SAT, 1-2 days) is the right
deep investment.

### Pre-flight findings (before any new code)

Two facts re-checked at the start of this session:

1. **Plateau JSON files do not carry piece IDs.** Both
   `output/pt_e2_*.json` (cell-CP→PT) and `output/edge_cp_e2_*.json`
   (edge-CP) persist only `bucas_url`, `details` (timing/score), and
   `puzzle` (metadata). The board state lives entirely inside the
   `bucas_url`'s `board_edges` parameter — a 1024-char alphabet-blob
   encoding 256 cells × 4 colors (N/E/S/W), alphabet `a..w` where `a`
   = BORDER and `b..w` = 22 interior colors.

   *Implication for Option A:* to reason about pieces (e.g., "which
   pieces are placed at mismatch cells, which would need to move"),
   the bucas blob must be re-matched against the piece-rotation
   catalog. Lossless when each cell's 4-tuple maps to a unique
   piece-rotation; collisions would themselves be a structural
   finding.

2. **The 449-state has `placed_cells: 256` and `matched_edges: 449`.**
   *All cells are placed*; the 31 unmatched are interior edges where
   adjacent cells' colors disagree. This sharpens the Option A
   question: the deficient set is not "cells with no piece"; it is
   the local neighborhood around the 31 color-mismatch edges, and
   the question is whether *some* permutation of pieces in that
   neighborhood resolves more mismatches without breaking others
   — i.e., a local-repair feasibility question.

### Refined Option A question

Given a 449-plateau board:

- Locate the 31 mismatch edges and the (≤62) cells incident to them.
- Are mismatch cells **spatially localized** (a few clusters, each
  bounded by good edges) or **distributed** across the board?
- For each cluster, define a *repair region* = cluster cells + their
  immediate good-edge neighbors holding the boundary fixed. Ask: does
  any piece-permutation on the repair region using only currently-
  used pieces yield > current-region-matched-edges? Does any
  permutation using *also* the global piece pool (i.e., swap with
  cells outside the region) help?
- Hall-deficiency proxy: bipartite graph of (mismatch cells × catalog
  pieces filterable by the fixed boundary). König's theorem identifies
  the minimum vertex cover; the deficient set is what's left.

Outcomes:

- **Localized + small clusters**: build a targeted mini-CP repair
  per cluster (≤ 16 cells, finite-domain CP solves exactly in seconds).
  This is option-A-followup-1.
- **Distributed**: confirms 449 is a hard structural limit; fall back
  to Option C (SAT) for authoritative confirmation. 1-2 day build.

Risk of A: low. Cost: half-day. Information value: high — whichever
outcome obtains, B-vs-C is settled.

### Method

1. Add a small analysis binary (`crates/benchmark/src/bin/plateau_analyze.rs`)
   that:
   - Loads the official 16×16 puzzle catalog (existing helper used
     by `pt_e2.rs` / `edge_cp_e2.rs`).
   - Loads a plateau JSON (CLI arg, default `pt_e2_1778519359_449of480.json`).
   - Parses the bucas `board_edges` blob into a `Board` with N/E/S/W
     colors per cell.
   - Matches each cell's 4-tuple against the piece-rotation catalog
     to recover `cell -> (piece_id, rotation)`. Reports collisions
     (cells with the same piece, cells matching no piece — should be
     zero if PT runs respect alldiff, which they do).
   - Identifies mismatch edges and dumps:
     - Adjacency-list of mismatch-cells in row-major coordinates
     - Connected components of the mismatch graph (cells linked if
       they share a mismatched edge OR are adjacent on a 4-neighborhood
       and both touch a mismatch)
     - Per-cluster size distribution, board-region overlay (ASCII or
       JSON for downstream plotting)
   - Hall deficiency of (mismatch cells × catalog pieces with corner/
     edge/interior class and current boundary respected). Uses the
     existing bipartite-matching code in `crates/edge-solver/src/search.rs`
     (`has_complete_matching` and the row-mask machinery) adapted to
     return the deficient set on failure rather than just a bool.

2. Output two artifacts: a JSON dump under `output/plateau_analysis_*.json`
   with all the above, and a human-readable ASCII board overlay
   printed to stdout.

3. Reuse existing puzzle-loading and bucas-decoding paths from
   `pt_e2.rs` and `analyze_topology.rs` rather than re-implementing.

### Decisions (user gave full latitude)

- **Plateau source**: generate a fresh 449 with an enriched snapshot
  format that persists `(cell → piece_id, rotation)` directly,
  bypassing the bucas-decode roundtrip. Rationale: every downstream
  analysis tool would otherwise re-implement fallible color→piece
  matching. One-time investment, reusable everywhere.
- **Session depth**: if the diagnostic shows mismatches are spatially
  localized, continue into the mini-CP repair this session. A real
  +1 edge gain from local repair is a falsifiable structural claim,
  far stronger than diagnostic statistics alone.

### Method (revised)

1. Add a `placement` field to `pt_e2` JSON output: array of length
   256 with `{piece_id, rotation}` per cell (or null). Touches
   `crates/benchmark/src/bin/pt_e2.rs` only; the underlying solver
   already tracks placements internally.

2. Re-run `pt_e2` to generate a fresh 449-plateau snapshot. Save
   under `output/pt_e2_*_449of480_enriched.json`.

3. Build `crates/benchmark/src/bin/plateau_analyze.rs` consuming the
   enriched snapshot:
   - Load placement + puzzle catalog.
   - Compute the 31 mismatch edges; list incident cells.
   - Connected-component analysis (cells adjacent on the grid and
     both touching a mismatch are linked).
   - For each component: bounding-box, piece set in component, can
     any piece-permutation *over the component* — boundary held
     fixed — improve the local match count? This is a small finite
     CP / brute-force feasibility check.
   - Hall-deficiency analysis using `has_complete_matching` from
     edge-solver, extended to return the deficient set.
   - Outputs: ASCII board overlay (G/B markers) + JSON dump under
     `output/plateau_analysis_*.json`.

4. If clusters are small (≤16 cells): implement mini-CP repair
   per cluster. Component-local search using either the
   `solver-engine` backtracker over the constrained region, or a
   direct enumeration of permutations of the component's pieces.
   Report edge-gain.

---

## Experiments

### 2026-05-11 — plateau_analyze on canonical 449 (Option A first cut)

**Setup**: ran `plateau_analyze --input output/pt_e2_1778519359_449of480.json`
on the canonical cell-CP→PT plateau from vol. 2's megarun. Since
that file predates the placement-field enrichment, the bin took the
bucas-decode path. No duplicate-piece collisions: all 256 cells map
uniquely to a piece-rotation.

**Result**:
- 31 mismatch edges (matches the persisted score: 480 − 449 = 31).
- Mismatch-incident cells form **4 connected components**:
  | comp | size | bbox (x0,y0,x1,y1) | inside / boundary mismatches |
  |------|------|--------------------|------------------------------|
  | 1    | 38   | (2,7)–(13,13)      | south-central blob          |
  | 2    | 6    | (4,6)–(8,6)        | row-6 band                  |
  | 3    | 5    | (9,4)–(13,6)       | north-central               |
  | 4    | 2    | (13,5)–(14,6)      | tiny pair                   |
- **Localization ratio = 0.745** (largest 38 / total 51 incident
  cells). This is the "single-blob-dominant" regime.

ASCII overlay (digit = component, `|` = h-mismatch, `-` = v-mismatch):

```
   0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
0  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
2  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
3  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
4  .  .  .  .  .  .  .  .  .  2  .  .  .  .  .  .
                              -
5  .  .  .  .  .  .  .  .  .  2  2  2| 2  .  .  .
                                 -
6  .  .  .  .  3| 3| 3  3| 3  .  2  .  .  4| 4  .
7  .  .  .  .  .  .  .  .  .  1  .  .  .  .  .  .
                              -
8  .  .  .  1| 1  .  .  1  .  1  1  .  .  .  .  .
            -  -        -     -  -
9  .  .  .  1  1  .  1  1  1  1  1  1| 1| 1  .  .
                     -     -
10 .  .  1| 1| 1  1  1  .  1  .  .  1| 1  .  .  .
                  -                 -  -
11 .  .  .  .  .  1  .  1| 1  .  .  1  1  .  .  .
12 .  .  .  .  .  .  1| 1  .  1| 1| 1  1  .  .  .
                     -                 -
13 .  .  .  .  .  .  1| 1  .  .  .  .  1  .  .  .
```

**First-pass interpretation (naïve)**: localized → mini-CP repair on
the 38-cell south blob is the natural followup. Comp 1 fits in a
~12×7 bbox.

**Second-pass interpretation (vol. 2 context)**: vol. 2 already ran
`central_repair` and `worst_region_repair` on a 450-plateau dump and
found:
- Freeing only the interior (border pinned): CP fails to complete
  in 60s.
- Freeing a worst k×k window: instant infeasibility.
- **Conclusion** (vol. 2): "Local CP repair can never fix this —
  the obstruction is in the *pinned* cells, not the freed ones."

This changes what an Option-A mini-CP repair would *prove*. If it
succeeds → contradicts vol. 2 and is a real breakthrough. If it
fails → confirms vol. 2's pinned-boundary obstruction from a new
angle (mismatch-cluster-targeted repair, rather than worst-window).

### Next step (committed): rerun the existing worst_region_repair on the south blob

Before building a connected-component-aware mini-CP, calibrate against
the existing rectangular-window code. The south blob bbox is (2,7)-
(13,13) = 12×7 cells. Vol. 2's `repair_region` works on k×k windows,
not rectangles, but `worst_region_repair --k 8` centered there is a
cheap probe. Expected outcome (from vol. 2): wipeout or timeout.
If unexpectedly the repair succeeds, that's the breakthrough.

### 2026-05-11 — F2-tight: bug from pinning across mismatched boundaries

Built `component_repair` to free *only* the cells of one mismatch
component (the 38-cell south blob), pinning the other 218 cells.
First run failed immediately:

```
outcome: Error(hint at position 89 is incompatible with constraints), new score: 0
```

Position 89 = (row 5, col 9), which is in component 2 (north-central).
The solver-engine's hint propagator rejects any hint set where the
pinned cells themselves contain a color mismatch — i.e., pinning
cells from multiple unrelated components introduces a contradiction
the engine refuses to enter.

**Fix**: when freeing component 0, must also free *all other* mismatch-
incident cells (components 1, 2, 3). The repaired set: free 51 cells
total (the union of all 4 components), pin the remaining 205. This is
strictly between F1 (free a single rectangle) and F2-tight (free one
component); it's the right "tight" formulation given the engine's
hint-feasibility constraint.

**Aside — multi-modality of E2 solutions** (from user note):
the 5-clue E2 has many distinct partial solutions in the 440-449
band; the search community has documented this for the 1-clue
variant too. This means our canonical 449 is one element of a
potentially large basin. If F2 fails on *this* state, that's not
the same as saying no 449→450 transition exists *anywhere*; a
different basin entry might be reachable. Diagnostic value of one
state's repair is still high (it tells us about *this* basin), but
generalization across basins requires re-running on multiple
plateau samples.

### 2026-05-11 — F2 retry: free all 4 components, then padded — both AC3-wipe

**F2-tight (free all 51 mismatch-incident cells)**: error in 0.05s,
"hint at position 93 causes immediate wipeout". Position 93 = (row 5,
col 13) — a *pinned, matched-edge* cell, not in any component. AC3
emptied its domain during initial propagation.

**F2-padded (free 111 = 51 + 4-neighbors)**: error in 0.08s, "hint at
position 206 causes immediate wipeout". Position 206 = (row 12, col 14)
— again a pinned cell outside any component.

**Diagnosis**: this replicates vol. 2's conclusion that local CP
repair can't fix the plateau — *the obstruction is in the pinned
cells*. AC3 propagation, given the plateau's pinned ring, derives a
contradiction. Removing the freed cells (where the mismatches *visibly*
are) doesn't help: the pinned cells themselves implicitly carry
constraints that AC3 cannot reconcile.

The mechanism: under AC3, every pinned cell's piece is a hard
assignment; its edge colors fully determine the allowed edges of its
4 neighbors. When those neighbors are *also* pinned, AC3 checks
consistency. Across 205 (resp. 145) pinned cells, some pair becomes
inconsistent under arc-consistency even though, as a *bare placement
fact*, the original 449 state is internally valid (just imperfect).
The contradiction arises because AC3 is *stronger* than mere
placement-validity — it deduces from the pinned edges what *other*
pieces could go in the freed cells, and finds the deduced domain
empty.

This is a sharper version of the vol. 2 obstruction: not "the
freed-window pieces can't complete" but "the pinned-cells alone are
not AC3-consistent." Even with 60+ freed cells.

### Verdict on Option A

- **Spatial structure**: definitively localized (0.745, 4 components,
  largest = 38 cells). The SESSION CLOSE prediction "localized →
  mini-CP can repair that region exactly" turns out to be wrong for
  *this* plateau state because of AC3 unsatisfiability of the pinned
  ring.
- **Local-repair viability**: ruled out for the canonical 449 state
  with both tight (51-free) and padded (111-free) free sets. The
  obstruction is structural in the pinned ring, not in the freed
  region. Replicates and sharpens vol. 2's central finding.
- **Direction**: per the SESSION CLOSE conditional logic
  ("distributed failures → confirms 449 is a hard structural limit,
  fall back to Option C"), the *combination* of (localized but
  unrepairable) is equally a fall-back signal: localization is
  spatial only, not algorithmic. **Recommend Option C (SAT) next.**

### 2026-05-11 — F2 on fresh 449 (different basin) — confirms basin-invariance of wipeout

Fresh `output/pt_e2_1778526208_449of480.json` produced by a 60s+600s
cell-CP→PT run with the same seed. **Same score (449), different
basin** (different bucas board_edges blob, different component
structure).

`plateau_analyze` on the fresh state:
- **5 components** (vs 4 in canonical), sizes **23/16/6/3/2**.
- Localization ratio: **0.460** (vs 0.745 — fresh basin is more
  multi-clustered).
- Largest component is 23 cells, in a different region than the
  canonical's 38-cell south blob.

`component_repair` with `--free-all-mismatch` (default, frees the
union of all 50 mismatch-incident cells) targeting each component
in turn: **all 5 components AC3-wipe** in < 0.1s. Wipeout is at
position 103 (row 6, col 7) — a *pinned non-mismatch* cell. Same
mechanism as canonical: AC3 finds the pinned ring inconsistent.

`--target-only` (freeing only the 2-cell smallest component): AC3
wipes at position 92 in 0.05s, but this is the expected case — the
48 mismatch-edge-incident cells in *other* components are still
pinned and inherently contradict each other.

**Cross-basin conclusion**:
- The component structure of the 31 mismatches *changes* between
  basins (4-comp 38/6/5/2 vs 5-comp 23/16/6/3/2), but
- The AC3-unsatisfiability of the pinned ring is **basin-invariant**
  — both 449 states fail the same way.
- This rules out "the canonical basin happens to be locally
  unrepairable; other basins are better" as a hypothesis. Local
  CP repair fails *across distinct basins of the 449 plateau*.

### Final Option A verdict

1. **Spatial localization of mismatches is real but basin-dependent**
   (0.745 vs 0.460). The plateau is not a uniform-failure regime.
2. **AC3-unsatisfiability of the plateau pinned ring is universal**
   across the 2 distinct basins tested. Mini-CP local repair cannot
   improve any of these states — the obstruction is structural to
   the plateau's cell placements, not to any single basin.
3. **Recommendation: Option C (SAT).** The structural-localization
   finding alone doesn't break the plateau; we need an authoritative
   feasibility answer to know whether 450+ is reachable *at all* on
   this 5-clue puzzle. CDCL is the right tool — it can prove
   infeasibility (≤449 is the ceiling) or find a witness (≥450 is
   reachable).

---

## Option C — SAT encoding (vol. 4 session 1)

### Design

Model: piece-rotation-at-cell (Ansótegui-Sellmann-Tabar 2008 lineage).

**Piece variables**: `x_{c,p,r}` = 1 iff piece p is placed at cell c
in rotation r. Class-filtered (only corner pieces at corners, edge
pieces on the boundary ring, interior pieces in the interior) and
border-matched (the piece's BORDER sides must align with the cell's
BORDER sides).

**Edge-match auxiliary variables**: For each interior edge e and each
non-border color k ∈ {1..=22}, `m_{e,k}` = 1 iff both incident cells
project color k onto edge e. Encoded via:
  m_{e,k} → ∨_{(p,r): emit(p,r,side_a)=k} x_{c_a,p,r}
  m_{e,k} → ∨_{(p,r): emit(p,r,side_b)=k} x_{c_b,p,r}

The reverse direction is implicit: the soft objective ranks models
by # satisfied "∨_k m_{e,k}" clauses.

**AMO encoding**: bimander (Hölldobler-Nguyen 2013) with √n groups
for n > 6, pairwise otherwise. Strictly better than pairwise for the
n ≈ 100-700 sizes per cell at the 16×16 scale.

**Hints**: unit clauses pinning the 5 official hint cells.

**MaxSAT objective**: maximize the number of satisfied
"∨_k m_{e,k}" clauses (one per interior edge). The optimum
equals the maximum matched-edge count achievable under the
puzzle's hard constraints.

### 16×16 official encoding sizes

```
piece-vars            156 816
edge-match aux         10 560
AMO aux                 ~3 736
total vars            171 112
hard clauses        5 796 245
soft clauses              480
WCNF file              108.8 MB
```

### Validation ladder

- **3×3 generated** (4 colors, splr): SAT, decoded board scores 100%.
- **4×4 generated** (5 colors, splr): SAT, 100%.
- **5×5 generated** (6 colors, splr): SAT, 100%.
- **5×5 generated** WCNF → RC2: optimum = 40/40 satisfied in 0.0s.
  End-to-end pipeline (encode → WCNF → pysat → RC2 → optimal) works.

### 16×16 official run

WCNF emitted to `output/sat_e2_size_16_official_eternity_1778526730.wcnf`
(108.8 MB). RC2 launched with 30-minute budget on backend Glucose-3.
Result pending; the instance is large and may exhaust budget.

The result is meaningful in either direction:
- **Optimum reported = 480**: a perfect solution exists — our local
  search has been leaving 31 edges on the table. Big result.
- **Optimum reported < 480 and proved**: the structural ceiling is
  authoritative. If ≤ 449, the cell-CP→PT pipeline is at the optimum.
  If 450-479, there's headroom local search hasn't reached.
- **No proof within budget**: most likely outcome at this scale.
  Would need state-of-the-art native MaxSAT solvers (EvalMaxSAT,
  CashWMaxSAT) and/or several hours.

### Code added

- New crate `crates/sat-encoder/` (lib + integration tests).
- New bin `crates/benchmark/src/bin/sat_e2.rs` (encode 16×16 or
  generated puzzles to CNF/WCNF).
- New script `scripts/run_maxsat.py` (load WCNF, run RC2 with budget).

### Paths forward if RC2 times out

The 16×16 instance is famously hard. If RC2 doesn't terminate in
30 min, the next session has multiple cleaner approaches:

1. **Native MaxSAT solvers** — EvalMaxSAT (Avellaneda 2020, MSE
   winner), CashWMaxSAT-Core (Lei-Cai 2021), or UWrMaxSAT (Piotrów
   2020). All require compilation from source. Install path:
   ```
   git clone https://github.com/forge-osi/EvalMaxSAT  # placeholder
   cd EvalMaxSAT && make
   ```
   These can be 10-100× faster than RC2 on industrial instances.
2. **Encoding refinements**:
   - **Sequential AMO** instead of bimander for cells with very
     large piece-rotation sets (n > 200): typically tighter UP.
   - **Cardinality-based MaxSAT objective**: encode "≥ k matched
     edges" as a hard clause via a sequential cardinality
     constraint, then binary-search over k. Avoids MaxSAT entirely
     — pure SAT decisions. Works with kissat/cadical (very fast
     CDCL).
3. **Problem decomposition**:
   - **Plateau-anchored MaxSAT**: pin the 256 - 51 = 205
     unambiguous cells from the 449-plateau as additional hard
     unit clauses, ask SAT/MaxSAT to maximize matches *over the
     51 mismatch-incident cells*. Drastically smaller instance.
     Caveat: this assumes the plateau's pinning is consistent —
     vol. 4 F2 showed AC3 wipes out, so the SAT solver itself
     would prove UNSAT, confirming "no improvement on this
     plateau" from another angle. Worth doing as a focused probe.
   - **Region-MaxSAT**: pin only the boundary ring (60 cells),
     MaxSAT over the 196 interior. Smaller search space; gives
     "best possible interior given the canonical border".
4. **Symmetry breaking**:
   - Rotational symmetry of pieces that have repeated edges:
     detect and emit only one rotation. Reduces piece-vars
     count by ~10-15% on typical E2 puzzles.
   - Translational symmetry: not present in E2 (5 hints break
     all global symmetries), so no gain there.

### Session-2 priority

Given vol. 4 session 1 has settled:
- Option A is *complete*: localized but locally-unrepairable.
- Option C *foundation* is built and validated.

The natural session-2 work is **harden the SAT pipeline**:
1. Install EvalMaxSAT (or whichever is most accessible).
2. Run 16×16 on a real overnight budget (8-24h).
3. If unproductive: try the *plateau-anchored MaxSAT* probe (#3
   above) — far smaller instance, may give a clean local-optimum
   confirmation in minutes.
4. Document the authoritative bound: if SAT finds ≥ 450, our
   stack has been suboptimal. If it proves ≤ 449, the 93.5%
   ceiling is structural.

---

## SESSION CLOSE (vol. 4 first session)

### Headline deliverables

1. **Option A complete** — plateau structural diagnostic. The 31
   mismatch edges at the canonical 449 plateau form 4 connected
   components (38/6/5/2), localization ratio 0.745 (strongly
   single-blob). A fresh 449 from a different basin has 5
   components (23/16/6/3/2), localization 0.460. **Cross-basin
   conclusion**: spatial structure is basin-dependent, but
   AC3-unsatisfiability of the plateau pinned ring is universal.
   Tools: `plateau_analyze`, `component_repair`.

2. **vol. 2 obstruction sharpened**. Mini-CP repair (free the
   mismatch components, pin everything else) AC3-wipes in <0.1s on
   both basins. Replicates and extends vol. 2's "local repair
   can't fix this" finding: not just that the freed-window pieces
   lack a completion, but that the *pinned cells alone* are not
   arc-consistent.

3. **Option C foundation built** — new crate `eternity2-sat-encoder`
   implementing Ansótegui-style piece-rotation-at-cell encoding +
   bimander AMO + edge-match aux vars for MaxSAT objective.
   Validated end-to-end on 3×3/4×4/5×5 generated puzzles (splr
   solves them all to 100%; RC2 confirms WCNF parsing and MaxSAT
   optimum). For 16×16 official: 171 112 vars, 5.8M hard clauses,
   480 soft clauses, 108.8 MB WCNF.

4. **Report enrichment**: `report.rs` now writes a per-cell
   `placement` array so analysis tools don't need to bucas-decode.

### Files added / changed

```
v2/crates/sat-encoder/                       (new crate)
  Cargo.toml, src/lib.rs, tests/end_to_end.rs
v2/crates/benchmark/
  Cargo.toml, src/report.rs (placement field),
  src/bin/plateau_analyze.rs, src/bin/component_repair.rs,
  src/bin/sat_e2.rs (all new)
v2/Cargo.toml                                (workspace member)
v2/scripts/run_maxsat.py                     (new helper)
v2/RESEARCH_NOTES_4.md                       (this file)
.claude/projects/.../memory/MEMORY.md        (auto-memory refresh)
.claude/projects/.../memory/project_e2_state.md
```

### Hard-won lessons

1. **A 0.745 localization ratio is not the same as repair-able.**
   The SESSION CLOSE prediction "localized → mini-CP can repair
   that region exactly" turned out to be over-optimistic. The
   right framing is: localization tells us *where* the failures
   are spatially, not whether the pinned surround admits any
   improvement. AC3 unsatisfiability of plateau states is
   stronger than spatial diagnosis can detect.

2. **AC3 unsatisfiability of the pinned ring is basin-invariant.**
   Two distinct 449 plateaus produced different component
   structures but the *same wipeout phenomenon* under
   component-repair. This is a strong negative result that
   moots the "mini-CP region repair" branch of the SESSION
   CLOSE conditional. The real ceiling-question is a global
   feasibility question — SAT-shaped.

3. **MaxSAT instance sizes are tractable for E2 by modern
   standards.** 5.8M clauses, 170k vars is at the easy-to-medium
   end of MaxSAT Evaluation benchmarks. RC2 may not finish, but
   a native solver should.

4. **Class-filtering shrinks the SAT instance dramatically.**
   The naive piece-rotation-at-cell count is 256×256×4 = 262 144;
   after class filtering it's 156 816 — a 40% reduction. Crucial
   for tractability.

5. **Bimander AMO is the right default.** Pairwise AMO on n=200
   cells would emit 20k clauses per cell × 256 cells = 5M clauses
   *just for AMO* — comparable to our total. Bimander makes the
   encoding feasible.

### Verified state for next session

- Cell-CP baseline: 449/480 (unchanged).
- Plateau structure: 4 components in canonical / 5 components in
  fresh, both spatially localized but AC3-incompatible with local
  repair.
- SAT encoder: validated on small puzzles, builds a 108.8 MB
  WCNF for 16×16 official in ~1s.
- RC2 16×16 run: status uncertain (may time out within 30 min
  budget). See `/tmp/rc2_16x16.log`.

### Open questions for next session

1. **Did RC2 finish?** If yes, what's the optimum? If timed out,
   *was the lower bound improving steadily*?
2. Native MaxSAT solver path — install EvalMaxSAT or
   CashWMaxSAT-Core, retry with longer budget.
3. **Plateau-anchored MaxSAT**: pin the 205 unambiguous cells
   from a canonical plateau, ask MaxSAT to maximize edge matches
   over the 51 mismatch cells. Drastically smaller instance —
   likely solvable in minutes. Sharpens the F2 wipeout finding
   to an exact lower-bound proof.
4. **Cardinality-MaxSAT alternative**: instead of MaxSAT, binary-
   search via decision-SAT with a "≥ k matched edges" cardinality
   constraint. Use kissat or cadical (both fast CDCL).

### Recommendation

Next session should focus on **(2) install a native MaxSAT solver
+ (3) plateau-anchored encoding**. The full-puzzle MaxSAT may
remain hard, but the plateau-anchored variant has very few
degrees of freedom and is likely to produce an authoritative
bound quickly. That settles the structural ceiling question for
the documented basin.

---

## 2026-05-11 — Post-session cleanup (user-driven)

After running pysat RC2 on the full 16×16 WCNF and the plateau-
anchored variant, two things became obvious:

1. **pysat RC2 is the wrong tool.** It runs the OLL algorithm
   without printing any intermediate bound. Either you get the
   answer or you don't; there's no progress signal. For a 5.8M-
   clause instance this is a near-useless mode — you'd burn an
   overnight budget and learn nothing if it didn't finish.

2. **The 205-cell plateau-anchored mode was the wrong question.**
   It asks "can we improve from *this specific basin*?", and
   vol. 4's F2 wipeout already says no (AC3 thinks the 205 are
   unsatisfiable). The headline question is "what's the puzzle's
   ceiling under the 5 *official* hints?" — and that's what the
   stock encoder already produces.

**Cleanup done in this commit:**
- Deleted `scripts/run_maxsat.py` and the python-sat detour. All
  SAT pipeline stays in Rust; the next session shells out to a
  *native* solver.
- Removed `--anchor-plateau` / `--anchor-analysis` flags from
  `sat_e2`. The bin is now focused on emitting the official
  5-clue puzzle as CNF/WCNF.
- Added a short user-facing hint at the end of `sat_e2` output
  pointing to the native solvers to try (kissat, cadical,
  EvalMaxSAT, cashwmaxsat-core, uwrmaxsat).

**Revised recommendation for vol. 4 session 2:**

> **Step 1**: literature survey. Use web research to systematically
> identify E2-relevant methods we haven't tried. The auto-memory
> standing instruction says "innovate, take time, reformulate
> across fields" — this is exactly the moment to reach outside
> our toolbox. Candidates to actually investigate:
> - Frame-first decomposition (Wenslowe / 1-clue 470 record).
>   Solve the border ring first (60 cells, much smaller),
>   freeze it, then attack interior. We haven't tried this.
> - Belief Propagation / Survey Propagation. Random-CSP
>   literature; may help on the high-Z plateau geometry.
> - Lagrangian relaxation of alldiff. Bound-tightening.
> - GA with Lamarckian local search (Verhoef 2009 family).
> - MCTS + neural-policy (AlphaZero-style). Latest E2 attempts
>   in 2023+ literature reportedly use this.
> - Path/branch decomposition + DP with explicit boundary state.
>   Treewidth on a grid is √n = 16, so full DP is intractable,
>   but path-decomposition tracks just the cut. Possibly works
>   for plateau-region-fixed problems.
> - Tabu Search with diversification (Schaus & Deville 2008).
>   We did SA + PT; tabu is a different escape mechanism.
>
> **Step 2**: native MaxSAT with the official 5-hint encoding.
> Install one of EvalMaxSAT / CashWMaxSAT-Core / UWrMaxSAT.
> Pick the highest-streaming-verbosity option. Run on the
> existing 108.8 MB WCNF that this session already produced.
> If it converges → authoritative ceiling answer. If it gets
> stuck at the same plateau → independent confirmation of the
> 449 structural limit.
>
> Step 1 is half-day and reframes everything; step 2 is
> overnight-compute and may answer the headline question
> directly. Do them in that order.

---

## 2026-05-11 — Literature survey (Step 1 from the revised plan)

Two parallel research agents with web access were spawned:
- **Track A** — structured survey of 8 specified methods + 2
  freeform additions, with effort estimates and predicted gains.
- **Track B** — unbiased breakthrough search for unexpected
  cross-domain reframings (max 3 findings).

Full agent transcripts retained in:
`.claude/.../tasks/a45124e86b2ebc040.output` (Track A)
`.claude/.../tasks/a750abb0bff6b144b.output` (Track B)

This section is a synthesis, with the headline contradictions
and best-supported takeaways foregrounded.

### Important corrections from the survey

1. **The Verhaard record is 467/480, Blackwood is 468/480** in
   published literature. The "470" referenced in our auto-memory
   `reference_blackwood_decoded.md` comes from inspecting the
   actual `libblackwood` repo's `jb470.py` scenario on the
   1-clue variant — not a published academic record. Both can
   be true: published ceiling = 468; repo ceiling = 470. Not a
   conflict, just two different sources at slightly different
   numbers.
2. The Wauters et al. tabu+VLNS published a **458/480** result
   on E2 in 2012. The META'10 competition reached 461 with
   memetic variants. So **our 449/480 is genuinely below
   2012-era SOTA** — the cell-CP→PT stack is leaving 9-12 edges
   on the table that simpler approaches with the right move-set
   architecture have demonstrated.
3. "Verhoef 2009" (the memetic-GA reference I cited from
   memory) is the wrong name — likely a confusion with
   Verhaard (the 467 record holder, who used pure backtracking,
   not GA). Memetic-GA work is Niang 2011 thesis + Muñoz et al.
   MICAI 2009.

### Track A — structured rankings (top 5)

| # | Method | Effort | Predicted gain | Why |
|---|---|---|---|---|
| 1 | **ALNS (adaptive LNS)** | 5-8 days | +2 to +5 | Multi-operator destroy-repair; PT only uses single-piece moves. Lowest-risk path to break 449. |
| 2 | **Tabu w/ diversification** | 3-5 days | +0 to +2 | Cheapest sanity-check; whether PT diversity is the bottleneck. |
| 3 | **Cost-based alldiff (Régin extension)** | 6-9 days | +0 to +3 | Strengthens CP propagation; allows PT to visit more basins per CPU-hour. |
| 4 | **Memetic GA + block crossover** | 7-10 days | +2 to +6 | Only listed method with a true *non-local* recombination operator; META'10 precedent of 461. |
| 5 | **Frame-first decomposition** | 4-6 days | +0 to +3 | Cheap to test; likely redundant with our border handling but worth confirming. |

Full table including #6-10 (BP/SP, path-decomposition DP, MCTS+NN,
Lagrangian, MIP) in the agent transcript. Bottom 3 dismissed
on cost-benefit grounds.

### Track B — three breakthrough angles

**B1. MWPM-defect-pairing from quantum surface-code decoders.**
- 31 mismatched edges = 31 defects on the cell-cell dual lattice.
- Minimum-Weight Perfect Matching pairs defects via Edmonds'
  blossom; each matched pair = a Kempe-chain of piece moves
  that nets to zero new defects.
- Tool: PyMatching v2 (sparse blossom, near-linear time on
  surface-code-scale graphs).
- Key reference: Higgott & Gidney, Quantum 2025.
- **Why it could break 449**: PT's local moves cannot find
  coordinated multi-cell rotation/swap chains. MWPM gives the
  *globally optimal* defect pairing, defining the LNS
  destroy-set explicitly.

**B2. Survey Propagation + freezing analysis as a diagnostic.**
- Run SP on our CP encoding once.
- Identify "frozen variables" (per Sly-Sun-Zhang 2023's rigorous
  treatment of 1RSB structure).
- If 449 is a 1RSB cluster boundary → no PT tuning helps
  (entropic barrier is order-N).
- If 449 is just a hard local min → cluster-aware PT crosses it.
- **Why it could break 449**: SP tells us *whether* the plateau
  is structural before we burn weeks on the wrong attack.

**B3. Diffusion-based PT proposals (IsingFormer 2025).**
- Train a graph diffusion model on partial E2 boards.
- Use sampled completions as PT swap proposals.
- Replaces the local-move proposal kernel with a learned
  long-range one.
- **Why it could break 449**: PT's bottleneck is proposal
  locality. A learned proposal kernel respects long-range
  correlations the local kernel can't see.
- Highest variance bet; defer until B1/B2 confirmed or ruled out.

### Synthesis — the merged session-2 plan

Track A's #1 (ALNS framework) and Track B's #1 (MWPM destroy-set
selector) are **complementary, not competing**. They combine into
a single move:

> **ALNS with MWPM-defect-pairing as one of the destroy operators.**

Concretely:
- Build the ALNS shell (multi-operator destroy + CP-repair +
  adaptive weights). 3-4 days.
- Implement destroy operators:
  - Random-region (baseline; mirrors existing region-repair)
  - Conflict-driven (mirrors Houdayer)
  - **MWPM-defect-pairing** (novel; Kempe-chain destroy-set)
  - Worst-edge (lowest-match-density window)
- Adaptive weights select among operators based on
  per-operator improvement rate.

This is the single highest-EV move from the survey:
- Builds on existing infrastructure (edge-CP bipartite matching,
  region-repair, CP backtracker).
- Includes the cheap variant (random/conflict destroy = ALNS
  baseline) as a regression test.
- Adds the genuinely novel MWPM operator that has the sharpest
  mechanistic claim to break 449.
- ~7-10 days total; predicted +2 to +5 edges if the merged
  hypothesis holds.

**Important caveat to verify before building**: in surface
codes, defects always come in pairs by construction (every
Pauli error creates exactly 2 syndrome flips). E2 has 31
mismatches — odd. The MWPM analogy needs adaptation: either
add a "virtual boundary defect" (standard QEC trick for open
boundaries) or rethink the mapping. This is a 1-day
back-of-envelope check before committing.

### Diagnostic (cheap, do alongside B1+A1)

Run **Survey Propagation (B2)** as a one-off diagnostic before
the ALNS build. If SP reports our plateau corresponds to a 1RSB
cluster, all local-search methods (including ALNS) are
fundamentally limited. If it reports something more tractable,
we proceed with ALNS+MWPM confidently. Cost: ~1-2 weeks if
implementing from scratch; cheaper if a pysat/cnf-tools BP
wrapper exists.

### What we're NOT doing

Per the survey rankings, the following are deferred or skipped:
- **MCTS + neural policy** (30-45 days, very high variance) —
  defer until ALNS+MWPM either succeeds or definitively rules
  out the move-set hypothesis.
- **Path-decomposition DP** (14-21 days, +0 edges, but bounds) —
  diagnostic only; do it only if we've decided 449 needs to be
  proved tight rather than improved.
- **Lagrangian relaxation, MIP+column-generation** — dominated
  by SAT/CP at E2 size per Salassa 2017.
- **Diffusion-PT proposals (B3)** — highest-variance; defer.

### Revised session-2 priority

1. **Sanity-check the MWPM defect-pairing mapping** (1 day). Is
   the 31-defect parity issue resolvable cleanly?
2. **Build ALNS shell + random/conflict-driven destroys** (3-4 days).
   Verify it reaches our PT baseline (~449) — regression test.
3. **Add MWPM-defect-pairing destroy operator** (2-3 days).
4. **Run for a real budget** (overnight). Report whether we
   break 449.
5. **In parallel**: launch SP diagnostic (B2). Even if the
   timing doesn't line up with the ALNS run, the SP result
   informs whether further local-search investment makes sense.

### Recovered context from the survey

The survey makes our progress trajectory legible:
- 2012 SOTA: 458/480 (Wauters tabu+VLNS).
- 2010 META'10: 461/480 (memetic).
- 2008 published: 467/480 (Verhaard backtracking).
- 2020 repo: 468-470/480 (Blackwood, 1-clue variant).
- Our 2026 stack: 449/480 (cell-CP→PT).

We're at the 2010-era heuristic level despite better
infrastructure. Track A's verdict is sharp: "**our 449 is
below 2012-era SOTA**." This implies real headroom from
move-set improvements alone — the structural-ceiling hypothesis
from vol. 3-4 may be over-pessimistic.

The reframe: maybe 449 is **not** the structural ceiling — it's
the **single-piece-PT ceiling**. ALNS+MWPM, by introducing
multi-piece coordinated moves, could land us at 458-461 (the
documented SOTA range) without changing the structural
hypothesis. Only if those *also* fail do we have evidence the
459+ region is actually unreachable.

---

## SESSION 2 PLAN (vol. 4, building starts now)

### MWPM-mapping sanity check (paper derivation)

In a surface code:
- Lattice = cells; syndromes = parities of Pauli errors on
  incident edges.
- A single qubit error on an edge flips both adjacent cell
  syndromes → **defects always come in pairs (Z2 parity)**.
- MWPM pairs defects; each pair = a "correction string"
  connecting them; flipping the string's edges restores zero
  syndromes.

In E2:
- Lattice = cells; mismatches = interior edges where two cells
  disagree on color.
- A single piece-rotation/swap at cell c can change 0-4
  incident-edge match states simultaneously → **no Z2 parity
  conservation**. The count of mismatches can change by any
  amount in {-4, ..., +4} per move.

**Direct surface-code analogy fails on parity.** Defects in E2
do NOT come in pairs by construction; we have 31 mismatches at
the canonical plateau (odd).

**But the core idea survives, weakened:** matching on the
mismatched-edge graph is a *heuristic destroy-set selector*,
not a correction algorithm. Specifically:

- **Nodes** = the n mismatched edges of the current board
  (n ≈ 31 on a 449-plateau).
- **Edges** between two mismatches = shortest cell-path between
  them. Weight = path length (Manhattan / hop count).
- Compute a min-weight matching (regular matching, Edmonds
  blossom). If n is odd, leave one defect unmatched.
- The **destroy-set** = union of cells on the matched paths.
  These are the cells whose simultaneous re-placement
  *could* jointly resolve their incident mismatches.

This is provably *not* a correction algorithm:
- Re-placing the destroy-set cells doesn't guarantee fewer
  mismatches (the repair-CP may not find a better assignment).
- Defects can be "boundary defects" (adjacent to a cell that's
  also wrong but to a different defect) — the matching
  ignores this.

It IS a *principled* destroy-set selector:
- Cells on short defect-defect paths are exactly where the
  current placement is locally incoherent.
- CP repair on these cells, with neighbors pinned, asks:
  "can we re-place these cells to remove both endpoint
  mismatches at once?"
- The minimality of the matching ensures the destroy-set is
  small enough for fast CP repair, large enough to give CP
  freedom.

**Verdict on sanity check**: ✓ proceed, but with the
understanding that MWPM is a *destroy-set heuristic for ALNS*,
not a stand-alone correction algorithm. The Track-B agent's
framing as "the exact algorithm QEC uses" was too strong; the
real claim is "a principled, cheap, defect-aware destroy
selector that single-piece moves can't replicate."

### Architecture

We need:

```
ALNS loop:
  current_board ← starting board (e.g., from cell-CP → PT seed)
  best_board ← current_board
  operator_weights ← uniform initial weights
  loop until budget:
    op ← roulette-select(destroy operators, operator_weights)
    free_set ← op(current_board)               // 30-100 cells typically
    new_board ← cp_repair(current_board, free_set, time_budget_ms=200)
    if new_board is None: continue              // repair failed
    Δ = score(new_board) - score(current_board)
    if accept(Δ): current_board ← new_board
    if score(new_board) > score(best_board): best_board ← new_board
    operator_weights[op] += reward(Δ)
```

**Destroy operators** (Rust trait):

```rust
pub trait DestroyOperator {
    fn destroy(&mut self, board: &Board, rng: &mut Rng) -> BTreeSet<Position>;
    fn name(&self) -> &str;
}
```

Implementations:
1. `RandomRegion { k: u32 }` — uniform-random k×k window.
2. `WorstWindow { k: u32 }` — pick window with lowest matched-edge density.
3. `ConflictDriven { radius: u32 }` — start from a random mismatched edge; grow set by 4-grid-adjacency until size cap.
4. `MwpmDefectPairing { matching_cost_cap: u32 }` — build mismatched-edge graph; min-cost matching; union of paths on matched pairs.

**Repair operator** (Rust function):

```rust
pub fn cp_repair(
    puzzle: &Puzzle,
    board: &Board,
    free_set: &BTreeSet<Position>,
    budget_ms: u64,
) -> Option<Board>
```

Reuses `eternity2_localsearch::repair::repair_region` logic
but accepts an arbitrary free-set (not just a rectangle).
Returns `None` if CP fails / times out without completing.

**Acceptance criterion** (Rust enum):

```rust
pub enum AcceptanceCriterion {
    Greedy,                          // accept only Δ > 0
    SimulatedAnnealing { t: f64 },   // Metropolis with cooling
    RecordToRecord { d: f64 },       // accept if score ≥ best - d
}
```

Default: SA-style with linear cooling, starting at T=2.0,
ending at T=0.05 (matches our PT temperature range).

**Adaptive weights** (Rust struct):

```rust
pub struct AdaptiveWeights {
    weights: Vec<f64>,              // one per operator
    rewards: Vec<f64>,              // cumulative reward this segment
    counts: Vec<u32>,
    segment_iters: u32,             // recompute weights every N iters
}
```

Reward schedule (per Ropke-Pisinger 2006):
- `σ1` for new best score
- `σ2` for accepted move with Δ > 0
- `σ3` for accepted move with Δ ≤ 0
- `σ4` for rejected move
Typical: σ1=33, σ2=9, σ3=13, σ4=0. Decay weights by factor
`r = 0.1` per segment to prevent runaway dominance.

### Crate layout

Add `crates/localsearch/src/alns.rs` (new module in existing
crate; doesn't justify a new crate yet — shares board/CP
infrastructure with PT and SA).

New bin `crates/benchmark/src/bin/alns_e2.rs` parallel to
`pt_e2.rs`:
- CLI args: time budget, starting board (from a plateau JSON
  or fresh CP seed), operator selection, log verbosity.
- Reports best board + per-operator stats at end.

### Validation strategy

1. **Regression**: ALNS with only `RandomRegion` destroy
   should reproduce performance similar to vol. 2's
   `repair_region` — confirms the shell is wired up.
2. **Operator-comparison**: run with each destroy operator
   alone, then with the full portfolio. Per-operator
   improvement count is reported.
3. **MWPM-specific test**: on a known 449 plateau, verify
   that MWPM picks cells that overlap with our plateau
   analysis's 4 components from vol. 4. If MWPM picks
   *different* cells, that's interesting — its
   defect-distance metric sees structure the
   connected-component analysis missed.
4. **Final overnight run**: 6-12h on the canonical 449
   plateau, full operator portfolio, with adaptive weights.
   Target: any improvement past 449. Stretch target:
   reach 458 (Wauters 2012) or 461 (META'10).

### Out of scope this session

- Survey Propagation diagnostic (Track B #2). Deferred to a
  later session; this session is for actually breaking 449.
- Frame-first decomposition (Track A #1 alt). Different
  workstream — would change the entire pipeline architecture.
- Memetic GA (Track A #3). Would compete with ALNS rather
  than complement; defer until we see ALNS results.
