"""One ES round: sample N perturbations, run each through engine, collect rewards,
compute parameter update.

Usage:
  python es_round.py --base runs/v3/model.pt --out runs/es/round_001 \
                     --n 20 --sigma 0.01 --lr 0.01 --budget-ms 60000 \
                     --parallel 4

Produces:
  <out>/perturbations/ — N perturbed model dirs (.pt + .onnx)
  <out>/rewards.json — per-perturbation results
  <out>/updated_model.pt — base + ES update
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import torch

from model_v2 import PositionRelativeModel, build_neighbour_indices, build_valid_mask


def export_perturbed(base_state, hidden, color_emb, noise_seed, sigma, out_dir, example_size=16, example_cands=128):
    """Apply Gaussian noise to base_state, save model.pt + model.onnx in out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.RandomState(noise_seed)
    new_state = {}
    noise_dict = {}
    for name, p in base_state.items():
        n = torch.tensor(rng.randn(*p.shape).astype(np.float32)) * sigma
        new_state[name] = p + n
        noise_dict[name] = n  # save for ES update

    model = PositionRelativeModel(hidden=hidden, color_emb=color_emb)
    model.load_state_dict(new_state)
    model.eval()

    torch.save({
        "state_dict": new_state,
        "hidden": hidden,
        "color_emb": color_emb,
    }, out_dir / "model.pt")

    # ONNX export.
    W = H = example_size
    N = W * H
    nb = build_neighbour_indices(W, H)
    vm = build_valid_mask(W, H)
    feats = torch.randn(1, N, 13)
    feats[..., 0:4] = feats[..., 0:4].abs().clamp(0, 22)
    tp = torch.zeros(1, dtype=torch.long)
    cand = torch.zeros(1, example_cands, 4, dtype=torch.long)

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
    meta = {"hidden": hidden, "color_emb": color_emb, "version": 2}
    with open(str(onnx_path) + ".meta.json", "w") as f:
        json.dump(meta, f)

    return noise_dict


def run_episode(onnx_path, seed, budget_ms):
    """Run engine with the given model. Returns dict with outcome."""
    env = os.environ.copy()
    env["E2_LEARNED_MODEL"] = str(onnx_path)
    cmd = [
        "./target/release/run_learned",
        "--seed", str(seed),
        "--budget-ms", str(budget_ms),
    ]
    # Run from project root.
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env, cwd=str(project_root),
    )
    if result.returncode != 0:
        return {"error": result.stderr[-500:], "matched": 0, "placed": 0}
    last = result.stdout.strip().split("\n")[-1]
    try:
        return json.loads(last)
    except Exception:
        return {"error": f"parse fail: {last}", "matched": 0, "placed": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--sigma", type=float, default=0.01)
    ap.add_argument("--lr", type=float, default=0.01)
    ap.add_argument("--budget-ms", type=int, default=60000)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--round-seed", type=int, default=1)
    ap.add_argument("--reward", choices=["depth", "matched"], default="matched")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    perturb_dir = out_dir / "perturbations"
    perturb_dir.mkdir(exist_ok=True)

    # Load base.
    payload = torch.load(args.base, map_location="cpu", weights_only=False)
    hidden = int(payload.get("hidden", 64))
    color_emb = int(payload.get("color_emb", 16))
    base_state = payload["state_dict"]

    # Generate perturbations and noise dicts.
    noise_dicts = []
    onnx_paths = []
    for i in range(args.n):
        seed = args.round_seed * 1000 + i
        nd = export_perturbed(
            base_state, hidden, color_emb, seed, args.sigma,
            perturb_dir / f"p_{i:03d}",
        )
        noise_dicts.append(nd)
        onnx_paths.append(perturb_dir / f"p_{i:03d}" / "model.onnx")
        print(f"perturbed {i+1}/{args.n}")

    # Run episodes in parallel.
    print(f"Running {args.n} episodes (parallel={args.parallel})...")
    rewards = [None] * args.n
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {
            ex.submit(run_episode, onnx_paths[i], args.round_seed * 100 + i, args.budget_ms): i
            for i in range(args.n)
        }
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                r = fut.result()
                if args.reward == "depth":
                    rewards[i] = float(r.get("placed", 0))
                else:
                    rewards[i] = float(r.get("matched", 0))
                print(f"  episode {i}: matched={r.get('matched', 0)} placed={r.get('placed', 0)}")
            except Exception as e:
                rewards[i] = 0.0
                print(f"  episode {i} ERROR: {e}")

    # Save rewards.
    with open(out_dir / "rewards.json", "w") as f:
        json.dump({"rewards": rewards, "args": vars(args)}, f, indent=2)
    print(f"Rewards saved: mean={np.mean(rewards):.2f}  std={np.std(rewards):.2f}  max={max(rewards):.2f}")

    # ES update: θ_new = θ + (lr / (N · σ)) · Σ_i (R_i - mean) · noise_i
    r = np.array(rewards, dtype=np.float32)
    centered = (r - r.mean()) / (r.std() + 1e-8)
    new_state = {}
    for name, p in base_state.items():
        update = torch.zeros_like(p)
        for i in range(args.n):
            update = update + centered[i] * noise_dicts[i][name]
        update = update * (args.lr / (args.n * args.sigma))
        new_state[name] = p + update

    # Save updated model.
    torch.save({
        "state_dict": new_state,
        "hidden": hidden,
        "color_emb": color_emb,
    }, out_dir / "updated_model.pt")
    print(f"Updated model saved: {out_dir / 'updated_model.pt'}")


if __name__ == "__main__":
    main()
