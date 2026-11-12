"""
Routes REST : catégories et produits (CRUD).

Protégées par JWT : seul un utilisateur connecté peut modifier l'inventaire (exigence sécurité).
"""
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .acces_inventaire_utilisateur import categorie_du_utilisateur, produit_du_utilisateur
from .dependances_injection import SessionDep, UserDep
from .modeles_tables_stock import Category, Product, StockMovement
from .schemas_echange_api import CategoryCreate, CategoryRead, ProductCreate, ProductRead, ProductUpdate
from .service_calcul_quantite_stock import quantite_stock_produit, quantites_pour_plusieurs_produits

router = APIRouter(prefix="/api", tags=["produits-et-categories"])

# Fichiers téléversés servis ensuite par StaticFiles sous /ui/ (nom aléatoire, non devinable).
_DOSSIER_MEDIA_FONDS_RAYONS = (
    Path(__file__).resolve().parent.parent.parent / "frontend" / "media" / "category_backgrounds"
)
_TAILLE_MAX_FOND_RAYON = 2_500_000
_TYPES_FOND_RAYON = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _verifier_magic_bytes_image(data: bytes, content_type: str) -> None:
    if content_type == "image/jpeg":
        if not data.startswith(b"\xff\xd8\xff"):
            raise HTTPException(status_code=400, detail="Fichier JPEG invalide")
    elif content_type == "image/png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=400, detail="Fichier PNG invalide")
    elif content_type == "image/webp":
        if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            raise HTTPException(status_code=400, detail="Fichier WebP invalide")


def _sku_deja_pris(
    db: Session, sku: str, owner_user_id: int, exclure_product_id: int | None = None
) -> bool:
    """Vérifie l’unicité du code article pour ce compte (hors produit en cours d’édition)."""
    q = db.query(Product).filter(Product.sku == sku, Product.owner_user_id == owner_user_id)
    if exclure_product_id is not None:
        q = q.filter(Product.id != exclure_product_id)
    return q.first() is not None


def _product_to_read(db: Session, p: Product, qty_map: dict[int, int] | None = None) -> ProductRead:
    """Assemble la réponse produit + nom de catégorie + quantité calculée."""
    qty = qty_map[p.id] if qty_map is not None else quantite_stock_produit(db, p.id)
    cat_name = p.category.name if p.category else None
    cat_img = p.category.image_url if p.category else None
    prix = float(p.price) if p.price is not None else None
    return ProductRead(
        id=p.id,
        name=p.name,
        category_id=p.category_id,
        category_name=cat_name,
        category_image_url=cat_img,
        min_stock=p.min_stock,
        lead_time_days=p.lead_time_days if p.lead_time_days is not None else 7,
        description=p.description,
        unit=p.unit,
        price=prix,
        sku=p.sku,
        brand=p.brand,
        reference_url=p.reference_url,
        quantity_stock=qty,
    )


# --- Catégories ---


@router.get("/categories", response_model=list[CategoryRead])
def lister_categories(db: SessionDep, user: UserDep) -> list[Category]:
    """Liste les catégories du compte connecté (menu déroulant côté front)."""
    return (
        db.query(Category)
        .filter(Category.owner_user_id == user.id)
        .order_by(Category.name)
        .all()
    )


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def creer_categorie(payload: CategoryCreate, db: SessionDep, user: UserDep) -> Category:
    """Ajoute une catégorie (ex. « Électricité ») pour le compte connecté."""
    nom = payload.name.strip()
    if (
        db.query(Category)
        .filter(Category.owner_user_id == user.id, Category.name == nom)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Vous avez déjà un rayon avec ce nom")
    c = Category(owner_user_id=user.id, name=nom, image_url=None)
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Impossible de créer la catégorie (nom dupliqué ?)")
    db.refresh(c)
    return c


@router.post("/categories/{category_id}/background", response_model=CategoryRead)
async def televerser_image_fond_rayon(
    category_id: int,
    db: SessionDep,
    user: UserDep,
    file: UploadFile = File(..., description="Image JPEG, PNG ou WebP (max 2,5 Mo)"),
) -> Category:
    """
    Enregistre une image de fond pour le rayon (prévisions IA, etc.).
    Fichier stocké sous ``frontend/media/category_backgrounds/`` avec nom aléatoire,
    URL référencée dans ``categories.image_url`` (servie via ``/ui/media/...``).
    """
    c = categorie_du_utilisateur(db, category_id, user.id)
    if not c:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in _TYPES_FOND_RAYON:
        raise HTTPException(
            status_code=400,
            detail="Format non supporté (utilisez JPEG, PNG ou WebP)",
        )
    ext = _TYPES_FOND_RAYON[ct]
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")
    if len(data) > _TAILLE_MAX_FOND_RAYON:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (maximum 2,5 Mo)")
    _verifier_magic_bytes_image(data, ct)

    _DOSSIER_MEDIA_FONDS_RAYONS.mkdir(parents=True, exist_ok=True)
    ancien = c.image_url or ""
    if "/ui/media/category_backgrounds/" in ancien:
        try:
            nom = ancien.rstrip("/").split("/")[-1]
            pth = _DOSSIER_MEDIA_FONDS_RAYONS / nom
            if pth.is_file() and nom and ".." not in nom:
                pth.unlink()
        except OSError:
            pass

    fname = f"{uuid.uuid4().hex[:20]}.{ext}"
    dest = _DOSSIER_MEDIA_FONDS_RAYONS / fname
    dest.write_bytes(data)
    c.image_url = f"/ui/media/category_backgrounds/{fname}"
    db.commit()
    db.refresh(c)
    return c


def _supprimer_produit_et_mouvements(db: Session, p: Product) -> None:
    """Supprime tous les mouvements d’un produit puis le produit (même logique que DELETE /products/{id})."""
    for m in list(p.movements):
        db.delete(m)
    db.delete(p)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_categorie(category_id: int, db: SessionDep, user: UserDep) -> None:
    """
    Supprime un rayon (catégorie) et, en cascade, tous les articles classés dans ce rayon
    ainsi que l’historique de mouvements de ces articles.
    """
    c = categorie_du_utilisateur(db, category_id, user.id)
    if not c:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    produits = db.query(Product).filter(Product.category_id == category_id).all()
    for p in produits:
        _supprimer_produit_et_mouvements(db, p)
    db.delete(c)
    db.commit()


# --- Produits ---


@router.get("/products", response_model=list[ProductRead])
def lister_produits(db: SessionDep, user: UserDep) -> list[ProductRead]:
    """Liste les produits du compte avec stock courant (agrégation des mouvements)."""
    products = (
        db.query(Product)
        .filter(Product.owner_user_id == user.id)
        .order_by(Product.name)
        .all()
    )
    ids = [p.id for p in products]
    qty_map = quantites_pour_plusieurs_produits(db, ids)
    return [_product_to_read(db, p, qty_map) for p in products]


@router.get("/products/{product_id}", response_model=ProductRead)
def lire_produit(product_id: int, db: SessionDep, user: UserDep) -> ProductRead:
    """Détail d'un produit par identifiant."""
    p = produit_du_utilisateur(db, product_id, user.id)
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return _product_to_read(db, p)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def creer_produit(payload: ProductCreate, db: SessionDep, user: UserDep) -> ProductRead:
    """Crée un produit pour le compte connecté ; vérifie que category_id est un de ses rayons."""
    if payload.category_id is not None:
        cat = categorie_du_utilisateur(db, payload.category_id, user.id)
        if not cat:
            raise HTTPException(status_code=400, detail="Catégorie inexistante")
    sku_norm = payload.sku.strip() if payload.sku else None
    if sku_norm and _sku_deja_pris(db, sku_norm, user.id):
        raise HTTPException(status_code=400, detail="Ce code article (SKU) est déjà utilisé")
    ref_url = payload.reference_url.strip() if payload.reference_url else None
    brand_norm = payload.brand.strip() if payload.brand else None
    p = Product(
        owner_user_id=user.id,
        name=payload.name.strip(),
        category_id=payload.category_id,
        min_stock=payload.min_stock,
        lead_time_days=payload.lead_time_days,
        description=payload.description,
        unit=payload.unit.strip() if payload.unit else None,
        price=Decimal(str(payload.price)) if payload.price is not None else None,
        sku=sku_norm or None,
        brand=brand_norm or None,
        reference_url=ref_url or None,
    )
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Code article (SKU) déjà utilisé ou données invalides")
    db.refresh(p)
    return _product_to_read(db, p)


@router.patch("/products/{product_id}", response_model=ProductRead)
def mettre_a_jour_produit(
    product_id: int,
    payload: ProductUpdate,
    db: SessionDep,
    user: UserDep,
) -> ProductRead:
    """Mise à jour partielle (nom, catégorie, seuil, description)."""
    p = produit_du_utilisateur(db, product_id, user.id)
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        cat = categorie_du_utilisateur(db, data["category_id"], user.id)
        if not cat:
            raise HTTPException(status_code=400, detail="Catégorie inexistante")
    if "sku" in data:
        if data["sku"] is None:
            pass
        else:
            sku_norm = data["sku"].strip() if isinstance(data["sku"], str) else None
            data["sku"] = sku_norm or None
            if data["sku"] and _sku_deja_pris(db, data["sku"], user.id, exclure_product_id=p.id):
                raise HTTPException(status_code=400, detail="Ce code article (SKU) est déjà utilisé")
    if "reference_url" in data:
        if data["reference_url"] is None:
            pass
        elif isinstance(data["reference_url"], str):
            data["reference_url"] = data["reference_url"].strip() or None
    if "brand" in data and isinstance(data.get("brand"), str):
        data["brand"] = data["brand"].strip() or None
    for k, v in data.items():
        if k == "price" and v is not None:
            setattr(p, k, Decimal(str(v)))
        elif k == "unit" and isinstance(v, str):
            setattr(p, k, v.strip() or None)
        else:
            setattr(p, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Code article (SKU) déjà utilisé ou données invalides")
    db.refresh(p)
    return _product_to_read(db, p)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_produit(product_id: int, db: SessionDep, user: UserDep) -> None:
    """Supprime un produit et ses mouvements (cascade SQLAlchemy par défaut si configuré — ici on supprime manuellement)."""
    p = produit_du_utilisateur(db, product_id, user.id)
    if not p:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    _supprimer_produit_et_mouvements(db, p)
    db.commit()


@router.post("/maintenance/supprimer-mouvements-demonstration")
def supprimer_mouvements_demonstration(db: SessionDep, user: UserDep) -> dict:
    """
    Supprime les mouvements dont la note indique une génération ou simulation de démonstration
    (anciennes données « Sortie simulée », « données de démonstration », réassorts démo, etc.).
    """
    n = StockMovement.note
    lc = func.lower(func.coalesce(n, ""))
    marqueurs = (
        "données de démonstration",
        "donnees de demonstration",
        "sortie simulée",
        "sortie simulee",
        "sortie simul",
        "réassort mi-période",
        "reassort mi-periode",
        "réassort final démo",
        "reassort final demo",
    )
    filt = or_(*[lc.contains(m) for m in marqueurs])
    q = (
        db.query(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .filter(Product.owner_user_id == user.id)
        .filter(n.isnot(None))
        .filter(filt)
    )
    ids = [m.id for m in q.all()]
    if not ids:
        return {"mouvements_supprimes": 0}
    supprimes = (
        db.query(StockMovement).filter(StockMovement.id.in_(ids)).delete(synchronize_session=False)
    )
    db.commit()
    return {"mouvements_supprimes": int(supprimes or 0)}
