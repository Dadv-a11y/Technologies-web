// bulletin.js : bouton « Imprimer » du bulletin.
// Le bouton est caché dans le HTML : sans JavaScript, il ne servirait à rien.

const boutonImprimer = document.querySelector("#bouton-imprimer");
if (boutonImprimer) {
  boutonImprimer.hidden = false;
  boutonImprimer.addEventListener("click", () => window.print());
}
