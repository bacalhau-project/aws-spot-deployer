# Multi-stage build for optimal size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements first for better caching
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv in production image
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY spot_deployer/ ./spot_deployer/
COPY instance/ ./instance/
COPY requirements.txt .

# Create directories for mounted files
RUN mkdir -p /app/config /app/files /app/output

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set up non-root user (optional, commented out for AWS compatibility)
# RUN useradd -m -s /bin/bash spotuser
# USER spotuser

# Environment variables for configuration
ENV SPOT_CONFIG_PATH=/app/config/config.yaml
ENV SPOT_FILES_DIR=/app/files
ENV SPOT_OUTPUT_DIR=/app/output

# Default to help command
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["help"]