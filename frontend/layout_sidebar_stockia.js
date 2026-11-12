/**
 * Barre latérale commune StockIA.web (navigation inventaire, ventes, prévisions).
 * Déconnexion en bas de la barre. Chaque page définit window.STOCKIA_PAGE avant ce script.
 */
(function () {
    const LIENS = [
        { page: "dashboard", href: "index.html", label: "Tableau de bord" },
        { page: "produits", href: "gestion_produits_inventaire.html", label: "Produits" },
        { page: "mouvements", href: "mouvements_stock_historique.html", label: "Mouvements" },
        { page: "rayons", href: "catalogue_previsions_rayons.html", label: "Recherche & rayons" },
        { separator: true },
        {
            page: "previsions-categories",
            href: "previsions_ia_categories.html",
            label: "Prévisions IA par catégorie",
        },
        { page: "ventes", href: "ventes.html", label: "Ventes" },
        { separator: true },
        { page: "rapport", href: "rapport_inventaire.html", label: "Rapport / inventaire" },
        { page: "profil", href: "profil_etablissement.html", label: "Profil établissement" },
        { page: "aide", href: "aide_stockia.html", label: "Aide" },
    ];

    function deconnecter() {
        if (typeof enregistrerJeton === "function") {
            enregistrerJeton(null);
        } else {
            try {
                localStorage.removeItem("stockia_jwt");
            } catch {
                /* ignore */
            }
        }
        window.location.href = "connexion_utilisateur.html";
    }

    function init() {
        const root = document.getElementById("stockia-sidebar-root");
        if (!root) return;

        const active = typeof window.STOCKIA_PAGE === "string" ? window.STOCKIA_PAGE : "dashboard";

        const nav = document.createElement("nav");
        nav.className = "stockia-sidebar-inner";
        nav.setAttribute("aria-label", "Navigation principale");

        const brand = document.createElement("div");
        brand.className = "stockia-sidebar-brand";
        brand.innerHTML =
            '<a href="index.html" class="stockia-sidebar-brand-link"><span class="stockia-sidebar-logo">StockIA</span><span class="stockia-sidebar-dot">.web</span></a><div class="stockia-sidebar-tagline">Matériaux de construction · Inventaire &amp; prévisions</div>';
        nav.appendChild(brand);

        const ul = document.createElement("ul");
        ul.className = "stockia-sidebar-menu list-unstyled mb-0";
        LIENS.forEach((item) => {
            if (item.separator) {
                const liSep = document.createElement("li");
                liSep.className = "stockia-sidebar-sep px-2 my-2";
                liSep.setAttribute("role", "presentation");
                const hr = document.createElement("hr");
                hr.className = "stockia-sidebar-hr";
                liSep.appendChild(hr);
                ul.appendChild(liSep);
                return;
            }
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = item.href;
            a.textContent = item.label;
            a.className = "stockia-sidebar-link";
            if (item.page === active) {
                a.classList.add("active");
                a.setAttribute("aria-current", "page");
            }
            li.appendChild(a);
            ul.appendChild(li);
        });
        nav.appendChild(ul);

        const spacer = document.createElement("div");
        spacer.className = "stockia-sidebar-spacer";
        spacer.setAttribute("aria-hidden", "true");
        nav.appendChild(spacer);

        const foot = document.createElement("div");
        foot.className = "stockia-sidebar-footer";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = "btn-deconnexion";
        btn.className = "btn btn-warning btn-sm w-100 fw-semibold";
        btn.textContent = "Déconnexion";
        btn.addEventListener("click", deconnecter);
        foot.appendChild(btn);
        nav.appendChild(foot);

        root.appendChild(nav);
    }

    function preparerTopbarsPourOrganisation() {
        document.querySelectorAll(".stockia-main > header.stockia-topbar").forEach((bar) => {
            if (bar.dataset.stockiaTopbarLay) return;
            bar.dataset.stockiaTopbarLay = "1";
            const title = bar.querySelector(":scope > .stockia-topbar-title");
            if (!title) return;
            const right = document.createElement("div");
            right.className = "ms-auto d-flex align-items-center gap-2 flex-wrap stockia-topbar-right";
            const orgSlot = document.createElement("div");
            orgSlot.className = "stockia-topbar-org text-end flex-shrink-0";
            right.appendChild(orgSlot);
            const toMove = [];
            for (const child of [...bar.children]) {
                if (child !== title) {
                    toMove.push(child);
                }
            }
            toMove.forEach((el) => right.appendChild(el));
            bar.appendChild(right);
        });
    }

    async function injecterOrganisationTopbars() {
        preparerTopbarsPourOrganisation();
        if (typeof lireJeton !== "function" || !lireJeton()) return;
        if (typeof chargerProfilUtilisateur !== "function") return;
        const slots = document.querySelectorAll(".stockia-topbar-org");
        slots.forEach((s) => {
            s.textContent = "";
            const ph = document.createElement("span");
            ph.className = "small text-muted";
            ph.textContent = "Chargement du profil…";
            s.appendChild(ph);
        });
        const profil = await chargerProfilUtilisateur();
        slots.forEach((s) => {
            s.textContent = "";
            if (!profil) return;
            const nom = libelleAffichageEtablissement(profil);
            const ligne = document.createElement("div");
            ligne.className = "stockia-org-nom-ligne fw-semibold small text-body text-end";
            ligne.title =
                nom === "Magasin / entreprise (non renseigné)"
                    ? "Complétez la page Profil établissement avec le nom de votre magasin."
                    : nom;
            ligne.textContent = nom;
            s.appendChild(ligne);
        });
    }

    function apresInit() {
        injecterOrganisationTopbars().catch(() => {});
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            init();
            apresInit();
        });
    } else {
        init();
        apresInit();
    }
})();
