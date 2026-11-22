(function () {
  const canvas = document.querySelector("#productos-rotacion-chart");
  if (!canvas || typeof Chart === "undefined") return;

  const labelsElement = document.querySelector("#productos-labels");
  const valoresElement = document.querySelector("#productos-valores");
  if (!labelsElement || !valoresElement) return;

  const labels = JSON.parse(labelsElement.textContent);
  const valores = JSON.parse(valoresElement.textContent);

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Unidades vendidas",
        data: valores,
        backgroundColor: "rgba(84, 120, 90, 0.78)",
        borderColor: "#54785a",
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
})();
