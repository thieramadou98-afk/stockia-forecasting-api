"""
Routes pour le tableau de bord : synthèse des stocks et derniers mouvements.

Alimente la page d'accueil : alertes sous le seuil minimal, compteurs, liste récente.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func

from .dependances_injection import SessionDep, UserDep
from .modeles_tables_stock import Product, StockMovement
from .schemas_echange_api import (
    DashboardOverview,
    DashboardProductSummary,
    DashboardWidgets,
    MovementRead,
    RecentCatalogueRow,
    TopSortieRow,
)
from .service_calcul_quantite_stock import quantites_pour_plusieurs_produits

router = APIRouter(prefix="/api", tags=["tableau-de-bord"])


@router.get("/dashboard/summary", response_model=list[DashboardProductSummary])
def resume_par_produit(db: SessionDep, user: UserDep) -> list[DashboardProductSummary]:
    """Une ligne par produit : stock actuel, seuil, alerte si stock au seuil ou en dessous."""
    products = (
        db.query(Product)
        .filter(Product.owner_user_id == user.id)
        .order_by(Product.name)
        .all()
    )
    ids = [p.id for p in products]
    qty_map = quantites_pour_plusieurs_produits(db, ids)
    out: list[DashboardProductSummary] = []
    for p in products:
        q = qty_map.get(p.id, 0)
        seuil = p.min_stock
        sous_ou_au_seuil = seuil > 0 and q <= seuil
        out.append(
            DashboardProductSummary(
                product_id=p.id,
                name=p.name,
                category_name=p.category.name if p.category else None,
                quantity_stock=q,
                min_stock=seuil,
                below_min=sous_ou_au_seuil,
            )
        )
    return out


@router.get("/dashboard/overview", response_model=DashboardOverview)
def vue_ensemble_tableau_bord(db: SessionDep, user: UserDep) -> DashboardOverview:
    """Vue globale : totaux + 15 derniers mouvements pour un aperçu rapide."""
    products = db.query(Product).filter(Product.owner_user_id == user.id).all()
    ids = [p.id for p in products]
    qty_map = quantites_pour_plusieurs_produits(db, ids)
    # Stock au seuil minimal fixé par l’utilisateur ou en dessous (réapprovisionnement à prévoir)
    alerts = sum(
        1
        for p in products
        if p.min_stock > 0 and qty_map.get(p.id, 0) <= p.min_stock
    )

    recent = (
        db.query(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .filter(Product.owner_user_id == user.id)
        .order_by(StockMovement.created_at.desc())
        .limit(15)
        .all()
    )
    return DashboardOverview(
        total_products=len(products),
        alerts_below_min=alerts,
        recent_movements=[MovementRead.model_validate(m) for m in recent],
    )


@router.get("/dashboard/widgets", response_model=DashboardWidgets)
def widgets_tableau_bord(
    db: SessionDep,
    user: UserDep,
    jours: int = Query(default=30, ge=1, le=366, description="Fenêtre pour les sorties cumulées"),
) -> DashboardWidgets:
    """Mini-listes : plus fortes sorties sur la période, derniers articles ajoutés au catalogue."""
    cutoff = datetime.utcnow() - timedelta(days=jours)

    agg = (
        db.query(StockMovement.product_id, func.sum(StockMovement.quantity).label("t"))
        .join(Product, StockMovement.product_id == Product.id)
        .filter(
            Product.owner_user_id == user.id,
            StockMovement.movement_type == "sortie",
            StockMovement.created_at >= cutoff,
        )
        .group_by(StockMovement.product_id)
        .order_by(func.sum(StockMovement.quantity).desc())
        .limit(5)
        .all()
    )
    top_sorties: list[TopSortieRow] = []
    for pid, total in agg:
        p = db.query(Product).filter(Product.id == pid, Product.owner_user_id == user.id).first()
        if p:
            top_sorties.append(
                TopSortieRow(
                    product_id=int(pid),
                    product_name=p.name,
                    total_sortie=int(total or 0),
                )
            )

    recent_products = (
        db.query(Product)
        .filter(Product.owner_user_id == user.id)
        .order_by(Product.id.desc())
        .limit(5)
        .all()
    )
    ids = [p.id for p in recent_products]
    qty_map = quantites_pour_plusieurs_produits(db, ids)
    recents = [
        RecentCatalogueRow(
            product_id=p.id,
            name=p.name,
            category_name=p.category.name if p.category else None,
            quantity_stock=qty_map.get(p.id, 0),
        )
        for p in recent_products
    ]

    return DashboardWidgets(
        top_sorties=top_sorties,
        recents_catalogue=recents,
        periode_jours=jours,
    )
