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

## (entries follow as experiments run)
