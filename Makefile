.PHONY: test test-unit test-integration lint format typecheck check dev-setup run clean

test:
	uv run python -m pytest

test-unit:
	uv run python -m pytest tests/unit/

test-integration:
	uv run python -m pytest tests/integration/

lint:
	uv run ruff check . --fix

format:
	uv run ruff format .

typecheck:
	uv run mypy .

check:  ## Run all checks (lint, format, typecheck, tests)
	uv run pre-commit run --all-files
	uv run python -m pytest tests/unit/

dev-setup:  ## Set up development environment
	uv sync --extra dev
	uv run pre-commit install

run:
	uv run python app.py

clean:  ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf .ruff_cache
