# Current vol — vol-120 OPENED 2026-05-16

## Audit-at-open compliance

- Vol-119 closed: INVENTION (corpus-restricted region MIP), 30-board
  corpus assembled, NEW 458 basin (sweep_p18_s2). Standing 459
  UNCHANGED.
- Aged unbuilt items: no new aged items past vol-119.
- Key handhold: vol-119 found that corpus-LP=INT (tight). To break
  459, need new basin sources OUTSIDE current corpus.

## Vol-120 binding items (≤ 3)

### T1 — vanilla_path basin hunt (clean-slate)

Cross-machine SOTA used `vanilla_path border-first × 9 threads ×
30min → 403 → ALNS basic 30min seed=42 → 459`. Vol-119 used
`vanilla_fast --pin-hints` partials (only 8 of them). Let me run
vanilla_path with multiple thread-id-offsets to discover NEW partials.

Sweep: `border-first-mrv` × {offset 0, 8, 16, 24, 32} × 1min each
(produces 5 distinct starting partials) → ALNS basic 5min × 4 seeds
each = 20 jobs.

Effort: 1h wall.

Prior: medium. Vol-60 used different starting points to find p06
basin's 459. Different partials → different basins.

### T2 — corpus-restricted region MIP on NEW basins (apply T5 invention)

Once T1 produces new 458+ basins, add them to the corpus and run
T5 region MIP. Test: does corpus enlargement raise the MIP INT
optimum above 459?

Prior: medium-low. Vol-119 found basins are roughly piece-conflict
fragmented (cluster A vs B vs McGavin can't co-mix). New
canonical-hint basins might merge with cluster B.

### T3 — RL self-play scaffolding (unrefuted handhold)

Per ONBOARDING §6: "RL self-play with reward = max-score (multi-week,
only unrefuted theoretical handhold per vol-114)."

This is multi-week to fully build. T3 = SCAFFOLDING ONLY this vol:
identify the right RL framework (REINFORCE / PPO), draft action/state
representation, sketch reward shaping. NO training run.

## Linked

- [[../INDEX]]
- [[../sessions/vol-119|vol-119 close]]
- [[../concepts/corpus-restricted-region-mip-locked]]
- [[../concepts/sigma-subset-bound-empirically-tight]]
