# PALIMPSEST — Historical-Consensus Invariant Mining

**Status**: `partial` (Vol-129, 2026-05-19 — analysis built, escape-pinning attack in progress)
**Origin**: Brainstorm reservoir round-3
[[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
**Files**:
- `scripts/v129_palimpsest_consensus.py` — pair-tuple consensus
- `scripts/v129_palimpsest_geometry.py` — trap-density heatmap
- `scripts/v129_trap_pieces_per_position.py` — per-position trap/escape
- `scripts/v129_interior_traps.py` — interior-only filtering
- `scripts/v129_escape_piece_pinning.py` — full-overlay attack (rediscovers McGavin)
- `scripts/v129_escape_pinning_v2.py` — K-pin sweep attack (K=16,32,64)
- `scripts/v129_top_row_destroy.py` — row-0-3 cycle-destroy attack

## Definition

Across $N$ runs over a hard combinatorial problem, the solver visits
many near-optimal boards. PALIMPSEST mines this archive: adjacencies
that appear in ALL high-score runs are almost certainly correct;
adjacencies that appear in low-score runs but never in high-score
runs are **consensus traps** — the agreed-on wrong choice locking
the search into a sub-optimal basin.

## V129 measurements

**Data**: 1278 boards in `database-400-480/` (score $\ge 400$).

**Per-pair consensus** (V129-T1):
- 223 788 distinct realized pair-tuples
  $(i, j, \text{dir}, \text{pid}_i, \text{rot}_i, \text{pid}_j, \text{rot}_j)$.
- Category A (likely-correct, count $\ge 5$ AND max-score $\ge 462$):
  **490** pairs.
- Category B (consensus traps, count $\ge 20$ AND max-score $\le 460$):
  **5573** pairs.

**Trap-density heatmap** (V129-T2):
- Trap density is HIGH in rows 0-3 (8-12 traps per cell, peaking at
  pos (2, 2) with 12 traps).
- Trap density is LOW in rows 10-15 (0-3 traps per cell).
- **Our 461 basin family is locked at the top half; bottom half is
  consensus-correct.**

**Per-position trap/escape pieces** (V129-T5):
- All 256 positions have at least one trap piece AND at least one
  escape piece.
- Top trap-heavy positions are **border cells** (top row, bottom
  row, left/right columns).
- Examples:
  - pos 8 (top row, c=8): TRAP $p{=}18, r{=}0$ in 230 boards;
    ESCAPE $p{=}39, r{=}0$ in 5 boards.
  - pos 128 (left col, r=8): TRAP $p{=}56, r{=}3$ in 188 boards;
    ESCAPE $p{=}57, r{=}3$ in 6 boards.

**Interior traps** (V129-T8):
- 139 of 144 interior cells have trap $\ne$ escape.
- Highest-trap interior cells in rows 2-5.
- Example pos 35 (row 2, col 3): TRAP $p{=}69$ in 242 boards; ESCAPE
  $p{=}97$ in 6 boards.

## V129 attacks

**Attack 1 — full escape overlay** (V129-T6):
- Pin top escape piece at every trap-heavy position (251 positions
  after excluding canonical hints).
- Result: starting board has **corner perm $(3, 2, 0, 1)$ = McGavin's
  basin**, score 451/480.
- This rediscovers McGavin's basin via consensus mining — interesting
  validation but no novel basin.

**Attack 2 — K-pin sweep** (V129-T7, in flight):
- Pin only top-K escape pieces by trap strength. $K \in \{16, 32, 64\}$.
- Starting boards: K=16 → 415/480, K=32 → 382/480, K=64 → 298/480.
- ALNS basic 30min × 2 seeds per K. Results pending ~08:13 CEST.

**Attack 3 — top-row cycle-destroy** (V129-T9, queued):
- Cycle-permute pieces in rows 0-3 to break the trap consensus
  without pinning specific replacements. Let ALNS rebuild.

## Conclusion (in progress)

Established:
1. The 461 basin family is identifiable by SPECIFIC TRAP PIECES at
   BORDER + ROW-2-5 INTERIOR positions.
2. Replacing those trap pieces with their escape counterparts
   reassembles the board into McGavin's basin (corner perm (3,2,0,1))
   at score 451/480.

Pending:
- Whether partial pinning (K=16,32,64) finds a NOVEL basin > 461 that
  isn't McGavin (the WIN), or just degraded versions of our 461 / McGavin.

## What's still open

- Top-row cycle-destroy attack with no replacement specification.
- Soft pinning (penalty rather than hard pin).
- Score-weighted multi-basin clustering of records — find OTHER
  basins beyond McGavin / our 461.
- Iterate: use V129 escape-pieces as a soft prior for transformer
  training (consensus pieces are training targets).

## Vol-129 close (pending K-sweep results)

Status will be set after V129-T7 completes (~08:13).

## Linked

- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[fpl-frozen-pair-lifting]] (refuted — V125-T34)
- [[concord-difference-map]] (partial)
- [[concretion-rigid-molecules]] (refuted)
- [[atlas-pattern-database]] (refuted)
- [[basin-440-469]]
- [[basin-457-pt]]
