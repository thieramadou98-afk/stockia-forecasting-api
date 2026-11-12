/**
 * Page Recherche & rayons : recherche produit + fiche (aperçu IA par article).
 */

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

    const inputSearch = document.getElementById("input-recherche-produit");
    const datalist = document.getElementById("datalist-produits");
    const listeDefil = document.getElementById("liste-produits-defilante");
    const ficheBox = document.getElementById("fiche-produit-selectionne");
    const ficheCorps = document.getElementById("fiche-produit-corps");

    let produits = [];
    let insightParId = new Map();

    async function chargerDonnees() {
        const [r1, r2] = await Promise.all([appelerApi("/products"), appelerApi("/insights")]);
        const d1 = await lireReponseJson(r1);
        const d2 = await lireReponseJson(r2);
        if (!r1.ok || !r2.ok) throw new Error("Chargement API impossible");
        produits = d1.sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
        insightParId = new Map(d2.map((i) => [i.product_id, i]));
    }

    function remplirRechercheEtListe() {
        datalist.innerHTML = "";
        produits.forEach((p) => {
            const o = document.createElement("option");
            o.value = p.name;
            o.label = `${p.name} (réf. ${p.id})`;
            datalist.appendChild(o);
        });
        rendreListeFiltree("");
    }

    function rendreListeFiltree(filtre) {
        const f = (filtre || "").trim().toLowerCase();
        listeDefil.innerHTML = "";
        produits.forEach((p) => {
            const match =
                !f ||
                p.name.toLowerCase().includes(f) ||
                String(p.id).includes(f) ||
                (p.sku && String(p.sku).toLowerCase().includes(f));
            if (!match) return;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "list-group-item list-group-item-action py-2 text-start";
            btn.innerHTML = `${echapperHtml(p.name)} <span class="text-muted small">${p.category_name ? "· " + echapperHtml(p.category_name) : ""} · réf. ${p.id}</span>`;
            btn.addEventListener("click", () => afficherFicheProduit(p));
            listeDefil.appendChild(btn);
        });
        if (!listeDefil.children.length) {
            listeDefil.innerHTML = '<p class="text-muted small p-3 mb-0">Aucun produit ne correspond.</p>';
        }
    }

    function afficherFicheProduit(p) {
        const i = insightParId.get(p.id);
        ficheBox.classList.remove("d-none");
        inputSearch.value = p.name;
        let html = `<p class="mb-1"><strong>${echapperHtml(p.name)}</strong></p>`;
        html += `<p class="small text-muted mb-1">Réf. inventaire : ${p.id}</p>`;
        html += `<p class="small mb-1">Rayon : ${p.category_name ? echapperHtml(p.category_name) : "—"}</p>`;
        html += `<p class="small mb-1">Stock actuel : <strong>${p.quantity_stock}</strong> (seuil min ${p.min_stock})</p>`;
        if (i) {
            const fu = window.stockiaFmtUnitesIA || ((n) => String(Math.round(Number(n) || 0)));
            const fc = window.stockiaFmtConsoJour || ((n) => String(n));
            const fen = window.STOCKIA_IA_FENETRE_CONSO_JOURS || 14;
            const cov = i.coverage_cycle_days ?? 7;
            const qCmd = Number(i.recommended_order_qty) || 0;
            const badge =
                i.stockout_risk_level === "eleve"
                    ? "danger"
                    : i.stockout_risk_level === "moyen"
                      ? "warning"
                      : "success";
            html += `<p class="small mb-1">Conso. moy. (<strong>${fen}</strong> j., jours avec sortie) : <strong>${fc(i.avg_daily_out_last_days)}</strong> / jour</p>`;
            html += `<p class="small mb-1">Prévision IA : <strong>${fc(i.predicted_daily_out)}</strong> / jour</p>`;
            html += `<p class="small mb-1">Délai fournisseur : <strong>${fu(i.lead_time_days)}</strong> j · point de commande ≈ <strong>${fu(i.reorder_point_qty)}</strong> u. · stock sécurité ≈ <strong>${fu(i.safety_stock_qty)}</strong> u.</p>`;
            html += `<p class="small mb-1">Risque rupture : <span class="badge bg-${badge}">${i.stockout_risk_level}</span></p>`;
            if (qCmd === 0) {
                html += `<p class="mb-2 small text-success"><strong>Aucune commande suggérée</strong> — stock suffisant (PdC + ${cov} j. de couverture).</p>`;
            } else {
                html += `<p class="mb-2"><strong>Quantité suggérée :</strong> <strong>${fu(qCmd)}</strong> unités <span class="text-muted small">(PdC + ${cov} j. demande estimée)</span></p>`;
            }
        } else {
            html += `<p class="small text-muted mb-0">Pas encore d’indicateur IA pour ce produit.</p>`;
        }
        ficheCorps.innerHTML = html;
    }

    inputSearch.addEventListener("input", () => rendreListeFiltree(inputSearch.value));
    inputSearch.addEventListener("change", () => {
        const v = inputSearch.value.trim();
        const m = v.match(/^#(\d+)/);
        if (m) {
            const p = produits.find((x) => x.id === Number(m[1]));
            if (p) afficherFicheProduit(p);
            return;
        }
        const exact = produits.find((x) => x.name === v);
        if (exact) afficherFicheProduit(exact);
    });

    try {
        await chargerDonnees();
        remplirRechercheEtListe();
    } catch (e) {
        listeDefil.innerHTML = `<div class="alert alert-danger m-2">${echapperHtml(e.message)}</div>`;
    }
});
