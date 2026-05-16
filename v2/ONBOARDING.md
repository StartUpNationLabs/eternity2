# Eternity II — autonomous-agent onboarding

**Purpose**: comprehensive reference for the consolidated v2 infrastructure.
If you (a future autonomous run, or a human collaborator) need to score, load,
save, verify, or run an experiment on an E2 board, READ THIS FIRST.

Established 2026-05-16 after vol-118 found and fixed a critical bf bug
that escaped vol-15 → vol-118 because the verification path was fragmented
across 14+ per-bin implementations. The consolidation work in vols 118 T7-T9
collapsed that to one canonical implementation per concern.

---

## 1. Three things every E2 task needs

1. **Load a puzzle** (canonical 16×16 Selby-Riordan + canonical hints).
2. **Load a board** (a placement of pieces, possibly partial).
3. **Score / verify** the board.

All three have ONE canonical implementation. Use them; don't roll your own.

### Loading the canonical puzzle

```rust
use eternity2_benchmark::loader::load_puzzle_with_hints;
use std::path::PathBuf;

let puzzle_path = PathBuf::from("../data/puzzles/size_16_official_eternity.csv");
let (puzzle, hints) = load_puzzle_with_hints(&puzzle_path).expect("load puzzle");
```

The CSV's color encoding: 16-bit binary words. `1111111111111111` = BORDER (color 0).
Other values map directly: `0000000000000001` → color 1, `0000000000000010` → color 2, ...
Canonical puzzle has 22 interior colors + BORDER.

### Loading a board

```rust
use eternity2_export::load_board;

let board = load_board(&path, &puzzle)?;  // returns Result<Board, LoadError>
```

**`eternity2_export::load_board` reads ALL three on-disk formats:**
- Canonical placement-sparse: `{"placement": [{"pos","piece_id","rotation"}]}`
- Placement-indexed (legacy): `{"placement": [{"piece_id","rotation"}]}` (index = position)
- DumpedBoard (legacy): `{"cells": [[pid, rot] | null, ...]}` (index = position)
- Nested: `{"board": {"placement": [...]}}` (from run_e2_restart summaries)

**DO NOT** write your own `fn load_board`. The 14+ duplicates were collapsed in vol-118 T9.

### Saving a board

```rust
use eternity2_export::{save_board, BoardMetadata};

let meta = BoardMetadata {
    source: Some("my_algorithm".to_string()),
    seed: Some(42),
    elapsed_ms: Some(60_000),
    note: Some("3-min ALNS basic from 452".to_string()),
};
save_board(&path, &puzzle, &board, &meta)?;
```

Writes the **canonical placement-sparse format** with explicit `pos` field
(see `docs/BOARD_FORMAT.md`).

For CSV: `save_board_csv(&path, &puzzle, &board)?` / `load_board_csv(&path, &puzzle)?`.

### Scoring + verifying

The CANONICAL scorer is `eternity2_export::score_board(puzzle, board) -> (matched, total)`:

```rust
use eternity2_export::score_board;
let (matched, total) = score_board(&puzzle, &board);  // matched/480 for canonical
```

`matched` = count of edge-color matches between adjacent placed pieces.
`total`   = count of total placed-pair adjacencies (capped at 480 for a complete 16×16).

**For a FULL verification including illegal-placement checks**:

```rust
use eternity2_export::verify;
let report = verify(&puzzle, &hints, &board);
println!("legal={}, complete={}, hints={}/{}",
    report.is_legal(), report.is_legal_complete(),
    report.hint_compliance.matched, report.hint_compliance.total);
```

`VerifyReport` checks:
- **piece-uniqueness** (no duplicate `piece_id`)
- **border-consistency** (no edge-piece at interior with BORDER edge facing inward — this catches the vol-118 bf-bucket-bug class!)
- **hint-compliance** (canonical hints in pinned positions+rotations)
- **edge-match score** (matched/total)

`is_legal()` = piece-unique + 0 border violations + all hints match.
`is_legal_complete()` = legal AND all 256 cells placed.

### Command-line verification

```bash
./target/release/verify_board <board.json> [<board.json> ...]
```

or via the canonical wrapper:

```bash
scripts/verify_records.sh <board.json> [...]
```

Returns exit 0 if all boards legal, 1 otherwise. Prints a summary table:

```
path                                              placed   matched/total   uniq    hints    borders   status
bseed1_score459.json                               256/256   459/480       256   0/5       0        ILLEGAL  ← 0/5 hints means it's 0-clue convention
v17a_par8_60s_FIXED.json                           231/256   414/431       231   5/5       0        LEGAL_PARTIAL
winning5_sa_t1_s100_*.json                         256/256   452/480       256   5/5       0        LEGAL_COMPLETE
```

For illegal boards, the bin dumps detailed violation breakdowns to stderr.

---

## 2. The board JSON format

See `docs/BOARD_FORMAT.md` for the full spec. Quick reference:

```json
{
  "placement": [
    {"pos": 0,   "piece_id": 3,   "rotation": 2},
    {"pos": 15,  "piece_id": 17,  "rotation": 0}
  ],
  "score": 459,
  "metadata": {
    "source": "bf_bw_schedule_hinted",
    "seed": 42
  }
}
```

- `pos`: row-major position, `pos = y * width + x` (0-indexed).
- `piece_id`: 0-indexed integer.
- `rotation`: 0|1|2|3 (90° clockwise turns).
- **Empty cells are OMITTED** from the placement array.

CSV format:
```
pos,piece_id,rotation
0,3,2
15,17,0
```

---

## 3. Score conventions (clarity matters)

There are MULTIPLE valid "score" interpretations. Always be explicit about which.

| convention                  | score | how reached | check |
|-----------------------------|------:|-------------|-------|
| Matched-edges (4/5 hints)   |   459 | our pipeline | hints_matched ≥ 4 |
| **Strict-canonical (5/5)**  |   457 | blackwood_mrv | `verify_board` reports `5/5` |
| 1-clue (Blackwood's puzzle) | 470 | Blackwood algorithm | different puzzle |
| McGavin corner perm (3,2,0,1) | 469 | McGavin algorithm | corner perm + 5/5 |
| Unconstrained (0/5 hints)   |   469 | corpus max | hints_matched = 0 |

Memory `reference_blackwood_decoded`: Blackwood's 470 is on the 1-CLUE variant, not the 5-clue canonical Selby-Riordan.

`reference_e2_corpus_480_false_positives`: 4 boards in our corpus claim 480 — all FALSE positives (different piece sets).

---

## 4. The pipeline: what produces records

The strict-canonical pipeline (gets to 446-452):

```
par-8 bf_bw_schedule_hinted (60s, v17a schedule, 5/5 hint pin)
   ↓ partial: ~231 cells, score ~414, 5/5 hints OK
edge_bound_ascent (1000 iter, accept-all, seed=42)
   ↓ score ~411, UB measurement
edge_target_match  (Hungarian, hint-preserving since vol-116)
   ↓ score ~430, 256/256 placed, 5/5 hints OK
alns_only --ops basic --alns-budget-ms 60000 --seed <N>
   ↓ score 443-452, LEGAL_COMPLETE 5/5
```

The cross-machine SOTA 459 (4/5 convention) was:
- `vanilla_path border-first × 9 threads × 30 min` → 403
- `alns_only --ops minimal × 5min seed=1` → 452
- `alns_only --ops minimal × 8 inputs × 8 seeds × 15 min sweep` → 454
- `alns_only --ops basic × 30 min seed=42 from 454` → **459**

---

## 5. Critical conventions / gotchas

### `--ops basic` ≠ `--ops winning5`

Per memory `project_e2_459_sota_cross_machine`:
- `minimal` (4 destroy ops) is the right starting point.
- `basic` = `minimal` + `WorstBand{4}` — the smallest escalation past minimal.
- `winning5` = `basic` + `ConflictDriven{80}` — adds aggression.
- `mega`/`full` scorch good cells; DO NOT use for record-track work.

Empirical: **`basic` beats `winning5` 4/4 in paired comparisons** on strict-canonical pipeline output. Use `basic` as default.

### `relaxed_bound` is NOT an upper bound

`eternity2_bench_audit::relaxed_bound` returns a greedy local-search score WITH PIECE REUSE. It's OFTEN HIGHER than the true integer ceiling. **Never** call it a "bound" without "greedy-relaxed (NOT a UB)".

For TRUE upper bounds: `border_lp_ub` (LP relaxation, sound UB) or vol-55 cluster MIP (integer ceiling).

### Hint conventions in CSV

The canonical puzzle CSV embeds hints inline. The columns are `top,right,bottom,left,x,y,rotation`. A non-zero `(x,y,rotation)` triple at any piece row marks that piece as a canonical hint placed at `(x,y)` with the given rotation.

Canonical 5 hints (positions in row-major: `pos = y*16 + x`):
- pos 34 = (2, 2), piece 207, rot 1
- pos 45 = (13, 2), piece 254, rot 1
- pos 135 = (7, 8), piece 138, rot 0 (CENTER)
- pos 210 = (2, 13), piece 180, rot 1
- pos 221 = (13, 13), piece 248, rot 2

### Output paths must be timestamped

Per CLAUDE.md trap #6:
> Scripts that write to `output/some_name/` overwrite previous runs. This destroys history. Every script must default to `output/some_name_$(date +%Y%m%dT%H%M%S)/` or use `VOL_RUN_TAG` envvar.

The `vol60_corner_sweep.sh` and `vol118_par_bf_ub_filter_sweep.sh` patterns are the template.

### Re-verify any board claim

Per CLAUDE.md rule #5: every claimed record must pass `verify_board`. The vol-15 → vol-118 bf-bucket bug demonstrates why — even valid-LOOKING partials can have illegal placements that ONLY surface under proper verification.

---

## 6. The 459 problem — current understanding

The 459-level set is structurally rigid. As of vol-118:

- **Cluster A** (5 distinct basins, from our pipeline): pairwise Hamming 34-44, max σ-cycle 9-25.
- **Cluster B** (vol-60 RECORD_TIE_459): Hamming 251-253 to Cluster A.
- **McGavin-469**: 154-cycle σ-distance from any 459. Indecomposable.

**All tested algorithmic operators bounded ≤ 459** from any starting 459 basin:
- Direct ALNS, pipeline ALNS, σ-subset enumeration, σ-cycle apply, basin-mix MIP (4 basins), high-T MCMC, σ-cycle Metropolis, greedy min-boundary subset, intra-cluster σ-subset.

**Quantitative bound** (vault/MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM.md):
Δ(S) ≈ -B(S) where B(S) is the grid-boundary cardinality of σ-subset S.
For 154-cycle, min B ≈ 64-190, all >> ALNS recovery capacity. σ-subset attack STRUCTURALLY refuted.

To break 459 (or strict-canonical 457): need an operator OUTSIDE the explored family. Candidates:
1. RL self-play (multi-week, unrefuted theoretical handhold)
2. Cutting-plane MIP (multi-week)
3. Longer ALNS budgets (memory: 30min from 454 → 459 worked)
4. Hint-aware schedule recalibration (vol-118 T5 sketch, low priority post-conflict-fix)

---

## 7. Common bins (canonical pipeline tools)

All located in `target/release/` after `cargo build --release -p eternity2-bench-audit`.

| bin                          | role                                                |
|------------------------------|-----------------------------------------------------|
| `verify_board`               | comprehensive verifier (piece-uniqueness + border + hints + score) |
| `rescore_board`              | quick score recomputation (legacy; use verify_board) |
| `diff_boards`                | piece-id cell-by-cell diff between two boards |
| `print_bucas`                | print bucas-render URL for visual inspection |
| `bf_bw_schedule_hinted`      | 5/5-hint-pinned blackwood schedule DFS (vol-117 T1 / vol-118 T5) |
| `bf_bw_hinted`               | 5/5-hint-pinned raw DFS (no schedule) |
| `bf_bw`                      | unhinted blackwood schedule DFS |
| `edge_bound_ascent`          | UB-pushing iterative LP-driven board polish |
| `edge_target_match`          | Hungarian piece-position matching (hint-preserving since vol-116) |
| `alns_only`                  | run ALNS on a saved board (`--cp-board PATH`) |
| `io_smoke_test`              | sanity-check load_board / save_board round-trip |

### Pipeline invocation

```bash
# 1. Get a strong hint-respecting bf partial (60s, par-8)
./target/release/bf_bw_schedule_hinted --threads 8 --seed-offset 0 \
  --budget-ms 60000 --schedule v17a \
  --dump-partial output/run/par_bf.json

# 2. Verify it
./target/release/verify_board output/run/par_bf.json

# 3. Run bound-ascent
./target/release/edge_bound_ascent --board output/run/par_bf.json \
  --iters 1000 --seed 42 --acceptance accept
# writes output/v21_bound_ascent_b<UB>_s<score>.json

# 4. Hungarian
./target/release/edge_target_match \
  --board $(ls -t output/v21_bound_ascent_*.json | head -1)
# writes output/v21_target_match_<score>.json

# 5. ALNS sweep
for SEED in 1 7 42 100; do
  for OPS in basic; do
    ./target/release/alns_only \
      --cp-board $(ls -t output/v21_target_match_*.json | head -1) \
      --alns-budget-ms 60000 --seed $SEED --ops $OPS
  done
done
# writes to output/v17_alns_only/

# 6. Verify final boards
./target/release/verify_board output/v17_alns_only/*.json
```

---

## 8. Building & testing

```bash
# Build everything
source $HOME/.cargo/env
cargo build --release --workspace

# Build only bench-audit bins (after T9 migration, this is most bins)
cargo build --release -p eternity2-bench-audit --bins

# Run unit tests on export crate (verify + I/O round-trip tests)
cargo test --release -p eternity2-export

# Test a specific bin against canonical data
./target/release/verify_board output/vol-110/basins/bseed1_score459.json
# expected: matched=459/480, hints=0/5 (it's a 0-clue board)
```

---

## 9. Where things are

```
v2/
├── crates/
│   ├── core/              # Board, Puzzle, Hints, PieceId, Rotation, BORDER
│   ├── puzzle-io/         # load_puzzle_with_hints (legacy alias)
│   ├── benchmark/         # loader::load_puzzle_with_hints (forwards to puzzle-io)
│   ├── export/            # CANONICAL load_board, save_board, verify, score_board, bucas_url
│   ├── blackwood-fast/    # 232×-faster engine (vol-106-115)
│   ├── solver-engine/     # the CSP backtracker (5 profiles)
│   ├── localsearch/       # ALNS, PT
│   └── bench-audit/       # ~88 experiment bins (all using canonical I/O after vol-118 T9)
├── docs/
│   └── BOARD_FORMAT.md    # canonical JSON + CSV schemas
├── scripts/
│   ├── verify_records.sh        # canonical verifier wrapper
│   ├── vol118_T9_bulk_migrate.py # migration tool (history)
│   └── ...                # experiment-specific scripts
├── vault/                  # Obsidian-compatible knowledge base
│   ├── INDEX.md           # MoC, click any wikilink
│   ├── README.md          # vault discipline
│   ├── concepts/          # one page per algorithm/structural finding
│   ├── basins/            # notable boards
│   └── sessions/          # per-volume journals
├── output/                 # experimental results
└── data/puzzles/           # canonical puzzle CSVs
```

---

## 10. The "diff first" rule (CLAUDE.md #2 and #11)

When asking "are two boards the same?", the FIRST action is to compare
placement piece-ids cell-by-cell. Color labelings (Bucas's Joshua coloring
vs our pt coloring) can σ-permute, but piece-ids 0..255 are unambiguous.

```bash
./target/release/diff_boards <a.json> <b.json>
```

NEVER reason about "same board" from bucas URLs alone — colors can permute.

---

## 11. When you discover a bug

The vol-118 bf-bucket bug was found because the user visually inspected
a bucas render and noticed broken edges. The bug had been hiding since
vol-15 because:

1. Complete-board scoring catches illegal placements (they cost score, so
   optimization removes them).
2. Per-bin verify scripts didn't check "no BORDER edge facing interior
   neighbor".
3. Visual inspection (bucas render) was the only way to catch it.

**Mitigation**: `verify_board` now checks border-consistency. Run it on
every partial output and every record claim.

If you find a similar bug:
1. Reproduce minimally.
2. Verify with `verify_board`.
3. Document in a new `vault/concepts/<bug-name>.md` page.
4. Fix the engine.
5. Commit with `CRITICAL FIX:` prefix.
6. Update this onboarding doc if the bug class wasn't caught by canonical tools.

---

## 12. Self-check rules for autonomous runs

Per CLAUDE.md ROLE rules:

1. **What are you working on? Highest-EV available track?**
2. **Comfort-lottery?** (Same op + new seed + new budget = NO)
3. **Notes AS YOU GO?** Vault concept page touched this hour?
4. **Variance / rescoring / diffing?** Don't claim results without them.
5. **CVC / 8x8 OUT OF SCOPE** per 2026-05-16 directive.

Senior-researcher mode: do the math when math is the bottleneck.
NO LIMITING THOUGHTS on ambition. NO time estimates.
Never pause, never wait. User is away ~1 month.

---

**Last updated**: 2026-05-16 by vol-118 autonomous run (post-T9 consolidation).
