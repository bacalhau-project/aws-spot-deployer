"""Bacalhau configuration generation utilities."""

import os
import tempfile
from typing import Optional


def generate_bacalhau_config_with_credentials(
    template_path: str,
    orchestrator_endpoint: Optional[str] = None,
    orchestrator_token: Optional[str] = None,
    files_directory: Optional[str] = None,
) -> str:
    """
    Generate a Bacalhau config.yaml with credentials injected.

    Returns the path to the generated config file.
    """
    # Try to read credentials from files if not provided
    if not orchestrator_endpoint and files_directory:
        endpoint_file = os.path.join(files_directory, "orchestrator_endpoint")
        if os.path.exists(endpoint_file):
            with open(endpoint_file, "r") as f:
                orchestrator_endpoint = f.read().strip()

    if not orchestrator_token and files_directory:
        token_file = os.path.join(files_directory, "orchestrator_token")
        if os.path.exists(token_file):
            with open(token_file, "r") as f:
                orchestrator_token = f.read().strip()

    # If we don't have credentials, then exit with an error
    if not orchestrator_endpoint or not orchestrator_token:
        raise ValueError("No credentials provided")

    # Load the bacalhau config template
    with open(template_path, "r") as f:
        config_content = f.read()

    # Inject the credentials into the config
    config_content = config_content.replace("{{ORCHESTRATOR_ENDPOINT}}", orchestrator_endpoint)
    config_content = config_content.replace("{{ORCHESTRATOR_TOKEN}}", orchestrator_token)

    # Write to temporary file
    temp_config = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    temp_config.write(config_content)
    temp_config.close()

    return temp_config.name
