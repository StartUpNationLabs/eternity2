# Session prompt — Vol-219 — THE LABEL ECONOMY

You are a senior researcher attacking **Eternity II** (canonical
5-clue, Selby-Riordan) in this repo. **You have unlimited time and
resources for this session. Aim big. Multi-day builds and overnight
sweeps are in scope. No limiting thoughts.** Goal unchanged:
strict-canonical record ≥461 (5/5 hints MANDATORY); user target:
**<10 errors (471+, beats SOTA)**; standing directive: INNOVATION
toward 480 — records are the measuring stick, not the destination.

## USER DIRECTIVES (binding, standing — violating these wastes the session)

1. **NO witness-frame material anywhere.** Corpus boards =
   break-anatomy reconnaissance ONLY.
2. **Full-board frame-free construction only.** The border EMERGES
   from search. Never fix a ring up front.
3. **NO 8×8 full-solution enumeration. Never re-propose it.**
4. 8 cores max TOTAL; 5/5 hints in everything.

## THE STATE YOU INHERIT (vol-218, one day, user present)

Vol-218 SETTLED the instrument question with pre-registered rigor at
10×10 ([[bandsaw-band-split-exact]], [[relaxation-gap-curve]],
session [[vol-218]] — every gate answered same-day, zero wrong
answers anywhere):

- ★★ **THE STRATEGIC CONCLUSION (build everything on this): the
  exactness wall is two-sided, and only MEASUREMENT crosses it.**
  (a) Relaxed counts are FICTION at band depth ≥2 (×7 overcount at
  one row, ×10⁴ at two, 100% phantom-feasible at three) — floors
  are passage LBs, never finishability certificates, and
  floor-ranked selection ≈ RANDOM (M4: 6/8). (b) Exact
  certification crawls ×20 per break of budget from below
  (decidability horizon b\*≈6-7 at 10×10; real-board bracket
  [11, 52]). (c) Measured greedy labels are the ONLY instrument
  touching the achievable region: label-ranked cohorts finish
  **3-8 breaks better, 8/8 instances** (M4 P4.1). Stop seeking
  cheap certificates; build the measurement economy.
- ★ **MITM COMPLETION PROBE discovery** (M4, logged as
  `mitm-completion-probe`): where BANDSAW's join fires (2% of blind
  10×10 entries) its completions beat the greedy label by **median
  12 breaks (7-17, 17/17 head-to-heads)** — globally-coordinated
  halves the greedy commitment ordering never reaches; join-fires is
  itself an elite-entry signal. 16×16 fire rate = unmeasured.
- **Deployed and validated on the REAL board same-day**: tropical
  suffix tables (exact floors: 38 ms k=3, 1.7 s k=4; ≡ fb_oracle ≡
  counting profile), suffix-pruned ID-B&B (2.2× after the allocator
  fix; slack ceilings explode — always ID +1 from the floor),
  certified-LB ladder (+2 median over floors at 10×10; +1 on real
  entries at cheap budgets), **v2 labeler** (column-major+suffix,
  median −1 vs stage4_finish at 1.5 s; 60W/10T/31L, more DNFs —
  not uniform), **fb-suffix-incremental** (1.83 ms what-if floor
  per candidate at k=3 — the vol-217 row-11 steering ask, built and
  validated; 65 ms at k=4 = re-ranking tier).
- **437/480 ×2 from scratch** (5/5 hints, emergent border,
  independently rescored) — frame-free track best (431→436→437);
  both plateau at 43 breaks under 120 s B&B
  (`output/vol-218/best_finish_20260612T151541/`).
- **MIRROR: honest null** at registered compute (flat ±1 vs the ±8
  bar, both compute points; control owns the deep tail). Not
  globally refuted (one compute scale); do not re-run without a
  fundamentally different descent engine or ≥100× compute/top.
- **Fugacity correction: two-regime verdict on ground truth** —
  recovers 86-98% of the gap at b\* 2-4, decays to 43-53% at 5-6,
  and is PROVABLY first-moment-blind to exchange-symmetric
  overcounting. 16×16 S1 deferred on measured grounds; the adjoint
  (forward-backward usages) is the only route to testing it at
  NC=23.
- Data on disk: 8×200 10×10 entry banks + full M1-M4 grids
  (`output/vol-218/m_run_20260612T140054/`), 400 relabeled 16×16
  entries (`output/vol-218/e2_relabel_20260612T143904/`), MIRROR
  race (`mirror_race2_*`), fugacity ladder (`fugladder_*`).

## Vol-219 binding plan (formalize CURRENT-VOL-219-DRAFT.md at open)

1. **LABEL FACTORY v2 AT SCALE + THE FIRST LEARNED RANKER.**
   Overnight labeling on the real 16×16 across tiers (stage-2 exits,
   stage-3 entries) and generation recipes — the 2.2× B&B + v2
   labeler make ~50k-200k labels/night feasible on 8 cores. Then
   train the first ranker on measured (state, label) pairs
   (features: frontier color histograms, pool composition, suffix
   floors k=3/k=4, bottom-chain profile, LB certificates — all
   cheap). PRE-REGISTER the validation BEFORE training: the M4
   cohort-completion protocol transplanted to the real board —
   ranker-top-K (ranked WITHOUT labels) vs label-top-K vs
   floor-top-K vs random-K, all cohorts labeled at a deeper budget;
   bars set at prereg time after a sizing smoke. The ranker's win
   condition is generalization: ranking UNLABELED states at
   microseconds each.
2. **MITM COMPLETION PROBE AT 16×16** (`mitm-completion-probe`).
   Budget-capped join probes on (a) the 400 relabeled entries,
   (b) the label factory's elite tier. Measure the join-fire rate
   vs budget; harvest completions where it fires (10×10 precedent:
   −12 breaks vs greedy). PRE-REGISTER fire-rate reporting + the
   comparison protocol. Concrete target: beat 437 on the frame-free
   track; stretch: the <10-error shape needs entries whose pools
   cohere — join-fires IS that detector.
3. **STEERED STAGE-3 GENERATION** (fb-suffix-incremental, built).
   Wire the 1.83 ms k=3 what-if asks into stage-3 exit construction
   (row-11-analog steering: choose commits that preserve frontier
   floors — the vol-217 row-11 decision point, finally actionable).
   A/B steered vs blind populations on label distributions at
   matched generation compute; prereg the bar after a sizing smoke.

Alternates if bindings close early: fugacity adjoint
(forward-backward usage marginals — unlocks the deferred 16×16 S1);
NEON min-plus vectorization + compact cost-0 index (QUIET-machine
benches only — the full (tn,tw) index L2-thrashes on M1, measured);
12×12 scaling point (M5 leftover); samply + line-tables-only setup
for named-frame profiles.

## Hard-won lessons (vol-218 additions — do not re-learn)

- Generated puzzles have SHUFFLED pieces: index rotation tables by
  `p.id`, never by `pieces()` iteration order (M0 caught 30 phantom
  breaks).
- Naive row-major walkers stall at clue cells for seconds (the d34
  wall): pre-filter the N/W neighbor cells of every forced cell to
  clue-compatible candidates (zero completeness loss).
- Slack-ceiling B&B explodes (600 s+ DNF on near-canonical
  entries): ALWAYS iterative-deepen the break ceiling +1 from an
  admissible floor. Suffix tables make each rung's proof tree tight.
- Node-capped runs are binary-speed-invariant (same data, faster);
  time-capped runs are not — never mix binaries within a phase, and
  prebuild band-level structures (suffix, cost index) OUTSIDE timed
  label budgets.
- Per-node allocations dominate before algorithms do: profile FIRST
  (malloc was half of all samples), and beware locality — the
  "obviously better" precomputed index lost 1.86× to L2-thrash on
  M1 (128 B lines, small L2). Measure on a QUIET machine; nice'd
  processes land on E-cores and corrupt A/Bs.
- zsh `$(jobs)` is subshell-blind (the race oversubscribed 280-wide);
  throttle with `xargs -P` + a worker script (BSD xargs -I has a
  tiny replsize — no inline scripts).
- Greedy labels are anytime-order-sensitive: keep candidate
  iteration order IDENTICAL across labeler versions or labels stop
  being comparable.
- Pre-register every gate; report letter AND substance; honest
  negatives same-day; mid-vol discoveries get BACKLOG entries, not
  pivots (the MITM probe discovery followed this rule).

## Toolchain quick map (all tested, committed on develop)

- `crates/bench-audit/src/mini.rs` — the band machinery (selftested
  M0): `Mini::{from_seed,from_puzzle}`, `Band`, `endgame_band`,
  `tropical_suffix`/`tropical_prefix`/`whatif_floor`
  (fb-suffix-incremental), `bb_min_break` (scan core; `_idx`
  experimental), `bandsaw` (LB/UB semantics), `exact_count`,
  `relax_profile`/`weighted_profile`, `fugacity_corrected_lncount`,
  `build_cost_index`.
- `mini_e2` — real-16×16 per-entry driver: floors, 1.5 s v2 labels,
  LB ladder, `--save-best` (rescored full boards), `--whatif-bench`,
  `--k`. `mini_gen`/`mini_lab` — 10×10 testbed (m1/m23/m4/m2ladder).
  `mirror_gen` — broken-top generator. `fugacity_lab` — saddle
  validation (ladder mode).
- vanilla_fast (207M pp/s, `--init-board/--init-rows`, hint-piece
  protection), stage4_finish (v1 labeler, superseded), fb_oracle
  (k=3 tropical/counting; k=4 unsupported — use mini machinery).
- `scripts/v218_mirror/{race.sh,race_one.sh,full_grid.sh,
  m3_analysis.py,m4_analysis.py}`; `scripts/v217_crossing/*`.
- Records tooling: `rescore_board` before ANY claim;
  `attribution_url.py` for break anatomy.

## Discipline

Audit-at-open per CLAUDE.md (BACKLOG sweep — vol-216 cohort now ages
to 3 vols: DECISIONS REQUIRED on sinkhorn-lp-surrogate,
sa2-tail-bound, fast-probe-generator, strip-oracle-sat,
transfer-profile-features, actuary-rate-tensor-completion;
formalize CURRENT-VOL from the 219 draft, ≤3 bindings). One named
invention per vol. Research notes AS YOU GO (vol-218 standard: ~28
commits, every finding in the vault same-hour). ≥8 seeds
min/med/max. The 480 perspective governs: local oracles DEAD (now
with measured proof), the wall is two-sided, and the live route is
LEARNING FROM REALITY AT SCALE — vol-219's job is to industrialize
it: labels by the hundred-thousand, a ranker that generalizes,
probes that harvest the elite tail.

## Read first

1. `vault/plans/CURRENT-VOL-219-DRAFT.md` (formalize at open)
2. `vault/sessions/vol-218.md` (the full day: all verdicts + numbers)
3. `vault/concepts/bandsaw-band-split-exact.md` +
   `vault/concepts/relaxation-gap-curve.md` (the settled science)
4. `vault/plans/BACKLOG.md` — `mitm-completion-probe`,
   `greedy-finish-label-factory`, `fb-suffix-incremental` (built),
   vol-216 cohort (aged 3 — decisions due)
5. Memory: `project_e2_vol218_bandsaw_2026_06_12`,
   `project_e2_480_perspective_2026_06_11`,
   `feedback_e2_no_8x8_enumeration`
