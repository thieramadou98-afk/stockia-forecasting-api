"""
Module d'intelligence artificielle appliqué au stock (exigence projet StockIA — plan 8INF206).

Exploite l’historique des **sorties** (pandas) et combine des modèles simples prévus au plan :
régression linéaire, **moyenne mobile** sur les quantités journalières, et **forêt aléatoire**
(RandomForest) lorsqu’il y a assez de points (≥ 10 jours avec activité).

En déduit : risque de rupture, consommation estimée, point de commande (demande × délai fournisseur
+ stock de sécurité), quantité recommandée (cible au-dessus du PdC + couverture cycle).
"""
from collections import defaultdict
from datetime import date, timedelta
import math

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from .modeles_tables_stock import Product, StockMovement
from .service_calcul_quantite_stock import quantite_stock_produit


def _nombre_flottant_positif_fini(x: float) -> float:
    """Évite NaN / inf dans les calculs (sinon int() ou Pydantic peuvent faire échouer l’API avec une 500)."""
    if not math.isfinite(x) or x < 0:
        return 0.0
    return float(x)


def _dataframe_sorties_par_jour(db: Session, product_id: int) -> pd.DataFrame:
    """
    Construit un DataFrame avec une ligne par jour : date, quantité totale sortie ce jour-là.

    Les entrées sont ignorées ici : on modélise la demande (sorties), pas les réceptions.
    """
    rows = (
        db.query(StockMovement)
        .filter(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "sortie",
        )
        .order_by(StockMovement.created_at.asc())
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["date", "qty"])

    by_day: dict[date, int] = defaultdict(int)
    for m in rows:
        d = m.created_at.date()
        by_day[d] += m.quantity

    df = pd.DataFrame([{"date": d, "qty": q} for d, q in sorted(by_day.items())])
    return df


def predire_consommation_journaliere(df: pd.DataFrame, horizon_jours: int = 7) -> float:
    """
    Estime la consommation moyenne journalière future (unités par jour).

    - Peu de points : moyenne simple.
    - Sinon : combinaison pondérée **régression linéaire** (tendance sur l’indice du jour),
      **moyenne mobile** (dernier lissage sur une fenêtre courte), et **Random Forest**
      si au moins 10 jours d’historique (comme au plan de cours : linéaire / moyennes mobiles / RF).

    Paramètre horizon_jours : réservé pour une extension « horizon de prédiction » (fiche projet).
    """
    _ = horizon_jours
    if df.empty:
        return 0.0

    daily = df["qty"].astype(float)
    avg_simple = _nombre_flottant_positif_fini(float(daily.mean()))

    if len(df) < 3:
        return avg_simple

    X = np.arange(len(df)).reshape(-1, 1)
    y = daily.values.reshape(-1, 1)
    next_x = np.array([[len(df)]])

    lin = LinearRegression()
    lin.fit(X, y.ravel())
    pred_point = _nombre_flottant_positif_fini(float(lin.predict(next_x)[0]))
    pred_lin = _nombre_flottant_positif_fini(0.5 * pred_point + 0.5 * avg_simple)

    w_ma = min(5, len(df))
    ma_series = daily.rolling(window=w_ma, min_periods=1).mean()
    pred_ma = _nombre_flottant_positif_fini(float(ma_series.iloc[-1]))

    pred_rf = pred_lin
    if len(df) >= 10:
        rf = RandomForestRegressor(n_estimators=25, max_depth=4, random_state=42)
        rf.fit(X, y.ravel())
        pred_rf = _nombre_flottant_positif_fini(float(rf.predict(next_x)[0]))

    combine = _nombre_flottant_positif_fini(0.45 * pred_lin + 0.30 * pred_ma + 0.25 * pred_rf)
    return combine


def evaluer_produit_insight(db: Session, product: Product, jours_moyenne: int = 14) -> dict:
    """
    Calcule tous les indicateurs IA pour un produit : stock, moyenne sorties, risque, recommandation.

    Retourne un dict sérialisable vers ProductInsightRead côté routeur.
    """
    qty = quantite_stock_produit(db, product.id)
    df = _dataframe_sorties_par_jour(db, product.id)

    cutoff = date.today() - timedelta(days=jours_moyenne)
    recent = df[df["date"] >= cutoff] if not df.empty else df

    if recent.empty:
        avg_daily = 0.0
    else:
        # Moyenne des sorties par jour sur la fenêtre (jours sans sortie = 0 implicite si on veut être strict ;
        # ici on moyenne seulement les jours où il y a eu activité pour rester simple)
        avg_daily = _nombre_flottant_positif_fini(float(recent["qty"].mean()))

    predicted = predire_consommation_journaliere(df)
    predicted = _nombre_flottant_positif_fini(predicted)
    # On prend le max entre moyenne récente et prédiction pour une recommandation prudente
    demande_ref = max(avg_daily, predicted)

    L = max(1, min(365, int(getattr(product, "lead_time_days", None) or 7)))
    # Écart-type des sorties par jour (jours avec activité) ; proxy 30 % de la demande si peu de données
    if len(recent) >= 3:
        sigma_d = _nombre_flottant_positif_fini(float(recent["qty"].std(ddof=1)))
    else:
        sigma_d = (
            _nombre_flottant_positif_fini(0.3 * demande_ref) if demande_ref > 0 else 0.0
        )
    # Stock de sécurité type « délai d’approvisionnement » (approx. 90 % service, z ≈ 1,28)
    z_service = 1.28
    safety = z_service * sigma_d * math.sqrt(float(L))
    safety = _nombre_flottant_positif_fini(safety)
    rop_demand = demande_ref * float(L) + safety
    rop_demand = _nombre_flottant_positif_fini(rop_demand)
    reorder_trigger = (
        max(rop_demand, float(product.min_stock)) if product.min_stock > 0 else rop_demand
    )
    reorder_trigger = _nombre_flottant_positif_fini(reorder_trigger)

    coverage_cycle_days = 7
    target_level = reorder_trigger + demande_ref * float(coverage_cycle_days)
    target_level = _nombre_flottant_positif_fini(target_level)
    shortage = max(0, product.min_stock - qty)
    rec_raw = math.ceil(target_level - qty) if target_level > qty else 0
    recommended = max(int(rec_raw) if math.isfinite(float(rec_raw)) else 0, shortage, 0)

    if demande_ref <= 0:
        days_left = None
        if product.min_stock > 0 and qty <= product.min_stock:
            risk = "moyen"
        else:
            risk = "faible"
    else:
        days_left = qty / demande_ref
        if not math.isfinite(days_left):
            days_left = None
            risk = "faible"
        else:
            trigger_ceil = math.ceil(reorder_trigger) if reorder_trigger > 0 else 0
            sous_cible = qty <= trigger_ceil if reorder_trigger > 0 else qty <= product.min_stock
            if qty <= product.min_stock or sous_cible or days_left < 7:
                risk = "eleve"
            elif days_left < 14:
                risk = "moyen"
            else:
                risk = "faible"

    return {
        "product_id": product.id,
        "product_name": product.name,
        "quantity_stock": qty,
        "min_stock": product.min_stock,
        "lead_time_days": L,
        "avg_daily_out_last_days": round(avg_daily, 3),
        "predicted_daily_out": round(predicted, 3),
        "days_until_stockout_estimate": round(days_left, 2)
        if days_left is not None and math.isfinite(days_left)
        else None,
        "stockout_risk_level": risk,
        "recommended_order_qty": recommended,
        "safety_stock_qty": round(safety, 3),
        "reorder_point_qty": round(reorder_trigger, 3),
        "coverage_cycle_days": coverage_cycle_days,
    }
