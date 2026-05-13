---
tags: [concept, structural, trap]
status: built
origin-vol: 2
---

# Prefix determinism (the 449-plateau trap)

**Status**: KEY FINDING (vol-2)
**Origin**: vol-2
**Files**: vol-2 measurement scripts

## Statement

PT's canonical CP partial — the deterministic 449/480 prefix produced by standard cell-CP + AC-3 + gacolor with row-major scan — is **globally infeasible to extend past 449**.

Specifically: after CP fills the deterministic prefix, the remaining cells form a sub-CSP that is **provably unsolvable to 480** within local-CP repair of any reasonable budget. The 449 plateau is **upstream of SA**, not a local-search failure.

## How it was demonstrated (vol-2)

- Harvest plateau states (449/480) from PT.
- Try local CP region repair: keep prefix, re-solve any sub-rectangle.
- Result: **all attempts fail**. The deterministic border is inconsistent with any 480-feasible interior.

## Confirmations

- **Diverse-prefix harvest** (vol-2): random-shuffle CP gives 443-444 (lower than deterministic 449). The deterministic prefix is at least locally good but at a dead-end.
- **Consensus-seeding** (vol-2): seeding from consensus partials lands back in the 452-basin family.

## What broke the plateau

- **Vol-4 frame-first** (border-seed `0xCAFEFEEF`): different border ring → 450 (first +1 over 449).
- **Vol-5 GA-LARGE** (4×4-6×6 region crossover): 453.
- **Vol-6 pt_e2 --pin-perimeter** + corpus border + GA-cascade interior seed: 454 (warm-PT record).
- **Vol-15+ Blackwood schedule**: deliberately breaks exact-matching to find different deterministic prefixes.

## Implication for solver design

- **Don't trust the deterministic CP prefix as a "warm start".** It's a local trap.
- The 449 deterministic prefix is one of perhaps 3-4 dominant prefixes; the corpus border-monoculture finding (vol-6) confirms this.
- Diversification at the **prefix level** (border ring, hint-relaxed schedules, frame catalogues) is the lever, not diversification within ALNS repair.

## Linked concepts

- [[frame-first]] — vol-4 break
- [[border-diversity]] — vol-6 break
- [[blackwood-algorithm]] — vol-15 break (deliberate schedule)

## Linked memory

- `project_e2_state` (vol-2 row)
