---
tags: [concept, propagator, sat, community]
status: refuted-as-hard-pruner
origin-vol: 32
---

# Unsat-clause propagator (capiman/e2 community database)

**Status (post-vol-34)**:
- **Hard-pruner**: `refuted` — capiman's clauses are heuristic-specific,
  not globally unsat. Silently kills valid moves.
- **Soft value-order (depth-conditional)**: `unbuilt` — vol-35 candidate.
  Empirical depth-rank measurement shows strong signal at d≤100, mixed
  signal at d≥160.

**Origin**: vol-32 (community-research discovery).
**Vol-34**: encoding reconciliation shipped (`ml/data/{color_map,piece_card_map}.json`)
and hard-pruner refuted.
**Files**:
- `output/capiman_e2/` — cloned community CNF database (336 MB, 68 files,
  ~70M total clauses across rounds).
- `ml/unsat_propagator_proto.py` — Python loader + decoder.
- `output/vol-32/unsat_propagator/literal_decoder.json` — exported decoder
  table (3 MB JSON) for Rust loading.

## What this propagator does

Capiman + Akos's community work over 2021 enumerated unsat 2-piece
clauses on canonical Eternity II using SAT solvers: pairs of
`(piece, position, rotation)` placements that demonstrably cannot
co-exist in any valid solution. Each clause is `-X -Y 0` where X, Y
are positive literals 1..130180, each encoding a `(field, card, rotation)`
triple via the `e2_info.c` table.

At engine integration: when piece P is placed at field F in rotation R,
look up its literal X; for every Y in `forbidden_partners(X)`, remove
the placement decoded from Y from the relevant cell's domain. This
acts as a **2-piece-lookahead propagator** — strictly stronger than
pairwise AC-3 because the SAT-derived forbidden set encodes long-range
unsatisfiability proofs that AC-3 cannot rediscover locally.

## Encoding (decoded by vol-32 prototype)

- **NR_OF_SAT_VARIABLES = 130180**, max literal in CNFs matches.
- **e2_info.c** defines 130180 rows, each
  `{Index, Field, Card, Rotation, PatternN, PatternE, PatternS, PatternW}`.
- Literal = Index (1-indexed). Field = 0..255, Card = 1..256 (i.e.
  piece_id 0..255 with +1 offset), Rotation = 1..4 (i.e. our 0..3 with +1 offset).
- The `enabled_fields` in `e2_info.c` says all 256 fields are populated.

## What we measured (vol-32 prototype)

- 130,180 literals parsed in 0.43 s.
- Round_1 (largest CNF, 125 MB): **53,194,585 clauses parsed in 56.6 s**.
- Forbidden-partner-count distribution across 130,174 literals: mean 817,
  max 4317. (Round_1 alone — full database higher.)
- Total directed forbidden-pair edges: ~106M from round_1.
- Memory estimate for full CSR: ~424 MB at u32 per edge (~106M entries
  × 4 bytes × 2 arrays). Higher with the full 70M-clause database.

## Architecture (vol-33 implementation plan)

1. **Build phase** (once at engine init): load all CNF files; parse `-X -Y 0`
   lines; build CSR `row_starts[L+1]` + `col[K]` arrays. Or sparse hash
   map if memory's an issue.
2. **Decoder table**: `Vec<(field, piece, rot)>` indexed by literal.
   3 MB (loaded from JSON, or built from `e2_info.c` parse at startup).
   Reverse map `[(piece, field, rot) → literal]` as a `[u32; 256*256*4]`
   or HashMap.
3. **Engine integration**: in `place_and_propagate` (after gacolor + AC-3),
   compute the placed literal X, iterate `forbidden_partners[X]`, decode
   each Y back to `(piece, field, rot)`, and call `remove_from_domain`.
4. **Cache budget**: forbidden_partners[X].len() ≈ 800 mean ops per
   placement, ~1000 cycles each ≈ 0.8 ms per placement. At ~500K nodes/run
   on canonical that's 400s — likely too expensive. Need either:
   a) Lazy partial activation: only check forbidden set for high-symmetry
      pieces.
   b) Precomputed per-cell relevant subsets: at field F, only literals with
      `forbidden[L].field == F'` for some nearby F' need checking.
   c) Bitset representation: per literal, 130180-bit forbidden mask
      (16 KB / literal = 2 GB total — too big).

The cheapest realistic plan: **incremental tightening of EdgeBpMarginals'
candidate filter** using the forbidden list. Vol-33 first pass: just
filter out the top-1 candidate if it's forbidden by anything already
placed.

## Vol-34 refutation evidence

After full encoding reconciliation (color map + piece_card map +
rotation table all bijective), validate against the verified vol-32
458 record board (a known-good fully-placed canonical-clue board):

| Forbidden set | Conflict pairs | Missing-from-encoder |
|---|---:|---:|
| forbidden_all.bin (all rounds combined) | 56 | 71 |
| forbidden_round1.bin (round 1 only)    | 18 | 71 |

**56 / 18 conflicts on a board that is *demonstrably* valid** means
the database has many false-positive unsat claims under our search
regime. The capiman README was misleading — these are NOT
globally-proven-unsat 2-clauses; they're round-specific heuristic
restrictions that emerge from capiman's own search constraints
(heuristic-side + break-index policy).

## Soft value-order signal (vol-34 measurement)

Ranked the ground-truth candidate (the placement at position k in
a verified record board) among all encoder candidates at field k,
sorted ascending by unsat-forbidden-partner-count with already-placed
pieces:

| Depth | Best record (% rank) | Worst (% rank) | N entries at field |
|---:|---:|---:|---:|
| 30 | 0% (perfect) | 32% | 287 |
| 50 | 49% | partial | 45 |
| 80 | 9% | 20% | 56 |
| 120 | 2% | partial | 515 |
| 160 | 29% | 89% | 56 |
| 200 | 21% | partial | 573 |

Pattern: strong at d≤100, inconsistent at d≥160. Vol-35 candidate:
implement as `ValueOrder::UnsatSoft` active at depth < 100.

## What is open

- Soft-pruner depth-conditional integration (vol-35 T2 candidate).
- Performance budget for soft-pruner: ~800 forbidden-partners per
  placed-literal ops at d=100. At joe_depth150_bp's ~7k nps × 100
  placements per node = 7M ops/s/thread = ~0.1 ms/lookup, plausible.

## Linked concepts

- [[ac3]] — pairwise arc-consistency. Unsat propagator generalises this
  with proven-unsat 2-clauses beyond local consistency.
- [[gacolor]] — Régin alldiff. Unsat propagator is *complementary* — it
  proves global infeasibilities that alldiff cannot see locally.
- [[community-corpus]] — the broader corpus that capiman + Akos data
  came from.

## Linked memory

- (to write at vol-33 close)
