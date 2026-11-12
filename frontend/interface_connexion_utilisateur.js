/**
 * interface_connexion_utilisateur.js
 * Connexion OAuth2 « password » (RFC 6749) ; inscription REST JSON sur /api/auth/register.
 * Validation du formulaire d’inscription côté client (courriel au blur et à la validation, sans pop-up native du navigateur).
 */

/** Bouton œil : bascule entre saisie masquée et visible (connexion + inscription). */
function brancherAffichageMotDePasse() {
    document.querySelectorAll("[data-stockia-toggle-password]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = btn.getAttribute("data-stockia-toggle-password");
            const input = document.getElementById(id);
            if (!input) return;
            input.type = input.type === "password" ? "text" : "password";
            const masked = input.type === "password";
            btn.setAttribute("aria-pressed", masked ? "false" : "true");
            btn.setAttribute("aria-label", masked ? "Afficher le mot de passe" : "Masquer le mot de passe");
            btn.title = masked ? "Afficher le mot de passe" : "Masquer le mot de passe";
            const openI = btn.querySelector(".stockia-icon-eye-open");
            const offI = btn.querySelector(".stockia-icon-eye-off");
            if (openI && offI) {
                openI.classList.toggle("d-none", !masked);
                offI.classList.toggle("d-none", masked);
            }
        });
    });
}

function setChampErreur(idInput, idFeedback, message) {
    const inp = document.getElementById(idInput);
    const fb = document.getElementById(idFeedback);
    if (!inp || !fb) return;
    if (message) {
        fb.textContent = message;
        fb.classList.remove("d-none");
        inp.classList.add("is-invalid");
    } else {
        fb.textContent = "";
        fb.classList.add("d-none");
        inp.classList.remove("is-invalid");
    }
}

function validerInscriptionAfficherTout() {
    const org = document.getElementById("reg-organization").value.trim();
    const email = document.getElementById("reg-email").value;
    const phone = document.getElementById("reg-phone").value;
    const addr = document.getElementById("reg-address").value.trim();
    const username = document.getElementById("reg-username").value.trim();
    const password = document.getElementById("reg-password").value;
    const password2 = document.getElementById("reg-password2").value;

    let ok = true;

    if (org.length < 2) {
        setChampErreur("reg-organization", "reg-feedback-organization", "Indiquez au moins 2 caractères pour l’entreprise ou le magasin.");
        ok = false;
    } else {
        setChampErreur("reg-organization", "reg-feedback-organization", "");
    }

    const errMail = stockiaMessageErreurCourriel(email);
    if (errMail) {
        setChampErreur("reg-email", "reg-feedback-email", errMail);
        ok = false;
    } else {
        setChampErreur("reg-email", "reg-feedback-email", "");
    }

    const errTel = stockiaMessageErreurTelephone(phone);
    if (errTel) {
        setChampErreur("reg-phone", "reg-feedback-phone", errTel);
        ok = false;
    } else {
        setChampErreur("reg-phone", "reg-feedback-phone", "");
    }

    if (addr.length < 5) {
        setChampErreur("reg-address", "reg-feedback-address", "L’adresse postale doit contenir au moins 5 caractères.");
        ok = false;
    } else {
        setChampErreur("reg-address", "reg-feedback-address", "");
    }

    if (username.length < 3) {
        setChampErreur("reg-username", "reg-feedback-username", "L’identifiant de connexion doit contenir au moins 3 caractères.");
        ok = false;
    } else {
        setChampErreur("reg-username", "reg-feedback-username", "");
    }

    if (password.length < 6) {
        setChampErreur("reg-password", "reg-feedback-password", "Le mot de passe doit contenir au moins 6 caractères.");
        ok = false;
    } else {
        setChampErreur("reg-password", "reg-feedback-password", "");
    }

    if (password !== password2) {
        setChampErreur("reg-password2", "reg-feedback-password2", "Les deux mots de passe ne correspondent pas.");
        ok = false;
    } else {
        setChampErreur("reg-password2", "reg-feedback-password2", "");
    }

    return ok;
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("form-connexion");
    const formReg = document.getElementById("form-inscription");
    const msg = document.getElementById("message-connexion");
    const msgReg = document.getElementById("message-inscription");
    const inpEmail = document.getElementById("reg-email");
    const inpPhone = document.getElementById("reg-phone");

    if (lireJeton()) {
        window.location.href = "index.html";
        return;
    }

    brancherAffichageMotDePasse();

    inpEmail.addEventListener("blur", () => {
        const err = stockiaMessageErreurCourriel(inpEmail.value);
        if (err) {
            setChampErreur("reg-email", "reg-feedback-email", err);
        } else {
            setChampErreur("reg-email", "reg-feedback-email", "");
        }
    });

    inpEmail.addEventListener("input", () => {
        if (!stockiaMessageErreurCourriel(inpEmail.value)) {
            setChampErreur("reg-email", "reg-feedback-email", "");
        }
    });

    inpPhone.addEventListener("blur", () => {
        const err = stockiaMessageErreurTelephone(inpPhone.value);
        if (err) {
            setChampErreur("reg-phone", "reg-feedback-phone", err);
        } else {
            setChampErreur("reg-phone", "reg-feedback-phone", "");
        }
    });

    inpPhone.addEventListener("input", () => {
        if (!stockiaMessageErreurTelephone(inpPhone.value)) {
            setChampErreur("reg-phone", "reg-feedback-phone", "");
        }
    });

    /** Après inscription réussie : même flux que la connexion (OAuth2 password). */
    async function connecterAvecIdentifiants(username, password) {
        const corps = new URLSearchParams();
        corps.append("username", username);
        corps.append("password", password);
        const reponse = await fetch("/api/auth/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: corps.toString(),
        });
        const data = await reponse.json().catch(() => ({}));
        if (!reponse.ok) {
            throw new Error(
                data.detail ||
                    "Connexion impossible pour le moment. Utilisez « Se connecter » avec le même identifiant et mot de passe."
            );
        }
        enregistrerJeton(data.access_token);
        window.location.href = "index.html";
    }

    formReg.addEventListener("submit", async (e) => {
        e.preventDefault();
        msgReg.textContent = "";
        msgReg.className = "small";

        if (!validerInscriptionAfficherTout()) {
            msgReg.textContent = "Veuillez corriger les champs indiqués ci-dessus avant d’envoyer le formulaire.";
            msgReg.className = "small text-danger";
            return;
        }

        const username = document.getElementById("reg-username").value.trim();
        const password = document.getElementById("reg-password").value;
        const organization_name = document.getElementById("reg-organization").value.trim();
        const email = document.getElementById("reg-email").value.trim();
        const phone = document.getElementById("reg-phone").value.trim();
        const address_line = document.getElementById("reg-address").value.trim();

        try {
            const reponse = await fetch("/api/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username,
                    password,
                    organization_name,
                    email,
                    phone,
                    address_line,
                }),
            });
            const data = await reponse.json().catch(() => ({}));
            if (!reponse.ok) {
                msgReg.textContent = formaterDetailErreurApi(data);
                msgReg.className = "small text-danger";
                return;
            }
            msgReg.textContent = "Compte créé. Connexion en cours…";
            msgReg.className = "small text-success";
            await connecterAvecIdentifiants(username, password);
        } catch (err) {
            msgReg.textContent = err.message || String(err);
            msgReg.className = "small text-danger";
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        msg.textContent = "";
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        const corps = new URLSearchParams();
        corps.append("username", username);
        corps.append("password", password);

        try {
            const reponse = await fetch("/api/auth/token", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: corps.toString(),
            });
            const data = await reponse.json().catch(() => ({}));
            if (!reponse.ok) {
                msg.textContent =
                    typeof data.detail === "string"
                        ? data.detail
                        : "Identifiant ou mot de passe incorrect.";
                msg.className = "text-danger";
                return;
            }
            enregistrerJeton(data.access_token);
            window.location.href = "index.html";
        } catch (err) {
            msg.textContent = "Erreur réseau ou timeout : " + err.message;
            msg.className = "text-danger";
        }
    });
});
