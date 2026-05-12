# RESEARCH_NOTES_17_PLAN.md — vol-17 mission brief

Vol-17 opens after vol-16 closed with 21 commits, 4.6× engine throughput,
4.6× algorithmic win on `score_board`, and Cat-2 Stage A done. Vol-17
is back on **new algorithms, math, and research** — clean slate for ideas.

## Carry-over from vol-16

Hard-blocked items that vol-17 must land BEFORE anything else:

1. **Blackwood schedule calibration from community 469 boards.**
   Recipe in [[project-e2-vol15-blackwood-results]]. One afternoon.
   Unblocks Tier 1 (≥454 cold-start).
2. **SolveRequest schedule attachment.** Proto change so Blackwood
   profiles run server-side. Pairs with #1.

Plumbing/quality follow-ups (not blocking, do as time allows):

3. **Cat-2 Stage B**: trait + dyn dispatch per V2_DESIGN.md Option A.
   Long-tail refactor; ~6 hours coherent PR.
4. **Per-profile propagator unit tests** to catch the class of
   regression vol-16 Cat-2 introduced.
5. **AC-3 incremental count maintenance** — would skip the per-call
   rebuild loop. Mid-effort, ~5–10× joe_depth150 speedup potential.
6. **gacolor/multiset_equality precompute sweep** per vol-16 Cat-4f
   pattern.
7. **tonic 0.12 → 0.14 + prost 0.13 → 0.14** coordinated upgrade.

## Research direction: ideas to try

This is a brainstorm. Some are PoC-grade; some need theory work first.
Pick the highest-EV ones; some are wild and that's fine.

### A. Calibration-driven Blackwood (the safest T1 unlock)

**What:** Per the vol-15 recipe, mine the 1.2k Discord + 123 bucas-decoded
community boards for the empirical heuristic-color-prefix curve. Fit a
piecewise-linear schedule at the 25th percentile (conservative) and the
median. Run both as separate profiles.

**Why it works:** Vol-15's schedule was *scaled* from Blackwood's
self-reported numbers (his puzzle, not ours). The new curve is the
empirical truth from community 469s. Should match the constraint surface
the search actually sees.

**Effort:** half a day. **Expected:** cold-start ≥454, possibly ≥460.

### B. Houdayer-style cluster-relaxed warm-up

**What:** Verhaard / pt_e2's warm chains do single-piece swaps. Vol-14's
"443-board mismatch geometry" memo says all mismatches cluster in one
connected component. Instead of single-piece swaps, do **cluster swaps**:
identify a connected mismatch region, delete it whole, repair via CP from
a single-port boundary.

**Why it might work:** A k=5 ALNS repair can't escape a 62-cell defect
cluster (vol-14 finding). A whole-cluster repair operator with k =
cluster_size IS the operation that could.

**Effort:** 1–2 days. **Expected:** if it works, lifts post-PT score from
446/480 to ≥455 by escaping iso-score plateaus.

### C. Bipartite-matching gacolor v2

**What:** Current `gacolor_check` is a *necessary* condition (per-color
slack must be non-negative + even). The real feasibility test is a
bipartite matching: can the remaining edge-color supply actually be
distributed across the remaining slot-types? Use Hopcroft–Karp on the
color × side bipartite graph.

**Why it might work:** vol-11 BP measurements found the constraint surface
near full placement is sharp; current gacolor passes states that real
matching would reject. Catching them earlier prunes harder.

**Effort:** 3–5 days incl. theory writeup. **Expected:** 10–30% node
reduction on joe_depth150_bp.

### D. Zobrist hash for PT (already noted)

**What:** Maintain a 64-bit board fingerprint, XOR-updated on every
swap. Used by PT to detect chain stagnation (board repeats) without
recomputing the full board state.

**Why:** vol-14 `project_e2_vol14_pt_no_tabu` notes PT lacks tabu
mechanisms; this gives an O(1) tabu check.

**Effort:** half a day. **Expected:** small but reliable PT speedup;
clean implementation pattern.

### E. SAT-based corner ring enumeration (1-clue variant)

**What:** Blackwood reached 470 on the 1-clue variant. We could enumerate
ALL valid border rings via SAT, then for each ring, brute-force the
interior with our fast engine. The ring enumeration is small (~10⁴ rings
under symmetry); the interior brute force gets multi-core speedup
multiplied by the ring count.

**Why it might work:** Decouples the search into two independent stages.
The interior search has no border-edge uncertainty, simplifying the
domain dramatically.

**Effort:** 3–4 days. **Expected:** unknown — could be a dead end if
interior search per ring is still too expensive, or could be the bridge
to community-equivalent scores on the 1-clue variant.

### F. Quantum-inspired tensor network for partial board count

**What:** Vol-13 measured boundary-MPS gave Z* ≈ 7×10⁹³ overcounting by
10¹⁰¹. Piece-uniqueness was the binding rigidity. **New idea:** add
piece-uniqueness as a hard constraint via a *projected* MPS that zeros
out repeated piece IDs. The resulting tensor contraction would give a
tighter partition function estimate — useful as a heuristic value-order
or as a pre-search domain pruner.

**Why it might work:** PMPS (projected matrix product state) is a real
technique from condensed-matter physics; never tried on edge-matching
puzzles. Could give per-cell marginals that are tighter than BP's.

**Effort:** 1–2 weeks of theory + 3–5 days implementation. **Expected:**
publishable null OR breakthrough; high variance.

### G. Self-supervised piece-embedding (graph neural network)

**What:** Train a tiny GNN on the puzzle graph (nodes = pieces, edges =
"piece u edge-i matches piece v edge-j"). Use the learned embeddings as
a value-order heuristic. Trained on community 469 boards as positive
examples.

**Why it might work:** vol-14's edge-BP was a hand-crafted version of
this. A GNN could capture multi-hop compatibility patterns BP misses.

**Effort:** 2–3 days incl. data prep + training. **Expected:** could be
catastrophically worse (overfitting to community boards) or 5–10% node
reduction. Risk-on.

### H. Spectral cell-ordering (Fiedler-based)

**What:** The puzzle's cell-adjacency graph has a Fiedler vector
(2nd smallest Laplacian eigenvalue). Cells partition into halves; the
"hard" middle band is where the mismatch cluster lives (vol-14 finding).
Try ordering cells by Fiedler value — should reach the hard region in
mid-search, where the engine still has flexibility.

**Why it might work:** Vol-14 hint-centric was a hand-rolled version
of this and failed. But Fiedler is the principled answer to "which order
exposes the cluster soonest"; hint-centric used a wrong proxy.

**Effort:** 1 day. **Expected:** quick PoC, easy to refute or confirm.

### I. Constraint streaming via cooperative CP+SAT

**What:** Run the engine and a SAT encoding (we have sat-encoder!) in
parallel. Every k seconds, the engine streams its current best
no-goods (failed prefixes) into the SAT solver as clauses. SAT-derived
implied unit clauses stream back to the engine as domain prunes.

**Why it might work:** Best of both worlds. Engine is fast at local
inference; SAT is good at global learning. Vol-12's bitset engine doesn't
do nogood learning; SAT does.

**Effort:** 3–5 days. **Expected:** if the latency is right, could be
the structural fix for the depth-174 plateau.

### J. Energy-based pre-search via simulated annealing on the *piece set*

**What:** Verhaard's actual method (vol-7 memo). Instead of SA on
placements, SA on *which 180-190 inner pieces to commit to* — same as
Verhaard's outer phase. We have `solver-verhaard` as a skeleton; it never
got the SA component. Bring it in.

**Why it works:** Verhaard hit 467 in 2008 with this on a slower machine.
The technique is documented; we just need to ship it.

**Effort:** 2–3 days. **Expected:** stable 460–467 cold-start score IF the
phase-2 completion works. The phase-2 completion is the hard part.

## Suggested ordering

| order | idea | why first |
|---|---|---|
| 1 | A. Schedule calibration | unblocks T1, single afternoon |
| 2 | D. Zobrist for PT | small, clean, enables E better tabu |
| 3 | B. Cluster-swap ALNS | direct lever on the 446 → ≥455 gap |
| 4 | H. Fiedler ordering | quick PoC; refute or commit |
| 5 | C. Bipartite gacolor v2 | structural prune improvement |
| 6 | J. Verhaard set-SA | high-EV historical method |
| 7 | F. PMPS | wild card; publishable null OK |
| 8 | I. CP+SAT cooperative | infrastructure-heavy; later |
| 9 | E. Ring enumeration | only after 1-clue context is needed |
| 10 | G. GNN piece embedding | last; needs trained model |

## Bars for vol-17

| tier | requirement |
|---|---|
| T1 | Calibrated Blackwood schedule shipped + cold-start ≥454 |
| T2 | T1 + one new algorithm (B/C/H/J) shipped with measurement |
| T3 | T2 + measurable score improvement past 446 on canonical E2 |
| T4 | T3 + two new algorithms + a publishable result (T1 met OR a clean novel null) |

## Open questions for the user

(Not blocking — answer when convenient, or leave for the agent to choose.)

- Of the 10 ideas above, which appeal most? Anything missing?
- Are publishable nulls of equal value to score wins for vol-17, or
  should the session prioritize score?
- Is there appetite for the "wild" ideas (F, G, I) or focus on the
  proven-promising ones (A, B, J)?

## How to start vol-17

```
1. Read this file + project_e2_vol16_closeout.md + project_e2_vol15_blackwood_results.md
2. Pick one of A/B/D as the entry task.
3. For A: load community_corpus/ boards, build the curve, attach it to a new BLACKWOOD_CALIBRATED profile.
4. Measure on canonical E2 seed 1 with 5min CP + 5min ALNS.
5. Honest framing: if it doesn't lift past 416, publish the null.
```
