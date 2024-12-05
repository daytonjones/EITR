from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
    # Parse submitted form data
    selected_providers = json.loads(enabled_providers)  # List of enabled providers
    selected_resources = json.loads(resources)  # Dictionary of resources per provider
    resource_options = json.loads(options)  # Resource-specific options
    
    terraform_config = []

    # Generate Terraform configurations for selected providers and resources
    for provider in selected_providers:
        provider_resources = selected_resources.get(provider, {})
        for resource, opts in provider_resources.items():
            template_file = f"templates/terraform/{provider}_{resource}.tf.j2"
            if os.path.exists(template_file):
                # Render the resource template with provided options
                rendered = templates.TemplateResponse(
                    f"terraform/{provider}_{resource}.tf.j2",
                    {"request": request, "options": opts}
                )
                terraform_config.append(rendered.body.decode())

    # Combine rendered templates into a single Terraform file
    full_config = "\n\n".join(terraform_config)
    config_file_path = "output/main.tf"
    os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
    with open(config_file_path, "w") as f:
        f.write(full_config)

    # Respond with the generated configuration displayed on the index page
    return templates.TemplateResponse("index.html", {
        "request": request,
        "providers": PROVIDERS,
        "resources": RESOURCES,
        "terraform_config": full_config
    })

