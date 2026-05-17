---
name: j1-chain-hinted-v2-fix
description: "J1-hinted v2 — corrects v1's silent failure mode by reserving downstream hint pieces upstream. Result: 240/256 placed, 5/5 hints, 414/480 matched, LEGAL_PARTIAL."
metadata:
  type: project
---

# J1-hinted v2 — hint piece reservation fix

## Bug in v1

In `j1_chain_hinted` v1 (commit 3c5adc7), each band correctly locked the
hint piece at its (row, col) via `fixed_top` / `fixed_bot` constraints,
but pieces were NOT reserved across bands. Result: J1's column-DP would
greedily consume hint pieces in earlier bands.

Concrete trace on canonical 16×16:
- Hint at pos 210 (r=13, c=2) expects piece 180 rot 1.
- J1's band 3 (rows 2,3) greedy beam chose piece 180 (in some rotation)
  for position (3, 10). Score-optimal locally.
- When band 12 (rows 12, 13) tried to lock piece 180 rot 1 at (13, 2),
  the piece was no longer available → "NO STATES at col 2" infeasibility.

Same with piece 248 (placed at (4, 7) instead of waiting for (13, 13)).

V1 result: 208/256 placed (rows 0-12 only), 3/5 hints obeyed, band 12
fails.

## Fix (v2)

Before solving each band, mark all DOWNSTREAM hint pieces as used in
`initial_used`:

```rust
for (&(hr, _), &(hpid, _)) in hint_by_rc.iter() {
    if hr > bot_row {
        initial_used.set(hpid);
    }
}
```

Now hint pieces are reserved from the start, and J1's beam search
naturally routes around them in earlier bands.

## V2 result (beam=100k, canonical 16×16)

- **240/256 placed** (rows 0-14, row 15 empty)
- **5/5 hints obeyed**
- **414/480 matched edges**
- **status LEGAL_PARTIAL** (verify_board)
- Band 14 col 15 fails — last column, last band, after a long chain
  with the constraints imposed.

## Significance

This is the FIRST J1-family algorithm to produce a 5/5-hint-compliant
canonical board with band-perfect structure for most bands.

The 240-cell partial is a CLEAN seed for ALNS basic 30min × 4 seeds
(seeds 1, 7, 13, 42). Currently running.

## Next steps

1. Wait for ALNS results.
2. If ALNS lifts to ≥458, this beats the strict-canonical 457 record.
3. If ALNS lifts to ≥460, this beats the matched-edges 459 record
   (since 5/5 hints satisfies 4/5).
4. If ALNS stays at 440-450 range, the J1-hinted partial structure
   is sub-optimal for ALNS exploration — consider J1-hinted with
   stronger band-14 search (larger beam, multi-start).

## Linked

- [[j1-chain-hinted-band-12-failure]] (v1 failure analysis)
- [[j1-rust-beam100k-first-complete-board]]
- [[j1-loss-localization-math]]
- [[j1-forward-look-heuristic]]
