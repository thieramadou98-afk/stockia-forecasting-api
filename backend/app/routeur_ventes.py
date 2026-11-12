"""
Ventes : agrégation des sorties explicitement classées « vente » (sortie_kind = vente).

Montant = Σ (quantité × prix unitaire enregistré sur le mouvement, ou prix catalogue si absent).
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from .dependances_injection import SessionDep, UserDep
from .filtre_dates_client import bornes_periode_pour_created_at_utc_naif
from .modeles_tables_stock import Category, Product, StockMovement
from .schemas_echange_api import VenteAgregeeRow, VentesAgregeesMeta, VentesAgregeesReport

router = APIRouter(prefix="/api", tags=["ventes-estimees"])


@router.get("/reports/ventes", response_model=VentesAgregeesReport)
def rapport_ventes_agrege(
    db: SessionDep,
    user: UserDep,
    groupe: str = Query(
        ...,
        pattern="^(jour|mois|annee)$",
        description="Regroupement : jour (AAAA-MM-JJ), mois (AAAA-MM) ou année (AAAA)",
    ),
    date_debut: date | None = None,
    date_fin: date | None = None,
    fuseau_iana: str | None = Query(
        default=None,
        alias="timezone",
        max_length=80,
        description="Fuseau IANA du navigateur (ex. America/Toronto), pour interpréter les dates.",
    ),
) -> VentesAgregeesReport:
    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        if groupe == "jour":
            date_debut = date_fin - timedelta(days=90)
        elif groupe == "mois":
            date_debut = date_fin - timedelta(days=730)
        else:
            date_debut = date(date_fin.year - 5, 1, 1)

    if date_fin < date_debut:
        date_debut, date_fin = date_fin, date_debut

    debut_dt, fin_exclusif = bornes_periode_pour_created_at_utc_naif(date_debut, date_fin, fuseau_iana)

    if groupe == "jour":
        periode_expr = func.strftime("%Y-%m-%d", StockMovement.created_at)
    elif groupe == "mois":
        periode_expr = func.strftime("%Y-%m", StockMovement.created_at)
    else:
        periode_expr = func.strftime("%Y", StockMovement.created_at)

    prix_ligne = func.coalesce(StockMovement.sale_unit_price, Product.price)
    montant_expr = func.sum(StockMovement.quantity * prix_ligne)

    stmt = (
        select(
            periode_expr.label("periode"),
            Product.id.label("pid"),
            Product.name.label("pname"),
            Category.name.label("cname"),
            func.sum(StockMovement.quantity).label("qty"),
            func.count(StockMovement.id).label("nbm"),
            montant_expr.label("montant_total"),
        )
        .select_from(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            Product.owner_user_id == user.id,
            StockMovement.movement_type == "sortie",
            StockMovement.sortie_kind == "vente",
            StockMovement.created_at >= debut_dt,
            StockMovement.created_at < fin_exclusif,
        )
        .group_by(periode_expr, Product.id)
        .having(func.sum(StockMovement.quantity) > 0)
        .order_by(periode_expr.desc(), Product.name.asc())
    )

    rows_out: list[VenteAgregeeRow] = []
    for row in db.execute(stmt):
        periode, pid, pname, cname, qty, nbm, montant_total = row
        qty_i = int(qty or 0)
        mt = montant_total
        if mt is None or qty_i <= 0:
            montant = None
            prix_moyen = None
        else:
            montant = round(float(mt), 2)
            prix_moyen = round(montant / qty_i, 2)
        rows_out.append(
            VenteAgregeeRow(
                periode=str(periode),
                product_id=int(pid),
                product_name=str(pname),
                category_name=str(cname) if cname else None,
                quantite_totale=qty_i,
                nb_mouvements=int(nbm or 0),
                prix_unitaire_reference=prix_moyen,
                montant_estime=montant,
            )
        )

    note = (
        "Uniquement les ventes enregistrées dans Mouvements ; montant basé sur le prix à la vente saisi, "
        "ou sur le prix catalogue si absent."
    )
    return VentesAgregeesReport(
        meta=VentesAgregeesMeta(
            groupe=groupe,
            date_debut=date_debut,
            date_fin=date_fin,
            note=note,
        ),
        rows=rows_out,
    )
