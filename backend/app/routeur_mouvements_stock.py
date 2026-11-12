"""
Routes REST : mouvements de stock (entrées / sorties) et historique.

Chaque écriture met à jour implicitement le stock via la table des mouvements.
Une sortie refusée si le stock devient négatif (règle métier).
"""
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import Session

from .acces_inventaire_utilisateur import produit_du_utilisateur
from .dependances_injection import SessionDep, UserDep
from .modeles_tables_stock import Product, StockMovement
from .schemas_echange_api import MovementCreate, MovementRead
from .service_calcul_quantite_stock import quantite_stock_produit

router = APIRouter(prefix="/api", tags=["mouvements-stock"])


@router.post("/products/{product_id}/movements", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def enregistrer_mouvement(
    product_id: int,
    payload: MovementCreate,
    db: SessionDep,
    user: UserDep,
) -> StockMovement:
    """
    Enregistre une entrée (réception fournisseur) ou sortie (vente / utilisation).

    Avant une sortie, on vérifie que la quantité en stock est suffisante.
    """
    p = produit_du_utilisateur(db, product_id, user.id)
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    if payload.movement_type == "sortie":
        actuel = quantite_stock_produit(db, product_id)
        if actuel < payload.quantity:
            # 422 : requête comprise mais règle métier non satisfaite (évite la constante dépréciée UNPROCESSABLE_ENTITY)
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Stock insuffisant : {actuel} unité(s) disponible(s), "
                    f"{payload.quantity} demandée(s) pour cette sortie."
                ),
            )

    sale_orm: Decimal | None = None
    if payload.movement_type == "sortie":
        kind = payload.sortie_kind or "vente"
        if kind == "vente":
            if payload.sale_unit_price is not None:
                sale_orm = Decimal(str(payload.sale_unit_price)).quantize(Decimal("0.01"))
            elif p.price is not None:
                sale_orm = (
                    p.price
                    if isinstance(p.price, Decimal)
                    else Decimal(str(p.price)).quantize(Decimal("0.01"))
                )

    sortie_enregistree: str | None = None
    if payload.movement_type == "sortie":
        sk = payload.sortie_kind or "vente"
        sortie_enregistree = sk if sk else "vente"

    m = StockMovement(
        product_id=product_id,
        movement_type=payload.movement_type,
        sortie_kind=sortie_enregistree,
        sale_unit_price=sale_orm,
        quantity=payload.quantity,
        note=payload.note,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/movements", response_model=list[MovementRead])
def historique_mouvements(
    db: SessionDep,
    user: UserDep,
    product_id: int | None = Query(default=None, description="Filtrer par produit"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[StockMovement]:
    """
    Historique global ou filtré par produit, du plus récent au plus ancien.

    Paramètre limit : évite de charger des milliers de lignes d'un coup (performance).
    """
    q = (
        db.query(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .filter(Product.owner_user_id == user.id)
    )
    if product_id is not None:
        p = produit_du_utilisateur(db, product_id, user.id)
        if not p:
            return []
        q = q.filter(StockMovement.product_id == product_id)
    return q.order_by(StockMovement.created_at.desc()).limit(limit).all()
