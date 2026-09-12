# -*- coding: utf-8 -*-
"""
In-content image hygiene
========================

A Pelican plugin that post-processes the rendered HTML of articles and pages
to improve loading performance and rendering behavior of inline `<img>` tags.

For every `<img>` tag in the content body it adds:

* ``loading="lazy"``   - defer offscreen images until they are near the viewport
* ``decoding="async"`` - let the browser decode the image off the main thread
* ``width`` / ``height`` - the image's real pixel dimensions, read from the
  source file on disk, so the browser can reserve layout space before the
  bytes arrive and avoid cumulative layout shift (CLS).

Attributes are only added when absent, so author-specified values (e.g. an
eager hero image with ``loading="eager"``, or an ``<img>`` that already carries
its own ``width``/``height``) are preserved.

Why width/height is safe here
-----------------------------
``content/static/custom.css`` styles content images with::

    main article p img { aspect-ratio: auto; height: auto; max-width: 100%; }

``height: auto`` (an author-stylesheet rule) beats the HTML ``height``
presentational attribute, so the injected dimensions never distort the image:
the browser derives the intrinsic aspect ratio from ``width``/``height`` and
scales by width. ``aspect-ratio: auto`` explicitly tells the browser to honour
those attributes for space reservation, which is exactly what kills CLS.

The dimensions are emitted as plain HTML attributes (``width="800"``), never a
``style=""`` attribute, so the strict-CSP audit (scripts/csp_audit.py) stays
green.

Resolving src -> file on disk
-----------------------------
``width``/``height`` require reading the source image, so the plugin maps each
``<img src>`` back to a file under the content tree. At
``content_object_init`` the ``src`` is still an intra-site marker
(``{static}/images/foo.webp``); after Pelican resolves links it is a site URL
(``/images/foo.webp`` or ``https://rivassec.com/images/foo.webp``). Both forms
carry the same site-relative path, so ``_resolve_src_to_file`` strips any
marker, scheme, or host and maps the ``/images/...`` (or any ``STATIC_PATHS``
directory) tail onto ``<PATH>/images/...`` on disk. Remote hosts and
``data:``/``blob:`` URIs are skipped - there is no local file to measure.

The transform is a conservative regex over the content HTML; it never rewrites
``src``/``href`` values, so Pelican's ``{static}``/``{filename}`` link
resolution (which runs lazily on ``.content`` access) is unaffected.
"""

import os
import re
import logging

from pelican import signals, contents

try:  # Pillow is a build dependency; degrade gracefully if it is ever absent.
    from PIL import Image
except Exception:  # pragma: no cover - only hit if Pillow is missing
    Image = None

logger = logging.getLogger(__name__)

# Match a single <img ...> start tag. [^>]* is the standard practical bound;
# it does not handle a literal ">" inside a quoted attribute value, which is
# vanishingly rare in image alt text.
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HAS_LOADING_RE = re.compile(r"\bloading\s*=", re.IGNORECASE)
_HAS_DECODING_RE = re.compile(r"\bdecoding\s*=", re.IGNORECASE)
_HAS_WIDTH_RE = re.compile(r"\bwidth\s*=", re.IGNORECASE)
_HAS_HEIGHT_RE = re.compile(r"\bheight\s*=", re.IGNORECASE)
_SRC_RE = re.compile(r"""\bsrc\s*=\s*(?P<q>["'])(?P<val>.*?)(?P=q)""", re.IGNORECASE)
# Intra-site link markers Pelican leaves in _content before .content resolves.
_MARKER_RE = re.compile(r"^\{(?:static|filename|attach)\}", re.IGNORECASE)

# filepath -> (width, height) | None. Process-lifetime cache so an image
# referenced from several posts is only opened once per build.
_DIM_CACHE = {}


def _dimensions(filepath):
    """Return (width, height) for a local image file, or None on any failure."""
    if filepath in _DIM_CACHE:
        return _DIM_CACHE[filepath]
    result = None
    if Image is not None:
        try:
            with Image.open(filepath) as im:
                result = im.size  # (width, height)
        except Exception as exc:  # noqa: BLE001 - never let image reads break the build
            # Broad on purpose: Pillow raises DecompressionBombError (subclasses
            # Exception, not OSError) on very large images; dimension injection
            # is best-effort and must degrade to "no dims", never fail the build.
            logger.debug("img_hygiene: cannot read dimensions of %s: %s", filepath, exc)
    _DIM_CACHE[filepath] = result
    return result


def _resolve_src_to_file(src, settings):
    """Map an <img src> (marker or resolved URL) to a source file on disk.

    Returns an absolute/relative filesystem path if the src points at a local
    static asset that exists, else None (remote, data URI, or not found).
    """
    src = src.strip()
    if not src:
        return None

    # Strip a leading intra-site marker ({static}/{filename}/{attach}); the
    # remainder is a site-relative path such as /images/foo.webp.
    marker = _MARKER_RE.match(src)
    if marker:
        path = src[marker.end():]
    else:
        lower = src.lower()
        if lower.startswith(("data:", "blob:")):
            return None
        if "://" in src:
            # Absolute URL. Only our own site can be mapped to disk; anything
            # else is a remote image with no local file to measure.
            scheme, _, rest = src.partition("://")
            if scheme.lower() not in ("http", "https"):
                return None
            host, _, tail = rest.partition("/")
            siteurl = (settings.get("SITEURL") or "") if settings else ""
            local_hosts = {"rivassec.com", "www.rivassec.com"}
            if "://" in siteurl:
                local_hosts.add(siteurl.split("://", 1)[1].split("/", 1)[0])
            if host not in local_hosts:
                return None
            path = "/" + tail
        else:
            # Site-relative or document-relative path (e.g. /images/x.webp or
            # ../images/x.webp).
            path = src

    # Drop any query string or fragment.
    path = path.split("?", 1)[0].split("#", 1)[0]

    content_root = settings.get("PATH", "content") if settings else "content"
    static_dirs = settings.get("STATIC_PATHS", ["images"]) if settings else ["images"]

    # Locate the static directory segment (e.g. "images/") within the path and
    # rebuild the path relative to the content root. Handles /images/x.webp,
    # ../images/x.webp, {static}/images/x.webp alike.
    for static_dir in static_dirs:
        needle = static_dir.strip("/") + "/"
        idx = path.rfind("/" + needle)
        if idx != -1:
            rel = path[idx + 1:]
        elif path.startswith(needle):
            rel = path
        else:
            continue
        candidate = os.path.join(content_root, rel)
        if os.path.isfile(candidate):
            return candidate
    return None


def _make_augmenter(settings):
    def _augment_img(match):
        tag = match.group(0)
        additions = ""
        if not _HAS_LOADING_RE.search(tag):
            additions += ' loading="lazy"'
        if not _HAS_DECODING_RE.search(tag):
            additions += ' decoding="async"'

        # Only inject dimensions when the tag has neither width nor height, so
        # author-specified sizing is always respected.
        if not _HAS_WIDTH_RE.search(tag) and not _HAS_HEIGHT_RE.search(tag):
            src_match = _SRC_RE.search(tag)
            if src_match:
                filepath = _resolve_src_to_file(src_match.group("val"), settings)
                if filepath:
                    dims = _dimensions(filepath)
                    if dims:
                        additions += ' width="%d" height="%d"' % (dims[0], dims[1])

        if not additions:
            return tag
        # Insert new attributes just before the tag close, preserving whether
        # the original tag was self-closing ("/>") or a plain start tag (">").
        if tag.endswith("/>"):
            return tag[:-2].rstrip() + additions + " />"
        return tag[:-1] + additions + ">"

    return _augment_img


def add_image_hygiene(content):
    # Static objects (raw files) carry no rendered HTML body to rewrite.
    if isinstance(content, contents.Static):
        return
    html = getattr(content, "_content", None)
    if not html or "<img" not in html:
        return
    settings = getattr(content, "settings", None) or {}
    content._content = _IMG_TAG_RE.sub(_make_augmenter(settings), html)


def register():
    signals.content_object_init.connect(add_image_hygiene)
