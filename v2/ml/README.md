# ml/ — vol-26 learned value-order gate

Day-1 gate for the diffusion-on-edge-matching direction. Question: does a
small imitation-learning model trained on synthetic E2-family puzzles
produce a value-ordering that beats `BorderFirstMRV + LeastConstraining`
at 6×6/5-color?

## Pipeline

```
crates/generator (Rust)
    → crates/ml-export gen-export bin
        → ml/data/{train,test}_6x6_5c.jsonl
            → ml/train.py  →  ml/runs/v1/model.pt
                → ml/evaluate.py
                    → crates/ml-export bench-eval bin (engine + ValueOrder::Learned)
                        → ml/infer_bridge.py (stdio JSON)
```

The synthetic puzzles come from the existing Rust generator
(`eternity2-generator`), not a Python re-implementation. That keeps the
generator as a single source of truth.

## Files

- `selby_riordan.py` — NOT REIMPLEMENTED. The vol-26 plan called for a
  Python re-implementation; we use the existing Rust generator instead
  (see `vault/concepts/synthetic-puzzle-generator.md` for the rationale).
- `dataset.py` — load the JSONL and produce `(state, target_pos, target_action)` tuples.
- `model.py` — small GNN (~53 k params at 6×6) with 2 grid-conv layers.
- `train.py` — imitation training loop; CPU by default (MPS has gather/Adam quirks at this scale).
- `infer_bridge.py` — stdio JSON inference subprocess; spawned by the Rust engine.
- `evaluate.py` — runs the gate: MRV baseline vs Learned, prints PASS/FAIL.

## Run

Generate data (from `v2/`):

```bash
cargo build --release -p eternity2-ml-export
./target/release/gen-export --out ml/data/train_6x6_5c.jsonl --seeds 1..10001 --size 6 --colors 5
./target/release/gen-export --out ml/data/test_6x6_5c.jsonl  --seeds 100000..100200 --size 6 --colors 5
```

Train (from `ml/`):

```bash
E2_ML_DEVICE=cpu uv run python train.py \
    --data data/train_6x6_5c.jsonl \
    --out runs/v1/model.pt \
    --epochs 5 --batch-size 1024 --lr 1e-3
```

Evaluate (from `ml/`):

```bash
E2_LEARNED_MODEL=runs/v1/model.pt uv run python evaluate.py
```

`evaluate.py` returns exit 0 on gate-pass, exit 1 on gate-fail. The full
metrics are written to `runs/v1/gate.json`.
