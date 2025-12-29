# ==============================================================================
# Dockerfile for neo4j-livelihood-support
# 生活保護受給者尊厳支援データベース
# ==============================================================================

# Stage 1: Base image with uv
FROM python:3.12-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# ==============================================================================
# Stage 2: Builder - Install dependencies
# ==============================================================================
FROM base AS builder

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY lib/ ./lib/
COPY api/ ./api/
COPY mcp/ ./mcp/
COPY app_case_record.py ./
COPY setup_schema.py ./

# ==============================================================================
# Stage 3: FastAPI Production Image
# ==============================================================================
FROM base AS api

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/lib ./lib
COPY --from=builder /app/api ./api
COPY --from=builder /app/pyproject.toml ./

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Change ownership to appuser
RUN chown -R appuser:appuser /app

USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ==============================================================================
# Stage 4: Streamlit Production Image
# ==============================================================================
FROM base AS streamlit

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/lib ./lib
COPY --from=builder /app/app_case_record.py ./
COPY --from=builder /app/pyproject.toml ./

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Change ownership to appuser
RUN chown -R appuser:appuser /app

USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app_case_record.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ==============================================================================
# Stage 5: MCP Server Image
# ==============================================================================
FROM base AS mcp

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy virtual environment and application from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/lib ./lib
COPY --from=builder /app/mcp ./mcp
COPY --from=builder /app/pyproject.toml ./

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Change ownership to appuser
RUN chown -R appuser:appuser /app

USER appuser

# Run MCP server
CMD ["python", "-m", "mcp.server"]
