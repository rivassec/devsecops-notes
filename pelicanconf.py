import os
import subprocess

AUTHOR = 'Oliver Rivas'


def _asset_version() -> str:
    """Return a stable per-deploy version string for cache-busting.

    Priority:
    1. GITHUB_SHA env var (set by GitHub Actions; changes on every commit)
    2. `git rev-parse HEAD` (works for local builds)
    3. Literal 'dev' (last resort so builds never fail on this)

    Truncated to 8 chars because we only need it distinct per deploy, not
    cryptographically unique. Referenced from base.html as ?v={{ ASSET_VERSION }}.
    """
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:8]
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if sha:
            return sha[:8]
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return "dev"


ASSET_VERSION = _asset_version()
SITENAME = 'RivasSec | DevSecOps, Kubernetes, AWS IAM'
SITETITLE = 'RivasSec'
SITESUBTITLE = 'Infrastructure. Security. Insight.'
SITEURL = 'https://rivassec.com'
SITEDESCRIPTION = 'Field notes on infrastructure security, cloud hardening, Kubernetes, IAM, and OSINT by RivasSec.'
OG_IMAGE = 'images/og-default.png'
TWITTER_USERNAME = 'rivassec'

PATH = "content"
ARTICLE_EXCLUDES = ['_external', 'extra']
STATIC_PATHS = ['images', 'static']
CUSTOM_CSS = 'static/custom.css'
THEME = 'themes/Flex'
TIMEZONE = 'America/Los_Angeles'
DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Appearance and menu
MAIN_MENU = True
DISPLAY_PAGES_ON_MENU = False
DISPLAY_CATEGORIES_ON_MENU = True
DISPLAY_TAGS_ON_MENU = True
USE_GOOGLE_FONTS = False
BROWSER_COLOR = '#222222'
PYGMENTS_STYLE = 'monokai'

# Optional site assets
SITELOGO = 'images/avatar.png'
SITELOGO_SIZE = 32
# Favicon lives at /favicon.ico so browser defaults find it. Multiple PNG
# sizes are emitted for higher-DPI tabs and iOS home-screen shortcuts.
FAVICON = '/favicon.ico'
EXTRA_PATH_METADATA = {
    'images/avatar.png': {'path': 'images/avatar.png'},
}

# Plugins (vendored under plugins/; see plugins/ for sources)
PLUGIN_PATHS = ['plugins']
PLUGINS = [
    'sitemap',
    'neighbors',
    'post_stats',
    'related_posts',
    'extract_toc',
    'img_hygiene',
]

# related_posts configuration
RELATED_POSTS_MAX = 5

# Markdown: extract_toc needs the python-markdown `toc` extension to emit a
# <div class="toc"> block that it then lifts into article.toc.
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {'permalink': False},
    },
    'output_format': 'html5',
}

SITEMAP = {
    'format': 'xml',
    'priorities': {
        'articles': 0.8,
        'indexes': 0.5,
        'pages': 0.3,
    },
    'changefreqs': {
        'articles': 'weekly',
        'indexes': 'daily',
        'pages': 'monthly',
    },
    # Tag pages are noindex,follow (see themes/Flex/templates/base.html) because
    # they are thin taxonomy that overlaps the curated Category pages. Keep them
    # out of the sitemap too, so we never advertise a URL we ask Google not to
    # index. Categories remain the indexable taxonomy surface. Matched with
    # re.match against the output URL (e.g. "tag/aws.html").
    # tags.html and archives.html are noindex,follow (see base.html), so keep
    # them out of the sitemap too - never advertise a URL we ask Google not to
    # index. Surfaced by GSC 'Discovered - not indexed' 2026-08-16.
    'exclude': ['tag/', 'tags.html', 'archives.html'],
}
STATIC_PATHS.append('extra')
# Client-side tools ship verbatim: content/tools/ -> /tools/ (no remap, no
# Pelican processing). See tools/iam-blast-radius/docs/DEPLOY.md.
STATIC_PATHS.append('tools')
EXTRA_PATH_METADATA['extra/robots.txt'] = {'path': 'robots.txt'}
# Favicons ship at the site root so /favicon.ico resolves on every request.
EXTRA_PATH_METADATA['extra/favicon.ico'] = {'path': 'favicon.ico'}
EXTRA_PATH_METADATA['extra/favicon-16.png'] = {'path': 'favicon-16.png'}
EXTRA_PATH_METADATA['extra/favicon-32.png'] = {'path': 'favicon-32.png'}
EXTRA_PATH_METADATA['extra/apple-touch-icon.png'] = {'path': 'apple-touch-icon.png'}
# Legacy slug redirect: PR #15 renamed bt-tether-multi -> pwnagotchi-bluetooth-tethering.
EXTRA_PATH_METADATA['extra/bt-tether-multi.html'] = {'path': 'bt-tether-multi.html'}
EXTRA_PATH_METADATA['tools/iam-blast-radius/index.html'] = {'path': 'tools/iam-blast-radius/index.html'}
# Serve raw HTML files (the tool's index.html, the bt-tether redirect stub) as
# static assets. Without this, Pelican's HTML reader claims a dateless static
# .html and skips it ("could not find information about 'date'") so it never
# reaches output. Both content .html files are static (no Pelican metadata),
# verified with an isolated build. See tools/iam-blast-radius/docs/DEPLOY.md.
READERS = {'html': None}
EXTRA_PATH_METADATA['extra/security.txt'] = {'path': '.well-known/security.txt'}

# Social widget
SOCIAL = (
    ("GitHub", "https://github.com/rivassec"),
#    ("LinkedIn", "https://linkedin.com/in/9082311s2"),
)
GITHUB_URL = "https://github.com/rivassec"

# Footer
COPYRIGHT_NAME = "RivasSec"

DEFAULT_PAGINATION = 10

# Author-page de-duplication: with a single canonical author (see AUTHOR
# above) plus DEFAULT_PAGINATION=10, an author with >10 posts would still
# split into author/<slug>.html AND author/<slug>2.html - a pagination
# page 2 that looks like a duplicate author page. The Flex author template
# requires the pagination context, so we cannot drop 'author' from the set;
# instead we give author pages a very high per-page count so every post by
# the canonical author lands on one page. index/tag/category keep the
# default (None -> DEFAULT_PAGINATION).
PAGINATED_TEMPLATES = {'index': None, 'tag': None, 'category': None, 'author': 10000}

# Auto-defer future-dated posts.
# Any article with a Date: value in the future gets Status: draft by
# default and is not built into the published site. Lets us schedule
# posts by editing the Date: frontmatter and letting the build cadence
# pick them up once the date passes.
# Docs: https://docs.getpelican.com/en/latest/settings.html
WITH_FUTURE_DATES = False

# Development
RELATIVE_URLS = True

TAG_CLOUD_MAX_ITEMS = 10
MENUITEMS = [
    ('About', 'https://rivassec.com/pages/about.html'),
    ('Categories', 'https://rivassec.com/categories.html'),
    ('Tools', 'https://rivassec.com/tools/iam-blast-radius/'),
    ('GitHub', 'https://github.com/rivassec'),
]
SUMMARY_MAX_LENGTH = 350  # words
DIRECT_TEMPLATES = ['index', 'categories', 'tags', 'archives']

# Render llms.txt / llms-full.txt for AI-crawler discovery from the article set.
TEMPLATE_PAGES = {
    'llms_txt.html': 'llms.txt',
    'llms_full_txt.html': 'llms-full.txt',
}

# One-line intros rendered at the top of each /category/<name>.html page.
# Keys match Category: frontmatter values exactly.
CATEGORY_INTROS = {
    'DevSecOps': 'Security defaults, pipeline hardening, and operational lessons from running production infrastructure under real adversary pressure.',
    'Kubernetes Security': 'Pod-level guardrails, RBAC, and the Pod Security Standards applied to production workloads.',
    'Incident Retrospectives': 'Post-mortems on real outages - what broke, why it broke, and what the industry should have learned.',
    'Projects': 'Tools, plugins, and one-off builds from my homelab and field work.',
    'Threat Intelligence': 'OSINT investigations and case studies on phishing infrastructure, nation-state operations, and emerging threats.',
}

# Homepage featured posts: hand-picked slugs, ordered. Surfaced at the
# top of index.html as a "Start here" panel ahead of the chronological
# feed.
FEATURED_POST_SLUGS = [
    'paved-road-adoption-as-control',
    'iam-safe-defaults-fail-loud',
    'teensy-efi-bruteforce-hours-late',
]
