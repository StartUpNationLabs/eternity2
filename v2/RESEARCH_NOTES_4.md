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
