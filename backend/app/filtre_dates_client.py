"""
Bornes temporelles pour filtrer ``created_at`` (UTC naïf, comme ``datetime.utcnow()``).

Les champs ``<input type="date">`` représentent des **jours calendaires locaux**. On convertit
début / fin de période via un fuseau **IANA** (ex. ``America/Toronto``), puis on compare en UTC
naïf — même référence que les horodatages en base.
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def fuseau_rapport_par_defaut() -> str:
    """Défaut Canada Est (aligné README / Azure Canada East) ; surcharge possible ``STOCKIA_TIMEZONE``."""
    v = (os.environ.get("STOCKIA_TIMEZONE") or "America/Toronto").strip()
    return v or "America/Toronto"


def zoneinfo_ou_defaut(nom_iana: str | None) -> ZoneInfo:
    cle = (nom_iana or "").strip()
    if not cle:
        cle = fuseau_rapport_par_defaut()
    try:
        return ZoneInfo(cle)
    except Exception:
        return ZoneInfo(fuseau_rapport_par_defaut())


def bornes_periode_pour_created_at_utc_naif(
    date_debut: date,
    date_fin: date,
    timezone_iana: str | None,
) -> tuple[datetime, datetime]:
    """
    Retourne ``(debut_inclusif_utc_naif, fin_exclusif_utc_naif)`` pour
    ``created_at >= debut AND created_at < fin_exclusif``.

    ``timezone_iana`` : fuseau IANA du navigateur (paramètre de requête ``timezone``), ex.
    ``America/Toronto``. Si absent ou invalide : ``STOCKIA_TIMEZONE`` ou ``America/Toronto``.
    """
    tz = zoneinfo_ou_defaut(timezone_iana)
    debut = datetime.combine(date_debut, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    fin_exclusif = (
        datetime.combine(date_fin + timedelta(days=1), time.min, tzinfo=tz)
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )
    return debut, fin_exclusif
