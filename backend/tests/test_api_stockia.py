"""
Tests automatisés de l'API StockIA (FastAPI TestClient).

À lancer depuis le dossier backend : pytest
Ou dans VS Code : icône Testing, ou palette « Python: Run All Tests ».

Le client HTTP simule un navigateur ; le gestionnaire de contexte déclenche le démarrage
de l'app (création des tables + catalogue de référence si BD vide — sans compte prédéfini).
"""
import uuid

from fastapi.testclient import TestClient

# Import après conftest.py (env STOCKIA_DATABASE_URL déjà défini)
from app.main import app


def _inscription_et_jeton(client: TestClient) -> str:
    """Inscrit un utilisateur avec profil établissement complet et retourne un JWT."""
    u = f"t_{uuid.uuid4().hex[:14]}"
    reg = {
        "username": u,
        "password": "secret12",
        "organization_name": "Magasin Test API",
        "email": f"{u}@example.org",
        "phone": "+1 418-555-0100",
        "address_line": "100 rue Test, Chicoutimi QC",
    }
    assert client.post("/api/auth/register", json=reg).status_code == 201, reg
    r = client.post("/api/auth/token", data={"username": u, "password": "secret12"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_sante_api():
    """Vérifie que l'endpoint de santé répond (smoke test)."""
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"
        assert r.json().get("service") == "StockIA.web"


def test_connexion_jeton_apres_inscription():
    """Après inscription, l’API émet un jeton JWT valide."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        assert len(token) > 20


def test_inscription_identifiant_demo_reserve():
    """L’identifiant « demo » ne peut plus être choisi à l’inscription."""
    with TestClient(app) as client:
        r = client.post(
            "/api/auth/register",
            json={
                "username": "demo",
                "password": "demo123",
                "organization_name": "Test réservé",
                "email": "demo-reserve@example.org",
                "phone": "+1 418-555-0100",
                "address_line": "1 rue Y",
            },
        )
        assert r.status_code == 400


def test_connexion_identifiant_demo_rejetee():
    """Aucun jeton pour l’identifiant « demo », même si un mot de passe est fourni."""
    with TestClient(app) as client:
        r = client.post("/api/auth/token", data={"username": "demo", "password": "demo123"})
        assert r.status_code == 401


def test_compte_demo_supprime_au_demarrage_si_present():
    """Un utilisateur « demo » présent en base est retiré au cycle de vie de l’app ; connexion impossible."""
    from app.database import SessionLocal, init_db
    from app.initialisation_donnees_demonstration import retirer_compte_demonstration_obsolete
    from app.modeles_tables_stock import User
    from app.securite_authentification import hacher_mot_de_passe

    init_db()
    db = SessionLocal()
    try:
        retirer_compte_demonstration_obsolete(db)
        db.add(
            User(
                username="demo",
                hashed_password=hacher_mot_de_passe("demo123"),
                is_active=True,
                organization_name="Ancien compte",
                email="ancien-demo@example.org",
                phone="+1 418-555-0100",
                address_line="1 rue Test",
            )
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        r = client.post("/api/auth/token", data={"username": "demo", "password": "demo123"})
        assert r.status_code == 401


def test_profil_me_apres_inscription():
    """GET /api/auth/me renvoie le profil établissement saisi à l’inscription."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["username"].startswith("t_")
        assert body.get("organization_name") == "Magasin Test API"
        assert body.get("email", "").endswith("@example.org")


def test_me_remplit_catalogue_si_compte_sans_rayons():
    """Compte existant sans catégories : GET /api/auth/me déclenche le gabarit ; les produits apparaissent."""
    from app.database import SessionLocal, init_db
    from app.modeles_tables_stock import User
    from app.securite_authentification import hacher_mot_de_passe

    init_db()
    u = f"legacy_{uuid.uuid4().hex[:12]}"
    db = SessionLocal()
    try:
        db.add(
            User(
                username=u,
                hashed_password=hacher_mot_de_passe("secret12"),
                is_active=True,
                organization_name="SuperConstruction",
                email=f"{u}@example.org",
                phone="+1 418-555-0100",
                address_line="1 rue Test",
            )
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        r = client.post("/api/auth/token", data={"username": u, "password": "secret12"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/auth/me", headers=h).status_code == 200
        prods = client.get("/api/products", headers=h)
        assert prods.status_code == 200
        assert len(prods.json()) >= 90
        cats = client.get("/api/categories", headers=h)
        assert cats.status_code == 200
        assert len(cats.json()) == 12


def test_televersement_image_fond_rayon_png():
    """POST /categories/{id}/background enregistre l’image et met à jour image_url + ProductRead."""
    # PNG 1×1 pixel (transparent)
    png_mini = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        cats = client.get("/api/categories", headers=h)
        assert cats.status_code == 200
        cid = cats.json()[0]["id"]
        r = client.post(
            f"/api/categories/{cid}/background",
            headers=h,
            files={"file": ("test.png", png_mini, "image/png")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["image_url"].startswith("/ui/media/category_backgrounds/")
        prods = client.get("/api/products", headers=h).json()
        assert any(p.get("category_image_url") == body["image_url"] for p in prods if p.get("category_id") == cid)


def test_inscription_avec_profil_etablissement():
    """L’inscription exige les champs établissement et les persiste ; courriel unique."""
    with TestClient(app) as client:
        u = f"u_{uuid.uuid4().hex[:10]}"
        payload = {
            "username": u,
            "password": "secret12",
            "organization_name": "Quincaillerie Test",
            "email": f"{u}@example.org",
            "phone": "+1 418-555-0100",
            "address_line": "100 rue Exemple, Chicoutimi QC",
        }
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["organization_name"] == "Quincaillerie Test"
        assert data["email"] == payload["email"].lower()
        r2 = client.post("/api/auth/register", json={**payload, "username": f"{u}_2"})
        assert r2.status_code == 400


def test_inscription_telephone_sans_indicatif_plus_rejetee():
    """Sans « + » et indicatif pays, l’API refuse le numéro (aligné sur le formulaire)."""
    with TestClient(app) as client:
        u = f"u_{uuid.uuid4().hex[:10]}"
        r = client.post(
            "/api/auth/register",
            json={
                "username": u,
                "password": "secret12",
                "organization_name": "Test Tel",
                "email": f"{u}@example.org",
                "phone": "4505550100",
                "address_line": "100 rue X, Ville QC",
            },
        )
        assert r.status_code == 422


def test_inscription_telephone_plus1_incomplet_rejetee():
    """+1 avec moins de 10 chiffres nationaux (ex. +1450193648) → rejet."""
    with TestClient(app) as client:
        u = f"u_{uuid.uuid4().hex[:10]}"
        r = client.post(
            "/api/auth/register",
            json={
                "username": u,
                "password": "secret12",
                "organization_name": "Test Tel",
                "email": f"{u}@example.org",
                "phone": "+1450193648",
                "address_line": "100 rue X, Ville QC",
            },
        )
        assert r.status_code == 422


def test_patch_me_corps_vide():
    """PATCH /api/auth/me sans aucun champ explicite → 400."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.patch("/api/auth/me", headers=h, json={})
        assert r.status_code == 400


def test_patch_me_maj_profil_partiel():
    """PATCH /api/auth/me ne modifie que les champs envoyés ; les autres restent inchangés."""
    with TestClient(app) as client:
        u = f"patch_{uuid.uuid4().hex[:10]}"
        mail = f"{u}@example.org"
        reg = {
            "username": u,
            "password": "secret12",
            "organization_name": "Avant mise à jour",
            "email": mail,
            "phone": "+1 418-111-1111",
            "address_line": "1 rue A, Ville QC",
        }
        assert client.post("/api/auth/register", json=reg).status_code == 201
        token = client.post("/api/auth/token", data={"username": u, "password": "secret12"}).json()[
            "access_token"
        ]
        h = {"Authorization": f"Bearer {token}"}
        r = client.patch(
            "/api/auth/me",
            headers=h,
            json={"organization_name": "Après PATCH", "phone": "+1 418-222-2222"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["organization_name"] == "Après PATCH"
        assert body["email"] == mail
        assert body["phone"] == "+1 418-222-2222"
        assert body["address_line"] == "1 rue A, Ville QC"


def test_patch_me_courriel_deja_utilise():
    """On ne peut pas attribuer un courriel déjà lié à un autre compte."""
    with TestClient(app) as client:
        u1 = f"p1_{uuid.uuid4().hex[:8]}"
        u2 = f"p2_{uuid.uuid4().hex[:8]}"
        mail = f"unique_{uuid.uuid4().hex[:10]}@example.org"
        base = {
            "password": "secret12",
            "organization_name": "Org Test",
            "phone": "+1 418-555-0100",
            "address_line": "100 rue X, Ville QC",
        }
        assert client.post("/api/auth/register", json={**base, "username": u1, "email": mail}).status_code == 201
        assert (
            client.post(
                "/api/auth/register",
                json={
                    **base,
                    "username": u2,
                    "email": f"autre_{uuid.uuid4().hex[:8]}@example.org",
                },
            ).status_code
            == 201
        )
        token2 = client.post("/api/auth/token", data={"username": u2, "password": "secret12"}).json()[
            "access_token"
        ]
        r = client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
            json={"email": mail},
        )
        assert r.status_code == 400


def test_produits_proteges_sans_jeton():
    """Sans Authorization, l'API doit refuser l'accès (401)."""
    with TestClient(app) as client:
        r = client.get("/api/products")
        assert r.status_code == 401


def test_produits_avec_jeton():
    """Avec Bearer token, la liste des produits est accessible."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        r = client.get("/api/products", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "quantity_stock" in data[0]


def test_sortie_stock_insuffisant():
    """Une sortie supérieure au stock disponible doit être refusée (422)."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        # Créer un produit avec stock 0 (aucun mouvement)
        r = client.post(
            "/api/products",
            headers=h,
            json={"name": "Produit test stock zero", "min_stock": 0, "category_id": None},
        )
        assert r.status_code == 201
        pid = r.json()["id"]
        r2 = client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={"movement_type": "sortie", "quantity": 5},
        )
        assert r2.status_code == 422


def test_insights_ia():
    """Les prévisions IA renvoient une liste avec les champs attendus."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        r = client.get("/api/insights", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        first = rows[0]
        assert "stockout_risk_level" in first
        assert "recommended_order_qty" in first
        assert "lead_time_days" in first
        assert "reorder_point_qty" in first
        assert "safety_stock_qty" in first


def test_tableau_de_bord_resume():
    """Synthèse dashboard : liste des produits avec stock et seuil (plan : tableaux)."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/dashboard/summary", headers=h)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert "quantity_stock" in rows[0]
        assert "below_min" in rows[0]


def test_dashboard_widgets():
    """Mini-listes KPI : structure JSON attendue."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/dashboard/widgets?jours=30", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert "top_sorties" in d
        assert "recents_catalogue" in d
        assert d.get("periode_jours") == 30


def test_rapport_inventaire_periode():
    """Rapport inventaire sur une plage de dates."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.get(
            "/api/reports/inventory-period?date_debut=2020-01-01&date_fin=2030-12-31",
            headers=h,
        )
        assert r.status_code == 200
        d = r.json()
        assert "meta" in d and "rows" in d
        assert len(d["rows"]) >= 1
        row0 = d["rows"][0]
        assert "stock_debut" in row0
        assert "sorties_vente" in row0
        assert "sorties_perte" in row0
        assert "sorties_autre" in row0


def test_rapport_ventes_agrege():
    """Rapport ventes (sorties vente agrégées) : structure JSON."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.get(
            "/api/reports/ventes?groupe=jour&date_debut=2020-01-01&date_fin=2030-12-31",
            headers=h,
        )
        assert r.status_code == 200
        d = r.json()
        assert "meta" in d and "rows" in d
        assert d["meta"]["groupe"] == "jour"
        assert isinstance(d["rows"], list)


def test_maintenance_supprimer_mouvements_demonstration():
    """Supprime les mouvements dont la note ressemble à de la donnée de démonstration."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r0 = client.get("/api/products", headers=h)
        assert r0.status_code == 200
        pid = r0.json()[0]["id"]
        client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={
                "movement_type": "entree",
                "quantity": 5,
                "note": "entrée test purge démo",
            },
        )
        client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={
                "movement_type": "sortie",
                "quantity": 1,
                "sortie_kind": "vente",
                "note": "Sortie simulée (test API)",
            },
        )
        r = client.post("/api/maintenance/supprimer-mouvements-demonstration", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data.get("mouvements_supprimes", 0) >= 1


def test_sortie_vente_enregistre_sale_unit_price():
    """Une sortie vente avec prix explicite renvoie sale_unit_price dans la réponse."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        r0 = client.post(
            "/api/products",
            headers=h,
            json={"name": "Article test prix vente", "min_stock": 0, "category_id": None, "price": 10.0},
        )
        assert r0.status_code == 201
        pid = r0.json()["id"]
        client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={"movement_type": "entree", "quantity": 3},
        )
        r2 = client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={
                "movement_type": "sortie",
                "quantity": 1,
                "sortie_kind": "vente",
                "sale_unit_price": 12.5,
            },
        )
        assert r2.status_code == 201
        body = r2.json()
        assert body.get("sale_unit_price") == 12.5


def test_supprimer_categorie_supprime_produits_et_mouvements():
    """Supprimer une catégorie supprime en cascade les produits du rayon et leurs mouvements."""
    with TestClient(app) as client:
        token = _inscription_et_jeton(client)
        h = {"Authorization": f"Bearer {token}"}
        nom_rayon = f"Rayon test cascade {uuid.uuid4().hex[:10]}"
        r_cat = client.post("/api/categories", headers=h, json={"name": nom_rayon})
        assert r_cat.status_code == 201
        cid = r_cat.json()["id"]
        r_p = client.post(
            "/api/products",
            headers=h,
            json={"name": "Produit test cascade cat", "min_stock": 0, "category_id": cid},
        )
        assert r_p.status_code == 201
        pid = r_p.json()["id"]
        client.post(
            f"/api/products/{pid}/movements",
            headers=h,
            json={"movement_type": "entree", "quantity": 5},
        )
        r_del = client.delete(f"/api/categories/{cid}", headers=h)
        assert r_del.status_code == 204
        assert client.get(f"/api/products/{pid}", headers=h).status_code == 404
        cats = client.get("/api/categories", headers=h).json()
        assert all(c["id"] != cid for c in cats)
