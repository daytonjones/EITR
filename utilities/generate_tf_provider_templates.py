#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
This section will check for required modules and attempt to install them
========================== check for required modules ========================
'''
import os
import re
import subprocess
import sys

REQUIRED = ['colorama', 'jinja2']
EXIST = []
MISSING = []

for mod in REQUIRED:
    try:
        EXIST.append(__import__(mod))
    except ImportError as e:
        MISSING.append(mod)

os.system('clear')


def _install_required(MISSING):
    for mod in MISSING:
        try:
            subprocess.run(
                [
                    "python3", "-m",
                    "pip",
                    "install",
                    "--user",
                    "{}".format(mod)
                ], check=True
            )
            MISSING.remove(mod)
        except subprocess.CalledProcessError:
            print("Could not install {}\n".format(mod))


def _check_install(INSTALL):
    if INSTALL == 'retry':
        os.system('clear')
        print("You have missing modules that are required to run {}:\n\t{}\n".
              format(os.path.basename(__file__), MISSING))
        INSTALL = input("Shall I try to install them for you? (y/n) ")

    if INSTALL.lower() not in ['y', 'n']:
        print("Please enter either 'y' or 'n'")
        INSTALL = 'retry'
        _check_install(INSTALL)

    if INSTALL.lower() == 'y':
        _install_required(MISSING)
    elif INSTALL.lower() == 'n':
        print("exiting {}".format(os.path.basename(__file__)))
        sys.exit(0)


if len(MISSING) != 0:
    print("You have missing modules that are required to run {}:\n\t{}\n".
          format(os.path.basename(__file__), MISSING))
    INSTALL = input("Shall I try to install them for you? (y/n) ")
    _check_install(INSTALL)

if len(MISSING) != 0:
    print("There are still missing dependencies that I could not resolve, \
          please try to install them manually:\n\t", MISSING)
    sys.exit(1)

'''
======================= end check for required modules ========================

                    The "main" script
'''

import json
import shutil
from colorama import Fore
from jinja2 import Template

error_log = []

# Helper function to run shell commands
def run_command(command, cwd=None):
    """Helper function to run a shell command."""
    try:
        result = subprocess.run(command, shell=True, check=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode(), result.stderr.decode()
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Error occurred while running command: {Fore.YELLOW}{command}{Fore.RESET}")
        print(f"{Fore.BLUE}STDOUT:{Fore.RESET} {e.stdout.decode()}")
        print(f"{Fore.CYAN}STDERR:{Fore.RESET} {e.stderr.decode()}")
        return None, e.stderr.decode()

# Initialize Terraform in the given directory
def init_terraform(directory):
    print(f"{Fore.GREEN}Initializing Terraform in {Fore.LIGHTGREEN_EX}{directory}{Fore.GREEN}...{Fore.RESET}")
    return run_command("terraform init", cwd=directory)

# Create a simple main.tf file with provider configurations
def create_main_tf(directory, providers_file="config/providers.json"):
    """Create a main.tf file dynamically based on providers.json."""
    # Load providers from the JSON file
    if not os.path.exists(providers_file):
        raise FileNotFoundError(f"Providers file not found: {providers_file}")

    with open(providers_file, "r") as f:
        providers = json.load(f)

    # Generate the required_providers block
    required_providers = "\n".join(
        f"""        {provider["name"]} = {{
          source  = \"hashicorp/{provider['name']}\"
          version = \">= {provider['version']}\"
        }}"""
        for provider in providers
    )

    # Build the main.tf content
    main_tf_content = f"""
    terraform {{
      required_providers {{
{required_providers}
      }}
    }}
    """

    # Write the main.tf file
    main_tf_path = os.path.join(directory, "main.tf")
    with open(main_tf_path, "w") as f:
        f.write(main_tf_content.strip())
    print(f"{Fore.GREEN}Created main.tf in {Fore.LIGHTGREEN_EX}{directory}{Fore.RESET}")
    return main_tf_path

# Reinitialize Terraform after creating main.tf
def reinit_terraform(directory):
    print(f"{Fore.GREEN}Re-initializing Terraform...{Fore.RESET}")
    return run_command("terraform init", cwd=directory)

# Extract the Terraform provider schema and save it as JSON
def extract_terraform_schema(directory, output_file):
    print(f"{Fore.GREEN}Extracting provider schemas...{Fore.RESET}")
    command = "terraform providers schema -json | jq ."
    stdout, stderr = run_command(command, cwd=directory)
    if stdout:
        with open(output_file, "w") as f:
            f.write(stdout)
        print(f"{Fore.GREEN}Schema extracted to {Fore.LIGHTGREEN_EX}{output_file}{Fore.RESET}")
    else:
        print(f"{Fore.RED}Error extracting schema:{Fore.RESET} {stderr}")

# Set up Terraform and extract schema
def setup_terraform_schema(directory, output_file="config/provider_schemas.json"):
    """Set up Terraform, create main.tf, reinit, and extract schema."""
    stdout, stderr = init_terraform(directory)
    if stderr:
        print(f"{Fore.RED}Error initializing Terraform:{Fore.RESET} {stderr}")
        return
    create_main_tf(directory)
    stdout, stderr = reinit_terraform(directory)
    if stderr:
        print(f"{Fore.RED}Error reinitializing Terraform:{Fore.RESET} {stderr}")
        return
    extract_terraform_schema(directory, output_file)

# Process providers and generate templates
def resolve_missing_types(errors, schema):
    """Resolve missing types using the provider schema."""
    unresolved_errors = []
    for error in errors:
        provider_key = error["provider"]
        resource_name = error.get("resource") or error.get("data_source")
        attribute_name = error["attribute"]

        # Locate the resource or data source in the schema
        provider_schema = schema.get("provider_schemas", {}).get(provider_key, {})
        entity_schemas = provider_schema.get("resource_schemas", {}) if "resource" in error else provider_schema.get("data_source_schemas", {})
        entity_schema = entity_schemas.get(resource_name, {})
        attributes = entity_schema.get("block", {}).get("attributes", {})

        # Attempt to resolve the type
        attribute_schema = attributes.get(attribute_name, {})
        resolved_type = attribute_schema.get("type")

        if resolved_type:
            print(f"{Fore.GREEN}Resolved type for {Fore.YELLOW}{resource_name}.{attribute_name}: {Fore.CYAN}{resolved_type}{Fore.RESET}")
            error["resolved_type"] = resolved_type
        else:
            print(f"{Fore.RED}Unresolved type for {Fore.YELLOW}{resource_name}.{attribute_name}{Fore.RESET}")
            unresolved_errors.append(error)

    return unresolved_errors


def process_provider(schema, provider_key, template_dir):
    """Process a specific provider to generate templates."""
    provider_schema = schema["provider_schemas"].get(provider_key, {})
    resources = provider_schema.get("resource_schemas", {})
    data_sources = provider_schema.get("data_source_schemas", {})

    print(f"\n{Fore.GREEN}Processing {Fore.BLUE}{provider_key}{Fore.GREEN}: Found {Fore.MAGENTA}{len(resources)}{Fore.GREEN} resources and {Fore.MAGENTA}{len(data_sources)}{Fore.GREEN} data sources.{Fore.RESET}")

    # Create provider-specific directory
    os.makedirs(template_dir, exist_ok=True)

    # Define Jinja templates
    resource_template = Template(
        """\
resource "{{ resource_type }}" "{{ resource_name }}" {
    {% for attribute, details in attributes.items() %}
    {{ attribute }} = "{{ details['type_var'] }}"
    {% endfor %}
}
""", trim_blocks=True, lstrip_blocks=True
    )

    data_source_template = Template(
        """\
# {{ data_type }}-data.tf.j2
data "{{ data_type }}" "{{ data_name }}" {
    {% for attribute, details in attributes.items() %}
    {{ attribute }} = "{{ details['type_var'] }}"
    {% endfor %}
}
""", trim_blocks=True, lstrip_blocks=True
    )

    # Helper to convert attribute types to template variables, handling nested types
    def convert_to_template_variable(attribute_details, key=None):
        if "type" in attribute_details:  # Normal attribute with a type
            return f"{{{{ {key} }}}}"
        elif "nested_type" in attribute_details:  # Handle nested attributes
            nested_attributes = attribute_details["nested_type"].get("attributes", {})
            nested_template = []
            for nested_key, nested_details in nested_attributes.items():
                nested_value = convert_to_template_variable(nested_details, nested_key)
                nested_template.append(f"    {nested_key} = {nested_value}")
            return "{\n" + "\n".join(nested_template) + "\n}"
        else:  # Fallback for unsupported cases
            return f"{{{{ unsupported_{key} }}}}"
    
    # Updated logic for resource templates
    for resource_name, resource_details in resources.items():
        attributes = resource_details["block"].get("attributes", {})
        for attribute, details in attributes.items():
            try:
                details["type_var"] = convert_to_template_variable(details, attribute)
            except KeyError as e:
                error_message = {
                    "provider": provider_key,
                    "resource": resource_name,
                    "attribute": attribute,
                    "error": str(e),
                }
                error_log.append(error_message)
                details["type_var"] = f"{{{{ unsupported_{attribute} }}}}"
    
        rendered_resource = resource_template.render(
            resource_type=resource_name,
            resource_name="example",
            attributes=attributes,
        )
        write_template_to_file(os.path.join(template_dir, f"{resource_name}-resource.tf.j2"), rendered_resource)
    
    
    # Generate data source templates
    # Generate data source templates
    for data_name, data_details in data_sources.items():
        attributes = data_details["block"].get("attributes", {})
        for attribute, details in attributes.items():
            try:
                # Use the updated convert_to_template_variable function
                details["type_var"] = convert_to_template_variable(details, attribute)
            except KeyError:
                error_message = {
                    "provider": provider_key,
                    "data_source": data_name,
                    "attribute": attribute,
                    "error": "Missing 'type' key"
                }
                error_log.append(error_message)
                details["type_var"] = f"{{{{ unsupported_{attribute} }}}}"
    
        rendered_data_source = data_source_template.render(
            data_type=data_name,
            data_name="example",
            attributes=attributes,
        )
        write_template_to_file(os.path.join(template_dir, f"{data_name}-data.tf.j2"), rendered_data_source)
    

# Write errors to a file
def write_errors_to_file(errors, file_path="errors.json"):
    """Write the collected errors to a JSON or text file."""
    with open(file_path, "w") as f:
        json.dump(errors, f, indent=4)
    print(f"\nErrors have been logged to {file_path}")

# Write a template to a file
def write_template_to_file(file_path, template_content):
    with open(file_path, "w") as f:
        f.write(template_content)
        print(f"\t{Fore.LIGHTBLUE_EX}{file_path}{Fore.LIGHTGREEN_EX} created{Fore.RESET}")

# Main execution
working_directory = "tf_temp"
os.makedirs(working_directory, exist_ok=True)
setup_terraform_schema(working_directory)

# Load provider schema JSON
with open("config/provider_schemas.json", "r") as f:
    schema = json.load(f)

# Dynamically construct providers dictionary from schema
providers = {
    provider_key: os.path.join("templates/terraform/", provider_key.split("/")[-1])
    for provider_key in schema.get("provider_schemas", {}).keys()
}

print(f"{Fore.GREEN}Found {Fore.MAGENTA}{len(providers)}{Fore.GREEN} providers. Processing all providers...{Fore.RESET}")

for provider_key, template_dir in providers.items():
    process_provider(schema, provider_key, template_dir)

# Write errors to errors.json
if error_log:
    write_errors_to_file(error_log)

# Remove the temporary directory
shutil.rmtree(working_directory)
#print(f"\n{Fore.GREEN}Temporary directory {Fore.BLUE}{working_directory}{Fore.GREEN} has been removed.{Fore.RESET}\n")

