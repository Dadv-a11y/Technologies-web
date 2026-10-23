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

// ---------- Toasts : messages affichés en bas de l'écran ----------
const zoneToasts = document.querySelector("#toasts");

function fermerToast(toast) {
  toast.remove();
}

// Ajoute le bouton de fermeture et, si duree > 0, la disparition automatique (en millisecondes).
function preparerToast(toast, duree) {
  const bouton = document.createElement("button");
  bouton.type = "button";
  bouton.className = "toast-fermer";
  bouton.setAttribute("aria-label", "Fermer le message");
  bouton.textContent = "×";
  bouton.addEventListener("click", () => fermerToast(toast));
  toast.append(bouton);
  if (duree > 0) setTimeout(() => fermerToast(toast), duree);
}

// type : "erreur", "succes" ou "info". Avec options.cle, un nouveau message remplace l'ancien de même clé ;
// avec options.duree = 0, le message reste affiché jusqu'à masquerToast(cle) ou jusqu'à sa fermeture.
function afficherToast(texte, type = "erreur", options = {}) {
  if (!zoneToasts) return;
  if (options.cle) masquerToast(options.cle);
  const toast = document.createElement("div");
  toast.className = "toast " + type;
  toast.setAttribute("role", type === "erreur" ? "alert" : "status");
  if (options.cle) toast.dataset.cle = options.cle;
  const paragraphe = document.createElement("p");
  paragraphe.textContent = texte;
  toast.append(paragraphe);
  preparerToast(toast, options.duree === undefined ? 7000 : options.duree);
  zoneToasts.append(toast);
}

function masquerToast(cle) {
  if (!zoneToasts) return;
  for (const toast of zoneToasts.querySelectorAll(".toast")) {
    if (toast.dataset.cle === cle) fermerToast(toast);
  }
}

// Les messages envoyés par le serveur (flash) deviennent eux aussi des toasts qui disparaissent seuls.
if (zoneToasts) {
  for (const toast of zoneToasts.querySelectorAll(".toast")) {
    preparerToast(toast, toast.classList.contains("erreur") ? 8000 : 5000);
  }
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

// Prévient l'utilisateur quand l'API n'a pas répondu (le tableau HTML reste lisible).
function afficherEchecGraphique() {
  afficherToast("Le graphique est momentanément indisponible. Les valeurs figurent dans le tableau.", "erreur");
}
