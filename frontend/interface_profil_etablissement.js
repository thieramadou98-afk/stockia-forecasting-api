/**
 * Page Profil établissement : lecture GET /api/auth/me, mise à jour PATCH /api/auth/me.
 */

function profilSetFeedback(idInput, idFb, msg) {
    const inp = document.getElementById(idInput);
    const fb = document.getElementById(idFb);
    if (!inp || !fb) return;
    if (msg) {
        fb.textContent = msg;
        fb.classList.remove("d-none");
        inp.classList.add("is-invalid");
    } else {
        fb.textContent = "";
        fb.classList.add("d-none");
        inp.classList.remove("is-invalid");
    }
}

function champTexteOuNull(el) {
    const v = el.value.trim();
    return v.length ? v : null;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!lireJeton()) {
        window.location.href = "connexion_utilisateur.html";
        return;
    }

    const errEl = document.getElementById("erreur-profil");
    const okEl = document.getElementById("succes-profil");
    const form = document.getElementById("form-profil-etablissement");
    const inpUser = document.getElementById("profil-username");
    const inpOrg = document.getElementById("profil-organization");
    const inpEmail = document.getElementById("profil-email");
    const inpPhone = document.getElementById("profil-phone");
    const inpAddr = document.getElementById("profil-address");

    function montrerErreur(msg) {
        okEl.classList.add("d-none");
        if (!msg) {
            errEl.classList.add("d-none");
            errEl.textContent = "";
            return;
        }
        errEl.textContent = msg;
        errEl.classList.remove("d-none");
    }

    function montrerSucces(msg) {
        errEl.classList.add("d-none");
        okEl.textContent = msg;
        okEl.classList.remove("d-none");
    }

    try {
        const profil = await chargerProfilUtilisateur({ force: true });
        if (!profil) {
            montrerErreur("Impossible de charger le profil ; vérifiez votre session.");
            return;
        }
        inpUser.value = profil.username || "";
        inpOrg.value = profil.organization_name || "";
        inpEmail.value = profil.email || "";
        inpPhone.value = profil.phone || "";
        inpAddr.value = profil.address_line || "";
    } catch {
        montrerErreur("Erreur lors du chargement du profil.");
        return;
    }

    inpEmail.addEventListener("blur", () => {
        const t = inpEmail.value.trim();
        if (!t) {
            profilSetFeedback("profil-email", "profil-feedback-email", "");
            return;
        }
        const err = stockiaMessageErreurCourriel(inpEmail.value);
        profilSetFeedback("profil-email", "profil-feedback-email", err || "");
    });
    inpEmail.addEventListener("input", () => {
        if (!inpEmail.value.trim() || !stockiaMessageErreurCourriel(inpEmail.value)) {
            profilSetFeedback("profil-email", "profil-feedback-email", "");
        }
    });

    inpPhone.addEventListener("blur", () => {
        const t = inpPhone.value.trim();
        if (!t) {
            profilSetFeedback("profil-phone", "profil-feedback-phone", "");
            return;
        }
        const err = stockiaMessageErreurTelephone(inpPhone.value);
        profilSetFeedback("profil-phone", "profil-feedback-phone", err || "");
    });
    inpPhone.addEventListener("input", () => {
        if (!inpPhone.value.trim() || !stockiaMessageErreurTelephone(inpPhone.value)) {
            profilSetFeedback("profil-phone", "profil-feedback-phone", "");
        }
    });

    function validerAvantPatch() {
        let ok = true;
        const org = inpOrg.value.trim();
        const em = inpEmail.value.trim();
        const ph = inpPhone.value.trim();
        const ad = inpAddr.value.trim();

        if (org && org.length < 2) {
            profilSetFeedback("profil-organization", "profil-feedback-org", "Au moins 2 caractères si le champ est renseigné.");
            ok = false;
        } else {
            profilSetFeedback("profil-organization", "profil-feedback-org", "");
        }

        if (em) {
            const errM = stockiaMessageErreurCourriel(inpEmail.value);
            if (errM) {
                profilSetFeedback("profil-email", "profil-feedback-email", errM);
                ok = false;
            } else {
                profilSetFeedback("profil-email", "profil-feedback-email", "");
            }
        } else {
            profilSetFeedback("profil-email", "profil-feedback-email", "");
        }

        if (ph) {
            const errP = stockiaMessageErreurTelephone(inpPhone.value);
            if (errP) {
                profilSetFeedback("profil-phone", "profil-feedback-phone", errP);
                ok = false;
            } else {
                profilSetFeedback("profil-phone", "profil-feedback-phone", "");
            }
        } else {
            profilSetFeedback("profil-phone", "profil-feedback-phone", "");
        }

        if (ad && ad.length < 5) {
            profilSetFeedback("profil-address", "profil-feedback-address", "Au moins 5 caractères si l’adresse est renseignée.");
            ok = false;
        } else {
            profilSetFeedback("profil-address", "profil-feedback-address", "");
        }

        return ok;
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        montrerErreur("");
        okEl.classList.add("d-none");

        if (!validerAvantPatch()) {
            montrerErreur("Veuillez corriger les champs indiqués avant d’enregistrer.");
            return;
        }

        const body = {
            organization_name: champTexteOuNull(inpOrg),
            email: champTexteOuNull(inpEmail),
            phone: champTexteOuNull(inpPhone),
            address_line: champTexteOuNull(inpAddr),
        };

        try {
            const r = await appelerApi("/auth/me", {
                method: "PATCH",
                body: JSON.stringify(body),
            });
            const data = await lireReponseJson(r);
            if (!r.ok) {
                montrerErreur(formaterDetailErreurApi(data));
                return;
            }
            await chargerProfilUtilisateur({ force: true });
            montrerSucces("Vos informations ont été enregistrées.");
        } catch (ex) {
            montrerErreur(ex.message || String(ex));
        }
    });
});
