"""Accès aux entités d’inventaire limitées au compte connecté (propriétaire)."""

from sqlalchemy.orm import Session

from .modeles_tables_stock import Category, Product


def categorie_du_utilisateur(db: Session, category_id: int, user_id: int) -> Category | None:
    return (
        db.query(Category)
        .filter(Category.id == category_id, Category.owner_user_id == user_id)
        .first()
    )


def produit_du_utilisateur(db: Session, product_id: int, user_id: int) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.id == product_id, Product.owner_user_id == user_id)
        .first()
    )


def ids_produits_du_utilisateur(db: Session, user_id: int) -> list[int]:
    rows = db.query(Product.id).filter(Product.owner_user_id == user_id).all()
    return [int(r[0]) for r in rows]
