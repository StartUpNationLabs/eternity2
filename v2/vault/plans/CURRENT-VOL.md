# Current vol — vol-56 (queued, session-end disposition) — 2026-05-15

**Predecessor**: vol-55 shipped MVP B&P-and-cut and confirmed the 458
record is MIP-locally-optimal on 4 distinct cluster geometries.

## Session summary

Vols 54-55 shipped in the same autonomous session:
- vol-54 (math): resolved vol-50 vs vol-53 contradiction; established
  cell-fractional x as the precise gap mechanism via worked example +
  HiGHS verification.
- vol-55 (code): MVP B&P shipped today after user's "limiting thoughts"
  feedback. 458 confirmed MIP-locally-optimal on 4 cluster geometries
  beyond vol-44's single 196-cell test.

Standing 458 record unchanged but **its local-optimality is now much
more strongly established** than before this session.

## Vol-56 candidate directions (per audit-at-open at next-open)

After vol-55's local-optimality result, the path to >458 needs:
- A **different basin** (vol-22 basin-escape recipe direction).
- Or a **fundamentally different search algorithm** (CDCL no-good
  learning, neural MCTS, RL self-play — multi-week each).

Vol-55 confirmed that LP-tightening alone (the vol-44 → vol-52 → vol-54
arc) is NOT a record-track path. The LP gap is real but it's LP
looseness, not 458 suboptimality.

Active candidates for vol-56:

1. **Basin-finding lottery** — vol-22's basin-escape recipe at a budget
   we haven't tested (e.g., 30 different starting partials, ALNS-PT at
   30 min each). Goal: discover a basin with MIP > 458 *if one exists*.
   1-2 day compute, no novel algorithm. ~highest EV given vol-55's
   result.

2. **CDCL no-good learning in solver-engine** — multi-week build,
   genuinely new algorithm. Unclear EV but the only structurally novel
   path.

3. **rl-self-play-value-order** (BACKLOG since vol-30) — multi-week
   build + training compute. The only direction that could
   structurally beat vol-29's imitation ceiling.

## Audit-at-open compliance (when vol-56 opens)

Same set of aged-3+ items as vol-54 audit; vol-55 doesn't add new ones.
The `vol-52 design` page is now `refuted` not `unbuilt`, removing it
from the aged-unbuilt list.

## What is NOT changing

Standing 458 record. The vault now has stronger evidence for its local
optimality:
- vol-44: 196-cell whole-interior MIP at 1h compute.
- vol-55: 4 cluster geometries (3×3, 4×4, 5×4, 6×3) at 30s-90s each.

## Linked

- [[../sessions/vol-55]] — MVP result
- [[../sessions/vol-54]] — math foundation
- [[../concepts/y-linearisation-cell-fractional-gap]] — mechanism
- memory: `project_e2_vol55_local_optimality_multi_cluster.md`
