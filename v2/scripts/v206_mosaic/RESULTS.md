# MOSAIC window-MaxSAT — tractability (vol-206, 2026-06-09)

pysat RC2 weighted-partial-MaxSAT, window placement maximizing matched edges.
Pool = all 196 interior pieces (worst case; reserved pools will be smaller/faster).

| window | cells | matched_internal | solve time |
|---|---:|---:|---:|
| 2×2 | 4 | 4/4 (perfect) | 3.2s |
| 2×3 | 6 | 7/7 | 5.8s |
| 3×3 | 9 | 12/12 | 11.0s |
| 3×4 | 12 | 17/17 | 17.8s |
| 4×4 | 16 | 24/24 | 31.7s |
| 2×8 | 16 | 22/22 | 23.3s |
| 3×5 | 15 | 22/22 | 25.9s |

Confirms Anjou's tractability: windows solve to OPTIMUM (all-matched here, since
the full interior pool can tile a small window perfectly). Solve time grows with
cells AND pool size; reserved (smaller) pools will be faster. ~16 cells in ~30s
with full pool is the working envelope for the MOSAIC composition engine.

## MOSAIC-soft composition — full board (vol-206, 2026-06-09)

Boundary matches made SOFT (blocks never go infeasible — pay for mismatches).
Sequential 4×4-block fill, no backtrack, no ALNS, no warm start, full 256-piece pool.

**RESULT: 443/480 from pure exact-block composition** (363s, 16 blocks).

Per-block trace: first 13 blocks near-perfect (24-32/max); degradation concentrated
in the LAST 3 blocks (bottom-right): block(3,1)=27/32, (3,2)=24/32, (3,3)=17/32 —
classic piece-theft: the pool is depleted by the time we reach the corner, so the
last blocks pay many mismatches.

Significance:
- 443 >> greedy single-descent (~385, vol-205) with NO local search.
- The wall is LOCALIZED to the last ~3 blocks → reservation + localized
  block-backtracking should lift it substantially.
- Confirms MOSAIC composition is a strong constructive engine. Earlier perfect-
  block backtracking (mosaic_bt) hit the SAME depth-157 wall as edge-strict DFS
  (block 39/64) because requiring perfect blocks ≡ edge-strict. The fix is SOFT
  boundaries (MaxScore, never dies).

Next: scarcity reservation (keep corner-needed pieces), block-backtrack last 3
blocks, better block order. Then Rust port (user-endorsed) for speed + bigger search.

## Rust port — validated (vol-206, 2026-06-10)

`crates/bench-audit/src/bin/mosaic.rs` — self-contained Rust engine (per-block
exact MaxScore DFS, no SAT-solver dependency). Reproduces the Python result:

| mode | matched | hints | verify_board | notes |
|---|---:|---:|---|---|
| unhinted (row, rf=0.08) | 447 | 0/5 | 256/256 unique, LEGAL | matched-edges convention |
| `--hints` (row, rf=0.08) | 438 | **5/5** | LEGAL_COMPLETE | strict-canonical; user-verified in Bucas |

Bug fixed during port: `must_border` returned border sides in push-order
(N,S,W,E) but candidate border-side sets are ascending — the SE corner (mb=[S,E])
never matched any piece → block infeasible. Fix: sort must_border output.

CONVENTION NOTE (verified by diffing hint cells vs McGavin): McGavin 469 and all
our 460+ matched-edges records have 0/5 canonical hints obeyed — they trade
hint-compliance for score. MOSAIC `--hints` is the genuine strict-canonical track
(5/5). One engine, both conventions.

Next: block-backtracking (fix bottom-right corner degradation) + ALNS post-step.
Strict-canonical 438 + hint-preserving ALNS has headroom toward the 458 record.

## MOSAIC config sweep (vol-206, 2026-06-10)
- row-major + exact (node cap 2e9), rf=0.08: **447** in ~50s — BEST config.
- corners order: 371 (worse — fragmented boundaries). spiral: 388. → row-major wins.
- candidate-shuffle seeds (cap 50M): 410-429, fast (~2s) but quality too low.
- The first block (free boundary) is the only expensive solve (~50s exact); all
  boundary-constrained blocks are fast. Quality↔speed tradeoff lives in block 1.
- MOSAIC basin is 95-99% Hamming-distinct from all known 459-469 basins (novel).
- ALNS on 447 → 448 plateau (σ-locked in MOSAIC's basin).

DECISION: row-major exact is the quality config. Diversity must come WITHOUT
killing quality — vary reservation/seed at full node-cap. Decisive open test:
does ANY MOSAIC novel basin ALNS-lift past the 460 plateau?
