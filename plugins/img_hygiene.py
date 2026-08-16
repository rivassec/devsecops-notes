# -*- coding: utf-8 -*-
"""
In-content image hygiene
========================

A Pelican plugin that post-processes the rendered HTML of articles and pages
to improve loading performance and rendering behavior of inline `<img>` tags.

For every `<img>` tag in the content body it adds:

* ``loading="lazy"``   - defer offscreen images until they are near the viewport
* ``decoding="async"`` - let the browser decode the image off the main thread

Attributes are only added when absent, so author-specified values (e.g. an
eager hero image with ``loading="eager"``) are preserved. The transform is a
conservative regex over the content HTML - it never touches ``src``/``href``
values, so Pelican's ``{static}``/``{filename}`` link resolution (which runs
lazily on ``.content`` access) is unaffected.

Width/height injection is intentionally NOT performed: it would require
resolving each ``{static}`` path back to a local file and reading its
dimensions with PIL, which is not straightforward given intra-site link
markers are unresolved at ``content_object_init`` time. Lazy-loading plus
async decoding are the high-value, zero-risk wins.
"""

import re
import logging

from pelican import signals, contents

logger = logging.getLogger(__name__)

# Match a single <img ...> start tag. [^>]* is the standard practical bound;
# it does not handle a literal ">" inside a quoted attribute value, which is
# vanishingly rare in image alt text.
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HAS_LOADING_RE = re.compile(r"\bloading\s*=", re.IGNORECASE)
_HAS_DECODING_RE = re.compile(r"\bdecoding\s*=", re.IGNORECASE)


def _augment_img(match):
    tag = match.group(0)
    additions = ""
    if not _HAS_LOADING_RE.search(tag):
        additions += ' loading="lazy"'
    if not _HAS_DECODING_RE.search(tag):
        additions += ' decoding="async"'
    if not additions:
        return tag
    # Insert new attributes just before the tag close, preserving whether the
    # original tag was self-closing ("/>") or a plain HTML5 start tag (">").
    if tag.endswith("/>"):
        return tag[:-2].rstrip() + additions + " />"
    return tag[:-1] + additions + ">"


def add_image_hygiene(content):
    # Static objects (raw files) carry no rendered HTML body to rewrite.
    if isinstance(content, contents.Static):
        return
    html = getattr(content, "_content", None)
    if not html or "<img" not in html:
        return
    content._content = _IMG_TAG_RE.sub(_augment_img, html)


def register():
    signals.content_object_init.connect(add_image_hygiene)
