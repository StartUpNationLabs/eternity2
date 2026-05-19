# Current Volume — Vol-145

**Theme**: ICEBERG — constructive heuristic that MINIMIZES forbidden
2x3 count (not matched edges).

V140/V143 found: forbidden-count tweaks don't help ALNS escape 461.
But maybe forbidden-count helps with **starting positions**.

New invention: a GRAIN-like constructive heuristic that greedily
places pieces to minimize NEW forbidden 2x3 patches, not to maximize
matched edges. The output may have LOWER matched score than GRAIN but
FEWER forbidden patches — a structurally cleaner seed for ALNS.

## Binding items (3 max)

1. **ICEBERG constructive**: GRAIN-like (random seeds + greedy growth),
   but the attachment criterion is "minimize forbidden 2x3 count
   contribution".
2. **Compare to GRAIN seed quality**: same wallclock, compare both
   (matched-edges, forbidden 2x3 count).
3. **ICEBERG → ALNS pipeline vs GRAIN → ALNS**: which seeder produces
   better 60s ALNS finals?

## Linked

- [[concepts/grain-polycrystalline]]
- [[concepts/forbidden-patch-theorem-2026-05-19]]
- [[sessions/vol-145]]
