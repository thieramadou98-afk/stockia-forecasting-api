"""
Sécurité : hachage des mots de passe (bcrypt) et jetons JWT pour l'API.

Répond à l'exigence « authentification de base » du projet StockIA.
Les mots de passe ne sont jamais stockés en clair.
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

# Clé secrète : obligatoire en production via STOCKIA_SECRET_KEY (voir backend/env.example)
SECRET_KEY = os.environ.get(
    "STOCKIA_SECRET_KEY",
    "changez-moi-en-production-stockia-8inf206",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 heures de session pour la démo


def hacher_mot_de_passe(plain: str) -> str:
    """Transforme le mot de passe en empreinte bcrypt (salt intégré) stockée en base."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verifier_mot_de_passe(plain: str, hashed: str) -> bool:
    """Vérifie le mot de passe saisi contre l'empreinte bcrypt enregistrée."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def creer_jeton_acces(subject_username: str) -> str:
    """
    Génère un JWT signé contenant le nom d'utilisateur (sub) et l'expiration.

    Le client renverra ce jeton dans Authorization: Bearer <token>.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject_username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_nom_utilisateur_depuis_jeton(token: str) -> str | None:
    """
    Décode et valide le JWT ; retourne le « sub » (username) ou None si invalide.
    """
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = data.get("sub")
        return str(sub) if sub else None
    except JWTError:
        return None
