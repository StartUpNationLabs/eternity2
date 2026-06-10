---
name: cloister-ii-border-anchored
description: "CLOISTER-II (vol-212) — border-anchored break-DFS: fix a perfect 60-piece frame, search the 14×14 interior with the 56 IB edges as real constraints from cell 1 (break-payable), exact endgames scoring rim sides, 5/5 hints forced. Collects the ~14-edge rim-compatibility value vol-211 proved uncollectable post-hoc (IB realized 48-50 vs 34-39). Strict-track record condition: total = 480 − breaks ≥ 461 with 5/5 hints."
status: built
metadata:
  type: concept
---

# CLOISTER-II — border-anchored break-DFS (vol-212)

**Origin**: vol-212 (2026-06-10), forced by the vol-211 ★ rim-compatibility
result ([[cloister-standalone-interior]]): equal-II interiors differ by ~14
attachable IB depending on whether they were grown inside a border, and the
property is NOT retrofittable. ⇒ the border must constrain the interior
DURING construction. The community strict-460s are this architecture
without break scheduling or exact endgames.

**Files**: `crates/cloister/` (`eternity2-cloister`): `frame.rs` (ring →
per-cell rim targets), `dfs.rs` (break-DFS with `Fixed` rim constraints,
gates, hint machinery, row/boustro scans, optional LDS bound), `endgame.rs`
(1-row + 2-row exact tails scoring rim sides, forced-cell aware), `sa.rs`
(II+IB annealer), `border.rs` (attach MIP), `verify.rs`. Bins `cloister2`
(`--frame <file|dir>`), `attach2`. Campaign driver
`scripts/v212_cloister2/campaign.sh`.

## Definition

Fix a FRAME = legal assignment of the 60 border pieces to the ring
(BB ≤ 60 known, prefer 60). Each interior cell gains fixed color targets on
its rim-facing sides (56 targets total). The interior break-DFS treats
those targets as constraints identical to placed-neighbor edges: cost-0
candidates match all constraints; break candidates (gated by the schedule)
violate exactly one; exact tails count target mismatches in their
objective. Complete board score = II + IB + BB(frame) = 480 − breaks for a
perfect frame. **Strict record condition: breaks ≤ 19 with 5/5 hints.**

## Vol-212 measurements (30 s × 8 seeds unless noted; strict460a frame)

| quantity | value |
|---|---|
| bordered perfect wall (II+IB, no breaks) | 152-155, median 153 (3 frames) — vs 174 free-rim |
| reach per break | ≈ 2.5 cells ⇒ ≥ 12 breaks to reach the 1-row trigger (182) |
| unhinted, breaks 12 gates 130-190 + et14 | totals **450/451/453**, II 340-345, **IB 47-50** |
| break-budget economics (30 s) | 12 → 453 max; 16 → 449; 19 → 447; 24 → 442 (tight budgets dominate; loose budgets flood the anytime-min) |
| hinted, breaks 12-14 + et14 | 0-1/8 complete (depth wall 180-181 vs trigger 182); the single completion: **447, 5/5** |
| hinted, breaks 8 + tail2 (trigger 168) | **8/8 complete, 445/445/446, all 5/5** |
| tail2polish post-hoc on T453 | null at 500M nodes (tail 20 unimproved) |

Key facts established:

1. ★ **The rim-compatibility value is collected**: border-anchored
   construction realizes IB 47-50 immediately; every vol-211 post-hoc
   attach capped at 34-39. The strict-460s sit at IB=50.
2. **et14 is structurally required** bordered (et8's trigger 188 is
   unreachable; the bottom row's S-targets also belong inside the exact
   tail). Hinted, **tail2 (trigger 168) inverts the vol-211 refutation**:
   the 28-cell column-pair tail absorbs both deep hints (row 12) and is
   the reliable 5/5 recipe.
3. **Frame hint-compatibility is a hard constraint**: the Bucas-469
   (1-clue-era) frame jams ALL hinted seeds at depth 13 — row-1 hints'
   pre-filters conflict with its top inward colors. Cheap probe: 6 s
   hinted run, jam at depth < 20 ⇒ incompatible.
4. Witness bound: frame strict460a provably admits II+IB = 400 with 5/5
   (the community board). Our 30 s search reaches 386 on it — the gap is
   search, not frame, on that frame; whether another frame admits ≥ 401
   is the campaign's open question.

## What's open

- 300 s anytime curves (in flight at write time), SA/hybrid polish delta,
  in-DFS tail2 node-cap sweep (30k → 100k+), LDS + boustro probes.
- Frame breadth: compat-probe vol-76 corpus + decoded community frames;
  per-frame total distributions; fat-tail hunting.
- Frame generation beyond corpora: attach MIP (`--require-bb60`) on our
  best hinted interiors as a frame sampler.

## Linked

- [[cloister-standalone-interior]] — vol-211: the rim result + free-rim records
- [[blackwood-algorithm]] — the community border-first lineage
- [[vol-212]] — session journal (engineering details: bitset candidates
  refuted 0.64×, list engine 0.94× of vol-211 with full generality)
