/* Theme + accent switching.
 *
 * The inline script in <head> applies the saved theme before paint (no flash).
 * This file wires the dropdowns / preference radios, keeps state in sync,
 * persists to localStorage for everyone and (for logged-in users) to the
 * backend through accounts:set_theme so the choice follows across devices.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var THEME_KEY = "sgi-theme";
  var ACCENT_KEY = "sgi-accent";

  function resolveTheme(theme) {
    if (theme === "AUTO") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return String(theme || "LIGHT").toLowerCase();
  }

  function syncOptions(attribute, value) {
    var target = String(value || "").toUpperCase();
    document.querySelectorAll("[" + attribute + "]").forEach(function (el) {
      var isActive = String(el.getAttribute(attribute)).toUpperCase() === target;
      el.classList.toggle("active", isActive);
      el.setAttribute("aria-pressed", isActive ? "true" : "false");
      if (el.matches("input[type=radio]")) {
        el.checked = isActive;
      }
    });
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-bs-theme", resolveTheme(theme));
    syncOptions("data-theme-option", theme);
    document.querySelectorAll("[data-theme-label]").forEach(function (el) {
      el.textContent =
        theme === "DARK" ? "Sombre" : theme === "LIGHT" ? "Clair" : "Auto";
    });
  }

  function applyAccent(accent) {
    root.setAttribute("data-accent", String(accent || "BLUE").toLowerCase());
    syncOptions("data-accent-option", accent);
  }

  function isAuthenticated() {
    return document.body.getAttribute("data-authenticated") === "1";
  }

  function endpoint() {
    return document.body.getAttribute("data-set-theme-url");
  }

  function csrfToken() {
    var meta = document.querySelector("meta[name=csrf-token]");
    return meta ? meta.getAttribute("content") : "";
  }

  function persist(theme, accent) {
    var payload = new URLSearchParams();
    if (theme) payload.set("theme", theme);
    if (accent) payload.set("accent", accent);
    if (!isAuthenticated() || !endpoint() || !csrfToken()) return;
    fetch(endpoint(), {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
      },
      body: payload.toString(),
      credentials: "same-origin",
    }).catch(function () {
      /* Keep the client-side choice even if the network call fails. */
    });
  }

  function setTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
    applyTheme(theme);
    persist(theme, null);
  }

  function setAccent(accent) {
    localStorage.setItem(ACCENT_KEY, accent);
    applyAccent(accent);
    persist(null, accent);
  }

  function init() {
    applyTheme(root.getAttribute("data-theme") || localStorage.getItem(THEME_KEY) || "AUTO");
    applyAccent(root.getAttribute("data-accent") || localStorage.getItem(ACCENT_KEY) || "BLUE");

    document.addEventListener("click", function (event) {
      var themeEl = event.target.closest("[data-theme-option]");
      if (themeEl && themeEl.tagName !== "INPUT") {
        event.preventDefault();
        setTheme(themeEl.getAttribute("data-theme-option"));
      }
      var accentEl = event.target.closest("[data-accent-option]");
      if (accentEl && accentEl.tagName !== "INPUT") {
        event.preventDefault();
        setAccent(accentEl.getAttribute("data-accent-option"));
      }
    });

    document.addEventListener("change", function (event) {
      if (event.target.matches("[data-theme-option]")) {
        setTheme(event.target.getAttribute("data-theme-option"));
      }
      if (event.target.matches("[data-accent-option]")) {
        setAccent(event.target.getAttribute("data-accent-option"));
      }
    });

    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", function () {
        if (root.getAttribute("data-theme") === "AUTO") {
          applyTheme("AUTO");
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
