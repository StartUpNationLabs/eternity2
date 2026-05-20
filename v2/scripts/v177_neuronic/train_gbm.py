#!/usr/bin/env python3
"""V177 NEURONIC — try gradient boosting (more robust than MLP on small data)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
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
            d['prior_sum'] / max(d['n_placed'], 1),
            d['n_unsupported'],
            # mismatch_count REMOVED — too redundant with target (matched = 480 - mismatch)
            d['mismatch_components'],
        ] + d['border_spec']
        X.append(v)
        y.append(d['matched'])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', default='output/vol-177/features.jsonl')
    args = ap.parse_args()

    feats = load_features(REPO / args.features)
    X, y = feature_matrix(feats)
    print(f"X shape: {X.shape}, y range: [{y.min()}, {y.max()}]")

    # Models to try.
    models = {
        'Ridge α=1': Ridge(alpha=1.0),
        'Ridge α=10': Ridge(alpha=10.0),
        'RandomForest 50': RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42),
        'GBM 100 lr=0.1': GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42),
        'GBM 200 lr=0.05': GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42),
    }
    for name, model in models.items():
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        r2_list = []
        for tr, te in kf.split(X):
            # Models that need scaling (Ridge)
            if 'Ridge' in name:
                scaler = StandardScaler().fit(X[tr])
                X_tr = scaler.transform(X[tr])
                X_te = scaler.transform(X[te])
            else:
                X_tr, X_te = X[tr], X[te]
            model.fit(X_tr, y[tr])
            y_pred = model.predict(X_te)
            ss_res = ((y[te] - y_pred) ** 2).sum()
            ss_tot = ((y[te] - y[te].mean()) ** 2).sum()
            r2_list.append(1 - ss_res / ss_tot)
        print(f"  {name:>25}: R² = {np.mean(r2_list):.4f} ± {np.std(r2_list):.4f}")

    # Identify best model and inspect feature importance.
    print()
    gbm = GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42)
    gbm.fit(X, y)
    names = ['prior_norm', 'n_unsupported', 'mismatch_components',
             'spec_k5', 'spec_k7', 'spec_k12', 'spec_k13',
             'spec_k16', 'spec_k19', 'spec_k26', 'spec_k29']
    print("GBM feature importance:")
    imps = sorted(zip(names, gbm.feature_importances_), key=lambda x: -x[1])
    for n, i in imps:
        bar = '*' * int(i * 100)
        print(f"  {n:>22}: {i:>7.4f}  {bar}")


if __name__ == '__main__':
    main()
