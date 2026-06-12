# SESSION PROMPT — VOL-218 — rigor at 10×10: the band-split program

You are a senior researcher attacking **Eternity II** (canonical
5-clue, Selby-Riordan) in this repo. **You have unlimited time and
resources for this session — the user said so explicitly. Aim big.
Multi-day builds and overnight sweeps are in scope. No limiting
thoughts.** Goal unchanged: strict-canonical record ≥461 (5/5 hints
MANDATORY); user target: **<10 errors (471+, beats SOTA)**; standing
directive: INNOVATION toward 480 — records are the measuring stick,
not the destination.

## USER DIRECTIVES (binding, standing — violating these wastes the session)

1. **NO witness-frame material anywhere.** The 460 witness boards and
   every banked witness-frame prefix are dead as material ("we DO NOT
   CARE about those old boards"). Corpus boards = break-anatomy
   reconnaissance ONLY.
2. **Full-board frame-free construction only.** The border EMERGES
   from search (top edge in stage 1, flanks per band, bottom edge
   last). Never fix a ring up front.
3. **NO 8×8 full-solution enumeration. Never re-propose it.** The
   10×10 program below is SUB-PROBLEM rigor (band enumerations,
   endgame joins, instrument comparisons) — not full enumeration.
4. 8 cores max TOTAL; 5/5 hints in everything.

## THE STATE YOU INHERIT (vol-217, one day, user present)

The frame-free staged full-board pipeline EXISTS end-to-end
([[staged-fullboard-construction]] has every number):

- **Best from-scratch finish: 436/480** (5/5 hints, emergent border,
  `output/vol-217/s4_finish_*/best_f6_open.json`).
- ★ PROVEN: the stage-2 rows-8-10 tropical floor is a CAUSAL
  passage filter — every floor≥1 state dies at d135 = the center
  clue; zero overlap, generator-history controlled. Floor-0 rate 16%.
- ★ REFUTED: relaxed floors as FINISHABILITY certificates —
  **relaxation gap 38-45 breaks** (entry floors 6-9 → measured
  finishes 44-52, n=149 greedy labels: min 44 / med 52).
  Repeats-allowed counting cannot see the distinctness wall. Never
  select endgame entries by relaxed floors.
- ★ Pinned-prefix subtrees are EXHAUSTIBLE IN SECONDS (1 thread) —
  compute never binds blind stage-3; the states bind. Equivalently:
  the vertical-coupling collapse (2.1e15 one-row chains → ~1e3 after
  ONE row of coupling) means CONDITIONED band sub-problems are
  enumerably small. This is the foundation of the vol-218 program.
- ★ SOTA ANATOMY (reconnaissance): McGavin 469 = 11 breaks ALL in
  rows 0-4; Blackwood 470 ×2 = 10 breaks ALL rows 1-4; crossing and
  band ZERO. SOTA = perfect ~12-row block + ≤11-break 4-row band,
  band built FIRST in their construction order.
- NEW CAPABILITY: **greedy-finish labels** — measured,
  distinctness-aware finish cost in 1.5 s via stage4_finish (was
  300 s/label). 149 labeled entries on disk
  (`output/vol-217/stage3_bank_*/greedy_labels.jsonl` + census12
  lists).
- Witnesses A/B are SIBLINGS (172/176 shared cells rows 0-10):
  treat "two community 460s" as ~ONE independent datum.

## Vol-218 binding plan (CURRENT-VOL.md is the formal copy)

**Open with binding 2 — the user's explicit final steer.**

1. **MIRROR gate** (days-scale, pre-registered, run as the parallel
   experiment): stage-1 rows 0-3 with ~8-12 DELIBERATE breaks
   (placement informed by MIDDEN damage geometry + the 469/470 break
   maps; keep row-2 clues obeyed) → demand perfect rows 4-15
   (`vanilla_fast --init-board --init-rows 4`). Mechanism: b1≈20 per
   break ⇒ ~10¹³× conditional-subtree inflation. PRE-REGISTER
   broken-tops vs perfect-tops penetration at matched compute;
   honest null same-day if flat.
2. **BAND-SPLIT EXACT SOLVE, validated RIGOROUSLY at 10×10 first**
   (USER-DIRECTED: "take that problem on smaller scale and be very
   rigorous"). Instances: `build_puzzle(10, 8, seed)` (bench-audit
   lib; vol-35 convention — 8 colors ≈ E2's edges-per-color
   density), 5 hints placed analogously, **≥8 instance seeds,
   distributions not points**. PRE-REGISTER M1-M5 BEFORE measuring:
   - M1: distinct-piece band-enumeration sizes vs repeats-allowed
     counts on REAL frontiers — the relaxation-gap curve by depth
     and pool size.
   - M2 (correctness gate): last-4-rows exact min-break via
     band-split meet-in-the-middle ≡ exhaustive B&B ground truth,
     EXACT match, every entry, all instances. 16×16 deployment is
     GATED on M2.
   - M3: join sizes, interface-grouping compression, wall-clock vs
     B&B — the scaling law.
   - M4 (strategic): rank entry cohorts by relaxed floor vs greedy
     label vs EXACT min-break; complete all cohorts; achieved-total
     per instrument = each instrument's value in breaks.
   - M5 (stretch): breaks-early vs breaks-late geometry at 10×10;
     12×12 scaling point.
   TRANSFERS: machinery correctness, scaling laws, instrument
   ORDERING. DOES NOT TRANSFER: absolute constants (vol-35 lesson —
   size governs landscape). Say so in every writeup.
   LIGHTHOUSE caveat (vol-184): bidirectional MERGE of heuristic
   populations was refuted; the band-split join differs by EXACT
   complementary-pool accounting — treat the precedent as a hazard
   list, measure join sizes first.
   Side gate (same-day, data on disk): [[fugacity-corrected-counts]]
   estimates vs the 149 measured 16×16 labels — pre-register a ρ bar.
3. **LABEL FACTORY at scale + learned ranker**: parallel greedy
   labeling across entry tiers and generation recipes; train the
   first ranker on measured cost. Composes with binding 2
   (certificates calibrate the labels).

Alternates if bindings close early: finisher v2 (exact bottom-row
DP memoized on the 20-bit edge key, late-release gates, parallel
B&B); fb-floor-attribution; fb-suffix-incremental.

## Hard-won lessons (vol-217 additions — do not re-learn)

- Pre-register every gate; report letter AND substance (the
  penetration prereg metric was underpowered; max_depth carried it).
- Relaxed/local instruments: passage YES, finishability NO. The
  distinctness wall eats every relaxation (LEDGER, bigram, floors).
- User probing questions = data (rule 12 drove 3 of vol-217's
  findings: BL-hint poisoning, the frame challenge, the full-board
  clarification).
- Engine traps fixed/known: hint pieces must be bucket-EXCLUDED when
  pinning (94% silent non-strict states before the fix); pool-order
  candidate scans never complete (cost-order them); never chain
  background runs via pgrep-on-name (wait on log markers); output/
  is gitignored — the vault carries the numbers.
- Tropical min-plus exclusion needs exact per-(q,w0) row-min tables
  (a greedy top-k skyline is provably inexact).
- ≥8 seeds min/med/max; verify+rescore notable finishes
  (attribution.py recount); UTC tags from `date -u`, never
  self-estimated; capped runs must report cap-hit; honest negatives
  same-day.

## Toolchain quick map (all tested, committed on develop)

- `crates/bench-audit/src/bin/fb_oracle.rs` — full-board N-row band
  oracle: counting (soft, 0.3 s) + `--floor-only` tropical (50 ms),
  `--bottom-chain`, batch+rayon. Python reference (exact selftests):
  `scripts/v217_crossing/fb_oracle.py`.
- `vanilla_fast` — 207M pp/s full-board generator; `--pin-hints`
  (clue pieces protected), `--init-board F --init-rows R` (pin a
  stage state), on-visit snapshots.
- `crates/bench-audit/src/bin/stage4_finish.rs` — B&B min-break
  endgame finisher + 1.5 s greedy labels (`--max-breaks 64
  --budget-ms 1500`).
- `scripts/v217_crossing/` — census_driver (H7 dedup), run_census2
  (two-pass census), stage3_bank, run_stage4_census, pick_strata,
  attribution(_url).py (break anatomy), bucas_url.py.
- Small puzzles: `eternity2_bench_audit::build_puzzle(size, colors,
  seed)` + `solved_board` (10×10/8c precedent: vol-35).
- Data: `output/vol-217/stage2_gen_clean_*/` (23,774 stage-2 states
  + floors), `stage3_bank_*/` (149 entries + greedy labels + census12),
  `s4_finish_*/best_f6_open.json` (the 436).

## Discipline

Audit-at-open per CLAUDE.md (BACKLOG sweep — vol-216 cohort ages to
2 vols; formalize CURRENT-VOL.md, ≤3 bindings). One named invention
per vol. Research notes AS YOU GO (vol-217 standard: ~30 commits,
every finding in the vault same-hour). Honest negatives same-day.
The 480 perspective governs: local oracles DEAD, multipliers bought,
the missing capability is an instrument that sees DISTINCTNESS —
vol-218's job is to build it on ground that can't lie (exact
sub-problem enumeration), then aim it at the real board.

## Read first

1. `vault/plans/CURRENT-VOL.md` (formalize at open)
2. `vault/concepts/staged-fullboard-construction.md` (pipeline + all
   vol-217 numbers)
3. `vault/concepts/crossing-oracle.md` (incl. scope refutation)
4. `vault/plans/BACKLOG.md` — `band-split-exact-solve` (binding 2
   spec), `sota-mirrored-stage1`, `greedy-finish-label-factory`
5. `vault/sessions/vol-217.md` (the full day incl. the user's
   step-back review)
6. Memory: `project_e2_vol217_staged_fullboard_2026_06_12`,
   `project_e2_480_perspective_2026_06_11`,
   `feedback_e2_no_8x8_enumeration`
