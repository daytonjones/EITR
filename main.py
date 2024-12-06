from datetime import datetime
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from textwrap import dedent
import hcl2
import io
import json
import os

app = FastAPI()

# Static files and templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load provider and resource configurations
with open("config/providers.json") as f:
    PROVIDERS = json.load(f)
with open("config/provider_schemas.json") as f:
    SCHEMAS = json.load(f)

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    providers_with_resource_names = []

    # List of keys to include in the response
    schema_keys = [
        "provider",
        "data_source_schemas",
        "ephemeral_resource_schemas",
        "functions",
        "resource_schemas",
    ]

    # Combine providers and their schemas into one structured object
    for provider in PROVIDERS:
        provider_name = provider["name"]
        provider_key = f"registry.terraform.io/hashicorp/{provider_name}"

        # Extract data for each schema key
        schema_data = {}
        for key in schema_keys:
            schema_data[key] = sorted(list(SCHEMAS["provider_schemas"].get(provider_key, {}).get(key, {}).keys()))

        providers_with_resource_names.append({
            "name": provider_name,
            "description": provider["description"],
            "schemas": schema_data
        })

    total_providers = len(providers_with_resource_names)
    total_resources = sum(len(provider["schemas"]["resource_schemas"]) for provider in providers_with_resource_names)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "providers": providers_with_resource_names,
        "total_providers": total_providers,
        "total_resources": total_resources
    })

@app.get("/load_templates/{provider}/{schema_type}/{resource}", response_class=JSONResponse)
async def load_templates(provider: str, schema_type: str, resource: str):
    templates_path = f"templates/terraform/{provider}/"
    template_file = ""

    # Determine the template file based on schema type
    if schema_type == "provider":
        template_file = os.path.join(templates_path, "provider.tf.j2")
    else:
        template_file = os.path.join(templates_path, f"{resource}-{schema_type}.tf.j2")

    if os.path.exists(template_file):
        with open(template_file, "r") as f:
            template_content = f.read()
        return JSONResponse(content={schema_type: template_content})
    else:
        return JSONResponse(content={schema_type: "No template found"}, status_code=404)

@app.post("/generate", response_class=HTMLResponse)
async def generate_terraform_config(
    request: Request,
    enabled_providers: str = Form(...),
    resources: str = Form(...),
    options: str = Form(...)
):
    selected_providers = json.loads(enabled_providers)
    selected_resources = json.loads(resources)
    resource_options = json.loads(options)

    terraform_config = []
    for provider in selected_providers:
        provider_resources = selected_resources.get(provider, {})
        for resource, opts in provider_resources.items():
            template_file = f"templates/terraform/{provider}_{resource}.tf.j2"
            if os.path.exists(template_file):
                rendered = templates.TemplateResponse(
                    f"terraform/{provider}_{resource}.tf.j2",
                    {"request": request, "options": opts}
                )
                terraform_config.append(rendered.body.decode())

    full_config = "\n\n".join(terraform_config)

#    now = datetime.now()
#    timestamp = now.strftime("%m%d%Y%H%M")

    # Save HCL file with simple formatting
    hcl_file_path = os.path.join(config_dir, f"main_{timestamp}.tf")
    pretty_hcl = "\n".join(line.strip() for line in full_config.splitlines() if line.strip())
    with open(hcl_file_path, "w") as f:
        f.write(pretty_hcl)

    # Save JSON file with pretty formatting
    json_file_path = os.path.join(config_dir, f"main_{timestamp}.json")
    with open(json_file_path, "w") as f:
        json.dump({"terraform_config": full_config}, f, indent=4)  # Pretty print JSON

    return templates.TemplateResponse("index.html", {
        "request": request,
        "providers": PROVIDERS,
        "resources": RESOURCES,
        "terraform_config": full_config,
        "download_ready": True,  # Add a flag to indicate config is ready
    })
#        "timestamp": timestamp,  # Pass the timestamp for download links

@app.post("/save_config/{format}", response_class=JSONResponse)
async def save_terraform_config(format: str, config: dict = Body(...)):
    now = datetime.now()
    timestamp = now.strftime("%m%d%Y%H%M")

    # Extract the configuration
    full_config = config.get("config", "").strip()
    if not full_config:
        return JSONResponse(
            status_code=400,
            content={"error": "No configuration provided."},
        )

    if format == "json":
        try:
            # Use hcl2 to parse the HCL string into a Python dictionary
            hcl_stream = io.StringIO(full_config)
            hcl_data = hcl2.load(hcl_stream)

            # Convert the HCL dictionary into pretty-printed JSON
            pretty_json = json.dumps(hcl_data, indent=4)

            return JSONResponse(
                content={"config": pretty_json},
                headers={
                    "Content-Disposition": f"attachment; filename=generated_terraform_{timestamp}.json"
                },
            )
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to parse HCL to JSON: {str(e)}"},
            )

    elif format == "hcl":
        # Format HCL manually by dedenting and cleaning extra spaces
        pretty_hcl = dedent(full_config).strip()
        return JSONResponse(
            content={"config": pretty_hcl},
            headers={
                "Content-Disposition": f"attachment; filename=generated_terraform_{timestamp}.tf"
            },
        )

    return JSONResponse(
        status_code=400,
        content={"error": "Unsupported format. Please choose 'json' or 'hcl'."},
    )

