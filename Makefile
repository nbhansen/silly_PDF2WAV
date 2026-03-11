.PHONY: test test-unit test-integration lint format typecheck check dev-setup run clean

test:
	python -m pytest

test-unit:
	python -m pytest tests/unit/

test-integration:
	python -m pytest tests/integration/

lint:
	ruff check . --fix

format:
	ruff format .

typecheck:
	mypy .

check:  ## Run all checks (lint, format, typecheck, tests)
	pre-commit run --all-files
	python -m pytest tests/unit/

dev-setup:  ## Set up development environment
	pip install -r requirements.txt
	pre-commit install

run:
	python app.py

clean:  ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	rm -rf .ruff_cache
