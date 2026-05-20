---
name: three-milestones-from-veteran
description: "Vol-121 — three intermediate milestones identified by an Eternity II veteran researcher (years of work): (1) 471/480 matched-edges, (2) 231/258 linear placement adjacencies, (3) complete internal 14×14 no matter the border. These are different angles on the same problem. The 14×14 complete-interior decomposition is the structurally cleanest attack."
metadata:
  type: project
status: built
---

# Three veteran-suggested milestones (vol-121)

User shared three next-step milestones from a veteran E2 researcher.
All three are decompositions of the same record-breaking problem.

## Milestone 1: 471/480 matched-edges

McGavin 469 + 2. The smallest community-meaningful score improvement.

- Our gap from standing record (459): 12 edges.
- Mismatched-interior count at 471: 9 mismatch edges (vs McGavin's 11).
- Convention: matched-edges, doesn't require hint compliance (1-clue
  acceptable for community 471 record).

## Milestone 2: 231/258 linear placement

If 258 = total placement adjacencies in some counting convention,
231 = 89.5% matched in a **linear scan** sense.

- "Linear placement" suggests a CSP-depth / progress-along-scan metric.
- Distinct from complete-board matched-edges: this is a depth-class
  measurement.
- Our vol-12 / vol-14 work measures max CSP depth (~150-220 in our
  best pipelines). 231 may correspond to a deeper depth than we've
  consistently reached.
- **Diagnostic still needed**: at what CSP depth does our pipeline
  hit 231 matched adjacencies? Not previously measured directly.

## Milestone 3: complete internal 14×14 no matter the border

The structurally cleanest attack:
- Canonical 16×16 has 14×14 = 196 interior cells.
- Interior-touching edges: ~420 of 480 total.
- A 0-mismatch interior 14×14 would resolve ~420 edges deterministically.
- Add a separately-solved border (vol-44 LP-UB class A = 478) and total
  could reach 478+/480.

**This is what Blackwood's algorithm essentially does on the 1-clue
variant.** McGavin 469 ≈ near-complete interior + 11 mismatches all
in one cluster (vol-82 found this clustering).

### Why this is the right decomposition

- The border has 60 cells, well-understood (vol-44 border-class A/B/C
  enumeration).
- The interior has 196 cells, all the same "type" (no border edges).
- The two problems are **near-separable** if you allow B-I edges to
  be lossy.
- The standalone interior puzzle = a 14×14 E2-like puzzle with 22
  colors and 196 pieces. Significantly easier than the full 16×16.

### Mapping to our current state

Vol-4 [[frame-first]] explored border-first decomposition (basin-450).
Vol-44 [[lp-ub-478-basins]] characterized border classes. But neither
solved the STANDALONE INTERIOR.

The veteran's framing suggests vol-122+ should:
1. Take an existing 459 board (or any board).
2. Extract its 14×14 interior (196 cells).
3. Run a standalone interior MIP / CSP / ALNS that tries to PERFECT
   all 364 internal-internal adjacencies, ignoring border completely.
4. If solvable: score = 364 + (existing border match) + (B-I match
   on the surviving border). Could exceed 471.
5. If unsolvable: the obstruction IS the structural wall.

### Open questions

- What is the LP-UB on the standalone 14×14 interior, unconstrained
  by border?
- Is the interior puzzle PROVABLY solvable to all 364 internal edges?
  (Combinatorially possible per piece-edge counts; unknown if
  geometrically feasible.)
- How does our 30-board corpus compare in interior-only score?
  (Each board has some interior-matched count; this is the partial
  metric to track.)

## Tasks

Open as candidate items in [[BACKLOG]]:
- `interior-14x14-lp-ub` — compute LP UB for the standalone interior.
- `interior-14x14-mip` — vol-44-style MIP but restricted to interior.
- `interior-14x14-maxsat` — full MaxSAT enumeration on interior.
- `csp-depth-231` — measure CSP-depth required to reach 231 matched
  edges in our pipelines.

## Linked

- [[frame-first]]
- [[lp-ub-478-basins]]
- [[blackwood-algorithm]]
- [[basin-mcgavin-469]]
- [[vol-121]]
