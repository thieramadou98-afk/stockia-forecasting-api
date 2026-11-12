"""
Schémas Pydantic : valident et documentent les données entrantes/sortantes de l'API REST.

Sépare les « modèles BD » (SQLAlchemy) des « contrats API » (JSON), bonne pratique FastAPI.
"""
from datetime import date, datetime
from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _valider_et_normaliser_telephone(v: str) -> str:
    """
    Téléphone au format international : indicatif pays obligatoire avec « + », chiffres type E.164.
    Pour +1 (Canada / É.-U.), exactement 11 chiffres au total dont indicatif régional (NPA) 200–999.
    """
    t = v.strip()
    if not t.startswith("+"):
        raise ValueError(
            "Le numéro doit commencer par l’indicatif pays avec « + » (ex. : +1 418 555 0100)."
        )
    if len(t) > 40:
        raise ValueError("Téléphone trop long (40 caractères maximum).")
    if not re.fullmatch(r"[+\d\s().\-]+", t):
        raise ValueError(
            "Utilisez uniquement des chiffres et les séparateurs « + », espaces, ( ), . et -."
        )
    digits = re.sub(r"\D", "", t)
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError(
            "Numéro incomplet ou invalide : en format international, de 8 à 15 chiffres au total."
        )
    if digits[0] == "1":
        if len(digits) != 11:
            raise ValueError(
                "Pour l’indicatif +1 (Canada / États-Unis), saisissez exactement 10 chiffres après le 1 "
                "(ex. : +1 450 555 0100)."
            )
        npa = int(digits[1:4])
        if npa < 200 or npa > 999:
            raise ValueError(
                "Indicatif régional invalide : après +1, les trois premiers chiffres doivent être entre 200 et 999."
            )
    return t


# --- Catégories ---


class CategoryCreate(BaseModel):
    """Données pour créer une catégorie (nom unique côté service)."""

    name: str = Field(..., min_length=1, max_length=120)


class CategoryRead(BaseModel):
    """Catégorie renvoyée au client après lecture ou création."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str | None = None


# --- Produits ---


class ProductCreate(BaseModel):
    """Création d'un produit : nom obligatoire, catégorie et seuil optionnels."""

    name: str = Field(..., min_length=1, max_length=200)
    category_id: int | None = None
    min_stock: int = Field(default=0, ge=0)
    lead_time_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Délai fournisseur (jours) pour le point de commande IA",
    )
    description: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, max_length=40)
    price: float | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=50)
    brand: str | None = Field(default=None, max_length=120)
    reference_url: str | None = Field(default=None, max_length=750)


class ProductUpdate(BaseModel):
    """Mise à jour partielle d'un produit (tous les champs optionnels)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    min_stock: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=1, le=365)
    description: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, max_length=40)
    price: float | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=50)
    brand: str | None = Field(default=None, max_length=120)
    reference_url: str | None = Field(default=None, max_length=750)


class ProductRead(BaseModel):
    """Produit avec quantité actuelle calculée à partir des mouvements (pas stockée en dur)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category_id: int | None
    category_name: str | None = None
    category_image_url: str | None = None
    min_stock: int
    lead_time_days: int = 7
    description: str | None
    unit: str | None = None
    price: float | None = None
    sku: str | None = None
    brand: str | None = None
    reference_url: str | None = None
    quantity_stock: int = 0  # injecté par le routeur après calcul métier


# --- Mouvements ---


class MovementCreate(BaseModel):
    """Enregistrement d'une entrée ou sortie : type + quantité positive."""

    movement_type: str = Field(..., pattern="^(entree|sortie)$")
    quantity: int = Field(..., gt=0)
    note: str | None = Field(default=None, max_length=500)
    # Pour une sortie : vente (défaut), perte ou autre. Ignoré pour une entrée.
    sortie_kind: Literal["vente", "perte", "autre"] | None = None
    # Pour une sortie « vente » : prix unitaire au moment de la vente (sinon prix catalogue).
    sale_unit_price: float | None = Field(default=None, ge=0)

    @field_validator("sortie_kind", mode="before")
    @classmethod
    def _coerce_sortie_kind_vide(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def normaliser_sortie_kind(self):
        if self.movement_type == "entree":
            object.__setattr__(self, "sortie_kind", None)
            object.__setattr__(self, "sale_unit_price", None)
        elif self.sortie_kind is None:
            object.__setattr__(self, "sortie_kind", "vente")
        elif self.sortie_kind != "vente":
            object.__setattr__(self, "sale_unit_price", None)
        return self


class MovementRead(BaseModel):
    """Ligne d'historique de mouvement renvoyée au front (tableaux / graphiques)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    movement_type: str
    quantity: int
    note: str | None
    sortie_kind: str | None = None
    sale_unit_price: float | None = None
    created_at: datetime

    @model_validator(mode="after")
    def afficher_sortie_kind(self):
        if self.movement_type == "entree":
            object.__setattr__(self, "sortie_kind", None)
        elif not self.sortie_kind:
            object.__setattr__(self, "sortie_kind", "vente")
        return self


# --- Authentification ---


class UserCreate(BaseModel):
    """Inscription : identifiants de connexion + métadonnées d’établissement (affichage rapports / en-tête)."""

    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=6, max_length=128)
    organization_name: str = Field(..., min_length=2, max_length=200, description="Raison sociale ou nom du point de vente")
    email: EmailStr = Field(..., description="Adresse courriel de contact professionnel")
    phone: str = Field(..., min_length=6, max_length=40, description="Téléphone joignable")
    address_line: str = Field(..., min_length=5, max_length=500, description="Adresse postale du magasin ou siège")

    @field_validator("phone")
    @classmethod
    def valider_telephone(cls, v: str) -> str:
        return _valider_et_normaliser_telephone(v)


class UserRead(BaseModel):
    """Profil utilisateur sans mot de passe."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    organization_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line: str | None = None


class UserProfileUpdate(BaseModel):
    """Mise à jour partielle du profil établissement (PATCH /api/auth/me). Champs absents = inchangés."""

    organization_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address_line: str | None = Field(default=None, max_length=500)

    @field_validator("organization_name")
    @classmethod
    def org_si_renseigne(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if len(s) < 2:
            raise ValueError("La raison sociale doit contenir au moins 2 caractères")
        return s

    @field_validator("phone")
    @classmethod
    def tel_si_renseigne(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _valider_et_normaliser_telephone(v)

    @field_validator("address_line")
    @classmethod
    def adresse_si_renseignee(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if len(s) < 5:
            raise ValueError("L’adresse doit contenir au moins 5 caractères")
        return s


class TokenResponse(BaseModel):
    """Réponse OAuth2 : jeton JWT à placer dans l'en-tête Authorization: Bearer ..."""

    access_token: str
    token_type: str = "bearer"


# --- Tableau de bord & IA ---


class DashboardProductSummary(BaseModel):
    """Résumé par produit pour le dashboard : stock actuel vs seuil."""

    product_id: int
    name: str
    category_name: str | None
    quantity_stock: int
    min_stock: int
    below_min: bool  # True si min_stock > 0 et quantity_stock <= min_stock (réappro.)


class DashboardOverview(BaseModel):
    """Vue globale : nombre de produits, alertes sous seuil, derniers mouvements."""

    total_products: int
    alerts_below_min: int
    recent_movements: list[MovementRead]


class TopSortieRow(BaseModel):
    """Produit avec volume de sorties sur une fenêtre glissante."""

    product_id: int
    product_name: str
    total_sortie: int


class RecentCatalogueRow(BaseModel):
    """Derniers articles ajoutés au catalogue (identifiant décroissant)."""

    product_id: int
    name: str
    category_name: str | None
    quantity_stock: int


class DashboardWidgets(BaseModel):
    """Mini-listes sous les KPI (tableau de bord)."""

    top_sorties: list[TopSortieRow]
    recents_catalogue: list[RecentCatalogueRow]
    periode_jours: int


class InventoryPeriodRow(BaseModel):
    """Une ligne de fiche inventaire sur une période [date_debut, date_fin]."""

    product_id: int
    name: str
    category_name: str | None
    stock_debut: int  # ≥ 0 (plancher appliqué dans le rapport)
    entrees_periode: int
    sorties_vente: int
    sorties_perte: int
    sorties_autre: int
    stock_fin_theorique: int  # ≥ 0 (plancher appliqué dans le rapport)
    min_stock: int


class InventoryPeriodMeta(BaseModel):
    date_debut: date
    date_fin: date


class InventoryPeriodReport(BaseModel):
    """Rapport inventaire : métadonnées + lignes par produit."""

    meta: InventoryPeriodMeta
    rows: list[InventoryPeriodRow]


class VenteAgregeeRow(BaseModel):
    """Une ligne agrégée : ventes (sorties type vente) par période et par article."""

    periode: str
    product_id: int
    product_name: str
    category_name: str | None
    quantite_totale: int
    nb_mouvements: int
    prix_unitaire_reference: float | None = None
    montant_estime: float | None = None


class VentesAgregeesMeta(BaseModel):
    groupe: str  # jour | mois | annee
    date_debut: date
    date_fin: date
    note: str


class VentesAgregeesReport(BaseModel):
    """Synthèse des ventes à partir des sorties classées « vente » dans les mouvements."""

    meta: VentesAgregeesMeta
    rows: list[VenteAgregeeRow]


class ProductInsightRead(BaseModel):
    """
    Sortie du module IA : consommation estimée, risque de rupture, suggestion de commande.
    Point de commande = demande/jour × délai fournisseur + stock de sécurité (volatilité).
    """

    product_id: int
    product_name: str
    quantity_stock: int
    min_stock: int
    lead_time_days: int
    avg_daily_out_last_days: float
    predicted_daily_out: float
    days_until_stockout_estimate: float | None
    stockout_risk_level: str  # « faible » | « moyen » | « eleve »
    recommended_order_qty: int
    safety_stock_qty: float
    reorder_point_qty: float
    coverage_cycle_days: int = Field(
        default=7,
        description="Jours de demande ajoutés après le point de commande pour la quantité suggérée",
    )
