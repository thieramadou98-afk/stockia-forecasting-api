"""
Point d'entrée FastAPI : assemble les routeurs, CORS, fichiers statiques du frontend.

Lancez avec : uvicorn app.main:app --reload --app-dir backend
(ou depuis le dossier backend : uvicorn app.main:app --reload)
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .database import SessionLocal, engine, init_db
from .initialisation_donnees_demonstration import retirer_compte_demonstration_obsolete
from .service_catalogue_initial_utilisateur import assurer_catalogue_gabarit_pour_tous_les_comptes
from .routeur_authentification import router as router_auth
from .routeur_ia_previsions import router as router_ia
from .routeur_mouvements_stock import router as router_mouvements
from .routeur_produits_categories import router as router_produits
from .routeur_rapports import router as router_rapports
from .routeur_tableau_bord import router as router_dashboard
from .routeur_ventes import router as router_ventes

def _afficher_chemin_base_sqlite_au_demarrage() -> None:
    """Aide au débogage : le fichier SQLite est relatif au répertoire courant du terminal (souvent backend/)."""
    url = engine.url
    if url.get_backend_name() != "sqlite" or not url.database:
        print(f"[StockIA] Base de données : {url.render_as_string(hide_password=False)}")
        return
    rel = Path(url.database)
    abs_db = rel.resolve() if rel.is_absolute() else (Path.cwd() / rel).resolve()
    print(f"[StockIA] Base SQLite utilisée (fichier) : {abs_db}")
    print(
        "[StockIA] Si le tableau de bord renvoie 500 après une mise à jour du code, "
        "fermez uvicorn, supprimez ce fichier (ou utilisez STOCKIA_DATABASE_URL vers un nouveau .db), puis relancez."
    )


@asynccontextmanager
async def gestionnaire_cycle_vie(app: FastAPI):
    """
    Remplace l’ancien @app.on_event("startup") (déprécié dans FastAPI / Starlette).

    Au démarrage : création des tables SQLite, suppression de l’ancien compte « demo » si présent, gabarit de catalogue pour les comptes qui en ont besoin.
    """
    _afficher_chemin_base_sqlite_au_demarrage()
    init_db()
    db = SessionLocal()
    try:
        retirer_compte_demonstration_obsolete(db)
        assurer_catalogue_gabarit_pour_tous_les_comptes(db)
    finally:
        db.close()
    yield


# Application principale ; title/description apparaissent dans la doc OpenAPI automatique (/docs)
app = FastAPI(
    title="StockIA.web API",
    description="API REST de gestion d'inventaire et prévisions de stock (projet 8INF206).",
    version="1.0.0",
    lifespan=gestionnaire_cycle_vie,
)

# CORS : autorise le frontend servi depuis un autre port ou fichier local pendant le développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_auth)
app.include_router(router_produits)
app.include_router(router_mouvements)
app.include_router(router_dashboard)
app.include_router(router_rapports)
app.include_router(router_ventes)
app.include_router(router_ia)


@app.get("/api/health")
def sante_api():
    """Point de contrôle simple pour vérifier que l'API répond (tests / supervision légère)."""
    return {"status": "ok", "service": "StockIA.web"}


def _redirection_page_connexion():
    """URL canonique de la page de connexion (fichiers statiques sous /ui/)."""
    return RedirectResponse(url="/ui/connexion_utilisateur.html", status_code=302)


@app.get("/", include_in_schema=False)
def racine_redirection_interface():
    """
    Racine du site : même cible que les court-chemins /fr et /connexion.
    En production derrière https://www.stockia.ca/, cette route répond à l’URL sans chemin.
    """
    return _redirection_page_connexion()


@app.get("/fr", include_in_schema=False)
@app.get("/fr/", include_in_schema=False)
def racine_locale_fr():
    """
    Court-chemin « style site public » : https://exemple.com/fr → connexion.
    À combiner en production avec un nom de domaine (DNS) et HTTPS (voir docs/DEPLOIEMENT_AZURE_DEVOPS.md ou docs/DEPLOIEMENT_CLOUD.md).
    """
    return _redirection_page_connexion()


@app.get("/connexion", include_in_schema=False)
def court_chemin_connexion():
    """Alias lisible : …/connexion → page de connexion."""
    return _redirection_page_connexion()


@app.get("/favicon.ico", include_in_schema=False)
def favicon_navigateur():
    """Réponse vide : évite un 404 répété dans les journaux quand le navigateur demande l’icône."""
    return Response(status_code=204)


# Sert le dossier frontend/ à l'URL /ui (ouvrir http://localhost:8000/ui/)
_frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount(
        "/ui",
        StaticFiles(directory=str(_frontend_dir), html=True),
        name="interface_web_stockia",
    )