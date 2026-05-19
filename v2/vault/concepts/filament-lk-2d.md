# FILAMENT — Lin-Kernighan on 2D Grid

**Status**: `partial` (Vol-130, 2026-05-19 — built, integrated as
RepairKind, validated on bad boards; LOSES to SA-repair on equal
budget. Could still help if used in addition to SA, not replacing it.)
**Origin**: Brainstorm reservoir round-4
[[plans/EXTERNAL_BRAINSTORM_2026-05-18]] — extending vol-123 W4's
LkhChainDestroy with TRUE variable-depth gain tracking.
**Files**:
- `crates/localsearch/src/filament.rs` (Rust impl)
- `crates/localsearch/src/alns.rs` (RepairKind::Filament integration)
- `crates/bench-audit/src/bin/v130_filament_apply.rs` (standalone bin)

## Definition

Lin-Kernighan's TSP innovation: a swap chain where each link can be
LOCALLY BAD (or zero gain), but the chain CLOSES when cumulative gain
is positive. Variable depth + gain-aware backtracking.

E2 instantiation:
1. Seed at a worst-match cell (low cell-match count).
2. Find the best swap partner (highest local match-count gain).
3. Apply swap. Track cumulative gain across the chain.
4. Repeat from the newly swapped position.
5. Cut chain when cumulative gain falls below $-\text{max\_loss}$.
6. Return board state at the depth of maximum cumulative gain.

## Difference from vol-123 W4 `LkhChainDestroy`

| Aspect              | LkhChainDestroy (vol-123 W4)    | FILAMENT (vol-130)               |
|---------------------|---------------------------------|----------------------------------|
| Output              | Set of cells to destroy         | Modified board (chain applied)   |
| Gain tracking       | None (just cell selection)      | Per-step + cumulative, with backtracking |
| Pieces moved        | After SA repair (delayed)        | During chain construction        |
| Variable depth      | Fixed max_size                  | Cuts when cumulative gain too low |
| Close condition     | Reaches max_size                | Best-gain prefix of chain        |

## V130 measurements

**Standalone FILAMENT** (`v130_filament_apply`):
- 461 base board × {16, 256} seeds × {12, 16} depth × 5-50 trials:
  no improvement (deep local minimum).
- 451 base (PALIMPSEST escape overlay) × similar: no improvement.
- 254 base (McGavin-overlay broken) × 32 seeds × 16 depth × 5 trials:
  254 → 290 (+36) gain.

**FILAMENT as ALNS repair** (`alns_only --repair-kind filament`):
- 254 base × 60sec budget × ops=basic: 254 → 331 (+77).
- **SA-repair baseline same setup**: 254 → 380 (+126).
- **SA wins by 49 points on equal budget.** FILAMENT is more expensive
  per repair call (multi-seed chain search), so fewer total ALNS
  iterations complete in the same wall-clock.

## What works

- The Rust implementation compiles, passes its property test
  (gain never negative), and integrates cleanly.
- On weakly-optimized boards, FILAMENT-repair beats standalone
  FILAMENT (60sec ALNS+filament → +77 vs standalone +36).
- Combined with ALNS' destroy operators, FILAMENT provides a
  fundamentally different repair semantics than SA: each repair pass
  is a deterministic local-best chain rather than a random walk.

## What's still open

- Comparison against SA-repair on near-optimal boards (461/480).
  Long-run benchmark needed.
- Tuning: max_depth (currently 12), max_loss (currently 4),
  try_rotations (currently true), seed_worst (currently false in
  filament_repair, true in standalone).
- Multi-start FILAMENT inside repair (rather than just per-cell
  seeds in the free_set).

## Vol-130 close (pending benchmarks)

Status `partial`: core implementation works; effectiveness on
record-track problems unmeasured. Next vol opens after benchmarks
complete. Or: vol-130 closes as `partial`, next vol picks the next
brainstorm invention (GRAIN, PRISM, TUNNEL, etc.).

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[fpl-frozen-pair-lifting]] (refuted)
- [[palimpsest-historical-consensus]] (partial)
- vol-123 W4 LkhChainDestroy (parent)
- [[sessions/vol-130]] (to-be-created at formal vol open)
