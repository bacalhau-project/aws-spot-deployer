FROM python:3.13-slim

# Build arguments
ARG BUILD_DATE
ARG BUILD_VERSION
ARG BUILD_COMMIT
ARG DOCKER_TAG

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    openssh-client \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Install Bacalhau CLI for node cleanup (latest version)
RUN curl -sL https://get.bacalhau.org/install.sh | bash

# Set working directory
WORKDIR /app

# Copy package files
COPY pyproject.toml ./
COPY spot_deployer ./spot_deployer
COPY instance ./instance

# Create a dummy README.md for the package (required by pyproject.toml)
RUN echo "# Spot Deployer\n\nSee documentation at https://github.com/bacalhau-project/aws-spot-deployer" > README.md

# Install the package and dependencies
RUN uv pip install --system -e . && \
    # Verify the command is available
    which spot-deployer && \
    spot-deployer help > /dev/null

# Copy entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/config /app/files /app/output

# Set environment variables
ENV SPOT_CONFIG_PATH=/app/config/config.yaml
ENV SPOT_FILES_DIR=/app/files
ENV SPOT_OUTPUT_DIR=/app/output
ENV SPOT_STATE_PATH=/app/output/instances.json
ENV PYTHONPATH=/app

# Set build information
ENV BUILD_DATE=${BUILD_DATE}
ENV BUILD_VERSION=${BUILD_VERSION}
ENV BUILD_COMMIT=${BUILD_COMMIT}
ENV DOCKER_TAG=${DOCKER_TAG}
ENV DOCKER_CONTAINER=true

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["help"]
