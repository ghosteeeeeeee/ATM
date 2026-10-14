#!/usr/bin/env python3
"""
train_classifier.py — Train RandomForest trade quality predictor.

Usage: python3 scripts/ml_classifier/train_classifier.py [--days 90]
"""
import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import HERMES_DATA
from ml_classifier.feature_engineering import query_trades, build_dataset

MODELS_DIR = os.path.join(os.path.dirname(HERMES_DATA), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def train(days=90):
    # 1. Load data
    print(f"Querying {days}d trades...")
    df = query_trades(days)
    print(f"  {len(df)} trades, WR={df['pnl_pct'].gt(0).mean()*100:.1f}%")

    # 2. Build features
    data = build_dataset(df)
    feature_cols = [c for c in data.columns if c != 'won']
    X = data[feature_cols]
    y = data['won']
    print(f"  Features: {len(feature_cols)}, positives: {y.sum()}/{len(y)}")

    # 3. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # 4. Train
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_split=50,
        min_samples_leaf=25,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # 5. Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    cv = cross_val_score(model, X, y, cv=5, scoring='roc_auc')

    print(f"\n=== Results ===")
    print(f"Test accuracy: {acc:.3f}")
    print(f"Test AUC: {auc:.3f}")
    print(f"5-fold CV AUC: {cv.mean():.3f} ± {cv.std():.3f}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['LOSS', 'WIN'])}")

    # Feature importances
    importances = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1])
    print("Top 15 features:")
    for name, imp in importances[:15]:
        print(f"  {name:40s} {imp:.4f}")

    # 6. Save
    import joblib
    model_path = os.path.join(MODELS_DIR, 'trade_classifier.joblib')
    joblib.dump(model, model_path)

    with open(os.path.join(MODELS_DIR, 'trade_classifier_features.json'), 'w') as f:
        json.dump({
            'feature_cols': feature_cols,
            'importances': {name: float(imp) for name, imp in importances},
            'trained_at': datetime.now().isoformat(),
            'n_trades': len(df),
            'win_rate': float(y.mean()),
        }, f, indent=2)

    with open(os.path.join(MODELS_DIR, 'trade_classifier_metrics.json'), 'w') as f:
        json.dump({
            'test_accuracy': float(acc),
            'test_auc': float(auc),
            'cv_auc_mean': float(cv.mean()),
            'cv_auc_std': float(cv.std()),
            'n_train': len(X_train),
            'n_test': len(X_test),
            'trained_at': datetime.now().isoformat(),
        }, f, indent=2)

    print(f"\nModel saved: {model_path}")
    return model, auc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90)
    args = parser.parse_args()
    train(args.days)
