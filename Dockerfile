FROM python:3.11-slim

WORKDIR /app
COPY src/ ./src/

# Baked in at build time. A change to the vocabulary does not reach a running
# container until the image is rebuilt, so the two have to move together.
COPY config/categories.json ./config/categories.json

ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "digest.cli"]
