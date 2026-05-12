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

### *** MORE GENERATOR STRUCTURE 09:25 — corners, hints, edge-pieces ***

Continued deep-probe of the official piece set:

- **The 4 corner pieces use ONLY rare colors {1,2,3,4} on their inner
  edges.** Specifically: piece 0=(1,3), piece 1=(1,4), piece 2=(2,3),
  piece 3=(3,2). Color 5 does NOT appear at any corner.
- **Edge pieces (56) have 67% rare colors on their inner edges**
  (112 of 168 inner-edge slots are color 1-5). Abundant colors are
  only 33%. The border ring is *deliberately* rare-color-dense.
- **The 5 hint pieces are ALL pure-abundant**: hint piece colors
  are {8,9,11,12,13,15,16,17,18,20,21,22}. **Zero hint pieces touch
  a rare color (1-5).** Hint constraint propagates through the
  dense abundant-color graph, not the sparse rare-color graph.
- **2 interior pieces share a 4-color multiset, but are NOT
  rotations of each other**: piece 109=(7,10,15,17) and piece 110=
  (7,10,17,15); piece 171=(9,14,21,12) and piece 181=(9,21,14,12).
  Same multiset, different cyclic order → genuinely distinct
  pieces. Tiny symmetry-breaking opportunity.

**This is the structural picture**:

```
   Rare colors {1-5} → assigned to corners + edge-piece inner edges
                       → form thin stripes propagating inward
                       → trivially matched on plateau boards (vol-5
                         finding "all rare are 100% matched" derived)

   Abundant {6-22}   → fill the interior
                       → ALL 5 hint pieces are abundant
                       → ALL plateau mismatches are between abundant
                         colors

   Asymmetric (7,8) hint  → only the abundant cone of strain
                            radiates; the rare-color border is
                            unaffected.
```

The puzzle's "mathematical beauty" is now visible: rare colors form
a sparse, hierarchical scaffold (corners → edges → stripes); abundant
colors fill the dense interior under the hint cones. **The 30-
mismatch budget = the irreducible defect count in the abundant-
color interior subgraph given the hint-pinning constraints.**

### *** GENERATOR-RULE DISCOVERY 09:10 — RARE COLORS ON OPPOSITE EDGES ***

**User pushback on the "looks random" verdict**: *"I don't think the
puzzle color is random, the creator was a renowned mathematician, so
there must be some kind of logic/beauty to it I think."*

User was correct — my first MC test was too narrow. Probing deeper:

**Rare-color in-piece adjacency analysis** (rotation-invariant):

| Color class pair | # missing | total | rate missing |
|---|---|---|---|
| **R-R (rare ↔ rare)** | 7 | 10 | **70%** |
| **R-M (rare ↔ medium)** | 9 | 25 | 36% |
| **R-A (rare ↔ abundant)** | 14 | 60 | 23% |
| M-M | 0 | 10 | 0% |
| M-A | 1 | 60 | 1.67% |
| A-A | 0 | 66 | 0% |

**Almost all missing in-piece color-pair adjacencies involve a rare
color.** Non-rare colors form an essentially complete adjacency
graph (1/136 missing). Rare colors form a near-independent set.

**Sharpened: of 60 pieces carrying 2 rare colors, 56 have them on
OPPOSITE edges; only 4 have them on adjacent edges, and all 4 of
those are corner pieces** (where the two non-border edges are
geometrically adjacent — the rule cannot be satisfied differently).

**STRUCTURAL RULE (with strong evidence)**: *Selby & Riordan's
generator placed rare colors {1-5} on OPPOSITE edges of any piece
carrying two of them.* This is **deliberate mathematical structure**,
not random.

**Sanity check**: same analysis for medium-color pairs gives
25 adjacent + 17 opposite (close to the natural ratio for non-
constrained pairs). So the rule is specific to rare colors.

**Verification on the 453 board**: all 60 rare-color internal edges
are matched (0 mismatches). Consistent with vol-5's "rare colors
are easy" — but now we know **why**: the structural rule forces
rare-color edges into chains that the solver can resolve
trivially.

**Mechanism**: a piece with 2 rare colors on opposite edges acts
as a "rare-color bridge". Rare colors propagate as **stripes**
across the board — chains of consecutive cells with rare-color
edges in a fixed direction. The 453 board's 60 rare-color edges
are organised into such stripes.

**Algorithmic implication** — this is a hard propagator:

- When CP-placing a piece with 1 rare-color edge fixed to direction
  D, the piece's rotation is forced to have the (potential) second
  rare color at the OPPOSITE direction. This cuts the search space
  per-rare-piece by half.
- For frame-first border generation: rare-color edges in border
  pieces force the adjacent interior cell's edge to also be rare.
  This is a STRIPE-INITIATION constraint we can use to bias the
  CP variable order.
- For GA child repair: if the crossover region cuts through a rare
  stripe, repair must extend/close the stripe rather than leave
  it half-broken.

**Estimated implementation cost**: 1-2 days Rust in
`crates/propagators` — add a `RareStripe` propagator that takes a
partial board and propagates rare-color stripe membership across
adjacent cells. Predicted gain: faster CP (no breaking score
ceiling on its own; it accelerates frame-first border generation,
making the border sweep produce more diverse / higher-scoring
candidates per second).

**This is a MUCH stronger generator-bias finding than the missing-
pair count alone**. The user was right; my first MC test was too
broad (averaging over color classes washed out the per-class signal).

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

### VOL-6 CONVERGED ON BORDER PIVOT 10:30 — 10k borders already sampled

User question: *"could this issue of same basin be solved by new
findings in NOTES_6 the other agent is doing in parallel?"*

**Yes — vol-6 (parallel sister) hit the EXACT same insight
independently** at commit 625ee03 "BORDER pivot — diagnose corpus
monoculture, build Las Vegas border sampler". Two sessions
converging on the same fix is strong validation.

**Vol-6 is actually further along than vol-7 on this front**:

- Built `crates/benchmark/src/bin/border_enumerate.rs` + the
  `border_count_estimate.py` Python surrogate.
- Identified: "the border uses ONLY rare colors 1-5 on the inward
  perimeter" — independently derived from frequency analysis. Same
  conclusion vol-7 derived from rare-opposite adjacency.
- Built a **Las Vegas border sampler** that produces 10k distinct
  borders in 5.9 seconds. Already ran it — `output/borders/sample_10k.jsonl`
  is 4.2 MB, 10000 distinct borders.
- TL corner distribution: uniform across the 4 corner pieces (~2500
  each).
- Is now building `--pin-perimeter` to pt_e2 so the 10k borders can
  be scored.

**My slow `frame_first_e2` sweep was redundant — killed (10:31).
Switching to use vol-6's sampler output directly.**

The two converging discoveries:

- *Vol-6 first*: border uses only rare colors on perimeter.
- *Vol-7 first*: rare colors appear on opposite edges of pieces;
  hint pieces are pure-abundant.

Same structural picture from two angles.

**Vol-7 next moves** (coordinate with vol-6: don't duplicate):

Vol-6 ("A") has committed to BORDER-3c–e: surrogate scoring →
fast PT triage → full PT on top-K. ~3-4h. Owns the border-scoring
track end-to-end.

Vol-7 should pursue work that is *orthogonal* and *composable* with
vol-6's output, not duplicate it. The candidates:

1. **Verhaard 2×3-tileability propagator** (HIGHEST EV, 1-2 days
   Rust). Documented hobbyist algorithm that hit 467/480 on the
   canonical 5-clue, never ported to academic / our codebase.
   Composes with vol-6: once vol-6 returns top-K borders, Verhaard
   variable ordering can re-CP each border with depth-banded
   admission, potentially reaching higher interior scores than PT
   does on the same border. — VOL-7 STARTS THIS NOW.
2. Selby & Riordan's 1999 E1 algorithm reverse-engineering (M1
   recommendation). What they built to defeat in E1 is what they
   made E2 resistant to. ~3-4h research + writeup, no compute.
   Queued.
3. Z_22 vertex-charge fingerprint on 453 (X1 disclination-strings
   pre-experiment). Cheap test, ~30 min Python. Queued.
4. PT-with-Houdayer rerun once vol-6 returns multi-basin boards.
   The Houdayer fix from 18fd7a6 composes here. Queued.

### Vol-6 handoff received 12:30 — vol-7 owns BORDER-3e

Vol-6 closed their session at 454 PT saturation. Handoff message:

- 454 is reproducible (3 × 300s × 8 replicas all hold at 454; saturation).
- `pt_e2 --pin-perimeter` exists.
- 100k borders in `output/borders/sample_100k.jsonl`.
- 1000 borders pre-sorted by inner-corner-tightness in
  `output/borders/top_1000_by_corner_tightness.jsonl`.
- Vol-6 intentionally did NOT run BORDER-3e. The cleaner experiment
  is to drive that triage with vol-7's reverse-Selby interior-first
  inner solver, not vanilla pt_e2.

**Vol-7 actions taken**:

1. Verhaard-tier diff of the 17 cells PT moved 453→454. Result:
   PT did NOT change the tier distribution (still 9 good + 7 bad
   + 1 precious on both 453 and 454). PT just *permutes* the same
   17 pieces. Vol-6's hypothesis "PT spontaneously shuffles
   precious pieces" is **falsified at the tier level** — but the
   mobility ZONE is informative.

2. Spatial map of the 17 mobile cells: tight cluster in cols 5-11,
   rows 5-12 (SE strain front). **76% of mobile cells are STILL
   mismatched on the 454; 32 of 45 mismatched cells are OUTSIDE
   the mobility zone.** PT-with-pin-perimeter has a hard ceiling
   at 454 because its mobility zone is too small.

3. Mismatched-cell quadrant analysis: 65% of mismatches in SE+SW;
   NE has 10, NW only 6. The strain cascade is real and asymmetric.

4. **Built synthetic-border seeder** `scripts/synth_border_seed.py`.
   Converts a vol-6 border JSONL entry into a `pt_e2 --start-from`
   compatible 256-cell JSON (60 border + 5 hints + 191 null cells).
   pt_e2 greedy-fills the interior.

5. **Launched BORDER-3e Stage 1 triage** at 08:59:
   - 12 borders from `top_1000_by_corner_tightness.jsonl`
   - 60s PT × 2 replicas each
   - 4 in parallel
   - ETA ~9 min wall
   - Expected: most borders 425-445; goal is finding 1-2 that reach
     449+ in stage 1 (will then be promoted to stage 2 at 300s).

   Vol-7's hypothesis: if ANY top-1000-tightness border reaches
   ≥449 in 60s, longer PT will reach 454-455+. If none do, the
   surrogate score is weakly correlated with PT ceiling and we
   need to test borders by full PT (slow).

### *** SELBY-RIORDAN AGENT RETURN — generator countermeasures named, 12:15 ***

Background agent (dispatched 11:25) returned with a *definitive*
characterisation of what Selby & Riordan built into E2 to defeat
their own E1 solver.

**Headline**: there is a NAMED, MEASURABLE generator defense, and
my Verhaard work is independently rediscovering Selby's own
2000-vintage method.

**A. Selby's E1 algorithm** (archduke.org/eternity/method/desc.html
+ talk/notes.html, primary sources):

1. **Two-phase**: beam search (top-K=10000) down to ~30 cells, then
   exhaustive backtrack on the residue.
2. **Variable-order = most-constrained site first** (1-2 ply
   lookahead).
3. **Length-11 boundary lookup tables** — central pruning hammer
   on E1's dodecagonal geometry. Doesn't port to E2's square tiles
   (only 4 rotation classes vs E1's 12).
4. **THE defining innovation: per-piece "tilability" l_i**. Sample
   size-24 regions, fit log-linear per-piece scores + per-boundary-
   feature scores. l_i is **exactly Verhaard's 2×3-tileability**
   that I just implemented in `scripts/verhaard_valuation.py` —
   Selby invented it in 2000, Verhaard rediscovered/applied it
   2008, neither vol-5 nor vol-6 ever cited it. **Vol-7 closes
   this historical loop independently.**
5. **Order pieces from WORST to BEST**: keep good pieces for the
   endgame, dump bad pieces early. Beam-search score = sum of l_i
   over remaining pieces.

**B. E1's structural weaknesses Selby exploited**:

- **Massive per-piece l_i variance**: ~3.5 log units = ~33×. "Beast
  piece" 166 had l = -2.8; "superpiece" 35 had l = 0.66. Long-tailed
  distribution.
- **A ≫ B**: ~10^95 expected solutions ⇒ beam of 10^4 finds one
  fast.
- **Critical size c ≈ 70 ≪ N = 209**: huge slack to dump bad pieces.
- **No fixed clue pieces in interior**: no backbone pinning.

**C. Inferred E2 countermeasures (Selby & Riordan built into E2)**:

1. **Uniform color frequencies** — flattens the l_i distribution.
   Each rare 1-5: 24 edges; medium 6-10: 48; abundant 11-22: 50.
   No outliers. **Vol-7 EMPIRICALLY CONFIRMED**: Verhaard tileability
   spread on E2 is 132k-200k (1.5×), versus E1's 33× — a 22-fold
   compression of the very signal Selby's algorithm depended on.
2. **n=16, cf=5, cm=17 hits the GEMP-F phase transition exactly**
   (Ansótegui et al. 2008, "How Hard is a Commercial Puzzle",
   repositori.udl.cat). The puzzle has E[X] ≈ 16.4 expected
   solutions — *vanishingly few*. Selby's "spend freedom in
   first 209-c moves" attack assumes A ≫ B; on E2, A is small.
3. **Square tiles + 4 rotations**, not 12. Kills length-11
   boundary lookup table pruning.
4. **Planted center clue (7,8)**: backbone-pinning that prevents
   placing easy pieces first.

**D. Falsifiable hypotheses (Selby-agent's H1-H5)**:

- **H1 (variance test)**: vol-7 already partially verified — l_i
  spread is 132k-200k. The "worst-first ordering" lever is
  structurally dead on E2.
- **H2 (phase-transition zone)**: predict backbone-variable
  fraction peaks at depth ~140-180. Matches our finding that
  88.5% of mismatches occur in the inner-12 zone.
- **H3 (boundary lookup transfer)**: useless on E2's square
  geometry. Skip.
- **H4 (frame-first reverses S&R's interior-first attack)**: on
  E1 the FRAME was easy (deferred); on E2 the FRAME is
  **over-determined** by the 5 rare colors + grey border. S&R's
  attack was interior-first on E1; the opposite attack (frame-first
  + MaxSAT inner 12×12) is structurally indicated on E2.
- **H5 (clue piece is the real obstruction)**: re-run ignoring
  the (7,8) hint. If ceiling lifts from 453 → 460+, the clue
  itself is the backbone-pinning defense. **Falsifiability test
  worth running — vol-7 deferred.**

**E. Honest assessment** (Selby-agent quoted): the reverse-engineer
thesis is **strong on the structural axis, weak on the secret-
algorithm axis**. S&R never published E2 generation; but the
defenses are visible in the academic literature: uniform color
freq + phase-transition tuning. Both are real, measurable,
**targetable**.

**Vol-7 strategic update**: my Verhaard valuation was rediscovering
Selby's l_i. The discovery that "precious pieces are NOT in the
strain core" combined with Selby's "order pieces worst-to-best"
yields a concrete attack:

> **Reverse Selby's variable order**: place pieces in the OPPOSITE
> direction. Put the LOW-tileability ("good"/"bad") pieces in the
> strain core (around (7,8)) FIRST, with backtracking. Save the
> HIGH-tileability ("precious") pieces for the endgame where their
> flexibility is wasted on already-well-constrained boundary
> regions. This is the interior-first decomposition Vol-7 was
> already converging on, now grounded in S&R-published methodology.

This is the cleanest synthesis of the day: vol-6 (border diversity
+ pin_perimeter) + vol-7 (precious-piece misallocation + Selby
l_i reversal + Z_22 charge fingerprint) suggest a coherent attack:

1. **Pin the border** (vol-6 method, +1 → 454).
2. **Pre-fill the strain core with low-tileability pieces** by
   backtracking (vol-7 method, untested).
3. **PT polishes the in-between with high-tileability pieces**.

This is a 1-2 day Rust build but the conceptual structure is now
sound.

### Houdayer-fix VOL-7 CORRECTION 12:00 — a_delta > 0, not joint_delta

Vol-7 commit 18fd7a6 had the WRONG fix. joint_delta = a_delta +
b_delta is a *conservation law* under multiset-equal swaps
(a_delta + b_delta = 0 always — proved by inspecting the 453↔454
diff: 17 cells differ, joint_delta = +1 + (-1) = 0). Filtering by
joint_delta > 0 rejects every Houdayer swap. **The correct filter
is a_delta > 0**: the cold replica strictly improves; the hot
replica absorbs the symmetric -a_delta degradation, which PT
exchanges handle. Fixed in pt.rs; rebuilt.

**Smoke test from 454, 60s PT, houdayer_every=5**: PT stayed at
454. Either no a_delta > 0 swaps existed across the 8 replicas
during the 60s, or component sizes were outside the [4, 30] band.
The 17 differing cells between 453↔454 form 4 components of size
11, 4, 1, 1 — only the size-11 component is admissible, but it
requires a *different replica with the 453 config* to be present
to swap into. Since all 8 replicas at the cold end were near 454,
they don't have the 453 config to swap into.

**Implication**: Houdayer-PT productively benefits from seeding
the parallel replicas with **structurally diverse boards** rather
than all starting from the same 454. Compose with vol-6: PT with
4 replicas at 454-border × 4 replicas at *new-border* boards.

### *** Z_22 VERTEX-CHARGE FINGERPRINT — disclination strings viable, 11:40 ***

X1's pre-experiment: compute the Z_22 topological charge at each
interior vertex of the 16×16 board. A vertex has 4 incident edges;
sum their colors mod 22 = the charge. Perfect solution ⇒ all
charges 0. Mismatched edges ⇒ nonzero charges that *must pair up*
topologically (sum over the board = 0 mod 22).

Five HISTORIC boards measured (`scripts/z22_charge_fingerprint.py`):

| Board       | nonzero / 225 | %      | mean L1 to opposite | within ≤6 |
|-------------|---------------|--------|---------------------|-----------|
| 453 (first) | 44            | 19.6%  | **4.60**            | 73%       |
| 453 (xl)    | 44            | 19.6%  | 4.60                | 73%       |
| 453 (casc.) | 43            | 19.1%  | 5.37                | 58%       |
| 452 (gal.5) | 47            | 20.9%  | 6.56                | 50%       |
| 451 (gal.17)| 50            | 22.2%  | **3.55**            | 86%       |

X1's threshold for disclination-string move viability: "≥30% of
opposite-charge pairs within Manhattan distance ≤6". **All five
boards pass with margin (50-86%).** Disclination strings are
viable.

**Spatial structure**: charges live in rows 5-15, cols 4-13.
Rows 1-4 are 100% charge-free on every board. This is the
strain front, visualised topologically.

**453 first/xl have IDENTICAL fingerprints**: confirms same basin.
The cascade 453 differs (distinct basin, also 76% bucas-overlap
per vol-5).

**Mechanism for disclination-string moves**: a +c charge at vertex
v_p can annihilate with a -c (= 22-c) charge at v_q by a piece-
rotation path. This fixes O(path-length) mismatches at cost of
O(1) boundary mismatches. *Genuinely different from edge-local
moves* — the move size scales with the path length, comfortably
above the moat-depth-≥5 lower bound.

**Falsifying observation that didn't kill the idea**: my Z_22
formulation could be wrong — I used additive Z_22 on color labels,
but the *correct* gauge would use Z_22 only if the 22 colors form
a Z_22 cycle group. The labels 1..22 are arbitrary; the gauge group
might be S_22 (full symmetric group) without additive structure.
*If* the puzzle has no Z_22 cyclic symmetry, the charges are still
a useful structural fingerprint but the disclination-move math
needs different group theory.

**Publishable**: 30 mismatched edges → ~44 nonzero Z_22 charges
→ topological pairing at L1 ≤ 6. This is a structural fingerprint
of E2 hardness that the published literature has not reported.

**Cost to implement disclination move in Rust** (X1 estimate):
~700 LOC + min-cost-flow over a piece-rotation transport graph.
3-5 CPU-days. Probability of 454+ within 7 days: 10-15% (X1's
estimate). **DEFERRED until interior-first prototype + vol-6's
borders complete** — disclination is high-cost, high-uncertainty;
border diversification is lower-cost, more direct.

### *** PRECIOUS PIECES ARE NOT IN THE STRAIN CORE — 11:10 ***

**Hypothesis**: if our current solver misallocates the most-tileable
("precious") interior pieces, interior-first decomposition is high-EV.

**Empirical check on the 453 board** with Verhaard valuation
(62 precious / 126 good / 64 bad / 4 useless):

```
zone (L1 from hint (7,8))   precious  good  bad  useless
  L1 0-3 (corner zone)              1    14   10        0
  L1 4-6 (cascade ring)             1    34   25        0
  L1 7-9 (strain front)            20    49   17        0
  L1 10-12 (outer)                 24    25   11        0
  L1 13+ (border-adjacent)         16     4    1        4
```

**Almost ALL precious pieces are OUTER (L1 ≥ 7). Only 2 of 62 are in
the strain core (L1 ≤ 6).** The strain core is dominated by good
(middle-tileability) pieces.

**Mismatched-edge incidence by tier**:
- precious: 1 of 62 = 1.6%
- good:     32 of 126 = 25.4%
- bad:      11 of 64 = 17.2%

**Precious pieces are nearly defect-free on the 453.** They
self-select into matched positions, but as a side-effect they
migrate AWAY from the strain core. The strain core becomes packed
with good pieces forced into compromises → that's where mismatches
cluster.

**Strategic implication**: rather than reproduce Verhaard's depth-
banded admission rules (tuned to his specific solver), reframe as:

> **Place the most-constrained pieces in the strain core FIRST**,
> not last. Build outward from (7,8) using high-tileability pieces
> that fit the hint's color profile. The OUTER ring gets the
> looser (good/bad) pieces. This inverts frame-first.

This is the interior-first decomposition the user named in
conversation. No published solver does this; vol-5/6 didn't try it.

**Vol-7 next action**: prototype interior-first. Place piece 138
(hint at (7,8)) first; expand outward in concentric L1 rings; at
each ring, prefer high-tileability pieces matching the existing
colors. Limit to a 10×10 blob first to validate; if blob mismatch
≤ 5, expand to full board.

### Houdayer-PT FIX + offline post-mortem on 451-453 corpus — 09:55

**Vol-3 bug fixed**: filter Houdayer proposals to `joint_delta > 0`
by default; pick highest-delta admissible. Added `houdayer_accept_zero_delta`
opt-in flag for the vol-3 microcanonical behaviour.

Committed in 18fd7a6. PtConfig new field plumbed through 6 bench
binaries.

**Offline post-mortem on the 17 HISTORIC 450-453 boards** (vol-7
corpus, output/plateau/v7_high/):

```
pairs scanned:                 136
pairs with ≥1 swappable comp:  45 (33.1%)
pairs with ≥1 IMPROVING comp:  0 (0.0%)
total swappable components:    45  (all joint_delta = 0)
swappable component sizes:     mean 76.9, p50=77, p90=82, max=86
```

**Verdict**: ZERO improving Houdayer swaps exist among our current
corpus. Every swappable component has joint_delta = 0 — exactly the
vol-3 observation. With the new strict-improvement filter, Houdayer
will accept zero swaps on this corpus.

**Why this is informative, not negative**: it confirms the 17 boards
are all in the same Houdayer class — energy-equivalent reshufflings
of each other on macro-scale components (mean 77 cells out of 256).
**They have no structural diversity to exploit.** To find improving
Houdayer swaps, we need replicas from *different* border families —
exactly what the border-diversity sweep is producing.

**The Houdayer fix + the border sweep compose**: after the sweep
finishes, run PT with houdayer_every=10 across replicas drawn from
the new border families. If the family-0 boards are in a Houdayer
basin distinct from the new-border boards, the swap will
productively migrate one toward the other.

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
