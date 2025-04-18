# DevSecOps Notes

A growing collection of field-tested tips, security hardening guides, and cloud-native best practices — written from hands-on experience in DevSecOps, Kubernetes, and infrastructure security.

This blog is generated using [Pelican](https://getpelican.com/), a static site generator written in Python, and published via GitHub Pages.

## 🔍 Topics Covered

- Kubernetes security (Pod Security Standards, restricted profiles)
- CI/CD pipeline hardening
- Infrastructure as Code (IaC) security
- Secrets management
- Secure defaults for cloud-native deployments
- Container hardening (Docker, Podman)

## 🚀 Getting Started

1. Clone the repository:

```bash
git clone https://github.com/rivassec/devsecops-notes.git
cd devsecops-notes
```

2. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run a local preview:

```bash
pelican content -o output -s pelicanconf.py
python3 -m http.server --directory output/
```

5. Visit `http://localhost:8000` in your browser.

## 🌐 Live Site

View the published blog at:  
👉 https://rivassec.github.io/devsecops-notes/

## 📄 License

- Text and articles are licensed under [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- Code snippets are available under the [MIT License](LICENSE).
