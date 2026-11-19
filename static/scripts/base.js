(function () {
  const body = document.body;
  const sidebar = document.querySelector(".cm-sidebar");
  const toggle = document.querySelector(".cm-sidebar-toggle");
  const backdrop = document.querySelector(".cm-sidebar-backdrop");
  const mobileQuery = window.matchMedia("(max-width: 900px)");
  const storageKey = "cm-sidebar-collapsed";

  function setDesktopState(collapsed, save) {
    body.classList.toggle("cm-sidebar-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute(
      "aria-label",
      collapsed ? "Mostrar barra lateral" : "Ocultar barra lateral",
    );

    if (save) {
      window.localStorage.setItem(storageKey, String(collapsed));
    }
  }

  function syncForViewport() {
    backdrop.classList.remove("active");
    body.classList.remove("cm-sidebar-mobile-open");

    if (mobileQuery.matches) {
      body.classList.remove("cm-sidebar-collapsed");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Mostrar barra lateral");
      return;
    }

    const savedState = window.localStorage.getItem(storageKey) === "true";
    setDesktopState(savedState, false);
  }

  toggle.addEventListener("click", function () {
    if (mobileQuery.matches) {
      const isOpen = body.classList.toggle("cm-sidebar-mobile-open");
      backdrop.classList.toggle("active", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.setAttribute(
        "aria-label",
        isOpen ? "Ocultar barra lateral" : "Mostrar barra lateral",
      );
      return;
    }

    setDesktopState(!body.classList.contains("cm-sidebar-collapsed"), true);
  });

  backdrop.addEventListener("click", function () {
    body.classList.remove("cm-sidebar-mobile-open");
    backdrop.classList.remove("active");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Mostrar barra lateral");
  });

  document.addEventListener("keydown", function (event) {
    if (
      event.key === "Escape" &&
      body.classList.contains("cm-sidebar-mobile-open")
    ) {
      backdrop.click();
    }
  });

  document
    .querySelectorAll(".cm-nav-link, .cm-brand, .cm-logout")
    .forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
      });
    });

  sidebar.setAttribute("aria-hidden", "false");
  mobileQuery.addEventListener("change", syncForViewport);
  syncForViewport();
})();
