/**
 * Formatage cohérent pour l’affichage IA (aligné sur service_previsions_stock_ia : fenêtre 14 j).
 */
(function (global) {
    const FENETRE_CONSO_JOURS = 14;

    function fmtUnites(n) {
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return Math.round(x).toLocaleString("fr-CA");
    }

    function fmtConsoJour(n) {
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return x.toLocaleString("fr-CA", { maximumFractionDigits: 2, minimumFractionDigits: 0 });
    }

    function fmtJoursRupture(n) {
        if (n == null || n === "") return "—";
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return x.toLocaleString("fr-CA", { maximumFractionDigits: 1, minimumFractionDigits: 0 });
    }

    global.STOCKIA_IA_FENETRE_CONSO_JOURS = FENETRE_CONSO_JOURS;
    global.stockiaFmtUnitesIA = fmtUnites;
    global.stockiaFmtConsoJour = fmtConsoJour;
    global.stockiaFmtJoursRupture = fmtJoursRupture;
})(typeof window !== "undefined" ? window : globalThis);
