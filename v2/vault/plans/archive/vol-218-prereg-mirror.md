# Vol-218 pre-registration — MIRROR gate (broken-top penetration)

Registered 2026-06-12 (UTC, same day as the BANDSAW prereg), BEFORE
any race ran. Generator (`mirror_gen.rs`) built; no race executed at
registration time.

## Design

Stage-1 = **rows 0–4** of the official E2 (80 cells; row-2 clues at
positions 34/45 forced; all 5 hint pieces reserved). Rationale for
rows 0–4 (not 0–3): cell-level attribution of the SOTA maps — each
cell pays its N and W edges — puts McGavin-469's 11 breaks in cells
of rows 1–4 (one double-payer at (4,14)) and Blackwood-470's in rows
1–4 plus one at (5,14) which we drop. Perfect rows 5–15 are demanded
(`vanilla_fast --init-board TOP --init-rows 5 --pin-hints`),
including the rows-4/5 join.

Arms (break-paying cells; non-mask cells must place at cost 0):
1. **control** — 0 breaks (perfect rows 0–4).
2. **sota469** — McGavin's exact cell map: (1,9),(2,8),(2,9),(3,7),
   (3,8),(3,14),(4,10),(4,11),(4,12) at cost 1; (4,14) at cost 2.
   Total 11.
3. **sota470** — Blackwood's map clipped to rows 0–4: (1,13),(2,5),
   (2,15),(3,13),(3,14),(4,6),(4,15) at cost 1; (2,10) at cost 2.
   Total 9.
4. **dispersed** — 10 cost-1 cells staggered rows 1–4 (MIDDEN-style):
   (1,4),(1,10),(1,15),(2,7),(2,13),(3,4),(3,10),(3,15),(4,7),(4,13).
5. **free** — budget 10 anywhere in rows 0–4 (DFS chooses; realized
   geometry recorded) — the temporal-default placement control.

K = 56 tops per arm (dedup by (row-4 souths, pool)); race = 60 s ×
1 thread per top, identical engine config, 7 concurrent workers
(8-core cap respected). Matched compute by construction.

## Registered metrics and bars

- **P-M1 (primary)**: median max-depth (absolute board depth from
  `[best-partial] depth=`) per arm. Mechanism prediction: broken tops
  penetrate deeper (b1≈20 per break ⇒ ~10^13 conditional-subtree
  inflation for ~10 breaks). **Gate: any broken arm beats control's
  median by ≥ +8 cells → PASS (promote MIRROR to a construction
  program). Within ±8 → FLAT (honest null, same-day). ≤ −8 →
  INVERTED (breaks poison the pool more than they relax the wall —
  also informative; report as such).**
- **P-M2 (secondary)**: rate of tops reaching depth ≥ 192 (perfect
  rows 0–11 analog... here depth counts the broken prefix; d≥192 =
  12 full rows placed); any full completions reported with total
  breaks and verified by rescore.
- **P-M3 (exploratory)**: free-arm realized break geometry vs
  achieved depth; dispersed-vs-sota ordering (does the MIDDEN
  "damage geometry matters" finding transfer to pre-paid tops?).

## Honesty clauses

- Letter AND substance reported (vol-217 lesson: an underpowered
  registered metric does not get to silently become a different one).
- The SOTA existence proof (469/470 boards EXIST with this shape)
  says nothing about reachability at our compute — a FLAT result
  refutes only the reachability claim at 60 s/top, not the shape.
- 8 cores max total; race runs only while the 10×10 program is not
  using the cores (serialized, not interleaved).
