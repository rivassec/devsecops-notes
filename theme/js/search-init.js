/* Initializes the Pagefind UI on /search/. Lives in an external file on
 * purpose: the site ships zero inline scripts (script-src 'self',
 * precondition enforced by scripts/csp_audit.py in CI). Loaded with defer
 * after pagefind-ui.js, so PagefindUI is defined and the DOM is parsed. */
(function () {
  "use strict";
  if (typeof PagefindUI === "undefined") { return; }
  new PagefindUI({
    element: "#search",
    showSubResults: true,
    showImages: false,
  });
})();
