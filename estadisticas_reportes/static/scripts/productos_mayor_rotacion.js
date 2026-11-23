(function () {
  const searchInput = document.querySelector("#rotation-search");
  const rows = document.querySelectorAll(".rotation-row");
  const emptyState = document.querySelector("#rotation-empty-state");

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
