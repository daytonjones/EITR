from datetime import datetime
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import hcl2
import io
import json
import os
from textwrap import dedent

app = FastAPI()

# Static files and templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load provider and resource configurations
with open("config/providers.json") as f:
    PROVIDERS = json.load(f)
with open("config/provider_schemas.json") as f:
    SCHEMAS = json.load(f)

# ConfigManager class for in-memory state management
class ConfigManager:
    def __init__(self):
        self.config = {}

    def update_config(self, provider, schema_type, resource, action):
        """Update in-memory configuration based on user actions."""
        if action == "add":
            self.config.setdefault(provider, {}).setdefault(schema_type, [])
            if resource not in self.config[provider][schema_type]:
                self.config[provider][schema_type].append(resource)
        elif action == "remove":
            if provider in self.config and schema_type in self.config[provider]:
                if resource in self.config[provider][schema_type]:
                    self.config[provider][schema_type].remove(resource)
                if not self.config[provider][schema_type]:
                    del self.config[provider][schema_type]
                if not self.config[provider]:
                    del self.config[provider]

    def get_ordered_config(self):
        """Return the current configuration ordered by provider and schema type."""
        ordered_config = {}
        for provider in sorted(self.config.keys()):
            ordered_config[provider] = {}
            for schema_type in sorted(self.config[provider].keys()):
                items = self.config[provider][schema_type]
                if schema_type == "provider":
                    ordered_config[provider][schema_type] = items
                else:
                    ordered_config[provider][schema_type] = sorted(items)
        return ordered_config

config_manager = ConfigManager()

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

@app.post("/update_config")
async def update_config(request: Request):
    """Update in-memory configuration and return updated structure."""
    try:
        # Parse the incoming JSON body
        data = await request.json()
        
        # Extract necessary fields from the JSON body
        provider = data.get("provider")
        schema_type = data.get("schema_type")
        resource = data.get("resource")
        action = data.get("action")

        # Validate that all necessary fields are provided
        if not all([provider, schema_type, resource, action]):
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields"}
            )

        # Update the in-memory configuration
        config_manager.update_config(provider, schema_type, resource, action)

        # Return the updated configuration
        return {"config": config_manager.get_ordered_config()}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal Server Error: {str(e)}"}
        )

@app.get("/get_current_config")
async def get_current_config():
    """Return the current configuration without modifying it."""
    return {"config": config_manager.get_ordered_config()}

@app.get("/load_templates/{provider}/{schema_type}/{resource}", response_class=JSONResponse)
async def load_templates(provider: str, schema_type: str, resource: str):
    """Load templates for selected resources."""
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
    """Generate Terraform configuration based on selected resources."""
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

    return templates.TemplateResponse("index.html", {
        "request": request,
        "providers": PROVIDERS,
        "resources": SCHEMAS,
        "terraform_config": full_config,
        "download_ready": True,
    })

@app.post("/save_config/{format}", response_class=JSONResponse)
async def save_terraform_config(format: str, config: dict = Body(...)):
    """Save Terraform configuration in the specified format."""
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
            hcl_stream = io.StringIO(full_config)
            hcl_data = hcl2.load(hcl_stream)
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

@app.post("/reset_config")
async def reset_config():
    """Reset the in-memory configuration."""
    config_manager.config.clear()
    return {"message": "Configuration reset successfully"}

