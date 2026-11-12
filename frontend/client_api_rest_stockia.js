/**
 * client_api_rest_stockia.js
 * Client HTTP pour l'API StockIA : ajoute automatiquement le jeton JWT sur chaque requête.
 *
 * Usage pédagogique : montre comment un front SPA consomme une API REST sécurisée
 * (authentification Bearer), conforme au cours sur l'intégration d'API Web.
 */

/** Clé localStorage où est stocké le jeton après connexion (persistance côté navigateur). */
const CLE_STOCKAGE_JETON = "stockia_jwt";

/** Promesse mise en cache pour éviter plusieurs GET /auth/me sur une même page. */
let _profilStockiaPromise = null;

/** Préfixe des routes API (même origine que /ui/ quand tout est servi par FastAPI). */
const PREFIX_API = "/api";

/**
 * L'API persiste les horodatages en UTC (``datetime.utcnow``) mais les renvoie souvent en ISO **sans** « Z ».
 * Sans correction, ``new Date("…T12:00:00")`` est interprété comme **heure locale**, ce qui décale la date affichée.
 *
 * @param {string|Date|null|undefined} iso
 * @returns {Date}
 */
function parseApiDateTimeUtcNaive(iso) {
    if (iso == null || iso === "") return new Date(NaN);
    if (iso instanceof Date) return iso;
    const s = String(iso).trim();
    if (!s) return new Date(NaN);
    if (/[zZ]$|[+-]\d{2}:\d{2}$|[+-]\d{4}$/.test(s)) {
        return new Date(s);
    }
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) {
        return new Date(s.endsWith("Z") ? s : s + "Z");
    }
    return new Date(s);
}

/**
 * Affiche un instant API en fuseau **local** du navigateur (fr-CA).
 *
 * @param {string|null|undefined} iso
 * @returns {string}
 */
function formaterDateHeureApiFrCa(iso) {
    const d = parseApiDateTimeUtcNaive(iso);
    return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("fr-CA");
}

/**
 * Fuseau IANA du navigateur (pour que l’API interprète les dates ``<input type="date">`` comme jours locaux).
 * @returns {string}
 */
function fuseauIANACalendrier() {
    try {
        const z = Intl.DateTimeFormat().resolvedOptions().timeZone;
        return z && typeof z === "string" && z.length > 0 ? z : "America/Toronto";
    } catch {
        return "America/Toronto";
    }
}

/**
 * Fragment de query HTTP ``&timezone=…`` pour les rapports (Ventes, inventaire, etc.).
 * @returns {string}
 */
function paramRequeteFuseauCalendrier() {
    return "&timezone=" + encodeURIComponent(fuseauIANACalendrier());
}

/**
 * Lit le jeton sauvegardé ; retourne null si l'utilisateur n'est pas connecté.
 */
function lireJeton() {
    return localStorage.getItem(CLE_STOCKAGE_JETON);
}

/**
 * Enregistre ou efface le jeton (déconnexion = removeItem).
 */
function enregistrerJeton(token) {
    _profilStockiaPromise = null;
    if (token) {
        localStorage.setItem(CLE_STOCKAGE_JETON, token);
    } else {
        localStorage.removeItem(CLE_STOCKAGE_JETON);
    }
}

/**
 * Profil JSON retourné par GET /api/auth/me (jeton Bearer requis).
 * @param {{ force?: boolean }} [opts]
 * @returns {Promise<object|null>}
 */
async function chargerProfilUtilisateur(opts) {
    const force = opts && opts.force;
    if (!lireJeton()) {
        return null;
    }
    if (force) {
        _profilStockiaPromise = null;
    }
    if (!_profilStockiaPromise) {
        _profilStockiaPromise = (async () => {
            try {
                const r = await appelerApi("/auth/me");
                if (!r.ok) {
                    return null;
                }
                return await lireReponseJson(r);
            } catch {
                return null;
            }
        })();
    }
    return _profilStockiaPromise;
}

/**
 * Nom affiché pour le magasin / entreprise (en-tête, fiches imprimables).
 * N’utilise pas l’identifiant de connexion : un pseudo ne doit pas passer pour la raison sociale.
 * @param {object|null} profil
 * @returns {string}
 */
function libelleAffichageEtablissement(profil) {
    if (!profil) return "—";
    const o = (profil.organization_name || "").trim();
    if (o.length >= 2) return o;
    return "Magasin / entreprise (non renseigné)";
}

/**
 * Remplit un conteneur (fiche imprimable) avec les coordonnées de l’établissement.
 * @param {string} elementId
 */
async function injecterFicheEtablissement(elementId) {
    const el = document.getElementById(elementId);
    if (!el) {
        return;
    }
    const profil = await chargerProfilUtilisateur();
    el.textContent = "";
    if (!profil) {
        el.classList.add("d-none");
        return;
    }
    el.classList.remove("d-none");
    const nom = libelleAffichageEtablissement(profil);
    const email = profil.email || "—";
    const tel = profil.phone || "—";
    const adr = profil.address_line || "—";

    const wrap = document.createElement("div");
    wrap.className = "stockia-fiche-etablissement-inner px-3 py-2 border-bottom";

    const titre = document.createElement("div");
    titre.className = "stockia-fiche-entete text-uppercase text-secondary mb-2";
    titre.textContent = "Profil établissement";
    wrap.appendChild(titre);

    const h = document.createElement("div");
    h.className = "stockia-fiche-nom-magasin fw-bold mb-2";
    h.textContent = nom;
    wrap.appendChild(h);

    function ligne(label, valeur) {
        const d = document.createElement("div");
        d.className = "stockia-fiche-ligne mb-1";
        const lab = document.createElement("span");
        lab.className = "stockia-fiche-ligne-label";
        lab.textContent = label + " :";
        const val = document.createElement("span");
        val.className = "stockia-fiche-ligne-valeur";
        val.textContent = "\u00a0" + valeur;
        d.appendChild(lab);
        d.appendChild(val);
        return d;
    }

    wrap.appendChild(ligne("Adresse", adr));
    wrap.appendChild(ligne("Courriel", email));
    wrap.appendChild(ligne("Téléphone", tel));
    el.appendChild(wrap);
}

/**
 * Appel fetch générique vers l'API : fusionne les en-têtes JSON + Authorization.
 * @param {string} chemin - ex. "/products" → requête GET /api/products
 * @param {RequestInit} options - options fetch (method, body, …)
 */
async function appelerApi(chemin, options = {}) {
    const jeton = lireJeton();
    const headers = new Headers(options.headers || {});
    if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
        headers.set("Content-Type", "application/json");
    }
    if (jeton) {
        headers.set("Authorization", "Bearer " + jeton);
    }
    const reponse = await fetch(PREFIX_API + chemin, { ...options, headers });
    if (reponse.status === 401) {
        enregistrerJeton(null);
        window.location.href = "connexion_utilisateur.html";
        throw new Error("Session expirée");
    }
    return reponse;
}

/**
 * Parse JSON si possible ; sinon lève une erreur avec le texte brut du serveur.
 */
async function lireReponseJson(reponse) {
    const texte = await reponse.text();
    if (!texte) {
        return null;
    }
    try {
        return JSON.parse(texte);
    } catch {
        throw new Error(texte);
    }
}

/**
 * Formate le champ `detail` d’une erreur FastAPI (chaîne, liste de validation, ou objet).
 * @param {object} data
 * @returns {string}
 */
function formaterDetailErreurApi(data) {
    if (typeof data.detail === "string") {
        return data.detail;
    }
    if (Array.isArray(data.detail)) {
        return data.detail
            .map((e) => (e && e.msg ? `${e.loc ? e.loc.join(".") + " : " : ""}${e.msg}` : JSON.stringify(e)))
            .join(" · ");
    }
    return JSON.stringify(data.detail || data);
}

/** Aligné sur les contraintes côté API (inscription / profil). */
const STOCKIA_RE_COURIEL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * @param {string} v
 * @returns {string} chaîne vide si valide, sinon message d’erreur affichable
 */
function stockiaMessageErreurCourriel(v) {
    const t = String(v || "").trim();
    if (!t) {
        return "Veuillez saisir une adresse courriel.";
    }
    if (!t.includes("@")) {
        return 'Veuillez inclure « @ » dans l’adresse courriel. Il manque un symbole « @ » dans votre saisie.';
    }
    if (!STOCKIA_RE_COURIEL.test(t)) {
        return "Adresse courriel invalide (format attendu : nom@domaine.ca).";
    }
    return "";
}

/**
 * Téléphone international : « + » obligatoire, 8 à 15 chiffres ; pour +1, exactement 10 chiffres nationaux (11 chiffres au total).
 * @param {string} v
 * @returns {string} chaîne vide si valide, sinon message d’erreur affichable
 */
function stockiaMessageErreurTelephone(v) {
    const t = String(v || "").trim();
    if (!t) {
        return "Veuillez saisir un numéro de téléphone.";
    }
    if (!t.startsWith("+")) {
        return "Préfixez le numéro avec l’indicatif pays « + » (ex. : +1 450 555 0100 pour le Canada ou les États-Unis).";
    }
    if (t.length > 40) {
        return "Numéro trop long (40 caractères maximum).";
    }
    if (!/^[+\d\s().\-]+$/.test(t)) {
        return "Utilisez uniquement des chiffres et les séparateurs « + », espaces, ( ), . et tiret.";
    }
    const digits = t.replace(/\D/g, "");
    if (digits.length < 8 || digits.length > 15) {
        return "Numéro incomplet ou invalide : en format international, de 8 à 15 chiffres au total.";
    }
    if (digits[0] === "1") {
        if (digits.length !== 11) {
            return "Pour l’indicatif +1 (Canada / États-Unis), saisissez exactement 10 chiffres après le 1 (ex. : +1 450 555 0100).";
        }
        const npa = parseInt(digits.slice(1, 4), 10);
        if (Number.isNaN(npa) || npa < 200 || npa > 999) {
            return "Indicatif régional invalide : après +1, les trois premiers chiffres doivent être entre 200 et 999.";
        }
    }
    return "";
}
