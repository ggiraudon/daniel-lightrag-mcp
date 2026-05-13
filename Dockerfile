FROM python:3.12-slim

LABEL org.opencontainers.image.title="daniel-lightrag-mcp"
LABEL org.opencontainers.image.description="MCP server for LightRAG integration"
LABEL org.opencontainers.image.version="0.1.0"

ENV LIGHTRAG_BASE_URL="http://host.docker.internal:9621" \
    LIGHTRAG_API_KEY="" \
    LIGHTRAG_TIMEOUT="30" \
    LOG_LEVEL="INFO" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "daniel_lightrag_mcp"]
