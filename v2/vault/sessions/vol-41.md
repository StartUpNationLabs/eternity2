# Vol-41 — ValueOrder::RecordsPrior (positive signal, no record-break)

**Theme**: Build a real engine modification using the vol-37 structural-scan
findings. New ValueOrder variant ranks candidate (pid, rot) at each cell
by record-frequency from our 7 verified canonical-E2 records.

**Status**: SHIPPED. Positive but small signal.

## What was built

Engine changes:
- `ValueOrder::RecordsPrior` variant in `crates/solver-engine/src/config.rs`
- `SolveOpts.records_prior_map: Option<Arc<Vec<Vec<(u16,u8,u32)>>>>` in solver-trait
- `load_records_prior_map(path)` loader in solver-engine
- `EngineSolver::with_value_order(vo)` builder method
- Recurse-time re-ranking block in `solver-engine/src/lib.rs` (between
  BlackwoodHeuristic and break-index)

A/B harness:
- `crates/bench-audit/src/bin/run_e2_records_prior_ab.rs`
- Reads `output/vol-37_revised/cell_value_order.json` produced by vol-37
  structural_scan.

Both arms use the same engine profile (`joe_depth150_bp_par`); only
value-order differs.

## What was measured

**CP A/B (canonical E2, seed 1, joe_depth150_bp_par):**

| Budget | Metric | A (EdgeBpMarginals) | B (RecordsPrior) | Δ |
|---:|---|---:|---:|:---:|
| 30s | max_depth | 168 | 171 | **+3** |
| 30s | matched_edges | 288 | 297 | **+9** |
| 60s | max_depth | 168 | 171 | +3 |
| 60s | matched_edges | 288 | 297 | +9 |
| 5min | max_depth | 171 | 171 | 0 (ceiling) |
| 5min | matched_edges | 292 | 298 | +6 |

**Downstream ALNS A/B (4 seeds × 5min each from partials):**

| Seed | A (baseline) | B (RecordsPrior) | Δ |
|---:|---:|---:|:---:|
| 1 | 429 | 428 | -1 |
| 2 | 428 | **439** | **+11** |
| 3 | 427 | 433 | +6 |
| 4 | 423 | **439** | **+16** |
| **mean** | **426.75** | **434.75** | **+8** |

## Findings

1. **RecordsPrior consistently +5-9 matched-edges in CP** at iso-depth
   (60s) and iso-time (5min, where both hit depth 171 ceiling).
2. **Downstream ALNS amplifies the advantage** to +8 average / +16 best.
3. **No record-break**: best ALNS-completion score 439, well below our
   existing canonical records (455-457).
4. **Engine depth ceiling at 171-176** is hit by both arms — the value-
   order doesn't shift that ceiling, only WHAT'S PLACED within it.

## Why this signal exists

The 7 verified records are biased samples of high-score local optima.
Their per-cell (pid, rot) frequencies encode "what kinds of pieces
tend to be at this position in good solutions". RecordsPrior uses this
as a soft prior — at each cell, try the high-frequency candidates
first. Within a fixed depth budget, this places more solution-likely
pieces, accumulating more matched edges.

The depth-171 ceiling is determined by the propagator stack + the
joe_depth150 gate; value-order doesn't change it. But MATCHES per
placed cell are determined by piece choice.

## Limits

- **Self-reinforcing concern**: the records were produced by search
  algorithms with their own biases. RecordsPrior reflects those biases,
  not necessarily ground-truth structure. To meaningfully break records
  we'd need a prior from boards we DIDN'T produce (e.g. community 469).
- **No magic**: the +6-9 edge advantage doesn't propagate into +1 depth.
  The depth wall is structural, not value-order-related.

## What this enables (open)

1. **Composition with EdgeBpMarginals**: secondary tie-break by
   RecordsPrior within EdgeBpMarginals' ordering. Not yet built.
2. **Records-prior from community 469 board**: would give ground-truth
   prior (one canonical record). Need to decode + add to value-order map.
3. **Use as ALNS-time prior**: ALNS doesn't currently use value-order.
   Could be added as a repair-step bias.

## Records ledger (no change)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 |
| 456 | 5/5 | vol-32 blackwood_raw seed 2, 4 |
| 455 | 5/5 | vol-39 diverse seed 1, 5 |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 |

## Linked

- [[vol-37-pos161-discovery]] — produced the cell_value_order.json
- [[scan-order]] — RecordsPrior is a value-order, not scan-order
- [[edge-bp-marginals]] — baseline A
