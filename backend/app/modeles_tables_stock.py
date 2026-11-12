"""
Modèles ORM SQLAlchemy : tables « catégories », « produits », « mouvements », « utilisateurs ».

Chaque classe représente une table ; les relations (clés étrangères) reflètent
la gestion d'inventaire : un produit appartient à une catégorie ; chaque mouvement
est lié à un produit (entrée ou sortie de stock).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Category(Base):
    """Catégorie de produits (ex. ciment, plomberie), propre à un compte utilisateur."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("owner_user_id", "name", name="uq_categories_owner_nom"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    # Icône / illustration du rayon (URL servie sous /ui/, ex. /ui/images/categories/plomberie.svg)
    image_url = Column(String(500), nullable=True)

    # Relation inverse : une catégorie regroupe plusieurs produits
    products = relationship("Product", back_populates="category")


class Product(Base):
    """Produit en inventaire : nom, lien catégorie, seuil d'alerte de stock minimal."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    # Référence optionnelle à une catégorie (nullable si non classé)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    # Seuil en-deçà duquel on signale un risque de rupture (exigence projet StockIA)
    min_stock = Column(Integer, default=0, nullable=False)
    # Délai d’approvisionnement (jours) : sert au point de commande et à la suggestion IA
    lead_time_days = Column(Integer, default=7, nullable=False)
    description = Column(Text, nullable=True)
    # Unité de vente (sac, rouleau, chaque…) et prix indicatif pour démo / rapport
    unit = Column(String(40), nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    # Code article (ex. code magasin) — optionnel ; unicité vérifiée par compte côté API
    sku = Column(String(50), nullable=True, index=True)
    # Marque / fabricant (saisie manuelle pour la démo ; pas d’import automatique)
    brand = Column(String(120), nullable=True, index=True)
    # Lien vers une fiche produit publique (référence documentaire, pas une API d’import)
    reference_url = Column(String(750), nullable=True)

    category = relationship("Category", back_populates="products")
    # order_by : affiche l'historique des mouvements du plus ancien au plus récent
    movements = relationship(
        "StockMovement",
        back_populates="product",
        order_by="StockMovement.created_at",
    )


class StockMovement(Base):
    """
    Mouvement de stock : entrée (réception) ou sortie (vente / consommation).
    L'historique complet permet tableaux, graphiques et module IA (consommation passée).
    """

    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    # Valeurs attendues : « entree » ou « sortie » (cohérent avec la consigne métier en français)
    movement_type = Column(String(20), nullable=False)
    # Pour movement_type == « sortie » : vente | perte | autre (NULL = non classé, compté « autre » au rapport inventaire)
    sortie_kind = Column(String(20), nullable=True)
    quantity = Column(Integer, nullable=False)  # toujours > 0 ; le type indique le sens
    # Prix unitaire figé au moment de la sortie « vente » (page Ventes) ; sinon NULL
    sale_unit_price = Column(Numeric(10, 2), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    product = relationship("Product", back_populates="movements")


class User(Base):
    """Utilisateur pour l'authentification de base (exigence sécurité du projet)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Profil établissement (point de vente / entreprise) — renseigné à l’inscription ; NULL pour comptes historiques
    organization_name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(40), nullable=True)
    address_line = Column(String(500), nullable=True)
