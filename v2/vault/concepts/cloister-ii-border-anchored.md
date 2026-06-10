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

## Saturation (vol-212 close — every lever measured)

| lever | result |
|---|---|
| compute (30→300 s) | +2.5 totals/decade ⇒ 461 needs ~10⁵× — ruled out alone |
| recipe shape (caps/budgets/boustro) | flat ±2 around 445-447 |
| naive LDS (max-disc 3/8) | REFUTED — depth 83-103, 0 completions |
| frame axis (24 probed; early-gate bypass) | only strict-460 frames pass gates ≥120; early gates (≤14) open 2/10 vol-76 frames at full strength; ALL completing frames land in one 444-449 band — no fat tail |
| SA polish (8×120 s from T449, rim-aware) | **null: all seeds return init exactly** — bordered-hinted basins are σ-locked like every high E2 board |
| tail2polish post-hoc | null at 500M nodes |

**v1 plateau: 449-strict (II 339 + IB 50 + BB 60) / 453-unhinted.** Gap
anatomy at IB≈50: II 339-345 vs the witness 350 (community 460 on the SAME
frame) — the bordered+hinted II search is the binding wall. We match the
460s' IB; we trail their II by ~11 at minutes-scale budgets.

## What's open (→ vol-213)

- Seam-scan CLOISTER-III: two-front growth meeting at an exact-closure
  middle seam (relocates tail damage to max-supply territory; the seam
  endgame is fully constrained on both sides).
- Assignment-relaxation value priors for the II side; frame_ub with a
  direct-HiGHS builder (good_lp construction stalls); hint-compatible
  frame generation at scale (row-0 chain CSP as the filter).
- ~~2 h slope confirmation in flight at close~~ **LANDED (same day)**:
  strict460a 448/450/450, strict460b 449/449/449 (4 seeds each, all 5/5;
  II 340-344, IB 45-50). 300 s → 7200 s = **+1 to +1.5 total** — the slope
  FLATTENS (+2.5/decade at small budgets → ~+1/decade). Saturation
  confirmed; **final CLOISTER-II v1 plateau = 450-strict / 453-unhinted.**
  The II wall (340-344 vs witness 350) holds at every budget tested.

## Linked

- [[cloister-standalone-interior]] — vol-211: the rim result + free-rim records
- [[blackwood-algorithm]] — the community border-first lineage
- [[vol-212]] — session journal (engineering details: bitset candidates
  refuted 0.64×, list engine 0.94× of vol-211 with full generality)
