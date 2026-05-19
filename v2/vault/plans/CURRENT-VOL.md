# Current Volume — Vol-143

**Theme**: ForbidDestroy — destroy 2x3 forbidden patches, repair.

V142 established: forbidden 2x3 count is a strong inverse correlate
of matched-edge score (LOW 137, MID 66, HIGH 36, McGavin 26).

V140's tiebreaker integration was inert. New approach: use forbidden-
2x3 patches as DESTROY TARGETS. Pick one of the (currently
forbidden) 2x3 patches on the board, destroy its 6 cells, let
repair fill with feasible pieces.

## Binding items (3 max)

1. **Rust ForbidDestroy operator**: enumerate forbidden 2x3 patches,
   pick one (random or worst-cost), output destroy-set of 6 positions.
2. **Wire into ALNS**: add to operator portfolio.
3. **Benchmark**: 461 base + ForbidDestroy 5min vs vanilla ALNS.

## Linked

- [[sessions/vol-143]]
- [[concepts/forbidden-patch-theorem-2026-05-19]]
