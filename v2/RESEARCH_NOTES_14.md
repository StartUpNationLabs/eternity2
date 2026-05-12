# RESEARCH_NOTES_14.md — vol-14 session log

**Started**: 2026-05-12 14:43 CEST.
**Brief**: `RESEARCH_NOTES_14_PLAN.md`. Compose v6-v13 learnings into one
runnable stack; portfolio composition, not another isolated probe.

## Calibration (vol-14 start)

| stack | budget | best | source |
|---|---|---|---|
| `joe_depth150_par` CP cold | 5 min | depth 174, 303/480 | vol-12, `output/v12_run/run_e2_5min_board.json` |
| vol-12 CP → ALNS fill | 5 + 5 min | 443/480, flat after 15 s | vol-12, `output/v12_fill/alns_443.json` |
| vol-6 warm-PT (historical) | many h | **454/480** | vol-6 record `HISTORIC_first_454_1778567792.json` |
| McGavin 2020 (community) | ~200 cores × few days | **469/480** | reference (verified ceiling) |

Tiers: 1 = #1 ships + measurable depth lift vs 174. 2 = ≥454 cold. 3 = ≥460
cold or structural artifact. 4 = ≥469/≥470 (tie/clear SOTA).

## Tonight's plan

1. **Ship #1**: port vol-12's edge-color BP marginals
   (`output/v12_bp/edge_bp_60i.json`, 544 edges × 23 colors) as a new
   `ValueOrder::EdgeBpMarginals` in `solver-engine`. Combine with
   `joe_depth150_par` ⇒ new profile `joe_depth150_par_bp`. Bench at
   5 min on canonical E2.
2. **If time after #1 lands**: start #2 (Joe-Saunders true RESTART loop),
   wrapping `EngineSolver::solve` with an outer loop that prunes back
   to depth T and re-randomizes after N stuck iters. v12 shipped only
   the depth-gate; the *restart* policy is the missing piece.
3. **#3+**: parked unless #1/#2 land early.

## Why edge-BP-as-value-order first

- Vol-12 measured **18.84% interior-edge entropy reduction** from BP,
  **2.24× more than vol-11's cell-encoding (8.4%)** which lost to
  random as value-order. In Python A/B edge-BP **beat** random
  (depth 67 vs 66; score 65 vs 62, 90 s budget). Crossing the
  signal threshold predicts useful lift in Rust where AC-3 + bitset
  amplifies any direction the heuristic biases toward.
- The 10¹⁰¹ vol-13 overcounting null says local methods are bounded —
  but as a heuristic *plug-in* into a CP engine that enforces global
  piece-uniqueness rigidly, BP marginals are safe (we just bias which
  branch to try first; correctness is preserved by the engine).

## Implementation sketch (#1)

- New `ValueOrder::EdgeBpMarginals` variant in `EngineConfig`.
- New `SolveOpts.edge_bp_marginals: Option<Arc<Vec<[f32; 23]>>>` —
  flat per-edge × 23 colors. Loader: `load_edge_bp_marginals(path)
  -> std::io::Result<Arc<...>>`.
- `SearchState::new` precomputes `cell_side_edge: Vec<u32>` of length
  `n_pos*4` mapping (cell,side) → edge_id. Construction must match
  the Python BP edge enumeration order exactly:
  - Cells scanned (y,x) in row-major.
  - For each cell: assign N (or reuse from northern neighbour's S),
    S only if y == H-1, W (or reuse from western neighbour's E),
    E only if x == W-1.
- In `recurse()`: if value-order is EdgeBpMarginals, score each row
  by `Σ_{side=0..4} marginal[edge_id[cell,side]][row.edges[side] as usize]`,
  sort **descending** (higher = engine prefers this branch).
- Smoke test: assert mapping by checking number of boundary edges
  (64) and total (544) match the BP file.

## Run plan

```
cargo test -p eternity2-solver-engine     # green
cargo build --profile bench-fast -p eternity2-bench-audit --bin run_e2_5min
./target/bench-fast/run_e2_5min           # baseline already on disk; rerun for parity-ofdate
# Then variant: a new bin or edit to switch profile.
```

Bench output → `output/v14_bp/run_e2_5min.log` and `_board.json`.

## Status

- [x] #1 EdgeBpMarginals ported + green tests (commit `6679045`)
- [x] #1 30 s smoke A/B: BP +4 depth, +10 edge matches, +4 placed
- [ ] #1 5 min A/B in progress (PID 87879, started 14:54)
- [ ] Tier rating + memory update
- [ ] (Stretch) #2 Joe RESTART

## Output-dir cleanup (2026-05-12 14:56)

- 74 stale top-level exploration boards swept into
  `output/_archive/loose_top_level/` (vol-7..10 pt_e2 + alns_e2 runs).
  HISTORIC + all 454-class boards retained at top level.
- v14 bench harnesses now write to `output/v14_<topic>/run_<unixsecs>/`
  so reruns don't overwrite. A `latest` symlink points to the most
  recent run.
- `/output` is already `.gitignore`d — these moves are filesystem-only,
  no commits.

Convention for vol-15+: any new bench bin should call
`output/v14_<topic>/run_<unix>/` (see
`crates/bench-audit/src/bin/run_e2_5min_bp_ab.rs::main`).
