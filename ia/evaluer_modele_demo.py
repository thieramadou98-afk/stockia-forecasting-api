"""
Script d’évaluation des modèles de prévision de stock.

Compare la régression linéaire et le Random Forest sur une série de consommation
avec une séparation chronologique (train / test) pour éviter la fuite d’information.

Usage :
    python ia/evaluer_modele_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

# Données factices : sorties par jour (même logique que l’agrégation dans l’API)
def _serie_demo(n: int = 40, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = 5 + np.arange(n) * 0.08
    bruit = rng.normal(0, 1.2, n)
    qty = np.maximum(1, base + bruit)
    return pd.DataFrame({"t": np.arange(n), "qty": qty})


def evaluer_chronologique(df: pd.DataFrame, test_ratio: float = 0.25) -> None:
    n = len(df)
    n_test = max(2, int(n * test_ratio))
    n_train = n - n_test
    train = df.iloc[:n_train]
    test = df.iloc[n_train:]

    X_train = train[["t"]].values
    y_train = train["qty"].values
    X_test = test[["t"]].values
    y_test = test["qty"].values

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    pred_lr = lr.predict(X_test)

    rf = RandomForestRegressor(n_estimators=30, max_depth=4, random_state=42)
    rf.fit(X_train, y_train)
    pred_rf = rf.predict(X_test)

    mae_lr = mean_absolute_error(y_test, pred_lr)
    mae_rf = mean_absolute_error(y_test, pred_rf)
    print("Évaluation chronologique (derniers jours = test)")
    print(f"  Points train={n_train}, test={n_test}")
    print(f"  MAE régression linéaire : {mae_lr:.3f}")
    print(f"  MAE Random Forest      : {mae_rf:.3f}")
    print("Script terminé.")


def main() -> int:
    df = _serie_demo()
    evaluer_chronologique(df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
