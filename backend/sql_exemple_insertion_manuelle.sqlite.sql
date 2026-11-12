-- SQLite pour StockIA.
-- crée déjà les tables et le catalogue via SQLAlchemy (initialisation_donnees_demonstration).
-- Après modification du schéma, supprimez stockia.db ou migrez les colonnes avant d'exécuter ce fichier.

-- Catégories (noms uniques)
INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'Gros œuvre');
INSERT OR IGNORE INTO categories (id, name) VALUES (2, 'Plomberie');

-- Produits : unit, price, sku (code article unique si renseigné), reference_url (fiche publique)
INSERT OR IGNORE INTO products (id, name, category_id, min_stock, description, unit, price, sku, brand, reference_url)
VALUES (
  1,
  'Ciment Portland 40 kg',
  1,
  60,
  'Sac pour béton et mortier (exemple).',
  'sac',
  8.99,
  NULL,
  'ExempleMarque',
  NULL
);

-- Mouvement d’entrée puis sortie (quantités positives ; le type indique le sens)
INSERT OR IGNORE INTO stock_movements (id, product_id, movement_type, quantity, note, created_at)
VALUES (1, 1, 'entree', 200, 'Livraison fournisseur', datetime('now', '-30 days'));
INSERT OR IGNORE INTO stock_movements (id, product_id, movement_type, quantity, note, created_at)
VALUES (2, 1, 'sortie', 12, 'Vente', datetime('now', '-1 days'));

-- Utilisateur : le mot de passe doit être haché (bcrypt) en vrai ; utilisez plutôt POST /api/auth/register.
