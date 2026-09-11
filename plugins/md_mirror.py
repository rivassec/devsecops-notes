# -*- coding: utf-8 -*-
"""
Markdown mirrors for published articles
=======================================

A Pelican plugin that copies each published article's Markdown source into the
output root as ``{slug}.md``, so language models and other tooling can fetch a
token-cheap plain-text version of any post (the llms.txt convention of linking
``.md`` variants next to HTML pages).

Only published articles are mirrored: drafts live on ``generator.drafts`` and
are never touched, so nothing under ``Status: draft`` can leak. The copy runs
on the ``finalized`` signal, after every generator (including the sitemap) has
written, so mirrors never appear in the sitemap.
"""
import os
import shutil

from pelican import signals

_articles = []


def _grab_articles(generator):
    global _articles
    _articles = list(generator.articles)


def _write_mirrors(pelican):
    out = pelican.settings['OUTPUT_PATH']
    count = 0
    for article in _articles:
        src = getattr(article, 'source_path', None)
        if not src or not src.endswith('.md') or not os.path.isfile(src):
            continue
        dst = os.path.join(out, '{0}.md'.format(article.slug))
        shutil.copyfile(src, dst)
        count += 1
    print('md_mirror: wrote {0} markdown mirrors'.format(count))


def register():
    signals.article_generator_finalized.connect(_grab_articles)
    signals.finalized.connect(_write_mirrors)
