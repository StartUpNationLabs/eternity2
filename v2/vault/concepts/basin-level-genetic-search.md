# Basin-Level Genetic Search (BLGS) — vol-66 design

**Status**: `design` — vol-66 (2026-05-15).
**Type**: INVENTED ALGORITHM per user directive.
**Inventor**: this autonomous run.

## Audit-at-design

Codebase search (`grep -ri "genetic\|crossover\|GA\b" crates/`): no
genetic algorithms in our codebase. The standard E2 literature uses
GAs at the PIECE level (each gene = one piece-position-rotation
tuple). BLGS uses BASINS as the level of abstraction — each gene
is a SUB-REGION of a basin.

## Motivation

Vol-65 σ-orbit analysis (2026-05-15) showed:
- Same-score basins form GROUP ORBITS under σ-cycle permutations.
- Local 459 ↔ McGavin 469 σ-distance = 255 cells (indecomposable).
- Local 459 and McGavin 469 have 255/256 cells with DIFFERENT pieces.

Standard ALNS is single-basin and cannot bridge this gap. Standard
piece-level GAs would crossover INDIVIDUAL pieces, which violates
piece-uniqueness (can't have two of the same piece). Therefore
piece-level GA on E2 is awkward.

BLGS sidesteps both:
- Each "individual" in the GA population is a complete board.
- Crossover takes a SPATIAL REGION (e.g., shell-3 of board A) and
  COPIES it into board B, then repairs the rest via CP-MaxScore or
  ALNS to restore piece-uniqueness.

## The mechanism

```
def BLGS(initial_population_of_boards):
    pop = initial_population_of_boards
    for generation in iterations:
        # Selection: rank by matched-edge score
        pop.sort(key=lambda b: score(b), reverse=True)
        elites = pop[:k]
        # Crossover: produce offspring
        offspring = []
        for parent_a, parent_b in random_pairs(pop):
            # Pick a REGION to inherit from a
            region = random_region(parent_a)
            # Construct child:
            child = parent_b.copy()
            inherited_pieces = {parent_a.piece_at(c): c for c in region}
            # Place a's pieces in child at region cells
            for cell in region:
                child.place(cell, parent_a.piece_at(cell), parent_a.rotation_at(cell))
            # Now child may have duplicate pieces (where parent_a's
            # pieces also appeared in parent_b's non-region cells).
            # Resolve via CP-MaxScore or local repair (Hungarian).
            child = repair_duplicates(child)
            offspring.append(child)
        # Mutation: standard ALNS on each child
        offspring = [alns_step(c, budget=short) for c in offspring]
        pop = elites + offspring  # new population
```

## Key choices

### Region shape
- **Rectangular**: easiest. Pick a random rectangle in the board.
- **Shell-based**: e.g., "inherit shell-0/1 from parent A, rest from B."
  Aligns with the shell-decomposition finding (vol-65: defects are
  in shells 1-3 across all our records).
- **σ-cycle-aligned**: pick a region that's an entire σ-cycle of the
  parent A → parent B map. This preserves the cycle structure.
- **Component-driven**: pick a region around parent A's defect
  cluster.

### Duplicate repair
After crossover, the child usually has 5-30 duplicate pieces. Repair:
- **Hungarian matching**: re-assign duplicated pieces to alternative
  positions. Polynomial.
- **CP-MaxScore probe**: solve a small MIP to find the optimal
  re-arrangement given the inherited region as fixed.
- **Greedy swap**: replace duplicates with unused pieces from the
  puzzle's pool (those not in either parent's contributions).

### Crossover budget
Per child, a 100-cell region crossover + Hungarian repair is ~100ms.
At population size 16 and 8 offspring per generation, one generation
≈ 1 second. Over an hour: 3600 generations.

## Hypothesis

Standard ALNS explores one basin. BLGS explores N basins
simultaneously and cross-pollinates structural features. If the
"top half" geometry of McGavin 469 is good and the "bottom half"
geometry of our 459 is good, a BLGS crossover might combine them.

The σ-cycle indecomposability finding makes a SINGLE σ-cycle
import impossible (every cycle alone is negative). But BLGS does
something different: it imports a RECTANGULAR REGION (e.g., 50
cells in a 5×10 block), and the regions' boundary is FRESHLY
EXPOSED to the rest of the board — the rest can be CP-repaired
to fit. This is structurally different from σ-cycle import which
keeps everything outside the cycle exactly as it was.

## Initial population

The 4 known 458/459 records + McGavin 469. Add 5-10 more by running
the vol-61 pipeline with different corner perms / seeds, for a
starting population of ~15.

## Open questions

1. **Will Hungarian repair often fail?** If the inherited region's
   pieces have very different color-budgets from parent B's pieces
   in that region, Hungarian may not find a good assignment.
2. **Genetic drift**: after many generations, will the population
   collapse to one basin (loss of diversity)?
3. **Optimal crossover rate**: how big a region should we inherit?
4. **Multi-parent crossover**: instead of A's region + B's rest,
   use A's region + B's region + C's region + ... and CP-repair.

## Implementation plan (vol-66)

### Day 1
- Write BLGS prototype in Python: load population, crossover via
  region inheritance + Hungarian repair, score, iterate.

### Day 2
- Variants: rectangular, shell-based, component-driven regions.
- Measure: does any variant improve on the population's best score?

### Day 3
- Profile and port hot loops to Rust if Python is too slow.
- Run overnight (~12h) on initial population, see if 459 → 460+ emerges.

## Linked

- [[piece-side-matching]] (vol-65 PSM context)
- [[basin-permutation-group]] (vol-65 σ-orbit finding that motivates BLGS)
- [[../sessions/vol-65]]
- [[../plans/VOLS-62-70-ROADMAP.md]] (vol-66+)
- [[../plans/AUTONOMOUS-MONTH-PLAN.md]]
