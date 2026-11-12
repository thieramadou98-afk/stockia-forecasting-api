/**
 * interface_gestion_produits_inventaire.js
 * Liste les produits par rayon (catégorie), thème StockIA.web + formulaire CRUD.
 */

function echapperHtml(texte) {
    const d = document.createElement("div");
    d.textContent = texte;
    return d.innerHTML;
}

function celluleSku(p) {
    if (!p.sku) return "—";
    const s = echapperHtml(p.sku);
    const ru = typeof p.reference_url === "string" ? p.reference_url.trim() : "";
    const hrefOk = /^https?:\/\//i.test(ru);
    return hrefOk
        ? `<a href="${ru.replace(/"/g, "%22")}" target="_blank" rel="noopener noreferrer">${s}</a>`
        : s;
}

/** Seuil &gt; 0 et stock au niveau du seuil ou en dessous → penser réapprovisionnement. */
function produitAlerteSeuilReappro(p) {
    const m = Number(p.min_stock);
    const q = Number(p.quantity_stock);
    return Number.isFinite(m) && m > 0 && Number.isFinite(q) && q <= m;
}

function ligneProduitHtml(p) {
    const prix =
        p.price != null && p.price !== undefined ? Number(p.price).toFixed(2) + " $" : "—";
    const alerte = produitAlerteSeuilReappro(p);
    const cellStock = alerte
        ? `<td class="fw-semibold"><span class="badge bg-warning text-dark me-1 align-middle">Réappro.</span>${p.quantity_stock}</td>`
        : `<td>${p.quantity_stock}</td>`;
    const cellMin = alerte
        ? `<td class="fw-semibold text-danger">${p.min_stock}</td>`
        : `<td>${p.min_stock}</td>`;
    return `
          <td>${p.id}</td>
          <td>${echapperHtml(p.name)}</td>
          <td>${p.brand ? echapperHtml(p.brand) : "—"}</td>
          <td>${celluleSku(p)}</td>
          <td>${p.unit ? echapperHtml(p.unit) : "—"}</td>
          <td>${prix}</td>
          ${cellStock}
          <td>${p.lead_time_days != null ? p.lead_time_days : 7}</td>
          ${cellMin}
          <td>
            <button type="button" class="btn btn-sm btn-outline-primary btn-editer" data-id="${p.id}">Modifier</button>
            <button type="button" class="btn btn-sm btn-outline-danger btn-supprimer" data-id="${p.id}">Supprimer</button>
          </td>`;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    const selCat = document.getElementById("filtre-categorie");
    const catalogue = document.getElementById("catalogue-rayons");
    const form = document.getElementById("form-produit");
    const err = document.getElementById("erreur-produits");
    let categories = [];
    let produits = [];

    const paramsKpi = new URLSearchParams(window.location.search);
    const kpiParam = paramsKpi.get("kpi");
    const kpiVue =
        kpiParam === "reappro" || kpiParam === "rupture" || kpiParam === "rayons" ? kpiParam : null;
    const filtrageKpi = kpiVue === "reappro" || kpiVue === "rupture" ? kpiVue : null;

    function majBandeauVueKpi(listeLength) {
        const el = document.getElementById("bandeau-vue-kpi");
        if (!el) return;
        if (!kpiVue) {
            el.classList.add("d-none");
            el.innerHTML = "";
            return;
        }
        el.classList.remove("d-none");
        const lienRetour =
            '<a href="gestion_produits_inventaire.html" class="alert-link">Afficher tout le catalogue</a>';
        if (kpiVue === "rayons") {
            const n = categories.length;
            el.innerHTML = `<div class="alert alert-secondary border-0 shadow-sm mb-0 py-2">
<strong>Vue rayons</strong> — Onglet <strong>catégories</strong> ouvert : ${n} rayon(s) listé(s) ci-dessous. ${lienRetour} pour revenir au formulaire produit par défaut.</div>`;
            return;
        }
        if (kpiVue === "reappro") {
            el.innerHTML = `<div class="alert alert-warning border-0 shadow-sm mb-0 py-2">
<strong>Vue réapprovisionnement</strong> (tableau de bord) — <strong>${listeLength}</strong> article(s) au seuil minimal ou en dessous, selon le filtre rayon ci-dessus. ${lienRetour}.</div>`;
            return;
        }
        if (kpiVue === "rupture") {
            el.innerHTML = `<div class="alert border-0 shadow-sm mb-0 py-2 text-white" style="background:linear-gradient(135deg,#c62828,#b71c1c)">
<strong>Stock = 0</strong> — <strong>${listeLength}</strong> article(s) avec stock <strong>exactement à 0</strong> (filtre rayon appliqué). <a href="gestion_produits_inventaire.html" class="text-white fw-semibold text-decoration-underline">Tout le catalogue</a>.</div>`;
            return;
        }
    }

    function ouvrirOngletRayonsSiDemande() {
        if (kpiVue !== "rayons") return;
        const tabEl = document.getElementById("tab-ajout-categorie");
        if (tabEl && typeof bootstrap !== "undefined" && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(tabEl).show();
        }
        requestAnimationFrame(() => {
            document.getElementById("liste-categories-gestion")?.scrollIntoView({
                behavior: "smooth",
                block: "nearest",
            });
        });
    }

    catalogue.addEventListener("click", (e) => {
        const ed = e.target.closest(".btn-editer");
        if (ed) remplirFormEdition(Number(ed.dataset.id));
        const su = e.target.closest(".btn-supprimer");
        if (su) supprimerProduit(Number(su.dataset.id));
    });

    function majListeCategoriesSuppression() {
        const ul = document.getElementById("liste-categories-gestion");
        if (!ul) return;
        ul.innerHTML = "";
        if (!categories.length) {
            const li = document.createElement("li");
            li.className = "list-group-item text-muted";
            li.textContent = "Aucune catégorie pour l’instant.";
            ul.appendChild(li);
            return;
        }
        categories.forEach((c) => {
            const li = document.createElement("li");
            li.className =
                "list-group-item d-flex justify-content-between align-items-center gap-2 flex-wrap py-2";
            const span = document.createElement("span");
            span.className = "d-flex align-items-center gap-2";
            if (c.image_url) {
                const im = document.createElement("img");
                im.src = c.image_url;
                im.alt = "";
                im.width = 36;
                im.height = 36;
                im.className = "rounded border bg-white flex-shrink-0";
                im.style.objectFit = "cover";
                span.appendChild(im);
            }
            const lab = document.createElement("span");
            lab.textContent = c.name;
            span.appendChild(lab);
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-sm btn-outline-danger btn-supprimer-categorie";
            btn.dataset.id = String(c.id);
            btn.textContent = "Supprimer";
            li.appendChild(span);
            li.appendChild(btn);
            ul.appendChild(li);
        });
    }

    async function chargerCategories() {
        const r = await appelerApi("/categories");
        categories = await lireReponseJson(r);
        selCat.innerHTML = '<option value="">Toutes les catégories de produits</option>';
        categories.forEach((c) => {
            const o = document.createElement("option");
            o.value = c.id;
            o.textContent = c.name;
            selCat.appendChild(o);
        });
        const selFormCat = document.getElementById("produit-category");
        selFormCat.innerHTML = '<option value="">(aucune)</option>';
        categories.forEach((c) => {
            const o = document.createElement("option");
            o.value = c.id;
            o.textContent = c.name;
            selFormCat.appendChild(o);
        });
        majListeCategoriesSuppression();
    }

    async function chargerProduits() {
        const r = await appelerApi("/products");
        produits = await lireReponseJson(r);
        afficherCatalogue();
    }

    function afficherCatalogue() {
        const filtre = selCat.value;
        let liste = produits.filter((p) => !filtre || String(p.category_id) === filtre);
        if (filtrageKpi === "reappro") {
            liste = liste.filter(produitAlerteSeuilReappro);
        } else if (filtrageKpi === "rupture") {
            liste = liste.filter((p) => Number(p.quantity_stock) === 0);
        }
        majBandeauVueKpi(liste.length);
        catalogue.innerHTML = "";

        const bandeau = document.getElementById("bandeau-alertes-reappro");
        if (bandeau && filtrageKpi !== "reappro") {
            if (liste.length === 0) {
                bandeau.innerHTML = "";
                bandeau.classList.add("d-none");
            } else {
                const alertes = liste.filter(produitAlerteSeuilReappro);
                if (alertes.length === 0) {
                    bandeau.innerHTML = "";
                    bandeau.classList.add("d-none");
                } else {
                    bandeau.classList.remove("d-none");
                    const extra = alertes.length > 10 ? alertes.length - 10 : 0;
                    const noms = alertes
                        .slice(0, 10)
                        .map((p) => echapperHtml(p.name))
                        .join(" · ");
                    bandeau.innerHTML = `<div class="alert alert-warning mb-0 shadow-sm border border-warning">
<strong>Réapprovisionnement :</strong> ${alertes.length} article(s) au <strong>seuil minimal fixé</strong> (stock égal au minimum ou en dessous) — prévoyez une <strong>commande</strong>.
<span class="d-block small mt-2 mb-0">${noms}${extra ? ` <span class="text-muted">(+${extra} autre(s))</span>` : ""}</span>
</div>`;
                }
            }
        }

        if (liste.length === 0) {
            catalogue.innerHTML = '<p class="text-muted">Aucun produit pour ce filtre.</p>';
            return;
        }

        const byCat = new Map();
        for (const p of liste) {
            const k = p.category_name || "Sans catégorie";
            if (!byCat.has(k)) byCat.set(k, []);
            byCat.get(k).push(p);
        }
        const nomsRayons = Array.from(byCat.keys()).sort(comparerNomsRayons);

        for (const catName of nomsRayons) {
            const theme = themePourCategorie(catName === "Sans catégorie" ? null : catName);
            const catObj =
                catName !== "Sans catégorie" ? categories.find((x) => x.name === catName) : null;
            const urlPerso = catObj && catObj.image_url ? String(catObj.image_url).trim() : "";
            const bgUrl =
                typeof globalThis.urlFondPhotoPleinEcranPourRayon === "function"
                    ? globalThis.urlFondPhotoPleinEcranPourRayon(urlPerso, catName)
                    : urlPerso || (theme.image ? imageFondPourCategorie(theme) : "");

            const section = document.createElement("section");
            section.className = "section-rayon-ia mb-4 section-rayon-catalogue-produits";
            section.style.setProperty("--rayon-accent", theme.hex);
            const bgEsc = bgUrl.replace(/'/g, "%27");
            section.style.setProperty("--rayon-bg-image", `url('${bgEsc}')`);

            const inner = document.createElement("div");
            inner.className = "section-rayon-ia-inner";

            const header = document.createElement("div");
            header.className = "rayon-titre-sur-fond rounded px-3 py-2 mb-3 d-flex flex-wrap align-items-center gap-3";
            const titresHtml = `
                <div class="flex-grow-1">
                <h2 class="h5 mb-1 text-white text-shadow-rayon">${echapperHtml(catName)}</h2>
                <p class="small text-white-50 mb-0">${echapperHtml(theme.libelle || "")}</p>
                </div>`;
            header.innerHTML = titresHtml;
            /* Même visuel que le fond du rayon (photo Unsplash / téléversement), pas l’icône SVG seule. */
            if (bgUrl) {
                const im = document.createElement("img");
                im.src = bgUrl;
                im.alt = "";
                im.className = "vignette-fond-rayon-produit flex-shrink-0";
                im.referrerPolicy = "no-referrer";
                im.loading = "lazy";
                header.insertBefore(im, header.firstChild);
            }
            inner.appendChild(header);

            const body = document.createElement("div");
            body.className = "tableau-rayon-sur-fond table-responsive";
            const table = document.createElement("table");
            table.className = "table table-striped table-sm mb-0";
            table.innerHTML =
                "<thead><tr><th>ID</th><th>Nom</th><th>Marque</th><th>SKU</th><th>Unité</th><th>Prix</th><th>Stock</th><th>Délai (j)</th><th>Min</th><th></th></tr></thead>";
            const tb = document.createElement("tbody");
            byCat.get(catName).forEach((p) => {
                const tr = document.createElement("tr");
                if (produitAlerteSeuilReappro(p)) {
                    tr.classList.add("table-warning");
                }
                tr.innerHTML = ligneProduitHtml(p);
                tb.appendChild(tr);
            });
            table.appendChild(tb);
            body.appendChild(table);
            inner.appendChild(body);
            section.appendChild(inner);
            catalogue.appendChild(section);
        }
    }

    function remplirFormEdition(id) {
        const p = produits.find((x) => x.id === id);
        if (!p) return;
        document.getElementById("produit-id").value = p.id;
        document.getElementById("produit-nom").value = p.name;
        document.getElementById("produit-min").value = p.min_stock;
        const elLead = document.getElementById("produit-lead");
        if (elLead) elLead.value = p.lead_time_days != null ? p.lead_time_days : 7;
        document.getElementById("produit-desc").value = p.description || "";
        document.getElementById("produit-category").value = p.category_id || "";
        document.getElementById("produit-unite").value = p.unit || "";
        document.getElementById("produit-prix").value =
            p.price != null && p.price !== undefined ? p.price : "";
        document.getElementById("produit-marque").value = p.brand || "";
        document.getElementById("produit-sku").value = p.sku || "";
        document.getElementById("produit-url").value = p.reference_url || "";
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    async function supprimerProduit(id) {
        if (!confirm("Supprimer ce produit et son historique de mouvements ?")) return;
        const r = await appelerApi("/products/" + id, { method: "DELETE" });
        if (!r.ok) {
            err.textContent = "Suppression refusée";
            return;
        }
        await chargerProduits();
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        err.className = "text-danger small mb-2";
        err.textContent = "";
        const id = document.getElementById("produit-id").value;
        const prixRaw = document.getElementById("produit-prix").value.trim();
        const urlRaw = document.getElementById("produit-url").value.trim();
        const payload = {
            name: document.getElementById("produit-nom").value.trim(),
            min_stock: Number(document.getElementById("produit-min").value),
            lead_time_days: Number(document.getElementById("produit-lead")?.value || 7),
            description: document.getElementById("produit-desc").value || null,
            category_id: document.getElementById("produit-category").value
                ? Number(document.getElementById("produit-category").value)
                : null,
            unit: document.getElementById("produit-unite").value.trim() || null,
            price: prixRaw === "" ? null : Number(prixRaw),
            brand: document.getElementById("produit-marque").value.trim() || null,
            sku: document.getElementById("produit-sku").value.trim() || null,
            reference_url: urlRaw === "" ? null : urlRaw,
        };
        let r;
        if (id) {
            r = await appelerApi("/products/" + id, {
                method: "PATCH",
                body: JSON.stringify(payload),
            });
        } else {
            r = await appelerApi("/products", { method: "POST", body: JSON.stringify(payload) });
        }
        if (!r.ok) {
            const d = await lireReponseJson(r);
            err.textContent = d.detail || "Erreur";
            return;
        }
        form.reset();
        document.getElementById("produit-id").value = "";
        await chargerProduits();
    });

    document.getElementById("btn-nouveau").addEventListener("click", () => {
        form.reset();
        document.getElementById("produit-id").value = "";
    });

    selCat.addEventListener("change", afficherCatalogue);

    document.getElementById("liste-categories-gestion")?.addEventListener("click", async (e) => {
        const btn = e.target.closest(".btn-supprimer-categorie");
        if (!btn) return;
        const id = Number(btn.dataset.id);
        const cat = categories.find((x) => x.id === id);
        const nom = cat ? cat.name : "ce rayon";
        if (
            !confirm(
                `Supprimer le rayon « ${nom} » ? Tous les articles de ce rayon et leur historique de mouvements seront définitivement supprimés.`,
            )
        ) {
            return;
        }
        const msgCat = document.getElementById("message-categorie");
        if (msgCat) {
            msgCat.textContent = "";
            msgCat.className = "small mt-2";
        }
        const r = await appelerApi("/categories/" + id, { method: "DELETE" });
        if (r.status === 204) {
            if (msgCat) {
                msgCat.classList.add("text-success");
                msgCat.textContent = `Rayon « ${nom} » supprimé.`;
            }
            await chargerCategories();
            await chargerProduits();
            return;
        }
        const d = await lireReponseJson(r);
        const detail =
            typeof d?.detail === "string"
                ? d.detail
                : "Impossible de supprimer ce rayon (erreur serveur).";
        if (msgCat) {
            msgCat.classList.add("text-danger");
            msgCat.textContent = detail;
        }
    });

    document.getElementById("form-categorie")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const msgCat = document.getElementById("message-categorie");
        const inputNom = document.getElementById("categorie-nom");
        msgCat.textContent = "";
        msgCat.className = "small mt-2";
        const nom = inputNom.value.trim();
        if (!nom) return;
        const r = await appelerApi("/categories", {
            method: "POST",
            body: JSON.stringify({ name: nom }),
        });
        const d = await lireReponseJson(r);
        if (!r.ok) {
            msgCat.classList.add("text-danger");
            msgCat.textContent = typeof d.detail === "string" ? d.detail : "Impossible de créer la catégorie.";
            return;
        }
        msgCat.classList.add("text-success");
        msgCat.textContent = `Catégorie « ${d.name} » créée. Vous pouvez l’assigner aux produits.`;
        inputNom.value = "";
        await chargerCategories();
        await chargerProduits();
    });

    try {
        await chargerCategories();
        await chargerProduits();
        ouvrirOngletRayonsSiDemande();
    } catch (e) {
        err.textContent = e.message;
    }
});
