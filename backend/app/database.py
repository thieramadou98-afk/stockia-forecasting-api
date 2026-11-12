"""
Connexion à la base de données SQLite et fabrique de sessions SQLAlchemy.

Ce module centralise l'URL de la BD et crée les tables au démarrage de l'API.
Conforme au projet StockIA : base relationnelle (SQLite en développement).

Variable d'environnement STOCKIA_DATABASE_URL (optionnelle) : permet à pytest d'utiliser
une base de test isolée sans écraser stockia.db de développement.

Par défaut : fichier ``stockia.db`` sous ``backend/`` en développement (même base quel que soit
le répertoire de lancement). Sur **Azure App Service** (variable d'environnement ``WEBSITE_INSTANCE_ID``),
la base par défaut est ``/home/stockia.db`` afin de survivre aux redéploiements lorsque le stockage
``/home`` est activé (``WEBSITES_ENABLE_APP_SERVICE_STORAGE=true``). Sinon, définir ``STOCKIA_DATABASE_URL``.
"""
import os
import re
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _url_sqlite_par_defaut() -> str:
    # Azure App Service Linux : /home est monté sur du stockage persistant si
    # WEBSITES_ENABLE_APP_SERVICE_STORAGE=true (sinon même effacement qu'au reste du conteneur).
    if os.environ.get("WEBSITE_INSTANCE_ID"):
        return "sqlite:////home/stockia.db"
    chemin = (_BACKEND_DIR / "stockia.db").resolve()
    return f"sqlite:///{chemin.as_posix()}"


DATABASE_URL = os.environ.get("STOCKIA_DATABASE_URL") or _url_sqlite_par_defaut()

# check_same_thread=False : requis pour SQLite avec FastAPI (plusieurs requêtes concurrentes)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def _configurer_sqlite_si_applicable(dbapi_connection, _connection_record) -> None:
    """WAL + attente courte : limite les erreurs « database is locked » (tableau de bord en requêtes parallèles)."""
    # Ne pas utiliser connection_record.dialect : absent sur _ConnectionRecord (SQLAlchemy 2.x).
    if engine.url.get_backend_name() != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()

# SessionLocal : usine à sessions (une session = une « conversation » avec la BD par requête)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base déclarative : toutes les classes de modèles en héritent pour être mappées à des tables
Base = declarative_base()


def init_db() -> None:
    """
    Crée les tables manquantes à partir des modèles ORM importés.
    Appelé une fois au démarrage de l'application FastAPI.
    """
    # Import latéral : enregistre les tables auprès de Base.metadata avant create_all
    from . import modeles_tables_stock  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_ajouter_sortie_kind_si_absent(engine)
    _migrate_ajouter_sale_unit_price_si_absent(engine)
    _migrate_ajouter_lead_time_days_si_absent(engine)
    _migrate_products_champs_catalogue_si_absents(engine)
    _migrate_categories_owner_image_si_absent(engine)
    _migrate_products_owner_si_absent(engine)
    _migrate_users_profil_etablissement_si_absent(engine)
    _migrate_categories_unique_proprietaire_nom_sqlite(engine)


def _migrate_ajouter_sortie_kind_si_absent(engine) -> None:
    """SQLite : ajoute la colonne sortie_kind aux BD créées avant cette évolution."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(stock_movements)")).fetchall()
        col_names = {row[1] for row in rows}
        if "sortie_kind" not in col_names:
            conn.execute(text("ALTER TABLE stock_movements ADD COLUMN sortie_kind VARCHAR(20)"))


def _migrate_ajouter_sale_unit_price_si_absent(engine) -> None:
    """SQLite : colonne sale_unit_price (prix à la vente enregistré sur le mouvement)."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(stock_movements)")).fetchall()
        col_names = {row[1] for row in rows}
        if "sale_unit_price" not in col_names:
            conn.execute(text("ALTER TABLE stock_movements ADD COLUMN sale_unit_price NUMERIC(10,2)"))


def _migrate_ajouter_lead_time_days_si_absent(engine) -> None:
    """SQLite : délai fournisseur (jours) pour le calcul du point de commande IA."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(products)")).fetchall()
        col_names = {row[1] for row in rows}
        if "lead_time_days" not in col_names:
            conn.execute(
                text("ALTER TABLE products ADD COLUMN lead_time_days INTEGER NOT NULL DEFAULT 7")
            )


def _migrate_products_champs_catalogue_si_absents(engine) -> None:
    """SQLite : colonnes produit (unité, prix, SKU, etc.) pour les BD créées avant ces champs."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(products)")).fetchall()
        col_names = {row[1] for row in rows}
        if "description" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN description TEXT"))
        if "unit" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN unit VARCHAR(40)"))
        if "price" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN price NUMERIC(10,2)"))
        if "sku" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN sku VARCHAR(50)"))
        if "brand" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN brand VARCHAR(120)"))
        if "reference_url" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN reference_url VARCHAR(750)"))


def _migrate_categories_owner_image_si_absent(engine) -> None:
    """SQLite : propriétaire du rayon + image (catalogue par compte)."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(categories)")).fetchall()
        col_names = {row[1] for row in rows}
        if "owner_user_id" not in col_names:
            conn.execute(text("ALTER TABLE categories ADD COLUMN owner_user_id INTEGER REFERENCES users(id)"))
        if "image_url" not in col_names:
            conn.execute(text("ALTER TABLE categories ADD COLUMN image_url VARCHAR(500)"))


def _migrate_products_owner_si_absent(engine) -> None:
    """SQLite : propriétaire de l’article (inventaire isolé par compte)."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(products)")).fetchall()
        col_names = {row[1] for row in rows}
        if "owner_user_id" not in col_names:
            conn.execute(text("ALTER TABLE products ADD COLUMN owner_user_id INTEGER REFERENCES users(id)"))


def _migrate_users_profil_etablissement_si_absent(engine) -> None:
    """SQLite : colonnes profil magasin / entreprise sur users (inscription enrichie)."""
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        col_names = {row[1] for row in rows}
        if "organization_name" not in col_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN organization_name VARCHAR(200)"))
        if "email" not in col_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
        if "phone" not in col_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(40)"))
        if "address_line" not in col_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN address_line VARCHAR(500)"))


def _chemin_fichier_sqlite_migre(engine) -> Path | None:
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database:
        return None
    p = Path(engine.url.database)
    return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()


def _sqlite_categories_a_unique_composite_owner_nom(conn: sqlite3.Connection) -> bool:
    """True si un index UNIQUE couvre déjà (owner_user_id, name)."""
    try:
        rows = conn.execute("PRAGMA index_list('categories')").fetchall()
    except sqlite3.OperationalError:
        return False
    for row in rows:
        if not row[2]:  # unique
            continue
        idx_name = row[1]
        if not isinstance(idx_name, str) or not re.match(r"^[\w]+$", idx_name):
            continue
        info = conn.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
        cols = {r[2] for r in info if r[2] is not None and r[2] != ""}
        if cols == {"owner_user_id", "name"}:
            return True
    return False


def _sqlite_categories_a_unique_global_sur_nom_seul(conn: sqlite3.Connection) -> bool:
    """True si un index UNIQUE ne porte que sur ``name`` (ancien schéma incompatible multi-comptes)."""
    try:
        rows = conn.execute("PRAGMA index_list('categories')").fetchall()
    except sqlite3.OperationalError:
        return False
    for row in rows:
        if not row[2]:
            continue
        idx_name = row[1]
        if not isinstance(idx_name, str) or not re.match(r"^[\w]+$", idx_name):
            continue
        info = conn.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
        cols = [r[2] for r in info if r[2] is not None and r[2] != ""]
        if cols == ["name"]:
            return True
    return False


def _sqlite_create_sql_categories_unique_nom_seul(conn: sqlite3.Connection) -> bool:
    """Détecte un UNIQUE sur ``name`` dans le CREATE TABLE (sans couple owner_user_id + name)."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'"
    ).fetchone()
    if not row or not row[0]:
        return False
    s = row[0].replace("\n", " ")
    compact = re.sub(r"\s+", "", s)
    if "UNIQUE(owner_user_id,name)" in compact or "UNIQUE(name,owner_user_id)" in compact:
        return False
    if re.search(r"\bname\b\s+VARCHAR\([^)]*\)\s+NOT\s+NULL\s+UNIQUE", s, re.IGNORECASE):
        return True
    if re.search(r"UNIQUE\s*\(\s*name\s*\)", s, re.IGNORECASE):
        return True
    return False


def _migrate_categories_unique_proprietaire_nom_sqlite(engine) -> None:
    """
    Anciennes BD : ``categories.name`` était UNIQUE seul → impossible d’avoir « Plomberie »
    pour deux utilisateurs. Reconstruit la table avec UNIQUE (owner_user_id, name).
    """
    db_path = _chemin_fichier_sqlite_migre(engine)
    if db_path is None or not db_path.is_file():
        return
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='categories'"
        )
        if cur.fetchone() is None:
            return
        if _sqlite_categories_a_unique_composite_owner_nom(conn):
            return
        if not (
            _sqlite_categories_a_unique_global_sur_nom_seul(conn)
            or _sqlite_create_sql_categories_unique_nom_seul(conn)
        ):
            return
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE categories RENAME TO categories_old")
        conn.execute(
            """
            CREATE TABLE categories (
                id INTEGER NOT NULL,
                owner_user_id INTEGER,
                name VARCHAR(120) NOT NULL,
                image_url VARCHAR(500),
                PRIMARY KEY (id),
                FOREIGN KEY (owner_user_id) REFERENCES users (id),
                UNIQUE (owner_user_id, name)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO categories (id, owner_user_id, name, image_url)
            SELECT id, owner_user_id, name, image_url FROM categories_old
            """
        )
        conn.execute("DROP TABLE categories_old")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error:
            pass
        conn.close()
