"""
Réservé au cycle de vie de l’application.

Le catalogue type (matériaux de construction) est **dupliqué pour chaque utilisateur**
à l’inscription : voir ``service_catalogue_initial_utilisateur``.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from .modeles_tables_stock import Category, Product, StockMovement, User


def retirer_compte_demonstration_obsolete(db: Session) -> None:
    """
    Supprime tout utilisateur dont l’identifiant est « demo » (casse ignorée) et son inventaire.

    L’ancien compte de démonstration ne doit plus permettre la connexion ; les données associées
    sont effacées pour éviter les clés étrangères orphelines.
    """
    users = db.query(User).filter(func.lower(User.username) == "demo").all()
    if not users:
        return
    for u in users:
        pids = [int(r[0]) for r in db.query(Product.id).filter(Product.owner_user_id == u.id).all()]
        if pids:
            db.query(StockMovement).filter(StockMovement.product_id.in_(pids)).delete(synchronize_session=False)
        db.query(Product).filter(Product.owner_user_id == u.id).delete(synchronize_session=False)
        db.query(Category).filter(Category.owner_user_id == u.id).delete(synchronize_session=False)
        db.delete(u)
    db.commit()
