/**
 * Page Ventes : agrégation /api/reports/ventes (jour | mois | année).
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

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    if (typeof injecterFicheEtablissement === "function") {
        await injecterFicheEtablissement("stockia-fiche-etablissement-ventes");
    }

    const form = document.getElementById("form-ventes");
    const selGroupe = document.getElementById("ventes-groupe");
    const inpDebut = document.getElementById("ventes-debut");
    const inpFin = document.getElementById("ventes-fin");
    const tbody = document.querySelector("#table-ventes tbody");
    const errEl = document.getElementById("erreur-ventes");
    const noteMeta = document.getElementById("ventes-note-meta");
    const kpiLignes = document.getElementById("kpi-ventes-lignes");
    const kpiQte = document.getElementById("kpi-ventes-qte");
    const kpiMontant = document.getElementById("kpi-ventes-montant");

    const fin = new Date();
    const debut = new Date();
    debut.setDate(debut.getDate() - 90);
    inpFin.value = dateIsoLocal(fin);
    inpDebut.value = dateIsoLocal(debut);

    async function charger() {
        errEl.classList.add("d-none");
        const g = selGroupe.value;
        const d0 = inpDebut.value;
        const d1 = inpFin.value;
        let q = `?groupe=${encodeURIComponent(g)}`;
        if (d0) q += `&date_debut=${encodeURIComponent(d0)}`;
        if (d1) q += `&date_fin=${encodeURIComponent(d1)}`;
        q += paramRequeteFuseauCalendrier();

        const r = await appelerApi("/reports/ventes" + q);
        const data = await lireReponseJson(r);
        if (!r.ok) {
            errEl.textContent = typeof data.detail === "string" ? data.detail : "Erreur chargement ventes.";
            errEl.classList.remove("d-none");
            return;
        }

        const meta = data.meta;
        noteMeta.textContent = meta.note || "";

        const rows = (data.rows || []).filter((row) => Number(row.quantite_totale) > 0);
        tbody.innerHTML = "";
        let sumQte = 0;
        let sumMontant = 0;
        let nMontant = 0;

        if (rows.length === 0) {
            const tr = document.createElement("tr");
            tr.innerHTML =
                '<td colspan="8" class="text-muted text-center py-4">Aucune vente sur cette période (aucune sortie « vente » enregistrée).</td>';
            tbody.appendChild(tr);
        } else {
            rows.forEach((row, idx) => {
                sumQte += row.quantite_totale;
                if (row.montant_estime != null) {
                    sumMontant += row.montant_estime;
                    nMontant += 1;
                }
                const tr = document.createElement("tr");
                const prix =
                    row.prix_unitaire_reference != null
                        ? Number(row.prix_unitaire_reference).toFixed(2) + " $"
                        : "—";
                const montant =
                    row.montant_estime != null ? Number(row.montant_estime).toFixed(2) + " $" : "—";
                tr.innerHTML = `
        <td class="font-monospace">${echapperHtml(row.periode)}</td>
        <td class="ventes-col-n font-monospace">${idx + 1}</td>
        <td>${echapperHtml(row.product_name)} <span class="text-muted small">· réf. ${row.product_id}</span></td>
        <td>${row.category_name ? echapperHtml(row.category_name) : "—"}</td>
        <td class="text-end font-monospace">${row.quantite_totale}</td>
        <td class="text-end font-monospace">${row.nb_mouvements}</td>
        <td class="text-end font-monospace">${prix}</td>
        <td class="text-end font-monospace">${montant}</td>`;
                tbody.appendChild(tr);
            });
        }

        kpiLignes.textContent = String(rows.length);
        kpiQte.textContent = String(sumQte);
        kpiMontant.textContent =
            nMontant > 0
                ? sumMontant.toFixed(2) + " $"
                : rows.length > 0
                  ? "— (prix catalogue ou prix vente manquant)"
                  : "—";
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        charger().catch((ex) => {
            errEl.textContent = ex.message || String(ex);
            errEl.classList.remove("d-none");
        });
    });

    try {
        await charger();
    } catch (e) {
        errEl.textContent = e.message || String(e);
        errEl.classList.remove("d-none");
    }
});
