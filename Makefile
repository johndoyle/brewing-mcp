.PHONY: install setup-hooks test lint format check clean

# Install all packages in development mode
install:
	uv sync

# Set up pre-commit hooks
setup-hooks:
	uv run pre-commit install

# Run all tests
test:
	uv run pytest packages/ -v --tb=short

# Run tests with coverage
test-cov:
	uv run pytest packages/ -v --tb=short --cov=packages --cov-report=html --cov-report=term

# Run linting
lint:
	uv run ruff check packages/
	uv run mypy packages/

# Format code
format:
	uv run ruff format packages/
	uv run ruff check --fix packages/

# Run all checks
check: lint test

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# Run a specific MCP server
run-beersmith:
	uv run --package mcp-beersmith python -m mcp_beersmith

run-grocy:
	uv run --package mcp-grocy python -m mcp_grocy

run-brewfather:
	uv run --package mcp-brewfather python -m mcp_brewfather
