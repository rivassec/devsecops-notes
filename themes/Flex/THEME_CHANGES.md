# Local changes to Flex

This is a vendored copy of [alexandrevicenzi/Flex](https://github.com/alexandrevicenzi/Flex) with repo-specific edits. Keep this file up to date when making further changes so an upstream sync is a clean rebase.

## Template edits

### `templates/base.html`
- Removed `{% if USE_LESS %}` branch and the CDN `less.min.js` fetch. We ship only pre-compiled `.min.css`.
- Removed Font Awesome `<link rel=stylesheet>` tags (3 of them). Icons are inline SVG now.
- Removed includes for `ga.html`, `ggst.html`, `plausible.html`, `gtm.html`, `clarity.html`, `gtm_noscript.html`, `guages.html`, `addthis.html`, `matomo.html`, `github.html`, `stork.html`, `cf_analytics.html`. None of the gate variables they expected are ever set.
- Removed the page-level Google Adsense script block and the `main_menu` ad slot.
- Kept includes: `icon.html`, `color.html`, `feed.html`, `og.html`, `sidebar.html`, `nav.html`, `footer.html`, `jsonld.html`.

### `templates/article.html`
- Added `{% include "partial/jsonld_article.html" %}` in the meta block (the partial was shipped but never rendered upstream).
- Added `{% if article.toc %}<aside class="article-toc">` block that renders the `extract_toc` plugin output.
- Removed `article_top` / `article_bottom` Google Adsense blocks.
- Removed includes for `disqus.html`, `isso.html`.

### `templates/index.html`
- Removed `index_top` and `index_bottom` Google Adsense blocks.

### `templates/partial/og.html`
- Replaced site-level `og:image` fallback chain with `OG_IMAGE` default -> `SITELOGO`, emitting absolute URL.
- Added Twitter Card tags (`twitter:card=summary_large_image`, `twitter:title`, `twitter:description`, `twitter:image`, `twitter:site`).

### `templates/partial/og_article.html`
- Extended `og:image` fallback chain to `article.cover -> OG_IMAGE -> SITELOGO`.
- Added Twitter Card tags with per-article values.

### `templates/partial/jsonld.html`
- `image` now emits an absolute URL (was relative to current page).
- Prefers `OG_IMAGE` over `SITELOGO` when set.

### `templates/partial/jsonld_article.html`
- Article-specific image chain: `article.cover -> OG_IMAGE -> SITELOGO`, all absolute URLs.
- Fixed default-cover default reference (upstream template had a string-literal bug).

### `templates/partial/icon.html`
- Rewrote to emit proper `rel="icon"` + `apple-touch-icon` link tags with explicit `sizes` attributes. Uses `SITEURL`-prefixed absolute URLs so they resolve from any page.

### `templates/partial/neighbors.html` and `partial/pagination.html`
- Chevrons replaced with inline SVG (was Font Awesome `<i class="fa fa-angle-*">`).

### `templates/partial/sidebar.html`
- Social-icon loop delegates to `partial/social_icons.html` for inline SVG dispatch. `aria-label` added to each link for screen-reader accessibility.
- Removed `aside` Google Adsense slot.

### `templates/partial/social_icons.html` (new)
- Repo-specific partial. Dispatches on the lowercase SOCIAL name to inline SVG: github, linkedin, twitter/x, mastodon, rss, envelope, with a generic external-link fallback.

## Static edits

### `static/font-awesome/` (removed entirely)
- 1.04 MB of CSS + webfont files for 3 icons, replaced with inline SVG in templates.

### `static/pygments/`
- Kept only `monokai.*` (active) and `github.*` (dark-mode fallback). Removed 72 other syntax themes.

### `static/stylesheet/`
- Removed `style.less`, `dark-theme.less`, `variables.less` (source files). Only pre-compiled `.min.css` ship.

### `translations/` (removed entirely)
- 23 gettext locale files, 176 KB. `DEFAULT_LANG='en'` is the only language configured; none load.

## Upstream sync strategy

When pulling new upstream Flex releases:

1. Fetch upstream to a comparison checkout.
2. Diff `templates/base.html`, `templates/article.html`, `templates/index.html`, and the `templates/partial/` files against this tree.
3. For each upstream change, decide: accept cleanly, merge with our local edit, or keep our version verbatim.
4. Do NOT re-add Font Awesome, LESS sources, unused pygments themes, translations, or the dead analytics/ads partials - those deletions are intentional and tracked here.

The above list is canonical; when adding a new local edit, update this file in the same PR.
