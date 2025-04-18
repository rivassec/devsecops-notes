# DevSecOps Notes by RivasSec

This is the source code and content for [DevSecOps Notes](https://rivassec.github.io/devsecops-notes), a technical blog focused on infrastructure security, OSINT, cloud hardening, and DevSecOps practices — curated and maintained by **RivasSec**.

---

## 📦 Features

- Static site powered by [Pelican](https://getpelican.com/)
- Professional layout using the [Flex theme](https://github.com/alexandrevicenzi/Flex)
- Markdown-based blog posts located in `content/`
- GitHub Pages deployment (via the `output/` folder)

---

## 🛠️ Local Development

### 1. Install dependencies

```bash
pip install pelican markdown
```

(Optional) Create a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Clone and build the theme

```bash
git clone https://github.com/alexandrevicenzi/Flex themes/Flex
```

### 3. Build the site

```bash
make clean
make html
make serve  # View at http://localhost:8000
```

---

## 🚀 Deploying to GitHub Pages

The blog is deployed from the `output/` directory. After rebuilding the site:

```bash
cd output
git add .
git commit -m "Update site"
git push
```

Make sure your `gh-pages` branch (or root) is configured correctly in the GitHub Pages settings.

---

## 🧾 License

Content is © RivasSec. All rights reserved unless otherwise noted.

For inquiries or collaboration, reach out via [GitHub](https://github.com/rivassec).

