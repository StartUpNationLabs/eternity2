# Research notes — vol. 2

Continuation of `RESEARCH_NOTES.md`. Vol. 1 ends with the 2026-05-11 SESSION CLOSE summary, which is the right place to read first for context.

## Starting state (2026-05-11)

- Best on official Eternity II: **449/480 (93.5%)** matched edges, in ~3 minutes (30s CP + greedy_fill + 180s PT).
- Community SOTA: **470/480 (97.9%) — Joshua Blackwood** (libblackwood). Verhaard 2008 = 467/480.
- The 446-449 plateau is structural; pure local-search saturates here regardless of move set.

## Methodology rule (carried over from vol. 1)

Every experiment writes one section here with:
- **H** — hypothesis in one sentence.
- **Setup** — corpus, runs/cell, profiles compared.
- **Result** — JSON path + headline numbers (median ms, nodes, backtracks).
- **Verdict** — kept / dropped / iterated, with one-line reason.

Negative results count. Numbers from the same corpus under the same budget are required for "successful".

---

## Mindset for this volume

- Take time. Long-horizon research is expected.
- Reformulate. If a problem feels stuck, ask: which other field has solved a structurally-equivalent problem? Math ↔ geometry ↔ graph ↔ physics ↔ logic ↔ algebra. Translation often unlocks the move that's invisible from inside the original framing.
- Cheap experiments first. 30-line diagnostics can falsify expensive hypotheses.
- Trust strong negative results — when N variants of approach X all hit the same number, that's a theorem, not noise. Change approach class, not parameters.

---

---

## 2026-05-11 — Cross-field literature scan (research agent dive)

**H** — There is a field-translation of E2 that we haven't tried and that
contains a known method for our specific plateau problem.

**Setup** — Time-boxed (~30 min) literature search across 8 candidate
angles: survey propagation, edge-first dual, tropical geometry,
topological invariants of color flows, quantum annealing / Ising
mapping, replica-symmetry-breaking, neural-guided search, plus
catch-all. For each: prior E2 work, closest structural analog,
cheap diagnostic, P(beats 449).

**Result** — Two angles are no longer speculative; they have
named-after-E2 prior art.

1. **RSB / spin-glass framing (Angle 6) — ★ highest EV.**
   - Hamze, Jacob, Katzgraber (Phys Rev E 97, 043303, 2018):
     "From near to eternity: Spin-glass planting, tiling puzzles,
     and constraint-satisfaction problems." Constructs spin-glass
     Hamiltonians via tiling decompositions; tile puzzles are
     literally a planted-instance spin-glass class.
     https://arxiv.org/abs/1711.04083
   - Follow-up: 1907.10809 "Computational hardness of spin-glass
     problems with tile-planted solutions."
   - Yucesoy-Machta-Katzgraber (PRE 87, 012104, 2013): PT plateau
     correlates with free-energy landscape roughness — predicts
     our exact symptom. https://arxiv.org/abs/1210.6290
   - **Cheap diagnostic (≤ day-1):** dump N≥200 independent
     plateau states from PT runs, compute pairwise overlap
     distribution P(q). If P(q) is broad and multi-modal with
     ultrametric structure → 1-RSB or full-RSB landscape → PT
     plateaus *provably*; Houdayer cluster moves (Houdayer 2001)
     are the named cure. Never tried on E2.

2. **Topological / color-strand invariants (Angle 4).**
   - No direct E2 work, but each of 22 colors forms a chain across
     the board; total count fixed. Classical analog: Thurston
     height functions on domino tilings — gave previously
     intractable tileability decisions.
   - **Cheap diagnostic (≤ day-1):** compute per-color signed
     row/column crossings on each plateau state. If invariants
     are conserved across our 449s but differ between 449s and
     known higher solutions, we have a *global obstruction* that
     local moves preserve. That would explain why every cluster /
     swap variant we tried hits 449.

3. **Edge-first dual (Angle 3) — already explored.**
   - Ansótegui-Béjar-Fernández-Gomes-Mateu (2008): "Edge Matching
     Puzzles as Hard SAT/CSP Benchmarks" — uses the exact dual
     variables=edges encoding with channeling constraint PD6.
     Demote from candidate list.

4. **Survey Propagation (Angle 1) — interesting but riskier.**
   - No prior E2 work; BP on the cell-variable factor graph would
     be the right preflight. Day-1 cost moderate. Hold as
     fallback after RSB diagnostic.

5. **Other notable finds.**
   - **Blackwood holds 470/480** (corrected — user confirmed),
     not Verhaard's 467. libblackwood repo:
     https://github.com/jfbucas/libblackwood — code-read candidate.
   - **Houdayer cluster move** specifically designed to break 1-RSB
     plateaus where PT fails: pairs replicas, identifies clusters
     where they disagree, flips them coherently. Not in our move
     list.
   - **Population annealing** beats PT on rough landscapes; cheap
     to bolt on.
   - **Kovalsky-Glasner-Basri (2014):** convex relaxation for
     edge-matching — not yet read.
     https://arxiv.org/abs/1409.5957

**Verdict** — Plan: run the two day-1 diagnostics in parallel
(both cheap). They are non-overlapping: RSB tests the *dynamics*
hypothesis, topological tests the *kinematic obstruction*
hypothesis. One or both should give signal.

If RSB diagnostic confirms multi-modal P(q): implement Houdayer
cluster moves (~100 LOC on top of PT) as next experiment.

If topological diagnostic shows an invariant: design color-strand
surgery moves that change it deliberately.

Both negative would be informative: rules out two major
theoretical framings of the plateau.

---

## End-of-run reporting infrastructure (added 2026-05-11)

Every `pt_e2 / official_e2 / directed_e2 / rtcp` run now writes
two files under `v2/output/`:

- `<bin>_<timestamp>_<matched>of<total>.json` — full stats
  (score, timings, replica scores, swap rates, knobs used).
- `<bin>_<timestamp>_<matched>of<total>.url.txt` — clickable
  e2.bucas.name URL of the final board.

Both files have the score baked into the filename so plateau
states are easy to spot from `ls`. The Bucas URL is also echoed
to stderr at end-of-run.

`output/` is gitignored. Reporting code lives in
`crates/benchmark/src/report.rs`.

This unblocks the RSB diagnostic: we can now harvest plateau
states programmatically by running pt_e2 with N seeds and
collecting the resulting board JSONs.

---

## 2026-05-11 — RSB & topology diagnostic infrastructure

**H** — At least one of (a) plateau states cluster in configuration
space with ultrametric structure → 1-RSB landscape, or (b) plateau
states share an exact color-flow signature → global topological
obstruction. Either explanation tells us what move set to design
next. Both being false would also be informative (rules out two
named theoretical framings).

**Setup** — Three new tools under `crates/benchmark/src/bin/`:

- `harvest_plateau` — runs CP→PT pipeline N times with distinct
  seeds (CP partial reused across samples by default since CP is
  deterministic); dumps each final board to
  `output/plateau/<run_name>/sample_<idx>_seed_<hex>_score_<n>.json`.
  Lightweight format: width, height, seed, score, total_edges,
  cells = list of [piece_id, rotation] or null.

- `analyze_overlap` — reads dumps, computes two pairwise overlap
  metrics: `q_piece` (piece-id agreement, ignoring rotation) and
  `q_oriented` (piece+rotation agreement). For N samples we get
  N(N-1)/2 pair values. Reports mean/std/percentiles + 12-bin
  histogram for each metric. Writes `_overlap.json` summary.

- `analyze_topology` — for each plateau state, computes per-color
  matched-edge counts and per-row / per-col histograms. Reports
  how many (color, row|col) cells are *invariant* across all
  plateau states. Writes `_topology.json` summary.

**Run in progress (2026-05-11):** `rsb_n20_pt90` —
20 samples × (30s CP shared + 90s PT × 8 replicas) ≈ 30 min wall.
CP partial score: 293/480 (61.0%). PT temp range [0.05, 2.0].
Each sample harvested independently with seed mixed via the
golden-ratio multiplier 0x9E3779B97F4A7C15 from the base seed
0xE2E2E2E2.

**Expected outcomes & next steps:**

| Overlap signal | Topology signal | Interpretation | Next move |
|---|---|---|---|
| narrow peak near 1.0 | mostly invariant | one basin, deterministic | PT diversification is broken; debug seeding |
| broad single peak < 1.0 | <50% invariant | one giant basin, replica-symmetric | RSB framing wrong; revisit CP-side and SRGL |
| multi-modal | mostly invariant | 1-RSB + global obstruction (both!) | Houdayer + color-strand surgery (combine) |
| multi-modal | <50% invariant | 1-RSB clean signal | Houdayer cluster moves (Houdayer 2001) |
| broad single peak < 1.0 | >90% invariant | strong topological obstruction | color-strand surgery moves |

Bias: I expect **multi-modal overlap + partially invariant topology**,
because the negative results from all prior local-search variants
look most like 1-RSB clustering with some local rearrangements
still permitted (the score wobbles 446-449, not flat 449).

**Smoke check (N=3, 5s PT each):** q_oriented values {0.67, 0.68, 0.86}.
Already non-trivial spread; N=20 should give resolution.

---

## 2026-05-11 — First RSB / topology / Houdayer results (UNPINNED puzzle)

**H** — (a) Plateau states cluster in configuration space (multi-modal P(q))
or (b) share a color-flow invariant — at least one should give signal.

**Setup** — `rsb_n20_pt90`: 20 plateau states from 30s CP + 90s PT × 8
replicas, distinct seeds, **hint pinning OFF** (this was the harvest in
flight when we discovered pinning wasn't implemented). Scores spread
447–451 (mean 449.1). 190 unordered pairs.

**Results.**

*Hint preservation*: `audit_hints` confirms 0/20 samples preserve ANY of
the 5 official hints. Confirms our 449 baseline is on the unconstrained
puzzle. Pinning is now wired but harvest needs a re-run.

*Overlap P(q)*: q_oriented (190 pairs) is **multi-modal**.
- Main mode 0.67–0.75 (141 pairs, 74%).
- Tail 0.58–0.67 (33 pairs).
- Distinct peak 0.92–1.00 with 8 pairs at q ≈ 1.0 — different seeds
  occasionally converge to **identical** plateau boards.
- Smaller mass at 0.75–0.92 (8 pairs total).
This is consistent with 1-RSB or full RSB: discrete basins with some
seeds finding the same basin.

*Topology*:
- **Colors 1–5 (the freq=24 "edge-strip" colors) are TOTALLY invariant**
  in both h_total and v_total across all 20 states. Border edges fully
  locked.
- v_per_row: 55.2% of (color, row) cells invariant; h_per_col 40.0%.
- High-variance cells are concentrated in rows 4–9, cols 6–10 — the
  central ≈6×6 region. **The plateau is a center-of-board phenomenon.**

*Houdayer offline (per pair, on all 190 pairs)*:
- 225 disagreement components (size ≥ 2) found. Mean size 64.3 cells.
- **151 of 225 are piece-multiset swappable.**
- **ALL 151 swappable proposals have joint_delta = 0.**
- 0/190 pairs admit any improving Houdayer swap.
- Component sizes are HUGE (mean 80.7 for swappable): essentially the
  whole interior disagrees as one connected blob, surrounded by the
  perfectly-agreed border.

**Verdict**.
1. **Border edges are solved.** The plateau lives in the interior.
2. **Multi-modal P(q) supports 1-RSB.** Different seeds reach different
   basins; some basins are revisited.
3. **Houdayer alone won't beat 449** — every swappable region swap is
   zero-delta. But this is the published "swappable but not improving"
   regime: Houdayer is a *diversifier* whose value comes from combining
   with intra-replica SA moves, not from the cluster delta itself.
4. **The "right" next experiment** has shifted:
   - (a) Re-harvest with `--pin-hints` so we measure the actual constrained
     plateau. Numbers will likely drop because pinning removes flexibility.
   - (b) Implement Houdayer-in-PT (not just offline): after the cluster
     swap reshuffles, SA continues at that T. The zero-delta swap moves
     each replica to a different local optimum that intra-replica SA
     might then improve.
   - (c) Focus search effort on the central 6×6 region — try local-CP
     repair restricted to that area.

**Open question.** Is the q=1.0 peak (seeds converging to *identical*
boards) evidence that the deterministic CP partial dominates? With CP
shared across all 20 seeds, every replica starts from the same partial.
Most variation comes from PT's stochastic moves on top of that partial.
Re-running with `--reuse-cp=false` would test how much of the multi-
modality is intrinsic vs. CP-driven.

## 2026-05-11 — Color labeling and Bucas rendering

The user pointed at pieces.txt and clues.txt from e2.bucas.name. Investigation:

- `pieces.txt` is 256 tokens in Bucas 4-letter form, sorted alphabetically
  by canonical (lex-min over rotations).
- `clues.txt` URL encodes the official 5 clues at positions (2,2), (13,2),
  (7,8), (2,13), (13,13) with 1-indexed piece IDs into pieces.txt.
- Three URLs in the wild use **three different color labelings** of the
  same physical puzzle: pieces.txt's own, Joshua's `motifs_order=jblackwood`,
  and clues.txt's `motifs_order=jef`. All three have the same color
  frequency multiset (1 color×64 border + 5×24 + 5×48 + 12×50) but the
  labels-to-colors permutation differs.
- **Our existing CSV ALREADY uses pieces.txt's labeling**: piece 138 has
  edges (8,9,9,12) at rot 0, hint at (7,8) rot 0 — verified identical to
  what pieces.txt would generate.
- The hint rotations (R0, R270, R0, R270, R180) for (7,8), (2,2), (13,2),
  (2,13), (13,13) were solved via constraint-satisfaction on the partial
  color bijection — only ONE rotation tuple gave 13 consistent (out of
  22) σ mappings. These match the official rotations.

**Effect on Bucas rendering**: our generated URLs use pieces.txt's labels,
which Bucas renders as motifs A–V. The board is internally consistent and
matched edges share colors in the viewer. The visual color theme will
differ from Joshua's URL byte-for-byte (different motifs_order ⇒ different
letter→pattern mapping) but the **puzzle** is the same.

---

## 2026-05-11 — Two-bug fix: parallel CP ignoring hints + Bucas rendering

**H** — Our 449/93.5% baseline is unconstrained (no hints) because
something in the pipeline ignores them, despite us passing them to CP.

**Setup** — Audit one of the rsb_n20_pt90 plateau dumps for hint
preservation via the new `audit_hints` binary. CP+PT pipeline,
`opts.hints = file_hints`, 5 official hints.

**Result** — 0/20 plateau states preserve ANY of the 5 hints. Cause
isolated to two bugs:

1. **Parallel CP path (`parallel::solve_parallel`) silently ignored
   hints.** `solver-engine::SearchState::run()` applies hints inline
   before recursion (lib.rs:1123), but the parallel root-split path
   creates fresh `SearchState`s in `enumerate_units` and `run_unit`
   without ever calling that code. Every parallel solve was on the
   unconstrained instance. All seven parallel engine profiles
   (gacolor_ac3_par etc.) affected.
   **Fix**: extract hint+symmetry application into
   `SearchState::apply_symmetry_and_hints`; call from both
   enumeration and worker paths in `parallel.rs`.

2. **Bucas URL hardcoded `motifs_order=jblackwood`**, which uses a
   different color labeling than our CSV (pieces.txt's labels).
   The viewer rendered most pieces blank because letters didn't
   match its motifs catalog. **Fix**: drop the param; Bucas's
   default labeling matches ours.

Also wired hint pinning through PT/SA:
- `SaConfig::pinned_positions`, `PtConfig::pinned_positions`.
- `State::new_with_pinned` filters pinned cells out of per-class
  cell pools so random picks never select them.
- Cluster moves (2x2, 3x3 rotate, region swap, rotate-only on full
  grid) explicitly check `state.pinned[pos]` and bail.
- `pt_e2 --pin-hints` (default true) passes the puzzle file's hints
  as pinned positions.

**Verdict** — kept. Fresh pt_e2 run with pinning on now preserves
all 5 hints in the output board (verified via Python on the
Bucas URL). Bucas viewer renders cleanly without motifs_order.

**Implication for prior results** — Our previously-reported 449 on
"official E2" was actually on the unconstrained puzzle. Community
SOTA of 470 (Blackwood) is on the constrained puzzle. The numbers
are not directly comparable. We need a fresh constrained baseline.

---

## 2026-05-11 — Pinned baseline harvest (in progress)

**H** — With hint pinning on, the plateau score distribution
shifts down by some amount; the new mean is the true baseline
against which Blackwood's 470 should be compared.

**Setup** — `harvest_plateau --pin-hints --n-samples 20 --cp-seconds 30
--pt-seconds 90 --n-replicas 8 --run-name rsb_n20_pt90_pinned`.
Same parameters as the unpinned `rsb_n20_pt90` harvest for direct
A/B comparison.

**Result (stopped at 6/20 samples — user requested truncation)** —
scores [448, 448, 449, 447, 447, 450]. Mean **448.2**, range
[447, 450]. **Best constrained score: 450/480 (93.8%) from seed
0x171560a05f574f4b**.

Bucas URL of the 450-board (all 5 hints preserved, verified):
`https://e2.bucas.name/#puzzle=best_constrained_450&board_w=16&board_h=16&board_edges=abdaa...ceaab`
(saved to output/plateau/rsb_n20_pt90_pinned/sample_005...).

Compared to unpinned mean 449.1: **hint-pinning cost is ~1 edge on
average**. Much smaller than expected. Implies unpinned PT was NOT
heavily exploiting hint-free flexibility; the constrained and
unconstrained basins are geometrically close.

**Updated diagnostics on the 6 pinned dumps**:

*Overlap P(q)* (n=15 pairs):
- Main peak at 0.67-0.75 (13 pairs), one outlier at 0.66 and one
  at 0.83-0.92. **No q≈1.0 peak** (unlike unpinned, which had 8
  pairs at q ≥ 0.92).
- mean=0.716, std=0.042 — tighter than unpinned (mean 0.70, std
  0.07). With pinning, no two seeds converge to identical boards.
- The unpinned multi-modal structure has *weakened* under
  constraints — the q≈1 peak was an artifact of unpinned freedom.

*Topology*:
- Colors 1-5 still 100% invariant (border lock unchanged).
- v_per_row cells: **63.0% invariant** (was 55.2% unpinned).
- h_per_col cells: **53.3% invariant** (was 40.0% unpinned).
- **Hints INCREASE invariance** — they anchor structure that
  propagates outward. The plateau is even more geometrically
  localised under constraints.

*Houdayer offline*:
- 17 total disagreement components (mean size 63.6).
- Only **4 swappable** (vs 151/225 unpinned). Constrained pieces
  are less interchangeable across boards because hint pieces are
  anchored at specific cells.
- All 4 swappable have joint_delta = 0 (microcanonical).
- The lower swappable rate weakens the case for Houdayer as a
  pure offline operator, but not for Houdayer-in-PT (which
  benefits from post-swap SA, not just swap deltas).

**Verdict** — kept as the new constrained baseline. 450/480 best
known. 6 samples is enough to see the shifts; we don't need to
finish N=20 unless we want tighter histograms.

**Implication for next experiment**: with pinning making Houdayer
swaps rarer, the Houdayer-in-PT bet is more speculative. The
**central-region CP repair** thread becomes more attractive:
topology says even more of the board is invariant under pinning
(63% v-cells, 53% h-cells), so the candidate "frame" around the
central variance region is even more reliable as a hint set.

---

## 2026-05-11 — Upper-bound certificate threads (negative findings)

**H** — A cheap counting / LP upper bound can either certify our
plateau as near-optimal (publish a hardness result instead of
optimising) or confirm there's room and we should keep pushing.

**Setup** — Compute the simplest closed-form bounds in Python on
pieces.txt:
1. Color-multiplicity: UB = Σ_c ⌊N_c / 2⌋ over colors.
2. Per-edge color-compatibility: UB = #edges where the two cells
   have at least one common admissible color.

**Result** — both bounds give **480** (the trivial total-edge
upper bound).
- Color counts on official E2 are perfectly balanced: 5 colors at
  24 (each appearing 12× as matched edges), 5 at 48, 12 at 50, all
  even. Σ ⌊N_c / 2⌋ = 480 = total interior edges.
- Side-color sets cover all colors at every interior cell, so the
  per-edge compatibility bound is also 480.

**Verdict** — both dropped. **The hardness of E2 is genuinely
combinatorial.** Closed-form / counting bounds are too loose. A
real LP relaxation would have ~156k cell-placement variables —
borderline for scipy.linprog, and standard LP literature says the
relaxation is loose anyway (Kovalsky-Glasner-Basri 2014's SDP only
worked up to 7×7). Dropping the LP-certificate thread; it's
practically harder than the literature scan suggested.

**Lesson recorded** — pieces.txt color balance is itself a notable
structural fact: it tells us perfect E2 solutions exist
colorimetrically (no immediate parity obstruction), so the
obstruction is purely geometric/combinatorial.

---

## 2026-05-11 — Houdayer cluster moves integrated into PT

**H** — The offline Houdayer analysis showed swappable components
exist between plateau states but all have joint_delta = 0. The
move itself doesn't improve score, but might *redistribute* board
content so that subsequent SA reaches a better local optimum than
either replica would alone. Test by running PT with periodic
Houdayer moves.

**Setup** — New PtConfig fields:
  `houdayer_every: u64` (rounds between Houdayer phases, 0 = off)
  `houdayer_max_component: usize` (skip components above; default 20)
  `houdayer_min_component: usize` (skip components below; default 4)

After each PT round's replica-exchange phase, iterate over adjacent
pairs (i, i+1). For each pair, enumerate swappable disagreement
components (using existing `houdayer::enumerate_proposals`),
filter to the size band, pick one uniformly, apply
unconditionally. Update scores and best-board trackers per replica.
PtStats grows three counters.

**Smoke test result** — `pt_e2 --houdayer-every=5 --houdayer-max=200
--houdayer-min=2` (very wide band). Houdayer fires regularly on the
cold pair (0,1) with components of size 73-77. Hot pairs (1,2),
(2,3) have no components in the size band — their disagreement is
too large, which is the correct behaviour (hot-replica chaos
doesn't admit structure for cluster moves).

**Verdict** — wired, smoke-tested, ready for real A/B. The actual
question (does it help break 449?) needs a longer run with seed
sweep. Plan: after the pinned harvest finishes, run another harvest
with `--houdayer-every=10 --houdayer-max=30` for direct comparison.

---

## 2026-05-11 — Central-region CP repair (planned)

**H** — Topology results showed the variance across plateau states
is concentrated in rows 4-9, cols 6-10 (the central ~6x6). The
plateau is geometrically localised. The earlier mini-CP repair
failed (~99% wipeout) because pinning the boundary of an arbitrary
region created unsatisfiable sub-problems. But the BORDER of E2 is
fully solved across all plateau states (colors 1-5 invariant), and
the central 6x6 is far from the BORDER — so the boundary of the
central region IS the perfectly-matched middle rings, which should
admit feasible inner assignments.

**Setup** — when pinned harvest finishes: take one of the highest-
scoring plateau dumps, call existing `repair_region(board, 5, 5,
6, budget_ms=60_000)` to free the central 6x6 and re-solve via CP.
Measure score delta. Repeat across all 20 plateau dumps to estimate
expected improvement.

**Verdict** — pending.

---

## 2026-05-11 — Central-region CP repair: definitive negative result

**H** — Topology said variance is in the central 6x6; border colors
are 100% invariant across plateau states. Therefore, pinning the
outer cells and re-solving the central 6x6 via CP should fix the
plateau by exploiting the (correct) frame.

**Setup** — New binaries `central_repair` (free a chosen window)
and `worst_region_repair` (find the lowest-internal-match k×k
region and repair it). Tested on the 450/480 plateau dump
(sample_005_seed_171560a05f574f4b).

**Result** —
- `central_repair --k 6` (centre 6×6): **CP wipeout in 0.1s**
  (Exhausted: provably no feasible interior given the pinned
  surround).
- `central_repair --k 8`: wipeout in 0.0s.
- `central_repair --k 12`: wipeout in 30s budget (still no soln).
- `central_repair --k 14` (only border pinned): **timed out at 60s
  without completing the interior**.
- `worst_region_repair --k 6` (worst region at (8,5)): wipeout in 0.1s.

Even with only the BORDER pinned (60 cells), CP cannot complete
the 196 interior cells in 60s. With more cells pinned, it proves
infeasibility instantly.

**Verdict: dropped.** The plateau state is *globally inconsistent*
with completing the puzzle, even though its border is 100%
identical to every other plateau state's border, AND those border
choices look locally fine (all border-interior matches present).

**Deeper insight (changes our model of the plateau).**
- All 6 plateau states share the SAME border (60 cells identical).
- 97/196 (49%) interior cells are also invariant across plateau
  states.
- Yet CP can't extend the remaining cells from any plateau state's
  pinned outer cells. This means **the canonical-border-after-PT
  is not a valid prefix of any full E2 solution** under the piece
  set we have.
- PT/SA's greedy_fill chooses border pieces that *locally* match
  perfectly but *globally* don't admit interior completion. Every
  seed converges to the same wrong border because greedy_fill is
  deterministic given the CP partial.
- The 449-450 plateau is a fundamental constraint of "PT after CP
  + greedy_fill" — it has nothing to do with SA's move set.

**Implications for next steps.**

1. **Local CP repair can never fix this** — the obstruction is in
   the *pinned* cells, not the freed ones. To break 450, we need
   to *free border cells* and let CP find a different border
   permutation that does admit interior completion.

2. **Houdayer-in-PT** is more promising than I thought:
   - It teleports the SA chain to a different *interior*
     configuration with the same border.
   - But if the border is the bottleneck, Houdayer between same-
     border replicas won't help. Need Houdayer between DIFFERENT-
     border replicas, which requires different greedy_fills.
   - Concretely: re-run PT with `--diversify_fill` (already a flag,
     currently unused) so different replicas get different greedy
     fills, then Houdayer can swap between different-border replicas.

3. **The strongest next experiment** is no longer Houdayer-in-PT
   but rather **CP with a different border**. Two routes:
   - (a) Run CP itself from scratch with a different seed/heuristic
     so it finds a different partial → different greedy_fill →
     different border. We've effectively been doing this with
     different PT seeds, but PT only adds noise on TOP of the same
     CP partial. We need different CP partials.
   - (b) Explicitly perturb the CP partial: take CP's output,
     remove some random border pieces, and let CP re-solve from
     that. Or apply CP+restart with different variable ordering.

**Action**: pivot from "fix the plateau locally" to "find a
different prefix that admits global completion". Two concrete
experiments:
   (i) Run pt_e2 with --reuse-cp=false in harvest_plateau (run CP
       fresh per seed); compare to current results. If different
       CP partials → different borders → different plateaus, we
       learn whether CP itself is deterministic or seed-sensitive.
   (ii) Implement a "border-shuffle" CP restart: from a 450 plateau,
       remove the border pieces, re-run CP with hint+symmetry but
       a different variable-order seed.

---

## 2026-05-11 — σ bijection solved; Blackwood's 470 is on a DIFFERENT problem

**H** — Compare our CP's piece commitments against Blackwood's 470 solution
to find where our search makes "wrong" choices early.

**Setup** — Decode Blackwood's Bucas URL into our pieces.txt color
labeling. The σ: pt_color → joshua_color bijection is overdetermined by
having 256 known pieces in common; AC-3-style domain propagation
converges in 2 iterations to a unique σ for all 23 colors. Decoded
Blackwood board saved to `output/blackwood_decoded.json`.

**Surprise 1**: Blackwood places different pieces at the 4 corner-region
hint cells than the official 5-clue mandate.
  - (2,2):  Blackwood=piece 147, official=207
  - (2,13): Blackwood=piece 108, official=180
  - (13,2): Blackwood=piece 186, official=254
  - (13,13):Blackwood=piece 249, official=248
Only the central (7,8) hint matches.

**Cross-check via web research on libblackwood:**
The repo's puzzle definition `tomy_EternityII.py:E2ncud` pins only the
central piece. The 4 corner hints are dropped. **Blackwood's 470 is on
the 1-clue version, not the official 5-clue version.** All our 5-clue
plateau scores are NOT directly comparable to 470.

**The actual algorithm in libblackwood** (from the agent dive):
  1. Pure forward DFS in C, no CP/DLX/SAT. 40-57M nodes/sec.
  2. Random-seed multi-start parallelism (N processes × 15-min limits).
  3. Pruners:
     - Per-cell precomputed `(left_color, up_color) → sorted piece list`.
     - Monotone color-count constraint: 3 specific colors must keep
       cumulative count above an empirically-tuned piecewise-linear
       curve over depth. If below, prune subtree.
     - **Scheduled relaxations**: 10 specific late depths
       (197,203,210,216,221,225,229,233,236,238) where one edge
       mismatch is allowed. The 10 missing edges in 470/480 are
       DELIBERATELY scheduled, not accidental.
  4. Scenarios `jb466.py` … `jb471.py` differ only in how many
     relaxations are allowed. **`jb471.py` exists** (9 relaxations)
     but the public repo has no log of it succeeding.

**Verdict**: This completely reframes what 470 means.
  - 470 is "1 hint pinned, 10 mismatches deliberately allowed, brute-
    force search at 50M nodes/sec for hours until lucky restart."
  - It's NOT "the best E2 solver finds 470 on the standard 5-hint
    puzzle."
  - The hardness ramp 466→467→…→471 is real and *Blackwood himself
    doesn't have a public 471*.

**Action**: stop comparing our 5-clue scores to 470. Run our pipeline
in the same 1-clue config Blackwood uses to get an honest comparison.

---

## 2026-05-11 — prefix_compare result + diverse-prefix harvest stopped

**H** — Either our CP makes a specific wrong choice early that dooms it,
or our search is "fine but different" from Blackwood's.

**Setup** — Run CP with central hint only for 10s, capture committed
cells, compare to Blackwood at those cells.

**Result** — CP committed 169 cells in 10s; only **2 match Blackwood**
(the central hint + one accidental match). At cell (0,0) our CP picks
piece 0; Blackwood picks piece 2. **Divergence starts at cell #1.**

**Interpretation**: doesn't mean our choices are wrong — multiple
valid solutions exist. But combined with our earlier finding that local
CP repair on our plateau states is provably-infeasible, this suggests
our specific commitments lead to a dead end while Blackwood's lead
to a near-solution. The search-space exploration is fundamentally
different, not a small-mistake-then-recover difference.

**Diverse-prefix harvest** (`rsb_n20_random_cp`, stopped at 4/20):
RandomShuffle CP gives genuinely diverse prefixes (55/60 border cells
differ). But the plateau is now **443-444**, slightly LOWER than
deterministic-CP's 447-450. Diversity by itself doesn't help, and it
hurts a bit because random tiebreaks occasionally pick worse.

**Conclusion across the two**: prefix diversification, on its own, is
not the answer. Blackwood's solution combines:
  (a) a different problem (1 hint not 5),
  (b) a deliberate decision to accept mismatches (10 of them),
  (c) a custom pruning curve on a hand-picked color subset,
  (d) raw brute-force speed.

**Verdict** — close out the post-CP optimisation thread. The next
session's leverage is in (b) and (c): scheduled-relaxation and
monotone color-count pruning.

---

## 2026-05-11 — SESSION CLOSE

Big takeaways:
1. **Bugs fixed**: parallel CP ignored hints; PT/SA had no pinning;
   Bucas URL had wrong motifs_order. Bucas now renders correctly.
2. **Constrained baseline**: ~447-450 with all 5 hints pinned. Best
   so far 450/480 from one harvest seed.
3. **Plateau is upstream of SA**: CP+greedy_fill produces a globally-
   wrong prefix that local repair can't fix; the prefix dominates.
4. **Blackwood's 470 is on the 1-clue version**, not 5-clue. SOTA
   comparison was apples-to-oranges. The 5-clue community SOTA is
   not publicly known to us.
5. **Blackwood's secret**: scheduled relaxations + monotone color-count
   pruning + brute force at 50M nodes/sec. Not exotic. Empirical.

Next session priorities (in order):
  1. Run our pipeline 1-clue to get an honest comparison number.
  2. Add a "scheduled relaxation" mode: CP allows K edge mismatches
     at K specific late cells, picked by some heuristic. Test K=10.
  3. Add monotone color-count pruning as a CP propagator.
  4. (Maybe) implement the per-cell edge-pair lookup table for
     throughput.

The session's most important meta-lesson: **always verify the SOTA
target before optimising against it.** We spent significant compute
beating ourselves up against 470 which was on a different problem
altogether. The σ bijection + agent dive would have surfaced this
in 30 minutes had we done it Day 1.

## (entries follow as experiments run)
