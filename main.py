from datetime import datetime
from pathlib import Path
from hcl2.api import load as hcl_load
import io
import json
import re
import sys

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="EITR")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TEMPLATES_DIR = Path("templates/terraform")

with open("config/providers.json") as f:
    PROVIDERS = json.load(f)

try:
    with open("config/provider_schemas.json") as f:
        SCHEMAS = json.load(f)
except FileNotFoundError:
    sys.exit(
        "\nERROR: config/provider_schemas.json not found.\n"
        "Generate it first:\n"
        "  python utilities/generate_tf_provider_templates.py\n"
    )

SCHEMA_KEYS = [
    "provider",
    "resource_schemas",
    "data_source_schemas",
    "ephemeral_resource_schemas",
    "functions",
]

SCHEMA_SUFFIX = {
    "provider":                   "provider",
    "resource_schemas":           "resource",
    "data_source_schemas":        "data",
    "ephemeral_resource_schemas": "ephemeral",
    "functions":                  "functions",
}


def _template_filename(schema_type: str, resource: str) -> str:
    if schema_type == "provider":
        return "provider.tf.j2"
    return f"{resource}-{SCHEMA_SUFFIX.get(schema_type, schema_type)}.tf.j2"


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    providers_data = []
    for p in PROVIDERS:
        psrc = p.get("source") or f"hashicorp/{p['name']}"
        pkey = f"registry.terraform.io/{psrc}"
        pschema = SCHEMAS["provider_schemas"].get(pkey, {})
        schemas = {k: sorted(pschema.get(k, {}).keys()) for k in SCHEMA_KEYS}
        providers_data.append({
            "name": p["name"],
            "description": p["description"],
            "schemas": schemas,
        })

    total_resources = sum(len(p["schemas"]["resource_schemas"]) for p in providers_data)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "providers": providers_data,
            "total_providers": len(providers_data),
            "total_resources": total_resources,
            "provider_meta": {
                p["name"]: {
                    "source":  p.get("source") or f"hashicorp/{p['name']}",
                    "version": p["version"],
                }
                for p in PROVIDERS
            },
        },
    )


@app.get("/load_template/{provider}/{schema_type}/{resource}")
async def load_template(provider: str, schema_type: str, resource: str):
    path = TEMPLATES_DIR / provider / _template_filename(schema_type, resource)
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "Template not found"})
    return {"content": path.read_text()}


class SaveConfigRequest(BaseModel):
    config: str


@app.post("/save_config/{format}")
async def save_config(format: str, body: SaveConfigRequest):
    content = body.config.strip()
    if not content:
        return JSONResponse(status_code=400, content={"error": "No configuration provided"})

    timestamp = datetime.now().strftime("%m%d%Y%H%M")

    if format == "hcl":
        return {"config": content, "filename": f"terraform_{timestamp}.tf"}

    if format == "json":
        try:
            # Unquoted Jinja2 placeholders (booleans/numbers like `{{ enabled }}`) aren't
            # valid HCL; replace with a string sentinel before parsing.
            # Quoted ones ("{{ ami }}") are already valid HCL string literals.
            sanitized = re.sub(r'(?<!")\{\{\s*[\w_]+\s*\}\}(?!")', '"TODO"', content)
            data = hcl_load(io.StringIO(sanitized))
            return {"config": json.dumps(data, indent=2), "filename": f"terraform_{timestamp}.json"}
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"HCL parse error: {e}"})

    return JSONResponse(status_code=400, content={"error": "Format must be 'hcl' or 'json'"})


@app.get("/search")
async def search(q: str = ""):
    if len(q) < 2:
        return {"results": []}

    q_lower = q.lower()
    exact, starts, contains = [], [], []

    for p in PROVIDERS:
        psrc = p.get("source") or f"hashicorp/{p['name']}"
        pkey = f"registry.terraform.io/{psrc}"
        pschema = SCHEMAS["provider_schemas"].get(pkey, {})
        for key in SCHEMA_KEYS:
            for item in pschema.get(key, {}).keys():
                item_lower = item.lower()
                entry = {"provider": p["name"], "schema_type": key, "resource": item}
                if item_lower == q_lower:
                    exact.append(entry)
                elif item_lower.startswith(q_lower):
                    starts.append(entry)
                elif q_lower in item_lower:
                    contains.append(entry)

    results = (
        sorted(exact,    key=lambda x: x["resource"]) +
        sorted(starts,   key=lambda x: x["resource"]) +
        sorted(contains, key=lambda x: x["resource"])
    )
    return {"results": results[:100]}
