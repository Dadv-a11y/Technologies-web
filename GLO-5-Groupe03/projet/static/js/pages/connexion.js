// connexion.js : vérification des formulaires de connexion (élève et enseignant).
// Le serveur revérifie tout : ces contrôles ne servent qu'à éviter un aller-retour inutile.

function verifierFormulaire(formulaire, regles) {
  formulaire.addEventListener("submit", (evenement) => {
    const messages = [];
    for (const regle of regles) {
      const champ = formulaire.elements[regle.champ];
      const valide = regle.test(champ.value.trim());
      champ.classList.toggle("invalide", !valide);
      if (!valide) messages.push(regle.message);
    }
    if (messages.length > 0) {
      evenement.preventDefault();                       // on bloque l'envoi
      afficherToast(messages.join(" "), "erreur", { cle: "formulaire" });
    }
  });
}

const formEleve = document.querySelector("#form-eleve");
if (formEleve) {
  verifierFormulaire(formEleve, [
    { champ: "matricule", test: (v) => /^\d{10}$/.test(v), message: "Le matricule comporte 10 chiffres." },
    { champ: "code", test: (v) => /^\d{6}$/.test(v), message: "Le code d'accès comporte 6 chiffres." },
  ]);
}

const formEnseignant = document.querySelector("#form-enseignant");
if (formEnseignant) {
  verifierFormulaire(formEnseignant, [
    { champ: "login", test: (v) => v !== "", message: "Indiquez votre login." },
    { champ: "mot_de_passe", test: (v) => v !== "", message: "Indiquez votre mot de passe." },
  ]);
}
