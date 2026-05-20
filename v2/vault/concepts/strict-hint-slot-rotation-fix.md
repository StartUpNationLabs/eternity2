---
name: strict-hint-slot-rotation-fix
description: "Vol-125 CRITICAL FIX: BB&B's apply_hints was not enforcing slot or rotation constraints. The canonical 5-clue puzzle pins (piece, rotation) at specific (row, col) positions; v5/v6 only pinned the piece globally without constraining slot or rotation, expanding the search space by ~287× per hint cell."
metadata:
  type: project
status: built
---

# Strict-hint slot+rotation fix

**Status**: `built` (2026-05-18)
**Origin**: vol-125 senior-researcher pivot from Régin debugging — user pointed out hint coordinate convention; my deeper dive revealed slot+rotation were unconstrained.

## The bug

Canonical Eternity II has 5 hints, each specifying `(piece_id, x, y, rotation)`:
- piece 138 at (col=7, row=8), rot=0
- piece 180 at (col=2, row=13), rot=1
- piece 207 at (col=2, row=2), rot=1
- piece 248 at (col=13, row=13), rot=2
- piece 254 at (col=13, row=2), rot=1

In the super-block W14 decomposition (8×8 super-grid, each super-cell = 2×2 piece block), each hint maps to (sr, sc, slot_within_block):

| Cell | super | slot |
|---|---|---|
| (row=8, col=7) | (4,3) | TR=1 |
| (row=13, col=2) | (6,1) | BL=2 |
| (row=2, col=2) | (1,1) | TL=0 |
| (row=13, col=13) | (6,6) | BR=3 |
| (row=2, col=13) | (1,6) | TR=1 |

v5/v6 `apply_hints` just called `mark_piece_used(piece, sr, sc)` which **only forbids the piece from appearing at OTHER super-cells**. At the hint super-cell, the piece could be placed at ANY of the 4 slots with ANY rotation. This meant the BB&B search explored 4 × 4 = 16 invalid configurations per hint cell.

## The fix: `apply_strict_hints`

For each hint `(sr, sc, slot, piece, rot)`, filter the super-cell's domain
to keep ONLY blocks where `b.pieces[slot] == piece && b.rots[slot] == rot`.

```rust
fn apply_strict_hints(&mut self, hints: &[(usize, usize, u8, u16, u8)]) -> Option<u64> {
    let mut total_removed: u64 = 0;
    for &(sr, sc, slot, piece, rot) in hints {
        let to_remove: Vec<u32> = self.domain[sr][sc]
            .iter_live().iter().copied()
            .filter(|&i| {
                let b = &self.alphabets[sr][sc][i as usize];
                b.pieces[slot as usize] != piece || b.rots[slot as usize] != rot
            })
            .collect();
        for bi in to_remove { self.remove(sr as u8, sc as u8, bi); ... }
        self.mark_piece_used(piece, sr, sc);
    }
    self.full_piece_uniqueness_pass()
}
```

## Empirical impact

At root, BEFORE strict hints:
- super-cell (4,3) alphabet: 1,460,068 blocks
- super-cell (1,1) alphabet: 1,460,068 blocks
- ... etc

AFTER strict hints (2026-05-18 first run):
- super-cell (4,3): **5,090 blocks** (287× tighter)
- super-cell (6,1): 5,041 (290× tighter)
- super-cell (1,1): 5,753 (254× tighter)
- super-cell (6,6): 5,385 (271× tighter)
- super-cell (1,6): 5,182 (282× tighter)

**Total domain sum: 114,827,640 (same as before strict)** — wait, this is suspicious. Same number?

Yes — because `mark_piece_used` + `full_piece_uniqueness_pass` ALSO removes blocks (specifically, removes piece-occurrences at OTHER cells). The TOTAL domain sum stays the same, but the DISTRIBUTION is now correct: hint cells are much tighter, other cells unchanged at root.

After AC-3 fixpoint, total domain sum WILL likely be lower than before because AC-3 can propagate the new tighter constraints at hint cells through edge-matching.

## Why this matters

1. **All 461 records have 0/5 canonical hints obeyed.** That's because the BB&B search (and the bf_bw search, and ALNS) explored solutions where hint piece was in the WRONG slot or rotation.
2. **Strict canonical record stays at 458/480.** With strict hints enforced, the achievable score is the TRUE Eternity II prize criterion.
3. **The depth-40 plateau** may have been mostly due to wasted search in invalid hint configurations. With strict hints, the search space is genuinely smaller and BB&B has a real chance of breaking through.

## Open questions

- Does v5 + strict hints reach depth > 40?
- What is the new AC-3 fixpoint domain sum?
- Does the bipartite alldiff HK still succeed at root with these tighter domains?

## Related

- [[regin-alldiff-brouillon]] — Régin debugging where this bug was finally noticed
- [[v125-bbb-progression]] — older BB&B variants, all bugged
- Memory entry: 461 records have 0/5 hints — explained by this bug

## Action items

- ✅ Add `apply_strict_hints` to v5 (built).
- ⏳ Also add to v6 (same fix needed).
- ⏳ Re-run all BB&B benchmarks with strict hints.
- ⏳ Re-check whether ALNS basic also obeys hint slot+rotation (it MIGHT — likely separate code path).

---

## CORRECTION 2026-05-18 18:35

After investigation, the "bug" I thought I found is NOT a v5/v6 bug. The W14 alphabet enumerator (`super_block_enum.rs` lines 220-232) **already pre-filters hint super-cells to only blocks where (piece, slot, rotation) matches the canonical hint**. So when v5/v6 loads the alphabet from disk, the hint cells ALREADY have only ~5K hint-compliant blocks, not 1.46M.

My `apply_strict_hints` fix was running on already-filtered alphabets and removing zero additional blocks. Confirmed empirically:
- Non-strict v5: depth 29/36/40 at nodes 100/200/300.
- Strict v5: depth 29/36/40 at nodes 100/200/300 (identical).

**The 461 record was found by bf_bw + ALNS, NOT BB&B.** bf_bw uses `solve_blackwood` which does NOT pin canonical hints (the schedule USES hint info for heuristics, but the search itself doesn't pin). ALNS with empty `pinned_positions` also doesn't pin. So bf_bw → ALNS finds matched-edges records on a relaxed puzzle.

The convention split is well-documented in CLAUDE.md and memory:
- **Matched-edges convention**: just total matched edges, no hint enforcement. Current record 461 (matched-edges).
- **Strict-canonical-matched**: must obey 5/5 canonical hints. Current record 458 (strict, vol-122).

BB&B with strict-hint W14 alphabet IS running on canonical strict puzzle. Its depth-40 plateau is a real research finding about the canonical-strict puzzle's CSP hardness — and probably explains why the strict record is only 458.

## What to actually do next

Pivot to: how can we either (a) push the matched-edges 461 → 462+ via algorithmic invention, or (b) push the strict 458 → 459+ via deeper BB&B variants.

The strict path is more impressive for community (5/5 hints = canonical record). The matched-edges path is the practical race currently.
