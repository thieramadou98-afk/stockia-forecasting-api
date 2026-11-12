"""
Gabarit de catalogue pour StockIA : rayons et articles type grande surface de matériaux.

Les libellés décrivent des **familles de produits** courantes au Québec (cuisine, plomberie, etc.).
Ce fichier ne cite aucune enseigne : uniquement des noms génériques pour initialiser l’inventaire
d’un nouveau compte (prix indicatifs, à ajuster en magasin).
"""
from __future__ import annotations

from typing import NamedTuple


class ArticleCatalogue(NamedTuple):
    nom: str
    description: str
    min_stock: int
    unite: str
    prix: float
    brand: str | None = None
    sku: str | None = None
    reference_url: str | None = None


def _article_rayon(nom: str, unite: str = "unité", prix: float = 9.99, min_stock: int = 5) -> ArticleCatalogue:
    """Une ligne catalogue par sous-rayon (nom affiché tel quel dans l’inventaire)."""
    return ArticleCatalogue(
        nom,
        f"Gamme type pour « {nom} » — complétez prix, unité et stock selon vos fournisseurs.",
        min_stock,
        unite,
        prix,
    )


# Ordre d’affichage des rayons (départements)
NOMS_CATEGORIES: list[str] = [
    "Saisonnier",
    "Cuisine",
    "Salle de bains",
    "Maison et Décoration",
    "Matériaux",
    "Couvre-plancher",
    "Électricité et Luminaires",
    "Chauffage - Ventilation - Climatisation",
    "Outillage",
    "Peinture",
    "Plomberie",
    "Quincaillerie",
]

_SLUG_IMAGE_CATEGORIE: dict[str, str] = {
    "Saisonnier": "saisonnier",
    "Cuisine": "cuisine",
    "Salle de bains": "salle-de-bains",
    "Maison et Décoration": "maison-decoration",
    "Matériaux": "materiaux",
    "Couvre-plancher": "couvre-plancher",
    "Électricité et Luminaires": "electricite-luminaires",
    "Chauffage - Ventilation - Climatisation": "chauffage-ventilation",
    "Outillage": "outillage",
    "Peinture": "peinture",
    "Plomberie": "plomberie",
    "Quincaillerie": "quincaillerie",
}


def image_url_pour_categorie(nom_categorie: str) -> str:
    slug = _SLUG_IMAGE_CATEGORIE.get(nom_categorie, "defaut")
    return f"/ui/images/categories/{slug}.svg"


ARTICLES_PAR_CATEGORIE: dict[str, list[ArticleCatalogue]] = {
    "Saisonnier": [
        _article_rayon("Ameublement d'extérieur", "lot", 49.99),
        _article_rayon("Aménagement décoratif", "unité", 12.99),
        _article_rayon("Barbecues — cuisson d'extérieur", "unité", 199.0),
        _article_rayon("Jardinage — paysagement", "unité", 7.99),
        _article_rayon("Chauffage d'extérieur", "unité", 89.0),
        _article_rayon("Arrosage et récupération d'eau", "unité", 24.99),
        _article_rayon("Outillage de jardin", "unité", 34.99),
        _article_rayon("Piscines — spas — jeux", "unité", 0.0),
        _article_rayon("Rampes — clôtures", "unité", 59.0),
        _article_rayon("Plein air", "unité", 19.99),
    ],
    "Cuisine": [
        _article_rayon("Robinetterie de cuisine", "unité", 45.0),
        _article_rayon("Éviers", "unité", 120.0),
        _article_rayon("Hottes", "unité", 280.0),
        _article_rayon("Armoires", "unité", 0.0),
        _article_rayon("Articles de cuisine", "unité", 8.99),
        _article_rayon("Mobilier de cuisine", "unité", 0.0),
    ],
    "Salle de bains": [
        _article_rayon("Robinetterie de salle de bains", "unité", 39.0),
        _article_rayon("Baignoires — bains", "unité", 0.0),
        _article_rayon("Douches", "unité", 0.0),
        _article_rayon("Meubles-lavabos — armoires", "unité", 0.0),
        _article_rayon("Lavabos et vasques", "unité", 95.0),
        _article_rayon("Toilettes et sièges", "unité", 189.0),
        _article_rayon("Ventilateurs de salle de bains", "unité", 79.0),
        _article_rayon("Articles pour salle de bains", "unité", 14.99),
    ],
    "Maison et Décoration": [
        _article_rayon("Aspirateurs", "unité", 149.0),
        _article_rayon("Avertisseurs — extincteurs", "unité", 29.99),
        _article_rayon("Décoration", "unité", 11.99),
        _article_rayon("Entretien ménager", "unité", 6.49),
        _article_rayon("Garde-robes — rangements", "unité", 0.0),
        _article_rayon("Idées cadeaux", "unité", 24.99),
        _article_rayon("Mobilier d'intérieur", "unité", 0.0),
        _article_rayon("Poubelles — sacs à ordures", "unité", 18.0),
        _article_rayon("Pratico-pratique", "unité", 4.99),
        _article_rayon("Téléphonie — audio-vidéo", "unité", 39.99),
    ],
    "Matériaux": [
        _article_rayon("Bois et charpente", "unité", 0.0),
        _article_rayon("Contreplaqués — panneaux", "feuille", 42.0),
        _article_rayon("Gypse et moulures", "feuille", 15.99),
        _article_rayon("Fenêtres", "unité", 0.0),
        _article_rayon("Portes", "unité", 0.0),
        _article_rayon("Finition d'intérieur", "unité", 22.0),
        _article_rayon("Moulures et accessoires", "longueur", 3.49),
        _article_rayon("Revêtements d'extérieur", "unité", 1.25),
        _article_rayon("Isolation — insonorisation", "unité", 38.0),
        _article_rayon("Toiture", "unité", 0.0),
    ],
    "Couvre-plancher": [
        _article_rayon("Planchers stratifiés", "boîte", 39.99),
        _article_rayon("Planchers de vinyle", "boîte", 44.99),
        _article_rayon("Plancher de bois franc", "pi²", 6.99),
        _article_rayon("Céramiques — porcelaines", "pi²", 3.29),
        _article_rayon("Colles — coulis", "sac", 18.0),
        _article_rayon("Outils et accessoires pour céramiques", "unité", 12.0),
        _article_rayon("Tapis — carpettes", "unité", 29.0),
        _article_rayon("Produits de préparation et de finition", "unité", 16.5),
    ],
    "Électricité et Luminaires": [
        _article_rayon("Luminaires d'intérieur", "unité", 35.0),
        _article_rayon("Luminaires d'extérieur", "unité", 48.0),
        _article_rayon("Ampoules", "unité", 4.99),
        _article_rayon("Câblage électrique", "rouleau", 89.0),
        _article_rayon("Boîtes — raccords", "unité", 2.49),
        _article_rayon("Fusibles — disjoncteurs", "unité", 15.0),
        _article_rayon("Prises — interrupteurs", "unité", 3.99),
        _article_rayon("Rallonges — multiprises", "unité", 12.99),
        _article_rayon("Outils et utilitaires d'électricité", "unité", 27.0),
        _article_rayon("Sonnettes — carillons", "unité", 32.0),
    ],
    "Chauffage - Ventilation - Climatisation": [
        _article_rayon("Chauffage électrique — thermostats", "unité", 55.0),
        _article_rayon("Poêles — foyers", "unité", 0.0),
        _article_rayon("Foyers d'extérieur — chauffe-terrasses", "unité", 129.0),
        _article_rayon("Ventilation — aération", "unité", 74.0),
        _article_rayon("Climatisation", "unité", 0.0),
        _article_rayon("Bûches — combustibles", "unité", 8.99),
    ],
    "Outillage": [
        _article_rayon("Outillage manuel", "unité", 14.99),
        _article_rayon("Outillage électrique", "unité", 0.0),
        _article_rayon("Pièces et accessoires d'outils motorisés", "unité", 9.99),
        _article_rayon("Outillage pneumatique et au gaz", "unité", 0.0),
        _article_rayon("Outillage sans fil", "unité", 0.0),
        _article_rayon("Vêtements — équipements de protection", "unité", 24.0),
        _article_rayon("Coffres à outils — chariots — chevalets", "unité", 69.0),
        _article_rayon("Échelles — escabeaux", "unité", 119.0),
    ],
    "Peinture": [
        _article_rayon("Peintures — apprêts", "galon", 39.99),
        _article_rayon("Teintures — vernis", "galon", 44.99),
        _article_rayon("Protecteurs — enduits", "unité", 28.0),
        _article_rayon("Outils et utilitaires de peinture", "unité", 7.5),
        _article_rayon("Préparation des surfaces", "unité", 12.0),
    ],
    "Plomberie": [
        _article_rayon("Tuyaux et raccords d'alimentation", "longueur", 6.99),
        _article_rayon("Tuyaux et raccords d'évacuation", "longueur", 8.49),
        _article_rayon("Chauffe-eau et accessoires", "unité", 0.0),
        _article_rayon("Pompes et accessoires", "unité", 0.0),
        _article_rayon("Outils et utilitaires de plomberie", "unité", 19.99),
        _article_rayon("Colles — joints — soudure", "unité", 11.0),
        _article_rayon("Pièces de rechange / réparation", "unité", 4.5),
    ],
    "Quincaillerie": [
        _article_rayon("Serrurerie — sécurité", "unité", 22.0),
        _article_rayon("Clous — vis — boulons", "boîte", 9.99),
        _article_rayon("Quincaillerie de meubles et d'armoires", "unité", 6.49),
        _article_rayon("Ferronnerie de construction", "unité", 14.0),
        _article_rayon("Supports — ancrages", "unité", 3.29),
        _article_rayon("Cordes — chaînes — câbles", "unité", 12.0),
        _article_rayon("Boîtes aux lettres — affiches", "unité", 39.0),
    ],
}
