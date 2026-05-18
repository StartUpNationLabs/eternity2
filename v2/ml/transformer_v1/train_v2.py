"""Train the v2 edge-based transformer on synthetic E2-family puzzles.

This is the right architecture for our problem: predict the 4 edge colors
at each masked cell given the partial board. Trains on unlimited synthetic
data, transfers to canonical E2.

Usage:
    python3 train_v2.py [--epochs 100] [--samples-per-epoch 2000] [--batch-size 16]
"""

import argparse
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent))
from model_v2 import EdgeBoardTransformer, N_CELLS, N_COLORS, EMPTY_COLOR
from data_edges import EdgeBoardDataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--samples-per-epoch", type=int, default=2000)
    ap.add_argument("--val-samples", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--n-colors", type=int, default=22)
    ap.add_argument("--mask-min", type=int, default=8)
    ap.add_argument("--mask-max", type=int, default=128)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--checkpoint-dir", type=str, default="runs/v2_edges")
    ap.add_argument("--curriculum", action="store_true",
                    help="Start with small masks, gradually increase.")
    args = ap.parse_args()

    ckpt_dir = Path(__file__).parent / args.checkpoint_dir
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)

    model = EdgeBoardTransformer(n_layers=args.layers, n_heads=args.heads, hidden_dim=args.hidden).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}", flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_loss = float("inf")
    for epoch in range(args.epochs):
        # Curriculum: start with small masks (easier), accelerate.
        # New formula: spend first 20% at mask_max=16 (warmup), then linear
        # ramp to args.mask_max over remaining 80%.
        if args.curriculum:
            frac = (epoch + 1) / args.epochs
            warmup = 0.2
            if frac < warmup:
                mask_max = 16
            else:
                ramp = (frac - warmup) / (1.0 - warmup)
                mask_max = int(16 + ramp * (args.mask_max - 16))
        else:
            mask_max = args.mask_max

        train_ds = EdgeBoardDataset(
            n_colors=args.n_colors,
            mask_min=args.mask_min,
            mask_max=mask_max,
            samples_per_epoch=args.samples_per_epoch,
            seed=epoch * 100,
        )
        val_ds = EdgeBoardDataset(
            n_colors=args.n_colors,
            mask_min=args.mask_min,
            mask_max=mask_max,
            samples_per_epoch=args.val_samples,
            seed=epoch * 100 + 50,
        )
        train_loader = DataLoader(train_ds, batch_size=args.batch_size, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=args.batch_size, num_workers=0)

        model.train()
        t0 = time.time()
        train_loss_sum = 0.0
        train_n_batches = 0
        train_correct = 0
        train_total = 0
        for batch in train_loader:
            input_edges = batch["input_edges"].to(device)        # [B, 256, 4]
            target_edges = batch["target_edges"].to(device)      # [B, 256, 4]
            target_mask = batch["target_mask"].to(device)        # [B, 256]

            logits = model(input_edges)  # [B, 256, 4, N_COLORS]
            B = input_edges.shape[0]
            # Cross-entropy over color per (cell, edge). Only at masked cells.
            logits_flat = logits.view(B * N_CELLS * 4, N_COLORS)
            targets_flat = target_edges.view(B * N_CELLS * 4)
            # mask: [B, 256, 4] = target_mask broadcast
            mask_flat = target_mask.unsqueeze(-1).expand(B, N_CELLS, 4).reshape(-1)
            loss_per_edge = F.cross_entropy(logits_flat, targets_flat, reduction="none")
            loss_per_edge = loss_per_edge * mask_flat.float()
            loss = loss_per_edge.sum() / max(mask_flat.float().sum().item(), 1.0)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss_sum += loss.item()
            train_n_batches += 1

            with torch.no_grad():
                preds = logits.argmax(dim=-1)  # [B, 256, 4]
                mask_flat_3d = target_mask.unsqueeze(-1).expand(B, N_CELLS, 4)
                train_correct += ((preds == target_edges) & mask_flat_3d).sum().item()
                train_total += mask_flat_3d.sum().item()

        # Val
        model.eval()
        val_loss_sum = 0.0
        val_n_batches = 0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch in val_loader:
                input_edges = batch["input_edges"].to(device)
                target_edges = batch["target_edges"].to(device)
                target_mask = batch["target_mask"].to(device)
                logits = model(input_edges)
                B = input_edges.shape[0]
                logits_flat = logits.view(B * N_CELLS * 4, N_COLORS)
                targets_flat = target_edges.view(B * N_CELLS * 4)
                mask_flat = target_mask.unsqueeze(-1).expand(B, N_CELLS, 4).reshape(-1)
                loss_per_edge = F.cross_entropy(logits_flat, targets_flat, reduction="none")
                loss_per_edge = loss_per_edge * mask_flat.float()
                loss = loss_per_edge.sum() / max(mask_flat.float().sum().item(), 1.0)
                val_loss_sum += loss.item()
                val_n_batches += 1
                preds = logits.argmax(dim=-1)
                mask_flat_3d = target_mask.unsqueeze(-1).expand(B, N_CELLS, 4)
                val_correct += ((preds == target_edges) & mask_flat_3d).sum().item()
                val_total += mask_flat_3d.sum().item()

        scheduler.step()
        train_avg = train_loss_sum / max(train_n_batches, 1)
        val_avg = val_loss_sum / max(val_n_batches, 1)
        train_acc = train_correct / max(train_total, 1) * 100
        val_acc = val_correct / max(val_total, 1) * 100
        elapsed = time.time() - t0
        print(f"epoch {epoch+1:3d}/{args.epochs}  "
              f"mask_max={mask_max:3d}  "
              f"train_loss={train_avg:.4f}  val_loss={val_avg:.4f}  "
              f"train_acc={train_acc:.2f}%  val_acc={val_acc:.2f}%  ({elapsed:.1f}s)",
              flush=True)

        if val_avg < best_val_loss:
            best_val_loss = val_avg
            torch.save({
                "model": model.state_dict(),
                "epoch": epoch,
                "val_loss": val_avg,
                "args": vars(args),
            }, ckpt_dir / "best.pt")

    torch.save({"model": model.state_dict(), "args": vars(args)}, ckpt_dir / "final.pt")
    print(f"Done. Best val loss: {best_val_loss:.4f}")
    print(f"Checkpoints in {ckpt_dir}")


if __name__ == "__main__":
    main()
