/* Shared micro-interactions for the redesigned pages.
 *
 * - .reveal      : fades/slides in when it enters the viewport
 * - [data-counter]: counts up to its numeric value once, when visible
 *
 * Both respect prefers-reduced-motion: content is shown immediately and
 * counters jump straight to their final value.
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasObserver = "IntersectionObserver" in window;

  function animateCounter(element) {
    var target = parseFloat(element.getAttribute("data-counter"));
    if (isNaN(target)) return;

    var prefix = element.getAttribute("data-counter-prefix") || "";
    var suffix = element.getAttribute("data-counter-suffix") || "";
    var decimals = (String(target).split(".")[1] || "").length;
    var duration = 900;
    var startedAt = null;

    if (reduceMotion) {
      element.textContent = prefix + target.toFixed(decimals) + suffix;
      return;
    }

    function tick(now) {
      if (startedAt === null) startedAt = now;
      var progress = Math.min((now - startedAt) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (progress < 1) window.requestAnimationFrame(tick);
    }

    window.requestAnimationFrame(tick);
  }

  function initReveal() {
    var elements = document.querySelectorAll(".reveal");
    if (!elements.length) return;

    if (reduceMotion || !hasObserver) {
      elements.forEach(function (element) {
        element.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    elements.forEach(function (element) {
      observer.observe(element);
    });
  }

  function initCounters() {
    var elements = document.querySelectorAll("[data-counter]");
    if (!elements.length) return;

    if (reduceMotion || !hasObserver) {
      elements.forEach(animateCounter);
      return;
    }

    var observer = new IntersectionObserver(
      function (entries, current) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            current.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );

    elements.forEach(function (element) {
      observer.observe(element);
    });
  }

  function init() {
    initReveal();
    initCounters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
