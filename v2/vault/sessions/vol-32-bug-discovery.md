# Vol-32 Critical Finding — Vol-30/31 ML lift was a measurement artifact

**Status**: Confirmed by direct A/B + binary trace + md5 match of partials.
**Severity**: Vol-30 + vol-31 headline numbers (+9 depth, +10/+8 score)
need correction. The "first ML-driven canonical lift" is a bug.

## The bug

`crates/solver-engine/src/lib.rs:2550` initialised `cell_side_edge` only
when `value_order == EdgeBpMarginals` (literal match):

```rust
cell_side_edge: if matches!(solver.config.value_order, ValueOrder::EdgeBpMarginals)
    && opts.edge_bp_marginals.is_some()
{
    build_cell_side_edge(puzzle)
} else {
    Vec::new()
},
```

When vol-30 introduced `ValueOrder::LearnedOnTies` (commit `c1294ed`),
it added the LOT sort block at lib.rs:4067 but never updated this
initialiser. So under `value_order = LearnedOnTies`:

1. `cell_side_edge.is_empty()` is true.
2. The condition at lib.rs:4025 `(is_edge_bp || is_learned_on_ties) && ... && !self.cell_side_edge.is_empty()` is FALSE.
3. The BP-sort block never runs.
4. `bp_keys` stays empty.
5. The LOT rerank block at lib.rs:4067 `is_learned_on_ties && bp_keys.len() >= 2` is FALSE.
6. The Learned NN is never invoked.

The engine silently falls back to InsertionOrder.

## The measurement that exposed this

Added an env-gated trace at lib.rs:4088:
```rust
if std::env::var("E2_LOT_TRACE").is_ok() {
    eprintln!("LOT_TRACE depth={} pos={} ...", depth, pos, ...);
}
```

Ran `canonical-eval --mode learned_on_ties --budget-ms 5000`:
- 18k engine nodes.
- **0 LOT_TRACE events fired**.
- depth = 150 (matches InsertionOrder, not EdgeBpMarginals or true LOT).

## A/B with the fix

`cell_side_edge` initialiser extended to also match `LearnedOnTies`:

```rust
cell_side_edge: if matches!(solver.config.value_order,
    ValueOrder::EdgeBpMarginals | ValueOrder::LearnedOnTies)
    && opts.edge_bp_marginals.is_some()
{ build_cell_side_edge(puzzle) } else { Vec::new() },
```

Re-measured at canonical 16×16, 60 s budget, single-thread:

| Mode | Pre-fix (vol-30 measurement) | Post-fix (true LOT) | Reason |
|---|---:|---:|---|
| `edge_bp` (explicit) | 165 | 165 | Baseline unchanged. |
| `default` (= joe_depth150_bp's EdgeBpMarginals) | 165 | 165 | Baseline unchanged. |
| `insertion` | 174 | 174 | InsertionOrder unchanged. |
| `learned_on_ties` (vol-30's headline) | **174** | **165** | Pre-fix bypassed BP+NN entirely. |
| `learned` (full NN) | 164 | 164 (model actually called) | Already correct pre-fix. |

The "ML lift" of +9 was actually "InsertionOrder beats EdgeBpMarginals
by +9 under joe_depth150_bp". Nothing to do with the trained model.

## Independent confirmation: byte-identical partials

The four "different EPS / MAX_K" depth-174 partials I captured in
T3 setup are all md5-identical:

```
51b12f5ebdc6a8f213b8520a7dfbcc52  p1.json (eps=0.005 max_k=16)
51b12f5ebdc6a8f213b8520a7dfbcc52  p2.json (eps=0.05  max_k=8)
51b12f5ebdc6a8f213b8520a7dfbcc52  p3.json (eps=0.10  max_k=32)
51b12f5ebdc6a8f213b8520a7dfbcc52  p4.json (eps=0.40  max_k=2)
51b12f5ebdc6a8f213b8520a7dfbcc52  v3.json  (model v3, hidden=64,  20 traj)
51b12f5ebdc6a8f213b8520a7dfbcc52  v3b.json (model v3b, hidden=64, 100 traj)
51b12f5ebdc6a8f213b8520a7dfbcc52  v4.json  (model v4, hidden=128, 100 traj)
```

7 different (model, eps, max_k) combinations all produce the EXACT same
board. The hyperparameters and model file had zero effect because the
ML code was never executed. The board is just `--mode insertion`'s
fixed point under joe_depth150_bp on canonical 5-clue.

After the fix, distinct partials appear:
- `edge_bp_165.json` md5 = `4a08323a326453fcc7eee7adbc6d5ccb`
- `insertion_174.json` md5 = `51b12f5ebdc6a8f213b8520a7dfbcc52` (same as buggy LOT)
- `lot_fixed_v4.json` md5 = `e4097ef94c99aef868e1211d61955143` (NEW, real LOT)

## Score implications

| Partial | placed/256 | matched/480 (internal edges) |
|---|---:|---:|
| `edge_bp_165` (baseline) | 170 | 280 |
| `insertion_174` (vol-30/31's "ML" partial) | 179 | 303 |
| `lot_fixed_v4` (true LOT post-fix) | 170 | **283** (+3 vs baseline) |

Vol-31's reported "303 initial edges from depth-174 partial" was real,
just not from ML — it was from InsertionOrder bypassing BP sort. The
true LearnedOnTies (post-fix) gives +3 edges over baseline at the same
depth (165) — that's the *real* ML lift, much smaller than the
incorrectly-attributed +23 (303 - 280).

## What the corrected vol-30/31 results imply for prior conclusions

| Claim from vol-30/31 | Actual cause | Correct attribution |
|---|---|---|
| "+9 depth from LearnedOnTies" | InsertionOrder is the better value-order under joe_depth150_bp | Engine: InsertionOrder > EdgeBpMarginals under heavy propagators |
| "Lift invariant across v3/v3b/v4" | The model wasn't called in any case | Confirms ML wasn't doing anything |
| "+10 score (alns_only 5min)" | Better starting partial (303 vs 280 edges) | InsertionOrder-driven, not ML |
| "+8 score (pt_e2 15min)" | Same — better starting partial | Same |

## Implications for prior vol research

- The vol-30 LearnedOnTies finding (+9 depth invariance across models)
  is **fully refuted**. The model was never engaged. All three models
  produced identical results because they all triggered the same fall-
  through to InsertionOrder.
- The vol-31 score result (445 from depth-174 partial) is **real**
  but mis-attributed. PT-15min from this partial really does reach
  445; the partial just isn't an ML artifact.
- The vol-29 imitation-ceiling result (Δ=−1) is **unaffected** — that
  used `--mode learned` which goes through a different code path
  (lib.rs:4118) and was correctly calling the NN.
- The genuine ML signal at canonical is the **+3 edges from depth-165
  fixed LearnedOnTies**, much smaller than previously claimed.

## What still works

- The bug fix is one line. Post-fix LearnedOnTies actually calls the
  model.
- `LOT_TRACE` instrumentation confirms post-fix LOT fires ~10k times
  per 60s run. Tie-cluster sizes are mostly 2-3 with occasional 4-8.
- The pre-fix "InsertionOrder beats EdgeBpMarginals by +9" is now an
  open question worth investigating: why is BP-as-value-order *worse*
  here, when vol-12 measured BP as helping?

## Cleanest path forward

1. **Ship the fix** in a vol-32 commit.
2. **Re-measure** the actual LearnedOnTies lift at multiple budgets
   (already done above for 60s → +0 depth, +3 edges).
3. **Rerun T3 PT lottery** from the *real* partials post-fix.
4. **Investigate InsertionOrder vs EdgeBpMarginals**: under
   `joe_depth150_bp`, InsertionOrder reaches depth 174 vs EdgeBp's 165.
   This is a +9 axis for FREE that previously got attributed to ML.
5. **Update vol-29/30/31 vault entries** with correction notes.
6. **Memory entry** for the bug.
