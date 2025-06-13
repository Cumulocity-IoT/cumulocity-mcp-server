FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1

# Set working directory
WORKDIR /app

# Copy only the necessary files first
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync --locked

EXPOSE 80

# Set the entry point
#ENTRYPOINT ["uv", "run", "mcp-server-c8y",  "--host", "0.0.0.0", "--port", "80", "--transport", "hybrid", "--root-path", "/service/mcp-server-c8y"]
ENTRYPOINT uv run mcp-server-c8y --host 0.0.0.0 --port 80 --transport hybrid --root-path /service/$APPLICATION_NAME