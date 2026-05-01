from datetime import datetime
from pathlib import Path
from hcl2.api import load as hcl_load
import io
import json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="EITR")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

TEMPLATES_DIR = Path("templates/terraform")
CUSTOM_DIR = Path("templates/custom")
CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

with open("config/providers.json") as f:
    PROVIDERS = json.load(f)
with open("config/provider_schemas.json") as f:
    SCHEMAS = json.load(f)

SCHEMA_KEYS = [
    "provider",
    "resource_schemas",
    "data_source_schemas",
    "ephemeral_resource_schemas",
    "functions",
]

# Maps full schema key -> file suffix used in template filenames
SCHEMA_SUFFIX = {
    "provider": "provider",
    "resource_schemas": "resource",
    "data_source_schemas": "data",
    "ephemeral_resource_schemas": "ephemeral",
    "functions": "functions",
}


def _template_filename(schema_type: str, resource: str) -> str:
    if schema_type == "provider":
        return "provider.tf.j2"
    suffix = SCHEMA_SUFFIX.get(schema_type, schema_type)
    return f"{resource}-{suffix}.tf.j2"


def _resolve_template(provider: str, schema_type: str, resource: str) -> tuple[str | None, bool]:
    """Return (content, is_custom). Checks custom overlay first, then generated."""
    filename = _template_filename(schema_type, resource)
    for path, is_custom in [
        (CUSTOM_DIR / provider / filename, True),
        (TEMPLATES_DIR / provider / filename, False),
    ]:
        if path.exists():
            return path.read_text(), is_custom
    return None, False


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
        },
    )


@app.get("/load_template/{provider}/{schema_type}/{resource}")
async def load_template(provider: str, schema_type: str, resource: str):
    content, is_custom = _resolve_template(provider, schema_type, resource)
    if content is None:
        return JSONResponse(status_code=404, content={"error": "Template not found"})
    return {"content": content, "is_custom": is_custom}


class SaveTemplateRequest(BaseModel):
    provider: str
    schema_type: str
    resource: str
    content: str


@app.post("/save_template")
async def save_template(body: SaveTemplateRequest):
    filename = _template_filename(body.schema_type, body.resource)
    dest = CUSTOM_DIR / body.provider / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body.content)
    return {"message": "Template saved"}


@app.delete("/reset_template/{provider}/{schema_type}/{resource}")
async def reset_template(provider: str, schema_type: str, resource: str):
    filename = _template_filename(schema_type, resource)
    custom = CUSTOM_DIR / provider / filename
    if custom.exists():
        custom.unlink()
    return {"message": "Reset to default"}


class SaveConfigRequest(BaseModel):
    config: str


@app.post("/save_config/{format}")
async def save_config(format: str, body: SaveConfigRequest):
    content = body.config.strip()
    if not content:
        return JSONResponse(status_code=400, content={"error": "No configuration provided"})

    timestamp = datetime.now().strftime("%m%d%Y%H%M")

    if format == "hcl":
        return {
            "config": content,
            "filename": f"terraform_{timestamp}.tf",
        }

    if format == "json":
        try:
            data = hcl_load(io.StringIO(content))
            return {
                "config": json.dumps(data, indent=2),
                "filename": f"terraform_{timestamp}.json",
            }
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"HCL parse error: {e}"})

    return JSONResponse(status_code=400, content={"error": "Format must be 'hcl' or 'json'"})


@app.get("/search")
async def search(q: str = ""):
    if len(q) < 2:
        return {"results": []}

    q_lower = q.lower()
    results = []
    for p in PROVIDERS:
        psrc = p.get("source") or f"hashicorp/{p['name']}"
        pkey = f"registry.terraform.io/{psrc}"
        pschema = SCHEMAS["provider_schemas"].get(pkey, {})
        for key in SCHEMA_KEYS:
            for item in pschema.get(key, {}).keys():
                if q_lower in item.lower():
                    results.append({
                        "provider": p["name"],
                        "schema_type": key,
                        "resource": item,
                    })
        if len(results) >= 100:
            break

    return {"results": results[:100]}
