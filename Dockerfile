FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Separate venv so azure-cli dependencies do not conflict with the app.
RUN python -m venv /opt/azcli \
    && /opt/azcli/bin/pip install azure-cli \
    && ln -s /opt/azcli/bin/az /usr/local/bin/az

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install .

EXPOSE 8080

CMD ["ai-governance-dev"]
