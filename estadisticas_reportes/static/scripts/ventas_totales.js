(function () {
  const tabs = document.querySelectorAll(".period-tab");
  const fields = document.querySelectorAll("[data-period-field]");
  const filtersPanel = document.querySelector("[data-active-period]");
  const initialPeriod = filtersPanel?.dataset.activePeriod || "dia";

  function aplicarPeriodo(period) {
    tabs.forEach(function (item) {
      const active = item.dataset.period === period;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    });

    fields.forEach(function (field) {
      const visible = field.dataset.periodField === period;
      field.classList.toggle("d-none", !visible);

      const input = field.querySelector("input");
      if (input) input.disabled = !visible;
    });
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      aplicarPeriodo(tab.dataset.period);
    });
  });

  aplicarPeriodo(initialPeriod);
})();
