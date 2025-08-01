# AGENT.md - Development Guide for AI Agents

## Build/Test/Lint Commands
- **Test all**: `uv run python run_tests.py` (with coverage)
- **Single test**: `uv run python -m pytest tests/test_aws_manager.py::TestAWSResourceManager::test_initialization -v`
- **Lint check**: `uv run ruff check spot_deployer/`
- **Format**: `uv run ruff format spot_deployer/`
- **Type check**: `uv run pyright` or `uv run mypy spot_deployer/`
- **Pre-commit**: `uv run pre-commit run --all-files`

## Architecture & Structure
- **Package**: `spot_deployer/` - modular Python package with commands/, core/, utils/
- **Entry point**: `spot_deployer/main.py` - CLI using argparse
- **Managers**: AWSResourceManager, SSHManager, UIManager for centralized operations
- **State**: JSON-based state management (`instances.json`) with SimpleStateManager
- **Config**: YAML-based (`config.yaml`) with SimpleConfig class
- **CLI wrapper**: `./spot-dev` script for local development

## Code Style & Conventions
- **Python**: 3.9+ with full type annotations (`from typing import Dict, List, Optional`)
- **Line length**: 100 chars (ruff configured)
- **Import style**: Standard library, third-party, local imports separated
- **Error handling**: Manager classes handle retries/timeouts internally with exponential backoff
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Required for all public functions using triple quotes
- **No comments**: Code should be self-documenting unless complex logic requires explanation
- **Manager pattern**: All AWS/SSH/UI operations go through respective manager classes
