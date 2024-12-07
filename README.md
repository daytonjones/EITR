# EITR - Multi-Provider Terraform Config Generator

## Introduction
- **E**: Environment – Spanning cloud (AWS, Azure, GCP), local, and virtualized setups.
- **I**: Infrastructure – Focused on creating and managing critical infrastructure components.
- **T**: Terraform – The de facto tool for infrastructure as code.
- **R**: Renderer – A system for dynamically generating Terraform configurations.

**EITR** is a web-based application designed to simplify and streamline Terraform configuration generation. It allows users to dynamically select multiple providers and resources, and then generate ready-to-use Terraform templates with minimal effort.  

In Norse mythology, *eitr* represents raw potential and creation, making it the perfect name for a tool that shapes and defines infrastructure.

---

## Features

- **Dynamic Provider and Resource Management**  
  Choose from the configured providers and their resources to generate custom Terraform configurations.  By default, EITR uses the 35 official (as of December, 2024) providers (https://registry.terraform.io/search/providers?namespace=hashicorp&tier=official)

- **Template-Based Configuration**  
  Leverage Jinja2 templates for consistent and reusable Terraform code.

- **Rich User Interface**  
  Interactive sidebar navigation, resource toggles, and dynamic content loading.

- **Preview and Validation**  
  Review Terraform configurations dynamically before generating the final file.


---
## Prerequisites

To run the application, ensure you have the following installed:
- Python 3.12+
- Node.js 
- Terraform
- gunicorn

---

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/daytonjones/EITR.git
   cd EITR
   ```
2. Set up a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Generate the schemas, update the templates:
   ```bash
   utilities/generate_tf_provider_templates.py
   ```
5. Start the application:
   ```bash
   gunicorn -w 3 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app --daemon --name eitr
   ```
6. Access the app in your browser at `http://127.0.0.1:8000`.

## Usage
1. Open the application in your browser.
2. Select your provider(s) from the dropdown menu.
3. Choose the resources you want to create using the checkboxes.
4. Click either "Save as JSON" or "Save as HCL" to download the generated Terraform code.

To change the providers, edit config/providers.json and the re-run "utilities/generate_tf_provider_templates.py" 

## Project Structure

```
EITR
├── config
│   └── providers.json
├── Dockerfile
├── LICENSE
├── main.py
├── README.md
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

## License

EITR is licensed under the MIT License. See `LICENSE` for details.

---

