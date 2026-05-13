# VOL-26 — Learned value-order gate

**Opened**: 2026-05-13.
**Status**: drafted; awaiting execution.
**Note on ordering**: vol-26 is planned/executed BEFORE vol-25. The user shipped vol-25's CURRENT-VOL.md draft separately on the same day. The vol numbers are labels, not strict chronology — when reading the vault, vol-25's session journal will exist (chronologically later) and vol-26's will reference "shipped before vol-25."

## Why this volume exists

Vol-25 research pass produced three findings:
- **σ-bijection is not algebraic** ([[symmetry-analysis]]): no group-theoretic shortcut for canonical 5-clue E2.
- **Pure GA is structurally refuted** ([[genetic-algorithm]] amended): 16 years of literature, 6 independent attempts, cap at ~396 cold-start.
- **Diffusion-for-CSP is genuinely underexplored on edge-matching puzzles**: DIFUSCO (2023), DiffAssemble (CVPR 2024), JPDVT (CVPR 2024), PuzzleFusion (NeurIPS 2023) all target image jigsaw or Voronoi puzzles. **No published work tries discrete-diffusion / learned value-ordering on color-edge-matching at E2 scale.**

User-proposed framing: use a **Selby-Riordan-style generator** to produce synthetic E2-family puzzles with known solutions, train a learned model on the family distribution, evaluate transfer to canonical E2. This is exactly how training data works in ML; we'd been overthinking the "where does training data come from" question.

This vol does NOT commit to full diffusion. It commits to the **day-1 gate**: does *any* learned value-order beat MRV on small synthetic puzzles from the E2 family?

## Audit-at-open

Items aged ≥ 3 volumes — most were resolved at vol-24 open. Remaining open:

- **`piece-orbit-as-atom`** (5 vols, vol-20). Low value; deferring to vol-25 audit (the user is shipping vol-25 separately tonight per stated workflow).
- **`multi-cell-bound-ascent`** (3 vols, vol-22). Deferring to vol-25.
- **`bound-floor-alns-with-per-step-check`** (3 vols, partial). Deferring to vol-25.
- **`bound-ascent-then-blackwood-cp`** (3 vols, vol-22). Deferring to vol-25.
- **`gap-recording-instrumentation`** (3 vols, vol-22). Cheap; deferring to vol-25.
- **`diverse-457-search`** (3 vols, partial). Deferring to vol-25.
- **`kissat-rc2-maxsat`** (2 vols). Below threshold; no action.

Vol-26 does NOT need to audit these because vol-25 (which the user is shipping the same day) will. **Discipline gap acknowledged**: an audit should normally happen at every vol-open; this is the one exception, justified by the vol-25/vol-26 chronology inversion.

## Binding item

### T1 — Learned value-order gate on synthetic E2-family puzzles

**Question**: Does a small learned model trained on synthetic E2-family puzzles produce a value-ordering that strictly outperforms MRV when used as the engine's value-order on held-out synthetic puzzles?

**If yes**: vol-27+ scales up to canonical 16×16, and the diffusion direction is alive.
**If no**: the approach is dead at small scale and is unlikely to work at large scale. Close the door cleanly.

### Method (concrete)

**Step 1 — Generator (Python, ~200 LOC, ~3 hrs)**
- Re-implement the Selby-Riordan generator in Python. The existing C++ generator is in `solvers/` (read-only legacy); shelling out is more fragile than re-implementing.
- Inputs: board size `(W, H)`, n_border_colors, n_interior_colors, seed.
- Outputs:
  - `puzzle`: list of 256 pieces, each `(top, right, bottom, left)` colors.
  - `solution`: list of `(position, piece_id, rotation)` placements giving the canonical assembly.
- Generation procedure follows Selby-Riordan: build a solution first (place pieces with random edge colors respecting the constraint graph), then shuffle the pieces. Outputs are guaranteed to have at least one solution (the one we built).
- Validation: run our existing engine on 10 generated 6×6/5-color puzzles, confirm it solves all 10 within 5 seconds.

**Step 2 — Dataset (Python, ~30 min build, ~1 hr compute)**
- Generate 10 000 training puzzles + 200 held-out test puzzles at 6×6, 5 interior colors. Seed range 1..10 000 for training, 100 000..100 200 for test (disjoint).
- For each puzzle, generate the **search trajectory** of an optimal solver. Specifically:
  - Run our engine in FirstSolution mode on the puzzle with MRV + BorderFirstMRV.
  - At every successful placement, record `(partial_board_state, chosen_position, chosen_piece, chosen_rotation)`.
  - This is the "expert demonstration" data — each tuple says "given this partial board, an optimal solver picked this placement."
- Format: parquet files in `v2/ml/data/`. Schema:
  - `partial_board: bytes` (256-cell flat array of `(piece_id, rotation)` or `None`).
  - `next_position: u16`.
  - `next_piece_id: u16`.
  - `next_rotation: u8`.
  - `puzzle_id: u32`, `depth: u16` (for analysis).
- Expected size: ~36 tuples per puzzle (avg depth) × 10 000 puzzles = 360 000 tuples. Plenty for a small model.

**Step 3 — Model (Python + PyTorch, ~1 day build + ~2 hrs train)**
- **Architecture**: a small graph neural network. Input: the constraint graph of the partial board (nodes = cells, edges = adjacency; node features = `(placed_piece_one_hot, placed_rotation_one_hot, is_border, is_corner, neighbor_pinned_colors)`).
- 4 layers, hidden dim 64, ~200 k parameters. Edge-conditioned attention (standard GAT-style).
- Output: per-cell scores. The cell with the highest score is the predicted next position. For piece selection, a separate head outputs a piece-score per (position, piece-rotation) candidate.
- **Loss**: cross-entropy on the next-placement choice. Standard imitation learning.
- **NOT diffusion at this stage.** Diffusion adds complexity that doesn't matter at the gate. Imitation learning is the simplest possible learned signal; if even this beats MRV, diffusion is worth scaling up. If imitation learning doesn't beat MRV, diffusion won't either.
- Training: 50 epochs, Adam, lr 1e-3. ~2 hrs on a single GPU; longer on CPU. We have an M1 — MPS backend works fine for this scale.

**Step 4 — Bridge (Rust↔Python, ~4 hrs)**
- Add `ValueOrder::Learned` variant to `crates/solver-engine/src/lib.rs`.
- At engine startup (if `ValueOrder::Learned`), spawn a Python subprocess running the model in inference mode.
- Bridge protocol: stdio JSON pipe. Engine sends `{"board": [...], "candidates": [...]}` per node where value-ordering matters. Python returns `{"scores": [...]}`.
- One Python process per engine instance (no batching across engines). Inference latency at this scale: ~3-5 ms per query, dominated by JSON parsing. Acceptable for small puzzles.
- **Production it isn't.** Day-1 gate: just enough to measure.

**Step 5 — Measurement (~1 hr)**
- For each of 200 test puzzles:
  - **MRV baseline**: solve with `EngineSolver::border_first_lcv()` (single-threaded, MRV variable order, LCV value order). 5-second budget. Record: solved (yes/no), node count, depth reached.
  - **Learned**: same engine, but `ValueOrder::Learned`. Same 5-second budget. Same records.
- **Gate condition**:
  - Learned solves ≥ 95% of MRV's solved set (no regression on coverage).
  - **AND** median node count on commonly-solved puzzles is ≤ 80% of MRV's.
  - **AND** at least one puzzle that MRV failed is solved by Learned (categorically new capability).

If all three conditions hold: **vol-27 scales up to 8×8, then 10×10, then canonical 16×16**.

If any condition fails: the approach is dead. Document the failure mode in [[learned-value-order]] (new concept page) with `status: refuted` and the specific numbers.

### Honest cost

- Generator: 3 hrs.
- Dataset: 30 min build + 1 hr compute.
- Model + training: 1 day build + 2 hrs train.
- Bridge: 4 hrs.
- Measurement: 1 hr.
- Writing: 2 hrs.

**Total: 2-3 days of focused work.** Plausible single sitting if uninterrupted. NOT a 1-2 week commitment.

## What this vol explicitly does NOT do

- ❌ Full discrete diffusion (DIFUSCO architecture). Imitation learning is enough for the gate.
- ❌ Canonical 16×16 evaluation. Only 6×6 synthetic family.
- ❌ Self-play / RL. Supervised imitation only.
- ❌ Production-quality bridge. Stdio JSON is fine.
- ❌ Record-breaking attempt. The gate is a methodology test, not a 469-breaker.
- ❌ Multi-GPU, distributed training, fancy architectures. Small model, single device.

## Discoveries during the vol → log, don't pivot

Per CLAUDE.md vault discipline: any mid-vol findings go to `BACKLOG.md` as new entries. The pull to "actually, let's just use the full diffusion model" or "let's just try it on 16×16 right away" must be resisted — those are vol-27+ decisions. **One binding item; it ships or it doesn't.**

## Vol-close protocol

At vol-26 close:
1. Update T1 status in BACKLOG (`built` / `refuted` per gate result).
2. Create `vault/concepts/learned-value-order.md` with the measurement table (gate pass/fail with numbers).
3. Create `vault/concepts/synthetic-puzzle-generator.md` documenting the Selby-Riordan re-implementation.
4. Write `vault/sessions/vol-26.md` journal (compact, single page, link to concepts).
5. Update `vault/INDEX.md` — add a row to score-history (likely "no record change", but note the methodology result) and add new concepts to the catalogue.
6. **Draft `vault/plans/VOL-27.md`** that gates on vol-26's result:
   - If gate passed: vol-27 scales up to 8×8 evaluation.
   - If gate failed: vol-27 picks a different lever (engine profile B-1, or 1-clue calibration, or just publishability writeup of 457).
7. If a memory entry is warranted (the gate result is "important enough that a fresh agent would benefit from knowing it"), add it.

## File layout

```
v2/ml/                              # NEW — Python ML directory
├── pyproject.toml                  # uv project
├── uv.lock
├── .gitignore                      # excludes data/, runs/, *.pt
├── README.md                       # how to run the experiment
├── selby_riordan.py                # generator
├── dataset.py                      # generate + load training tuples
├── model.py                        # small GNN
├── train.py                        # training loop
├── infer_bridge.py                 # stdio JSON bridge (runs as subprocess)
├── evaluate.py                     # gate measurement
└── data/                           # GITIGNORED
    ├── train_6x6_5c.parquet
    ├── test_6x6_5c.parquet
    └── runs/
        └── 2026-05-13_gate_v1/
            ├── model.pt
            ├── metrics.json
            └── logs.txt
```

```
v2/crates/solver-engine/src/lib.rs  # MODIFY
                                    # Add ValueOrder::Learned variant
                                    # + bridge integration (one new file: bridge.rs)
```

## Open questions to handle as they come up

- **Tokenisation of piece IDs**: 256 pieces is fine as 256-way one-hot. Larger puzzles would need embeddings; 6×6 doesn't.
- **Position encoding in the GNN**: the constraint graph already encodes adjacency; explicit positional encoding might or might not help. Try without first.
- **What does "MRV" mean exactly in our engine?** `BorderFirstMRV` (corners > edges > inner, ties by smallest domain) is the strongest variable-order baseline. **The gate compares to this, not to plain MRV without border priority.**
- **Are we comparing value-order or variable-order?** Both can be learned in principle. Vol-26 learns **value-order** (within the chosen position, which piece-rotation to try first). Variable-order stays BorderFirstMRV. Simpler; one axis at a time.

## Linked concepts (existing)

- [[scan-order]] — variable-order families we've tried
- [[edge-bp-marginals]] — learned-from-data value-order we already shipped (vol-12); the diffusion path generalises this
- [[selby-riordan-generator]] — the family we're sampling from (existing concept page describes the analysis we did, not a generator implementation)
- [[mismatch-geometry]] — the structural signal a learned model might pick up

## Linked concepts (will create)

- [[learned-value-order]] — vol-26 deliverable (gate result + numbers)
- [[synthetic-puzzle-generator]] — vol-26 deliverable (the re-implemented Selby-Riordan)

## Why this is worth doing

Reasoning honestly through the alternatives at vol-26-open:
- **Engine rewrite (B-1)**: 3-5 weeks of engineering. High cost, low novelty. Categorically a craft project.
- **1-clue calibration**: 1-2 days, diagnostic only. Doesn't give a path forward, just narrows the hypothesis space.
- **Tighter MaxScore bound (vol-25's old T1)**: Incremental on a saturated direction. Plausibly +5 points if it works.
- **Population GA**: literature-refuted at this scale.
- **σ-bijection**: literature-refuted in vol-25.
- **Learned value-order gate (this vol)**: 2-3 days, real chance of opening a new direction, clean gate condition that closes the question either way. **Highest information-per-hour of the remaining options.**

The gate is the entire point. If it fails, we know diffusion/learned approaches don't help on E2-family puzzles at any scale, and we close that door for the project (with a vault page documenting why). If it passes, we have a new direction worth months of follow-up work. Either way, in 2-3 days we know.

This is the right shape for vol-26.
