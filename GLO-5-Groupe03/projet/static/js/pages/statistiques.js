// statistiques.js : graphique des tranches de moyenne, une série par classe.

async function dessinerTranches(canvas) {
  const donnees = await chargerJson(canvas.dataset.url);
  if (!donnees) return afficherEchecGraphique(canvas);
  const palette = [COULEURS.bleu, COULEURS.or, COULEURS.vert, COULEURS.gris];
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: donnees.tranches,
      datasets: donnees.classes.map((c, i) => ({
        label: c.classe,
        data: donnees.tranches.map((t) => c.tranches[t]),
        backgroundColor: palette[i % palette.length],
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "Nombre d'élèves" } } },
    },
  });
}

const canvasTranches = document.querySelector("#graphique-tranches");
if (canvasTranches && typeof Chart !== "undefined") dessinerTranches(canvasTranches);
