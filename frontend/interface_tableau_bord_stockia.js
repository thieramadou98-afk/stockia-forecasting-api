/**
 * interface_tableau_bord_stockia.js
 * Tableau de bord : graphique avec barres depuis 0 vers le haut (stocks négatifs plafonnés à l’affichage).
 */

let graphiqueStocks = null;

function libelleNatureMouvement(m) {
    if (m.movement_type === "entree") return "—";
    const k = m.sortie_kind || "vente";
    const map = { vente: "Vente", perte: "Perte", autre: "Autre" };
    return map[k] || k;
}

function echapperHtml(texte) {
    const d = document.createElement("div");
    d.textContent = texte;
    return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    const zoneErreur = document.getElementById("erreur-dashboard");

    async function chargerJson(chemin) {
        const r = await appelerApi(chemin);
        const data = await lireReponseJson(r);
        if (!r.ok) {
            const detail = data && data.detail ? data.detail : JSON.stringify(data);
            throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        return data;
    }

    try {
        const [ov, insights, produitsListe, wiz] = await Promise.all([
            chargerJson("/dashboard/overview"),
            chargerJson("/insights"),
            chargerJson("/products"),
            chargerJson("/dashboard/widgets?jours=30"),
        ]);
        const nomParId = new Map(produitsListe.map((p) => [p.id, p.name]));

        document.getElementById("kpi-produits").textContent = ov.total_products;
        document.getElementById("kpi-alertes").textContent = ov.alerts_below_min;

        const nbRuptures = produitsListe.filter((p) => Number(p.quantity_stock) === 0).length;
        document.getElementById("kpi-ruptures").textContent = nbRuptures;

        const rayons = new Set(
            produitsListe.map((p) => p.category_name).filter((n) => n && String(n).trim()),
        );
        document.getElementById("kpi-rayons").textContent = rayons.size;

        function produitReapproDashboard(p) {
            const m = Number(p.min_stock);
            const q = Number(p.quantity_stock);
            return Number.isFinite(m) && m > 0 && Number.isFinite(q) && q <= m;
        }

        function ligneProduitDetailKpi(p) {
            const cat = p.category_name ? echapperHtml(p.category_name) : "—";
            const sku = p.sku ? echapperHtml(p.sku) : "—";
            const del = p.lead_time_days != null ? p.lead_time_days : 7;
            return `<tr>
<td class="font-monospace">${p.id}</td>
<td>${echapperHtml(p.name)}</td>
<td>${cat}</td>
<td class="text-end">${Number(p.quantity_stock)}</td>
<td class="text-end">${Number(p.min_stock)}</td>
<td class="text-end">${del}</td>
<td class="small">${sku}</td>
</tr>`;
        }

        function ouvrirDetailKpi(mode) {
            const panneau = document.getElementById("panneau-detail-kpi");
            const titreEl = document.getElementById("panneau-detail-kpi-titre");
            const table = document.getElementById("table-detail-kpi");
            const thead = table?.querySelector("thead");
            const tbody = table?.querySelector("tbody");
            if (!panneau || !titreEl || !thead || !tbody) return;

            document.querySelectorAll(".kpi-tile-btn").forEach((b) => {
                b.classList.toggle("active", b.getAttribute("data-kpi-detail") === mode);
            });

            panneau.classList.remove("d-none");

            const triNom = (a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" });

            if (mode === "catalogue") {
                titreEl.textContent = `Articles au catalogue (${produitsListe.length})`;
                thead.innerHTML =
                    '<tr><th>Réf.</th><th>Nom</th><th>Rayon</th><th class="text-end">Stock</th><th class="text-end">Min</th><th class="text-end">Délai (j)</th><th>SKU</th></tr>';
                const rows = [...produitsListe].sort(triNom);
                tbody.innerHTML =
                    rows.map(ligneProduitDetailKpi).join("") ||
                    '<tr><td colspan="7" class="text-muted p-3">Aucun article.</td></tr>';
            } else if (mode === "reappro") {
                const rows = produitsListe.filter(produitReapproDashboard).sort(triNom);
                titreEl.textContent = `Réapprovisionnement — seuil atteint ou dépassé (${rows.length})`;
                thead.innerHTML =
                    '<tr><th>Réf.</th><th>Nom</th><th>Rayon</th><th class="text-end">Stock</th><th class="text-end">Seuil min</th><th class="text-end">Délai (j)</th><th>SKU</th></tr>';
                tbody.innerHTML =
                    rows.map(ligneProduitDetailKpi).join("") ||
                    '<tr><td colspan="7" class="text-muted p-3">Aucun article dans ce cas.</td></tr>';
            } else if (mode === "rupture") {
                const rows = produitsListe.filter((p) => Number(p.quantity_stock) === 0).sort(triNom);
                titreEl.textContent = `Stock = 0 (${rows.length} article(s))`;
                thead.innerHTML =
                    '<tr><th>Réf.</th><th>Nom</th><th>Rayon</th><th class="text-end">Stock</th><th class="text-end">Min</th><th class="text-end">Délai (j)</th><th>SKU</th></tr>';
                tbody.innerHTML =
                    rows.map(ligneProduitDetailKpi).join("") ||
                    '<tr><td colspan="7" class="text-muted p-3">Aucun article avec stock exactement à 0.</td></tr>';
            } else if (mode === "rayons") {
                const compte = new Map();
                for (const p of produitsListe) {
                    const k = p.category_name || "Sans catégorie";
                    compte.set(k, (compte.get(k) || 0) + 1);
                }
                const noms = Array.from(compte.keys()).sort(comparerNomsRayons);
                titreEl.textContent = `Rayons — ${noms.length} catégorie(s)`;
                thead.innerHTML = '<tr><th>Rayon</th><th class="text-end">Nombre d’articles</th></tr>';
                tbody.innerHTML =
                    noms
                        .map(
                            (nom) =>
                                `<tr><td>${echapperHtml(nom)}</td><td class="text-end">${compte.get(nom)}</td></tr>`,
                        )
                        .join("") || '<tr><td colspan="2" class="text-muted p-3">Aucun rayon.</td></tr>';
            }

            panneau.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        function fermerDetailKpi() {
            document.getElementById("panneau-detail-kpi")?.classList.add("d-none");
            document.querySelectorAll(".kpi-tile-btn").forEach((b) => b.classList.remove("active"));
        }

        document.querySelectorAll(".kpi-tile-btn").forEach((btn) => {
            btn.addEventListener("click", () => ouvrirDetailKpi(btn.getAttribute("data-kpi-detail")));
        });
        document.getElementById("btn-fermer-detail-kpi")?.addEventListener("click", fermerDetailKpi);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") fermerDetailKpi();
        });

        const horo = document.getElementById("dashboard-horodatage");
        if (horo) {
            horo.textContent = new Date().toLocaleString("fr-CA", {
                dateStyle: "medium",
                timeStyle: "short",
            });
        }

        const libPeriode = document.getElementById("widgets-periode-libelle");
        if (libPeriode) {
            libPeriode.textContent = `${wiz.periode_jours} derniers jours`;
        }
        const ulTop = document.getElementById("liste-top-sorties");
        if (ulTop) {
            ulTop.innerHTML = "";
            if (!wiz.top_sorties || !wiz.top_sorties.length) {
                ulTop.innerHTML =
                    '<li class="list-group-item text-muted small">Aucune sortie sur cette période.</li>';
            } else {
                wiz.top_sorties.forEach((row) => {
                    const li = document.createElement("li");
                    li.className =
                        "list-group-item d-flex justify-content-between align-items-center small";
                    li.innerHTML = `<span>${echapperHtml(row.product_name)}</span><span class="badge bg-dark">${row.total_sortie} sorties</span>`;
                    ulTop.appendChild(li);
                });
            }
        }
        const ulRec = document.getElementById("liste-recents-catalogue");
        if (ulRec) {
            ulRec.innerHTML = "";
            (wiz.recents_catalogue || []).forEach((row) => {
                const li = document.createElement("li");
                li.className =
                    "list-group-item d-flex justify-content-between align-items-center small";
                const cat = row.category_name ? echapperHtml(row.category_name) : "—";
                li.innerHTML = `<div><div class="fw-medium">${echapperHtml(row.name)}</div><div class="text-muted" style="font-size:0.78rem">${cat}</div></div><span class="text-nowrap ms-2">stock <strong>${row.quantity_stock}</strong></span>`;
                ulRec.appendChild(li);
            });
        }

        const tbody = document.querySelector("#tableau-mouvements tbody");
        tbody.innerHTML = "";
        ov.recent_movements.forEach((m) => {
            const nom = nomParId.get(m.product_id);
            const libelle = nom
                ? `${echapperHtml(nom)} <span class="text-muted small">· réf. ${m.product_id}</span>`
                : `Article ${m.product_id}`;
            const tr = document.createElement("tr");
            tr.innerHTML = `
        <td>${formaterDateHeureApiFrCa(m.created_at)}</td>
        <td>${libelle}</td>
        <td>${m.movement_type}</td>
        <td>${echapperHtml(libelleNatureMouvement(m))}</td>
        <td>${m.quantity}</td>
        <td>${m.note ? echapperHtml(m.note) : "—"}</td>`;
            tbody.appendChild(tr);
        });

        const fu = window.stockiaFmtUnitesIA || ((n) => String(Math.round(Number(n) || 0)));
        const fc = window.stockiaFmtConsoJour || ((n) => String(n));
        const fj = window.stockiaFmtJoursRupture || ((n) => (n == null || n === "" ? "—" : String(n)));
        const fen = window.STOCKIA_IA_FENETRE_CONSO_JOURS || 14;

        const divInsights = document.getElementById("cartes-ia");
        divInsights.innerHTML = "";
        insights.forEach((i) => {
            const badge =
                i.stockout_risk_level === "eleve"
                    ? "danger"
                    : i.stockout_risk_level === "moyen"
                      ? "warning"
                      : "success";
            const qCmd = Number(i.recommended_order_qty) || 0;
            const cov = i.coverage_cycle_days ?? 7;
            const blocSugg =
                qCmd === 0
                    ? `<p class="small mb-0 text-success"><strong>Aucune commande suggérée</strong> — le stock couvre le point de commande et environ <strong>${cov}</strong> j. de demande estimée.</p>`
                    : `<p class="text-muted small mb-0">Suggestion commande : <strong>${fu(qCmd)}</strong> unités<span class="d-block mt-1">(point de commande + ${cov} j. de demande estimée)</span></p>`;
            const col = document.createElement("div");
            col.className = "col-md-6 col-lg-4";
            col.innerHTML = `
        <div class="card h-100 border-${badge} border-2">
          <div class="card-body">
            <h5 class="card-title">${echapperHtml(i.product_name)}</h5>
            <p class="mb-1">Stock : <strong>${fu(i.quantity_stock)}</strong> (min ${fu(i.min_stock)}) · délai fourn. <strong>${fu(i.lead_time_days)}</strong> j</p>
            <p class="mb-1">Conso. moy. (fenêtre <strong>${fen}</strong> j.) : <strong>${fc(i.avg_daily_out_last_days)}</strong> / jour <span class="text-muted small">(jours avec sortie)</span></p>
            <p class="mb-1">Prévision IA : <strong>${fc(i.predicted_daily_out)}</strong> / jour</p>
            <p class="mb-1">Point de commande : <strong>${fu(i.reorder_point_qty)}</strong> u. · stock sécurité ≈ <strong>${fu(i.safety_stock_qty)}</strong> u.</p>
            <p class="mb-1">Rupture estimée : <strong>${fj(i.days_until_stockout_estimate)}</strong> j</p>
            <p class="mb-2">Risque : <span class="badge bg-${badge}">${i.stockout_risk_level}</span></p>
            ${blocSugg}
          </div>
        </div>`;
            divInsights.appendChild(col);
        });

        const summary = await chargerJson("/dashboard/summary");
        const ctx = document.getElementById("graphique-stocks");
        const wrap = document.getElementById("wrap-graphique-stocks");
        const labels = summary.map((s) => s.name);
        const stocksReels = summary.map((s) => s.quantity_stock);
        const stocksAffiche = stocksReels.map((q) => Math.max(0, q));
        const mins = summary.map((s) => s.min_stock);

        const couleursBarres = summary.map((s, i) => {
            const q = stocksReels[i];
            if (q <= 0) return "rgba(220, 53, 69, 0.85)";
            if (s.min_stock > 0 && q <= s.min_stock) return "rgba(255, 193, 7, 0.85)";
            return hexVersRgba(themePourCategorie(s.category_name).hex, 0.72);
        });

        const n = labels.length;
        const chartHeight = Math.max(360, Math.min(3400, n * 28 + 140));
        if (wrap) wrap.style.height = `${chartHeight}px`;

        if (graphiqueStocks) {
            graphiqueStocks.destroy();
        }
        graphiqueStocks = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Quantité en stock",
                        data: stocksAffiche,
                        backgroundColor: couleursBarres,
                        borderColor: "rgba(0,0,0,0.06)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#212529",
                            font: { size: 13 },
                            boxWidth: 14,
                        },
                    },
                    tooltip: {
                        titleFont: { size: 14, weight: "600" },
                        bodyFont: { size: 13 },
                        callbacks: {
                            title(items) {
                                const i = items[0].dataIndex;
                                return labels[i];
                            },
                            label(ctx) {
                                const i = ctx.dataIndex;
                                const reel = stocksReels[i];
                                const lines = [
                                    `Stock affiché : ${stocksAffiche[i]}${reel < 0 ? ` (réel en base : ${reel})` : ""}`,
                                    `Seuil minimal : ${mins[i]}`,
                                ];
                                if (reel <= 0) lines.push("Rupture : stock à 0 ou négatif.");
                                else if (mins[i] > 0 && reel <= mins[i]) {
                                    lines.push("Au seuil minimal ou en dessous — penser réapprovisionnement.");
                                }
                                return lines;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            color: "#263238",
                            font: { size: 12, weight: "500" },
                        },
                        grid: { color: "rgba(0,0,0,0.08)" },
                        title: {
                            display: true,
                            text: "Unités",
                            color: "#37474f",
                            font: { size: 13, weight: "600" },
                        },
                    },
                    y: {
                        ticks: {
                            color: "#212529",
                            font: { size: 12, weight: "500" },
                            autoSkip: false,
                            padding: 8,
                        },
                        grid: { display: false },
                    },
                },
            },
        });
    } catch (e) {
        zoneErreur.textContent = "Impossible de charger le tableau de bord : " + e.message;
        zoneErreur.classList.remove("d-none");
    }

});
