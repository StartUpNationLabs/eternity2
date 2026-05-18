"""Train the BoardTransformer on database-400-480 with masked-cell prediction.

Usage:
    python3 train.py [--epochs 50] [--batch-size 16] [--min-score 440]
"""

import argparse
import math
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split

sys.path.insert(0, str(Path(__file__).parent))
from model import BoardTransformer, N_PIECES, N_ROTATIONS
from data import BoardMaskedDataset, load_boards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--min-score", type=int, default=440)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--layers", type=int, default=4)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--checkpoint-dir", type=str, default="runs/v1")
    args = ap.parse_args()

    ckpt_dir = Path(__file__).parent / args.checkpoint_dir
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    print("Loading boards...", flush=True)
    boards = load_boards(min_score=args.min_score)
    print(f"  loaded {len(boards)} boards with score >= {args.min_score}", flush=True)
    if not boards:
        sys.exit("no boards")

    # 90/10 split
    n_train = int(0.9 * len(boards))
    n_val = len(boards) - n_train
    print(f"  train: {n_train}, val: {n_val}", flush=True)

    full_ds = BoardMaskedDataset(boards)
    train_ds, val_ds = random_split(full_ds, [n_train, n_val], generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)

    model = BoardTransformer(n_layers=args.layers, n_heads=args.heads, hidden_dim=args.hidden).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}", flush=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_loss = float("inf")
    for epoch in range(args.epochs):
        model.train()
        t0 = time.time()
        train_loss_sum = 0.0
        train_correct_piece = 0
        train_correct_both = 0
        train_n = 0
        for batch in train_loader:
            pieces = batch["pieces"].to(device)
            rotations = batch["rotations"].to(device)
            t_piece = batch["targets_piece"].to(device)
            t_rot = batch["targets_rot"].to(device)
            weight = batch["weight"].to(device)

            logits = model(pieces, rotations)  # [B, 256, P*R]
            B, N, C = logits.shape
            # Combined target: piece * N_ROTATIONS + rotation
            combined_target = t_piece * N_ROTATIONS + t_rot
            valid_mask = (t_piece >= 0)
            # Cross-entropy only on valid (masked) positions.
            logits_flat = logits.view(B * N, C)
            target_flat = combined_target.view(B * N)
            loss_per_pos = F.cross_entropy(logits_flat, target_flat.clamp(min=0), reduction="none")
            loss_per_pos = loss_per_pos.view(B, N)
            loss_per_pos = loss_per_pos * valid_mask.float()
            n_valid_per_b = valid_mask.float().sum(dim=1).clamp(min=1.0)
            loss_per_b = loss_per_pos.sum(dim=1) / n_valid_per_b
            loss = (loss_per_b * weight).mean()

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss_sum += loss.item() * B
            with torch.no_grad():
                preds = logits.argmax(dim=-1)  # [B, 256] combined index
                pred_piece = preds // N_ROTATIONS
                pred_rot = preds % N_ROTATIONS
                valid = (t_piece >= 0)
                train_correct_piece += ((pred_piece == t_piece) & valid).sum().item()
                train_correct_both += (((pred_piece == t_piece) & (pred_rot == t_rot)) & valid).sum().item()
                train_n += valid.sum().item()

        # Validation
        model.eval()
        val_loss_sum = 0.0
        val_correct_piece = 0
        val_correct_both = 0
        val_n = 0
        with torch.no_grad():
            for batch in val_loader:
                pieces = batch["pieces"].to(device)
                rotations = batch["rotations"].to(device)
                t_piece = batch["targets_piece"].to(device)
                t_rot = batch["targets_rot"].to(device)
                weight = batch["weight"].to(device)

                logits = model(pieces, rotations)
                B, N, C = logits.shape
                combined_target = t_piece * N_ROTATIONS + t_rot
                valid_mask = (t_piece >= 0)
                logits_flat = logits.view(B * N, C)
                target_flat = combined_target.view(B * N)
                loss_per_pos = F.cross_entropy(logits_flat, target_flat.clamp(min=0), reduction="none")
                loss_per_pos = loss_per_pos.view(B, N) * valid_mask.float()
                n_valid_per_b = valid_mask.float().sum(dim=1).clamp(min=1.0)
                loss_per_b = loss_per_pos.sum(dim=1) / n_valid_per_b
                loss = (loss_per_b * weight).mean()
                val_loss_sum += loss.item() * B
                preds = logits.argmax(dim=-1)
                pred_piece = preds // N_ROTATIONS
                pred_rot = preds % N_ROTATIONS
                valid = (t_piece >= 0)
                val_correct_piece += ((pred_piece == t_piece) & valid).sum().item()
                val_correct_both += (((pred_piece == t_piece) & (pred_rot == t_rot)) & valid).sum().item()
                val_n += valid.sum().item()

        scheduler.step()

        train_avg_loss = train_loss_sum / max(n_train, 1)
        val_avg_loss = val_loss_sum / max(n_val, 1)
        train_acc_p = train_correct_piece / max(train_n, 1) * 100
        train_acc_b = train_correct_both / max(train_n, 1) * 100
        val_acc_p = val_correct_piece / max(val_n, 1) * 100
        val_acc_b = val_correct_both / max(val_n, 1) * 100
        elapsed = time.time() - t0
        print(f"epoch {epoch+1:3d}/{args.epochs}  "
              f"train_loss={train_avg_loss:.3f} val_loss={val_avg_loss:.3f}  "
              f"train_acc_p={train_acc_p:.1f}% acc_pr={train_acc_b:.1f}%  "
              f"val_acc_p={val_acc_p:.1f}% acc_pr={val_acc_b:.1f}%  "
              f"({elapsed:.1f}s)", flush=True)

        if val_avg_loss < best_val_loss:
            best_val_loss = val_avg_loss
            torch.save({
                "model": model.state_dict(),
                "epoch": epoch,
                "val_loss": val_avg_loss,
                "args": vars(args),
            }, ckpt_dir / "best.pt")

    # Save final.
    torch.save({"model": model.state_dict(), "args": vars(args)}, ckpt_dir / "final.pt")
    print(f"Done. Best val loss: {best_val_loss:.3f}")
    print(f"Checkpoints in {ckpt_dir}")


if __name__ == "__main__":
    main()
