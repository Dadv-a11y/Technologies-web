// main.js : code commun à toutes les pages du portail de notes.
// Le code propre à une page est dans js/pages/ (chargé après ce fichier).

// ---------- Menu "hamburger" ----------
const boutonMenu = document.querySelector("#bouton-menu");
const menu = document.querySelector("#menu-principal");
if (boutonMenu && menu) {
  boutonMenu.addEventListener("click", () => {
    const ouvert = menu.classList.toggle("ouvert");
    boutonMenu.setAttribute("aria-expanded", ouvert);
  });
}

// ---------- Outils partagés par les pages avec graphique (Chart.js) ----------
const COULEURS = { bleu: "#1B3A6B", or: "#E0A526", vert: "#1F8A5B", gris: "#8A94A6", rouge: "#B3261E" };

// Télécharge du JSON avec fetch ; renvoie null en cas de problème (le tableau HTML reste lisible).
async function chargerJson(url) {
  try {
    const reponse = await fetch(url);
    if (!reponse.ok) throw new Error("Erreur " + reponse.status);
    return await reponse.json();
  } catch (e) {
    console.error(e);
    return null;
  }
}

// Affiche un message au-dessus du graphique quand l'API n'a pas répondu.
function afficherEchecGraphique(canvas) {
  const message = document.createElement("p");
  message.className = "message erreur";
  message.textContent = "Le graphique est momentanément indisponible. Les valeurs figurent dans le tableau.";
  canvas.closest("figure").prepend(message);
}
