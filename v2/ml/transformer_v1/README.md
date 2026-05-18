# transformer_v1 — Vol-125 T42a-extended

A board-completion transformer trained on our 1278-board database
(`database-400-480/`). Goal: provide a learned **piece-at-position prior**
that ALNS can query to bias its repair toward likely good completions.

## Architecture

- **Input**: 256 cells, each encoded as (piece_id, rotation) or "empty".
  Also a target position to predict.
- **Embedding**: piece_id ∈ {0..255, EMPTY=256} → 64-dim. Rotation ∈ {0..3, NONE=4} → 16-dim. Position ∈ {0..255} → 32-dim. Concat → 112-dim per cell.
- **Transformer encoder**: 4 layers, 4 heads, hidden 128. Standard
  multi-head self-attention across 256 cells.
- **Output head**: takes the encoded target cell representation, predicts
  logits over (piece_id × rotation) = 256 × 4 = 1024 classes.

## Training data

1278 boards from `database-400-480/`. Each board × 256 positions = ~327k
training examples. Mask out a random subset of cells, predict the masked
ones from context.

## Loss

Cross-entropy on (piece, rotation) prediction at masked cells, scaled by
the score of the source board (higher-scoring boards weighted more).

## Integration

Once trained, expose as a Python service via stdio JSON (like
`ml/infer_bridge.py` already does for vol-26). ALNS calls it for repair
guidance: given a board with K free cells, get top-K piece+rotation
predictions per cell.

## Files

- `model.py` — transformer architecture
- `data.py` — DB loading + masking
- `train.py` — training loop
- `infer.py` — inference + stdio interface
- `runs/v1/` — trained checkpoints (gitignored)
