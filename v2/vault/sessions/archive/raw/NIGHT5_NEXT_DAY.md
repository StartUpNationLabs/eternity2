# Night 5 → Day 6 — concrete prioritized experiment plan

**Audience**: morning-Claude, future-self.
**Premise**: tonight's structural science is solid (see NIGHT5_SYNTHESIS).
The score is at 450/480. This document lists experiments that, if
attempted tomorrow, have the highest expected impact.

Sorted by **expected probability of breaking 450** × **time efficiency**.

---

## ⭐ HIGHEST PRIORITY (post-breakthrough update 03:20)

### 0. SCALE THE GA — replicate and extend the 452 result

GA-light (12 crossovers, 8% hit rate) reached 452. **Scale to 100+
crossovers** and we expect ~10 hits at 451+. Of those, statistically
1-2 might be at 453+.

**Setup**: same `scripts/ga_crossover.py` building block. Modify
`scripts/ga_light_run.sh` to N=100, K=4 (the sweet spot region size),
PT seconds = 60 (faster cycles). Total compute: ~1.7h.

**Predicted gain**: at least 452 (≥1 hit) and likely 453-455 (1-3 hits).
With 100 samples we can estimate the breakthrough-rate distribution
and find a few outliers.

**Why this is the FIRST thing to do tomorrow**: directly cashes in
the night's discovery. Low risk, high EV, no new code.

### 0.5 CASCADE from the 452 board

Phase B of tonight's `post_ga_cascade.sh` does this (8 crossovers
using the 452 as one parent). If any reach 453+, we have a
*generative* process not just a one-off lucky hit.

**Status**: queued in chain, results expected ~04:30 CEST.

### 0.6 Apply the 4×4 (top-right) recipe systematically

The breakthrough was at region (11,1)+4. Try ALL 4×4 regions in
the top-right quadrant systematically (rows 1-5, cols 8-13 = ~30
regions). With NE2-K10 449 + vol-4 450 as parents. Total compute:
30 × 90s = 45 min. **Cheap, reproducible.**

If 30 regions in top-right produce ≥1 hit at 452, the recipe is
real. If only (11,1) works, the (11,1) hit was noise.

---

## Tier 1: best EV (each ≤ 1 day; ≥ 30% chance of producing a 451+)

### 1. Memetic GA with block crossover, full population

**Why**: tonight's GA-light (12 crossovers) is a smoke test. A real
GA needs:
- Population of 30-50 boards (mix of 449/450 + new mutations).
- Tournament selection (size 3).
- Crossover at multiple region sizes (4×4, 6×6, 8×8) with K varied.
- Each child polished by 60-120s pt_e2 PT.
- Replace worst-in-pop if better.
- Run 100-500 generations.

**Predicted gain**: +1 to +5 from 450, depending on whether crossover
breaks the moat-depth-5 lock. Vol-4 noted "Niang 2011 / Munoz MICAI
2009 — only listed method with non-local recombination."

**Time**: 3-4h to build the population manager + orchestrator;
8h+ to run.

**Falsification**: if 500 generations stays at 450, memetic GA is
also moat-depth-bounded and we need even larger moves.

**Build files needed**: `scripts/ga_population.py`, `scripts/ga_run.sh`.
The crossover building block (`scripts/ga_crossover.py`) already exists.

### 2. Wauters-style VLNS — large 8×8 destroys with slow SA repair

**Why**: tonight's ALNS uses 4-5 cell destroys. Wauters' published
458 used 50-cell-class destroys. Direct lift from the literature.

**Implementation**: extend `crates/localsearch/src/alns.rs` to
support `RandomRegion { k: 8 }` and `WorstWindow { k: 8 }`. SA
repair needs longer (10x) inner-iters since the destroyed region is
4× larger.

**Predicted gain**: per Wauters' published results, ~+8 from
canonical 449 → 458. Bigger than any other tonight-tested method.

**Time**: 3h Rust + 2-4h compute.

**Falsification**: if 8×8 destroys produce same plateau as 4×4
destroys, the ALNS framework has fundamental limit at PT-derived
plateau (we've already seen this for 5×5 in vol-4).

### 3. Multi-restart frame-first with explicit border DIVERSITY

**Why**: tonight's NE1 funnel produces 450s reliably but capped at
450. The hypothesis is that SOME borders, by changing the strain
field exotically, would reach 451+. Need to explore MUCH more
border space (1000+ borders, not 30).

**Implementation**: run `frame_first_e2 --n-borders 1000
--pt-seconds 30 --base-seed <random>` overnight (~8h). Stage-2
filter by top-12 universal-mismatch matches.

**Predicted gain**: +0 to +1. Statistical: with 1000 borders, even
if 0.1% reach 451+, we'd get 1.

**Time**: 0 dev (script exists), 8h compute.

**Falsification**: if 1000 borders all cap at 450, frame-first basin
diversity does not exceed 450.

---

## Tier 2: medium EV (each 1-3 days; <30% chance of 451+)

### 4. Cell-defect MWPM as ALNS destroy operator (NE7 integration)

`scripts/cell_defect_mwpm.py` already exists. Need a Rust wrapper
that calls Python via subprocess to get the destroy set, then
applies normal CP/SA repair.

Expected gain: small. Vol-4 ALNS+MWPM stalled at 449. This is the
SAME method but with a more principled destroy-set selection.
Probably +0 to +1.

Time: 4h.

### 5. Stronger SAT encoding + EvalMaxSAT

The current 114 MB WCNF is too large for EvalMaxSAT. A tighter
encoding that omits piece-rotation vars for pinned cells could
reduce by 3-5x. Then re-run EvalMaxSAT for 8h.

Expected gain: unclear. SAT might find ANY feasible solution = 480
or might still time out. Either way, useful diagnostic.

Time: 4h Rust (in `crates/sat-encoder/`) + 8h compute.

### 6. Survey Propagation on the right encoding

Tonight's NE-BP failed because it used the cell-compatibility
relaxation (no all-different). A correct SP would need the full
cell-place-rotation encoding with piece-uniqueness factors.

Vol-5 night's SP agent verdict was "1.5/5 stars, do not pursue."
This recommendation stands UNLESS someone has fresh ideas about
how to handle the all-different.

Time: probably 1-2 weeks. Skip unless other paths exhaust.

---

## Tier 3: structural/analytical (yields scientific output but
   unlikely to budge the score)

### 7. Drop the asymmetric (7,8) hint and run unconstrained PT
   for many seeds

The strain diagnostic queued in tonight's chain (PHASE 4) does this
ONCE for 600s. If it shows score >> 449, the hypothesis is confirmed
and a 100-seed sweep would establish a confidence interval.

Expected outcome: if hypothesis right, scores cluster around 460-470
when (7,8) is unpinned. This is NOT an "official E2" result.

Time: 0 dev (just rerun strain_diagnostic.sh with different seeds).

### 8. Static analysis of all 256 piece signatures

`scripts/puzzle_structural_analysis.py` already produces the rare-
vs-abundant breakdown. Future extensions:
- Per-piece "informativeness" metric (number of placements compatible
  with current placements of others).
- Co-occurrence graph of color pairs across pieces.
- Identify "globally-forcing" piece subsets.

Time: 4-8h Python. Pure structural; doesn't break the plateau.

### 9. Spectral analysis of the plateau Hamming graph

For each pair of plateau boards in the corpus, compute the Hamming
distance (= # cells differing). Build a graph on the 29 boards.
Look at clustering, spectral gap, etc. Published methods (Krzakala
et al. for SAT) could apply.

Time: 1-2 days.

---

## What NOT to try (already definitively ruled out tonight)

- **Soft-penalty PT alone (NE2/NE2.1)**: redistributes defects,
  conserves 30/31 budget.
- **2-swap or 3-cycle local search**: exhaustively tested, 0
  improvements on 450 boards.
- **Salassa TA Hungarian**: 0 improvements on PT-derived 450.
- **Salassa max-clique RO**: perfect-fill maxima smaller than
  current placement.
- **BP on edge-color**: paramagnetic fixed point, no signal.
- **EvalMaxSAT on full WCNF**: 1h22m, no `o` lines.
- **Iterative-deepening of forbidden set**: 30-budget conserved.

These are NEGATIVE RESULTS with rigorous evidence. Document them
and move on.

---

## Recommended morning execution

If user is interested in pushing the score: **start with Tier 1.1
(memetic GA full)**. Highest EV, biggest novel test.

If user wants maximum scientific output: **start with Tier 3.7
(strain hypothesis multi-seed test)**. The strongest publishable
finding (asymmetric hint cascade) becomes much stronger with more
seeds.

If user wants to write up: **the synthesis + abstract are ready**.
Need 1-2 days of polish + literature comparison before submission-
ready.

If user wants to build infrastructure for the long game: **NE2.2
(SAT 2024 adaptive clause-weighting)** ports a peer-reviewed 2024
algorithm to our codebase. Future-proofs against the 2024-2025
MaxSAT advances.

---

## Cost summary

| Tier | Days dev | Hours compute | EV gain |
|---|---|---|---|
| 1.1 GA full       | 1   | 8    | +1 to +5 |
| 1.2 VLNS 8×8      | 0.5 | 4    | +0 to +8 |
| 1.3 Multi-restart frame-first | 0 | 8 | +0 to +1 |
| 2.4 NE7 ALNS-MWPM | 0.5 | 2    | +0 to +1 |
| 2.5 Better SAT    | 0.5 | 8    | unclear |
| 2.6 SP correct    | 7-14| ?    | research bet |
| 3.7 Strain multi-seed | 0 | 4 | structural confirmation |
| 3.8 Static analysis | 1 | 0 | structural insight |
| 3.9 Spectral graph | 2 | 1 | structural insight |

The single most cost-effective experiment is **3.7 (strain
multi-seed)**: 0 dev, 4h compute, would conclusively confirm or
falsify the night's strongest hypothesis.

The single highest-EV-on-score is **1.1 (memetic GA full)**: 1 day
dev + 8h compute, plausible +5.

The single biggest open question: **does the moat-depth-≥-5 finding
extend to ≥6 or ≥7?** 5-piece sample was 30 quintuples (0.017% of
all). Larger sample needed; or move directly to 7×7 region rebuild
and see if anything fills.
