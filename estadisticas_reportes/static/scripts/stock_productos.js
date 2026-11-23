(function () {
  const searchInput = document.querySelector("#stock-search");
  const rows = document.querySelectorAll(".stock-row");
  const tabs = document.querySelectorAll(".stock-tab");
  const emptyState = document.querySelector("#stock-empty-state");
  let activeFilter = "todos";

  if (!searchInput) return;

  function actualizarTabla() {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    rows.forEach(function (row) {
      const coincideTexto =
        !query || (row.dataset.search || "").toLowerCase().includes(query);
      const coincideFiltro =
        activeFilter === "todos" || row.dataset.lowStock === "true";
      const visible = coincideTexto && coincideFiltro;

      row.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    if (emptyState) {
      emptyState.classList.toggle(
        "d-none",
        visibleCount > 0 || rows.length === 0,
      );
    }
  }

  searchInput.addEventListener("input", actualizarTabla);

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      activeFilter = tab.dataset.stockFilter;

      tabs.forEach(function (item) {
        const activo = item === tab;
        item.classList.toggle("active", activo);
        item.setAttribute("aria-pressed", String(activo));
      });

      actualizarTabla();
    });
  });
})();
