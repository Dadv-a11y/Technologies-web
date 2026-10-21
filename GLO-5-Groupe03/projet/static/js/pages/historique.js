// historique.js : graphique d'évolution d'un élève (moyennes de l'élève et de sa classe).

async function dessinerEvolution(canvas) {
  const donnees = await chargerJson(canvas.dataset.url);
  if (!donnees) return afficherEchecGraphique(canvas);
  new Chart(canvas, {
    type: "line",
    data: {
      labels: donnees.sequences,
      datasets: [
        { label: "Moyenne de l'élève", data: donnees.moyennes, borderColor: COULEURS.bleu, backgroundColor: COULEURS.bleu, borderWidth: 3, tension: 0.25 },
        { label: "Moyenne de la classe", data: donnees.moyennes_classe, borderColor: COULEURS.or, backgroundColor: COULEURS.or, borderDash: [6, 4], tension: 0.25 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { min: 0, max: 20, title: { display: true, text: "Moyenne /20" } } },
    },
  });
}

const canvasEvolution = document.querySelector("#graphique-evolution");
if (canvasEvolution && typeof Chart !== "undefined") dessinerEvolution(canvasEvolution);
