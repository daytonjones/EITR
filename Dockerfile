FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy application files
COPY . /app

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    snapd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Install Terraform using apt, and fallback to snap if it fails
    (apt-get install -y --no-install-recommends terraform || snap install terraform --classic)

# Install Python dependencies
RUN pip install -r requirements.txt

# Set the default command to run the app
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]

