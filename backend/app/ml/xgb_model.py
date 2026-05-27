"""XGBoost binary classifier — predicts probability of an upward move.

Honest scope: this is the simplest possible 'AI' baseline. It's a real model,
trains fast on a laptop, and gives the architecture a signal to compose with
rules. It is NOT a profitable strategy on its own — it's a foundation for the
self-learning loop to operate on.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from ..config import DATA_DIR
from .features import FEATURE_COLS, build_features, label_forward_returns

MODEL_DIR = DATA_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)


class XGBSignal:
    """Train on history, predict P(up) for the most recent bar."""

    def __init__(self, model_name: str = "xgb_default") -> None:
        self.path = MODEL_DIR / f"{model_name}.pkl"
        self.model: xgb.XGBClassifier | None = None
        if self.path.exists():
            with self.path.open("rb") as f:
                self.model = pickle.load(f)

    def fit(self, history: pd.DataFrame, horizon: int = 5, threshold: float = 0.01) -> dict:
        feat = build_features(history)
        y = label_forward_returns(history, horizon=horizon, threshold=threshold)
        data = pd.concat([feat, y.rename("y")], axis=1).dropna()
        if len(data) < 80:
            return {"trained": False, "reason": "not enough data", "n": len(data)}
        # Time-ordered split — no shuffle. Last 20% for validation.
        split = int(len(data) * 0.8)
        X_tr, y_tr = data.iloc[:split][FEATURE_COLS], data.iloc[:split]["y"]
        X_va, y_va = data.iloc[split:][FEATURE_COLS], data.iloc[split:]["y"]
        model = xgb.XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            objective="binary:logistic", eval_metric="logloss",
            tree_method="hist", verbosity=0,
        )
        model.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)
        val_acc = float((model.predict(X_va) == y_va).mean())
        base_rate = float(y_va.mean())
        self.model = model
        with self.path.open("wb") as f:
            pickle.dump(model, f)
        return {
            "trained": True, "n_train": int(len(X_tr)), "n_val": int(len(X_va)),
            "val_accuracy": val_acc, "val_base_rate": base_rate,
        }

    def predict_proba(self, history: pd.DataFrame) -> float | None:
        if self.model is None:
            return None
        feat = build_features(history).dropna()
        if feat.empty:
            return None
        x = feat[FEATURE_COLS].iloc[[-1]]
        if x.isna().any(axis=None):
            return None
        return float(self.model.predict_proba(x)[0, 1])
