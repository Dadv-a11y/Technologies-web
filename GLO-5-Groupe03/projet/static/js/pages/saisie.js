// saisie.js : saisie des notes, refus immédiat d'une note fausse et moyenne de la classe en direct.
// Le serveur revérifie chaque note : ces contrôles ne servent qu'au confort de l'enseignant.

const formSaisie = document.querySelector("#form-saisie");
if (formSaisie) {
  const champs = formSaisie.querySelectorAll(".champ-note");
  const erreur = document.querySelector("#erreur");
  const cellMoyenne = document.querySelector("#moyenne-direct");
  const resume = document.querySelector("#resume-saisie");

  // Renvoie la note (nombre) si le champ est valide, null si vide, NaN si refusée.
  function lireNote(champ) {
    const texte = champ.value.trim().replace(",", ".");
    if (texte === "") return null;
    const valeur = Number(texte);
    const deuxDecimales = Math.abs(valeur * 100 - Math.round(valeur * 100)) < 1e-6;
    if (Number.isNaN(valeur) || valeur < 0 || valeur > 20 || !deuxDecimales) return NaN;
    return valeur;
  }

  function mettreAJour() {
    const valeurs = [];
    let refusees = 0;
    let modifiees = 0;
    for (const champ of champs) {
      const note = lireNote(champ);
      const refusee = Number.isNaN(note);
      // Une note qui diffère de celle enregistrée est surlignée : nouvelle note ou correction.
      const changee = !refusee && note !== null &&
        (champ.dataset.ancienne === "" || Number(champ.dataset.ancienne) !== note);
      champ.classList.toggle("invalide", refusee);
      champ.classList.toggle("modifiee", changee);
      if (refusee) refusees++;
      if (changee) modifiees++;
      if (!refusee && note !== null) valeurs.push(note);
    }
    if (valeurs.length > 0) {
      const somme = valeurs.reduce((total, v) => total + v, 0);
      cellMoyenne.textContent = (somme / valeurs.length).toFixed(2).replace(".", ",") + " / 20 (" + valeurs.length + " notes)";
    } else {
      cellMoyenne.textContent = "—";
    }
    erreur.textContent = refusees > 0
      ? refusees + " note(s) refusée(s) : une note est comprise entre 0 et 20, avec deux décimales au maximum."
      : "";
    resume.textContent = modifiees + " note(s) à enregistrer.";
    return refusees === 0;
  }

  for (const champ of champs) champ.addEventListener("input", mettreAJour);
  formSaisie.addEventListener("submit", (evenement) => {
    if (!mettreAJour()) evenement.preventDefault();
  });
  mettreAJour();
}
