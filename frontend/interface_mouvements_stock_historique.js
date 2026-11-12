/**
 * interface_mouvements_stock_historique.js
 * Mouvements : validation côté client (rupture, sortie > stock), bandeau de stock lisible.
 */

function echapperHtml(texte) {
    const d = document.createElement("div");
    d.textContent = texte;
    return d.innerHTML;
}

function libelleNatureSortieMvt(m) {
    if (m.movement_type === "entree") return "—";
    const k = m.sortie_kind || "vente";
    const map = { vente: "Vente", perte: "Perte", autre: "Autre" };
    return map[k] || k;
}

function formaterDetailApi(d) {
    if (!d || d.detail === undefined || d.detail === null) return "Requête refusée.";
    if (typeof d.detail === "string") return d.detail;
    if (Array.isArray(d.detail)) {
        return d.detail
            .map((e) => (typeof e === "object" && e.msg ? e.msg : JSON.stringify(e)))
            .join(" ");
    }
    return String(d.detail);
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    const selProduit = document.getElementById("mvt-product");
    const selFiltre = document.getElementById("filtre-product");
    const tbody = document.querySelector("#table-mouvements tbody");
    const form = document.getElementById("form-mouvement");
    const errEl = document.getElementById("erreur-mouvements");
    const okEl = document.getElementById("message-mouvements");
    const infoEl = document.getElementById("info-stock-mouvement");
    const inpType = document.getElementById("mvt-type");
    const inpQty = document.getElementById("mvt-qty");
    const blocSortieKind = document.getElementById("bloc-mvt-sortie-kind");
    const selSortieKind = document.getElementById("mvt-sortie-kind");
    const blocPrixVente = document.getElementById("bloc-mvt-prix-vente");
    const inpPrixVente = document.getElementById("mvt-prix-vente");
    const inpRecherche = document.getElementById("mvt-recherche-produit");
    const divResultatsRecherche = document.getElementById("mvt-recherche-resultats");
    const btnRechercheTous = document.getElementById("mvt-recherche-tous");
    const msgRechercheHint = document.getElementById("mvt-recherche-vide");
    const tabBtnRecherche = document.getElementById("tab-mvt-recherche");

    let debounceRechercheTimer = null;

    function resetHintRecherche() {
        if (!msgRechercheHint) return;
        msgRechercheHint.classList.remove("d-none", "text-success", "text-danger");
        msgRechercheHint.classList.add("text-muted");
        msgRechercheHint.textContent =
            "Tapez au moins une lettre ou un chiffre pour voir les produits correspondants.";
    }

    function afficherResultatsRecherche() {
        if (!inpRecherche || !divResultatsRecherche || !msgRechercheHint) return;
        const t = inpRecherche.value.trim().toLowerCase();
        divResultatsRecherche.innerHTML = "";
        if (!t) {
            resetHintRecherche();
            msgRechercheHint.classList.remove("d-none");
            return;
        }
        msgRechercheHint.classList.add("d-none");
        const matches = [];
        nomsParId.forEach((name, id) => {
            const ref = String(id);
            if (name.toLowerCase().includes(t) || ref.includes(t)) {
                matches.push({ id, name });
            }
        });
        matches.sort((a, b) =>
            a.name.localeCompare(b.name, "fr", { sensitivity: "base" }),
        );
        const max = 60;
        if (matches.length === 0) {
            msgRechercheHint.classList.remove("d-none", "text-muted", "text-success");
            msgRechercheHint.classList.add("text-danger");
            msgRechercheHint.textContent = "Aucun produit ne correspond à cette recherche.";
            return;
        }
        matches.slice(0, max).forEach(({ id, name }) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "list-group-item list-group-item-action text-start py-2";
            btn.innerHTML = `${echapperHtml(name)} <span class="text-muted">· réf. ${id}</span>`;
            btn.addEventListener("click", () => {
                selFiltre.value = String(id);
                inpRecherche.value = name;
                divResultatsRecherche.innerHTML = "";
                chargerMouvements();
                msgRechercheHint.classList.remove("d-none", "text-muted", "text-danger");
                msgRechercheHint.classList.add("text-success");
                msgRechercheHint.textContent =
                    `Historique affiché pour ce produit. Utilisez l’onglet Liste pour le menu déroulant.`;
            });
            divResultatsRecherche.appendChild(btn);
        });
        if (matches.length > max) {
            const div = document.createElement("div");
            div.className = "list-group-item small text-muted border-0 py-2";
            div.textContent = `… et ${matches.length - max} autre(s) — affinez la recherche.`;
            divResultatsRecherche.appendChild(div);
        }
    }

    function majBlocSortieKind() {
        if (!blocSortieKind) return;
        blocSortieKind.classList.toggle("d-none", inpType.value === "entree");
    }

    function majBlocPrixVente() {
        if (!blocPrixVente || !inpPrixVente) return;
        const vente =
            inpType.value === "sortie" && selSortieKind && selSortieKind.value === "vente";
        blocPrixVente.classList.toggle("d-none", !vente);
        if (!vente) return;
        const pid = Number(selProduit.value);
        const ref = prixParId.get(pid);
        if (!inpPrixVente.dataset.userEdited) {
            inpPrixVente.value =
                ref != null && Number.isFinite(ref) ? ref.toFixed(2) : "";
        }
    }

    let mouvements = [];
    /** @type {Map<number, string>} */
    let nomsParId = new Map();
    /** @type {Map<number, number>} */
    let stockParId = new Map();
    /** @type {Map<number, number>} */
    let minParId = new Map();
    /** @type {Map<number, number | null>} */
    let prixParId = new Map();

    function cacherErreurSucces() {
        errEl.classList.add("d-none");
        okEl.classList.add("d-none");
    }

    function afficherErreur(msg) {
        okEl.classList.add("d-none");
        errEl.textContent = msg;
        errEl.classList.remove("d-none");
    }

    function afficherSucces(msg) {
        errEl.classList.add("d-none");
        okEl.textContent = msg;
        okEl.classList.remove("d-none");
    }

    function blocMessageSeuilReappro(stockActuel, stockApresMouvement) {
        const pid = Number(selProduit.value);
        const raw = minParId.get(pid);
        const m = typeof raw === "number" ? raw : 0;
        if (m <= 0) return "";
        const niveau =
            typeof stockApresMouvement === "number" ? stockApresMouvement : stockActuel;
        if (niveau > m) return "";
        const detail =
            typeof stockApresMouvement === "number" && stockApresMouvement !== stockActuel
                ? `Après cette opération, le stock sera à <strong>${stockApresMouvement}</strong> (votre seuil minimal : <strong>${m}</strong>).`
                : `Stock actuel <strong>${stockActuel}</strong>, seuil minimal fixé : <strong>${m}</strong>.`;
        return `<div class="mt-2 pt-2 border-top border-dark border-opacity-10 small"><strong>Réapprovisionnement :</strong> ${detail} Prévoyez une <strong>commande fournisseur</strong>.</div>`;
    }

    function majBandeauStock() {
        const id = Number(selProduit.value);
        if (!id) {
            infoEl.classList.add("d-none");
            return;
        }
        const stock = stockParId.get(id);
        const stockOk = typeof stock === "number" ? stock : 0;
        const nom = nomsParId.get(id) || "Article";
        const type = inpType.value;
        const qtyRaw = Number(inpQty.value);
        const qty = Number.isFinite(qtyRaw) && qtyRaw > 0 ? Math.floor(qtyRaw) : 0;

        infoEl.classList.remove("d-none", "alert-danger", "alert-warning", "alert-info", "alert-success");

        if (type === "sortie") {
            if (stockOk <= 0) {
                infoEl.classList.add("alert-danger");
                infoEl.innerHTML = `<strong>Rupture.</strong> Le stock de « ${echapperHtml(nom)} » est à <strong>0</strong>. Enregistrez une <strong>entrée</strong> (réception ou achat) avant toute sortie.${blocMessageSeuilReappro(stockOk)}`;
                return;
            }
            if (qty > 0 && qty > stockOk) {
                infoEl.classList.add("alert-warning");
                infoEl.innerHTML = `<strong>Quantité trop élevée.</strong> Stock disponible : <strong>${stockOk}</strong>. Vous demandez <strong>${qty}</strong> en sortie — la sortie sera <strong>refusée</strong> tant que la quantité dépasse le stock.${blocMessageSeuilReappro(stockOk)}`;
                return;
            }
            if (qty > 0 && qty === stockOk) {
                infoEl.classList.add("alert-warning");
                infoEl.innerHTML = `<strong>Attention :</strong> après cette sortie, le stock passera à <strong>0</strong> (rupture). Stock actuel : <strong>${stockOk}</strong>.${blocMessageSeuilReappro(stockOk, 0)}`;
                return;
            }
            infoEl.classList.add("alert-info");
            if (qty > 0) {
                const apres = stockOk - qty;
                infoEl.innerHTML = `Stock disponible : <strong>${stockOk}</strong>. Après cette sortie, il restera <strong>${apres}</strong>.${blocMessageSeuilReappro(stockOk, apres)}`;
            } else {
                infoEl.innerHTML = `Stock disponible : <strong>${stockOk}</strong>.${blocMessageSeuilReappro(stockOk)}`;
            }
            return;
        }

        infoEl.classList.add("alert-info");
        if (qty > 0) {
            const apres = stockOk + qty;
            infoEl.innerHTML = `Stock actuel : <strong>${stockOk}</strong>. Après cette entrée : <strong>${apres}</strong>.${blocMessageSeuilReappro(stockOk, apres)}`;
        } else {
            infoEl.innerHTML = `Stock actuel : <strong>${stockOk}</strong>.${blocMessageSeuilReappro(stockOk)}`;
        }
    }

    function _qtyStockDepuisApi(p) {
        const n = Number(p.quantity_stock);
        return Number.isFinite(n) ? n : 0;
    }

    function _minStockDepuisApi(p) {
        const n = Number(p.min_stock);
        return Number.isFinite(n) ? n : 0;
    }

    async function rafraichirStocks() {
        const r = await appelerApi("/products");
        if (!r.ok) {
            return;
        }
        const liste = await lireReponseJson(r);
        if (!Array.isArray(liste)) {
            return;
        }
        stockParId = new Map(liste.map((p) => [p.id, _qtyStockDepuisApi(p)]));
        minParId = new Map(liste.map((p) => [p.id, _minStockDepuisApi(p)]));
    }

    async function chargerProduitsSelect() {
        const r = await appelerApi("/products");
        const liste = await lireReponseJson(r);
        liste.sort((a, b) => a.name.localeCompare(b.name, "fr", { sensitivity: "base" }));
        nomsParId = new Map(liste.map((p) => [p.id, p.name]));
        stockParId = new Map(liste.map((p) => [p.id, _qtyStockDepuisApi(p)]));
        minParId = new Map(liste.map((p) => [p.id, _minStockDepuisApi(p)]));
        prixParId = new Map(
            liste.map((p) => {
                const x = p.price;
                const n = x != null && x !== "" ? Number(x) : null;
                return [p.id, Number.isFinite(n) ? n : null];
            }),
        );

        const prev = selProduit.value;
        selProduit.innerHTML = "";
        selFiltre.innerHTML = '<option value="">Tous les produits</option>';
        liste.forEach((p) => {
            const o1 = document.createElement("option");
            o1.value = p.id;
            o1.textContent = p.name;
            o1.title = `Réf. inventaire : ${p.id} · stock ${p.quantity_stock} · seuil min ${p.min_stock ?? 0}`;
            selProduit.appendChild(o1);
            const o2 = document.createElement("option");
            o2.value = p.id;
            o2.textContent = p.name;
            o2.title = `Réf. inventaire : ${p.id}`;
            selFiltre.appendChild(o2);
        });
        if (prev && [...selProduit.options].some((o) => o.value === prev)) {
            selProduit.value = prev;
        }
        if (inpRecherche && inpRecherche.value.trim()) {
            afficherResultatsRecherche();
        }
    }

    function libelleProduit(id) {
        const nom = nomsParId.get(Number(id));
        if (nom) return `${echapperHtml(nom)} <span class="text-muted small">· réf. ${id}</span>`;
        return `Article ${id}`;
    }

    async function chargerMouvements() {
        const pid = selFiltre.value;
        const q = pid ? "?product_id=" + encodeURIComponent(pid) : "";
        const r = await appelerApi("/movements" + q);
        mouvements = await lireReponseJson(r);
        tbody.innerHTML = "";
        mouvements.forEach((m) => {
            const pv =
                m.movement_type === "sortie" &&
                (m.sortie_kind || "vente") === "vente" &&
                m.sale_unit_price != null
                    ? Number(m.sale_unit_price).toFixed(2) + " $"
                    : "—";
            const tr = document.createElement("tr");
            tr.innerHTML = `
        <td>${formaterDateHeureApiFrCa(m.created_at)}</td>
        <td>${libelleProduit(m.product_id)}</td>
        <td><span class="badge bg-${m.movement_type === "entree" ? "success" : "secondary"}">${m.movement_type}</span></td>
        <td>${echapperHtml(libelleNatureSortieMvt(m))}</td>
        <td>${m.quantity}</td>
        <td class="text-end font-monospace">${pv}</td>
        <td>${m.note ? echapperHtml(m.note) : "—"}</td>`;
            tbody.appendChild(tr);
        });
        /* Même source que l’API : après tout chargement d’historique, realigner le bandeau
         * (évite stock « figé » alors que des entrées viennent d’être enregistrées). */
        await rafraichirStocks();
        majBandeauStock();
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        cacherErreurSucces();
        const productId = Number(selProduit.value);
        const payload = {
            movement_type: inpType.value,
            quantity: Number(inpQty.value),
            note: document.getElementById("mvt-note").value || null,
        };
        if (payload.movement_type === "sortie" && selSortieKind) {
            payload.sortie_kind = selSortieKind.value;
        }
        if (
            payload.movement_type === "sortie" &&
            selSortieKind &&
            selSortieKind.value === "vente" &&
            inpPrixVente
        ) {
            const raw = inpPrixVente.value.trim().replace(",", ".");
            if (raw !== "") {
                const pv = parseFloat(raw);
                if (Number.isFinite(pv) && pv >= 0) {
                    payload.sale_unit_price = pv;
                }
            }
        }

        if (!Number.isFinite(payload.quantity) || payload.quantity < 1) {
            afficherErreur("Indiquez une quantité d’au moins 1.");
            return;
        }

        const disponible = stockParId.get(productId);
        const stockActuel = typeof disponible === "number" ? disponible : 0;

        if (payload.movement_type === "sortie") {
            if (stockActuel <= 0) {
                afficherErreur(
                    "Impossible d’enregistrer la sortie : le stock de cet article est à 0 (rupture). Enregistrez d’abord une entrée.",
                );
                return;
            }
            if (payload.quantity > stockActuel) {
                afficherErreur(
                    `Impossible d’enregistrer la sortie : vous demandez ${payload.quantity} unité(s), alors que seulement ${stockActuel} sont en stock.`,
                );
                return;
            }
        }

        const r = await appelerApi("/products/" + productId + "/movements", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        if (!r.ok) {
            const d = await lireReponseJson(r);
            let msg = formaterDetailApi(d);
            if (msg.includes("Stock insuffisant")) {
                const nom = nomsParId.get(productId) || "cet article";
                msg = `Stock insuffisant : vous ne pouvez pas sortir plus que la quantité disponible pour « ${nom} ». ${msg}`;
            }
            afficherErreur(msg);
            return;
        }

        document.getElementById("mvt-note").value = "";
        inpQty.value = "1";
        if (inpPrixVente) {
            inpPrixVente.dataset.userEdited = "";
        }

        await rafraichirStocks();
        const apres = stockParId.get(productId) ?? 0;
        let msgOk = "Mouvement enregistré.";
        if (apres === 0) {
            msgOk += " Le stock de cet article est maintenant à 0 (rupture).";
        } else {
            msgOk += ` Stock actuel : ${apres}.`;
        }
        afficherSucces(msgOk);

        await chargerMouvements();
        majBandeauStock();
    });

    selProduit.addEventListener("change", () => {
        cacherErreurSucces();
        if (inpPrixVente) inpPrixVente.dataset.userEdited = "";
        majBlocPrixVente();
        majBandeauStock();
    });
    inpType.addEventListener("change", () => {
        cacherErreurSucces();
        majBlocSortieKind();
        majBlocPrixVente();
        majBandeauStock();
    });
    if (selSortieKind) {
        selSortieKind.addEventListener("change", () => {
            if (selSortieKind.value !== "vente" && inpPrixVente) {
                inpPrixVente.dataset.userEdited = "";
            }
            cacherErreurSucces();
            majBlocPrixVente();
            majBandeauStock();
        });
    }
    if (inpPrixVente) {
        inpPrixVente.addEventListener("input", () => {
            inpPrixVente.dataset.userEdited = inpPrixVente.value.trim() ? "1" : "";
        });
    }
    inpQty.addEventListener("input", () => {
        cacherErreurSucces();
        majBandeauStock();
    });

    selFiltre.addEventListener("change", () => {
        chargerMouvements();
        if (inpRecherche && selFiltre.value) {
            const nom = nomsParId.get(Number(selFiltre.value));
            if (nom) inpRecherche.value = nom;
        } else if (inpRecherche && !selFiltre.value) {
            inpRecherche.value = "";
            resetHintRecherche();
            if (divResultatsRecherche) divResultatsRecherche.innerHTML = "";
        }
    });

    inpRecherche?.addEventListener("input", () => {
        clearTimeout(debounceRechercheTimer);
        debounceRechercheTimer = setTimeout(afficherResultatsRecherche, 200);
    });

    btnRechercheTous?.addEventListener("click", () => {
        selFiltre.value = "";
        if (inpRecherche) inpRecherche.value = "";
        if (divResultatsRecherche) divResultatsRecherche.innerHTML = "";
        resetHintRecherche();
        msgRechercheHint?.classList.remove("d-none");
        chargerMouvements();
    });

    tabBtnRecherche?.addEventListener("shown.bs.tab", () => {
        inpRecherche?.focus();
        afficherResultatsRecherche();
    });

    document.getElementById("btn-print-mouvements")?.addEventListener("click", () => {
        window.print();
    });

    try {
        await chargerProduitsSelect();
        majBlocSortieKind();
        majBlocPrixVente();
        await chargerMouvements();
        majBandeauStock();
    } catch (e) {
        afficherErreur(e.message || String(e));
    }
});
