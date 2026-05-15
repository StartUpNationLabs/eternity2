# Temporal-Rewind-Search (vol-63 draft)

**Status**: `design` — vol-63 (2026-05-15).
**Type**: INVENTED ALGORITHM (per user directive vols 61-70).
**Inventor**: this autonomous run.

## Audit-at-design (lesson from vol-62)

Before writing the algorithm, audit the codebase for similar
mechanisms:

| existing op | what it does | how vol-63 differs |
|---|---|---|
| `kick_every` in PT | random swap × N every K rounds | random; no memory |
| Houdayer | cross-replica cluster move | between replicas; no memory |
| `OracleCycleSwap` | apply σ-cycle from known higher board | needs oracle; no memory |
| Tabu | (none in codebase) | — |
| Restart | (CP only; not in ALNS) | no memory of intermediate states |
| Adversarial revert | (none) | this is what vol-63 invents |

The temporal-rewind mechanism does NOT exist. Other operators perturb
forward (new state derived from current); this one perturbs BACKWARD
(force-revert to a recorded past state).

## Motivation

ALNS + PT converge to local optima. Existing escape mechanisms (kick,
Houdayer, oracle) are FORWARD perturbations: they generate new states.

A FORWARD perturbation cannot recover state that the search has
already DESTROYED. If at iteration t the search held a sub-board X
that was on a productive trajectory but discarded X at t+1 because
of a tiny local improvement that turned out to be a trap, X is gone.

Temporal-rewind keeps a sliding window of past board states. When
stuck (no improvement for K rounds), force-revert to a random past
state in the window. This may worsen current score by 5-10 but
re-opens previously-discarded trajectories.

## The mechanism

```
def Temporal_Rewind_ALNS(initial_board, window_size=50, rewind_every=200):
    B = initial_board
    history = circular_buffer(window_size)  # holds (board, score) pairs
    rounds_since_improvement = 0
    best_seen = B

    for t in iterations:
        history.append((B, score(B)))

        B' = standard_alns_destroy_repair(B)
        if score(B') >= score(B):  # SA acceptance, normal
            B = B'

        if score(B) > score(best_seen):
            best_seen = B
            rounds_since_improvement = 0
        else:
            rounds_since_improvement += 1

        if rounds_since_improvement >= rewind_every:
            # REWIND: pick a random past state from buffer
            (B_past, _) = history.random_sample()
            B = B_past
            rounds_since_improvement = 0
            # Note: best_seen is preserved; B is just the search anchor.
```

## Key properties

- **Strict monotone for best_seen**: rewinds NEVER overwrite the best.
- **Score may temporarily drop**: rewind to a state from t-30 rounds
  ago, which had score 5-10 below current.
- **Non-local**: the rewind target is a fully different board, not a
  perturbation of current.
- **Memory cost**: window_size × O(board_size) ≈ 50 × 256 piece slots
  ≈ negligible.

## Variants

- **TRS-Random**: pick rewind target uniformly from window.
- **TRS-Diverse**: pick rewind target with low Hamming-similarity to
  current (encourages exploration).
- **TRS-Score-Weighted**: prefer rewind targets with score ≥ current
  - delta_max.
- **TRS-Pre-Local-Optimum**: detect when search hit a local optimum
  in the past (a state followed by ≥ K worsening rounds) and rewind
  THERE specifically.

## Why this might work

A standard ALNS+SA trajectory looks like:

```
score
  ^         peak
  |        /|       peak
  |       / |      /\
  |      /  |    /     valley_after_peak (trap)
  |____|/____|__/____________________________
        t1  t2 t3
```

After hitting `valley_after_peak`, the search rarely climbs back to
peak because the destroy ops sample randomly. Temporal-rewind takes
us BACK to t2 (which had higher score), then re-explores from there
with NEW seed/op selections.

The hypothesis: the trajectory is path-dependent. Returning to a past
peak with new random seeds gives a fresh exploration of an old basin.

## Risk / refutation conditions

- If E2 ALNS trajectories are Markovian (path-independent), rewind
  buys nothing — re-exploring from a past state will visit the same
  configurations.
- If basins are truly basin-scale (no path-dependence within), the
  same SA destination is reached regardless of starting point. Rewind
  becomes equivalent to repeated SA starts.

**Empirical test**: 5 SA runs from initial → record max-score.
Compare to 1 SA run with rewind_every=200, total iterations × 5.
If they're equal, no path-dependence; rewind doesn't help. If
rewind beats serial restart, there IS path-dependence and the
mechanism is real.

## Vol-62 implications

Vol-62's MIP-bound test proved 459 basin is locally optimal at halo ≤
2. This means ANY local operator (including rewind-then-local) is
bounded by 459 from this basin. So vol-63 won't break 459 from a
459 starting board.

**Where vol-63 might win**: lower-score basins where the local
optimum is achievable but escape requires re-routing through earlier
trajectory points. E.g., the 453 stage-2 partial from vol-61: ALNS
gets stuck around 456-457 in saturation; rewind might find a path
to 459 via a different local optimum.

## Build plan

### Day 1 (vol-63 open)

- Audit, write this concept (done).
- Stub `TemporalRewindAlns` struct in `crates/localsearch/src/alns.rs`.
- Wire into `alns_only` bin with `--rewind-every N --rewind-window K`.

### Day 2

- Run on vol-61 stage 2 partial (453/480, NOT a record): does rewind
  beat 5 serial seeds within same total compute?
- 4 seeds × 30 min × {standard, rewind_every=200}.

### Day 3

- Iterate parameters; characterize basin geometry from rewind trace.

## Linked

- [[mip-local-optimality-459]] — bound on what local ops can do from
  459 basin
- [[component-quotient-destroy]] — refuted local op
- vol-22 basin-escape recipe (similar spirit, different mechanism)
