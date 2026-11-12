/**
 * Thème visuel StockIA.web : présentation type magasin de matériaux (noir / jaune, rayons).
 * Images de rayon : photos libres de droits (Unsplash) — usage décoratif uniquement.
 */
const MARQUE_NAV = "StockIA.web";

/**
 * Couleur d’accent + visuels par rayon (Unsplash, usage autorisé).
 * Les clés doivent correspondre aux noms de catégories renvoyés par l’API.
 */
const THEME_PAR_CATEGORIE = {
    Saisonnier: {
        hex: "#2e7d32",
        image: "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?auto=format&fit=crop&w=800&q=82",
        libelle: "Extérieur, jardin, saisonnier",
    },
    Cuisine: {
        hex: "#c62828",
        image: "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=800&q=82",
        libelle: "Cuisine & robinetterie",
    },
    "Salle de bains": {
        hex: "#1565c0",
        image: "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&w=800&q=82",
        libelle: "Salle de bains",
    },
    "Maison et Décoration": {
        hex: "#7b1fa2",
        image: "https://images.unsplash.com/photo-1562259949-e8e7689d7828?auto=format&fit=crop&w=800&q=82",
        libelle: "Maison & décoration",
    },
    Matériaux: {
        hex: "#6d4c41",
        image: "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=800&q=82",
        libelle: "Bois, gypse, structure",
    },
    "Couvre-plancher": {
        hex: "#5d4037",
        image: "https://images.unsplash.com/photo-1585128798505-67238311c8c7?auto=format&fit=crop&w=800&q=82",
        libelle: "Planchers & céramique",
    },
    "Électricité et Luminaires": {
        hex: "#f9a825",
        image: "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=800&q=82",
        libelle: "Électricité & luminaires",
    },
    "Chauffage - Ventilation - Climatisation": {
        hex: "#00838f",
        image: "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?auto=format&fit=crop&w=800&q=82",
        libelle: "CVC & confort thermique",
    },
    Outillage: {
        hex: "#37474f",
        image: "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=800&q=82",
        libelle: "Outillage",
    },
    Peinture: {
        hex: "#e65100",
        image: "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?auto=format&fit=crop&w=800&q=82",
        libelle: "Peinture & finition",
    },
    Plomberie: {
        hex: "#0277bd",
        image: "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&w=800&q=82",
        libelle: "Plomberie",
    },
    Quincaillerie: {
        hex: "#455a64",
        image: "https://images.unsplash.com/photo-1530124566582-a618bc261670?auto=format&fit=crop&w=800&q=82",
        libelle: "Quincaillerie",
    },
};

/** Photo de repli si le rayon n’a ni thème ni image en base (Unsplash). */
const IMAGE_FOND_RAYON_DEFAUT =
    "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=max&w=1600&q=82";

/** URL pour arrière-plan : fit=max limite le cadrage serré (mieux avec background-size: contain côté CSS). */
function imageFondPourCategorie(theme) {
    if (!theme || !theme.image) return "";
    const base = theme.image.split("?")[0];
    return `${base}?auto=format&fit=max&w=1600&q=82`;
}

const ORDRE_RAYONS = Object.keys(THEME_PAR_CATEGORIE);

function themePourCategorie(nom) {
    if (!nom) {
        return { hex: "#6c757d", image: null, libelle: "Sans catégorie" };
    }
    return THEME_PAR_CATEGORIE[nom] || { hex: "#546e7a", image: null, libelle: nom };
}

function hexVersRgba(hex, alpha) {
    const h = hex.replace("#", "");
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

function comparerNomsRayons(a, b) {
    const ia = ORDRE_RAYONS.indexOf(a);
    const ib = ORDRE_RAYONS.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b, "fr");
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
}

/**
 * Grande image de fond (Unsplash du thème). Les icônes SVG du catalogue API ne remplacent pas ce fond.
 * Exception : image téléversée par l’utilisateur (dossier category_backgrounds).
 */
function urlFondPhotoPleinEcranPourRayon(urlImageApi, nomRayon) {
    const u = (urlImageApi || "").trim();
    const estTeleversement =
        u.includes("/ui/media/category_backgrounds/") || u.includes("media/category_backgrounds/");
    const theme = themePourCategorie(
        nomRayon === "Sans catégorie" || !nomRayon ? null : nomRayon,
    );
    if (estTeleversement && u) {
        return u;
    }
    if (theme.image) {
        return imageFondPourCategorie(theme);
    }
    if (u) {
        return u;
    }
    return imageFondPourCategorie({ image: IMAGE_FOND_RAYON_DEFAUT });
}

/**
 * Icône petite (ex. SVG /ui/images/categories/…) à afficher à côté du titre ; pas pour les fonds téléversés.
 */
function urlIconeRayonPourEntete(urlImageApi) {
    const u = (urlImageApi || "").trim();
    if (!u || u.includes("/ui/media/category_backgrounds/")) {
        return "";
    }
    return u;
}

if (typeof globalThis !== "undefined") {
    globalThis.IMAGE_FOND_RAYON_DEFAUT = IMAGE_FOND_RAYON_DEFAUT;
    globalThis.urlFondPhotoPleinEcranPourRayon = urlFondPhotoPleinEcranPourRayon;
    globalThis.urlIconeRayonPourEntete = urlIconeRayonPourEntete;
}
