.PHONY: format format-check lint typecheck test coverage build up down logs compose-config bootstrap-codebase-memory remove-codebase-memory

up:
	docker compose --env-file config/development.defaults up --build

down:
	docker compose --env-file config/development.defaults down

logs:
	docker compose --env-file config/development.defaults logs

compose-config:
	docker compose --env-file config/development.defaults config

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

test:
	uv run pytest

coverage:
	uv run pytest --cov=erp_agent_os --cov-report=term-missing

build:
	uv run python -m build

bootstrap-codebase-memory:
	python scripts/bootstrap-codebase-memory.py

remove-codebase-memory:
	python scripts/bootstrap-codebase-memory.py --remove
