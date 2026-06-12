# Current Volume — Vol-217 — OPEN (2026-06-12)

**Theme: the CROSSING program.** Vol-216 localized the 452→460 gap
to the wall-crossing rows ~10.5-12 (witness endgame pools ordinary,
band costs equal, early board identical; witnesses pay 3-4 breaks
outside the bottom band vs our ~11). All three validated static
instruments cap at ρ≈0.3 because they measure endgame-pool health —
the dominant variance component (crossing cost) was unmeasured.
Strict bar: 461 original (5/5 hints MANDATORY). The 480 perspective
governs: from-scratch construction × multipliers × exact-region;
existing boards are reconnaissance, never material.

## Binding items (3)

1. **CROSSING ORACLE** (the named invention; build first). 3-row
   break-profile transfer over interior rows 10-12 conditioned on the
   prefix's ACTUAL placed frontier: N boundary of row 10 = exact
   placed row-9 south colors (no free-N relaxation — sharper than
   [[band-oracle]] by construction); placed row-10+ cells forced;
   row-12 clue hints pinned; S of row 12 free; all edges
   break-tolerant. Machinery: extend
   `scripts/v216_bandoracle/band_oracle.py` (new
   `scripts/v217_crossing/crossing_oracle.py`). PRE-REGISTERED GATE
   (file written before any score): witness d146 pools must separate
   decisively below our banked prefixes on crossing floor (numeric
   prediction: witness ≈3-4 vs banked ≈8-11); secondary: ρ vs ≥300s
   labels (n=75) must beat 0.335 (the LP). Gate fails → honest null
   SAME DAY, pivot to standing alternates.
2. **CROSSING-RANKED SELECTION** (the cheap win, hours once oracle
   exists). Re-rank ALL banked prefixes (3,416 across vol-214/215)
   + fresh probe streams by crossing cost; race top-k at 300 s × 8;
   wire as LADDER rung-0 (band oracle + LP as secondary lenses). If
   any banked prefix has a witness-grade crossing, this alone may
   break 452.
3. **CROSSING-GUIDED CONSTRUCTION — STAGED FULL-BOARD** (the
   capability jump; multi-day, aim here). USER-DIRECTED upgrade
   (2026-06-12 mid-vol, binding): the staged build runs on the REAL
   16×16 with all 256 pieces, frame-free — four 4×16 bands (rows
   0-3 / 4-7 / 8-11 / 12-15), border ring EMERGES (top edge in
   stage 1, W/E flanks per band, bottom edge chosen LAST when the
   pool is known). Witness anatomy in this staging: stages 1-3
   PERFECT, all 20 breaks in stage 4 ⇒ build three perfect stages
   presenting the best stage-4 entry; stage 4 = min-break endgame
   (64 cells) with budget spent inside rows 11-13. Components:
   fb_oracle (16-wide mixed-pool N-row profile), stage-1/2
   generator (frame-free), stage-3 population builder (never commit
   first-found — SEMAPHORE/CLIMB lesson), stage-4 DFS+et14.
   USER FRAME DIRECTIVE (binding): no new material on witness
   frames; banked witness-frame prefixes are reconnaissance only;
   fresh generation frame-free or framegen-original.

Pre-stated risk: crossing cost may be as emergent-global as
everything else (unsteerable mid-construction). Binding 1's gate
settles that in days.

## Audit-at-open compliance

- Vol-216 cohort is fresh (no aged-≥3-vols unbuilt items in it).
  Vol-216 binding statuses corrected in BACKLOG at this open:
  `assignment-lp-prefix-scoring` → `built` (validated + adopted as
  rung-0 lens); `actuary-markov-schedule-optimizer` → `partial`
  (calibrated to 5%, race-1 honest negative, iteration 2 scoped);
  `exact-region-growth` → `partial` (k>14 + value-LB + Hungarian
  shipped; in-DFS growth net negative at current bound strength;
  next rung = `sa2-tail-bound`).
- New vol-217 BACKLOG entries: `crossing-oracle`,
  `crossing-guided-construction`.
- Pre-cloister-era items (vol-109 and older) remain in last-audited
  state per the standing BACKLOG note.
- Vol-216 promised vs delivered: all three bindings shipped results
  same-day (1 built, 2 partial with mechanisms diagnosed); unplanned
  deliverables: band oracle (best median signal), witness-pool
  localization (the vol-217 foundation), fugacity equal-case,
  piece-tensor spectroscopy, constraint-immediacy principle.

## Standing discipline

≥8 seeds min/med/max; verify+rescore every ≥451; UTC tags; hinted
gates ≤120 or choke-derived; finals ≥300 s to read prefix quality;
never chain background runs via pgrep-on-script-name; capped exact
methods must surface cap-hit; 8 cores max TOTAL; pre-register every
gate before computing scores.

## Standing alternates (pick on merit if bindings close/fail early)

ACTUARY iteration 2 (per-arrival quality histogram in dfs.rs, pooled
refit, corridor trust region — objective REFRAMED to crossing cost);
fugacity-MPS honest counts (χ-convergence pre-registered);
8×8 exact counting rig; staged count-guided construction;
sinkhorn-lp-surrogate; sa2-tail-bound.
