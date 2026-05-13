# Vol-32 NEW FINDING — blackwood_raw + MRV → ALNS = 453/480 cold-start

## Headline

**453/480 cold-start score** achieved from a single 30s CP run + 5min
single-seed ALNS. **+21 over vol-31's weak-pipeline best** (432),
**−4 from the all-time record** (457 from vol-18's lucky basin).

## Pipeline

```
canonical 5-clue 16×16 E2
   ↓
joe-disabled engine config = blackwood_raw (BlackwoodHeuristic + RowMajorBottomUp
   scan, light propagators), but with value_order overridden to MRV (LeastConstraining)
   ↓ 30s, single-thread
depth-190 partial: 195/256 placed, 357/480 matched edges (74.4%)
   ↓ alns_only --ops winning5 --repair-kind sa --seed 1 --alns-budget-ms 300000
matched=453/480 (94.4%), 256/256 placed
```

## Comparison

| Pipeline | Partial source | Initial edges | ALNS-5min | Cold-start record |
|---|---|---:|---:|---|
| vol-32 baseline (joe + EdgeBp) | edge_bp_165 | 280 | 424 | — |
| vol-32 (joe + insertion / vol-31's "ML") | insertion_174 | 303 | 432 | — |
| vol-32 (joe + TRUE LOT post-fix) | lot_fixed_v4 | 283 | 422 | — |
| **vol-32 NEW (blackwood_raw + MRV)** | **blackwood_raw_190** | **357** | **453** | **+21 over insertion** |
| vol-18 lucky basin (hot-PT) | n/a | n/a | n/a | 457 (record) |

## What this changes

1. **The dominant value-order under `blackwood_raw` (vol-15 config)
   is MRV, not BlackwoodHeuristic**. Same engine, different value-order
   → +110 depth (80 → 190 in 30s).
2. **Cross-profile A/B was a vol-32 bonus** that surfaced this; the
   binding investigation was about ML hyperparams. We caught a real
   engine win on the way.
3. **vol-15's "Blackwood depth wall at 80" was schedule-specific**, not
   engine-config-specific. With the SAME engine config but MRV value-
   order, we reach depth 190 — well past the schedule wall.

## Verification

- Board placement validated: 256/256 cells, all 5 canonical hints in
  correct positions (cell 34/pid 207, cell 45/pid 254, cell 135/pid 138,
  cell 210/pid 180, cell 221/pid 248).
- `target/release/rescore_board`: 256/256 placed, 453/480 matched edges
  (94.4%).
- Saved board: `output/v17_alns_only/winning5_sa_t1_s1_1778714766.json`.

## Open follow-ups (for vol-33)

1. **PT-5min from this partial** — running now. If reaches 457+, NEW
   cold-start record candidate.
2. **Multi-seed ALNS lottery from this partial** — 16-seed batch at
   5min each → distribution of scores 449-455 likely.
3. **Cross-budget**: does 1-hour ALNS reach further?
4. **Confirm scan-order vs value-order independence**: rerun
   `blackwood_raw + MRV` with different scan orders.
5. **Investigate why MRV beats BlackwoodHeuristic on this engine**:
   the Blackwood schedule was designed for blackwood_raw; MRV winning
   suggests the schedule's prescribed value sequence isn't matching
   the actual search needs.

## Reproduction

```bash
# Step 1: generate the depth-190 partial
target/release/canonical-eval \
    --profile blackwood_raw --mode mrv \
    --budget-ms 30000 \
    --puzzle ../data/puzzles/size_16_official_eternity.csv \
    --bp-path output/v12_bp/edge_bp_60i.json \
    --dump-partial output/vol-32/t4/blackwood_raw_190.json

# Step 2: convert to alns format
python3 -c "
import json
b = json.load(open('output/vol-32/t4/blackwood_raw_190.json'))
placement = []
for pos, c in enumerate(b['cells']):
    if c is None: continue
    if isinstance(c, list): placement.append({'pos': pos, 'piece_id': c[0], 'rotation': c[1]})
json.dump({'placement': placement}, open('output/vol-32/t4/blackwood_raw_190.alns.json', 'w'))
"

# Step 3: ALNS 5min
target/release/alns_only \
    --cp-board output/vol-32/t4/blackwood_raw_190.alns.json \
    --alns-budget-ms 300000 \
    --seed 1 \
    --ops winning5 \
    --repair-kind sa
```

This was discovered as a vol-32 bonus during the cross-profile sweep.
