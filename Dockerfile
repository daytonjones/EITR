# ── Stage 1: Generate provider schemas and templates ─────────────────────────
# Terraform and jq are installed here and discarded — they never reach the
# final image. Docker's layer cache means provider downloads only re-run
# when config/providers.json changes.
FROM python:3.12-slim AS builder

WORKDIR /build

ARG TERRAFORM_VERSION=1.15.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip jq \
    && ARCH=$(dpkg --print-architecture) \
    && curl -fsSL \
       "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" \
       -o /tmp/tf.zip \
    && unzip /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip \
    && apt-get purge -y --autoremove curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy only what drives generation — cache busts only when these files change
COPY config/providers.json config/providers.json
COPY utilities/generate_tf_provider_templates.py utilities/generate_tf_provider_templates.py

RUN python utilities/generate_tf_provider_templates.py


# ── Stage 2: Runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY static/ static/
COPY config/providers.json config/providers.json
COPY templates/index.html templates/index.html

# Pull generated artifacts from the builder — no terraform in the final image
COPY --from=builder /build/config/provider_schemas.json config/provider_schemas.json
COPY --from=builder /build/templates/terraform/ templates/terraform/

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "main:app"]
