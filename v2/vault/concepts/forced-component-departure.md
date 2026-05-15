# Forced-Component-Departure ALNS (vol-67 design)

**Status**: `design` — vol-67 (2026-05-15).
**Type**: INVENTED ALGORITHM (per user directive vols 61-70).
**Inventor**: this autonomous run.

## Audit-at-design

Codebase search: no existing ALNS variant tracks basin-component
membership at runtime. Vol-62 ComponentClusterDestroy uses local
defect components, NOT the broader basin-component map. Vol-22
basin-escape used bound-ascent + Hungarian — different mechanism.

## Motivation

Vol-65 day 4 discovered: our 135 unique 455+ records form **47
disjoint basin-components** when connected via σ-distance < 100.
McGavin's 469 is a size-1 component, σ-distance ≥ 247 from any
other record.

Standard ALNS converges to ONE basin-component and refines within
it. Escape mechanisms (kick, Houdayer, OracleCycleSwap) sometimes
work, but the empirical record-distribution shows our pipeline
hits 47 components, suggesting BASIN-LOCK is the dominant failure.

## The mechanism

```
def Forced_Component_Departure_ALNS(B, components_db):
    # components_db = pre-computed list of basin-component representatives
    # Each rep is a high-score board exemplifying that component
    current_component = nearest_component(B, components_db)
    iterations_since_departure = 0
    while not done:
        # Standard ALNS step
        B' = destroy_and_repair(B)
        if accept(B'):
            B = B'
        # Check component membership
        nearest = nearest_component(B, components_db)
        if nearest == current_component:
            iterations_since_departure += 1
        else:
            current_component = nearest
            iterations_since_departure = 0
        # If stuck in same component too long, FORCE departure
        if iterations_since_departure > MAX_STUCK:
            # Force depart: large-scale random perturbation guaranteed
            # to move us > THRESHOLD cells (=100 by component definition)
            B = forced_perturbation(B, min_hamming=100, components_db,
                                    avoid_components=[current_component])
            current_component = nearest_component(B, components_db)
            iterations_since_departure = 0
```

## Key innovations

### 1. Component membership tracking

At each step, compute σ-distance to each of N components' representatives.
Closest = current component. O(N · 256) per step = O(47 × 256) = 12k
operations per iteration. Negligible.

### 2. Forced departure mechanism

When stuck, generate a random perturbation that:
- Changes ≥ 100 piece-positions (= component-distance threshold)
- Lands in a DIFFERENT component than current
- Has score ≥ some floor (e.g., current - 30)

Method: pick a random target component, take its representative,
apply a random subset of σ-cycles to morph current → target.
Reject if score drops too far.

### 3. Component-aware acceptance

Standard SA accepts based on score. FCD-ALNS adds:
- accept(score_delta) ∧ (component_membership_changes ∨ score_delta > 0)
- This biases toward exploring NEW components, not just refining current.

## Why this might work

Every existing ALNS variant gets stuck in basin-components. FCD
explicitly tracks AND forces departure. It uses the COMPONENT MAP
as a structural prior the search lacks.

The McGavin basin is component #X. If FCD ever stumbles into it,
the standard ALNS step refines within. Reaching it requires:
- Forced departure of magnitude > 247 (McGavin's isolation distance)
- Random target close to McGavin

The probability is low but non-zero. With long-budget runs, FCD
should sample MANY components, including potentially McGavin's.

## Build plan

### Day 1
- Pre-compute components_db from 135 saved 455+ records. Store as
  list of (rep_id, rep_placement, rep_score).
- Implement `nearest_component()` and `component_membership()` in
  Python (cheap).
- Implement `forced_perturbation()` that morphs toward a target rep.

### Day 2
- Wire FCD into a Python-driven ALNS loop, with Rust alns_only
  subprocess as the "destroy and repair" step (1-5s budgets).
- Test: starting from local-459, after N forced departures, do we
  ever land in McGavin's component?

### Day 3
- Measurement: distribution of component memberships visited
  vs standard ALNS. Did FCD broaden coverage?
- If yes, longer runs to potentially hit McGavin.

## Risks / refutation conditions

- **Component identification noise**: if components_db has < 47 reps
  or wrong reps, classification fails.
- **Forced departure may not reach McGavin**: it can only target
  components in components_db, and McGavin is just one of 47.
  Unless FCD also generates RANDOM targets outside the DB.
- **Score collapse during forced departure**: morphing toward a
  random target may take many low-score steps before recovery.
  The "score ≥ current - 30" filter may make most forced moves
  infeasible.

## Linked

- [[basin-component-landscape]] — the 47-component finding that
  motivates FCD
- [[basin-permutation-group]] — σ-cycle context
- [[basin-level-genetic-search]] — vol-66 precursor (refuted at
  reaching McGavin)
- [[../sessions/vol-67]] (TBD)
