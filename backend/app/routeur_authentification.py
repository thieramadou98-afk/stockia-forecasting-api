"""
Routes d'authentification : inscription, obtention du jeton JWT, profil connecté.

Le flux OAuth2 « password » est standard pour les SPA : POST /token avec username/password.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .dependances_injection import SessionDep, UserDep
from .modeles_tables_stock import User
from .schemas_echange_api import TokenResponse, UserCreate, UserProfileUpdate, UserRead
from .securite_authentification import creer_jeton_acces, hacher_mot_de_passe, verifier_mot_de_passe
from .service_catalogue_initial_utilisateur import dupliquer_catalogue_reference_pour_utilisateur

router = APIRouter(prefix="/api/auth", tags=["authentification"])


def _identifiant_demo_reserve(username: str) -> bool:
    """L’identifiant « demo » n’est plus autorisé (ancien compte de démonstration)."""
    return username.strip().lower() == "demo"


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def inscription_utilisateur(payload: UserCreate, db: SessionDep) -> User:
    """
    Crée un compte utilisateur (mot de passe haché). Utilisé une première fois ou pour les tests.

    En production, on restreindrait cette route aux administrateurs.
    """
    if _identifiant_demo_reserve(payload.username):
        raise HTTPException(
            status_code=400,
            detail="Ce nom d'utilisateur est réservé ; choisissez un autre identifiant",
        )
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur est déjà pris")
    email_norm = str(payload.email).strip().lower()
    exists_mail = db.query(User).filter(User.email == email_norm).first()
    if exists_mail:
        raise HTTPException(
            status_code=400,
            detail="Cette adresse courriel est déjà associée à un compte existant",
        )
    user = User(
        username=payload.username,
        hashed_password=hacher_mot_de_passe(payload.password),
        is_active=True,
        organization_name=payload.organization_name.strip(),
        email=email_norm,
        phone=payload.phone.strip(),
        address_line=payload.address_line.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    dupliquer_catalogue_reference_pour_utilisateur(db, user.id)
    return user


@router.post("/token", response_model=TokenResponse)
def connexion_jeton_oauth2(
    db: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """
    Émet un JWT si les identifiants sont valides.

    Après authentification, assure le catalogue gabarit (rayons + articles) pour ce compte
    s’il est encore vide : ventes, rapports et mouvements ne portent que sur les données
    ``owner_user_id`` du jeton.

    FastAPI attend un formulaire x-www-form-urlencoded (champs username, password).
    Le champ password du formulaire OAuth2 porte le mot de passe (nom imposé par la norme).
    """
    if _identifiant_demo_reserve(form_data.username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verifier_mot_de_passe(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Compte désactivé")
    # Gabarit rayons + articles si le compte n’en a pas encore (inscription ancienne, etc.)
    dupliquer_catalogue_reference_pour_utilisateur(db, user.id)
    token = creer_jeton_acces(user.username)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def profil_connecte(user: UserDep, db: SessionDep) -> User:
    """Retourne l'utilisateur associé au jeton Bearer (vérifie que la session est valide)."""
    dupliquer_catalogue_reference_pour_utilisateur(db, user.id)
    db.refresh(user)
    return user


@router.patch("/me", response_model=UserRead)
def maj_profil_connecte(payload: UserProfileUpdate, user: UserDep, db: SessionDep) -> User:
    """
    Met à jour les métadonnées d’établissement du compte connecté.
    Seuls les champs présents dans le corps JSON sont modifiés (sémantique PATCH).
    """
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Aucun champ fourni pour la mise à jour")

    if "email" in data:
        if data["email"] is None:
            user.email = None
        else:
            email_norm = str(data["email"]).strip().lower()
            exists = (
                db.query(User)
                .filter(User.email == email_norm, User.id != user.id)
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=400,
                    detail="Cette adresse courriel est déjà associée à un autre compte",
                )
            user.email = email_norm

    if "organization_name" in data:
        user.organization_name = data["organization_name"]
    if "phone" in data:
        user.phone = data["phone"]
    if "address_line" in data:
        user.address_line = data["address_line"]

    db.commit()
    db.refresh(user)
    return user
