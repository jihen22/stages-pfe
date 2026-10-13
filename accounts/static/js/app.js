/* App shell interactions: mobile sidebar drawer + Bootstrap toasts. */
(function () {
  "use strict";

  function init() {
    var sidebar = document.getElementById("appSidebar");
    var backdrop = document.getElementById("appBackdrop");

    function openSidebar() {
      if (sidebar) sidebar.classList.add("show");
      if (backdrop) backdrop.hidden = false;
    }

    function closeSidebar() {
      if (sidebar) sidebar.classList.remove("show");
      if (backdrop) backdrop.hidden = true;
    }

    document.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
      button.addEventListener("click", openSidebar);
    });
    document.querySelectorAll("[data-sidebar-close]").forEach(function (button) {
      button.addEventListener("click", closeSidebar);
    });
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeSidebar();
    });

    if (window.bootstrap && window.bootstrap.Toast) {
      document.querySelectorAll(".toast").forEach(function (element) {
        new window.bootstrap.Toast(element).show();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
