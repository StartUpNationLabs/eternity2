---
name: scarcity-skeleton-shared-core
description: "vol-208 probe — high boards (McGavin 469, vol-129 463) ACTIVATE ~30 of 121 unique-server (N,W) demands; 24 are SHARED (Jaccard 0.73) = a near-universal forced scarce-demand core. 28 pieces are unique server of 2-3 demands (57 demands mutually-exclusive), only 64 demands have a dedicated server. First piece-position-level commonality found across basins (orthogonal to the known 'no piece-at-position backbone')."
status: built
metadata:
  type: concept
---

# Scarcity skeleton & its shared core (vol-208)

**Origin**: vol-208 CONFLUENCE premise probe (2026-06-10),
`scripts/v208_confluence/probe_skeleton2.py`. Built on the vol-204 WATERSHED
scarcity finding ([[watershed-frontier-flow]]).

## Definitions
A cell's **(N,W) demand** = the (color on its North face, color on its West face)
of the piece placed there. A piece **serves** (c1,c2) if some rotation puts
N=c1, W=c2. Over interior demands (both colors ≠ border 65535) there are **362**
distinct (N,W) pairs; **121 have exactly ONE serving piece** (vol-204).

## What we measured

### 1. The scarcity graph has hard internal conflict structure
- **28 pieces are the unique server of MORE THAN ONE demand** (27 pieces serve 2
  demands, 1 piece serves 3). That ties up **57** of the 121 unique demands in
  mutual-exclusion groups: a single piece cannot sit at two cells, so **at most
  one demand per group is activatable**.
- Only **64** unique demands have a *dedicated* server (server serves no other
  unique demand). So the truly-free forced skeleton is ≤ 64 + (one-per-group),
  not 121.

### 2. High boards activate only ~30 of 121 — and share a core
| board | matched | interior cells (nonzero N,W) | unique-demands activated |
|---|---:|---:|---:|
| McGavin 469 | 469 | 225 | **30** |
| vol-129 463 | 463 | 225 | **27** |

- Overlap: **24 demands shared** between McGavin and 463 (Jaccard **0.73**).
- The placed piece is the unique server at 100% of activated unique-demand cells
  (forced, by definition — if the demand is realized, only one piece can do it).

### 3. This is the FIRST piece-position-level commonality across basins
[[E2_KNOWN_FACTS]] §4: across 5 high boards, **0 cells have all-5 piece-at-position
agreement**, 0 have 4-of-5, only 5 have 3-of-5 — "no universal piece-position
backbone". That is about *which piece sits at which position*. The scarce-demand
core is **orthogonal**: it's about *which scarce (N,W) color-demands are realized
anywhere on the board*. On that axis McGavin and 463 agree on **24/30** — a far
stronger conservation than any piece-position signal found in 207 volumes.

**Interpretation.** High boards are not arbitrary; they are concentrated in a
region of configuration space that *activates a common set of ~24 scarce demands*.
The unique server of each activated demand is then forced. This is a genuine,
previously-unmeasured structural attractor.

## Why this matters for construction
Greedy/MOSAIC constructors activate demands in *scan order* and spend unique
servers before knowing whether their co-activation is consistent → piece-theft →
447 plateau. A constructor that **commits to the shared scarce-demand core first**
(place the forced unique-server pieces at mutually-consistent cells, then fill
around them) starts *inside* the region all high boards share. This is the
[[transept-strip-assignment]] hypothesis.

## ★ CORPUS CHECK (vol-208) — the strong "fixed core" is REFUTED; a soft attractor remains
`scripts/v208_confluence/probe_corpus_core.py` over the full
`database-400-480/` corpus (re-scored, fakes filtered) by score band:

| band | valid boards | activated/board (min/med/max) | demands in ≥80% | demands in ≥50% |
|---|---:|---|---:|---:|
| 420–439 | 188 | 24/31/43 | **0** | 1 |
| 440–449 | 178 | 25/31/42 | **0** | 2 |
| 450–457 | 363 | 23/32/42 | **0** | 3 |
| **≥458** | 79 | 25/**32**/43 | **0** | **10** |

**Refutation of the strong version.** NO scarce-demand appears in ≥80% of high
boards. The McGavin↔463 Jaccard 0.73 was a 2-board coincidence — the most-common
demand across 79 ≥458 boards appears in only 51/79 (65%). **There is no universal
forced skeleton.** A constructor cannot just "commit the fixed core".

**The real (soft) signal.** The count of demands present in ≥50% of boards rises
*monotonically* with score: 1 → 2 → 3 → **10**. The ≥458 band has a markedly more
concentrated demand-activation profile. Activation *count* is band-invariant
(median ~31-32 everywhere) — it's *which* demands, not how many. So high boards
are drawn toward a **probabilistically preferred** demand set, not a hard core.
Top ≥458 demands (freq/79): (5,19):51, (14,20):49, (3,6):47, (4,21):47, (15,6):46.

**Implication for CONFLUENCE.** The lever is a *soft prior*, not a hard pin:
bias construction toward activating high-score-correlated scarce demands, while
solving the co-activation consistency globally. See [[transept-strip-assignment]].

## Caveats / open
- "Activated demand" is necessary-but-not-sufficient: activating the right demands
  doesn't place the *non-scarce* pieces; it's a skeleton, not a solution.
- The shared core's cells are not fixed positions — the same demand can be served
  at different board cells in different boards. The constructor must choose cells.
- The ≥50% set (10 demands) is itself only a correlation; co-activating all 10 may
  be inconsistent. The constructor must *select a consistent subset* under the prior.

## Linked
- [[watershed-frontier-flow]] — the (N,W) scarcity / piece-theft diagnosis
- [[transept-strip-assignment]] — the constructor built on this (vol-208)
- [[mosaic-window-maxsat]] — prior constructor that botches scarcity (scan-order)
- [[E2_KNOWN_FACTS]] §4 — the orthogonal "no piece-position backbone" fact
- memory: `project_e2_v204_death_mechanism_2026_06_09`
