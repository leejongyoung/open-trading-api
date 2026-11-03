# Dockerfile
# Use a Python image with uv pre-installed (Debian-based for better compatibility)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Server settings
ENV MCP_SERVER_NAME=kis-code-assistant-mcp
ENV MCP_SERVER_VERSION=0.1.0

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set the default port
ENV PORT=8081

# 컨테이너 안에서는 0.0.0.0으로 바인딩해야 포트 publish가 가능하다.
# 호스트 노출은 `docker run -p 127.0.0.1:8081:8081`로 로컬에만 제한할 것.
# 인증: -e MCP_ACCESS_TOKEN=..., CORS: -e MCP_CORS_ORIGINS=https://a.example,https://b.example
ENV MCP_HOST=0.0.0.0

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Expose the port that the server will run on
EXPOSE 8081

# Clean up caches to reduce image size
RUN rm -rf /root/.cache/uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Run the application directly using uv
CMD ["uv", "run", "server.py"]