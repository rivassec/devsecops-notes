# -*- coding: utf-8 -*-
"""
Feed polish
===========

A Pelican plugin that fixes two things in the generated Atom/RSS feeds, both
from the "RSS Feed Best Practices" checklist (kevincox.ca, 2022):

* **Absolute URLs in entry content.** Posts link to each other with relative
  hrefs (``iam-safe-defaults-fail-loud.html``, ``/tools/iam-blast-radius/``).
  That is fine on the site, but many feed readers resolve relative URLs in
  feed content wrongly (or not at all), so the links break in the reader. Every
  relative ``href``/``src`` in an entry's content and summary is resolved
  against the entry's own permalink. Fragments (``#x``), ``mailto:``,
  ``tel:`` and ``data:`` URLs are left alone.
* **Feed title.** Pelican always titles feeds with ``SITENAME`` (the long
  ``<title>`` used for SEO). ``FEED_TITLE``, when set, replaces that prefix in
  feed titles only, keeping Pelican's `` - <category>`` suffix on category feeds.

Runs on the ``feed_generated`` signal, so it only touches feeds, never the site
pages.
"""
import re
from urllib.parse import urljoin

_ATTR_RE = re.compile(r'(\s(?:href|src)\s*=\s*)(["\'])(.*?)\2', re.IGNORECASE | re.DOTALL)
_KEEP_RE = re.compile(r'^(?:[a-z][a-z0-9+.-]*:|//|#)', re.IGNORECASE)


def absolutize(html, base):
    """Resolve every relative href/src in ``html`` against ``base``."""
    if not html or not base:
        return html

    def repl(m):
        url = m.group(3).strip()
        if not url or _KEEP_RE.match(url):
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}{urljoin(base, url)}{m.group(2)}"

    return _ATTR_RE.sub(repl, html)


def polish_feed(context, feed):
    title = context.get("FEED_TITLE")
    sitename = context.get("SITENAME", "")
    if title and sitename:
        current = feed.feed.get("title", "")
        if current == sitename or current.startswith(sitename + " - "):
            feed.feed["title"] = title + current[len(sitename):]

    for item in feed.items:
        base = item.get("link")
        for key in ("description", "content"):
            if item.get(key):
                item[key] = absolutize(item[key], base)


def register():
    # Imported here so the helpers above stay testable without Pelican installed
    # (the tests workflow runs stdlib unittest only).
    from pelican import signals

    signals.feed_generated.connect(polish_feed)
