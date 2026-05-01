# Changelog

All notable changes to EITR are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — v2.0.0

### Added
- Monaco Editor (v0.52) with a custom HCL/Terraform language tokenizer: keyword, string, comment, jinja2-variable, heredoc, attribute, bracket, operator, and number token types; two custom themes (`eitr-dark`, `eitr-light`) tuned to GitHub-style palettes
- Dark/light theme toggle persisted to `localStorage`; defaults to dark
- CSS custom property token system (`--bg`, `--surface`, `--raised`, `--border`, `--text`, `--muted`, `--gold`, `--code-fg`) for correct single-class theme switching
- Schema-type color badges per card (Resources=blue, Data Sources=teal, Ephemeral=orange, Functions=pink, Provider=purple)
- Two-letter colour-coded avatar for each provider in the sidebar
- Mobile sidebar drawer with hamburger toggle and backdrop overlay
- `docker-compose.yml` — single-command deployment, maps host port 8085 to container 8000
- Volume mount for `templates/custom/` so edited templates survive container restarts
- `GET /load_template/{provider}/{schema_type}/{resource}` — loads template with custom overlay support; returns `is_custom` flag
- `POST /save_template` — persists user-edited templates to `templates/custom/` on the server
- `DELETE /reset_template/{provider}/{schema_type}/{resource}` — removes custom override, restoring generated default
- `GET /search?q=` — live resource search across all providers (min 2 chars, capped at 100 results)
- Search box in sidebar with 250 ms debounce and click-to-select results
- "Customized" badge on template blocks that have been edited
- "Reset to default" button on customized templates
- "Cancel" button to discard in-progress edits
- Empty-state message when no resources are selected
- Provider resource counts in sidebar
- Proper readable labels for schema types (Resources, Data Sources, Ephemeral Resources, Functions, Provider Config)
- Checkbox state is now restored on page reload from localStorage
- Confirmation dialog before clearing config

### Changed
- Backend rewritten with Pydantic request models and `pathlib.Path` throughout
- `TemplateResponse` updated to current Starlette keyword-argument API
- `SCHEMA_KEYS` ordering reordered: provider → resources → data sources → ephemeral → functions
- Save-buttons now shown/hidden via `classList` (fixes flex-vs-block layout bug)
- Checkbox events handled via delegation on `<nav>` — eliminates the clone-and-reattach listener pattern
- `/save_config` response now includes `filename` field used for the download
- Deprecated `<center>` tag replaced with Flexbox
- HCL save button now appears before JSON (HCL is the primary format)

### Removed
- Dead `/generate` endpoint (wrong template path convention, never called by frontend)
- Dead `/update_config` server-side endpoint (config was localStorage-only; server `ConfigManager` never used)
- Dead `/get_current_config` endpoint
- Stub `/update_template` endpoint (said "mock update for demonstration" in a comment — replaced by working `/save_template`)
- `ConfigManager` class (unused server-side state)
- Fragile `checkbox.name.split("_")[1]` schema-type extraction — replaced with `data-schema-type` attribute

### Fixed
- Template edits were silently discarded on page refresh (now persisted server-side)
- Schema type labels showed raw keys (`resource_schemas`, `data_source_schemas`) instead of readable names
- `saveButtons.style.display = "block"` broke flex layout — now uses classList
- `schemaType` extraction via `split("_")[1]` was fragile and would silently mismatch for multi-word types
- Checkbox states not restored on page reload (selections appeared in config display but boxes were unchecked)
- `hcl2.load` import corrected to `from hcl2 import load` (resolves Pyright reportPrivateImportUsage)

---

## [1.0.0] — Initial release

- FastAPI backend serving a single-page Terraform config generator
- 35 Hashicorp providers with schemas generated via `terraform providers schema -json`
- Jinja2 templates for resources, data sources, ephemeral resources, functions, and provider config
- Alpine.js + Tailwind CSS frontend
- localStorage-based config persistence
- HCL and JSON export
- Inline template editing (ephemeral — edits lost on refresh)
