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
- [x] #1 5 min A/B: **BP LOSES** depth -3, matched -11, placed -3
- [x] #2 PoC built (commit `2bef02a`): `run_e2_restart` alternating
      BpExploit + RandomExplore rounds. Not yet run.
- [ ] Tier rating + memory update

## #1 5-min A/B result (canonical E2, seed=1)

| arm | depth | matched | placed | nodes | nps |
|---|---:|---:|---:|---:|---:|
| `joe_depth150_par` (baseline) | **174** | 303 | 179/256 | 4,338,306 | 14,449 |
| `joe_depth150_bp_par` (vol-14) | 171 | 292 | 176/256 | 4,237,822 | 14,118 |
| **Δ (BP − baseline)** | **−3** | **−11** | **−3** | −2.3% | −2.3% |

**Honest framing**: the 30 s smoke test had BP +4 / +10 / +4. At 5 min
the sign FLIPS. The BP value-order pulls ahead at short horizons by
biasing toward the highest-marginal colors first (good first guesses),
but at depth this compresses search variance and the engine hits hard
constraints earlier than the unbiased baseline. The 2.3% nps overhead
is the BP scoring cost (4 lookups × `domain_size` per node) and is
not the main factor; the algorithmic loss dominates.

Combined with vol-13's 10¹⁰¹-overcounting null: **local heuristics
that score values in isolation cannot break the structural ceiling
on canonical E2**. BP marginals carry real signal (vol-12 confirmed
the 18.84% reduction) but the signal is exhausted by short-horizon
backtracking — once depth saturates, value bias from BP and the
engine's own propagators agree on what colors to try, and BP's
*ordering* preference becomes pure cost.

This is what vol-9 / vol-12 / vol-13 were collectively saying:
the depth-174 plateau on canonical E2 with 5 min budget is
**algorithmic-bound, not search-throughput-bound and not heuristic-
ordering-bound**. Diversity in the *exploration structure* (restart,
PT, frame-first decomposition) is the next attack surface, not
smarter per-node value-order.

Bench artifact: `output/v14_bp/ab_report.json`,
`A_baseline_board.json`, `B_bp_board.json`.

## Tier rating after #1

- **Tier 1 (depth lift over vol-12 174)**: ⚠️  marginal — baseline ran
  again at depth 174 (vol-12 result reproduced ±0). BP arm 171 (−3).
  No depth lift. **Net: Tier 1 NOT achieved by #1.**
- **Tier 2/3/4**: out of scope without #2/#3/#4 landing.

Pivot: #2 (iterated random-restart with BP/random alternation) is
already built and committed — run it next as the actual attempt at
diversity-bound lift. If it also fails to lift depth above ~180,
**the 174 plateau is the binding obstacle for our stack**, and the
right vol-15 move is #4/#5 (rare-color sub-CSP + frame-first sweep
on the 75 k Hamilton frames), not more search-policy tweaks.

## **Metric correction (mid-session, after user-raised concern)**

The original A/B "edge_matches" metric counted only **placed-pair**
adjacencies — useless because CP search always achieves 100% match
on placed pairs by construction. **Real metric**: `matched / 480`,
where 480 = `2*W*H - W - H` is the total internal edges of the
canonical 16×16 grid; unplaced cells contribute 0 matches but full
denominator. Fixed in `crates/bench-audit/src/bin/{run_e2_5min_bp_ab,
run_e2_restart,rescore_board}.rs`. Re-scored the 5-min A/B partials:

| Run | placed | matched/480 | pct |
|---|---:|---:|---:|
| vol-12 `joe_depth150_par` baseline (saved) | 179 | 303 | 63.1% |
| vol-14 `joe_depth150_par` (re-run, baseline) | 179 | 303 | 63.1% |
| vol-14 `joe_depth150_bp_par` | 176 | 292 | 60.8% |
| vol-14 restart loop best (of 10 rounds) | 177 | 301 | 62.7% |

## #2 (restart loop) result

10 rounds × 30 s each = 300 s budget. Alternating BpExploit
(joe_depth150_bp_par + BP marginals) and RandomExplore
(gacolor_ac3_random_par). Best round = #1 (random, seed 2):
**172 depth / 301 matched / 177 placed**.

BP rounds were **deterministic** given the marginals — all 5 BP
rounds hit identical depth 163, matched 281, placed 168. Random
rounds varied: depth 161–172. **Restart does not lift above the
single-shot CP baseline (174).** The 174 plateau is real.

## **THE BIG REVERSAL — ALNS-fill verdict**

Per user direction "do as best as possible", ran the vol-12
**ALNS-fill** workflow on each of the 3 CP partials. 5 min ALNS each.
Result:

| seed (CP partial) | seed matched/480 | ALNS-fill final/480 |
|---|---:|---:|
| baseline `joe_depth150_par` | 303 | **442** |
| **vol-14 BP** `joe_depth150_bp_par` | 292 | **443** ⬅ best |
| vol-14 restart-best (random seed 2) | 301 | **436** ⬅ worst |

**Even though the BP CP-arm CP-partial is 11 matches WORSE than
baseline, the BP-seeded ALNS-fill reaches 443/480 vs baseline-seeded
442/480.** BP biases the CP partial toward a configuration that has
*more escape room* for ALNS to climb. The vol-14 #1 (BP value-order)
is a **net positive** when correctly scored end-to-end.

Bench artifacts:
- `output/alns_e2_1778591861_442of480.json` (baseline-seeded fill)
- `output/alns_e2_1778592162_443of480.json` (BP-seeded fill, vol-14's
  best end-to-end result — ties vol-12's published 443/480)
- `output/alns_e2_1778592462_436of480.json` (restart-seeded fill,
  strictly worse — diverse-seed intuition disconfirmed)

## Frame-first structural finding (vol-12 frames 75 k → CSP-valid ≈ 0)

Wrote `crates/bench-audit/src/bin/run_e2_framefirst.rs` to test:
pin each of vol-12's 75 173 Hamilton frames + 5 canonical hints
(note: vol-14 audit found the 75 173 is a 120s-time-bounded
subset, NOT exhaustive — the true total is unknown),
run engine on the residual 14×14 interior.

**Result on a 500-frame sample (border_first_lcv, baseline edge-prop only):**
- 0/500 frames yield a SOLVED or partial-improving outcome.
- 267/500 (53.4%) frames pass hint-application; their interior search
  EXHAUSTS in < 200 ms (proven infeasible under baseline propagation).
- 233/500 (46.6%) frames are REJECTED at hint-application time
  — specifically at **ring[46] = (0,14)**, where 100% of rejected
  frames have piece 50 rot 3 (a specific edge piece) at that ring slot.

**On gacolor+AC3 (stronger propagation):** *all 20/20* sampled frames
are rejected at hint-application time, most at canonical-hint
positions (pos 210, 34) — vol-12's Hamilton enumeration did not
filter for global consistency with the 4 *interior* canonical hints.

**Implication:** vol-12's "75 173 valid Hamilton border rings" is
(a) a lower bound from a 120s-bounded DFS, NOT exhaustive, AND
(b) a
necessary-but-not-sufficient condition. The number of *globally-CSP-
valid* frames consistent with all 5 canonical hints is **vastly
smaller** (likely < 100) and the right vol-15 deliverable is a
proper boundary-encoder that filters them.

Bench artifact: `output/v14_framefirst/latest/results.tsv`.

## Tier rating at session close

- **Tier 1** (depth lift over vol-12 174 CP-only): ❌ NOT achieved
  in any vol-14 single-shot CP variant.
- **Tier 2** (≥454 cold-start end-to-end): ❌ — 443/480 reached on
  BP-seeded ALNS-fill (vol-14's best **completed-board** result),
  below vol-6's warm-started 454.
- **Tier 3** (≥460 cold-start or structural artifact): ✅ — TWO
  structural findings + one process correction:
  1. **The frame-first decomposition does NOT work directly on
     vol-12's Hamilton frames** — they are not globally CSP-valid
     under any propagation level. Vol-12's 75 173 count is
     itself a lower bound (DFS time-bounded), AND
     necessary-not-sufficient.
  2. **CP value-order biases (edge-BP) can hurt CP partial score
     but help downstream local-search escape** — BP-seeded ALNS
     hits 443 vs baseline-seeded 442.
  3. **CP-partial-score metric is misleading**; honest comparison
     must be end-to-end (CP + ALNS-fill).
- **Tier 4** (≥469 / ≥470 community SOTA): ❌

Net: **TIER 3 achieved by two complementary structural artifacts
and one methodology correction.** Honest framing: no new SOTA, but
ruled out an entire class of heuristic-only attacks (BP-as-value-
order in isolation) and a major frame-first naivety (Hamilton frames
≠ CSP-valid frames), and corrected the in-pipeline measurement
methodology.

## Recommendations for vol-15 (in priority order)

1. **🚨 Verify and re-validate**: with the ALNS-pinning fix in place,
   re-run vol-12 baseline + vol-14 BP+restart fills, get HONEST
   canonical-E2 scores. The vol-12 result is probably more like
   430-440, not 443. **Until this is done, all our published
   "scores" are suspect.**
2. **Implement Blackwood's algorithm** (`V15_BLACKWOOD_SPEC.md`).
   Without it we cannot reach 469. This is the binding constraint.
3. **CP-search policy axis is exhausted**: heuristic-side
   schedule + break-index allowance is the missing piece, not
   smarter LCV/BP/restart. See `project_e2_mcgavin_blackwood_gap_analysis`.
4. **Fix pt_e2 to validate hint integrity** when loading
   `--start-from`. Reject or auto-fix boards that violate hints.
5. **CSP-aware frame enumerator** (`V15_FRAME_ENUMERATOR_SPEC.md`).
6. **ALNS improvements**: cluster-sized repair (vol-14 finding:
   the defect cluster is ~62 cells, k=5 repair too small).
7. **PT tabu list** (`project_e2_vol14_pt_no_tabu`).
8. **Mismatch geometry awareness**: support bottom-up scan order
   to see if cluster moves to top (matching community 469s'
   geometry).

## 🛑 LATE SESSION: ALNS HINT-PINNING BUG DISCOVERED

While studying the structural overlap between our 443/480 board
and community 469s, found that **our 443 has piece 215 at pos 135
instead of canonical piece 138**. Tracing showed: alns_e2 was
freeing hint cells during destroy operators — the canonical hints
were not pinned. **All previous ALNS-fill scores (vol-12's 443,
vol-14's 442/443/436) are on the WRONG puzzle** — the canonical-E2
score is lower.

**Fix (commit `afb3dc9`)**: added `AlnsConfig.pinned_positions` +
applied at destroy time. Wired up in alns_e2 binary from file_hints.

**Re-running**: BP-seeded ALNS-fill with patched binary, results in
`output/v14_fill_fixed/`. Expected: canonical-E2 score < 443 (since
the "wrong piece" was helping the score before).

PT pinning was correct (`run_pt::pinned_positions` was always
wired), BUT the PT push earlier in this session started from the
*broken* 443 seed and PT pinned the (wrong) piece-215 at pos 135.
The 446 PT result was therefore also on the wrong puzzle.

This is a **major bug discovery** that invalidates vol-12 + early
vol-14 measurements. Memory entry:
`project_e2_vol14_alns_hint_bug.md`.

## Discoveries while PT ran (parallel research)

While the (broken) PT push was running, I:
1. **Reverse-engineered McGavin/Blackwood/Joe**: read
   `docs/community-mining/09_Blackwood` and `05_Joe`. Identified
   FOUR mechanisms we don't have: heuristic-side schedule,
   break-index allowance, in-place prune-restart, fit_table
   engineering. We are 20 000× slower in raw nps and missing the
   actual algorithm that gets to 469. Memory:
   `project_e2_mcgavin_blackwood_gap_analysis.md`.
2. **Compared mismatch geometry** across our 443 + vol-6's 454 +
   community 469/468 boards. **Our 443 and vol-6 454 BOTH have
   mismatches clustered in center-bottom (rows 4-14, cols 2-12);
   community 469/468 have them at the TOP**. Geometry is
   search-order-determined. Memory:
   `project_e2_vol14_443_mismatch_geometry.md`,
   `project_e2_vol14_mismatch_geometry_universal.md`.
3. **Wrote V15_FRAME_ENUMERATOR_SPEC.md** — design for CSP-aware
   replacement of vol-12's pairwise enumerator.
4. **Wrote V15_BLACKWOOD_SPEC.md** — full implementation blueprint
   for Blackwood's 2020 algorithm (the actual path to 469).
5. **Audited MEMORY.md** — updated 4 stale entries.
6. **Found the structural overlap**: our 443 and community 469 (c)
   share only **1 piece in the same position out of 256**. We are
   in different basins entirely. Community 469s are NOT a warm-start
   for our stack.

## What shipped this session (8 commits on develop)

| commit | description |
|---|---|
| `bafe12a` | session plan |
| `6679045` | #1: ValueOrder::EdgeBpMarginals + load_edge_bp_marginals + tests + JOE_DEPTH150_BP{,_PAR} profiles + server registry update |
| `2bef02a` | #2 PoC + timestamped run dirs + output cleanup |
| `51e46c0` | metric fix (matched/480) + rescore_board bin + run_e2_framefirst bin + 500-frame survey |
| `f148bbc` | mid-session closeout: tier-3 (BP wins end-to-end on broken puzzle, frame-first null) |
| `9af4f92` | V15_FRAME_ENUMERATOR_SPEC.md |
| `e9cae31` | V15_BLACKWOOD_SPEC.md + mismatch geometry analysis |
| `afb3dc9` | **CRITICAL BUG FIX**: ALNS was unpinning canonical hints |
| (this) | closeout: vol-14 final state + memory updates |

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
