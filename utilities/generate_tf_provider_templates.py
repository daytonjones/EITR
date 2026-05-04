#!/usr/bin/env python3
"""
EITR schema generator.

Downloads provider schemas from the Terraform registry and generates
Jinja2 template skeletons for every resource, data source, ephemeral
resource, function, and provider-config block.

Requirements: terraform and jq must be on PATH.
Run from the repo root:
    python utilities/generate_tf_provider_templates.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROVIDERS_FILE = Path("config/providers.json")
SCHEMA_FILE    = Path("config/provider_schemas.json")
TEMPLATE_DIR   = Path("templates/terraform")
TF_TIMEOUT     = 600   # seconds — provider downloads can be slow


# ── Provider helpers ──────────────────────────────────────────────────────────

def provider_source(p: dict) -> str:
    """registry source string, e.g. 'hashicorp/aws' or 'vmware/vsphere'."""
    return p.get("source", f"hashicorp/{p['name']}")


def registry_key(p: dict) -> str:
    """Key used in provider_schemas JSON output."""
    return f"registry.terraform.io/{provider_source(p)}"


# ── Template rendering ────────────────────────────────────────────────────────

def _type_placeholder(name: str, type_def) -> str:
    """Return a Jinja2 placeholder appropriate for the attribute type."""
    if isinstance(type_def, list):
        outer = type_def[0] if type_def else "string"
        if outer in ("list", "set"):
            return f'["{{{{ {name} }}}}"]'
        if outer == "map":
            return f'{{\n        key = "{{{{ {name}_value }}}}"\n      }}'
        # object / tuple — treat as opaque
        return f'{{{{ {name} }}}}'
    # primitive
    if type_def == "bool":
        return f'{{{{ {name} }}}}'
    if type_def == "number":
        return f'{{{{ {name} }}}}'
    # string or unknown
    return f'"{{{{ {name} }}}}"'


def _render_block(block: dict, indent: int = 2) -> str:
    """
    Recursively render a Terraform block schema as template text.
    Skips purely computed attributes (read-only, set by Terraform).
    """
    pad    = "  " * indent
    lines  = []

    # Flat attributes
    for attr, details in sorted(block.get("attributes", {}).items()):
        computed = details.get("computed", False)
        optional = details.get("optional", False)
        required = details.get("required", False)
        # Skip attributes the user can never set (read-only outputs like id, arn)
        if computed and not optional and not required:
            continue
        placeholder = _type_placeholder(attr, details.get("type"))
        lines.append(f"{pad}{attr} = {placeholder}")

    # Nested blocks
    for bname, bdef in sorted(block.get("block_types", {}).items()):
        inner   = bdef.get("block", {})
        nesting = bdef.get("nesting_mode", "list")
        body    = _render_block(inner, indent + 1)

        if nesting == "map":
            lines.append(f"{pad}{bname} {{")
            lines.append(f"{pad}  # Replace 'key' with the actual map key")
            lines.append(f"{'  ' * (indent + 1)}key = {{")
            if body:
                lines.append(body)
            lines.append(f"{'  ' * (indent + 1)}}}")
            lines.append(f"{pad}}}")
        else:
            lines.append(f"{pad}{bname} {{")
            if body:
                lines.append(body)
            lines.append(f"{pad}}}")

    return "\n".join(lines)


def _resource_template(rtype: str, block: dict) -> str:
    body = _render_block(block)
    return f'resource "{rtype}" "example" {{\n{body}\n}}\n'


def _data_template(dtype: str, block: dict) -> str:
    body = _render_block(block)
    return f'data "{dtype}" "example" {{\n{body}\n}}\n'


def _ephemeral_template(etype: str, block: dict) -> str:
    body = _render_block(block)
    return f'ephemeral "{etype}" "example" {{\n{body}\n}}\n'


def _provider_template(pname: str, block: dict) -> str:
    body = _render_block(block)
    return f'provider "{pname}" {{\n{body}\n}}\n'


def _function_template(fname: str, fdef: dict) -> str:
    """Functions aren't HCL blocks; emit a call-signature comment stub."""
    params = [p.get("name", f"arg{i}") for i, p in enumerate(fdef.get("params", []))]
    vp = fdef.get("variadic_param")
    if vp:
        params.append(f'{vp.get("name", "args")}...')
    sig = ", ".join(f"{{{{ {p} }}}}" for p in params)
    desc = fdef.get("description", "").split("\n")[0]
    lines = [f"# {fname}({sig})"]
    if desc:
        lines.append(f"# {desc}")
    lines.append(f"# provider::{{provider}}::{fname}({sig})")
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ── Terraform helpers ─────────────────────────────────────────────────────────

def _run(cmd: str, cwd=None, timeout: int = 120) -> tuple[str, str, int]:
    r = subprocess.run(
        cmd, shell=True, cwd=cwd, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return r.stdout.decode(), r.stderr.decode(), r.returncode


def _build_main_tf(providers: list[dict]) -> str:
    blocks = []
    for p in providers:
        src = provider_source(p)
        blocks.append(
            f'    {p["name"]} = {{\n'
            f'      source  = "{src}"\n'
            f'      version = ">= {p["version"]}"\n'
            f'    }}'
        )
    return (
        "terraform {\n"
        "  required_providers {\n"
        + "\n".join(blocks) +
        "\n  }\n"
        "}\n"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("EITR — Terraform schema generator")
    print("=" * 50)

    if not PROVIDERS_FILE.exists():
        sys.exit(f"ERROR: {PROVIDERS_FILE} not found. Run from the repo root.")

    providers: list[dict] = json.loads(PROVIDERS_FILE.read_text())
    print(f"Loaded {len(providers)} providers from {PROVIDERS_FILE}\n")

    # ── Step 1: terraform init + schema extraction ────────────────────────
    with tempfile.TemporaryDirectory(prefix="eitr_tf_") as tmp:
        tmpdir = Path(tmp)
        (tmpdir / "main.tf").write_text(_build_main_tf(providers))

        print("[1/3] Running terraform init  (provider downloads may take a while)…")
        stdout, stderr, rc = _run("terraform init -no-color", cwd=tmpdir, timeout=TF_TIMEOUT)

        if rc != 0:
            # Surface any hard errors clearly before aborting
            for line in stderr.splitlines():
                if "Error" in line:
                    print(f"  {line.strip()}")
            sys.exit(
                "\nERROR: terraform init failed. Fix the errors above and retry.\n"
                "Common causes: provider not in registry, network issue.\n"
                "Check config/providers.json for incorrect 'source' values."
            )

        # Surface non-fatal warnings (e.g. moved providers)
        for line in stderr.splitlines():
            if "Warning" in line or "moved" in line.lower():
                print(f"  WARN: {line.strip()}")

        print("\n[2/3] Extracting provider schemas…")
        stdout, stderr, rc = _run(
            "terraform providers schema -json | jq .",
            cwd=tmpdir, timeout=120,
        )

        if rc != 0 or not stdout.strip():
            sys.exit(f"ERROR: schema extraction failed:\n{stderr}")

        SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA_FILE.write_text(stdout)
        size_kb = len(stdout) // 1024
        print(f"  Saved {size_kb:,} KB to {SCHEMA_FILE}")

    # ── Step 2: generate templates ────────────────────────────────────────
    schema_data = json.loads(SCHEMA_FILE.read_text())
    all_schemas = schema_data.get("provider_schemas", {})

    print(f"\n[3/3] Generating templates → {TEMPLATE_DIR}/")

    total = 0
    for p in providers:
        key     = registry_key(p)
        pschema = all_schemas.get(key, {})

        if not pschema:
            print(f"  {'SKIP':6s}  {p['name']} — no schema (provider may not have initialized)")
            continue

        tdir = TEMPLATE_DIR / p["name"]
        count = 0

        for rname, rdef in pschema.get("resource_schemas", {}).items():
            _write(tdir / f"{rname}-resource.tf.j2",
                   _resource_template(rname, rdef.get("block", {})))
            count += 1

        for dname, ddef in pschema.get("data_source_schemas", {}).items():
            _write(tdir / f"{dname}-data.tf.j2",
                   _data_template(dname, ddef.get("block", {})))
            count += 1

        for ename, edef in pschema.get("ephemeral_resource_schemas", {}).items():
            _write(tdir / f"{ename}-ephemeral.tf.j2",
                   _ephemeral_template(ename, edef.get("block", {})))
            count += 1

        for fname, fdef in pschema.get("functions", {}).items():
            _write(tdir / f"{fname}-functions.tf.j2",
                   _function_template(fname, fdef))
            count += 1

        pb = pschema.get("provider", {}).get("block", {})
        if pb:
            _write(tdir / "provider.tf.j2",
                   _provider_template(p["name"], pb))
            count += 1

        total += count
        print(f"  {'OK':6s}  {p['name']:20s}  {count:5d} templates")

    print(f"\nDone — {total:,} templates written.")


if __name__ == "__main__":
    main()
