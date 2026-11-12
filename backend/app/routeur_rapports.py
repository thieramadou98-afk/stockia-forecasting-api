"""
Rapports inventaire et mouvements sur période (filtres dates, export imprimable côté client).
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from .acces_inventaire_utilisateur import categorie_du_utilisateur, produit_du_utilisateur
from .dependances_injection import SessionDep, UserDep
from .filtre_dates_client import bornes_periode_pour_created_at_utc_naif
from .modeles_tables_stock import Category, Product, StockMovement
from .schemas_echange_api import (
    InventoryPeriodMeta,
    InventoryPeriodReport,
    InventoryPeriodRow,
    MovementRead,
)
from .service_calcul_quantite_stock import (
    quantite_stock_jusqua_instant,
    sommes_entrees_et_sorties_detail_periode,
)

router = APIRouter(prefix="/api", tags=["rapports-inventaire"])


@router.get("/reports/inventory-period", response_model=InventoryPeriodReport)
def rapport_inventaire_periode(
    db: SessionDep,
    user: UserDep,
    date_debut: date = Query(..., description="Début de période (inclus), AAAA-MM-JJ"),
    date_fin: date = Query(..., description="Fin de période (inclusive), AAAA-MM-JJ"),
    product_id: int | None = Query(default=None, description="Limiter à un produit"),
    category_id: int | None = Query(default=None, description="Limiter aux produits de ce rayon"),
    fuseau_iana: str | None = Query(
        default=None,
        alias="timezone",
        max_length=80,
        description="Fuseau IANA du navigateur (ex. America/Toronto).",
    ),
) -> InventoryPeriodReport:
    """
    Fiche type inventaire : stock au début, entrées, sorties vente / perte / autre, stock fin.

    Le stock début affiché est le stock calculé avant la date de début, avec un **plancher à 0**.
    Total sorties = vente + perte + autre (les sorties sans nature sont regroupées sous « autre »).
    Stock fin = max(0, stock début + entrées − total sorties).
    Si ``product_id`` et ``category_id`` sont tous deux fournis, seul ``product_id`` est appliqué.
    """
    if date_fin < date_debut:
        raise HTTPException(status_code=400, detail="date_fin doit être ≥ date_debut")

    debut, fin_exclusif = bornes_periode_pour_created_at_utc_naif(date_debut, date_fin, fuseau_iana)

    if product_id is not None:
        p = produit_du_utilisateur(db, product_id, user.id)
        if not p:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        products = [p]
    elif category_id is not None:
        cat = categorie_du_utilisateur(db, category_id, user.id)
        if not cat:
            raise HTTPException(status_code=404, detail="Catégorie introuvable")
        products = (
            db.query(Product)
            .filter(
                Product.owner_user_id == user.id,
                Product.category_id == category_id,
            )
            .order_by(Product.name)
            .all()
        )
    else:
        products = (
            db.query(Product)
            .filter(Product.owner_user_id == user.id)
            .order_by(Product.name)
            .all()
        )

    rows: list[InventoryPeriodRow] = []
    for p in products:
        stock_debut_calcule = quantite_stock_jusqua_instant(db, p.id, debut)
        entrees, sv, sp, sa = sommes_entrees_et_sorties_detail_periode(db, p.id, debut, fin_exclusif)
        sorties_total = sv + sp + sa
        stock_debut = max(0, stock_debut_calcule)
        fin_theo = max(0, stock_debut + entrees - sorties_total)
        rows.append(
            InventoryPeriodRow(
                product_id=p.id,
                name=p.name,
                category_name=p.category.name if p.category else None,
                stock_debut=stock_debut,
                entrees_periode=entrees,
                sorties_vente=sv,
                sorties_perte=sp,
                sorties_autre=sa,
                stock_fin_theorique=fin_theo,
                min_stock=p.min_stock,
            )
        )

    return InventoryPeriodReport(
        meta=InventoryPeriodMeta(date_debut=date_debut, date_fin=date_fin),
        rows=rows,
    )


@router.get("/reports/movements-period", response_model=list[MovementRead])
def rapport_mouvements_periode(
    db: SessionDep,
    user: UserDep,
    date_debut: date = Query(...),
    date_fin: date = Query(...),
    product_id: int | None = Query(default=None),
    category_id: int | None = Query(default=None),
    fuseau_iana: str | None = Query(
        default=None,
        alias="timezone",
        max_length=80,
        description="Fuseau IANA du navigateur (ex. America/Toronto).",
    ),
) -> list[MovementRead]:
    """Liste chronologique des mouvements entre deux dates (pour tableau ou impression)."""
    if date_fin < date_debut:
        raise HTTPException(status_code=400, detail="date_fin doit être ≥ date_debut")
    debut, fin_exclusif = bornes_periode_pour_created_at_utc_naif(date_debut, date_fin, fuseau_iana)

    q = (
        db.query(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .filter(
            Product.owner_user_id == user.id,
            StockMovement.created_at >= debut,
            StockMovement.created_at < fin_exclusif,
        )
    )
    if product_id is not None:
        if not produit_du_utilisateur(db, product_id, user.id):
            return []
        q = q.filter(StockMovement.product_id == product_id)
    elif category_id is not None:
        cat = categorie_du_utilisateur(db, category_id, user.id)
        if not cat:
            raise HTTPException(status_code=404, detail="Catégorie introuvable")
        pids = [
            p.id
            for p in db.query(Product)
            .filter(Product.owner_user_id == user.id, Product.category_id == category_id)
            .all()
        ]
        if not pids:
            return []
        q = q.filter(StockMovement.product_id.in_(pids))
    mouvements = q.order_by(StockMovement.created_at.asc(), StockMovement.id.asc()).all()
    return [MovementRead.model_validate(m) for m in mouvements]
