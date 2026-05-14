# VOL-36 — binding plan

**Opened**: 2026-05-14 (~15:45 CEST) at vol-35 close.
**Status**: BINDING (user-approved direction).

## Why this volume exists

Vol-35 closed cleanly: 458 record stands, pin_hints bug fixed,
landscape mapped, no 459 break. The 457 attractors are
operator-locked under all current ops. Vol-36 picks the structural
unblock the audit-at-open keeps surfacing — and adds the user's
new "raw-DFS hint-linking path" idea, which is genuinely
new (vanilla_fast was hardcoded row-major; vol-14's
rectangle/layered used the engine, not vanilla).

## Multi-volume plan (user-approved 2026-05-14)

User intent: cover all four candidate directions across vol-36..38+
plus the layered-rectangle-on-vanilla idea.

| Vol | Binding items | Why this order |
|---:|---|---|
| **36** | (1) custom-path vanilla_fast bin (hints → center → outside); (2) McGavin prune-restart PoC | T1 is novel + user-fresh-proposed; T2 is the structural backlog item |
| 37 | (1) Soft unsat-pruner depth-conditional; (2) code-refactor batch (vol-25 debt) start | Mixed engine + code-quality vol |
| 38 | RL self-play for value-order | Big-swing; needs the unblock from earlier vols to compose |

This file pins vol-36's binding items. vol-37/38 listed in BACKLOG
under their own entries.

## Vol-36 binding items (≤3 per discipline)

### T1 — Raw-DFS custom-path vanilla (user-proposed)

**Build**: a vanilla-style backtracker (no propagators, dense bucket
arrays, ~100M+ pp/s target) that takes a **custom path** instead of
row-major scan. Default path: 5 canonical hints connected by short
shortest-grid-paths, then fill remaining interior cells (centre-out
spiral), then border ring.

**Why now**: vol-14's rectangle/layered (engine-based) lost as
static pre-commit because the engine's propagators choked on the
late-stage propagator-induced ordering conflicts. A raw DFS doesn't
have that failure mode — it just match-or-bust on each cell.
Different failure mode → potentially different basin geometry.

**Cost**: 0.5d build + 0.5d measurement. The infrastructure is in
place (vanilla_fast.rs is 687 lines, the bucket-array index is by
(north_color, west_color, n_is_border, ...)). Two changes:
1. accept `--path-csv <file>` for cell-visit order
2. recompute the lookup keys for non-row-major paths (cells have
   different known-neighbour sets when path differs)

**Gate**:
- Hint-linking path reaches depth ≥ 200 (vs vanilla_fast's typical
  200 in row-major) in 60s.
- ALNS post-fill from depth-200 hint-linking partial scores ≥ 450.
- Bonus: any seed reaches verified rescore ≥ 458.

### T2 — McGavin prune-restart PoC

**Build**: structural unblock for vol-22 + vol-35 bound-ascent
dead-end. At each bound-improving move, store a monotonically
growing "pinned set" of cells. The bound walk operates only on
un-pinned cells. Once bound reaches a target (e.g. 466), the pinned
set is materialised as Hints for an ALNS recovery pass — but the
recovery happens *with* the pinned set, not from scratch.

The vol-23 `mcgavin-prune-restart` shipped as a CP-depth-trigger
mechanism (depth-150 in joe_depth150 profile). T2 is a different
trigger: bound-improvement.

**Cost**: 1-2d. Engine already has `batch_hint_application`. New
work: pin-set growth schedule + bound-walk + handoff to ALNS.

**Gate**:
- The pipeline produces a verified score ≥ 458 from ANY starting
  basin in our 5-cluster verified record set.
- OR: at minimum, produces a score-≥455 board with a structurally
  different consensus from any existing 457 cluster (measured by
  pairwise Hamming with our 5 reps).

## Audit-at-open compliance

Resolved aged-unbuilt items:

| Item | Vol since | Resolution |
|---|---:|---|
| `multi-cell-bound-ascent` | vol-22 (14 vols) | **wont-do** — superseded by McGavin prune-restart (T2); 3/4-cycle moves without basin-context retention were the vol-21/22 failure mode |
| `bound-floor-alns-with-per-step-check` | vol-22 (14 vols) | **wont-do** — invasive, low EV; bounds-axis has fundamentally hit the recovery-collapse wall, no point shipping more bound-machinery without the retention fix that T2 IS |
| `diverse-457-search` | vol-21 (15 vols, partial) | **mark built (subsumed)** — vol-35 T1b shipped a comprehensive thread-id-offset basin diversity sweep that IS this item. 5 distinct cluster reps, 19 distinct basin families. No more diverse-457 lottery needed without a new operator. |
| `joe-iteration-budgeted-prune` | vol-32 (4 vols) | **defer to vol-37** — viable, low-cost (half-day), but vol-36's binding items already fill the volume. Move to BACKLOG vol-37 candidates. |

Aged items left intentionally:
- `unsat-soft-value-order-depth-conditional` (vol-34, 2 vols old, not yet aged).

## Out of scope for vol-36

- ❌ Code refactor (vol-37 territory).
- ❌ RL self-play training (vol-38).
- ❌ More vanilla_fast → ALNS replication (luck-chase, low EV
  per vol-35 finding).
- ❌ ML hyperparam sweeps (post-vol-32 bug fix, the ML space is
  largely closed under imitation; RL is the unblock, deferred to vol-38).

## Cost summary

- T1: 0.5d build + 0.5d measurement (total 1d).
- T2: 1-2d build + 0.5d measurement (total 1.5-2.5d).

**Vol total**: 2.5-3.5 days.

## Linked

- [[vol-35]] — predecessor.
- [[../concepts/prune-restart]] — vol-23 base; T2 extends.
- [[../basins/basin-457-pt]] — the locked attractor T2 targets.
- vol-14 [[../sessions/archive/raw/RESEARCH_NOTES_14|RESEARCH_NOTES_14.md]] for rectangle/layered prior art.
