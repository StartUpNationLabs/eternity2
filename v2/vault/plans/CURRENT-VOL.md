# Current Volume — Vol-213 (day 2) — REPLAY mode + frame generator

**Status**: re-drafted 2026-06-10 (day 2). Strict track (5/5) bar
unchanged: **461**. Day 1 banked: seam family ≤ row-major (II wall is
scan-geometry-invariant), self-pool priors asymptote null, witness track
saturates at 456-457 because break candidates are NOT prior-ordered
(the walk forks at the witness's first break cell), 500-frame census
1/500 hint-compatible with the killer cell pinpointed ((0,1)/(0,12)
triple-constraint chains).

## Binding items (≤3)

1. **REPLAY mode (`--prior-over-cost`)** — the live 460+ shot. In
   dfs.rs's priors branch: when `break_open`, ALSO drain break-segment
   candidates into the per-depth buffer; sort by (Reverse(weight),
   cost). Effect: the witness walk takes its break pieces AT its break
   cells ⇒ exact replay to depth 182, exact tail ≥ its row 13, then
   anytime backtracking explores the perfect-prefix NEIGHBORHOOD with
   exact endgames. Run both witnesses (460a/b), 8 seeds × 300 s, then
   hours if the curve moves. Every board ≥458: verify + rescore +
   provenance (witness-derived) stated.
2. **Hint-compatible frame GENERATOR** — unlock the frame pool. Ring
   enumeration with the four chain-feasibility constraints baked in
   (for each killer cell, ≥1 compatible interior (piece,rot) given the
   ring's inward colors), or generate-and-probe (diverse BB=60 rings +
   6 s hinted probe). Target 50+ compatible frames; v1-recipe census;
   the question: does ANY frame escape the 444-450 band? (vol-212's
   uniform-band claim is 5-frame-based — widen or refute.)
3. **Choke-map instrument + auto-gates** — per-depth death histograms
   from epoch ends; per-(frame, scan, hinted) choke profiles; gates AT
   measured chokes vs hand-spread (≥8 seeds, min/med/max). Also answers
   "are hint positions the choke?" quantitatively on the wider pool.

Standing invitation if items finish/stall: PREFIX VAULT (bank ≥160-deep
perfect prefixes as restart seeds — would open vol-214); frame_ub
direct-HiGHS builder (calibrate Bucas-469 → 409, strict460a → 400).

## Audit-at-open compliance

- Day-1 items closed: seam scan (measured, ≤ row-major, interim verdict
  in [[vol-213]]), priors (built, asymptote null, witness diagnostic ★).
- BACKLOG items frame_ub (`partial`) and frame-generator (`unbuilt`,
  since vol-212): generator is NOW binding item 2 (promoted); frame_ub
  stays parked behind the standing invitation.

## Discipline

≥8 seeds min/median/max; verify + independently rescore every ≥458
before any claim; timestamped outputs (UTC tags); append history CSV;
8 cores max TOTAL; honest negatives to the vault same-day.

## Linked

- [[cloister-ii-border-anchored]] (architecture + plateau + witness ladder)
- session: [[vol-213]]
