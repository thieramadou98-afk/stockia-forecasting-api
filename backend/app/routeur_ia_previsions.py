"""
Routes du module IA : prévisions de consommation, risque de rupture, recommandations.

S'appuie sur service_previsions_stock_ia (pandas + scikit-learn), conforme à la fiche projet.
"""
from fastapi import APIRouter, HTTPException

from .acces_inventaire_utilisateur import produit_du_utilisateur
from .dependances_injection import SessionDep, UserDep
from .modeles_tables_stock import Product
from .schemas_echange_api import ProductInsightRead
from .service_previsions_stock_ia import evaluer_produit_insight

router = APIRouter(prefix="/api", tags=["intelligence-artificielle-stock"])


@router.get("/insights", response_model=list[ProductInsightRead])
def insights_tous_les_produits(db: SessionDep, user: UserDep) -> list[ProductInsightRead]:
    """
    Calcule les indicateurs IA pour chaque produit (alertes et quantités suggérées).

    Utilisé par le tableau de bord pour afficher badges « risque » et recommandations.
    """
    products = (
        db.query(Product)
        .filter(Product.owner_user_id == user.id)
        .order_by(Product.name)
        .all()
    )
    return [ProductInsightRead(**evaluer_produit_insight(db, p)) for p in products]


@router.get("/insights/{product_id}", response_model=ProductInsightRead)
def insight_un_produit(product_id: int, db: SessionDep, user: UserDep) -> ProductInsightRead:
    """Détail des prévisions pour un seul produit (fiche ou modal côté client)."""
    p = produit_du_utilisateur(db, product_id, user.id)
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return ProductInsightRead(**evaluer_produit_insight(db, p))
