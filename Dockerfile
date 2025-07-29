# Dockerfile for MCP Sequential Think Server
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the entire application
COPY . .

# Ensure the virtual environment activation script works
RUN python -m venv .venv

# Make sure the database file has proper permissions
RUN touch sequential_think_prompts.db && chmod 666 sequential_think_prompts.db

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose ports for both stdio and SSE modes
EXPOSE 7070 7071

# Default command (can be overridden)
CMD ["python", "sequential_think_server.py", "--transport", "stdio"]
