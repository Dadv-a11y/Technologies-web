// liste_classe.js : graphique du nombre d'élèves par tranche de moyenne, pour une classe.

async function dessinerClasse(canvas) {
  const donnees = await chargerJson(canvas.dataset.url);
  if (!donnees) return afficherEchecGraphique(canvas);
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: Object.keys(donnees.tranches),
      datasets: [{ label: "Élèves", data: Object.values(donnees.tranches), backgroundColor: COULEURS.bleu }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "Nombre d'élèves" } } },
    },
  });
}

const canvasClasse = document.querySelector("#graphique-classe");
if (canvasClasse && typeof Chart !== "undefined") dessinerClasse(canvasClasse);
