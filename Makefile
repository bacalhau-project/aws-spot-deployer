# Makefile for local development and testing
# Prevents CI failures by running all checks locally first

.PHONY: help install test lint format type-check security ci-local pre-commit clean

help:  ## Show this help message
	@echo "🔧 Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync --frozen

test:  ## Run all tests
	uv run pytest tests/ -v

lint:  ## Run linting (ruff check + fix)
	uv run ruff check src/ tests/ scripts/ --fix

format:  ## Run code formatting
	uv run ruff format src/ tests/ scripts/

type-check:  ## Run type checking
	uv run mypy src/spot_deployer/ --ignore-missing-imports --check-untyped-defs

security:  ## Run security checks
	uv run bandit -r src/spot_deployer/ -ll --skip B101,B108,B202,B324,B601

smoke-test:  ## Run smoke tests
	uv run python scripts/smoke-test.py

ci-local:  ## Run full CI pipeline locally (RECOMMENDED BEFORE PUSH)
	@echo "🔧 Running complete CI pipeline locally..."
	./scripts/test-ci-locally.sh

pre-commit:  ## Install and run pre-commit hooks
	uv run pre-commit install
	uv run pre-commit run --all-files

# GitHub Actions simulation
act-setup:  ## Setup GitHub Actions local testing with act
	./scripts/setup-act.sh

act-ci:  ## Run GitHub Actions CI workflow locally (requires act)
	./scripts/run-ci-with-act.sh

# Quality checks (matches CI exactly)
check-all: install lint format type-check security test smoke-test  ## Run all quality checks

clean:  ## Clean cache and temp files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Convenience targets
dev: install pre-commit  ## Setup development environment
push-ready: ci-local  ## Verify you're ready to push (runs full CI locally)
