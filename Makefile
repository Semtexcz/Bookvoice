.PHONY: check test typecheck lint

check: lint typecheck test

test:
	poetry run pytest

typecheck:
	poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests

lint:
	poetry run ruff check .
