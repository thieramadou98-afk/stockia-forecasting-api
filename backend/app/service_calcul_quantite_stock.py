"""
Logique métier : calcul de la quantité en stock à partir de l'historique des mouvements.

Principe : on ne duplique pas un champ « stock courant » modifiable partout ;
on agrège entrées (+) et sorties (-) pour éviter les incohérences (exigence historique).
"""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .modeles_tables_stock import StockMovement


def quantite_stock_produit(db: Session, product_id: int) -> int:
    """
    Retourne le stock actuel d'un produit : somme des entrées moins somme des sorties.

    :param db: session SQLAlchemy active
    :param product_id: identifiant du produit
    """
    # Agrégation SQL : plus efficace que charger tous les enregistrements en Python
    entrees = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "entree",
        )
    )
    sorties = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "sortie",
        )
    )
    return int(entrees or 0) - int(sorties or 0)


def quantite_stock_jusqua_instant(db: Session, product_id: int, instant: datetime) -> int:
    """
    Stock théorique juste avant ``instant`` : tous les mouvements avec created_at < instant.
    Utilisé pour les rapports « stock début de période ».
    """
    entrees = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "entree",
            StockMovement.created_at < instant,
        )
    )
    sorties = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "sortie",
            StockMovement.created_at < instant,
        )
    )
    return int(entrees or 0) - int(sorties or 0)


def sommes_entrees_sorties_periode(
    db: Session, product_id: int, debut_inclus: datetime, fin_inclus: datetime
) -> tuple[int, int]:
    """Retourne (total entrées, total sorties) sur [debut_inclus, fin_inclus]."""
    entrees = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "entree",
            StockMovement.created_at >= debut_inclus,
            StockMovement.created_at <= fin_inclus,
        )
    )
    sorties = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "sortie",
            StockMovement.created_at >= debut_inclus,
            StockMovement.created_at <= fin_inclus,
        )
    )
    return int(entrees or 0), int(sorties or 0)


def sommes_entrees_et_sorties_detail_periode(
    db: Session, product_id: int, debut_inclus: datetime, fin_exclusif: datetime
) -> tuple[int, int, int, int]:
    """
    Sur la période demi-ouverte ``[debut_inclus, fin_exclusif)`` : total entrées, puis sorties
    « vente » (kind explicite vente uniquement), sorties « perte », sorties « autre »
    (y compris kind NULL / vide — hors vente et perte).
    La somme des trois sorties = toutes les sorties sur la période.
    """
    entrees = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product_id,
            StockMovement.movement_type == "entree",
            StockMovement.created_at >= debut_inclus,
            StockMovement.created_at < fin_exclusif,
        )
    )
    ent = int(entrees or 0)

    base = (
        StockMovement.product_id == product_id,
        StockMovement.movement_type == "sortie",
        StockMovement.created_at >= debut_inclus,
        StockMovement.created_at < fin_exclusif,
    )
    sv = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            *base,
            StockMovement.sortie_kind == "vente",
        )
    )
    sp = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            *base,
            StockMovement.sortie_kind == "perte",
        )
    )
    sa = db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            *base,
            or_(
                StockMovement.sortie_kind == "autre",
                StockMovement.sortie_kind.is_(None),
                StockMovement.sortie_kind == "",
            ),
        )
    )
    return ent, int(sv or 0), int(sp or 0), int(sa or 0)


def quantites_pour_plusieurs_produits(db: Session, product_ids: list[int]) -> dict[int, int]:
    """
    Calcule le stock pour une liste de produits en peu de requêtes (tableau de bord).
    Retourne un dictionnaire {id_produit: quantité}.
    """
    if not product_ids:
        return {}
    result: dict[int, int] = {pid: 0 for pid in product_ids}

    # Somme des entrées par produit
    for row in db.execute(
        select(StockMovement.product_id, func.sum(StockMovement.quantity)).where(
            StockMovement.product_id.in_(product_ids),
            StockMovement.movement_type == "entree",
        ).group_by(StockMovement.product_id)
    ):
        result[row[0]] = int(row[1] or 0)

    for row in db.execute(
        select(StockMovement.product_id, func.sum(StockMovement.quantity)).where(
            StockMovement.product_id.in_(product_ids),
            StockMovement.movement_type == "sortie",
        ).group_by(StockMovement.product_id)
    ):
        result[row[0]] -= int(row[1] or 0)

    return result
