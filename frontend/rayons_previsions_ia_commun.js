/**
 * Graphiques « prévisions IA » regroupés par catégorie (réutilisé : catalogue + page dédiée).
 * Dépend de : Chart.js, theme_stockia_web.js (comparerNomsRayons, themePourCategorie, …).
 */
(function (global) {
    const graphiquesParRayon = [];

    function echapperHtml(t) {
        const d = document.createElement("div");
        d.textContent = t;
        return d.innerHTML;
    }

    function slugCategorie(nom) {
        const s = (nom || "sans").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        return s.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "").toLowerCase() || "sans";
    }

    function tronquerNom(nom, max = 22) {
        if (!nom || nom.length <= max) return nom;
        return nom.slice(0, max - 1) + "…";
    }

    function fmtU(n) {
        const fn = typeof global.stockiaFmtUnitesIA === "function" ? global.stockiaFmtUnitesIA : null;
        if (fn) return fn(n);
        const x = Number(n);
        return Number.isFinite(x) ? String(Math.round(x)) : "—";
    }

    function fmtConso(n) {
        const fn = typeof global.stockiaFmtConsoJour === "function" ? global.stockiaFmtConsoJour : null;
        if (fn) return fn(n);
        const x = Number(n);
        return Number.isFinite(x) ? String(x) : "—";
    }

    function echapperAttr(t) {
        return echapperHtml(t).replace(/"/g, "&quot;");
    }

    /** Libellé français pour le badge risque (données API : eleve, moyen, faible). */
    function libelleRisqueRupture(code) {
        const m = { eleve: "élevé", moyen: "moyen", faible: "faible" };
        return m[code] || code || "—";
    }

    /**
     * Détail d’une carte article (aligné sur la fiche « Recherche & rayons »).
     * @param {object} p produit (id, name, category_name, quantity_stock, min_stock, …)
     * @param {object} i insight IA
     */
    function htmlCorpsCarteInsight(p, i) {
        const fen = global.STOCKIA_IA_FENETRE_CONSO_JOURS || 14;
        const cov = i.coverage_cycle_days ?? 7;
        const qCmd = Number(i.recommended_order_qty) || 0;
        const badge =
            i.stockout_risk_level === "eleve"
                ? "danger"
                : i.stockout_risk_level === "moyen"
                  ? "warning"
                  : "success";
        const stockSrc = Number.isFinite(Number(p.quantity_stock)) ? Number(p.quantity_stock) : i.quantity_stock;
        const minStock = p.min_stock != null && p.min_stock !== "" ? fmtU(p.min_stock) : "—";
        const nomComplet = echapperAttr(p.name || "");
        const nomCourt = echapperHtml(tronquerNom(p.name, 72));
        const rayon = p.category_name ? echapperHtml(p.category_name) : "—";
        let html = `<div class="fw-semibold small mb-1" title="${nomComplet}">${nomCourt}</div>`;
        html += `<p class="small text-white-50 mb-1">Réf. inventaire : ${echapperHtml(String(p.id))}</p>`;
        html += `<p class="small text-white-50 mb-1">Rayon : ${rayon}</p>`;
        html += `<p class="small mb-1">Stock actuel : <strong>${fmtU(stockSrc)}</strong> (seuil min ${minStock})</p>`;
        html += `<p class="small mb-1">Conso. moy. (<strong>${fen}</strong> j., jours avec sortie) : <strong>${fmtConso(i.avg_daily_out_last_days)}</strong> / jour</p>`;
        html += `<p class="small mb-1">Prévision IA : <strong>${fmtConso(i.predicted_daily_out)}</strong> / jour</p>`;
        html += `<p class="small mb-1">Délai fournisseur : <strong>${fmtU(i.lead_time_days)}</strong> j · point de commande ≈ <strong>${fmtU(i.reorder_point_qty)}</strong> u. · stock sécurité ≈ <strong>${fmtU(i.safety_stock_qty)}</strong> u.</p>`;
        html += `<p class="small mb-1">Risque rupture : <span class="badge bg-${badge}">${echapperHtml(libelleRisqueRupture(i.stockout_risk_level))}</span></p>`;
        if (qCmd === 0) {
            html += `<p class="small text-success mb-0"><strong>Aucune commande suggérée</strong> — stock suffisant (PdC + ${cov} j. de couverture).</p>`;
        } else {
            html += `<p class="small mb-0"><strong>Quantité suggérée (Cmd) :</strong> <strong>${fmtU(qCmd)}</strong> unités <span class="text-white-50">(PdC + ${cov} j. demande estimée)</span></p>`;
        }
        return html;
    }

    function detruireGraphiques() {
        graphiquesParRayon.forEach((c) => c.destroy());
        graphiquesParRayon.length = 0;
    }

    /**
     * @param {HTMLElement} conteneurRayons
     * @param {object[]} produits
     * @param {object[]} insights
     */
    function construireSectionsRayons(conteneurRayons, produits, insights, imagesRayonParNom) {
        detruireGraphiques();
        conteneurRayons.innerHTML = "";

        const mapImages =
            imagesRayonParNom instanceof Map ? imagesRayonParNom : new Map();

        const insightParId = new Map(insights.map((i) => [i.product_id, i]));

        const parCat = new Map();
        for (const p of produits) {
            const cat = p.category_name || "Sans catégorie";
            if (!parCat.has(cat)) parCat.set(cat, []);
            parCat.get(cat).push(p);
        }
        const noms = Array.from(parCat.keys()).sort(comparerNomsRayons);

        for (const catName of noms) {
            const theme = themePourCategorie(catName === "Sans catégorie" ? null : catName);
            const slug = slugCategorie(catName);
            const urlPerso = (mapImages.get(catName) || "").trim();
            const bgUrl =
                typeof globalThis.urlFondPhotoPleinEcranPourRayon === "function"
                    ? globalThis.urlFondPhotoPleinEcranPourRayon(urlPerso, catName)
                    : urlPerso || (theme.image ? imageFondPourCategorie(theme) : "");

            const section = document.createElement("section");
            section.className = "section-rayon-ia mb-5";
            section.id = `section-rayon-${slug}`;
            const bgEsc = bgUrl.replace(/'/g, "%27");
            section.style.setProperty("--rayon-bg-image", `url('${bgEsc}')`);

            const inner = document.createElement("div");
            inner.className = "section-rayon-ia-inner";

            const bandeauTitre = document.createElement("div");
            bandeauTitre.className = "rayon-titre-sur-fond rounded px-3 py-2 mb-3";

            const titre = document.createElement("h2");
            titre.className = "h4 mb-1 text-white text-shadow-rayon";
            titre.textContent = catName;

            const sous = document.createElement("p");
            sous.className = "small text-white-50 mb-0";
            sous.textContent = theme.libelle || "";
            bandeauTitre.appendChild(titre);
            bandeauTitre.appendChild(sous);

            const row = document.createElement("div");
            row.className = "row g-3";
            const colChart = document.createElement("div");
            colChart.className = "col-lg-7";
            const panneauGraph = document.createElement("div");
            panneauGraph.className = "rayon-graphique-panel rounded-3 shadow-sm p-3";
            const canvas = document.createElement("canvas");
            canvas.id = `chart-rayon-${slug}`;
            canvas.height = 120;
            panneauGraph.appendChild(canvas);
            colChart.appendChild(panneauGraph);

            const colCards = document.createElement("div");
            colCards.className = "col-lg-5";
            const liste = parCat.get(catName);
            const insightsCat = liste
                .map((p) => ({ p, i: insightParId.get(p.id) }))
                .filter((x) => x.i);

            insightsCat.forEach(({ p, i }) => {
                const card = document.createElement("div");
                card.className = "card mb-3 bg-dark bg-opacity-75 text-white border-0";
                card.id = `prod-card-${p.id}`;
                card.innerHTML = `<div class="card-body py-2 px-3">${htmlCorpsCarteInsight(p, i)}</div>`;
                colCards.appendChild(card);
            });

            row.appendChild(colChart);
            row.appendChild(colCards);
            inner.appendChild(bandeauTitre);
            inner.appendChild(row);
            section.appendChild(inner);
            conteneurRayons.appendChild(section);

            const labels = insightsCat.map(({ p }) => tronquerNom(p.name, 18));
            const qCmd = insightsCat.map(({ i }) => i.recommended_order_qty);
            const qStock = insightsCat.map(({ i }) => Math.max(0, i.quantity_stock));
            const couleur = hexVersRgba(theme.hex, 0.85);
            const couleur2 = "rgba(55, 71, 79, 0.35)";

            if (labels.length) {
                const chart = new Chart(canvas.getContext("2d"), {
                    type: "bar",
                    data: {
                        labels,
                        datasets: [
                            {
                                label: "Qté suggérée à commander (IA)",
                                data: qCmd,
                                backgroundColor: couleur,
                            },
                            {
                                label: "Stock actuel",
                                data: qStock,
                                backgroundColor: couleur2,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { labels: { color: "#212529", font: { size: 12 } } },
                            title: {
                                display: true,
                                text: "Prévisions & réapprovisionnement",
                                color: "#212529",
                                font: { size: 14, weight: "600" },
                            },
                        },
                        scales: {
                            x: {
                                ticks: { color: "#37474f", maxRotation: 40 },
                                grid: { color: "rgba(0,0,0,0.06)" },
                            },
                            y: {
                                beginAtZero: true,
                                ticks: { color: "#37474f" },
                                grid: { color: "rgba(0,0,0,0.08)" },
                            },
                        },
                    },
                });
                graphiquesParRayon.push(chart);
            } else {
                panneauGraph.innerHTML =
                    '<p class="text-muted small mb-0">Pas assez de données IA pour ce rayon (aucune sortie historique). Enregistrez des sorties dans <strong>Mouvements</strong> pour alimenter les prévisions.</p>';
            }
        }
    }

    global.StockIARayonsPrevisions = {
        slugCategorie,
        tronquerNom,
        echapperHtml,
        detruireGraphiques,
        construireSectionsRayons,
    };
})(typeof window !== "undefined" ? window : globalThis);
