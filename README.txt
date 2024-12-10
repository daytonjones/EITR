EITR - Multi-Provider Terraform Config Generator

Introduction
E: Environment – Spanning cloud (AWS, Azure, GCP), local, and virtualized setups.
I: Infrastructure – Focused on creating and managing critical infrastructure components.
T: Terraform – The de facto tool for infrastructure as code.
R: Renderer – A system for dynamically generating Terraform configurations.

EITR is a web-based application designed to simplify and streamline Terraform configuration generation. It allows users to dynamically select multiple providers and resources, and then generate ready-to-use Terraform templates with minimal effort.

In Norse mythology, eitr represents raw potential and creation, making it the perfect name for a tool that shapes and defines infrastructure.

---

Features

- Dynamic Provider and Resource Management  
  Choose from the configured providers and their resources to generate custom Terraform configurations. By default, EITR uses the 35 official (as of December 2024) providers from the Terraform Registry (https://registry.terraform.io/search/providers?namespace=hashicorp&tier=official).

- Template-Based Configuration  
  Leverage Jinja2 templates for consistent and reusable Terraform code.

- Rich User Interface  
  Interactive sidebar navigation, collapsible provider sections, and dynamic content loading.

- Editable Templates  
  Inline editing of Terraform templates directly in the browser.

- Dynamic Preview  
  Review Terraform configurations dynamically before saving the final file.

- Save and Reset Options  
  Save configurations as JSON or HCL and reset the workspace as needed.  Nothing is saved server-side, as the
 config is built dynamically in memory, and is only saved to your local machine.

---

Prerequisites

To run the application, ensure you have the following installed:
- Python 3.12+
- Node.js
- Terraform
- Gunicorn

---

Demo
Visit: https://eitr.gecko.org to view EITR in action.

---

Installation
1. Clone the repository:
   git clone https://github.com/daytonjones/EITR.git
   cd EITR

2. Set up a virtual environment:
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

3. Install dependencies:
   pip install -r requirements.txt

4. Generate the schemas and update the templates:
   python utilities/generate_tf_provider_templates.py

5. Start EITR:
   gunicorn -w 3 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app --daemon --name eitr

6. Access the app in your browser at http://127.0.0.1:8000

---

Usage
1. Open the application in your browser.
2. Select your provider(s) from the left to expand their collapsible sections.
3. Choose the resources you want to include using the checkboxes.
4. Click the "Edit" button to modify templates inline, then save your changes.
5. Click either "Save as JSON" or "Save as HCL" to download the generated Terraform code.
6. Use the "Reset Config" button to clear the workspace and deselect all resources.

To change the providers, edit config/providers.json and then re-run utilities/generate_tf_provider_templates.py.

---

Running utilities/generate_tf_provider_templates.py

This script parses `config/providers.json` and generates all the required Jinja2 templates for the providers, as well as the `config/provider_schemas.json` file. It must be run:

1. Before starting the app for the first time.
2. Anytime the `config/providers.json` file is modified.

### Steps to run:
1. Ensure you have the necessary Python modules installed (see the installation instructions).
2. Run the following command:
   ```bash
   python utilities/generate_tf_provider_templates.py
   ```
This will:

- Generate Jinja2 templates for each provider in the templates/terraform/ directory.
- Create or update the config/provider_schemas.json file containing provider schema information.

Project Structure

```
EITR
├── config
│   └── providers.json
├── Dockerfile
├── LICENSE
├── main.py
├── README.md
├── README.txt
├── requirements.txt
├── static
│   ├── eitr_background.jpeg
│   ├── eitr.ico
│   └── eitr.png
├── templates
│   ├── index.html
│   └── terraform
│       ├── ad
│       ├── archive
│       ├── assert
│       ├── aws
│       ├── awscc
│       ├── azuread
│       ├── azurerm
│       ├── azurestack
│       ├── boundary
│       ├── cloudinit
│       ├── consul
│       ├── dns
│       ├── external
│       ├── google
│       ├── google-beta
│       ├── googleworkspace
│       ├── hcp
│       ├── hcs
│       ├── helm
│       ├── http
│       ├── kubernetes
│       ├── local
│       ├── nomad
│       ├── null
│       ├── opc
│       ├── oraclepaas
│       ├── random
│       ├── salesforce
│       ├── template
│       ├── tfe
│       ├── tfmigrate
│       ├── time
│       ├── tls
│       ├── vault
│       └── vsphere
└── utilities
    └── generate_tf_provider_templates.py
```

License

EITR is licensed under the MIT License. See `LICENSE` for details.

---

