"""
Injections FastAPI : session base de données et utilisateur courant (JWT).

« Depends » permet de réutiliser la même logique sur plusieurs routes (DRY).
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .modeles_tables_stock import User
from .securite_authentification import decoder_nom_utilisateur_depuis_jeton

# Schéma OAuth2 : attend un jeton dans Authorization Bearer (formulaire token aussi supporté)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def obtenir_session_bd():
    """
    Fournit une session SQLAlchemy par requête HTTP, puis la ferme (try/finally).

    Évite les fuites de connexion et isole les transactions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias typé pour raccourcir les signatures : Annotated injecte automatiquement
SessionDep = Annotated[Session, Depends(obtenir_session_bd)]


def obtenir_utilisateur_courant(db: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    Dépendance : valide le JWT, charge l'utilisateur en BD, sinon 401 Unauthorized.

    À ajouter aux routes protégées via Depends(obtenir_utilisateur_courant).
    """
    username = decoder_nom_utilisateur_depuis_jeton(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    return user


UserDep = Annotated[User, Depends(obtenir_utilisateur_courant)]
