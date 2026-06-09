# Current Volume — Vol-204 — WATERSHED: Frontier Color-Flow Streamliner

**Theme**: A GLOBAL, incremental feasibility check that prunes a partial board the
moment its remaining piece supply provably cannot match the exposed frontier's
color demand (Hall / max-flow on the frontier). Attacks WHY deep edge-strict DFS
paths die (~depth 150-210) — the real bottleneck, since canonical DFS branching is
already tiny (~2-3 survivors/cell, measured vol-203).

## Naming
**WATERSHED** — the frontier is a watershed line; the color-flow check decides
whether remaining-piece "supply" can flow downhill to meet the frontier's "demand".

## Why this (vol-203 evidence → user-chosen direction)
Vol-203 established three negatives: PARQUET 2×2 LP capped at 480; F0 counting
vacuous; 2×2 patch-consistency prunes only ~6%. Canonical row-major DFS is
"deep & narrow": ~2-3 edge-strict survivors/cell, but paths die deep. So the lever
is NOT local branching reduction — it's detecting global infeasibility EARLIER.
The engine's gacolor/multiset propagators do partial color accounting but
apparently miss the binding frontier constraint (DFS still plateaus ~150-210).

## Binding items (3 max)
1. **Diagnose the death mechanism**: instrument edge-strict DFS; at each
   backtrack-to-dead-end record depth + WHY (no candidate at cell c). Test
   whether a color-flow / Hall check on the frontier would have detected the
   eventual dead-end EARLIER (how many levels of lookahead it saves). If deaths
   are supply-exhaustion → WATERSHED has leverage; if not → report + pivot.
2. **Build the incremental frontier color-flow feasibility check** (sound
   necessary condition for completion), measure pruning + max-depth gain vs
   edge-strict baseline at small + canonical scale.
3. **If it deepens DFS materially**, wire into a MaxScore run; measure score
   reached. Any ≥460 from-scratch is notable; any new-cp ≥460 a record.

## Days budget
3-5 days.

## Audit-at-open compliance
Supersedes vol-203 PARQUET (closed: bound direction capped). WATERSHED is the
search-side complement, chosen by user from the vol-203 decision fork.

## Linked
- [[watershed-frontier-flow]] (TBD)
- [[streamlining-for-e2]] (parent technique)
- [[parquet-overlapping-patch]] (vol-203 bound result)
- [[depth-40-wall-math]] (frontier supply-exhaustion conjecture)
- [[lague-rubik-transfer-ideas]] (admissible-bound philosophy)
