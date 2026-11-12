/**
 * Page dédiée : graphiques IA regroupés par catégorie (voir rayons_previsions_ia_commun.js).
 */

function construireCarteImagesRayons(categories) {
    const m = new Map();
    if (!Array.isArray(categories)) return m;
    for (const c of categories) {
        if (c && c.name && c.image_url) {
            m.set(String(c.name).trim(), String(c.image_url).trim());
        }
    }
    return m;
}

function remplirPanneauTeleversementFonds(categories, onUploaded) {
    const root = document.getElementById("liste-upload-fonds-rayons");
    if (!root) return;
    root.innerHTML = "";
    const liste = Array.isArray(categories)
        ? [...categories].sort((a, b) => String(a.name).localeCompare(String(b.name), "fr", { sensitivity: "base" }))
        : [];
    for (const cat of liste) {
        const id = cat.id;
        const nom = echapperHtml(cat.name || "");
        const col = document.createElement("div");
        col.className = "col-md-6 col-lg-4";
        col.innerHTML = `
            <div class="border rounded p-2 h-100 bg-light">
                <div class="fw-semibold small mb-2">${nom}</div>
                <input type="file" accept="image/jpeg,image/png,image/webp" class="form-control form-control-sm mb-2 stockia-input-fond-${id}" />
                <button type="button" class="btn btn-warning btn-sm w-100 stockia-btn-envoyer-fond" data-cat-id="${id}">Envoyer</button>
                <div class="small text-muted mt-1 stockia-msg-fond-${id}"></div>
            </div>`;
        root.appendChild(col);
    }
    root.querySelectorAll(".stockia-btn-envoyer-fond").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const cid = Number(btn.getAttribute("data-cat-id"));
            const inp = root.querySelector(`.stockia-input-fond-${cid}`);
            const msg = root.querySelector(`.stockia-msg-fond-${cid}`);
            if (!inp || !inp.files || !inp.files[0]) {
                if (msg) msg.textContent = "Choisissez un fichier.";
                return;
            }
            const fd = new FormData();
            fd.append("file", inp.files[0]);
            btn.disabled = true;
            if (msg) msg.textContent = "Envoi…";
            try {
                const r = await fetch(`/api/categories/${cid}/background`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${lireJeton()}` },
                    body: fd,
                });
                const txt = await r.text();
                if (!r.ok) {
                    let detail = txt;
                    try {
                        const j = JSON.parse(txt);
                        detail = j.detail || txt;
                    } catch {
                        /* ignore */
                    }
                    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
                }
                if (msg) msg.textContent = "Enregistré. Actualisation…";
                if (typeof onUploaded === "function") await onUploaded();
            } catch (e) {
                if (msg) msg.textContent = e.message || String(e);
            } finally {
                btn.disabled = false;
            }
        });
    });
}

function echapperHtml(t) {
    const d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    const R = window.StockIARayonsPrevisions;
    const conteneur = document.getElementById("conteneur-sections-rayons");
    const errEl = document.getElementById("erreur-previsions-cat");
    const btnToggle = document.getElementById("btn-toggle-upload-fonds");
    const corpsUpload = document.getElementById("corps-panneau-upload-fonds");

    if (!R || !conteneur) {
        if (errEl) {
            errEl.textContent = "Erreur de chargement du module graphiques.";
            errEl.classList.remove("d-none");
        }
        return;
    }

    async function chargerEtAfficher() {
        const [r1, r2, r3] = await Promise.all([
            appelerApi("/products"),
            appelerApi("/insights"),
            appelerApi("/categories"),
        ]);
        const produits = await lireReponseJson(r1);
        const insights = await lireReponseJson(r2);
        const categories = await lireReponseJson(r3);
        if (!r1.ok || !r2.ok || !r3.ok) throw new Error("Chargement API impossible");
        const liste = produits.sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
        const imgMap = construireCarteImagesRayons(categories);
        R.construireSectionsRayons(conteneur, liste, insights, imgMap);
        remplirPanneauTeleversementFonds(categories, chargerEtAfficher);

        const hash = (window.location.hash || "").replace(/^#/, "").trim();
        if (hash) {
            requestAnimationFrame(() => {
                const el = document.getElementById(hash);
                if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        }
    }

    if (btnToggle && corpsUpload) {
        btnToggle.addEventListener("click", () => {
            const ouvrir = corpsUpload.classList.contains("d-none");
            corpsUpload.classList.toggle("d-none", !ouvrir);
            btnToggle.setAttribute("aria-expanded", ouvrir ? "true" : "false");
        });
    }

    try {
        await chargerEtAfficher();
    } catch (e) {
        if (errEl) {
            errEl.textContent = e.message || String(e);
            errEl.classList.remove("d-none");
        }
        conteneur.innerHTML = "";
    }
});
