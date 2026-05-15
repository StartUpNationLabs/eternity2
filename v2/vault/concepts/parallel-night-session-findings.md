# Parallel-night-session findings (2026-05-14/15)

**Status**: future-work reference page. Not currently active.
**Origin**: parallel agent session ran overnight on a DIFFERENT MACHINE
(10 cores; our main session is on 8 cores) while the main agent
worked vol-44..vol-48. Findings archived for later integration.

**IMPORTANT** — separate machine context:
- Files referenced in the raw report (`runs/color_sweep/`,
  `data/puzzles/synth/`) live on that other machine. **They are not in
  our local repo.**
- The score-counter bug fix the night session reports as "shipped"
  may or may not be in our local branch. **Verify before relying on
  scores from `vanilla_path` / `vanilla_fastest`.**
- All numbers are observational from that report; cannot be reproduced
  locally without the puzzles and the other machine's logs.

**Raw**: [[../sessions/archive/raw/NIGHT_2026-05-14-15_color_sweep|raw report]].

## Headline findings

### F1. Vanilla DFS color-complexity sweep on 16×16 synthesized puzzles

Across C ∈ {6..12} colors (vs official E2's 22):

- **C=7 is the easiest-easier-than-E2 regime** (460.7 ± 8 / 480 across 3 seeds).
- **C=6 is NOT uniformly easy** — seed-2 dropped to 387/480, *harder than E2*.
  Instance-specific.
- **C=8 has a pathological seed** that drops to 261/480. Spread 191 edges.
- **C=9..12 is the stable regime** (3-4 edges loss per color, predictable).
- **Even C=6/7 doesn't solve in 60s** — vanilla DFS hits the "last 15-25
  cells" wall at every color count tested. The wall moves closer to 480
  as C decreases but doesn't disappear.

**Implication**: difficulty isn't only color-count. Below C=8, **specific
generator seed dominates**. Official E2 (C=22) may be a benign C=22 instance.

### F2. ALNS-`minimal` operators beat ALNS-`mega` operators

On a 403/480 vanilla partial, 5-min ALNS:
- `mega` ops (large destroy bands): 403 → 435.
- `minimal` ops (small surgical destroys): 403 → **452**.

**+17 edges from operator choice alone.** Consistent with vol-44's
basin-locking finding (small moves preserve good structure).

### F3. ALNS ceiling at 454/480 across 20 jobs

8 inputs × 8 seeds × 15 min with `minimal` ops:
- Best: 454 (seed=4 on 3 different inputs)
- Worst best-per-seed: 450
- **No seed broke 454.**

Confirms vol-44's "458 is firm" finding from a different starting set.

### F4. Score-counter bug discovered and fixed (during the night)

`vanilla_path` and `vanilla_fastest` were reporting
`matched_internal + matched_border` against `/480`, but the canonical
E2 score only counts internal adjacencies. The fix renames the metric
and exposes both for transparency. **Records claimed before this fix
need re-verification** against the corrected counter.

### F5. Trim-and-restart DFS dies on 403 partial

Pinning the 226 good cells from a 403 partial as hints and DFS-ing
the remaining cells dies at depth ~205 in milliseconds — the 403
partial is structurally **un-completable**. Joe McGavin's
prune-restart pattern reproduced at vanilla scale.

## Why this matters for our main track

The main agent has been doing LP-UB landscape analysis (vol-44, 45),
basin-MIP local optimality proofs (vol-44), lifted-LP attempts
(vol-47), and RL self-play (vol-48 in flight). The parallel agent's
findings **independently corroborate**:
- Basin lock pattern at 454-458 (consistent with our 458 firm-ceiling
  evidence).
- Path-order / scan-order matters (vol-14 finding).
- Local-search operator choice matters dramatically (vol-44 small-move
  preference).

Plus the **new instance-variance finding at low color counts** is
genuinely novel structural information we hadn't measured.

## Items for future vol-N backlog (no urgent action)

- **Q-vol-49+**: Run propagator engine on C=6/7 synthesized puzzles.
  If it solves trivially → clean propagator-value demo. If not →
  engine bug at low-C.
- **Q-vol-50+**: Run engine on the C=8 seed=3 adversarial puzzle.
  Robustness test.
- **Q-vol-N**: Finer C-sweep at 7.0..7.5 to localize the difficulty
  cliff with biased generators.
- **Q-vol-N**: Test border-first scan order with the full propagator
  engine (vs vanilla).

## Linked

- [[../sessions/archive/raw/NIGHT_2026-05-14-15_color_sweep|raw night report]]
- [[lp-ub-478-basins]] — main agent's basin-locking evidence
- [[458-class-A-mismatch-structure]] — main agent's 458 anatomy
- `project_e2_vol14_mismatch_geometry_universal` — memory entry on
  basin geometry being scan-order-determined
- BACKLOG item: `unified-edge-score-counter` (fix shipped during night)
