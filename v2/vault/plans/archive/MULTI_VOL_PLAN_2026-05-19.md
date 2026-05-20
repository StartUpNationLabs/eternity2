# Multi-Volume Research Plan — drafted 2026-05-19 18:00 CEST

**Context.** User away ~30 days. Vol-146 closed. 16 vols (V131–V146) since
the McGavin-pivot. Strong findings: scaling curve, 3-regime ALNS gap,
forbidden-patch theorem, 18 basin families ≥458, record **463** (within
McGavin (2,3,0,1)). Dead ends: short-budget local search on record-tier
boards is structurally inert (σ-cycle indecomposability dominates).

This plan covers Vols **147–158** as a coherent research arc, not a
laundry list. Each vol has a kill-criterion. Total budget: ~12 vols ×
~2 working days each = 3-4 wall-clock weeks (interleaved with compute).

## Strategic frame

Three classes of attack still have leverage:

- **(C) Compute campaigns**: longer-budget × wider-fan ALNS on the 15
  un-deep-explored basin families ≥458 (V129-T11 result). Proven recipe;
  V129-T12 found 463 this way.
- **(A) New algorithms**: INTAGLIO-pruned DFS, BP-guided destroy, FSMC
  memoization, PEPS-marginals (W1 cloud), LKH chain (W4 untested deeply).
- **(M) Math/structure**: stronger UBs (B3 per-border interior LP),
  freezing-structure characterization, σ-cycle algebra.

The plan **interleaves all three** — compute runs in background, algorithm
work foreground, math fills the gaps when builds are blocked.

## Hard rules

- One invention per vol (binding 2026-05-19).
- Vault session + concept page per vol.
- Variance reporting: ≥3 seeds, min/median/max.
- Timestamped output paths.
- 7 CPU cores max concurrent (1 free).
- Kill-criterion baked into each vol; no open-ended "keep trying".
- NO McGavin-anchored short-budget ALNS variants (V140/141/143/146 done).

## Vols 147–158

### Vol-147 — INTAGLIO-pruned DFS  *(algorithm A)*

**Idea.** Deterministic backtracking with post-placement check that
rejects any partial board containing a forbidden 2×2 or 2×3 patch.
Exploits V138-142's finding (99.72% of random 2×2 patches forbidden).

**Build.** Rust bin `crates/bench-audit/src/bin/v147_intaglio_dfs.rs`.
Reuse `solver-engine` or write a minimal backtracker. Forbidden-patch
table precomputed once (256³×4³ for 2×2 = ~256M entries; cacheable).

**Measure.** Nodes/sec, depth reached, max-matched at timeout, vs
`vanilla_fast` baseline at equal wallclock. 5×5 → 7×7 → canonical.

**Kill.** If at canonical scale the patch-check overhead > 2× the node
throughput loss in vanilla, refute as integration-loss. If patch-check
adds <2× overhead, run 4h × 4 seeds on canonical and report depth.

**Days budget.** 3.

### Vol-148 — Multi-basin compute campaign Tier-1A  *(compute C)*

**Idea.** V129-T12's recipe (18 × 30min ALNS basic seed=42) found 463.
**Scale up**: 18 basin families × {seed=1,7,42} × {basic, basic_lkh}
× 4h budget. Total ≈ 432 CPU-hr (~3 days wall on 7 cores).

**Build.** Sweep script `scripts/v148_basin_sweep.sh` that:
- Loads each of the 18 representative boards (V129-T11 corner-perm bucket
  representatives).
- For each (board, seed, ops): `alns_only` with `--alns-budget-ms
  14400000`.
- Logs to `output/vol-148/$(date)/run_<board>_s<seed>_<ops>.log`.

**Measure.** Per-(board, seed, ops): init score, final score, time to
each new-best. Aggregate: # basins where any seed/ops broke ≥460, ≥463.

**Kill.** Time-budget cap of 4 days wallclock. Any new ≥464 → record,
amend [[basins/basin-464]].

**Days budget.** 4 (mostly compute).

### Vol-149 — BP-guided destroy operator  *(algorithm A)*

**Idea.** W2 (vol-123) showed plain BP converges on canonical (3.6s, 13
iter, mean_max_prob=0.04). BP marginals were weak as **value-order**.
Untried: use marginals as **destroy target**. Destroy operator picks
cells whose ASSIGNED (piece,rot) has lowest BP marginal — these are the
"weak links" the LM thinks are likely wrong.

**Build.** New Rust destroy op `BpWeakDestroy` in `crates/localsearch/src/alns.rs`.
Loads precomputed BP marginals (`scripts/w2_sp/bp_confident.py` output).
Wrap as `--ops basic_bpdestroy`.

**Measure.** On 459-basin boards × 3 seeds × 30min: compare vs
`basic` baseline. Variance + median test (Wilcoxon).

**Kill.** If <+0.5 median improvement on 459 basin at equal budget,
refute as "marginals correlate with assignment too well to be useful as
destroy target". Pivot to ALNS as marginal **acceptor** instead (M-H
acceptance weighted by Δ-marginal).

**Days budget.** 2.

### Vol-150 — FSMC memoization in Rust  *(algorithm A)*

**Idea.** vol-122 J6 measured 17–94% subtree convergence rates on
3×3–7×7 puzzles. Port the Python PoC to Rust integrated with
`solver-engine`. Bloom-filter cache for state-key
(placed-piece bitset + frontier color signature).

**Build.** Rust bin `v150_fsmc_engine.rs` that wraps `EngineConfig` with
a memo layer. State-key hash → Bloom filter check → skip-subtree if hit.

**Measure.** On 6×6/8×8 generated: cache hit rate, nodes-saved
ratio, wall-time speedup vs vanilla. Scale to 12×12, then canonical.

**Kill.** If hit rate < 5% at 12×12 with 4 GB Bloom filter, refute as
"convergence collapses at scale". (Theoretical concern: state space
combinatorially explodes.) Pivot to bounded-depth memoization (only at
depth k ≤ 32).

**Days budget.** 3-4.

### Vol-151 — Hidden basins in 440-457 range  *(structural M)*

**Idea.** V129-T11 clustered the 18 basin families ≥458 by corner-perm.
The 440-457 range has hundreds of boards — likely contains additional
basin families not represented in the ≥458 set. **Cluster them**:
corner-perm × cell-diff distance. Find the densest 5 outliers.

**Build.** `scripts/v151_basin_clustering.py`. Load all `database-400-480`
boards with score ∈ [440, 457]. Compute:
- Corner-perm signature.
- Pairwise Hamming distance (placement[i] level).
- DBSCAN or hierarchical clustering on Hamming.

Pick 5 outlier basins (large min-distance to any ≥458 board).

**Measure.** On each of the 5: run V148-style sweep (4 seeds × 2h
ALNS basic). Did any **lift** through the 458 wall? If yes, that's a
"hidden ladder" — a basin family that ≥458 missed.

**Kill.** If none of the 5 lifts ≥458 within 2h, refute as
"low-score basins don't connect to high-score basins via local moves" —
which would itself be a publishable structural finding.

**Days budget.** 2.

### Vol-152 — Per-border interior LP-UB (B3 in backlog)  *(math M)*

**Idea.** A1 (vol-122) enumerated 50 piece-unique 60-matched borders.
For each, compute the LP-UB on the **interior 14×14 given that border
frozen**. Rank borders by UB. Surprising-rank borders → ALNS target.

**Build.** Adapt `border_lp_ub.rs` to take fixed border + run LP only on
interior 196 cells. Reuse vol-44 cell-pair LP machinery.

**Measure.** Distribution of per-border interior UBs across all 50.
Are some borders provably <420? Provably ≥468?

**Kill.** If all 50 borders yield interior LP-UB ≥ 460 (i.e., LP-UB
provides no discrimination), refute as "LP relaxation too loose at
border-frozen scale". Move on.

**Days budget.** 2.

### Vol-153 — Freezing structure of all 18 basins  *(math M)*

**Idea.** W7 (vol-123) measured 459-basin freezing: 1/256 cells truly
frozen, 76.6% with exactly 3 distinct piece-rotations. **Extend to all
18 basin families ≥458.** Aligns boards by corner-perm equivalence,
counts cell-level diversity per family.

**Build.** `scripts/v153_freezing_18_basins.py` extending W7. Per
basin family: representative + nearby ALNS-found variants. Cell-level
diversity histogram. Look for: (a) basins with high freezing → tight
local optima; (b) basins with low freezing → liquid → easier to escape.

**Measure.** Per-basin freezing fraction. Rank.

**Kill.** Always runs (pure analysis, no kill criterion needed).
Output: a vault concept page ranking the 18 basins by "looseness".

**Days budget.** 1.

### Vol-154 — Cluster MIP on 463 board halo-2  *(algorithm A)*

**Idea.** V129-T12's 463 board hasn't been MIP-locality-proven. Vol-44/55/58
proved 458 and McGavin 469 locally optimal at halo-1 and halo-2 cluster
MIPs. **Apply same to 463.** If 463 is halo-2 locally optimal, we have
proof it's an honest peak (not a near-trivial extension of the
(2,3,0,1) basin).

**Build.** Reuse `vol62_cluster_mip_bound` infrastructure. Run on the
463 board, halo-2 clusters.

**Measure.** Per-cluster Δ-improvement bound. If max-Δ over all
halo-2 clusters = 0, 463 is halo-2 locally optimal.

**Kill.** If MIP times out (>2h per cluster), drop to halo-1. Honest
local-optimality result either way.

**Days budget.** 2.

### Vol-155 — LKH-chain deep test  *(algorithm A)*

**Idea.** W4 (vol-123) implemented LKH chains as `basic_lkh` but only
tested on 459 basin × 4 seeds × 5min. **Deep test**: 18 basins × 4
seeds × 30min. Compare against `basic`.

**Build.** Already built. Just sweep.

**Measure.** Per-basin median Δ(basic_lkh vs basic). Identify basins
where LKH chains specifically help.

**Kill.** If median Δ across 18 basins ≤ +1.0, refute LKH as "general
booster" — but identify any specific basin where it helps.

**Days budget.** 1.

### Vol-156 — INTAGLIO-pruned DFS at canonical, longer compute  *(algorithm follow-on)*

**Idea.** Only runs if V147 passes its kill-criterion. **24h × 4 seeds
× canonical** with the patch-pruning DFS. Compare depth-reached and
max-matched against `vanilla_fast`.

**Kill.** 24h is the cap.

**Days budget.** 1 + 4 compute.

### Vol-157 — PEPS marginals at canonical (W1 cloud)  *(algorithm A)*

**Idea.** W1 (vol-123) Python PEPS solved 6×6 in 1s, 4×4 in 1s, but OOM at
canonical 16×16 on laptop (chi=32). Run on cloud if accessible (the
user has a 64-128 GB cloud option) — but **DO NOT** spend user money
without explicit approval.

**Build.** Estimate memory at chi=64 and chi=128. If chi=64 fits in 64GB
RAM, queue for user-approved cloud run. If not, document the memory
gap and defer.

**Kill.** No autonomous cloud spend. Write the memory analysis +
"ready to run" runbook; require user to launch.

**Days budget.** 0.5 (analysis only without user approval).

### Vol-158 — Plan close + synthesis  *(meta)*

**Idea.** Synthesize V147-V157 results. Update INVENTIONS_BACKLOG.md
with all status changes. Write a vault page "Vols 147-157 synthesis"
matching the V106-V115 synthesis style. Identify the 1-2 most
promising directions for vols 159+.

**Days budget.** 1.

## Calendar (rough)

| Vol | Days | Wall day | Type | Concurrent compute |
|-----|------|---------|------|--------|
| 147 | 3 | 1-3 | A | — |
| 148 | 4 | 4-7 | C | runs in bg vols 149-150 |
| 149 | 2 | 8-9 | A | 148 still running |
| 150 | 3-4 | 10-13 | A | |
| 151 | 2 | 14-15 | M | |
| 152 | 2 | 16-17 | M | |
| 153 | 1 | 18 | M | |
| 154 | 2 | 19-20 | A | |
| 155 | 1 | 21 | A | |
| 156 | 5 | 22-26 | A | (4d compute) |
| 157 | 0.5 | 27 | A | |
| 158 | 1 | 28 | meta | |
| buffer | 2 | 29-30 | — | |

Total ≈ 30 wall-days; matches the user's ~1-month autonomy window.

## Kill-the-plan criteria

This plan itself can be killed early if:

1. **A ≥464 board is found** before Vol-152. Pivot all remaining vols
   to deep-attacking that basin and the nearby ones.
2. **PEPS cloud becomes available** (user approves spend). Vol-157
   gets immediate priority.
3. **V147 INTAGLIO-DFS reaches an algorithmically dominant position**
   at canonical (e.g., depth >100 in <10min). Pivot to scale.
4. **Three consecutive vols (e.g., 151-153) all refute** without yielding
   new openings. Re-plan; consider a brute restart (V148-style but
   100× wider).

## What this plan deliberately does NOT do

- No new short-budget local-search tiebreakers (V140/141/143/146
  exhausted this).
- No more McGavin-anchored attempts.
- No `Δ-pre-estimation` of effort beyond "days budget" → "wall day".
- No reliance on user input. If a vol needs a decision the user hasn't
  pre-authorized (e.g., cloud spend), the vol does the prep work and
  parks at a clear handoff.

## Linked

- [[STRATEGIC_REVIEW_2026-05-19]]
- [[MONTH_AHEAD_2026-05-19]]
- [[INVENTIONS_BACKLOG]]
- [[vol-146-close]]
- [[forbidden-patch-theorem-2026-05-19]]
