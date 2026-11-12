/**
 * Page Rapport / inventaire : filtres (tout / rayon / article), fiche + mouvements, impression PDF navigateur.
 */

function echapperHtml(t) {
    const d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
}

function dateIsoLocal(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function libelleNatureSortie(m) {
    if (m.movement_type === "entree") return "—";
    const k = m.sortie_kind || "vente";
    const map = { vente: "Vente", perte: "Perte", autre: "Autre" };
    return map[k] || k;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    if (typeof injecterFicheEtablissement === "function") {
        await injecterFicheEtablissement("stockia-fiche-etablissement-rapport");
    }

    const err = document.getElementById("erreur-rapport");
    function montrerErreur(msg) {
        if (!msg) {
            err.textContent = "";
            err.classList.add("d-none");
            return;
        }
        err.textContent = msg;
        err.classList.remove("d-none");
    }

    const selPortee = document.getElementById("rapport-portee");
    const blocCat = document.getElementById("bloc-rapport-categorie");
    const blocArt = document.getElementById("bloc-rapport-article");
    const selCategory = document.getElementById("rapport-category");
    const selProduct = document.getElementById("rapport-product");
    const tbodyInv = document.querySelector("#table-inventaire-periode tbody");
    const tbodyMvt = document.querySelector("#table-mouvements-periode tbody");
    const titrePeriode = document.getElementById("titre-periode-rapport");
    const textePeriodeBar = document.getElementById("texte-periode-entree-sortie");
    const titrePeriodeMouvements = document.getElementById("titre-periode-mouvements");
    const inpDebut = document.getElementById("rapport-date-debut");
    const inpFin = document.getElementById("rapport-date-fin");

    function formaterPlageDatesRapport(d0, d1) {
        return `${d0} - ${d1}`;
    }

    function dateMouvementCourte(iso) {
        const d = parseApiDateTimeUtcNaive(iso);
        return Number.isNaN(d.getTime()) ? "—" : dateIsoLocal(d);
    }

    const fin = new Date();
    const debut = new Date();
    debut.setDate(debut.getDate() - 30);
    inpDebut.value = dateIsoLocal(debut);
    inpFin.value = dateIsoLocal(fin);

    function majVisibiliteFiltres() {
        const p = selPortee.value;
        blocCat.classList.toggle("d-none", p !== "categorie");
        blocArt.classList.toggle("d-none", p !== "article");
    }

    selPortee.addEventListener("change", majVisibiliteFiltres);

    document.getElementById("btn-imprimer-rapport").addEventListener("click", () => {
        window.print();
    });

    async function chargerCategoriesRapport() {
        const r = await appelerApi("/categories");
        const liste = await lireReponseJson(r);
        liste.sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
        selCategory.innerHTML = '<option value="">Toutes les catégories</option>';
        liste.forEach((c) => {
            const o = document.createElement("option");
            o.value = c.id;
            o.textContent = c.name;
            selCategory.appendChild(o);
        });
    }

    async function chargerProduitsRapport() {
        const r = await appelerApi("/products");
        const liste = await lireReponseJson(r);
        liste.sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
        selProduct.innerHTML = '<option value="">Tous les articles</option>';
        liste.forEach((p) => {
            const o = document.createElement("option");
            o.value = p.id;
            o.textContent = p.name;
            selProduct.appendChild(o);
        });
    }

    function construireQuery(d0, d1) {
        let q = `?date_debut=${encodeURIComponent(d0)}&date_fin=${encodeURIComponent(d1)}${paramRequeteFuseauCalendrier()}`;
        const portee = selPortee.value;
        if (portee === "article") {
            const pid = selProduct.value;
            if (pid) q += "&product_id=" + encodeURIComponent(pid);
        } else if (portee === "categorie") {
            const cid = selCategory.value;
            if (cid) q += "&category_id=" + encodeURIComponent(cid);
        }
        return q;
    }

    async function afficherRapport() {
        montrerErreur("");
        const d0 = inpDebut.value;
        const d1 = inpFin.value;
        if (!d0 || !d1) {
            montrerErreur("Choisissez les deux dates.");
            return;
        }
        const q = construireQuery(d0, d1);

        const [r1, r2] = await Promise.all([
            appelerApi("/reports/inventory-period" + q),
            appelerApi("/reports/movements-period" + q),
        ]);
        const inv = await lireReponseJson(r1);
        const mvt = await lireReponseJson(r2);

        if (!r1.ok) {
            montrerErreur(typeof inv.detail === "string" ? inv.detail : "Erreur inventaire.");
            return;
        }
        if (!r2.ok) {
            montrerErreur(typeof mvt.detail === "string" ? mvt.detail : "Erreur mouvements.");
            return;
        }

        const rProd = await appelerApi("/products");
        const allProducts = await lireReponseJson(rProd);
        const noms = new Map(allProducts.map((p) => [p.id, p.name]));

        const meta = inv.meta;
        const dDeb = String(meta.date_debut);
        const dFin = String(meta.date_fin);
        const plage = formaterPlageDatesRapport(dDeb, dFin);
        titrePeriode.textContent = plage;
        if (textePeriodeBar) {
            textePeriodeBar.innerHTML = `<span>${echapperHtml(dDeb)}</span><span>${echapperHtml(dFin)}</span>`;
        }
        if (titrePeriodeMouvements) titrePeriodeMouvements.textContent = plage;

        tbodyInv.innerHTML = "";
        if (!inv.rows.length) {
            tbodyInv.innerHTML =
                '<tr><td colspan="11" class="text-muted text-center py-2">Aucun article pour cette portée et ces dates.</td></tr>';
        } else {
            inv.rows.forEach((row, idx) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
        <td class="text-center font-monospace rapport-col-num rapport-col-n">${idx + 1}</td>
        <td>${echapperHtml(row.name)}</td>
        <td>${row.category_name ? echapperHtml(row.category_name) : "—"}</td>
        <td class="text-end font-monospace rapport-col-num rapport-col-court">${row.stock_debut}</td>
        <td class="text-end font-monospace text-success rapport-col-num rapport-col-court">${row.entrees_periode}</td>
        <td class="text-end font-monospace text-danger rapport-col-num rapport-col-court">${row.sorties_vente}</td>
        <td class="text-end font-monospace text-warning rapport-col-num rapport-col-court">${row.sorties_perte}</td>
        <td class="text-end font-monospace text-secondary rapport-col-num rapport-col-court">${row.sorties_autre}</td>
        <td class="text-end font-monospace fw-semibold rapport-col-num rapport-col-court">${row.stock_fin_theorique}</td>
        <td class="text-end font-monospace rapport-col-num rapport-col-court">${row.min_stock}</td>
        <td class="rapport-cell-manuscrit" aria-label="Zone de note manuscrite"></td>`;
                tbodyInv.appendChild(tr);
            });
        }

        tbodyMvt.innerHTML = "";
        if (!mvt.length) {
            tbodyMvt.innerHTML =
                '<tr><td colspan="8" class="text-muted text-center py-2">Aucun mouvement sur cette période.</td></tr>';
        } else {
            mvt.forEach((m, idx) => {
                const nom = noms.get(m.product_id) || `#${m.product_id}`;
                const typeLisible = m.movement_type === "entree" ? "entrée" : "sortie";
                const tr = document.createElement("tr");
                tr.innerHTML = `
          <td class="font-monospace rapport-col-mvt-date">${echapperHtml(dateMouvementCourte(m.created_at))}</td>
          <td class="text-center font-monospace rapport-col-num rapport-col-n">${idx + 1}</td>
          <td>${echapperHtml(nom)}</td>
          <td><span class="badge bg-${m.movement_type === "entree" ? "success" : "secondary"}">${echapperHtml(typeLisible)}</span></td>
          <td class="rapport-col-nat">${echapperHtml(libelleNatureSortie(m))}</td>
          <td class="text-end font-monospace rapport-col-num rapport-col-court">${m.quantity}</td>
          <td class="rapport-col-mvt-note small">${m.note ? echapperHtml(m.note) : "—"}</td>
          <td class="rapport-cell-manuscrit" aria-label="Zone de note manuscrite"></td>`;
                tbodyMvt.appendChild(tr);
            });
        }
    }

    document.getElementById("form-rapport-filtres").addEventListener("submit", (e) => {
        e.preventDefault();
        afficherRapport().catch((e2) => {
            montrerErreur(e2.message || String(e2));
        });
    });

    try {
        majVisibiliteFiltres();
        await chargerCategoriesRapport();
        await chargerProduitsRapport();
        await afficherRapport();
    } catch (e) {
        montrerErreur(e.message || String(e));
    }
});
