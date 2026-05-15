"""ES perturbation: load a v2 model checkpoint, add Gaussian noise to
weights, export the perturbed model to ONNX.

Usage:
  python es_perturb.py --base runs/v3/model.pt --out runs/es/perturbed_001 \
                       --sigma 0.01 --seed 1

Produces:
  <out>/model.pt  (perturbed checkpoint)
  <out>/model.onnx, model.onnx.data, model.onnx.meta.json (engine-ready)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
import numpy as np

from model_v2 import PositionRelativeModel, build_neighbour_indices, build_valid_mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Path to base model.pt")
    ap.add_argument("--out", required=True, help="Output dir for perturbed model + onnx")
    ap.add_argument("--sigma", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--example-size", type=int, default=16)
    ap.add_argument("--example-cands", type=int, default=128)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = torch.load(args.base, map_location="cpu", weights_only=False)
    hidden = int(payload.get("hidden", 64))
    color_emb = int(payload.get("color_emb", 16))

    model = PositionRelativeModel(hidden=hidden, color_emb=color_emb)
    model.load_state_dict(payload["state_dict"])
    model.eval()

    # Perturb each parameter tensor with seeded Gaussian noise.
    rng = np.random.RandomState(args.seed)
    perturbed_state = {}
    for name, p in model.state_dict().items():
        noise = torch.tensor(rng.randn(*p.shape).astype(np.float32)) * args.sigma
        perturbed_state[name] = p + noise
    model.load_state_dict(perturbed_state)

    # Save .pt
    new_payload = dict(payload)
    new_payload["state_dict"] = model.state_dict()
    torch.save(new_payload, out_dir / "model.pt")

    # Export ONNX. Use same shapes as export_v2.py.
    W = H = args.example_size
    N = W * H
    nb = build_neighbour_indices(W, H)
    vm = build_valid_mask(W, H)
    feats = torch.randn(1, N, 13)
    feats[..., 0:4] = feats[..., 0:4].abs().clamp(0, 22)
    tp = torch.zeros(1, dtype=torch.long)
    cand = torch.zeros(1, args.example_cands, 4, dtype=torch.long)

    onnx_path = out_dir / "model.onnx"
    torch.onnx.export(
        model,
        (feats, nb, vm, tp, cand),
        str(onnx_path),
        input_names=["feats", "nb_idx", "valid_mask", "target_pos", "cand_edges"],
        output_names=["scores"],
        dynamic_axes={
            "feats": {0: "batch", 1: "n_cells"},
            "nb_idx": {0: "n_cells"},
            "valid_mask": {0: "n_cells"},
            "target_pos": {0: "batch"},
            "cand_edges": {0: "batch", 1: "n_cands"},
            "scores": {0: "batch", 1: "n_cands"},
        },
        opset_version=17,
    )
    # Meta JSON.
    meta = {"hidden": hidden, "color_emb": color_emb, "version": 2}
    with open(out_dir / "model.onnx.meta.json", "w") as f:
        json.dump(meta, f)

    print(f"Wrote {out_dir}/model.pt and {onnx_path}")
    print(f"Perturbation: sigma={args.sigma}, seed={args.seed}")


if __name__ == "__main__":
    main()
