#!/usr/bin/env python3
"""V177 NEURONIC — train a tiny MLP on board features.

Features (from extract_features.py):
  prior_norm, n_unsupported, mismatch_count, mismatch_components,
  border_spec[8], used_corner_r, used_edge_r, used_interior_r

Target: matched score.

Architecture: 2-layer MLP, ~50 hidden units, ReLU, dropout, MSE loss.

Compare to OLS R²=0.24 baseline.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

REPO = Path(__file__).resolve().parents[2]


def load_features(path):
    feats = []
    with open(path) as f:
        for line in f:
            feats.append(json.loads(line))
    return feats


def feature_matrix(feats):
    X = []
    y = []
    for d in feats:
        if d.get('n_placed', 0) != 256: continue
        if d.get('matched') is None: continue
        if len(d.get('border_spec', [])) != 8: continue
        v = [
            d['prior_sum'] / max(d['n_placed'], 1),  # prior_norm
            d['n_unsupported'],
            d['mismatch_count'],
            d['mismatch_components'],
        ] + d['border_spec']
        X.append(v)
        y.append(d['matched'])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', default='output/vol-177/features.jsonl')
    ap.add_argument('--out', default='output/vol-177/mlp_model.json')
    ap.add_argument('--hidden', type=int, default=32)
    ap.add_argument('--max-iter', type=int, default=500)
    ap.add_argument('--folds', type=int, default=5)
    args = ap.parse_args()

    feats = load_features(REPO / args.features)
    print(f"Loaded {len(feats)} feature vectors")

    X, y = feature_matrix(feats)
    print(f"X shape: {X.shape}, y range: [{y.min()}, {y.max()}]")

    # K-fold CV.
    kf = KFold(n_splits=args.folds, shuffle=True, random_state=42)
    fold_r2 = []
    for fold, (tr, te) in enumerate(kf.split(X)):
        X_tr, X_te = X[tr], X[te]
        y_tr, y_te = y[tr], y[te]
        scaler = StandardScaler().fit(X_tr)
        X_tr_s = scaler.transform(X_tr)
        X_te_s = scaler.transform(X_te)
        mlp = MLPRegressor(
            hidden_layer_sizes=(args.hidden,),  # single hidden layer
            activation='relu',
            solver='adam',
            alpha=1e-1,  # stronger L2 to prevent overfit
            learning_rate_init=1e-3,
            max_iter=args.max_iter,
            random_state=42 + fold,
            early_stopping=True,
            validation_fraction=0.15,
            tol=1e-5,
            n_iter_no_change=20,
        )
        mlp.fit(X_tr_s, y_tr)
        y_pred = mlp.predict(X_te_s)
        ss_res = ((y_te - y_pred) ** 2).sum()
        ss_tot = ((y_te - y_te.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot
        fold_r2.append(r2)
        print(f"  Fold {fold}: R²={r2:.4f}, iters={mlp.n_iter_}")

    print(f"Mean R² across {args.folds} folds: {np.mean(fold_r2):.4f}  std: {np.std(fold_r2):.4f}")
    print(f"vs OLS R²=0.24")

    # Train final model on all data.
    scaler = StandardScaler().fit(X)
    X_s = scaler.transform(X)
    final = MLPRegressor(
        hidden_layer_sizes=(args.hidden,),
        activation='relu',
        solver='adam',
        alpha=1e-1,
        learning_rate_init=1e-3,
        max_iter=args.max_iter,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        tol=1e-5,
        n_iter_no_change=20,
    )
    final.fit(X_s, y)
    print(f"Final model: {final.n_iter_} iters, train R²={final.score(X_s, y):.4f}")

    # Feature importance via permutation (cheap, on held-out 20%).
    n = len(X)
    np.random.seed(42)
    idx = np.random.permutation(n)
    holdout = idx[:n // 5]
    X_h = X_s[holdout]
    y_h = y[holdout]
    y_pred = final.predict(X_h)
    base_mse = ((y_h - y_pred) ** 2).mean()
    names = ['prior_norm', 'n_unsupported', 'mismatch_count', 'mismatch_components',
             'spec_k5', 'spec_k7', 'spec_k12', 'spec_k13',
             'spec_k16', 'spec_k19', 'spec_k26', 'spec_k29']
    print(f"\nPermutation importance (Δ MSE when feature shuffled):")
    importances = []
    for i, name in enumerate(names[:X.shape[1]]):
        X_shuf = X_h.copy()
        np.random.shuffle(X_shuf[:, i])
        y_pred_shuf = final.predict(X_shuf)
        mse_shuf = ((y_h - y_pred_shuf) ** 2).mean()
        importances.append((name, mse_shuf - base_mse))
    importances.sort(key=lambda x: -x[1])
    for name, imp in importances:
        bar = '*' * min(int(imp / 10), 50)
        print(f"  {name:>20}: {imp:>+8.2f}  {bar}")

    # Save model as JSON (weights + scaler).
    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        'mean_r2': float(np.mean(fold_r2)),
        'fold_r2': [float(r) for r in fold_r2],
        'hidden': args.hidden,
        'feature_names': names[:X.shape[1]],
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
        # MLP weights
        'layers': [
            {'W': layer.tolist(), 'b': b.tolist()}
            for layer, b in zip(final.coefs_, final.intercepts_)
        ],
    }, indent=2))
    print(f"\nSaved model to {out_path}")


if __name__ == '__main__':
    main()
