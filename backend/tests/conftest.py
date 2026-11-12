"""
Configuration pytest : base SQLite dédiée aux tests (ne mélange pas avec stockia.db de dev).

Ce fichier est chargé en premier par pytest : on fixe STOCKIA_DATABASE_URL avant tout import de `app`.
"""
import os
from pathlib import Path

# Fichier de BD uniquement pour la suite de tests (supprimé au début pour repartir propre)
_TEST_DB_PATH = Path(__file__).resolve().parent / "test_stockia.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

# URL absolue pour SQLite sous Windows et Linux
os.environ["STOCKIA_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
