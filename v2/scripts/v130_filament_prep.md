# V130-T1 — FILAMENT (Lin-Kernighan on 2D Grid)

**Status**: Prep file for vol-130 — DO NOT consider as vol-130 open
yet. Vol-129 (PALIMPSEST) must close first per
[[feedback_e2_one_invention_per_volume]].

## Algorithm overview

Lin-Kernighan's superpower for TSP is **variable-depth swap chains**:
each swap link is locally bad (or zero), but the chain's cumulative
gain stays positive and the chain closes only when total gain is
positive.

Port to E2's 2D grid:
1. Pick a position $i_0$ where current mismatch is high.
2. Pick a neighbor $i_1$ such that swapping pieces at $i_0$ and $i_1$
   IMPROVES the local mismatch at $i_0$.
3. The swap moved piece $p_1$ to $i_0$. Now $i_1$ holds piece $p_0$
   from $i_0$. Check if $i_1$'s NEW mismatch (with $p_0$) is bad. If
   yes, pick $i_2$ adjacent to $i_1$ such that swapping $p_0$ with
   $i_2$'s piece improves things, and continue.
4. The chain extends as long as the cumulative score improvement is
   non-negative.
5. Close the chain when the last position's piece happens to be
   already a good neighbor (saturating the chain).

## Differences vs `worst_band`

- `worst_band{4}`: destroy a fixed 4-cell strip and SA-repair. Pieces
  move within the strip's destroyed set.
- FILAMENT: variable-length chain, each step a single swap,
  extends along the grid following the "worst" edge.

## Implementation plan

1. Add `RepairKind::Filament` to `crates/localsearch/src/alns.rs`.
2. Implement `filament_swap_chain` in
   `crates/localsearch/src/filament.rs`:
   - Input: board + max chain length (e.g., 8-16)
   - Output: new board with chain applied, gain reported.
3. Wire into `alns_only` with `--repair-kind filament`.
4. Test multi-seed × multiple boards.

## Risks

- Chain may oscillate (cycle of swaps that net zero) — add tabu list
  or no-repeat-piece constraint.
- Implementation is delicate (bookkeeping which pieces are bumped).
- May or may not outperform `worst_band` on E2's coupled grid; LK
  shines when the structure is path-like (TSP). E2 is 2D, every cell
  has 4 neighbors, so chains can branch.

## Files to create at vol-130 open

- `crates/localsearch/src/filament.rs` (Rust impl)
- `crates/localsearch/tests/filament.rs` (property test)
- `crates/bench-audit/src/bin/alns_only.rs` (add --repair-kind=filament)
- `vault/sessions/vol-130.md`
- `vault/concepts/filament-lk-2d.md`
- `scripts/v130_filament_bench.sh` (multi-seed sweep on canonical E2)

## Open at close of vol-129 → vol-130 open
