# EITR — Multi-Provider Terraform Config Generator

[![GitHub release](https://img.shields.io/github/v/release/daytonjones/eitr?sort=semver)](https://github.com/daytonjones/eitr/releases)
[![GitHub last commit](https://img.shields.io/github/last-commit/daytonjones/eitr)](https://github.com/daytonjones/eitr/commits/main)
[![GitHub issues](https://img.shields.io/github/issues/daytonjones/eitr)](https://github.com/daytonjones/eitr/issues)
[![License](https://img.shields.io/github/license/daytonjones/eitr)](https://github.com/daytonjones/eitr/blob/main/LICENSE)

---

## Introduction

- **E** — Environment: spanning cloud (AWS, Azure, GCP), local, and virtualised setups
- **I** — Infrastructure: focused on creating and managing critical infrastructure components
- **T** — Terraform: the de facto tool for infrastructure as code
- **R** — Renderer: dynamically generates Terraform configurations

**EITR** is a web application that simplifies Terraform configuration generation. Select providers and resources from the sidebar, edit the generated HCL templates inline with full syntax highlighting, and download the result as `.tf` or `.json`.

In Norse mythology, *eitr* is a primordial substance of raw creation — the perfect name for a tool that shapes infrastructure.

**Live demo:** https://eitr.gecko.org

---

## Features

- **33 official Terraform providers** — AWS, Azure, GCP, Kubernetes, Vault, Consul, and more; all schemas generated directly from the Terraform registry
- **Monaco editor** — full HCL/Terraform syntax highlighting, bracket matching, and line numbers for inline template editing
- **Template persistence** — edited templates are saved server-side (`templates/custom/`) and survive restarts; a "Reset to default" button restores the generated original
- **Dark / light theme** — toggle persisted to `localStorage`, defaults to dark
- **Resource search** — live cross-provider search with 250 ms debounce; click a result to select it directly
- **HCL and JSON export** — download the assembled configuration in either format; JSON export converts via `python-hcl2`
- **No server-side session state** — resource selection is stored in browser `localStorage`; only custom template edits are written to disk
- **Docker Compose** — single-command deployment

---

## Prerequisites

- Python 3.12+
- Terraform (for schema generation only)
- `jq` (for schema generation only)

---

## Quick start — Docker Compose

`config/provider_schemas.json` is not stored in the repo (it is ~180 MB). It must be generated locally before building the image.

```bash
git clone https://github.com/daytonjones/EITR.git
cd EITR

# One-time setup: generate provider schemas (requires terraform + jq on PATH)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python utilities/generate_tf_provider_templates.py

# Build and run
docker compose up --build
```

Open http://localhost:8085 in your browser.

The compose file maps host port **8085** → container port 8000.

---

## Local development

```bash
git clone https://github.com/daytonjones/EITR.git
cd EITR

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Generate provider schemas and Jinja2 templates (required before first run)
python utilities/generate_tf_provider_templates.py

uvicorn main:app --reload
```

Open http://localhost:8000 in your browser.

---

## Schema generation

`utilities/generate_tf_provider_templates.py` must be run:

- Before starting the app for the first time after a fresh clone
- After modifying `config/providers.json` (adding/removing/updating providers)

The script:

1. Writes a temporary `main.tf` from `config/providers.json`
2. Runs `terraform init` to download provider plugins (slow on first run)
3. Runs `terraform providers schema -json | jq .` and saves the output to `config/provider_schemas.json`
4. Generates Jinja2 template skeletons for every resource, data source, ephemeral resource, function, and provider-config block into `templates/terraform/{provider}/`

`config/provider_schemas.json` is gitignored (it is large); the generated templates in `templates/terraform/` are committed.

---

## Adding or updating providers

Edit `config/providers.json`. Each entry requires:

```json
{ "name": "aws", "description": "AWS (Amazon Web Services)", "version": "5.78.0" }
```

For providers not under the `hashicorp/` namespace, add a `source` field:

```json
{ "name": "vsphere", "description": "VMware vSphere", "version": "2.10.0", "source": "vmware/vsphere" }
```

Then re-run the generator.

---

## Usage

1. Open the app in your browser.
2. Use the sidebar to expand a provider and check the resources you need.
3. Use the search box to find a specific resource across all providers.
4. Click **Edit** on any resource card to edit its template in the Monaco editor.
5. Click **Save** to persist your edits to the server; a "customized" badge appears on the card.
6. Click **Reset to default** to restore the generated template.
7. Click **HCL** or **JSON** in the action bar to download the assembled configuration.
8. Click **Clear all** to deselect all resources (custom template edits are preserved).

---

## Project structure

```
EITR/
├── config/
│   └── providers.json           # Provider list (source of truth)
│   # provider_schemas.json      # Generated — gitignored
├── templates/
│   ├── index.html               # Single-page frontend
│   ├── terraform/               # Generated .tf.j2 skeletons (committed)
│   │   ├── aws/
│   │   ├── azurerm/
│   │   └── …
│   └── custom/                  # User-edited overrides (committed, volume-mounted)
├── static/
│   ├── eitr_background.jpeg
│   ├── eitr.ico
│   └── eitr.png
├── utilities/
│   └── generate_tf_provider_templates.py
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── CHANGELOG.md
```

---

## License

EITR is licensed under the MIT License. See `LICENSE` for details.
