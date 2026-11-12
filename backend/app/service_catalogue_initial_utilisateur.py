"""
Duplication du catalogue de référence (matériaux de construction) pour un nouvel utilisateur.

Chaque compte reçoit ses propres rayons et articles (stocks à 0 : aucun mouvement).
Les SKU du gabarit sont omis à la copie pour éviter les collisions entre comptes.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from .donnees_catalogue_reference_magasin import ARTICLES_PAR_CATEGORIE, NOMS_CATEGORIES, image_url_pour_categorie
from .modeles_tables_stock import Category, Product, User


def dupliquer_catalogue_reference_pour_utilisateur(db: Session, user_id: int) -> None:
    """
    Insère catégories + produits du gabarit pour ``user_id`` s’il n’a encore aucun rayon.

    On se base sur les **catégories** (rayons) : un compte sans rayon n’a jamais reçu le gabarit
    (inscription ancienne, erreur passée, etc.). Vérifier seulement les produits provoquait des
    doublons de noms de rayons si des catégories existaient déjà sans articles.
    """
    if db.query(Category).filter(Category.owner_user_id == user_id).first() is not None:
        return

    categories_par_nom: dict[str, Category] = {}
    for nom in NOMS_CATEGORIES:
        c = Category(
            owner_user_id=user_id,
            name=nom,
            image_url=image_url_pour_categorie(nom),
        )
        db.add(c)
        categories_par_nom[nom] = c
    db.flush()

    for nom_cat in NOMS_CATEGORIES:
        for art in ARTICLES_PAR_CATEGORIE.get(nom_cat, []):
            p = Product(
                owner_user_id=user_id,
                name=art.nom,
                category_id=categories_par_nom[nom_cat].id,
                min_stock=art.min_stock,
                lead_time_days=7,
                description=art.description,
                unit=art.unite,
                price=Decimal(str(art.prix)),
                brand=art.brand,
                sku=None,
                reference_url=art.reference_url,
            )
            db.add(p)
    db.commit()


def assurer_catalogue_gabarit_pour_tous_les_comptes(db: Session) -> None:
    """Au démarrage : remplit le gabarit pour tout utilisateur qui n’a encore aucun rayon."""
    for (uid,) in db.query(User.id).all():
        dupliquer_catalogue_reference_pour_utilisateur(db, int(uid))
