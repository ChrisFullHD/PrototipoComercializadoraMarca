(function () {
  const searchInput = document.querySelector("#baja-search");
  const rows = document.querySelectorAll(".record-row");
  const emptyState = document.querySelector("#search-empty-state");

  if (!searchInput) return;

  searchInput.addEventListener("input", function () {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    rows.forEach(function (row) {
      const matches = !query || (row.dataset.search || "").toLowerCase().includes(query);
      row.hidden = !matches;
      if (matches) visibleCount += 1;
    });

    if (emptyState) {
      emptyState.classList.toggle("d-none", visibleCount > 0 || rows.length === 0);
    }
  });
})();
