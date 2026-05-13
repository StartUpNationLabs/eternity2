---
tags: [concept, infrastructure, registry]
status: built-living
origin-vol: 12
---

# Engine profile registry

**Status**: `built` (vol-12 baseline, additions through vol-17)
**Origin**: vol-12 (`joe_depth150` family), extended ongoing
**Files**: `crates/solver-engine/src/lib.rs` (EngineConfig + `instantiate()`), `server/src/service.rs` (gRPC), `proto/solver/v2/solver.proto` (registry comment block)

## Registry shape

Per `V2_DESIGN.md`: canonical registry is **2 solver_ids × 7 heuristic profiles**. New strategies opt in by adding to `ListSolvers` + `instantiate()` — not by changing the proto.

`solver_id` and `heuristic_profile` are stable opaque strings; the registry comment in `solver.proto` and the entries in `server::service::instantiate` + `list_solvers` must stay in sync.

## Profiles shipped (chronological)

| Profile | Vol | Composition |
|---|:--:|---|
| `cell_cp_baseline` | 1 | AC-3 only |
| `gacolor_ac3_par` | 1 | + GAColor, RootSplit parallel |
| `joe_depth150_par` | 12 | + depth-gate (propagators fire at depth ≥150) |
| `gacolor_ac3_ns1` | 12 | + NS-1 multiset-equality |
| `joe_depth150_bp_par` | 14 | + `ValueOrder::EdgeBpMarginals` |
| `joe_depth150_bp_par` (variant) | 14 | + parity propagator toggle |
| `BLACKWOOD_RAW` | 15 | Blackwood schedule + breaks; **drop AC-3/gacolor/NS-1** (unsound under breaks); 47× single-thread speedup |
| `blackwood_raw_rect` | 15 | + RectangleDestroy pre-commit |
| `blackwood_raw_rect_layered` | 15 | + LayeredDestroy ordering |
| `calibrated_v17a/b/c` | 17 | Blackwood with empirically-calibrated schedules from community 469 corpus |

## Three orthogonal axes

`EngineConfig` exposes:
1. `variable_order` (cell scan order; see [[scan-order]])
2. `value_order` (BP, random, MRV, BlackwoodHeuristic)
3. `propagators` (PropagatorConfig sub-struct: ac3 / gacolor / ns1 / parity / class_balance / island toggles)

Profiles are preset combinations; new propagators add as a flag + a function in the `propagators` crate.

## Soundness matrix

| Profile | AC-3 | GAColor | NS-1 | Sound? |
|---|:--:|:--:|:--:|:--:|
| `gacolor_ac3_*` | ✓ | ✓ | — | ✓ exact-matching |
| `joe_depth150_*` | ✓ | ✓ | depth-gated | ✓ exact-matching |
| `BLACKWOOD_RAW` | ✗ | ✗ | ✗ | ✓ (only under break allowance — see [[blackwood-algorithm]]) |
| `calibrated_v17*` | ✗ | ✗ | ✗ | ✓ ditto |

Mixing **Blackwood + AC-3/gacolor → UNSOUND**: propagators remove rotations that the break_index allowance would license at later depths. This was the cliff-bug source in vol-15 before being explicitly forbidden.

## Vol-16 cleanup wins

- `PropagatorConfig` extracted as sub-struct (Cat-2 cleanup).
- `score_board` O(n²) → O(n) via `Puzzle::piece` O(1) cache.
- Precomputed `same_piece_rots` LUT for AC-3 → **2.9× joe_depth150 speedup**.
- BLACKWOOD_RAW post-cleanup → **4.6× single-thread** (~80k → ~367k nps).

## Linked concepts

- [[gacolor]], [[ac3]], [[ns1-deficit]] — the propagators referenced
- [[bp-marginals]] — `ValueOrder::EdgeBpMarginals`
- [[blackwood-algorithm]] — the soundness exception
- [[scan-order]] — the variable_order axis

## Linked memory

- `project_e2_vol12_engine_profiles`
- `project_e2_vol16_closeout`
