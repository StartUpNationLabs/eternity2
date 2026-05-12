# Eternity II research — volume 7 (sister vol-7, exploration mode)

Continuation in spirit of vols 5 and 6, but with a different mandate.

- **Vol-5** (night, 1782 lines): exhausted soft-penalty PT, NE1/NE2/NE2-iter,
  NE-BP, max-clique RO, Wauters/Salassa polishing, GA-light/cascade.
  Result: 449 → 452 → **453**.
- **Vol-6** (morning, 375 lines): rare-color/skeleton/free-zone analysis,
  EvalMaxSAT *minimal* encoder; **rigorously proved 453 is OPTIMAL for
  inner k=3, 4, 5 given its outer fixed**. Inner-only optimisation
  cannot break 453. Consensus seeding lands back in the 452 basin.
  Hard-skeleton + free-zone backtracking gives only 357 (over-rigid).
- **This vol-7** (May 12 ~08:00 CEST, sister-session): explicit mandate
  is **OUT-OF-FIELD ideas to escape the 453 basin**. Vols 5/6 were
  execution-mode; vol-7 is exploration-mode.

Authoritative state in `memory/project_e2_state.md`. Best score
**453/480** with 27 mismatches.

---

## Mission

Get OUT of the 453 basin (and its 452/451 neighbours). Vols 5-6
ruled out:

- Soft-penalty PT (NE2/NE2.1/NE2-iter) — redistributes, conserves budget.
- Single-T SA / vanilla PT — bounded by moat depth ≥5.
- ALNS at 4×4 / 5×5 destroys — below moat depth.
- ALNS + MWPM (cell-defect) — same.
- Edge-CP + PT — alldiff is the rigidity locus.
- Wauters TA (Hungarian, K=16) / TSR / max-clique RO — PT removes
  the slack their polishing assumes.
- Memetic GA at 4×4 / 6×6 (GA-light / GA-LARGE / GA-CASCADE) — reaches
  452/453 but does not break 453.
- Consensus seeding — collapses back to 452 basin.
- Anti-consensus — wrong target; corner-cascade edges.
- Hard skeleton + free-zone backtracking — over-rigid, 357.
- Frame-first 100-1000 borders — 450 ceiling; never broke 449 by
  border-search alone.
- BP on edge-color — paramagnetic; all rigidity lives in alldiff.
- Survey Propagation — 1.5/5 by literature review (short cycles + no
  rigid phase).
- IsingFormer / GFlowNet / diffusion-CO — 2-4 weeks, no track record.
- GPU/FPGA/quantum SAT — academic theater at 5-clue scale.
- EvalMaxSAT on full WCNF — no `o` lines, alldiff too dense.

What proves 453 is the ceiling for the current outer: vol-6's k=3,4,5
EvalMaxSAT optimality run. To get 454+ we **must change the outer**
— meaning the border, the corners, or the layer 0-1 rings, or the
strain-front configuration around (7,8).

## Working hypotheses for vol-7

1. **The puzzle designer (Lord Monckton) had a specific construction
   recipe** — maybe published, maybe in patents — that pre-determines
   which abundant-color pairs are "decoy" pairs intentionally placed
   to create combinatorial near-degeneracy. If so, reverse-engineering
   the construction would give a strong informed prior.
2. **The community (eternity2 groups.io, hobbyist solvers since 2010)
   may have observations we haven't seen** — folklore that didn't make
   it into peer-reviewed lit but that points at structural levers.
3. **Adjacent problems** (Potts-model defect dynamics, genome assembly
   overlap-layout-consensus, jigsaw-2024-2026 vision, origami flat-
   foldability, gauge fields on lattices) may bring techniques that
   nobody has tried on E2 specifically.
4. **Vols 5-6 left implications unexplored.** Specifically:
    - The **32-cell free zone** (0.80 threshold) is a *description*
      but the over-rigid backtracking failed because skeleton was held
      fixed. What about *soft* skeleton + *joint* search?
    - The asymmetric (7,8) hint creates the south-central strain
      cascade — but we never tested **what happens if we *manufacture*
      a hint-set with different asymmetry** to identify which exact
      mechanism is at fault.
    - The **bucas-overlap-19% between two 450 basins** says there
      are *very* different basins out there. We may not have sampled
      enough basins to find a 454-class outer.

## Why this vol matters

This is sister-vol-7; vol-6 is still alive in another session (tail
of /tmp/ga_xl.log). No CPU contention because GA-XL already finished
its compute and the listener is idle. Vol-7 has the full machine and
the obligation to think differently rather than rerun.

Score is 453/480; any move that yields 454+ is the headline.

## Operating rules (vol-7)

- Spawn research agents liberally for parallel literature mining.
- Commit after every significant finding.
- Update auto-memory when something session-defining happens.
- Cite sources when forum/agent claims something — link, archive.
- Negative results matter; clean "X but Y" entries are valuable.
- The cron loop at 11,56 \* \* \* \* will ping with reflective prompts;
  honour it (~45 min cadence).

## Per-experiment format

```
### <name> — <timestamp>
**Hypothesis**: …
**Setup**: …
**Result**: …
**Verdict**: …
```

## Vol-7 dispatch log

### Selby-Riordan generator-bias DIAGNOSTIC 09:00 — NEGATIVE

**Hypothesis (M1 H1)**: the Selby-Riordan generator imposed a
detectable statistical bias on the official E2 piece set (since
they engineered E2 to defeat their own E1 solver). Test: chi-square
on per-color edge counts and Monte-Carlo on color-pair co-
occurrence within pieces.

**Setup**: `scripts/sr_generator_bias.py`. Counted per-color edge
totals on all 256 pieces; per-color NS/EW direction split (in
the canonical-rotation CSV labeling); color-pair co-occurrence
within pieces; MC shuffle of the same edge bag into random pieces.

**Result**:

- **Color counts**: 5 rare (1-5: 24 edges each), 5 medium (6-10:
  48 each), 12 abundant (11-22: 50 each). **All counts even**, so
  the puzzle is theoretically fully matchable.
- **Per-color NS vs EW split**: heavy directional imbalance in
  canonical rotation (e.g. colors 4,5 are 100% on E/W; color 6 is
  46/48 N/S). **Not a generator signature** — pieces can rotate,
  so the per-color NS/EW split in the *canonical* labeling just
  reflects the generator's arbitrary canonicalization choice.
- **Multi-occurrence within a piece**: 75 pieces have a color
  appearing twice (palindromic-ish); only 3 pieces have a color
  appearing 3×; **zero pieces have any color appearing 4×**.
  Suggests a generator soft-constraint against extreme repetition.
- **Color-pair co-occurrence missing**: 23 out of 231 possible
  color-pairs never appear together on any single piece.
- **MONTE-CARLO TEST** (most rigorous): shuffle the 784 interior
  edge labels into random pieces; recompute missing-pair count.
  500 runs: mean **95.03** missing pairs, stdev 0.16, range [95, 96].
  **Official puzzle: 95 missing pairs.** P(MC ≤ obs) = 0.972.

**Verdict**: **The "missing pairs" finding is NOT a generator
signature** — it's the expected result of any random piece set
drawn from the same color frequencies. The Selby-Riordan generator,
at the level of color-frequency-conditional piece statistics,
**looks statistically random**. M1's H1 is falsified at this level.

**What this means for the algorithm**: there is no exploitable
color-statistics propagator from generator-bias analysis. The
22-color frequencies + alldiff structure of E2 is essentially the
generic random-pieces-with-these-frequencies setup. The hardness
is in the global combinatorics, not in hidden generator biases.

**Falsifying observation that DID survive**: 5 piece-signature
duplicates exist (multisets shared by 2 pieces each), of which 2
are pure-interior: (7,10,15,17) and (9,12,14,21). On a 16×16 these
"twin" pieces are interchangeable in any matching — a small but
real symmetry. **Could be used for symmetry breaking in
backtracking** but probably worth <1% gain.

**Conclusion**: M1's directionally-promising hypothesis turns out
to be empirically empty. Focus shifts to the *active* user pivot:
border diversification.

### USER PIVOT 08:35 — BORDER DIVERSITY IS A MASSIVE OVERSIGHT

**User observation**: *"I think it also might be interesting to try
new boards, with new borders, with mostly tested with the same one
which is an oversight as there are many many borders possible."*

**Empirical verification (vol-7 check)**: across our entire corpus of
boards ≥443/480 (18 boards at 451-453 + 6 frame-first boards at 443-
450), there are only **7 distinct border signatures**, and:

| Border family | n boards | max score |
|---|---|---|
| 0 (vol-4 base 0xCAFEFEED) | **18** | **453** |
| 1 (GA-LARGE #17 novel) | 1 | 451 |
| 2 (vol-4 0xCAFEFEED) | 3 | 450 |
| 3 (NE1 stage-1 0xCAFEFEEC) | 1 | 450 |
| 4 (NE1 stage-2 0xCAFEFEEC+8) | 1 | 450 |
| 5 (frame-first 1778529843) | 1 | 446 |
| 6 (frame-first 1778532175) | 1 | 443 |

**All 18 boards in the 451-453 basin share ONE border.** The 453-
optimality proof of vol-6 is *conditional on this single border*.
Vol-5 ran 30 borders × 90s in NE1 stage 1 and the ceiling was 450;
vol-6 only worked on the inner of the 453-border.

This is **textbook sampling bias**. We never produced a single 451+
board on a non-family-0 border. The "453 ceiling" might be the
ceiling for family-0; another border could have a higher inner
optimum.

**Decision: pivot vol-7 to massive border diversification.**

Plan:
1. Launch frame_first_e2 with `--n-borders 200 --cp-seconds 15
   --pt-seconds 30 --border-gen-seconds 5`. This is ~3h wall on 8
   cores at 200 × 50s ≈ 167 min, before subprocess overhead.
2. Filter the resulting borders to top-K by stage-1 PT score
   (target: K=20 borders with stage-1 ≥445).
3. **For each top-K border, do GA crossover** with the existing
   453-class board as parent A, the new-border board as parent B.
   Region size 4×4 (vol-5's sweet spot), 60s PT polish each.
4. Score every product, log basin-membership via bucas-overlap.
5. If ANY 451+ appears on a new border, that's the breakthrough.

This is the right vol-7 move; Houdayer / Verhaard / Selby-Riordan
all stay queued behind this.

### MAJOR DISCOVERY 08:25 — Houdayer-in-PT IS ALREADY BUILT

While preparing the X1-suggested Houdayer prototype I found:

- `crates/localsearch/src/houdayer.rs` (278 lines, vol-3 commit `683d76d`):
  `disagreement_components`, `component_is_swappable`,
  `delta_replace_with`, `HoudayerProposal` types — exactly the X1
  recipe.
- `crates/benchmark/src/bin/houdayer_offline.rs` — offline post-mortem
  across pairs of harvested plateau states.
- `crates/localsearch/src/pt.rs` lines 414-461: Houdayer **wired into
  the PT main loop** (`houdayer_every`, `houdayer_max_component`,
  `houdayer_min_component`, accepted-applications counters).
- Vol-3 megarun observation (commit `312c44b`, **never fixed**):
  *Houdayer keeps proposing the same swap every round. Energy-
  preserving swaps `joint_delta=0` confirmed offline; subsequent
  replica-exchange undoes the swap.* Three fix proposals were noted
  for "vol. 3 next session" but never executed:

  > 1. Apply Houdayer ONLY between paired replicas at the SAME
  >    temperature (microcanonical), not adjacent-T pairs.
  > 2. Track recently-swapped components and forbid re-swapping the
  >    same component within K rounds.
  > 3. Skip replica-exchange for the pair we just Houdayered.

**So X1's "novel" recommendation is actually a vol-3 bug fix that was
punted because of [[project-e2-dead-ends]] = "Inversion 2 might make
PT obsolete"** (it didn't). The Houdayer move IS the structurally
correct mechanism for moat-depth-≥5; we just never made it stick.

**Estimated effort to land the fix**: ~30-60 min Rust (fix #3 is the
smallest — skip replica-exchange for one round after a Houdayer
acceptance — single conditional in the PT main loop) + rerun PT
from 453 with `houdayer_every` enabled. **If any of the three fixes
lets Houdayer accept a strict positive joint-delta swap, that's the
crack in the wall.**

### X1 — 22-color Potts on 2D lattice — RETURN (08:14 CEST)

**Best two cross-domain bets (per agent):**

1. **Houdayer-style cluster moves adapted to the alldiff-constrained
   Potts ferromagnet.** Maintain two near-453 replicas A, B; define
   overlap field q_i = δ(σ_i^A, σ_i^B); identify connected components
   of the disagreement set D on the 16×16 grid; for each component
   apply the piece-permutation cycle that swaps A↔B labels on D
   while preserving alldiff (automatic because both replicas are
   permutations of the same bag). Energy inside D is *exchanged*;
   only boundary energy of D pays a cost.

   **Why it's the right tool for our moat**: documented mechanism for
   exactly the moat-depth-≥k pathology we observe (Zhu/Ochoa/
   Katzgraber arXiv:1501.05630; Fang/Wang 2023 on 10-state Potts;
   Mohseni et al. arXiv:2204.04897 "isoenergetic cluster" revival;
   Fang/Wang on disordered Potts arXiv:2310.02216). The alldiff that
   killed BP/SP is *automatically respected* because D has identical
   multiset content in both replicas.

   **Implementation**: ~400 LOC Rust on top of solver-engine. Replica
   pair maintenance, union-find for D-components, cycle extractor
   (just the bijection induced by position-matching two replicas
   restricted to D). 2 CPU-days for ~10^7 cluster-move pairs from
   ~50 diverse 449-453 replicas.

   **Falsification test**: histogram D-component sizes on a known
   (453, 451) replica pair. If bimodal with heavy tail above 10
   sites, abort. If median 3-8 sites, proceed.

   **Agent P(454+ in 7 days)**: 20-30%. Per [[feedback-no-self-time-
   estimates]] this is the AGENT'S estimate; verify by running.

2. **Lattice-gauge disclination strings (Z_22 plaquette charges).**
   Treat each interior vertex of the 16×16 board as a Z_22 plaquette;
   the 4 colors meeting at the vertex sum mod 22 to a topological
   charge c_v ∈ Z_22. Perfect solution has c_v = 0 everywhere; the
   453 state has 27 nonzero charges. Find pairs of opposite-charge
   vertices and apply min-cost-flow on a piece-swap graph to "transport"
   the charge to annihilate with its partner — fixing O(path-length)
   mismatches at cost of O(1) boundary mismatches.

   **Why it's genuinely new**: mismatched edges are not independent —
   they are bound in vertex-charge pairs. A standard local move tries
   to fix one edge and breaks 1-3 others (Peierls-barrier ≈ moat-
   depth-5). A string transports the charge, escaping the barrier.
   Reference: Kogut lattice gauge; Zohar et al. arXiv:2312.14640 on
   Z_N gauge ground states.

   **Implementation**: ~700 LOC, includes a min-cost-flow over a
   piece-rotation graph. 3-5 CPU-days.

   **Falsification test**: histogram c_v over 100 known 453 states.
   If charges are randomly distributed (no spatial clustering of
   opposite pairs), abort. If ≥30% of opposite-charge pairs are
   within Manhattan distance ≤6, proceed.

   **Agent P(454+ in 7 days)**: 10-15%.

**Things X1 explicitly ruled out** (as morally equivalent to already-
tried methods):
- Population annealing, Wang-Landau, simulated bifurcation — reduce
  to PT-equivalents on the alldiff manifold.
- Quantum-inspired Coherent Ising Machines — alldiff destroys the
  continuous relaxation.

**Vol-7 reading of X1**: Houdayer-cluster on the alldiff-Potts
manifold is the strongest candidate. The mechanism matches the
exact pathology (moat-depth-≥5 + alldiff rigidity) and it has not
been published on edge-matching. The disclination-strings idea is
*also* striking because it gives us a new, computable structural
invariant: the 27 c_v charges of the 453 board are a fingerprint
nobody has computed.

**Immediate cheap pre-experiment** (vol-7 candidate): compute the
Z_22 vertex-charge distribution on the 453 board. ~30 min Python
work. If charges cluster spatially (which they should, per the
strain-cascade hypothesis), the disclination move is viable. If
they're uniform, abort that branch. Either way, the *charge
fingerprint* is a publishable structural signature.

### M1 — Monckton design philosophy — RETURN (08:24 CEST)

**Headline**: *Monckton himself contributed nothing structural.*
Classics graduate, journalist, no mathematics. The Eternity II
piece set was *generated by Alex Selby and Oliver Riordan* (hired
by Monckton in 2005), the *same pair* who solved Eternity I in 2000.
Their generator was built specifically to defeat their own E1
solver. The lever is in their generator's bias choices, **not** in
Monckton's quotes.

Cited (agent-quoted):

- Wikipedia: *"Eternity II was designed by Monckton in 2005, in
  collaboration with Selby and Riordan, who designed a computer
  program that generated the final Eternity II design."*
- Riordan on Monckton: *"He wasn't looking at it in a mathematical
  way at all"* — plus.maths.org "Forever rich".
- £1M Eternity I "I had to sell my mansion" was a deliberate PR
  stunt, admitted by Monckton in 2006. *Public-facing claims are
  marketing artifacts, not technical statements.*

**Structural information M1 did surface from third parties**:

- 22 colors + gray. **5 colors used only on border/corner inward-
  facing edges; 17 colors used only on inner edges.** This bipartite
  color split is what our rare-vs-abundant inversion (vol-5) already
  exploits — *but it's a published fact, not our discovery*. Update
  [[project-e2-state]] to credit the community.
- 1 fixed starter piece (piece 139 at I8 ≈ row 8 col 7) + 4
  retrievable via "Clue Puzzles 1-4" (two 6×6 and two 12×6 sub-
  puzzles). The rule book says **the puzzle can be solved without
  using the hints**. This is the canonical 5-clue, but the "1-clue"
  community variant is just "use only piece 139" — community-defined.
- **No Monckton patent on E2 construction was found.** Defensive IP
  is trademark/copyright. No public construction recipe.

**Falsifiable Selby-Riordan-generator hypotheses (M1's H1-H4)**:

1. **H1 (Generator signature in color statistics).** Compute color-
   imbalance N/S vs E/W per color; compute chi-square fit of color
   counts. A uniform random generator gives random variance; a
   Selby-Riordan adversarial generator likely *maximized minimum
   local entropy* → variance below random expectation. **Cheap test
   (~30 min Python).**
2. **H2 (Hint positions forbid all 8 dihedral symmetries).** Test
   if the 5 hint set is fixed by no nontrivial element of D4. If
   yes, no symmetry reduction. We already know the (7,8) hint
   breaks 180; need to check the other 6 dihedral elements.
3. **H3 (Generator anti-Wang-tile).** Selby/Riordan exploited 2×3
   plateau structure in E1; for E2 they likely maximized min-cut on
   every 6×6 sub-window. Test: enumerate 11×11 sub-windows × 6×6,
   check min-cut-color-flow distribution flatness.
4. **H4 (Frame uniqueness count).** Count distinct frame solutions
   for E2. If O(10^5) vs random O(10^8) → generator bias toward
   frame-uniqueness → frame-first is either the right angle or
   exactly the wrong one.

**Algorithmic implication**: search *generator space*, not *board
space*. Train a classifier to distinguish official E2 piece-sets
from uniform random 256-tile sets on statistical features (color-
pair co-occurrence, frame-color budget, parity); >80% accuracy
features ARE the bias and can be added as propagators. This is
genuinely orthogonal to every solver in the academic record.

**Most actionable next step from M1**: read Selby & Riordan's
published E1 method (archduke.org/eternity/), because *whatever
they built to defeat in E1 is, by negation, what they made E2
resistant to*. Inversion is testable code.

### F1 — community / forum SOTA — RETURN (08:25 CEST)

**Headline**: *The hobbyist record on the canonical 5-clue is
**Louis Verhaard's 467/480 (Dec 2008)**, not 470.* The 470 number
that has been floating around (libblackwood / Blackwood) is on the
**1-clue / clueless variant** (default puzzle in libblackwood's
`data/__init__.py` is `E2ncud` = "E2 no clue, upside-down"). This
**confirms** [[reference-blackwood-decoded]] and resolves any
ambiguity.

| Score | Variant | Claimant | Date | Algorithm |
|---|---|---|---|---|
| **467/480** | **5-clue (canonical)** | Louis Verhaard | 2008-12 | "eii" distributed backtracker + useless/precious piece tiering |
| 466/480 | 5-clue | "eii" users | 2008 | same; ~100 found before 1st 467 |
| 463/480 | 5-clue | Verhaard pre-tiering | 2008 | early eii |
| 470/471 | 1-clue clueless | Joshua Blackwood / jfbucas | 2020-24 | scheduled "conflicts allowed" relaxations + motif demand |
| 459/480 | 5-clue | Wauters TS / Salassa | 2012/2017 | published |

**No verified hobbyist claim above 467 on 5-clue.**

**Two techniques NOT in academic literature** (high confidence):

1. **Verhaard's 2×3-tileability piece valuation.** For each piece,
   count how many distinct 2×3 sub-arrangements it appears in
   across all enumerations. Bucket pieces into
   `{useless, bad, good, precious}`. Then apply **depth-banded
   admission**: forbid `good` pieces before depth 63; cap `good`
   at 6 by depth 79; place all `useless` by depth 96. This is a
   *temporal* variable-order rule, not a static one. Source:
   shortestpath.se/eii/eii_details.html.

2. **Blackwood's "scheduled conflicts_allowed".** Specific backtrack
   depths (e.g. `[206, 211, 216, 221, 225, 229, 233, 237, 239]` in
   `jb471.py`) where the solver is *permitted to leave one mismatch
   and continue*. Combined with **Blackwood's "heuristic_patterns_count"
   demand curve** (piecewise-linear depth → minimum required count
   of a motif-triple). This is the formal version of "10 scheduled
   relaxations". Source: github.com/jfbucas/libblackwood/scenarios/.

**Empirical: Verhaard 467 occurred 2× more rarely than predicted by
his statistical model from 466 frequency** — he hypothesised a
structural barrier (possibly color parity) at 467→468 on 5-clue.
This matches our vol-5/6 finding of "30-mismatch budget", just
shifted: at the 466/467 plateau there is *another* barrier above.

**Verhaard's "X method"** thread on groups.io (link in agent output)
is paywalled — would need email subscription to access.

**Implication for vol-7**: H1+H2 are concrete builds. **Replace
MRV variable-ordering with 2×3-tileability ranking + depth-banded
admission + scheduled motif-count demand propagator.** This goes
into `propagators` crate. Estimated 1-2 days Rust. Predicted gain:
**reach 460+ regime, plausibly 463-467 (matching Verhaard)**.

The negative-result F1 surfaced: **groups.io is paywalled to
scrapers; r/Eternity2 is empty of verified > 467 claims**. The
community ceiling has held >10 years at 467 on 5-clue. That
congruence with the academic 458 ceiling is itself evidence of a
real structural barrier.

### Three-agent triangulation (08:26 CEST)

- **M1** (negative on Monckton, positive on Selby-Riordan): the
  generator bias is the unstudied lever.
- **F1** (Verhaard 467 ceiling, 2×3 tileability + depth-banded
  admission folklore): an unported piece-valuation algorithm
  exists and stops at 467.
- **X1** (Houdayer cluster move on alldiff-Potts): the move class
  matches the moat-depth-≥5 pathology — *and we already wrote it,
  just never fixed the replica-exchange revert bug*.

All three converge on **one missing observation: structural
information about the PIECE SET that none of our solvers consume.**

- Selby-Riordan generator → piece statistics are non-uniform.
- Verhaard 2×3 tileability → some pieces are intrinsically harder
  to place than others.
- Houdayer disagreement → the structural component of the moat is
  *which pieces are interchangeable across basins*.

This is the synthesis: **piece-level structure is the unmodelled
axis**. All our methods treat the 256 pieces as a uniform bag with
hard alldiff. None of them weight pieces by their structural role.

### 08:00 CEST — session start, parallel agents queued

Three research agents dispatched in parallel (M1 = Monckton, F1 =
forum/community, X1 = 22-color Potts/lattice defects). Each scoped
to 600-900 words, background, so vol-7's main thread can synthesise
while they run.

While they run, vol-7 main will:

1. Re-skim vol-5's bottom half (~lines 1200-1782) for any
   pattern that didn't surface from the synthesis — done.
2. Read NIGHT5_NEXT_DAY for the morning-Claude playbook — done.
3. Choose 1-2 cross-domain angles X1/M1/F1 surface for deeper work.
4. Begin building an outer-configuration search that uses the
   inner-optimality oracle (vol-6's k≤5 EvalMaxSAT) — this is the
   one genuinely new algorithmic class implied by vol-6 but not yet
   built: enumerate small perturbations of the 453's outer, solve
   each one's inner via MaxSAT to optimum, pick the best.
