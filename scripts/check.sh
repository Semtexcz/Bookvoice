#!/usr/bin/env sh
set -eu

poetry run ruff check .
poetry run mypy --config-file pyproject.toml --explicit-package-bases bookvoice tests
poetry run pytest
