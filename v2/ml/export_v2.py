"""Export a trained PositionRelativeModel to ONNX with dynamic shapes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
import numpy as np

from model_v2 import (
    PositionRelativeModel,
    build_neighbour_indices,
    build_valid_mask,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="runs/v2/model.pt")
    ap.add_argument("--out", default="runs/v2/model.onnx")
    ap.add_argument("--example-size", type=int, default=6)
    ap.add_argument("--example-cands", type=int, default=12)
    args = ap.parse_args()

    payload = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    hidden = int(payload.get("hidden", 64))
    color_emb = int(payload.get("color_emb", 16))
    m = PositionRelativeModel(hidden=hidden, color_emb=color_emb)
    m.load_state_dict(payload["state_dict"])
    m.eval()

    W = H = args.example_size
    N = W * H
    nb = build_neighbour_indices(W, H)
    vm = build_valid_mask(W, H)
    feats = torch.randn(1, N, 13)
    feats[..., 0:4] = feats[..., 0:4].abs().clamp(0, 22)
    tp = torch.zeros(1, dtype=torch.long)
    cand = torch.zeros(1, args.example_cands, 4, dtype=torch.long)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        m,
        (feats, nb, vm, tp, cand),
        str(out_path),
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

    meta = {"hidden": hidden, "color_emb": color_emb, "version": 2}
    Path(str(out_path) + ".meta.json").write_text(json.dumps(meta))
    print(f"exported {out_path}, size {os.path.getsize(out_path)} bytes")

    import onnxruntime as ort
    sess = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
    for ex_w in (6, 16):
        ex_n = ex_w * ex_w
        nb_e = build_neighbour_indices(ex_w, ex_w).numpy()
        vm_e = build_valid_mask(ex_w, ex_w).numpy()
        feats_e = np.random.randn(1, ex_n, 13).astype(np.float32)
        feats_e[..., 0:4] = np.abs(feats_e[..., 0:4]).clip(0, 22)
        tp_e = np.zeros(1, dtype=np.int64)
        cand_e = np.zeros((1, 8, 4), dtype=np.int64)
        out = sess.run(["scores"], {
            "feats": feats_e,
            "nb_idx": nb_e,
            "valid_mask": vm_e,
            "target_pos": tp_e,
            "cand_edges": cand_e,
        })
        print(f"  {ex_w}x{ex_w} forward ok: scores shape={out[0].shape}")


if __name__ == "__main__":
    main()
