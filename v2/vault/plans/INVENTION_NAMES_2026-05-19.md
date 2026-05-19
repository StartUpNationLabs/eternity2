# Invention Names Reserved — 2026-05-19

User directive (2026-05-19 evening, mid-V148-kill): **"those allowing
to build better puzzle from scratch faster feels good"**.

This is a preference signal: favor **constructive-from-scratch**
inventions over basin-attack / local-repair. I.e., algorithms that
build a high-quality board starting from no committed pieces.

## The 6 proposed (2026-05-19 18:30 CEST)

Numbered for vol-assignment. Marked **[from-scratch]** if user's
preference applies.

### 1. STRATUM — Layered-Algebra Decomposition  **[from-scratch]**
Pieces decompose into algebraic strata under color-permutation orbits
of the Selby-Riordan generator. Place stratum-equivalence classes
first, then refine within each class. Representation-theoretic search
on the piece set.
- PoC: 1 day to compute orbits + measure if 463/469 boards respect
  stratum structure (= they should if the generator left a fingerprint).
- Vol: 149 if pursued.

### 2. CHIASMUS — Two-Solver Mutual Refinement
Coupled fixed-point search between edge-strict DFS (vanilla_fast 85M
nps) and edge-loose ALNS. Different failure modes → mutual hints
unstick each other.
- PoC: 1-2 days for the message bus.
- Vol: 150 if pursued.

### 3. CIPHER — Score-Difference Cryptanalysis
Treat matched-edges f(board) as a hash; the 459/463/469 ceiling as
"near-collisions". Differential cryptanalysis: identify bit-flips
(piece swaps) that push f the most, build differential trail from
460→480.
- PoC: 2 days.
- Vol: 151 if pursued.

### 4. OUTRIDER — Pre-Committed Trajectory Search
Search by **trajectory** — fix a planned 8-cell move-sequence first
(swap A↔B, swap C↔D, rotate E by 90°, ...), then check if ANY
anchoring of that sequence onto an existing board improves it.
Template-based search. Bypasses σ-cycle indecomposability because a
template can encode the σ-cycle itself.
- PoC: 3 days for template language + matcher.
- Vol: 152 if pursued.

### 5. ANNEAL-INVERSE — Run SA Backwards
Reverse-time SA: start from a putative 480 (constructed locally), run
SA "backwards" to generate the basin of attraction. Output is a
prediction for what kind of partial board would attract toward 480.
- PoC: 1 day prototype.
- Vol: 153 if pursued.

### 6. WEAVING — Co-Evolutionary Two-Coordinate Search  **[from-scratch]**
Row-orderings and column-orderings as separate populations evolving
under co-evolutionary GA where row-fitness depends on currently-best
column-population and vice versa (Lotka-Volterra on permutations).
- PoC: 2-3 days.
- Vol: 154 if pursued.

### 7. HARMONICS — Frequency-Domain Edge-Demand Matching  **[from-scratch]**
*Added 2026-05-19 evening after V150-V151 ceiling at 455.*

Reverses the V150/V151 approach. Instead of CELL-FIRST construction
(pick piece for each cell), do MATCH-FIRST: solve the global matching
problem on the demand graph (1024 piece-sides → 480 same-color pairs),
THEN embed the resulting piece-pairing graph onto the 16×16 grid.

- Stage 1: max-weight matching on demand graph. Polynomial.
- Stage 2: grid-graph isomorphism heuristic. NP-hard but constrained.

- PoC: 3-5 days.
- Vol: 152 (active 2026-05-19).

## User-preference re-ranking (2026-05-19 directive: from-scratch faster)

Top picks under the **from-scratch / build-faster** preference:

| Rank | Invention | Why fits the directive |
|------|-----------|------------------------|
| 1 | **STRATUM** | Stratum-first placement IS a from-scratch builder. If orbits exist, building stratum-by-stratum is faster than DFS by a known orbit-count factor. |
| 2 | **WEAVING** | Co-evolutionary row/col populations build a board from no committed pieces. Each generation IS a new from-scratch board. |
| 3 | **OUTRIDER** | Can be reframed as a from-scratch builder if templates are *generative* (each template = a partial-board schema). Slightly less direct than 1-2. |
| 4 | **CHIASMUS** | Couples two existing approaches; can run from scratch but is fundamentally a refinement architecture. |
| 5 | **CIPHER** | Trail-building requires a starting basin; not from-scratch. |
| 6 | **ANNEAL-INVERSE** | Inverts SA which presumes a starting target; not from-scratch. |

## Recommended next vol (under preference)

**Vol-149 = STRATUM** — fastest PoC (1 day), highest "from-scratch
build-faster" alignment, and the orbit-measurement is a stand-alone
publishable finding even if the algorithm doesn't lift the record.

## Linked

- [[MULTI_VOL_PLAN_2026-05-19]] (superseded for invention-mode vols)
- [[../sessions/vol-147]]
- [[../sessions/vol-148]] (sweep killed mid-launch per user invention pivot)
