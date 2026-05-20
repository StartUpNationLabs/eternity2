#!/usr/bin/env python3
"""V177 NEURONIC PROMISE SCORE — rank partial/intermediate boards by
predicted lift potential.

NOT a NN yet. A simple linear combination of features identified in
the V177 corpus analysis:

  promise(b) = score(b)
             + α_prior * (prior_sum(b) / n_placed(b))      # avg corpus support
             - α_unsup * n_unsupported(b)                  # penalize OOD cells
             - α_mc    * mismatch_components(b)            # fewer = more recoverable
             + α_spec  * (border_spec[k=12] + border_spec[k=7]) # V173 signature

Coefficients fitted from corpus regression. Quick OLS on the 1278-board
feature dataset.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_features(path):
    feats = []
    with open(path) as f:
        for line in f:
            feats.append(json.loads(line))
    return feats


def feature_vector(d):
    """Convert a feature dict to a numeric vector with intercept."""
    return [
        1.0,
        float(d.get('matched', 0)),
        d['prior_sum'] / max(d['n_placed'], 1),
        float(d.get('n_unsupported', 0)),
        float(d.get('mismatch_components', 0)),
        d['border_spec'][1] if len(d.get('border_spec', [])) >= 8 else 0.0,  # k=7
        d['border_spec'][2] if len(d.get('border_spec', [])) >= 8 else 0.0,  # k=12
        d['border_spec'][3] if len(d.get('border_spec', [])) >= 8 else 0.0,  # k=13
    ]


def normal_equation_ols(X, y):
    """Solve OLS via normal equations: β = (X^T X)^-1 X^T y."""
    n = len(X)
    p = len(X[0])
    # X^T X
    xtx = [[sum(X[i][k] * X[i][l] for i in range(n)) for l in range(p)] for k in range(p)]
    # X^T y
    xty = [sum(X[i][k] * y[i] for i in range(n)) for k in range(p)]
    # Solve via Gaussian elimination
    # Augmented matrix
    A = [row[:] + [xty[k]] for k, row in enumerate(xtx)]
    # Forward elim
    for k in range(p):
        # Pivot
        max_row = max(range(k, p), key=lambda r: abs(A[r][k]))
        A[k], A[max_row] = A[max_row], A[k]
        if abs(A[k][k]) < 1e-12:
            return None
        for r in range(k + 1, p):
            ratio = A[r][k] / A[k][k]
            for c in range(k, p + 1):
                A[r][c] -= ratio * A[k][c]
    # Back sub
    beta = [0.0] * p
    for k in range(p - 1, -1, -1):
        beta[k] = (A[k][p] - sum(A[k][c] * beta[c] for c in range(k + 1, p))) / A[k][k]
    return beta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', default='output/vol-177/features.jsonl')
    ap.add_argument('--out', default='output/vol-177/promise_model.json')
    args = ap.parse_args()

    feats = load_features(REPO / args.features)
    print(f"Loaded {len(feats)} feature vectors")

    # Filter to 16x16 complete boards.
    feats = [d for d in feats if d.get('n_placed', 0) == 256]
    print(f"Complete boards: {len(feats)}")

    # Target: matched. Use all features except matched in input.
    # But we want to predict matched FROM features that DON'T include matched.
    # Since matched is a feature, we need a different target: lift potential.
    # For this corpus, we don't have a "lifted score" — boards are already lifted.
    # So the regression is: explain `matched` from other features.
    #
    # Fit y = X β where X = [1, prior_norm, n_unsup, mc, spec_7, spec_12, spec_13]
    # (no matched in input; predicting matched).

    feats_with_label = [d for d in feats if d.get('matched') is not None]
    X = []
    y = []
    for d in feats_with_label:
        if len(d.get('border_spec', [])) < 8:
            continue
        v = [
            1.0,
            d['prior_sum'] / max(d['n_placed'], 1),
            float(d.get('n_unsupported', 0)),
            float(d.get('mismatch_components', 0)),
            d['border_spec'][1],  # k=7
            d['border_spec'][2],  # k=12
            d['border_spec'][3],  # k=13
        ]
        X.append(v)
        y.append(float(d['matched']))

    print(f"Regression on {len(X)} boards")
    beta = normal_equation_ols(X, y)
    if beta is None:
        print("OLS failed")
        return

    names = ['intercept', 'prior_norm', 'n_unsupported', 'mismatch_comps', 'spec_k7', 'spec_k12', 'spec_k13']
    print(f"OLS coefficients:")
    for n, b in zip(names, beta):
        print(f"  {n:>18}: {b:>+10.4f}")

    # R²
    y_mean = sum(y) / len(y)
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    y_pred = [sum(X[i][k] * beta[k] for k in range(len(beta))) for i in range(len(X))]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(len(y)))
    r2 = 1 - ss_res / ss_tot
    print(f"  R² = {r2:.4f}")

    # Save model
    out = Path(REPO / args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'features': names,
        'beta': beta,
        'r2': r2,
        'n_train': len(X),
    }, indent=2))
    print(f"Saved model to {out}")

    # Top promise on existing builds: for our V155, V175 builds, what does the model say?
    print()
    print("Promise on V175 builds:")
    import glob
    for p in sorted(glob.glob(str(REPO / 'output/vol-175/*/builds/*.json'))):
        try:
            d = json.loads(Path(p).read_text())
        except Exception:
            continue
        # We need to compute features for V175 builds, but they may not have the
        # right structure. Skip for now.
        # break
        pass


if __name__ == '__main__':
    main()
