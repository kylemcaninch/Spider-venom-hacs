SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
VERSION := $(shell sed -n 's/.*"version": "\(.*\)".*/\1/p' custom_components/spider_venom/manifest.json)

.PHONY: help setup test lint format build check

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-8s %s\n", $$1, $$2}'

setup: ## Install dev dependencies from uv.lock
	@command -v uv >/dev/null || { echo "uv not found: https://docs.astral.sh/uv/" >&2; exit 3; }
	uv sync --frozen

test: ## Run tests
	uv run pytest

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .

format: ## Apply formatting
	uv run ruff format .
	uv run ruff check --fix .

build: ## Zip the integration: dist/spider_venom-<version>.zip
	rm -rf dist && mkdir -p dist
	zip -qr dist/spider_venom-$(VERSION).zip custom_components/spider_venom -x '*/__pycache__/*'

check: lint test ## Lint + tests
