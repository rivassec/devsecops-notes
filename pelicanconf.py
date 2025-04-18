AUTHOR = 'RivasSec'
SITENAME = 'DevSecOps Notes'
SITESUBTITLE = 'Infrastructure. Security. Insight.'
SITEURL = 'https://rivassec.github.io/devsecops-notes'

PATH = "content"
STATIC_PATHS = ['images']
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
USE_GOOGLE_FONTS = True
BROWSER_COLOR = '#222222'
PYGMENTS_STYLE = 'monokai'

# Optional site assets
SITELOGO = '/images/avatar.png'  # Must exist in content/images/
FAVICON = '/images/favicon.ico'
EXTRA_PATH_METADATA = {
    'images/favicon.ico': {'path': 'favicon.ico'},
    'images/avatar.png': {'path': 'avatar.png'},
}

# Social widget
SOCIAL = (
    ("GitHub", "https://github.com/rivassec"),
#    ("LinkedIn", "https://linkedin.com/in/9082311s2"),
)
GITHUB_URL = "https://github.com/rivassec"

# Footer
COPYRIGHT_NAME = "RivasSec"

DEFAULT_PAGINATION = 10

# Development
RELATIVE_URLS = True
