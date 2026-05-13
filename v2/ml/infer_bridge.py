"""Vol-26 stdio inference bridge: speak the JSON protocol described in
`crates/solver-engine/src/bridge.rs` to score candidate placements.

Protocol:
  startup -> writes {"ready": true, "model": <path>}
  loop:
    read one line of {"feats": [[...]], "target_pos": int, "candidates": [[piece_id, rotation], ...]}
    OR {"shutdown": true}  -> exit cleanly
    write one line of {"scores": [float, ...]} matching candidates length.

The model expects feats shape (N, 13) — a single 6×6/5c board. Other sizes
are rejected with {"scores": []} so the Rust side falls back to insertion
order without crashing the run.

The model file is read from env var `E2_LEARNED_MODEL` (default
runs/v1/model.pt).
"""

from __future__ import annotations

import json
import os
import sys

import torch

from model import PlacementModel


def emit(obj):
    sys.stdout.write(json.dumps(obj))
    sys.stdout.write("\n")
    sys.stdout.flush()


def load_model(path: str):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    size = int(payload["size"])
    n_pieces = int(payload["n_pieces"])
    hidden = int(payload.get("hidden", 64))
    m = PlacementModel(size=size, n_pieces=n_pieces, hidden=hidden)
    m.load_state_dict(payload["state_dict"])
    m.eval()
    return m, size, n_pieces


def main():
    model_path = os.environ.get("E2_LEARNED_MODEL", "runs/v1/model.pt")
    try:
        model, size, n_pieces = load_model(model_path)
    except Exception as exc:  # noqa: BLE001 - we want to report any failure
        emit({"error": f"load_model failed: {exc!r}"})
        return
    emit({"ready": True, "model": model_path, "size": size, "n_pieces": n_pieces})

    # Inference is cheap; keep on CPU. MPS adds first-call latency that hurts
    # the per-node budget.
    device = torch.device("cpu")
    model.to(device)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            emit({"scores": []})
            continue
        if req.get("shutdown"):
            return

        feats = req.get("feats")
        target_pos = req.get("target_pos")
        candidates = req.get("candidates")
        if not isinstance(feats, list) or len(feats) != size * size:
            emit({"scores": []})
            continue
        if not isinstance(candidates, list):
            emit({"scores": []})
            continue

        try:
            feat_t = torch.tensor(feats, dtype=torch.float32, device=device).unsqueeze(0)
            tp_t = torch.tensor([int(target_pos)], dtype=torch.long, device=device)
            with torch.no_grad():
                logits = model(feat_t, tp_t)[0]  # (n_actions,)
            # Convert candidates to flat action indices and gather scores.
            scores = []
            for c in candidates:
                pid = int(c[0])
                rot = int(c[1])
                action = pid * 4 + rot
                if 0 <= action < logits.size(0):
                    scores.append(float(logits[action].item()))
                else:
                    scores.append(float("-inf"))
            emit({"scores": scores})
        except Exception as exc:  # noqa: BLE001
            emit({"error": f"infer failed: {exc!r}", "scores": []})


if __name__ == "__main__":
    main()
