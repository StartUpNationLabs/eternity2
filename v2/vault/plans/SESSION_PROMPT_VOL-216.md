# Session prompt — Vol-216 (written at the vols-213-215 close, 2026-06-12)

You are a senior researcher attacking **Eternity II** (canonical 5-clue,
Selby-Riordan) in this repo. Vols 213-215 closed in one ~38 h session
(synthesis: `vault/SYNTHESIS_VOLS_213-215_2026-06-11.md` — READ IT
FIRST). **Goal unchanged: strict-canonical record ≥461 (5/5 hints
MANDATORY). Standing directive: INNOVATION toward 480 — records are the
measuring stick, not the destination.**

## Verified state (do NOT re-derive)

- **Unguided strict high: 452** (LADDER prefix d146-seed63 + 1 h; II 339
  + IB 53), and it is BOUNDED: basin flat at 6 h (451×8), no second
  escape prefix in ~1900 probes across 3 frames. 3416 banked prefixes.
- **Both community strict-460s reconstructed exactly** (REPLAY + mcb2 +
  et-cap); their 1-deviation neighborhoods are EMPTY across [60:182).
  They contain 4-5 DOUBLE-BREAK cells (why violate-≤1 engines never
  reached them). All-time original-board strict record: 458 (vol-122).
- **The 444-450 unguided band is universal** (55+ frames incl.
  generated); framegen makes hint-compatible frames at 73% yield —
  frame identity is CLOSED as a question.
- **Triple-null**: prefix quality is invisible to aggregate stats
  (LEDGER deficit ≡ 0 on perfect prefixes), neighborhoods (10% overlap),
  and local dynamics (FITSTAT curves identical). It is an emergent
  GLOBAL property; only ≥300 s empirical finals read it.
- **The 480 perspective (user-saved, memory
  `project_e2_480_perspective`)**: records = search × multiplier-stack ×
  exact-region. DEAD: local oracles. UNBOUGHT: multipliers. UNEXPLORED:
  growing proofs. Start there.
- MIDDEN (damage-geometry, vol-215 invention): mechanics solved
  (dispersed lattices move the perfect wall 153→174; graded-density
  rule), completion ECONOMICS open.

## Toolchain (crate `eternity2-cloister`, 28 tests green)

`cloister2` flags: `--prior-over-cost --max-cell-breaks --et-cap`
(loud cap-hit) `--replay-perturb --ledger --cairn --abort-below
--save-prefix --init-prefix file:K --quota D:M:frac --break-cells
rows:|cols:|cells: --schedule-from-choke tsv,B,floor
--schedule-from-board --scan row|boustro|seam:N|spiral` + FITSTAT/choke
TSVs auto-emitted. Harnesses: `scripts/v214_ladder/` (ladder.sh
FRAME/seed0-parametrized, ladder_rank2.py), `scripts/v213_replay/`.
Instruments: E2_TRACE, E2_LEDGER_CHECK.

## The plan (pick ≤3 binding at audit-at-open; one named invention)

1. **Verhaard markov optimizer** (the most-credentialed unbought
   multiplier — his records used it): per-depth fit/half-fit model
   (FITSTAT data exists in every run dir) → DP over (depth, slips) →
   search thousands of (order, gate-schedule) candidates offline →
   run the computed-optimal config vs the hand recipes, ≥8 seeds.
2. **Global prefix scoring** — the lens the triple-null never tested:
   assignment-LP with edge terms over the remaining pool (HiGHS,
   ~ms/prefix). Validate against the 35+ prefixes with measured
   finishes (the 451-producer must rank above its 446-twins or the
   approach is dead in one afternoon). If it ranks them: LADDER
   promotion uses it; if not: log the quadruple-null and move on.
3. **Grow the exact region** (the only practical-complexity lever, per
   the 480 perspective): et28-class exact endgame — last TWO rows as
   one B&B with stronger admissible bounds (assignment-LP bound per
   node?), MIDDEN-confined exact regions. Even et14 → et20 shrinks the
   lottery by ~6 branching decades.

Standing alternates: learned prefix ranking (3416 banked, 30 s labels,
vol-26/27 GNN precedent 540×); MIDDEN temporal×spatial gating; k=2
witness deviations; PREFIX-VAULT consolidation.

## Hard-won lessons (do not re-learn)

- Hinted gate schedules must start ≤120 (wall = 139) or be
  choke-derived; the `--breaks` default spread (154+) is unhinted-only.
- Finals need ≥300 s to read prefix quality; pins at depth−15 with
  TIGHT 12-14 breaks (22-break spans flood to 442 — vol-212 economics).
- Frame JSONs are FULL boards — filter ring positions (pos//16 or
  pos%16 ∈ {0,15}) in any analysis script (the ring-pollution bug).
- Never chain background runs via pgrep-on-script-name (mutual
  deadlock); compose sequentially in ONE command; `pgrep -x cloister2`
  is safe.
- A silently-capped "exact" method is greedy in disguise — caps must
  warn (TAIL_CAP lesson; pre-registered predictions catch such bugs).
- 8 cores max TOTAL; UTC dir tags; ≥8 seeds min/med/max; verify +
  independently rescore every ≥451 before any claim.

## Read first

1. `vault/SYNTHESIS_VOLS_213-215_2026-06-11.md`
2. `vault/plans/CURRENT-VOL.md` (vol-216 draft — formalize at open)
3. `vault/concepts/ladder-prefix-racing.md`,
   `vault/concepts/midden-damage-geometry.md`,
   `vault/concepts/replay-prior-over-cost.md`
4. Memory: `project_e2_480_perspective_2026_06_11`,
   `project_e2_vol214_ladder_2026_06_11`
